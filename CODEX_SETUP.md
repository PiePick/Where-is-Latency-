# Codex Reproduction Setup

This file is the handoff checklist for teammates using Codex on a fresh CREDO
workspace. Keep project-owned assets in git, but reinstall open-source runtimes,
model checkpoints, virtual environments, and caches locally.

## Asset Policy

Tracked CREDO assets:

```text
AI_NPC_System/VoiceSample/
AI_NPC_System/integrations/open_llm_vtuber/live2d_models/credo_avatar/
vendor/fish-speech/references/credo_voice_sample/
vendor/open-llm-vtuber/avatars/credo_avatar.png
vendor/open-llm-vtuber/live2d-models/credo_avatar/
TEAM_CODEX_PROMPT.md
```

Do not commit these local/open-source/runtime files:

```text
vendor/*/.venv/
vendor/fish-speech/checkpoints/
vendor/open-llm-vtuber/live2d-models/mao_pro/
vendor/open-llm-vtuber/live2d-models/shizuku/
AI_NPC_System/tts_outputs/
AI_NPC_System/latency_logs/
AI_NPC_System/fast_track_audio_cache*/
AI_NPC_System/expressive_audio_pool/
```

## Fresh Clone Recovery

From WSL:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
git pull origin Master
```

If an open-source vendor directory is missing, clone it locally:

```bash
mkdir -p vendor
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git vendor/open-llm-vtuber
git clone https://github.com/fishaudio/fish-speech.git vendor/fish-speech
git clone https://github.com/litagin02/Style-Bert-VITS2.git vendor/Style-Bert-VITS2
```

The CREDO avatar and Fish Speech reference files are tracked in this repo. If a
clone command overwrote or hid them, restore the tracked copies:

```bash
git checkout -- \
  vendor/fish-speech/references/credo_voice_sample \
  vendor/open-llm-vtuber/avatars/credo_avatar.png \
  vendor/open-llm-vtuber/live2d-models/credo_avatar
```

## Install Dependencies

Install or refresh Open-LLM-VTuber plus CREDO FastTrack dependencies:

```bash
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
vendor/open-llm-vtuber/.venv/bin/python -m pip install -r AI_NPC_System/scripts/requirements.txt
vendor/open-llm-vtuber/.venv/bin/python -m spacy download en_core_web_sm
```

Install Fish Speech runtime:

```bash
AI_NPC_System/scripts/install_fish_speech_runtime.sh
```

Prepare Piper for the dedicated FastTrack TTS server. Piper is used because the local StyleBERT assets are JP-only, while CREDO FastTrack must synthesize English reactions in real time. It installs into `vendor/piper-tts` and downloads one English ONNX voice:

```bash
PIPER_TTS_AUTO_INSTALL=1 PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 AI_NPC_System/scripts/setup_piper_fasttrack_tts.sh
```

Start the resident Piper FastTrack server before Open-LLM-VTuber. This server keeps the model loaded in RAM; do not use per-request CLI synthesis for the latency-cover path.

```bash
AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh
```

Benchmark the target latency after the server is up:

```bash
python3 AI_NPC_System/scripts/benchmark_fasttrack_tts_latency.py --engine piper_tts --text "That sounds good." --runs 5 --warmup 1
```

StyleBERT-VITS2 remains only as a legacy experiment path. JP-only default StyleBERT voices are not a valid CREDO English FastTrack configuration.

Download the Fish Speech S2-Pro checkpoint locally. This is intentionally not
tracked in git:

```bash
cd vendor/fish-speech
hf download fishaudio/s2-pro --local-dir checkpoints/s2-pro
cd /mnt/c/Users/CGLAB/Desktop/CREDO
```

If `hf` is missing, install the Hugging Face CLI in the environment you use for
downloads:

```bash
python3 -m pip install --user -U "huggingface_hub[cli]"
```

## Reference Voice

Expected reference directory:

```text
vendor/fish-speech/references/credo_voice_sample
```

It should contain four `.wav/.lab` pairs plus `source_translation.txt`. If the
directory is missing or stale, regenerate from the tracked voice sample:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/prepare_fish_reference_voice.py
```

Fish Speech caches reference tokens. After changing reference audio, restart the
Fish Speech server. The CREDO TTS client must keep:

```text
"use_memory_cache": "off"
```

## Audience Language Policy

CREDO is configured for English-only audience-facing output. Keep these defaults enabled unless an experiment explicitly studies multilingual output:

