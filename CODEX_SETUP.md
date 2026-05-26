# CREDO Reproduction Setup

현재 라이브 경로는 `Open-LLM-VTuber + local LLM + StyleBERT 언어 TTS`와
`prebuilt StyleBERT 비언어 음원`이다. Fish 서버, CosyVoice2, Piper는 기본 실행
의존성이 아니다.

## Required Local Resources

```text
vendor/open-llm-vtuber/                         UI, Live2D, websocket runtime
vendor/open-llm-vtuber/.venv/                   runtime Python environment
vendor/Style-Bert-VITS2/                        StyleBERT-VITS2 language TTS server
vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en/
AI_NPC_System/fasttrack_assets/models/          SWDA SetFit intent model
AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/manifest.json
AI_NPC_System/integrations/open_llm_vtuber/live2d_models/credo_avatar/
```

The separated dataset pool remains required as the labeled text evidence source.
The nonverbal StyleBERT manifest and its wav files are required for interjection
and motion playback; live Fish synthesis is not required during a live run.

## Install

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
vendor/open-llm-vtuber/.venv/bin/python -m pip install -r AI_NPC_System/scripts/requirements.txt
vendor/open-llm-vtuber/.venv/bin/python -m spacy download en_core_web_sm
```

The bundled Open-LLM-VTuber installation must be able to call the local
StyleBERT-VITS2 server at `http://127.0.0.1:5000`.

## Active Configuration

`AI_NPC_System/project_config.sh` is the canonical editable config.

```text
FAST_TRACK_TTS_MODE=stylebert_vits2
FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=0
FAST_TRACK_PERSONA_BUNDLE_ENABLED=0
FAST_TRACK_DATASET_POOL_FILE=fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json
FAST_TRACK_PREBUILT_ONLY=0
FAST_TRACK_KEYWORD_ECHO_ENABLED=0
STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en
STYLEBERT_VITS2_LANGUAGE=EN
STYLEBERT_VITS2_DEVICE=cuda
OPEN_LLM_VTUBER_TTS_MODEL=stylebert_vits2
OPEN_LLM_VTUBER_SLOW_TTS_MODE=open_llm
CREDO_VTUBER_SLOW_PREFETCH_ENABLED=1
CREDO_INTERJECTION_AUDIO_BUNDLE_FILE=fasttrack_assets/audio/expressive_interjection_bundle/manifest.json
```

Do not insert Fish style tags into spoken text. Fish style cues apply only
when generating the offline nonverbal bundle. Emotion and motion intensity
belong in output metadata and Live2D actions at runtime.

## Activate And Verify

After changes under `AI_NPC_System/integrations/open_llm_vtuber/`:

```bash
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/check_runtime_readiness.py
```

`PARTIAL` is expected if servers are not currently running. A missing
Open-LLM-VTuber environment, StyleBERT server/model, intent model, dataset pool,
or avatar asset is a setup failure.

## Run

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

`live` starts StyleBERT-VITS2, the local LLM, and Open-LLM-VTuber. It does not
allocate a GPU to Fish Speech or launch Piper. Open `http://127.0.0.1:12393`,
hard refresh after frontend changes, and select the VTuber panel factors. The
default candidate is `Grounded` contextual mapping and `Parallel` scheduling.

Startup warmup is enabled by default. After each required service is healthy,
the launcher performs one real StyleBERT synthesis, one local LLM chat
completion, and one Open-LLM-VTuber CREDO status call before the live monitor
loop starts. This keeps the first user-facing turn out of the cold path. Use
`--no-warmup` only when diagnosing startup failures; use `--warmup-timeout 180`
if the first GPU request needs more time.

Monitor latency:

```bash
tail -f AI_NPC_System/latency_logs/module_events.csv
```

## Archived Experiments

Fish Speech checkpoints are needed only to reproduce historical Fish experiments.
The generated `expressive_interjection_bundle` is a live StyleBERT asset;
other Fish/Cosy/Piper/Edge results are historical comparisons.
