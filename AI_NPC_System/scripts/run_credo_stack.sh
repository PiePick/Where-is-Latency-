#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/vendor/open-llm-vtuber/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Open-LLM-VTuber runtime is missing. Run:" >&2
  echo "  AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh" >&2
  exit 1
fi

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" AI_NPC_System/scripts/run_credo_stack.py "$@"
