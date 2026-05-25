#!/usr/bin/env python3
"""Audit persona candidate counts in manifest.json.

Exit code:
  0: all detected candidate lists have the target count
  1: at least one detected candidate list does not have the target count
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    items: list[Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit manifest persona candidate counts.")
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument("--target-count", type=int, default=5)
    parser.add_argument("--min-candidates", type=int, default=5)
    return parser.parse_args()


def looks_like_text_item(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(isinstance(value.get(field), str) and value[field].strip() for field in TEXT_FIELD_NAMES)
    return False


def is_candidate_list(key: str | int, items: list[Any], min_candidates: int) -> bool:
    if len(items) < min_candidates:
        return False
    if isinstance(key, str) and key not in LIST_FIELD_NAMES and len(items) != 30:
        return False
    text_like = sum(1 for item in items if looks_like_text_item(item))
    return text_like >= min(len(items), min_candidates)


def walk(node: Any, min_candidates: int, path: list[str | int] | None = None) -> list[CandidateList]:
    path = path or []
    found: list[CandidateList] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, list) and is_candidate_list(key, value, min_candidates):
                found.append(CandidateList(path + [key], value))
            else:
                found.extend(walk(value, min_candidates, path + [key]))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, list) and is_candidate_list(index, value, min_candidates):
                found.append(CandidateList(path + [index], value))
            else:
                found.extend(walk(value, min_candidates, path + [index]))
    return found


def path_string(path: list[str | int]) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    candidates = walk(data, args.min_candidates)
    if not candidates:
        print("No candidate-like lists found.")
        return 0

    failed = False
    for candidate in candidates:
        count = len(candidate.items)
        status = "OK" if count == args.target_count else "BAD"
        failed = failed or status == "BAD"
        print(f"{status}  {path_string(candidate.path)} count={count}")

    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
