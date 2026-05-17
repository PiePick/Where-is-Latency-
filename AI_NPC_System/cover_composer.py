"""Compose latency-cover blocks from emotion, intent, keywords, style tags, and motion."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from latency_predictor import LatencyPredictor


ROOT = Path(__file__).resolve().parent
REACTION_PATH = ROOT / "hybrid_reactions.json"
EXTREME_AUDIO_MANIFEST = ROOT / "expressive_audio_pool" / "manifest.json"
SWDA_PATH = ROOT / "prepared_fasttrack_data" / "swda_intent_coarse.jsonl"


MOTION_MAP = {
    "positive": ["positive_01", "positive_02", "positive_03", "positive_04"],
    "negative": ["negative_01", "negative_02", "negative_03", "negative_04"],
    "ambiguous": ["ambiguous_01", "ambiguous_02", "ambiguous_03", "ambiguous_04"],
    "neutral": ["neutral_01", "neutral_02", "neutral_03", "neutral_04"],
}

STYLE_TAGS = {
    "positive": [
        ["[laughing]", "[chuckle]", "[delight]", "[excited]", "[cute excited tone]"],
        ["[excited]", "[laughing]", "[emphasis]", "[inhale]", "[delight]"],
    ],
    "negative": [
        ["[sigh]", "[sad sigh]", "[exhale]", "[whisper]", "[pause]"],
        ["[sigh]", "[emphasis]", "[exhale]", "[short pause]", "[sad sigh]"],
    ],
    "ambiguous": [
        ["[surprised]", "[shocked]", "[inhale]", "[short pause]", "[whisper]"],
        ["[surprised gasp]", "[curious]", "[short pause]", "[inhale]", "[soft sigh]"],
    ],
    "neutral": [
        ["[short pause]", "[soft sigh]", "[exhale]", "[whisper]", "[pause]"],
        ["[pause]", "[inhale]", "[exhale]", "[soft sigh]", "[whisper]"],
    ],
}

INTENT_FALLBACKS = {
    "QUESTION": ["Wait, what do you mean?", "Can you say that again?"],
    "INFORM": ["I got it.", "That makes sense."],
    "ACKNOWLEDGE": ["Yeah, yeah.", "Right, I hear you."],
    "DIRECTIVE": ["Okay, let's do it.", "Point me there."],
    "EXPRESSIVE": ["That is a lot.", "I can feel that."],
    "REJECT": ["No way.", "I don't think so."],
    "UNKNOWN": ["Let me think.", "I see."],
}


@dataclass(frozen=True)
class CoverBlock:
    """One latency-cover block."""

    block_id: int
    kind: str
    text: str
    motion: str
    audio_path: str | None
    estimated_ms: float
    metadata: dict[str, Any]


class CoverComposer:
    """Create a block plan that can scale to the predicted SlowTrack latency."""

    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reactions = self._load_json(REACTION_PATH, {})
        self.extreme_audio = self._load_json(EXTREME_AUDIO_MANIFEST, {"items": []}).get("items", [])
        self.swda_examples = self._load_swda_examples()
        self.predictor = LatencyPredictor()

    def compose(
        self,
        *,
        user_text: str,
        fast_result: dict[str, Any],
        intent: str = "UNKNOWN",
        expected_slow_text: str = "",
    ) -> dict[str, Any]:
        """Build a latency-cover plan from current FastTrack metadata."""
        emotion = str(fast_result.get("emotion_label", "neutral")).lower()
        if emotion not in MOTION_MAP:
            emotion = "neutral"
        keywords = [str(item) for item in fast_result.get("keywords") or []]
        category_scores = fast_result.get("category_scores") or {}
        slow_probe = expected_slow_text or self._estimate_slow_probe(user_text)
        predicted = self.predictor.predict(slow_probe, engine="fish_speech")

        target_ms = max(1200.0, predicted.predicted_ms)
        blocks: list[CoverBlock] = []
        elapsed = 0.0
        block_id = 1
        while elapsed < target_ms and block_id <= 8:
            block = self._make_block(
                block_id=block_id,
                emotion=emotion,
                intent=intent,
                keywords=keywords,
                category_scores=category_scores,
            )
            blocks.append(block)
            elapsed += block.estimated_ms
            block_id += 1

        return {
            "emotion": emotion,
            "intent": intent,
            "keywords": keywords,
            "category_scores": category_scores,
            "predicted_slow_tts_ms": round(predicted.predicted_ms, 3),
            "prediction_method": predicted.method,
            "target_cover_ms": round(target_ms, 3),
            "estimated_cover_ms": round(elapsed, 3),
            "blocks": [block.__dict__ for block in blocks],
        }

    def choose_extreme_audio(self, emotion: str) -> str | None:
        """Pick one prebuilt extreme nonverbal audio path for the emotion."""
        candidates = [
            item for item in self.extreme_audio
            if str(item.get("emotion", "")).lower() == emotion and item.get("audio_path")
        ]
        if not candidates:
            return None
        return str(self.rng.choice(candidates)["audio_path"])

    def _make_block(
        self,
        *,
        block_id: int,
        emotion: str,
        intent: str,
        keywords: list[str],
        category_scores: dict[str, float],
    ) -> CoverBlock:
        motion = self.rng.choice(MOTION_MAP[emotion])
        style_tags = self.rng.choice(STYLE_TAGS[emotion])
        audio_path = self.choose_extreme_audio(emotion)

        if block_id == 1:
            reaction = self._choose_reaction(emotion)
            text = f"{' '.join(style_tags)} {reaction}".strip()
            kind = "reaction_style_motion"
        elif block_id == 2 and keywords:
            text = f"{' '.join(style_tags)} {keywords[0]}?"
            kind = "keyword_echo_style_motion"
        elif block_id == 3:
            text = f"{' '.join(style_tags)} {self._choose_intent_line(intent)}"
            kind = "intent_style_motion"
        else:
            reaction = self._choose_reaction(emotion)
            text = f"{' '.join(style_tags)} {reaction}".strip()
            kind = "loop_cover"

        return CoverBlock(
            block_id=block_id,
            kind=kind,
            text=text,
            motion=motion,
            audio_path=audio_path,
            estimated_ms=1800.0 + len(text) * 18.0,
            metadata={
                "style_tags": style_tags,
                "emotion_scores": category_scores,
                "intent": intent,
            },
        )

    def _choose_reaction(self, emotion: str) -> str:
        category = emotion.capitalize() if emotion != "ambiguous" else "Ambiguous"
        bucket = self.reactions.get(category, {})
        candidates = []
        if isinstance(bucket, dict):
            for source in ("everyday", "stream"):
                candidates.extend(bucket.get(source) or [])
        return self.rng.choice(candidates or ["I see."])

    def _choose_intent_line(self, intent: str) -> str:
        intent = intent.upper()
        examples = self.swda_examples.get(intent) or INTENT_FALLBACKS.get(intent) or INTENT_FALLBACKS["UNKNOWN"]
        return self.rng.choice(examples)

    def _estimate_slow_probe(self, user_text: str) -> str:
        return f"I hear you. Let me respond to that carefully: {user_text[:90]}"

    def _load_swda_examples(self) -> dict[str, list[str]]:
        examples: dict[str, list[str]] = {}
        if not SWDA_PATH.exists():
            return examples
        for line in SWDA_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            label = str(row.get("coarse_label", "UNKNOWN")).upper()
            text = str(row.get("text", "")).strip()
            if not text or len(text.split()) > 8:
                continue
            examples.setdefault(label, []).append(text)
            if all(len(items) >= 200 for items in examples.values()):
                break
        return examples

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
