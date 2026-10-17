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

        # Ollama token usage and server timings
        self.llm_prompt_tokens = 0
        self.llm_response_tokens = 0
        self.llm_total_tokens = 0
        self.llm_usage_responses = 0

        self.llm_prompt_eval_seconds = 0.0
        self.llm_generation_seconds = 0.0
        self.llm_load_seconds = 0.0
        self.llm_server_total_seconds = 0.0

        # ArticleSafetyGuard results
        self.article_safety_report: Dict[str, Any] = {}

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

    def log_article_safety_results(self, report: Dict[str, Any]):
        """Record ArticleSafetyGuard counts without changing article schemas."""
        self.article_safety_report = {
            key: value
            for key, value in report.items()
            if isinstance(value, (str, int, float, bool))
        }

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
        prompt_tokens: Optional[int] = None,
        response_tokens: Optional[int] = None,
        prompt_eval_seconds: Optional[float] = None,
        generation_seconds: Optional[float] = None,
        load_seconds: Optional[float] = None,
        server_total_seconds: Optional[float] = None,
    ):
        """Record existing call metrics and optional Ollama usage metadata."""
        self.llm_calls += 1
        self.llm_total_time += elapsed

        if not success:
            self.llm_failures += 1

        # Older callers can omit all usage arguments.
        if prompt_tokens is not None or response_tokens is not None:
            self.llm_usage_responses += 1

        if prompt_tokens is not None:
            self.llm_prompt_tokens += prompt_tokens

        if response_tokens is not None:
            self.llm_response_tokens += response_tokens

        if prompt_tokens is not None or response_tokens is not None:
            self.llm_total_tokens += (
                (prompt_tokens or 0) + (response_tokens or 0)
            )

        if prompt_eval_seconds is not None:
            self.llm_prompt_eval_seconds += prompt_eval_seconds

        if generation_seconds is not None:
            self.llm_generation_seconds += generation_seconds

        if load_seconds is not None:
            self.llm_load_seconds += load_seconds

        if server_total_seconds is not None:
            self.llm_server_total_seconds += server_total_seconds

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
            "article_safety": self.article_safety_report,
            "deduplication": self.dedup_report,
            "category_validation": self.category_validation_report,
            "llm_performance": {
                "total_calls": self.llm_calls,
                "total_failures": self.llm_failures,
                "total_time_seconds": round(self.llm_total_time, 2),
                "prompt_tokens": self.llm_prompt_tokens,
                "response_tokens": self.llm_response_tokens,
                "total_tokens": self.llm_total_tokens,
                "usage_responses": self.llm_usage_responses,
                "prompt_eval_seconds": round(self.llm_prompt_eval_seconds, 3),
                "generation_seconds": round(self.llm_generation_seconds, 3),
                "load_seconds": round(self.llm_load_seconds, 3),
                "server_total_seconds": round(self.llm_server_total_seconds, 3),
                "avg_response_time": (
                    round(self.llm_total_time / self.llm_calls, 2)
                    if self.llm_calls > 0
                    else 0.0
                ),
            },
        }
