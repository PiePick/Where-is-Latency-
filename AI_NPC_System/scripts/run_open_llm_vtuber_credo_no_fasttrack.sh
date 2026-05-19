#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

export FAST_TRACK_ENABLED="0"
export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"

exec "${ROOT_DIR}/AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh"
