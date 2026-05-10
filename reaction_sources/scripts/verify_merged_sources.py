"""Verify merged reaction strings against local raw source datasets."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
MERGED_PATH = ROOT / "merged" / "hybrid_reactions.json"
OUTPUT_PATH = ROOT / "merged" / "source_verification.json"

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
PUNCT_SPACE_RE = re.compile(r"\s+([?.!,;:])")


def normalize_text(text: str) -> str:
    """Match the lightweight normalization used by the reaction builder."""
    text = URL_RE.sub("", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = SPACE_RE.sub(" ", text).strip()
    return PUNCT_SPACE_RE.sub(r"\1", text)


def load_daily_dialog_texts() -> set[str]:
    """Load normalized DailyDialog utterances from local split zips."""
    values: set[str] = set()
    for split in ("train", "validation", "test"):
        zip_path = RAW_DIR / "daily_dialog" / f"{split}.zip"
        with ZipFile(zip_path) as split_zip:
            dialog_path = f"{split}/dialogues_{split}.txt"
            with split_zip.open(dialog_path) as dialog_file:
                for raw_line in dialog_file:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    for utterance in line.split("__eou__"):
                        text = normalize_text(utterance)
                        if text:
                            values.add(text.casefold())
    return values


def load_go_emotions_texts() -> set[str]:
    """Load normalized GoEmotions raw text from local official CSV files."""
    values: set[str] = set()
    for index in (1, 2, 3):
        csv_path = RAW_DIR / "go_emotions" / f"goemotions_{index}.csv"
        with csv_path.open(encoding="utf-8", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                text = normalize_text(row.get("text", ""))
                if text:
                    values.add(text.casefold())
    return values


def verify() -> dict[str, object]:
    """Check every final reaction against its expected source bucket."""
    reactions = json.loads(MERGED_PATH.read_text(encoding="utf-8"))
    source_sets = {
        "everyday": load_daily_dialog_texts(),
        "stream": load_go_emotions_texts(),
    }
    source_names = {
        "everyday": "daily_dialog",
        "stream": "go_emotions",
    }

    summary: dict[str, dict[str, dict[str, int]]] = {}
    missing: list[dict[str, str]] = []
    for category in ("Positive", "Negative", "Ambiguous", "Neutral"):
        summary[category] = {}
        for bucket in ("everyday", "stream"):
            expected = source_sets[bucket]
            values = reactions[category][bucket]
            found = 0
            for value in values:
                normalized = normalize_text(value).casefold()
                if normalized in expected:
                    found += 1
                else:
                    missing.append(
                        {
                            "category": category,
                            "bucket": bucket,
                            "expected_source": source_names[bucket],
                            "text": value,
                        }
                    )
            summary[category][bucket] = {
                "total": len(values),
                "found_in_raw": found,
                "missing": len(values) - found,
            }

    return {
        "source_map": {
            "everyday": "daily_dialog",
            "stream": "go_emotions",
        },
        "summary": summary,
        "missing": missing,
    }


def main() -> int:
    result = verify()
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    if result["missing"]:
        print(f"missing={len(result['missing'])}")
        return 1
    print("All merged reactions were found in the expected local raw source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
