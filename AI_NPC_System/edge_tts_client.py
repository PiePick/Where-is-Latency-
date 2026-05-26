"""Realtime Edge TTS adapter used by CREDO live FastTrack and prefetch."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import config


EDGE_TTS_VOICE_CANDIDATES = config.EDGE_TTS_VOICE_CANDIDATES
ACTIVE_VOICE_KEY = config.ACTIVE_VOICE_KEY


@dataclass(frozen=True)
class EdgeTTSConfig:
    """Live Edge TTS voice and output settings."""

    voice: str = config.OPEN_LLM_VTUBER_EDGE_TTS_VOICE
    output_dir: Path = config.EDGE_TTS_OUTPUT_DIR
    max_retained_files: int = config.EDGE_TTS_MAX_RETAINED_FILES
    connect_timeout: int = config.EDGE_TTS_CONNECT_TIMEOUT
    receive_timeout: int = config.EDGE_TTS_RECEIVE_TIMEOUT


class EdgeTTSClient:
    """Generate live audio with the same Edge engine used by Open-LLM-VTuber."""

    def __init__(self, cfg: EdgeTTSConfig | None = None) -> None:
        self.cfg = cfg or EdgeTTSConfig()
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)

    def synthesize_to_file(self, text: str, *, prefix: str = "edge_live") -> Path:
        """Synthesize one utterance into an MP3 file and return its path."""
        import edge_tts

        text = " ".join(str(text or "").split()).strip()
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        out_path = self.cfg.output_dir / (
            f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}.mp3"
        )
        edge_tts.Communicate(
            text,
            self.cfg.voice,
            connect_timeout=self.cfg.connect_timeout,
            receive_timeout=self.cfg.receive_timeout,
        ).save_sync(str(out_path))
        self._prune_old_output_files(exclude=out_path)
        return out_path

    def _prune_old_output_files(self, *, exclude: Path) -> None:
        """Bound prefetch/direct-audio files that bypass native TTS cleanup."""
        keep = max(1, int(self.cfg.max_retained_files))
        audio_files = sorted(
            (path for path in self.cfg.output_dir.glob("*.mp3") if path != exclude),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale_path in audio_files[max(0, keep - 1):]:
            try:
                stale_path.unlink()
            except OSError:
                pass
