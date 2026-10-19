"""Defensive, read-only access to the append-only Todards telemetry CSV."""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable


TIMESTAMP_FIELDS = {"timestamp"}
TEXT_FIELDS = {"date", "category_validation_status"}
BOOLEAN_FIELDS = {"article_safety_dry_run"}


@dataclass(frozen=True)
class TelemetryRecord:
    """One normalized source row. Invalid scalar values become None, never zero."""

    source_row: int
    timestamp: datetime | None
    values: dict[str, Any]
    issues: tuple[str, ...]

    @property
    def run_id(self) -> str:
        raw_timestamp = self.values.get("timestamp")
        return str(raw_timestamp or f"source-row-{self.source_row}")

    def number(self, field: str) -> float | None:
        value = self.values.get(field)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_row": self.source_row,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "date": self.values.get("date"),
            "values": self.values,
            "issues": list(self.issues),
        }


def default_telemetry_path() -> Path:
    """Resolve an optional override or the repository's established source CSV."""
    configured = os.getenv("TODARDS_TELEMETRY_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "reports" / "performance_history.csv"


def _parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_scalar(field: str, raw: str) -> tuple[Any, str | None]:
    value = raw.strip()
    if not value:
        return None, None
    if field in TEXT_FIELDS:
        return value, None
    if field in BOOLEAN_FIELDS:
        lowered = value.lower()
        if lowered in {"true", "1", "yes"}:
            return True, None
        if lowered in {"false", "0", "no"}:
            return False, None
        return None, f"invalid boolean for {field!r}"
    if field in TIMESTAMP_FIELDS:
        parsed = _parse_timestamp(value)
        return parsed, None if parsed else f"invalid ISO timestamp for {field!r}"
    try:
        number = float(value)
    except ValueError:
        return None, f"invalid numeric value for {field!r}"
    if not math.isfinite(number):
        return None, f"non-finite numeric value for {field!r}"
    return number, None


def load_telemetry(path: Path | None = None) -> tuple[list[TelemetryRecord], dict[str, Any]]:
    """Load all rows without modifying the source CSV.

    CSV schema changes are tolerated: known text and boolean fields retain their
    type and every other populated column is treated as numeric telemetry.
    """
    source = (path or default_telemetry_path()).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Telemetry CSV was not found: {source}")
    if not source.is_file():
        raise ValueError(f"Telemetry source is not a file: {source}")

    records: list[TelemetryRecord] = []
    headers: list[str] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = [field for field in (reader.fieldnames or []) if field]
        if not headers:
            raise ValueError("Telemetry CSV has no header row.")
        for source_row, row in enumerate(reader, start=2):
            issues: list[str] = []
            values: dict[str, Any] = {}
            for field in headers:
                parsed, issue = _parse_scalar(field, row.get(field) or "")
                if field == "timestamp":
                    values[field] = (row.get(field) or "").strip() or None
                    timestamp = parsed
                else:
                    values[field] = parsed
                if issue:
                    issues.append(issue)
            extras = row.get(None)
            if extras:
                issues.append("row contains more cells than the CSV header")
            records.append(
                TelemetryRecord(
                    source_row=source_row,
                    timestamp=timestamp if "timestamp" in headers else None,
                    values=values,
                    issues=tuple(issues),
                )
            )

    stat = source.stat()
    field_coverage = {
        field: round(sum(record.values.get(field) is not None for record in records) / len(records) * 100, 1)
        if records
        else 0.0
        for field in headers
    }
    return records, {
        "path": str(source),
        "row_count": len(records),
        "columns": headers,
        "invalid_row_count": sum(bool(record.issues) for record in records),
        "field_coverage_percent": field_coverage,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def filter_records(
    records: Iterable[TelemetryRecord], date_from: date | None = None, date_to: date | None = None
) -> list[TelemetryRecord]:
    """Filter valid-timestamp records inclusively. Untimestamped rows cannot be dated."""
    filtered: list[TelemetryRecord] = []
    for record in records:
        if (date_from or date_to) and record.timestamp is None:
            continue
        record_date = record.timestamp.date() if record.timestamp else None
        if date_from and record_date and record_date < date_from:
            continue
        if date_to and record_date and record_date > date_to:
            continue
        filtered.append(record)
    return sorted(filtered, key=lambda item: item.timestamp or datetime.combine(date.min, time.min))
