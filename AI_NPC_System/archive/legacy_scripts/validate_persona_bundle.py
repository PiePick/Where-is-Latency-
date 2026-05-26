#!/usr/bin/env python3
"""Validate a CREDO persona reaction bundle for runtime and experiment use."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent


EXPECTED_EMOTIONS = {"Positive", "Negative", "Surprise", "Neutral"}
EXPECTED_RESPONSE_ACTS = {"INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT"}
EXPECTED_STYLE_TAGS: set[str] = set()
EXPECTED_VARIANTS_PER_CELL = 25
QUESTION_LIKE_RE = re.compile(
    r"(?i)(\?|"
    r"\b(?:what|why|how|who|when|where)\b|"
    r"\b(?:can|could|would|will|do|did|does)\s+you\b|"
    r"\bare you\b|\bis it\b|\btell me\b)"
)

EMOTIVE_NOISE_RE = re.compile(
    r"(?ix)"
    r"(\b(?:ha[-\s]*){2,}h?\b|\bahaha+\b|\bhaha+\b|\bhehe+\b|\blol\b|\blmao\b|\brofl\b)"
    r"|[😂🤣😀😅😊😍🥲😭😡😳✨]"
    r"|(?:^|\s)(?:[:;=xX]-?[)(DPpOo/])(?:$|\s)"
)

UNSAFE_RE = re.compile(
    r"(?ix)\b("
    r"fuck|shit|bitch|asshole|slut|porn|sex|sexy|nude|nsfw|hentai|rape"
    r")\b"
)

SPECIFIC_CONTENT_RE = re.compile(
    r"(?ix)"
    r"(https?://|www\.|[@#][A-Za-z0-9_]+|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b"
    r"|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"|[$€£¥]\s*\d|\b\d+(?:\.\d+)?\s*(?:percent|%)\b"
    r"|\b(?:president|senator|minister|parliament|congress|election|campaign|court|lawsuit|trial)\b"
    r"|\b(?:facebook|twitter|x\.com|youtube|tiktok|instagram|reddit|netflix|disney|google|microsoft|apple|amazon)\b"
)

FRAGMENT_END_RE = re.compile(
    r"(?i)\b(?:a|an|and|any|are|at|but|can|could|do|does|did|else|ever|for|from|if|in|is|"
    r"just|like|of|on|or|really|say|so|that|the|then|to|try|uh|um|well|what|with|would)\s*[?.!]*$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a CREDO persona reaction bundle.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "fasttrack_assets" / "text" / "pekora_reaction_bundle_v1" / "manifest.json",
    )
    parser.add_argument("--expected-reference-id", default="")
    parser.add_argument("--expected-personality-id", default="usada_pekora_v1")
    parser.add_argument("--expected-variants-per-cell", type=int, default=EXPECTED_VARIANTS_PER_CELL)
    parser.add_argument("--write-json", type=Path, default=ROOT / "reports" / "persona_bundle_validation_latest.json")
    parser.add_argument("--write-md", type=Path, default=ROOT / "reports" / "persona_bundle_validation_latest.md")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as failures.")
    parser.add_argument("--require-audio", action="store_true", help="Fail if a legacy prebuilt-audio item is unavailable.")
    return parser.parse_args()


def resolve_audio_path(manifest_path: Path, raw_path: str) -> Path:
    path = Path(str(raw_path or ""))
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def validate(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.manifest.resolve()
    failures: list[str] = []
    warnings: list[str] = []

    if not manifest_path.exists():
        return {
            "status": "FAIL",
            "manifest": str(manifest_path),
            "failures": [f"manifest missing: {manifest_path}"],
            "warnings": [],
        }

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cells = payload.get("cells", [])
    items = payload.get("items", [])
    dimensions = payload.get("dimensions", {})

    expected_reference = args.expected_reference_id.strip()
    reference_id = str((payload.get("tts_reference") or {}).get("reference_id") or "").strip()
    if expected_reference and reference_id != expected_reference:
        failures.append(f"reference mismatch: manifest={reference_id!r}, expected={expected_reference!r}")

    expected_personality = args.expected_personality_id.strip()
    personality_id = str(payload.get("personality_id") or "").strip()
    if expected_personality and personality_id != expected_personality:
        failures.append(f"personality mismatch: manifest={personality_id!r}, expected={expected_personality!r}")

    emotions = set(dimensions.get("emotions") or [])
    response_acts = set(dimensions.get("response_acts") or dimensions.get("intents") or [])
    style_tags = set(dimensions.get("style_tags") or [])
    if emotions != EXPECTED_EMOTIONS:
        failures.append(f"unexpected emotions: {sorted(emotions)}")
    if response_acts != EXPECTED_RESPONSE_ACTS:
        failures.append(f"unexpected response acts: {sorted(response_acts)}")
    if style_tags != EXPECTED_STYLE_TAGS:
        failures.append(f"unexpected style tags: {sorted(style_tags)}")

    style_multiplier = max(1, len(EXPECTED_STYLE_TAGS))
    expected_cell_count = len(EXPECTED_EMOTIONS) * len(EXPECTED_RESPONSE_ACTS) * style_multiplier
    if len(cells) != expected_cell_count:
        failures.append(f"cell count mismatch: got={len(cells)}, expected={expected_cell_count}")

    item_by_id = {str(item.get("id")): item for item in items}
    audio_exists = 0
    missing_audio: list[str] = []
    specific_text: list[str] = []
    fragment_text: list[str] = []
    question_like_text: list[str] = []
    emotive_noise_text: list[str] = []
    unsafe_text: list[str] = []
    duplicate_texts: Counter[str] = Counter()
    cell_counts: dict[str, int] = {}
    style_counts: Counter[str] = Counter()
    emotion_counts: Counter[str] = Counter()
    response_act_counts: Counter[str] = Counter()

    cell_meta = {str(cell.get("cell_id")): cell for cell in cells}
    for cell in cells:
        cell_id = str(cell.get("cell_id"))
        item_ids = [str(item_id) for item_id in cell.get("item_ids", [])]
        cell_counts[cell_id] = len(item_ids)
        if len(item_ids) != args.expected_variants_per_cell:
            failures.append(f"{cell_id}: item count {len(item_ids)} != {args.expected_variants_per_cell}")
        for item_id in item_ids:
            if item_id not in item_by_id:
                failures.append(f"{cell_id}: missing item id {item_id}")

    for item in items:
        cell_id = str(item.get("cell_id"))
        cell = cell_meta.get(cell_id, {})
        emotion = str(item.get("emotion") or cell.get("emotion") or "")
        response_act = str(item.get("response_act") or cell.get("response_act") or item.get("intent") or "")
        style_tag = str(item.get("style_tag") or cell.get("style_tag") or "")
        text = clean_text(item.get("reaction") or item.get("plain_tts_text") or "")
        item_id = str(item.get("id"))

        emotion_counts[emotion] += 1
        response_act_counts[response_act] += 1
        style_counts[style_tag] += 1
        duplicate_texts[text.lower()] += 1

        if not text:
            failures.append(f"{item_id}: empty reaction text")
        if response_act.upper() == "QUESTION":
            failures.append(f"{item_id}: QUESTION response act is disallowed for FastTrack")
        if QUESTION_LIKE_RE.search(text):
            question_like_text.append(item_id)
        if EMOTIVE_NOISE_RE.search(text):
            emotive_noise_text.append(item_id)
        if UNSAFE_RE.search(text):
            unsafe_text.append(item_id)
        if text and not text.endswith((".", "!", "?")):
            warnings.append(f"{item_id}: reaction does not end with sentence punctuation")
        if SPECIFIC_CONTENT_RE.search(text):
            specific_text.append(item_id)
        if FRAGMENT_END_RE.search(text):
            fragment_text.append(item_id)

        raw_audio_path = str(item.get("audio_path") or "").strip()
        if raw_audio_path:
            audio_path = resolve_audio_path(manifest_path, raw_audio_path)
            if audio_path.exists():
                audio_exists += 1
            else:
                missing_audio.append(item_id)

    if args.require_audio and (missing_audio or audio_exists != len(items)):
        failures.append(f"missing audio files: {len(missing_audio)}")
    if specific_text:
        warnings.append(f"specific-content filter hits: {len(specific_text)}")
    if fragment_text:
        warnings.append(f"fragment-like endings: {len(fragment_text)}")
    if question_like_text:
        failures.append(f"question-like FastTrack texts: {len(question_like_text)}")
    if emotive_noise_text:
        failures.append(f"emotive-noise FastTrack texts: {len(emotive_noise_text)}")
    if unsafe_text:
        failures.append(f"unsafe FastTrack texts: {len(unsafe_text)}")

    repeated = {text: count for text, count in duplicate_texts.items() if text and count > 1}
    if repeated:
        warnings.append(f"duplicate reaction texts: {len(repeated)}")

    status = "FAIL" if failures else ("WARN" if warnings else "OK")
    return {
        "status": status,
        "manifest": str(manifest_path),
        "version": payload.get("version"),
        "reference_id": reference_id,
        "personality_id": personality_id,
        "cells": len(cells),
        "items": len(items),
        "audio_exists": audio_exists,
        "missing_audio": missing_audio[:20],
        "specific_text_item_ids": specific_text[:20],
        "fragment_text_item_ids": fragment_text[:20],
        "question_like_text_item_ids": question_like_text[:20],
        "emotive_noise_text_item_ids": emotive_noise_text[:20],
        "unsafe_text_item_ids": unsafe_text[:20],
        "duplicate_text_examples": list(repeated.items())[:20],
        "emotion_counts": dict(sorted(emotion_counts.items())),
        "response_act_counts": dict(sorted(response_act_counts.items())),
        "style_counts": dict(sorted(style_counts.items())),
        "failures": failures,
        "warnings": warnings,
    }


def write_reports(result: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Persona Bundle Validation",
        "",
        f"- status: {result['status']}",
        f"- manifest: `{result['manifest']}`",
        f"- version: `{result.get('version')}`",
        f"- reference_id: `{result.get('reference_id')}`",
        f"- personality_id: `{result.get('personality_id')}`",
        f"- cells: {result.get('cells')}",
        f"- items: {result.get('items')}",
        f"- audio_exists: {result.get('audio_exists')}",
        "",
        "## Failures",
    ]
    failures = result.get("failures") or []
    lines.extend([f"- {item}" for item in failures] or ["- none"])
    lines.append("")
    lines.append("## Warnings")
    warnings = result.get("warnings") or []
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.append("")
    lines.append("## Counts")
    for key in ("emotion_counts", "response_act_counts", "style_counts"):
        lines.append(f"### {key}")
        for name, count in (result.get(key) or {}).items():
            lines.append(f"- `{name}`: {count}")
        lines.append("")
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    result = validate(args)
    write_reports(result, args.write_json, args.write_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "FAIL":
        return 1
    if args.strict and result["status"] == "WARN":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
