"""Local text chat loop with Fast/Slow Track and Fish Speech TTS output."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import fast_track
import slow_track
from tts_client import FishSpeechTTSClient, play_audio


def _read_user_text() -> str | None:
    """Read one console turn; None means the user wants to stop."""
    try:
        text = input("\nUser: ").strip()
    except EOFError:
        return None
    if not text:
        return ""
    if text.lower() in {"exit", "quit", "q"}:
        return None
    return text


def _speak_or_log(tts: FishSpeechTTSClient, text: str, prefix: str) -> None:
    """Use Fish Speech when available, but keep text chat usable without it."""
    try:
        audio_path = tts.speak(text, prefix=prefix)
        print(f"{prefix} audio: {audio_path}")
    except Exception as exc:
        print(f"{prefix} TTS skipped: {exc}")


def _play_fast_cover_or_synthesize(tts: FishSpeechTTSClient, fast_result: dict, text: str) -> None:
    """Play cached FastTrack audio before falling back to live TTS synthesis."""
    audio_path = fast_result.get("fast_audio_path")
    if audio_path:
        path = Path(audio_path)
        if path.exists():
            played = play_audio(path)
            status = "played" if played else "ready; no local player found"
            print(f"fast cached audio {status}: {path}")
            return
        print(f"fast cached audio unavailable: {audio_path}")
    _speak_or_log(tts, text, "fast")


async def run_cycle() -> None:
    """Run a local chat loop: FastTrack first, SlowTrack second."""
    print("AI NPC local chat started. Type exit to quit.")
    tts = FishSpeechTTSClient()
    if tts.is_healthy():
        print("Fish Speech TTS server is ready.")
    else:
        print("Fish Speech TTS server is not reachable; text generation will still run.")

    while True:
        user_input = _read_user_text()
        if user_input is None:
            break
        if not user_input:
            continue

        started = time.time()
        # FastTrack returns immediately usable text plus metadata for logs/UI.
        fast_result = fast_track.analyze_and_react(user_input)
        fast_text = fast_result.get("tts_text") or fast_result["reaction"]
        print(
            "FastTrack: "
            f"{fast_text} "
            f"(emotion={fast_result['emotion_label']}, "
            f"source={fast_result.get('reaction_source')}, "
            f"cache={fast_result.get('fast_audio_cache_hit')}, "
            f"cue={fast_result.get('fish_speech_cue')})"
        )
        _play_fast_cover_or_synthesize(tts, fast_result, fast_text)

        # SlowTrack can spend more time on a natural full response.
        slow_text = await slow_track.generate_response(
            user_input,
            fast_text,
            fast_result.get("strategy"),
        )
        print(f"SlowTrack: {slow_text}")
        _speak_or_log(tts, slow_text, "slow")

        elapsed = time.time() - started
        print(f"cycle_seconds={elapsed:.3f}")


if __name__ == "__main__":
    try:
        asyncio.run(run_cycle())
    except KeyboardInterrupt:
        print("\nStopped.")
