# CREDO Open-LLM-VTuber Runtime Flow

작성 기준: 2026-05-27 KST

## Platform Boundary

Open-LLM-VTuber supplies the web UI, websocket conversation loop, Live2D
playback/lip-sync, and the runtime integration surface. CREDO adds a custom
agent for FastTrack routing, asynchronous SlowTrack generation, chat buffering,
motion actions, memory, and latency logging.

## Active Live Pipeline

```text
direct text / virtual broadcast chat / YouTube chat buffer / idle turn
  -> CREDO agent
     -> FastTrack classifier and selector
        DistilBERT emotion
        SetFit SWDA incoming-intent classifier
        SWDA transition-weighted response-act sampling, excluding QUESTION
        separated GoEmotions/SWDA dataset-pool retrieval
        runtime Professor's Lab Maid cover composition
        spaCy keyword metadata/source bias; spoken echo prefix paused
     -> selected mapping basis:
        grounded / emotion only / intent only / context-free control
     -> selected reaction StyleBERT TTS + viewer-emotion Live2D motion
     || SlowTrack local LLM + StyleBERT TTS audio preparation
  -> SlowTrack playback
  -> during playback: accumulate chat and prefetch next idle SlowTrack
```

If the next SlowTrack audio is already ready when the current utterance ends,
the agent sends it directly rather than adding unnecessary FastTrack filler.
When new chat has accumulated, the next turn uses the chat batch before an
idle-prefetched monologue.

## Runtime Experiment Controls

The VTuber overlay switches runtime mode and experimental policy parameters; it
does not swap the underlying conversation stack.

| Control | Values |
| --- | --- |
| Runtime mode | YouTube Live, Virtual Broadcast, 1:1 Chat |
| Experiment cases | `case_1_grounded_serial`, `case_2_emotion_only_serial`, `case_3_intent_only_serial`, `case_4_neutral_random_serial`, `case_5_slowtrack_only` |
| Scenario playback | Shared `shared_2m30` Lab Maid Donation Reality Check scenario with `Start Scenario` / `Stop Scenario` |
| Contextual mapping | Grounded, Emotion Only, Intent Only, Context-Free |
| Scheduling architecture | Serial generation, No FastTrack |

Each latency event is labeled with these values in
`AI_NPC_System/latency_logs/module_events.csv`.

The case buttons set `experiment_run_id`, `experiment_factor`, `scenario`,
`component_mode`, `selection_policy`, and `scheduling_mode` together. Manual
factor buttons are retained for debugging.

`Start Scenario` injects short reaction chats into the VTuber chat buffer and
longer counseling questions through the donation route. Donation events show a
20-second overlay, play the local donation SFX, and enter the conversation with
priority before the next buffered-chat summary turn.

The `neutral_random` compatibility value now represents a context-free
FastTrack control: FastTrack remains enabled, but emotion/response-act evidence
is not used as the grounding condition. `No FastTrack` is the SlowTrack-only
absolute control and is recorded as `component_mode=none`,
`scheduling_mode=serial`.

## What Changed

The old live path played a prebuilt Fish Speech wav selected from the persona
bundle and attempted a high-quality Fish SlowTrack. The latter measured roughly
`49.7 s` for a 20-word line (`51.1 s` total turn), so the live design now uses
StyleBERT-VITS2 for language FastTrack and SlowTrack.

- Standalone interjection playback is sealed for the current experiment set.
- Static persona text manifests are disabled in the active language path.
- The active language source is the separated GoEmotions/SWDA dataset pool.
- `spaCy` keywords remain available for metadata/source bias, but the spoken
  keyword echo prefix is paused for the current study.
- If SlowTrack remains pending, the active path avoids standalone nonverbal
  filler and keeps the viewer-emotion expression layer on the speaking response.
- Fish live synthesis is excluded; the active interjection bundle is generated
  with StyleBERT but remains archived while playback is sealed.
- Targeted viewer-facing SlowTrack/proactive speech may address one focused
  viewer as `<nickname> kyo-shu-zin-sa-ma`; multi-chat summaries should address
  the room without listing every nickname.

## Active Services

```text
Local LLM:       http://127.0.0.1:8001/v1   qwen2.5:7b
StyleBERT-VITS2: http://127.0.0.1:5000
Open-LLM-VTuber: http://127.0.0.1:12393
Language TTS:    StyleBERT-VITS2 credo_voice_sample_en
Interjections:   sealed; archived generated wav bundle only
```

The default `live` profile starts StyleBERT-VITS2, local LLM, and
Open-LLM-VTuber. It does not start Fish Speech or Piper.

## Key Source Files

```text
AI_NPC_System/project_config.sh
AI_NPC_System/stylebert_vits2_client.py
AI_NPC_System/fasttrack_router_v3.py
AI_NPC_System/fast_track_engine.py
AI_NPC_System/slow_track.py
AI_NPC_System/latency_observer.py
AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py
AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py
AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js
AI_NPC_System/docs/credo_live_usage_guide.md
```

## Run

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45
```

In the overlay select the runtime mode and experimental factor combination.
Observe current module latency in `AI_NPC_System/latency_logs/module_events.csv`.
