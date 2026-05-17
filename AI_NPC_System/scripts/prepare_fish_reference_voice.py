#!/usr/bin/env python3
"""Prepare a local Fish Speech reference voice from a user-provided wav sample."""

from __future__ import annotations

import argparse
import array
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DEFAULT_SOURCE = ROOT / "VoiceSample" / "VoicePack1_Morning.wav"
DEFAULT_REFERENCE_DIR = PROJECT_ROOT / "vendor" / "fish-speech" / "references" / "credo_voice_sample"
DEFAULT_REFERENCE_TEXT = "Ah, you have woken up? Good morning. Hm? This is breakfast. Though, it is almost noon."


def parse_args() -> argparse.Namespace:
    """Parse reference voice preparation options."""
    parser = argparse.ArgumentParser(description="Create a Fish Speech reference voice directory.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--reference-text", default=DEFAULT_REFERENCE_TEXT)
    parser.add_argument("--start-seconds", type=float, default=2.5)
    parser.add_argument("--duration-seconds", type=float, default=10.0)
    return parser.parse_args()


def read_segment(source: Path, start_seconds: float, duration_seconds: float) -> tuple[wave._wave_params, bytes]:
    """Read a wav segment and return mono PCM bytes."""
    with wave.open(str(source), "rb") as reader:
        params = reader.getparams()
        start_frame = max(0, int(params.framerate * start_seconds))
        frame_count = int(params.framerate * duration_seconds)
        reader.setpos(min(start_frame, params.nframes))
        raw = reader.readframes(min(frame_count, params.nframes - start_frame))

    if params.nchannels > 1:
        raw = mix_to_mono(raw, params.nchannels, params.sampwidth)
        params = params._replace(nchannels=1)

    params = params._replace(nframes=len(raw) // (params.sampwidth * params.nchannels))
    return params, raw


def mix_to_mono(raw: bytes, channels: int, sample_width: int) -> bytes:
    """Average interleaved PCM channels into mono."""
    if channels == 1:
        return raw
    if sample_width != 2:
        raise ValueError(f"Unsupported sample width for mono mix: {sample_width}")

    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()

    mono = array.array("h")
    usable = len(samples) - (len(samples) % channels)
    for index in range(0, usable, channels):
        mono.append(round(sum(samples[index : index + channels]) / channels))

    if sys.byteorder != "little":
        mono.byteswap()
    return mono.tobytes()


def write_reference(reference_dir: Path, params: wave._wave_params, raw: bytes, reference_text: str) -> None:
    """Write sample.wav and sample.lab for Fish Speech."""
    reference_dir.mkdir(parents=True, exist_ok=True)
    wav_path = reference_dir / "sample.wav"
    lab_path = reference_dir / "sample.lab"

    with wave.open(str(wav_path), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(raw)

    lab_path.write_text(reference_text.strip() + "\n", encoding="utf-8")


def main() -> int:
    """Command-line entrypoint."""
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source sample not found: {args.source}")

    params, raw = read_segment(args.source, args.start_seconds, args.duration_seconds)
    write_reference(args.reference_dir, params, raw, args.reference_text)

    seconds = params.nframes / params.framerate if params.framerate else 0.0
    print(f"Wrote Fish Speech reference voice: {args.reference_dir}")
    print(f"sample.wav: {params.nchannels}ch, {params.framerate}Hz, {seconds:.3f}s")
    print(f"sample.lab: {args.reference_text.strip()!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
