#!/usr/bin/env python3
"""Small resident Piper HTTP server for CREDO FastTrack TTS."""

from __future__ import annotations

import io
import json
import sys
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from piper import PiperVoice, SynthesisConfig  # noqa: E402

VOICE = PiperVoice.load(
    config.PIPER_TTS_MODEL_PATH,
    config_path=config.PIPER_TTS_CONFIG_PATH,
    use_cuda=config.PIPER_TTS_USE_CUDA,
)


def _float_param(payload: dict[str, object], name: str, default: float) -> float:
    raw = payload.get(name, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _speaker(payload: dict[str, object]) -> int | None:
    raw = payload.get("speaker_id", config.PIPER_TTS_SPEAKER_ID)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "CREDOPiperFastTrack/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[PiperFastTrack] {self.address_string()} - {fmt % args}")

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/docs"}:
            self._send_json(200, {
                "status": "ok",
                "engine": "piper_tts",
                "voice": config.PIPER_TTS_VOICE,
                "model": str(config.PIPER_TTS_MODEL_PATH),
            })
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/voice":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            payload = json.loads(raw.decode("utf-8") or "{}")
        else:
            payload = {key: values[-1] for key, values in parse_qs(raw.decode("utf-8")).items()}

        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_json(400, {"error": "text is required"})
            return

        syn_config = SynthesisConfig(
            speaker_id=_speaker(payload),
            length_scale=_float_param(payload, "length_scale", config.PIPER_TTS_LENGTH_SCALE),
            noise_scale=_float_param(payload, "noise_scale", config.PIPER_TTS_NOISE_SCALE),
            noise_w_scale=_float_param(payload, "noise_w", config.PIPER_TTS_NOISE_W),
        )
        audio = io.BytesIO()
        with wave.open(audio, "wb") as wav_file:
            VOICE.synthesize_wav(text, wav_file, syn_config=syn_config)
        data = audio.getvalue()

        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    host = config.PIPER_TTS_HOST
    port = config.PIPER_TTS_PORT
    print(f"[PiperFastTrack] loaded {config.PIPER_TTS_MODEL_PATH}")
    print(f"[PiperFastTrack] serving http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
