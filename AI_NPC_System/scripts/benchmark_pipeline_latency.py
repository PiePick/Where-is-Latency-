#!/usr/bin/env python3
"""Measure CREDO FastTrack, SlowTrack, and TTS latency.

The output separates raw component latency from perceived latency:

- no_cover_first_audio_ms: LLM + TTS, as if the viewer hears nothing first.
- cover_first_audio_ms: FastTrack + cached cover audio availability.
- hidden_latency_ms: latency masked by the immediate cover.

Run with local LLM and Fish Speech servers already started for full results.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import fast_track  # noqa: E402
import slow_track  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


DEFAULT_TEXTS = [
    "I finally passed the exam today!",
    "My little sister stole my money and I am upset.",
    "Wait, did that actually happen?",
    "I am just checking in before the stream starts.",
    "That boss fight was impossible but I won somehow.",
    "I don't know what to say about that.",
]


@dataclass(frozen=True)
class TimedResult:
    """Result and elapsed milliseconds for one measured call."""

    value: Any
    elapsed_ms: float
    error: str | None = None


def now_ms() -> float:
    """Return monotonic milliseconds."""
    return time.perf_counter() * 1000.0


def timed_call(fn, *args, **kwargs) -> TimedResult:
    """Measure a synchronous callable and keep errors in the result row."""
    started = now_ms()
    try:
        return TimedResult(fn(*args, **kwargs), now_ms() - started)
    except Exception as exc:
        return TimedResult(None, now_ms() - started, str(exc))


async def timed_async_call(fn, *args, **kwargs) -> TimedResult:
    """Measure an async callable and keep errors in the result row."""
    started = now_ms()
    try:
        return TimedResult(await fn(*args, **kwargs), now_ms() - started)
    except Exception as exc:
        return TimedResult(None, now_ms() - started, str(exc))


def load_texts(args: argparse.Namespace) -> list[str]:
    """Load benchmark input messages from CLI, file, or defaults."""
    if args.text:
        return [item.strip() for item in args.text if item.strip()]
    if args.text_file:
        lines = args.text_file.read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return DEFAULT_TEXTS


def percentile(values: list[float], pct: float) -> float:
    """Return a simple percentile without requiring numpy."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[index]


