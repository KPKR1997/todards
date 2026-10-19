"""Metric calculations for Todards observability.

All aggregation lives here so that the frontend renders API values rather than
reimplementing business rules in JavaScript.
"""

from __future__ import annotations

import math
from datetime import date
from statistics import median
from typing import Any, Iterable

from .metric_definitions import METRIC_DEFINITIONS
from .telemetry import TelemetryRecord


STAGES: tuple[tuple[str, str, str], ...] = (
    ("scrape", "Scrape", "stages_duration_seconds_scrape"),
    ("guardrails", "Guardrails", "stages_duration_seconds_guardrails"),
    ("deduplication", "Deduplication", "stages_duration_seconds_deduplication"),
    ("category_validation", "Category validation", "stages_duration_seconds_category_validation"),
    ("ranking", "Ranking", "stages_duration_seconds_ranking"),
    ("processing", "Processing", "stages_duration_seconds_processing"),
    ("assembly", "Assembly", "stages_duration_seconds_assembly"),
)

CATEGORY_FIELDS: tuple[tuple[str, str], ...] = (
    ("Health", "volume_scraped_by_category_health"),
    ("Technology", "volume_scraped_by_category_tech"),
    ("People & politics", "volume_scraped_by_category_people"),
    ("Environment", "volume_scraped_by_category_environment"),
    ("Economy", "volume_scraped_by_category_economy"),
    ("Entertainment", "volume_scraped_by_category_entertainment"),
)

FUNNEL_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("scraped", "Scraped", "volume_total_scraped"),
    ("guardrail_passed", "Guardrail passed", "volume_guardrail_passed"),
    ("guardrail_rejected", "Guardrail rejected", "volume_guardrail_rejected"),
    ("duplicates_removed", "Duplicates removed", "volume_dedup_removed"),
    ("reassignments", "Category reassignments", "volume_category_reassignments"),
    ("final_articles", "Final articles", "volume_final_articles"),
)


def _numbers(records: Iterable[TelemetryRecord], field: str) -> list[float]:
    return [value for record in records if (value := record.number(field)) is not None]


def _sum(records: Iterable[TelemetryRecord], field: str) -> float | None:
    values = _numbers(records, field)
    return sum(values) if values else None


def _ratio(numerator: float | None, denominator: float | None, multiplier: float = 100.0) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator * multiplier, 3)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = (len(ordered) - 1) * percentile / 100
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return round(ordered[low], 3)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 3)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "total": round(sum(values), 3) if values else None,
        "average": round(sum(values) / len(values), 3) if values else None,
        "median": round(median(values), 3) if values else None,
        "p50": _percentile(values, 50),
        "p95": _percentile(values, 95),
        "p99": _percentile(values, 99),
    }


def _series_timestamp(record: TelemetryRecord) -> str | None:
    return record.timestamp.isoformat() if record.timestamp else None


def _stage_summary(records: list[TelemetryRecord]) -> list[dict[str, Any]]:
    pipeline_total = _sum(records, "duration_seconds")
    count = len(records)
    items: list[dict[str, Any]] = []
    for stage_id, label, field in STAGES:
        values = _numbers(records, field)
        total = sum(values) if values else None
        items.append(
            {
                "id": stage_id,
                "label": label,
                "field": field,
                **_summary(values),
                "coverage_percent": round(len(values) / count * 100, 1) if count else 0.0,
                "share_of_pipeline_percent": _ratio(total, pipeline_total),
            }
        )
    return items


def _run_payload(record: TelemetryRecord) -> dict[str, Any]:
    values = record.values
    stages = {
        stage_id: record.number(field)
        for stage_id, _label, field in STAGES
    }
    return {
        "run_id": record.run_id,
        "source_row": record.source_row,
        "timestamp": _series_timestamp(record),
        "duration_seconds": record.number("duration_seconds"),
        "scraped": record.number("volume_total_scraped"),
        "final_articles": record.number("volume_final_articles"),
        "llm_calls": record.number("llm_performance_total_calls"),
        "llm_failures": record.number("llm_performance_total_failures"),
        "total_tokens": record.number("llm_performance_total_tokens"),
        "category_validation_status": values.get("category_validation_status"),
        "stages": stages,
        "issues": list(record.issues),
    }


