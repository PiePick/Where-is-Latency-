# Open-LLM-VTuber Integration

This integration keeps Open-LLM-VTuber as the UI, WebSocket, Live2D, lip-sync,
and supported TTS platform while CREDO provides the latency-cover agent.

## Current Runtime

```text
input/chat buffer
  -> DistilBERT emotion + SWDA response-act sampling
  -> optional spaCy keyword extraction for metadata
  -> persona manifest text from the selected mapping basis
  -> prebuilt StyleBERT short interjection+motion + StyleBERT language FastTrack
  || local LLM + StyleBERT SlowTrack prefetch
  -> continuous VTuber output loop
```

The bundled Open-LLM-VTuber default template still supports `edge_tts`, but
CREDO's active live route uses `stylebert_vits2` for language FastTrack and
SlowTrack. Prebuilt audio remains active only for short StyleBERT interjections
and their Live2D motion actions.

## Apply Integration

Source files in this directory are copied/patched into the vendored runtime:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
```

Generated runtime targets include:

```text
vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py
vendor/open-llm-vtuber/characters/credo_latency_cover.yaml
vendor/open-llm-vtuber/conf.credo.yaml
vendor/open-llm-vtuber/conf.yaml
```

## Live2D Outputs

Each spoken response can include expression and `credo_motion_profile:*`
actions. Energetic/playful responses trigger stronger talk motion; steady/low
responses remain restrained while lip-sync controls the mouth. Short pure
interjection wav files are delivered from the prebuilt StyleBERT bundle with
their motion action.

## Experiment Controls

The VTuber panel exposes two primary switchable factors:

```text
Experiment cases:       case_1_grounded_serial /
                        case_2_emotion_only_serial /
                        case_3_intent_only_serial /
                        case_4_neutral_random_serial /
                        case_5_slowtrack_only
Scenario playback:      shared_2m30 Lab Maid Donation Reality Check
                        with Start Scenario / Stop Scenario
Contextual mapping:      Grounded / Emotion Only / Intent Only / Neutral Random
Scheduling architecture: Serial / No FastTrack
```

The primary study should use the case buttons because they set `run_id`,
`factor`, `scenario`, and the runtime factors in one operation. The visible
case buttons use the same `shared_2m30` scenario. Short chat events are
buffered for later batch reaction, while long counseling questions are routed as
priority donations with a 20-second overlay and local SFX. The corrected
mapping control is `Neutral random`, which keeps FastTrack enabled and samples
from Neutral candidates. Case 5 is `SlowTrack Only`: FastTrack is disabled, so
contextual mapping is effectively `None`.

Parallel scheduling remains in the codebase for later async-prefetch work, but
the current experiment keeps scenario execution on `scheduling_mode=serial` and
does not expose Parallel or Case 5 in the browser panel.

The overlay also exposes `LLM Settings` for an operator broadcast direction
prompt. That text is added to VTuber idle, batch chat, monologue, and donation
prompts without replacing the configured persona.

Forced persona suffixes such as `peko` are not requested by the prompts and are
stripped before display/TTS if they remain in legacy manifest text.
