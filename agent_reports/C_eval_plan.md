# Agent C — Evaluation Plan

## Objective
Compare old threshold-like deterministic routing vs probabilistic policy.

## Offline replay
- Fixed turn corpus (stratified by emotion intensity / utterance length)
- Replay both policies with fixed seeds
- Compare: alignment, repetition rate, fast-latency distribution, error/fallback rates

## Online A/B
- Session-level 50/50 split
- Primary: fast p95 latency, satisfaction, complaint rate
- Secondary: empathy score, contradiction rate, retention

## Statistics
- Continuous: Welch t-test / Mann-Whitney
- Proportions: chi-square / Fisher exact
- Multiple metrics: FDR (Benjamini-Hochberg)

## Stop/Go
Hard stop if:
- fast p95 latency +5% 이상
- complaint +2pp 이상
Go if:
- primary KPI 유의 개선 + 안전성 악화 없음
