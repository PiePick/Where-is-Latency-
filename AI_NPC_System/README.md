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
stylebert_vits2_client.py  StyleBERT-VITS2 client for FastTrack.
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
VoiceSample/                       Local-only CREDO voice reference source.
```

Generated audio outputs are intentionally ignored by git:

```text
VoiceSample/
integrations/open_llm_vtuber/live2d_models/
tts_outputs/
latency_benchmarks/
fast_track_audio_cache*/
fish_speech_tag_audio/
```

## Run

From WSL:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
AI_NPC_System/scripts/start_fish_speech_server.sh
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Open:

```text
http://localhost:12393
```

StyleBERT-VITS2 FastTrack TTS is configured but requires `vendor/Style-Bert-VITS2` and model assets:

```bash
AI_NPC_System/scripts/start_stylebert_vits2_server.sh
```

## Evaluate

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/evaluate_and_tune_setfit_intent.py
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_pipeline_latency.py --runs 3
```
