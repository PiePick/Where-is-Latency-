#!/usr/bin/env python3
"""Measure Fish Speech latency across text lengths for dynamic cover planning."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from latency_observer import LatencyEvent, LatencyLogger  # noqa: E402
from tts_client import FishSpeechTTSClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser(description="Benchmark Fish Speech by text length.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--lengths", default="20,40,60,80,100,140,180,240")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "latency_logs")
    return parser.parse_args()


def build_text(char_len: int) -> str:
    """Create a stable English sentence near the target length."""
    base = "[cute bright voice] [soft sigh] I hear you, and I will answer carefully with a calm friendly tone. "
    text = base
    while len(text) < char_len:
        text += "That detail matters. "
    return text[:char_len].rstrip(". ,") + "."


def main() -> int:
    args = parse_args()
    lengths = [int(item.strip()) for item in args.lengths.split(",") if item.strip()]
    client = FishSpeechTTSClient()
    if not client.is_healthy():
        raise SystemExit("Fish Speech server is not reachable.")

    logger = LatencyLogger()
    rows = []
    for length in lengths:
        for run in range(1, args.runs + 1):
            text = build_text(length)
            started = time.perf_counter()
            path = client.synthesize_to_file(text, prefix=f"length_{length:03d}")
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            row = {
                "length": length,
                "run": run,
                "elapsed_ms": round(elapsed_ms, 3),
                "audio_path": str(path),
                "text": text,
            }
            rows.append(row)
            logger.log(
                LatencyEvent(
                    stage="fish_speech_length_sweep_tts",
                    elapsed_ms=elapsed_ms,
                    text=text,
                    engine="fish_speech",
                    metadata={"length": length, "run": run, "audio_path": str(path)},
                )
            )
            print(f"length={length} run={run} elapsed_ms={elapsed_ms:.1f}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / f"fish_speech_length_sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["length", "run", "elapsed_ms", "audio_path", "text"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
