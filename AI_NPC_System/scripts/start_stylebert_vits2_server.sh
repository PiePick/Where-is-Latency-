#!/usr/bin/env bash
# Launch a local Style-Bert-VITS2 FastAPI server for FastTrack TTS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
fi

STYLEBERT_DIR="${STYLEBERT_VITS2_REPO_DIR:-${ROOT_DIR}/vendor/Style-Bert-VITS2}"
PYTHON_BIN="${STYLEBERT_VITS2_PYTHON:-${STYLEBERT_DIR}/.venv/bin/python}"
HOST="${STYLEBERT_VITS2_HOST:-127.0.0.1}"
PORT="${STYLEBERT_VITS2_PORT:-5000}"
MODEL_DIR="${STYLEBERT_VITS2_MODEL_DIR:-${STYLEBERT_DIR}/model_assets}"

if [[ ! -d "${STYLEBERT_DIR}" ]]; then
  echo "Missing Style-Bert-VITS2 repo: ${STYLEBERT_DIR}" >&2
  echo "Clone https://github.com/litagin02/Style-Bert-VITS2 into vendor/Style-Bert-VITS2 first." >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing Style-Bert-VITS2 Python runtime: ${PYTHON_BIN}" >&2
  echo "Create the Style-Bert-VITS2 venv and install its requirements first." >&2
  exit 1
fi

if [[ ! -d "${MODEL_DIR}" ]]; then
  echo "Missing Style-Bert-VITS2 model assets: ${MODEL_DIR}" >&2
  echo "Place the CREDO voice-compatible Style-Bert-VITS2 model under model_assets." >&2
  exit 1
fi

cd "${STYLEBERT_DIR}"
echo "Starting Style-Bert-VITS2 server on http://${HOST}:${PORT}"
exec "${PYTHON_BIN}" server_fastapi.py --host "${HOST}" --port "${PORT}" --dir "${MODEL_DIR}"
