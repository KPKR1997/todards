"""
Todards Pipeline — Local RAG Historical Archive

Maintains a persistent vector store of published articles in ChromaDB.
Zero external API cost; uses local sentence-transformers for embeddings.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import (
    RAG_STORE_DIR,
    RAG_COLLECTION_NAME,
    DEDUP_EMBEDDING_MODEL,
    RAG_ENABLED,
)

logger = logging.getLogger("todards.rag.archive")


class HistoricalArticleArchive:
    """
    Local vector store for published Todards articles using ChromaDB.
    """

    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = RAG_COLLECTION_NAME,
        embedding_model_name: str = DEDUP_EMBEDDING_MODEL,
        enabled: bool = RAG_ENABLED,
    ):
        self.enabled = enabled
        self.persist_directory = Path(persist_directory or RAG_STORE_DIR)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name

        self._client = None
        self._collection = None
        self._embedding_model = None

    def _init_db(self):
        if not self.enabled or self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.persist_directory))

            self._embedding_model = SentenceTransformer(self.embedding_model_name)

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB initialized at {self.persist_directory} "
                f"with collection '{self.collection_name}' ({self._collection.count()} articles)."
            )
        except Exception as e:
            logger.warning(f"Could not initialize ChromaDB: {e}. RAG archive will be disabled.")
            self.enabled = False

    def archive_published_articles(self, articles: List[Dict[str, Any]], date_str: Optional[str] = None):
        """
        Archive final published articles from today's issue into ChromaDB.
        """
        if not self.enabled:
            return

        self._init_db()
        if not self._collection or not self._embedding_model:
            return

        if not articles:
            return

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for art in articles:
            art_id = str(art.get("id") or f"{date_str}_{art.get('category', 'gen')}_{len(ids)}")
            title = art.get("title", "")
            content = art.get("content", "")
            category = art.get("category", "")
            place = art.get("place", "")

            # Combine title + summary for semantic indexing
            doc_text = f"{title}. {content}".strip()
            if not doc_text:
                continue

            ids.append(f"{date_str}_{art_id}")
            documents.append(doc_text)
            metadatas.append({
                "date": date_str,
                "title": title,
                "category": category,
                "place": place,
                "url": art.get("image", ""),
            })

        if not documents:
            return

        try:
            embeds = self._embedding_model.encode(
                documents,
                batch_size=16,
                normalize_embeddings=True,
            ).tolist()

            # Upsert into collection
            self._collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeds,
            )
            logger.info(f"Archived {len(documents)} published articles into RAG vector store.")
        except Exception as e:
            logger.error(f"Failed to archive articles into ChromaDB: {e}")

    def count(self) -> int:
        if not self.enabled:
            return 0
        self._init_db()
        if self._collection:
            return self._collection.count()
        return 0
