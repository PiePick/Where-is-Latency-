# Team Codex Setup Prompt for CREDO

You are working on the CREDO AI VTuber/NPC latency-cover research project.

Before editing code, restore local resources that are excluded by `.gitignore`.
The project will not run correctly unless these assets, checkpoints, references,
and virtual environments are installed or linked.

Use `CODEX_SETUP.md` as the canonical install checklist for missing open-source
runtimes, checkpoints, Python dependencies, and readiness verification.

CREDO's audience-facing speech is English-only. Understand multilingual viewer
input as context, but keep FastTrack, SlowTrack, proactive VTuber mode, donation
reactions, captions, and TTS text in natural English. Do not mention this policy
to viewers.

## Required Local Resources

1. Fish Speech
- Expected path: `vendor/fish-speech`
- Required checkpoint: `vendor/fish-speech/checkpoints/s2-pro`
- `codec.pth` must exist inside the checkpoint directory.
- Required runtime voice reference: `vendor/fish-speech/references/credo_eunice_english_v2`
- The reference directory must contain matching `.wav` and `.lab` pairs.
- If missing, regenerate it from:
  - `AI_NPC_System/VoiceSample/VoicePack1_Morning.wav`
  - `AI_NPC_System/scripts/prepare_fish_reference_voice.py`

2. Open-LLM-VTuber
- Expected path: `vendor/open-llm-vtuber`
- Required runtime: `vendor/open-llm-vtuber/.venv`
- Re-apply the CREDO integration after editing integration files:
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate`

3. Python ML Dependencies
Open-LLM-VTuber `.venv` must support:
- `transformers`
- `torch`
- `spacy`
- `datasets`
- `setfit`
- `faiss`
- `en_core_web_sm`

If FastTrack fails with `FastTrack ML runtime dependencies are missing`, install
dependencies into `vendor/open-llm-vtuber/.venv`.

```bash
vendor/open-llm-vtuber/.venv/bin/python -m pip install -r AI_NPC_System/scripts/requirements.txt
vendor/open-llm-vtuber/.venv/bin/python -m spacy download en_core_web_sm
```

4. Local LLM
- OpenAI-compatible endpoint: `http://127.0.0.1:8001/v1`
- Default served model: `qwen2.5:7b`
- Start script: `AI_NPC_System/scripts/start_local_llm_server.sh`

5. Runtime Config
Main config file:
- `AI_NPC_System/project_config.sh`

Important current decisions:
- Realtime FastTrack TTS is discarded for the main handoff path. Do not require Piper or StyleBERT to run CREDO.
- The latency-cover path is real-time selection/sequencing of prepared assets, not real-time synthesis.
- `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"` should remain disabled so the wrong cute fallback voice does not appear.
- `FISH_SPEECH_REFERENCE_ID="credo_eunice_english_v2"`
- `FISH_SPEECH_GLOBAL_STYLE_TAG=""`
- `OPEN_LLM_VTUBER_SLOW_TTS_MODE="credo_fish_speech"`
- Fish Speech is for SlowTrack high-quality TTS and offline audio/bundle generation.
- Strong CREDO emotion motions should be attached only to prebuilt nonverbal latency-cover audio; normal speech should stay on Idle/Talk/lip-sync.
- Latency-cover planning must use the artifact-backed kNN predictor in `AI_NPC_System/latency_predictor.py`; rebuild `AI_NPC_System/reports/latency_prediction_model.json` from `latency_logs/events.jsonl` after new benchmark/runtime measurements.

Do not put bracketed style tags such as `[chuckle]`, `[sigh]`, `[playful]`, or `[pause]` inside spoken text. Fish Speech may read them aloud. Store style tags as metadata only.


## Current Research State

Current block pipeline:
1. DistilBERT emotion selects a pre-generated nonverbal Fish Speech interjection audio clip.
2. The matching emotion AvatarMotion plays with that nonverbal audio.
3. The offline persona reaction bundle supplies a short text/audio reaction candidate.
4. If predicted SlowTrack latency remains, a pre-generated residual filler such as a long “Hmm...” clip may be inserted.
5. SlowTrack local LLM + Fish Speech produces the main answer.

Persona reaction bundle files:
- `AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/manifest.json`: runtime file with 120 cells and 600 selected reactions/audio files.
- `AI_NPC_System/scripts/build_persona_reaction_bundle.py`: generator for the compact dataset-grounded bundle.

FastTrack realtime TTS status:
- Discarded for the main research path.
- Piper/StyleBERT files may remain in the repo as legacy experiments, but a new Codex should not make them required startup dependencies.

## Startup Order

Start local LLM:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
```

Start Fish Speech for SlowTrack on GPU0:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_fish_speech_server.sh
```

Do not start Piper or StyleBERT for the current default path. They are legacy experiment scripts only.

Start Open-LLM-VTuber with CREDO:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Open:

```text
http://localhost:12393
```

Hard refresh the browser after frontend changes.

## Debug Checklist

Run readiness check:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/check_runtime_readiness.py
```

Check these first when broken:
- Fish Speech health: `http://127.0.0.1:8080/v1/health`
- Local LLM models: `http://127.0.0.1:8001/v1/models`
- `credo_eunice_english_v2` contains `.wav/.lab` pairs.
- `transformers.pipeline` imports inside Open-LLM-VTuber `.venv`.
- `spacy.load("en_core_web_sm")` works.
- CREDO integration was re-applied after integration edits.

## Git-Tracked Project Assets

These project-owned assets should be tracked even if broader ignore rules hide
binary files:
- `AI_NPC_System/VoiceSample`
- `vendor/fish-speech/references/credo_voice_sample`
- `vendor/fish-speech/references/credo_eunice_english_v2` when distributing the current Eunice runtime voice outside this workstation
- `AI_NPC_System/integrations/open_llm_vtuber/live2d_models/credo_avatar`
- `vendor/open-llm-vtuber/live2d-models/credo_avatar`
- `vendor/open-llm-vtuber/avatars/credo_avatar.png`
- `reaction_sources/AvatarMotion`

Do not track:
- Python `.venv`
- model checkpoints
- Hugging Face caches
- generated TTS output caches
- temporary experiment logs

## Development Rule

Do not assume git-tracked files are enough. This project depends on local model
checkpoints, generated voice references, vendored repositories, and Python
virtual environments that may be intentionally excluded from git.
