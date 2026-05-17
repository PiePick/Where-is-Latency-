"""HTTP adapter for Style-Bert-VITS2 FastTrack synthesis."""

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
class StyleBertVITS2Config:
    """HTTP settings for a local Style-Bert-VITS2 FastAPI server."""

    voice_url: str = config.STYLEBERT_VITS2_VOICE_URL
    health_url: str = config.STYLEBERT_VITS2_HEALTH_URL
    output_dir: Path = config.STYLEBERT_VITS2_OUTPUT_DIR
    timeout: float = config.STYLEBERT_VITS2_TIMEOUT
    model_id: int = config.STYLEBERT_VITS2_MODEL_ID
    speaker_id: int = config.STYLEBERT_VITS2_SPEAKER_ID
    style: str = config.STYLEBERT_VITS2_STYLE
    style_weight: float = config.STYLEBERT_VITS2_STYLE_WEIGHT
    language: str = config.STYLEBERT_VITS2_LANGUAGE
    auto_play: bool = config.STYLEBERT_VITS2_AUTO_PLAY


class StyleBertVITS2Client:
    """Small client for short FastTrack utterances through Style-Bert-VITS2."""

    def __init__(self, cfg: StyleBertVITS2Config | None = None) -> None:
        self.cfg = cfg or StyleBertVITS2Config()
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)

    def is_healthy(self) -> bool:
        """Check whether the Style-Bert-VITS2 server is reachable."""
        try:
            with urllib.request.urlopen(self.cfg.health_url, timeout=3.0) as response:
                return 200 <= response.status < 500
        except Exception:
            return False

    def synthesize_to_file(
        self,
        text: str,
        *,
        prefix: str = "stylebert_fast",
        style: str | None = None,
        style_weight: float | None = None,
    ) -> Path:
        """Synthesize text and write the returned wav bytes to disk."""
        text = text.strip()
        if not text:
            raise ValueError("Cannot synthesize empty text.")

        params = {
            "text": text,
            "model_id": str(self.cfg.model_id),
            "speaker_id": str(self.cfg.speaker_id),
            "style": style or self.cfg.style,
            "style_weight": str(self.cfg.style_weight if style_weight is None else style_weight),
            "language": self.cfg.language,
        }
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            self.cfg.voice_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "audio/wav",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout) as response:
                audio = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Style-Bert-VITS2 failed: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Style-Bert-VITS2 server is unreachable at {self.cfg.voice_url}: {exc}") from exc

        out_path = self.cfg.output_dir / f"{prefix}_{int(time.time() * 1000)}.wav"
        out_path.write_bytes(audio)
        return out_path

    def speak(
        self,
        text: str,
        *,
        prefix: str = "stylebert_fast",
        style: str | None = None,
        style_weight: float | None = None,
    ) -> Path:
        """Synthesize and optionally play a FastTrack reaction."""
        path = self.synthesize_to_file(
            text,
            prefix=prefix,
            style=style,
            style_weight=style_weight,
        )
        if self.cfg.auto_play:
            play_audio(path)
        return path
