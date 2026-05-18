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
- `FAST_TRACK_TTS_MODE="piper_tts"`
- `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"`
- `FAST_TRACK_AUDIO_CACHE_ENABLED="0"` by default; FastTrack uses realtime lightweight TTS, not prebuilt audio.
- `FAST_TRACK_INLINE_CUES_ENABLED="0"`; Piper FastTrack uses request parameters, not Fish Speech bracket cue bundles.
- `PIPER_TTS_BASE_URL="http://127.0.0.1:5001"`; the resident Piper server must be running for sub-second FastTrack TTS.
- `PIPER_TTS_VOICE="en_US-lessac-medium"`; replace only with another English Piper voice that benchmarks under the target.
- `PIPER_TTS_LENGTH_SCALE_*` and `PIPER_TTS_NOISE_SCALE_*` map FastTrack emotions to Piper voice-control parameters.
- `FISH_SPEECH_REFERENCE_ID="credo_voice_sample"`
- `FISH_SPEECH_GLOBAL_STYLE_TAG=""`
- `OPEN_LLM_VTUBER_SLOW_TTS_MODE="credo_fish_speech"`
- Strong CREDO emotion motions should be attached only to prebuilt nonverbal latency-cover audio; normal speech should stay on Idle/Talk/lip-sync.
- Latency-cover planning must use the artifact-backed kNN predictor in `AI_NPC_System/latency_predictor.py`; rebuild `AI_NPC_System/reports/latency_prediction_model.json` from `latency_logs/events.jsonl` after new benchmark/runtime measurements.

Do not put bracketed style tags such as `[chuckle]`, `[sigh]`, or `[pause]`
inside spoken text. For the current Piper FastTrack path, emotion is passed
through Piper request parameters such as length/noise scale. Nonverbal behavior must be controlled by the
audio and motion layers.

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

Prepare/start the dedicated FastTrack Piper TTS server:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
PIPER_TTS_AUTO_INSTALL=1 PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 AI_NPC_System/scripts/setup_piper_fasttrack_tts.sh
AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh
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
