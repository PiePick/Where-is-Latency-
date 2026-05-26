# CREDO Low-Latency Factor Benchmark

Generated: 2026-05-27T00:08:43+09:00
Live language TTS: `stylebert_vits2` / `credo_voice_sample_en`

## Module Baselines

| Module | Median ms | Source |
| --- | ---: | --- |
| `fasttrack_analysis` | 80.000 | assumption |
| `nonverbal_dispatch` | 0.000 | prebuilt interjection audio; pass measured route/dispatch delay when available |
| `language_fasttrack_tts` | 1200.000 | assumption |
| `slowtrack_llm` | 1500.000 | assumption |
| `slowtrack_tts` | 1800.000 | assumption |
| `slowtrack_playback_window` | 4200.000 | measured audio duration or explicit assumption |

## Simulation

Each row uses `100` deterministic jittered trials. Mapping basis is expected to affect fit, not latency.
For `none`, FastTrack remains enabled and the cover text uses the context-free control path without contextual lookup.

| FastTrack | Mapping level | Runtime selection | Scheduling | First audio median ms | Slow ready median ms | Next wait median ms |
| --- | --- | --- | --- | ---: | ---: | ---: |
| both | grounded | grounded | parallel | 79.927 | 3387.471 | 0.0 |
| both | grounded | grounded | serial | 80.749 | 3390.84 | 3390.84 |
| both | emotion_only | emotion_only | parallel | 79.87 | 3328.987 | 0.0 |
| both | emotion_only | emotion_only | serial | 81.155 | 3392.1 | 3392.1 |
| both | response_act_only | response_act_only | parallel | 80.515 | 3387.075 | 0.0 |
| both | response_act_only | response_act_only | serial | 82.17 | 3376.661 | 3376.661 |
| both | none | neutral_random | parallel | 80.239 | 3375.228 | 0.0 |
| both | none | neutral_random | serial | 80.983 | 3360.828 | 3360.828 |

## Interpretation Boundary

This is a module benchmark plus scheduling simulation, not a participant trial or browser playback measurement.
The nonverbal value is prebuilt interjection audio dispatch, not synthesis time; browser playback smoke is required for audible-onset claims.
Final study results must be calculated from live `latency_logs/module_events.csv` rows labeled with the active factor levels.
