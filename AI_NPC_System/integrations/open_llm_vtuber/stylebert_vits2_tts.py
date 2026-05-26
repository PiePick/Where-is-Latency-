"""Open-LLM-VTuber TTS adapter for the local CREDO Style-Bert-VITS2 server."""

from __future__ import annotations

import os
import re
import time
import wave
import urllib.error
import urllib.parse
import urllib.request
from array import array
from io import BytesIO
from pathlib import Path

from loguru import logger

from .tts_interface import TTSInterface


def _resolve_project_root() -> Path:
    """Find the CREDO workspace so relative output paths stay stable."""
    configured = os.getenv("CREDO_AI_NPC_PATH")
    if configured:
        return Path(configured).expanduser().resolve().parent

    current = Path(__file__).resolve()
    for candidate in (Path.cwd(), current, *current.parents):
        if (candidate / "AI_NPC_System" / "project_config.sh").exists():
            return candidate
    return Path.cwd().resolve()


def _safe_name(value: str | None) -> str:
    """Keep generated filenames readable while avoiding path control chars."""
    if not value:
        value = "stylebert"
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())[:96].strip("._")
    return value or "stylebert"


def _stabilize_wav_bytes(audio: bytes) -> bytes:
    """Reduce clipping and short model tail artifacts in StyleBERT output."""
    try:
        with wave.open(BytesIO(audio), "rb") as source:
            params = source.getparams()
            if params.sampwidth != 2 or params.nframes <= 0:
                return audio
            frame_bytes = source.readframes(params.nframes)

        samples = array("h")
        samples.frombytes(frame_bytes)
        channels = max(1, params.nchannels)
        frame_count = len(samples) // channels
        if frame_count <= 0:
            return audio

        trim_frames = int(params.framerate * 0.08) if frame_count > int(params.framerate * 0.9) else 0
        if trim_frames and frame_count - trim_frames > int(params.framerate * 0.25):
            del samples[(frame_count - trim_frames) * channels :]
            frame_count -= trim_frames

        peak = max(abs(value) for value in samples) if samples else 0
        target_peak = int(32767 * 0.88)
        scale = min(1.0, target_peak / peak) if peak else 1.0
        fade_in_frames = min(frame_count, int(params.framerate * 0.008))
        fade_out_frames = min(frame_count, int(params.framerate * 0.08))

        for frame_index in range(frame_count):
            gain = scale
            if fade_in_frames and frame_index < fade_in_frames:
                gain *= frame_index / fade_in_frames
            if fade_out_frames and frame_index >= frame_count - fade_out_frames:
                gain *= (frame_count - frame_index - 1) / fade_out_frames
            if gain == 1.0:
                continue
            for channel in range(channels):
                sample_index = frame_index * channels + channel
                samples[sample_index] = max(-32768, min(32767, int(samples[sample_index] * gain)))

        output = BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(params.nchannels)
            target.setsampwidth(params.sampwidth)
            target.setframerate(params.framerate)
            target.setcomptype(params.comptype, params.compname)
            target.writeframes(samples.tobytes())
        return output.getvalue()
    except Exception as exc:
        logger.debug(f"StyleBERT wav stabilization skipped: {exc}")
        return audio


class TTSEngine(TTSInterface):
    """Synthesize Open-LLM-VTuber speech through CREDO Style-Bert-VITS2."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5000",
        voice_url: str | None = None,
        health_url: str | None = None,
        output_dir: str = "AI_NPC_System/tts_outputs/stylebert_open_llm",
        timeout: float = 30.0,
        model_id: int = 0,
        model_name: str = "credo_voice_sample_en",
        speaker_id: int = 0,
        style: str = "Neutral",
        style_weight: float = 1.0,
        sdp_ratio: float = 0.1,
        noise: float = 0.35,
        noisew: float = 0.45,
        length: float = 0.95,
        language: str = "EN",
        **_: object,
    ) -> None:
        self.base_url = (base_url or "http://127.0.0.1:5000").rstrip("/")
        self.voice_url = voice_url or f"{self.base_url}/voice"
        self.health_url = health_url or f"{self.base_url}/docs"
        self.timeout = float(timeout)
        self.model_id = int(model_id)
        self.model_name = model_name or "credo_voice_sample_en"
        self.speaker_id = int(speaker_id)
        self.style = style or "Neutral"
        self.style_weight = float(style_weight)
        self.sdp_ratio = float(sdp_ratio)
        self.noise = float(noise)
        self.noisew = float(noisew)
        self.length = float(length)
        self.language = language or "EN"

        output_path = Path(output_dir).expanduser()
        if not output_path.is_absolute():
            output_path = _resolve_project_root() / output_path
        self.output_dir = output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_audio(self, text: str, file_name_no_ext=None) -> str | None:
        """Generate one wav file and return its path for Open-LLM playback."""
        text = (text or "").strip()
        if not text:
            logger.warning("StyleBERT TTS skipped empty text.")
            return None

        params = {
            "text": text,
            "model_id": str(self.model_id),
            "speaker_id": str(self.speaker_id),
            "style": self.style,
            "style_weight": str(self.style_weight),
            "sdp_ratio": str(self.sdp_ratio),
            "noise": str(self.noise),
            "noisew": str(self.noisew),
            "length": str(self.length),
            "language": self.language,
        }
        if self.model_name:
            params["model_name"] = self.model_name

        separator = "&" if "?" in self.voice_url else "?"
        url = f"{self.voice_url}{separator}{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "audio/wav",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                audio_bytes = _stabilize_wav_bytes(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error(f"StyleBERT TTS failed: HTTP {exc.code}: {body}")
            return None
        except urllib.error.URLError as exc:
            logger.error(f"StyleBERT server is unreachable at {self.voice_url}: {exc}")
            return None

        filename = f"{_safe_name(file_name_no_ext)}_{int(time.time() * 1000)}.wav"
        audio_path = self.output_dir / filename
        audio_path.write_bytes(audio_bytes)
        return str(audio_path)
