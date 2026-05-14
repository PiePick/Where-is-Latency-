"""Pre-generate FastTrack latency-cover audio.

This script turns emotion-tagged reaction lines into ready-to-play Fish Speech
audio clips. Runtime FastTrack then returns an audio path instead of waiting for
live TTS generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


DEFAULT_REACTION_PATH = config.REACTION_DB_PATH
DEFAULT_CUE_PATH = config.FISH_SPEECH_CUE_PATH
DEFAULT_OUTPUT_DIR = config.FAST_TRACK_AUDIO_CACHE_PATH.parent
CATEGORIES = ("Positive", "Negative", "Ambiguous", "Neutral")
SOURCES = ("everyday", "stream")

DEFAULT_CUE_TAGS = {
    "Positive": ["[chuckle]", "[excited]"],
    "Negative": ["[sigh]", "[soft sigh]"],
    "Ambiguous": ["[surprised]", "[short pause]"],
    "Neutral": ["[short pause]", "[pause]"],
}

DEFAULT_REACTION_LINES = {
    ("Positive", "everyday"): ["Great.", "Fantastic."],
    ("Positive", "stream"): ["Good work, friend.", "Have fun!"],
    ("Negative", "everyday"): ["I feel sorry for you.", "I am worried."],
    ("Negative", "stream"): ["I'm so sorry", "I'm sorry. That's awful"],
    ("Ambiguous", "everyday"): ["Could you elaborate on that?", "Exactly how bad?"],
    ("Ambiguous", "stream"): ["Huh. Weird.", "Are you sure?"],
    ("Neutral", "everyday"): ["No problem, anytime.", "Nothing much."],
    ("Neutral", "stream"): ["Fair enough.", "Not wrong."],
}


def parse_args() -> argparse.Namespace:
    """Parse cache builder options."""
    parser = argparse.ArgumentParser(description="Prebuild FastTrack TTS audio cache.")
    parser.add_argument("--reaction-path", type=Path, default=DEFAULT_REACTION_PATH)
    parser.add_argument("--cue-path", type=Path, default=DEFAULT_CUE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-reactions-per-source", type=int, default=3)
    parser.add_argument("--cues-per-category", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    """Load UTF-8 JSON with a short error surface."""
    return json.loads(path.read_text(encoding="utf-8"))


def stable_id(category: str, source: str, cue_tag: str, reaction: str) -> str:
    """Create a deterministic file id for one cover clip."""
    raw = f"{category}|{source}|{cue_tag}|{reaction}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def choose_reactions(
    reactions: dict[str, Any],
    *,
    category: str,
    source: str,
    limit: int,
    rng: random.Random,
) -> list[str]:
    """Sample a small reproducible subset from the final reaction list."""
    bucket = reactions.get(category, {})
    candidates = list(dict.fromkeys(bucket.get(source, []) if isinstance(bucket, dict) else []))
    preferred = [line for line in DEFAULT_REACTION_LINES.get((category, source), []) if line in candidates]
    if len(preferred) >= limit:
        return preferred[:limit]
    remaining = [line for line in candidates if line not in preferred]
    if len(preferred) + len(remaining) <= limit:
        return preferred + remaining
    return preferred + sorted(rng.sample(remaining, limit - len(preferred)))


def choose_cues(cue_data: dict[str, Any], *, category: str, limit: int) -> list[dict[str, Any]]:
    """Use the highest-weight cue tags for stable pre-generated covers."""
    if "cues" in cue_data:
        cues = list(cue_data.get("cues", {}).get(category, []))
    else:
        cues = list(cue_data.get(category, []))
    cues.sort(key=lambda item: float(item.get("weight", 0.0)), reverse=True)
    by_tag = {str(item.get("tag", "")): item for item in cues}
    selected = [by_tag[tag] for tag in DEFAULT_CUE_TAGS.get(category, []) if tag in by_tag]
    selected = selected[:limit]
    if len(selected) < limit:
        selected_ids = {id(item) for item in selected}
        selected.extend(item for item in cues if id(item) not in selected_ids)
    return selected[:limit]


def build_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build manifest items before any TTS call is made."""
    reactions = load_json(args.reaction_path)
    cue_data = load_json(args.cue_path)
    rng = random.Random(args.seed)
    items: list[dict[str, Any]] = []

    for category in CATEGORIES:
        cues = choose_cues(cue_data, category=category, limit=args.cues_per_category)
        for source in SOURCES:
            lines = choose_reactions(
                reactions,
                category=category,
                source=source,
                limit=args.max_reactions_per_source,
                rng=rng,
            )
            for reaction in lines:
                plain = reaction.strip()
                for cue in cues:
                    tag = str(cue.get("tag", "")).strip()
                    tts_text = f"{tag} {plain}".strip()
                    cache_id = stable_id(category, source, tag, plain)
                    audio_rel = Path(category) / source / f"{cache_id}.wav"
                    items.append(
                        {
                            "id": cache_id,
                            "category": category,
                            "source": source,
                            "reaction": plain,
                            "plain_tts_text": plain,
                            "tts_text": tts_text,
                            "cue": cue,
                            "audio_path": audio_rel.as_posix(),
                        }
                    )
    return items


def synthesize_items(args: argparse.Namespace, items: list[dict[str, Any]]) -> None:
    """Call Fish Speech once per missing cache item."""
    if args.dry_run:
        return

    client = FishSpeechTTSClient(FishSpeechTTSConfig(output_dir=args.output_dir))
    if not client.is_healthy():
        raise SystemExit("Fish Speech server is not reachable. Start it before prebuilding cache.")

    for index, item in enumerate(items, start=1):
        audio_path = args.output_dir / item["audio_path"]
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        if audio_path.exists() and not args.force:
            print(f"[skip {index}/{len(items)}] {audio_path}")
            continue

        print(f"[tts {index}/{len(items)}] {item['tts_text']}")
        tmp_path = client.synthesize_to_file(item["tts_text"], prefix=f"fast_{item['id']}")
        tmp_path.replace(audio_path)


def write_manifest(args: argparse.Namespace, items: list[dict[str, Any]]) -> Path:
    """Write the runtime manifest next to the generated audio tree."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    generated_at = datetime.now(timezone.utc).isoformat()
    if args.dry_run and manifest_path.exists():
        previous = load_json(manifest_path)
        generated_at = str(previous.get("generated_at", generated_at))

    manifest = {
        "version": "fast-track-tts-cache-v01",
        "generated_at": generated_at,
        "generator": "AI_NPC_System/scripts/prebuild_fast_track_tts_cache.py",
        "reaction_path": str(args.reaction_path),
        "cue_path": str(args.cue_path),
        "policy": {
            "max_reactions_per_source": args.max_reactions_per_source,
            "cues_per_category": args.cues_per_category,
            "keyword_usage": "Keywords are used only to bias everyday vs stream cache selection.",
        },
        "items": items,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def main() -> int:
    args = parse_args()
    items = build_items(args)
    synthesize_items(args, items)
    manifest_path = write_manifest(args, items)
    print(f"Wrote {len(items)} cache entries to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
