#!/usr/bin/env python3
"""Build a lightweight latency prediction artifact from CREDO latency logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "latency_logs" / "events.jsonl"
DEFAULT_JSON = ROOT / "reports" / "latency_prediction_model.json"
DEFAULT_MD = ROOT / "reports" / "latency_prediction_model.md"


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        elapsed = float(row.get("elapsed_ms") or 0.0)
        if elapsed <= 0:
            continue
        rows.append(row)
    return rows


def engine_key(engine: str) -> str:
    engine = str(engine or "").lower()
    if "fish" in engine:
        return "fish_speech"
    if "stylebert" in engine or "style-bert" in engine:
        return "stylebert_vits2"
    return "default"


def fit_fallback(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {"intercept_ms": 3500.0, "char_ms": 65.0, "tag_ms": 450.0, "records": 0}
    xs = [max(1, int(row.get("char_len") or len(str(row.get("text", ""))))) for row in rows]
    ys = [float(row.get("elapsed_ms") or 0.0) for row in rows]
    per_char = [y / x for x, y in zip(xs, ys) if x > 0 and y > 0]
    char_ms = max(5.0, min(500.0, median(per_char) if per_char else 65.0))
    residuals = [max(0.0, y - char_ms * x) for x, y in zip(xs, ys)]
    intercept = max(100.0, min(30000.0, median(residuals) if residuals else 3500.0))
    tag_rows = [row for row in rows if int(row.get("tag_count") or 0) > 0]
    tag_ms = 450.0
    if tag_rows:
        tagged = median(float(row.get("elapsed_ms") or 0.0) for row in tag_rows)
        untagged_rows = [row for row in rows if int(row.get("tag_count") or 0) == 0]
        if untagged_rows:
            untagged = median(float(row.get("elapsed_ms") or 0.0) for row in untagged_rows)
            tag_ms = max(0.0, min(3000.0, tagged - untagged))
    return {
        "intercept_ms": round(intercept, 3),
        "char_ms": round(char_ms, 3),
        "tag_ms": round(tag_ms, 3),
        "records": len(rows),
    }


def summarize(rows: list[dict], source_log: Path) -> dict:
    by_stage = defaultdict(list)
    by_engine = defaultdict(list)
    tts_rows = []
    for row in rows:
        stage = str(row.get("stage") or "unknown")
        engine = engine_key(str(row.get("engine") or ""))
        by_stage[stage].append(float(row.get("elapsed_ms") or 0.0))
        by_engine[engine].append(row)
        if "tts" in stage:
            tts_rows.append(row)
    fallback_by_engine = {key: fit_fallback(value) for key, value in by_engine.items()}
    fallback_by_engine.setdefault("default", fit_fallback(tts_rows or rows))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_log": str(source_log),
        "record_count": len(rows),
        "tts_record_count": len(tts_rows),
        "method": "runtime_knn_with_engine_fallback",
        "fallback_by_engine": fallback_by_engine,
        "stage_medians_ms": {key: round(median(values), 3) for key, values in sorted(by_stage.items()) if values},
    }


def write_markdown(model: dict, path: Path) -> None:
    lines = [
        "# CREDO Latency Prediction Model",
        "",
        f"Generated: {model['generated_at']}",
        f"Source records: {model['record_count']}",
        f"TTS records: {model['tts_record_count']}",
        "",
        "## Fallback Coefficients",
        "",
        "| Engine | Records | Intercept ms | ms/char | ms/tag |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for engine, row in sorted(model.get("fallback_by_engine", {}).items()):
        lines.append(
            f"| {engine} | {row.get('records', 0)} | {row.get('intercept_ms', 0)} | {row.get('char_ms', 0)} | {row.get('tag_ms', 0)} |"
        )
    lines.extend(["", "## Stage Medians", "", "| Stage | Median ms |", "| --- | ---: |"])
    for stage, ms in sorted(model.get("stage_medians_ms", {}).items()):
        lines.append(f"| {stage} | {ms} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    rows = read_records(args.log)
    model = summarize(rows, args.log)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(model, args.markdown)
    print(f"Wrote {args.json}")
    print(f"Wrote {args.markdown}")


if __name__ == "__main__":
    main()
