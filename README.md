# CREDO Latency-Cover VTuber Prototype

CREDO is a research prototype for hiding perceived LLM/TTS latency in an AI VTuber or virtual NPC. The current platform is Open-LLM-VTuber with a Python-side CREDO agent. All audience-facing CREDO speech is constrained to natural English, even when viewer input is multilingual.

Team handoff and machine setup notes live in [`TEAM_CODEX_PROMPT.md`](TEAM_CODEX_PROMPT.md).
Codex-based dependency and open-source runtime recovery steps live in
[`CODEX_SETUP.md`](CODEX_SETUP.md).

## Current Handoff Snapshot

The current research direction is **latency cover by real-time selection and sequencing**, not real-time FastTrack TTS synthesis.

Current decisions:
- Audience-facing output is English-only.
- FastTrack realtime TTS is discarded for the main path. Do not revive Piper/StyleBERT as the default FastTrack TTS without a new experiment decision.
- Fish Speech is used for SlowTrack high-quality TTS and offline audio/bundle generation, not per-turn FastTrack synthesis.
- The first latency-cover block should be a pre-generated nonverbal interjection audio clip selected by DistilBERT emotion, paired with matching Live2D AvatarMotion.
- The second block uses the offline persona reaction bundle: 4 emotions x 6 response intents x 5 style tags x 5 variants = 600 selected text reactions.
- If predicted residual latency remains, use pre-generated filler audio such as a long “Hmm...” clip.
- Normal speech should keep Idle/Talk/lip-sync. Emotion motions should be tied to pre-generated nonverbal audio blocks only.

Generated bundle files:
- `AI_NPC_System/persona_reaction_bundle_response_act_v1/manifest.json` is the runtime bundle. It has 120 cells and 600 selected reactions/audio files.
- `AI_NPC_System/reports/intent_transition_matrix_from_swda.*` stores the SWDA user-intent to response-act transition evidence used for probabilistic response selection.

## Current Architecture

```text
Viewer text / mic input
  -> Open-LLM-VTuber websocket loop
  -> CREDO analysis
       DistilBERT emotion classifier
       SetFit/SWDA intent classifier
       SWDA response-intent transition
       latency predictor
  -> Latency-cover block sequence
       pre-generated nonverbal audio + emotion motion
       persona reaction bundle text/audio candidate
       optional residual filler audio
  -> CREDO SlowTrack
       local OpenAI-compatible LLM
       Fish Speech expressive TTS
  -> Live2D avatar response with Idle/Talk/lip-sync preserved for speech
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
  Local-only JSONL, CSV, and Markdown latency records generated during experiments.

AI_NPC_System/expressive_interjection_bundle/
  Current pre-generated Fish Speech interjection bundle used before FastTrack text audio.

AI_NPC_System/archive/
  Legacy manifests, old TTS style examples, and deprecated local-only audio pools.

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

FastTrack realtime TTS is not part of the current default run. Do not start Piper or StyleBERT for the main CREDO path. Piper and StyleBERT scripts remain only as legacy experiments.

Run the Open-LLM-VTuber CREDO integration after the LLM and Fish Speech servers are up:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

For a SlowTrack-only ablation run that skips FastTrack analysis, FastTrack text, FastTrack TTS, and FastTrack motion, do not start Piper. Use:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo_no_fasttrack.sh
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

CREDO's user-facing speech policy is English-only. Korean, Japanese, Chinese, or other multilingual viewer input may be understood as context, but FastTrack/SlowTrack/proactive/donation outputs should answer naturally in English and should not mention the language rule.

## Configuration

Change experiment components in:

```bash
nano AI_NPC_System/project_config.sh
```

Key variables:

```text
LOCAL_LLM_MODEL                  SlowTrack local LLM served name
LOCAL_LLM_BASE_URL               OpenAI-compatible local LLM endpoint
FAST_TRACK_ENABLED               1 by default; set 0 for SlowTrack-only ablation
FAST_TRACK_TTS_MODE              none/offline path; realtime FastTrack TTS is deprecated
FAST_TRACK_INLINE_CUES_ENABLED   0; do not put Fish bracket cues in spoken text
FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK 0 prevents default cute FastTrack TTS fallback
SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK 0 prevents wrong-voice SlowTrack fallback when Fish Speech fails
FAST_TRACK_AUDIO_CACHE_ENABLED   optional only for offline/prebuilt audio experiments
FISH_SPEECH_BASE_URL             SlowTrack TTS endpoint
FISH_SPEECH_REFERENCE_ID         voice reference id
OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME Live2D model name
CREDO_ENGLISH_ONLY_OUTPUT        1 keeps all audience-facing output in English
CREDO_LANGUAGE_POLICY            shared language rule appended to LLM prompts
SLOW_TRACK_SYSTEM_PROMPT         local LLM response policy
CREDO_MAX_COVER_BLOCKS           extra prebuilt cover blocks while SlowTrack waits
CREDO_ENABLE_EXTRA_COVER_AUDIO   enable expressive audio blocks
LATENCY_PREDICTOR_MODEL_FILE  generated artifact-backed kNN latency predictor
LOCAL_LLM_CUDA_VISIBLE_DEVICES   GPU1 for SlowTrack local LLM
FISH_SPEECH_CUDA_VISIBLE_DEVICES GPU0 for heavier SlowTrack Fish Speech
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

