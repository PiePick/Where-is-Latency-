#!/usr/bin/env python3
"""Build short pre-generated "교수진사마" callout audio for FastTrack use."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_NPC_ROOT = PROJECT_ROOT / "AI_NPC_System"
if str(AI_NPC_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_NPC_ROOT))

import config  # noqa: E402
from tts_client import FishSpeechTTSClient  # noqa: E402


VARIANTS: list[dict[str, Any]] = [
    {
        "id": "professor_jinsama_soft_01",
        "label": "soft",
        "emotion": "positive",
        "tension": 0.25,
        "tts_text": "교수진사마.",
        "usage": "quiet affectionate recognition",
    },
    {
        "id": "professor_jinsama_bright_01",
        "label": "bright",
        "emotion": "positive",
        "tension": 0.50,
        "tts_text": "교수진사마!",
        "usage": "normal upbeat FastTrack callout",
    },
    {
        "id": "professor_jinsama_playful_01",
        "label": "playful",
        "emotion": "ambiguous",
        "tension": 0.62,
        "tts_text": "교수진사마?",
        "usage": "curious teasing callout",
    },
    {
        "id": "professor_jinsama_excited_01",
        "label": "excited",
        "emotion": "positive",
        "tension": 0.82,
        "tts_text": "교수진사마!!",
        "usage": "high-energy greeting or surprise",
    },
    {
        "id": "professor_jinsama_flustered_01",
        "label": "flustered",
        "emotion": "ambiguous",
        "tension": 0.72,
        "tts_text": "교수진사마아!",
        "usage": "panicked cute appeal",
    },
]


def build_manifest(output_dir: Path, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact manifest for runtime FastTrack lookup."""
    return {
        "version": "professor-jinsama-call-bundle-v1",
        "purpose": "Pre-generated Lera Mei callout audio for FastTrack special beats.",
        "persona": "Lera Mei",
        "reference_id": config.FISH_SPEECH_REFERENCE_ID,
        "policy": {
            "spoken_phrase": "교수진사마",
            "no_realtime_fasttrack_tts": True,
            "use": "Select by emotion/tension; do not synthesize during runtime.",
        },
        "output_dir": str(output_dir),
        "items": items,
    }


def synthesize(output_dir: Path, items: list[dict[str, Any]], *, limit: int | None) -> int:
    """Synthesize missing callouts with Fish Speech."""
    client = FishSpeechTTSClient()
    if not client.is_healthy():
        raise RuntimeError(f"Fish Speech server is not reachable at {client.cfg.health_url}")

    made = 0
    for item in items:
        if limit is not None and made >= limit:
            break
        existing = item.get("audio_path")
        if existing and Path(str(existing)).exists():
            continue
        audio_path = client.synthesize_to_file(str(item["tts_text"]), prefix=str(item["id"]))
        target = output_dir / "audio" / f"{item['id']}{audio_path.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        audio_path.replace(target)
        item["audio_path"] = str(target)
        made += 1
        print(f"audio {made}: {item['id']} -> {target}")
    return made


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 교수진사마 FastTrack callout bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AI_NPC_ROOT / "professor_jinsama_call_bundle",
    )
    parser.add_argument("--synthesize", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"

    items = [dict(item) for item in VARIANTS]
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        previous_by_id = {item.get("id"): item for item in previous.get("items", [])}
        for item in items:
            old = previous_by_id.get(item["id"]) or {}
            if old.get("audio_path"):
                item["audio_path"] = old["audio_path"]

    made = synthesize(args.output_dir, items, limit=args.limit) if args.synthesize else 0
    manifest = build_manifest(args.output_dir, items)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path}")
    print(f"items={len(items)}, synthesized_audio={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
