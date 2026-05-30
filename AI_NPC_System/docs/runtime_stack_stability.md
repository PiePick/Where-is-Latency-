# CREDO Runtime Stack Stability

작성 기준: 2026-05-26 KST

## Live Entry Point

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

`live` starts and monitors:

1. StyleBERT-VITS2 at `http://127.0.0.1:5000`
2. local LLM at `http://127.0.0.1:8001`
3. Open-LLM-VTuber at `http://127.0.0.1:12393`

Language TTS executes through the local StyleBERT-VITS2 server; there is no
Fish or Piper service in the current live stack. Standalone interjection
playback is sealed; regenerated nonverbal bundles are archive/reproduction
assets unless a future experiment explicitly reopens that path.

## Startup And Restart Policy

The stack runner waits for each service health endpoint and stores logs/pids:

```text
AI_NPC_System/runtime/logs/
AI_NPC_System/runtime/pids/
AI_NPC_System/runtime/credo_stack_state.json
```

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --status
AI_NPC_System/scripts/run_credo_stack.sh --profile live --max-restarts 3
AI_NPC_System/scripts/run_credo_stack.sh --profile live --no-restart
```

Warmup is enabled by default after a service passes health:

```text
stylebert -> POST /voice once with CREDO_STYLEBERT_WARMUP_TEXT
llm       -> POST /v1/chat/completions once with a tiny warmup prompt
open-llm  -> GET /credo/vtuber-mode/status once
```

The same warmup runs again when the stack runner restarts a crashed child
service. This intentionally moves StyleBERT first-synthesis cost and LLM
first-completion cost before the live monitor loop. To debug startup only:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --no-warmup
AI_NPC_System/scripts/run_credo_stack.sh --profile live --warmup-timeout 180
```

If Open-LLM-VTuber integration files change, activate them before restart:

```bash
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
```

## VTuber Mode Loop

Use the frontend factor controls. The default candidate is `Grounded`
contextual mapping and `Parallel` scheduling.

```text
current trigger
  -> StyleBERT FastTrack language reaction + viewer-emotion Live2D motion
  || local LLM starts SlowTrack work immediately
  -> StyleBERT SlowTrack playback
  -> while playback continues, chat is buffered and next idle speech is prefetched
  -> chat batch takes precedence; otherwise a prepared idle segment is used
```

Standalone interjection playback is sealed. The persona reaction and SlowTrack
are synthesized through StyleBERT-VITS2 on demand; expression/body tone follows
the analyzed viewer emotion while mouth movement remains audio lip-sync driven.

## Latency Trace

Each runtime module event is appended to:

```text
AI_NPC_System/latency_logs/module_events.csv
```

```bash
tail -f AI_NPC_System/latency_logs/module_events.csv
```

Primary modules are `fasttrack_analysis`, `emotion_motion_payload`,
`fasttrack_audio`, `slowtrack_llm`, `slowtrack_tts`, and `turn_total`.
Each new row also includes `component_mode`, `selection_policy`, and
`scheduling_mode`. Use this CSV, not prior Fish logs, when reporting the new
live condition.

`emotion_motion_payload` records the viewer-emotion Live2D action payload.
Standalone `fasttrack_interjection_dispatch` rows should not appear in the
current sealed-interjection runtime.

## Operational Limits

- StyleBERT server availability and first synthesis must complete before live
  turns; cold-start model load should be excluded from warm latency claims.
- A failed FastTrack/SlowTrack StyleBERT request is not retried through a second
  live TTS path by default; that would mix experimental conditions.
- Fish checkpoints are not needed during live operation. Generated StyleBERT
  interjection bundles are archived unless a future experiment explicitly
  reopens standalone playback.
