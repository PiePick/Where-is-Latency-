# CREDO Runtime Stack Stability

Use `run_credo_stack.sh` as the normal entrypoint for a full local CREDO run.
It starts the services in dependency order, waits for health checks, writes
logs/pids, and monitors child processes.

## Full Live Stack

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

`live` starts:

1. Fish Speech on `http://127.0.0.1:8080`
2. Local LLM on `http://127.0.0.1:8001`
3. Open-LLM-VTuber on `http://127.0.0.1:12393`

Piper is no longer part of the default `live` profile. It is kept only for
explicit realtime-TTS experiments:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live-piper
```

If a service is already healthy, the stack runner reuses it instead of starting
a duplicate.

## Common Modes

```bash
# Check health only.
AI_NPC_System/scripts/run_credo_stack.sh --profile live --status

# Fish-only mode for offline cache generation.
AI_NPC_System/scripts/run_credo_stack.sh --profile cache

# Alias for the default Fish-bundle live path.
AI_NPC_System/scripts/run_credo_stack.sh --profile live-no-piper

# Start only selected services.
AI_NPC_System/scripts/run_credo_stack.sh --only fish,llm
```

## Logs And Pids

Logs are written to:

```text
AI_NPC_System/runtime/logs/
```

Pids are written to:

```text
AI_NPC_System/runtime/pids/
```

The latest machine-readable service state is:

```text
AI_NPC_System/runtime/credo_stack_state.json
```

## Live Latency CSV

Every CREDO turn appends module-level latency rows in real time:

```text
AI_NPC_System/latency_logs/module_events.csv
```

Each row is one measured module/stage event, not a whole session summary. The
important columns are:

- `turn_id`: groups FastTrack, SlowTrack, TTS, and total rows from the same user turn.
- `module`: compact module name such as `fasttrack_analysis`, `fasttrack_audio`, `slowtrack_llm`, `slowtrack_tts`, or `turn_total`.
- `elapsed_ms`: measured latency for that module.
- `emotion`, `intent`, `response_act`, `style_tag`: runtime routing labels when available.
- `cache_hit`, `audio_path`: whether FastTrack used a prebuilt wav and where it came from.
- `text_preview`: short preview for quickly matching the row to the utterance.

Watch it while the stack is running:

```bash
tail -f AI_NPC_System/latency_logs/module_events.csv
```

The older JSONL log and Markdown summary are still written:

```text
AI_NPC_System/latency_logs/events.jsonl
AI_NPC_System/latency_logs/latest_summary.md
```

## Restart Policy

By default, child services are restarted up to two times if they exit. The
Open-LLM-VTuber UI is not auto-restarted because it is the visible frontend and
manual restart is easier to reason about during demos.

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --max-restarts 3
AI_NPC_System/scripts/run_credo_stack.sh --profile live --no-restart
```

Fish Speech may not answer `/v1/health` immediately while a long TTS request is
running. The stack runner therefore uses a longer default health timeout and
also checks whether the TCP port is open before deciding that a server is dead.
If you are generating longer sentences or running under heavy GPU load,
increase the timeout:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 30
```

## VTuber Mode

Open the Open-LLM-VTuber frontend after the live stack starts:

```text
http://127.0.0.1:12393
```

The CREDO overlay in the bottom-right controls VTuber mode.

- `Stream topic`: the topic anchor for quiet moments.
- `Idle sec`: how long chat must be quiet before CREDO speaks by itself.
- `VTuber Mode`: starts contextual idle monologues and optionally the YouTube chat bridge.
- `Monologue`: queues one intentional longer streamer-style segment.
- `Donation`: queues a test support reaction.

Idle speech now uses server-side stream state instead of a fixed short prompt:

1. It waits until no conversation is active.
2. It checks how long chat has been quiet.
3. It includes the topic anchor and latest viewer/chat text.
4. It asks the CREDO agent for one cohesive 12-24 word spoken segment.
5. It uses the same Fish/Live2D path as normal speech.

Short-term memory is still lightweight JSON memory, not a vector database. It
stores recent turns plus simple profile facts such as name, likes, dislikes,
and current projects, then injects that compact context into the local LLM only
when generating SlowTrack or VTuber-mode speech.

## Important Operational Rule

Do not start a second Fish Speech server while a 600-item offline synthesis run
is active. If Fish is already healthy, `run_credo_stack.sh` will reuse it.

For the current Fish-cache plan:

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python \
AI_NPC_System/scripts/build_persona_reaction_bundle.py \
  --output-dir AI_NPC_System/persona_reaction_bundle_response_act_v1 \
  --skip-existing \
  --synthesize
```

This command is resumable. Re-running it skips items whose `audio_path` already
exists. Do not add `--disable-tts-cues` for the current Fish 600-audio bundle;
the intended bundle uses inline emotion/style cues during offline synthesis such
as `[happy] [playful]` and `[excited] [energetic]`. Runtime playback uses the
pre-generated wav files, not inline tags.

## Interjection Audio Bundle

FastTrack starts with pre-generated nonverbal/interjection audio plus Live2D
motion before the text reaction. The current pure-interjection bundle is:

```text
AI_NPC_System/expressive_interjection_bundle/manifest.json
```

It contains only short carriers such as `ha-ha!`, `hee-hee!`, `ahaha!`,
`haha!`, `oh!`, `aw!`, `ugh.`, `hm.`, `mm.`, `huh?`, and `oh?`. Dialogue-like
carriers such as `nice!`, `let's go!`, `what?`, `wait.`, `okay.`, `got it.`,
and `alright.` are intentionally excluded from this bundle. Each synthesized
line starts and ends with one `[short pause]` cue so the clip does not cut in or
out too abruptly.

Regenerate or resume the bundle:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python \
AI_NPC_System/scripts/build_interjection_audio_bundle.py \
  --skip-existing \
  --synthesize
```
