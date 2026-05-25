#!/usr/bin/env bash
set -euo pipefail

# Run CREDO with a named experimental condition.
#
# This wrapper only sets condition-specific environment variables. The actual
# service orchestration is delegated to run_credo_stack.sh.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONDITION="${1:-}"
shift || true

usage() {
  cat <<'USAGE'
Usage:
  AI_NPC_System/scripts/run_experiment_condition.sh <condition> [run_credo_stack args...]

Conditions:
  no-cover
    Disable FastTrack. SlowTrack LLM/TTS is the first response.

  affective-cached-fish
    Default condition. Use emotion/intent/response-act selection with the
    pre-generated Fish Speech persona bundle.

  piper-realtime
    Use Piper as a lightweight realtime FastTrack TTS baseline.

  slow-only-text-fallback
    Disable FastTrack and allow Open-LLM-VTuber fallback TTS for debugging only.

Examples:
  AI_NPC_System/scripts/run_experiment_condition.sh affective-cached-fish --profile live
  AI_NPC_System/scripts/run_experiment_condition.sh no-cover --profile live
  AI_NPC_System/scripts/run_experiment_condition.sh piper-realtime --profile live-piper
USAGE
}

if [[ -z "${CONDITION}" || "${CONDITION}" == "-h" || "${CONDITION}" == "--help" ]]; then
  usage
  exit 0
fi

case "${CONDITION}" in
  no-cover)
    export CREDO_EXPERIMENT_CONDITION="no-cover"
    export FAST_TRACK_ENABLED="0"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    ;;
  affective-cached-fish)
    export CREDO_EXPERIMENT_CONDITION="affective-cached-fish"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="cached_fish_bundle"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="1"
    export FAST_TRACK_PERSONA_BUNDLE_FILE="fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/manifest.json"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    ;;
  piper-realtime)
    export CREDO_EXPERIMENT_CONDITION="piper-realtime"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="piper_tts"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="0"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    ;;
  slow-only-text-fallback)
    export CREDO_EXPERIMENT_CONDITION="slow-only-text-fallback"
    export FAST_TRACK_ENABLED="0"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    ;;
  *)
    echo "Unknown condition: ${CONDITION}" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$#" -eq 0 ]]; then
  set -- --profile live
fi

cd "${ROOT_DIR}"
echo "CREDO experiment condition: ${CREDO_EXPERIMENT_CONDITION}"
exec AI_NPC_System/scripts/run_credo_stack.sh "$@"
