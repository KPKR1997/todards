"""
Todards Pipeline — Automated Orchestrator

Master orchestrator for the Todards daily news pipeline:
1. Multi-source web scraping (Health, Tech, Politics, Environment, Economy)
2. Content guardrails & moderation (Toxicity, NSFW, Gossip filtering)
3. Semantic deduplication with dual thresholds & TF-IDF validation
4. Category cross-validation with automated reassignment
5. LLM importance ranking and event clustering
6. Story processing with RAG historical context, headlines, places, and images
7. Cross-article perceptual image deduplication
8. RAG historical archive indexing into local ChromaDB
9. Frontend dataset updates (todards.json) with issue numbering
10. Evaluation reporting (Markdown & JSON metrics)
"""

import os
import sys
import json
import copy
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from config.settings import (
    TODARDS_JSON_PATH,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    ALL_DATA_FOLDERS,
    CATEGORY_FOLDERS,
    DEDUP_SIMILARITY_THRESHOLD,
    DEDUP_CROSS_DAY_THRESHOLD,
    RANKING_TOP_N,
    RANKING_SIMILARITY_THRESHOLD,
    GUARDRAIL_ENABLED,
    CATEGORY_VALIDATION_ENABLED,
    RAG_ENABLED,
)
from backend.core.logger import setup_logger
from backend.core.progress import PipelineProgressTracker
from backend.core.ollama_client import OllamaClient
from backend.post_processing.content_guardrails import ContentGuardrails
from backend.post_processing.article_deduplication import ArticleDuplicateRemover
from backend.post_processing.category_validator import CategoryValidator
from backend.post_processing.ranking.ranker import NewsRanker
from backend.processing.process_pipeline import (
    MainProcessPipeline,
    ensure_unique_images,
    ensure_unique_sections,
)
from backend.processing.fetch_image import ImageFetcher
from backend.processing.image_match_scorer import SigLIPMatcher
from backend.rag.archive import HistoricalArticleArchive
from backend.rag.context_enricher import ContextEnricher
from evaluation.metrics import PipelineMetrics
from evaluation.reporter import PipelineReporter

# Scrapers (Untouched)
from webscrape.health_scrape import HealthDataScrapper
from webscrape.tech_scrapper import TechDataScrapper
from webscrape.politics import PoliticsDataScrapper
from webscrape.environment_scrapper import EnvironmentDataScrapper
from webscrape.economy_scrapper import EconomicsDataScrapper
from webscrape.entertainment_scrapper import EntertainmentDataScrapper

from notifications.send_report_email import send_daily_report

logger = setup_logger("todards")


def run_scrapers(
    metrics: PipelineMetrics,
    progress: PipelineProgressTracker,
    date_str: str,
) -> Dict[str, str]:
    """Execute all category scrapers with error isolation."""
    progress.update_stage("Web Scraping: Multi-source Ingestion", 10.0)
    data_paths = {}

    scrapers = [
        ("Health", "health_data", HealthDataScrapper, "scrape_health_data"),
        ("Tech", "tech_data", TechDataScrapper, "scrape_tech_data"),
        ("People", "people_data", PoliticsDataScrapper, "scrape_politics_data"),
        ("Environment", "environment_data", EnvironmentDataScrapper, "scrape_environment_data"),
        ("Economy", "economy_data", EconomicsDataScrapper, "scrape_economics_data"),
        ("Entertainment", "entertainment_data", EntertainmentDataScrapper, "scrape_entertainment_data"),
    ]

    for idx, (display_name, folder_name, scraper_cls, method_name) in enumerate(scrapers, 1):
        progress.update_status(f"Scraping {display_name} ({idx}/{len(scrapers)})")
        filename = f"{date_str}_{folder_name}.json"
        path_str = f"data/{folder_name}/{filename}"
        data_paths[folder_name] = path_str

        try:
            logger.info(f"Starting {display_name} scraper...")
            scraper_inst = scraper_cls()
            getattr(scraper_inst, method_name)()

            # Count scraped articles
            p = Path(path_str)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    cnt = len(json.load(f))
                metrics.log_scrape_count(display_name, cnt)
                logger.info(f"{display_name} scraper finished: {cnt} articles scraped.")
            else:
                metrics.log_scrape_count(display_name, 0)
        except Exception as e:
            logger.error(f"Scraper error in {display_name}: {e}. Continuing with remaining scrapers.")
            metrics.log_scrape_count(display_name, 0)

    return data_paths


