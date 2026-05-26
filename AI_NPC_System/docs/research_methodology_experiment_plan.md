# CREDO Research Methodology And Experiment Plan

작성 기준: 2026-05-27 KST

## Research Question

장문의 LLM 응답을 기다리는 VTuber 방송에서, 데이터셋 기반의 짧은 실시간
반응과 다음 발화 비동기 준비가 체감 응답성과 대화 연속성을 개선하는가?

고품질 voice-clone TTS의 30-50초대 지연은 숨길 수 있는 지연이 아니므로,
현재 연구는 StyleBERT-VITS2 실시간 합성을 고정하고, 확률적 전이 기반
FastTrack 매핑과 비동기 scheduling의 효과를 비교한다.

## Current Method

```text
incoming chat batch
  -> emotion: DistilBERT / GoEmotions four-way mapping
  -> user intent: SetFit model trained on SWDA coarse acts
  -> response act: sampled from SWDA adjacent-turn transition weights, excluding QUESTION
  -> optional keyword extraction: spaCy noun/verb context for analysis/logging
  -> reaction text: separated GoEmotions/SWDA pool retrieval
  -> runtime Professor's Lab Maid persona-cover composition
  -> FastTrack: prebuilt nonverbal interjection/motion + StyleBERT language TTS
  || SlowTrack: local LLM persona response + StyleBERT preparation
```

The active language source is not a static persona manifest. GoEmotions and
SWDA remain as separated filtered evidence pools, then the runtime combines the
selected evidence with the current Professor's Lab Maid cover rule. This keeps
the academic data provenance clear: emotion evidence, dialogue-act evidence,
and persona realization are independent stages. The current validated pool has
`1131` GoEmotions items and `1049` SWDA items; SWDA `QUESTION` is excluded from
FastTrack output response acts.

The previous dynamic A/B/C assembly idea is excluded from the primary method.
spaCy keyword extraction can remain as analysis metadata, but it must not
insert a separate echo utterance into the live FastTrack sequence.

## Experimental Factors

The overlay now changes two factors without changing the overall chat, LLM,
TTS, motion, or logging pipeline.

| Factor | Levels | Purpose |
| --- | --- | --- |
| Contextual Mapping | `grounded`, `emotion_only`, `response_act_only`, `neutral_random` | Compare Grounded, Emotion Only, Intent Only, and context-free lookup while keeping FastTrack enabled |
| Scheduling Architecture | `parallel`, `serial`, `no_fasttrack` | Compare async prefetch, serial FastTrack operation, and SlowTrack-only dead-air control |

The primary run set is not a full factorial grid. It uses six two-and-a-half-minute video
cases. All cases use the same `shared_2m30` Graduate School Survival
Counseling Center scenario so the recording content stays constant while the
system condition changes. The timeline mixes short reaction chat messages with
longer counseling questions delivered as donation events.

| Case | Factor | Scenario | Component | Selection | Scheduling |
| --- | --- | --- | --- | --- | --- |
| `case_1_grounded_serial` | `contextual_mapping` | `shared_2m30` | `both` | `grounded` | `serial` |
| `case_2_emotion_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `emotion_only` | `serial` |
| `case_3_intent_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `response_act_only` | `serial` |
| `case_4_neutral_random_serial` | `contextual_mapping` | `shared_2m30` | `both` | `neutral_random` | `serial` |
| `case_5_grounded_parallel` | `scheduling_architecture` | `shared_2m30` | `both` | `grounded` | `parallel` |
| `case_6_slowtrack_only` | `scheduling_architecture` | `shared_2m30` | `none` | `none` | `serial` |

`neutral_random` is retained as a compatibility name for the context-free
FastTrack control: it ignores emotion and response-act grounding while keeping
FastTrack enabled. Case 6 is the SlowTrack-only condition; it is represented in
logs as `component_mode=none` and `scheduling_mode=serial`, and its contextual
mapping is interpreted as `None` because FastTrack is disabled.

`grounded + parallel` is the default live candidate. The old
`edge-no-cover`, `edge-fasttrack`, and `edge-async-cover` presets remain only
as compatibility settings for older runs.

## Controlled Elements

| Element | Current fixed setting |
| --- | --- |
| TTS engine | StyleBERT-VITS2 for FastTrack and SlowTrack |
| voice/model | `credo_voice_sample_en` |
| SlowTrack persona / memory | identical across cells |
| chat input batches | reuse the same ordered input set |
| keyword echo | disabled in the primary study; spaCy keywords remain metadata only |

## Measurements

`AI_NPC_System/latency_logs/module_events.csv` must be used as the primary
runtime record. It records `experiment_run_id`, `experiment_factor`,
`scenario`, `component_mode`, `selection_policy`, and `scheduling_mode` on each
new module row. In the current design, `selection_policy` is the mapping-basis
factor.

The current persona rule is handled by the Professor's Lab Maid cover composer,
not by storing character-specific suffixes in dataset evidence text.

| Metric | Meaning |
| --- | --- |
| `fasttrack_analysis` | emotion, intent, response-act, text selection time |
| `fasttrack_interjection_dispatch` | prebuilt short StyleBERT interjection wav and motion sent; no live synthesis duration |
| `fasttrack_audio` | selected language FastTrack StyleBERT synthesis/delivery preparation |
| `fasttrack_keyword_echo` | should remain absent in the primary study |
| `slowtrack_llm` | persona LLM response generation |
| `slowtrack_tts` | StyleBERT synthesis or prepared-audio delivery |
| `turn_total` | turn completion time |
| time to first audible reaction | derived from event/browser timing |

Participant ratings should cover perceived speed, affective fit, turn
coherence, motion fit, and whether the system seemed stalled.

For a pre-study engineering check, run
`AI_NPC_System/scripts/benchmark_experiment_factors.py`. It separates direct
module measurements from scheduling simulation output. The measured
Any prior `nonverbal_tts` live-synthesis value is superseded because active interjections
are prebuilt StyleBERT wav files. Simulation is not a substitute for recorded
participant turns or browser first-audio timing.

## Interpretation Limits

- StyleBERT warm synthesis is usable for live language responses, but cold
  startup must be excluded from turn-level latency claims.
- spaCy keyword extraction is input-grounded analysis metadata, not an active
  echo utterance in the current primary study.
- Lightweight JSON memory supplies only recent context, not long-term semantic
  memory.
- Fish and CosyVoice measurements justify rejecting them from the primary live
  condition; they are not part of the claimed current runtime.
