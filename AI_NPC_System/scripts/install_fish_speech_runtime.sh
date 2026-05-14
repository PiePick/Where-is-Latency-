#!/usr/bin/env bash
set -euo pipefail

# Build the local Python environment used by start_fish_speech_server.sh.
# PyAudio is intentionally skipped because the HTTP API server does not need
# local microphone capture and PyAudio requires WSL system headers.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [ -f "${CONFIG_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
  set +a
fi

FISH_DIR="${FISH_SPEECH_REPO_DIR:-${ROOT_DIR}/vendor/fish-speech}"
VENV_DIR="${FISH_SPEECH_VENV_DIR:-${FISH_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TORCH_INDEX_URL="${FISH_SPEECH_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

if [ ! -d "${FISH_DIR}" ]; then
  echo "Missing Fish Speech repo: ${FISH_DIR}" >&2
  exit 2
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
  if "${PYTHON_BIN}" -m venv "${VENV_DIR}" 2>/dev/null; then
    :
  elif "${PYTHON_BIN}" -m virtualenv "${VENV_DIR}"; then
    :
  else
    echo "Failed to create venv. Install python3-venv or virtualenv first." >&2
    exit 2
  fi
fi

PIP="${VENV_DIR}/bin/python -m pip"
${PIP} install -U pip
${PIP} install -e "${FISH_DIR}" --no-deps
${PIP} install --extra-index-url "${TORCH_INDEX_URL}" \
  numpy \
  torch==2.8.0 \
  torchaudio==2.8.0 \
  'transformers<=4.57.3' \
  datasets==2.18.0 \
  'lightning>=2.1.0' \
  'hydra-core>=1.3.2' \
  'tensorboard>=2.14.1' \
  'natsort>=8.4.0' \
  'einops>=0.7.0' \
  'librosa>=0.10.1' \
  'rich>=13.5.3' \
  'gradio>5.0.0' \
  'wandb>=0.19.0' \
  'grpcio>=1.58.0' \
  'kui>=1.6.0' \
  'uvicorn>=0.30.0' \
  'loguru>=0.6.0' \
  'loralib>=0.1.2' \
  'pyrootutils>=1.0.4' \
  'resampy>=0.4.3' \
  'einx[torch]==0.2.2' \
  'zstandard>=0.22.0' \
  pydub \
  modelscope==1.17.1 \
  opencc-python-reimplemented==0.1.7 \
  silero-vad \
  ormsgpack \
  'tiktoken>=0.8.0' \
  pydantic==2.9.2 \
  cachetools \
  descript-audio-codec \
  safetensors

echo "Fish Speech runtime is ready: ${VENV_DIR}"
