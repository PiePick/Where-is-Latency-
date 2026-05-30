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
    r"(?ix)("
    r"\?|(?-i:^[a-z])|peko|\bah!|\bhaha\b|\bahaha\b|\blol\b|\blmao\b|\bhm\.|\bugh\.|\blaugh(?:s|ed|ing)?\b|"
    r"^\s*(?:ah|oh|uh|um|er|hmm|hm)\b|[()*^]|;;|!{2,}|"
    r"\b(?:dont|cant|wont|thats|im|ive|ill|omg|huh|ye|kinda|trolling|spidey|cookies|trinity)\b|"
    r"\bvaccin\w*\b|\bgood\s+luck\b|\bno\s+idea\b|"
    r"\b(?:talking|conversation|speaking|calling|phone|current\s+events|pleasant\s+evening|good\s+day|so\s+long|my\s+pleasure)\b|"
    r"\b(?:talk\s+(?:to|with)\s+you|good\s+to\s+hear\s+from\s+you|nice\s+to\s+talk\s+to\s+you)\b|"
    r"\b(?:enjoyed\s+(?:this|it|our|talk|talking)|exhausted\s+everything|that'?s\s+about\s+all|think\s+that\s+covers)\b|"
    r"\b(?:same\s+weather|where\s+you\s+are|coughing|doing\s+fine|i'?m\s+great|trying\s+to\s+think\s+of\s+the\s+name)\b|"
    r"\b(?:getting\s+help|what\s+was\s+wondering)\b|"
    r"\b(?:read|story|person|people|drive|driver|over\s+there|allowed\s+to\s+drive)\b|"
    r"\bii\s+can'?t\b|"
    r"\bworked\s+out\s+real\s+good\b|"
    r"\b(?:covered\s+all\s+the\s+bases|let\s+you\s+go|take\s+good\s+care|another\s+line\s+calling|time\s+is\s+up|we\s+can\s+quit)\b|"
    r"\b(?:furnace|lake|grass|consumer\s+guide|statistical\s+analysis|item\s+analysis|favorable|younger|we'?re\s+north)\b|"
    r"\b(?:ma'am|sir)\b|"
    r"^\s*(?:well,?\s*)?(?:yes|yeah|okay|really|you\s+too)\b|"
    r"^\s*(?:very\s+faint|my\s+word|that\s+right|ta,|i,\s*i,)|"
    r"^\s*,\s*oh,\s*see\b|"
    r"^that'?s\s+right,\s*yes\b|"
    r"^\s*\.?\s*that's\s+true\b|"
    r"^\s*well,?\s*(?:guess|i'?ve|it\s+was|it'?s\s+been|enjoyed|good|nice|we'?ll\s+be)|"
    r"^\s*(?:but|and|so),?\s*(?:no|yes|yeah|right|okay|ok)\b|"
    r"\bfuck\b|\bshit\b|\bdamn\b|\bhell\b|idiot|retard|porn|sex|"
    r"reddit|youtube|subreddit|\#[A-Za-z]|"
    r"\b(?:hi|hello|hey|howdy|hiya|yo|sup|welcome|nice\s+to\s+meet|pleased\s+to\s+meet|good\s+to\s+see|"
    r"good\s+morning|good\s+afternoon|good\s+evening|good\s+night|morning|afternoon|evening|"
    r"how\s+are\s+you|how\s+do\s+you\s+do|how(?:'| i)?s\s+it\s+going|what(?:'| i)?s\s+up|long\s+time\s+no\s+see|"
    r"goodbye|bye|see\s+you|nice\s+seeing\s+you|take\s+care|have\s+a\s+good|thanks|thank\s+you|"
    r"you'?re\s+welcome|cheers|appreciate\s+it)\b|"
    r"\b(?:photo|picture|title|movie|film|show|game|album|song|team|player|guy|wife|husband|"
    r"boyfriend|girlfriend|cat|dog|shoe|leather|clown)\b"
    r")"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate separated FastTrack dataset pool.")
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--min-go-per-label", type=int, default=20)
    parser.add_argument("--min-swda-per-label", type=int, default=3)
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
