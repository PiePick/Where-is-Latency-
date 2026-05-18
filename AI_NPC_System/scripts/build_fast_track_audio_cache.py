#!/usr/bin/env python3
"""Build pre-generated FastTrack audio covers with the configured CREDO voice."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from stylebert_vits2_client import StyleBertVITS2Client, StyleBertVITS2Config  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402

CATEGORY_NAMES = ("Positive", "Negative", "Ambiguous", "Neutral")
SOURCE_NAMES = ("everyday", "stream")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FastTrack audio cache from hybrid reactions.")
    parser.add_argument("--reaction-path", type=Path, default=config.REACTION_DB_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "fast_track_audio_cache")
    parser.add_argument("--engine", choices=("fish_speech", "stylebert_vits2"), default="fish_speech")
    parser.add_argument("--per-bucket", type=int, default=4, help="Number of reactions per category/source bucket.")
    parser.add_argument("--seed", type=int, default=config.FISH_SPEECH_SEED)
    parser.add_argument("--force", action="store_true", help="Remove the existing cache directory first.")
    parser.add_argument("--format", default=config.FISH_SPEECH_FORMAT, choices=("wav", "mp3", "opus", "pcm"))
    return parser.parse_args()


def load_reactions(path: Path) -> dict[str, dict[str, list[str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected reaction file: {path}")
    return payload


def select_items(reactions: dict[str, dict[str, list[str]]], per_bucket: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    selected: list[dict[str, str]] = []
    for category in CATEGORY_NAMES:
        by_source = reactions.get(category, {})
        for source in SOURCE_NAMES:
            texts = [str(item).strip() for item in by_source.get(source, []) if str(item).strip()]
            if not texts:
                continue
            sample_size = min(per_bucket, len(texts))
            for index, reaction in enumerate(rng.sample(texts, sample_size), start=1):
                selected.append(
                    {
                        "id": f"{category.lower()}_{source}_{index:02d}",
                        "category": category,
                        "source": source,
                        "reaction": reaction,
                        "plain_tts_text": reaction,
                        "tts_text": reaction,
                    }
                )
    return selected


def build_client(engine: str, output_dir: Path, audio_format: str) -> Any:
    if engine == "fish_speech":
        cfg = FishSpeechTTSConfig(output_dir=output_dir, audio_format=audio_format, auto_play=False)
        client = FishSpeechTTSClient(cfg)
        if not client.is_healthy():
            raise RuntimeError(f"Fish Speech server is not reachable at {cfg.health_url}")
        return client

    cfg = StyleBertVITS2Config(output_dir=output_dir, auto_play=False)
    client = StyleBertVITS2Client(cfg)
    if not client.is_healthy():
        raise RuntimeError(f"Style-Bert-VITS2 server is not reachable at {cfg.health_url}")
    return client


def stylebert_style_for_category(category: str) -> str:
    key = str(category or "neutral").lower()
    style_map = {
        "positive": config.STYLEBERT_VITS2_STYLE_POSITIVE,
        "negative": config.STYLEBERT_VITS2_STYLE_NEGATIVE,
        "ambiguous": config.STYLEBERT_VITS2_STYLE_AMBIGUOUS,
        "neutral": config.STYLEBERT_VITS2_STYLE_NEUTRAL,
    }
    return style_map.get(key, config.STYLEBERT_VITS2_STYLE)


def cache_reference(engine: str) -> dict[str, Any]:
    if engine == "fish_speech":
        return {
            "engine": engine,
            "reference_id": config.FISH_SPEECH_REFERENCE_ID,
            "source_dir": str(PROJECT_ROOT / "vendor" / "fish-speech" / "references" / str(config.FISH_SPEECH_REFERENCE_ID)),
            "use_memory_cache": "off",
        }
    return {
        "engine": engine,
        "reference_id": config.STYLEBERT_VITS2_REFERENCE_VOICE,
        "model_id": config.STYLEBERT_VITS2_MODEL_ID,
        "model_name": config.STYLEBERT_VITS2_MODEL_NAME,
        "speaker_id": config.STYLEBERT_VITS2_SPEAKER_ID,
        "style": config.STYLEBERT_VITS2_STYLE,
        "style_weight": config.STYLEBERT_VITS2_STYLE_WEIGHT,
        "emotion_styles": {
            "positive": config.STYLEBERT_VITS2_STYLE_POSITIVE,
            "negative": config.STYLEBERT_VITS2_STYLE_NEGATIVE,
            "ambiguous": config.STYLEBERT_VITS2_STYLE_AMBIGUOUS,
            "neutral": config.STYLEBERT_VITS2_STYLE_NEUTRAL,
        },
    }


def main() -> int:
    args = parse_args()
    if args.force and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    audio_root = args.output_dir / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)

    reactions = load_reactions(args.reaction_path)
    selected = select_items(reactions, args.per_bucket, args.seed)
    if not selected:
        raise SystemExit("No FastTrack reactions selected.")

    client = build_client(args.engine, audio_root, args.format)
    manifest_items: list[dict[str, Any]] = []
    for item in selected:
        category_dir = audio_root / item["category"] / item["source"]
        category_dir.mkdir(parents=True, exist_ok=True)
        original_output_dir = client.cfg.output_dir
        object.__setattr__(client.cfg, "output_dir", category_dir)
        try:
            synth_kwargs: dict[str, Any] = {}
            if args.engine == "stylebert_vits2":
                synth_kwargs["style"] = stylebert_style_for_category(item["category"])
            audio_path = client.synthesize_to_file(item["tts_text"], prefix=item["id"], **synth_kwargs)
        finally:
            object.__setattr__(client.cfg, "output_dir", original_output_dir)

        rel_audio = audio_path.relative_to(args.output_dir)
        manifest_items.append(
            {
                **item,
                "audio_path": rel_audio.as_posix(),
                "cue": None,
            }
        )
        print(f"cached {item['id']}: {audio_path}")

    manifest = {
        "version": "credo-fasttrack-audio-cache-v1",
        "created_at_unix": time.time(),
        "tts_reference": cache_reference(args.engine),
        "items": manifest_items,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote FastTrack audio cache: {manifest_path}")
    print(f"items={len(manifest_items)}, reference={manifest['tts_reference'].get('reference_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
