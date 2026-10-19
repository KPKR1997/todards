
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from backend.post_processing.ranking.article_analyzer import ArticleAnalyzer
from backend.post_processing.ranking.editorial_selector import EditorialSelector
from backend.post_processing.ranking.ranking_rules import RankingRules
from backend.post_processing.ranking.story_clusterer import StoryClusterer
from config.settings import ALL_DATA_FOLDERS
class NewsRanker:
    def __init__(
        self,
        data_root="data",
        backup_root="data/backup",
        top_n=3,
        similarity_threshold=0.78,
        ollama_url="http://localhost:11434",
        model="llama3:latest",
    ):
        self.data_root = Path(data_root)
        self.backup_root = Path(backup_root)
        self.top_n = max(0, int(top_n))
        self.article_analyzer = ArticleAnalyzer(
            url=ollama_url,
            model=model,
        )
        self.editorial_selector = EditorialSelector(
            client=self.article_analyzer.client,
        )
        self.ranking_rules = RankingRules()
        self.story_clusterer = StoryClusterer(
            similarity_threshold=similarity_threshold,
        )
        self.today = datetime.now().strftime("%d%m%Y")
        self.records: List[Dict[str, Any]] = []
     
    # LOAD TODAY'S ARTICLES
     
    def load_today_articles(self):
        self.records = []
        print("\nLOADING TODAY'S ARTICLES")
        for folder_name in ALL_DATA_FOLDERS:
            folder = self.data_root / folder_name
            if not folder.exists():
                print(f"Skipping missing folder: {folder}")
                continue
            for file_path in sorted(folder.glob(f"{self.today}_*.json")):
                print(f"Loading: {file_path}")
                try:
                    with file_path.open("r", encoding="utf-8") as file:
                        data = json.load(file)
                except Exception as exc:
                    print(f"Failed to read {file_path}: {exc}")
                    continue
                if not isinstance(data, list):
                    print(f"Skipping {file_path}: JSON root is not a list")
                    continue
                for article_index, article in enumerate(data):
                    if not isinstance(article, dict):
                        continue
                    if not str(article.get("content", "") or "").strip():
                        continue
                    self.records.append({
                        "article": article,
                        "file_path": file_path,
                        "article_index": article_index,
                        "folder": folder_name,
                    })
        print(f"\nTotal articles loaded: {len(self.records)}")
     
    # ANALYZE AND APPLY THE EXISTING PUBLISHABILITY GATE
     
    @staticmethod
    def _failed_analysis() -> dict:
        return {
            "editorial_relevance": 0,
            "publishable": False,
            "rejection_reason": (
                "Article analysis failed and therefore the article "
                "is not eligible for ranking."
            ),
            "everyday_impact": 0,
            "dont_miss": 0,
            "human_consequence": 0,
            "economic_impact": 0,
            "political_significance": 0,
            "health_significance": 0,
            "scientific_significance": 0,
            "entertainment_significance": 0,
            "technology_significance": 0,
            "remarkability": 0,
            "global_reach": 0,
            "urgency": 0,
            "public_impact": 0,
            "public_need_to_know": 0,
            "public_concern": 0,
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
                "Analysis failed, so the article was not considered "
                "eligible for publication."
            ),
        }
    def analyze_articles(self):
        print("\n ANALYZING ARTICLES")
        if not self.records:
            print("No articles available for analysis.")
            return
        total_articles = len(self.records)
        for index, record in enumerate(self.records, 1):
            article = record["article"]
            title = str(article.get("title", "") or "")
            print(f"\nAnalyzing {index}/{total_articles}: {title[:100]}")
            try:
                analysis = self.article_analyzer.analyze(article)
                if not isinstance(analysis, dict):
                    raise TypeError("ArticleAnalyzer returned a non-dictionary result")
            except Exception as exc:
                print(f"Analysis failed: {exc}")
                analysis = self._failed_analysis()
            record["analysis"] = analysis
        original_count = len(self.records)
        rejected_records = []
        publishable_records = []
        for record in self.records:
            analysis = record.get("analysis", {})
            if analysis.get("publishable", False) is True:
                publishable_records.append(record)
            else:
                rejected_records.append(record)
        self.records = publishable_records
        print("\n========== EDITORIAL PUBLISHABILITY GATE ==========")
        print(f"Articles analyzed: {original_count}")
        print(f"Articles accepted: {len(self.records)}")
        print(f"Articles rejected: {len(rejected_records)}")
        for record in rejected_records:
            article = record.get("article", {})
            analysis = record.get("analysis", {})
            title = str(article.get("title", "") or "").strip()
            reason = str(
                analysis.get("rejection_reason")
                or "No sufficient public significance."
            ).strip()
            print(f"\nREJECTED: {title}\nReason: {reason}")
        print("\nEditorial gate complete.")
     
    # CLUSTER SIMILAR STORIES
     
    def cluster_stories(self):
        print("\n========== CLUSTERING STORIES ==========")
        if not self.records:
            print("No publishable articles available for clustering.")
            return []
        articles = [record["article"] for record in self.records]
        clusters = self.story_clusterer.cluster(articles)
        print(f"Story clusters created: {len(clusters)}")
        return clusters
     
    # CHOOSE THE BEST ARTICLE REPRESENTING EACH CLUSTER
     
    @staticmethod
    def _safe_diagnostic_score(candidate) -> float:
        try:
            return float(candidate.get("score_data", {}).get("final_score", 0.0))
        except (TypeError, ValueError, AttributeError):
            return 0.0
    def score_clusters(self, clusters):
        print("\n========== PREPARING STORY CANDIDATES ==========")
        stories = []
        articles = [record["article"] for record in self.records]
        for cluster_number, cluster in enumerate(clusters, 1):
            valid_indices = [
                index for index in cluster
                if isinstance(index, int) and 0 <= index < len(self.records)
            ]
            if not valid_indices:
                continue
            source_count = self.story_clusterer.get_source_count(
                articles,
                valid_indices,
            )
            candidates = []
            for record_index in valid_indices:
                record = self.records[record_index]
                try:
                    score_data = self.ranking_rules.calculate_score(
                        record["analysis"],
                        record["article"],
                        source_count,
                    )
                except Exception as exc:
                    # Keep a diagnostic score shape so the story can still be
                    # compared by the editorial model; zero is only fallback metadata.
                    print(
                        "Diagnostic scoring failed for "
                        f"{record['article'].get('title', '')}: {exc}"
                    )
                    score_data = {
                        "final_score": 0.0,
                        "base_score": 0.0,
                        "event_multiplier": 1.0,
                        "severity_multiplier": 1.0,
                        "freshness_multiplier": 1.0,
                        "source_multiplier": 1.0,
                    }
                candidates.append({
                    "record_index": record_index,
                    "score_data": score_data,
                })
            def article_and_analysis(candidate):
                record = self.records[candidate["record_index"]]
                return record["article"], record["analysis"]
            best = self.editorial_selector.best_of(
                candidates,
                article_and_analysis=article_and_analysis,
                score=self._safe_diagnostic_score,
            )
            if best is None:
                continue
            record = self.records[best["record_index"]]
            stories.append({
                "cluster_id": cluster_number,
                "record_index": best["record_index"],
                "article": record["article"],
                "analysis": record["analysis"],
                "score": best["score_data"],
                "source_count": source_count,
                "cluster_size": len(valid_indices),
                "representative_selection_method": "llm_pairwise_comparison",
            })
            print(
                "Representative chosen: "
                f"{record['article'].get('title', '')} "
                f"(cluster {cluster_number}, {len(valid_indices)} candidate(s))"
            )
        # Intentionally do not sort by the diagnostic weighted score. The
        # category-wise LLM top-k selector determines the editorial ordering.
        print(f"Story representatives prepared: {len(stories)}")
        return stories
     
    # SELECT TOP N PER CATEGORY, THEN APPLY FINAL QUALITY GATE
     
    @staticmethod
    def _story_article_and_analysis(story):
        return story["article"], story["analysis"]
    @staticmethod
    def _story_diagnostic_score(story) -> float:
        try:
            return float(story.get("score", {}).get("final_score", 0.0))
        except (TypeError, ValueError, AttributeError):
            return 0.0
    def select_top_stories(self, stories):
        print("\n========== LLM EDITORIAL TOP STORIES BY CATEGORY ==========")
        stories_by_category = {}
        for story in stories:
            category = str(
                story.get("article", {}).get("category", "Unknown") or "Unknown"
            ).strip() or "Unknown"
            stories_by_category.setdefault(category, []).append(story)
        selected = []
        for category, category_stories in stories_by_category.items():
            remaining = list(category_stories)
            category_selected = []
            print(f"\nCategory: {category}")
            print(f"Eligible stories: {len(remaining)}")
            # Re-select the best from the remaining candidates whenever a
            # finalist fails the separate quality gate. This prevents a failed
            # candidate from occupying a card or being selected repeatedly.
            while remaining and len(category_selected) < self.top_n:
                best = self.editorial_selector.best_of(
                    remaining,
                    article_and_analysis=self._story_article_and_analysis,
                    score=self._story_diagnostic_score,
                )
                if best is None:
                    break
                passed, quality_reason = self.editorial_selector.final_quality_check(
                    best["article"],
                    best["analysis"],
                )
                best["final_quality"] = {
                    "passed": passed,
                    "reason": quality_reason,
                }
                # Remove by object identity so equivalent dictionaries cannot
                # accidentally remove a different candidate.
                remaining = [candidate for candidate in remaining if candidate is not best]
                if not passed:
                    print(f"\nFINAL QUALITY REJECTED: {best['article'].get('title', '')}")
                    print(f"Reason: {quality_reason}")
                    continue
                best["selection_method"] = "llm_pairwise_top_k"
                best["rank"] = len(category_selected) + 1
                category_selected.append(best)
                print(f"\nRank {best['rank']}: {best['article'].get('title', '')}")
                print(
                    "Diagnostic score (not the primary ordering method): "
                    f"{self._story_diagnostic_score(best)}"
                )
                print(f"Final quality: PASS — {quality_reason}")
            selected.extend(category_selected)
            print(f"Selected for {category}: {len(category_selected)} / {self.top_n}")
        print(f"\nTotal selected across categories: {len(selected)}")
        print(f"Target: up to {self.top_n} stories per category")
        return selected
     
    # BACK UP ORIGINAL JSON FILES BEFORE MODIFYING THEM
     
    def backup_original_files(self):
        backup_directory = self.backup_root / self.today
        backup_directory.mkdir(parents=True, exist_ok=True)
        print("\n========== BACKING UP RAW DATA ==========")
        backed_up = []
        for folder_name in ALL_DATA_FOLDERS:
            folder = self.data_root / folder_name
            if not folder.exists():
                continue
            for file_path in sorted(folder.glob(f"{self.today}_*.json")):
                destination = backup_directory / file_path.name
                try:
                    shutil.copy2(file_path, destination)
                    backed_up.append(file_path)
                    print(f"Backup: {file_path} -> {destination}")
                except Exception as exc:
                    # A backup failure must stop publication; continuing could
                    # overwrite source JSONs without a recoverable copy.
                    raise RuntimeError(
                        f"Could not back up {file_path}; refusing to update JSON files."
                    ) from exc
        print(f"\nBacked up files: {len(backed_up)}")
        return backed_up
     
    # UPDATE ORIGINAL JSON FILES USING THE EXISTING ARTICLE SCHEMA
     
    def update_json_files(self, selected):
        print("\n========== UPDATING JSON FILES ==========")
        selected_by_file = {}
        for story in selected:
            record = self.records[story["record_index"]]
            file_path = record["file_path"]
            article = record["article"].copy()
            article["rank"] = story["rank"]
            article["ranking_score"] = story["score"].get("final_score", 0.0)
            article["ranking_reason"] = story["analysis"].get("reason", "")
            article["ranking"] = {
                "rank": story["rank"],
                "score": story["score"].get("final_score", 0.0),
                "base_score": story["score"].get("base_score", 0.0),
                "event_multiplier": story["score"].get("event_multiplier", 1.0),
                "severity_multiplier": story["score"].get("severity_multiplier", 1.0),
                "freshness_multiplier": story["score"].get("freshness_multiplier", 1.0),
                "source_multiplier": story["score"].get("source_multiplier", 1.0),
                "source_count": story["source_count"],
                "cluster_size": story["cluster_size"],
                "analysis": story["analysis"],
                "selection_method": story.get("selection_method", "llm_pairwise_top_k"),
                "representative_selection_method": story.get(
                    "representative_selection_method", "llm_pairwise_comparison"
                ),
                "final_quality": story.get("final_quality", {}),
            }
            selected_by_file.setdefault(file_path, []).append(article)
        updated_count = 0
        for folder_name in ALL_DATA_FOLDERS:
            folder = self.data_root / folder_name
            if not folder.exists():
                continue
            for file_path in sorted(folder.glob(f"{self.today}_*.json")):
                new_data = selected_by_file.get(file_path, [])
                new_data.sort(key=lambda article: article.get("rank", 999))
                with file_path.open("w", encoding="utf-8") as file:
                    json.dump(new_data, file, ensure_ascii=False, indent=4)
                print(f"Updated: {file_path}")
                print(f"Remaining articles: {len(new_data)}")
                updated_count += 1
        print(f"\nUpdated files: {updated_count}")
     
    # SAVE THE RANKING REPORT
     
    def save_ranking_report(self, stories):
        ranking_directory = self.backup_root / self.today
        ranking_directory.mkdir(parents=True, exist_ok=True)
        report_path = ranking_directory / "ranking_report.json"
        report = []
        for story in stories:
            article = story["article"]
            report.append({
                "rank": story.get("rank"),
                "id": article.get("id"),
                "category": article.get("category"),
                "title": article.get("title"),
                "score": story.get("score", {}),
                "analysis": story.get("analysis", {}),
                "source_count": story.get("source_count", 1),
                "cluster_size": story.get("cluster_size", 1),
                "representative_selection_method": story.get(
                    "representative_selection_method"
                ),
                "selection_method": story.get("selection_method"),
                "final_quality": story.get("final_quality", {}),
            })
        with report_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False, indent=4)
        print(f"\nRanking report saved to: {report_path}")
     
    # MAIN RUN — INTERFACE PRESERVED FOR main.py
     
    def run(self):
        print("\n" + "=" * 80)
        print("TODARDS NEWS RANKING SYSTEM")
        print("=" * 80)
        print(f"Date: {self.today}")
        print(f"Target: up to {self.top_n} articles per category")
        # 1. Load today's articles.
        self.load_today_articles()
        if not self.records:
            print("\nNo articles found.")
            return []
        # 2. Analyze and apply the existing publishability gate.
        self.analyze_articles()
        if not self.records:
            print("\nNo publishable articles available after editorial gate.")
            return []
        # 3. Cluster similar stories.
        clusters = self.cluster_stories()
        if not clusters:
            print("\nNo story clusters available.")
            return []
        # 4. Prepare one editorially selected representative per story cluster.
        stories = self.score_clusters(clusters)
        if not stories:
            print("\nNo stories available.")
            return []
        # 5. Choose up to top_n stories per category, with a final quality gate.
        selected = self.select_top_stories(stories)
        if not selected:
            print("\nNo stories passed final selection; original JSON files were not changed.")
            return []
        # 6. Back up originals before any JSON modification.
        self.backup_original_files()
        # 7. Update today's JSON files with selected articles only.
        self.update_json_files(selected)
        # 8. Save an audit report.
        self.save_ranking_report(selected)
        print("\n" + "=" * 80)
        print("RANKING COMPLETE")
        print("=" * 80)
        return selected
