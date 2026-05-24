#!/usr/bin/env python3
"""Generate extreme Fish Speech nonverbal reaction audio by emotion."""

from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from latency_observer import LatencyEvent, LatencyLogger  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


OUTPUT_DIR = ROOT / "expressive_audio_pool"

PROMPTS = {
    "positive": [
        ("pos_laugh_01", ["[laughing]", "[chuckle]", "[delight]", "[excited]", "[cute excited tone]"], "ha-ha!"),
        ("pos_laugh_02", ["[chuckle]", "[laughing]", "[excited]", "[inhale]", "[delight]"], "hee-hee!"),
        ("pos_laugh_03", ["[laughing]", "[excited]", "[emphasis]", "[delight]", "[chuckle]"], "ahaha!"),
        ("pos_laugh_04", ["[chuckle]", "[delight]", "[soft sigh]", "[excited]", "[cute excited tone]"], "oh!"),
        ("pos_laugh_05", ["[laughing]", "[chuckle]", "[delight]", "[inhale]", "[excited]"], "haha!"),
        ("pos_laugh_06", ["[delight]", "[excited]", "[chuckle]", "[laughing]", "[emphasis]"], "yay!"),
        ("pos_laugh_07", ["[chuckle]", "[emphasis]", "[excited]", "[delight]", "[short pause]"], "nice!"),
        ("pos_laugh_08", ["[laughing]", "[chuckle]", "[inhale]", "[exhale]", "[delight]"], "ha, perfect."),
        ("pos_laugh_09", ["[excited]", "[cute excited tone]", "[laughing]", "[chuckle]", "[emphasis]"], "let's go!"),
        ("pos_laugh_10", ["[delight]", "[laughing]", "[soft sigh]", "[chuckle]", "[excited]"], "aw!"),
    ],
    "negative": [
        ("neg_sigh_01", ["[sigh]", "[sad sigh]", "[exhale]", "[pause]", "[whisper]"], "oh."),
        ("neg_sigh_02", ["[sigh]", "[sad sigh]", "[soft sigh]", "[exhale]", "[pause]"], "mm."),
        ("neg_sigh_03", ["[sigh]", "[emphasis]", "[exhale]", "[short pause]", "[sad sigh]"], "ugh."),
        ("neg_sigh_04", ["[sigh]", "[short pause]", "[exhale]", "[pause]", "[soft sigh]"], "ah."),
        ("neg_sigh_05", ["[sad sigh]", "[whisper]", "[soft sigh]", "[pause]", "[exhale]"], "hm."),
        ("neg_sigh_06", ["[emphasis]", "[sigh]", "[short pause]", "[exhale]", "[sad sigh]"], "ugh."),
        ("neg_sigh_07", ["[sad sigh]", "[soft sigh]", "[pause]", "[exhale]", "[whisper]"], "ah."),
        ("neg_sigh_08", ["[sigh]", "[inhale]", "[exhale]", "[emphasis]", "[short pause]"], "mm."),
        ("neg_sigh_09", ["[sad sigh]", "[exhale]", "[whisper]", "[pause]", "[soft sigh]"], "hm."),
        ("neg_sigh_10", ["[sigh]", "[short pause]", "[emphasis]", "[exhale]", "[sad sigh]"], "ugh?"),
    ],
    "ambiguous": [
        ("amb_gasp_01", ["[surprised]", "[shocked]", "[inhale]", "[short pause]", "[whisper]"], "huh?"),
        ("amb_gasp_02", ["[surprised]", "[inhale]", "[shocked]", "[pause]", "[short pause]"], "what?"),
        ("amb_gasp_03", ["[shocked]", "[surprised]", "[emphasis]", "[inhale]", "[short pause]"], "wait."),
        ("amb_gasp_04", ["[surprised]", "[soft sigh]", "[whisper]", "[short pause]", "[inhale]"], "really?"),
        ("amb_gasp_05", ["[shocked]", "[inhale]", "[surprised]", "[short pause]", "[emphasis]"], "oh?"),
        ("amb_gasp_06", ["[surprised]", "[short pause]", "[inhale]", "[whisper]", "[shocked]"], "how?"),
        ("amb_gasp_07", ["[surprised]", "[pause]", "[soft sigh]", "[short pause]", "[emphasis]"], "hm?"),
        ("amb_gasp_08", ["[shocked]", "[surprised]", "[inhale]", "[pause]", "[whisper]"], "oh."),
        ("amb_gasp_09", ["[surprised]", "[short pause]", "[whisper]", "[shocked]", "[inhale]"], "why?"),
        ("amb_gasp_10", ["[surprised]", "[shocked]", "[emphasis]", "[short pause]", "[inhale]"], "oh?"),
    ],
    "neutral": [
        ("neu_pause_01", ["[short pause]", "[soft sigh]", "[exhale]", "[whisper]", "[pause]"], "mm."),
        ("neu_pause_02", ["[pause]", "[inhale]", "[exhale]", "[soft sigh]", "[whisper]"], "okay."),
        ("neu_pause_03", ["[short pause]", "[whisper]", "[exhale]", "[pause]", "[soft sigh]"], "mm."),
        ("neu_pause_04", ["[inhale]", "[exhale]", "[pause]", "[whisper]", "[soft sigh]"], "hm."),
        ("neu_pause_05", ["[short pause]", "[whisper]", "[soft sigh]", "[exhale]", "[pause]"], "got it."),
        ("neu_pause_06", ["[pause]", "[soft sigh]", "[whisper]", "[short pause]", "[exhale]"], "mm."),
        ("neu_pause_07", ["[inhale]", "[short pause]", "[exhale]", "[whisper]", "[pause]"], "hm."),
        ("neu_pause_08", ["[soft sigh]", "[pause]", "[whisper]", "[short pause]", "[exhale]"], "alright."),
        ("neu_pause_09", ["[short pause]", "[pause]", "[exhale]", "[soft sigh]", "[whisper]"], "hm."),
        ("neu_pause_10", ["[pause]", "[inhale]", "[soft sigh]", "[exhale]", "[whisper]"], "mm."),
    ],
}