```text
CREDO_OUTPUT_LANGUAGE=English
CREDO_ENGLISH_ONLY_OUTPUT=1
```

FastTrack, SlowTrack, VTuber idle monologues, and donation reactions should understand multilingual viewer input as context but answer in natural English without mentioning the policy.

## FastTrack Realtime TTS

FastTrack uses a dedicated resident Piper TTS server by default. It does not require prebuilt FastTrack audio cache files:

```text
FAST_TRACK_TTS_MODE=piper_tts
FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=0
FAST_TRACK_AUDIO_CACHE_ENABLED=0
FAST_TRACK_INLINE_CUES_ENABLED=0
FISH_SPEECH_CUES_ENABLED=0
PIPER_TTS_BASE_URL=http://127.0.0.1:5001
PIPER_TTS_VOICE=en_US-lessac-medium
PIPER_TTS_LENGTH_SCALE_POSITIVE=0.92
PIPER_TTS_LENGTH_SCALE_NEGATIVE=1.08
PIPER_TTS_LENGTH_SCALE_AMBIGUOUS=0.98
PIPER_TTS_LENGTH_SCALE_NEUTRAL=1.0
```

This keeps the pipeline as: FastTrack reaction text selection, immediate Piper synthesis with emotion-specific request parameters, then playback. Fish Speech bracket cue bundles are not inserted into FastTrack text unless `FAST_TRACK_TTS_MODE=fish_speech` and `FAST_TRACK_INLINE_CUES_ENABLED=1` are both explicitly set. Open-LLM-VTuber's default cute TTS is blocked unless `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=1` is explicitly set.

Latency-cover planning uses `AI_NPC_System/reports/latency_prediction_model.json` as an artifact-backed kNN index. Local `latency_logs/events.jsonl` is preferred when present; otherwise the committed artifact still provides real kNN neighbors for SlowTrack Fish Speech TTS prediction. Rebuild it after benchmark runs with:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_latency_prediction_model.py
```

The cache builder remains available only as an optional experiment tool:

```bash
AI_NPC_System/scripts/build_fast_track_audio_cache.py --engine fish_speech --force
```

## GPU Allocation

Default async server placement. Piper FastTrack runs on CPU/RAM through its resident server; Fish Speech remains the heavier GPU-side TTS and the local LLM stays on GPU1:

```text
LOCAL_LLM_CUDA_VISIBLE_DEVICES=1
FISH_SPEECH_CUDA_VISIBLE_DEVICES=0
PIPER_TTS_USE_CUDA=0
PIPER_TTS_BASE_URL=http://127.0.0.1:5001
```

GPU0 is reserved for the heavier TTS side, especially Fish Speech. GPU1 is used for the local LLM server. Piper keeps its English ONNX model in system RAM so FastTrack synthesis avoids extra VRAM pressure while staying sub-second.

## Apply Integration

Re-apply CREDO files into Open-LLM-VTuber after changing integration code:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
```

## Verify

FastTrack dependency smoke test:

```bash
vendor/open-llm-vtuber/.venv/bin/python - <<'PY'
from transformers import pipeline
import spacy
spacy.load("en_core_web_sm")
print("FastTrack deps OK")
PY
```

Runtime readiness:
Latency predictor artifact:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_latency_prediction_model.py
```

Runtime readiness:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/check_runtime_readiness.py
cat AI_NPC_System/reports/runtime_readiness_latest.md
```

`PARTIAL` is acceptable when the local LLM, Fish Speech server, or
Open-LLM-VTuber web server is not currently running. `BLOCKED` means a required
asset, checkpoint, or dependency is missing.

## Run

Use separate terminals:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
```

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_fish_speech_server.sh
```

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh
```

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Open:

```text
http://localhost:12393
```

Hard refresh the browser after frontend changes.

## Before Committing

Never use `git add .` in this repo. Stage only CREDO-owned files:

```bash
git status --short
git diff --stat
git add README.md TEAM_CODEX_PROMPT.md CODEX_SETUP.md .gitignore
git add AI_NPC_System/VoiceSample
git add AI_NPC_System/integrations/open_llm_vtuber/live2d_models/credo_avatar
git add -f vendor/fish-speech/references/credo_voice_sample
git add -f vendor/open-llm-vtuber/avatars/credo_avatar.png
git add -f vendor/open-llm-vtuber/live2d-models/credo_avatar
```

Do not stage vendored open-source source trees, checkpoints, virtual
environments, Hugging Face caches, generated audio, or temporary logs.
