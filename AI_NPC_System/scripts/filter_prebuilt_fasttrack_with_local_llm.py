#!/usr/bin/env python3
"""Filter unusable prebuilt FastTrack lines with the local LLM.

The script removes lines that are too context-specific, unclear without hidden
context, unsafe, or too tied to a one-off internet/media situation. When
--apply is used, matching wav files are deleted and manifest.json is rewritten.
"""

from __future__ import annotations

import argparse
import json
import math
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
DEFAULT_MANIFEST = ROOT / "fasttrack_assets" / "audio" / "prebuilt_stylebert_v1" / "manifest.json"
DEFAULT_LLM_URL = "http://127.0.0.1:8001/v1/chat/completions"
DEFAULT_MODEL = "qwen2.5:7b"


SYSTEM_PROMPT = """You are a conservative dataset curation judge for short AI VTuber FastTrack reaction lines.
Reject only CLEAR problems that should not be spoken in a general VTuber live chat:
- concrete unseen-media references: face, title, song, album, show, comic, ad, photo, video, scene, game, team, player, animal, food, object, body part, clothing, product, place, politics, or one-off story
- proper nouns, brands, niche memes, personal relationship details, anniversaries, or private-life references
- hard to understand without hidden context, malformed, unfinished, typo-garbled, or semantically incoherent
- sexual, profane, violent, self-harm, hateful, cruel, insulting a group, medical/legal advice, or risky content
Do NOT reject a line just because it is short, plain, generic, emotional, or uses words like "this", "that", "it", "thing", "answer", "method", or "problem".
Keep reusable generic reactions such as "This is not good.", "Of course not.", "This is so true.", "That's a weird answer.", "That is really weird.", or "Well that took a turn real quick."
Also KEEP generic lines like "This is funny though.", "That was brutal.", "This really hurts my feelings.", "Thanks hate it.", "Oh wow, hate that.", "The absolute worst!", and "It's not like it's a bad thing..." unless they contain an explicit concrete reference or unsafe term.
Do not infer sexual, violent, or hateful meaning unless explicit words in the line prove it.
Return only strict compact JSON using candidate numbers, not full ids:
{"reject":[{"n":0,"reason":"short reason"}]}."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_text(item: dict[str, Any]) -> str:
    text = str(item.get("plain_text") or item.get("text") or "")
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def is_generic_rescue(text: str) -> bool:
    """Keep short generic reactions when the LLM over-interprets them."""
    normalized = " ".join(text.lower().strip().split())
    normalized = normalized.strip('"')
    exact_keep = {
        "this is funny though.",
        "that was brutal.",
        "this really hurts my feelings.",
        "thanks hate it.",
        "oh wow, hate that.",
        "the absolute worst!",
        "it's not like it's a bad thing...",
        "it's not like it's a bad thing.",
        "that sentence should be illegal.",
    }
    if normalized in exact_keep:
        return True
    return bool(
        re.fullmatch(
            r"(this|that|it|that answer|this answer)( is|'s| was)? ?"
            r"(not )?(good|bad|funny|weird|true|brutal|awesome|great|amazing|terrible|interesting)"
            r"( though)?[.!?]*",
            normalized,
        )
    )


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
    lines = [
        "Judge each candidate. Reject only clear problems. Keep generic reusable lines.",
        "Candidates:",
    ]
    for index, item in enumerate(batch):
        source = str(item.get("source_dataset") or "")
        emotion = str(item.get("emotion") or "")
        response = str(item.get("response_act") or "")
        lines.append(f"- n={index}; source={source}; emotion={emotion}; response={response}; text={json.dumps(clean_text(item), ensure_ascii=False)}")
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
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        args.llm_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Local LLM rejected batch: HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local LLM unreachable at {args.llm_url}: {exc}") from exc

    content = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    parsed = json_from_text(content)
    rejected: dict[str, str] = {}
    for row in parsed.get("reject", []):
        if not isinstance(row, dict):
            continue
        raw_n = row.get("n")
        try:
            batch_index = int(raw_n)
        except (TypeError, ValueError):
            continue
        if batch_index < 0 or batch_index >= len(batch):
            continue
        item_id = str(batch[batch_index].get("id") or "").strip()
        reason = str(row.get("reason") or "llm_rejected").strip()
        if item_id and not is_generic_rescue(clean_text(batch[batch_index])):
            rejected[item_id] = reason[:200]
    return rejected


def batched(items: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def judge_all(args: argparse.Namespace, items: list[dict[str, Any]]) -> dict[str, str]:
    rejected: dict[str, str] = {}
    batches = batched(items, args.batch_size)
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


def resolve_audio_path(manifest_path: Path, item: dict[str, Any]) -> Path | None:
    raw = str(item.get("audio_path") or "").strip()
    if not raw:
        return None
    audio_path = Path(raw)
    if audio_path.is_absolute():
        return audio_path
    return manifest_path.parent / audio_path


def apply_filter(
    manifest_path: Path,
    data: dict[str, Any],
    rejected: dict[str, str],
    report_dir: Path,
    model: str,
) -> tuple[int, int]:
    items = list(data.get("items") or [])
    rejected_ids = set(rejected)
    backup_path = report_dir / f"manifest.before_llm_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy2(manifest_path, backup_path)

    deleted_audio = 0
    removed_items = []
    kept_items = []
    for item in items:
        item_id = str(item.get("id") or "")
        if item_id not in rejected_ids:
            kept_items.append(item)
            continue
        audio_path = resolve_audio_path(manifest_path, item)
        if audio_path and audio_path.exists():
            audio_path.unlink()
            deleted_audio += 1
        removed = dict(item)
        removed["llm_filter_reason"] = rejected[item_id]
        removed_items.append(removed)

    data["items"] = kept_items
    data["summary"] = {
        **(data.get("summary") if isinstance(data.get("summary"), dict) else {}),
        "items": len(kept_items),
        "llm_filtered_removed": len(removed_items),
        "llm_filter_applied_at": datetime.now(timezone.utc).isoformat(),
    }
    data["llm_quality_filter"] = {
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "removed_items": len(removed_items),
        "deleted_audio_files": deleted_audio,
        "backup_manifest": str(backup_path),
        "criteria": [
            "too context-specific",
            "unclear without hidden context",
            "unsafe or unsuitable",
            "proper-noun or unseen-media dependent",
        ],
    }
    write_json(manifest_path, data)
    write_json(report_dir / "removed_items.json", removed_items)
    return len(removed_items), deleted_audio


def summarize_rejections(items: list[dict[str, Any]], rejected: dict[str, str]) -> dict[str, Any]:
    by_id = {str(item.get("id") or ""): item for item in items}
    removed = [by_id[item_id] for item_id in rejected if item_id in by_id]
    return {
        "rejected": len(removed),
        "by_source": dict(Counter(str(item.get("source_dataset") or "") for item in removed)),
        "by_emotion": dict(Counter(str(item.get("emotion") or "") for item in removed)),
        "by_response_act": dict(Counter(str(item.get("response_act") or "") for item in removed)),
        "examples": [
            {
                "id": str(item.get("id") or ""),
                "text": clean_text(item),
                "reason": rejected.get(str(item.get("id") or ""), ""),
            }
            for item in removed[: args_example_limit()]
        ],
    }


def args_example_limit() -> int:
    return 40


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--llm-url", default=DEFAULT_LLM_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=18)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--max-removal-ratio", type=float, default=0.30)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force-large-removal", action="store_true")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "reports" / f"fasttrack_llm_quality_filter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    return parser


def main() -> int:
    global args
    args = build_parser().parse_args()
    manifest_path = args.manifest.resolve()
    data = read_json(manifest_path)
    items = list(data.get("items") or [])
    args.report_dir.mkdir(parents=True, exist_ok=True)

    rejected = judge_all(args, items)
    ratio = (len(rejected) / len(items)) if items else 0.0
    summary = summarize_rejections(items, rejected)
    summary.update(
        {
            "manifest": str(manifest_path),
            "items_before": len(items),
            "removal_ratio": round(ratio, 6),
            "apply": bool(args.apply),
            "model": args.model,
            "llm_url": args.llm_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_json(args.report_dir / "summary.json", summary)

    lines = [
        "# FastTrack LLM Quality Filter",
        "",
        f"- Manifest: `{manifest_path}`",
        f"- Items before: {len(items)}",
        f"- LLM rejected: {len(rejected)}",
        f"- Removal ratio: {ratio:.2%}",
        f"- Applied: {bool(args.apply)}",
        "",
        "| ID | Reason | Text |",
        "| --- | --- | --- |",
    ]
    by_id = {str(item.get("id") or ""): item for item in items}
    for item_id, reason in list(rejected.items())[:80]:
        item = by_id.get(item_id, {})
        text = clean_text(item).replace("|", "/")
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append(f"| `{item_id}` | {reason.replace('|', '/')} | {text} |")
    (args.report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"items_before={len(items)}")
    print(f"llm_rejected={len(rejected)}")
    print(f"removal_ratio={ratio:.2%}")
    print(f"report={args.report_dir}")

    if args.apply:
        if ratio > args.max_removal_ratio and not args.force_large_removal:
            raise SystemExit(
                f"Refusing to remove {ratio:.2%}; exceeds --max-removal-ratio {args.max_removal_ratio:.2%}. "
                "Review report or pass --force-large-removal."
            )
        removed_count, deleted_audio = apply_filter(manifest_path, data, rejected, args.report_dir, args.model)
        print(f"removed_items={removed_count}")
        print(f"deleted_audio_files={deleted_audio}")
    else:
        print("dry_run=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
