# Agent B — Fast Lane Refactor Plan

## Target
Split emotion merge logic from `fast_lane.py` into dedicated policy module for easier rollout and A/B.

## Plan
1. Add `merge_policy.py`
2. Keep `analyze_and_react(text)` backward-compatible
3. Keep existing keys; add alias (`emotion_detail`) and new debug/policy fields
4. Add policy toggle path for future (`sum / probabilistic`)

## Risks
- behavior drift from old winner-take-all
- runtime failures from model/reaction-path issues
- response style instability

## Mitigation
- default-safe policy fallback
- retain existing return schema
- log policy decisions per turn
