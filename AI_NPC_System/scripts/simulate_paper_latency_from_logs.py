#!/usr/bin/env python3
"""Bootstrap CREDO paper latency metrics from recorded module logs.

This does not drive the browser. It resamples measured module latencies from a
clean log window and estimates full-case distributions for the current paper
conditions.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CASES = (
    "case_1_grounded_serial",
    "case_2_emotion_only_serial",
    "case_3_intent_only_serial",
    "case_4_neutral_random_serial",
    "case_5_slowtrack_only",
)
FASTTRACK_CASES = set(CASES[:-1])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default="latency_logs/paper_latency_20260529_000308.module_events.csv",
        help="module_events.csv path relative to AI_NPC_System or absolute.",
    )
    parser.add_argument(
        "--window-start",
        default="2026-05-29T03:36:00+09:00",
        help="Inclusive ISO timestamp for the clean analysis window.",
    )
    parser.add_argument("--runs", type=int, default=5000, help="Simulated full experiment repetitions.")
    parser.add_argument("--turns-per-case", type=int, default=8, help="Simulated VTuber turns per case.")
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument(
        "--output-dir",
        default="reports/latency_simulation_paper_20260529",
        help="Output directory relative to AI_NPC_System or absolute.",
    )
    return parser.parse_args()


def resolve_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == ROOT.name:
        return ROOT.parent.joinpath(path)
    return ROOT / path


def parse_float(raw: str) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def read_rows(path: Path, window_start: datetime | None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if window_start is None:
        return rows
    clean: list[dict[str, str]] = []
    for row in rows:
        ts = parse_ts(row.get("ts_local", ""))
        if ts is not None and ts >= window_start:
            clean.append(row)
    return clean


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


def collect_stage_samples(rows: list[dict[str, str]]) -> dict[str, dict[str, list[float]]]:
    by_case_stage: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        case = row.get("experiment_run_id", "")
        stage = row.get("stage", "")
        elapsed = parse_float(row.get("elapsed_ms", ""))
        if case and stage and elapsed is not None:
            by_case_stage[case][stage].append(elapsed)
    return by_case_stage


def collect_turn_samples(rows: list[dict[str, str]]) -> dict[str, dict[str, list[float]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        turn_id = row.get("turn_id", "")
        if turn_id:
            grouped[turn_id].append(row)

    samples: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for turn_rows in grouped.values():
        cases = [row.get("experiment_run_id", "") for row in turn_rows if row.get("experiment_run_id")]
        if not cases:
            continue
        case = cases[0]
        stage_sums: dict[str, float] = defaultdict(float)
        for row in turn_rows:
            stage = row.get("stage", "")
            elapsed = parse_float(row.get("elapsed_ms", ""))
            if stage and elapsed is not None:
                stage_sums[stage] += elapsed

        if "fast_track_analysis" in stage_sums and "fast_track_tts_or_cache" in stage_sums:
            fasttrack_ready = (
                stage_sums.get("fast_track_analysis", 0.0)
                + stage_sums.get("emotion_motion_payload", 0.0)
                + stage_sums.get("fast_track_tts_or_cache", 0.0)
                + stage_sums.get("latency_cover_plan", 0.0)
            )
            samples[case]["fasttrack_ready_ms"].append(fasttrack_ready)

        if "slow_track_llm" in stage_sums and "slow_track_tts" in stage_sums:
            slowtrack_compute = stage_sums.get("slow_track_llm", 0.0) + stage_sums.get("slow_track_tts", 0.0)
            samples[case]["slowtrack_compute_ms"].append(slowtrack_compute)

        if stage_sums.get("turn_total", 0.0) > 0:
            samples[case]["turn_total_logged_ms"].append(stage_sums["turn_total"])

    return samples


def all_values(samples: dict[str, dict[str, list[float]]], metric: str, cases: tuple[str, ...] = CASES) -> list[float]:
    values: list[float] = []
    for case in cases:
        values.extend(samples.get(case, {}).get(metric, []))
    return values


def choose_sample(
    rng: random.Random,
    samples: dict[str, dict[str, list[float]]],
    case: str,
    metric: str,
    fallback_cases: tuple[str, ...] = CASES,
) -> float:
    values = samples.get(case, {}).get(metric, [])
    if not values:
        values = all_values(samples, metric, fallback_cases)
    if not values:
        raise RuntimeError(f"No measured samples for {case}:{metric}")
    return rng.choice(values)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def probability(values: list[float], threshold: float, *, op: str = "lt") -> float:
    if not values:
        return 0.0
    if op == "lt":
        count = sum(value < threshold for value in values)
    else:
        count = sum(value > threshold for value in values)
    return round(count / len(values), 4)


def simulate(samples: dict[str, dict[str, list[float]]], *, runs: int, turns_per_case: int, seed: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rng = random.Random(seed)
    turn_rows: list[dict[str, object]] = []
    run_rows: list[dict[str, object]] = []

    for run_index in range(1, runs + 1):
        for case in CASES:
            first_ready_values: list[float] = []
            slow_compute_values: list[float] = []
            hidden_values: list[float] = []
            for turn_index in range(1, turns_per_case + 1):
                slow_compute = choose_sample(rng, samples, case, "slowtrack_compute_ms")
                if case in FASTTRACK_CASES:
                    fasttrack_ready = choose_sample(rng, samples, case, "fasttrack_ready_ms", tuple(FASTTRACK_CASES))
                    first_ready = fasttrack_ready
                    hidden_latency = max(0.0, slow_compute - fasttrack_ready)
                    condition = "fasttrack_on"
                else:
                    fasttrack_ready = 0.0
                    first_ready = slow_compute
                    hidden_latency = 0.0
                    condition = "slowtrack_only"

                first_ready_values.append(first_ready)
                slow_compute_values.append(slow_compute)
                hidden_values.append(hidden_latency)
                turn_rows.append(
                    {
                        "simulation_run": run_index,
                        "turn_index": turn_index,
                        "case": case,
                        "condition": condition,
                        "first_response_ready_ms": round(first_ready, 3),
                        "fasttrack_ready_ms": round(fasttrack_ready, 3),
                        "slowtrack_compute_ms": round(slow_compute, 3),
                        "hidden_latency_ms": round(hidden_latency, 3),
                    }
                )

            run_rows.append(
                {
                    "simulation_run": run_index,
                    "case": case,
                    "condition": "fasttrack_on" if case in FASTTRACK_CASES else "slowtrack_only",
                    "turns": turns_per_case,
                    "mean_first_response_ready_ms": round(statistics.fmean(first_ready_values), 3),
                    "median_first_response_ready_ms": round(statistics.median(first_ready_values), 3),
                    "mean_slowtrack_compute_ms": round(statistics.fmean(slow_compute_values), 3),
                    "median_slowtrack_compute_ms": round(statistics.median(slow_compute_values), 3),
                    "mean_hidden_latency_ms": round(statistics.fmean(hidden_values), 3),
                    "median_hidden_latency_ms": round(statistics.median(hidden_values), 3),
                }
            )

    return turn_rows, run_rows


def metric_rows_from_turns(turn_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in turn_rows:
        case = str(row["case"])
        condition = str(row["condition"])
        for metric in ("first_response_ready_ms", "slowtrack_compute_ms", "hidden_latency_ms"):
            grouped[(case, condition, metric)].append(float(row[metric]))

    output: list[dict[str, object]] = []
    for (case, condition, metric), values in sorted(grouped.items()):
        summary = summarize(values)
        output.append(
            {
                "case": case,
                "condition": condition,
                "metric": metric,
                **summary,
                "p_lt_100ms": probability(values, 100.0, op="lt"),
                "p_lt_500ms": probability(values, 500.0, op="lt"),
                "p_lt_1000ms": probability(values, 1000.0, op="lt"),
                "p_gt_2000ms": probability(values, 2000.0, op="gt"),
            }
        )

    for condition in ("fasttrack_on", "slowtrack_only"):
        condition_rows = [row for row in turn_rows if row["condition"] == condition]
        for metric in ("first_response_ready_ms", "slowtrack_compute_ms", "hidden_latency_ms"):
            values = [float(row[metric]) for row in condition_rows]
            summary = summarize(values)
            output.append(
                {
                    "case": "ALL_FASTTRACK_CASES" if condition == "fasttrack_on" else "ALL_SLOWTRACK_ONLY",
                    "condition": condition,
                    "metric": metric,
                    **summary,
                    "p_lt_100ms": probability(values, 100.0, op="lt"),
                    "p_lt_500ms": probability(values, 500.0, op="lt"),
                    "p_lt_1000ms": probability(values, 1000.0, op="lt"),
                    "p_gt_2000ms": probability(values, 2000.0, op="gt"),
                }
            )
    return output


def metric_rows_from_runs(run_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in run_rows:
        case = str(row["case"])
        condition = str(row["condition"])
        for metric in (
            "mean_first_response_ready_ms",
            "median_first_response_ready_ms",
            "mean_slowtrack_compute_ms",
            "median_slowtrack_compute_ms",
            "mean_hidden_latency_ms",
            "median_hidden_latency_ms",
        ):
            grouped[(case, condition, metric)].append(float(row[metric]))
    output: list[dict[str, object]] = []
    for (case, condition, metric), values in sorted(grouped.items()):
        output.append({"case": case, "condition": condition, "metric": metric, **summarize(values)})
    return output


def write_report(
    path: Path,
    *,
    source: Path,
    window_start: str,
    source_rows: int,
    turn_rows: list[dict[str, object]],
    turn_metrics: list[dict[str, object]],
    run_metrics: list[dict[str, object]],
    runs: int,
    turns_per_case: int,
    seed: int,
) -> None:
    metric_lookup = {
        (str(row["case"]), str(row["metric"])): row
        for row in turn_metrics
    }
    fast = metric_lookup[("ALL_FASTTRACK_CASES", "first_response_ready_ms")]
    slow = metric_lookup[("ALL_SLOWTRACK_ONLY", "first_response_ready_ms")]
    hidden = metric_lookup[("ALL_FASTTRACK_CASES", "hidden_latency_ms")]
    improvement = float(slow["median_ms"]) - float(fast["median_ms"])
    reduction = 100.0 * (1.0 - (float(fast["median_ms"]) / float(slow["median_ms"])))
    ratio = float(slow["median_ms"]) / max(float(fast["median_ms"]), 1e-9)

    lines = [
        "# Simulated Paper Latency From Recorded Logs",
        "",
        f"- Source log: `{source}`",
        f"- Window start: `{window_start}`",
        f"- Source rows used: `{source_rows}`",
        f"- Simulation: `{runs}` full experiment repetitions x `{turns_per_case}` turns per case.",
        f"- Seed: `{seed}`",
        "- Method: empirical bootstrap resampling from measured turn-level module latencies.",
        "",
        "## Core Simulated Result",
        "",
        "| Metric | n simulated turns | Median ms | Mean ms | p75 ms | p95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| FastTrack first-response readiness | {fast['n']} | {fast['median_ms']} | {fast['mean_ms']} | {fast['p75_ms']} | {fast['p95_ms']} |",
        f"| SlowTrack-only first-response readiness | {slow['n']} | {slow['median_ms']} | {slow['mean_ms']} | {slow['p75_ms']} | {slow['p95_ms']} |",
        f"| Hidden latency by FastTrack | {hidden['n']} | {hidden['median_ms']} | {hidden['mean_ms']} | {hidden['p75_ms']} | {hidden['p95_ms']} |",
        "",
        f"- Simulated median improvement: `{improvement:.1f} ms`.",
        f"- Simulated relative reduction: `{reduction:.1f}%`.",
        f"- SlowTrack-only first response is `{ratio:.1f}x` slower by median.",
        f"- P(FastTrack first response < 100 ms): `{float(fast['p_lt_100ms']) * 100:.1f}%`.",
        f"- P(SlowTrack-only first response > 2000 ms): `{float(slow['p_gt_2000ms']) * 100:.1f}%`.",
        "",
        "## Case-Level Turn Distribution",
        "",
        "| Case | Metric | n | Median ms | Mean ms | p75 ms | p95 ms | P<100ms | P>2000ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in turn_metrics:
        case = str(row["case"])
        if case.startswith("ALL_"):
            continue
        metric = str(row["metric"])
        if metric not in {"first_response_ready_ms", "hidden_latency_ms", "slowtrack_compute_ms"}:
            continue
        lines.append(
            f"| {case} | {metric} | {row['n']} | {row['median_ms']} | {row['mean_ms']} | "
            f"{row['p75_ms']} | {row['p95_ms']} | {float(row['p_lt_100ms']) * 100:.1f}% | "
            f"{float(row['p_gt_2000ms']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Run-Level Stability",
            "",
            "Each simulated run is one full case playback with the configured number of turns. "
            "These rows estimate how stable the case-level average would be if the scenario were replayed many times.",
            "",
            "| Case | Metric | n runs | Median ms | p25 ms | p75 ms | p95 ms |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in run_metrics:
        metric = str(row["metric"])
        if metric not in {"mean_first_response_ready_ms", "mean_hidden_latency_ms"}:
            continue
        lines.append(
            f"| {row['case']} | {metric} | {row['n']} | {row['median_ms']} | "
            f"{row['p25_ms']} | {row['p75_ms']} | {row['p95_ms']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This is a recorded-log bootstrap simulation, not a new browser playback run.",
            "- It estimates processing-side first-response readiness. It does not replace frontend audible-onset measurement.",
            "- Use this for methods/results planning; use a browser `audio_play_started` log for final perceptual latency claims.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.runs < 1 or args.turns_per_case < 1:
        raise SystemExit("--runs and --turns-per-case must be positive")

    source = resolve_path(args.csv)
    output_dir = resolve_path(args.output_dir)
    window_start = parse_ts(args.window_start) if args.window_start else None
    rows = read_rows(source, window_start)
    samples = collect_turn_samples(rows)

    missing = []
    for case in CASES:
        if case in FASTTRACK_CASES and not samples.get(case, {}).get("fasttrack_ready_ms"):
            missing.append(f"{case}:fasttrack_ready_ms")
        if not samples.get(case, {}).get("slowtrack_compute_ms"):
            missing.append(f"{case}:slowtrack_compute_ms")
    if missing:
        raise SystemExit(f"Missing required measured samples: {', '.join(missing)}")

    turn_rows, run_rows = simulate(
        samples,
        runs=args.runs,
        turns_per_case=args.turns_per_case,
        seed=args.seed,
    )
    turn_metrics = metric_rows_from_turns(turn_rows)
    run_metrics = metric_rows_from_runs(run_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "simulation_turn_samples.csv", turn_rows)
    write_csv(output_dir / "simulation_run_samples.csv", run_rows)
    write_csv(output_dir / "simulation_turn_summary.csv", turn_metrics)
    write_csv(output_dir / "simulation_run_summary.csv", run_metrics)
    write_report(
        output_dir / "summary.md",
        source=source,
        window_start=args.window_start,
        source_rows=len(rows),
        turn_rows=turn_rows,
        turn_metrics=turn_metrics,
        run_metrics=run_metrics,
        runs=args.runs,
        turns_per_case=args.turns_per_case,
        seed=args.seed,
    )

    print(f"source={source}")
    print(f"source_rows={len(rows)}")
    print(f"simulated_turn_rows={len(turn_rows)}")
    print(f"summary={output_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
