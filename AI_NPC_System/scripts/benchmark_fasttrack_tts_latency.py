#!/usr/bin/env python3
"""Benchmark CREDO FastTrack TTS latency for short utterances."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from piper_tts_client import PiperTTSClient  # noqa: E402
from stylebert_vits2_client import StyleBertVITS2Client  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure FastTrack TTS latency.")
    parser.add_argument("--engine", choices=("piper_tts", "stylebert_vits2"), default=config.FAST_TRACK_TTS_MODE)
    parser.add_argument("--text", default="That sounds good.")
    parser.add_argument("--emotion", choices=("positive", "negative", "ambiguous", "neutral"), default="positive")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--save-audio", action="store_true")
    return parser.parse_args()


def piper_controls(emotion: str) -> dict[str, float]:
    length_map = {
        "positive": config.PIPER_TTS_LENGTH_SCALE_POSITIVE,
        "negative": config.PIPER_TTS_LENGTH_SCALE_NEGATIVE,
        "ambiguous": config.PIPER_TTS_LENGTH_SCALE_AMBIGUOUS,
        "neutral": config.PIPER_TTS_LENGTH_SCALE_NEUTRAL,
    }
    noise_map = {
        "positive": config.PIPER_TTS_NOISE_SCALE_POSITIVE,
        "negative": config.PIPER_TTS_NOISE_SCALE_NEGATIVE,
        "ambiguous": config.PIPER_TTS_NOISE_SCALE_AMBIGUOUS,
        "neutral": config.PIPER_TTS_NOISE_SCALE_NEUTRAL,
    }
    return {
        "length_scale": length_map.get(emotion, config.PIPER_TTS_LENGTH_SCALE),
        "noise_scale": noise_map.get(emotion, config.PIPER_TTS_NOISE_SCALE),
        "noise_w": config.PIPER_TTS_NOISE_W,
    }


def synthesize(args: argparse.Namespace, index: int) -> tuple[float, Path]:
    started = time.perf_counter()
    if args.engine == "piper_tts":
        client = PiperTTSClient()
        path = client.synthesize_to_file(args.text, prefix=f"bench_piper_{index:02d}", **piper_controls(args.emotion))
    else:
        client = StyleBertVITS2Client()
        style = {
            "positive": config.STYLEBERT_VITS2_STYLE_POSITIVE,
            "negative": config.STYLEBERT_VITS2_STYLE_NEGATIVE,
            "ambiguous": config.STYLEBERT_VITS2_STYLE_AMBIGUOUS,
            "neutral": config.STYLEBERT_VITS2_STYLE_NEUTRAL,
        }.get(args.emotion, config.STYLEBERT_VITS2_STYLE)
        path = client.synthesize_to_file(args.text, prefix=f"bench_stylebert_{index:02d}", style=style)
    return time.perf_counter() - started, path


def main() -> int:
    args = parse_args()
    if args.engine == "piper_tts":
        ready, reason = PiperTTSClient().is_ready()
        if not ready:
            raise SystemExit(reason)

    for index in range(args.warmup):
        elapsed, path = synthesize(args, index)
        print(f"warmup {index + 1}: {elapsed:.3f}s, path={path}")
        if not args.save_audio:
            path.unlink(missing_ok=True)

    elapsed_values: list[float] = []
    for index in range(args.runs):
        elapsed, path = synthesize(args, index)
        elapsed_values.append(elapsed)
        print(f"run {index + 1}: {elapsed:.3f}s, path={path}")
        if not args.save_audio:
            path.unlink(missing_ok=True)

    print(json.dumps({
        "engine": args.engine,
        "text": args.text,
        "runs": args.runs,
        "mean_seconds": round(statistics.mean(elapsed_values), 3),
        "median_seconds": round(statistics.median(elapsed_values), 3),
        "min_seconds": round(min(elapsed_values), 3),
        "max_seconds": round(max(elapsed_values), 3),
        "target_seconds": 1.0,
        "meets_subsecond_target": max(elapsed_values) < 1.0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
