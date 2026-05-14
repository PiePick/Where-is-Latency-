#!/usr/bin/env bash
set -euo pipefail

# Run with the Open-LLM-VTuber venv because it already has websockets installed.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OLV_VENV_PYTHON="${ROOT_DIR}/vendor/open-llm-vtuber/.venv/bin/python"
PYTHON_BIN="${YOUTUBE_CHAT_BRIDGE_PYTHON:-${OLV_VENV_PYTHON}}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "Missing Python runtime: ${PYTHON_BIN}" >&2
  echo "Run first: AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh" >&2
  exit 2
fi

exec "${PYTHON_BIN}" "${ROOT_DIR}/AI_NPC_System/scripts/youtube_live_chat_bridge.py" "$@"
