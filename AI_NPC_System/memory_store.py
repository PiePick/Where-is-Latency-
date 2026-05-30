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
    "version": 2,
    "user_profile": {
        "name": None,
        "likes": [],
        "dislikes": [],
        "facts": [],
        "speaking_style": "casual",
    },
    "viewer_profiles": {},
    "recent_donations": [],
    "stream_events": [],
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
        lines = [
            "Memory context. Use only when relevant; do not mention that you have memory.",
            "The spoken answer must stay short even if this private context is rich.",
        ]

        name = profile.get("name")
        if name:
            lines.append(f"- User name: {name}")
        if profile.get("likes"):
            lines.append(f"- User likes: {', '.join(profile['likes'][:8])}")
        if profile.get("dislikes"):
            lines.append(f"- User dislikes: {', '.join(profile['dislikes'][:8])}")
        if profile.get("facts"):
            lines.append(f"- Useful user facts: {'; '.join(profile['facts'][:8])}")
        if profile.get("speaking_style"):
            lines.append(f"- User speaking style: {profile['speaking_style']}")

        viewers = self.data.get("viewer_profiles", {})
        viewer_rows = []
        for name, viewer in sorted(
            viewers.items(),
            key=lambda item: str(item[1].get("last_seen", "")),
            reverse=True,
        )[:6]:
            facts = "; ".join(viewer.get("facts", [])[-3:])
            topics = ", ".join(viewer.get("topics", [])[-4:])
            tone = viewer.get("last_emotion") or "neutral"
            summary = f"{name}: last emotion {tone}"
            if topics:
                summary += f"; topics {topics}"
            if facts:
                summary += f"; facts {facts}"
            viewer_rows.append(summary)
        if viewer_rows:
            lines.append("- Viewer memory by nickname:")
            for row in viewer_rows:
                lines.append(f"  - {row}")

        donations = self.data.get("recent_donations", [])[-4:]
        if donations:
            lines.append("- Recent donation counseling:")
            for item in donations:
                viewer = item.get("viewer") or "viewer"
                text = item.get("message") or ""
                emotion = item.get("emotion") or "neutral"
                lines.append(f"  - {viewer} ({emotion}): {text}")

        stream_events = self.data.get("stream_events", [])[-5:]
        if stream_events:
            lines.append("- Recent stream events:")
            for item in stream_events:
                event = item.get("event") or "turn"
                viewer = item.get("viewer") or "chat"
                topic = item.get("topic") or ""
                summary = item.get("summary") or ""
                topic_part = f"; topic {topic}" if topic else ""
                lines.append(f"  - {event} with {viewer}{topic_part}: {summary}")

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
        viewer_name: str | None = None,
        event: str | None = None,
        topic: str | None = None,
        donation_amount: str | None = None,
        recent_chat: str | None = None,
    ) -> None:
        """Persist one conversation turn and extract simple long-term facts."""
        user_text = self._clean_text(user_text)
        assistant_text = self._clean_text(assistant_text)
        if not user_text:
            return

        inferred_viewer = self._clean_viewer_name(viewer_name) or self._infer_viewer_name(user_text)
        inferred_event = self._infer_event(user_text, event)
        topic = self._trim_phrase(topic or "")
        recent_chat = self._clean_text(recent_chat)
        self._update_profile(user_text)
        self._update_viewer_profile(inferred_viewer, user_text, emotion, keywords or [])
        self._append_recent_turn(user_text, assistant_text, fast_reaction, emotion, inferred_viewer, inferred_event)
        self._append_stream_event(inferred_event, inferred_viewer, user_text, assistant_text, emotion, topic, recent_chat)
        if inferred_event == "donation":
            self._append_recent_donation(inferred_viewer, user_text, emotion, donation_amount)
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
        merged["version"] = DEFAULT_MEMORY["version"]
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

        fact_patterns = [
            r"\bi(?:'m| am) working on\s+([^.!?]{2,100})",
            r"\bi(?:'m| am) studying\s+([^.!?]{2,100})",
            r"\bi(?:'m| am) building\s+([^.!?]{2,100})",
            r"\bmy project is\s+([^.!?]{2,100})",
            r"\bmy favorite\s+([^.!?]{2,100})",
            r"\bi(?:'m| am) from\s+([^.!?]{2,80})",
        ]
        for pattern in fact_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                self._append_unique(profile.setdefault("facts", []), self._trim_phrase(match.group(0)), 16)
                break

        if re.search(r"\b(?:speak|talk|answer|reply)\b.*\bcasual(?:ly)?\b", text, flags=re.IGNORECASE):
            profile["speaking_style"] = "casual"
        elif re.search(r"\b(?:speak|talk|answer|reply)\b.*\bshort(?:ly)?\b", text, flags=re.IGNORECASE):
            profile["speaking_style"] = "brief"

    def _append_recent_turn(
        self,
        user_text: str,
        assistant_text: str,
        fast_reaction: str | None,
        emotion: str | None,
        viewer_name: str | None,
        event: str,
    ) -> None:
        """Keep a short rolling window of recent dialogue turns."""
        turns = self.data.setdefault("recent_turns", [])
        turns.append(
            {
                "time": self._now(),
                "viewer": viewer_name,
                "event": event,
                "user": user_text,
                "assistant": assistant_text,
                "fast_reaction": fast_reaction,
                "emotion": emotion,
            }
        )
        del turns[: max(0, len(turns) - self.settings.max_recent_turns)]

    def _update_viewer_profile(
        self,
        viewer_name: str | None,
        user_text: str,
        emotion: str | None,
        keywords: list[str],
    ) -> None:
        """Track short per-viewer memory for live stream continuity."""
        if not viewer_name:
            return
        viewers = self.data.setdefault("viewer_profiles", {})
        viewer = viewers.setdefault(
            viewer_name,
            {
                "facts": [],
                "topics": [],
                "last_emotion": "neutral",
                "last_seen": "",
                "turn_count": 0,
            },
        )
        viewer["last_seen"] = self._now()
        viewer["last_emotion"] = str(emotion or "neutral").lower()
        viewer["turn_count"] = int(viewer.get("turn_count") or 0) + 1
        for keyword in keywords[:6]:
            keyword = self._trim_phrase(str(keyword or ""))
            if keyword:
                self._append_unique(viewer.setdefault("topics", []), keyword, 12)
        fact = self._extract_viewer_fact(user_text)
        if fact:
            self._append_unique(viewer.setdefault("facts", []), fact, 10)
        if len(viewers) > 24:
            oldest = sorted(viewers.items(), key=lambda item: str(item[1].get("last_seen", "")))
            for name, _value in oldest[: len(viewers) - 24]:
                viewers.pop(name, None)

    def _append_recent_donation(
        self,
        viewer_name: str | None,
        user_text: str,
        emotion: str | None,
        donation_amount: str | None,
    ) -> None:
        """Keep recent donation counseling context separate from normal chat."""
        donations = self.data.setdefault("recent_donations", [])
        message = self._strip_event_prefix(user_text)
        donations.append(
            {
                "time": self._now(),
                "viewer": viewer_name or self._infer_viewer_name(user_text) or "viewer",
                "amount": self._trim_phrase(donation_amount or ""),
                "emotion": str(emotion or "neutral").lower(),
                "message": message[:260],
            }
        )
        del donations[: max(0, len(donations) - 8)]

    def _append_stream_event(
        self,
        event: str,
        viewer_name: str | None,
        user_text: str,
        assistant_text: str,
        emotion: str | None,
        topic: str,
        recent_chat: str,
    ) -> None:
        """Track a compact sequence of stream events for SlowTrack continuity."""
        if event == "turn" and not recent_chat:
            return
        events = self.data.setdefault("stream_events", [])
        summary_bits = [self._strip_event_prefix(user_text)]
        if recent_chat and recent_chat not in user_text:
            summary_bits.append(f"recent chat: {recent_chat}")
        if assistant_text:
            summary_bits.append(f"answered: {assistant_text}")
        events.append(
            {
                "time": self._now(),
                "event": event,
                "viewer": viewer_name or "chat",
                "emotion": str(emotion or "neutral").lower(),
                "topic": topic,
                "summary": self._clean_text(" | ".join(summary_bits))[:360],
            }
        )
        del events[: max(0, len(events) - 12)]

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

    def _infer_viewer_name(self, text: str) -> str | None:
        """Infer a viewer nickname from live-chat or donation phrasing."""
        return self._clean_viewer_name(
            self._first_match(
                text,
                [
                    r"\bViewer\s+([A-Za-z0-9 _-]{1,48})\s+says\s*:",
                    r"\b([A-Za-z0-9 _-]{1,48})\s+sent support\b",
                    r"\bviewer\s+\"([^\"]{1,48})\"",
                ],
            )
        )

    def _infer_event(self, text: str, event: str | None) -> str:
        """Infer a stream event type from metadata or text."""
        event = str(event or "").strip().lower()
        if event:
            return event
        lowered = text.lower()
        if "vtuber mode donation" in lowered or " sent support" in lowered:
            return "donation"
        if "live chat" in lowered or "viewer " in lowered:
            return "live_chat"
        if "vtuber mode idle" in lowered:
            return "idle"
        return "turn"

    def _clean_viewer_name(self, value: str | None) -> str | None:
        """Normalize viewer names for memory keys."""
        name = re.sub(r"\s+", " ", str(value or "")).strip(" @:;,.!?\"'")
        if not name or name.lower() in {"viewer", "chat", "anonymous", "anonymousdonor"}:
            return None
        return name[:48]

    def _extract_viewer_fact(self, text: str) -> str | None:
        """Extract one short viewer-specific fact from a message."""
        cleaned = self._strip_event_prefix(text)
        fact = self._first_match(
            cleaned,
            [
                r"\bi(?:'m| am) working on\s+([^.!?]{2,90})",
                r"\bi(?:'m| am) studying\s+([^.!?]{2,90})",
                r"\bi(?:'m| am) building\s+([^.!?]{2,90})",
                r"\bmy(?: current)? project is\s+([^.!?]{2,90})",
                r"\bi have to\s+([^.!?]{2,90})",
                r"\bi keep\s+([^.!?]{2,90})",
            ],
        )
        if fact:
            return self._trim_phrase(fact)
        return None

    def _strip_event_prefix(self, text: str) -> str:
        """Remove transport prefixes from memory summaries."""
        text = re.sub(r"^VTuber mode [a-z_]+:\s*", "", str(text or ""), flags=re.IGNORECASE)
        text = re.sub(r"^\[Live chat:[^\]]+\]\s*", "", text, flags=re.IGNORECASE)
        return self._clean_text(text)

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
