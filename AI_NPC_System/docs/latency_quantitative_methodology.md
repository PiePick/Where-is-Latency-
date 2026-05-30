# CREDO Latency Quantitative Methodology

이 문서는 논문용 정량 latency 분석을 위해 어떤 로그를 남기고, 어떤 지표를
계산하며, 어떤 row를 제외할지 정의한다. 주관 설문 결과와 결합하기 전의
객관 로그 분석 기준이다.

## Active Log Session

Current session stem:

```text
paper_latency_20260529_000308
```

Runtime output paths:

```text
AI_NPC_System/latency_logs/paper_latency_20260529_000308.events.jsonl
AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv
AI_NPC_System/latency_logs/paper_latency_20260529_000308.latest_summary.md
AI_NPC_System/latency_logs/paper_latency_20260529_000308.session.json
```

The CSV is the primary quantitative file. JSONL preserves full event metadata,
and the Markdown file is only for live inspection.

## Experimental Conditions

The current paper run uses serial scheduling only. Parallel scheduling remains a
future architecture condition but is not part of the active recording protocol.

| Case | FastTrack | Mapping | Scheduling | Purpose |
| --- | --- | --- | --- | --- |
| Case 1 | on | Grounded | Serial | Emotion plus SWDA response-act mapping |
| Case 2 | on | Emotion Only | Serial | Emotion-only lookup ablation |
| Case 3 | on | Intent Only | Serial | SWDA response-act-only lookup ablation |
| Case 4 | on | Neutral Random | Serial | Context-free FastTrack baseline |
| Case 6 | off | None | Serial | SlowTrack-only dead-air baseline |

All conditions should use the same scenario and the same model/runtime settings
except for the intended experimental factor.

## Logged Variables

`module_events.csv` records one row per measured runtime event. The most
important columns for analysis are:

| Column | Meaning |
| --- | --- |
| `ts_local` | Local timestamp for ordering and troubleshooting |
| `experiment_run_id` | Case label such as `case_1_grounded_serial` |
| `experiment_factor` | High-level factor label |
| `scenario` | Scenario identifier |
| `component_mode` | FastTrack component mode, usually `both` or `none` |
| `selection_policy` | `grounded`, `emotion_only`, `response_act_only`, `neutral_random`, or `none` |
| `scheduling_mode` | Current active study should be `serial` |
| `runtime_mode` | `virtual_broadcast`, `youtube_live`, or `direct_chat` |
| `module` | Coarse module bucket for grouping |
| `stage` | Fine-grained measured stage |
| `elapsed_ms` | Measured duration in milliseconds |
| `engine` | Runtime engine, when available |
| `emotion` | DistilBERT/GoEmotions coarse label, when available |
| `intent` | Incoming intent label, when available |
| `response_act` | System response act selected through SWDA transition mapping |
| `cache_hit` | Whether prebuilt audio/cache was used |
| `audio_path` | Selected audio file path, when applicable |
| `char_len`, `word_count` | Text length controls |

## Objective Metrics

Report the following descriptive statistics per condition and per module:

| Metric | Definition |
| --- | --- |
| `n` | Number of valid rows used |
| `median_ms` | Primary robust central tendency |
| `p25_ms`, `p75_ms` | Interquartile range |
| `p95_ms` | Upper-tail latency, useful for perceived stalls |
| `mean_ms` | Secondary descriptive mean |
| `min_ms`, `max_ms` | Range for sanity checking |

Primary module groups:

| Module | Interpretation |
| --- | --- |
| `experiment_config` | Operator condition changes |
| `vtuber_runtime` | Mode start/stop lifecycle |
| `virtual_chat` | Chat buffering |
| `donation_readout` | Donation TTS readout path |
| `fasttrack_analysis` | Emotion/intent/router analysis |
| `fasttrack_audio` | Prebuilt FastTrack audio lookup/dispatch |
| `slowtrack_llm` | Main LLM generation latency |
| `slowtrack_tts` | Main TTS synthesis latency |
| `vtuber_total` or `turn_total` | End-to-end server-side turn timing, if emitted |

For the paper, separate:

1. Server-side computational latency.
2. First audible response timing, if browser-side timing is available.
3. Cold-start latency, which must not be mixed with warm experimental turns.

## Exclusion Rules

Exclude rows from quantitative analysis when any of the following is true:

1. The run happened before all servers were warmed up.
2. `experiment_run_id` is empty or does not match the intended case.
3. The row belongs to operator setup, manual debugging, failed startup, or route
   probing rather than the recorded scenario.
4. `scheduling_mode` is not `serial` for the current paper run.
5. The scenario differs from the shared recording scenario.
6. The row was produced after a crash, reload, or browser reconnect that changed
   the condition mid-run.

Keep excluded raw rows in the source log. Do not delete them; filter during
analysis.

## Subjective Survey Mapping

Objective latency is interpreted together with the questionnaire:

| Construct | Questions | Expected use |
| --- | --- | --- |
| Perceived Latency | q1, q2, q3 | Main perceived waiting-time outcome |
| Conversational Naturalness | q4, q5 | Whether flow felt like a broadcast dialogue |
| Reaction Appropriateness | q6, q7, q8 | Whether FastTrack reactions matched context |
| Social Presence | q9, q10 | Whether the VTuber felt responsive and present |
| Character Appeal | q11, q12 | Whether latency cover preserved persona appeal |
| Engagement | q13, q14 | Whether participants wanted to keep watching |
| Final Preference | q15, q16, q17 | Overall comparison across videos |

For reverse-coded questions, invert before aggregation. Use the same participant
order table used for video counterbalancing.

## Analysis Plan

1. Group objective rows by `experiment_run_id`, `selection_policy`,
   `scheduling_mode`, `module`, and `stage`.
2. Compute median, IQR, p95, mean, min, and max.
3. Confirm that Case 1-4 have FastTrack rows and Case 6 does not.
4. Compare subjective Likert outcomes across cases with a within-subject test.
   If normality is not defensible, use Friedman tests with paired post-hoc
   Wilcoxon signed-rank tests and Holm correction.
5. Interpret objective latency and subjective perceived latency separately.
   A condition can have similar physical latency but different perceived
   waiting-time ratings.

## Commands

Create a new session:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/start_latency_log_session.py --update-config
```

Start the runtime after the session is set:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45
```

Watch live rows:

```bash
tail -f AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv
```

Summarize the session after recording:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/summarize_latency_session.py --session-stem paper_latency_20260529_000308
```

Output summary:

```text
AI_NPC_System/reports/latency_quantitative_paper_latency_20260529_000308/summary.md
AI_NPC_System/reports/latency_quantitative_paper_latency_20260529_000308/module_summary.csv
```