def build_dashboard(records: list[TelemetryRecord], source_meta: dict[str, Any], date_from: date | None, date_to: date | None) -> dict[str, Any]:
    """Produce the complete dashboard payload for a selected time interval."""
    durations = _numbers(records, "duration_seconds")
    duration_summary = _summary(durations)
    scraped_total = _sum(records, "volume_total_scraped")
    final_total = _sum(records, "volume_final_articles")
    total_duration = duration_summary["total"]
    latest = max((item for item in records if item.timestamp), key=lambda item: item.timestamp, default=None)
    stages = _stage_summary(records)
    slowest_stage = max((item for item in stages if item["average"] is not None), key=lambda item: item["average"], default=None)

    llm_calls = _sum(records, "llm_performance_total_calls")
    llm_failures = _sum(records, "llm_performance_total_failures")
    llm_total_time = _sum(records, "llm_performance_total_time_seconds")
    prompt_tokens = _sum(records, "llm_performance_prompt_tokens")
    response_tokens = _sum(records, "llm_performance_response_tokens")
    total_tokens = _sum(records, "llm_performance_total_tokens")
    usage_responses = _sum(records, "llm_performance_usage_responses")

    duration_trend = [
        {
            "run_id": item.run_id,
            "timestamp": _series_timestamp(item),
            "duration_seconds": item.number("duration_seconds"),
            "scraped": item.number("volume_total_scraped"),
            "final_articles": item.number("volume_final_articles"),
        }
        for item in records
    ]
    stage_trend = [
        {
            "run_id": item.run_id,
            "timestamp": _series_timestamp(item),
            **{stage_id: item.number(field) for stage_id, _label, field in STAGES},
        }
        for item in records
    ]
    llm_trend = [
        {
            "run_id": item.run_id,
            "timestamp": _series_timestamp(item),
            "prompt_eval_seconds": item.number("llm_performance_prompt_eval_seconds"),
            "generation_seconds": item.number("llm_performance_generation_seconds"),
            "load_seconds": item.number("llm_performance_load_seconds"),
            "server_total_seconds": item.number("llm_performance_server_total_seconds"),
            "total_tokens": item.number("llm_performance_total_tokens"),
        }
        for item in records
    ]
    category_totals = [
        {"category": label, "articles": _sum(records, field), "coverage_percent": round(len(_numbers(records, field)) / len(records) * 100, 1) if records else 0.0}
        for label, field in CATEGORY_FIELDS
    ]
    funnel = [
        {"id": key, "label": label, "value": _sum(records, field), "coverage_percent": round(len(_numbers(records, field)) / len(records) * 100, 1) if records else 0.0}
        for key, label, field in FUNNEL_FIELDS
    ]

    token_inconsistencies: list[dict[str, Any]] = []
    for item in records:
        prompt = item.number("llm_performance_prompt_tokens")
        response = item.number("llm_performance_response_tokens")
        total = item.number("llm_performance_total_tokens")
        if prompt is not None and response is not None and total is not None and abs((prompt + response) - total) > 0.001:
            token_inconsistencies.append({"run_id": item.run_id, "timestamp": _series_timestamp(item), "expected": prompt + response, "recorded": total})

    safety_fields = (
        ("files_seen", "article_safety_files_seen"),
        ("articles_seen", "article_safety_articles_seen"),
        ("classified_safe", "article_safety_classified_safe"),
        ("classified_unsafe", "article_safety_classified_unsafe"),
        ("unsafe_removed", "article_safety_unsafe_removed"),
        ("unsafe_would_remove", "article_safety_unsafe_would_remove"),
        ("unclassified", "article_safety_unclassified"),
        ("unclassified_retained", "article_safety_unclassified_retained"),
        ("model_errors", "article_safety_model_errors"),
        ("file_errors", "article_safety_file_errors"),
    )
    safety_values = {name: _sum(records, field) for name, field in safety_fields}
    safety_coverage = round(len(_numbers(records, "article_safety_articles_seen")) / len(records) * 100, 1) if records else 0.0

    warnings = [
        "Overall successful/failed run counts are unavailable: category_validation_status describes that stage, not the whole pipeline.",
        "Stage durations may overlap or omit uninstrumented work; their shares are not expected to total 100%.",
        "LLM latency percentiles are unavailable because the source contains per-run aggregates, not individual call observations.",
        "Funnel counts are diagnostic measurements and can overlap; they are not treated as a strict sequential conversion funnel.",
    ]
    if source_meta["invalid_row_count"]:
        warnings.append(f"{source_meta['invalid_row_count']} source row(s) contain malformed values; malformed values are shown as unavailable.")
    if token_inconsistencies:
        warnings.append(f"{len(token_inconsistencies)} run(s) have recorded token totals that do not equal prompt + response tokens.")

    return {
        "meta": {
            "source": source_meta,
            "selected_row_count": len(records),
            "warnings": warnings,
        },
        "period": {
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        },
        "overview": {
            "run_count": len(records),
            "successful_runs": None,
            "failed_runs": None,
            "run_status_note": "Unavailable: no reliable whole-pipeline run status field is present.",
            "latest_run": _run_payload(latest) if latest else None,
            "duration": duration_summary,
            "total_scraped": scraped_total,
            "total_final_articles": final_total,
            "publication_yield_percent": _ratio(final_total, scraped_total),
            "articles_per_minute": _ratio(final_total, total_duration, 60.0),
            "slowest_stage": slowest_stage,
        },
        "duration_trend": duration_trend,
        "stages": {
            "summary": stages,
            "trend": stage_trend,
            "note": "Stage durations are independently measured. Their sum can differ from total pipeline duration because stages may overlap or because some work is not instrumented.",
        },
        "content": {
            "funnel": funnel,
            "category_totals": category_totals,
            "deduplication": {
                "total_checked": _sum(records, "deduplication_total_checked"),
                "exact_duplicate_pairs": _sum(records, "deduplication_exact_duplicate_pairs"),
                "semantic_duplicate_pairs": _sum(records, "deduplication_semantic_duplicate_pairs"),
                "duplicate_pairs_found": _sum(records, "deduplication_duplicate_pairs_found"),
                "duplicate_clusters": _sum(records, "deduplication_duplicate_clusters"),
                "duplicates_removed": _sum(records, "deduplication_duplicates_removed"),
                "published_duplicates_removed": _sum(records, "deduplication_published_duplicates_removed"),
            },
            "note": "Funnel metrics may overlap or originate at different stages. They are shown as observed diagnostic counts, not as a single conservation equation.",
        },
        "llm": {
            "total_calls": llm_calls,
            "total_failures": llm_failures,
            "failure_rate_percent": _ratio(llm_failures, llm_calls),
            "weighted_average_response_time_seconds": _ratio(llm_total_time, llm_calls, 1.0),
            "total_prompt_tokens": prompt_tokens,
            "total_response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "tokens_per_usage_response": _ratio(total_tokens, usage_responses, 1.0),
            "tokens_per_final_article": _ratio(total_tokens, final_total, 1.0),
            "latency_percentiles": None,
            "latency_percentiles_note": "Unavailable: individual call-level latency observations are not recorded in the CSV.",
            "token_total_inconsistencies": token_inconsistencies,
            "trend": llm_trend,
        },
        "safety": {
            "coverage_percent": safety_coverage,
            "values": safety_values,
            "dry_run_rows": sum(item.values.get("article_safety_dry_run") is True for item in records),
        },
        "runs": [_run_payload(item) for item in reversed(records)],
        "metric_definition_ids": list(METRIC_DEFINITIONS),
    }
