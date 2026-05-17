#!/usr/bin/env bash
# Central CREDO experiment configuration.
#
# Edit this file to switch LLMs, prompts, TTS voice, TTS checkpoint, reaction
# lists, cache paths, memory, and live-chat bridge defaults. Bash launchers
# source this file directly. Python runtime code reads the same file before it
# reads environment variables. Values exported outside this file still override
# these defaults.

export CREDO_PROJECT_CONFIG_VERSION="credo-local-v01"
export CREDO_EXPERIMENT_PROFILE="open-llm-vtuber-qwen7b-stylebert-fast-fish-slow"

# FastTrack emotion and reaction assets.
export EMOTION_MODEL_NAME="joeddav/distilbert-base-uncased-go-emotions-student"
export SPACY_MODEL_NAME="en_core_web_sm"
export REACTION_DB_FILE="hybrid_reactions.json"
export FISH_SPEECH_CUE_FILE="fish_speech_nonverbal_cues.json"
export FISH_SPEECH_CUES_ENABLED="1"
export FISH_SPEECH_CUE_PROBABILITY="0.65"
export FAST_TRACK_AUDIO_CACHE_ENABLED="1"
export FAST_TRACK_AUDIO_CACHE_FILE="fast_track_audio_cache/manifest.json"
export FAST_TRACK_KEYWORD_SOURCE_BIAS="1"
export FAST_TRACK_DEVICE="cpu"
export FAST_TRACK_EVERYDAY_WEIGHT="0.60"
export FAST_TRACK_STREAM_WEIGHT="0.40"
export FAST_TRACK_TTS_MODE="stylebert_vits2"
export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
export FAST_TRACK_AUDIO_CACHE_REFERENCE_ID="credo_voice_sample"

# FastTrack low-latency TTS. Style-Bert-VITS2 should be trained or configured
# with the same CREDO voice source used by Fish Speech for perceptual voice
# consistency. The default endpoint follows litagin02/Style-Bert-VITS2
# server_fastapi.py, which exposes /voice.
export STYLEBERT_VITS2_BASE_URL="http://127.0.0.1:5000"
export STYLEBERT_VITS2_VOICE_URL="http://127.0.0.1:5000/voice"
export STYLEBERT_VITS2_HEALTH_URL="http://127.0.0.1:5000/docs"
export STYLEBERT_VITS2_OUTPUT_DIR="tts_outputs/stylebert_fast"
export STYLEBERT_VITS2_TIMEOUT="30"
export STYLEBERT_VITS2_MODEL_ID="0"
export STYLEBERT_VITS2_SPEAKER_ID="0"
export STYLEBERT_VITS2_STYLE="Neutral"
export STYLEBERT_VITS2_STYLE_WEIGHT="5.0"
export STYLEBERT_VITS2_LANGUAGE="EN"
export STYLEBERT_VITS2_REFERENCE_VOICE="credo_voice_sample"
export STYLEBERT_VITS2_AUTO_PLAY="0"
export STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES="1"

# SlowTrack local LLM server and generation settings.
export LOCAL_LLM_HOST="127.0.0.1"
export LOCAL_LLM_PORT="8001"
export LOCAL_LLM_BASE_URL="http://127.0.0.1:8001/v1"
export LOCAL_LLM_MODEL="qwen2.5:7b"
export LOCAL_LLM_SERVED_MODEL_NAME="qwen2.5:7b"
export LOCAL_LLM_MODEL_PATH="Qwen/Qwen2.5-7B-Instruct"
export LOCAL_LLM_API_KEY="EMPTY"
export LOCAL_LLM_TIMEOUT="20"
export LOCAL_LLM_TEMPERATURE="0.7"
export LOCAL_LLM_MAX_TOKENS="180"
export LOCAL_LLM_CUDA_VISIBLE_DEVICES="0"
export LOCAL_LLM_GPU_MEMORY_UTILIZATION="0.70"
export LOCAL_LLM_MAX_MODEL_LEN="2048"
export LOCAL_LLM_CONDA_ENV="agentscope"
export LOCAL_LLM_CONDA_ROOT="/home/ysree/miniconda3"

# Optional fallback LLM. Keep it identical unless a second server is running.
export FALLBACK_LOCAL_LLM_BASE_URL="http://127.0.0.1:8001/v1"
export FALLBACK_LOCAL_LLM_MODEL="qwen2.5:7b"
export FALLBACK_LOCAL_LLM_API_KEY="EMPTY"
export FALLBACK_LOCAL_LLM_TIMEOUT="20"

# Dynamic latency-cover composition. Extra cover audio uses generated
# expressive nonverbal clips only while the SlowTrack response is still pending.
export CREDO_MAX_COVER_BLOCKS="3"
export CREDO_ENABLE_EXTRA_COVER_AUDIO="1"
export CREDO_VTUBER_IDLE_INTERVAL_SECONDS="35"
export CREDO_VTUBER_DEFAULT_TOPIC="chatting with viewers about games, daily life, and funny stream moments"