Generate the current pure-interjection Fish Speech audio bundle:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_interjection_audio_bundle.py --force
```

Build or refresh the persona-conditioned reaction bundle. This generates 600 short text reactions from the 4 emotion x 6 intent x 5 style-tag grid. Each cell samples 30 labeled GoEmotions/SWDA seed pairs and the local LLM filters/re-writes 5 persona-matched reactions. The runtime file stores only the selected reactions; full seed pairs are kept separately in `seed_provenance.json`.

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --skip-existing --seed-max-words 7 --seed-max-chars 70 --max-tokens 240
```

If offline audio is needed later, synthesize from the completed bundle with Fish Speech as a batch job rather than live FastTrack TTS.

See `AI_NPC_System/docs/persona_reaction_bundle.md` for the manifest schema and smoke-test commands.

Measure Fish Speech latency by text length for dynamic cover planning:

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_fish_speech_length_sweep.py --runs 2
```

Latency records are appended to `AI_NPC_System/latency_logs/events.jsonl`.
`AI_NPC_System/latency_logs/latest_summary.md` is a readable rolling summary.

## Current Limitation

FastTrack realtime TTS was tested and then removed from the main path. The default `live` stack starts Fish Speech, the local LLM, and Open-LLM-VTuber only. It uses the pre-generated Fish Speech persona bundle for FastTrack cover audio. Piper and StyleBERT remain as legacy scripts and can be tested with `AI_NPC_System/scripts/run_credo_stack.sh --profile live-piper`, but they are not required startup dependencies.

SlowTrack uses Fish Speech. CREDO serializes SlowTrack Fish requests because the GPU-heavy server is most stable with one long request at a time. `FISH_SPEECH_TIMEOUT=300` and `LOCAL_LLM_MAX_TOKENS=96` are the current runtime defaults to reduce client-side disconnects. If Fish Speech is cancelled, times out, or disconnects, CREDO suppresses Open-LLM-VTuber fallback TTS by default so the response does not suddenly switch to the wrong voice. Keep `SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=0` for voice-consistency experiments. If a temporary fallback is intentionally enabled, the emergency Edge voice is `en-US-JennyNeural`, not the child-like `en-US-AnaNeural`.

Project-owned voice samples, Fish Speech references, and the CREDO Live2D avatar/motions are tracked through explicit `.gitignore` exceptions. Large runtimes, virtual environments, model checkpoints, generated audio caches, and temporary experiment logs remain local-only.
