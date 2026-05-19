#!/usr/bin/env bash
set -euo pipefail

# Launch the Fish Speech HTTP API from the vendored repository.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
if [ -f "${CONFIG_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
  set +a
fi

FISH_DIR="${FISH_SPEECH_REPO_DIR:-${ROOT_DIR}/vendor/fish-speech}"
HOST="${FISH_SPEECH_HOST:-127.0.0.1}"
PORT="${FISH_SPEECH_PORT:-8080}"
CUDA_DEVICES="${FISH_SPEECH_CUDA_VISIBLE_DEVICES:-0}"
CHECKPOINT_NAME="${FISH_SPEECH_CHECKPOINT_NAME:-s2-pro}"
CHECKPOINT_DIR="${FISH_SPEECH_CHECKPOINT_DIR:-${FISH_DIR}/checkpoints/${CHECKPOINT_NAME}}"
MODEL_REPO="${FISH_SPEECH_MODEL_REPO:-fishaudio/s2-pro}"
API_KEY="${FISH_SPEECH_API_KEY:-}"
EXTRA_ARGS="${FISH_SPEECH_EXTRA_ARGS:-}"
DEFAULT_VENV_PYTHON="${FISH_DIR}/.venv/bin/python"
REFERENCE_ID="${FISH_SPEECH_REFERENCE_ID:-credo_voice_sample}"
REFERENCE_SOURCE="${FISH_SPEECH_REFERENCE_SOURCE:-AI_NPC_System/VoiceSample/VoicePack1_Morning.wav}"
EDGE_REFERENCE_VOICE="${FISH_SPEECH_EDGE_REFERENCE_VOICE:-en-US-JennyNeural}"
REFERENCE_TEXT="${FISH_SPEECH_REFERENCE_TEXT:-Hi hi, good work. Let us keep the stream bright and fun.}"
REGENERATE_REFERENCE="${FISH_SPEECH_REGENERATE_REFERENCE:-0}"
REFERENCE_TIMEOUT="${FISH_SPEECH_REFERENCE_TIMEOUT:-60s}"
REFERENCE_DIR="${FISH_DIR}/references/${REFERENCE_ID}"
FFMPEG_BIN="${FFMPEG_BIN:-${ROOT_DIR}/vendor/open-llm-vtuber/.venv/bin/ffmpeg}"
EDGE_TTS_PYTHON="${EDGE_TTS_PYTHON:-${ROOT_DIR}/vendor/open-llm-vtuber/.venv/bin/python}"

if [ -n "${FISH_SPEECH_PYTHON:-}" ]; then
  PYTHON_BIN="${FISH_SPEECH_PYTHON}"
elif [ -x "${DEFAULT_VENV_PYTHON}" ]; then
  PYTHON_BIN="${DEFAULT_VENV_PYTHON}"
else
  PYTHON_BIN="python3"
fi

cd "${FISH_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/credo-fish-speech-matplotlib}"
mkdir -p "${MPLCONFIGDIR}"

# The server needs the S2-Pro checkpoint and codec file under one directory.
if [ ! -d "${CHECKPOINT_DIR}" ]; then
  echo "Missing Fish Speech checkpoint: ${CHECKPOINT_DIR}" >&2
  echo "Download first:" >&2
  echo "  cd ${FISH_DIR} && hf download ${MODEL_REPO} --local-dir checkpoints/${CHECKPOINT_NAME}" >&2
  exit 2
fi

# Keep a stable bright female reference voice for local Fish Speech calls.
should_generate_reference=0
case "${REGENERATE_REFERENCE,,}" in
  1|true|yes|on) should_generate_reference=1 ;;
esac
if [ "${REFERENCE_ID}" = "credo_bright_female" ] && [ ! -f "${REFERENCE_DIR}/sample.wav" ]; then
  should_generate_reference=1
fi

if [ "${REFERENCE_ID}" = "credo_bright_female" ] && [ "${should_generate_reference}" = "1" ]; then
  mkdir -p "${REFERENCE_DIR}"
  tmp_mp3="${REFERENCE_DIR}/sample.edge.mp3"
  if timeout "${REFERENCE_TIMEOUT}" "${EDGE_TTS_PYTHON}" -m edge_tts \
    --voice "${EDGE_REFERENCE_VOICE}" \
    --text "${REFERENCE_TEXT}" \
    --write-media "${tmp_mp3}" >/dev/null 2>&1 && \
    "${FFMPEG_BIN}" -y -v error -i "${tmp_mp3}" -ar 44100 -ac 1 "${REFERENCE_DIR}/sample.wav"; then
    printf '%s\n' "${REFERENCE_TEXT}" > "${REFERENCE_DIR}/sample.lab"
    rm -f "${tmp_mp3}"
    echo "Generated Fish Speech fallback reference with Edge voice ${EDGE_REFERENCE_VOICE}."
  else
    echo "Could not generate ${REFERENCE_ID} with edge-tts; using existing/cache fallback." >&2
    if [ ! -f "${REFERENCE_DIR}/sample.wav" ]; then
      cp "${ROOT_DIR}/AI_NPC_System/fast_track_audio_cache/Positive/stream/e551e29fc1249359.wav" "${REFERENCE_DIR}/sample.wav"
      printf '%s\n' 'Good work, friend.' > "${REFERENCE_DIR}/sample.lab"
    fi
  fi
fi

# Keep the command as an array so paths with spaces remain safe.
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

# EXTRA_ARGS is intentionally appended unquoted for advanced one-off tuning.
echo "Starting Fish Speech server on http://${HOST}:${PORT}"
echo "Using CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "Using Python: ${PYTHON_BIN}"
echo "Using Fish Speech checkpoint: ${CHECKPOINT_DIR}"
echo "Using Fish Speech reference id: ${REFERENCE_ID}"
if [ "${REFERENCE_ID}" = "credo_voice_sample" ]; then
  echo "Using Fish Speech reference source sample: ${ROOT_DIR}/${REFERENCE_SOURCE}"
elif [ "${REFERENCE_ID}" = "credo_bright_female" ]; then
  echo "Using Fish Speech generated fallback source voice: ${EDGE_REFERENCE_VOICE}"
else
  echo "Using Fish Speech reference directory: ${REFERENCE_DIR}"
fi
"${cmd[@]}" ${EXTRA_ARGS}
