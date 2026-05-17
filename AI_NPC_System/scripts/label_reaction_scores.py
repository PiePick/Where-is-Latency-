#!/usr/bin/env python3
"""Add detailed DistilBERT score metadata to the final reaction list."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "hybrid_reactions.json"
DEFAULT_OUTPUT = ROOT / "hybrid_reactions_labeled.json"
MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"
CATEGORIES = ("Positive", "Negative", "Ambiguous", "Neutral")
SOURCES = ("everyday", "stream")

LABEL_TO_CATEGORY = {
    "admiration": "Positive",
    "amusement": "Positive",
    "approval": "Positive",
    "caring": "Positive",
    "desire": "Positive",
    "excitement": "Positive",
    "gratitude": "Positive",
    "joy": "Positive",
    "love": "Positive",
    "optimism": "Positive",
    "pride": "Positive",
    "relief": "Positive",
    "anger": "Negative",
    "annoyance": "Negative",
    "disappointment": "Negative",
    "disapproval": "Negative",
    "disgust": "Negative",
    "embarrassment": "Negative",
    "fear": "Negative",
    "grief": "Negative",
    "nervousness": "Negative",
    "remorse": "Negative",
    "sadness": "Negative",
    "confusion": "Ambiguous",
    "curiosity": "Ambiguous",
    "realization": "Ambiguous",
    "surprise": "Ambiguous",
    "neutral": "Neutral",
}


def parse_args() -> argparse.Namespace:
    """Parse labeling options."""
    parser = argparse.ArgumentParser(description="Write detailed DistilBERT scores for reactions.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--torch-threads", type=int, default=0)
    parser.add_argument("--copy-to-reaction-sources", action="store_true")
    return parser.parse_args()


def require_runtime_deps() -> tuple[Any, Any]:
    """Import model dependencies only when the script runs."""
    try:
        import torch
        from transformers import pipeline
    except ImportError as exc:
        print("Missing dependency. Install with:")
        print("  python3 -m pip install -r AI_NPC_System/scripts/requirements.txt")
        raise SystemExit(2) from exc
    return torch, pipeline


def choose_device(torch: Any, requested: str) -> int:
    """Select a Transformers pipeline device."""
    if requested == "cpu":
        return -1
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("CUDA was requested, but torch.cuda.is_available() is false.")
        return 0
    return 0 if torch.cuda.is_available() else -1


def normalize_score_list(raw: Any) -> list[dict[str, Any]]:
    """Normalize Transformers output across pipeline versions."""
    if isinstance(raw, list):
        if not raw:
            return [{"label": "neutral", "score": 0.0}]
        if isinstance(raw[0], list):
            return raw[0]
        return raw
    return [raw]


def round_score(value: float) -> float:
    """Use stable rounded scores without hiding small labels."""
    return round(float(value), 6)


def aggregate_category_scores(label_scores: dict[str, float]) -> dict[str, float]:
    """Collapse original GoEmotions label scores into four categories."""
    scores = {category: 0.0 for category in CATEGORIES}
    for label, score in label_scores.items():
        category = LABEL_TO_CATEGORY.get(label)
        if category:
            scores[category] += score
    return {category: round_score(score) for category, score in scores.items()}


def flatten_reactions(data: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    """Flatten the runtime JSON while preserving original bucket membership."""
    unique_texts: list[str] = []
    seen: set[str] = set()
    memberships: list[dict[str, str]] = []

    for category in CATEGORIES:
        bucket = data.get(category, {})
        for source in SOURCES:
            for text in bucket.get(source, []):
                if not isinstance(text, str) or not text.strip():
                    continue
                text = text.strip()
                memberships.append({"text": text, "bucket_category": category, "source": source})
                if text not in seen:
                    seen.add(text)
                    unique_texts.append(text)

    return unique_texts, memberships


def classify_texts(classifier: Any, texts: list[str], batch_size: int) -> dict[str, dict[str, Any]]:
    """Classify unique reaction strings and return detailed score metadata."""
    labeled: dict[str, dict[str, Any]] = {}
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        results = classifier(batch, truncation=True, batch_size=batch_size)
        for text, raw in zip(batch, results):
            score_items = normalize_score_list(raw)
            ranked = sorted(
                (
                    {
                        "label": str(item.get("label", "neutral")).lower(),
                        "score": round_score(float(item.get("score", 0.0))),
                    }
                    for item in score_items
                ),
                key=lambda item: item["score"],
                reverse=True,
            )
            label_scores = {item["label"]: item["score"] for item in ranked}
            category_scores = aggregate_category_scores(label_scores)
            top1 = ranked[0] if ranked else {"label": "neutral", "score": 0.0}
            top2 = ranked[1] if len(ranked) > 1 else {"label": "", "score": 0.0}
            labeled[text] = {
                "text": text,
                "assigned_category": LABEL_TO_CATEGORY.get(top1["label"], "Neutral"),
                "top1_top2_margin": round_score(top1["score"] - top2["score"]),
                "category_scores": category_scores,
                "label_scores": label_scores,
            }
    return labeled


def build_output(args: argparse.Namespace) -> dict[str, Any]:
    """Build the detailed labeled reaction dataset."""
    torch, pipeline = require_runtime_deps()
    if args.torch_threads > 0:
        torch.set_num_threads(args.torch_threads)

    data = json.loads(args.input.read_text(encoding="utf-8"))
    unique_texts, memberships = flatten_reactions(data)
    device = choose_device(torch, args.device)
    classifier = pipeline(
        "text-classification",
        model=args.model,
        tokenizer=args.model,
        top_k=None,
        device=device,
    )

    started = time.perf_counter()
    labels_by_text = classify_texts(classifier, unique_texts, args.batch_size)
    elapsed = time.perf_counter() - started

    memberships_by_text: dict[str, list[dict[str, str]]] = {text: [] for text in unique_texts}
    for membership in memberships:
        memberships_by_text[membership["text"]].append(
            {
                "bucket_category": membership["bucket_category"],
                "source": membership["source"],
            }
        )

    items: list[dict[str, Any]] = []
    for index, text in enumerate(unique_texts, start=1):
        item = dict(labels_by_text[text])
        item["id"] = f"rxn_{index:04d}"
        item["memberships"] = memberships_by_text[text]
        item["category_match"] = any(
            item["assigned_category"] == membership["bucket_category"]
            for membership in item["memberships"]
        )
        items.append(item)

    return {
        "version": "hybrid-reactions-labeled-v02",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_reaction_path": str(args.input),
        "model": args.model,
        "labeling": {
            "method": "DistilBERT GoEmotions top-k=None over final reaction strings",
            "runtime_reaction_json_unchanged": True,
            "score_fields": [
                "top1_top2_margin",
                "category_scores",
                "label_scores",
            ],
            "label_scores_order": "descending by DistilBERT score; first key is top-1, second key is top-2",
            "category_mapping": LABEL_TO_CATEGORY,
        },
        "counts": {
            "unique_texts": len(unique_texts),
            "bucket_memberships": len(memberships),
            "elapsed_seconds": round(elapsed, 3),
            "bucket_counts": {
                category: {
                    source: sum(
                        1
                        for membership in memberships
                        if membership["bucket_category"] == category and membership["source"] == source
                    )
                    for source in SOURCES
                }
                for category in CATEGORIES
            },
        },
        "items": items,
    }


def main() -> int:
    """Command-line entrypoint."""
    args = parse_args()
    output = build_output(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(json.dumps(output["counts"], ensure_ascii=False, indent=2))

    if args.copy_to_reaction_sources:
        target = ROOT.parent / "reaction_sources" / "merged" / args.output.name
        target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
