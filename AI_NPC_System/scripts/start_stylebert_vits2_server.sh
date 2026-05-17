#!/usr/bin/env bash
# Launch a local Style-Bert-VITS2 FastAPI server for CREDO FastTrack TTS.
# The preflight section handles common WSL/Python 3.12/StyleBERT drift issues.

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
CUDA_DEVICES="${STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES:-0}"
AUTO_FIX="${STYLEBERT_VITS2_AUTO_FIX:-1}"
AUTO_INSTALL="${STYLEBERT_VITS2_AUTO_INSTALL:-0}"
AUTO_APT="${STYLEBERT_VITS2_AUTO_APT:-0}"
AUTO_DOWNLOAD_BERT="${STYLEBERT_VITS2_AUTO_DOWNLOAD_BERT:-0}"

info() { printf '[StyleBERT] %s\n' "$*"; }
warn() { printf '[StyleBERT][WARN] %s\n' "$*" >&2; }
die() { printf '[StyleBERT][ERROR] %s\n' "$*" >&2; exit 1; }
is_on() { case "${1:-0}" in 1|true|TRUE|yes|YES|on|ON) return 0 ;; *) return 1 ;; esac; }

run_pip() {
  "${PYTHON_BIN}" -m pip "$@"
}

normalize_shell_line_endings() {
  if ! is_on "${AUTO_FIX}"; then
    return 0
  fi
  local fixed=0
  while IFS= read -r -d '' file; do
    if LC_ALL=C grep -q $'\r' "${file}"; then
      sed -i 's/\r$//' "${file}"
      fixed=$((fixed + 1))
    fi
  done < <(find "${ROOT_DIR}/AI_NPC_System/scripts" -type f -name '*.sh' -print0)
  if [[ ${fixed} -gt 0 ]]; then
    info "Normalized LF line endings for ${fixed} shell script(s)."
  fi
}

require_vendor_repo() {
  if [[ -d "${STYLEBERT_DIR}" ]]; then
    return 0
  fi
  if is_on "${AUTO_INSTALL}"; then
    mkdir -p "$(dirname "${STYLEBERT_DIR}")"
    git clone https://github.com/litagin02/Style-Bert-VITS2.git "${STYLEBERT_DIR}"
    return 0
  fi
  die "Missing Style-Bert-VITS2 repo: ${STYLEBERT_DIR}. Run: git clone https://github.com/litagin02/Style-Bert-VITS2.git vendor/Style-Bert-VITS2"
}

missing_apt_packages() {
  if ! command -v dpkg-query >/dev/null 2>&1; then
    return 0
  fi
  local packages=(
    python3.12-venv
    python3.12-dev
    pkg-config
    ffmpeg
    libavformat-dev
    libavcodec-dev
    libavdevice-dev
    libavutil-dev
    libavfilter-dev
    libswscale-dev
    libswresample-dev
  )
  local missing=()
  local pkg
  for pkg in "${packages[@]}"; do
    if ! dpkg-query -W -f='${Status}' "${pkg}" 2>/dev/null | grep -q 'install ok installed'; then
      missing+=("${pkg}")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    printf '%s\n' "${missing[@]}"
  fi
}

check_system_prereqs() {
  local missing
  missing="$(missing_apt_packages || true)"
  if [[ -z "${missing}" ]]; then
    return 0
  fi

  local apt_cmd="sudo apt update && sudo apt install -y $(tr '\n' ' ' <<<"${missing}")"
  if is_on "${AUTO_APT}"; then
    warn "Installing missing Ubuntu packages: $(tr '\n' ' ' <<<"${missing}")"
    sudo apt update
    # shellcheck disable=SC2046
    sudo apt install -y $(tr '\n' ' ' <<<"${missing}")
  else
    warn "Missing Ubuntu build/runtime packages for Python 3.12 media wheels: $(tr '\n' ' ' <<<"${missing}")"
    warn "Install them with: ${apt_cmd}"
  fi
}

ensure_venv() {
  if [[ -x "${PYTHON_BIN}" ]]; then
    return 0
  fi
  if ! is_on "${AUTO_INSTALL}"; then
    die "Missing Style-Bert-VITS2 Python runtime: ${PYTHON_BIN}. Create it with: cd ${STYLEBERT_DIR} && python3 -m venv .venv"
  fi
  info "Creating Style-Bert-VITS2 venv at ${STYLEBERT_DIR}/.venv"
  if ! python3 -m venv "${STYLEBERT_DIR}/.venv"; then
    die "python3 -m venv failed. On Ubuntu noble install: sudo apt install -y python3.12-venv"
  fi
}

patch_requirements_for_python312() {
  if ! is_on "${AUTO_FIX}"; then
    return 0
  fi
  local file
  for file in "${STYLEBERT_DIR}"/requirements*.txt; do
    [[ -f "${file}" ]] || continue
    if grep -Eq '^(faster-whisper==0\.10\.1|av==10\.0\.0)' "${file}"; then
      info "Patching Python 3.12-incompatible pins in ${file}"
      sed -i \
        -e 's/^faster-whisper==0\.10\.1/faster-whisper>=1.0.3/' \
        -e 's/^av==10\.0\.0/av>=11.0.0/' \
        "${file}"
    fi
  done
}

