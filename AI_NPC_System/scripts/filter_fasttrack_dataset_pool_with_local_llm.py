#!/usr/bin/env python3
"""Curate the active separated FastTrack dataset pool with the local LLM.

The active FastTrack language source is not a persona manifest. It is the
separated GoEmotions/SWDA dataset pool, so this script removes unsuitable
candidate text from those two pools while keeping their provenance separate.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL = ROOT / "fasttrack_assets" / "text" / "professor_lab_maid_dataset_pool_v1" / "pool.json"
DEFAULT_PREBUILT_MANIFEST = ROOT / "fasttrack_assets" / "audio" / "prebuilt_stylebert_v1" / "manifest.json"
DEFAULT_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
DEFAULT_MODEL = "qwen2.5:7b"

SYSTEM_PROMPT = """You are a conservative curation judge for CREDO AI VTuber FastTrack dataset candidates.
The candidate may be spoken as a very short live-stream reaction by a cute professor's lab maid character.

Reject any candidate that is not a clean standalone FastTrack reaction for arbitrary VTuber live chat.
Problems include:
- too specific to unseen media, one-off internet posts, photos, titles, games, food, clothes, family, politics, brands, places, dates, or private life
- body parts, animals, objects, props, vehicles, homework, ads, slogans, call/phone closings, or niche internet/community references
- unclear without hidden context, malformed, unfinished, typo-garbled, or semantically incoherent
- profanity, sexual wording, violent/self-harm wording, hateful wording, insults, medical/legal advice, or risky content
- explicit laughter/filler/emoticon/emoji text such as haha, lol, lmao, ahaha, ha!, hm, ugh, or emoji
- question text, because FastTrack must not answer with a question
- bare acknowledgements or call closings such as "Well, no.", "well, yeah.", "good talking to you", or "thanks for calling"

Keep generic reusable short reactions even if plain:
"This is not good.", "That is really weird.", "This is so true.", "That was brutal.",
"That sounds good.", "That's not always possible.", "Go right ahead.", "I'm so sorry."

Do not reject a candidate just because it uses "this", "that", "it", "thing", "problem", or "method".
Return only strict compact JSON using candidate numbers:
{"reject":[{"n":0,"reason":"short reason"}]}."""

SURFACE_REJECT_RE = re.compile(
    r"(?ix)"
    r"\?"
    r"|(?-i:^[a-z])"
    r"|[()*^]"
    r"|;;"
    r"|!{2,}"
    r"|\b(?:dont|cant|wont|thats|im|ive|ill|omg|huh|ye|kinda|trolling|spidey|cookies|trinity)\b"
    r"|\bvaccin\w*\b"
    r"|\bgood\s+luck\b"
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
    r"|\bno\s+idea\b"
    r"|^\s*(?:but|and|so),?\s*(?:no|yes|yeah|right|okay|ok)\b"
    r"|^\s*(?:ah|oh|uh|um|er|hmm|hm)\b"
    r"|\b(?:haha|ahaha|lol|lmao|rofl|ha!|hm\.|ugh\.|hee-hee|oh!|aw!)"
    r"|\b(?:laugh|laughs|laughed|laughing)\b"
    r"|\b(?:fuck|shit|damn|hell|goddamn|pedos?|porn|sex|sexy|suicide|kill|dead|death)\b"
    r"|\b(?:guy|guys|lady|wife|husband|wifey|boyfriend|girlfriend|mom|dad|daughter|children|kid|kids)\b"
    r"|\b(?:photo|picture|title|movie|film|show|game|album|song|team|player|sports|shoe|leather|clown|cat|dog)\b"
    r"|[$€£¥]\s*\d"
)
GREETING_REJECT_RE = re.compile(
    r"(?ix)"
    r"\b(?:hi|hello|hey|howdy|hiya|yo|sup|welcome|nice\s+to\s+meet|pleased\s+to\s+meet|good\s+to\s+see)\b"
    r"|\b(?:good\s+morning|good\s+afternoon|good\s+evening|good\s+night|morning|afternoon|evening)\b"
    r"|\b(?:how\s+are\s+you|how\s+do\s+you\s+do|how(?:'| i)?s\s+it\s+going|what(?:'| i)?s\s+up|long\s+time\s+no\s+see)\b"
    r"|\b(?:goodbye|bye|see\s+you|we'?ll\s+see\s+you|nice\s+seeing\s+you|take\s+care|have\s+a\s+good(?:\s+day|\s+night|\s+evening|\s+weekend|\s+time)?)\b"
    r"|\b(?:thanks|thank\s+you|thankyou|you'?re\s+welcome|cheers|appreciate\s+it)\b"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(text: str) -> str:
    return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())


def item_text(item: dict[str, Any]) -> str:
    return clean_text(str(item.get("text") or ""))


def is_generic_rescue(text: str) -> bool:
    normalized = clean_text(text).lower().strip('"')
    if normalized in {
        "this is not good.",
        "this is so true.",
        "that is really weird.",
        "that was brutal.",
        "that sounds good.",
        "that's not always possible.",
        "go right ahead.",
        "i'm so sorry.",
        "that sounds real good.",
        "that would be really good.",
        "that is right.",
        "that's right, yes.",
    }:
        return True
    return bool(
        re.fullmatch(
            r"(this|that|it|the answer|this answer|that answer)( is|'s| was| sounds)? ?"
            r"(not )?(good|bad|funny|weird|true|brutal|awesome|great|interesting|possible)"
            r"( though)?[.!]*",
            normalized,
        )
    )


def flatten_pool(pool: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_key in ("go_emotions", "swda"):
        source = pool.get(source_key, {})
        buckets = source.get("buckets", {}) if isinstance(source, dict) else {}
        for label, items in buckets.items():
            for item in items or []:
                row = dict(item or {})
                row["_source_key"] = source_key
                row["_label"] = str(label)
                row["_id"] = str(row.get("id") or "")
                rows.append(row)
    return rows


def surface_rejections(items: list[dict[str, Any]]) -> dict[str, str]:
    rejected: dict[str, str] = {}
    for item in items:
        text = item_text(item)
        if SURFACE_REJECT_RE.search(text):
            rejected[str(item["_id"])] = "surface_specific_or_unsuitable"
        elif GREETING_REJECT_RE.search(text):
            rejected[str(item["_id"])] = "greeting_or_closing_phrase"
    return rejected


def prebuilt_missing_rejections(items: list[dict[str, Any]], manifest_path: Path) -> dict[str, str]:
    """Remove pool rows whose derived prebuilt audio asset is no longer usable."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"prebuilt manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    available_source_ids: set[str] = set()
    manifest_root = manifest_path.parent
    for item in manifest.get("items", []) or []:
        source_item_id = str(item.get("source_item_id") or "")
        if not source_item_id:
            continue
        audio_path = Path(str(item.get("audio_path") or ""))
        if audio_path and not audio_path.is_absolute():
            audio_path = manifest_root / audio_path
        if audio_path.exists():
            available_source_ids.add(source_item_id)
    return {
        str(item["_id"]): "prebuilt_audio_missing_for_dataset_item"
        for item in items
        if str(item.get("_id") or "") not in available_source_ids
    }


