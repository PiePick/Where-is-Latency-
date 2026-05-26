#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${CREDO_PROJECT_CONFIG:-${ROOT_DIR}/AI_NPC_System/project_config.sh}"
declare -A USER_OVERRIDES=()
for key in \
  FAST_TRACK_ENABLED \
  FAST_TRACK_TTS_MODE \
  FAST_TRACK_PERSONA_BUNDLE_ENABLED \
  FAST_TRACK_PERSONA_BUNDLE_FILE \
  FAST_TRACK_DATASET_POOL_FILE \
  FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK \
  FAST_TRACK_PREBUILT_ONLY \
  OPEN_LLM_VTUBER_TTS_MODEL \
  OPEN_LLM_VTUBER_SLOW_TTS_MODE \
  SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK \
  CREDO_VTUBER_SLOW_PREFETCH_ENABLED; do
  if [[ -v "${key}" ]]; then
    USER_OVERRIDES["${key}"]="${!key}"
  fi
done
if [ -f "${CONFIG_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${CONFIG_FILE}"
  set +a
fi
for key in "${!USER_OVERRIDES[@]}"; do
  export "${key}=${USER_OVERRIDES[${key}]}"
done

OLV_DIR="$ROOT_DIR/vendor/open-llm-vtuber"
VENV_DIR="$OLV_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Runtime is not installed. Run:" >&2
  echo "  AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh" >&2
  exit 1
fi

export CREDO_AI_NPC_PATH="${CREDO_AI_NPC_PATH:-$ROOT_DIR/AI_NPC_System}"
export FAST_TRACK_DEVICE="${FAST_TRACK_DEVICE:-cpu}"
export LOCAL_LLM_BASE_URL="${LOCAL_LLM_BASE_URL:-http://${LOCAL_LLM_HOST:-127.0.0.1}:${LOCAL_LLM_PORT:-8001}/v1}"
export LOCAL_LLM_MODEL="${LOCAL_LLM_MODEL:-${LOCAL_LLM_SERVED_MODEL_NAME:-qwen2.5:7b}}"
export FALLBACK_LOCAL_LLM_BASE_URL="${FALLBACK_LOCAL_LLM_BASE_URL:-$LOCAL_LLM_BASE_URL}"
export FALLBACK_LOCAL_LLM_MODEL="${FALLBACK_LOCAL_LLM_MODEL:-$LOCAL_LLM_MODEL}"
export PATH="$VENV_DIR/bin:$PATH"

allow_open_llm_fast_tts=0
case "${FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK:-0}" in
  1|true|TRUE|yes|YES|on|ON) allow_open_llm_fast_tts=1 ;;
esac

fast_track_enabled=1
case "${FAST_TRACK_ENABLED:-1}" in
  0|false|FALSE|no|NO|off|OFF) fast_track_enabled=0 ;;
esac

resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$ROOT_DIR" "$1" ;;
  esac
}

fast_tts_mode="${FAST_TRACK_TTS_MODE:-edge_tts}"
open_llm_tts_status="$("$ROOT_DIR/AI_NPC_System/scripts/select_tts_engine.py" --status 2>/dev/null || true)"
open_llm_tts_model="$(printf '%s\n' "${open_llm_tts_status}" | awk -F': ' '/Open-LLM-VTuber TTS/ {print $2; exit}')"
open_llm_tts_model="${open_llm_tts_model:-${OPEN_LLM_VTUBER_TTS_MODEL:-unknown}}"

if [[ "${open_llm_tts_model}" == "cosyvoice2_tts" ]]; then
  cosy_health="${COSYVOICE2_HEALTH_URL:-http://127.0.0.1:50000/}"
  if ! "$VENV_DIR/bin/python" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1.5).close()' "${cosy_health}" >/dev/null 2>&1; then
    echo "Open-LLM-VTuber TTS is set to CosyVoice2, but its server is not ready." >&2
    echo "Start it first:" >&2
    echo "  AI_NPC_System/scripts/start_cosyvoice2_server.sh" >&2
    echo "Or switch to a serverless default:" >&2
    echo "  AI_NPC_System/scripts/select_tts_engine.py edge --check" >&2
    echo "Health URL checked: ${cosy_health}" >&2
    exit 2
  fi
fi

