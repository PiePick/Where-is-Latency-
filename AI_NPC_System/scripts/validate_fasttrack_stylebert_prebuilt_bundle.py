#!/usr/bin/env python3
"""Validate a pre-generated StyleBERT FastTrack language audio bundle."""

from __future__ import annotations

import argparse
import json
import re
import sys
import wave
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


DEFAULT_MANIFEST = ROOT / "fasttrack_assets" / "audio" / "prebuilt_stylebert_v1" / "manifest.json"
REQUIRED_ITEM_FIELDS = (
    "text",
    "plain_text",
    "emotion",
    "response_act",
    "source_dataset",
    "audio_path",
    "duration_ms",
    "tts_engine",
    "voice_model",
)
EMOTIONS = {"POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL"}
RESPONSE_ACTS = {"INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT"}
OPTIONAL_LABEL = "UNSPECIFIED"
FRAGMENT_END_RE = re.compile(
    r"(?i)(?:[,;:-]|\b(?:and|but|or|so|because|if|when|while|that|the|a|an|to|of|for|with)\b)$"
)
BAD_SURFACE_RE = re.compile(
    r"(?i)(\?|peko|haha|ahaha|lol|lmao|fuck|shit|idiot|retard|porn|sex|reddit|youtube|subreddit|#[A-Za-z]|"
    r"assault|dangerous fantasy|mental illness|mental illnesses|\bowner\b|\bdog\b|\bvideo\b|"
    r"\btrump\b|\bbiden\b|\bkill\b|\bdie\b|\bsuicide\b|\bhell\b|\bthis guy\b|\bthat guy\b|"
    r"\bthis man\b|\bthat man\b|\bthis woman\b|\bthat woman\b|\blady\b|\bphoto\b|\bpicture\b|"
    r"\bshow\b|\balbum\b|\bsong\b|\btitle\b|\bface\b|\bspider\b|\bteam\b|cake day|anniversary|"
    r"\bcop\b|\burinal\b|microplastics|\bdayz\b|\bcomic\b|\bboyfriend\b|\bwifey\b|\bmother\b|"
    r"\bdamn\b|\bshoe\b|\bleather\b|\bclown\b|\bfurniture\b|polyamory|assholery|\bthigh\b|"
    r"\bhoodie\b|\bzebra\b|\bliar\b|\bcheater\b|\bwitch\b|\bcigarette\b|\bkindergarten\b|"
    r"\bsoap\b|\bpopulism\b|terrorists|hentaipoon|cromulent|calamari|baloney|parvo|foreign money)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FastTrack StyleBERT prebuilt audio manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--strict-voice-model", action="store_true")
    parser.add_argument("--min-items", type=int, default=1)
    return parser.parse_args()


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
    return int(round(frames * 1000.0 / rate)) if rate else 0


