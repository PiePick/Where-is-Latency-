# Team Codex Setup Prompt for CREDO

You are working on the CREDO AI VTuber/NPC latency-cover research project.

Before editing code, restore local resources that are excluded by `.gitignore`.
The project will not run correctly unless these assets, checkpoints, references,
and virtual environments are installed or linked.

Use `CODEX_SETUP.md` as the canonical install checklist for missing open-source
runtimes, checkpoints, Python dependencies, and readiness verification.

## Required Local Resources

1. Fish Speech
- Expected path: `vendor/fish-speech`
- Required checkpoint: `vendor/fish-speech/checkpoints/s2-pro`
- `codec.pth` must exist inside the checkpoint directory.
- Required voice reference: `vendor/fish-speech/references/credo_voice_sample`
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

Important values:
- `FAST_TRACK_TTS_MODE="stylebert_vits2"`
- `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"`
- `FAST_TRACK_AUDIO_CACHE_REFERENCE_ID="credo_voice_sample"`
- `FISH_SPEECH_REFERENCE_ID="credo_voice_sample"`
- `FISH_SPEECH_GLOBAL_STYLE_TAG=""`
- `OPEN_LLM_VTUBER_SLOW_TTS_MODE="credo_fish_speech"`

Do not put bracketed style tags such as `[chuckle]`, `[sigh]`, or `[pause]`
inside spoken text. Nonverbal behavior must be controlled by the audio and
motion layers.

## Startup Order

Start local LLM:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_local_llm_server.sh
```

Start Fish Speech for SlowTrack on GPU1:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_fish_speech_server.sh
```

Start the dedicated FastTrack StyleBERT-VITS2 TTS server on GPU1:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_stylebert_vits2_server.sh
```

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
- `credo_voice_sample` contains `.wav/.lab` pairs.
- `transformers.pipeline` imports inside Open-LLM-VTuber `.venv`.
- `spacy.load("en_core_web_sm")` works.
- CREDO integration was re-applied after integration edits.

## Git-Tracked Project Assets

These project-owned assets should be tracked even if broader ignore rules hide
binary files:
- `AI_NPC_System/VoiceSample`
- `vendor/fish-speech/references/credo_voice_sample`
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
