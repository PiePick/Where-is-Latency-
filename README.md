# CREDO Latency-Cover VTuber Prototype

CREDO is a research prototype for hiding perceived LLM/TTS latency in an AI VTuber or virtual NPC. The current platform is Open-LLM-VTuber with a Python-side CREDO agent. Audience-facing speech and runtime scenario prompts are English by default.

Team handoff and machine setup notes live in [`TEAM_CODEX_PROMPT.md`](TEAM_CODEX_PROMPT.md).
Codex-based dependency and open-source runtime recovery steps live in
[`CODEX_SETUP.md`](CODEX_SETUP.md).

## Current Handoff Snapshot

The current research direction is **latency cover by probabilistic FastTrack
selection and asynchronous SlowTrack scheduling**.

Current decisions:
- Audience-facing output defaults to English, with scenario-specific language
  steering allowed through `broadcast_direction`.
- Live language TTS uses the local StyleBERT-VITS2 model
  `credo_voice_sample_en` for both FastTrack language reactions and SlowTrack
  persona speech.
- Fish Speech is not used for live language synthesis. The active short
  interjection wav bundle is now generated with the same StyleBERT voice.
- FastTrack language reactions are selected from separated GoEmotions/SWDA
  dataset evidence pools, covered with the current Professor's Lab Maid persona
  rule, and synthesized in real time; they are not selected as prebuilt language
  wav files.
- The active recording plan is six two-and-a-half-minute video cases with one shared
  scenario: four serial contextual-mapping cases, one grounded parallel case,
  and one SlowTrack-only case.

Active bundle files:
- `AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`
  is the runtime language evidence pool. It keeps GoEmotions and SWDA text
  sources separated, filters out over-specific or unsafe source text, and
  excludes `QUESTION` from FastTrack output response acts while preserving it as
  an incoming intent label.
- `AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/manifest.json`
  is the runtime nonverbal bundle. It contains `65` prebuilt wav files with
  Live2D motion metadata.
- `AI_NPC_System/reports/intent_transition_matrix_from_swda.*` stores the SWDA
  user-intent to response-act transition evidence used for probabilistic
  response selection.

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
       prebuilt nonverbal audio + Live2D motion
       separated dataset-pool retrieval + persona cover + StyleBERT FastTrack speech
  -> CREDO SlowTrack
       local OpenAI-compatible LLM
       StyleBERT-VITS2 speech
  -> Live2D avatar response with Idle/Talk/lip-sync preserved for speech
```

The old Unity project and WinTTS prototype were removed. The active runtime is now:

```text
AI_NPC_System/                 CREDO Python code, FastTrack assets, reports, docs, scripts
reaction_sources/              source datasets and merged reaction evidence
vendor/open-llm-vtuber/        VTuber UI/runtime platform
vendor/Style-Bert-VITS2/       live language TTS runtime
vendor/fish-speech/            archived Fish Speech experiments
```

## Important Files

```text
AI_NPC_System/project_config.sh
  Single place to change LLM, TTS, voice, prompt, reaction, and runtime settings.

AI_NPC_System/integrations/open_llm_vtuber/
  CREDO agent adapter for Open-LLM-VTuber.

AI_NPC_System/fasttrack_assets/models/setfit_swda_intent_minilm_optimized/
  Selected SWDA SetFit intent model.

AI_NPC_System/reports/setfit_intent_evaluation.xlsx
  Validation/test report for the SetFit intent model.

AI_NPC_System/fasttrack_assets/datasets/prepared_fasttrack_data/
  Preprocessed GoEmotions and SWDA coarse-label data.

AI_NPC_System/latency_logs/
  Local-only JSONL, CSV, and Markdown latency records generated during experiments.

AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/
  Current prebuilt StyleBERT short interjection bundle used before FastTrack text audio.

AI_NPC_System/fasttrack_assets/
  Canonical FastTrack datasets, SetFit models, separated reaction text pools, and nonverbal audio.

AI_NPC_System/archive/
  Legacy manifests, old TTS style examples, deprecated local-only audio pools, resolved notes, and old one-off repair tools.

AI_NPC_System/VoiceSample/
  Project voice source used for CREDO voice reference preparation.

AI_NPC_System/integrations/open_llm_vtuber/live2d_models/
  Project Live2D avatar and motion assets copied into Open-LLM-VTuber.

vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en/
  Current StyleBERT-VITS2 language voice model.

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

Start the StyleBERT-VITS2 TTS server:

```bash
AI_NPC_System/scripts/start_stylebert_vits2_server.sh
```

Run the Open-LLM-VTuber CREDO integration after the LLM and StyleBERT servers are up:

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

The usual live launcher starts the required stack in order:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

