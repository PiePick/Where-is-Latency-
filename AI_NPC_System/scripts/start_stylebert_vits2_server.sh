#!/usr/bin/env bash
# Launch a local Style-Bert-VITS2 FastAPI server for CREDO FastTrack TTS.
# The preflight section handles common WSL/Python 3.12/StyleBERT drift issues.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
ENV_STYLEBERT_VITS2_LANGUAGE="${STYLEBERT_VITS2_LANGUAGE:-}"
ENV_STYLEBERT_VITS2_MODEL_NAME="${STYLEBERT_VITS2_MODEL_NAME:-}"
ENV_STYLEBERT_VITS2_DEVICE="${STYLEBERT_VITS2_DEVICE:-}"
ENV_STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES="${STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES:-}"
ENV_STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH="${STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH:-}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
fi
if [[ -n "${ENV_STYLEBERT_VITS2_LANGUAGE}" ]]; then
  export STYLEBERT_VITS2_LANGUAGE="${ENV_STYLEBERT_VITS2_LANGUAGE}"
fi
if [[ -n "${ENV_STYLEBERT_VITS2_MODEL_NAME}" ]]; then
  export STYLEBERT_VITS2_MODEL_NAME="${ENV_STYLEBERT_VITS2_MODEL_NAME}"
fi
if [[ -n "${ENV_STYLEBERT_VITS2_DEVICE}" ]]; then
  export STYLEBERT_VITS2_DEVICE="${ENV_STYLEBERT_VITS2_DEVICE}"
fi
if [[ -n "${ENV_STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES}" ]]; then
  export STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES="${ENV_STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES}"
fi
if [[ -n "${ENV_STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH}" ]]; then
  export STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH="${ENV_STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH}"
fi

STYLEBERT_DIR="${STYLEBERT_VITS2_REPO_DIR:-${ROOT_DIR}/vendor/Style-Bert-VITS2}"
PYTHON_BIN="${STYLEBERT_VITS2_PYTHON:-${STYLEBERT_DIR}/.venv/bin/python}"
HOST="${STYLEBERT_VITS2_HOST:-127.0.0.1}"
PORT="${STYLEBERT_VITS2_PORT:-5000}"
MODEL_DIR="${STYLEBERT_VITS2_MODEL_DIR:-${STYLEBERT_DIR}/model_assets}"
MODEL_NAME="${STYLEBERT_VITS2_MODEL_NAME:-}"
DEVICE="${STYLEBERT_VITS2_DEVICE:-cpu}"
DEVICE="$(printf '%s' "${DEVICE}" | tr '[:upper:]' '[:lower:]')"
CUDA_DEVICES="${STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES:-0}"
case "${DEVICE}" in
  cpu|cuda) ;;
  *) printf '[StyleBERT][ERROR] STYLEBERT_VITS2_DEVICE must be cpu or cuda, got: %s\n' "${DEVICE}" >&2; exit 1 ;;
esac
AUTO_FIX="${STYLEBERT_VITS2_AUTO_FIX:-1}"
AUTO_INSTALL="${STYLEBERT_VITS2_AUTO_INSTALL:-0}"
AUTO_APT="${STYLEBERT_VITS2_AUTO_APT:-0}"
AUTO_DOWNLOAD_BERT="${STYLEBERT_VITS2_AUTO_DOWNLOAD_BERT:-0}"
AUTO_DOWNLOAD_MODELS="${STYLEBERT_VITS2_AUTO_DOWNLOAD_MODELS:-0}"
ALLOW_LANGUAGE_MISMATCH="${STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH:-0}"
FASTTRACK_LANGUAGE="${STYLEBERT_VITS2_LANGUAGE:-EN}"
PYTHON_IMPORT_TIMEOUT="${STYLEBERT_VITS2_IMPORT_TIMEOUT:-90}"

info() { printf '[StyleBERT] %s\n' "$*"; }
warn() { printf '[StyleBERT][WARN] %s\n' "$*" >&2; }
die() { printf '[StyleBERT][ERROR] %s\n' "$*" >&2; exit 1; }
is_on() { case "${1:-0}" in 1|true|TRUE|yes|YES|on|ON) return 0 ;; *) return 1 ;; esac; }

