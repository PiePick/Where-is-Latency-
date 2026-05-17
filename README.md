# CREDO Latency-Cover VTuber Prototype

CREDO is a research prototype for hiding perceived LLM/TTS latency in an AI VTuber or virtual NPC. The current platform is Open-LLM-VTuber with a Python-side CREDO agent.

Team handoff and machine setup notes live in [`TEAM_CODEX_PROMPT.md`](TEAM_CODEX_PROMPT.md).
Codex-based dependency and open-source runtime recovery steps live in
[`CODEX_SETUP.md`](CODEX_SETUP.md).

## Current Architecture

```text
Viewer text / mic input
  -> Open-LLM-VTuber websocket loop
  -> CREDO FastTrack
       DistilBERT emotion classifier
       spaCy keyword extraction
       hybrid reaction list
       StyleBERT-VITS2 short TTS
  -> CREDO SlowTrack
       local OpenAI-compatible LLM
       Fish Speech expressive TTS
  -> Live2D avatar response
```

The old Unity project and WinTTS prototype were removed. The active runtime is now:

```text
AI_NPC_System/                 CREDO Python code, models, data, scripts
reaction_sources/              source datasets and merged reaction evidence
vendor/open-llm-vtuber/        VTuber UI/runtime platform
vendor/fish-speech/            SlowTrack expressive TTS runtime
```

## Important Files

```text
AI_NPC_System/project_config.sh
  Single place to change LLM, TTS, voice, prompt, reaction, and runtime settings.

AI_NPC_System/integrations/open_llm_vtuber/
  CREDO agent adapter for Open-LLM-VTuber.

AI_NPC_System/models/setfit_swda_intent_minilm_optimized/
  Selected SWDA SetFit intent model.

AI_NPC_System/reports/setfit_intent_evaluation.xlsx
  Validation/test report for the SetFit intent model.

AI_NPC_System/prepared_fasttrack_data/
  Preprocessed GoEmotions and SWDA coarse-label data.

AI_NPC_System/latency_logs/
  Local-only JSONL and Markdown latency records generated during experiments.

AI_NPC_System/expressive_audio_pool/
  Local-only Fish Speech extreme nonverbal reaction clips and manifest.

AI_NPC_System/VoiceSample/
  Project voice source used for CREDO voice reference preparation.

AI_NPC_System/integrations/open_llm_vtuber/live2d_models/
  Project Live2D avatar and motion assets copied into Open-LLM-VTuber.

vendor/fish-speech/references/credo_voice_sample/
  Fish Speech reference voice clips generated from the tracked CREDO sample.

vendor/open-llm-vtuber/live2d-models/credo_avatar/
  Open-LLM-VTuber runtime copy of the CREDO Live2D model.
```

## WSL Quick Start

Run these commands in WSL, not Windows CMD:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
```

For a fresh teammate machine, follow [`CODEX_SETUP.md`](CODEX_SETUP.md) first.

Install or refresh Open-LLM-VTuber dependencies:

```bash
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
```

Install FastTrack build/evaluation dependencies when needed:

```bash
vendor/open-llm-vtuber/.venv/bin/python -m pip install -r AI_NPC_System/scripts/requirements.txt
vendor/open-llm-vtuber/.venv/bin/python -m spacy download en_core_web_sm
```

Start the local LLM server:

```bash
AI_NPC_System/scripts/start_local_llm_server.sh
```

Start Fish Speech for SlowTrack TTS on GPU0:

```bash
AI_NPC_System/scripts/start_fish_speech_server.sh
```

Start the dedicated FastTrack StyleBERT-VITS2 TTS server on GPU0 after its repo and CREDO-compatible model assets are installed. The launcher now preflights WSL line endings, Python 3.12 media dependencies, StyleBERT config drift, and BERT weight presence:

```bash
AI_NPC_System/scripts/start_stylebert_vits2_server.sh
```

For a fresh StyleBERT venv, allow local Python dependency repair:

```bash
STYLEBERT_VITS2_AUTO_INSTALL=1 AI_NPC_System/scripts/start_stylebert_vits2_server.sh

