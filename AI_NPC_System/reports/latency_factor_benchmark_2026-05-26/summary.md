# CREDO Low-Latency Factor Benchmark

Generated: 2026-05-26T13:04:31+09:00
Live language voice: `en-US-AnaNeural`

## Module Baselines

| Module | Median ms | Source |
| --- | ---: | --- |
| `fasttrack_analysis` | 10.788 | measured n=3 |
| `nonverbal_dispatch` | 0.000 | prebuilt interjection audio; pass measured route/dispatch delay when available |
| `language_fasttrack_tts` | 603.125 | measured n=3 |
| `slowtrack_llm` | 902.333 | measured n=3 |
| `slowtrack_tts` | 643.252 | measured n=3 |
| `slowtrack_playback_window` | 5736.000 | measured audio duration or explicit assumption |

## Simulation

Each row uses `100` deterministic jittered trials. Selection policy is expected to affect fit, not latency.
For `none`, selection policy is recorded but behaviorally inoperative. Parallel overlap is evaluated only where FastTrack is present.

| Components | Selection | Scheduling | First audio median ms | Slow ready median ms | Next wait median ms |
| --- | --- | --- | ---: | ---: | ---: |
| both | grounded | parallel | 11.099 | 1566.937 | 0.0 |
| both | grounded | serial | 11.14 | 1550.057 | 1550.057 |
| both | random | parallel | 11.267 | 1545.712 | 0.0 |
| both | random | serial | 11.061 | 1571.319 | 1571.319 |
| language_only | grounded | parallel | 622.022 | 1561.241 | 0.0 |
| language_only | grounded | serial | 622.179 | 1568.464 | 1568.464 |
| language_only | random | parallel | 597.067 | 1571.965 | 0.0 |
| language_only | random | serial | 615.973 | 1544.51 | 1544.51 |
| nonverbal_only | grounded | parallel | 11.321 | 1570.124 | 0.0 |
| nonverbal_only | grounded | serial | 10.735 | 1556.386 | 1556.386 |
| nonverbal_only | random | parallel | 11.109 | 1558.662 | 0.0 |
| nonverbal_only | random | serial | 11.315 | 1557.742 | 1557.742 |
| none | not_applicable | parallel | 1543.642 | 1543.642 | 1543.642 |
| none | not_applicable | serial | 1550.252 | 1550.252 | 1550.252 |
| none | not_applicable | parallel | 1545.205 | 1545.205 | 1545.205 |
| none | not_applicable | serial | 1554.862 | 1554.862 | 1554.862 |

## Interpretation Boundary

This is a module benchmark plus scheduling simulation, not a participant trial or browser playback measurement.
The nonverbal value is prebuilt interjection audio dispatch, not synthesis time; browser playback smoke is required for audible-onset claims.
Final study results must be calculated from live `latency_logs/module_events.csv` rows labeled with the active factor levels.
