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
python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py
```

To also activate the generated config as Open-LLM-VTuber's `conf.yaml`:

```bash
python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
```

Open-LLM-VTuber still needs its own Python dependencies before the server can
run. Follow its upstream install flow inside `vendor/open-llm-vtuber`; this
adapter does not vendor those packages.

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
   - Falls back to Open-LLM-VTuber TTS if the cached wav is missing.
   - Sends Live2D expression actions mapped from Positive, Negative,
     Ambiguous, or Neutral.
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
`model_dict.json` `emotionMap`. The adapter will use the first matching
expression per turn.
