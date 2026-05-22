#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COSYVOICE_DIR="${COSYVOICE_DIR:-${ROOT_DIR}/vendor/CosyVoice}"
CONDA_PYTHON="${COSYVOICE_PYTHON:-/home/ysree/miniconda3/envs/cosyvoice/bin/python}"
MODEL_DIR="${COSYVOICE_MODEL_DIR:-pretrained_models/CosyVoice2-0.5B}"
PORT="${COSYVOICE_PORT:-50000}"
CUDA_DEVICES="${COSYVOICE_CUDA_VISIBLE_DEVICES:-0}"

if [ ! -x "${CONDA_PYTHON}" ]; then
  echo "Missing CosyVoice Python: ${CONDA_PYTHON}" >&2
  echo "Create it with: /home/ysree/miniconda3/bin/conda create -n cosyvoice -y python=3.10" >&2
  exit 2
fi

if [ ! -d "${COSYVOICE_DIR}" ]; then
  echo "Missing CosyVoice repo: ${COSYVOICE_DIR}" >&2
  exit 2
fi

cd "${COSYVOICE_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
echo "Starting CosyVoice2 server on http://127.0.0.1:${PORT}"
echo "Using Python: ${CONDA_PYTHON}"
echo "Using model: ${MODEL_DIR}"
exec "${CONDA_PYTHON}" webui.py --port "${PORT}" --model_dir "${MODEL_DIR}"
