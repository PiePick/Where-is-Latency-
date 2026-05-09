"""HTTP adapter for a local Fish Speech API server."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass(frozen=True)
class FishSpeechTTSConfig:
    tts_url: str = config.FISH_SPEECH_TTS_URL
    health_url: str = config.FISH_SPEECH_HEALTH_URL
    api_key: str = config.FISH_SPEECH_API_KEY
    reference_id: str | None = config.FISH_SPEECH_REFERENCE_ID
    output_dir: Path = config.FISH_SPEECH_OUTPUT_DIR
    audio_format: str = config.FISH_SPEECH_FORMAT
    timeout: float = config.FISH_SPEECH_TIMEOUT
    top_p: float = config.FISH_SPEECH_TOP_P
    temperature: float = config.FISH_SPEECH_TEMPERATURE
    repetition_penalty: float = config.FISH_SPEECH_REPETITION_PENALTY
    max_new_tokens: int = config.FISH_SPEECH_MAX_NEW_TOKENS
    chunk_length: int = config.FISH_SPEECH_CHUNK_LENGTH
    auto_play: bool = config.FISH_SPEECH_AUTO_PLAY


class FishSpeechTTSClient:
    def __init__(self, cfg: FishSpeechTTSConfig | None = None) -> None:
        self.cfg = cfg or FishSpeechTTSConfig()
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)

    def is_healthy(self) -> bool:
        req = urllib.request.Request(self.cfg.health_url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3.0) as response:
                return response.status == 200
        except Exception:
            return False

    def synthesize_to_file(self, text: str, *, prefix: str = "tts") -> Path:
        text = text.strip()
        if not text:
            raise ValueError("Cannot synthesize empty text.")

        payload = {
            "text": text,
            "format": self.cfg.audio_format,
            "references": [],
            "reference_id": self.cfg.reference_id,
            "normalize": True,
            "streaming": False,
            "max_new_tokens": self.cfg.max_new_tokens,
            "chunk_length": self.cfg.chunk_length,
            "top_p": self.cfg.top_p,
            "repetition_penalty": self.cfg.repetition_penalty,
            "temperature": self.cfg.temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": self._accept_header(),
        }
        if self.cfg.api_key:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"

        req = urllib.request.Request(self.cfg.tts_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout) as response:
                audio = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Fish Speech TTS failed: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Fish Speech TTS server is unreachable at {self.cfg.tts_url}: {exc}") from exc

        suffix = self.cfg.audio_format
        out_path = self.cfg.output_dir / f"{prefix}_{int(time.time() * 1000)}.{suffix}"
        out_path.write_bytes(audio)
        return out_path

    def speak(self, text: str, *, prefix: str = "tts") -> Path:
        audio_path = self.synthesize_to_file(text, prefix=prefix)
        if self.cfg.auto_play:
            play_audio(audio_path)
        return audio_path

    def _accept_header(self) -> str:
        if self.cfg.audio_format == "wav":
            return "audio/wav"
        if self.cfg.audio_format == "mp3":
            return "audio/mpeg"
        if self.cfg.audio_format == "opus":
            return "audio/ogg"
        return "application/octet-stream"


def play_audio(audio_path: Path) -> bool:
    audio_path = audio_path.resolve()

    # WSL can usually delegate playback to Windows.
    if _is_wsl() and shutil.which("powershell.exe"):
        try:
            windows_path = subprocess.check_output(
                ["wslpath", "-w", str(audio_path)],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            script = (
                "$player = New-Object System.Media.SoundPlayer "
                f"'{windows_path}'; $player.PlaySync()"
            )
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            pass

    players = [
        ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(audio_path)]),
        ("afplay", ["afplay", str(audio_path)]),
        ("aplay", ["aplay", str(audio_path)]),
        ("paplay", ["paplay", str(audio_path)]),
    ]
    for binary, command in players:
        if not shutil.which(binary):
            continue
        try:
            subprocess.run(command, check=False)
            return True
        except Exception:
            continue
    return False


def _is_wsl() -> bool:
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
        return "microsoft" in release or "wsl" in release
    except OSError:
        return False