def parse_args() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser(description="Generate 40 extreme nonverbal Fish Speech clips.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pad-ms", type=int, default=450)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    return parser.parse_args()


def add_silence_padding(path: Path, pad_ms: int) -> None:
    """Add silence before and after a wav file."""
    if pad_ms <= 0 or path.suffix.lower() != ".wav":
        return
    with wave.open(str(path), "rb") as reader:
        params = reader.getparams()
        raw = reader.readframes(params.nframes)
    silence_frames = int(params.framerate * pad_ms / 1000.0)
    silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth
    with wave.open(str(path), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(silence + raw + silence)


def main() -> int:
    """Generate all prompt combinations and write a manifest."""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cfg = FishSpeechTTSConfig(max_new_tokens=args.max_new_tokens, auto_play=False)
    client = FishSpeechTTSClient(cfg)
    if not client.is_healthy():
        raise SystemExit("Fish Speech server is not reachable. Start AI_NPC_System/scripts/start_fish_speech_server.sh first.")

    logger = LatencyLogger()
    items: list[dict[str, Any]] = []
    for emotion, prompts in PROMPTS.items():
        emotion_dir = args.output_dir / emotion
        emotion_dir.mkdir(parents=True, exist_ok=True)
        for prompt_id, tags, carrier in prompts:
            text = f"{' '.join(tags)} {carrier}".strip()
            out_path = emotion_dir / f"{prompt_id}.wav"
            if out_path.exists() and not args.force:
                items.append(
                    {
                        "id": prompt_id,
                        "emotion": emotion,
                        "tags": tags,
                        "carrier": carrier,
                        "text": text,
                        "audio_path": str(out_path),
                        "reused": True,
                    }
                )
                continue

            started = time.perf_counter()
            generated = client.synthesize_to_file(text, prefix=prompt_id)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            generated.replace(out_path)
            add_silence_padding(out_path, args.pad_ms)
            logger.log(
                LatencyEvent(
                    stage="fish_speech_extreme_nonverbal_tts",
                    elapsed_ms=elapsed_ms,
                    text=text,
                    engine="fish_speech",
                    metadata={"emotion": emotion, "prompt_id": prompt_id},
                )
            )
            items.append(
                {
                    "id": prompt_id,
                    "emotion": emotion,
                    "tags": tags,
                    "carrier": carrier,
                    "text": text,
                    "audio_path": str(out_path),
                    "latency_ms": round(elapsed_ms, 3),
                    "pad_ms": args.pad_ms,
                }
            )
            print(f"{emotion} {prompt_id}: {elapsed_ms:.1f} ms -> {out_path}")

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "AI_NPC_System/scripts/build_extreme_nonverbal_reactions.py",
        "items": items,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
