#!/usr/bin/env python3
"""Measure SlowTrack LLM and StyleBERT latency by generated output length bin."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from stylebert_vits2_client import StyleBertVITS2Client  # noqa: E402


BINS = (
    ("10-100자", 10, 100, 70, 96),
    ("100-200자", 100, 200, 150, 96),
    ("200-500자", 200, 500, 330, 160),
    ("500-1000자", 500, 1000, 680, 320),
)


PROMPTS = (
    "A viewer says the professor just sent 'can we take a quick look?' during dinner.",
    "A viewer says their lab notebook looks cursed after three revisions.",
    "A viewer says they want encouragement before a graphics deadline.",
    "A viewer says the render finished but the result looks emotionally expensive.",
    "A viewer says they feel betrayed because a senior reused their lab-meeting idea.",
    "A viewer says they still respect the professor, but the deadline bell is haunting them.",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials-per-bin", type=int, default=30)
    parser.add_argument("--max-attempts-per-bin", type=int, default=120)
    parser.add_argument(
        "--output-dir",
        default="/mnt/c/Users/CGLAB/Desktop/결과 분석/slowtrack_length_benchmark_20260529",
    )
    parser.add_argument("--base-url", default=config.LOCAL_LLM_BASE_URL)
    parser.add_argument("--model", default=config.LOCAL_LLM_MODEL)
    parser.add_argument("--api-key", default=config.LOCAL_LLM_API_KEY)
    parser.add_argument("--timeout", type=float, default=config.LOCAL_LLM_TIMEOUT)
    return parser.parse_args()


def classify_bin(char_len: int) -> str | None:
    for label, low, high, _target, _tokens in BINS:
        if low <= char_len < high:
            return label
    return None


def call_llm(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float,
    prompt: str,
    target_chars: int,
    max_tokens: int,
) -> tuple[str, float]:
    system = (
        "You are Professor's Lab Maid, an English-speaking AI VTuber. "
        "Write only the spoken SlowTrack answer. "
        "Use concrete lab-maid counseling about professors, rendering, deadlines, papers, or experiments. "
        "Do not mention prompts, latency, tests, models, FastTrack, or SlowTrack. "
        "Do not use filler openings such as well, okay, hmm, let me think, or I think. "
        "Do not use markdown, emoji, stage directions, or bullet points. "
        f"Target about {target_chars} English characters."
    )
    user = (
        f"{prompt}\n"
        f"Generate a natural VTuber spoken answer near {target_chars} characters. "
        "Keep the answer self-contained and complete."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.LOCAL_LLM_TEMPERATURE,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("local LLM returned an empty response")
    return text, elapsed_ms


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


def stats(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "n": 0,
            "mean_ms": "",
            "sd_ms": "",
            "median_ms": "",
            "p95_ms": "",
            "min_ms": "",
            "max_ms": "",
        }
    return {
        "n": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "sd_ms": round(statistics.stdev(values), 3) if len(values) > 1 else "",
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 95), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tts = StyleBertVITS2Client()

    rows: list[dict[str, object]] = []
    accepted_by_bin: dict[str, int] = {label: 0 for label, *_rest in BINS}
    attempts_by_bin: dict[str, int] = {label: 0 for label, *_rest in BINS}

    for label, low, high, target_chars, max_tokens in BINS:
        while accepted_by_bin[label] < args.trials_per_bin:
            attempts_by_bin[label] += 1
            if attempts_by_bin[label] > args.max_attempts_per_bin:
                raise RuntimeError(
                    f"Only collected {accepted_by_bin[label]} accepted rows for {label} "
                    f"after {args.max_attempts_per_bin} attempts"
                )
            prompt = PROMPTS[(attempts_by_bin[label] - 1) % len(PROMPTS)]
            text, llm_ms = call_llm(
                base_url=args.base_url,
                api_key=args.api_key,
                model=args.model,
                timeout=args.timeout,
                prompt=prompt,
                target_chars=target_chars,
                max_tokens=max_tokens,
            )
            char_len = len(text)
            actual_bin = classify_bin(char_len)
            if actual_bin != label:
                continue
            started = time.perf_counter()
            audio_path = tts.synthesize_to_file(text, prefix="slowtrack_length_bench")
            tts_ms = (time.perf_counter() - started) * 1000.0
            accepted_by_bin[label] += 1
            row = {
                "trial_index": accepted_by_bin[label],
                "attempt_index": attempts_by_bin[label],
                "target_bin": label,
                "actual_bin": actual_bin,
                "char_len": char_len,
                "LLM_ms": round(llm_ms, 3),
                "TTS_ms": round(tts_ms, 3),
                "Total_ms": round(llm_ms + tts_ms, 3),
                "audio_path": str(audio_path),
                "text": text,
            }
            rows.append(row)
            print(
                f"{label} {accepted_by_bin[label]}/{args.trials_per_bin}: "
                f"chars={char_len} llm={llm_ms:.1f}ms tts={tts_ms:.1f}ms"
            )

    raw_path = output_dir / "slowtrack_length_bin_raw.csv"
    write_csv(raw_path, rows)

    summary_rows: list[dict[str, object]] = []
    compact_rows: list[dict[str, object]] = []
    for label, *_rest in BINS:
        bin_rows = [row for row in rows if row["actual_bin"] == label]
        llm_values = [float(row["LLM_ms"]) for row in bin_rows]
        tts_values = [float(row["TTS_ms"]) for row in bin_rows]
        total_values = [float(row["Total_ms"]) for row in bin_rows]
        for module_label, values in (
            ("SlowTrack LLM 응답 생성", llm_values),
            ("SlowTrack TTS 음성 합성", tts_values),
            ("SlowTrack 합계(LLM+TTS)", total_values),
        ):
            summary_rows.append({"module_label": module_label, "length_bin": label, **stats(values)})
        compact_rows.append(
            {
                "track": "SlowTrack",
                "length_bin": label,
                "n_turns": len(bin_rows),
                "LLM_mean_ms": round(statistics.fmean(llm_values), 1),
                "TTS_mean_ms": round(statistics.fmean(tts_values), 1),
                "Total_mean_ms": round(statistics.fmean(total_values), 1),
            }
        )

    write_csv(output_dir / "SlowTrack_출력길이별_모듈지연시간_상세_filled.csv", summary_rows)
    write_csv(output_dir / "SlowTrack_직관형_mean_ms_filled.csv", compact_rows)

    report = [
        "# SlowTrack Length-Bin Latency Benchmark",
        "",
        f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}",
        f"- Trials per bin: {args.trials_per_bin}",
        f"- LLM endpoint: `{args.base_url}`",
        f"- LLM model: `{args.model}`",
        "- TTS endpoint: StyleBERT-VITS2 from active CREDO config",
        "- Purpose: fill length bins that had no observed SlowTrack rows in the existing paper table.",
        "",
        "## Compact Mean Table",
        "",
        "| track | length_bin | n_turns | LLM_mean_ms | TTS_mean_ms | Total_mean_ms |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in compact_rows:
        report.append(
            f"| {row['track']} | {row['length_bin']} | {row['n_turns']} | "
            f"{row['LLM_mean_ms']} | {row['TTS_mean_ms']} | {row['Total_mean_ms']} |"
        )
    report.extend(
        [
            "",
            "## Interpretation Note",
            "",
            "This is a controlled module benchmark using the active local LLM and StyleBERT-VITS2 endpoints. "
            "It is not a participant-study result and does not replace browser audible-onset timing. "
            "It is appropriate for filling the module-latency table by output length bin.",
            "",
            f"Raw rows: `{raw_path}`",
        ]
    )
    (output_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
