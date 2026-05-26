#!/usr/bin/env python3
"""Measure current live modules and simulate CREDO experiment-factor latency.

This benchmark does not drive the browser or claim end-to-end user latency.
It records repeatable module measurements, then estimates the effect of the
current mapping-basis and scheduling factors while keeping the same runtime
pipeline. Dynamic A/B/C FastTrack assembly is intentionally excluded.

Experiment-factor note: the `none` mapping level means "no contextual mapping";
FastTrack stays enabled and the cover text should be sampled from Neutral
candidates without emotion or intent lookup.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fast_track  # noqa: E402
import slow_track  # noqa: E402
import config  # noqa: E402
from stylebert_vits2_client import StyleBertVITS2Client  # noqa: E402


FAST_PROMPTS = [
    "I passed the exam today and I am really happy!",
    "That update went badly and I feel frustrated.",
    "Wait, what does that mean?",
    "I am here for today's stream.",
]
TTS_TEXT = {
    "language_fasttrack_tts": "That sounds great, tell me more!",
    "slowtrack_tts": "I was thinking about that too, and chat might have a fun answer for us today.",
}
MAPPING_POLICIES = ("grounded", "emotion_only", "response_act_only", "none")
SCHEDULING_MODES = ("parallel", "serial")


@dataclass(frozen=True)
class Metric:
    name: str
    median_ms: float
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure CREDO modules and simulate experiment-factor latency.")
    parser.add_argument("--runs", type=int, default=5, help="Repeat count for measured modules.")
    parser.add_argument("--trials", type=int, default=100, help="Simulated turns per factor condition.")
    parser.add_argument("--measure-tts", action="store_true", help="Run live configured TTS synthesis measurements.")
    parser.add_argument("--measure-edge", action="store_true", help="Deprecated alias for --measure-tts.")
    parser.add_argument("--measure-fasttrack", action="store_true", help="Run FastTrack classifier measurements.")
    parser.add_argument("--measure-llm", action="store_true", help="Run local SlowTrack LLM measurements.")
    parser.add_argument("--slow-llm-ms", type=float, default=1500.0, help="LLM assumption if not measured.")
    parser.add_argument("--slow-audio-ms", type=float, default=4200.0, help="Playback overlap window assumption if duration is unavailable.")
    parser.add_argument(
        "--nonverbal-dispatch-ms",
        type=float,
        default=0.0,
        help="Measured prebuilt Fish interjection payload/dispatch delay, when available.",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "latency_factor_benchmark_2026-05-26")
    return parser.parse_args()


def measure_calls(name: str, runs: int, callback: Callable[[int], object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(runs):
        started = time.perf_counter()
        error = ""
        try:
            result = callback(index)
        except Exception as exc:
            result = None
            error = str(exc)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        rows.append({"module": name, "run": index + 1, "elapsed_ms": round(elapsed_ms, 3), "error": error})
        if isinstance(result, Path):
            rows[-1]["output_path"] = str(result)
    return rows


def measure_fasttrack(runs: int) -> list[dict[str, object]]:
    fast_track.analyze_and_react(FAST_PROMPTS[0])
    return measure_calls(
        "fasttrack_analysis",
        runs,
        lambda index: fast_track.analyze_and_react(FAST_PROMPTS[index % len(FAST_PROMPTS)]),
    )


def measure_tts(runs: int) -> tuple[list[dict[str, object]], float | None]:
    client = StyleBertVITS2Client()
    rows: list[dict[str, object]] = []
    slow_duration_ms: float | None = None
    for module, text in TTS_TEXT.items():
        module_rows = measure_calls(
            module,
            runs,
            lambda index, key=module, spoken=text: client.synthesize_to_file(spoken, prefix=f"bench_{key}_{index + 1:02d}"),
        )
        rows.extend(module_rows)
        if module == "slowtrack_tts":
            paths = [Path(str(row["output_path"])) for row in module_rows if row.get("output_path") and not row["error"]]
            if paths:
                slow_duration_ms = probe_audio_duration_ms(paths[-1])
    return rows, slow_duration_ms


async def _one_slowtrack_call(index: int) -> str:
    return await slow_track.generate_response(
        FAST_PROMPTS[index % len(FAST_PROMPTS)],
        "I hear you.",
        "benchmark",
        None,
        mode="vtuber_monologue",
        max_tokens=48,
    )


def measure_llm(runs: int) -> list[dict[str, object]]:
    try:
        with urllib.request.urlopen(
            f"{config.LOCAL_LLM_BASE_URL.rstrip('/')}/models", timeout=2.0
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"health returned HTTP {response.status}")
    except Exception as exc:
        return [
            {
                "module": "slowtrack_llm",
                "run": 0,
                "elapsed_ms": 0.0,
                "error": f"LLM endpoint unavailable; assumption used: {exc}",
            }
        ]
    return measure_calls("slowtrack_llm", runs, lambda index: asyncio.run(_one_slowtrack_call(index)))


def probe_audio_duration_ms(path: Path) -> float | None:
    try:
        output = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            text=True,
            timeout=5,
        )
        return round(float(output.strip()) * 1000.0, 3)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return None


def metric(rows: list[dict[str, object]], name: str, fallback: float) -> Metric:
    measured = [float(row["elapsed_ms"]) for row in rows if row["module"] == name and not row.get("error")]
    if measured:
        return Metric(name, round(statistics.median(measured), 3), f"measured n={len(measured)}")
    return Metric(name, float(fallback), "assumption")


def jitter(rng: random.Random, metric_ms: float) -> float:
    return max(0.0, rng.gauss(metric_ms, max(1.0, metric_ms * 0.08)))


def simulate(metrics: dict[str, Metric], trials: int, slow_audio_ms: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rng = random.Random(20260526)
    for mapping_policy in MAPPING_POLICIES:
        for scheduling_mode in SCHEDULING_MODES:
            first_values: list[float] = []
            slow_ready_values: list[float] = []
            next_wait_values: list[float] = []
            for _ in range(trials):
                analysis_ms = jitter(rng, metrics["fasttrack_analysis"].median_ms)
                nonverbal_ms = jitter(rng, metrics["nonverbal_dispatch"].median_ms)
                llm_ms = jitter(rng, metrics["slowtrack_llm"].median_ms)
                slow_tts_ms = jitter(rng, metrics["slowtrack_tts"].median_ms)
                fasttrack_enabled = True
                slow_ready_ms = analysis_ms + llm_ms + slow_tts_ms
                first_audio_ms = analysis_ms + nonverbal_ms
                if scheduling_mode == "parallel":
                    next_wait_ms = max(0.0, slow_ready_ms - slow_audio_ms)
                else:
                    next_wait_ms = slow_ready_ms
                first_values.append(first_audio_ms)
                slow_ready_values.append(slow_ready_ms)
                next_wait_values.append(next_wait_ms)
            rows.append({
                "component_mode": "both",
                "mapping_level": mapping_policy,
                "selection_policy": mapping_policy if mapping_policy != "none" else "neutral_random",
                "scheduling_mode": scheduling_mode,
                "trials": trials,
                "first_audio_median_ms": round(statistics.median(first_values), 3),
                "slow_ready_median_ms": round(statistics.median(slow_ready_values), 3),
                "next_turn_wait_median_ms": round(statistics.median(next_wait_values), 3),
            })
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for name in row:
            if name not in fieldnames:
                fieldnames.append(name)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    path: Path,
    metrics: dict[str, Metric],
    simulation: list[dict[str, object]],
    *,
    slow_audio_ms: float,
    trials: int,
) -> None:
    lines = [
        "# CREDO Low-Latency Factor Benchmark",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Live language TTS: `{config.FAST_TRACK_TTS_MODE}` / `{config.STYLEBERT_VITS2_MODEL_NAME}`",
        "",
        "## Module Baselines",
        "",
        "| Module | Median ms | Source |",
        "| --- | ---: | --- |",
    ]
    for item in metrics.values():
        lines.append(f"| `{item.name}` | {item.median_ms:.3f} | {item.source} |")
    lines.extend([
        f"| `slowtrack_playback_window` | {slow_audio_ms:.3f} | measured audio duration or explicit assumption |",
        "",
        "## Simulation",
        "",
        f"Each row uses `{trials}` deterministic jittered trials. Mapping basis is expected to affect fit, not latency.",
        "For `none`, FastTrack remains enabled and the cover text is sampled from Neutral candidates without contextual lookup.",
        "",
        "| FastTrack | Mapping level | Runtime selection | Scheduling | First audio median ms | Slow ready median ms | Next wait median ms |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ])
    for row in simulation:
        lines.append(
            f"| {row['component_mode']} | {row.get('mapping_level', row['selection_policy'])} | "
            f"{row['selection_policy']} | {row['scheduling_mode']} | "
            f"{row['first_audio_median_ms']} | {row['slow_ready_median_ms']} | {row['next_turn_wait_median_ms']} |"
        )
    lines.extend([
        "",
        "## Interpretation Boundary",
        "",
        "This is a module benchmark plus scheduling simulation, not a participant trial or browser playback measurement.",
        "The nonverbal value is prebuilt interjection audio dispatch, not synthesis time; browser playback smoke is required for audible-onset claims.",
        "Final study results must be calculated from live `latency_logs/module_events.csv` rows labeled with the active factor levels.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.runs < 1 or args.trials < 1:
        raise SystemExit("--runs and --trials must be positive.")
    measured_rows: list[dict[str, object]] = []
    slow_audio_ms: float | None = None
    if args.measure_fasttrack:
        measured_rows.extend(measure_fasttrack(args.runs))
    if args.measure_tts or args.measure_edge:
        tts_rows, slow_audio_ms = measure_tts(args.runs)
        measured_rows.extend(tts_rows)
    if args.measure_llm:
        measured_rows.extend(measure_llm(args.runs))

    metrics = {
        "fasttrack_analysis": metric(measured_rows, "fasttrack_analysis", 80.0),
        "nonverbal_dispatch": Metric(
            "nonverbal_dispatch",
            float(args.nonverbal_dispatch_ms),
            "prebuilt interjection audio; pass measured route/dispatch delay when available",
        ),
        "language_fasttrack_tts": metric(measured_rows, "language_fasttrack_tts", 1200.0),
        "slowtrack_llm": metric(measured_rows, "slowtrack_llm", args.slow_llm_ms),
        "slowtrack_tts": metric(measured_rows, "slowtrack_tts", 1800.0),
    }
    playback_ms = slow_audio_ms if slow_audio_ms is not None else args.slow_audio_ms
    simulation = simulate(metrics, args.trials, playback_ms)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "module_measurements.csv", measured_rows)
    write_csv(args.output_dir / "factor_simulation.csv", simulation)
    write_report(
        args.output_dir / "summary.md",
        metrics,
        simulation,
        slow_audio_ms=playback_ms,
        trials=args.trials,
    )
    (args.output_dir / "baselines.json").write_text(
        json.dumps(
            {
                "language_tts": config.FAST_TRACK_TTS_MODE,
                "stylebert_model": config.STYLEBERT_VITS2_MODEL_NAME,
                "metrics": {name: item.__dict__ for name, item in metrics.items()},
                "slowtrack_playback_window_ms": playback_ms,
                "measured_rows": len(measured_rows),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote benchmark outputs: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
