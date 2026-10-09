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

from config.settings import ALL_DATA_FOLDERS


class NewsRanker:
    """
    Main Todards news ranking system.

    Workflow:

        Load today's articles
            ↓
        Ollama editorial analysis
            ↓
        Editorial publishability gate
            ↓
        Story clustering
            ↓
        Deterministic scoring
            ↓
        Select best article per story
            ↓
        Rank stories
            ↓
        Select top N from EACH category
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
                similarity_threshold=(
                    similarity_threshold
                )
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

        folders = ALL_DATA_FOLDERS

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

        if not self.records:
            return

        total_articles = len(
            self.records
        )

        for index, record in enumerate(
            self.records,
            1,
        ):

            article = record["article"]

            print(
                f"\nAnalyzing "
                f"{index}/{total_articles}: "
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

                # Fail closed.
                #
                # If editorial analysis fails,
                # the article must NOT be eligible
                # for ranking.

                analysis = {
                    "editorial_relevance": 0,
                    "publishable": False,
                    "rejection_reason": (
                        "Article analysis failed "
                        "and therefore the article "
                        "is not eligible for ranking."
                    ),
                    "everyday_impact": 0,
                    "public_impact": 0,
                    "public_need_to_know": 0,
                    "public_concern": 0,
                    "human_consequence": 0,
                    "economic_impact": 0,
                    "political_significance": 0,
                    "health_significance": 0,
                    "scientific_significance": 0,
                    "technology_significance": 0,
                    "global_reach": 0,
                    "urgency": 0,
                    "remarkability": 0,
                    "severity_tier": 1,
                    "events": {
                        "major_disaster": False,
                        "mass_casualties": False,
                        "pandemic": False,
                        "election": False,
                        "major_political_change": False,
                        "major_economic_event": False,
                        "major_award": False,
                        "celebrity_death": False,
                        "record_breaking": False,
                        "unprecedented_event": False,
                        "major_scientific_discovery": False,
                        "major_technology_event": False,
                    },
                    "reason": (
                        "Analysis failed, so the "
                        "article was not considered "
                        "eligible for publication."
                    ),
                }

            record["analysis"] = analysis

        # =====================================================
        # EDITORIAL PUBLISHABILITY GATE
        # =====================================================

        original_count = len(
            self.records
        )

        rejected_records = []

        publishable_records = []

        for record in self.records:

            analysis = record.get(
                "analysis",
                {},
            )

            publishable = analysis.get(
                "publishable",
                False,
            )

            if publishable:
                publishable_records.append(
                    record
                )
            else:
                rejected_records.append(
                    record
                )

        self.records = publishable_records

        rejected_count = len(
            rejected_records
        )

        print(
            "\n========== EDITORIAL GATE =========="
        )

        print(
            f"Articles analyzed: "
            f"{original_count}"
        )

        print(
            f"Articles accepted: "
            f"{len(self.records)}"
        )

        print(
            f"Articles rejected: "
            f"{rejected_count}"
        )

        if rejected_records:

            print(
                "\nRejected articles:"
            )

            for record in rejected_records:

                article = record[
                    "article"
                ]

                analysis = record.get(
                    "analysis",
                    {},
                )

                title = str(
                    article.get(
                        "title",
                        "",
                    )
                ).strip()

                reason = str(
                    analysis.get(
                        "rejection_reason",
                        "No sufficient public significance.",
                    )
                ).strip()

                print(
                    f"\nREJECTED: {title}"
                )

                print(
                    f"Reason: {reason}"
                )

        print(
            "\nEditorial gate complete."
        )

    # =========================================================
    # CLUSTER STORIES
    # =========================================================

    def cluster_stories(self):

        print(
            "\n========== CLUSTERING STORIES =========="
        )

        if not self.records:
            print(
                "No publishable articles "
                "available for clustering."
            )
            return []

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

            if not cluster:
                continue

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

                if index >= len(
                    self.records
                ):
                    continue

                record = self.records[
                    index
                ]

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

            if not candidates:
                continue

            # Best article represents
            # this story.

            candidates.sort(
                key=lambda x:
                x["score_data"][
                    "final_score"
                ],
                reverse=True,
            )

            best = candidates[0]

            record = self.records[
                best["record_index"]
            ]

            article = record[
                "article"
            ]

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
    # SELECT TOP STORIES FROM EACH CATEGORY
    # =========================================================

    def select_top_stories(
        self,
        stories,
    ):

        print(
            "\n========== SELECTING TOP STORIES BY CATEGORY =========="
        )

        # -----------------------------------------------------
        # Group stories by category
        # -----------------------------------------------------

        stories_by_category = {}

        for story in stories:

            article = story[
                "article"
            ]

            category = str(
                article.get(
                    "category",
                    "Unknown",
                )
            ).strip()

            if not category:
                category = "Unknown"

            stories_by_category.setdefault(
                category,
                [],
            ).append(
                story
            )

        # -----------------------------------------------------
        # Select top N from EACH category
        # -----------------------------------------------------

        selected = []

        for category, category_stories in (
            stories_by_category.items()
        ):

            # Stories are already globally
            # sorted by score, but sort again
            # so each category is explicitly
            # ranked independently.

            category_stories.sort(
                key=lambda x:
                x["score"]["final_score"],
                reverse=True,
            )

            category_selected = (
                category_stories[
                    :self.top_n
                ]
            )

            # Rank starts from 1 for
            # every category.

            for rank, story in enumerate(
                category_selected,
                1,
            ):

                story["rank"] = rank

            selected.extend(
                category_selected
            )

            print(
                f"\nCategory: {category}"
            )

            print(
                f"Available stories: "
                f"{len(category_stories)}"
            )

            print(
                f"Selected: "
                f"{len(category_selected)}"
            )

            for story in category_selected:

                article = story[
                    "article"
                ]

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

        print(
            f"\nTotal selected stories across "
            f"all categories: {len(selected)}"
        )

        print(
            f"Target: up to "
            f"{self.top_n} stories per category"
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

        folders = ALL_DATA_FOLDERS

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

        folders = ALL_DATA_FOLDERS

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

                new_data = (
                    selected_by_file.get(
                        file_path,
                        [],
                    )
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

            article = story[
                "article"
            ]

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
                        story["score"],

                    "analysis":
                        story["analysis"],

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
            f"Top articles per category: "
            f"{self.top_n}"
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
        # 3. Stop if editorial gate rejected
        #    everything.
        # -----------------------------------------------------

        if len(self.records) == 0:

            print(
                "\nNo publishable articles "
                "available after editorial gate."
            )

            return []

        # -----------------------------------------------------
        # 4. Cluster similar stories
        # -----------------------------------------------------

        clusters = (
            self.cluster_stories()
        )

        if not clusters:

            print(
                "\nNo story clusters available."
            )

            return []

        # -----------------------------------------------------
        # 5. Score stories
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
        # 6. Select top 3 from EACH category
        # -----------------------------------------------------

        selected = (
            self.select_top_stories(
                stories
            )
        )

        if not selected:

            print(
                "\nNo stories selected."
            )

            return []

        # -----------------------------------------------------
        # 7. BACKUP BEFORE MODIFYING
        # -----------------------------------------------------

        self.backup_original_files()

        # -----------------------------------------------------
        # 8. Replace original JSONs
        # -----------------------------------------------------

        self.update_json_files(
            selected
        )

        # -----------------------------------------------------
        # 9. Save ranking report
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