def is_incomplete_sentence(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return True
    return bool(re.search(r"[,;:-]\s*$", normalized))


def validate_item(item: dict[str, Any], index: int, root: Path, strict_voice_model: bool) -> list[str]:
    errors: list[str] = []
    item_id = str(item.get("id") or f"index:{index}")
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            errors.append(f"{item_id} missing field: {field}")

    text = str(item.get("text") or "").strip()
    plain_text = str(item.get("plain_text") or "").strip()
    if not text:
        errors.append(f"{item_id} empty text")
    if not plain_text:
        errors.append(f"{item_id} empty plain_text")
    if text and plain_text and text != plain_text:
        errors.append(f"{item_id} text/plain_text mismatch")
    if is_incomplete_sentence(text):
        errors.append(f"{item_id} incomplete sentence: {text}")
    if BAD_SURFACE_RE.search(text):
        errors.append(f"{item_id} blocked surface text: {text}")

    emotion = str(item.get("emotion") or "").upper()
    response_act = str(item.get("response_act") or "").upper()
    source_dataset = str(item.get("source_dataset") or "")
    if source_dataset == "go_emotions":
        valid_emotion = emotion in EMOTIONS
        valid_response = response_act == OPTIONAL_LABEL
    elif source_dataset == "swda":
        valid_emotion = emotion == OPTIONAL_LABEL
        valid_response = response_act in RESPONSE_ACTS
    else:
        valid_emotion = emotion in EMOTIONS or emotion == OPTIONAL_LABEL
        valid_response = response_act in RESPONSE_ACTS or response_act == OPTIONAL_LABEL
    if not valid_emotion:
        errors.append(f"{item_id} invalid emotion: {emotion}")
    if not valid_response:
        errors.append(f"{item_id} invalid response_act: {response_act}")

    if str(item.get("tts_engine") or "") != "stylebert_vits2":
        errors.append(f"{item_id} invalid tts_engine: {item.get('tts_engine')}")
    if strict_voice_model and str(item.get("voice_model") or "") != config.STYLEBERT_VITS2_MODEL_NAME:
        errors.append(
            f"{item_id} voice_model mismatch: {item.get('voice_model')} != {config.STYLEBERT_VITS2_MODEL_NAME}"
        )

    audio_value = str(item.get("audio_path") or "")
    audio_path = Path(audio_value)
    if not audio_path.is_absolute():
        audio_path = root / audio_path
    if not audio_path.exists():
        errors.append(f"{item_id} missing audio_path: {audio_value}")
    elif audio_path.stat().st_size <= 44:
        errors.append(f"{item_id} empty wav file: {audio_value}")
    else:
        try:
            actual_duration = wav_duration_ms(audio_path)
            declared_duration = int(item.get("duration_ms") or 0)
            if declared_duration <= 0:
                errors.append(f"{item_id} non-positive duration_ms: {declared_duration}")
            elif abs(actual_duration - declared_duration) > 50:
                errors.append(
                    f"{item_id} duration mismatch: manifest={declared_duration} actual={actual_duration}"
                )
        except Exception as exc:
            errors.append(f"{item_id} invalid wav: {audio_value}: {exc}")
    return errors


def main() -> int:
    args = parse_args()
    if not args.manifest.exists():
        print(f"FAILED\n- manifest does not exist: {args.manifest}")
        return 1
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = list(payload.get("items") or [])
    errors: list[str] = []
    if len(items) < args.min_items:
        errors.append(f"manifest item count too small: {len(items)} < {args.min_items}")
    if payload.get("source_policy", {}).get("separate_source_datasets") is not True:
        errors.append("source_policy.separate_source_datasets must be true")
    if payload.get("source_policy", {}).get("no_fallback_text_on_tts_failure") is not True:
        errors.append("source_policy.no_fallback_text_on_tts_failure must be true")
    if payload.get("source_policy", {}).get("no_runtime_text_composition") is not True:
        errors.append("source_policy.no_runtime_text_composition must be true")

    root = args.manifest.parent
    seen_ids: set[str] = set()
    emotion_counts: Counter[str] = Counter()
    response_counts: Counter[str] = Counter()
    cell_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for index, item in enumerate(items, start=1):
        item_id = str(item.get("id") or "")
        if item_id and item_id in seen_ids:
            errors.append(f"{item_id} duplicate id")
        if item_id:
            seen_ids.add(item_id)
        emotion_counts[str(item.get("emotion") or "").upper()] += 1
        response_counts[str(item.get("response_act") or "").upper()] += 1
        cell_counts[f"{str(item.get('emotion') or '').upper()}:{str(item.get('response_act') or '').upper()}"] += 1
        source_counts[str(item.get("source_dataset") or "")] += 1
        errors.extend(validate_item(item, index, root, args.strict_voice_model))

    print(f"manifest={args.manifest}")
    print(f"items={len(items)}")
    print("emotion_distribution=" + json.dumps(dict(sorted(emotion_counts.items())), ensure_ascii=False))
    print("response_act_distribution=" + json.dumps(dict(sorted(response_counts.items())), ensure_ascii=False))
    print("source_dataset_distribution=" + json.dumps(dict(sorted(source_counts.items())), ensure_ascii=False))
    print("cell_distribution=" + json.dumps(dict(sorted(cell_counts.items())), ensure_ascii=False))
    if errors:
        print("FAILED")
        for error in errors[:100]:
            print(f"- {error}")
        if len(errors) > 100:
            print(f"... {len(errors) - 100} more")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
