# CREDO Research Methodology And Experiment Plan

작성 기준: 2026-05-29 KST

## Research Question

장문의 LLM 응답을 기다리는 VTuber 방송에서, 데이터셋 기반으로 사전
음성화된 짧은 반응이 체감 응답성과 대화 연속성을 개선하는가?

현재 가설은 FastTrack을 무조건 좋은 기능으로 가정하지 않고, 조건부로
효과적인 기능으로 평가한다.

| Hypothesis | Statement |
| --- | --- |
| H1 | 통합 FastTrack은 SlowTrack only보다 perceived latency를 낮춘다. |
| H2 | 통합 FastTrack은 단일 신호 기반 FastTrack보다 맥락 적합성과 자연스러움이 높다. |
| H3 | 사전 음성화된 FastTrack은 실시간 FastTrack TTS보다 첫 audible reaction의 안정성을 높인다. |
| H4 | 맥락 적합성이 낮은 FastTrack은 빠르더라도 어색함을 증가시킬 수 있다. |

고품질 voice-clone TTS의 30-50초대 지연은 숨길 수 있는 지연이 아니므로,
현재 연구는 FastTrack 언어 반응을 StyleBERT-VITS2로 사전 음성화하고,
확률적 전이 기반 FastTrack 매핑의 효과를 우선 비교한다. 비동기 parallel
scheduling은 구현 후보로 보존하지만, 1차 실험 UI에서는 노출하지 않는다.

## Current Method

```text
incoming chat batch
  -> emotion: DistilBERT / GoEmotions four-way mapping
  -> user intent: SetFit model trained on SWDA coarse acts
  -> response act: sampled from SWDA adjacent-turn transition weights, excluding QUESTION
  -> keyword extraction: spaCy noun/verb anchor for metadata/source bias only
  -> FastTrack: prebuilt StyleBERT wav lookup from separated GoEmotions/SWDA provenance
  -> viewer-emotion Live2D motion
  -> SlowTrack: local LLM persona/memory response + realtime StyleBERT preparation
```

The active language source is not a static persona corpus. GoEmotions and SWDA
remain as separated filtered evidence pools. A build-time step combines selected
evidence with the Professor's Lab Maid cover rule, synthesizes the result with
StyleBERT-VITS2, and stores the wav plus provenance metadata in a FastTrack audio
index. This keeps the academic data provenance clear: emotion evidence,
dialogue-act evidence, persona realization, and audio delivery are independent
stages. The current validated pool has `385` GoEmotions items and `244` SWDA
items; SWDA `QUESTION` is excluded from FastTrack output response acts.

The 2026-05-29 filtering pass removed unsuitable source lines before persona
realization. The exclusion protocol rejects proper nouns and platform/brand
references; topic-specific or niche lines about sports, games, films, politics,
news, phone-call closings, and external events; profanity, sexual, violent, or
hate wording; greetings and closings such as `hi`, `hello`, `yo`, `good
morning`, `how are you`, `what's up`, `long time no see`, `goodbye`, `thanks`,
and `cheers`; standalone fillers and laughter such as `ah`, `oh`, `hm`,
`haha`, `lol`, and emoji; lowercase fragments, malformed or unfinished
sentences; and utterances that require hidden context. A local LLM quality pass
then removes candidates that remain unsuitable as standalone FastTrack speech.
After filtering, the active bucket counts are GoEmotions `POSITIVE=141`,
`NEGATIVE=133`, `SURPRISE=23`, `NEUTRAL=88`, and SWDA `INFORM=199`,
`ACKNOWLEDGE=3`, `DIRECTIVE=18`, `EXPRESSIVE=14`, `REJECT=10`. A greeting and
closing scan reports `0` remaining hits.

Frequent repeated FastTrack lines are therefore not treated as a normal limit of
the combinatorial space. They indicate that the retrieval traversal is too
narrow, or that the post-filtered spoken candidates are low quality. Grounded
selection should traverse cross-pairs between GoEmotions evidence and SWDA
response-act evidence instead of pairing only same-rank hits. In Serial
conditions, a repeated candidate must not by itself suppress FastTrack, because
that would confound the Contextual Mapping factor with FastTrack presence.
Parallel conditions remain a deferred architecture candidate, but the active
study does not use them as a primary comparison.

The previous dynamic A/B/C assembly idea is excluded from the primary method.
spaCy keyword extraction is retained for metadata/source bias, but the spoken
keyword echo prefix is paused for the current primary study. It does not insert
a separate utterance or a separate audio block.

## Experimental Factors

The overlay now changes two factors without changing the overall chat, LLM,
TTS, motion, or logging pipeline.

| Factor | Levels | Purpose |
| --- | --- | --- |
| Contextual Mapping | `grounded`, `emotion_only`, `response_act_only`, `neutral_random` | Compare Grounded, Emotion Only, Intent Only, and context-free lookup while keeping FastTrack enabled |
| Scheduling Architecture | `serial`, `no_fasttrack` | Current recordings focus on Serial FastTrack operation and SlowTrack-only dead-air control. Async prefetch is preserved in code but held out of the active study UI. |

The primary UI now exposes five two-and-a-half-minute case buttons: Case 1
through Case 5. The active recording set uses Serial cases only.
All visible case buttons use the same
`shared_2m30` Lab Maid Donation Reality Check scenario so the
recording content stays constant while the system condition changes. The
timeline mixes short reaction chat messages with longer counseling questions
delivered as donation events.

현재 `shared_2m30` 시나리오 앵커는 다음과 같다.

