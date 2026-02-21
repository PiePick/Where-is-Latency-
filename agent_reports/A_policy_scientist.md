# Agent A — Policy Scientist Report

## Summary
- Current system is fast/slow dual lane, but no explicit merge-controller.
- Fast output currently influences slow lane mainly through `fast_reaction` prompt injection.

## Proposed probabilistic policy
Use category distribution features:
- `top1`, `top2`, `margin=top1-top2`, `entropy(norm)`

Confidence bands:
- High: `top1>=0.62 && margin>=0.25 && entropy<=0.50`
- Medium: `top1>=0.50 && margin>=0.10 && entropy<=0.75`
- Low: else

## Action routing
- Emotion-first: high confidence + positive/negative
- Echo-first: medium confidence + keyword/question
- Bridge: high uncertainty or anticipated wait
- Neutral-minimal: low confidence

## Telemetry required
`strategy, confidence_band, top1, margin, entropy, category_scores, model, fast/slow latency, fallback path`

## Acceptance criteria
- High confidence turns mostly route to Emotion/Echo
- Low confidence turns mostly route to Neutral/Bridge
- No latency regression >5% p95
- Contradiction rate reduction target: 30%
