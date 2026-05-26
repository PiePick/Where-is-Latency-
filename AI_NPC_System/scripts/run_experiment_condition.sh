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
  stylebert-no-fasttrack
    Disable FastTrack. StyleBERT SlowTrack is the first audible response.

  stylebert-grounded-parallel
    Use grounded emotion + SWDA response-act FastTrack with background prefetch.

  stylebert-grounded-serial
    Use grounded FastTrack, then start the next SlowTrack after playback.

  stylebert-emotion-only
    Use GoEmotions-only FastTrack mapping with background prefetch.

  stylebert-response-act-only
    Use SWDA response-act-only FastTrack mapping with background prefetch.

Examples:
  AI_NPC_System/scripts/run_experiment_condition.sh stylebert-no-fasttrack --profile live
  AI_NPC_System/scripts/run_experiment_condition.sh stylebert-grounded-parallel --profile live
  AI_NPC_System/scripts/run_experiment_condition.sh stylebert-response-act-only --profile live
USAGE
}

if [[ -z "${CONDITION}" || "${CONDITION}" == "-h" || "${CONDITION}" == "--help" ]]; then
  usage
  exit 0
fi

case "${CONDITION}" in
  stylebert-no-fasttrack|edge-no-cover)
    export CREDO_EXPERIMENT_CONDITION="stylebert-no-fasttrack"
    export FAST_TRACK_ENABLED="0"
    export FAST_TRACK_TTS_MODE="stylebert_vits2"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export OPEN_LLM_VTUBER_TTS_MODEL="stylebert_vits2"
    export OPEN_LLM_VTUBER_SLOW_TTS_MODE="open_llm"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    export CREDO_FASTTRACK_COMPONENT_MODE="none"
    export CREDO_FASTTRACK_SELECTION_POLICY="grounded"
    export CREDO_CONTEXT_SCHEDULING_MODE="serial"
    export CREDO_VTUBER_SLOW_PREFETCH_ENABLED="0"
    ;;
  stylebert-grounded-serial|edge-fasttrack)
    export CREDO_EXPERIMENT_CONDITION="stylebert-grounded-serial"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="stylebert_vits2"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="0"
    export FAST_TRACK_DATASET_POOL_FILE="fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export FAST_TRACK_PREBUILT_ONLY="0"
    export OPEN_LLM_VTUBER_TTS_MODEL="stylebert_vits2"
    export OPEN_LLM_VTUBER_SLOW_TTS_MODE="open_llm"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    export CREDO_FASTTRACK_COMPONENT_MODE="both"
    export CREDO_FASTTRACK_SELECTION_POLICY="grounded"
    export CREDO_CONTEXT_SCHEDULING_MODE="serial"
    export CREDO_VTUBER_SLOW_PREFETCH_ENABLED="0"
    ;;
  stylebert-grounded-parallel|edge-async-cover)
    export CREDO_EXPERIMENT_CONDITION="stylebert-grounded-parallel"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="stylebert_vits2"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="0"
    export FAST_TRACK_DATASET_POOL_FILE="fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export FAST_TRACK_PREBUILT_ONLY="0"
    export OPEN_LLM_VTUBER_TTS_MODEL="stylebert_vits2"
    export OPEN_LLM_VTUBER_SLOW_TTS_MODE="open_llm"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    export CREDO_FASTTRACK_COMPONENT_MODE="both"
    export CREDO_FASTTRACK_SELECTION_POLICY="grounded"
    export CREDO_CONTEXT_SCHEDULING_MODE="parallel"
    export CREDO_VTUBER_SLOW_PREFETCH_ENABLED="1"
    ;;
  stylebert-emotion-only)
    export CREDO_EXPERIMENT_CONDITION="stylebert-emotion-only"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="stylebert_vits2"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="0"
    export FAST_TRACK_DATASET_POOL_FILE="fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export FAST_TRACK_PREBUILT_ONLY="0"
    export OPEN_LLM_VTUBER_TTS_MODEL="stylebert_vits2"
    export OPEN_LLM_VTUBER_SLOW_TTS_MODE="open_llm"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    export CREDO_FASTTRACK_COMPONENT_MODE="both"
    export CREDO_FASTTRACK_SELECTION_POLICY="emotion_only"
    export CREDO_CONTEXT_SCHEDULING_MODE="parallel"
    export CREDO_VTUBER_SLOW_PREFETCH_ENABLED="1"
    ;;
  stylebert-response-act-only)
    export CREDO_EXPERIMENT_CONDITION="stylebert-response-act-only"
    export FAST_TRACK_ENABLED="1"
    export FAST_TRACK_TTS_MODE="stylebert_vits2"
    export FAST_TRACK_PERSONA_BUNDLE_ENABLED="0"
    export FAST_TRACK_DATASET_POOL_FILE="fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json"
    export FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="0"
    export FAST_TRACK_PREBUILT_ONLY="0"
    export OPEN_LLM_VTUBER_TTS_MODEL="stylebert_vits2"
    export OPEN_LLM_VTUBER_SLOW_TTS_MODE="open_llm"
    export SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK="1"
    export CREDO_FASTTRACK_COMPONENT_MODE="both"
    export CREDO_FASTTRACK_SELECTION_POLICY="response_act_only"
    export CREDO_CONTEXT_SCHEDULING_MODE="parallel"
    export CREDO_VTUBER_SLOW_PREFETCH_ENABLED="1"
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
