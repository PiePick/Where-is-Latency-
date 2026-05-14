#!/usr/bin/env bash
set -euo pipefail

# Start a compact OpenAI-compatible vLLM server for SlowTrack.
# Defaults match the CREDO runtime config and can be overridden per experiment.
HOST="${LOCAL_LLM_HOST:-127.0.0.1}"
PORT="${LOCAL_LLM_PORT:-8001}"
SERVED_MODEL_NAME="${LOCAL_LLM_SERVED_MODEL_NAME:-qwen2.5:7b}"
MODEL_PATH="${LOCAL_LLM_MODEL_PATH:-Qwen/Qwen2.5-7B-Instruct}"
CUDA_DEVICES="${LOCAL_LLM_CUDA_VISIBLE_DEVICES:-1}"
GPU_MEMORY_UTILIZATION="${LOCAL_LLM_GPU_MEMORY_UTILIZATION:-0.70}"
MAX_MODEL_LEN="${LOCAL_LLM_MAX_MODEL_LEN:-2048}"
ENV_NAME="${LOCAL_LLM_CONDA_ENV:-agentscope}"
CONDA_ROOT="${LOCAL_LLM_CONDA_ROOT:-/home/ysree/miniconda3}"
CUDA_RUNTIME_LIB="${CONDA_ROOT}/envs/${ENV_NAME}/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"

source "${CONDA_ROOT}/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

export PYTHONNOUSERSITE=1
export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
export LD_LIBRARY_PATH="${CUDA_RUNTIME_LIB}:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"
export TEMP="${TMPDIR}"
export TMP="${TMPDIR}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"

python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL_PATH}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --enforce-eager
