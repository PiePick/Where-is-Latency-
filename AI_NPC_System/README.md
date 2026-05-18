# AI_NPC_System

Python-side CREDO research code for Open-LLM-VTuber.

## Runtime Modules

```text
config.py                  Shared config loader.
project_config.sh          Main editable experiment settings.
fast_track.py              Stable FastTrack facade.
fast_track_engine.py       DistilBERT emotion, spaCy keyword, reaction routing.
slow_track.py              OpenAI-compatible local LLM caller.
tts_client.py              Fish Speech client for SlowTrack.
piper_tts_client.py         Dedicated Piper client for FastTrack.
stylebert_vits2_client.py  Legacy StyleBERT-VITS2 client for experiments.
tts_cues.py                Fish Speech cue selection helpers.
memory_store.py            JSON-backed memory for SlowTrack prompts.
integrations/open_llm_vtuber/ Open-LLM-VTuber adapter and Live2D assets.
```

## Data and Models

```text
hybrid_reactions.json              Final FastTrack reaction list.
fish_speech_nonverbal_cues.json    Fish Speech tag candidates.
prepared_fasttrack_data/           Preprocessed GoEmotions and SWDA data.
models/setfit_swda_intent_minilm_optimized/ Selected intent model.
reports/setfit_intent_evaluation.xlsx       SetFit validation/test report.
VoiceSample/                       Tracked CREDO voice reference source.
```

Generated runtime outputs are intentionally ignored by git. Project-owned
voice/avatar assets are tracked through root `.gitignore` exceptions:

```text
tts_outputs/
latency_benchmarks/
fast_track_audio_cache*/
fish_speech_tag_audio/
```

For teammate setup and missing open-source dependency recovery, see
`../CODEX_SETUP.md`.

## Run

From WSL:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
AI_NPC_System/scripts/start_fish_speech_server.sh
AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Open:

```text
http://localhost:12393
```

Dedicated FastTrack Piper TTS is the default and requires `vendor/piper-tts` plus an English ONNX voice. Prepare it once, then keep the resident server running for sub-second synthesis:

```bash
PIPER_TTS_AUTO_INSTALL=1 PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 AI_NPC_System/scripts/setup_piper_fasttrack_tts.sh
AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh
```

## Evaluate

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/evaluate_and_tune_setfit_intent.py
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_pipeline_latency.py --runs 3
```
