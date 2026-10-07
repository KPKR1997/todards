"""
Todards Pipeline — Enhanced Article Deduplication

Finds semantically duplicate articles across categories and days using:
1. SentenceTransformer embeddings (title + content concatenation)
2. Dual similarity thresholds (within-day: 0.75, cross-day: 0.85)
3. TF-IDF top keyword overlap verification
4. Category priority hierarchy when deciding which copy to prune
5. Structured reporting for pipeline metrics and evaluation
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

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
    """
    Enhanced deduplication engine for Todards articles.
    """

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

        self.model = SentenceTransformer(model_name)
        self.records: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.duplicate_log: List[Dict[str, Any]] = []

    @staticmethod
    def clean_text(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text)).strip()

    def load_articles(self, days: Optional[int] = None):
        days = days or self.days
        self.records = []

        folders = [
            "health_data",
            "tech_data",
            "people_data",
            "environment_data",
            "economy_data",
            "entertainment_data"
        ]

        today = datetime.now().date()
        valid_dates = {
            (today - timedelta(days=i)).strftime("%d%m%Y")
            for i in range(days)
        }
        today_str = today.strftime("%d%m%Y")

        logger.info(f"Checking articles from last {days} days: {', '.join(sorted(valid_dates))}")

        for folder_name in folders:
            folder = self.data_root / folder_name
            if not folder.exists():
                continue

            for file_path in sorted(folder.glob("*.json")):
                filename = file_path.name
                file_date = filename[:8]

                if file_date not in valid_dates:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
                    continue

                if not isinstance(data, list):
                    continue

                for index, article in enumerate(data):
                    if not isinstance(article, dict):
                        continue

                    title = self.clean_text(article.get("title", ""))
                    content = self.clean_text(article.get("content", ""))

                    if not content and not title:
                        continue

                    # Text used for embeddings: title carries high event signal
                    combined_text = f"{title}. {content}".strip()

                    self.records.append({
                        "file_path": file_path,
                        "article_index": index,
                        "article": article,
                        "folder": folder_name,
                        "title": title,
                        "content": content,
                        "combined_text": combined_text,
                        "file_date": file_date,
                        "is_today": (file_date == today_str),
                    })

        logger.info(f"Loaded {len(self.records)} articles across {days} days.")

    def create_embeddings(self):
        texts = [record["combined_text"] for record in self.records]
        logger.info("Computing article embeddings with title + content signal...")
        self.embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def _calculate_tfidf_overlap(self, text_a: str, text_b: str, top_k: int = 10) -> float:
        """Calculate overlap of top TF-IDF words between two articles."""
        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
            tfidf = vectorizer.fit_transform([text_a, text_b])
            feature_names = np.array(vectorizer.get_feature_names_out())

            if len(feature_names) == 0:
                return 0.0

            top_a_indices = np.argsort(tfidf[0].toarray()[0])[::-1][:top_k]
            top_b_indices = np.argsort(tfidf[1].toarray()[0])[::-1][:top_k]

            words_a = set(feature_names[top_a_indices])
            words_b = set(feature_names[top_b_indices])

            if not words_a or not words_b:
                return 0.0

            intersection = words_a.intersection(words_b)
            return len(intersection) / min(len(words_a), len(words_b))
        except Exception:
            return 0.0

    def choose_delete(self, i: int, j: int) -> int:
        """
        Determines which article to delete based on priority rules:
        1. Keep today's article over past days' article if only one is today.
        2. Higher priority category keeps the article (e.g. economy/tech > people).
        3. Longer content wins.
        4. Tie-break: keep first article.
        """
        a = self.records[i]
        b = self.records[j]

        # Rule 1: Date priority - always preserve today's article
        if a["is_today"] and not b["is_today"]:
            return j
        if b["is_today"] and not a["is_today"]:
            return i

        # Rule 2: Category priority ranking
        prio_a = CATEGORY_PRIORITY.get(a["folder"], 1)
        prio_b = CATEGORY_PRIORITY.get(b["folder"], 1)

        if prio_a > prio_b:
            return j  # delete b
        elif prio_b > prio_a:
            return i  # delete a

        # Rule 3: Content length
        len_a = len(a["content"])
        len_b = len(b["content"])

        if len_a < len_b:
            return i
        if len_b < len_a:
            return j

        # Rule 4: Tie break
        return j

    def find_duplicates(self) -> List[Dict[str, Any]]:
        if self.embeddings is None or len(self.records) < 2:
            return []

        similarity_matrix = cosine_similarity(self.embeddings)
        duplicate_pairs = []

        for i in range(len(self.records)):
            for j in range(i + 1, len(self.records)):
                score = float(similarity_matrix[i, j])

                is_same_day = (self.records[i]["file_date"] == self.records[j]["file_date"])
                threshold = self.similarity_threshold if is_same_day else self.cross_day_threshold

                is_duplicate = False

                if score >= threshold:
                    is_duplicate = True
                elif score >= (threshold - 0.08):
                    # Check TF-IDF keyword overlap for borderline cases
                    overlap = self._calculate_tfidf_overlap(
                        self.records[i]["combined_text"],
                        self.records[j]["combined_text"],
                    )
                    if overlap >= DEDUP_TFIDF_OVERLAP_THRESHOLD:
                        is_duplicate = True

                if is_duplicate:
                    delete_index = self.choose_delete(i, j)
                    duplicate_pairs.append({
                        "i": i,
                        "j": j,
                        "similarity": round(score, 4),
                        "delete": delete_index,
                    })

        duplicate_pairs.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicate_pairs

    def print_duplicates(self, pairs: List[Dict[str, Any]]):
        if not pairs:
            print("\nNo duplicates found.")
            return

        print("\n" + "=" * 90)
        print(f"DUPLICATE PAIRS FOUND: {len(pairs)}")
        print("=" * 90)

        for number, pair in enumerate(pairs, 1):
            a = self.records[pair["i"]]
            b = self.records[pair["j"]]
            deleted = self.records[pair["delete"]]
            kept = b if pair["delete"] == pair["i"] else a

            print(f"\nDuplicate #{number}")
            print(f"Similarity : {pair['similarity']:.4f}")
            print(f"DELETE     : {deleted['file_path']} | {deleted['folder']} | {deleted['title'][:40]}")
            print(f"KEEP       : {kept['file_path']} | {kept['folder']} | {kept['title'][:40]}")

    def resolve_deletions(self, pairs: List[Dict[str, Any]]) -> Set[int]:
        deleted: Set[int] = set()
        for pair in pairs:
            i = pair["i"]
            j = pair["j"]

            if i in deleted or j in deleted:
                continue

            delete_index = pair["delete"]
            deleted.add(delete_index)

        return deleted

    def delete_from_files(self, deleted_indices: Set[int]) -> int:
        if not deleted_indices:
            return 0

        by_file: Dict[Path, List[int]] = {}
        for index in deleted_indices:
            record = self.records[index]
            by_file.setdefault(record["file_path"], []).append(record["article_index"])

        total_deleted = 0
        for file_path, indices in by_file.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                delete_positions = set(indices)
                new_data = [art for idx, art in enumerate(data) if idx not in delete_positions]
                removed = len(data) - len(new_data)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=4)

                total_deleted += removed
                logger.info(f"Updated {file_path.name}: removed {removed}, remaining {len(new_data)}")
            except Exception as e:
                logger.error(f"Failed to update {file_path}: {e}")

        return total_deleted

    def run(self) -> Dict[str, Any]:
        logger.info(f"Running Article Duplicate Remover (within-day: {self.similarity_threshold}, cross-day: {self.cross_day_threshold})")
        self.load_articles()

        if len(self.records) < 2:
            logger.info("Not enough articles to compare.")
            return {"total_checked": len(self.records), "duplicates_removed": 0}

        self.create_embeddings()
        pairs = self.find_duplicates()
        self.print_duplicates(pairs)

        deleted_indices = self.resolve_deletions(pairs)
        total_deleted = self.delete_from_files(deleted_indices)

        report = {
            "total_checked": len(self.records),
            "duplicate_pairs_found": len(pairs),
            "duplicates_removed": total_deleted,
        }

        if self.metrics:
            self.metrics.log_dedup_results(report)

        return report


if __name__ == "__main__":
    remover = ArticleDuplicateRemover()
    remover.run()
