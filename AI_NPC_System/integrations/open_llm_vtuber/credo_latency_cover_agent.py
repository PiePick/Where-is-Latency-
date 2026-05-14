"""Open-LLM-VTuber Agent adapter for the CREDO latency-cover pipeline.

This file is copied into `vendor/open-llm-vtuber` by `apply_integration.py`.
It keeps Open-LLM-VTuber responsible for the UI, Live2D frontend, ASR, and
websocket loop while delegating the research logic to `AI_NPC_System`.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from pathlib import Path
from typing import Any, AsyncIterator

from loguru import logger

from ..input_types import BaseInput, BatchInput, TextSource
from ..output_types import Actions, AudioOutput, DisplayText, SentenceOutput
from .agent_interface import AgentInterface


DEFAULT_EXPRESSION_TAGS = {
    "positive": ["joy", "happy", "smile", "positive_01"],
    "negative": ["sadness", "sad", "worried", "negative_01"],
    "ambiguous": ["surprise", "confused", "ambiguous_01"],
    "neutral": ["neutral", "idle", "neutral_01"],
}


PROACTIVE_IDLE_COVERS = [
    {
        "text": "Great.",
        "audio": "fast_track_audio_cache/Positive/everyday/bd103151cfbbbb32.wav",
        "emotion": "positive",
    },
    {
        "text": "Good work, friend.",
        "audio": "fast_track_audio_cache/Positive/stream/e551e29fc1249359.wav",
        "emotion": "positive",
    },
    {
        "text": "Fair enough.",
        "audio": "fast_track_audio_cache/Neutral/stream/8cbbaa5f2ddb319e.wav",
        "emotion": "neutral",
    },
    {
        "text": "No problem, anytime.",
        "audio": "fast_track_audio_cache/Neutral/everyday/41f42f8fd64754ba.wav",
        "emotion": "neutral",
    },
]


class CredoLatencyCoverAgent(AgentInterface):
    """Run CREDO FastTrack first, then continue with CREDO SlowTrack."""

    def __init__(
        self,
        *,
        settings: dict[str, Any],
        system_prompt: str,
        live2d_model=None,
        character_avatar: str = "",
    ) -> None:
        self.settings = settings or {}
        self.system_prompt = system_prompt
        self.live2d_model = live2d_model
        self.character_avatar = character_avatar
        self.character_name = str(self.settings.get("character_name", "AI"))
        self.use_fast_audio = bool(self.settings.get("use_fast_audio", True))
        self.slow_enabled = bool(self.settings.get("slow_enabled", True))
        self.slow_tts_mode = str(self.settings.get("slow_tts_mode", "credo_fish_speech"))
        self.record_memory = bool(self.settings.get("record_memory", True))
        self.expression_map = self.settings.get("expression_map") or DEFAULT_EXPRESSION_TAGS
        self.rng = random.Random(self.settings.get("seed"))
        self._proactive_count = 0

        self.ai_npc_path = self._resolve_ai_npc_path()
        self._load_credo_modules()

        self.memory = None
        if self.record_memory and self._credo_config.MEMORY_ENABLED:
            self.memory = self._memory_store.MemoryStore()

        self.fish_tts = None
        if self.slow_tts_mode == "credo_fish_speech":
            self.fish_tts = self._tts_client.FishSpeechTTSClient()

        logger.info(f"CREDO latency-cover agent loaded from {self.ai_npc_path}")

    def _resolve_ai_npc_path(self) -> Path:
        """Resolve the CREDO AI_NPC_System folder from config or environment."""
        configured = (
            self.settings.get("ai_npc_path")
            or os.getenv("CREDO_AI_NPC_PATH")
            or "../../AI_NPC_System"
        )
        path = Path(str(configured)).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve()
        if not (path / "fast_track.py").exists():
            raise FileNotFoundError(f"CREDO AI_NPC_System not found: {path}")
        return path

    def _load_credo_modules(self) -> None:
        """Import CREDO runtime modules after adding AI_NPC_System to sys.path."""
        sys.path.insert(0, str(self.ai_npc_path))
        import config as credo_config
        import fast_track
        import slow_track
        import tts_client
        from memory_store import MemoryStore

        self._credo_config = credo_config
        self._fast_track = fast_track
        self._slow_track = slow_track
        self._tts_client = tts_client
        self._memory_store = type("_MemoryModule", (), {"MemoryStore": MemoryStore})

    async def chat(self, input_data: BaseInput) -> AsyncIterator[AudioOutput | SentenceOutput]:
        """Yield the cached latency cover before the slower generated response."""
        user_text, is_proactive = self._extract_input(input_data)
        if not user_text:
            return

        if is_proactive:
            yield self._build_proactive_output()
            return

        fast_result = await asyncio.to_thread(self._fast_track.analyze_and_react, user_text)
        fast_tts_text = fast_result.get("tts_text") or fast_result.get("reaction") or "I see."
        fast_display_text = fast_result.get("plain_tts_text") or fast_result.get("reaction") or fast_tts_text
        emotion = str(fast_result.get("emotion_label", "neutral")).lower()
        actions = self._build_actions(emotion)

        logger.info(
            "CREDO FastTrack cover: "
            f"emotion={emotion}, source={fast_result.get('reaction_source')}, "
            f"cache={fast_result.get('fast_audio_cache_hit')}"
        )

        fast_audio_path = fast_result.get("fast_audio_path")
        if self.use_fast_audio and fast_audio_path and Path(str(fast_audio_path)).exists():
            yield AudioOutput(
                audio_path=str(fast_audio_path),
                display_text=self._display(fast_display_text),
                transcript=fast_display_text,
                actions=actions,
            )
        else:
            yield SentenceOutput(
                display_text=self._display(fast_display_text),
                tts_text=fast_tts_text,
                actions=actions,
            )

        if not self.slow_enabled:
            return

        memory_context = self.memory.build_prompt_context() if self.memory else None
        slow_text = await self._slow_track.generate_response(
            user_text,
            fast_tts_text,
            fast_result.get("strategy"),
            memory_context,
        )
        slow_text = slow_text.strip() or "I hear you."

        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        if slow_audio:
            yield AudioOutput(
                audio_path=str(slow_audio),
                display_text=self._display(slow_text),
                transcript=slow_text,
                actions=actions,
            )
        else:
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text=slow_text,
                actions=actions,
            )

        if self.memory:
            self.memory.record_turn(
                user_text=user_text,
                assistant_text=slow_text,
                fast_reaction=fast_tts_text,
                emotion=emotion,
                keywords=fast_result.get("keywords") or [],
            )

    def _extract_user_text(self, input_data: BaseInput) -> str:
        """Backward-compatible helper used by local tests."""
        text, _is_proactive = self._extract_input(input_data)
        return text

    def _extract_input(self, input_data: BaseInput) -> tuple[str, bool]:
        """Extract the normal text input from Open-LLM-VTuber's BatchInput."""
        if isinstance(input_data, BatchInput):
            parts = [
                item.content
                for item in input_data.texts
                if item.source == TextSource.INPUT and item.content
            ]
            text = "\n".join(parts).strip()
            if self._is_proactive_input(input_data, text):
                return self._build_proactive_prompt(), True
            return text, False
        return str(input_data).strip(), False

    def _is_proactive_input(self, input_data: BatchInput, text: str) -> bool:
        """Detect Open-LLM-VTuber's idle/proactive speak request."""
        metadata = input_data.metadata or {}
        if metadata.get("proactive_speak"):
            return True
        normalized = " ".join(text.lower().split())
        return normalized.startswith("please say something")

    def _build_proactive_prompt(self) -> str:
        """Turn a repeated idle trigger into varied conversational intent."""
        self._proactive_count += 1
        choices = [
            "Start a brief upbeat idle comment as an AI VTuber waiting for chat. Do not mention tests or system state.",
            "Make a short curious remark that invites the viewer to share something. Do not say this is a test phase.",
            "Offer one playful observation about the quiet moment, then ask a light question.",
            "Say a concise warm check-in for the viewer, avoiding generic filler and avoiding the word test.",
            "React as if the stream has gone quiet for a moment; keep it natural, brief, and emotionally positive.",
            "Make a small self-contained comment that would fit between viewer messages. Do not repeat previous idle lines.",
        ]
        prompt = self.rng.choice(choices)
        return f"{prompt} Idle turn number: {self._proactive_count}."

    def _build_proactive_output(self) -> AudioOutput | SentenceOutput:
        """Return an immediate cached idle utterance for proactive speak."""
        cover = self.rng.choice(PROACTIVE_IDLE_COVERS)
        text = cover["text"]
        emotion = cover["emotion"]
        actions = self._build_actions(emotion)
        audio_path = self.ai_npc_path / cover["audio"]

        logger.info(
            "CREDO proactive idle cover: "
            f"emotion={emotion}, cache={audio_path.exists()}, text={text!r}"
        )

        if self.use_fast_audio and audio_path.exists():
            return AudioOutput(
                audio_path=str(audio_path),
                display_text=self._display(text),
                transcript=text,
                actions=actions,
            )
        return SentenceOutput(
            display_text=self._display(text),
            tts_text=text,
            actions=actions,
        )

    def _build_actions(self, emotion: str) -> Actions:
        """Map CREDO's four emotions to Live2D expression actions."""
        tags = self.expression_map.get(emotion) or self.expression_map.get("neutral") or []
        if not isinstance(tags, list):
            tags = [str(tags)]

        expressions: list[Any] = []
        shuffled = list(tags)
        self.rng.shuffle(shuffled)
        for tag in shuffled:
            tag = str(tag).strip().strip("[]").lower()
            if not tag:
                continue
            extracted = []
            if self.live2d_model is not None:
                try:
                    extracted = self.live2d_model.extract_emotion(f"[{tag}]")
                except Exception:
                    extracted = []
            expressions.extend(extracted or [tag])
            if expressions:
                break

        return Actions(expressions=expressions or None)

    async def _try_synthesize_slow_audio(self, text: str) -> Path | None:
        """Use CREDO's local Fish Speech client for SlowTrack when configured."""
        if self.slow_tts_mode != "credo_fish_speech" or self.fish_tts is None:
            return None
        try:
            return await asyncio.to_thread(self.fish_tts.synthesize_to_file, text, prefix="olv_slow")
        except Exception as exc:
            logger.warning(f"CREDO Fish Speech slow TTS fallback to Open-LLM TTS: {exc}")
            return None

    def _display(self, text: str) -> DisplayText:
        """Build display metadata for Open-LLM-VTuber."""
        return DisplayText(text=text, name=self.character_name, avatar=self.character_avatar)

    def handle_interrupt(self, heard_response: str) -> None:
        """Keep interruption compatible with Open-LLM-VTuber's agent interface."""
        logger.info(f"CREDO agent interrupted after: {heard_response}")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """CREDO uses its own JSON memory store, so chat-history replay is not required."""
        logger.debug(f"CREDO agent ignoring Open-LLM history replay: {conf_uid}/{history_uid}")
