import hashlib
import json
import logging
import re
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config.categories import CATEGORY_PRIORITY, FOLDER_TO_CATEGORY
from config.settings import (
    DATA_ROOT,
    DEDUP_SIMILARITY_THRESHOLD,
    DEDUP_CROSS_DAY_THRESHOLD,
    DEDUP_EMBEDDING_MODEL,
    DEDUP_HISTORY_DAYS,
    DEDUP_TFIDF_OVERLAP_THRESHOLD,
)
logger = logging.getLogger("todards.dedup")
class ArticleDuplicateRemover:

    FOLDERS = [
        "health_data",
        "tech_data",
        "people_data",
        "environment_data",
        "economy_data",
        "entertainment_data",
    ]
    def __init__(
        self,
        data_root: Optional[Path] = None,
        similarity_threshold: float = DEDUP_SIMILARITY_THRESHOLD,
        cross_day_threshold: float = DEDUP_CROSS_DAY_THRESHOLD,
        model_name: str = DEDUP_EMBEDDING_MODEL,
        days: int = DEDUP_HISTORY_DAYS,
        metrics_collector=None,
    ):
        self.data_root = Path(data_root or DATA_ROOT)
        self.similarity_threshold = similarity_threshold
        self.cross_day_threshold = cross_day_threshold
        self.days = days
        self.metrics = metrics_collector
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.records: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.duplicate_pairs: List[Dict[str, Any]] = []
        self.duplicate_clusters: List[List[int]] = []
       
    # TEXT NORMALIZATION
       
    @staticmethod
    def clean_text(text: Any) -> str:

        if text is None:
            return ""
        text = str(text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    @staticmethod
    def normalize_for_hash(text: str) -> str:
        text = str(text).lower()
        # Remove punctuation
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    @classmethod
    def titles_are_duplicates(cls, title_a: str, title_b: str) -> bool:
        a = cls.normalize_for_hash(title_a)
        b = cls.normalize_for_hash(title_b)
        if not a or not b:
            return False
        if a == b:
            return len(a) >= 12
        # A close headline match is strong evidence, but avoid very short,
        # generic titles where a character-level match is less meaningful.
        if min(len(a), len(b)) >= 22 and SequenceMatcher(None, a, b).ratio() >= 0.92:
            return True
        # Catch reordered or lightly edited headlines.
        words_a = set(a.split())
        words_b = set(b.split())
        if min(len(words_a), len(words_b)) >= 4:
            overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
            if overlap >= 0.85:
                return True
        return False
    @classmethod
    def create_fingerprint(cls, title: str, content: str) -> str:
        normalized_title = cls.normalize_for_hash(title)
        normalized_content = cls.normalize_for_hash(content)
        combined = f"{normalized_title} {normalized_content}".strip()
        return hashlib.sha256(
            combined.encode("utf-8")
        ).hexdigest()
       
    # LOAD ARTICLES
       
    def load_articles(self, days: Optional[int] = None):
        days = days or self.days
        self.records = []
        today = datetime.now().date()
        valid_dates = {
            (today - timedelta(days=i)).strftime("%d%m%Y")
            for i in range(days)
        }
        today_str = today.strftime("%d%m%Y")
        logger.info(
            f"Checking articles from last {days} days: "
            f"{', '.join(sorted(valid_dates))}"
        )
        for folder_name in self.FOLDERS:
            folder = self.data_root / folder_name
            if not folder.exists():
                logger.debug(f"Folder does not exist: {folder}")
                continue
            for file_path in sorted(folder.glob("*.json")):
                filename = file_path.name
                file_date = filename[:8]
                if file_date not in valid_dates:
                    continue
                try:
                    with open(
                        file_path,
                        "r",
                        encoding="utf-8",
                    ) as f:
                        data = json.load(f)
                except Exception as e:
                    logger.warning(
                        f"Could not read {file_path}: {e}"
                    )
                    continue
                if not isinstance(data, list):
                    continue
                for index, article in enumerate(data):
                    if not isinstance(article, dict):
                        continue
                    title = self.clean_text(
                        article.get("title", "")
                    )
                    content = self.clean_text(
                        article.get("content", "")
                    )
                    if not title and not content:
                        continue
                    combined_text = (
                        f"{title}. {content}"
                    ).strip()
                    fingerprint = self.create_fingerprint(
                        title,
                        content,
                    )
                    self.records.append(
                        {
                            "file_path": file_path,
                            "article_index": index,
                            "article": article,
                            "folder": folder_name,
                            "title": title,
                            "content": content,
                            "combined_text": combined_text,
                            "file_date": file_date,
                            "is_today": file_date == today_str,
                            "fingerprint": fingerprint,
                        }
                    )
        logger.info(
            f"Loaded {len(self.records)} articles across {days} days."
        )
       
    # EXACT DUPLICATES
       
    def find_exact_duplicates(self) -> List[Dict[str, Any]]:
        fingerprint_map: Dict[str, List[int]] = defaultdict(list)
        for index, record in enumerate(self.records):
            fingerprint_map[
                record["fingerprint"]
            ].append(index)
        duplicate_pairs = []
        for fingerprint, indices in fingerprint_map.items():
            if len(indices) < 2:
                continue
            # First article is the initial keeper.
            keeper = indices[0]
            for duplicate_index in indices[1:]:
                delete_index = self.choose_delete(
                    keeper,
                    duplicate_index,
                )
                duplicate_pairs.append(
                    {
                        "i": keeper,
                        "j": duplicate_index,
                        "similarity": 1.0,
                        "tfidf_overlap": 1.0,
                        "method": "exact",
                        "delete": delete_index,
                    }
                )
                # If the duplicate has higher priority, it becomes
                # the keeper for subsequent copies.
                if delete_index == keeper:
                    keeper = duplicate_index
        logger.info(
            f"Exact duplicate pairs found: {len(duplicate_pairs)}"
        )
        return duplicate_pairs
       
    # EMBEDDINGS
       
    def create_embeddings(self):
        if not self.records:
            self.embeddings = np.empty((0, 0))
            return
        texts = [
            record["combined_text"]
            for record in self.records
        ]
        logger.info(
            "Computing article embeddings with title + content..."
        )
        self.embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
       
    # TF-IDF
       
    def _calculate_tfidf_overlap(
        self,
        text_a: str,
        text_b: str,
        top_k: int = 15,
    ) -> float:
 
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=200,
            )
            tfidf = vectorizer.fit_transform(
                [text_a, text_b]
            )
            feature_names = np.array(
                vectorizer.get_feature_names_out()
            )
            if len(feature_names) == 0:
                return 0.0
            scores_a = tfidf[0].toarray()[0]
            scores_b = tfidf[1].toarray()[0]
            top_a_indices = np.argsort(scores_a)[::-1][:top_k]
            top_b_indices = np.argsort(scores_b)[::-1][:top_k]
            words_a = set(
                feature_names[top_a_indices]
            )
            words_b = set(
                feature_names[top_b_indices]
            )
            if not words_a or not words_b:
                return 0.0
            intersection = words_a.intersection(words_b)
            return len(intersection) / min(
                len(words_a),
                len(words_b),
            )
        except Exception:
            return 0.0
       
    # DELETE PRIORITY
       
    def choose_delete(self, i: int, j: int) -> int:

        a = self.records[i]
        b = self.records[j]
          
        # Rule 1: Today's article
          
        if a["is_today"] and not b["is_today"]:
            return j
        if b["is_today"] and not a["is_today"]:
            return i
          
        # Rule 2: Category priority
          
        prio_a = CATEGORY_PRIORITY.get(
            a["folder"],
            1,
        )
        prio_b = CATEGORY_PRIORITY.get(
            b["folder"],
            1,
        )
        if prio_a > prio_b:
            return j
        if prio_b > prio_a:
            return i
          
        # Rule 3: Longer content
          
        len_a = len(a["content"])
        len_b = len(b["content"])
        if len_a > len_b:
            return j
        if len_b > len_a:
            return i
          
        # Rule 4: Tie
          
        return j
       
    # SEMANTIC DUPLICATES
       
    def find_semantic_duplicates(
        self,
        excluded_indices: Optional[Set[int]] = None,
    ) -> List[Dict[str, Any]]:

        if (
            self.embeddings is None
            or len(self.records) < 2
        ):
            return []
        excluded_indices = excluded_indices or set()
        similarity_matrix = cosine_similarity(
            self.embeddings
        )
        duplicate_pairs = []
        for i in range(len(self.records)):
            if i in excluded_indices:
                continue
            for j in range(i + 1, len(self.records)):
                if j in excluded_indices:
                    continue
                score = float(
                    similarity_matrix[i, j]
                )
                record_a = self.records[i]
                record_b = self.records[j]
                is_same_day = (
                    record_a["file_date"]
                    == record_b["file_date"]
                )
                threshold = (
                    self.similarity_threshold
                    if is_same_day
                    else self.cross_day_threshold
                )
                is_duplicate = False
                tfidf_overlap = 0.0
                method = "semantic"
                # Headline matching is independent of body similarity. This
                # catches same-category duplicates whose summaries differ.
                if self.titles_are_duplicates(
                    record_a["title"], record_b["title"]
                ):
                    is_duplicate = True
                    method = "title"
                # Strong semantic match
                elif score >= threshold:
                    is_duplicate = True
                # Borderline semantic match
                elif score >= threshold - 0.08:
                    tfidf_overlap = (
                        self._calculate_tfidf_overlap(
                            record_a["combined_text"],
                            record_b["combined_text"],
                        )
                    )
                    if (
                        tfidf_overlap
                        >= DEDUP_TFIDF_OVERLAP_THRESHOLD
                    ):
                        is_duplicate = True
                        method = "semantic+tfidf"
                if not is_duplicate:
                    continue
                delete_index = self.choose_delete(
                    i,
                    j,
                )
                duplicate_pairs.append(
                    {
                        "i": i,
                        "j": j,
                        "similarity": round(
                            score,
                            4,
                        ),
                        "tfidf_overlap": round(
                            tfidf_overlap,
                            4,
                        ),
                        "method": method,
                        "delete": delete_index,
                    }
                )
        return duplicate_pairs
       
    # DUPLICATE GRAPH
       
    def build_duplicate_clusters(
        self,
        pairs: List[Dict[str, Any]],
    ) -> List[List[int]]:
  
        if not pairs:
            return []
        parent: Dict[int, int] = {}
        rank: Dict[int, int] = {}
        def find(x: int) -> int:
            if x not in parent:
                parent[x] = x
                rank[x] = 0
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        def union(a: int, b: int):
            root_a = find(a)
            root_b = find(b)
            if root_a == root_b:
                return
            if rank[root_a] < rank[root_b]:
                parent[root_a] = root_b
            elif rank[root_a] > rank[root_b]:
                parent[root_b] = root_a
            else:
                parent[root_b] = root_a
                rank[root_a] += 1
        for pair in pairs:
            union(
                pair["i"],
                pair["j"],
            )
        clusters: Dict[int, List[int]] = defaultdict(list)
        for index in parent:
            clusters[find(index)].append(index)
        result = [
            sorted(cluster)
            for cluster in clusters.values()
            if len(cluster) > 1
        ]
        result.sort(
            key=lambda x: len(x),
            reverse=True,
        )
        return result
       
    # RESOLVE CLUSTERS
       
    def resolve_clusters(
        self,
        clusters: List[List[int]],
    ) -> Set[int]:
 
        deleted: Set[int] = set()
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            keeper = cluster[0]
            for candidate in cluster[1:]:
                delete_index = self.choose_delete(
                    keeper,
                    candidate,
                )
                if delete_index == keeper:
                    keeper = candidate
                deleted.add(delete_index)
            # Safety: the final keeper must never be deleted.
            deleted.discard(keeper)
        return deleted
       
    # PRINT DUPLICATES
       
    def print_duplicates(
        self,
        pairs: List[Dict[str, Any]],
        clusters: List[List[int]],
    ):
  
        if not pairs:
            print("\nNo duplicates found.")
            return
        print("\n" + "=" * 90)
        print(
            f"DUPLICATE PAIRS FOUND: {len(pairs)}"
        )
        print(
            f"DUPLICATE CLUSTERS: {len(clusters)}"
        )
        print("=" * 90)
        for number, cluster in enumerate(
            clusters,
            1,
        ):
            print(
                f"\nDuplicate Cluster #{number}"
            )
            print(
                f"Articles in cluster: {len(cluster)}"
            )
            # Determine keeper using the same priority rules.
            keeper = cluster[0]
            for candidate in cluster[1:]:
                delete_index = self.choose_delete(
                    keeper,
                    candidate,
                )
                if delete_index == keeper:
                    keeper = candidate
            keeper_record = self.records[keeper]
            print(
                f"KEEP: "
                f"{keeper_record['file_path']} | "
                f"{keeper_record['folder']} | "
                f"{keeper_record['title'][:80]}"
            )
            for index in cluster:
                if index == keeper:
                    continue
                record = self.records[index]
                # Find similarity for this pair if available.
                similarities = [
                    pair["similarity"]
                    for pair in pairs
                    if (
                        (
                            pair["i"] == keeper
                            and pair["j"] == index
                        )
                        or (
                            pair["i"] == index
                            and pair["j"] == keeper
                        )
                    )
                ]
                similarity_text = (
                    f"{max(similarities):.4f}"
                    if similarities
                    else "clustered"
                )
                print(
                    f"DELETE: "
                    f"{record['file_path']} | "
                    f"{record['folder']} | "
                    f"{record['title'][:80]} | "
                    f"similarity={similarity_text}"
                )
       
    # DELETE FROM FILES
       
    def delete_from_files(
        self,
        deleted_indices: Set[int],
    ) -> int:
      
        if not deleted_indices:
            return 0
        by_file: Dict[Path, List[int]] = defaultdict(list)
        for index in deleted_indices:
            record = self.records[index]
            by_file[
                record["file_path"]
            ].append(
                record["article_index"]
            )
        total_deleted = 0
        for file_path, indices in by_file.items():
            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8",
                ) as f:
                    data = json.load(f)
                delete_positions = set(indices)
                new_data = [
                    article
                    for idx, article in enumerate(data)
                    if idx not in delete_positions
                ]
                removed = (
                    len(data)
                    - len(new_data)
                )
                with open(
                    file_path,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(
                        new_data,
                        f,
                        ensure_ascii=False,
                        indent=4,
                    )
                total_deleted += removed
                logger.info(
                    f"Updated {file_path.name}: "
                    f"removed {removed}, "
                    f"remaining {len(new_data)}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to update {file_path}: {e}"
                )
        return total_deleted
      
    # MAIN PIPELINE
      
       
    # READ-ONLY PUBLICATION REFERENCE FILTER
       
    def remove_published_duplicates(
        self,
        publication_data: Dict[str, Any],
    ) -> int:

        sections = publication_data.get("sections", [])
        if not isinstance(sections, list) or not sections or not self.records:
            logger.info("No usable publication references or incoming articles.")
            return 0
        references = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            cards = section.get("cards", [])
            if not isinstance(cards, list):
                continue
            for card in cards:
                if not isinstance(card, dict):
                    continue
                title = self.clean_text(card.get("title", ""))
                content = self.clean_text(card.get("content", card.get("summary", "")))
                if not title and not content:
                    continue
                references.append({
                    "title": title,
                    "content": content,
                    "combined_text": f"{title}. {content}".strip(),
                    "fingerprint": self.create_fingerprint(title, content),
                })
        if not references:
            logger.info("Publication reference contains no usable cards.")
            return 0
        # Only today's scraped records are "incoming". Older source files
        # remain available for cross-day source deduplication, but this
        # publication-reference pass must not delete them.
        incoming_indices = [
            index for index, record in enumerate(self.records)
            if record.get("is_today")
        ]
        if not incoming_indices:
            logger.info("No today's incoming source articles to compare.")
            return 0
        incoming_texts = [
            self.records[index]["combined_text"] for index in incoming_indices
        ]
        reference_texts = [record["combined_text"] for record in references]
        embeddings = self.model.encode(
            incoming_texts + reference_texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        incoming_embeddings = embeddings[:len(incoming_indices)]
        reference_embeddings = embeddings[len(incoming_indices):]
        deleted_indices = set()
        matches = []
        for local_index, source_index in enumerate(incoming_indices):
            incoming = self.records[source_index]
            for reference_index, reference in enumerate(references):
                score = float(
                    np.dot(
                        incoming_embeddings[local_index],
                        reference_embeddings[reference_index],
                    )
                )
                method = None
                if incoming["fingerprint"] == reference["fingerprint"]:
                    method = "exact"
                elif self.titles_are_duplicates(incoming["title"], reference["title"]):
                    method = "title"
                elif score >= self.cross_day_threshold:
                    method = "semantic"
                elif score >= self.cross_day_threshold - 0.08:
                    overlap = self._calculate_tfidf_overlap(
                        incoming["combined_text"], reference["combined_text"]
                    )
                    if overlap >= DEDUP_TFIDF_OVERLAP_THRESHOLD:
                        method = "semantic+tfidf"
                if method:
                    deleted_indices.add(source_index)
                    matches.append(
                        (incoming["title"], reference["title"], method, score)
                    )
                    break
        for incoming_title, reference_title, method, score in matches:
            logger.info(
                "Rejecting incoming article already covered by publication "
                "reference: incoming=%r | reference=%r | method=%s | similarity=%.4f",
                incoming_title, reference_title, method, score,
            )
        removed = self.delete_from_files(deleted_indices)
        logger.info(
            "Read-only publication-reference filtering complete: "
            "matched=%d, removed_from_source_files=%d; publication unchanged.",
            len(deleted_indices), removed,
        )
        return removed
    def run(
        self,
        publication_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
  
        logger.info(
            "Running Article Duplicate Remover "
            f"(within-day: {self.similarity_threshold}, "
            f"cross-day: {self.cross_day_threshold})"
        )
          
        # 1. Load
          
        self.load_articles()
        # Treat the existing publication strictly as a read-only reference.
        # Delete only matching incoming source records, then reload because
        # source-file indices may have changed after removal.
        published_duplicates_removed = 0
        if publication_data is not None:
            published_duplicates_removed = self.remove_published_duplicates(
                publication_data
            )
            if published_duplicates_removed:
                self.load_articles()
        if len(self.records) < 2:
            logger.info(
                "Not enough articles to compare."
            )
            report = {
                "total_checked": len(self.records),
                "exact_duplicate_pairs": 0,
                "semantic_duplicate_pairs": 0,
                "duplicate_pairs_found": 0,
                "duplicate_clusters": 0,
                "duplicates_removed": 0,
                "published_duplicates_removed": published_duplicates_removed,
            }
            return report
       
        # 2. Exact duplicate detection
        
        exact_pairs = (
            self.find_exact_duplicates()
        )
        exact_duplicate_indices = set()
        for pair in exact_pairs:
            exact_duplicate_indices.add(
                pair["i"]
            )
            exact_duplicate_indices.add(
                pair["j"]
            )
        
        # 3. Semantic embeddings
       
        self.create_embeddings()
        
        # 4. Semantic duplicate detection
                # We still allow semantic comparison between exact duplicates
        # because an exact group may contain the strongest representative.
        # The final graph handles everything together.
        
        semantic_pairs = (
            self.find_semantic_duplicates()
        )
         
        # 5. Combine duplicate relationships
         
        all_pairs = (
            exact_pairs
            + semantic_pairs
        )
        # Remove duplicate relationships.
        unique_relationships = {}
        for pair in all_pairs:
            a = min(
                pair["i"],
                pair["j"],
            )
            b = max(
                pair["i"],
                pair["j"],
            )
            key = (a, b)
            # Keep strongest evidence.
            if key not in unique_relationships:
                unique_relationships[key] = pair
            else:
                existing = unique_relationships[key]
                if pair["similarity"] > existing["similarity"]:
                    unique_relationships[key] = pair
        all_pairs = list(
            unique_relationships.values()
        )
        
        # 6. Build duplicate clusters
        
        clusters = (
            self.build_duplicate_clusters(
                all_pairs
            )
        )
        self.duplicate_pairs = all_pairs
        self.duplicate_clusters = clusters
          
        # 7. Print diagnostics
       
        self.print_duplicates(
            all_pairs,
            clusters,
        )
          
        # 8. Resolve clusters
        
        deleted_indices = (
            self.resolve_clusters(
                clusters
            )
        )
          
        # 9. Modify JSON files
          
        total_deleted = (
            self.delete_from_files(
                deleted_indices
            )
        )
          
        # 10. Report
          
        exact_count = sum(
            1
            for pair in all_pairs
            if pair["method"] == "exact"
        )
        semantic_count = sum(
            1
            for pair in all_pairs
            if pair["method"] != "exact"
        )
        report = {
            "total_checked": len(
                self.records
            ),
            "exact_duplicate_pairs": exact_count,
            "semantic_duplicate_pairs": semantic_count,
            "duplicate_pairs_found": len(
                all_pairs
            ),
            "duplicate_clusters": len(
                clusters
            ),
            "duplicates_removed": total_deleted,
            "published_duplicates_removed": published_duplicates_removed,
        }
        if self.metrics:
            self.metrics.log_dedup_results(
                report
            )
        logger.info(
            "Source-file deduplication complete: "
            f"checked={report['total_checked']}, "
            f"pairs={report['duplicate_pairs_found']}, "
            f"clusters={report['duplicate_clusters']}, "
            f"removed={report['duplicates_removed']}"
        )
        return report
      
    # FINAL PUBLICATION JSON DEDUPLICATION
       
    def deduplicate_publication_data(
        self,
        publication_data: Dict[str, Any],
    ) -> Dict[str, Any]:

        sections = publication_data.get("sections", [])
        if not isinstance(sections, list):
            logger.warning("Final publication JSON has no valid sections list.")
            return {
                "total_checked": 0,
                "duplicate_pairs_found": 0,
                "duplicate_clusters": 0,
                "duplicates_removed": 0,
            }
        flat_records: List[Dict[str, Any]] = []
        refs: List[Tuple[int, int]] = []
        category_to_folder = {
            str(category).strip().lower(): folder
            for folder, category in FOLDER_TO_CATEGORY.items()
        }
        for section_index, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            section_id = self.clean_text(section.get("id", "")).lower()
            folder = category_to_folder.get(section_id, section_id)
            cards = section.get("cards", [])
            if not isinstance(cards, list):
                continue
            for card_index, card in enumerate(cards):
                if not isinstance(card, dict):
                    continue
                title = self.clean_text(card.get("title", ""))
                content = self.clean_text(
                    card.get("content", card.get("summary", ""))
                )
                if not title and not content:
                    continue
                combined_text = f"{title}. {content}".strip()
                flat_records.append({
                    "file_path": Path("<final-publication-json>"),
                    "article_index": len(flat_records),
                    "article": card,
                    "folder": folder,
                    "title": title,
                    "content": content,
                    "combined_text": combined_text,
                    "file_date": datetime.now().strftime("%d%m%Y"),
                    "is_today": True,
                    "fingerprint": self.create_fingerprint(title, content),
                    "section_index": section_index,
                    "card_index": card_index,
                })
                refs.append((section_index, card_index))
        total = len(flat_records)
        if total < 2:
            return {
                "total_checked": total,
                "duplicate_pairs_found": 0,
                "duplicate_clusters": 0,
                "duplicates_removed": 0,
            }
        # Preserve the source-dedup state while reusing its loaded model.
        old_records = self.records
        old_embeddings = self.embeddings
        old_pairs = self.duplicate_pairs
        old_clusters = self.duplicate_clusters
        try:
            self.records = flat_records
            # Exact normalized title + content matches.
            fingerprint_map: Dict[str, List[int]] = defaultdict(list)
            for index, record in enumerate(flat_records):
                fingerprint_map[record["fingerprint"]].append(index)
            exact_pairs: List[Dict[str, Any]] = []
            for indices in fingerprint_map.values():
                if len(indices) < 2:
                    continue
                anchor = indices[0]
                for other in indices[1:]:
                    exact_pairs.append({
                        "i": anchor,
                        "j": other,
                        "similarity": 1.0,
                        "tfidf_overlap": 1.0,
                        "method": "exact",
                        "delete": self.choose_delete(anchor, other),
                    })
            # Semantic comparisons across all cards, regardless of section.
            texts = [record["combined_text"] for record in flat_records]
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            self.embeddings = embeddings
            similarity_matrix = cosine_similarity(embeddings)
            semantic_pairs: List[Dict[str, Any]] = []
            for i in range(total):
                for j in range(i + 1, total):
                    score = float(similarity_matrix[i, j])
                    overlap = 0.0
                    method = "semantic"
                    is_duplicate = self.titles_are_duplicates(
                        flat_records[i]["title"], flat_records[j]["title"]
                    )
                    if is_duplicate:
                        method = "title"
                    elif score >= self.similarity_threshold:
                        is_duplicate = True
                    else:
                        is_duplicate = False
                    if (
                        not is_duplicate
                        and score >= self.similarity_threshold - 0.08
                    ):
                        overlap = self._calculate_tfidf_overlap(
                            flat_records[i]["combined_text"],
                            flat_records[j]["combined_text"],
                        )
                        if overlap >= DEDUP_TFIDF_OVERLAP_THRESHOLD:
                            is_duplicate = True
                            method = "semantic+tfidf"
                    if is_duplicate:
                        semantic_pairs.append({
                            "i": i,
                            "j": j,
                            "similarity": round(score, 4),
                            "tfidf_overlap": round(overlap, 4),
                            "method": method,
                            "delete": self.choose_delete(i, j),
                        })
            # Merge relationships so each pair appears only once.
            relationships: Dict[Tuple[int, int], Dict[str, Any]] = {}
            for pair in exact_pairs + semantic_pairs:
                key = (min(pair["i"], pair["j"]), max(pair["i"], pair["j"]))
                existing = relationships.get(key)
                if existing is None or pair["similarity"] > existing["similarity"]:
                    relationships[key] = pair
            pairs = list(relationships.values())
            clusters = self.build_duplicate_clusters(pairs)
            deleted_indices = self.resolve_clusters(clusters)
            # Remove duplicates across categories/sections, retaining the
            # article selected by the existing category/content priority.
            deleted_by_section: Dict[int, Set[int]] = defaultdict(set)
            for flat_index in deleted_indices:
                section_index, card_index = refs[flat_index]
                deleted_by_section[section_index].add(card_index)
            for section_index, card_indices in deleted_by_section.items():
                cards = sections[section_index].get("cards", [])
                sections[section_index]["cards"] = [
                    card
                    for card_index, card in enumerate(cards)
                    if card_index not in card_indices
                ]
            report = {
                "total_checked": total,
                "duplicate_pairs_found": len(pairs),
                "duplicate_clusters": len(clusters),
                "duplicates_removed": len(deleted_indices),
            }
            logger.info("Final publication deduplication: %s", report)
            return report
        finally:
            self.records = old_records
            self.embeddings = old_embeddings
            self.duplicate_pairs = old_pairs
            self.duplicate_clusters = old_clusters
    def deduplicate_final_json(self, json_path: Path) -> Dict[str, Any]:
  
        json_path = Path(json_path)
        with json_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        report = self.deduplicate_publication_data(data)
        temporary_path = json_path.with_suffix(json_path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        temporary_path.replace(json_path)
        return report
    
if __name__ == "__main__":
    remover = ArticleDuplicateRemover()
    result = remover.run()
    print("\n" + "=" * 90)
    print("DEDUPLICATION SUMMARY")
    print("=" * 90)
    for key, value in result.items():
        print(f"{key}: {value}")