def summarize_metric(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    """Summarize one numeric metric across successful rows."""
    values = [
        float(row[key])
        for row in rows
        if isinstance(row.get(key), int | float) and row.get(key) is not None
    ]
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "p95": round(percentile(values, 95), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def build_tts_client(enabled: bool) -> FishSpeechTTSClient | None:
    """Create a non-playing Fish Speech client for benchmark synthesis."""
    if not enabled:
        return None
    cfg = FishSpeechTTSConfig(
        tts_url=config.FISH_SPEECH_TTS_URL,
        health_url=config.FISH_SPEECH_HEALTH_URL,
        api_key=config.FISH_SPEECH_API_KEY,
        reference_id=config.FISH_SPEECH_REFERENCE_ID,
        output_dir=ROOT / "latency_benchmarks" / "audio",
        audio_format=config.FISH_SPEECH_FORMAT,
        timeout=config.FISH_SPEECH_TIMEOUT,
        seed=config.FISH_SPEECH_SEED,
        top_p=config.FISH_SPEECH_TOP_P,
        temperature=config.FISH_SPEECH_TEMPERATURE,
        repetition_penalty=config.FISH_SPEECH_REPETITION_PENALTY,
        max_new_tokens=config.FISH_SPEECH_MAX_NEW_TOKENS,
        chunk_length=config.FISH_SPEECH_CHUNK_LENGTH,
        auto_play=False,
    )
    return FishSpeechTTSClient(cfg)


def measure_tts(client: FishSpeechTTSClient | None, text: str, prefix: str) -> TimedResult:
    """Measure TTS synthesis if a client is enabled."""
    if client is None:
        return TimedResult(None, 0.0, "skipped")
    return timed_call(client.synthesize_to_file, text, prefix=prefix)


async def measure_one(
    *,
    text: str,
    index: int,
    tts_client: FishSpeechTTSClient | None,
    skip_llm: bool,
    measure_live_fast_tts: bool,
) -> dict[str, Any]:
    """Measure one user input through the CREDO latency-cover pipeline."""
    fast = timed_call(fast_track.analyze_and_react, text)
    fast_result = fast.value or {}
    fast_text = fast_result.get("tts_text") or fast_result.get("reaction") or ""
    cache_path = fast_result.get("fast_audio_path")
    cache_hit = bool(fast_result.get("fast_audio_cache_hit") and cache_path and Path(str(cache_path)).exists())

    fast_live_tts = TimedResult(None, 0.0, "skipped")
    if measure_live_fast_tts and fast_text:
        fast_live_tts = measure_tts(tts_client, fast_text, f"bench_fast_{index:03d}")

    if skip_llm:
        slow = TimedResult("", 0.0, "skipped")
    else:
        slow = await timed_async_call(
            slow_track.generate_response,
            text,
            fast_text,
            fast_result.get("strategy"),
            None,
        )

    slow_text = str(slow.value or "").strip()
    slow_tts = measure_tts(tts_client, slow_text, f"bench_slow_{index:03d}") if slow_text else TimedResult(None, 0.0, "no slow text")

    llm_ms = None if slow.error else slow.elapsed_ms
    tts_ms = None if slow_tts.error else slow_tts.elapsed_ms
    live_fast_tts_ms = None if fast_live_tts.error else fast_live_tts.elapsed_ms

    if cache_hit:
        cover_first_audio_ms = fast.elapsed_ms
    elif live_fast_tts_ms is not None:
        cover_first_audio_ms = fast.elapsed_ms + live_fast_tts_ms
    else:
        cover_first_audio_ms = None

    no_cover_first_audio_ms = None
    if llm_ms is not None and tts_ms is not None:
        no_cover_first_audio_ms = llm_ms + tts_ms

    hidden_latency_ms = None
    if no_cover_first_audio_ms is not None and cover_first_audio_ms is not None:
        hidden_latency_ms = max(0.0, no_cover_first_audio_ms - cover_first_audio_ms)

    full_response_ready_ms = None
    if no_cover_first_audio_ms is not None:
        full_response_ready_ms = fast.elapsed_ms + no_cover_first_audio_ms

    return {
        "index": index,
        "input_text": text,
        "emotion": fast_result.get("emotion_label"),
        "reaction_source": fast_result.get("reaction_source"),
        "fast_reaction": fast_text,
        "slow_text": slow_text,
        "fasttrack_ms": round(fast.elapsed_ms, 3),
        "fasttrack_internal_ms": round(float(fast_result.get("latency_ms") or 0.0), 3),
        "bert_ms": round(_parse_seconds(fast_result.get("bert_time")) * 1000.0, 3),
        "spacy_ms": round(_parse_seconds(fast_result.get("spacy_time")) * 1000.0, 3),
        "fast_cache_hit": cache_hit,
        "fast_audio_path": str(cache_path or ""),
        "fast_live_tts_ms": _round_or_none(live_fast_tts_ms),
        "llm_ms": _round_or_none(llm_ms),
        "slow_tts_ms": _round_or_none(tts_ms),
        "cover_first_audio_ms": _round_or_none(cover_first_audio_ms),
        "no_cover_first_audio_ms": _round_or_none(no_cover_first_audio_ms),
        "full_response_ready_ms": _round_or_none(full_response_ready_ms),
        "hidden_latency_ms": _round_or_none(hidden_latency_ms),
        "fast_error": fast.error,
        "fast_live_tts_error": fast_live_tts.error,
        "llm_error": slow.error,
        "slow_tts_error": slow_tts.error,
    }


def _parse_seconds(value: Any) -> float:
    """Parse strings like '0.0123s' from FastTrack metadata."""
    if value is None:
        return 0.0
    raw = str(value).strip().removesuffix("s")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _round_or_none(value: float | None) -> float | None:
    """Round metric values while preserving None."""
    return None if value is None else round(float(value), 3)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write row-level benchmark data."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write summary JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse benchmark options."""
    parser = argparse.ArgumentParser(description="Benchmark CREDO pipeline latency.")
    parser.add_argument("--text", action="append", help="Input text. Can be passed multiple times.")
    parser.add_argument("--text-file", type=Path, help="UTF-8 file with one input per line.")
    parser.add_argument("--runs", type=int, default=3, help="Repeated passes over the input set.")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup FastTrack calls before recording.")
    parser.add_argument("--skip-llm", action="store_true", help="Measure only FastTrack and optional fast TTS.")
    parser.add_argument("--skip-tts", action="store_true", help="Skip Fish Speech synthesis.")
    parser.add_argument(
        "--measure-live-fast-tts",
        action="store_true",
        help="Also synthesize the FastTrack text live to compare cached vs uncached cover latency.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "latency_benchmarks",
        help="Directory for CSV and JSON outputs.",
    )
    return parser.parse_args()


async def main_async() -> int:
    """Run the benchmark."""
    args = parse_args()
    texts = load_texts(args)
    if not texts:
        raise SystemExit("No benchmark texts supplied.")

    for warm_index in range(args.warmup):
        fast_track.analyze_and_react(texts[warm_index % len(texts)])

    tts_client = build_tts_client(not args.skip_tts)
    if tts_client is not None and not tts_client.is_healthy():
        print(f"warning: Fish Speech is not reachable at {config.FISH_SPEECH_HEALTH_URL}", file=sys.stderr)

    rows: list[dict[str, Any]] = []
    sample_index = 0
    for run_index in range(args.runs):
        for text in texts:
            sample_index += 1
            row = await measure_one(
                text=text,
                index=sample_index,
                tts_client=tts_client,
                skip_llm=args.skip_llm,
                measure_live_fast_tts=args.measure_live_fast_tts,
            )
            row["run"] = run_index + 1
            rows.append(row)
            print(
                "sample "
                f"{sample_index}: fast={row['fasttrack_ms']}ms, "
                f"llm={row['llm_ms']}ms, tts={row['slow_tts_ms']}ms, "
                f"cover_first={row['cover_first_audio_ms']}ms, "
                f"no_cover={row['no_cover_first_audio_ms']}ms"
            )

    metrics = [
        "fasttrack_ms",
        "fasttrack_internal_ms",
        "bert_ms",
        "spacy_ms",
        "fast_live_tts_ms",
        "llm_ms",
        "slow_tts_ms",
        "cover_first_audio_ms",
        "no_cover_first_audio_ms",
        "full_response_ready_ms",
        "hidden_latency_ms",
    ]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "profile": os.getenv("CREDO_EXPERIMENT_PROFILE", ""),
            "llm_model": config.LOCAL_LLM_MODEL,
            "llm_base_url": config.LOCAL_LLM_BASE_URL,
            "tts_url": config.FISH_SPEECH_TTS_URL,
            "tts_reference_id": config.FISH_SPEECH_REFERENCE_ID,
            "reaction_db": str(config.REACTION_DB_PATH),
            "audio_cache": str(config.FAST_TRACK_AUDIO_CACHE_PATH),
        },
        "inputs": len(texts),
        "runs": args.runs,
        "rows": len(rows),
        "metrics": {metric: summarize_metric(rows, metric) for metric in metrics},
        "errors": {
            "llm": sum(1 for row in rows if row.get("llm_error") not in (None, "skipped")),
            "slow_tts": sum(1 for row in rows if row.get("slow_tts_error") not in (None, "skipped", "no slow text")),
            "fast_live_tts": sum(1 for row in rows if row.get("fast_live_tts_error") not in (None, "skipped")),
        },
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.output_dir / f"pipeline_latency_{stamp}.csv"
    json_path = args.output_dir / f"pipeline_latency_{stamp}.json"
    write_csv(csv_path, rows)
    write_json(json_path, summary)

    print(json.dumps(summary["metrics"], indent=2))
    print(f"Wrote rows: {csv_path}")
    print(f"Wrote summary: {json_path}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
