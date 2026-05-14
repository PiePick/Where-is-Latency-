# AI NPC System

This folder contains the Python side of the FastTrack/SlowTrack VTuber NPC prototype.

## Runtime Files

```text
main.py                 Local text chat loop.
tcp_server.py           TCP server for Unity or another local client.
fast_track.py           Stable FastTrack facade.
fast_track_engine.py    DistilBERT, spaCy, cache-aware reaction sampling, and TTS cue mixing.
fast_track_audio_cache.py  Manifest loader for pre-generated FastTrack cover audio.
memory_store.py        JSON-backed user profile, recent-turn, and emotional-event memory.
slow_track.py           Local OpenAI-compatible LLM caller.
tts_client.py           Fish Speech HTTP TTS client and local playback helper.
tts_cues.py             Emotion-aware Fish Speech cue selector.
config.py               Python loader for the shared project settings.
project_config.sh       Single editable experiment config for LLM, prompts, TTS, data, and runtime paths.
integrations/open_llm_vtuber/  Open-LLM-VTuber agent adapter and installer.
```

## Data Files

```text
hybrid_reactions.json               Final FastTrack reaction list.
fish_speech_nonverbal_cues.json     Fish Speech nonverbal cue buckets.
fast_track_audio_cache/manifest.json    Pre-generated FastTrack audio cache manifest.
memory/user_memory.json                 Runtime memory file, ignored by git.
```

## Scripts

```text
scripts/build_reaction_dataset.py       Rebuild hybrid_reactions.json.
scripts/build_tts_cues.py               Rebuild fish_speech_nonverbal_cues.json.
scripts/benchmark_tts_latency.py        Measure Fish Speech /v1/tts latency.
scripts/prebuild_fast_track_tts_cache.py Pre-generate FastTrack latency-cover wav files.
scripts/install_fish_speech_runtime.sh  Install the local Fish Speech Python runtime.
scripts/start_fish_speech_server.sh     Start the local Fish Speech API server.
scripts/start_local_llm_server.sh       Start the compact local vLLM server.
scripts/install_open_llm_vtuber_runtime.sh Install Open-LLM-VTuber runtime dependencies.
scripts/run_open_llm_vtuber_credo.sh    Start Open-LLM-VTuber with the CREDO agent.
scripts/smoke_open_llm_vtuber_credo.sh  Validate config and FastTrack loading.
scripts/run_youtube_live_chat_bridge.sh Forward YouTube Live Chat into Open-LLM-VTuber.
scripts/requirements.txt                Dataset/FastTrack build dependencies.
```

## Common Commands

Change experiment components in one place first:

```bash
nano AI_NPC_System/project_config.sh
```

The shell launchers source this file, and Python runtime modules load the same
file before reading environment variables. A one-off environment variable still
overrides the file, for example:

```bash
LOCAL_LLM_MODEL="other-served-name" AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

```bash
python3 -m pip install -r AI_NPC_System/scripts/requirements.txt
python3 -m spacy download en_core_web_sm
FAST_TRACK_DEVICE=cpu python3 AI_NPC_System/main.py
python3 AI_NPC_System/tcp_server.py
AI_NPC_System/scripts/install_fish_speech_runtime.sh
AI_NPC_System/scripts/start_fish_speech_server.sh
python3 AI_NPC_System/scripts/prebuild_fast_track_tts_cache.py --max-reactions-per-source 1 --cues-per-category 1
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
AI_NPC_System/scripts/smoke_open_llm_vtuber_credo.sh
YOUTUBE_API_KEY=... AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id YOUTUBE_VIDEO_ID --ignore-first-page
```

## Open-LLM-VTuber Platform

Open-LLM-VTuber can run the same research logic through the CREDO integration
agent. The platform handles the Live2D UI and websocket conversation loop. The
agent calls `AI_NPC_System` for DistilBERT emotion classification, cached
FastTrack audio, SlowTrack local LLM generation, Fish Speech synthesis, and JSON
memory. See `integrations/open_llm_vtuber/README.md` for the installation and
expression-map details. See `docs/open_llm_vtuber_runtime_flow.md` for the
research-facing runtime architecture and module boundaries.

## FastTrack Audio Cache

FastTrack now treats the immediate response as a pre-generated latency cover.
Keywords are not appended to the spoken line. They are used only as a weak hint
for choosing the everyday or stream bucket. If `fast_track_audio_cache/manifest.json`
points to existing wav files, runtime packets include `fast_audio_path` and the
local chat loop plays that file immediately. If the cache is missing, FastTrack
falls back to live Fish Speech text generation.

The default generated cache is intentionally small: one safe cover per emotion
and source pair, for eight wav files total. Increase `--max-reactions-per-source`
and `--cues-per-category` only when a larger video stimulus set is needed.

## Memory

The local LLM is stateless, so persistent memory is stored outside the model in
`memory/user_memory.json`. The memory module keeps a small user profile, recent
turns, and emotionally important events, then injects a compact memory context
into SlowTrack prompts. Disable it with `MEMORY_ENABLED=0` when a controlled
experiment should not include prior context.
