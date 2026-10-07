"""
Todards Pipeline — Metrics Collector

Tracks execution time, stage throughput, LLM statistics, duplicate detection,
guardrail blocks, and system resource consumption across each pipeline run.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("todards.metrics")


class PipelineMetrics:
    """
    Central collector for pipeline performance, data volume, and quality metrics.
    """

    def __init__(self):
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.date_str = datetime.now().strftime("%d%m%Y")

        # Stage timings
        self.stage_times: Dict[str, float] = {}
        self._active_stages: Dict[str, float] = {}

        # Article volumes
        self.scraped_counts: Dict[str, int] = {}
        self.guardrail_passed: int = 0
        self.guardrail_rejected: int = 0
        self.guardrail_rejections: List[Dict[str, Any]] = []

        # Deduplication
        self.dedup_report: Dict[str, Any] = {}

        # Category validation
        self.category_validation_report: Dict[str, Any] = {}

        # Ranking
        self.ranking_report: Dict[str, Any] = {}

        # LLM stats
        self.llm_calls: int = 0
        self.llm_retries: int = 0
        self.llm_failures: int = 0
        self.llm_total_time: float = 0.0

        # Final output
        self.final_articles_count: int = 0
        self.final_categories_count: int = 0

    def start_stage(self, stage_name: str):
        self._active_stages[stage_name] = time.time()
        logger.debug(f"Stage '{stage_name}' started.")

    def end_stage(self, stage_name: str) -> float:
        if stage_name in self._active_stages:
            elapsed = time.time() - self._active_stages.pop(stage_name)
            self.stage_times[stage_name] = self.stage_times.get(stage_name, 0.0) + elapsed
            logger.debug(f"Stage '{stage_name}' finished in {elapsed:.2f}s.")
            return elapsed
        return 0.0

    def log_scrape_count(self, category: str, count: int):
        self.scraped_counts[category] = count

    def log_guardrail_results(self, passed_count: int, rejections: List[Dict[str, Any]]):
        self.guardrail_passed += passed_count
        self.guardrail_rejected += len(rejections)
        self.guardrail_rejections.extend(rejections)

    def log_dedup_results(self, report: Dict[str, Any]):
        self.dedup_report = report

    def log_category_validation(self, report: Dict[str, Any]):
        self.category_validation_report = report

    def log_ranking_results(self, report: Dict[str, Any]):
        self.ranking_report = report

    def log_llm_call(
        self,
        model: str,
        prompt_length: int,
        response_length: int,
        elapsed: float,
        success: bool = True,
    ):
        self.llm_calls += 1
        self.llm_total_time += elapsed
        if not success:
            self.llm_failures += 1

    def finish(self, final_articles_count: int = 0, final_categories_count: int = 0):
        self.end_time = time.time()
        self.final_articles_count = final_articles_count
        self.final_categories_count = final_categories_count

    def to_dict(self) -> Dict[str, Any]:
        total_duration = (
            (self.end_time or time.time()) - self.start_time
        )

        return {
            "date": self.date_str,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(total_duration, 2),
            "stages_duration_seconds": {
                k: round(v, 2) for k, v in self.stage_times.items()
            },
            "volume": {
                "scraped_by_category": self.scraped_counts,
                "total_scraped": sum(self.scraped_counts.values()),
                "guardrail_passed": self.guardrail_passed,
                "guardrail_rejected": self.guardrail_rejected,
                "dedup_removed": self.dedup_report.get("duplicates_removed", 0),
                "category_reassignments": self.category_validation_report.get("reassigned_count", 0),
                "final_articles": self.final_articles_count,
                "final_categories": self.final_categories_count,
            },
            "guardrail_rejections": self.guardrail_rejections,
            "deduplication": self.dedup_report,
            "category_validation": self.category_validation_report,
            "llm_performance": {
                "total_calls": self.llm_calls,
                "total_failures": self.llm_failures,
                "total_time_seconds": round(self.llm_total_time, 2),
                "avg_response_time": (
                    round(self.llm_total_time / self.llm_calls, 2)
                    if self.llm_calls > 0
                    else 0.0
                ),
            },
        }
