# TTS Engine Routing

CREDO now has one local selector for swapping TTS engines without manually editing
Open-LLM-VTuber YAML.

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/select_tts_engine.py --list
AI_NPC_System/scripts/select_tts_engine.py --status
```

## Main Open-LLM-VTuber TTS

Use this when changing the voice used by the normal Open-LLM-VTuber response.

```bash
AI_NPC_System/scripts/select_tts_engine.py edge --check
AI_NPC_System/scripts/select_tts_engine.py cosyvoice2 --check
AI_NPC_System/scripts/select_tts_engine.py melo --check
AI_NPC_System/scripts/select_tts_engine.py coqui --check
```

Current practical choices:

- `edge`: fastest stable English fallback. No voice clone, no style tags.
- `cosyvoice2`: middle-ground experiment. Uses the current English reference
  voice sample and measured around 4.0 seconds through the Open-LLM-VTuber
  client on the local setup.
- `melo` / `coqui`: Open-LLM-VTuber-supported alternatives, but local voice
  quality and dependency readiness still need separate validation.

When `cosyvoice2` is selected, start its server before Open-LLM-VTuber:

```bash
AI_NPC_System/scripts/start_cosyvoice2_server.sh
```

Then start Open-LLM-VTuber:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

The launcher now fails early if `cosyvoice2_tts` is selected but the
CosyVoice2 web server is not reachable.

## FastTrack TTS

FastTrack is a separate low-latency path. It can be changed with the same
selector:

```bash
AI_NPC_System/scripts/select_tts_engine.py piper --check
AI_NPC_System/scripts/select_tts_engine.py fish --check
AI_NPC_System/scripts/select_tts_engine.py stylebert --check
```

Current practical choices:

- `piper`: default FastTrack path. Very fast English speech, no voice clone.
- `fish`: expressive/reference experiment, but too slow for realtime FastTrack.
- `stylebert`: kept only as a legacy path until an English model is prepared.

## Stability Rule

For live runs, use:

- Open-LLM main TTS: `edge` for reliability, or `cosyvoice2` for current
  reference-voice testing.
- FastTrack TTS: `piper`.

Only switch FastTrack to `fish` for offline cache generation or explicit
quality experiments.
