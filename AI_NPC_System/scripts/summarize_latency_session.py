#!/usr/bin/env python3
"""Summarize one CREDO module_events.csv latency session."""

from __future__ import annotations

import argparse
import csv
import os
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def as_float(raw: str) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def summarize(values: list[float]) -> dict[str, float | int]:
    clean = [value for value in values if value >= 0]
    if not clean:
        return {
            "n": 0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "p25_ms": 0.0,
            "p75_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }
    return {
        "n": len(clean),
        "mean_ms": round(statistics.fmean(clean), 3),
        "median_ms": round(statistics.median(clean), 3),
        "p25_ms": round(percentile(clean, 25), 3),
        "p75_ms": round(percentile(clean, 75), 3),
        "p95_ms": round(percentile(clean, 95), 3),
        "min_ms": round(min(clean), 3),
        "max_ms": round(max(clean), 3),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def group_summaries(rows: list[dict[str, str]]) -> list[dict[str, str | int | float]]:
    grouped: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        elapsed = as_float(row.get("elapsed_ms", ""))
        if elapsed is None:
            continue
        key = (
            row.get("experiment_run_id", "") or "unlabeled",
            row.get("selection_policy", "") or "unlabeled",
            row.get("scheduling_mode", "") or "unlabeled",
            row.get("module", "") or "unlabeled",
            row.get("stage", "") or "unlabeled",
        )
        grouped[key].append(elapsed)

    output: list[dict[str, str | int | float]] = []
    for key, values in sorted(grouped.items()):
        run_id, mapping, scheduling, module, stage = key
        output.append(
            {
                "experiment_run_id": run_id,
                "selection_policy": mapping,
                "scheduling_mode": scheduling,
                "module": module,
                "stage": stage,
                **summarize(values),
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "experiment_run_id",
        "selection_policy",
        "scheduling_mode",
        "module",
        "stage",
        "n",
        "mean_ms",
        "median_ms",
        "p25_ms",
        "p75_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_markdown(path: Path, session: str, source: Path, rows: list[dict[str, str | int | float]]) -> None:
    lines = [
        f"# Latency Session Summary: {session}",
        "",
        f"- Source: `{source}`",
        f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- Groups: {len(rows)}",
        "",
        "| Run | Mapping | Scheduling | Module | Stage | n | Median ms | p75 ms | p95 ms |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {run} | {mapping} | {sched} | {module} | {stage} | {n} | {median} | {p75} | {p95} |".format(
                run=row.get("experiment_run_id", ""),
                mapping=row.get("selection_policy", ""),
                sched=row.get("scheduling_mode", ""),
                module=row.get("module", ""),
                stage=row.get("stage", ""),
                n=row.get("n", 0),
                median=row.get("median_ms", 0.0),
                p75=row.get("p75_ms", 0.0),
                p95=row.get("p95_ms", 0.0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_stem() -> str:
    return os.getenv("CREDO_LATENCY_LOG_STEM", "").strip() or os.getenv("CREDO_LOG_SESSION_ID", "").strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-stem", default=default_stem(), help="Latency session stem.")
    parser.add_argument(
        "--csv",
        default="",
        help="Explicit module_events.csv path. Overrides --session-stem.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory. Defaults to reports/latency_quantitative_<session>.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stem = args.session_stem.strip()
    if args.csv:
        source = Path(args.csv).expanduser()
        if not source.is_absolute():
            source = ROOT / source
        if not stem:
            stem = source.name.replace(".module_events.csv", "")
    else:
        if not stem:
            raise SystemExit("Missing --session-stem or CREDO_LATENCY_LOG_STEM")
        source = ROOT / "latency_logs" / f"{stem}.module_events.csv"

    rows = read_rows(source)
    summaries = group_summaries(rows)
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else ROOT / "reports" / f"latency_quantitative_{stem}"
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    write_csv(out_dir / "module_summary.csv", summaries)
    write_markdown(out_dir / "summary.md", stem, source, summaries)
    print(f"source={source}")
    print(f"rows={len(rows)}")
    print(f"groups={len(summaries)}")
    print(f"summary={out_dir / 'summary.md'}")
    print(f"module_summary={out_dir / 'module_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
