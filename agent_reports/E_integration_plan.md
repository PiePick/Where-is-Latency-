# Agent E — Integration Plan

## Current
- Server sends newline-delimited JSON packets (`fast`, `slow`)
- Unity currently reads a fixed subset: `type, emotion, reaction, echo_text, npc_reply`

## Non-breaking schema extension
- Keep legacy fields untouched
- Add optional fields: `schema_version, strategy, confidence_band, top1, margin, entropy, latency_ms`

## Migration
1. Server emits additive v2 fields while preserving v1 keys
2. Unity ignores unknown fields (safe)
3. Later Unity can consume new fields optionally

## Why safe
- additive-only change
- no required parser change for current client
- preserves `fast/slow` behavior
