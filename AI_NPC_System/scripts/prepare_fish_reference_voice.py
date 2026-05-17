#!/usr/bin/env python3
"""Prepare local Fish Speech reference clips from the CREDO voice sample."""

from __future__ import annotations

import argparse
import array
import shutil
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DEFAULT_SOURCE = ROOT / "VoiceSample" / "VoicePack1_Morning.wav"
DEFAULT_REFERENCE_DIR = PROJECT_ROOT / "vendor" / "fish-speech" / "references" / "credo_voice_sample"
DEFAULT_REFERENCE_SEGMENTS = [
    (
        "sample_01",
        2.40,
        8.20,
        "Ah, you've woken up? Good morning. Hm? This is breakfast. Though, it is almost noon.",
    ),
    (
        "sample_02",
        10.85,
        7.10,
        "Come over here and taste my cooking. So, how is it? Tasty?",
    ),
    (
        "sample_03",
        18.20,
        7.80,
        "Right, right. Of course it is tasty. I included the special ingredient, love, after all.",
    ),
    (
        "sample_04",
        31.30,
        8.80,
        "Are you still asleep? Hurry up and wake up. You are already late, idiot.",
    ),
]


def parse_args() -> argparse.Namespace:
    """Parse reference voice preparation options."""
    parser = argparse.ArgumentParser(description="Create a Fish Speech reference voice directory.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--keep-existing", action="store_true")
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


def write_reference_clip(
    reference_dir: Path,
    stem: str,
    params: wave._wave_params,
    raw: bytes,
    reference_text: str,
) -> float:
    """Write one wav/lab pair for Fish Speech and return clip seconds."""
    reference_dir.mkdir(parents=True, exist_ok=True)
    wav_path = reference_dir / f"{stem}.wav"
    lab_path = reference_dir / f"{stem}.lab"

    with wave.open(str(wav_path), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(raw)

    lab_path.write_text(reference_text.strip() + "\n", encoding="utf-8")
    return params.nframes / params.framerate if params.framerate else 0.0


def main() -> int:
    """Command-line entrypoint."""
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source sample not found: {args.source}")

    if args.reference_dir.exists() and not args.keep_existing:
        shutil.rmtree(args.reference_dir)
    args.reference_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for stem, start_seconds, duration_seconds, reference_text in DEFAULT_REFERENCE_SEGMENTS:
        params, raw = read_segment(args.source, start_seconds, duration_seconds)
        seconds = write_reference_clip(args.reference_dir, stem, params, raw, reference_text)
        written.append((stem, seconds, reference_text))

    translation = args.source.with_name("Translation_for_Voice_Pack_1_Morning.txt")
    if translation.exists():
        shutil.copy2(translation, args.reference_dir / "source_translation.txt")

    print(f"Wrote Fish Speech reference voice: {args.reference_dir}")
    for stem, seconds, reference_text in written:
        print(f"{stem}.wav: {seconds:.3f}s")
        print(f"{stem}.lab: {reference_text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
