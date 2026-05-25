"""Compose latency-cover blocks from emotion, intent, keywords, TTS style controls, and motion."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config
from intent_transition_matrix import IntentTransitionPlanner
from latency_predictor import LatencyPredictor


ROOT = Path(__file__).resolve().parent
REACTION_PATH = ROOT / "hybrid_reactions.json"
EXTREME_AUDIO_MANIFEST = ROOT / "archive" / "legacy_audio" / "expressive_audio_pool" / "manifest.json"
SWDA_PATH = ROOT / "fasttrack_assets" / "datasets" / "prepared_fasttrack_data" / "swda_intent_coarse.jsonl"


MOTION_MAP = {
    "positive": ["positive_01", "positive_02", "positive_03", "positive_04"],
    "negative": ["negative_01", "negative_02", "negative_03", "negative_04"],
    "ambiguous": ["ambiguous_01", "ambiguous_02", "ambiguous_03", "ambiguous_04"],
    "neutral": ["neutral_01", "neutral_02", "neutral_03", "neutral_04"],
}

PURE_INTERJECTION_CARRIERS = {
    "positive": {"ha-ha!", "hee-hee!", "ahaha!", "oh!", "haha!", "yay!", "aw!"},
    "negative": {"oh.", "mm.", "ugh.", "ah.", "hm.", "ugh?"},
    "ambiguous": {"huh?", "oh?", "hm?", "oh."},
    "neutral": {"mm.", "hm."},
}

FISH_SPEECH_CUE_BUNDLES = {
    "positive": ["[laughing]", "[chuckle]", "[delight]", "[excited]"],
    "negative": ["[sigh]", "[sad sigh]", "[exhale]", "[whisper]"],
    "ambiguous": ["[surprised]", "[shocked]", "[inhale]", "[curious]"],
    "neutral": ["[short pause]", "[soft sigh]", "[exhale]", "[whisper]"],
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
        self.extreme_audio = self._load_audio_items()
        self.thinking_bridge_audio = self._load_thinking_bridge_items()
        self.swda_examples = self._load_swda_examples()
        self.predictor = LatencyPredictor()
        self.intent_transition = IntentTransitionPlanner()

    def _load_audio_items(self) -> list[dict[str, Any]]:
        """Load the pure interjection bundle first, then the legacy pool."""
        bundle_path = getattr(config, "CREDO_INTERJECTION_AUDIO_BUNDLE_PATH", None)
        if bundle_path and Path(bundle_path).exists():
            raw = self._load_json(Path(bundle_path), {"items": []})
            root = Path(bundle_path).parent
            items = []
            for item in raw.get("items", []):
                audio_path = str(item.get("audio_path") or "")
                if audio_path and not Path(audio_path).is_absolute():
                    item = dict(item)
                    item["audio_path"] = str((root / audio_path).resolve())
                items.append(item)
            return items
        return self._load_json(EXTREME_AUDIO_MANIFEST, {"items": []}).get("items", [])

    def _load_thinking_bridge_items(self) -> list[dict[str, Any]]:
        """Load short spoken thinking bridges such as 'Let me think about it.'"""
        bundle_path = getattr(config, "CREDO_THINKING_BRIDGE_AUDIO_BUNDLE_PATH", None)
        if not bundle_path or not Path(bundle_path).exists():
            return []
        raw = self._load_json(Path(bundle_path), {"items": []})
        root = Path(bundle_path).parent
        items = []
        for item in raw.get("items", []):
            audio_path = str(item.get("audio_path") or "")
            if audio_path and not Path(audio_path).is_absolute():
                item = dict(item)
                item["audio_path"] = str((root / audio_path).resolve())
            if item.get("audio_path"):
                items.append(item)
        return items

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
        transition = self.intent_transition.choose(intent, emotion=emotion, rng=self.rng)
        slow_probe = expected_slow_text or self._estimate_slow_probe(user_text)
        predicted = self.predictor.predict(slow_probe, engine="fish_speech", stage="slow_track_tts")

        target_ms = max(1200.0, predicted.predicted_ms)
        blocks: list[CoverBlock] = []
        elapsed = 0.0
        block_id = 1
        while elapsed < target_ms and block_id <= 8:
            block = self._make_block(
                block_id=block_id,
                emotion=emotion,
                intent=transition.response_intent,
                keywords=keywords,
                category_scores=category_scores,
            )
            blocks.append(block)
            elapsed += block.estimated_ms
            block_id += 1

        return {
            "emotion": emotion,
            "user_intent": transition.user_intent,
            "response_intent": transition.response_intent,
            "intent_transition_distribution": transition.distribution,
            "keywords": keywords,
            "category_scores": category_scores,
            "predicted_slow_tts_ms": round(predicted.predicted_ms, 3),
            "prediction_method": predicted.method,
            "prediction_source": predicted.source,
            "prediction_neighbors": predicted.neighbors,
            "prediction_neighbor_ms": predicted.neighbor_ms,
            "prediction_engine_key": predicted.engine_key,
            "prediction_stage_key": predicted.stage_key,
            "target_cover_ms": round(target_ms, 3),
            "estimated_cover_ms": round(elapsed, 3),
            "blocks": [block.__dict__ for block in blocks],
        }

    def choose_extreme_audio_items(self, emotion: str, count: int = 1) -> list[dict[str, Any]]:
        """Pick prebuilt pure interjection audio items for the emotion."""
        emotion = str(emotion or "neutral").lower()
        allowed = PURE_INTERJECTION_CARRIERS.get(emotion, PURE_INTERJECTION_CARRIERS["neutral"])
        candidates = [
            item for item in self.extreme_audio
            if str(item.get("emotion", "")).lower() == emotion
            and str(item.get("carrier", "")).lower().strip() in allowed
            and item.get("audio_path")
        ]
        if not candidates:
            candidates = [
                item for item in self.extreme_audio
                if str(item.get("emotion", "")).lower() == "neutral"
                and str(item.get("carrier", "")).lower().strip() in PURE_INTERJECTION_CARRIERS["neutral"]
                and item.get("audio_path")
            ]
        if not candidates:
            return []

        self.rng.shuffle(candidates)
        return candidates[: max(0, count)]

    def choose_extreme_audio_item(self, emotion: str) -> dict[str, Any] | None:
        """Pick one prebuilt pure interjection audio manifest item for the emotion."""
        items = self.choose_extreme_audio_items(emotion, count=1)
        return items[0] if items else None

    def choose_extreme_audio(self, emotion: str) -> str | None:
        """Pick one prebuilt extreme nonverbal audio path for the emotion."""
        item = self.choose_extreme_audio_item(emotion)
        if not item:
            return None
        return str(item["audio_path"])

    def choose_waiting_audio_item(self) -> dict[str, Any] | None:
        """Pick a short neutral filler such as hm/mm while SlowTrack is not ready."""
        candidates = [
            item for item in self.extreme_audio
            if str(item.get("emotion", "")).lower() == "neutral"
            and str(item.get("carrier", "")).lower().strip() in PURE_INTERJECTION_CARRIERS["neutral"]
            and item.get("audio_path")
        ]
        if not candidates:
            return self.choose_extreme_audio_item("neutral")
        return self.rng.choice(candidates)

    def choose_thinking_bridge_audio_item(self, emotion: str = "neutral") -> dict[str, Any] | None:
        """Pick a short spoken thinking bridge before longer SlowTrack speech."""
        candidates = [
            item for item in self.thinking_bridge_audio
            if str(item.get("emotion", "")).lower() in {str(emotion or "").lower(), "neutral"}
            and item.get("audio_path")
        ]
        if not candidates:
            candidates = [item for item in self.thinking_bridge_audio if item.get("audio_path")]
        if not candidates:
            return None
        return self.rng.choice(candidates)

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
        style_control = self._style_control(emotion)
        audio_path = self.choose_extreme_audio(emotion)

        if block_id == 1:
            reaction = self._choose_reaction(emotion)
            text = reaction.strip()
            kind = "reaction_tts_style_motion"
        elif block_id == 2 and keywords:
            text = f"{keywords[0]}?"
            kind = "keyword_echo_tts_style_motion"
        elif block_id == 3:
            text = self._choose_intent_line(intent)
            kind = "intent_tts_style_motion"
        else:
            reaction = self._choose_reaction(emotion)
            text = reaction.strip()
            kind = "loop_cover"

        return CoverBlock(
            block_id=block_id,
            kind=kind,
            text=text,
            motion=motion,
            audio_path=audio_path,
            estimated_ms=1800.0 + len(text) * 18.0,
            metadata={
                "tts_style_control": style_control,
                "emotion_scores": category_scores,
                "intent": intent,
            },
        )

    def _style_control(self, emotion: str) -> dict[str, Any]:
        stylebert_map = {
            "positive": config.STYLEBERT_VITS2_STYLE_POSITIVE,
            "negative": config.STYLEBERT_VITS2_STYLE_NEGATIVE,
            "ambiguous": config.STYLEBERT_VITS2_STYLE_AMBIGUOUS,
            "neutral": config.STYLEBERT_VITS2_STYLE_NEUTRAL,
        }
        piper_length_map = {
            "positive": config.PIPER_TTS_LENGTH_SCALE_POSITIVE,
            "negative": config.PIPER_TTS_LENGTH_SCALE_NEGATIVE,
            "ambiguous": config.PIPER_TTS_LENGTH_SCALE_AMBIGUOUS,
            "neutral": config.PIPER_TTS_LENGTH_SCALE_NEUTRAL,
        }
        piper_noise_map = {
            "positive": config.PIPER_TTS_NOISE_SCALE_POSITIVE,
            "negative": config.PIPER_TTS_NOISE_SCALE_NEGATIVE,
            "ambiguous": config.PIPER_TTS_NOISE_SCALE_AMBIGUOUS,
            "neutral": config.PIPER_TTS_NOISE_SCALE_NEUTRAL,
        }
        return {
            "piper_tts": {
                "length_scale": piper_length_map.get(emotion, config.PIPER_TTS_LENGTH_SCALE),
                "noise_scale": piper_noise_map.get(emotion, config.PIPER_TTS_NOISE_SCALE),
                "noise_w": config.PIPER_TTS_NOISE_W,
            },
            "stylebert_vits2": stylebert_map.get(emotion, config.STYLEBERT_VITS2_STYLE),
            "fish_speech_cues": FISH_SPEECH_CUE_BUNDLES.get(emotion, FISH_SPEECH_CUE_BUNDLES["neutral"]),
            "inline_cues_enabled": config.FAST_TRACK_INLINE_CUES_ENABLED,
        }

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
