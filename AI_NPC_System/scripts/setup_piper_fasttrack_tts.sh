#!/usr/bin/env bash
# Prepare Piper for CREDO FastTrack TTS. Piper runs as a CLI, so no resident
# FastTrack TTS server is required after this setup/check passes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
fi

PIPER_DIR="${PIPER_TTS_DIR:-${ROOT_DIR}/vendor/piper-tts}"
PIPER_VENV="${PIPER_TTS_VENV:-${PIPER_DIR}/.venv}"
PIPER_PYTHON="${PIPER_TTS_PYTHON:-${PIPER_VENV}/bin/python}"
PIPER_BIN="${PIPER_TTS_BIN:-${PIPER_VENV}/bin/piper}"
VOICE="${PIPER_TTS_VOICE:-en_US-lessac-medium}"
VOICE_DIR="${PIPER_TTS_VOICE_DIR:-${PIPER_DIR}/voices}"
MODEL_PATH="${PIPER_TTS_MODEL_PATH:-${VOICE_DIR}/${VOICE}.onnx}"
CONFIG_PATH="${PIPER_TTS_CONFIG_PATH:-${MODEL_PATH}.json}"
AUTO_INSTALL="${PIPER_TTS_AUTO_INSTALL:-0}"
AUTO_DOWNLOAD_VOICE="${PIPER_TTS_AUTO_DOWNLOAD_VOICE:-0}"

info() { printf '[Piper] %s\n' "$*"; }
die() { printf '[Piper][ERROR] %s\n' "$*" >&2; exit 1; }
is_on() { case "${1:-0}" in 1|true|TRUE|yes|YES|on|ON) return 0 ;; *) return 1 ;; esac; }

mkdir -p "${PIPER_DIR}" "${VOICE_DIR}"

if [[ ! -x "${PIPER_PYTHON}" ]]; then
  if ! is_on "${AUTO_INSTALL}"; then
    die "Missing Piper venv: ${PIPER_PYTHON}. Run: PIPER_TTS_AUTO_INSTALL=1 ${0}"
  fi
  info "Creating Piper venv at ${PIPER_VENV}"
  python3 -m venv "${PIPER_VENV}"
fi

if [[ ! -x "${PIPER_BIN}" ]]; then
  if ! is_on "${AUTO_INSTALL}"; then
    die "Missing Piper executable: ${PIPER_BIN}. Run: PIPER_TTS_AUTO_INSTALL=1 ${0}"
  fi
  info "Installing piper-tts into ${PIPER_VENV}"
  "${PIPER_PYTHON}" -m pip install --upgrade pip
  "${PIPER_PYTHON}" -m pip install piper-tts
fi

if [[ ! -f "${MODEL_PATH}" || ! -f "${CONFIG_PATH}" ]]; then
  if ! is_on "${AUTO_DOWNLOAD_VOICE}"; then
    die "Missing Piper voice files: ${MODEL_PATH} and ${CONFIG_PATH}. Run: PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 ${0}"
  fi
  info "Downloading Piper voice ${VOICE} into ${VOICE_DIR}"
  "${PIPER_PYTHON}" -m piper.download_voices --download-dir "${VOICE_DIR}" "${VOICE}"
fi

[[ -f "${MODEL_PATH}" ]] || die "Piper model still missing after setup: ${MODEL_PATH}"
[[ -f "${CONFIG_PATH}" ]] || die "Piper config still missing after setup: ${CONFIG_PATH}"

info "Ready. Piper FastTrack TTS uses CLI synthesis, so keep no separate TTS server terminal open."
info "Binary: ${PIPER_BIN}"
info "Voice: ${VOICE}"
info "Model: ${MODEL_PATH}"
