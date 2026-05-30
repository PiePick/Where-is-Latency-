# CREDO User Study Protocol Draft

작성 기준: 2026-05-27 KST

## Objective

같은 StyleBERT-VITS2 언어 TTS 환경에서 확률적 전이 기반 FastTrack과
사전 음성화된 FastTrack 반응이 AI VTuber의 체감 응답성, 대화 자연스러움,
모션 적합성을 개선하는지 Serial 조건을 기준으로 비교한다.

## Conditions

Use the VTuber overlay `Experiment cases` section to set the condition before
each two-and-a-half-minute video trial. All cases use the same `shared_2m30` Graduate
Lab Maid Donation Reality Check scenario. Short chat lines are mainly
reaction comments; longer counseling questions are injected as donation events
and should be answered before the surrounding chat batch.

| Case | Factor | Scenario | Component | Selection | Scheduling |
| --- | --- | --- | --- | --- | --- |
| `case_1_grounded_serial` | `contextual_mapping` | `shared_2m30` | `both` | `grounded` | `serial` |
| `case_2_emotion_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `emotion_only` | `serial` |
| `case_3_intent_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `response_act_only` | `serial` |
| `case_4_neutral_random_serial` | `contextual_mapping` | `shared_2m30` | `both` | `neutral_random` | `serial` |
| `case_5_slowtrack_only` | `scheduling_architecture` | `shared_2m30` | `none` | `none` | `serial` |

Parallel scheduling is retained in the codebase for later architecture work,
but it is not part of the active recording protocol and is not exposed in the
current browser panel. Current scenario runs should log `scheduling_mode=serial`.

The previous dynamic A/B/C assembly and static random condition are excluded
from this primary study. The fixed FastTrack path uses one language reaction
plus viewer-emotion Live2D expression/body motion in every Contextual Mapping
condition; standalone nonverbal interjection audio is sealed. In `Neutral Random`,
the language reaction uses the context-free control path without emotion or
intent grounding. In Case 5, FastTrack is
disabled and the trial waits for the SlowTrack response. Condition order should
be counterbalanced.

Current dataset evidence text is kept persona-neutral and the Professor's Lab
Maid style is applied by the runtime cover composer.

## Prompt Set

Use comparable English chat prompts covering positive questions, negative
personal reports, ambiguous questions, neutral information, directives, and
expressive reactions. The same ordered set must be used for all conditions.
VTuber-mode trials may additionally use a fixed batch of virtual-chat messages.

## Ratings

Rate each condition on a 1-5 Likert scale:

| Item | Question |
| --- | --- |
| Q1 | The character began reacting quickly. |
| Q2 | The system did not feel stalled. |
| Q3 | The first reaction suited my message. |
| Q4 | The reaction and main speech formed a coherent turn. |
| Q5 | The Live2D motion matched the spoken emotion. |
| Q6 | The interaction felt like a continuous VTuber broadcast. |
| Q7 | The latency was acceptable. |

## Logged Fields

```text
participant_id, experiment_run_id, experiment_factor, scenario
component_mode, selection_policy, scheduling_mode, trial_index, input_source, input_text
emotion, user_intent, sampled_response_act, style_tag, keyword_echo_used
fasttrack_analysis_ms, time_to_first_audio_ms, slowtrack_llm_ms
slowtrack_tts_ms, turn_total_ms
```

System-side event rows are taken from
`AI_NPC_System/latency_logs/module_events.csv`. In the current protocol,
`selection_policy` records the mapping basis and `keyword_echo_used` should be
false.

## Exclusion Rules

- StyleBERT TTS server failure or silent audio payload.
- websocket disconnection or browser playback failure.
- local LLM endpoint unavailable during a trial.
- participant deviates from the fixed prompt/batch procedure.
- experiment condition was not correctly selected before the trial.

Fish/Cosy/Edge latency is background evidence for engine selection and is not
a participant condition in the current primary study. Before participant runs,
use `AI_NPC_System/scripts/benchmark_experiment_factors.py` for module
baselines and scheduling simulation, then use live CSV rows for reported
results.
