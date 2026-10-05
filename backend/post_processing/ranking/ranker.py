import json
import shutil
from datetime import datetime
from pathlib import Path

from backend.post_processing.ranking.article_analyzer import (
    ArticleAnalyzer,
)

from backend.post_processing.ranking.ranking_rules import (
    RankingRules,
)

from backend.post_processing.ranking.story_clusterer import (
    StoryClusterer,
)


class NewsRanker:
    """
    Main Todards news ranking system.

    Workflow:

        Load today's articles
            ↓
        Ollama analysis
            ↓
        Story clustering
            ↓
        Deterministic scoring
            ↓
        Select best article per story
            ↓
        Rank stories
            ↓
        Select top N
            ↓
        Backup original JSONs
            ↓
        Replace original JSONs with ranked articles
    """

    def __init__(
        self,
        data_root="data",
        backup_root="data/backup",
        top_n=3,
        similarity_threshold=0.78,
        ollama_url="http://localhost:11434",
        model="llama3:latest",
    ):

        self.data_root = Path(
            data_root
        )

        self.backup_root = Path(
            backup_root
        )

        self.top_n = top_n

        self.article_analyzer = (
            ArticleAnalyzer(
                url=ollama_url,
                model=model,
            )
        )

        self.ranking_rules = (
            RankingRules()
        )

        self.story_clusterer = (
            StoryClusterer(
                similarity_threshold=
                similarity_threshold
            )
        )

        self.today = datetime.now().strftime(
            "%d%m%Y"
        )

        self.records = []

    # =========================================================
    # LOAD ARTICLES
    # =========================================================

    def load_today_articles(self):

        self.records = []

        folders = [
            "health_data",
            "tech_data",
            "people_data",
        ]

        print(
            "\n========== LOADING TODAY'S ARTICLES =========="
        )

        for folder_name in folders:

            folder = (
                self.data_root
                / folder_name
            )

            if not folder.exists():

                print(
                    f"Skipping missing folder: "
                    f"{folder}"
                )

                continue

            files = list(
                folder.glob(
                    f"{self.today}_*.json"
                )
            )

            for file_path in files:

                print(
                    f"Loading: {file_path}"
                )

                try:

                    with open(
                        file_path,
                        "r",
                        encoding="utf-8",
                    ) as f:

                        data = json.load(f)

                except Exception as e:

                    print(
                        f"Failed to read "
                        f"{file_path}: {e}"
                    )

                    continue

                if not isinstance(
                    data,
                    list,
                ):

                    print(
                        f"Skipping {file_path}: "
                        f"root is not list"
                    )

                    continue

                for index, article in enumerate(
                    data
                ):

                    if not isinstance(
                        article,
                        dict,
                    ):
                        continue

                    content = str(
                        article.get(
                            "content",
                            "",
                        )
                    ).strip()

                    if not content:
                        continue

                    self.records.append(
                        {
                            "article": article,
                            "file_path": file_path,
                            "article_index": index,
                            "folder": folder_name,
                        }
                    )

        print(
            f"\nTotal articles loaded: "
            f"{len(self.records)}"
        )

    # =========================================================
    # ANALYZE ARTICLES
    # =========================================================

    def analyze_articles(self):

        print(
            "\n========== ANALYZING ARTICLES =========="
        )

        for index, record in enumerate(
            self.records,
            1,
        ):

            article = record["article"]

            print(
                f"\nAnalyzing "
                f"{index}/{len(self.records)}: "
                f"{article.get('title', '')[:100]}"
            )

            try:

                analysis = (
                    self.article_analyzer.analyze(
                        article
                    )
                )

            except Exception as e:

                print(
                    f"Analysis failed: {e}"
                )

                # Safe fallback.
                analysis = {
                    "everyday_impact": 0,
                    "dont_miss": 0,
                    "human_consequence": 0,
                    "economic_impact": 0,
                    "political_significance": 0,
                    "health_significance": 0,
                    "scientific_significance": 0,
                    "entertainment_significance": 0,
                    "remarkability": 0,
                    "global_reach": 0,
                    "urgency": 0,
                    "severity_tier": 1,
                    "events": {},
                    "reason": "Analysis failed.",
                }

            record["analysis"] = analysis

    # =========================================================
    # CLUSTER STORIES
    # =========================================================

    def cluster_stories(self):

        print(
            "\n========== CLUSTERING STORIES =========="
        )

        articles = [
            record["article"]
            for record in self.records
        ]

        clusters = (
            self.story_clusterer.cluster(
                articles
            )
        )

        print(
            f"Story clusters created: "
            f"{len(clusters)}"
        )

        return clusters

    # =========================================================
    # SCORE STORIES
    # =========================================================

    def score_clusters(
        self,
        clusters,
    ):

        print(
            "\n========== SCORING STORIES =========="
        )

        stories = []

        for cluster_number, cluster in enumerate(
            clusters,
            1,
        ):

            source_count = (
                self.story_clusterer.get_source_count(
                    [
                        record["article"]
                        for record in self.records
                    ],
                    cluster,
                )
            )

            candidates = []

            for index in cluster:

                record = self.records[index]

                score_data = (
                    self.ranking_rules.calculate_score(
                        record["analysis"],
                        record["article"],
                        source_count,
                    )
                )

                candidates.append(
                    {
                        "record_index": index,
                        "score_data": score_data,
                    }
                )

            # Best article represents this story.
            candidates.sort(
                key=lambda x:
                x["score_data"]["final_score"],
                reverse=True,
            )

            best = candidates[0]

            record = self.records[
                best["record_index"]
            ]

            article = record["article"]

            stories.append(
                {
                    "cluster_id": cluster_number,

                    "record_index":
                        best["record_index"],

                    "article": article,

                    "analysis":
                        record["analysis"],

                    "score":
                        best["score_data"],

                    "source_count":
                        source_count,

                    "cluster_size":
                        len(cluster),
                }
            )

        # Highest score first.
        stories.sort(
            key=lambda x:
            x["score"]["final_score"],
            reverse=True,
        )

        return stories

    # =========================================================
    # SELECT TOP STORIES
    # =========================================================

    def select_top_stories(
        self,
        stories,
    ):

        print(
            "\n========== SELECTING TOP STORIES =========="
        )

        selected = []

        for story in stories:

            if len(selected) >= self.top_n:
                break

            selected.append(
                story
            )

        for rank, story in enumerate(
            selected,
            1,
        ):

            story["rank"] = rank

        print(
            f"\nSelected {len(selected)} "
            f"top stories."
        )

        for story in selected:

            article = story["article"]

            print(
                f"\nRank {story['rank']}"
            )

            print(
                f"Score: "
                f"{story['score']['final_score']}"
            )

            print(
                f"Category: "
                f"{article.get('category')}"
            )

            print(
                f"Title: "
                f"{article.get('title')}"
            )

            print(
                f"Reason: "
                f"{story['analysis'].get('reason')}"
            )

        return selected

    # =========================================================
    # BACKUP ORIGINAL FILES
    # =========================================================

    def backup_original_files(self):

        backup_directory = (
            self.backup_root
            / self.today
        )

        backup_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            "\n========== BACKING UP RAW DATA =========="
        )

        folders = [
            "health_data",
            "tech_data",
            "people_data",
        ]

        backed_up = []

        for folder_name in folders:

            folder = (
                self.data_root
                / folder_name
            )

            if not folder.exists():
                continue

            files = list(
                folder.glob(
                    f"{self.today}_*.json"
                )
            )

            for file_path in files:

                destination = (
                    backup_directory
                    / file_path.name
                )

                shutil.copy2(
                    file_path,
                    destination,
                )

                backed_up.append(
                    file_path
                )

                print(
                    f"Backup: "
                    f"{file_path}"
                )

        print(
            f"\nBacked up files: "
            f"{len(backed_up)}"
        )

        return backed_up

    # =========================================================
    # UPDATE ORIGINAL JSON FILES
    # =========================================================

    def update_json_files(
        self,
        selected,
    ):

        print(
            "\n========== UPDATING JSON FILES =========="
        )

        # -----------------------------------------------------
        # Group selected articles by their original file.
        # -----------------------------------------------------

        selected_by_file = {}

        for story in selected:

            record = self.records[
                story["record_index"]
            ]

            file_path = record[
                "file_path"
            ]

            article = record[
                "article"
            ].copy()

            article["rank"] = story[
                "rank"
            ]

            article["ranking_score"] = (
                story["score"][
                    "final_score"
                ]
            )

            article["ranking_reason"] = (
                story["analysis"].get(
                    "reason",
                    "",
                )
            )

            article["ranking"] = {
                "rank":
                    story["rank"],

                "score":
                    story["score"][
                        "final_score"
                    ],

                "base_score":
                    story["score"][
                        "base_score"
                    ],

                "event_multiplier":
                    story["score"][
                        "event_multiplier"
                    ],

                "severity_multiplier":
                    story["score"][
                        "severity_multiplier"
                    ],

                "freshness_multiplier":
                    story["score"][
                        "freshness_multiplier"
                    ],

                "source_multiplier":
                    story["score"][
                        "source_multiplier"
                    ],

                "source_count":
                    story["source_count"],

                "cluster_size":
                    story["cluster_size"],

                "analysis":
                    story["analysis"],
            }

            selected_by_file.setdefault(
                file_path,
                [],
            ).append(
                article
            )

        # -----------------------------------------------------
        # Find today's files.
        # -----------------------------------------------------

        folders = [
            "health_data",
            "tech_data",
            "people_data",
        ]

        updated_count = 0

        for folder_name in folders:

            folder = (
                self.data_root
                / folder_name
            )

            if not folder.exists():
                continue

            files = list(
                folder.glob(
                    f"{self.today}_*.json"
                )
            )

            for file_path in files:

                new_data = selected_by_file.get(
                    file_path,
                    [],
                )

                # Keep ranking order.
                new_data.sort(
                    key=lambda article:
                    article.get(
                        "rank",
                        999,
                    )
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

                print(
                    f"Updated: "
                    f"{file_path}"
                )

                print(
                    f"Remaining articles: "
                    f"{len(new_data)}"
                )

                updated_count += 1

        print(
            f"\nUpdated files: "
            f"{updated_count}"
        )

    # =========================================================
    # SAVE RANKING REPORT
    # =========================================================

    def save_ranking_report(
        self,
        stories,
    ):

        ranking_directory = (
            self.backup_root
            / self.today
        )

        ranking_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_path = (
            ranking_directory
            / "ranking_report.json"
        )

        report = []

        for story in stories:

            article = story["article"]

            report.append(
                {
                    "rank":
                        story.get(
                            "rank"
                        ),

                    "id":
                        article.get(
                            "id"
                        ),

                    "category":
                        article.get(
                            "category"
                        ),

                    "title":
                        article.get(
                            "title"
                        ),

                    "score":
                        story[
                            "score"
                        ],

                    "analysis":
                        story[
                            "analysis"
                        ],

                    "source_count":
                        story[
                            "source_count"
                        ],

                    "cluster_size":
                        story[
                            "cluster_size"
                        ],
                }
            )

        with open(
            report_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                report,
                f,
                ensure_ascii=False,
                indent=4,
            )

        print(
            f"\nRanking report saved to: "
            f"{report_path}"
        )

    # =========================================================
    # MAIN RUN
    # =========================================================

    def run(self):

        print(
            "\n"
            + "=" * 80
        )

        print(
            "TODARDS NEWS RANKING SYSTEM"
        )

        print(
            "=" * 80
        )

        print(
            f"Date: {self.today}"
        )

        print(
            f"Top articles: {self.top_n}"
        )

        # -----------------------------------------------------
        # 1. Load today's articles
        # -----------------------------------------------------

        self.load_today_articles()

        if len(self.records) == 0:

            print(
                "\nNo articles found."
            )

            return []

        # -----------------------------------------------------
        # 2. Analyze with Ollama
        # -----------------------------------------------------

        self.analyze_articles()

        # -----------------------------------------------------
        # 3. Cluster similar stories
        # -----------------------------------------------------

        clusters = (
            self.cluster_stories()
        )

        # -----------------------------------------------------
        # 4. Score stories
        # -----------------------------------------------------

        stories = (
            self.score_clusters(
                clusters
            )
        )

        if not stories:

            print(
                "\nNo stories available."
            )

            return []

        # -----------------------------------------------------
        # 5. Select top 3
        # -----------------------------------------------------

        selected = (
            self.select_top_stories(
                stories
            )
        )

        # -----------------------------------------------------
        # 6. BACKUP BEFORE MODIFYING
        # -----------------------------------------------------

        self.backup_original_files()

        # -----------------------------------------------------
        # 7. Replace original JSONs
        # -----------------------------------------------------

        self.update_json_files(
            selected
        )

        # -----------------------------------------------------
        # 8. Save ranking report
        # -----------------------------------------------------

        self.save_ranking_report(
            selected
        )

        print(
            "\n"
            + "=" * 80
        )

        print(
            "RANKING COMPLETE"
        )

        print(
            "=" * 80
        )

        return selected