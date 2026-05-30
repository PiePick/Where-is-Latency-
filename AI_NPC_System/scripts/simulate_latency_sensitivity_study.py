#!/usr/bin/env python3
"""Generate a CREDO latency sensitivity simulation dataset from measured logs.

The output is intended for paper planning and quantitative sensitivity analysis.
It is not a replacement for browser audible-onset measurement or participant
study results.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

FASTTRACK_POLICIES = (
    "grounded",
    "emotion_only",
    "response_act_only",
    "neutral_random",
    "slowtrack_only",
)

POLICY_TO_CASE = {
    "grounded": "case_1_grounded_serial",
    "emotion_only": "case_2_emotion_only_serial",
    "response_act_only": "case_3_intent_only_serial",
    "neutral_random": "case_4_neutral_random_serial",
    "slowtrack_only": "case_5_slowtrack_only",
}

SLOWTRACK_LOAD_PROFILES = {
    "current_prompt": {
        "llm_multiplier": 1.0,
        "tts_multiplier": 1.0,
        "description": "Measured current prompt and current response length.",
    },
    "expanded_memory": {
        "llm_multiplier": 1.6,
        "tts_multiplier": 1.1,
        "description": "Longer persona, recent-memory, and audience-summary prompt.",
    },
    "heavy_context": {
        "llm_multiplier": 2.4,
        "tts_multiplier": 1.25,
        "description": "World-state, topic memory, and longer answer generation.",
    },
    "stress_context": {
        "llm_multiplier": 3.4,
        "tts_multiplier": 1.4,
        "description": "Stress-test prompt with dense memory and longer responses.",
    },
}

FRONTEND_PROFILES = {
    "backend_ready": {
        "low_ms": 0.0,
        "mode_ms": 3.0,
        "high_ms": 8.0,
        "description": "Backend readiness only, minimal frontend overhead.",
    },
    "local_browser": {
        "low_ms": 20.0,
        "mode_ms": 45.0,
        "high_ms": 90.0,
        "description": "Local browser dispatch and audio element start overhead.",
    },
    "capture_stress": {
        "low_ms": 80.0,
        "mode_ms": 150.0,
        "high_ms": 280.0,
        "description": "OBS/capture/browser stress overhead sensitivity.",
    },
}

SCENARIO_PROFILES = {
    "chat_only": {
        "donation_turn_probability": 0.0,
        "description": "Only batched chat turns; no donation readout gate.",
    },
    "donation_mix": {
        "donation_turn_probability": 0.45,
        "description": "Broadcast scenario with donation readout gates mixed into chat.",
    },
}


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
        help="Inclusive ISO timestamp for the clean source window.",
    )
    parser.add_argument("--repetitions", type=int, default=500, help="Simulated runs per condition.")
    parser.add_argument("--turns-per-run", type=int, default=8, help="Simulated turns per run.")
    parser.add_argument("--seed", type=int, default=2026052902)
    parser.add_argument(
        "--output-dir",
        default="reports/latency_sensitivity_study_20260529",
        help="Output directory relative to AI_NPC_System or absolute.",
    )
    parser.add_argument(
        "--write-long-module-raw",
        action="store_true",
        help="Also write one row per module per simulated turn. Large file.",
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


def summarize(values: Iterable[float]) -> dict[str, float | int]:
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


def probability(values: list[float], threshold: float, *, op: str = "lt") -> float:
    if not values:
        return 0.0
    if op == "lt":
        count = sum(value < threshold for value in values)
    else:
        count = sum(value > threshold for value in values)
    return round(count / len(values), 5)


def read_source_rows(path: Path, window_start: datetime | None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if window_start is None:
        return rows
    output: list[dict[str, str]] = []
    for row in rows:
        ts = parse_ts(row.get("ts_local", ""))
        if ts is not None and ts >= window_start:
            output.append(row)
    return output


def collect_samples(rows: list[dict[str, str]]) -> dict[str, dict[str, list[float]]]:
    samples: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        case = row.get("experiment_run_id", "")
        stage = row.get("stage", "")
        elapsed = parse_float(row.get("elapsed_ms", ""))
        if not case or not stage or elapsed is None:
            continue
        samples[case][stage].append(elapsed)
        samples["ALL"][stage].append(elapsed)
    return samples


def sample_stage(
    rng: random.Random,
    samples: dict[str, dict[str, list[float]]],
    case: str,
    stage: str,
    *,
    fallback_stage: str | None = None,
) -> float:
    stage_name = fallback_stage or stage
    values = samples.get(case, {}).get(stage_name, [])
    if not values:
        values = samples.get("ALL", {}).get(stage_name, [])
    if not values:
        return 0.0
    return float(rng.choice(values))


def jitter_multiplier(rng: random.Random, base: float, multiplier: float, noise_ratio: float = 0.06) -> float:
    if base <= 0:
        return 0.0
    value = base * multiplier
    sigma = max(1.0, value * noise_ratio)
    return max(0.0, rng.gauss(value, sigma))


def frontend_overhead(rng: random.Random, profile: str) -> float:
    cfg = FRONTEND_PROFILES[profile]
    return rng.triangular(float(cfg["low_ms"]), float(cfg["high_ms"]), float(cfg["mode_ms"]))


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


def simulate(args: argparse.Namespace, samples: dict[str, dict[str, list[float]]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rng = random.Random(args.seed)
    turn_rows: list[dict[str, object]] = []
    module_rows: list[dict[str, object]] = []

    condition_index = 0
    for policy in FASTTRACK_POLICIES:
        case = POLICY_TO_CASE[policy]
        for load_name, load_cfg in SLOWTRACK_LOAD_PROFILES.items():
            for frontend_name in FRONTEND_PROFILES:
                for scenario_name, scenario_cfg in SCENARIO_PROFILES.items():
                    condition_index += 1
                    condition_id = f"c{condition_index:03d}_{policy}_{load_name}_{frontend_name}_{scenario_name}"
                    fasttrack_enabled = policy != "slowtrack_only"
                    for repetition in range(1, args.repetitions + 1):
                        for turn_index in range(1, args.turns_per_run + 1):
                            donation_turn = rng.random() < float(scenario_cfg["donation_turn_probability"])

                            fasttrack_analysis_ms = 0.0
                            emotion_motion_payload_ms = 0.0
                            fasttrack_audio_lookup_ms = 0.0
                            latency_cover_plan_ms = 0.0
                            if fasttrack_enabled:
                                fasttrack_analysis_ms = sample_stage(rng, samples, case, "fast_track_analysis")
                                emotion_motion_payload_ms = sample_stage(rng, samples, case, "emotion_motion_payload")
                                fasttrack_audio_lookup_ms = sample_stage(rng, samples, case, "fast_track_tts_or_cache")
                                latency_cover_plan_ms = sample_stage(rng, samples, case, "latency_cover_plan")

                            donation_emotion_motion_ms = 0.0
                            donation_readout_tts_ms = 0.0
                            if donation_turn:
                                donation_emotion_motion_ms = sample_stage(rng, samples, case, "donation_emotion_motion")
                                donation_readout_tts_ms = sample_stage(rng, samples, case, "donation_readout_tts")

                            slowtrack_llm_base = sample_stage(rng, samples, case, "slow_track_llm")
                            slowtrack_tts_base = sample_stage(rng, samples, case, "slow_track_tts")
                            slowtrack_llm_ms = jitter_multiplier(
                                rng,
                                slowtrack_llm_base,
                                float(load_cfg["llm_multiplier"]),
                            )
                            slowtrack_tts_ms = jitter_multiplier(
                                rng,
                                slowtrack_tts_base,
                                float(load_cfg["tts_multiplier"]),
                            )
                            slowtrack_compute_ms = slowtrack_llm_ms + slowtrack_tts_ms
                            frontend_audio_overhead_ms = frontend_overhead(rng, frontend_name)

                            fasttrack_ready_ms = (
                                fasttrack_analysis_ms
                                + emotion_motion_payload_ms
                                + fasttrack_audio_lookup_ms
                                + latency_cover_plan_ms
                            )
                            if fasttrack_enabled:
                                first_response_ready_ms = fasttrack_ready_ms + frontend_audio_overhead_ms
                                hidden_latency_ms = max(0.0, slowtrack_compute_ms - fasttrack_ready_ms)
                            else:
                                first_response_ready_ms = slowtrack_compute_ms + frontend_audio_overhead_ms
                                hidden_latency_ms = 0.0

                            full_answer_ready_ms = slowtrack_compute_ms + frontend_audio_overhead_ms
                            row = {
                                "condition_id": condition_id,
                                "repetition": repetition,
                                "turn_index": turn_index,
                                "case": case,
                                "policy": policy,
                                "fasttrack_enabled": int(fasttrack_enabled),
                                "slowtrack_load_profile": load_name,
                                "llm_multiplier": load_cfg["llm_multiplier"],
                                "tts_multiplier": load_cfg["tts_multiplier"],
                                "frontend_profile": frontend_name,
                                "scenario_profile": scenario_name,
                                "donation_turn": int(donation_turn),
                                "fasttrack_analysis_ms": round(fasttrack_analysis_ms, 3),
                                "emotion_motion_payload_ms": round(emotion_motion_payload_ms, 3),
                                "fasttrack_audio_lookup_ms": round(fasttrack_audio_lookup_ms, 3),
                                "latency_cover_plan_ms": round(latency_cover_plan_ms, 3),
                                "donation_emotion_motion_ms": round(donation_emotion_motion_ms, 3),
                                "donation_readout_tts_ms": round(donation_readout_tts_ms, 3),
                                "slowtrack_llm_ms": round(slowtrack_llm_ms, 3),
                                "slowtrack_tts_ms": round(slowtrack_tts_ms, 3),
                                "slowtrack_compute_ms": round(slowtrack_compute_ms, 3),
                                "frontend_audio_overhead_ms": round(frontend_audio_overhead_ms, 3),
                                "fasttrack_ready_ms": round(fasttrack_ready_ms, 3),
                                "first_response_ready_ms": round(first_response_ready_ms, 3),
                                "full_answer_ready_ms": round(full_answer_ready_ms, 3),
                                "hidden_latency_ms": round(hidden_latency_ms, 3),
                            }
                            turn_rows.append(row)

                            if args.write_long_module_raw:
                                for module_name in (
                                    "fasttrack_analysis_ms",
                                    "emotion_motion_payload_ms",
                                    "fasttrack_audio_lookup_ms",
                                    "latency_cover_plan_ms",
                                    "donation_emotion_motion_ms",
                                    "donation_readout_tts_ms",
                                    "slowtrack_llm_ms",
                                    "slowtrack_tts_ms",
                                    "frontend_audio_overhead_ms",
                                ):
                                    module_rows.append(
                                        {
                                            "condition_id": condition_id,
                                            "repetition": repetition,
                                            "turn_index": turn_index,
                                            "case": case,
                                            "policy": policy,
                                            "slowtrack_load_profile": load_name,
                                            "frontend_profile": frontend_name,
                                            "scenario_profile": scenario_name,
                                            "donation_turn": int(donation_turn),
                                            "module": module_name.replace("_ms", ""),
                                            "elapsed_ms": row[module_name],
                                        }
                                    )
    return turn_rows, module_rows


def build_condition_summary(turn_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in turn_rows:
        key = (
            str(row["condition_id"]),
            str(row["policy"]),
            str(row["slowtrack_load_profile"]),
            str(row["frontend_profile"]),
            str(row["scenario_profile"]),
        )
        grouped[key].append(row)

    metrics = (
        "first_response_ready_ms",
        "fasttrack_ready_ms",
        "slowtrack_compute_ms",
        "full_answer_ready_ms",
        "hidden_latency_ms",
        "donation_readout_tts_ms",
    )
    output: list[dict[str, object]] = []
    for key, rows in sorted(grouped.items()):
        condition_id, policy, load_profile, frontend_profile, scenario_profile = key
        base = {
            "condition_id": condition_id,
            "policy": policy,
            "slowtrack_load_profile": load_profile,
            "frontend_profile": frontend_profile,
            "scenario_profile": scenario_profile,
            "turns": len(rows),
            "fasttrack_enabled": rows[0]["fasttrack_enabled"],
        }
        for metric in metrics:
            values = [float(row[metric]) for row in rows]
            summary = summarize(values)
            for stat_name, value in summary.items():
                base[f"{metric}_{stat_name}"] = value
            base[f"{metric}_p_lt_100ms"] = probability(values, 100.0, op="lt")
            base[f"{metric}_p_lt_500ms"] = probability(values, 500.0, op="lt")
            base[f"{metric}_p_gt_2000ms"] = probability(values, 2000.0, op="gt")
        output.append(base)
    return output


def build_module_summary(turn_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    module_columns = (
        "fasttrack_analysis_ms",
        "emotion_motion_payload_ms",
        "fasttrack_audio_lookup_ms",
        "latency_cover_plan_ms",
        "donation_emotion_motion_ms",
        "donation_readout_tts_ms",
        "slowtrack_llm_ms",
        "slowtrack_tts_ms",
        "frontend_audio_overhead_ms",
    )
    grouped: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    for row in turn_rows:
        for module in module_columns:
            # Donation module zeros are real for non-donation rows, but they hide
            # generation latency. Summaries include only rows where the module ran.
            value = float(row[module])
            if module.startswith("donation_") and not int(row["donation_turn"]):
                continue
            if not int(row["fasttrack_enabled"]) and module in {
                "fasttrack_analysis_ms",
                "emotion_motion_payload_ms",
                "fasttrack_audio_lookup_ms",
                "latency_cover_plan_ms",
            }:
                continue
            key = (
                str(row["policy"]),
                str(row["slowtrack_load_profile"]),
                str(row["frontend_profile"]),
                str(row["scenario_profile"]),
                module,
            )
            grouped[key].append(value)

    output: list[dict[str, object]] = []
    for key, values in sorted(grouped.items()):
        policy, load_profile, frontend_profile, scenario_profile, module = key
        output.append(
            {
                "policy": policy,
                "slowtrack_load_profile": load_profile,
                "frontend_profile": frontend_profile,
                "scenario_profile": scenario_profile,
                "module": module,
                **summarize(values),
            }
        )
    return output


def write_assumptions(path: Path, args: argparse.Namespace, source: Path, source_rows: int) -> None:
    payload = {
        "source_log": str(source),
        "window_start": args.window_start,
        "source_rows": source_rows,
        "repetitions": args.repetitions,
        "turns_per_run": args.turns_per_run,
        "seed": args.seed,
        "fasttrack_policies": FASTTRACK_POLICIES,
        "slowtrack_load_profiles": SLOWTRACK_LOAD_PROFILES,
        "frontend_profiles": FRONTEND_PROFILES,
        "scenario_profiles": SCENARIO_PROFILES,
        "interpretation_boundary": (
            "Recorded-log empirical bootstrap and sensitivity simulation. "
            "It estimates backend/frontend-readiness latency, not final browser audible onset."
        ),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def pick_rows(rows: list[dict[str, object]], **filters: str) -> list[dict[str, object]]:
    output = rows
    for key, value in filters.items():
        output = [row for row in output if str(row.get(key)) == value]
    return output


def median_of(rows: list[dict[str, object]], metric: str) -> float:
    if not rows:
        return 0.0
    return float(summarize(float(row[metric]) for row in rows)["median_ms"])


def write_report(path: Path, *, args: argparse.Namespace, source: Path, source_rows: int, turn_rows: list[dict[str, object]], condition_summary: list[dict[str, object]]) -> None:
    current_fast = pick_rows(
        turn_rows,
        policy="grounded",
        slowtrack_load_profile="current_prompt",
        frontend_profile="local_browser",
        scenario_profile="donation_mix",
    )
    current_slow = pick_rows(
        turn_rows,
        policy="slowtrack_only",
        slowtrack_load_profile="current_prompt",
        frontend_profile="local_browser",
        scenario_profile="donation_mix",
    )
    heavy_fast = pick_rows(
        turn_rows,
        policy="grounded",
        slowtrack_load_profile="heavy_context",
        frontend_profile="local_browser",
        scenario_profile="donation_mix",
    )
    heavy_slow = pick_rows(
        turn_rows,
        policy="slowtrack_only",
        slowtrack_load_profile="heavy_context",
        frontend_profile="local_browser",
        scenario_profile="donation_mix",
    )
    stress_fast = pick_rows(
        turn_rows,
        policy="grounded",
        slowtrack_load_profile="stress_context",
        frontend_profile="capture_stress",
        scenario_profile="donation_mix",
    )
    stress_slow = pick_rows(
        turn_rows,
        policy="slowtrack_only",
        slowtrack_load_profile="stress_context",
        frontend_profile="capture_stress",
        scenario_profile="donation_mix",
    )

    def result_line(name: str, fast_rows: list[dict[str, object]], slow_rows: list[dict[str, object]]) -> str:
        fast = median_of(fast_rows, "first_response_ready_ms")
        slow = median_of(slow_rows, "first_response_ready_ms")
        improvement = slow - fast
        reduction = 100.0 * (1.0 - fast / slow) if slow else 0.0
        hidden = median_of(fast_rows, "hidden_latency_ms")
        return (
            f"| {name} | {fast:.1f} | {slow:.1f} | {improvement:.1f} | "
            f"{reduction:.1f}% | {hidden:.1f} |"
        )

    lines = [
        "# CREDO Latency Sensitivity Simulation Study",
        "",
        f"- Source log: `{source}`",
        f"- Source window start: `{args.window_start}`",
        f"- Source rows used: `{source_rows}`",
        f"- Simulation conditions: `{len(FASTTRACK_POLICIES) * len(SLOWTRACK_LOAD_PROFILES) * len(FRONTEND_PROFILES) * len(SCENARIO_PROFILES)}`",
        f"- Repetitions per condition: `{args.repetitions}`",
        f"- Turns per repetition: `{args.turns_per_run}`",
        f"- Simulated turn rows: `{len(turn_rows)}`",
        f"- Seed: `{args.seed}`",
        "",
        "## What This Data Means",
        "",
        "This is a sensitivity simulation based on measured module latency distributions. "
        "Each row samples real measured FastTrack analysis, prebuilt audio lookup, SlowTrack LLM, "
        "SlowTrack TTS, donation readout, and frontend overhead distributions, then applies explicit "
        "experimental condition multipliers. It is suitable for paper planning and computational "
        "simulation results, but final perceptual latency still needs browser audible-onset timing.",
        "",
        "## Headline Conditions",
        "",
        "| Scenario | FastTrack median first response ms | SlowTrack-only median first response ms | Median improvement ms | Reduction | Median hidden latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        result_line("Current prompt / local browser / donation mix", current_fast, current_slow),
        result_line("Heavy context / local browser / donation mix", heavy_fast, heavy_slow),
        result_line("Stress context / capture stress / donation mix", stress_fast, stress_slow),
        "",
        "## Generated Files",
        "",
        "| File | Contents |",
        "| --- | --- |",
        "| `simulated_turns_wide.csv` | One row per simulated turn. All module latencies are columns. |",
        "| `condition_summary.csv` | Summary statistics for every condition and metric. |",
        "| `module_summary.csv` | Module-level latency summary by condition. |",
        "| `assumptions.json` | Full factor definitions and simulation assumptions. |",
        "",
        "## Recommended Paper Wording",
        "",
        "Use the phrase `empirical bootstrap sensitivity simulation from recorded module logs`. "
        "Do not describe this as a participant result or browser audible-onset result.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.repetitions < 1 or args.turns_per_run < 1:
        raise SystemExit("--repetitions and --turns-per-run must be positive.")
    source = resolve_path(args.csv)
    output_dir = resolve_path(args.output_dir)
    window_start = parse_ts(args.window_start) if args.window_start else None
    rows = read_source_rows(source, window_start)
    samples = collect_samples(rows)
    turn_rows, module_rows = simulate(args, samples)
    condition_summary = build_condition_summary(turn_rows)
    module_summary = build_module_summary(turn_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "simulated_turns_wide.csv", turn_rows)
    if args.write_long_module_raw:
        write_csv(output_dir / "simulated_modules_long.csv", module_rows)
    write_csv(output_dir / "condition_summary.csv", condition_summary)
    write_csv(output_dir / "module_summary.csv", module_summary)
    write_assumptions(output_dir / "assumptions.json", args, source, len(rows))
    write_report(
        output_dir / "summary.md",
        args=args,
        source=source,
        source_rows=len(rows),
        turn_rows=turn_rows,
        condition_summary=condition_summary,
    )

    print(f"source={source}")
    print(f"source_rows={len(rows)}")
    print(f"simulated_turn_rows={len(turn_rows)}")
    print(f"conditions={len(condition_summary)}")
    print(f"summary={output_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