def apply_guardrails(
    metrics: PipelineMetrics,
    progress: PipelineProgressTracker,
    data_paths: Dict[str, str],
    ollama_client: OllamaClient,
):
    """Filter scraped files using content moderation guardrails."""
    if not GUARDRAIL_ENABLED:
        logger.info("Content guardrails disabled.")
        return

    progress.update_stage("Content Moderation & Guardrails", 22.0)
    guardrails = ContentGuardrails(client=ollama_client, enabled=True)

    for folder_name, path_str in data_paths.items():
        p = Path(path_str)
        if not p.exists():
            continue

        progress.update_status(f"Guardrail screening: {folder_name}")
        try:
            with open(p, "r", encoding="utf-8") as f:
                articles = json.load(f)

            if not isinstance(articles, list) or not articles:
                continue

            passed, rejected = guardrails.filter_articles(articles)
            metrics.log_guardrail_results(len(passed), rejected)

            if rejected:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(passed, f, ensure_ascii=False, indent=4)
                logger.info(f"Guardrails pruned {len(rejected)} toxic/gossip items from {folder_name}.")
        except Exception as e:
            logger.error(f"Guardrail filtering failed for {path_str}: {e}")


def main():
    date_str = datetime.now().strftime("%d%m%Y")
    metrics = PipelineMetrics()
    reporter = PipelineReporter()

    # Determine current issue number
    issue_number = 1
    if TODARDS_JSON_PATH.exists():
        try:
            with open(TODARDS_JSON_PATH, "r", encoding="utf-8") as f:
                init_data = json.load(f)
            curr_str = init_data.get("publication", {}).get("issue", "Issue No. 0")
            issue_number = int(curr_str.replace("Issue No.", "").strip()) + 1
        except Exception:
            pass

    progress = PipelineProgressTracker(issue_number=issue_number, date_str=date_str)
    progress.start()

    # Central LLM Client
    ollama_client = OllamaClient(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        metrics_collector=metrics,
    )

    # ------------------------------------------------------------
    # 1. SCRAPE
    # ------------------------------------------------------------
    metrics.start_stage("scrape")
    data_paths = run_scrapers(metrics, progress, date_str)
    metrics.end_stage("scrape")

    # ------------------------------------------------------------
    # 2. CONTENT GUARDRAILS
    # ------------------------------------------------------------
    metrics.start_stage("guardrails")
    apply_guardrails(metrics, progress, data_paths, ollama_client)
    metrics.end_stage("guardrails")

    # ------------------------------------------------------------
    # 3. DEDUPLICATION
    # ------------------------------------------------------------
    progress.update_stage("Deduplication: Semantic & Cross-Day", 35.0)
    metrics.start_stage("deduplication")
    try:
        deduplicator = ArticleDuplicateRemover(
            data_root=Path("data"),
            similarity_threshold=DEDUP_SIMILARITY_THRESHOLD,
            cross_day_threshold=DEDUP_CROSS_DAY_THRESHOLD,
            metrics_collector=metrics,
        )
        dedup_report = deduplicator.run()
        logger.info(f"Deduplication complete: {dedup_report.get('duplicates_removed', 0)} duplicates removed.")
    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
    metrics.end_stage("deduplication")

    # ------------------------------------------------------------
    # 4. CATEGORY CROSS-VALIDATION
    # ------------------------------------------------------------
    progress.update_stage("Category Cross-Validation", 45.0)
    metrics.start_stage("category_validation")
    try:
        validator = CategoryValidator(
            client=ollama_client,
            enabled=CATEGORY_VALIDATION_ENABLED,
            metrics_collector=metrics,
        )
        val_summary = validator.validate_today_articles(date_str)
        logger.info(f"Category validation complete: {val_summary.get('reassigned_count', 0)} reassignments.")
    except Exception as e:
        logger.error(f"Category validation failed: {e}")
    metrics.end_stage("category_validation")

    # ------------------------------------------------------------
    # 5. RANKING
    # ------------------------------------------------------------
    progress.update_stage("Deterministic Scoring & Story Clustering", 58.0)
    metrics.start_stage("ranking")
    try:
        ranker = NewsRanker(
            data_root="data",
            backup_root="data/backup",
            top_n=RANKING_TOP_N,
            similarity_threshold=RANKING_SIMILARITY_THRESHOLD,
            ollama_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
        )
        ranked_articles = ranker.run()
        metrics.log_ranking_results({"ranked_count": len(ranked_articles)})
        logger.info(f"Ranking complete: {len(ranked_articles)} stories selected.")
    except Exception as e:
        logger.error(f"News ranker failed: {e}")
        ranked_articles = []
    metrics.end_stage("ranking")

    # ------------------------------------------------------------
    # 6. STORY PROCESSING (RAG + Summarize + Place + Headlines + Images)
    # ------------------------------------------------------------
    progress.update_stage("Article Processing & Media Generation", 70.0)
    metrics.start_stage("processing")

    # Initialize shared components once
    shared_image_fetcher = ImageFetcher(model=OLLAMA_MODEL)
    shared_image_scorer = SigLIPMatcher()
    rag_archive = HistoricalArticleArchive(enabled=RAG_ENABLED)
    rag_enricher = ContextEnricher(archive=rag_archive) if RAG_ENABLED else None

    processor = MainProcessPipeline(
        url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        image_fetcher=shared_image_fetcher,
        image_scorer=shared_image_scorer,
        rag_enricher=rag_enricher,
    )

    combined_output = []
    categories_to_process = [
        ("Health", "health_data"),
        ("Science & Technology", "tech_data"),
        ("People / Politics", "people_data"),
        ("Earth & Environment", "environment_data"),
        ("Economy & Business", "economy_data"),
        ("Entertainment", "entertainment_data")
    ]

    for display_cat, folder_name in categories_to_process:
        p_path = data_paths.get(folder_name)
        if p_path and Path(p_path).exists():
            progress.update_status(f"Processing category: {display_cat}")
            try:
                cat_output = processor.run_pipeline(
                    p_path,
                    progress_tracker=progress,
                    stage_name=display_cat,
                )
                combined_output.extend(cat_output)
                logger.info(f"Processed {len(cat_output)} articles for {display_cat}.")
            except Exception as e:
                logger.error(f"Processing failed for category {display_cat}: {e}")

    # ------------------------------------------------------------
    # 7. CROSS-ARTICLE IMAGE DEDUPLICATION PASS
    # ------------------------------------------------------------
    progress.update_stage("Final Media Verification & Image Dedup", 88.0)
    combined_output = ensure_unique_images(combined_output, shared_image_fetcher)

    # ------------------------------------------------------------
    # 8. RAG ARCHIVING
    # ------------------------------------------------------------
    if RAG_ENABLED and rag_archive:
        try:
            rag_archive.archive_published_articles(combined_output)
            logger.info("Archived published issue to RAG vector database.")
        except Exception as e:
            logger.warning(f"RAG archiving failed: {e}")

    metrics.end_stage("processing")

    # ------------------------------------------------------------
    # 9. ASSEMBLE TODARDS.JSON
    # ------------------------------------------------------------
    progress.update_stage("Assembling Publication Dataset", 95.0)
    metrics.start_stage("assembly")

    if not TODARDS_JSON_PATH.exists():
        logger.error(f"Todards JSON not found at {TODARDS_JSON_PATH}")
        return

    with open(TODARDS_JSON_PATH, "r", encoding="utf-8") as f:
        frontend_data = json.load(f)

    copy_data = copy.deepcopy(frontend_data)

    # Update publication metadata
    pub = copy_data.setdefault("publication", {})
    pub["issue"] = f"Issue No. {issue_number}"
    pub["publishedAt"] = datetime.now().strftime("%d %B %Y")
    copy_data["publication"] = pub

    # Group output by category
    output_by_category = {}
    for card in combined_output:
        cat_key = card["category"].strip().lower()
        output_by_category.setdefault(cat_key, []).append(card)

    # Update cards in each section
    updated_sections_count = 0
    for section in copy_data.get("sections", []):
        section_id = section.get("id", "").strip().lower()
        if section_id not in output_by_category:
            continue

        new_cards = output_by_category[section_id]
        existing_cards = section.get("cards", [])

        for idx, new_card in enumerate(new_cards):
            if idx >= len(existing_cards):
                break
            existing_card = existing_cards[idx]
            existing_card["title"] = new_card["title"]
            existing_card["image"] = new_card["image"]
            existing_card["place"] = new_card["place"]
            existing_card["time"] = new_card["time"]
            existing_card["content"] = new_card["content"]

        updated_sections_count += 1

    # Publication-wide uniqueness pass: Guarantee zero duplicate images across all sections/cards
    copy_data["sections"] = ensure_unique_sections(
        copy_data.get("sections", []),
        shared_image_fetcher,
    )

    with open(TODARDS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(copy_data, f, ensure_ascii=False, indent=2)

    dist_todards_json = Path("frontend/dist/data/todards.json")
    if dist_todards_json.parent.exists():
        with open(dist_todards_json, "w", encoding="utf-8") as f:
            json.dump(copy_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Saved {len(combined_output)} articles across {updated_sections_count} sections to {TODARDS_JSON_PATH}")
    metrics.end_stage("assembly")

    # ------------------------------------------------------------
    # 10. EVALUATION & METRICS REPORTING
    # ------------------------------------------------------------
    metrics.finish(
        final_articles_count=len(combined_output),
        final_categories_count=updated_sections_count,
    )
    report_paths = reporter.generate_report(metrics)

    progress.finish(
        f"Issue #{issue_number} published successfully! ({len(combined_output)} articles in {metrics.to_dict()['duration_seconds']}s)"
    )
    print(f"\nEvaluation Report: {report_paths['markdown']}")

    email_result = send_daily_report()
    logger.info(email_result)


if __name__ == "__main__":
    main()