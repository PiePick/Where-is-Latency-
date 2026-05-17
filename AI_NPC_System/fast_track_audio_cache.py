"""Prebuilt FastTrack audio cache lookup.

The cache is generated offline so runtime FastTrack can return a ready audio
file instead of calling a slow tag-aware TTS model inside the live path.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CachedCover:
    """One pre-generated latency cover utterance."""

    cache_id: str
    category: str
    source: str
    reaction: str
    plain_tts_text: str
    tts_text: str
    audio_path: Path
    cue: dict[str, Any] | None


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
