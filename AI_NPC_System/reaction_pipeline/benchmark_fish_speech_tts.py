"""Benchmark local Fish Speech TTS latency for short utterances."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_TTS_URL = "http://127.0.0.1:8080/v1/tts"
DEFAULT_HEALTH_URL = "http://127.0.0.1:8080/v1/health"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure Fish Speech /v1/tts latency.")
    parser.add_argument("--url", default=DEFAULT_TTS_URL)
    parser.add_argument("--health-url", default=DEFAULT_HEALTH_URL)
    parser.add_argument("--text", default="[excited] That is really great.")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--format", choices=("wav", "mp3", "opus", "pcm"), default="wav")
    parser.add_argument("--output-dir", type=Path, default=Path("AI_NPC_System/tts_benchmarks"))
    parser.add_argument("--reference-id", default=None)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args()


def health_check(url: str) -> None:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"health check failed: HTTP {response.status}")


def synthesize(args: argparse.Namespace, index: int, save: bool) -> tuple[float, int]:
    payload = {
        "text": args.text,
        "format": args.format,
        "references": [],
        "reference_id": args.reference_id,
        "normalize": True,
        "streaming": False,
        "max_new_tokens": 1024,
        "chunk_length": 200,
        "top_p": 0.8,
        "repetition_penalty": 1.1,
        "temperature": 0.8,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "audio/wav" if args.format == "wav" else "application/octet-stream",
    }
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    req = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=args.timeout) as response:
        audio = response.read()
    elapsed = time.perf_counter() - started

    if save:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out = args.output_dir / f"fish_speech_bench_{index:02d}.{args.format}"
        out.write_bytes(audio)
    return elapsed, len(audio)


def main() -> int:
    args = parse_args()
    health_check(args.health_url)

    for index in range(args.warmup):
        elapsed, size = synthesize(args, index, save=False)
        print(f"warmup {index + 1}: {elapsed:.3f}s, bytes={size}")

    elapsed_values: list[float] = []
    for index in range(args.runs):
        elapsed, size = synthesize(args, index, save=True)
        elapsed_values.append(elapsed)
        print(f"run {index + 1}: {elapsed:.3f}s, bytes={size}")

    print(
        json.dumps(
            {
                "text": args.text,
                "runs": args.runs,
                "mean_seconds": round(statistics.mean(elapsed_values), 3),
                "median_seconds": round(statistics.median(elapsed_values), 3),
                "min_seconds": round(min(elapsed_values), 3),
                "max_seconds": round(max(elapsed_values), 3),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Fish Speech server is not reachable: {exc}") from exc
