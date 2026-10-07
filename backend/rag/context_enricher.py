"""
Todards Pipeline — RAG Context Enricher

Queries local ChromaDB historical archive to find related past reporting.
Injects concise historical context into the summarizer prompt when relevant.
"""

import logging
from typing import Optional, List, Dict, Any

from backend.rag.archive import HistoricalArticleArchive
from config.settings import RAG_SIMILARITY_THRESHOLD, RAG_MAX_HISTORY_RESULTS

logger = logging.getLogger("todards.rag.enricher")


class ContextEnricher:
    """
    Enriches new incoming articles with historical Todards context.
    """

    def __init__(
        self,
        archive: Optional[HistoricalArticleArchive] = None,
        similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
        max_results: int = RAG_MAX_HISTORY_RESULTS,
    ):
        self.archive = archive or HistoricalArticleArchive()
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results

    def get_context(self, title: str, content: str) -> Optional[str]:
        """
        Query ChromaDB for relevant historical coverage of this topic.
        Returns formatted context string if found, otherwise None.
        """
        if not self.archive.enabled:
            return None

        self.archive._init_db()
        if not self.archive._collection or not self.archive._embedding_model:
            return None

        # Check if there are any archived records
        try:
            if self.archive._collection.count() == 0:
                return None
        except Exception:
            return None

        query_text = f"{title}. {content[:300]}".strip()
        if not query_text:
            return None

        try:
            query_embed = self.archive._embedding_model.encode(
                [query_text],
                normalize_embeddings=True,
            ).tolist()

            results = self.archive._collection.query(
                query_embeddings=query_embed,
                n_results=min(self.max_results, self.archive._collection.count()),
                include=["metadatas", "documents", "distances"],
            )

            if not results or not results.get("distances") or not results["distances"][0]:
                return None

            relevant_entries = []
            distances = results["distances"][0]
            metadatas = results["metadatas"][0]
            docs = results["documents"][0]

            for dist, meta, doc in zip(distances, metadatas, docs):
                # ChromaDB cosine distance: distance = 1 - cosine_similarity
                similarity = 1.0 - dist
                if similarity >= self.similarity_threshold:
                    date = meta.get("date", "Previously")
                    category = meta.get("category", "")
                    past_title = meta.get("title", "")
                    brief = doc[:120].strip()

                    entry = f"- On {date} ({category}): '{past_title}' — {brief}..."
                    relevant_entries.append(entry)

            if relevant_entries:
                logger.info(f"RAG found {len(relevant_entries)} historical articles for '{title[:30]}...'")
                return "\n".join(relevant_entries)

            return None

        except Exception as e:
            logger.warning(f"RAG context query failed: {e}")
            return None