# Download temporary default StyleBERT voices if model_assets is empty:
STYLEBERT_VITS2_AUTO_DOWNLOAD_MODELS=1 AI_NPC_System/scripts/start_stylebert_vits2_server.sh

# The downloaded default voices are JP-only. This is only for Japanese smoke tests:
STYLEBERT_VITS2_LANGUAGE=JP AI_NPC_System/scripts/start_stylebert_vits2_server.sh

# For CREDO English FastTrack, place a CREDO-compatible English StyleBERT model under vendor/Style-Bert-VITS2/model_assets.
```

Run the Open-LLM-VTuber CREDO integration after the LLM, Fish Speech, and FastTrack TTS servers are up:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Open the UI:

```text
http://localhost:12393
```

The Open-LLM-VTuber page now includes a small `CREDO VTuber Mode` panel in the
browser. `VTuber Mode` starts proactive monologue, `Monologue` triggers one
manual idle line, and `Donation` queues a donation-style reaction for recording
experiments. If a YouTube API key plus either a live chat ID or video ID is
entered, the same mode starts the local YouTube live-chat bridge.

## Configuration

Change experiment components in:

```bash
nano AI_NPC_System/project_config.sh
```

Key variables:

```text
LOCAL_LLM_MODEL                  SlowTrack local LLM served name
LOCAL_LLM_BASE_URL               OpenAI-compatible local LLM endpoint
FAST_TRACK_TTS_MODE              stylebert_vits2 dedicated FastTrack TTS
FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK 0 prevents default cute TTS fallback
FAST_TRACK_AUDIO_CACHE_ENABLED   0 for realtime FastTrack TTS by default
STYLEBERT_VITS2_BASE_URL         FastTrack TTS endpoint
FISH_SPEECH_BASE_URL             SlowTrack TTS endpoint
FISH_SPEECH_REFERENCE_ID         voice reference id
OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME Live2D model name
SLOW_TRACK_SYSTEM_PROMPT         local LLM response policy
CREDO_MAX_COVER_BLOCKS           extra prebuilt cover blocks while SlowTrack waits
CREDO_ENABLE_EXTRA_COVER_AUDIO   enable expressive audio blocks
LOCAL_LLM_CUDA_VISIBLE_DEVICES   GPU1 for SlowTrack local LLM
FISH_SPEECH_CUDA_VISIBLE_DEVICES GPU0 for heavier SlowTrack Fish Speech
STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES GPU0 for FastTrack TTS
```

## Data and Model Tasks

Rebuild the reaction dataset:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_reaction_dataset.py
```

Run the dual classifier prototype script:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/fasttrack_dual_classifier_pipeline.py
```

Evaluate and tune the SetFit intent classifier:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/evaluate_and_tune_setfit_intent.py
```

Measure TTS latency:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_tts_latency.py --runs 3
```

Measure end-to-end pipeline latency:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_pipeline_latency.py --runs 3
```

Generate the temporary Fish Speech extreme nonverbal audio pool:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_extreme_nonverbal_reactions.py --force
```

Measure Fish Speech latency by text length for dynamic cover planning:

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_fish_speech_length_sweep.py --runs 2
```

Latency records are appended to `AI_NPC_System/latency_logs/events.jsonl`.
`AI_NPC_System/latency_logs/latest_summary.md` is a readable rolling summary.

## Current Limitation

StyleBERT-VITS2 is the realtime lightweight FastTrack TTS path and must be installed separately under `vendor/Style-Bert-VITS2` with CREDO voice-compatible model assets. FastTrack does not require prebuilt audio cache files and no longer falls back to Open-LLM-VTuber default TTS unless `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=1` is explicitly set.

Project-owned voice samples, Fish Speech references, and the CREDO Live2D avatar/motions are tracked through explicit `.gitignore` exceptions. Large runtimes, virtual environments, model checkpoints, generated audio caches, and temporary experiment logs remain local-only.
