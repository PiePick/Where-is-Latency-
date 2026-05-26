"""Legacy FastTrack cache and static-manifest compatibility helpers.

The active live path uses ``fasttrack_router_v3`` and the separated
GoEmotions/SWDA dataset pool. These classes remain only for disabled cached
audio experiments and for small compatibility helpers used by the Open-LLM
adapter.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


USER_INTENT_TO_RESPONSE_ACT_WEIGHTS: dict[str, tuple[tuple[str, float], ...]] = {
    # Incoming user intent is not the response intent. Runtime samples a response
    # act from these distributions, then picks a prebuilt audio/text candidate.
    # QUESTION is intentionally excluded from response acts because a FastTrack
    # follow-up question often conflicts with the pending SlowTrack answer.
    "QUESTION": (
        ("INFORM", 0.48),
        ("ACKNOWLEDGE", 0.28),
        ("EXPRESSIVE", 0.15),
        ("DIRECTIVE", 0.07),
        ("REJECT", 0.02),
    ),
    "INFORM": (
        ("ACKNOWLEDGE", 0.44),
        ("EXPRESSIVE", 0.30),
        ("INFORM", 0.16),
        ("DIRECTIVE", 0.07),
        ("REJECT", 0.03),
    ),
    "ACKNOWLEDGE": (
        ("ACKNOWLEDGE", 0.50),
        ("EXPRESSIVE", 0.26),
        ("INFORM", 0.14),
        ("DIRECTIVE", 0.07),
        ("REJECT", 0.03),
    ),
    "DIRECTIVE": (
        ("ACKNOWLEDGE", 0.35),
        ("DIRECTIVE", 0.28),
        ("INFORM", 0.21),
        ("EXPRESSIVE", 0.11),
        ("REJECT", 0.05),
    ),
    "EXPRESSIVE": (
        ("EXPRESSIVE", 0.46),
        ("ACKNOWLEDGE", 0.32),
        ("INFORM", 0.13),
        ("DIRECTIVE", 0.07),
        ("REJECT", 0.02),
    ),
    "REJECT": (
        ("ACKNOWLEDGE", 0.34),
        ("REJECT", 0.29),
        ("INFORM", 0.17),
        ("EXPRESSIVE", 0.12),
        ("DIRECTIVE", 0.08),
    ),
}

DISALLOWED_RESPONSE_ACTS = {"QUESTION"}
FALLBACK_RESPONSE_ACT = "ACKNOWLEDGE"


def normalize_response_act(response_act: str) -> str:
    """Return a runtime-safe FastTrack response act."""
    act = str(response_act or FALLBACK_RESPONSE_ACT).upper()
    return FALLBACK_RESPONSE_ACT if act in DISALLOWED_RESPONSE_ACTS else act


@dataclass(frozen=True)
class CachedCover:
    """One pre-generated latency cover utterance."""

    cache_id: str
    category: str
    source: str
    reaction: str
    plain_tts_text: str
    tts_text: str
    audio_path: Path | None
    cue: dict[str, Any] | None
    response_act: str = ""
    style_tag: str = ""


class FastTrackAudioCache:
    """Load and sample pre-generated FastTrack cover audio."""

    def __init__(
        self,
        manifest_path: Path,
        *,
        enabled: bool = True,
        seed: int | None = None,
        expected_reference_id: str | None = None,
        strict_reference: bool = True,
    ) -> None:
        self.manifest_path = manifest_path
        self.enabled = enabled
        self.rng = random.Random(seed)
        self.expected_reference_id = expected_reference_id
        self.strict_reference = strict_reference
        self.metadata: dict[str, Any] = {}
        self._by_category: dict[str, list[CachedCover]] = {}
        self._by_category_source: dict[tuple[str, str], list[CachedCover]] = {}
        if enabled:
            self._load()

    @property
    def available(self) -> bool:
        """Return true when the manifest has at least one usable audio item."""
        return bool(self._by_category)

    def choose(
        self,
        category: str,
        *,
        preferred_source: str | None = None,
    ) -> CachedCover | None:
        """Sample one cached cover, preferring a keyword-selected source when possible."""
        if not self.enabled or not self.available:
            return None

        candidates: list[CachedCover] = []
        if preferred_source:
            candidates = self._by_category_source.get((category, preferred_source), [])
        if not candidates:
            candidates = self._by_category.get(category, [])
        if not candidates:
            candidates = self._by_category.get("Neutral", [])
        if not candidates:
            return None
        return self.rng.choice(candidates)

    def _load(self) -> None:
        """Read a legacy FastTrack audio manifest when cache fallback is enabled."""
        if not self.manifest_path.exists():
            return

        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.metadata = raw.get("tts_reference", {}) if isinstance(raw, dict) else {}
        if self.strict_reference and self.expected_reference_id:
            cache_reference = str(self.metadata.get("reference_id", "")).strip()
            if cache_reference != self.expected_reference_id:
                return

        root = self.manifest_path.parent
        for item in raw.get("items", []):
            audio_path = Path(str(item.get("audio_path", "")))
            if not audio_path.is_absolute():
                audio_path = (root / audio_path).resolve()
            if not audio_path.exists():
                continue

            cover = CachedCover(
                cache_id=str(item["id"]),
                category=str(item["category"]),
                source=str(item["source"]),
                reaction=str(item["reaction"]),
                plain_tts_text=str(item["plain_tts_text"]),
                tts_text=str(item["tts_text"]),
                audio_path=audio_path,
                cue=item.get("cue"),
            )
            self._by_category.setdefault(cover.category, []).append(cover)
            self._by_category_source.setdefault((cover.category, cover.source), []).append(cover)

class PersonaReactionBundle:
    """Legacy static persona manifest lookup.

    Active runtime sets ``FAST_TRACK_PERSONA_BUNDLE_ENABLED=0`` and receives
    text from router v3. This class is kept so older cached-manifest
    experiments can still be reproduced deliberately.
    """

    def __init__(
        self,
        manifest_path: Path,
        *,
        enabled: bool = True,
        seed: int | None = None,
        expected_reference_id: str | None = None,
        strict_reference: bool = True,
        personality_id: str | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.enabled = enabled
        self.rng = random.Random(seed)
        self.expected_reference_id = expected_reference_id
        self.strict_reference = strict_reference
        self.personality_id = personality_id
        self.metadata: dict[str, Any] = {}
        self._by_cell: dict[tuple[str, str, str], list[CachedCover]] = {}
        self._by_emotion_response_act: dict[tuple[str, str], list[CachedCover]] = {}
        self._by_emotion: dict[str, list[CachedCover]] = {}
        if enabled:
            self._load()

    @property
    def available(self) -> bool:
        """Return true when the bundle has at least one usable item."""
        return bool(self._by_emotion)

    def choose(self, emotion: str, intent: str, style_tag: str = "") -> CachedCover | None:
        """Choose by emotion plus a sampled response act for the incoming user intent."""
        if not self.enabled or not self.available:
            return None
        emotion_key = str(emotion or "Neutral").lower()
        if emotion_key == "ambiguous":
            emotion_key = "surprise"
        user_intent = str(intent or "ACKNOWLEDGE").upper()
        response_act = self._sample_response_act(user_intent)
        style_key = str(style_tag or "bright").lower()
        candidates = self._by_cell.get((emotion_key, response_act, style_key), [])
        if not candidates:
            candidates = self._by_emotion_response_act.get((emotion_key, response_act), [])
        if not candidates:
            candidates = self._by_emotion.get(emotion_key, [])
        if not candidates:
            candidates = self._by_emotion.get("neutral", [])
        if not candidates:
            return None
        return self.rng.choice(candidates)

    def choose_by_response_act(self, emotion: str, response_act: str, *, top_k: int = 3) -> list[CachedCover]:
        """Return candidate reactions from the compressed emotion/response-act cell."""
        if not self.enabled or not self.available:
            return []
        emotion_key = str(emotion or "Neutral").lower()
        if emotion_key == "ambiguous":
            emotion_key = "surprise"
        act_key = normalize_response_act(response_act)
        candidates = list(self._by_emotion_response_act.get((emotion_key, act_key), []))
        if not candidates:
            candidates = list(self._by_emotion.get(emotion_key, []))
        if not candidates:
            candidates = list(self._by_emotion.get("neutral", []))
        self.rng.shuffle(candidates)
        return candidates[: max(1, int(top_k))]

    def choose_by_emotion(self, emotion: str) -> CachedCover | None:
        """Choose from one GoEmotions bucket without conditioning on response act."""
        if not self.enabled or not self.available:
            return None
        emotion_key = str(emotion or "Neutral").lower()
        if emotion_key == "ambiguous":
            emotion_key = "surprise"
        candidates = list(self._by_emotion.get(emotion_key, []))
        if not candidates:
            candidates = list(self._by_emotion.get("neutral", []))
        return self.rng.choice(candidates) if candidates else None

    def choose_neutral_random(self) -> CachedCover | None:
        """Choose randomly from the neutral pool while ignoring detected context."""
        if not self.enabled or not self.available:
            return None
        candidates = list(self._by_emotion.get("neutral", []))
        return self.rng.choice(candidates) if candidates else None

    def choose_by_response_act_only(self, response_act: str) -> CachedCover | None:
        """Choose by SWDA response act while ignoring the detected emotion bucket."""
        if not self.enabled or not self.available:
            return None
        act_key = normalize_response_act(response_act)
        candidates = [
            cover
            for (_emotion, candidate_act), items in self._by_emotion_response_act.items()
            if candidate_act == act_key
            for cover in items
        ]
        if not candidates:
            candidates = [cover for items in self._by_emotion.values() for cover in items]
        return self.rng.choice(candidates) if candidates else None

    def choose_random(self) -> CachedCover | None:
        """Choose a label-agnostic candidate for the random-selection ablation."""
        if not self.enabled or not self.available:
            return None
        candidates = [cover for items in self._by_emotion.values() for cover in items]
        return self.rng.choice(candidates) if candidates else None

    def sample_response_act(self, user_intent: str) -> str:
        """Expose SWDA adjacent-turn response-act sampling for ablations."""
        return self._sample_response_act(user_intent)

    def _sample_response_act(self, user_intent: str) -> str:
        """Sample how CREDO should respond to the detected incoming intent."""
        raw_weights = USER_INTENT_TO_RESPONSE_ACT_WEIGHTS.get(
            str(user_intent or "ACKNOWLEDGE").upper(),
            USER_INTENT_TO_RESPONSE_ACT_WEIGHTS["ACKNOWLEDGE"],
        )
        weights = tuple(
            (normalize_response_act(act), weight)
            for act, weight in raw_weights
            if str(act or "").upper() not in DISALLOWED_RESPONSE_ACTS
        ) or ((FALLBACK_RESPONSE_ACT, 1.0),)
        threshold = self.rng.random() * sum(weight for _act, weight in weights)
        cumulative = 0.0
        for act, weight in weights:
            cumulative += weight
            if threshold <= cumulative:
                return act
        return weights[-1][0]

    def _load(self) -> None:
        if not self.manifest_path.exists():
            return

        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.metadata = raw.get("tts_reference", {}) if isinstance(raw, dict) else {}
        manifest_personality_id = str(raw.get("personality_id", "")).strip() if isinstance(raw, dict) else ""
        if self.strict_reference and self.expected_reference_id:
            cache_reference = str(self.metadata.get("reference_id", "")).strip()
            if cache_reference != self.expected_reference_id:
                return

        root = self.manifest_path.parent
        cell_meta_by_id = {
            str(cell.get("cell_id")): cell
            for cell in raw.get("cells", [])
            if isinstance(cell, dict)
        }
        for item in raw.get("items", []):
            item_personality_id = str(item.get("personality_id") or manifest_personality_id).strip()
            if self.personality_id and item_personality_id != self.personality_id:
                continue
            raw_audio = str(item.get("audio_path") or "").strip()
            audio_path: Path | None = None
            if raw_audio:
                audio_path = Path(raw_audio)
                if not audio_path.is_absolute():
                    audio_path = (root / audio_path).resolve()
                if not audio_path.exists():
                    audio_path = None

            cell_meta = cell_meta_by_id.get(str(item.get("cell_id")), {})
            emotion = str(item.get("emotion") or cell_meta.get("emotion") or item.get("category") or "Neutral")
            if emotion.lower() == "ambiguous":
                emotion = "Surprise"
            response_act = str(
                item.get("response_act")
                or cell_meta.get("response_act")
                or item.get("intent")
                or cell_meta.get("intent")
                or "ACKNOWLEDGE"
            ).upper()
            if response_act in DISALLOWED_RESPONSE_ACTS:
                continue
            response_act = normalize_response_act(response_act)
            style_tag = str(item.get("style_tag") or cell_meta.get("style_tag") or "").lower()
            reaction = str(item.get("reaction") or item.get("plain_tts_text") or "")
            plain_tts_text = str(item.get("plain_tts_text") or reaction)
            tts_text = str(item.get("tts_text") or plain_tts_text)
            cover = CachedCover(
                cache_id=str(item["id"]),
                category=emotion,
                source=str(item.get("source") or "persona_bundle"),
                reaction=reaction,
                plain_tts_text=plain_tts_text,
                tts_text=tts_text,
                audio_path=audio_path,
                cue=item.get("cue"),
                response_act=response_act,
                style_tag=style_tag,
            )
            if not cover.plain_tts_text:
                continue
            emotion_key = emotion.lower()
            if style_tag:
                self._by_cell.setdefault((emotion_key, response_act, style_tag), []).append(cover)
            self._by_emotion_response_act.setdefault((emotion_key, response_act), []).append(cover)
            self._by_emotion.setdefault(emotion_key, []).append(cover)