run_pip() {
  "${PYTHON_BIN}" -m pip "$@"
}

run_python_check() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${seconds}" "${PYTHON_BIN}" "$@"
  else
    "${PYTHON_BIN}" "$@"
  fi
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
  info "Checking StyleBERT Python imports: fastapi, torch, uvicorn, yaml (timeout ${PYTHON_IMPORT_TIMEOUT}s)."
  if run_python_check "${PYTHON_IMPORT_TIMEOUT}" - <<'PY' >/dev/null 2>&1
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
  info "Checking Python 3.12 media compatibility imports: pkg_resources, av, faster_whisper (timeout ${PYTHON_IMPORT_TIMEOUT}s)."
  if run_python_check "${PYTHON_IMPORT_TIMEOUT}" - <<'PY' >/dev/null 2>&1
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

  info "Ensuring StyleBERT config.yml uses port ${PORT} and device ${DEVICE}."
  "${PYTHON_BIN}" - "${STYLEBERT_DIR}/config.yml" "${PORT}" "${DEVICE}" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
port = int(sys.argv[2])
device = sys.argv[3]
data = yaml.safe_load(path.read_text(encoding='utf-8'))
server = data.setdefault('server', {})
server['port'] = port
server['device'] = device
path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding='utf-8')
PY
}

has_stylebert_model_assets() {
  [[ -d "${MODEL_DIR}" ]] || return 1
  local first_match
  first_match="$(find "${MODEL_DIR}" -mindepth 2 \( -name 'config.json' -o -name 'style_vectors.npy' -o -name '*.pth' -o -name '*.pt' -o -name '*.safetensors' -o -name '*.onnx' \) -print -quit 2>/dev/null || true)"
  [[ -n "${first_match}" ]]
}

ensure_model_assets() {
  info "Checking StyleBERT model assets under ${MODEL_DIR}."
  if has_stylebert_model_assets; then
    return 0
  fi

  if is_on "${AUTO_DOWNLOAD_MODELS}"; then
    info "Downloading StyleBERT default inference models with initialize.py --only_infer."
    (cd "${STYLEBERT_DIR}" && "${PYTHON_BIN}" initialize.py --only_infer)
  fi

  if has_stylebert_model_assets; then
    return 0
  fi

  if [[ ! -d "${MODEL_DIR}" ]]; then
    die "Missing Style-Bert-VITS2 model assets: ${MODEL_DIR}. Place a CREDO-compatible model under model_assets or run STYLEBERT_VITS2_AUTO_DOWNLOAD_MODELS=1 ${0}."
  fi
  die "No usable StyleBERT model files found under ${MODEL_DIR}. Expected model subdirectories with config.json, style_vectors.npy, and model weights. For a temporary default voice, run: STYLEBERT_VITS2_AUTO_DOWNLOAD_MODELS=1 ${0}"
}