if [[ "${fast_track_enabled}" == "1" && "${allow_open_llm_fast_tts}" != "1" && "${fast_tts_mode}" == "piper_tts" ]]; then
  piper_health="${PIPER_TTS_HEALTH_URL:-http://127.0.0.1:5001/health}"
  if ! "$VENV_DIR/bin/python" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1.5).close()' "${piper_health}" >/dev/null 2>&1; then
    echo "FastTrack realtime lightweight TTS is not ready." >&2
    echo "Open-LLM-VTuber default TTS fallback is disabled to avoid the wrong cute FastTrack voice." >&2
    echo "CREDO now uses a resident Piper FastTrack TTS server to avoid CLI cold-start latency." >&2
    echo "Prepare Piper once if needed:" >&2
    echo "  PIPER_TTS_AUTO_INSTALL=1 PIPER_TTS_AUTO_DOWNLOAD_VOICE=1 AI_NPC_System/scripts/setup_piper_fasttrack_tts.sh" >&2
    echo "Then start the FastTrack TTS server:" >&2
    echo "  AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh" >&2
    echo "Health URL checked: ${piper_health}" >&2
    exit 2
  fi
fi

stylebert_required=0
if [[ "${open_llm_tts_model}" == "stylebert_vits2" ]]; then
  stylebert_required=1
fi
if [[ "${fast_track_enabled}" == "1" && "${fast_tts_mode}" == "stylebert_vits2" ]]; then
  stylebert_required=1
fi

stylebert_ready=0
if [[ "${stylebert_required}" == "1" ]]; then
  if "$VENV_DIR/bin/python" -c 'import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1.5).close()'     "${STYLEBERT_VITS2_HEALTH_URL:-http://127.0.0.1:5000/docs}" >/dev/null 2>&1; then
    stylebert_ready=1
  fi
fi

if [[ "${stylebert_required}" == "1" && "${stylebert_ready}" != "1" ]]; then
  echo "CREDO StyleBERT TTS is not ready." >&2
  echo "Start the selected CREDO VoiceSample StyleBERT server first:" >&2
  echo "  AI_NPC_System/scripts/start_stylebert_vits2_server.sh" >&2
  echo "StyleBERT health URL checked: ${STYLEBERT_VITS2_HEALTH_URL:-http://127.0.0.1:5000/docs}" >&2
  exit 2
fi

if [[ "${fast_track_enabled}" == "1" && "${allow_open_llm_fast_tts}" != "1" && "${fast_tts_mode}" == "cached_fish_bundle" ]]; then
  if ! "$VENV_DIR/bin/python" -c 'import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0, str(root/"AI_NPC_System")); import config; from fast_track_audio_cache import PersonaReactionBundle; bundle=PersonaReactionBundle(config.FAST_TRACK_PERSONA_BUNDLE_PATH, enabled=config.FAST_TRACK_PERSONA_BUNDLE_ENABLED, seed=20260514, expected_reference_id=config.FAST_TRACK_AUDIO_CACHE_REFERENCE_ID, personality_id=config.FAST_TRACK_PERSONA_ID); raise SystemExit(0 if bundle.available else 1)' "$ROOT_DIR" >/dev/null 2>&1; then
    echo "FastTrack cached Fish bundle is not available." >&2
    echo "Expected legacy manifest: ${FAST_TRACK_PERSONA_BUNDLE_FILE:-archive/legacy_manifests/persona_reaction_bundle_response_act_probe/manifest.json}" >&2
    echo "Expected reference id: ${FAST_TRACK_AUDIO_CACHE_REFERENCE_ID:-unset}" >&2
    echo "FastTrack fallback is disabled, so Open-LLM-VTuber would appear silent before SlowTrack." >&2
    echo "Point FAST_TRACK_PERSONA_BUNDLE_FILE at a legacy manifest with existing audio_path files, or use the default StyleBERT realtime path." >&2
    exit 2
  fi
fi

cd "$ROOT_DIR"
"$VENV_DIR/bin/python" AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate

cd "$OLV_DIR"
echo "Starting Open-LLM-VTuber with CREDO latency-cover agent."
echo "Open: http://localhost:12393"
echo "CREDO config: ${CONFIG_FILE}"
echo "SlowTrack LLM: ${LOCAL_LLM_MODEL} (${LOCAL_LLM_BASE_URL})"
echo "Open-LLM-VTuber TTS: ${open_llm_tts_model}"
if [[ "${fast_track_enabled}" == "1" ]]; then
  echo "FastTrack: enabled (${FAST_TRACK_TTS_MODE:-edge_tts})"
else
  echo "FastTrack: disabled (SlowTrack-only experiment)"
fi
echo "Compute placement: FastTrack TTS ${FAST_TRACK_TTS_MODE:-edge_tts}, Local LLM GPU${LOCAL_LLM_CUDA_VISIBLE_DEVICES:-1}"
if [[ "${OPEN_LLM_VTUBER_SLOW_TTS_MODE:-open_llm}" == "credo_fish_speech" ]]; then
  echo "SlowTrack Fish Speech: GPU${FISH_SPEECH_CUDA_VISIBLE_DEVICES:-0}"
else
  echo "SlowTrack realtime TTS: ${open_llm_tts_model}"
fi
exec "$VENV_DIR/bin/python" run_server.py
