#!/usr/bin/env python3
"""Build separated filtered FastTrack dataset pools.

This does not create a prewritten persona reaction manifest. It keeps the two
source datasets physically separate:

- GoEmotions: emotion-grounded text evidence.
- SWDA: response-act-grounded text evidence, with QUESTION excluded.

Runtime routing combines the selected labels and retrieved evidence on demand.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GO_EMOTIONS = ROOT / "fasttrack_assets" / "datasets" / "prepared_fasttrack_data" / "go_emotions_coarse.jsonl"
DEFAULT_SWDA = ROOT / "fasttrack_assets" / "datasets" / "prepared_fasttrack_data" / "swda_intent_coarse.jsonl"
DEFAULT_OUTPUT = ROOT / "fasttrack_assets" / "text" / "professor_lab_maid_dataset_pool_v1" / "pool.json"

EMOTION_LABELS = ("POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL")
RESPONSE_ACT_LABELS = ("INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")
DISALLOWED_RESPONSE_ACTS = {"QUESTION"}

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
PUNCT_SPACE_RE = re.compile(r"\s+([?.!,;:])")
SWDA_MARKER_RE = re.compile(r"^(?:[A-Z]\s+){1,3}")
EMOTICON_RE = re.compile(r"[:;=xX][-']?[)(DPpOo/]|[()']\s*[vV]\s*[()']")
EMOTIVE_NOISE_RE = re.compile(
    r"(?ix)"
    r"(\b(?:ha[-\s]*){2,}h?\b|\bah!|\bahaha+\b|\bhaha+\b|\bhehe+\b|\blol\b|\blmao\b|\brofl\b|\blaugh(?:s|ed|ing)?\b)"
    r"|[😂🤣😀😅😊😍🥲😭😡😳✨]"
)
FILLER_START_RE = re.compile(r"(?i)^\s*(?:ah|oh|uh|um|er|hmm|hm)\b")
LOW_QUALITY_SOURCE_NOISE_RE = re.compile(
    r"(?ix)"
    r"\b(?:dont|cant|wont|thats|im|ive|ill|omg|huh|ye|kinda|trolling|spidey|cookies|trinity)\b"
    r"|\bvaccin\w*\b|\bgood\s+luck\b|\bno\s+idea\b|;;|!{2,}"
    r"|\b(?:talking|conversation|speaking|calling|phone|current\s+events|pleasant\s+evening|good\s+day|so\s+long|my\s+pleasure)\b"
    r"|\b(?:talk\s+(?:to|with)\s+you|good\s+to\s+hear\s+from\s+you|nice\s+to\s+talk\s+to\s+you)\b"
    r"|\b(?:enjoyed\s+(?:this|it|our|talk|talking)|exhausted\s+everything|that'?s\s+about\s+all|think\s+that\s+covers)\b"
    r"|\b(?:same\s+weather|where\s+you\s+are|coughing|doing\s+fine|i'?m\s+great|trying\s+to\s+think\s+of\s+the\s+name)\b"
    r"|\b(?:getting\s+help|what\s+was\s+wondering)\b"
    r"|\b(?:read|story|person|people|drive|driver|over\s+there|allowed\s+to\s+drive)\b"
    r"|\bii\s+can'?t\b"
    r"|\bworked\s+out\s+real\s+good\b"
    r"|\b(?:covered\s+all\s+the\s+bases|let\s+you\s+go|take\s+good\s+care|another\s+line\s+calling|time\s+is\s+up|we\s+can\s+quit)\b"
    r"|\b(?:furnace|lake|grass|consumer\s+guide|statistical\s+analysis|item\s+analysis|favorable|younger|we'?re\s+north)\b"
    r"|\b(?:ma'am|sir)\b"
    r"|^\s*(?:well,?\s*)?(?:yes|yeah|okay|really|you\s+too)\b"
    r"|^\s*(?:very\s+faint|my\s+word|that\s+right|ta,|i,\s*i,)"
    r"|^\s*,\s*oh,\s*see\b"
    r"|^that'?s\s+right,\s*yes\b"
    r"|^\s*\.?\s*that's\s+true\b"
    r"|^\s*well,?\s*(?:guess|i'?ve|it\s+was|it'?s\s+been|enjoyed|good|nice|we'?ll\s+be)"
    r"|^\s*(?:but|and|so),?\s*(?:no|yes|yeah|right|okay|ok)\b"
)
GREETING_RE = re.compile(
    r"(?ix)"
    r"\b(?:hi|hello|hey|howdy|hiya|yo|sup|welcome|nice\s+to\s+meet|pleased\s+to\s+meet|good\s+to\s+see)\b"
    r"|\b(?:good\s+morning|good\s+afternoon|good\s+evening|good\s+night|morning|afternoon|evening)\b"
    r"|\b(?:how\s+are\s+you|how\s+do\s+you\s+do|how(?:'| i)?s\s+it\s+going|what(?:'| i)?s\s+up|long\s+time\s+no\s+see)\b"
    r"|\b(?:goodbye|bye|see\s+you|we'?ll\s+see\s+you|nice\s+seeing\s+you|take\s+care|have\s+a\s+good(?:\s+day|\s+night|\s+evening|\s+weekend|\s+time)?)\b"
    r"|\b(?:thanks|thank\s+you|thankyou|you'?re\s+welcome|cheers|appreciate\s+it)\b"
)
UNSAFE_RE = re.compile(
    r"(?ix)\b("
    r"fuck|fucking|fucked|shit|bullshit|bitch|asshole|cunt|slut|porn|sex|sexy|nude|nsfw|"
    r"hentai|rape|sexual|assault|kill|killing|suicide|dead|death|cocaine|heroin|meth|weed|terrorist|nazi|racist|"
    r"idiot|idiots|dumbass|stupid|retard|retardation|disgusting|filth|miserable|"
    r"shitty|shitting|shithole|shite|fuckup|damn|goddamn|hell|pedo|pedos"
    r")\b"
)
SPECIFIC_CONTENT_RE = re.compile(
    r"(?ix)"
    r"(@[A-Za-z0-9_]+|\#[A-Za-z0-9_]+|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)"
    r"|\b(?:19|20)\d{2}\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b"
    r"|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"|[$€£¥]\s*\d|\b\d+(?:\.\d+)?\s*(?:percent|%)\b"
    r"|\b(?:president|senator|minister|parliament|congress|election|campaign|court|lawsuit|trial|republican|democrat|military)\b"
    r"|\b(?:facebook|twitter|x\.com|youtube|tiktok|instagram|reddit|netflix|disney|google|microsoft|apple|amazon)\b"
    r"|\b(?:pokemon|minecraft|fortnite|valorant|league of legends|genshin|hololive|twitch|nba|nfl|mlb|director|movie|film)\b"
    r"|\b(?:subreddit|subreddits|reddits|tworedditorsonecup|brigading|repo|post|comment|bot|doxing|dox|game|season|fishing|golf|television|stereo)\b"
    r"|\b(?:photo|picture|title|album|song|show|team|player|sports|shoe|leather|clown|cat|dog|animal|face|body)\b"
    r"|\b(?:uncle|couple|college|adhd|calories|universe|projection|admin|assistant|houston|mom|dad|daughter|children|kid|kids)\b"
)
CONTEXT_BOUND_RE = re.compile(
    r"(?ix)\b("
    r"he|he's|him|his|she|she's|her|hers|they|they're|them|their|theirs|that person|"
    r"my wife|my husband|my girlfriend|my boyfriend|your mom|your dad|your team|your friend|this guy|that guy"
    r")\b"
)
PERSONA_UNLIKELY_RE = re.compile(
    r"(?ix)\b("
    r"as an ai|language model|i am a bot|i'm a bot|subscribe|upvote|downvote|dm me|"
    r"i hate you|shut up|get out|go away|choose wisely|kneel|bladder|conspirac\w*|threatened|"
    r"dishes|day care|children|house|clicked this link"
    r")\b"
)
FRAGMENT_END_RE = re.compile(r"(?i)(?:[,;:-]|\b(?:and|but|or|so|because|if|when|while|that|the|a|an|to|of|for|with)\b)$")
QUESTION_START_RE = re.compile(r"(?i)^(?:oh,\s*)?(?:what|why|how|who|when|where|is|are|am|was|were|do|did|does|can|could|would|will|should)\b")
NUMBER_WORD_RE = re.compile(
    r"(?i)\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b"
)
COMMON_TITLECASE = {
    "I",
    "I'm",
    "I've",
    "I'd",
    "Okay",
    "Sure",
    "Really",
    "Wow",
    "Oh",
    "No",
    "Yes",
    "Maybe",
    "Happy",
    "Very",
    "Totally",
    "It",
    "So",
    "Well",
    "Good",
    "Great",
    "Nice",
    "Thanks",
    "Thank",
    "That",
    "This",
    "The",
    "A",
    "An",
}
ALLOWED_UPPERCASE = {"I", "OK", "TV"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build separated filtered FastTrack dataset pools.")
    parser.add_argument("--go-emotions", type=Path, default=DEFAULT_GO_EMOTIONS)
    parser.add_argument("--swda", type=Path, default=DEFAULT_SWDA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-per-label", type=int, default=320)
    parser.add_argument("--max-words", type=int, default=14)
    parser.add_argument("--max-chars", type=int, default=96)
    return parser.parse_args()


def normalize_text(text: str) -> str:
    text = URL_RE.sub("", str(text or ""))
    text = text.replace("\\/", "/").replace("/", " ")
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.replace("#", " ")
    text = re.sub(r"\b[A-Z]\s+(?:uh|um)\b", " ", text)
    text = re.sub(r"\b[A-Z]\s*-\s*", " ", text)
    text = re.sub(r"\b[A-Z]\b(?=\s|$)", " ", text)
    text = re.sub(r"\b(?:uh|um|er)\b[, ]*", " ", text, flags=re.IGNORECASE)
    text = SWDA_MARKER_RE.sub("", text.strip())
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r",\s*,+", ",", text)
    text = SPACE_RE.sub(" ", text).strip()
    text = PUNCT_SPACE_RE.sub(r"\1", text)
    return text.strip(" \t\r\n\"'")


def has_unwanted_proper_noun(text: str) -> bool:
    for token in re.findall(r"\b[A-Z][a-z]{2,}\b", text):
        if token in COMMON_TITLECASE:
            continue
        return True
    for token in re.findall(r"\b[A-Z]{2,}\b", text):
        if token not in ALLOWED_UPPERCASE:
            return True
    return False


def rejection_reason(text: str, *, max_words: int, max_chars: int) -> str | None:
    text = normalize_text(text)
    if not text:
        return "empty"
    if "?" in text:
        return "question_text"
    if len(text) > max_chars:
        return "too_long"
    words = WORD_RE.findall(text)
    if len(words) < 2:
        return "too_short"
    if len(words) > max_words:
        return "too_many_words"
    if text and text[0].islower():
        return "source_noise"
    if QUESTION_START_RE.search(text):
        return "question_like"
    if FRAGMENT_END_RE.search(text):
        return "fragment"
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return "non_ascii"
    if any(mark in text for mark in ("<", ">", "{", "}", "[", "]", "%")):
        return "markup_or_symbol"
    if any(mark in text for mark in ("(", ")", "*", "^")):
        return "markup_or_symbol"
    if any(ch.isdigit() for ch in text):
        return "numeric_or_specific"
    if NUMBER_WORD_RE.search(text):
        return "numeric_or_specific"
    if EMOTICON_RE.search(text) or EMOTIVE_NOISE_RE.search(text):
        return "emotive_noise"
    if FILLER_START_RE.search(text):
        return "emotive_noise"
    if LOW_QUALITY_SOURCE_NOISE_RE.search(text):
        return "source_noise"
    if GREETING_RE.search(text):
        return "greeting_or_closing_phrase"
    if UNSAFE_RE.search(text):
        return "unsafe"
    if SPECIFIC_CONTENT_RE.search(text):
        return "specific_or_topic_skewed"
    if CONTEXT_BOUND_RE.search(text):
        return "context_bound"
    if PERSONA_UNLIKELY_RE.search(text):
        return "persona_unlikely"
    if has_unwanted_proper_noun(text):
        return "proper_noun"
    return None


def quality_score(text: str, *, source_name: str, label: str) -> float:
    """Rank filtered candidates so clean general-purpose snippets appear first."""
    words = WORD_RE.findall(text)
    word_count = len(words)
    score = 0.0
    if 3 <= word_count <= 8:
        score += 4.0
    elif 2 <= word_count <= 12:
        score += 2.0
    if text.endswith((".", "!")):
        score += 2.0
    if text and text[0].isupper():
        score += 1.0
    if "," in text:
        score -= 1.25
    if "..." in text or ".." in text:
        score -= 1.5
    if re.search(r"(?i)\b(?:you|your|yours)\b", text):
        score -= 1.0
    if re.search(r"(?i)\b(?:thing|something|anything|that|this)\b", text):
        score += 0.5
    if source_name == "swda" and label == "ACKNOWLEDGE" and re.search(r"(?i)\b(?:okay|right|sure|yes|yeah|all right|got it)\b", text):
        score += 2.0
    if source_name == "swda" and label == "REJECT" and re.search(r"(?i)\b(?:no|not|don't|cannot|can't)\b", text):
        score += 2.0
    if source_name == "go_emotions" and label == "NEGATIVE" and re.search(r"(?i)\b(?:hard|rough|tired|worried|confusing|wrong|not)\b", text):
        score += 1.0
    return score


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_source_pool(
    *,
    source_name: str,
    path: Path,
    allowed_labels: tuple[str, ...],
    disallowed_labels: set[str],
    max_per_label: int,
    max_words: int,
    max_chars: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    candidates: dict[str, list[tuple[float, int, dict[str, Any]]]] = {label: [] for label in allowed_labels}
    seen_texts: set[str] = set()
    rejection_counts: Counter[str] = Counter()
    input_counts: Counter[str] = Counter()
    allowed_set = set(allowed_labels)

    for row_index, row in enumerate(read_jsonl(path)):
        label = str(row.get("coarse_label") or "").upper()
        input_counts[label] += 1
        if label in disallowed_labels:
            rejection_counts[f"disallowed_label:{label}"] += 1
            continue
        if label not in allowed_set:
            rejection_counts[f"unsupported_label:{label or 'EMPTY'}"] += 1
            continue

        text = normalize_text(str(row.get("text") or ""))
        reason = rejection_reason(text, max_words=max_words, max_chars=max_chars)
        if reason:
            rejection_counts[reason] += 1
            continue
        dedupe_key = text.lower()
        if dedupe_key in seen_texts:
            rejection_counts["duplicate_text"] += 1
            continue
        seen_texts.add(dedupe_key)
        item = {
            "text": text,
            "label": label,
            "source_dataset": source_name,
            "source": row.get("source") or source_name,
            **({"raw_dialog_act": row.get("raw_dialog_act")} if row.get("raw_dialog_act") else {}),
        }
        candidates[label].append(
            (quality_score(text, source_name=source_name, label=label), row_index, item)
        )

    buckets: dict[str, list[dict[str, Any]]] = {label: [] for label in allowed_labels}
    for label in allowed_labels:
        ranked = sorted(candidates[label], key=lambda item: (-item[0], item[1]))
        for index, (_score, _row_index, item) in enumerate(ranked[:max_per_label], start=1):
            item = dict(item)
            item["id"] = f"{source_name}_{label.lower()}_{index:04d}"
            buckets[label].append(item)
        if len(ranked) > max_per_label:
            rejection_counts[f"label_cap:{label}"] += len(ranked) - max_per_label

    report = {
        "path": str(path),
        "input_counts": dict(sorted(input_counts.items())),
        "kept_counts": {label: len(buckets[label]) for label in allowed_labels},
        "rejection_counts": dict(sorted(rejection_counts.items())),
    }
    return buckets, report


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    go_pool, go_report = build_source_pool(
        source_name="go_emotions",
        path=args.go_emotions,
        allowed_labels=EMOTION_LABELS,
        disallowed_labels=set(),
        max_per_label=args.max_per_label,
        max_words=args.max_words,
        max_chars=args.max_chars,
    )
    swda_pool, swda_report = build_source_pool(
        source_name="swda",
        path=args.swda,
        allowed_labels=RESPONSE_ACT_LABELS,
        disallowed_labels=DISALLOWED_RESPONSE_ACTS,
        max_per_label=args.max_per_label,
        max_words=args.max_words,
        max_chars=args.max_chars,
    )
    return {
        "version": "credo-professor-lab-maid-separated-dataset-pool-v1",
        "created_at_unix": int(time.time()),
        "personality_id": "professor_lab_maid_v1",
        "personality_name": "Professor's Lab Maid",
        "architecture": {
            "static_reaction_manifest": False,
            "separate_source_datasets": True,
            "runtime_composition": True,
            "note": (
                "GoEmotions and SWDA are filtered and indexed separately. "
                "Runtime routing retrieves emotion evidence from GoEmotions and response-act evidence from SWDA, "
                "then composes a short lab-maid FastTrack line on demand."
            ),
        },
        "filter_policy": [
            "exclude proper nouns, brand names, social-platform references, dates, numbers, and topic-skewed content",
            "exclude profanity, sexual wording, violent wording, and unsafe content",
            "exclude emoticons, emoji, long laughter tokens, and explicit emotional noise",
            "exclude question text from both pools and exclude QUESTION as a response act",
            "exclude context-bound utterances that rely on specific people or outside conversation history",
        ],
        "go_emotions": {
            "role": "emotion_text_evidence",
            "labels": list(EMOTION_LABELS),
            "buckets": go_pool,
            "report": go_report,
        },
        "swda": {
            "role": "response_act_text_evidence",
            "labels": list(RESPONSE_ACT_LABELS),
            "excluded_labels": sorted(DISALLOWED_RESPONSE_ACTS),
            "buckets": swda_pool,
            "report": swda_report,
        },
    }


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    go_counts = payload["go_emotions"]["report"]["kept_counts"]
    swda_counts = payload["swda"]["report"]["kept_counts"]
    print(f"Wrote separated FastTrack dataset pool: {args.output}")
    print(f"go_emotions={go_counts}")
    print(f"swda={swda_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
