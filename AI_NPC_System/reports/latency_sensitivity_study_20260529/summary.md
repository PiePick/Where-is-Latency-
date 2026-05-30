# CREDO Latency Sensitivity Simulation Study

- Source log: `/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`
- Source window start: `2026-05-29T03:36:00+09:00`
- Source rows used: `508`
- Simulation conditions: `120`
- Repetitions per condition: `500`
- Turns per repetition: `8`
- Simulated turn rows: `480000`
- Seed: `2026052902`

## What This Data Means

This is a sensitivity simulation based on measured module latency distributions. Each row samples real measured FastTrack analysis, prebuilt audio lookup, SlowTrack LLM, SlowTrack TTS, donation readout, and frontend overhead distributions, then applies explicit experimental condition multipliers. It is suitable for paper planning and computational simulation results, but final perceptual latency still needs browser audible-onset timing.

## Headline Conditions

| Scenario | FastTrack median first response ms | SlowTrack-only median first response ms | Median improvement ms | Reduction | Median hidden latency ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current prompt / local browser / donation mix | 76.0 | 2330.6 | 2254.6 | 96.7% | 2400.0 |
| Heavy context / local browser / donation mix | 76.5 | 4597.7 | 4521.1 | 98.3% | 4739.0 |
| Stress context / capture stress / donation mix | 195.4 | 6318.7 | 6123.3 | 96.9% | 6379.3 |

## Generated Files

| File | Contents |
| --- | --- |
| `simulated_turns_wide.csv` | One row per simulated turn. All module latencies are columns. |
| `condition_summary.csv` | Summary statistics for every condition and metric. |
| `module_summary.csv` | Module-level latency summary by condition. |
| `assumptions.json` | Full factor definitions and simulation assumptions. |

## Recommended Paper Wording

Use the phrase `empirical bootstrap sensitivity simulation from recorded module logs`. Do not describe this as a participant result or browser audible-onset result.