The launcher now warms up the cold path by default after each service becomes
healthy: it sends one real StyleBERT `/voice` request, one local LLM
`/chat/completions` request, and one Open-LLM-VTuber CREDO status request before
entering the monitor loop. Use `--no-warmup` only for debugging a startup issue.

For current live operation details, see:

```text
AI_NPC_System/docs/credo_live_usage_guide.md
```

Open the UI:

```text
http://localhost:12393
```

The Open-LLM-VTuber page now includes a small `CREDO VTuber Mode` panel in the
browser. It exposes `YouTube Live`, `Virtual Broadcast`, and `1:1 Chat`
runtime modes plus the current `Contextual mapping x Scheduling architecture`
experiment controls: Grounded/Emotion Only/Intent Only/Neutral Random by
Parallel/Serial/No FastTrack. Use `Experiment cases` for participant videos:
`case_1_grounded_serial`, `case_2_emotion_only_serial`,
`case_3_intent_only_serial`, `case_4_neutral_random_serial`,
`case_5_grounded_parallel`, and `case_6_slowtrack_only`. `Start Scenario`
runs the shared two-and-a-half-minute `Graduate School Survival Counseling Center` virtual broadcast scenario
for the selected case. Scenario donations show a 20-second broadcast overlay,
play the local donation SFX, and are answered before buffered reaction chat.
`LLM Settings` accepts an operator broadcast direction prompt, and `Donation`
queues the same priority donation-style reaction in Virtual Broadcast mode.

CREDO's default user-facing speech policy is English. Runtime scenario
`broadcast_direction` should stay in English for the current participant videos.

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
FAST_TRACK_TTS_MODE              stylebert_vits2 in the active live profile
FAST_TRACK_INLINE_CUES_ENABLED   0; do not put Fish bracket cues in spoken text
FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK 0 prevents default cute FastTrack TTS fallback
FAST_TRACK_AUDIO_CACHE_ENABLED   optional only for offline/prebuilt audio experiments
FAST_TRACK_DATASET_POOL_FILE     active separated GoEmotions/SWDA text pool
STYLEBERT_VITS2_BASE_URL         live language TTS endpoint
OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME Live2D model name
CREDO_ENGLISH_ONLY_OUTPUT        1 keeps all audience-facing output in English
CREDO_LANGUAGE_POLICY            shared language rule appended to LLM prompts
SLOW_TRACK_SYSTEM_PROMPT         local LLM response policy
CREDO_MAX_COVER_BLOCKS           extra prebuilt cover blocks while SlowTrack waits
CREDO_ENABLE_EXTRA_COVER_AUDIO   enable expressive audio blocks
LATENCY_PREDICTOR_MODEL_FILE  generated artifact-backed kNN latency predictor
LOCAL_LLM_CUDA_VISIBLE_DEVICES   GPU1 for SlowTrack local LLM
```

## Data and Model Tasks

Rebuild the reaction dataset:

```bash
vendor/open-llm-vtuber/.venv/bin/python reaction_sources/scripts/build_reaction_dataset.py
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

Generate the current pure-interjection StyleBERT audio bundle:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_interjection_audio_bundle.py --engine stylebert_vits2 --synthesize --force
```

Build and validate the active separated Professor's Lab Maid dataset pool from
the filtered GoEmotions/SWDA sources:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_fasttrack_dataset_pools.py
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/validate_fasttrack_dataset_pool.py
```

If offline audio is needed later, synthesize it as a batch job rather than live
FastTrack TTS.

See `AI_NPC_System/docs/persona_reaction_bundle.md` for the active dataset-pool
schema and smoke-test commands.

Historical only: measure Fish Speech latency by text length if reproducing the
rejected high-latency TTS baseline:

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/benchmark_fish_speech_length_sweep.py --runs 2
```

Latency records are appended to `AI_NPC_System/latency_logs/events.jsonl`.
`AI_NPC_System/latency_logs/latest_summary.md` is a readable rolling summary.

## Current Limitation

StyleBERT-VITS2 is fast enough for the current live path, but it is not a
high-fidelity voice clone. Fish Speech and CosyVoice2 remain useful comparison
systems, yet their live latency was too large for the primary VTuber condition.
The project therefore evaluates whether probabilistic FastTrack mapping and
parallel SlowTrack scheduling improve perceived continuity under a practical
low-latency TTS engine.

Cold model start should not be mixed with warm turn latency. Browser-side first
audible onset also needs to be separated from server-side payload dispatch.

Project-owned voice samples, Fish Speech references, and the CREDO Live2D avatar/motions are tracked through explicit `.gitignore` exceptions. Large runtimes, virtual environments, model checkpoints, generated audio caches, and temporary experiment logs remain local-only.
