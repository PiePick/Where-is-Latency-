"""Open-LLM-VTuber Agent adapter for the CREDO latency-cover pipeline.

This file is copied into `vendor/open-llm-vtuber` by `apply_integration.py`.
It keeps Open-LLM-VTuber responsible for the UI, Live2D frontend, ASR, and
websocket loop while delegating the research logic to `AI_NPC_System`.
"""

from __future__ import annotations

import asyncio
import os
import random
import re
import sys
import time
import uuid
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

STYLE_MOTION_PROFILE_BY_STYLE = {
    "bright": "bright",
    "high-pitched": "bright",
    "high_pitched": "bright",
    "playful": "playful",
    "energetic": "energetic",
    "excited": "energetic",
    "smug": "smug",
    "cute": "cute",
}

MOTION_PROFILE_BY_EMOTION = {
    "positive": "bright",
    "negative": "low",
    "ambiguous": "alert",
    "neutral": "steady",
}


PROACTIVE_IDLE_CATEGORIES = ("Positive", "Neutral")
FISH_STYLE_TAG_RE = re.compile(r"\s*\[[^\]]+\]\s*")
LAUGH_EVENT_RE = re.compile(r"(?i)(?:\b(?:ha+ha+|he+he+|ahaha+|hehe+|lol)\b)")
SURPRISE_EVENT_RE = re.compile(r"(?i)(?:\b(?:wow|whoa|woah|no way)\b|oh[!,.]?)")
THINKING_EVENT_RE = re.compile(r"(?i)\b(?:uh|um|hmm+|mmm+)\b")
SIGH_EVENT_RE = re.compile(r"(?i)\b(?:sigh|ugh|oof)\b")


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
        self.speech_emotion_motion_enabled = bool(self.settings.get("speech_emotion_motion_enabled", True))
        self.record_memory = bool(self.settings.get("record_memory", True))
        self.expression_map = self.settings.get("expression_map") or DEFAULT_EXPRESSION_TAGS
        self.rng = random.Random(self.settings.get("seed"))
        self._proactive_count = 0
        self._vtuber_slow_prefetch_task: asyncio.Task | None = None
        self._recent_runtime_context: list[dict[str, str]] = []

        self.ai_npc_path = self._resolve_ai_npc_path()
        self._load_credo_modules()
        self.latency_logger = self._latency_observer.LatencyLogger()
        self.cover_composer = self._cover_composer.CoverComposer(seed=self.settings.get("seed"))
        self._intent_model = None
        self._intent_model_checked = False
        self.fast_track_enabled = self._as_bool(
            self.settings.get(
                "fast_track_enabled",
                getattr(self._credo_config, "FAST_TRACK_ENABLED", True),
            )
        )

        self.memory = None
        if self.record_memory and self._credo_config.MEMORY_ENABLED:
            self.memory = self._memory_store.MemoryStore()

        self.fish_tts = None
        self._slow_fish_tts_lock = asyncio.Lock()
        if self.slow_tts_mode == "credo_fish_speech":
            self.fish_tts = self._tts_client.FishSpeechTTSClient()
        self.fast_stylebert_tts = None
        if self._credo_config.FAST_TRACK_TTS_MODE == "stylebert_vits2":
            self.fast_stylebert_tts = self._stylebert_vits2_client.StyleBertVITS2Client()
        self.fast_piper_tts = None
        if self._credo_config.FAST_TRACK_TTS_MODE == "piper_tts":
            self.fast_piper_tts = self._piper_tts_client.PiperTTSClient()

        self.proactive_audio_cache = self._fast_track_audio_cache.FastTrackAudioCache(
            self._credo_config.FAST_TRACK_AUDIO_CACHE_PATH,
            enabled=self._credo_config.FAST_TRACK_AUDIO_CACHE_ENABLED,
            seed=self.settings.get("seed"),
            expected_reference_id=self._credo_config.FAST_TRACK_AUDIO_CACHE_REFERENCE_ID,
        )
        self.persona_reaction_bundle = self._fast_track_audio_cache.PersonaReactionBundle(
            self._credo_config.FAST_TRACK_PERSONA_BUNDLE_PATH,
            enabled=getattr(self._credo_config, "FAST_TRACK_PERSONA_BUNDLE_ENABLED", False),
            seed=self.settings.get("seed"),
            expected_reference_id=self._credo_config.FAST_TRACK_AUDIO_CACHE_REFERENCE_ID,
            personality_id=getattr(self._credo_config, "FAST_TRACK_PERSONA_ID", None),
        )

        logger.info(f"CREDO latency-cover agent loaded from {self.ai_npc_path}")

    @staticmethod
    def _as_bool(value: Any) -> bool:
        """Parse bool-like config values from YAML, env, or Python settings."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off", "none"}

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
        import stylebert_vits2_client
        import piper_tts_client
        import fast_track_audio_cache
        import cover_composer
        import latency_observer
        from memory_store import MemoryStore

        self._credo_config = credo_config
        self._fast_track = fast_track
        self._slow_track = slow_track
        self._tts_client = tts_client
        self._stylebert_vits2_client = stylebert_vits2_client
        self._piper_tts_client = piper_tts_client
        self._fast_track_audio_cache = fast_track_audio_cache
        self._cover_composer = cover_composer
        self._latency_observer = latency_observer
        self._memory_store = type("_MemoryModule", (), {"MemoryStore": MemoryStore})

    async def chat(self, input_data: BaseInput) -> AsyncIterator[AudioOutput | SentenceOutput]:
        """Yield immediate cover, then continue with SlowTrack when ready."""
        turn_started = time.perf_counter()
        metadata = dict(input_data.metadata) if isinstance(input_data, BatchInput) and input_data.metadata else {}
        turn_id = str(metadata.get("turn_id") or uuid.uuid4())
        metadata["turn_id"] = turn_id
        user_text, is_proactive = self._extract_input(input_data)
        if not user_text:
            return
        if metadata.get("vtuber_mode"):
            logger.info(
                "CREDO VTuber turn entering FastTrack-first path: "
                f"event={metadata.get('vtuber_event')}, surface={user_text[:80]!r}"
            )

        if not self.fast_track_enabled:
            logger.info("CREDO FastTrack disabled; running SlowTrack-only turn.")
            async for output in self._chat_slow_only(user_text, turn_started, turn_id):
                yield output
            return

        if is_proactive:
            output = self._build_proactive_output()
            self._log_latency(
                "proactive_cover",
                turn_started,
                text=getattr(getattr(output, "display_text", None), "text", "") or "",
                engine="prebuilt_cover_cache",
                metadata={"turn_id": turn_id, "proactive": True},
            )
            yield output
            return

        fast_started = time.perf_counter()
        fast_result = await asyncio.to_thread(self._fast_track.analyze_and_react, user_text)
        self._log_latency(
            "fast_track_analysis",
            fast_started,
            text=user_text,
            engine="distilbert_spacy",
            metadata={
                "emotion": fast_result.get("emotion_label"),
                "keywords": fast_result.get("keywords") or [],
                "turn_id": turn_id,
                "vtuber_mode": bool(metadata.get("vtuber_mode")),
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )

        fast_raw_tts_text = str(
            fast_result.get("tts_text")
            or fast_result.get("plain_tts_text")
            or fast_result.get("reaction")
            or "I see."
        )
        fast_plain_text = self._clean_spoken_text(
            fast_result.get("plain_tts_text") or fast_raw_tts_text
        )
        fast_tts_text = self._prepare_fast_tts_text(fast_raw_tts_text, fast_plain_text)
        fast_display_text = self._with_response_gap(fast_plain_text)
        emotion = str(fast_result.get("emotion_label", "neutral")).lower()
        if metadata.get("vtuber_mode") and metadata.get("emotion"):
            emotion = self._normalize_emotion(str(metadata.get("emotion")))
            fast_result["emotion_label"] = emotion
        intent = self._classify_intent(user_text)
        style_tag = self._style_tag_for_emotion(emotion)
        if metadata.get("vtuber_mode") and metadata.get("style_tag"):
            style_tag = str(metadata.get("style_tag")).strip().lower() or style_tag
        persona_cover = self.persona_reaction_bundle.choose(emotion, intent, style_tag)
        if persona_cover:
            fast_plain_text = self._clean_spoken_text(persona_cover.plain_tts_text)
            fast_raw_tts_text = persona_cover.tts_text
            fast_tts_text = self._prepare_fast_tts_text(fast_raw_tts_text, fast_plain_text)
            fast_display_text = self._with_response_gap(fast_plain_text)
            fast_result["reaction_source"] = persona_cover.source
            fast_result["fast_audio_path"] = str(persona_cover.audio_path) if persona_cover.audio_path else None
            fast_result["fast_audio_cache_path"] = str(persona_cover.audio_path) if persona_cover.audio_path else None
            fast_result["fast_audio_cache_hit"] = bool(persona_cover.audio_path and persona_cover.audio_path.exists())
            fast_result["persona_bundle_id"] = persona_cover.cache_id
            fast_result["persona_style_tag"] = style_tag
            fast_result["persona_response_act"] = persona_cover.response_act
        speech_actions = self._speech_actions(emotion, style_tag=style_tag, text=fast_plain_text)

        logger.info(
            "CREDO FastTrack cover: "
            f"emotion={emotion}, intent={intent}, source={fast_result.get('reaction_source')}, "
            f"cache={fast_result.get('fast_audio_cache_hit')}"
        )

        memory_context = self._build_memory_context()
        slow_started = time.perf_counter()
        slow_task: asyncio.Task | None = None
        prefetched_slow = self._take_ready_vtuber_slow_prefetch(metadata)
        cover_plan: dict[str, Any] = {}
        if self.slow_enabled and prefetched_slow is None:
            slow_input = self._build_vtuber_prompt(user_text, metadata) if metadata.get("vtuber_mode") else user_text
            slow_strategy = fast_result.get("strategy")
            slow_mode = None
            slow_max_tokens = None
            if metadata.get("vtuber_mode"):
                event = str(metadata.get("vtuber_event") or "idle")
                slow_strategy = f"vtuber_mode:{event}; fasttrack:{slow_strategy or 'persona_bundle'}"
                slow_mode = "vtuber_monologue"
                slow_max_tokens = getattr(self._credo_config, "CREDO_VTUBER_LLM_MAX_TOKENS", 180)
            slow_task = asyncio.create_task(
                self._slow_track.generate_response(
                    slow_input,
                    fast_tts_text,
                    slow_strategy,
                    memory_context,
                    mode=slow_mode,
                    max_tokens=slow_max_tokens,
                )
            )

        for interjection in self._build_initial_interjection_outputs(emotion, turn_id):
            yield interjection

        fast_audio_started = time.perf_counter()
        fast_audio_path = await self._resolve_fast_audio(fast_result, fast_tts_text, emotion=emotion)
        self._log_latency(
            "fast_track_tts_or_cache",
            fast_audio_started,
            text=fast_tts_text,
            engine=self._credo_config.FAST_TRACK_TTS_MODE,
            metadata={
                "audio_path": str(fast_audio_path) if fast_audio_path else None,
                "emotion": emotion,
                "intent": intent,
                "style_tag": style_tag,
                "persona_style_tag": fast_result.get("persona_style_tag"),
                "response_act": fast_result.get("persona_response_act"),
                "persona_response_act": fast_result.get("persona_response_act"),
                "fast_audio_cache_hit": bool(fast_audio_path and Path(str(fast_audio_path)).exists()),
                "turn_id": turn_id,
                "vtuber_mode": bool(metadata.get("vtuber_mode")),
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )

        if self.slow_enabled:
            cover_plan = await asyncio.to_thread(
                self.cover_composer.compose,
                user_text=user_text,
                fast_result=fast_result,
                intent=intent,
                expected_slow_text="",
            )
            self.latency_logger.log(
                self._latency_observer.LatencyEvent(
                    stage="latency_cover_plan",
                    elapsed_ms=0.0,
                    text=user_text,
                    engine="composer_faiss_knn",
                    metadata={**cover_plan, "turn_id": turn_id, "emotion": emotion, "intent": intent},
                )
            )

        if self.use_fast_audio and fast_audio_path and Path(str(fast_audio_path)).exists():
            yield AudioOutput(
                audio_path=str(fast_audio_path),
                display_text=self._display(fast_display_text),
                transcript=fast_display_text,
                actions=speech_actions,
            )
        elif self._credo_config.FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK:
            yield SentenceOutput(
                display_text=self._display(fast_display_text),
                tts_text=fast_tts_text,
                actions=speech_actions,
            )
        else:
            logger.warning(
                "Skipping FastTrack Open-LLM TTS fallback because dedicated FastTrack audio is unavailable."
            )

        if not self.slow_enabled:
            return

        if prefetched_slow is not None:
            slow_text = str(prefetched_slow.get("text") or "").strip() or "I hear you."
            slow_audio_raw = prefetched_slow.get("audio_path")
            slow_audio = Path(str(slow_audio_raw)) if slow_audio_raw else None
            if slow_audio and not slow_audio.exists():
                slow_audio = None
            self._log_latency(
                "vtuber_slow_prefetch_hit",
                turn_started,
                text=slow_text,
                engine="prefetched_fish_speech",
                metadata={
                    "audio_path": str(slow_audio) if slow_audio else None,
                    "emotion": emotion,
                    "intent": intent,
                    "turn_id": turn_id,
                    "vtuber_mode": bool(metadata.get("vtuber_mode")),
                    "vtuber_event": metadata.get("vtuber_event"),
                    "prefetch_age_ms": int((time.perf_counter() - float(prefetched_slow.get("created_at", turn_started))) * 1000),
                },
            )
            self._start_vtuber_slow_prefetch(
                user_text=user_text,
                metadata=metadata,
                fast_reaction=fast_tts_text,
                strategy=f"prefetch_after:{fast_result.get('strategy') or 'persona_bundle'}",
                memory_context=memory_context,
                emotion=emotion,
                turn_id=turn_id,
            )
            if slow_audio:
                yield AudioOutput(
                    audio_path=str(slow_audio),
                    display_text=self._display(slow_text),
                    transcript=slow_text,
                    actions=speech_actions,
                )
            elif getattr(self._credo_config, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", False):
                yield SentenceOutput(
                    display_text=self._display(slow_text),
                    tts_text=slow_text,
                    actions=speech_actions,
                )
            else:
                yield SentenceOutput(
                    display_text=self._display(slow_text),
                    tts_text="",
                    actions=speech_actions,
                )

            self._remember_runtime_context(
                user_text=user_text,
                assistant_text=slow_text,
                emotion=emotion,
                event=str(metadata.get("vtuber_event") or ""),
            )
            if self.memory and not metadata.get("skip_memory"):
                self.memory.record_turn(
                    user_text=user_text,
                    assistant_text=slow_text,
                    fast_reaction=fast_plain_text,
                    emotion=emotion,
                    keywords=[str(metadata.get("topic") or ""), str(metadata.get("vtuber_event") or "")],
                )
            self._log_latency(
                "turn_total",
                turn_started,
                text=f"{fast_display_text} {slow_text}",
                engine="open_llm_vtuber_credo",
                metadata={
                    "emotion": emotion,
                    "intent": intent,
                    "turn_id": turn_id,
                    "vtuber_mode": bool(metadata.get("vtuber_mode")),
                    "vtuber_event": metadata.get("vtuber_event"),
                    "used_slow_prefetch": True,
                },
            )
            return

        if slow_task is None:
            return

        async for cover_output in self._yield_waiting_cover_audio(slow_task, emotion, turn_id, reason="slow_llm"):
            yield cover_output

        slow_text = await slow_task
        self._log_latency(
            "slow_track_llm",
            slow_started,
            text=user_text,
            engine=self._credo_config.LOCAL_LLM_MODEL,
            metadata={
                "emotion": emotion,
                "intent": intent,
                "turn_id": turn_id,
                "vtuber_mode": bool(metadata.get("vtuber_mode")),
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )
        slow_text = self._clean_spoken_text(slow_text) or "I hear you."

        slow_tts_started = time.perf_counter()
        slow_audio_task = asyncio.create_task(self._try_synthesize_slow_audio(slow_text))
        async for cover_output in self._yield_waiting_cover_audio(slow_audio_task, emotion, turn_id, reason="slow_tts"):
            yield cover_output
        slow_audio = await slow_audio_task
        self._log_latency(
            "slow_track_tts",
            slow_tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={
                "audio_path": str(slow_audio) if slow_audio else None,
                "emotion": emotion,
                "intent": intent,
                "turn_id": turn_id,
                "vtuber_mode": bool(metadata.get("vtuber_mode")),
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )

        if slow_audio:
            self._start_vtuber_slow_prefetch(
                user_text=user_text,
                metadata=metadata,
                fast_reaction=fast_tts_text,
                strategy=f"prefetch_after:{fast_result.get('strategy') or 'persona_bundle'}",
                memory_context=memory_context,
                emotion=emotion,
                turn_id=turn_id,
            )
            yield AudioOutput(
                audio_path=str(slow_audio),
                display_text=self._display(slow_text),
                transcript=slow_text,
                actions=speech_actions,
            )
        elif getattr(self._credo_config, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", False):
            logger.warning("Fish Speech slow audio unavailable; using configured Open-LLM fallback TTS.")
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text=slow_text,
                actions=speech_actions,
            )
        else:
            logger.warning("Fish Speech slow audio unavailable; suppressing Open-LLM fallback TTS to avoid wrong voice.")
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text="",
                actions=speech_actions,
            )

        self._remember_runtime_context(
            user_text=user_text,
            assistant_text=slow_text,
            emotion=emotion,
            event=str(metadata.get("vtuber_event") or ""),
        )
        if self.memory and not metadata.get("skip_memory"):
            self.memory.record_turn(
                user_text=user_text,
                assistant_text=slow_text,
                fast_reaction=fast_plain_text,
                emotion=emotion,
                keywords=(
                    [str(metadata.get("topic") or ""), str(metadata.get("vtuber_event") or "")]
                    if metadata.get("vtuber_mode")
                    else fast_result.get("keywords") or []
                ),
            )

        self._log_latency(
            "turn_total",
            turn_started,
            text=f"{fast_display_text} {slow_text}",
            engine="open_llm_vtuber_credo",
            metadata={
                "emotion": emotion,
                "intent": intent,
                "turn_id": turn_id,
                "vtuber_mode": bool(metadata.get("vtuber_mode")),
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )

    def _vtuber_slow_prefetch_enabled(self, metadata: dict[str, Any]) -> bool:
        """Return whether this VTuber turn can use the next-SlowTrack prefetch slot."""
        if not metadata.get("vtuber_mode"):
            return False
        if not getattr(self._credo_config, "CREDO_VTUBER_SLOW_PREFETCH_ENABLED", True):
            return False
        event = str(metadata.get("vtuber_event") or "idle")
        # Live chat and donations must be generated from the newest batch; using an old
        # prepared monologue there would feel like ignoring chat.
        return event not in {"live_chat_batch", "donation"}

    def _take_ready_vtuber_slow_prefetch(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Consume a prepared SlowTrack audio bundle if it is fresh enough."""
        if not self._vtuber_slow_prefetch_enabled(metadata):
            return None
        task = self._vtuber_slow_prefetch_task
        if task is None or not task.done():
            return None
        self._vtuber_slow_prefetch_task = None
        try:
            result = task.result()
        except Exception as exc:
            logger.warning(f"CREDO VTuber SlowTrack prefetch failed before use: {exc}")
            return None
        created_at = float(result.get("created_at") or 0.0)
        max_age = float(getattr(self._credo_config, "CREDO_VTUBER_SLOW_PREFETCH_MAX_AGE_SECONDS", 120.0))
        if created_at and time.perf_counter() - created_at > max_age:
            logger.info("CREDO VTuber SlowTrack prefetch expired; generating a fresh SlowTrack turn.")
            return None
        return result

    def _start_vtuber_slow_prefetch(
        self,
        *,
        user_text: str,
        metadata: dict[str, Any],
        fast_reaction: str | None,
        strategy: str | None,
        memory_context: str | None,
        emotion: str,
        turn_id: str,
    ) -> None:
        """Prepare the next idle SlowTrack response while the current audio is playing."""
        if not self._vtuber_slow_prefetch_enabled(metadata):
            return
        task = self._vtuber_slow_prefetch_task
        if task is not None and not task.done():
            return
        next_metadata = dict(metadata)
        next_metadata["vtuber_event"] = "idle_prefetch"
        next_metadata["skip_memory"] = True
        next_metadata["skip_history"] = True
        topic = str(next_metadata.get("topic") or "").strip()
        last_chat = str(next_metadata.get("last_chat") or user_text or "").strip()
        next_metadata["vtuber_instruction"] = (
            "Prepare the next short VTuber stream continuation in case chat is quiet after the current speech. "
            "Keep one coherent thread, do not answer a specific new message unless recent chat is provided, "
            "and end with a light hook for chat. Aim for 12 to 22 spoken words."
        )
        if topic:
            next_metadata["topic"] = topic
        if last_chat:
            next_metadata["last_chat"] = last_chat
        self._vtuber_slow_prefetch_task = asyncio.create_task(
            self._prefetch_vtuber_slow_audio(
                seed_text="Keep the stream moving for one more beat.",
                metadata=next_metadata,
                fast_reaction=fast_reaction,
                strategy=strategy,
                memory_context=memory_context,
                emotion=emotion,
                parent_turn_id=turn_id,
            )
        )
        self._vtuber_slow_prefetch_task.add_done_callback(self._observe_vtuber_prefetch_result)

    def _observe_vtuber_prefetch_result(self, task: asyncio.Task) -> None:
        """Log background prefetch failures promptly instead of leaving silent task errors."""
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as exc:
            logger.warning(f"CREDO VTuber SlowTrack prefetch task failed: {exc}")

    async def _prefetch_vtuber_slow_audio(
        self,
        *,
        seed_text: str,
        metadata: dict[str, Any],
        fast_reaction: str | None,
        strategy: str | None,
        memory_context: str | None,
        emotion: str,
        parent_turn_id: str,
    ) -> dict[str, Any]:
        """Generate and synthesize one future VTuber SlowTrack segment."""
        started = time.perf_counter()
        prompt = self._build_vtuber_prompt(seed_text, metadata)
        slow_text = await self._slow_track.generate_response(
            prompt,
            fast_reaction=fast_reaction,
            strategy=strategy,
            memory_context=memory_context,
            mode="vtuber_monologue",
            max_tokens=getattr(self._credo_config, "CREDO_VTUBER_LLM_MAX_TOKENS", 180),
        )
        slow_text = self._clean_spoken_text(slow_text) or "So, chat, where should we take this next?"
        self._log_latency(
            "vtuber_slow_prefetch_llm",
            started,
            text=prompt,
            engine=self._credo_config.LOCAL_LLM_MODEL,
            metadata={
                "emotion": emotion,
                "parent_turn_id": parent_turn_id,
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )

        tts_started = time.perf_counter()
        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        self._log_latency(
            "vtuber_slow_prefetch_tts",
            tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={
                "audio_path": str(slow_audio) if slow_audio else None,
                "emotion": emotion,
                "parent_turn_id": parent_turn_id,
                "vtuber_event": metadata.get("vtuber_event"),
            },
        )
        return {
            "text": slow_text,
            "audio_path": str(slow_audio) if slow_audio else "",
            "created_at": time.perf_counter(),
            "emotion": emotion,
            "metadata": metadata,
        }

    async def _chat_vtuber_mode(
        self,
        user_text: str,
        metadata: dict[str, Any],
        turn_started: float,
    ) -> AsyncIterator[AudioOutput | SentenceOutput]:
        """Generate a cohesive solo/live-stream segment for CREDO VTuber mode."""
        event = str(metadata.get("vtuber_event") or "idle")
        emotion = str(metadata.get("emotion") or "positive").lower()
        speech_actions = self._speech_actions(emotion, style_tag=metadata.get("style_tag"), text=user_text)
        memory_context = self._build_memory_context()

        prompt = self._build_vtuber_prompt(user_text, metadata)
        slow_started = time.perf_counter()
        slow_text = await self._slow_track.generate_response(
            prompt,
            fast_reaction=None,
            strategy=f"vtuber_mode:{event}",
            memory_context=memory_context,
            mode="vtuber_monologue",
            max_tokens=getattr(self._credo_config, "CREDO_VTUBER_LLM_MAX_TOKENS", 180),
        )
        turn_id = str(metadata.get("turn_id") or uuid.uuid4())
        self._log_latency(
            "vtuber_mode_llm",
            slow_started,
            text=prompt,
            engine=self._credo_config.LOCAL_LLM_MODEL,
            metadata={"event": event, "emotion": emotion, "turn_id": turn_id},
        )

        slow_text = self._clean_spoken_text(slow_text) or "Chat got quiet for a second, so I am keeping the room warm. What should we talk about next?"
        speech_actions = self._speech_actions(emotion, style_tag=metadata.get("style_tag"), text=slow_text)

        slow_tts_started = time.perf_counter()
        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        self._log_latency(
            "vtuber_mode_tts",
            slow_tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={
                "event": event,
                "emotion": emotion,
                "style_tag": metadata.get("style_tag", ""),
                "audio_path": str(slow_audio) if slow_audio else None,
                "turn_id": turn_id,
            },
        )

        if slow_audio:
            yield AudioOutput(
                audio_path=str(slow_audio),
                display_text=self._display(slow_text),
                transcript=slow_text,
                actions=speech_actions,
            )
        elif getattr(self._credo_config, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", False):
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text=slow_text,
                actions=speech_actions,
            )
        else:
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text="",
                actions=speech_actions,
            )

        self._remember_runtime_context(
            user_text=user_text,
            assistant_text=slow_text,
            emotion=emotion,
            event=event,
        )
        if self.memory and not metadata.get("skip_memory"):
            self.memory.record_turn(
                user_text=f"VTuber mode {event}: {user_text}",
                assistant_text=slow_text,
                fast_reaction="",
                emotion=emotion,
                keywords=[str(metadata.get("topic") or ""), event],
            )

        self._log_latency(
            "vtuber_mode_total",
            turn_started,
            text=slow_text,
            engine="open_llm_vtuber_credo",
            metadata={"event": event, "emotion": emotion, "turn_id": turn_id},
        )

    def _build_memory_context(self) -> str | None:
        """Combine persistent memory with a short in-process stream context window."""
        blocks: list[str] = []
        if self.memory:
            persistent = self.memory.build_prompt_context().strip()
            if persistent:
                blocks.append(persistent)
        if self._recent_runtime_context:
            lines = [
                "Recent stream context. Use for continuity; do not mention that this is memory."
            ]
            for turn in self._recent_runtime_context[-6:]:
                event = turn.get("event") or "turn"
                emotion = turn.get("emotion") or "neutral"
                user = turn.get("user") or ""
                assistant = turn.get("assistant") or ""
                lines.append(f"- {event}/{emotion} viewer context: {user}")
                lines.append(f"  Lera Mei said: {assistant}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks) if blocks else None

    def _remember_runtime_context(
        self,
        *,
        user_text: str,
        assistant_text: str,
        emotion: str,
        event: str,
    ) -> None:
        """Keep a small volatile context window for VTuber continuity."""
        user_text = self._clean_spoken_text(str(user_text or ""))[:360]
        assistant_text = self._clean_spoken_text(str(assistant_text or ""))[:360]
        if not user_text and not assistant_text:
            return
        self._recent_runtime_context.append(
            {
                "user": user_text,
                "assistant": assistant_text,
                "emotion": str(emotion or "neutral"),
                "event": str(event or "turn"),
            }
        )
        del self._recent_runtime_context[: max(0, len(self._recent_runtime_context) - 8)]

    def _build_vtuber_prompt(self, text: str, metadata: dict[str, Any]) -> str:
        """Make route-provided stream state explicit without exposing internals."""
        topic = str(metadata.get("topic") or "").strip()
        silence = metadata.get("silence_seconds")
        last_chat = str(metadata.get("last_chat") or "").strip()
        event = str(metadata.get("vtuber_event") or "idle")
        instruction = str(metadata.get("vtuber_instruction") or "").strip()
        parts = [instruction or str(text or "").strip()]
        if topic:
            parts.append(f"Current stream topic anchor: {topic}.")
        if last_chat and last_chat != text:
            parts.append(f"Most recent viewer/chat context: {last_chat}")
        if silence is not None:
            parts.append(f"The chat has been quiet for about {int(float(silence))} seconds.")
        if event == "idle":
            parts.append(
                "Continue the stream by yourself for a short while. Keep one clear thread, add one small detail, then invite chat back in."
            )
        elif event == "manual_monologue":
            parts.append("Make this feel like an intentional streamer monologue, not a Q&A answer.")
        elif event == "donation":
            parts.append("React to the support warmly, then fold it back into the stream topic.")
        return "\n".join(part for part in parts if part)

    async def _chat_slow_only(
        self,
        user_text: str,
        turn_started: float,
        turn_id: str,
    ) -> AsyncIterator[AudioOutput | SentenceOutput]:
        """Run the ablation path with no FastTrack analysis, cover text, audio, or motion."""
        speech_actions = self._speech_actions("neutral")
        memory_context = self._build_memory_context()

        slow_started = time.perf_counter()
        slow_text = await self._slow_track.generate_response(
            user_text,
            fast_reaction=None,
            strategy="fast_track_disabled",
            memory_context=memory_context,
        )
        self._log_latency(
            "slow_track_llm",
            slow_started,
            text=user_text,
            engine=self._credo_config.LOCAL_LLM_MODEL,
            metadata={"fast_track_enabled": False, "turn_id": turn_id},
        )
        slow_text = self._clean_spoken_text(slow_text) or "I hear you."

        slow_tts_started = time.perf_counter()
        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        self._log_latency(
            "slow_track_tts",
            slow_tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={
                "audio_path": str(slow_audio) if slow_audio else None,
                "fast_track_enabled": False,
                "turn_id": turn_id,
            },
        )

        if slow_audio:
            yield AudioOutput(
                audio_path=str(slow_audio),
                display_text=self._display(slow_text),
                transcript=slow_text,
                actions=speech_actions,
            )
        elif getattr(self._credo_config, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", False):
            logger.warning("Fish Speech slow audio unavailable; using configured Open-LLM fallback TTS.")
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text=slow_text,
                actions=speech_actions,
            )
        else:
            logger.warning("Fish Speech slow audio unavailable; suppressing Open-LLM fallback TTS to avoid wrong voice.")
            yield SentenceOutput(
                display_text=self._display(slow_text),
                tts_text="",
                actions=speech_actions,
            )

        self._remember_runtime_context(
            user_text=user_text,
            assistant_text=slow_text,
            emotion="fast_track_disabled",
            event="slow_only",
        )
        if self.memory:
            self.memory.record_turn(
                user_text=user_text,
                assistant_text=slow_text,
                fast_reaction="",
                emotion="fast_track_disabled",
                keywords=[],
            )

        self._log_latency(
            "turn_total",
            turn_started,
            text=slow_text,
            engine="open_llm_vtuber_credo",
            metadata={"fast_track_enabled": False, "turn_id": turn_id},
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
        if getattr(self._credo_config, "CREDO_ENGLISH_ONLY_OUTPUT", True):
            prompt = f"{prompt} {self._credo_config.CREDO_LANGUAGE_POLICY}"
        return f"{prompt} Idle turn number: {self._proactive_count}."

    def _build_proactive_output(self) -> AudioOutput | SentenceOutput:
        """Return an immediate idle utterance from the current configured cache."""
        category = self.rng.choice(PROACTIVE_IDLE_CATEGORIES)
        source = self.rng.choice(("everyday", "stream"))
        cover = self.proactive_audio_cache.choose(category, preferred_source=source)

        if cover:
            text = self._clean_spoken_text(cover.plain_tts_text)
            tts_text = self._prepare_fast_tts_text(cover.tts_text, text)
            emotion = cover.category.lower()
            audio_path = cover.audio_path
        else:
            text = self.rng.choice(("Hi hi.", "I am here.", "Tell me something fun."))
            tts_text = text
            emotion = category.lower()
            audio_path = None

        actions = self._speech_actions(emotion)

        logger.info(
            "CREDO proactive idle cover: "
            f"emotion={emotion}, cache={bool(audio_path and audio_path.exists())}, "
            f"path={audio_path}, text={text!r}"
        )

        if (
            self.use_fast_audio
            and not audio_path
            and self._credo_config.FAST_TRACK_TTS_MODE == "stylebert_vits2"
        ):
            audio_path = self._synthesize_fast_audio_sync(tts_text, emotion=emotion)

        if self.use_fast_audio and audio_path and audio_path.exists():
            return AudioOutput(
                audio_path=str(audio_path),
                display_text=self._display(text),
                transcript=text,
                actions=actions,
            )
        return SentenceOutput(
            display_text=self._display(text),
            tts_text=tts_text,
            actions=actions,
        )

    def _clean_spoken_text(self, text: str) -> str:
        """Remove Fish Speech control tags before display or fallback TTS."""
        text = FISH_STYLE_TAG_RE.sub(" ", str(text or ""))
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([,.!?])", r"\1", text)
        return text

    def _with_response_gap(self, text: str) -> str:
        """Keep Open-LLM-VTuber's appended chat bubbles from running together."""
        text = self._clean_spoken_text(text)
        if not text:
            return text
        return text if text.endswith((" ", "\n")) else f"{text} "

    def _prepare_fast_tts_text(self, raw_text: str, plain_text: str) -> str:
        """Keep cue tags only for engines that support inline style cues."""
        raw_text = str(raw_text or "").strip()
        plain_text = self._clean_spoken_text(plain_text)
        if not raw_text:
            return plain_text
        if (
            self._credo_config.FAST_TRACK_TTS_MODE == "fish_speech"
            and getattr(self._credo_config, "FAST_TRACK_INLINE_CUES_ENABLED", False)
        ):
            return raw_text
        # StyleBERT-VITS2 uses API style controls. Fish Speech bracket tags can be
        # read aloud by non-Fish engines, so normal FastTrack StyleBERT speech stays clean.
        return plain_text

    def _speech_actions(
        self,
        emotion: str = "neutral",
        *,
        style_tag: str | None = None,
        text: str | None = None,
    ) -> Actions:
        """Use Open-LLM-VTuber expressions plus speech-safe CREDO motion cues."""
        base_actions = self._build_actions(emotion)
        expressions = list(base_actions.expressions or [])
        if self.speech_emotion_motion_enabled:
            normalized = self._normalize_emotion(emotion)
            expressions.insert(0, f"credo_speech_motion:{normalized}")
            style_motion = self._normalize_style_tag(style_tag)
            if style_motion:
                expressions.insert(0, f"credo_style_motion:{style_motion}")
            expressions.insert(0, f"credo_motion_profile:{self._motion_profile(normalized, style_motion)}")
            expressions.extend(self._speech_event_tags(text))
        return Actions(expressions=expressions or None)

    def _normalize_emotion(self, emotion: str) -> str:
        """Normalize arbitrary emotion labels into CREDO's four motion groups."""
        emotion = str(emotion or "neutral").lower()
        return emotion if emotion in DEFAULT_EXPRESSION_TAGS else "neutral"

    def _normalize_style_tag(self, style_tag: str | None) -> str | None:
        """Map persona bundle style tags to frontend motion tags."""
        style = str(style_tag or "").strip().lower()
        mapping = {
            "high-pitched": "bright",
            "high_pitched": "bright",
            "bright": "bright",
            "playful": "playful",
            "energetic": "energetic",
            "excited": "energetic",
            "smug": "smug",
            "cute": "cute",
        }
        return mapping.get(style)

    def _motion_profile(self, emotion: str, style_motion: str | None = None) -> str:
        """Choose the frontend motion-intensity profile for this utterance."""
        if style_motion and style_motion in STYLE_MOTION_PROFILE_BY_STYLE:
            return STYLE_MOTION_PROFILE_BY_STYLE[style_motion]
        return MOTION_PROFILE_BY_EMOTION.get(self._normalize_emotion(emotion), "steady")

    def _speech_event_tags(self, text: str | None) -> list[str]:
        """Detect short spoken events that should trigger brief timed motions."""
        spoken = str(text or "")
        tags: list[str] = []
        if LAUGH_EVENT_RE.search(spoken):
            tags.append("credo_event_motion:laugh")
        if SURPRISE_EVENT_RE.search(spoken):
            tags.append("credo_event_motion:surprise")
        if THINKING_EVENT_RE.search(spoken):
            tags.append("credo_event_motion:thinking")
        if SIGH_EVENT_RE.search(spoken):
            tags.append("credo_event_motion:sigh")
        return tags

    def _build_actions(self, emotion: str) -> Actions:
        """Map CREDO's four emotions to Open-LLM-VTuber expression actions."""
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

    def _style_tag_for_emotion(self, emotion: str) -> str:
        """Pick a persona-bundle style tag; keep all selected styles reachable."""
        style_tags = getattr(self._credo_config, "FAST_TRACK_PERSONA_STYLE_TAGS", []) or []
        style_tags = [str(tag).strip().lower() for tag in style_tags if str(tag).strip()]
        if style_tags:
            return self.rng.choice(style_tags)
        key = str(emotion or "neutral").lower()
        mapping = {
            "positive": getattr(self._credo_config, "FAST_TRACK_STYLE_POSITIVE", "playful"),
            "negative": getattr(self._credo_config, "FAST_TRACK_STYLE_NEGATIVE", "cute"),
            "ambiguous": getattr(self._credo_config, "FAST_TRACK_STYLE_AMBIGUOUS", "energetic"),
            "neutral": getattr(self._credo_config, "FAST_TRACK_STYLE_NEUTRAL", "smug"),
        }
        return str(mapping.get(key, mapping["neutral"])).lower()

    def _nonverbal_cover_actions(self, emotion: str) -> Actions:
        """Trigger CREDO emotion motion only for prebuilt nonverbal cover audio."""
        emotion = self._normalize_emotion(emotion)
        return Actions(expressions=[f"credo_fast_motion:{emotion}"])

    def _expressive_cover_actions(self, emotion: str, event: str) -> Actions:
        """Trigger a short expressive Live2D motion together with nonverbal audio."""
        emotion = self._normalize_emotion(emotion)
        profile = self._motion_profile(emotion)
        expressions = [
            f"credo_motion_profile:{profile}",
            f"credo_fast_motion:{emotion}",
            f"credo_event_motion:{event}",
        ]
        return Actions(expressions=expressions)

    def _event_for_emotion(self, emotion: str) -> str:
        """Map emotion classes to the nearest available event-motion group."""
        emotion = self._normalize_emotion(emotion)
        return {
            "positive": "laugh",
            "negative": "sigh",
            "ambiguous": "surprise",
            "neutral": "thinking",
        }.get(emotion, "thinking")

    def _build_initial_interjection_outputs(self, emotion: str, turn_id: str) -> list[AudioOutput]:
        """Return initial FastTrack beats: pure interjection audio plus Live2D motion."""
        if not getattr(self._credo_config, "CREDO_ENABLE_INITIAL_INTERJECTION_AUDIO", True):
            return []
        count = max(1, int(getattr(self._credo_config, "CREDO_INITIAL_INTERJECTION_MAX_BLOCKS", 2)))
        items = self.cover_composer.choose_extreme_audio_items(self._normalize_emotion(emotion), count=count)
        event = self._event_for_emotion(emotion)
        outputs: list[AudioOutput] = []
        for index, item in enumerate(items, start=1):
            audio_path = Path(str(item.get("audio_path") or ""))
            if not audio_path.exists():
                continue
            carrier = self._clean_spoken_text(str(item.get("carrier") or ""))
            self.latency_logger.log(
                self._latency_observer.LatencyEvent(
                    stage="fast_track_interjection",
                    elapsed_ms=0.0,
                    text=carrier,
                    engine="interjection_audio_bundle",
                    metadata={
                        "turn_id": turn_id,
                        "emotion": self._normalize_emotion(emotion),
                        "event": event,
                        "interjection_index": index,
                        "audio_path": str(audio_path),
                    },
                )
            )
            outputs.append(
                AudioOutput(
                    audio_path=str(audio_path),
                    display_text=self._display(""),
                    transcript="",
                    actions=self._expressive_cover_actions(emotion, event),
                )
            )
        return outputs

    async def _yield_waiting_cover_audio(
        self,
        pending_task: asyncio.Task,
        emotion: str,
        turn_id: str,
        *,
        reason: str,
    ) -> AsyncIterator[AudioOutput]:
        """Play short hm/mm waiting audio while SlowTrack is not ready."""
        if not getattr(self._credo_config, "CREDO_ENABLE_WAITING_COVER_AUDIO", True):
            return

        max_blocks = max(0, int(getattr(self._credo_config, "CREDO_WAITING_COVER_MAX_BLOCKS", 1)))
        gap = max(0.0, float(getattr(self._credo_config, "CREDO_WAITING_COVER_GAP_SECONDS", 0.45)))
        for _idx in range(max_blocks):
            if pending_task.done():
                break
            if gap:
                await asyncio.sleep(gap)
            if pending_task.done():
                break
            item = self.cover_composer.choose_waiting_audio_item()
            if not item:
                break
            audio_path = Path(str(item.get("audio_path") or ""))
            if not audio_path.exists():
                break
            text = self._clean_spoken_text(str(item.get("carrier") or item.get("text") or "hm."))
            self.latency_logger.log(
                self._latency_observer.LatencyEvent(
                    stage="fast_track_waiting_audio",
                    elapsed_ms=0.0,
                    text=text,
                    engine="interjection_audio_bundle",
                    metadata={
                        "turn_id": turn_id,
                        "emotion": self._normalize_emotion(emotion),
                        "event": "thinking",
                        "reason": reason,
                        "audio_path": str(audio_path),
                    },
                )
            )
            yield AudioOutput(
                audio_path=str(audio_path),
                display_text=self._display(""),
                transcript="",
                actions=self._expressive_cover_actions("neutral", "thinking"),
            )

    async def _yield_extra_cover_audio(
        self,
        cover_plan: dict[str, Any],
        slow_task: asyncio.Task,
        emotion: str,
    ) -> AsyncIterator[AudioOutput]:
        """Send prebuilt expressive blocks while SlowTrack is still pending."""
        if not self._credo_config.CREDO_ENABLE_EXTRA_COVER_AUDIO:
            return

        max_blocks = max(0, int(self._credo_config.CREDO_MAX_COVER_BLOCKS))
        blocks = list(cover_plan.get("blocks") or [])[1 : 1 + max_blocks]
        for block in blocks:
            if slow_task.done():
                break
            await asyncio.sleep(0.05)
            if slow_task.done():
                break

            audio_path = block.get("audio_path")
            if not audio_path or not Path(str(audio_path)).exists():
                continue

            text = self._clean_spoken_text(str(block.get("text") or ""))
            yield AudioOutput(
                audio_path=str(audio_path),
                display_text=self._display(text),
                transcript=text,
                actions=self._nonverbal_cover_actions(emotion),
            )

    def _classify_intent(self, text: str) -> str:
        """Use the local SetFit model when loadable, with deterministic fallback."""
        normalized = " ".join(text.lower().split())
        if self._intent_model is None and not self._intent_model_checked:
            self._intent_model_checked = True
            model_dir = self.ai_npc_path / "models" / "setfit_swda_intent_minilm_optimized"
            if model_dir.exists():
                try:
                    from setfit import SetFitModel

                    self._intent_model = SetFitModel.from_pretrained(str(model_dir), local_files_only=True)
                except Exception as exc:
                    logger.warning(f"CREDO intent model unavailable; using rule fallback: {exc}")

        if self._intent_model is not None:
            try:
                prediction = self._intent_model.predict([text])
                return str(prediction[0]).upper()
            except Exception as exc:
                logger.warning(f"CREDO intent inference failed; using rule fallback: {exc}")

        first_word = normalized.split(" ", 1)[0] if normalized else ""
        if normalized.endswith("?") or first_word in {"who", "what", "when", "where", "why", "how", "can", "could", "do", "does", "did", "is", "are"}:
            return "QUESTION"
        if normalized.startswith(("please ", "show ", "tell ", "look ", "read ", "play ", "stop ", "try ")):
            return "DIRECTIVE"
        if normalized in {"yes", "yeah", "yep", "ok", "okay", "sure", "right", "no", "nope"}:
            return "ACKNOWLEDGE"
        if normalized.startswith(("no ", "nah ", "never ", "don't ", "do not ")) or " disagree" in normalized:
            return "REJECT"
        if any(token in normalized for token in ("lol", "haha", "wow", "omg", "awesome", "sad", "angry", "love")):
            return "EXPRESSIVE"
        return "INFORM"

    def _log_latency(
        self,
        stage: str,
        started: float,
        *,
        text: str = "",
        engine: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append one latency event for experiment analysis."""
        self.latency_logger.log(
            self._latency_observer.LatencyEvent(
                stage=stage,
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                text=text,
                engine=engine,
                metadata=metadata or {},
            )
        )

    async def _try_synthesize_slow_audio(self, text: str) -> Path | None:
        """Use CREDO's local Fish Speech client for SlowTrack when configured.

        Fish Speech is GPU-heavy and the local server behaves poorly when multiple
        long requests are interrupted concurrently. Keep SlowTrack Fish requests
        single-flight and let an interrupted request drain before allowing the next one.
        """
        if self.slow_tts_mode != "credo_fish_speech" or self.fish_tts is None:
            return None
        queued_at = time.perf_counter()
        async with self._slow_fish_tts_lock:
            queue_wait_ms = (time.perf_counter() - queued_at) * 1000.0
            if queue_wait_ms > 1000.0:
                logger.info(f"CREDO Fish Speech waited {queue_wait_ms:.0f} ms for the previous request to finish.")
            task = asyncio.create_task(
                asyncio.to_thread(self.fish_tts.synthesize_to_file, text, prefix="olv_slow")
            )
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                logger.warning("CREDO Fish Speech request was interrupted; waiting for the server request to drain before releasing the TTS lock.")
                try:
                    await task
                except Exception as exc:
                    logger.warning(f"CREDO Fish Speech interrupted request drained with error: {exc}")
                raise
            except Exception as exc:
                timeout = getattr(getattr(self, "fish_tts", None), "cfg", None)
                timeout_value = getattr(timeout, "timeout", "unknown")
                logger.warning(f"CREDO Fish Speech slow TTS unavailable after timeout={timeout_value}s: {exc}")
                return None

    async def _resolve_fast_audio(
        self,
        fast_result: dict[str, Any],
        text: str,
        *,
        emotion: str = "neutral",
    ) -> Path | None:
        """Return only prebuilt FastTrack audio unless legacy fallback is explicitly enabled."""
        cached_path = fast_result.get("fast_audio_path")
        if cached_path and Path(str(cached_path)).exists():
            return Path(str(cached_path))

        if getattr(self._credo_config, "FAST_TRACK_PREBUILT_ONLY", True):
            logger.warning(
                "CREDO FastTrack prebuilt audio missing; realtime FastTrack TTS is disabled by FAST_TRACK_PREBUILT_ONLY."
            )
            return None

        if self._credo_config.FAST_TRACK_TTS_MODE == "fish_speech":
            audio = await self._try_synthesize_fast_fish_audio(text)
            if audio:
                return audio

        if self._credo_config.FAST_TRACK_TTS_MODE == "stylebert_vits2":
            audio = await asyncio.to_thread(self._synthesize_fast_audio_sync, text, emotion=emotion)
            if audio:
                return audio

        if self._credo_config.FAST_TRACK_TTS_MODE == "piper_tts":
            audio = await asyncio.to_thread(self._synthesize_fast_piper_audio_sync, text, emotion=emotion)
            if audio:
                return audio

        return None

    async def _try_synthesize_fast_fish_audio(self, text: str) -> Path | None:
        """Use Fish Speech for FastTrack when voice consistency is more important than speed."""
        if self.fish_tts is None:
            return None
        try:
            return await asyncio.to_thread(self.fish_tts.synthesize_to_file, text, prefix="olv_fast")
        except Exception as exc:
            logger.warning(f"CREDO Fish Speech fast TTS fallback to Open-LLM TTS: {exc}")
            return None

    def _stylebert_style_for_emotion(self, emotion: str) -> str:
        """Return the configured StyleBERT style name for the FastTrack emotion."""
        key = str(emotion or "neutral").lower()
        style_map = {
            "positive": getattr(self._credo_config, "STYLEBERT_VITS2_STYLE_POSITIVE", None),
            "negative": getattr(self._credo_config, "STYLEBERT_VITS2_STYLE_NEGATIVE", None),
            "ambiguous": getattr(self._credo_config, "STYLEBERT_VITS2_STYLE_AMBIGUOUS", None),
            "neutral": getattr(self._credo_config, "STYLEBERT_VITS2_STYLE_NEUTRAL", None),
        }
        return str(style_map.get(key) or getattr(self._credo_config, "STYLEBERT_VITS2_STYLE", "Neutral"))

    def _synthesize_fast_audio_sync(self, text: str, *, emotion: str = "neutral") -> Path | None:
        """Use Style-Bert-VITS2 for short FastTrack audio when available."""
        if self.fast_stylebert_tts is None:
            return None
        try:
            return self.fast_stylebert_tts.synthesize_to_file(
                text,
                prefix="olv_fast",
                style=self._stylebert_style_for_emotion(emotion),
            )
        except Exception as exc:
            logger.warning(f"CREDO Style-Bert-VITS2 fast TTS fallback: {exc}")
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
