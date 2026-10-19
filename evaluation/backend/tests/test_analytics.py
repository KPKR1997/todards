from __future__ import annotations

import unittest
from datetime import datetime

from backend.services.analytics import build_dashboard
from backend.services.telemetry import TelemetryRecord


def record(row: int, timestamp: str, **values: float | str | None) -> TelemetryRecord:
    return TelemetryRecord(
        source_row=row,
        timestamp=datetime.fromisoformat(timestamp),
        values={"timestamp": timestamp, **values},
        issues=(),
    )


class AnalyticsTests(unittest.TestCase):
    def test_weighted_rates_and_percentages_use_underlying_denominators(self) -> None:
        records = [
            record(2, "2026-10-01T10:00:00", duration_seconds=60, volume_total_scraped=10, volume_final_articles=5, llm_performance_total_calls=10, llm_performance_total_failures=1, llm_performance_total_time_seconds=20),
            record(3, "2026-10-02T10:00:00", duration_seconds=240, volume_total_scraped=90, volume_final_articles=9, llm_performance_total_calls=90, llm_performance_total_failures=0, llm_performance_total_time_seconds=90),
        ]
        payload = build_dashboard(records, {"invalid_row_count": 0}, None, None)
        self.assertEqual(payload["overview"]["publication_yield_percent"], 14.0)
        self.assertEqual(payload["overview"]["articles_per_minute"], 2.8)
        self.assertEqual(payload["llm"]["failure_rate_percent"], 1.0)
        self.assertEqual(payload["llm"]["weighted_average_response_time_seconds"], 1.1)

    def test_token_mismatch_is_reported_not_corrected(self) -> None:
        records = [record(2, "2026-10-01T10:00:00", llm_performance_prompt_tokens=10, llm_performance_response_tokens=2, llm_performance_total_tokens=11)]
        payload = build_dashboard(records, {"invalid_row_count": 0}, None, None)
        self.assertEqual(len(payload["llm"]["token_total_inconsistencies"]), 1)
        self.assertEqual(payload["llm"]["total_tokens"], 11)


if __name__ == "__main__":
    unittest.main()
