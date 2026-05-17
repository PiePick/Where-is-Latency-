"""Build Fish Speech nonverbal cue buckets with DistilBERT labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "fish_speech_nonverbal_cues.json"
MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"

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

# Fish Speech supports free-form tags. Keep this list broad enough to use the
# README/WebUI examples, but exclude cues that are too context-bound for FastTrack.
CANDIDATES = [
    {"tag": "[chuckle]", "cue_text": "chuckle", "weight": 1.0},
    {"tag": "[cute bright voice]", "cue_text": "cute bright voice", "weight": 1.0, "override": "Positive"},
    {"tag": "[cute excited tone]", "cue_text": "cute excited tone", "weight": 0.9, "override": "Positive"},
    {"tag": "[pitch up]", "cue_text": "pitch up", "weight": 0.8, "override": "Positive"},
    {"tag": "[laughing]", "cue_text": "laughing", "weight": 0.85},
    {"tag": "[laughing tone]", "cue_text": "laughing tone", "weight": 0.82, "override": "Positive"},
    {"tag": "[chuckling]", "cue_text": "chuckling", "weight": 0.82, "override": "Positive"},
    {"tag": "[excited]", "cue_text": "excited", "weight": 0.8},
    {"tag": "[excited tone]", "cue_text": "excited tone", "weight": 0.78, "override": "Positive"},
    {"tag": "[delight]", "cue_text": "delight", "weight": 0.75},
    {"tag": "[squeal of delight]", "cue_text": "squeal of delight", "weight": 0.55, "override": "Positive"},
    {"tag": "[relieved sigh]", "cue_text": "relieved sigh", "weight": 0.65},
    {"tag": "[excited inhale]", "cue_text": "excited inhale", "weight": 0.6},
    {"tag": "[breathless]", "cue_text": "breathless", "weight": 0.45, "override": "Positive"},
    {"tag": "[angry]", "cue_text": "angry", "weight": 1.0, "override": "Negative"},
    {"tag": "[sad sigh]", "cue_text": "sad sigh", "weight": 1.0},
    {"tag": "[sigh]", "cue_text": "sigh", "weight": 0.95},
    {"tag": "[soft sigh]", "cue_text": "soft sigh", "weight": 0.9},
    {"tag": "[sad]", "cue_text": "sad", "weight": 0.75},
    {"tag": "[tsk]", "cue_text": "tsk", "weight": 0.62, "override": "Negative"},
    {"tag": "[whisper]", "cue_text": "whisper", "weight": 0.45},
    {"tag": "[low voice]", "cue_text": "low voice", "weight": 0.35},
    {"tag": "[screaming]", "cue_text": "screaming", "weight": 0.25, "override": "Negative"},
    {"tag": "[shouting]", "cue_text": "shouting", "weight": 0.25, "override": "Negative"},
    {"tag": "[surprised]", "cue_text": "surprised", "weight": 1.0},
    {"tag": "[shocked]", "cue_text": "shocked", "weight": 0.9},
    {"tag": "[surprised gasp]", "cue_text": "surprised gasp", "weight": 0.9},
    {"tag": "[pause]", "cue_text": "pause", "weight": 0.55},
    {"tag": "[clearing throat]", "cue_text": "clearing throat", "weight": 0.4},
    {"tag": "[inhale]", "cue_text": "inhale", "weight": 0.35, "override": "Ambiguous"},
    {"tag": "[short pause]", "cue_text": "short pause", "weight": 1.0, "override": "Neutral"},
    {"tag": "[pause]", "cue_text": "pause", "weight": 0.75, "override": "Neutral"},
    {"tag": "[break]", "cue_text": "break", "weight": 0.72, "override": "Neutral"},
    {"tag": "[emphasis]", "cue_text": "emphasis", "weight": 0.65, "override": "Neutral"},
    {"tag": "[emphasize]", "cue_text": "emphasize", "weight": 0.6, "override": "Neutral"},
    {"tag": "[exhale]", "cue_text": "exhale", "weight": 0.55, "override": "Neutral"},
    {"tag": "[inhale]", "cue_text": "inhale", "weight": 0.45, "override": "Neutral"},
    {"tag": "[volume up]", "cue_text": "volume up", "weight": 0.35, "override": "Neutral"},
    {"tag": "[volume down]", "cue_text": "volume down", "weight": 0.35, "override": "Neutral"},
    {"tag": "[low volume]", "cue_text": "low volume", "weight": 0.3, "override": "Neutral"},
    {"tag": "[loud]", "cue_text": "loud", "weight": 0.25, "override": "Neutral"},
]


def parse_args() -> argparse.Namespace:
    """Parse cue builder options."""
    parser = argparse.ArgumentParser(description="Build Fish Speech cue JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    return parser.parse_args()


def normalize_score_list(raw: Any) -> list[dict[str, Any]]:
    """Normalize Transformers pipeline output shape."""
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        return raw[0]
    if isinstance(raw, list):
        return raw
    return [raw]


def main() -> int:
    """Label candidate cue text and write emotion buckets."""
    args = parse_args()
    try:
        import torch
        from transformers import pipeline
    except ImportError as exc:
        raise SystemExit("Install transformers and torch first.") from exc

    device = 0 if args.device == "cuda" and torch.cuda.is_available() else -1
    classifier = pipeline(
        "text-classification",
        model=args.model,
        tokenizer=args.model,
        top_k=None,
        device=device,
    )

    buckets: dict[str, list[dict[str, Any]]] = {
        "Positive": [],
        "Negative": [],
        "Ambiguous": [],
        "Neutral": [],
    }
    for item in CANDIDATES:
        scores = normalize_score_list(classifier(item["cue_text"], truncation=True))
        top = max(scores, key=lambda score: float(score.get("score", 0.0)))
        label = str(top["label"]).lower()
        category = str(item.get("override") or LABEL_TO_CATEGORY.get(label, "Neutral"))
        buckets[category].append(
            {
                "tag": item["tag"],
                "cue_text": item["cue_text"],
                "distilbert_label": label,
                "distilbert_score": round(float(top["score"]), 4),
                "final_category": category,
                "weight": item["weight"],
            }
        )

    output = {
        "meta": {
            "version": "fish-speech-cues-v02",
            "source": "Fish Speech README inline control examples plus Fish Speech WebUI examples",
            "model": args.model,
            "labeling_method": "DistilBERT top-1 label on plain English cue text, then mapped to FastTrack categories; override marks voice-control tags whose emotion bucket is semantic.",
            "excluded_tags": [
                "[singing]",
                "[interrupting]",
                "[echo]",
                "[audience laughter]",
                "[with strong accent]",
                "[panting]",
                "[moaning]",
            ],
            "note": "Pause, volume, emphasis, and breath cues are paralinguistic controls, so DistilBERT confidence can be low. The final_category field is the runtime bucket used by FastTrack.",
        },
        **buckets,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