def json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def build_user_prompt(batch: list[dict[str, Any]]) -> str:
    lines = ["Judge these dataset candidates. Reject only clear problems.", "Candidates:"]
    for index, item in enumerate(batch):
        lines.append(
            f"- n={index}; dataset={item['_source_key']}; label={item['_label']}; "
            f"text={json.dumps(item_text(item), ensure_ascii=False)}"
        )
    return "\n".join(lines)


def call_llm(args: argparse.Namespace, batch: list[dict[str, Any]]) -> dict[str, str]:
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(batch)},
        ],
        "temperature": 0,
        "max_tokens": args.max_tokens,
    }
    request = urllib.request.Request(
        args.llm_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Local LLM rejected batch: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local LLM unreachable at {args.llm_url}: {exc}") from exc

    content = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    parsed = json_from_text(content)
    rejected: dict[str, str] = {}
    for row in parsed.get("reject", []):
        if not isinstance(row, dict):
            continue
        try:
            index = int(row.get("n"))
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(batch):
            continue
        item = batch[index]
        text = item_text(item)
        if is_generic_rescue(text):
            continue
        rejected[str(item["_id"])] = str(row.get("reason") or "llm_rejected")[:200]
    return rejected


def batched(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def judge_all(args: argparse.Namespace, items: list[dict[str, Any]]) -> dict[str, str]:
    rejected = surface_rejections(items) if args.surface_prescreen else {}
    llm_items = [item for item in items if str(item["_id"]) not in rejected]
    batches = batched(llm_items, args.batch_size)
    for index, batch in enumerate(batches, start=1):
        for attempt in range(1, args.retries + 2):
            try:
                rejected.update(call_llm(args, batch))
                break
            except RuntimeError as exc:
                if attempt > args.retries:
                    raise
                print(f"retry batch {index}/{len(batches)} attempt={attempt}: {exc}")
                time.sleep(min(3.0, 0.5 * attempt))
        if index % args.progress_every == 0 or index == len(batches):
            print(f"judged {index}/{len(batches)} batches; rejected_so_far={len(rejected)}")
    return rejected


def apply_filter(pool_path: Path, pool: dict[str, Any], rejected: dict[str, str], report_dir: Path) -> dict[str, Any]:
    backup_path = report_dir / f"pool.before_llm_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy2(pool_path, backup_path)
    rejected_ids = set(rejected)
    removed: list[dict[str, Any]] = []

    for source_key in ("go_emotions", "swda"):
        buckets = pool.get(source_key, {}).get("buckets", {})
        for label, items in list(buckets.items()):
            kept = []
            for item in items or []:
                item_id = str(item.get("id") or "")
                if item_id in rejected_ids:
                    removed_item = dict(item)
                    removed_item["dataset"] = source_key
                    removed_item["label"] = label
                    removed_item["llm_filter_reason"] = rejected[item_id]
                    removed.append(removed_item)
                else:
                    kept.append(item)
            buckets[label] = kept

    pool["llm_quality_filter"] = {
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "removed_items": len(removed),
        "backup_pool": str(backup_path),
        "criteria": [
            "general-purpose live-stream reuse",
            "no hidden-context dependency",
            "no question output",
            "no explicit filler/laughter/emoticon text",
            "no unsafe or overly specific content",
        ],
    }
    for source_key in ("go_emotions", "swda"):
        report = pool.get(source_key, {}).get("report")
        buckets = pool.get(source_key, {}).get("buckets", {})
        if isinstance(report, dict):
            report["kept_counts_after_llm_filter"] = {
                label: len(items or []) for label, items in buckets.items()
            }
    write_json(pool_path, pool)
    return {"backup_path": str(backup_path), "removed": removed}


def summarize(items: list[dict[str, Any]], rejected: dict[str, str]) -> dict[str, Any]:
    by_id = {str(item["_id"]): item for item in items}
    removed = [by_id[item_id] for item_id in rejected if item_id in by_id]
    return {
        "items_before": len(items),
        "rejected": len(removed),
        "removal_ratio": round((len(removed) / len(items)) if items else 0.0, 6),
        "by_dataset": dict(Counter(str(item["_source_key"]) for item in removed)),
        "by_label": dict(Counter(f"{item['_source_key']}:{item['_label']}" for item in removed)),
        "examples": [
            {
                "id": str(item["_id"]),
                "dataset": str(item["_source_key"]),
                "label": str(item["_label"]),
                "reason": rejected.get(str(item["_id"]), ""),
                "text": item_text(item),
            }
            for item in removed[:80]
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--prebuilt-manifest", type=Path, default=DEFAULT_PREBUILT_MANIFEST)
    parser.add_argument("--llm-url", default=DEFAULT_LLM_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--max-removal-ratio", type=float, default=0.35)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force-large-removal", action="store_true")
    parser.add_argument("--surface-prescreen", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--surface-only",
        action="store_true",
        help="Apply only deterministic surface rules without calling the local LLM.",
    )
    parser.add_argument(
        "--require-prebuilt-manifest",
        action="store_true",
        help="Also remove pool rows that no longer have a usable derived prebuilt audio asset.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "reports" / f"fasttrack_dataset_pool_llm_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pool_path = args.pool.resolve()
    pool = read_json(pool_path)
    items = flatten_pool(pool)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    if args.surface_only:
        rejected = surface_rejections(items)
    else:
        rejected = judge_all(args, items)
    if args.require_prebuilt_manifest:
        missing = prebuilt_missing_rejections(items, args.prebuilt_manifest.resolve())
        rejected.update({item_id: reason for item_id, reason in missing.items() if item_id not in rejected})
    summary = summarize(items, rejected)
    summary.update(
        {
            "pool": str(pool_path),
            "apply": bool(args.apply),
            "model": args.model,
            "llm_url": args.llm_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_json(args.report_dir / "summary.json", summary)

    lines = [
        "# FastTrack Dataset Pool LLM Filter",
        "",
        f"- Pool: `{pool_path}`",
        f"- Items before: {summary['items_before']}",
        f"- Rejected: {summary['rejected']}",
        f"- Removal ratio: {summary['removal_ratio']:.2%}",
        f"- Applied: {bool(args.apply)}",
        "",
        "| Dataset | Label | ID | Reason | Text |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in summary["examples"]:
        text = str(item["text"]).replace("|", "/")
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append(
            f"| {item['dataset']} | {item['label']} | `{item['id']}` | "
            f"{str(item['reason']).replace('|', '/')} | {text} |"
        )
    (args.report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"items_before={summary['items_before']}")
    print(f"llm_rejected={summary['rejected']}")
    print(f"removal_ratio={summary['removal_ratio']:.2%}")
    print(f"by_dataset={summary['by_dataset']}")
    print(f"report={args.report_dir}")

    if args.apply:
        if summary["removal_ratio"] > args.max_removal_ratio and not args.force_large_removal:
            raise SystemExit(
                f"Refusing to remove {summary['removal_ratio']:.2%}; exceeds "
                f"--max-removal-ratio {args.max_removal_ratio:.2%}."
            )
        result = apply_filter(pool_path, pool, rejected, args.report_dir)
        write_json(args.report_dir / "removed_items.json", result["removed"])
        print(f"removed_items={len(result['removed'])}")
        print(f"backup_pool={result['backup_path']}")
    else:
        print("dry_run=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
