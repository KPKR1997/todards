
import csv
import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from evaluation.metrics import PipelineMetrics
from config.settings import EVALUATION_REPORTS_DIR
logger = logging.getLogger("todards.reporter")

class PipelineReporter:
    HISTORY_FILE = "performance_history.csv"
    TODAY_FILE = "todays_metrics.csv"
    EMAIL_SUMMARY_FILE = "todays_summary.txt"
    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = Path(reports_dir or EVALUATION_REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    @staticmethod
    def _column_name(value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "_", str(value)).strip("_").lower()
        return value or "metric"
    @classmethod
    def _flatten_metrics(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        row: Dict[str, Any] = {}
        def walk(value: Any, prefix: str = "") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_prefix = f"{prefix}_{key}" if prefix else str(key)
                    walk(child, child_prefix)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                if prefix and value is not None:
                    row[cls._column_name(prefix)] = value
            # Lists are excluded from the CSV; retain useful counts instead.
        walk(data)
        row["guardrail_rejection_details_count"] = len(
            data.get("guardrail_rejections", []) or []
        )
        validation = data.get("category_validation", {})
        reassignments = (
            validation.get("reassignments", [])
            if isinstance(validation, dict)
            else []
        )
        row["category_reassignment_details_count"] = len(reassignments or [])
        return row
    @staticmethod
    def _read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
        if not path.exists() or path.stat().st_size == 0:
            return [], []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                return list(reader.fieldnames or []), list(reader)
        except (OSError, csv.Error) as exc:
            logger.warning("Could not read existing CSV %s: %s", path, exc)
            return [], []
    @staticmethod
    def _write_csv_rows(
        path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]
    ) -> None:
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        temporary_path.replace(path)


    def _append_history(self, row: Dict[str, Any]) -> Tuple[Optional[Dict[str, str]], List[Dict[str, str]]]:
        path = self.reports_dir / self.HISTORY_FILE
        old_fields, old_rows = self._read_csv_rows(path)
        previous = old_rows[-1] if old_rows else None
        fields = list(old_fields)
        for key in row:
            if key not in fields:
                fields.append(key)
        if not fields:
            fields = list(row.keys())
        old_rows.append({
            key: str(value) if value is not None else ""
            for key, value in row.items()
        })
        self._write_csv_rows(path, old_rows, fields)
        return previous, old_rows
    def _write_today_metrics(self, row: Dict[str, Any]) -> Path:
        path = self.reports_dir / self.TODAY_FILE
        self._write_csv_rows(path, [row], list(row.keys()))
        return path
    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            if value is None or str(value).strip() == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
    @staticmethod
    def _duration_seconds(row: Dict[str, Any]) -> Optional[float]:
        for key in ("duration_seconds", "pipeline_duration_seconds"):
            value = PipelineReporter._number(row.get(key))
            if value is not None:
                return value
        return None
    @staticmethod

    def _category_count(row: Dict[str, Any], category: str) -> Optional[float]:
        target = re.sub(r"[^a-z0-9]", "", category.lower())
        for key, value in row.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if "scrapedbycategory" in normalized and normalized.endswith(target):
                number = PipelineReporter._number(value)
                if number is not None:
                    return number
        return None
    def _build_observations(
        self,
        data: Dict[str, Any],
        current: Dict[str, Any],
        previous: Optional[Dict[str, str]],
        history_rows: List[Dict[str, str]],

    ) -> List[str]:
        observations: List[str] = []
        volume = data.get("volume", {}) if isinstance(data.get("volume"), dict) else {}
        duration = self._number(data.get("duration_seconds"))
        scraped = self._number(volume.get("total_scraped"))
        duplicates = self._number(volume.get("dedup_removed"))
        if duration is not None:
            observations.append(f"Pipeline duration: {duration / 60:.1f} minutes.")
        if scraped is not None and duplicates is not None:
            if scraped > 0:
                ratio = duplicates / scraped * 100
                observations.append(
                    f"Semantic deduplication removed {duplicates:g} duplicate articles "
                    f"from {scraped:g} scraped articles ({ratio:.1f}% of scraped volume; "
                    "the count is relative to total scraped articles)."
                )
            elif duplicates > 0:
                observations.append(
                    f"Deduplication removed {duplicates:g} duplicates while total scraped volume is zero; "
                    "check metric definitions or collection."
                )
        if previous:
            old_duration = self._number(previous.get("duration_seconds"))
            old_scraped = self._number(previous.get("volume_total_scraped"))
            old_duplicates = self._number(previous.get("volume_dedup_removed"))
            if duration is not None and old_duration is not None and old_duration > 0:
                change = (duration - old_duration) / old_duration * 100
                observations.append(
                    f"Pipeline duration changed {change:+.1f}% versus the previous recorded run."
                )
            if scraped is not None and old_scraped is not None:
                observations.append(
                    f"Scraped article volume changed from {old_scraped:g} to {scraped:g} "
                    "versus the previous recorded run."
                )
            if duplicates is not None and old_duplicates is not None:
                observations.append(
                    f"Duplicates removed changed from {old_duplicates:g} to {duplicates:g} "
                    "versus the previous recorded run."
                )
        # Flag four consecutive recorded runs with zero Guardian scrape count.
        # Only make this claim when the metric exists in every checked run.
        recent = history_rows[-4:]
        if len(recent) == 4:
            guardian_counts = [self._category_count(item, "guardian") for item in recent]
            if all(value is not None for value in guardian_counts) and all(
                value == 0 for value in guardian_counts
            ):
                observations.append(
                    "Guardian scraped article count is zero in each of the last four "
                    "recorded runs. This is a source-ingestion anomaly worth investigating; "
                    "the metrics alone do not establish the cause."
                )
        if not observations:
            observations.append(
                "The available metrics contain limited data for trend analysis; avoid "
                "asserting normality or anomalies without supporting evidence."
            )
        return observations
    @staticmethod
    def _evaluation_prompt(
        data: Dict[str, Any],
        current: Dict[str, Any],
        observations: List[str],
    ) -> str:
        compact_data = {
            "date": data.get("date"),
            "timestamp": data.get("timestamp"),
            "duration_seconds": data.get("duration_seconds"),
            "volume": data.get("volume", {}),
            "llm_performance": data.get("llm_performance", {}),
            "stages_duration_seconds": data.get("stages_duration_seconds", {}),
            "current_flat_metrics": current,
            "evidence_based_observations": observations,
        }
        return (
            "You are the Todards pipeline evaluation agent. Write a concise, useful "
            "plain-text evaluation for the operator's daily email. Assess overall run "
            "health, elapsed time only relative to available historical evidence, scrape "
            "volume, semantic deduplication, source/category ingestion anomalies, and LLM "
            "performance where metrics support it. State what looks healthy, what deserves "
            "investigation, and the next practical check.\n\n"
            "Grounding rules:\n"
            "- Use only the supplied data and evidence-based observations.\n"
            "- Never invent a source count, historical baseline, incident, or cause.\n"
            "- Do not call duration 'normal' unless comparison data supports that conclusion.\n"
            "- Distinguish a suspicious pattern from a proven failure.\n"
            "- If evidence is insufficient, say so explicitly.\n"
            "- Do not repeat every metric; interpret the important ones.\n"
            "- Return 2-5 short paragraphs or concise bullets, no greeting or signature.\n\n"
            f"DATA:\n{json.dumps(compact_data, ensure_ascii=False, indent=2, default=str)}"
        )
    def _generate_llm_evaluation(
        self,
        data: Dict[str, Any],
        current: Dict[str, Any],
        observations: List[str],
    ) -> str:
        base_url = os.getenv("TODARDS_OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model = "llama3:latest"
        payload = {
            "model": model,
            "prompt": self._evaluation_prompt(data, current, observations),
            "stream": False,
            "options": {"temperature": 0.2},
        }
        request = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = str(result.get("response", "")).strip()
            if text:
                return text
            raise ValueError("Ollama returned an empty evaluation.")
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logger.exception("Could not generate LLM evaluation with Ollama.")
            fallback = [
                "LLM evaluation unavailable: Ollama did not return an evaluation.",
                f"Reason: {type(exc).__name__}: {exc}",
                "",
                "Metrics-based observations (not an LLM-generated assessment):",
            ]
            fallback.extend(f"- {item}" for item in observations)
            fallback.append(
                "- Check that Ollama is running and TODARDS_OLLAMA_MODEL names an installed model."
            )
            return "\n".join(fallback)
    def _render_email_summary(
        self,
        data: Dict[str, Any],
        current: Dict[str, Any],
        previous: Optional[Dict[str, str]],
        history_rows: List[Dict[str, str]],
    ) -> str:
        observations = self._build_observations(data, current, previous, history_rows)
        evaluation = self._generate_llm_evaluation(data, current, observations)
        date = data.get("date", "unknown date")
        duration = self._number(data.get("duration_seconds"))
        duration_text = f"{duration / 60:.1f} minutes" if duration is not None else "unknown"
        return (
            f"TODARDS LLM PIPELINE EVALUATION — {date}\n"
            f"Execution timestamp: {data.get('timestamp', 'Unknown')}\n"
            f"Pipeline duration: {duration_text}\n\n"
            f"{evaluation.strip()}\n"
        )
    def generate_report(self, metrics: PipelineMetrics) -> Dict[str, Path]:
        data = metrics.to_dict()
        date_str = str(data.get("date", "unknown-date"))
        row = self._flatten_metrics(data)
        previous, history_rows = self._append_history(row)
        today_path = self._write_today_metrics(row)
        email_summary = self._render_email_summary(
            data, row, previous, history_rows
        )
        email_path = self.reports_dir / self.EMAIL_SUMMARY_FILE
        email_path.write_text(email_summary, encoding="utf-8")
        # Retain legacy outputs to avoid breaking existing consumers.
        json_path = self.reports_dir / f"{date_str}_report.json"
        md_path = self.reports_dir / f"{date_str}_report.md"
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=4)
        md_path.write_text(self._render_markdown(data), encoding="utf-8")
        logger.info(
            "Evaluation reports generated: %s, %s, %s",
            self.TODAY_FILE, self.HISTORY_FILE, self.EMAIL_SUMMARY_FILE,
        )
        return {
            "performance_history": self.reports_dir / self.HISTORY_FILE,
            "todays_metrics": today_path,
            "email_summary": email_path,
            "json": json_path,
            "markdown": md_path,
        }
    def _render_markdown(self, data: Dict[str, Any]) -> str:
        vol = data.get("volume", {})
        llm = data.get("llm_performance", {})
        stages = data.get("stages_duration_seconds", {})
        md = [
            f"# Todards Pipeline Evaluation Report — {data.get('date')}",
            f"\n> **Execution Timestamp**: {data.get('timestamp')}",
            f"> **Total Duration**: {data.get('duration_seconds')} seconds\n",
            "## Executive Summary\n",
            "| Metric | Value |", "|---|---|",
            f"| Total Scraped Articles | {vol.get('total_scraped', 0)} |",
            f"| Guardrail Filtered (NSFW/Rumor) | {vol.get('guardrail_rejected', 0)} |",
            f"| Semantic Duplicates Removed | {vol.get('dedup_removed', 0)} |",
            f"| Category Reassignments | {vol.get('category_reassignments', 0)} |",
            f"| Final Published Articles | {vol.get('final_articles', 0)} ({vol.get('final_categories', 0)} categories) |",
            f"| Total Ollama LLM Calls | {llm.get('total_calls', 0)} |",
            f"| Ollama Avg Latency | {llm.get('avg_response_time', 0)}s |",
            "\n## Stage Timing Breakdown\n", "| Pipeline Stage | Duration (s) |", "|---|---|",
        ]
        for stage, duration in sorted(stages.items()):
            try:
                md.append(f"| {stage.replace('_', ' ').title()} | {float(duration):.2f}s |")
            except (TypeError, ValueError):
                md.append(f"| {stage.replace('_', ' ').title()} | {duration} |")
        md.extend(["\n## Ingestion Breakdown\n", "| Category | Articles Scraped |", "|---|---|"])
        for category, count in vol.get("scraped_by_category", {}).items():
            md.append(f"| {category} | {count} |")
        rejections = data.get("guardrail_rejections", [])
        if rejections:
            md.extend(["\n## Guardrail Filtering Details\n", "| Article Title | Triggered Flags | Reason |", "|---|---|---|"])
            for rejection in rejections:
                flags = ", ".join(rejection.get("guardrail_flags", []))
                reason = str(rejection.get("guardrail_reason", "")).replace("|", "\\|")
                title = str(rejection.get("title", ""))[:45].replace("|", "\\|")
                md.append(f"| {title}... | `{flags}` | {reason} |")
        else:
            md.append("\n## Guardrail Filtering\n- Zero articles flagged for safety or gossip issues.")
        cat_val = data.get("category_validation", {})
        reassignments = cat_val.get("reassignments", []) if isinstance(cat_val, dict) else []
        if reassignments:
            md.extend(["\n## Category Cross-Validation Reassignments\n", "| Article Title | From | Reassigned To | Confidence |", "|---|---|---|---|"])
            for item in reassignments:
                title = str(item.get("title", ""))[:40].replace("|", "\\|")
                try:
                    confidence = float(item.get("confidence", 0))
                except (TypeError, ValueError):
                    confidence = 0.0
                md.append(f"| {title}... | {item.get('from')} | **{item.get('to')}** | {confidence:.2f} |")
        md.append("\n---\n*Report auto-generated by Todards Enterprise Pipeline.*")
        return "\n".join(md)
