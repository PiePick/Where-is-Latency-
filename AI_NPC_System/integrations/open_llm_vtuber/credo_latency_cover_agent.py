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


PROACTIVE_IDLE_CATEGORIES = ("Positive", "Neutral")
FISH_STYLE_TAG_RE = re.compile(r"\s*\[[^\]]+\]\s*")
LAUGH_EVENT_RE = re.compile(r"(?i)(?:\b(?:ha+ha+|he+he+|ahaha+|hehe+|lol)\b)")
SURPRISE_EVENT_RE = re.compile(r"(?i)(?:\b(?:wow|whoa|woah|no way)\b|oh[!,.]?)")
THINKING_EVENT_RE = re.compile(r"(?i)\b(?:uh|um|hmm+|mmm+)\b")


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
        user_text, is_proactive = self._extract_input(input_data)
        if not user_text:
            return

        if not self.fast_track_enabled:
            logger.info("CREDO FastTrack disabled; running SlowTrack-only turn.")
            async for output in self._chat_slow_only(user_text, turn_started):
                yield output
            return

        if is_proactive:
            yield self._build_proactive_output()
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
        intent = self._classify_intent(user_text)
        style_tag = self._style_tag_for_emotion(emotion)
        persona_cover = self.persona_reaction_bundle.choose(emotion, intent, style_tag)
        if persona_cover:
            fast_plain_text = self._clean_spoken_text(persona_cover.plain_tts_text)
            fast_raw_tts_text = persona_cover.tts_text
            fast_tts_text = self._prepare_fast_tts_text(fast_raw_tts_text, fast_plain_text)
            fast_display_text = self._with_response_gap(fast_plain_text)
            fast_result["reaction_source"] = persona_cover.source
            fast_result["fast_audio_path"] = str(persona_cover.audio_path) if persona_cover.audio_path else None
            fast_result["fast_audio_cache_path"] = str(persona_cover.audio_path) if persona_cover.audio_path else None
            fast_result["persona_bundle_id"] = persona_cover.cache_id
            fast_result["persona_style_tag"] = style_tag
        speech_actions = self._speech_actions(emotion, style_tag=style_tag, text=fast_plain_text)

        logger.info(
            "CREDO FastTrack cover: "
            f"emotion={emotion}, intent={intent}, source={fast_result.get('reaction_source')}, "
            f"cache={fast_result.get('fast_audio_cache_hit')}"
        )

        fast_audio_started = time.perf_counter()
        fast_audio_path = await self._resolve_fast_audio(fast_result, fast_tts_text, emotion=emotion)
        self._log_latency(
            "fast_track_tts_or_cache",
            fast_audio_started,
            text=fast_tts_text,
            engine=self._credo_config.FAST_TRACK_TTS_MODE,
            metadata={"audio_path": str(fast_audio_path) if fast_audio_path else None},
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

        memory_context = self.memory.build_prompt_context() if self.memory else None
        slow_started = time.perf_counter()
        slow_task = asyncio.create_task(
            self._slow_track.generate_response(
                user_text,
                fast_tts_text,
                fast_result.get("strategy"),
                memory_context,
            )
        )

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
                metadata=cover_plan,
            )
        )
        async for cover_output in self._yield_extra_cover_audio(cover_plan, slow_task, emotion):
            yield cover_output

        slow_text = await slow_task
        self._log_latency(
            "slow_track_llm",
            slow_started,
            text=user_text,
            engine=self._credo_config.LOCAL_LLM_MODEL,
            metadata={"emotion": emotion, "intent": intent},
        )
        slow_text = self._clean_spoken_text(slow_text) or "I hear you."

        slow_tts_started = time.perf_counter()
        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        self._log_latency(
            "slow_track_tts",
            slow_tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={"audio_path": str(slow_audio) if slow_audio else None},
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

        if self.memory:
            self.memory.record_turn(
                user_text=user_text,
                assistant_text=slow_text,
                fast_reaction=fast_plain_text,
                emotion=emotion,
                keywords=fast_result.get("keywords") or [],
            )

        self._log_latency(
            "turn_total",
            turn_started,
            text=f"{fast_display_text} {slow_text}",
            engine="open_llm_vtuber_credo",
            metadata={"emotion": emotion, "intent": intent},
        )

    async def _chat_slow_only(
        self,
        user_text: str,
        turn_started: float,
    ) -> AsyncIterator[AudioOutput | SentenceOutput]:
        """Run the ablation path with no FastTrack analysis, cover text, audio, or motion."""
        speech_actions = self._speech_actions("neutral")
        memory_context = self.memory.build_prompt_context() if self.memory else None

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
            metadata={"fast_track_enabled": False},
        )
        slow_text = self._clean_spoken_text(slow_text) or "I hear you."

        slow_tts_started = time.perf_counter()
        slow_audio = await self._try_synthesize_slow_audio(slow_text)
        self._log_latency(
            "slow_track_tts",
            slow_tts_started,
            text=slow_text,
            engine="fish_speech" if slow_audio else "open_llm_tts_fallback",
            metadata={"audio_path": str(slow_audio) if slow_audio else None, "fast_track_enabled": False},
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
            metadata={"fast_track_enabled": False},
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
        """Prefer CREDO's own cached FastTrack audio, then the configured fast TTS engine."""
        cached_path = fast_result.get("fast_audio_path")
        if cached_path and Path(str(cached_path)).exists():
            return Path(str(cached_path))

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
