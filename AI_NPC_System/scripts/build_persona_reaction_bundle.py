#!/usr/bin/env python3
"""Build a persona-conditioned FastTrack reaction text/audio bundle.

The bundle is intentionally generated offline. Runtime FastTrack should only
retrieve a short reaction from this manifest instead of asking an LLM or a slow
TTS model during the live turn.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tts_client import FishSpeechTTSClient, FishSpeechTTSConfig  # noqa: E402


EMOTIONS = ("Positive", "Negative", "Ambiguous", "Neutral")
INTENTS = ("QUESTION", "INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")
STYLE_TAGS = {
    "high-pitched": {
        "label": "high-pitched",
        "tts_cue": "[high-pitched]",
        "instruction": "bright, youthful, high-register, excited delivery; the line should feel openly cheerful",
    },
    "playful": {
        "label": "playful",
        "tts_cue": "[playful]",
        "instruction": "teasing, casual, bouncy, mischievous, and clearly playful",
    },
    "energetic": {
        "label": "energetic",
        "tts_cue": "[energetic]",
        "instruction": "high-spirited, excited, fast-reacting, animated, and upbeat",
    },
    "smug": {
        "label": "smug",
        "tts_cue": "[smug]",
        "instruction": "cheeky, self-satisfied, lightly bratty, and teasing",
    },
    "cute": {
        "label": "cute",
        "tts_cue": "[cute]",
        "instruction": "soft, adorable, compact, friendly, and sweet",
    },
}

EMOTION_TTS_CUES = {
    "Positive": "[happy]",
    "Negative": "[sad]",
    "Ambiguous": "[surprised]",
    "Neutral": "[calm]",
}

# Each personality style axis expands into multiple Fish Speech prosody cues.
# Keep these cues to pitch, energy, pace, tension, and attitude only. Nonverbal
# events such as laughs, sighs, sobs, and gasps are handled by motion/audio event
# scheduling, not by inline TTS style tags.
STYLE_TTS_CUE_CHAINS = {
    "high-pitched": ("[high-pitched]", "[bright]", "[youthful]"),
    "playful": ("[playful]", "[teasing]", "[bouncy]", "[lively]"),
    "energetic": ("[excited]", "[energetic]", "[loud]", "[hype]"),
    "smug": ("[smug]", "[playful]", "[cheeky]", "[confident]"),
    "cute": ("[cute]", "[soft]", "[bright]", "[high-pitched]"),
}

DISALLOWED_TTS_EVENT_CUES = {
    "giggle",
    "laugh",
    "laughing",
    "chuckle",
    "sigh",
    "sighing",
    "sob",
    "cry",
    "crying",
    "gasp",
    "gasping",
}

DEFAULT_VARIANTS_PER_CELL = 5
DEFAULT_PERSONALITY_ID = "dataset_grounded_playful_vtuber"
DEFAULT_PERSONALITY = (
    "The speaker is a playful English VTuber-style persona: cute, energetic, mischievous, "
    "casual, clumsy in a charming way, and friendly to the audience. The persona often acts confident "
    "then gets silly or flustered. Reactions must sound like a bright stream moment, not a neutral "
    "chatbot answer. Keep them informal, brief, playful, and never formal. For dataset integrity, "
    "do not inject catchphrases, meme words, names, character-lore terms, or topic details unless they "
    "are already present in the selected dataset seeds."
)


@dataclass(frozen=True)
class Cell:
    emotion: str
    intent: str
    style_tag: str

    @property
    def id(self) -> str:
        return f"{self.emotion.lower()}_{self.intent.lower()}_{self.style_tag}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a CREDO persona reaction bundle.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "persona_reaction_bundle")
    parser.add_argument("--variants-per-cell", type=int, default=DEFAULT_VARIANTS_PER_CELL)
    parser.add_argument("--personality-id", default=DEFAULT_PERSONALITY_ID)
    parser.add_argument("--personality", default=DEFAULT_PERSONALITY)
    parser.add_argument("--emotion-data", type=Path, default=ROOT / "prepared_fasttrack_data" / "go_emotions_coarse.jsonl")
    parser.add_argument("--intent-data", type=Path, default=ROOT / "prepared_fasttrack_data" / "swda_intent_coarse.jsonl")
    parser.add_argument("--candidate-pool-size", type=int, default=30)
    parser.add_argument("--seed-max-words", type=int, default=10)
    parser.add_argument("--seed-max-chars", type=int, default=96)
    parser.add_argument("--model", default=config.LOCAL_LLM_MODEL)
    parser.add_argument("--base-url", default=config.LOCAL_LLM_BASE_URL)
    parser.add_argument("--api-key", default=config.LOCAL_LLM_API_KEY)
    parser.add_argument("--timeout", type=float, default=max(config.LOCAL_LLM_TIMEOUT, 60.0))
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--limit-cells", type=int, default=0, help="Debug limit. 0 means all 120 cells.")
    parser.add_argument("--skip-existing", action="store_true", help="Reuse existing text cells.")
    parser.add_argument("--synthesize", action="store_true", help="Also synthesize missing Fish Speech audio.")
    parser.add_argument("--audio-limit", type=int, default=0, help="Debug limit for synthesis. 0 means all missing audio.")
    parser.add_argument("--format", default=config.FISH_SPEECH_FORMAT, choices=("wav", "mp3", "opus", "pcm"))
    return parser.parse_args()


def cells() -> list[Cell]:
    return [Cell(emotion, intent, style) for emotion in EMOTIONS for intent in INTENTS for style in STYLE_TAGS]


def chat_completion(args: argparse.Namespace, messages: list[dict[str, str]]) -> str:
    url = args.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Local LLM endpoint rejected request at {url}: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local LLM endpoint is unreachable at {url}: {exc}") from exc
    return str(data["choices"][0]["message"]["content"]).strip()


def clean_dataset_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace("\\/", "/")
    # SWDA/GPT-style transcript markers such as D, F, C, and trailing slash are labels, not spoken text.
    text = re.sub(r"(?<![A-Za-z])(?:[CDFM])\s*,?\s+", "", text)
    text = re.sub(r"\s*/\s*$", "", text)
    text = re.sub(r"\s+-\s*", " ", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" -/\t\r\n")
    return text


def load_labeled_jsonl(path: Path, allowed_labels: set[str] | dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    if isinstance(allowed_labels, dict):
        label_aliases = {
            str(target).upper(): tuple(str(alias).upper() for alias in aliases)
            for target, aliases in allowed_labels.items()
        }
    else:
        label_aliases = {str(label).upper(): (str(label).upper(),) for label in allowed_labels}

    source_to_target = {
        alias: target
        for target, aliases in label_aliases.items()
        for alias in aliases
    }
    buckets = {label: [] for label in label_aliases}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            label = str(row.get("coarse_label", "")).upper()
            target_label = source_to_target.get(label)
            if target_label is None:
                continue
            text = clean_dataset_text(row.get("text", ""))
            if is_usable_seed(text):
                buckets[target_label].append(text)
    return buckets


def is_usable_seed(text: str) -> bool:
    if not text:
        return False
    words = text.split()
    if len(words) < 3 or len(words) > 24:
        return False
    if re.search(r"https?://|www\.", text, flags=re.I):
        return False
    if sum(ch.isalpha() for ch in text) < 8:
        return False
    return True


def build_seed_pools(args: argparse.Namespace) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    emotion_labels = {emotion.upper(): (emotion.upper(),) for emotion in EMOTIONS}
    emotion_labels["AMBIGUOUS"] = ("AMBIGUOUS", "SURPRISE")
    intent_labels = {intent.upper() for intent in INTENTS}
    return (
        load_labeled_jsonl(args.emotion_data, emotion_labels),
        load_labeled_jsonl(args.intent_data, intent_labels),
    )


def sample_seed_pool(items: list[str], *, seed_key: str, size: int) -> list[str]:
    deduped = list(dict.fromkeys(items))
    rng = random.Random(seed_key)
    rng.shuffle(deduped)
    return deduped[:size]


def compact_seed(text: str, *, max_words: int, max_chars: int) -> str:
    words = clean_dataset_text(text).split()
    compact = " ".join(words[:max_words])
    if len(compact) > max_chars:
        compact = compact[:max_chars].rsplit(" ", 1)[0].strip()
    return compact or clean_dataset_text(text)[:max_chars]


def build_seed_pairs(
    emotion_seeds: list[str],
    intent_seeds: list[str],
    *,
    max_words: int,
    max_chars: int,
) -> list[dict[str, str]]:
    return [
        {
            "pair_id": f"seed_{index:02d}",
            "emotion_seed": compact_seed(emotion, max_words=max_words, max_chars=max_chars),
            "intent_seed": compact_seed(intent, max_words=max_words, max_chars=max_chars),
        }
        for index, (emotion, intent) in enumerate(zip(emotion_seeds, intent_seeds), start=1)
    ]


def build_prompt(
    cell: Cell,
    args: argparse.Namespace,
    seed_pairs: list[dict[str, str]],
) -> list[dict[str, str]]:
    style = STYLE_TAGS[cell.style_tag]
    system = (
        "You filter and rewrite labeled dataset examples into offline FastTrack reaction candidates for CREDO. "
        "Return JSON only. All text must be natural English. Do not include markdown, numbering, "
        "emoji, bracketed style tags, stage directions, or explanations."
    )
    user = {
        "personality": args.personality,
        "emotion": cell.emotion,
        "response_intent": cell.intent,
        "style_tag": cell.style_tag,
        "style_instruction": style["instruction"],
        "labeled_seed_pairs": seed_pairs,
        "task": (
            f"Pick exactly {args.variants_per_cell} rows from labeled_seed_pairs and rewrite each into one short FastTrack reaction. "
            "Keys: pair_id=row id, emotion_seed=same-emotion evidence, intent_seed=same-intent evidence. "
            "Ground every reaction in one row's emotion_seed+intent_seed; do not create from scratch. "
            "Make the persona/style obvious only through tone, rhythm, informality, punctuation, and wording grounded in the selected seeds. "
            "Do not add catchphrases, meme words, names, character-lore terms, or topic details unless they are present in the seeds. "
            "Remove dataset transcript markers such as standalone C, D, F, M, slashes, and broken hesitation labels. "
            "Each reaction must be 3 to 12 words, self-contained, audience-safe, and not a dataset quote. "
            "Avoid repeated wording."
        ),
        "json_schema": {"reactions": ["sentence 1", "sentence 2"]},
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]

def load_llm_payload(raw: str) -> Any:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    candidates = [text]
    if fenced:
        candidates.insert(0, fenced.group(1).strip())

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

    reactions_match = re.search(r"reactions\s*[:=]\s*(\[[\s\S]*?\])", text, flags=re.I)
    if reactions_match:
        candidates.insert(0, reactions_match.group(1).strip())

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(candidate)
            except (json.JSONDecodeError, SyntaxError, ValueError):
                continue
    return None


def clean_reaction_text(item: Any) -> str:
    if isinstance(item, dict):
        item = (
            item.get("reaction")
            or item.get("text")
            or item.get("sentence")
            or item.get("plain_tts_text")
            or ""
        )
    text = re.sub(r"\[[^\]]+\]", " ", str(item))
    text = re.sub(r"^\s*[-*\d.)]+\s*", "", text)
    text = clean_dataset_text(text)
    text = re.sub(r"\s+", " ", text).strip(" -/\t\r\n\"'")
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = text.rstrip(" ,/")
    return text


def parse_reactions(raw: str, expected: int) -> list[str]:
    payload = load_llm_payload(raw)
    if isinstance(payload, dict):
        reactions = payload.get("reactions") or payload.get("items") or payload.get("responses") or []
    elif isinstance(payload, list):
        reactions = payload
    else:
        reactions = []

    if not reactions:
        quoted = re.findall(r"[\"“]([^\"”]{3,180})[\"”]|'([^']{3,180})'", raw)
        reactions = [left or right for left, right in quoted]
    if not reactions:
        reactions = [line for line in raw.splitlines() if line.strip()]

    cleaned: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for item in reactions:
        text = clean_reaction_text(item)
        lowered = text.lower()
        if (
            not text
            or lowered in {"reactions", "items", "responses"}
            or lowered.endswith(":")
            or lowered.startswith(("here ", "json"))
        ):
            continue
        if lowered in seen:
            duplicates.append(text)
            continue
        seen.add(lowered)
        cleaned.append(text)
        if len(cleaned) >= expected:
            break

    if len(cleaned) < expected:
        for text in duplicates:
            cleaned.append(text)
            if len(cleaned) >= expected:
                break

    if len(cleaned) != expected:
        raise RuntimeError(f"Expected {expected} reactions, got {len(cleaned)} from: {raw}")
    return cleaned


def _validate_tts_cues(cues: list[str]) -> None:
    """Keep generated TTS controls free of nonverbal event cues."""
    bad = []
    for cue in cues:
        normalized = str(cue).strip().strip("[]").lower()
        if normalized in DISALLOWED_TTS_EVENT_CUES:
            bad.append(cue)
    if bad:
        raise RuntimeError(
            "TTS cue chains must not include nonverbal event cues; "
            f"move these to motion/audio events instead: {', '.join(bad)}"
        )


def synthesis_text_for_item(item: dict[str, Any]) -> str:
    """Add compact Fish Speech prosody cue chains only for synthesis."""
    emotion = str(item.get("emotion") or "Neutral")
    style_tag = str(item.get("style_tag") or "").strip()
    cues: list[str] = []

    emotion_cue = EMOTION_TTS_CUES.get(emotion)
    if emotion_cue:
        cues.append(emotion_cue)

    cues.extend(STYLE_TTS_CUE_CHAINS.get(style_tag, ()))
    _validate_tts_cues(cues)

    deduped_cues = list(dict.fromkeys(cues))
    text = str(item.get("tts_text") or item.get("reaction") or "").strip()
    return " ".join([*deduped_cues, text]).strip()


def compact_manifest_item(
    item: dict[str, Any],
    cell: Cell,
    args: argparse.Namespace,
    *,
    reaction: str | None = None,
    seed_pair_count: int | None = None,
) -> dict[str, Any]:
    """Return the compact runtime item without duplicating cell metadata."""
    reaction_text = clean_reaction_text(
        reaction
        if reaction is not None
        else item.get("reaction") or item.get("plain_tts_text") or item.get("tts_text") or ""
    )
    if not reaction_text:
        raise RuntimeError(f"Empty reaction for cell {cell.id}")

    item_id = str(item.get("id") or f"{cell.id}_{1:02d}")
    compact = {
        "id": item_id,
        "cell_id": cell.id,
        "reaction": reaction_text,
        "audio_path": item.get("audio_path"),
    }
    tts_text = clean_reaction_text(item.get("tts_text") or "")
    if tts_text and tts_text != reaction_text:
        compact["tts_text"] = tts_text
    return compact



def normalize_reaction_key(text: str) -> str:
    text = clean_reaction_text(text).lower()
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_manifest_items(items: list[dict[str, Any]]) -> None:
    seen_by_cell: dict[str, dict[str, str]] = {}
    duplicates: list[str] = []
    for item in items:
        cell_id = str(item.get("cell_id") or "")
        key = normalize_reaction_key(str(item.get("reaction") or ""))
        if not key:
            raise RuntimeError(f"Empty reaction in item {item.get('id')}")
        seen = seen_by_cell.setdefault(cell_id, {})
        previous = seen.get(key)
        if previous:
            duplicates.append(f"{previous} == {item.get('id')}: {item.get('reaction')}")
        else:
            seen[key] = str(item.get("id"))
    if duplicates:
        preview = "\n".join(duplicates[:10])
        raise RuntimeError(f"Duplicate reactions found inside a cell.\n{preview}")


def cells_by_id(cell_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(cell.get("cell_id")): cell for cell in cell_payloads if isinstance(cell, dict)}

def build_text_bundle(args: argparse.Namespace, manifest_path: Path) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    if args.skip_existing and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing_items = [item for item in existing.get("items", []) if isinstance(item, dict)]
    if not existing_items:
        for cell_payload in existing.get("cells", []):
            if isinstance(cell_payload, dict):
                existing_items.extend(item for item in cell_payload.get("items", []) if isinstance(item, dict))

    existing_by_cell: dict[str, list[dict[str, Any]]] = {}
    for item in existing_items:
        cell_id = str(item.get("cell_id") or "")
        if cell_id:
            existing_by_cell.setdefault(cell_id, []).append(item)

    emotion_buckets, intent_buckets = build_seed_pools(args)
    selected_cells = cells()
    if args.limit_cells:
        selected_cells = selected_cells[: args.limit_cells]

    bundle_cells: list[dict[str, Any]] = []
    manifest_items: list[dict[str, Any]] = []
    for cell in selected_cells:
        cell_items: list[dict[str, Any]] = []
        if cell.id in existing_by_cell:
            for existing_item in existing_by_cell[cell.id]:
                item = compact_manifest_item(existing_item, cell, args)
                cell_items.append(item)
                manifest_items.append(item)
        else:
            accepted_reactions: list[str] = []
            last_count = 0
            for attempt in range(1, 6):
                emotion_seeds = sample_seed_pool(
                    emotion_buckets.get(cell.emotion.upper(), []),
                    seed_key=f"{cell.id}:emotion:{attempt}",
                    size=args.candidate_pool_size,
                )
                intent_seeds = sample_seed_pool(
                    intent_buckets.get(cell.intent.upper(), []),
                    seed_key=f"{cell.id}:intent:{attempt}",
                    size=args.candidate_pool_size,
                )
                if not emotion_seeds:
                    raise RuntimeError(f"No emotion-labeled seeds for {cell.emotion} from {args.emotion_data}")
                if not intent_seeds:
                    raise RuntimeError(f"No intent-labeled seeds for {cell.intent} from {args.intent_data}")
                seed_pairs = build_seed_pairs(
                    emotion_seeds,
                    intent_seeds,
                    max_words=args.seed_max_words,
                    max_chars=args.seed_max_chars,
                )
                raw = chat_completion(args, build_prompt(cell, args, seed_pairs))
                try:
                    reactions = parse_reactions(raw, args.variants_per_cell)
                except RuntimeError:
                    last_count = 0
                    continue
                tentative: list[str] = []
                tentative_keys: set[str] = set()
                for reaction in reactions:
                    key = normalize_reaction_key(reaction)
                    if key in tentative_keys:
                        continue
                    tentative_keys.add(key)
                    tentative.append(reaction)
                last_count = len(tentative)
                if len(tentative) == args.variants_per_cell:
                    accepted_reactions = tentative
                    break
            if len(accepted_reactions) != args.variants_per_cell:
                raise RuntimeError(
                    f"Cell {cell.id} produced duplicate reactions inside the cell after 5 attempts: "
                    f"expected {args.variants_per_cell}, got {last_count}"
                )
            for index, reaction in enumerate(accepted_reactions, start=1):
                item = compact_manifest_item(
                    {"id": f"{cell.id}_{index:02d}", "audio_path": None},
                    cell,
                    args,
                    reaction=reaction,
                    seed_pair_count=len(seed_pairs),
                )
                cell_items.append(item)
                manifest_items.append(item)
        bundle_cells.append(
            {
                "cell_id": cell.id,
                "emotion": cell.emotion,
                "intent": cell.intent,
                "style_tag": cell.style_tag,
                "item_ids": [item["id"] for item in cell_items],
            }
        )
        print(f"text cell {cell.id}: {len(cell_items)} reactions")

    manifest = {
        "version": "credo-persona-reaction-bundle-v2",
        "created_at_unix": time.time(),
        "personality_id": args.personality_id,
        "personality": args.personality,
        "dimensions": {
            "emotions": list(EMOTIONS),
            "intents": list(INTENTS),
            "style_tags": list(STYLE_TAGS),
            "variants_per_cell": args.variants_per_cell,
        },
        "style_tag_details": STYLE_TAGS,
        "style_tts_cue_chains": STYLE_TTS_CUE_CHAINS,
        "tts_cue_policy": "Fish Speech inline cues control only pitch, energy, pace, tension, and attitude. Nonverbal events such as laugh, giggle, sigh, sob, or gasp are excluded and should be handled by separate motion/audio events.",
        "labeled_dataset_sources": {
            "emotion_data": str(args.emotion_data),
            "intent_data": str(args.intent_data),
            "candidate_pool_size": args.candidate_pool_size,
            "seed_pair_count_per_cell": args.candidate_pool_size,
            "seed_max_words": args.seed_max_words,
            "seed_max_chars": args.seed_max_chars,
        },
        "llm_filter": {
            "model": args.model,
            "base_url": args.base_url,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "role": "filter_and_rewrite_labeled_dataset_seeds",
        },
        "tts_reference": {
            "engine": "fish_speech",
            "reference_id": config.FISH_SPEECH_REFERENCE_ID,
            "source_dir": str(PROJECT_ROOT / "vendor" / "fish-speech" / "references" / str(config.FISH_SPEECH_REFERENCE_ID)),
            "use_memory_cache": "off",
        },
        "cells": bundle_cells,
        "items": manifest_items,
    }
    validate_manifest_items(manifest_items)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def synthesize_missing_audio(args: argparse.Namespace, manifest: dict[str, Any], manifest_path: Path) -> None:
    audio_root = args.output_dir / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    client = FishSpeechTTSClient(
        FishSpeechTTSConfig(output_dir=audio_root, audio_format=args.format, auto_play=False)
    )
    if not client.is_healthy():
        raise RuntimeError(f"Fish Speech server is not reachable at {client.cfg.health_url}")

    made = 0
    by_id = {item["id"]: item for item in manifest["items"]}
    cell_meta = cells_by_id(manifest.get("cells", []))
    for item in manifest["items"]:
        current = item.get("audio_path")
        if current and (args.output_dir / current).exists():
            continue
        if args.audio_limit and made >= args.audio_limit:
            break

        cell = cell_meta.get(str(item.get("cell_id")), {})
        emotion = str(cell.get("emotion") or item.get("emotion") or "Neutral")
        intent = str(cell.get("intent") or item.get("intent") or "ACKNOWLEDGE")
        style_tag = str(cell.get("style_tag") or item.get("style_tag") or "")
        synth_item = {**item, "emotion": emotion, "intent": intent, "style_tag": style_tag}

        cell_audio_dir = audio_root / emotion / intent / style_tag
        cell_audio_dir.mkdir(parents=True, exist_ok=True)
        original_output_dir = client.cfg.output_dir
        object.__setattr__(client.cfg, "output_dir", cell_audio_dir)
        try:
            audio_path = client.synthesize_to_file(synthesis_text_for_item(synth_item), prefix=item["id"])
        finally:
            object.__setattr__(client.cfg, "output_dir", original_output_dir)

        rel_audio = audio_path.relative_to(args.output_dir).as_posix()
        item["audio_path"] = rel_audio
        by_id[item["id"]]["audio_path"] = rel_audio
        made += 1
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"audio {made}: {item['id']} -> {audio_path}")

    print(f"synthesized_audio={made}")


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest = build_text_bundle(args, manifest_path)
    if args.synthesize:
        synthesize_missing_audio(args, manifest, manifest_path)
    print(f"Wrote persona reaction bundle: {manifest_path}")
    print(f"items={len(manifest['items'])}, cells={len(manifest['cells'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
