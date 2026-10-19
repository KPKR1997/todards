# Todards Model & Pipeline Observatory

## Scope and preservation guarantee

The observatory is an additive, read-only interface over `reports/performance_history.csv`.

- It does not import, invoke, modify, or replace `metrics.py` or `reporter.py`.
- It never writes to `performance_history.csv`, `todays_metrics.csv`, JSON reports, Markdown reports, or the text summary.
- Existing report formats and pipeline output contracts remain unchanged.

The existing collector in `metrics.py` establishes the semantics used here. `reporter.py` flattens its nested output to the append-only history CSV. The observatory therefore reads that history rather than adding another telemetry writer.

## Components

```text
Todards pipeline (unchanged)
  └─ metrics.py → reporter.py → reports/performance_history.csv
                                         │ read only
                                         ▼
                                backend/services/telemetry.py
                                         ▼
                                backend/services/analytics.py
                                         ▼
                                  FastAPI /api/v1/*
                                         ▼
                            frontend (Next.js + Recharts)
```

`backend/services/telemetry.py` normalizes scalar values, ISO timestamps, booleans, malformed rows, and source coverage. A malformed value becomes `null`; it is never coerced to zero. `backend/services/analytics.py` owns all formulas, summaries, trends, and data-quality caveats. The web client only renders the API response.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | Confirms that the source CSV can be read. |
| `GET /api/v1/dashboard?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` | Complete typed dashboard payload with inclusive filters. |
| `GET /api/v1/runs` | Run ledger for integrations. |
| `GET /api/v1/metric-definitions` | Formula, unit, denominator, and missing-data policy for every derived metric. |

FastAPI also exposes the endpoint schemas at `/docs` while the backend is running.

## Source verification performed

The current repository contains no existing Next.js application, Python API, dependency manifest, or test suite. The telemetry source is `reports/performance_history.csv`, written by `PipelineReporter._append_history` in `reporter.py` after `PipelineMetrics.to_dict()` produces the run data in `metrics.py`.

At implementation time, the source contained 24 records from 15 October through 19 October 2026. Timestamps were unique. Core duration, stage, volume, deduplication, category-validation, and LLM call columns were populated in all current rows. Article-safety and token/timing fields were added later and were populated for 11 of 24 historical rows; the dashboard displays that coverage instead of treating historical blanks as zero.

## Metric rules

The central implementation is `backend/services/metric_definitions.py`. Important rules:

- Publication yield is `sum(final articles) / sum(scraped)`, never an average of run rates.
- Articles/minute is `sum(final articles) / (sum(run duration) / 60)`.
- Stage percentiles are computed across individual stage measurements. A zero is a valid stage measurement; a blank is not.
- Stage shares use `sum(stage duration) / sum(overall duration)`. They are not expected to add to 100%: independent timers can overlap and some overall time may be uninstrumented.
- LLM failure rate uses total failures / total calls. Average LLM response time is weighted from the source collector's total LLM time / total call count—not an average of per-run averages.
- LLM P50/P95/P99 latency is intentionally unavailable because the CSV contains run-level aggregates, not individual calls.
- Prompt + response tokens are checked against recorded total tokens; discrepancies are surfaced and source data is not silently corrected.
- No currency or estimated LLM cost is calculated: model identity and pricing assumptions are not in telemetry.
- `category_validation_status` belongs to one stage. It is not used to invent overall successful/failed pipeline run counts.
- The content funnel is visualized as observed processing counts, not a strict conservation sequence, because documented counts can overlap or refer to separate phases.

## Configuration

The source defaults to the repository-local `reports/performance_history.csv`. Set `TODARDS_TELEMETRY_PATH` only to point the API to a different existing CSV; this does not change any pipeline configuration.

`TODARDS_CORS_ORIGINS` is a comma-separated allow-list, defaulting to local Next.js development URLs. The frontend's `NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000/api/v1`.
