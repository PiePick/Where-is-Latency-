#!/usr/bin/env python3
"""Filter manifest example candidates down to persona-aligned top 5 items.

This is a repair/verification utility for manifests that still contain the
30 randomly sampled examples per case instead of the 5 persona-selected
examples requested by the CREDO voice-bundle workflow.

Default LLM endpoint:
  http://127.0.0.1:8000/v1/chat/completions

The endpoint is expected to be OpenAI-compatible, as provided by common local
LLM servers such as vLLM, LM Studio, llama.cpp server wrappers, or Ollama
OpenAI-compatible routes.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PERSONA_PROMPT = """You are filtering candidate TTS lines for a single persona.

Persona:
- Name: Gawr Gura
- Identity: a playful, cute, mischievous shark girl from Atlantis.
- Tone: high-spirited, informal, teasing, energetic, and approachable.
- Traits: clumsy cuteness, smug confidence, flustered reactions, simple silly mistakes.
- Speech habits: short "A" or "Shaark" exclamations, marine/shark/Atlantis jokes,
  exaggerated excitement or panic, casual English, no formal wording.

Style tags:
- high-pitched
- playful
- energetic
- smug
- cute

Task:
Select exactly 5 candidates that best fit this persona as spoken TTS lines.
Prioritize lines that sound natural for the persona, expressive, short enough
for voice generation, and compatible with the style tags. Avoid generic,
formal, flat, out-of-character, or overly long lines.
Return only valid JSON in this shape:
{"selected_indices":[0,1,2,3,4]}
"""


LIST_FIELD_NAMES = {
    "examples",
    "example_texts",
    "sentences",
    "sentence_examples",
    "utterances",
    "samples",
    "sample_texts",
    "candidates",
    "candidate_texts",
    "texts",
    "lines",
    "items",
}

TEXT_FIELD_NAMES = (
    "text",
    "sentence",
    "utterance",
    "line",
    "content",
    "response",
    "prompt",
)


@dataclass
class CandidateList:
    path: list[str | int]
    parent: Any
    key: str | int
    items: list[Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter persona candidate lists in a manifest down to 5 items."
    )
    parser.add_argument("--manifest", default="manifest.json", help="Input manifest JSON path.")
    parser.add_argument("--output", default=None, help="Output path. Defaults to overwrite input.")
    parser.add_argument("--backup", action="store_true", help="Write <manifest>.bak before overwrite.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    parser.add_argument("--target-count", type=int, default=5, help="Final item count per case.")
    parser.add_argument("--min-candidates", type=int, default=6, help="Only filter lists at least this long.")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("LOCAL_LLM_ENDPOINT", "http://127.0.0.1:8000/v1/chat/completions"),
        help="OpenAI-compatible chat completions endpoint.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LOCAL_LLM_MODEL", os.environ.get("VLLM_MODEL", "local-model")),
        help="Model name sent to the local LLM endpoint.",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def looks_like_text_item(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(isinstance(value.get(field), str) and value[field].strip() for field in TEXT_FIELD_NAMES)
    return False


def item_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for field in TEXT_FIELD_NAMES:
            text = value.get(field)
            if isinstance(text, str) and text.strip():
                return text
    return json.dumps(value, ensure_ascii=False)


def is_candidate_list(key: str | int, items: list[Any], min_candidates: int) -> bool:
    if len(items) < min_candidates:
        return False
    if isinstance(key, str) and key not in LIST_FIELD_NAMES and len(items) != 30:
        return False
    text_like = sum(1 for item in items if looks_like_text_item(item))
    return text_like >= min(len(items), min_candidates)


def walk_candidate_lists(node: Any, min_candidates: int, path: list[str | int] | None = None) -> list[CandidateList]:
    path = path or []
    found: list[CandidateList] = []

    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, list) and is_candidate_list(key, value, min_candidates):
                found.append(CandidateList(path + [key], node, key, value))
            else:
                found.extend(walk_candidate_lists(value, min_candidates, path + [key]))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, list) and is_candidate_list(index, value, min_candidates):
                found.append(CandidateList(path + [index], node, index, value))
            else:
                found.extend(walk_candidate_lists(value, min_candidates, path + [index]))

    return found


def path_string(path: list[str | int]) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def build_user_prompt(items: list[Any], target_count: int) -> str:
    lines = [
        f"Select exactly {target_count} persona-aligned candidates from this list.",
        "Return their zero-based indices only as JSON.",
        "",
    ]
    for index, item in enumerate(items):
        text = item_text(item).replace("\n", " ").strip()
        lines.append(f"{index}: {text}")
    return "\n".join(lines)


def call_local_llm(
    endpoint: str,
    model: str,
    items: list[Any],
    target_count: int,
    temperature: float,
    timeout: float,
    retries: int,
) -> list[int]:
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": PERSONA_PROMPT},
            {"role": "user", "content": build_user_prompt(items, target_count)},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            response_json = json.loads(body)
            content = response_json["choices"][0]["message"]["content"]
            return parse_selected_indices(content, len(items), target_count)
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.0 + attempt)

    raise RuntimeError(f"local LLM filtering failed: {last_error}")


def parse_selected_indices(content: str, item_count: int, target_count: int) -> list[int]:
    content = content.strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise ValueError(f"LLM did not return JSON: {content[:200]}")
        parsed = json.loads(match.group(0))

    indices = parsed.get("selected_indices") if isinstance(parsed, dict) else parsed
    if not isinstance(indices, list):
        raise ValueError(f"selected_indices is not a list: {indices!r}")

    cleaned: list[int] = []
    for value in indices:
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and 0 <= value < item_count and value not in cleaned:
            cleaned.append(value)

    if len(cleaned) != target_count:
        raise ValueError(f"expected {target_count} unique indices, got {cleaned}")

    return cleaned


def fallback_select(items: list[Any], target_count: int) -> list[int]:
    """Deterministic fallback used only when a list is already short enough.

    It should not replace LLM selection for 30-item candidate lists.
    """
    return list(range(min(len(items), target_count)))


def filter_manifest(data: Any, args: argparse.Namespace) -> tuple[Any, list[str]]:
    updated = copy.deepcopy(data)
    candidate_lists = walk_candidate_lists(updated, args.min_candidates)
    report: list[str] = []

    for candidate_list in candidate_lists:
        items = candidate_list.items
        if len(items) == args.target_count:
            report.append(f"OK   {path_string(candidate_list.path)} already has {args.target_count}")
            continue
        if len(items) < args.target_count:
            raise RuntimeError(
                f"{path_string(candidate_list.path)} has only {len(items)} items; "
                f"cannot select {args.target_count}"
            )

        indices = call_local_llm(
            args.endpoint,
            args.model,
            items,
            args.target_count,
            args.temperature,
            args.timeout,
            args.retries,
        )
        filtered = [items[index] for index in indices]
        candidate_list.parent[candidate_list.key] = filtered
        report.append(
            f"FIX  {path_string(candidate_list.path)} {len(items)} -> {len(filtered)} "
            f"indices={indices}"
        )

    verify_manifest(updated, args.target_count, args.min_candidates)
    return updated, report


def verify_manifest(data: Any, target_count: int, min_candidates: int) -> None:
    remaining = walk_candidate_lists(data, min_candidates)
    too_long = [entry for entry in remaining if len(entry.items) > target_count]
    too_short = [entry for entry in remaining if len(entry.items) < target_count]
    if too_long or too_short:
        messages = []
        for entry in too_long[:20]:
            messages.append(f"{path_string(entry.path)} has {len(entry.items)} items")
        for entry in too_short[:20]:
            messages.append(f"{path_string(entry.path)} has only {len(entry.items)} items")
        raise RuntimeError("manifest verification failed:\n" + "\n".join(messages))


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    output_path = Path(args.output) if args.output else manifest_path

    data = load_json(manifest_path)
    updated, report = filter_manifest(data, args)

    print("\n".join(report) if report else "No candidate lists found.")

    if args.dry_run:
        print("Dry run: no file written.")
        return 0

    if args.backup and output_path == manifest_path:
        backup_path = manifest_path.with_suffix(manifest_path.suffix + ".bak")
        save_json(backup_path, data)
        print(f"Backup written: {backup_path}")

    save_json(output_path, updated)
    print(f"Filtered manifest written: {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
