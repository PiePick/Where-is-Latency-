#!/usr/bin/env python3
"""Build short spoken thinking-bridge audio for the third FastTrack beat."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
import sys

sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


PHRASES = [
    ("thinking_bridge_01", "Let me think about it.", "neutral", "thinking", "steady"),
    ("thinking_bridge_02", "Give me a second to think.", "neutral", "thinking", "steady"),
    ("thinking_bridge_03", "Hold on, let me think.", "ambiguous", "thinking", "curious"),
    ("thinking_bridge_04", "Let me think for a second.", "neutral", "thinking", "soft"),
    ("thinking_bridge_05", "Okay, let me think about that.", "positive", "thinking", "playful"),
]


def build_manifest(output_dir: Path) -> Path:
    """Write a manifest with relative target audio paths."""
    items: list[dict[str, Any]] = []
    for item_id, text, emotion, event, style_tag in PHRASES:
        items.append(
            {
                "id": item_id,
                "emotion": emotion,
                "event": event,
                "style_tag": style_tag,
                "carrier": text,
                "tts_text": text,
                "audio_path": f"audio/{item_id}.wav",
            }
        )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "AI_NPC_System/scripts/build_thinking_bridge_audio_bundle.py",
        "kind": "thinking_bridge_audio_bundle",
        "purpose": "Short spoken bridge after FastTrack persona wav while SlowTrack is still pending.",
        "tts_reference": {
            "reference_id": config.FISH_SPEECH_REFERENCE_ID,
            "reference_source": config.FISH_SPEECH_REFERENCE_SOURCE,
        },
        "items": items,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def synthesize(output_dir: Path, manifest_path: Path, *, skip_existing: bool, audio_limit: int) -> int:
    """Synthesize missing thinking bridge wav files."""
    client = FishSpeechTTSClient(
        FishSpeechTTSConfig(output_dir=output_dir / "audio", audio_format="wav", auto_play=False)
    )
    if not client.is_healthy():
        raise RuntimeError(f"Fish Speech server is not reachable at {client.cfg.health_url}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    made = 0
    for item in manifest["items"]:
        target = output_dir / item["audio_path"]
        if target.exists() and skip_existing:
            continue
        if audio_limit and made >= audio_limit:
            break
        target.parent.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        generated = client.synthesize_to_file(str(item["tts_text"]), prefix=str(item["id"]))
        generated.replace(target)
        item["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        made += 1
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"audio {made}: {item['id']} -> {target}")
    return made


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CREDO thinking bridge FastTrack audio.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "thinking_bridge_bundle")
    parser.add_argument("--synthesize", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--audio-limit", type=int, default=0)
    args = parser.parse_args()

    manifest_path = build_manifest(args.output_dir)
    made = 0
    if args.synthesize:
        made = synthesize(
            args.output_dir,
            manifest_path,
            skip_existing=args.skip_existing,
            audio_limit=max(0, args.audio_limit),
        )
    print(f"Wrote thinking bridge bundle: {manifest_path}")
    print(f"synthesized_audio={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