ensure_fasttrack_language_compatibility() {
  info "Checking StyleBERT model language compatibility for STYLEBERT_VITS2_LANGUAGE=${FASTTRACK_LANGUAGE}."
  if is_on "${ALLOW_LANGUAGE_MISMATCH}"; then
    warn "Skipping StyleBERT language/model compatibility check because STYLEBERT_VITS2_ALLOW_LANGUAGE_MISMATCH=1."
    return 0
  fi

  "${PYTHON_BIN}" - "${MODEL_DIR}" "${FASTTRACK_LANGUAGE}" "${MODEL_NAME}" <<'PY'
import json
import sys
from pathlib import Path

model_dir = Path(sys.argv[1])
language = sys.argv[2].upper()
model_name = sys.argv[3].strip()
configs = sorted(model_dir.glob('*/config.json'))
if not configs:
    raise SystemExit('No StyleBERT model config.json files found.')

if model_name:
    config_path = model_dir / model_name / 'config.json'
    if not config_path.exists():
        existing = ', '.join(path.parent.name for path in configs[:12])
        raise SystemExit(
            f'STYLEBERT_VITS2_MODEL_NAME={model_name!r} was requested, but {config_path} does not exist. '
            f'Existing model directories: {existing}'
        )
    check_paths = [config_path]
else:
    check_paths = configs

versions = []
for path in check_paths:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        continue
    versions.append(str(payload.get('version', '')))

jp_only = versions and all('JP' in version.upper() for version in versions)
if language != 'JP' and jp_only:
    names = ', '.join(path.parent.name for path in check_paths[:8])
    if model_name:
        detail = f'STYLEBERT_VITS2_MODEL_NAME={model_name} points to JP-only model ({names}).'
    else:
        detail = f'model_assets contains only JP-only models ({names}).'
    raise SystemExit(
        f'StyleBERT model/language mismatch: configured STYLEBERT_VITS2_LANGUAGE={language}, but {detail} '
        'Install a CREDO-compatible English StyleBERT model under vendor/Style-Bert-VITS2/model_assets/<model_name> '
        'and set STYLEBERT_VITS2_MODEL_NAME=<model_name>. '
        'STYLEBERT_VITS2_LANGUAGE=JP is only for temporary Japanese smoke tests, not CREDO English FastTrack.'
    )

if language != 'JP' and not model_name:
    names = ', '.join(path.parent.name for path in configs[:12])
    raise SystemExit(
        f'STYLEBERT_VITS2_LANGUAGE={language} requires explicit STYLEBERT_VITS2_MODEL_NAME so CREDO does not accidentally use JP default model_id=0. '
        f'Install/select an English model directory under model_assets and set STYLEBERT_VITS2_MODEL_NAME. Existing model directories: {names}'
    )
PY
}

ensure_japanese_bert_weights() {
  info "Checking StyleBERT Japanese BERT weights needed by the bundled default models."
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
  if [[ "${DEVICE}" == "cpu" ]]; then
    info "Device=cpu (system RAM mode; CUDA_VISIBLE_DEVICES is cleared for StyleBERT)"
  else
    info "Device=cuda, CUDA_VISIBLE_DEVICES=${CUDA_DEVICES}"
  fi
  info "Model name=${MODEL_NAME:-<unset>}, model_id=${STYLEBERT_VITS2_MODEL_ID:-0}"
  info "Auto fix=${AUTO_FIX}, auto install=${AUTO_INSTALL}, auto apt=${AUTO_APT}, auto model download=${AUTO_DOWNLOAD_MODELS}, auto BERT download=${AUTO_DOWNLOAD_BERT}, language=${FASTTRACK_LANGUAGE}, import timeout=${PYTHON_IMPORT_TIMEOUT}s"
}

info "Loaded CREDO config: ${CONFIG_FILE}"
info "StyleBERT preflight starts. If a step stalls, rerun with STYLEBERT_VITS2_IMPORT_TIMEOUT=30 for faster failure."
info "Preflight 1/10: normalize shell line endings."
normalize_shell_line_endings
info "Preflight 2/10: check vendor repo."
require_vendor_repo
info "Preflight 3/10: check Ubuntu packages."
check_system_prereqs
info "Preflight 4/10: check Python venv."
ensure_venv
info "Preflight 5/10: patch Python 3.12 incompatible requirement pins."
patch_requirements_for_python312
info "Preflight 6/10: check Python package imports."
install_python_deps_if_needed
info "Preflight 7/10: check Python 3.12 media compatibility."
ensure_python312_compat_packages
info "Preflight 8/10: ensure StyleBERT config."
ensure_stylebert_config
info "Preflight 9/10: check model assets."
ensure_model_assets
info "Preflight 10/10: check model/language compatibility and BERT weights."
ensure_fasttrack_language_compatibility
ensure_japanese_bert_weights

cd "${STYLEBERT_DIR}"
if [[ "${DEVICE}" == "cpu" ]]; then
  export CUDA_VISIBLE_DEVICES=""
else
  export CUDA_VISIBLE_DEVICES="${CUDA_DEVICES}"
fi
print_launch_summary
# Recent Style-Bert-VITS2 reads host/port from config.yml and accepts --dir only.
exec "${PYTHON_BIN}" server_fastapi.py --dir "${MODEL_DIR}"
