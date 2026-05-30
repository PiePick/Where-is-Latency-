"""HTTP adapter for Style-Bert-VITS2 FastTrack synthesis."""

from __future__ import annotations

import re
import time
import wave
import urllib.error
import urllib.parse
import urllib.request
from array import array
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import config
from tts_client import play_audio


def _stabilize_wav_bytes(audio: bytes) -> bytes:
    """Reduce clipping without shortening the generated StyleBERT waveform."""
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

        peak = max(abs(value) for value in samples) if samples else 0
        target_peak = int(32767 * 0.88)
        scale = min(1.0, target_peak / peak) if peak else 1.0
        fade_in_frames = min(frame_count, int(params.framerate * 0.008))
        fade_out_frames = min(frame_count, int(params.framerate * 0.006))

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
    except Exception:
        return audio


def _append_wav_silence(audio: bytes, silence_ms: int) -> bytes:
    """Append physical silence so players and lip-sync do not clip the tail."""
    silence_ms = max(0, int(silence_ms or 0))
    if silence_ms <= 0:
        return audio
    try:
        with wave.open(BytesIO(audio), "rb") as source:
            params = source.getparams()
            frames = source.readframes(source.getnframes())
        silence_frames = int(params.framerate * silence_ms / 1000.0)
        if silence_frames <= 0:
            return audio
        silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth
        output = BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(params.nchannels)
            target.setsampwidth(params.sampwidth)
            target.setframerate(params.framerate)
            target.setcomptype(params.comptype, params.compname)
            target.writeframes(frames + silence)
        return output.getvalue()
    except Exception:
        return audio


def _split_tts_sentences(text: str) -> list[str]:
    """Split spoken text at sentence boundaries so pauses can be physical silence."""
    stripped = (text or "").strip()
    if not stripped:
        return []
    parts: list[str] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+", stripped):
        segment = stripped[start:match.start()].strip()
        if segment:
            parts.append(segment)
        start = match.end()
    tail = stripped[start:].strip()
    if tail:
        parts.append(tail)
    return parts or [stripped]


def _join_wav_bytes(audio_parts: list[bytes], pause_ms: int) -> bytes:
    """Concatenate WAV chunks with a short silence between sentence chunks."""
    if not audio_parts:
        return b""
    if len(audio_parts) == 1 or pause_ms <= 0:
        return audio_parts[0]
    try:
        frames: list[bytes] = []
        params = None
        for audio in audio_parts:
            with wave.open(BytesIO(audio), "rb") as source:
                current = source.getparams()
                if params is None:
                    params = current
                elif (
                    current.nchannels != params.nchannels
                    or current.sampwidth != params.sampwidth
                    or current.framerate != params.framerate
                    or current.comptype != params.comptype
                ):
                    return audio_parts[0]
                frames.append(source.readframes(source.getnframes()))
        assert params is not None
        silence_frames = int(params.framerate * pause_ms / 1000.0)
        silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth
        output = BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(params.nchannels)
            target.setsampwidth(params.sampwidth)
            target.setframerate(params.framerate)
            target.setcomptype(params.comptype, params.compname)
            target.writeframes(silence.join(frames))
        return output.getvalue()
    except Exception:
        return audio_parts[0]


@dataclass(frozen=True)
class StyleBertVITS2Config:
    """HTTP settings for a local Style-Bert-VITS2 FastAPI server."""

    voice_url: str = config.STYLEBERT_VITS2_VOICE_URL
    health_url: str = config.STYLEBERT_VITS2_HEALTH_URL
    output_dir: Path = config.STYLEBERT_VITS2_OUTPUT_DIR
    timeout: float = config.STYLEBERT_VITS2_TIMEOUT
    model_id: int = config.STYLEBERT_VITS2_MODEL_ID
    model_name: str = config.STYLEBERT_VITS2_MODEL_NAME
    speaker_id: int = config.STYLEBERT_VITS2_SPEAKER_ID
    style: str = config.STYLEBERT_VITS2_STYLE
    style_weight: float = config.STYLEBERT_VITS2_STYLE_WEIGHT
    sdp_ratio: float = config.STYLEBERT_VITS2_SDP_RATIO
    noise: float = config.STYLEBERT_VITS2_NOISE
    noisew: float = config.STYLEBERT_VITS2_NOISEW
    length: float = config.STYLEBERT_VITS2_LENGTH
    sentence_pause_ms: int = config.STYLEBERT_VITS2_SENTENCE_PAUSE_MS
    trailing_silence_ms: int = config.STYLEBERT_VITS2_TRAILING_SILENCE_MS
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
        preserve_text_edges: bool = False,
    ) -> Path:
        """Synthesize text and write the returned wav bytes to disk."""
        raw_text = str(text or "")
        if not raw_text.strip():
            raise ValueError("Cannot synthesize empty text.")
        text = raw_text if preserve_text_edges else raw_text.strip()

        def request_audio(segment: str) -> bytes:
            params = {
                "text": segment,
                "model_id": str(self.cfg.model_id),
                "speaker_id": str(self.cfg.speaker_id),
                "style": style or self.cfg.style,
                "style_weight": str(self.cfg.style_weight if style_weight is None else style_weight),
                "sdp_ratio": str(self.cfg.sdp_ratio),
                "noise": str(self.cfg.noise),
                "noisew": str(self.cfg.noisew),
                "length": str(self.cfg.length),
                "language": self.cfg.language,
            }
            if self.cfg.model_name:
                params["model_name"] = self.cfg.model_name
            separator = "&" if "?" in self.cfg.voice_url else "?"
            url = f"{self.cfg.voice_url}{separator}{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "audio/wav",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.cfg.timeout) as response:
                    return _stabilize_wav_bytes(response.read())
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Style-Bert-VITS2 failed: HTTP {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"Style-Bert-VITS2 server is unreachable at {self.cfg.voice_url}: {exc}") from exc

        segments = (
            [text]
            if preserve_text_edges
            else (_split_tts_sentences(text) if self.cfg.sentence_pause_ms > 0 else [text])
        )
        audio = _join_wav_bytes([request_audio(segment) for segment in segments], self.cfg.sentence_pause_ms)
        audio = _append_wav_silence(audio, self.cfg.trailing_silence_ms)

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