| Time | Event | Payload role |
| --- | --- | --- |
| T+1s | donation | Playful criticism: the maid is cute, but her words land like a katana |
| T+38s | donation | High-intensity betrayal: a senior presented the viewer's lab-meeting idea as their own |
| T+78s | donation | High-intensity positive overinvestment: professors are described as unbearably adorable |
| T+108s | donation | Sudden status reveal: the professor is watching the stream right now |
| T+2.5s-144s | chat | English-only reaction chat that follows each donation's topic and emotional tone, with two recurring internet-style chatters using heavier `lol`/emoji reactions |

| Case | Factor | Scenario | Component | Selection | Scheduling |
| --- | --- | --- | --- | --- | --- |
| `case_1_grounded_serial` | `contextual_mapping` | `shared_2m30` | `both` | `grounded` | `serial` |
| `case_2_emotion_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `emotion_only` | `serial` |
| `case_3_intent_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `response_act_only` | `serial` |
| `case_4_neutral_random_serial` | `contextual_mapping` | `shared_2m30` | `both` | `neutral_random` | `serial` |
| `case_5_slowtrack_only` | `scheduling_architecture` | `shared_2m30` | `none` | `none` | `serial` |

`neutral_random` is retained as a compatibility name for the context-free
FastTrack control: it ignores emotion and response-act grounding while keeping
FastTrack enabled. Case 5 is the SlowTrack-only condition; it is represented in
logs as `component_mode=none` and `scheduling_mode=serial`, and its contextual
mapping is interpreted as `None` because FastTrack is disabled.

The active study baseline is Serial. `grounded + parallel` remains implemented
as a deferred architecture candidate, but the recording protocol should not use
it during the first study. The current browser panel no longer exposes the old
Parallel control or Case 5 button.
The old `edge-no-cover`, `edge-fasttrack`, and `edge-async-cover` presets remain
only as compatibility settings for older runs.

## Controlled Elements

| Element | Current fixed setting |
| --- | --- |
| TTS engine | Prebuilt StyleBERT-VITS2 wav for FastTrack; realtime StyleBERT-VITS2 for SlowTrack |
| voice/model | `credo_voice_sample_en` |
| SlowTrack persona / memory | identical across cells |
| chat input batches | reuse the same ordered input set |
| keyword echo | paused; spaCy keywords remain metadata/source-bias signals only |

## Measurements

Session-stamped files under `AI_NPC_System/latency_logs/` must be used as the
primary runtime record. They record `experiment_run_id`, `experiment_factor`,
`scenario`, `component_mode`, `selection_policy`, and `scheduling_mode` on each
new module row. In the current design, `selection_policy` is the mapping-basis
factor.

The current persona rule is handled by the Professor's Lab Maid cover composer,
not by storing character-specific suffixes in dataset evidence text. Generated
Targeted SlowTrack/proactive speech may address one focused viewer as
`<nickname> kyo-shu-zin-sa-ma`; multi-chat summaries should address the room
without listing every nickname.

| Metric | Meaning |
| --- | --- |
| `fasttrack_analysis` | emotion, intent, response-act, text selection time |
| `emotion_motion_payload` | viewer-emotion Live2D action payload; mouth remains audio lip-sync owned |
| `fasttrack_audio` | selected prebuilt language FastTrack wav lookup/delivery preparation |
| `fasttrack_keyword_echo` | absent as a separate row; spoken echo is paused, while disabled state is logged in FastTrack metadata |
| `slowtrack_llm` | persona LLM response generation |
| `slowtrack_tts` | StyleBERT synthesis or prepared-audio delivery |
| `turn_total` | turn completion time |
| time to first audible reaction | derived from event/browser timing |

Participant ratings use a 7-point Likert scale after each video, plus final
comparative choices after all videos. The six core constructs are:

| Construct | Items | Interpretation |
| --- | --- | --- |
| Perceived Latency | q1-q3 | Felt waiting time and whether the VTuber seemed stalled; q3 is reverse-coded |
| Conversational Naturalness | q4-q5 | Natural turn flow and live-broadcast plausibility |
| Reaction Appropriateness | q6-q8 | Whether the FastTrack reaction was meaningful, non-random, and connected to the following answer; q7 is reverse-coded |
| Social Presence | q9-q10 | Whether the VTuber seemed to listen and interact as a real broadcaster |
| Character Appeal | q11-q12 | Whether reactions strengthened character appeal |
| Engagement | q13-q14 | Immersion and willingness to keep watching |

Final comparison items are q15 for the most natural conversation flow, q16 for
the most awkward/uncomfortable video, and q17 for the video whose reaction best
matched context. Grounded FastTrack should be interpreted primarily through
q6-q8, q15, and q17. Prebuilt FastTrack latency-cover should be interpreted
through q1-q3 and browser first-audio timing. SlowTrack-only limitations should
be visible through low Perceived Latency scores and q16 selections.

For a pre-study engineering check, run
`AI_NPC_System/scripts/benchmark_experiment_factors.py`. It separates direct
module measurements from scheduling simulation output. The measured
Any prior `nonverbal_tts` or interjection-dispatch value is superseded because
standalone interjection playback is sealed. Simulation is not a substitute for
recorded participant turns or browser first-audio timing.

## Interpretation Limits

- FastTrack audio delivery should be measured separately from the offline
  StyleBERT prebuild step; SlowTrack realtime StyleBERT cold startup must still
  be excluded from turn-level latency claims.
- spaCy keyword extraction is input-grounded, but spoken keyword echo is paused
  so it does not introduce an extra lexical condition inside FastTrack output.
- Lightweight JSON memory supplies only recent context, not long-term semantic
  memory.
- Fish and CosyVoice measurements justify rejecting them from the primary live
  condition; they are not part of the claimed current runtime.
