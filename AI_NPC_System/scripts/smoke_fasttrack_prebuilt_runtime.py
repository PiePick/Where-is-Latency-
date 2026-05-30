#!/usr/bin/env python3
"""Smoke-test FastTrack router prebuilt wav lookup without realtime TTS."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from fasttrack_router_v3 import RouterV3Runtime  # noqa: E402


INPUTS = (
    "This is great and amazing.",
    "No, that sounds wrong.",
    "Wow, that is really surprising.",
)


def make_test_runtime() -> RouterV3Runtime:
    runtime = RouterV3Runtime()
    runtime.spacy_checked = True
    runtime.emotion_checked = True
    runtime.intent_checked = True
    return runtime


class MissingAudioManifest:
    manifest_path = Path("/tmp/credo_missing_fasttrack_manifest.json")
    available = True

    def attach_sequence(self, candidate: dict) -> dict:
        segments = []
        for item in candidate.get("segments") or [candidate]:
            segment = dict(item)
            segment.update(
                {
                    "audio_path": None,
                    "selected_audio_path": None,
                    "prebuilt_hit": False,
                    "cache_hit": False,
                    "prebuilt_miss_reason": "audio_file_missing",
                }
            )
            segments.append(segment)
        enriched = dict(candidate)
        enriched.update(
            {
                "segments": segments,
                "audio_sequence": segments,
                "audio_path": None,
                "selected_audio_path": None,
                "selected_audio_paths": [],
                "prebuilt_hit": False,
                "cache_hit": False,
                "prebuilt_miss_reason": "audio_file_missing",
            }
        )
        return enriched


async def route_with_runtime(runtime: RouterV3Runtime, text: str) -> dict:
    result = await runtime.route(text)
    if not result:
        raise AssertionError(f"router returned no result for: {text}")
    return result


async def main() -> int:
    manifest = Path(config.FASTTRACK_PREBUILT_MANIFEST_PATH)
    if not manifest.exists():
        raise AssertionError(f"prebuilt manifest missing: {manifest}")

    runtime = make_test_runtime()
    for text in INPUTS:
        result = await route_with_runtime(runtime, text)
        selected_audio = result.get("selected_audio_path")
        audio_sequence = result.get("audio_sequence") or []
        response_act = str(result.get("response_act") or "")
        if response_act == "QUESTION":
            raise AssertionError(f"response_act must not be QUESTION: {result}")
        if not selected_audio or not Path(str(selected_audio)).exists():
            raise AssertionError(f"prebuilt wav path missing for {text!r}: {selected_audio}")
        if len(audio_sequence) < 2:
            raise AssertionError(f"grounded FastTrack must return emotion+intent audio sequence: {result}")
        if str(audio_sequence[0].get("source_dataset") or "") != "go_emotions":
            raise AssertionError(f"first FastTrack segment must be GoEmotions emotion audio: {audio_sequence}")
        if str(audio_sequence[1].get("source_dataset") or "") != "swda":
            raise AssertionError(f"second FastTrack segment must be SWDA intent audio: {audio_sequence}")
        for item in audio_sequence:
            audio_path = item.get("audio_path")
            if not audio_path or not Path(str(audio_path)).exists():
                raise AssertionError(f"audio sequence item missing wav path: {item}")
        if not result.get("prebuilt_hit"):
            raise AssertionError(f"prebuilt_hit false for {text!r}")
        print(
            "OK prebuilt",
            f"input={text!r}",
            f"text={result.get('selected_text')!r}",
            f"audio_sequence={len(audio_sequence)}",
            f"emotion={(result.get('emotion') or {}).get('label')}",
            f"incoming_intent={(result.get('intent') or {}).get('label')}",
            f"response_act={response_act}",
            f"lookup_latency_ms={result.get('lookup_latency_ms')}",
        )

    runtime.prebuilt_manifest = MissingAudioManifest()
    miss = await runtime.route("This is great and amazing.")
    if not miss:
        raise AssertionError("missing-audio route returned no result")
    if miss.get("selected_audio_path") or miss.get("prebuilt_hit"):
        raise AssertionError(f"missing manifest must not report prebuilt audio: {miss}")
    if any(item.get("audio_path") for item in miss.get("audio_sequence") or []):
        raise AssertionError(f"missing manifest must not return audio sequence paths: {miss}")
    if miss.get("selected_reaction", {}).get("tts_engine") in {"stylebert_vits2", "edge_tts", "piper_tts", "fish_speech"}:
        raise AssertionError(f"missing manifest must not select realtime TTS: {miss}")
    print("OK missing_audio_no_fallback", miss.get("selected_reaction", {}).get("prebuilt_miss_reason"))

    agent_source = (ROOT / "integrations" / "open_llm_vtuber" / "credo_latency_cover_agent.py").read_text(encoding="utf-8")
    if 'if scheduling_mode == "parallel"' not in agent_source:
        raise AssertionError("agent must gate early SlowTrack task creation behind parallel scheduling")
    if str(getattr(config, "CREDO_CONTEXT_SCHEDULING_MODE", "serial")).lower() != "serial":
        raise AssertionError("CREDO_CONTEXT_SCHEDULING_MODE must default to serial while parallel is deferred")
    print("OK serial_order_guard")
    return 0


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    exit_code = loop.run_until_complete(main())
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
