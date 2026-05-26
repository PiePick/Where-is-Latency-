"""Append-only latency logging for CREDO experiments."""

from __future__ import annotations

import json
import csv
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = ROOT / "latency_logs"
DEFAULT_JSONL = DEFAULT_LOG_DIR / "events.jsonl"
DEFAULT_MODULE_CSV = DEFAULT_LOG_DIR / "module_events.csv"
DEFAULT_MARKDOWN = DEFAULT_LOG_DIR / "latest_summary.md"


MODULE_BY_STAGE = {
    "fast_track_analysis": "fasttrack_analysis",
    "fast_track_interjection": "fasttrack_interjection_dispatch",
    "fast_track_tts_or_cache": "fasttrack_audio",
    "fast_track_keyword_echo": "fasttrack_keyword_echo",
    "fast_track_waiting_audio": "fasttrack_waiting_audio",
    "latency_cover_plan": "cover_plan",
    "slow_track_llm": "slowtrack_llm",
    "slow_track_tts": "slowtrack_tts",
    "turn_total": "turn_total",
    "proactive_cover": "proactive_cover",
    "vtuber_mode_llm": "vtuber_llm",
    "vtuber_mode_tts": "vtuber_tts",
    "vtuber_mode_total": "vtuber_total",
}

MODULE_CSV_FIELDS = [
    "ts_local",
    "turn_id",
    "experiment_run_id",
    "experiment_factor",
    "scenario",
    "component_mode",
    "selection_policy",
    "scheduling_mode",
    "module",
    "stage",
    "elapsed_ms",
    "engine",
    "emotion",
    "intent",
    "response_act",
    "style_tag",
    "cache_hit",
    "audio_path",
    "char_len",
    "word_count",
    "text_preview",
]


@dataclass
class LatencyEvent:
    """One measured latency event."""

    stage: str
    elapsed_ms: float
    text: str = ""
    engine: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        """Return a JSON-serializable event."""
        text = self.text or ""
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": self.stage,
            "elapsed_ms": round(float(self.elapsed_ms), 3),
            "engine": self.engine,
            "char_len": len(text),
            "word_count": len(text.split()),
            "tag_count": text.count("["),
            "text": text,
            "metadata": self.metadata,
        }


class LatencyLogger:
    """Write latency events to JSONL and a readable rolling Markdown summary."""

    def __init__(
        self,
        *,
        jsonl_path: Path = DEFAULT_JSONL,
        module_csv_path: Path = DEFAULT_MODULE_CSV,
        markdown_path: Path = DEFAULT_MARKDOWN,
        summary_limit: int = 80,
    ) -> None:
        self.jsonl_path = jsonl_path
        self.module_csv_path = module_csv_path
        self.markdown_path = markdown_path
        self.summary_limit = summary_limit
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: LatencyEvent) -> dict[str, Any]:
        """Append one event and refresh the Markdown summary."""
        record = event.to_record()
        with self.jsonl_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.write_module_csv_row(record)
        self.write_summary()
        return record

    def write_module_csv_row(self, record: dict[str, Any]) -> None:
        """Append one compact module-level CSV row for live inspection."""
        self._ensure_module_csv_schema()
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        stage = str(record.get("stage", ""))
        text = str(record.get("text", "") or "").replace("\r", " ").replace("\n", " ")
        text_preview = " ".join(text.split())
        if len(text_preview) > 120:
            text_preview = text_preview[:117] + "..."

        row = {
            "ts_local": datetime.now().astimezone().isoformat(timespec="seconds"),
            "turn_id": metadata.get("turn_id", ""),
            "experiment_run_id": metadata.get("experiment_run_id", ""),
            "experiment_factor": metadata.get("experiment_factor", ""),
            "scenario": metadata.get("scenario", ""),
            "component_mode": metadata.get("component_mode", ""),
            "selection_policy": metadata.get("selection_policy", ""),
            "scheduling_mode": metadata.get("scheduling_mode", ""),
            "module": MODULE_BY_STAGE.get(stage, stage),
            "stage": stage,
            "elapsed_ms": record.get("elapsed_ms", 0.0),
            "engine": record.get("engine", ""),
            "emotion": metadata.get("emotion", ""),
            "intent": metadata.get("intent", ""),
            "response_act": metadata.get("response_act") or metadata.get("persona_response_act", ""),
            "style_tag": metadata.get("style_tag") or metadata.get("persona_style_tag", ""),
            "cache_hit": metadata.get("fast_audio_cache_hit", ""),
            "audio_path": metadata.get("audio_path", ""),
            "char_len": record.get("char_len", 0),
            "word_count": record.get("word_count", 0),
            "text_preview": text_preview,
        }

        write_header = not self.module_csv_path.exists() or self.module_csv_path.stat().st_size == 0
        with self.module_csv_path.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=MODULE_CSV_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def _ensure_module_csv_schema(self) -> None:
        """Upgrade existing CSV logs when experiment-factor columns are introduced."""
        if not self.module_csv_path.exists() or self.module_csv_path.stat().st_size == 0:
            return
        with self.module_csv_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames == MODULE_CSV_FIELDS:
                return
            existing_rows = list(reader)
        temporary_path = self.module_csv_path.with_suffix(".csv.tmp")
        with temporary_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=MODULE_CSV_FIELDS)
            writer.writeheader()
            for existing_row in existing_rows:
                writer.writerow({field: existing_row.get(field, "") for field in MODULE_CSV_FIELDS})
        temporary_path.replace(self.module_csv_path)

    def write_summary(self) -> None:
        """Write the most recent events as a compact Markdown table."""
        records = self.read_recent(self.summary_limit)
        lines = [
            "# CREDO Latency Log",
            "",
            f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| Time | Stage | Engine | ms | Chars | Words | Tags | Text |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for row in records:
            text = str(row.get("text", "")).replace("|", "/")
            if len(text) > 80:
                text = text[:77] + "..."
            timestamp = str(row.get("ts", ""))[11:19]
            lines.append(
                "| {time} | {stage} | {engine} | {ms:.1f} | {chars} | {words} | {tags} | {text} |".format(
                    time=timestamp,
                    stage=row.get("stage", ""),
                    engine=row.get("engine", ""),
                    ms=float(row.get("elapsed_ms", 0.0)),
                    chars=row.get("char_len", 0),
                    words=row.get("word_count", 0),
                    tags=row.get("tag_count", 0),
                    text=text,
                )
            )
        self.markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def read_recent(self, limit: int) -> list[dict[str, Any]]:
        """Read the most recent JSONL records."""
        if not self.jsonl_path.exists():
            return []
        lines = self.jsonl_path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-limit:]:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records


class Timer:
    """Context manager that records elapsed time on exit."""

    def __init__(self, logger: LatencyLogger, stage: str, *, text: str = "", engine: str = "", **metadata: Any) -> None:
        self.logger = logger
        self.stage = stage
        self.text = text
        self.engine = engine
        self.metadata = metadata
        self.started = 0.0

    def __enter__(self) -> "Timer":
        self.started = time.perf_counter()
        return self

    def __exit__(self, *_exc: object) -> None:
        elapsed_ms = (time.perf_counter() - self.started) * 1000.0
        self.logger.log(
            LatencyEvent(
                stage=self.stage,
                elapsed_ms=elapsed_ms,
                text=self.text,
                engine=self.engine,
                metadata=self.metadata,
            )
        )
