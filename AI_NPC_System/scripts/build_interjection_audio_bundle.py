#!/usr/bin/env python3
"""Build a pre-generated pure interjection audio bundle for FastTrack."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


OUTPUT_DIR = ROOT / "expressive_interjection_bundle"

EMOTION_CUES = {
    "positive": "[happy]",
    "negative": "[sad]",
    "ambiguous": "[surprised]",
    "neutral": "[calm]",
}

EVENT_CUES = {
    "positive": "[chuckle]",
    "negative": "[sigh]",
    "ambiguous": "[inhale]",
    "neutral": "[soft sigh]",
}

STYLE_CUE_CHAINS = {
    "high-pitched": ("[high-pitched]", "[bright]", "[youthful]"),
    "playful": ("[playful]", "[teasing]", "[bouncy]", "[lively]"),
    "energetic": ("[excited]", "[energetic]", "[loud]", "[hype]"),
    "smug": ("[smug]", "[playful]", "[cheeky]", "[confident]"),
    "cute": ("[cute]", "[soft]", "[bright]", "[high-pitched]"),
}

PURE_CARRIERS = {
    "positive": ("ha-ha!", "hee-hee!", "ahaha!", "haha!", "oh!", "aw!"),
    "negative": ("ugh.", "hm.", "mm."),
    "ambiguous": ("huh?", "oh?"),
    "neutral": ("hm.", "mm."),
}

EVENT_BY_EMOTION = {
    "positive": "laugh",
    "negative": "sigh",
    "ambiguous": "surprise",
    "neutral": "thinking",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pure interjection Fish Speech audio for CREDO FastTrack.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--synthesize", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--audio-limit", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    return parser.parse_args()


def synthesis_text(emotion: str, style_tag: str, carrier: str) -> str:
    """Build Fish Speech text with one pause cue before and after the carrier."""
    cues = [
        "[short pause]",
        EMOTION_CUES[emotion],
        EVENT_CUES[emotion],
        *STYLE_CUE_CHAINS[style_tag],
    ]
    cues = list(dict.fromkeys(cues))
    return " ".join([*cues, carrier, "[short pause]"]).strip()


def make_items() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create deterministic manifest cells and items."""
    cells: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for emotion, carriers in PURE_CARRIERS.items():
        for style_tag in STYLE_CUE_CHAINS:
            cell_id = f"{emotion}_{style_tag}"
            cells.append(
                {
                    "cell_id": cell_id,
                    "emotion": emotion,
                    "style_tag": style_tag,
                    "event": EVENT_BY_EMOTION[emotion],
                    "carriers": list(carriers),
                }
            )
            for index, carrier in enumerate(carriers, start=1):
                item_id = f"{cell_id}_{index:02d}"
                items.append(
                    {
                        "id": item_id,
                        "cell_id": cell_id,
                        "emotion": emotion,
                        "style_tag": style_tag,
                        "event": EVENT_BY_EMOTION[emotion],
                        "carrier": carrier,
                        "plain_tts_text": carrier,
                        "tts_text": synthesis_text(emotion, style_tag, carrier),
                    }
                )
    return cells, items


def load_existing_audio(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.exists():
        return {}
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        str(item.get("id")): str(item.get("audio_path"))
        for item in raw.get("items", [])
        if item.get("id") and item.get("audio_path")
    }


def write_manifest(args: argparse.Namespace, cells: list[dict[str, Any]], items: list[dict[str, Any]]) -> Path:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "AI_NPC_System/scripts/build_interjection_audio_bundle.py",
        "kind": "pure_interjection_audio_bundle",
        "tts_reference": {
            "reference_id": config.FISH_SPEECH_REFERENCE_ID,
            "reference_source": config.FISH_SPEECH_REFERENCE_SOURCE,
        },
        "policy": {
            "spoken_content": "pure interjection or nonverbal filler only",
            "no_dialogue_carriers": True,
            "pause_cue_policy": "Each synthesized text starts and ends with exactly one [short pause] cue.",
        },
        "style_tts_cue_chains": STYLE_CUE_CHAINS,
        "cells": cells,
        "items": items,
    }
    manifest_path = args.output_dir / "manifest.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def synthesize(args: argparse.Namespace, items: list[dict[str, Any]], manifest_path: Path) -> int:
    """Synthesize missing wav files and update the manifest after every item."""
    client = FishSpeechTTSClient(
        FishSpeechTTSConfig(max_new_tokens=args.max_new_tokens, auto_play=False)
    )
    if not client.is_healthy():
        raise RuntimeError(f"Fish Speech server is not reachable at {client.cfg.health_url}")

    made = 0
    for item in items:
        current = str(item.get("audio_path") or "")
        if current and not args.force:
            audio_path = args.output_dir / current
            if audio_path.exists() and args.skip_existing:
                continue
        if args.audio_limit and made >= args.audio_limit:
            break

        audio_dir = args.output_dir / "audio" / item["emotion"] / item["style_tag"]
        audio_dir.mkdir(parents=True, exist_ok=True)
        target = audio_dir / f"{item['id']}.wav"
        if target.exists() and not args.force and args.skip_existing:
            item["audio_path"] = target.relative_to(args.output_dir).as_posix()
            continue

        started = time.perf_counter()
        generated = client.synthesize_to_file(str(item["tts_text"]), prefix=item["id"])
        generated.replace(target)
        made += 1
        item["audio_path"] = target.relative_to(args.output_dir).as_posix()
        item["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry for entry in raw["items"]}
        by_id[item["id"]].update({"audio_path": item["audio_path"], "latency_ms": item["latency_ms"]})
        manifest_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"audio {made}: {item['id']} -> {target}")
    return made


def main() -> int:
    args = parse_args()
    cells, items = make_items()
    existing_audio = load_existing_audio(args.output_dir / "manifest.json") if args.skip_existing else {}
    for item in items:
        if item["id"] in existing_audio:
            item["audio_path"] = existing_audio[item["id"]]

    manifest_path = write_manifest(args, cells, items)
    made = synthesize(args, items, manifest_path) if args.synthesize else 0
    print(f"Wrote interjection bundle: {manifest_path}")
    print(f"items={len(items)}, cells={len(cells)}, synthesized_audio={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
