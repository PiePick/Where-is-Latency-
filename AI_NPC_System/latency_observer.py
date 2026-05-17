"""Append-only latency logging for CREDO experiments."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = ROOT / "latency_logs"
DEFAULT_JSONL = DEFAULT_LOG_DIR / "events.jsonl"
DEFAULT_MARKDOWN = DEFAULT_LOG_DIR / "latest_summary.md"


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
        markdown_path: Path = DEFAULT_MARKDOWN,
        summary_limit: int = 80,
    ) -> None:
        self.jsonl_path = jsonl_path
        self.markdown_path = markdown_path
        self.summary_limit = summary_limit
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: LatencyEvent) -> dict[str, Any]:
        """Append one event and refresh the Markdown summary."""
        record = event.to_record()
        with self.jsonl_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.write_summary()
        return record

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
