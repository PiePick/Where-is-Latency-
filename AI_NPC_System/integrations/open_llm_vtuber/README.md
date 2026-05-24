# Open-LLM-VTuber Integration

This adapter makes Open-LLM-VTuber the interaction platform while keeping the
CREDO research logic inside `AI_NPC_System`.

## Role Split

- Open-LLM-VTuber: frontend, websocket loop, ASR/VAD, Live2D rendering, chat UI.
- AI_NPC_System: DistilBERT emotion classification, hybrid reaction list, cached
  FastTrack Fish Speech audio, SlowTrack local LLM prompt, JSON memory.

## Install

From the repository root:

```bash
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
```

Run the integrated server with:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

The install script creates `vendor/open-llm-vtuber/.venv`, installs
Open-LLM-VTuber dependencies, installs the CREDO FastTrack runtime dependencies,
downloads `en_core_web_sm`, provides a venv-local `ffmpeg`, updates submodules,
and activates the generated CREDO config.

For a config and FastTrack smoke test:

```bash
AI_NPC_System/scripts/smoke_open_llm_vtuber_credo.sh
```

The script copies the CREDO agent into:

```text
vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py
```

It also registers the agent in Open-LLM-VTuber's factory/config schema and adds:

```text
vendor/open-llm-vtuber/characters/credo_latency_cover.yaml
vendor/open-llm-vtuber/conf.credo.yaml
```

## Runtime Behavior

For each user turn, the CREDO agent emits:

1. A FastTrack latency-cover output.
   - Uses pre-generated Fish Speech audio when available.
   - Does not fall back to Open-LLM-VTuber TTS in the default profile; missing cached wav files are treated as a configuration problem to avoid wrong-voice output.
   - Sends Open-LLM-VTuber expression actions plus CREDO speech-safe motion tags.
   - Nonverbal cover audio uses stronger `credo_fast_motion:*` motion tags.
2. A SlowTrack continuation.
   - Uses the local OpenAI-compatible LLM configured in `AI_NPC_System/config.py`.
   - Can synthesize through the local Fish Speech HTTP server.
   - Records CREDO JSON memory when `MEMORY_ENABLED=1`.

## Live2D Expression Mapping

The included character config uses broad fallback tags:

```yaml
positive: ['joy', 'happy', 'smile', 'positive_01', 'positive_02', 'positive_03']
negative: ['sadness', 'sad', 'worried', 'negative_01', 'negative_02', 'negative_03']
ambiguous: ['surprise', 'confused', 'ambiguous_01', 'ambiguous_02', 'ambiguous_03']
neutral: ['neutral', 'idle', 'neutral_01', 'neutral_02', 'neutral_03']
```

For the custom Live2D model, put matching keys in Open-LLM-VTuber's
`model_dict.json` `emotionMap`. The adapter keeps that default expression path
alive and also adds `credo_speech_motion:positive|negative|ambiguous|neutral`
during spoken output. The frontend maps those tags to the mouth-stripped
`PositiveTalk`, `NegativeTalk`, `AmbiguousTalk`, and `NeutralTalk` motion groups
so lip-sync can continue controlling the mouth.

The agent also sends a `credo_motion_profile:*` tag for each spoken output.
The frontend overlay maps that profile to motion intensity:

- `energetic` and `playful`: faster talk-motion repeats, stronger body/head
  parameter pulses, and a small lip-sync mouth-open boost.
- `bright` and `alert`: moderate body movement for positive or surprised turns.
- `smug`, `cute`, `low`, and `steady`: restrained mouth/body movement for calmer
  or negative turns.

This keeps expression selection, speech timing, and movement intensity coupled to
the same audio payload instead of firing unrelated idle motions.

Prebuilt nonverbal cover audio still uses `credo_fast_motion:*`, mapped to the
stronger non-talk motion groups.
