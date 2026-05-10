# Fish Speech Integration

## Purpose

Fish Speech is used as the local TTS layer for the AI NPC prototype. Unity does not need to load Fish Speech directly. The Python side generates FastTrack and SlowTrack text, calls the local Fish Speech HTTP server, saves an audio file, and plays it locally when possible.

## License Note

Fish Speech is distributed under the Fish Audio Research License. Research and non-commercial use are permitted by that license, while commercial use requires a separate Fish Audio license. For experiments and papers, describe the usage as research use and keep attribution/license notices. For voice cloning, only use reference voices with consent.

## Local Layout

```text
vendor/fish-speech
AI_NPC_System/tts_client.py
AI_NPC_System/tts_cues.py
AI_NPC_System/fish_speech_nonverbal_cues.json
AI_NPC_System/scripts/start_fish_speech_server.sh
AI_NPC_System/scripts/build_tts_cues.py
```

## Fish Speech Server

Download weights inside the cloned repo:

```bash
cd vendor/fish-speech
hf download fishaudio/s2-pro --local-dir checkpoints/s2-pro
```

Start the server:

```bash
AI_NPC_System/scripts/start_fish_speech_server.sh
```

Default endpoint:

```text
http://127.0.0.1:8080/v1/tts
```

The base TTS model is selected when the Fish Speech server starts. The request does not include a model name.

## FastTrack Behavior

FastTrack now builds a Fish Speech-ready TTS string:

```text
[surprised] Ah I had no idea! About today?
```

The emotional reaction still comes from `hybrid_reactions.json`. The nonverbal cue comes from `fish_speech_nonverbal_cues.json`.

Cue selection is controlled by:

```text
FISH_SPEECH_CUES_ENABLED=1
FISH_SPEECH_CUE_PROBABILITY=0.65
```

The FastTrack cue list now uses most stable Fish Speech README/WebUI tags. It excludes tags that are too context-bound or risky for automatic short reactions, such as `[singing]`, `[echo]`, `[audience laughter]`, `[with strong accent]`, `[moaning]`, `[interrupting]`, and `[panting]`.

## SlowTrack Behavior

SlowTrack system prompts now tell the local LLM that Fish Speech supports inline tags. The model is allowed to use at most one short tag per sentence from the approved tag set.

Primary local LLM:

```text
http://127.0.0.1:8002/v1
llama3.3:70b-awq
```

Fallback local LLM:

```text
http://127.0.0.1:8001/v1
qwen2.5:7b
```

## Local Chat Test

```bash
FAST_TRACK_DEVICE=cpu python3 AI_NPC_System/main.py
```

If the Fish Speech server is reachable, the script writes audio files under:

```text
AI_NPC_System/tts_outputs
```

and attempts local playback. If the server is not running, text generation continues and TTS is skipped.

## Unity Strategy

The recommended architecture is:

```text
Unity or Live2D UI
  -> Python local server
      -> FastTrack text
      -> SlowTrack text
      -> Fish Speech HTTP TTS
      -> wav file or audio URL
  -> UI plays wav/audio URL
```

This avoids embedding Fish Speech inside Unity. A Live2D or browser-based chat UI can use the same Python backend later.