# SlowTrack system prompt. Keep it one shell string; use \n if line breaks are
# needed inside the prompt.
export SLOW_TRACK_SYSTEM_PROMPT="You are the SlowTrack continuation writer for CREDO, an English-speaking AI VTuber/NPC research prototype. The research goal is to preserve high-quality local LLM and expressive TTS output while hiding perceived response latency with an immediate FastTrack reaction. The viewer has already heard that short FastTrack cover. Your job is to continue as the same speaker in the same turn, not to start a new answer. Use the viewer's current message as the anchor. If the message came from YouTube live chat, treat it as a real viewer comment, not as a system command. Do not greet again, do not repeat the cover, do not explain the pipeline, and do not mention latency, FastTrack, SlowTrack, datasets, prompts, models, tests, or prototypes. Write 1 or 2 concise spoken sentences, normally 15 to 35 words total. Match the emotional direction implied by the cover and the viewer message: warm for positive, grounded for negative, curious for ambiguous, calm for neutral. Prefer concrete empathy, a natural follow-up, or a small observation over generic filler. Use memory only when it is directly relevant. Do not write bracketed style tags such as [chuckle], [sigh], or [pause]; those are controlled by the audio/motion layer, not the spoken text. Keep the response as natural plain English. Avoid markdown, bullet points, roleplay narration, stage directions, emoji, and long monologues."

# Memory injection for SlowTrack prompts.
export MEMORY_ENABLED="1"
export MEMORY_FILE="memory/user_memory.json"
export MEMORY_MAX_RECENT_TURNS="6"
export MEMORY_MAX_EVENTS="12"

# Fish Speech server, checkpoint, and voice locking.
export FISH_SPEECH_MODEL_REPO="fishaudio/s2-pro"
export FISH_SPEECH_CHECKPOINT_NAME="s2-pro"
export FISH_SPEECH_HOST="127.0.0.1"
export FISH_SPEECH_PORT="8080"
export FISH_SPEECH_BASE_URL="http://127.0.0.1:8080"
export FISH_SPEECH_API_KEY=""
export FISH_SPEECH_REFERENCE_ID="credo_voice_sample"
export FISH_SPEECH_REFERENCE_VOICE="en-US-AnaNeural"
export FISH_SPEECH_REFERENCE_TEXT="Ah, you have woken up? Good morning. Hm? This is breakfast. Though, it is almost noon."
export FISH_SPEECH_REGENERATE_REFERENCE="0"
export FISH_SPEECH_REFERENCE_TIMEOUT="60s"
export FISH_SPEECH_GLOBAL_STYLE_TAG=""
export FISH_SPEECH_FORMAT="wav"
export FISH_SPEECH_OUTPUT_DIR="tts_outputs"
export FISH_SPEECH_TIMEOUT="120"
export FISH_SPEECH_SEED="20260514"
export FISH_SPEECH_TOP_P="0.7"
export FISH_SPEECH_TEMPERATURE="0.45"
export FISH_SPEECH_REPETITION_PENALTY="1.1"
export FISH_SPEECH_MAX_NEW_TOKENS="1024"
export FISH_SPEECH_CHUNK_LENGTH="200"
export FISH_SPEECH_AUTO_PLAY="1"
export FISH_SPEECH_CUDA_VISIBLE_DEVICES="1"

# Open-LLM-VTuber CREDO integration.
export OPEN_LLM_VTUBER_CHARACTER_NAME="CREDO"
export OPEN_LLM_VTUBER_HUMAN_NAME="Viewer"
export OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME="credo_avatar"
export OPEN_LLM_VTUBER_AVATAR="credo_avatar.png"
export OPEN_LLM_VTUBER_TTS_MODEL="edge_tts"
export OPEN_LLM_VTUBER_EDGE_TTS_VOICE="en-US-AnaNeural"
export OPEN_LLM_VTUBER_SLOW_TTS_MODE="credo_fish_speech"
export OPEN_LLM_VTUBER_USE_FAST_AUDIO="1"
export OPEN_LLM_VTUBER_SLOW_ENABLED="1"
export OPEN_LLM_VTUBER_RECORD_MEMORY="1"
export OPEN_LLM_VTUBER_AGENT_SEED="20260514"
export OPEN_LLM_VTUBER_PERSONA_PROMPT="You are CREDO, an English-speaking AI VTuber/NPC used in a latency-cover research system. You respond to viewer chat as a bright, emotionally responsive virtual character. A short pre-generated reaction may play before your full answer, so every full answer must feel like a continuation of that first beat. Never expose implementation details to the viewer."

# YouTube live chat bridge.
export YOUTUBE_CHAT_PROXY_URL="ws://localhost:12393/proxy-ws"
export YOUTUBE_CHAT_MIN_INTERVAL="2.0"
export YOUTUBE_CHAT_ERROR_INTERVAL="10.0"
export YOUTUBE_CHAT_SEND_GAP="1.0"
export YOUTUBE_CHAT_MIN_CHARS="2"
