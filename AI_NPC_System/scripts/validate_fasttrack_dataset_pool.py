#!/usr/bin/env python3
"""Validate the separated FastTrack dataset pool used by router v3."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = ROOT / "fasttrack_assets" / "text" / "professor_lab_maid_dataset_pool_v1" / "pool.json"
EMOTIONS = ("POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL")
RESPONSE_ACTS = ("INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")
BAD_RE = re.compile(
    r"(?i)(\?|peko|haha|ahaha|lol|lmao|fuck|shit|idiot|retard|porn|sex|reddit|youtube|subreddit|#[A-Za-z])"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate separated FastTrack dataset pool.")
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--min-go-per-label", type=int, default=120)
    parser.add_argument("--min-swda-per-label", type=int, default=50)
    return parser.parse_args()


def scan_bucket(items: list[dict], label: str, source: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item.get("text") or "").strip()
        if not text:
            errors.append(f"{source}:{label}:{item.get('id')} empty text")
        if BAD_RE.search(text):
            errors.append(f"{source}:{label}:{item.get('id')} blocked text: {text}")
        dedupe = text.lower()
        if dedupe in seen:
            errors.append(f"{source}:{label}:{item.get('id')} duplicate text: {text}")
        seen.add(dedupe)
    return errors


def main() -> int:
    args = parse_args()
    payload = json.loads(args.pool.read_text(encoding="utf-8"))
    errors: list[str] = []
    go = payload.get("go_emotions", {}).get("buckets", {})
    swda = payload.get("swda", {}).get("buckets", {})
    if payload.get("architecture", {}).get("separate_source_datasets") is not True:
        errors.append("architecture.separate_source_datasets must be true")
    if "QUESTION" in swda and swda["QUESTION"]:
        errors.append("SWDA QUESTION bucket must be absent or empty")
    for label in EMOTIONS:
        items = list(go.get(label, []))
        if len(items) < args.min_go_per_label:
            errors.append(f"go_emotions:{label} too small: {len(items)}")
        errors.extend(scan_bucket(items, label, "go_emotions"))
    for label in RESPONSE_ACTS:
        items = list(swda.get(label, []))
        if len(items) < args.min_swda_per_label:
            errors.append(f"swda:{label} too small: {len(items)}")
        errors.extend(scan_bucket(items, label, "swda"))
    if errors:
        print("FAILED")
        for error in errors[:80]:
            print(f"- {error}")
        if len(errors) > 80:
            print(f"... {len(errors) - 80} more")
        return 1
    print("OK")
    print(f"pool={args.pool}")
    print(f"go_emotions={sum(len(go.get(label, [])) for label in EMOTIONS)}")
    print(f"swda={sum(len(swda.get(label, [])) for label in RESPONSE_ACTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
