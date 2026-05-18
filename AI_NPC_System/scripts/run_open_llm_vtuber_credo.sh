#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [ -f "${CONFIG_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
  set +a
fi

OLV_DIR="$ROOT_DIR/vendor/open-llm-vtuber"
VENV_DIR="$OLV_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Runtime is not installed. Run:" >&2
  echo "  AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh" >&2
  exit 1
fi

export CREDO_AI_NPC_PATH="${CREDO_AI_NPC_PATH:-$ROOT_DIR/AI_NPC_System}"
export FAST_TRACK_DEVICE="${FAST_TRACK_DEVICE:-cpu}"
export LOCAL_LLM_BASE_URL="${LOCAL_LLM_BASE_URL:-http://${LOCAL_LLM_HOST:-127.0.0.1}:${LOCAL_LLM_PORT:-8001}/v1}"
export LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-${LOCAL_LLM_SERVED_MODEL_NAME:-qwen2.5:7b}}"
export FALLBACK_LOCAL_LLM_BASE_URL="${FALLBACK_LOCAL_LLM_BASE_URL:-$LOCAL_LLM_BASE_URL}"
export FALLBACK_LOCAL_LLM_MODEL="${FALLBACK_LOCAL_LLM_MODEL:-$LOCAL_LLM_MODEL}"
export PATH="$VENV_DIR/bin:$PATH"

allow_open_llm_fast_tts=0
case "${FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK:-0}" in
  1|true|TRUE|yes|YES|on|ON) allow_open_llm_fast_tts=1 ;;
esac

stylebert_ready=0
if [[ "${FAST_TRACK_TTS_MODE:-stylebert_vits2}" == "stylebert_vits2" ]]; then
  if "$VENV_DIR/bin/python" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1.5).close()'     "${STYLEBERT_VITS2_HEALTH_URL:-http://127.0.0.1:5000/docs}" >/dev/null 2>&1; then
    stylebert_ready=1
  fi
fi

if [[ "${allow_open_llm_fast_tts}" != "1" && "${FAST_TRACK_TTS_MODE:-stylebert_vits2}" == "stylebert_vits2" && "${stylebert_ready}" != "1" ]]; then
  echo "FastTrack realtime lightweight TTS is not ready." >&2
  echo "Open-LLM-VTuber default TTS fallback is disabled to avoid the wrong cute FastTrack voice." >&2
  echo "Start the FastTrack StyleBERT-VITS2 server first:" >&2
  echo "  AI_NPC_System/scripts/start_stylebert_vits2_server.sh" >&2
  echo "If that script appears to stall, rerun it with visible fast-fail diagnostics:" >&2
  echo "  STYLEBERT_VITS2_IMPORT_TIMEOUT=30 AI_NPC_System/scripts/start_stylebert_vits2_server.sh" >&2
  echo "If it reports JP-only model_assets with STYLEBERT_VITS2_LANGUAGE=EN, install a CREDO-compatible English StyleBERT model under vendor/Style-Bert-VITS2/model_assets and set STYLEBERT_VITS2_MODEL_NAME." >&2
  echo "Temporary JP smoke tests can use STYLEBERT_VITS2_LANGUAGE=JP, but that is not the CREDO English FastTrack configuration." >&2
  echo "Health URL checked: ${STYLEBERT_VITS2_HEALTH_URL:-http://127.0.0.1:5000/docs}" >&2
  exit 2
fi

cd "$ROOT_DIR"
"$VENV_DIR/bin/python" AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate

cd "$OLV_DIR"
echo "Starting Open-LLM-VTuber with CREDO latency-cover agent."
echo "Open: http://localhost:12393"
echo "CREDO config: ${CONFIG_FILE}"
echo "SlowTrack LLM: ${LOCAL_LLM_MODEL} (${LOCAL_LLM_BASE_URL})"
echo "GPU placement: Fish Speech GPU${FISH_SPEECH_CUDA_VISIBLE_DEVICES:-0}, StyleBERT ${STYLEBERT_VITS2_DEVICE:-cpu} mode, Local LLM GPU${LOCAL_LLM_CUDA_VISIBLE_DEVICES:-1}"
exec "$VENV_DIR/bin/python" run_server.py
