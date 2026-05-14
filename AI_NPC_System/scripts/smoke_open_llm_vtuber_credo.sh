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

export PATH="$VENV_DIR/bin:$PATH"

cd "$OLV_DIR"
"$VENV_DIR/bin/python" - <<'PY'
from src.open_llm_vtuber.config_manager import read_yaml, validate_config

cfg = validate_config(read_yaml("conf.yaml"))
choice = cfg.character_config.agent_config.conversation_agent_choice
assert choice == "credo_latency_cover_agent", choice
print("config:", choice)
PY

cd "$ROOT_DIR/AI_NPC_System"
FAST_TRACK_DEVICE="${FAST_TRACK_DEVICE:-cpu}" "$VENV_DIR/bin/python" fast_track.py
