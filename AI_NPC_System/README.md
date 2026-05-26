# AI_NPC_System

CREDO's Open-LLM-VTuber integration and latency-cover research modules.

## Live Runtime

The 2026-05-26 live method prioritizes conversational responsiveness over
reference-voice similarity:

```text
chat buffer / idle trigger
  -> DistilBERT emotion + SetFit/SWDA response-act routing
  -> separated GoEmotions/SWDA dataset-pool retrieval
  -> Professor's Lab Maid runtime cover composition
  -> prebuilt StyleBERT short interjection+motion and/or StyleBERT language FastTrack
  || local LLM + StyleBERT SlowTrack/prefetch
```

StyleBERT-VITS2 `credo_voice_sample_en` is the active language TTS model.
Fish and CosyVoice2 live language synthesis remain excluded; the short
interjection wav bundle is also generated with StyleBERT to keep voice color
consistent.

## Main Files

```text
config.py                         Shared settings and defaults.
project_config.sh                 Active editable experiment profile.
fasttrack_router_v3.py            Emotion, intent, transition, and FAISS routing.
stylebert_vits2_client.py         StyleBERT-VITS2 audio generation for live speech.
slow_track.py                     OpenAI-compatible local LLM caller.
memory_store.py                   Lightweight recent-turn memory.
latency_observer.py               Module latency CSV/JSONL logging.
integrations/open_llm_vtuber/    Agent, config activation, Live2D/frontend glue.
fasttrack_assets/                 Prepared datasets, models, and text/audio artifacts.
```

## FastTrack Dataset Pool

`fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`
is the active language FastTrack source. It is not a static persona reaction
manifest. It keeps GoEmotions and SWDA filtered pools separate, then router v3
searches and composes the Professor's Lab Maid FastTrack line at runtime.
The selected response act is sampled from SWDA transition evidence instead of
being copied from the incoming user intent. `QUESTION` is intentionally excluded
from FastTrack response acts; if transition evidence would select a question,
the next allowed response act is used instead.
`fasttrack_assets/audio/expressive_interjection_bundle/manifest.json` supplies
`65` short StyleBERT interjection clips played with Live2D motion.

## Run

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/check_runtime_readiness.py
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

The live launcher runs startup warmup by default before accepting the first
turn: StyleBERT synthesizes one tiny wav, the local LLM completes one tiny
chat, and Open-LLM-VTuber's CREDO status route is touched. The same warmup
repeats after a supervised service restart. Use `--no-warmup` only for startup
debugging.

Open `http://127.0.0.1:12393` and use the `CREDO VTuber Mode` panel. The
current UI exposes three runtime modes (`YouTube Live`, `Virtual Broadcast`,
`1:1 Chat`), six `Experiment cases`, and the manual factor buttons
(`Contextual mapping`, `Scheduling architecture`). For participant trials, use
`case_1_grounded_serial` through `case_6_slowtrack_only`, then click
`Start Scenario` to run the shared two-and-a-half-minute `Graduate School Survival Counseling Center` virtual
broadcast scenario. Short chat events are buffered for later batch reaction;
long counseling questions are routed as priority donations with a 20-second
overlay and donation SFX. The selected `experiment_run_id`,
`experiment_factor`, and `scenario` are recorded with the runtime factors.
`LLM Settings` can add a broadcast direction prompt for topic steering. Labeled latency rows are
appended to `AI_NPC_System/latency_logs/module_events.csv`.

Current usage details are documented in:

```text
AI_NPC_System/docs/credo_live_usage_guide.md
```

## Historical TTS Artifacts

Fish Speech is not started for the default live run. Piper, Edge TTS,
CosyVoice2, and non-active Fish assets remain historical comparison material.
Do not insert bracketed Fish style tags into spoken text.
