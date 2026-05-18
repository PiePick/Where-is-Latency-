#!/usr/bin/env bash
# Start CREDO's resident Piper FastTrack TTS server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
fi

PIPER_DIR="${PIPER_TTS_DIR:-${ROOT_DIR}/vendor/piper-tts}"
case "${PIPER_DIR}" in
  /*) ;;
  *) PIPER_DIR="${ROOT_DIR}/${PIPER_DIR}" ;;
esac
PIPER_PYTHON="${PIPER_TTS_PYTHON:-${PIPER_DIR}/.venv/bin/python}"

if [[ ! -x "${PIPER_PYTHON}" ]]; then
  echo "Piper runtime is missing. Run:" >&2
  echo "  PIPER_TTS_AUTO_INSTALL=1 PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 AI_NPC_System/scripts/setup_piper_fasttrack_tts.sh" >&2
  exit 1
fi

cd "${ROOT_DIR}"
exec "${PIPER_PYTHON}" AI_NPC_System/scripts/piper_fasttrack_server.py
