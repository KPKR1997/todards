"""Central, display-ready definitions for all derived observability metrics.

The source CSV remains authoritative.  Definitions in this module describe only
derived dashboard values and deliberately do not mutate or repair source data.
"""

from __future__ import annotations

from typing import Final


METRIC_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "total_pipeline_runs": {
        "label": "Total pipeline runs",
        "formula": "Count of telemetry CSV rows in the selected period.",
        "unit": "runs",
        "denominator": "None",
        "missing_data": "Rows with an invalid timestamp are retained in source-quality counts but excluded when a date filter is applied.",
    },
    "latest_run_duration": {
        "label": "Latest run duration",
        "formula": "duration_seconds from the latest valid timestamped row.",
        "unit": "seconds",
        "denominator": "None",
        "missing_data": "Unavailable when no valid timestamped row has duration_seconds.",
    },
    "publication_yield": {
        "label": "Publication yield",
        "formula": "sum(volume_final_articles) / sum(volume_total_scraped) × 100",
        "unit": "percent",
        "denominator": "Sum of valid scraped-article counts",
        "missing_data": "Unavailable when the denominator is zero or unavailable. It is not an average of per-run percentages.",
    },
    "articles_per_minute": {
        "label": "Articles published per minute",
        "formula": "sum(volume_final_articles) / (sum(duration_seconds) / 60)",
        "unit": "articles/minute",
        "denominator": "Sum of valid overall durations",
        "missing_data": "Unavailable when total duration is zero or unavailable.",
    },
    "stage_share_of_pipeline": {
        "label": "Stage share of pipeline time",
        "formula": "sum(stage duration) / sum(duration_seconds) × 100",
        "unit": "percent",
        "denominator": "Sum of valid overall run durations",
        "missing_data": "Unavailable when the denominator is zero or unavailable. Stage durations may overlap or omit overhead, so shares do not have to total 100%.",
    },
    "llm_failure_rate": {
        "label": "LLM failure rate",
        "formula": "sum(llm_performance_total_failures) / sum(llm_performance_total_calls) × 100",
        "unit": "percent",
        "denominator": "Sum of valid LLM call counts",
        "missing_data": "Unavailable when total calls are zero or unavailable.",
    },
    "weighted_llm_response_time": {
        "label": "Weighted LLM response time",
        "formula": "sum(llm_performance_total_time_seconds) / sum(llm_performance_total_calls)",
        "unit": "seconds/call",
        "denominator": "Sum of valid LLM call counts",
        "missing_data": "Unavailable when calls or total LLM time are unavailable. This is preferred over averaging per-run averages because the collector records total time and calls.",
    },
    "tokens_per_usage_response": {
        "label": "Tokens per usage response",
        "formula": "sum(llm_performance_total_tokens) / sum(llm_performance_usage_responses)",
        "unit": "tokens/response",
        "denominator": "Sum of valid usage-response counts",
        "missing_data": "Unavailable when the denominator is zero or unavailable.",
    },
    "tokens_per_final_article": {
        "label": "Tokens per final article",
        "formula": "sum(llm_performance_total_tokens) / sum(volume_final_articles)",
        "unit": "tokens/article",
        "denominator": "Sum of valid final-article counts",
        "missing_data": "Unavailable when the denominator is zero or unavailable.",
    },
}


def definitions_as_list() -> list[dict[str, str]]:
    """Return definitions with stable identifiers for the API and documentation."""
    return [{"id": key, **value} for key, value in METRIC_DEFINITIONS.items()]
