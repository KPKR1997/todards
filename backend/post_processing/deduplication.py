import json
import re
from pathlib import Path
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, timedelta


class ArticleDuplicateRemover:
    """
    Finds semantically duplicate articles across JSON files using
    cosine similarity.

    Folder structure:
        data/
            health_data/*.json
            tech_data/*.json
            people_data/*.json

    Duplicate rule:
      1. If one article is from people_data and the other is not,
         delete the people_data article.
      2. Otherwise, keep the article with longer content.
      3. If content lengths are equal, keep the first article.

    JSON files are modified in place.
    """

    def __init__(
        self,
        data_root="data",
        similarity_threshold=0.85,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.data_root = Path(data_root)
        self.similarity_threshold = similarity_threshold

        self.model = SentenceTransformer(model_name)

        self.records = []
        self.embeddings = None

    @staticmethod
    def clean_text(text):
        return re.sub(r"\s+", " ", str(text)).strip()

    def load_articles(self, days=5):

        self.records = []

        folders = [
            "health_data",
            "tech_data",
            "people_data",
        ]

        today = datetime.now().date()

        # Last 5 calendar days, including today
        valid_dates = {
            (today - timedelta(days=i)).strftime("%d%m%Y")
            for i in range(days)
        }

        print(
            f"\nChecking articles from the last {days} days:"
        )

        print(
            ", ".join(sorted(valid_dates))
        )

        for folder_name in folders:

            folder = self.data_root / folder_name

            if not folder.exists():

                print(
                    f"Skipping missing folder: {folder}"
                )

                continue

            for file_path in sorted(folder.glob("*.json")):

                # -------------------------------------------------
                # Extract date from filename
                #
                # Example:
                # 06102026_health_data.json
                #       ↓
                # 06102026
                # -------------------------------------------------

                filename = file_path.name

                file_date = filename[:8]

                if file_date not in valid_dates:

                    continue

                try:

                    with open(
                        file_path,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        data = json.load(f)

                except Exception as e:

                    print(
                        f"Could not read {file_path}: {e}"
                    )

                    continue

                if not isinstance(data, list):

                    print(
                        f"Skipping {file_path}: "
                        f"root is not a list"
                    )

                    continue

                print(
                    f"Loading: {file_path}"
                )

                for index, article in enumerate(data):

                    if not isinstance(article, dict):
                        continue

                    content = self.clean_text(
                        article.get(
                            "content",
                            ""
                        )
                    )

                    if not content:
                        continue

                    self.records.append({

                        "file_path": file_path,

                        "article_index": index,

                        "article": article,

                        "folder": folder_name,

                        "content": content,

                    })

        print(
            f"\nLoaded {len(self.records)} articles "
            f"from the last {days} days."
        )

    def create_embeddings(self):
        texts = [record["content"] for record in self.records]

        print("\nCreating embeddings...")

        self.embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        print("Embeddings created.")

    def choose_delete(self, i, j):
        a = self.records[i]
        b = self.records[j]

        # Always prefer non-people article.
        if a["folder"] == "people_data" and b["folder"] != "people_data":
            return i

        if b["folder"] == "people_data" and a["folder"] != "people_data":
            return j

        # Otherwise keep the article with more content.
        len_a = len(a["content"])
        len_b = len(b["content"])

        if len_a < len_b:
            return i

        if len_b < len_a:
            return j

        # Same length: keep first.
        return j

    def find_duplicates(self):
        similarity_matrix = cosine_similarity(self.embeddings)

        duplicate_pairs = []

        for i in range(len(self.records)):
            for j in range(i + 1, len(self.records)):
                score = float(similarity_matrix[i, j])

                if score >= self.similarity_threshold:
                    delete_index = self.choose_delete(i, j)

                    duplicate_pairs.append({
                        "i": i,
                        "j": j,
                        "similarity": score,
                        "delete": delete_index,
                    })

        duplicate_pairs.sort(
            key=lambda x: x["similarity"],
            reverse=True,
        )

        return duplicate_pairs

    def print_duplicates(self, pairs):
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
            print(f"DELETE     : {deleted['file_path']}")
            print(f"             ID = {deleted['article'].get('id')}")
            print(f"             Category = {deleted['folder']}")
            print(f"KEEP       : {kept['file_path']}")
            print(f"             ID = {kept['article'].get('id')}")
            print(f"             Category = {kept['folder']}")

    def resolve_deletions(self, pairs):
        """
        Process highest-similarity pairs first.

        Once an article is marked for deletion, it remains deleted.
        If a later pair points to an already-deleted article as the
        survivor, the pair is skipped.
        """
        deleted = set()

        for pair in pairs:
            i = pair["i"]
            j = pair["j"]

            if i in deleted or j in deleted:
                continue

            delete_index = pair["delete"]
            deleted.add(delete_index)

        return deleted

    def delete_from_files(self, deleted_indices):
        if not deleted_indices:
            print("\nNothing to delete.")
            return

        by_file = {}

        for index in deleted_indices:
            record = self.records[index]
            by_file.setdefault(record["file_path"], []).append(
                record["article_index"]
            )

        total_deleted = 0

        for file_path, indices in by_file.items():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                delete_positions = set(indices)

                new_data = [
                    article
                    for index, article in enumerate(data)
                    if index not in delete_positions
                ]

                removed = len(data) - len(new_data)

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        new_data,
                        f,
                        ensure_ascii=False,
                        indent=4,
                    )

                total_deleted += removed

                print(f"\nUpdated: {file_path}")
                print(f"Removed : {removed}")
                print(f"Remaining: {len(new_data)}")

            except Exception as e:
                print(f"Failed to update {file_path}: {e}")

        print(f"\nTOTAL DELETED: {total_deleted}")

    def run(self):
        print("=" * 90)
        print("ARTICLE DUPLICATE REMOVER")
        print("=" * 90)
        print(f"Data root: {self.data_root}")
        print(f"Similarity threshold: {self.similarity_threshold}")

        self.load_articles()

        if len(self.records) < 2:
            print("Not enough articles to compare.")
            return

        self.create_embeddings()

        pairs = self.find_duplicates()

        self.print_duplicates(pairs)

        if not pairs:
            print("\nNo duplicates found.")
            return

        deleted_indices = self.resolve_deletions(pairs)

        print(
            f"\nArticles selected for deletion: "
            f"{len(deleted_indices)}"
        )

        self.delete_from_files(deleted_indices)


if __name__ == "__main__":
    remover = ArticleDuplicateRemover(
        data_root="data",
        similarity_threshold=0.85,
    )

    remover.run()