install_python_deps_if_needed() {
  if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import fastapi
import torch
import uvicorn
import yaml
PY
  then
    return 0
  fi
  if ! is_on "${AUTO_INSTALL}"; then
    die "Style-Bert-VITS2 Python dependencies are incomplete. Re-run with STYLEBERT_VITS2_AUTO_INSTALL=1 or install requirements.txt in ${STYLEBERT_DIR}."
  fi

  info "Installing Style-Bert-VITS2 Python dependencies."
  run_pip install -U pip
  run_pip install 'setuptools<70.0.0'
  if [[ -f "${STYLEBERT_DIR}/requirements.txt" ]]; then
    run_pip install -r "${STYLEBERT_DIR}/requirements.txt"
  else
    die "Missing requirements.txt under ${STYLEBERT_DIR}"
  fi
}

ensure_python312_compat_packages() {
  if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import pkg_resources
import av
import faster_whisper
PY
  then
    return 0
  fi
  if ! is_on "${AUTO_FIX}"; then
    die "Python 3.12 compatibility packages are missing. Need setuptools<70, faster-whisper>=1.0.3, and a PyAV wheel compatible with Python 3.12."
  fi
  info "Repairing Python 3.12 compatibility packages inside StyleBERT venv."
  run_pip install 'setuptools<70.0.0'
  run_pip install 'faster-whisper>=1.0.3' 'av>=11.0.0'
}

ensure_stylebert_config() {
  [[ -f "${STYLEBERT_DIR}/default_config.yml" ]] || die "Missing StyleBERT default_config.yml in ${STYLEBERT_DIR}"
  if [[ ! -f "${STYLEBERT_DIR}/config.yml" ]]; then
    cp "${STYLEBERT_DIR}/default_config.yml" "${STYLEBERT_DIR}/config.yml"
  fi

  "${PYTHON_BIN}" - "${STYLEBERT_DIR}/config.yml" "${PORT}" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
port = int(sys.argv[2])
data = yaml.safe_load(path.read_text(encoding='utf-8'))
server = data.setdefault('server', {})
server['port'] = port
server['device'] = 'cuda'
path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
PY
}

ensure_model_assets() {
  if [[ ! -d "${MODEL_DIR}" ]]; then
    die "Missing Style-Bert-VITS2 model assets: ${MODEL_DIR}. Place the CREDO voice-compatible model under model_assets."
  fi
  if ! find "${MODEL_DIR}" -mindepth 2 \( -name 'config.json' -o -name 'style_vectors.npy' -o -name 'G_*.pth' -o -name '*.safetensors' \) | grep -q .; then
    die "No usable StyleBERT model files found under ${MODEL_DIR}. Expected model subdirectories with config.json, style_vectors.npy, and model weights."
  fi
}

ensure_japanese_bert_weights() {
  local bert_dir="${STYLEBERT_DIR}/bert/deberta-v2-large-japanese-char-wwm"
  local weight_file="${bert_dir}/pytorch_model.bin"
  if [[ -f "${weight_file}" || -f "${bert_dir}/model.safetensors" ]]; then
    return 0
  fi
  if ! is_on "${AUTO_DOWNLOAD_BERT}"; then
    warn "Missing Japanese BERT weights: ${weight_file}"
    warn "Download with: STYLEBERT_VITS2_AUTO_DOWNLOAD_BERT=1 AI_NPC_System/scripts/start_stylebert_vits2_server.sh"
    warn "Or manually place ku-nlp/deberta-v2-large-japanese-char-wwm files under ${bert_dir}."
    return 0
  fi

  info "Downloading Japanese BERT weights to ${bert_dir}."
  mkdir -p "${bert_dir}"
  run_pip install -U huggingface_hub
  "${PYTHON_BIN}" - "${bert_dir}" <<'PY'
from pathlib import Path
import sys
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='ku-nlp/deberta-v2-large-japanese-char-wwm',
    local_dir=Path(sys.argv[1]),
    local_dir_use_symlinks=False,
    allow_patterns=['pytorch_model.bin', 'config.json', 'tokenizer*', 'vocab.txt', 'special_tokens_map.json'],
)
PY
}

print_launch_summary() {
  info "Starting Style-Bert-VITS2 server on http://${HOST}:${PORT}"
  info "Repo: ${STYLEBERT_DIR}"
  info "Python: ${PYTHON_BIN}"
  info "Model dir: ${MODEL_DIR}"
  info "CUDA_VISIBLE_DEVICES=${CUDA_DEVICES}"
  info "Auto fix=${AUTO_FIX}, auto install=${AUTO_INSTALL}, auto apt=${AUTO_APT}, auto BERT download=${AUTO_DOWNLOAD_BERT}"
}

normalize_shell_line_endings
require_vendor_repo
check_system_prereqs
ensure_venv
patch_requirements_for_python312
install_python_deps_if_needed
ensure_python312_compat_packages
ensure_stylebert_config
ensure_model_assets
ensure_japanese_bert_weights

cd "${STYLEBERT_DIR}"
export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
print_launch_summary
# Recent Style-Bert-VITS2 reads host/port from config.yml and accepts --dir only.
exec "${PYTHON_BIN}" server_fastapi.py --dir "${MODEL_DIR}"
