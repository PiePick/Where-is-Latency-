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

cd "$ROOT_DIR"
"$VENV_DIR/bin/python" AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate

cd "$OLV_DIR"
echo "Starting Open-LLM-VTuber with CREDO latency-cover agent."
echo "Open: http://localhost:12393"
echo "CREDO config: ${CONFIG_FILE}"
echo "SlowTrack LLM: ${LOCAL_LLM_MODEL} (${LOCAL_LLM_BASE_URL})"
exec "$VENV_DIR/bin/python" run_server.py
