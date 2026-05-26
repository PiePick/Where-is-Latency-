# CREDO Six Factor-Level Experiment Status - Corrected None Control

Date: 2026-05-27 00:09 KST

## Correction

The previous `None` interpretation was wrong.

`None` in the Contextual Mapping factor does **not** mean "disable FastTrack"
or "SlowTrack-only." It means:

```text
FastTrack stays enabled.
Do not use emotion or SWDA/response-act context for lookup.
Use the context-free FastTrack control without emotion or response-act grounding.
```

The earlier 2026-05-26 report was superseded for the `None` condition and was
removed during documentation cleanup.

## Correct Six Factor Levels

| Case | Factor | User-facing label | Correct target values | Runtime behavior |
|---:|---|---|---|---|
| 1 | Contextual Mapping | Grounded | `component_mode=both`, `selection_policy=grounded` | Uses emotion plus SWDA/response-act routing before persona candidate lookup. |
| 2 | Contextual Mapping | Emotion Only | `component_mode=both`, `selection_policy=emotion_only` | Ignores response-act lookup and chooses by detected emotion bucket. |
| 3 | Contextual Mapping | Intent Only | `component_mode=both`, `selection_policy=response_act_only` | Ignores emotion bucket and chooses by transitioned response act. |
| 4 | Contextual Mapping | None | `component_mode=both`, target `selection_policy=neutral_random` | Ignores emotion and response-act context; uses the context-free control path. |
| 5 | Scheduling Architecture | Parallel | `scheduling_mode=parallel` | Allows SlowTrack prefetch during current playback. |
| 6 | Scheduling Architecture | Serial | `scheduling_mode=serial` | Disables prefetch and waits for the serial generation path. |

## Current Runtime Mismatch

The current UI/runtime wiring does **not** yet implement the corrected `None`
condition.

Current implementation state:

- Frontend button: `No FastTrack`
- Payload currently sent by that button: `component_mode=none`
- Backend accepted component modes: `both`, `none`
- Backend accepted selection policies: `grounded`, `emotion_only`, `response_act_only`
- Agent behavior for `component_mode=none`: SlowTrack-only

That means the current `No FastTrack` control is a component ablation, not the
Contextual Mapping `None` control requested for this experiment.

To implement the corrected experiment, runtime needs a distinct mapping policy,
for example:

```text
component_mode=both
selection_policy=neutral_random
scheduling_mode=parallel | serial
```

The agent-side behavior should select through the context-free pool route,
equivalent to:

```text
router.choose_context_free()
```

and must not disable FastTrack.

## Corrected 8-Combination Simulation

The benchmark script was corrected so `none` keeps FastTrack enabled and maps to
`neutral_random`.

Command:

```bash
python3 AI_NPC_System/scripts/benchmark_experiment_factors.py \
  --runs 1 \
  --trials 100 \
  --output-dir AI_NPC_System/reports/six_factor_cases_status_2026-05-27/benchmark_assumption
```

CSV:

```text
AI_NPC_System/reports/six_factor_cases_status_2026-05-27/benchmark_assumption/factor_simulation.csv
```

| Component Mode | Mapping Level | Runtime Selection | Scheduling | First Audio Median ms | Slow Ready Median ms | Next Turn Wait Median ms |
|---|---|---|---|---:|---:|---:|
| both | grounded | grounded | parallel | 79.927 | 3387.471 | 0.000 |
| both | grounded | grounded | serial | 80.749 | 3390.840 | 3390.840 |
| both | emotion_only | emotion_only | parallel | 79.870 | 3328.987 | 0.000 |
| both | emotion_only | emotion_only | serial | 81.155 | 3392.100 | 3392.100 |
| both | response_act_only | response_act_only | parallel | 80.515 | 3387.075 | 0.000 |
| both | response_act_only | response_act_only | serial | 82.170 | 3376.661 | 3376.661 |
| both | none | neutral_random | parallel | 80.239 | 3375.228 | 0.000 |
| both | none | neutral_random | serial | 80.983 | 3360.828 | 3360.828 |

## Interpretation

- Contextual Mapping changes which FastTrack cover line is selected, not whether
  FastTrack exists.
- `None` is the correct neutral random FastTrack control.
- `No FastTrack` is a different component-level ablation and should not be used
  as the `None` condition for this experiment.
- The current runtime must be patched before live participant data can be trusted
  for the corrected `None` condition.

## Files Checked

- `AI_NPC_System/fast_track_audio_cache.py`
- `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
- `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
- `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
- `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`

The forbidden agent file was inspected but not edited in this correction pass.
