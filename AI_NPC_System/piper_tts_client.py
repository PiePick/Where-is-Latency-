"""CLI adapter for Piper FastTrack synthesis."""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import config
from tts_client import play_audio


@dataclass(frozen=True)
class PiperTTSConfig:
    """Local Piper command settings for short FastTrack utterances."""

    voice_url: str = config.PIPER_TTS_VOICE_URL
    health_url: str = config.PIPER_TTS_HEALTH_URL
    binary: Path = config.PIPER_TTS_BIN
    model_path: Path = config.PIPER_TTS_MODEL_PATH
    config_path: Path = config.PIPER_TTS_CONFIG_PATH
    output_dir: Path = config.PIPER_TTS_OUTPUT_DIR
    timeout: float = config.PIPER_TTS_TIMEOUT
    use_cuda: bool = config.PIPER_TTS_USE_CUDA
    speaker_id: str = config.PIPER_TTS_SPEAKER_ID
    length_scale: float = config.PIPER_TTS_LENGTH_SCALE
    noise_scale: float = config.PIPER_TTS_NOISE_SCALE
    noise_w: float = config.PIPER_TTS_NOISE_W
    auto_play: bool = False


class PiperTTSClient:
    """Synthesize FastTrack reactions with Piper without a resident server."""

    def __init__(self, cfg: PiperTTSConfig | None = None) -> None:
        self.cfg = cfg or PiperTTSConfig()
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)

    def is_ready(self) -> tuple[bool, str]:
        """Return whether the resident Piper FastTrack server is reachable."""
        try:
            with urllib.request.urlopen(self.cfg.health_url, timeout=5.0) as response:
                if 200 <= response.status < 500:
                    return True, "Piper FastTrack TTS server is ready."
                return False, f"Piper health returned HTTP {response.status}: {self.cfg.health_url}"
        except Exception as exc:
            return False, f"Piper FastTrack TTS server is unreachable at {self.cfg.health_url}: {exc}"

    def synthesize_to_file(
        self,
        text: str,
        *,
        prefix: str = "piper_fast",
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_w: float | None = None,
    ) -> Path:
        """Synthesize text by invoking Piper's CLI and return a wav path."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        ready, reason = self.is_ready()
        if not ready:
            raise RuntimeError(reason)

        payload = {
            "text": text,
            "length_scale": str(self.cfg.length_scale if length_scale is None else length_scale),
            "noise_scale": str(self.cfg.noise_scale if noise_scale is None else noise_scale),
            "noise_w": str(self.cfg.noise_w if noise_w is None else noise_w),
        }
        if self.cfg.speaker_id:
            payload["speaker_id"] = self.cfg.speaker_id
        req = urllib.request.Request(
            self.cfg.voice_url,
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "audio/wav"},
            method="POST",
        )
        audio = self._request_audio(req)

        out_path = self.cfg.output_dir / f"{prefix}_{int(time.time() * 1000)}.wav"
        out_path.write_bytes(audio)
        return out_path

    def _request_audio(self, req: urllib.request.Request) -> bytes:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if 500 <= exc.code < 600 and attempt < 3:
                    last_error = exc
                    time.sleep(0.5 * attempt)
                    continue
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Piper FastTrack failed: HTTP {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(0.5 * attempt)
                    continue
                raise RuntimeError(f"Piper FastTrack server is unreachable at {self.cfg.voice_url}: {exc}") from exc
        raise RuntimeError(f"Piper FastTrack failed after retries: {last_error}")

    def speak(
        self,
        text: str,
        *,
        prefix: str = "piper_fast",
        length_scale: float | None = None,
        noise_scale: float | None = None,
        noise_w: float | None = None,
    ) -> Path:
        """Synthesize and optionally play a FastTrack reaction."""
        path = self.synthesize_to_file(
            text,
            prefix=prefix,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
        )
        if self.cfg.auto_play:
            play_audio(path)
        return path
