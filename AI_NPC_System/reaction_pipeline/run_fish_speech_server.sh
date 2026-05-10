#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FISH_DIR="${FISH_SPEECH_REPO_DIR:-${ROOT_DIR}/vendor/fish-speech}"
HOST="${FISH_SPEECH_HOST:-127.0.0.1}"
PORT="${FISH_SPEECH_PORT:-8080}"
CUDA_DEVICES="${FISH_SPEECH_CUDA_VISIBLE_DEVICES:-0}"
CHECKPOINT_DIR="${FISH_SPEECH_CHECKPOINT_DIR:-${FISH_DIR}/checkpoints/s2-pro}"
API_KEY="${FISH_SPEECH_API_KEY:-}"
EXTRA_ARGS="${FISH_SPEECH_EXTRA_ARGS:-}"
PYTHON_BIN="${FISH_SPEECH_PYTHON:-python3}"

cd "${FISH_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"

if [ ! -d "${CHECKPOINT_DIR}" ]; then
  echo "Missing Fish Speech checkpoint: ${CHECKPOINT_DIR}" >&2
  echo "Download first:" >&2
  echo "  cd ${FISH_DIR} && hf download fishaudio/s2-pro --local-dir checkpoints/s2-pro" >&2
  exit 2
fi

cmd=(
  "${PYTHON_BIN}" tools/api_server.py
  --llama-checkpoint-path "${CHECKPOINT_DIR}"
  --decoder-checkpoint-path "${CHECKPOINT_DIR}/codec.pth"
  --decoder-config-name modded_dac_vq
  --listen "${HOST}:${PORT}"
  --half
)

if [ -n "${API_KEY}" ]; then
  cmd+=(--api-key "${API_KEY}")
fi

echo "Starting Fish Speech server on http://${HOST}:${PORT}"
echo "Using CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
"${cmd[@]}" ${EXTRA_ARGS}
