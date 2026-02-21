# Upgrade v01 — Text Merge Quality

## Scope
- probabilistic merge-policy scaffold
- short-form reaction pack integration
- additive server schema extension
- telemetry fields for policy decisions

## Changes
1. `AI_NPC_System/merge_policy.py` added
2. `fast_lane.py` updated with strategy/confidence routing
3. `reactions_v01.json` added and wired via `config.REACTION_DB_FILE`
4. `slow_lane.py` cleanup (duplicate block removed)
5. `server.py` emits additive fields: `schema_version`, `strategy`, `confidence_band`, `top1`, `margin`, `entropy`, `latency_ms`
6. `main.py` compatibility fix (`emotion_detail` bug)
7. open-source reaction reference folder added (`reaction_sources/*`)

## Review scores (v01 baseline)
- Architecture clarity: 8.3 / 10
- Backward compatibility: 8.8 / 10
- Fast response naturalness: 8.1 / 10
- Observability readiness: 7.9 / 10
- Risk control: 8.0 / 10
- Overall: **8.2 / 10**

## Known gaps
- no automated replay harness yet
- no real online A/B gating yet
- confidence thresholds not calibrated on real logs
