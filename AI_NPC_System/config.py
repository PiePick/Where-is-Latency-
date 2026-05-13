"""Runtime configuration for the AI NPC Fast/Slow Track prototype.

Every value can be overridden with an environment variable so experiments can
switch models, ports, and output paths without editing runtime code.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool) -> bool:
    """Read a permissive boolean environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() not in {"0", "false", "no", "off"}


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable with a clear fallback."""
    return float(os.getenv(name, str(default)))


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a clear fallback."""
    return int(os.getenv(name, str(default)))


# Cloud fallback is intentionally disabled by default.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Fast Track: DistilBERT + spaCy + prebuilt hybrid reaction list.
EMOTION_MODEL_NAME = os.getenv(
    "EMOTION_MODEL_NAME",
    "joeddav/distilbert-base-uncased-go-emotions-student",
)
SPACY_MODEL_NAME = os.getenv("SPACY_MODEL_NAME", "en_core_web_sm")
REACTION_DB_FILE = os.getenv("REACTION_DB_FILE", "hybrid_reactions.json")
REACTION_DB_PATH = ROOT_DIR / REACTION_DB_FILE
FISH_SPEECH_CUE_FILE = os.getenv("FISH_SPEECH_CUE_FILE", "fish_speech_nonverbal_cues.json")
FISH_SPEECH_CUE_PATH = ROOT_DIR / FISH_SPEECH_CUE_FILE
FISH_SPEECH_CUES_ENABLED = _env_bool("FISH_SPEECH_CUES_ENABLED", True)
FISH_SPEECH_CUE_PROBABILITY = _env_float("FISH_SPEECH_CUE_PROBABILITY", 0.65)
FAST_TRACK_AUDIO_CACHE_ENABLED = _env_bool("FAST_TRACK_AUDIO_CACHE_ENABLED", True)
FAST_TRACK_AUDIO_CACHE_FILE = os.getenv(
    "FAST_TRACK_AUDIO_CACHE_FILE",
    "fast_track_audio_cache/manifest.json",
)
FAST_TRACK_AUDIO_CACHE_PATH = ROOT_DIR / FAST_TRACK_AUDIO_CACHE_FILE
FAST_TRACK_KEYWORD_SOURCE_BIAS = _env_bool("FAST_TRACK_KEYWORD_SOURCE_BIAS", True)
FAST_TRACK_DEVICE = os.getenv("FAST_TRACK_DEVICE", "auto")
FAST_TRACK_MIN_RUNTIME_SCORE = _env_float("FAST_TRACK_MIN_RUNTIME_SCORE", 0.0)
FAST_TRACK_EVERYDAY_WEIGHT = _env_float("FAST_TRACK_EVERYDAY_WEIGHT", 0.60)
FAST_TRACK_STREAM_WEIGHT = _env_float("FAST_TRACK_STREAM_WEIGHT", 0.40)

# Slow Track: quality local LLM first, smaller local model second.
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8002/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.3:70b-awq")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "EMPTY")
LOCAL_LLM_TIMEOUT = _env_float("LOCAL_LLM_TIMEOUT", 45.0)
LOCAL_LLM_TEMPERATURE = _env_float("LOCAL_LLM_TEMPERATURE", 0.7)
LOCAL_LLM_MAX_TOKENS = _env_int("LOCAL_LLM_MAX_TOKENS", 180)

FALLBACK_LOCAL_LLM_BASE_URL = os.getenv(
    "FALLBACK_LOCAL_LLM_BASE_URL",
    "http://127.0.0.1:8001/v1",
)
FALLBACK_LOCAL_LLM_MODEL = os.getenv("FALLBACK_LOCAL_LLM_MODEL", "qwen2.5:7b")
FALLBACK_LOCAL_LLM_API_KEY = os.getenv("FALLBACK_LOCAL_LLM_API_KEY", "EMPTY")
FALLBACK_LOCAL_LLM_TIMEOUT = _env_float("FALLBACK_LOCAL_LLM_TIMEOUT", 20.0)

# Backward-compatible aliases for older scripts.
OLLAMA_URL = FALLBACK_LOCAL_LLM_BASE_URL
OLLAMA_MODEL = FALLBACK_LOCAL_LLM_MODEL

# Slow lane ETA hint for clients/logging.
EXPECTED_SLOW_LANE_MS = _env_int("EXPECTED_SLOW_LANE_MS", 3500)

# External memory. The LLM stays stateless; this file is injected into prompts.
MEMORY_ENABLED = _env_bool("MEMORY_ENABLED", True)
MEMORY_FILE = os.getenv("MEMORY_FILE", "memory/user_memory.json")
MEMORY_PATH = ROOT_DIR / MEMORY_FILE
MEMORY_MAX_RECENT_TURNS = _env_int("MEMORY_MAX_RECENT_TURNS", 6)
MEMORY_MAX_EVENTS = _env_int("MEMORY_MAX_EVENTS", 12)

# Fish Speech TTS HTTP server. The base model is selected when that server starts.
FISH_SPEECH_BASE_URL = os.getenv("FISH_SPEECH_BASE_URL", "http://127.0.0.1:8080")
FISH_SPEECH_TTS_URL = os.getenv("FISH_SPEECH_TTS_URL", f"{FISH_SPEECH_BASE_URL}/v1/tts")
FISH_SPEECH_HEALTH_URL = os.getenv("FISH_SPEECH_HEALTH_URL", f"{FISH_SPEECH_BASE_URL}/v1/health")
FISH_SPEECH_API_KEY = os.getenv("FISH_SPEECH_API_KEY", "")
FISH_SPEECH_REFERENCE_ID = os.getenv("FISH_SPEECH_REFERENCE_ID") or None
FISH_SPEECH_FORMAT = os.getenv("FISH_SPEECH_FORMAT", "wav")
FISH_SPEECH_OUTPUT_DIR = ROOT_DIR / os.getenv("FISH_SPEECH_OUTPUT_DIR", "tts_outputs")
FISH_SPEECH_TIMEOUT = _env_float("FISH_SPEECH_TIMEOUT", 120.0)
FISH_SPEECH_TOP_P = _env_float("FISH_SPEECH_TOP_P", 0.8)
FISH_SPEECH_TEMPERATURE = _env_float("FISH_SPEECH_TEMPERATURE", 0.8)
FISH_SPEECH_REPETITION_PENALTY = _env_float("FISH_SPEECH_REPETITION_PENALTY", 1.1)
FISH_SPEECH_MAX_NEW_TOKENS = _env_int("FISH_SPEECH_MAX_NEW_TOKENS", 1024)
FISH_SPEECH_CHUNK_LENGTH = _env_int("FISH_SPEECH_CHUNK_LENGTH", 200)
FISH_SPEECH_AUTO_PLAY = _env_bool("FISH_SPEECH_AUTO_PLAY", True)
