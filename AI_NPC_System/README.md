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
piper_tts_client.py         Legacy Piper experiment client; not current default.
stylebert_vits2_client.py  Legacy StyleBERT-VITS2 experiment client; not current default.
tts_cues.py                Fish Speech cue selection helpers.
memory_store.py            JSON-backed memory for SlowTrack prompts.
integrations/open_llm_vtuber/ Open-LLM-VTuber adapter and Live2D assets.
docs/persona_reaction_bundle.md Offline persona-conditioned FastTrack bundle pipeline.
```

## Data and Models

```text
hybrid_reactions.json              Final FastTrack reaction list.
fish_speech_nonverbal_cues.json    Fish Speech tag candidates.
prepared_fasttrack_data/           Preprocessed GoEmotions and SWDA data.
persona_reaction_bundle/           Generated persona-filtered FastTrack text/audio bundle.
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

From WSL, current default run:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
AI_NPC_System/scripts/start_fish_speech_server.sh
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Do not start Piper/StyleBERT for the current main path. Realtime FastTrack TTS has been discarded; latency cover should use pre-generated nonverbal audio, the offline persona reaction bundle, and optional residual filler audio.

For a SlowTrack-only ablation, run:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo_no_fasttrack.sh
```

Open:

```text
http://localhost:12393
```

Legacy Piper/StyleBERT scripts are kept for experiments only. They are not required for the current handoff path.

## Persona Reaction Bundle

The offline persona bundle creates:

```text
4 emotions x 6 response intents x 5 style tags x 5 variants = 600 reactions
```

The local LLM filters/re-writes labeled GoEmotions and SWDA seed pairs for the configured VTuber personality.

Current files:
- `persona_reaction_bundle/manifest.json`: runtime bundle, 120 cells and 600 selected reactions.
- `persona_reaction_bundle/seed_provenance.json`: 30 labeled seed pairs per cell for reproducibility, not runtime candidates.

Full details: `docs/persona_reaction_bundle.md`.

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --skip-existing --seed-max-words 7 --seed-max-chars 70 --max-tokens 240
```

## Evaluate

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/evaluate_and_tune_setfit_intent.py
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_pipeline_latency.py --runs 3
```
