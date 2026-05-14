#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OLV_DIR="$ROOT_DIR/vendor/open-llm-vtuber"
VENV_DIR="$OLV_DIR/.venv"

if [[ ! -d "$OLV_DIR" ]]; then
  echo "Open-LLM-VTuber clone not found: $OLV_DIR" >&2
  exit 1
fi

cd "$OLV_DIR"
git submodule update --init --recursive

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  if python3 -m venv "$VENV_DIR" 2>/dev/null; then
    :
  else
    python3 -m pip install --user --break-system-packages virtualenv
    python3 -m virtualenv "$VENV_DIR"
  fi
fi

"$VENV_DIR/bin/python" -m pip install -r requirements.txt
"$VENV_DIR/bin/python" -m pip install "spacy>=3.7.0" "transformers>=4.38.0" "imageio-ffmpeg>=0.6.0"
"$VENV_DIR/bin/python" -m spacy download en_core_web_sm

# pydub expects an ffmpeg executable on PATH. Keep it inside the project venv
# so the runtime does not depend on system-level sudo package installation.
FFMPEG_EXE="$("$VENV_DIR/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
ln -sf "$FFMPEG_EXE" "$VENV_DIR/bin/ffmpeg"

cd "$ROOT_DIR"
"$VENV_DIR/bin/python" AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate

echo "Open-LLM-VTuber CREDO runtime is ready."
echo "Run: AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh"
