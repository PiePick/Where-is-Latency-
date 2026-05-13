"""Small persistent memory store for the AI VTuber prototype.

The LLM itself is stateless. This module keeps a lightweight external memory
file and injects relevant facts into SlowTrack prompts.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config


DEFAULT_MEMORY = {
    "version": 1,
    "user_profile": {
        "name": None,
        "likes": [],
        "dislikes": [],
        "speaking_style": "casual",
    },
    "emotional_events": [],
    "recent_turns": [],
}


@dataclass(frozen=True)
class MemorySettings:
    """Runtime limits for prompt-sized memory context."""

    path: Path = config.MEMORY_PATH
    max_recent_turns: int = config.MEMORY_MAX_RECENT_TURNS
    max_events: int = config.MEMORY_MAX_EVENTS


class MemoryStore:
    """JSON-backed memory for profile facts, recent turns, and emotional events."""

    def __init__(self, settings: MemorySettings | None = None) -> None:
        self.settings = settings or MemorySettings()
        self.settings.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def build_prompt_context(self) -> str:
        """Build a compact memory block for the local LLM prompt."""
        profile = self.data.get("user_profile", {})
        lines = ["Memory context. Use only when relevant; do not mention that you have memory."]

        name = profile.get("name")
        if name:
            lines.append(f"- User name: {name}")
        if profile.get("likes"):
            lines.append(f"- User likes: {', '.join(profile['likes'][:8])}")
        if profile.get("dislikes"):
            lines.append(f"- User dislikes: {', '.join(profile['dislikes'][:8])}")
        if profile.get("speaking_style"):
            lines.append(f"- User speaking style: {profile['speaking_style']}")

        events = self.data.get("emotional_events", [])[-self.settings.max_events :]
        if events:
            lines.append("- Important emotional memories:")
            for event in events:
                lines.append(
                    f"  - {event.get('emotion', 'Unknown')}: {event.get('summary', '')}"
                )

        turns = self.data.get("recent_turns", [])[-self.settings.max_recent_turns :]
        if turns:
            lines.append("- Recent conversation:")
            for turn in turns:
                lines.append(f"  - User: {turn.get('user', '')}")
                lines.append(f"    Assistant: {turn.get('assistant', '')}")

        return "\n".join(lines)

    def record_turn(
        self,
        *,
        user_text: str,
        assistant_text: str,
        fast_reaction: str | None,
        emotion: str | None,
        keywords: list[str] | None = None,
    ) -> None:
        """Persist one conversation turn and extract simple long-term facts."""
        user_text = self._clean_text(user_text)
        assistant_text = self._clean_text(assistant_text)
        if not user_text:
            return

        self._update_profile(user_text)
        self._append_recent_turn(user_text, assistant_text, fast_reaction, emotion)
        self._maybe_add_emotional_event(user_text, emotion, keywords or [])
        self._save()

    def _load(self) -> dict[str, Any]:
        """Load existing memory or initialize a fresh structure."""
        if not self.settings.path.exists():
            return deepcopy(DEFAULT_MEMORY)
        try:
            loaded = json.loads(self.settings.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = self.settings.path.with_suffix(".broken.json")
            self.settings.path.replace(backup)
            return deepcopy(DEFAULT_MEMORY)
        return self._merge_defaults(loaded)

    def _save(self) -> None:
        """Write memory atomically enough for a local single-user prototype."""
        tmp_path = self.settings.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.settings.path)

    def _merge_defaults(self, loaded: dict[str, Any]) -> dict[str, Any]:
        """Keep older memory files compatible with the current schema."""
        merged = deepcopy(DEFAULT_MEMORY)
        for key, value in loaded.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        return merged

    def _update_profile(self, text: str) -> None:
        """Extract simple stable profile facts from first-person statements."""
        profile = self.data.setdefault("user_profile", deepcopy(DEFAULT_MEMORY["user_profile"]))
        name = self._first_match(
            text,
            [
                r"\bmy name is\s+([A-Za-z][A-Za-z0-9 _-]{0,40})",
                r"\bcall me\s+([A-Za-z][A-Za-z0-9 _-]{0,40})",
            ],
        )
        if name:
            profile["name"] = self._trim_phrase(name)

        for pattern, field in (
            (r"\bi (?:really )?(?:like|love|enjoy)\s+([^.!?]{2,80})", "likes"),
            (r"\bi (?:really )?(?:hate|dislike|don't like)\s+([^.!?]{2,80})", "dislikes"),
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                self._append_unique(profile.setdefault(field, []), self._trim_phrase(match.group(1)), 12)

    def _append_recent_turn(
        self,
        user_text: str,
        assistant_text: str,
        fast_reaction: str | None,
        emotion: str | None,
    ) -> None:
        """Keep a short rolling window of recent dialogue turns."""
        turns = self.data.setdefault("recent_turns", [])
        turns.append(
            {
                "time": self._now(),
                "user": user_text,
                "assistant": assistant_text,
                "fast_reaction": fast_reaction,
                "emotion": emotion,
            }
        )
        del turns[: max(0, len(turns) - self.settings.max_recent_turns)]

    def _maybe_add_emotional_event(
        self,
        user_text: str,
        emotion: str | None,
        keywords: list[str],
    ) -> None:
        """Save only emotionally meaningful user facts for long-term recall."""
        normalized = (emotion or "").lower()
        if normalized not in {"positive", "negative", "ambiguous"}:
            return
        if len(user_text.split()) < 4:
            return

        summary = f"User said: {user_text}"
        events = self.data.setdefault("emotional_events", [])
        if any(event.get("summary") == summary for event in events):
            return

        events.append(
            {
                "time": self._now(),
                "emotion": normalized.title(),
                "summary": summary,
                "keywords": keywords[:8],
                "importance": self._importance(normalized),
            }
        )
        events.sort(key=lambda item: (float(item.get("importance", 0.0)), item.get("time", "")))
        del events[: max(0, len(events) - self.settings.max_events)]

    def _importance(self, emotion: str) -> float:
        """Assign a coarse importance score for retention."""
        if emotion == "negative":
            return 0.85
        if emotion == "positive":
            return 0.7
        return 0.55

    def _first_match(self, text: str, patterns: list[str]) -> str | None:
        """Return the first regex group matched by any pattern."""
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _append_unique(self, items: list[str], value: str, limit: int) -> None:
        """Append a short value while preserving order and avoiding duplicates."""
        if not value:
            return
        lowered = {item.lower() for item in items}
        if value.lower() not in lowered:
            items.append(value)
        del items[: max(0, len(items) - limit)]

    def _trim_phrase(self, value: str) -> str:
        """Normalize one extracted profile phrase."""
        value = self._clean_text(value)
        value = re.sub(r"\b(?:and|but|because|when|if)\b.*$", "", value, flags=re.IGNORECASE)
        return value.strip(" ,.;:!?\"'()")[:80]

    def _clean_text(self, value: str | None) -> str:
        """Collapse whitespace and keep prompt memory compact."""
        return re.sub(r"\s+", " ", value or "").strip()[:500]

    def _now(self) -> str:
        """Return an ISO timestamp for memory entries."""
        return datetime.now(timezone.utc).isoformat()
