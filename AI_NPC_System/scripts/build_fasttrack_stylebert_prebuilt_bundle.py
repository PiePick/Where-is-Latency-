#!/usr/bin/env python3
"""Build StyleBERT wav files for every filtered FastTrack pool item.

This reads the active separated ``pool.json`` directly. It does not compose
GoEmotions and SWDA text together; each filtered dataset item gets one wav.
Failed TTS items are logged and are not replaced with fallback text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import wave
from datetime import datetime, timezone
from hashlib import blake2b
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from stylebert_vits2_client import StyleBertVITS2Client, StyleBertVITS2Config  # noqa: E402


DEFAULT_OUTPUT_DIR = ROOT / "fasttrack_assets" / "audio" / "prebuilt_stylebert_v1"
EMOTIONS = ("POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL")
RESPONSE_ACTS = ("INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")
FRAGMENT_END_RE = re.compile(
    r"(?i)(?:[,;:-]|\b(?:and|but|or|so|because|if|when|while|that|the|a|an|to|of|for|with)\b)$"
)
STRONG_TERMINAL_RE = re.compile(r"""[.!?]["')\]]*$""")
BLOCKED_SURFACE_RE = re.compile(
    r"(?i)(assault|dangerous fantasy|mental illness|mental illnesses|\bowner\b|\bdog\b|\bvideo\b|"
    r"\btrump\b|\bbiden\b|\bkill\b|\bdie\b|\bsuicide\b|\bfuck\b|\bshit\b|\bsex\b|\bporn\b|"
    r"\bhell\b|\bthis guy\b|\bthat guy\b|\bthis man\b|\bthat man\b|\bthis woman\b|\bthat woman\b|"
    r"\blady\b|\bphoto\b|\bpicture\b|\bshow\b|\balbum\b|\bsong\b|\btitle\b|\bface\b|\bspider\b|"
    r"\bteam\b|cake day|anniversary|\bcop\b|\burinal\b|microplastics|\bdayz\b|\bcomic\b|"
    r"\bboyfriend\b|\bwifey\b|\bmother\b|\bdamn\b|\bshoe\b|\bleather\b|\bclown\b|"
    r"\bfurniture\b|polyamory|assholery|\bthigh\b|\bhoodie\b|\bzebra\b|\bliar\b|\bcheater\b|"
    r"\bwitch\b|\bcigarette\b|\bkindergarten\b|\bsoap\b|\bpopulism\b|terrorists|hentaipoon|"
    r"cromulent|calamari|baloney|parvo|foreign money)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-generate StyleBERT wav files for FastTrack router-v3 candidate text."
    )
    parser.add_argument("--pool", type=Path, default=config.FAST_TRACK_DATASET_POOL_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--tts-edge-padding-spaces",
        type=int,
        default=3,
        help="Spaces added only to the StyleBERT request text to reduce clipped wav edges.",
    )
    parser.add_argument(
        "--tts-terminal-punctuation",
        default=".",
        help="Punctuation appended only to StyleBERT request text when the source text has no strong terminator.",
    )
    parser.add_argument(
        "--tts-trailing-silence-ms",
        type=int,
        default=config.STYLEBERT_VITS2_TRAILING_SILENCE_MS,
        help="Physical silence appended to each generated wav tail.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=12,
        help="Stop the current run after this many consecutive TTS failures; 0 disables the guard.",
    )
    parser.add_argument(
        "--request-sleep-ms",
        type=int,
        default=0,
        help="Optional delay between StyleBERT requests for unstable local servers.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Debug limit; 0 builds every filtered item.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select candidates and print a summary without contacting StyleBERT or writing manifest.json.",
    )
    return parser.parse_args()


def duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
    return int(round(frames * 1000.0 / rate)) if rate else 0


def text_hash(text: str) -> str:
    return blake2b(text.encode("utf-8"), digest_size=8).hexdigest()


def is_incomplete_sentence(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    return not normalized


def is_blocked_surface_text(text: str) -> bool:
    """Block source-dataset remnants that are too specific or unsafe for FastTrack."""
    return bool(BLOCKED_SURFACE_RE.search(str(text or "")))


def synthesis_request_text(text: str, *, padding_spaces: int, terminal_punctuation: str) -> tuple[str, bool]:
    """Build StyleBERT-only request text without changing manifest/subtitle text."""
    spoken = re.sub(r"\s+", " ", str(text or "")).strip()
    punctuation = str(terminal_punctuation or "").strip()
    punctuation_added = False
    if punctuation and not STRONG_TERMINAL_RE.search(spoken):
        spoken = f"{spoken}{punctuation}"
        punctuation_added = True
    padding = " " * max(0, int(padding_spaces))
    return f"{padding}{spoken}{padding}", punctuation_added


def item_id(source_dataset: str, label: str, source_item_id: str, text: str) -> str:
    safe_source_id = re.sub(r"[^A-Za-z0-9_-]+", "_", source_item_id).strip("_")
    return f"{source_dataset}_{label.lower()}_{safe_source_id}_{text_hash(text)}"


def collect_candidates(args: argparse.Namespace) -> list[dict[str, Any]]:
    payload = json.loads(args.pool.read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []
    seen_text: set[str] = set()

    def add_item(*, source_dataset: str, label: str, raw_item: dict[str, Any]) -> None:
        text = re.sub(r"\s+", " ", str(raw_item.get("text") or "")).strip()
        if not text or is_blocked_surface_text(text):
            return
        text_key = f"{source_dataset}:{text.lower()}"
        if text_key in seen_text:
            return
        seen_text.add(text_key)
        source_item_id = str(raw_item.get("id") or f"{source_dataset}_{len(candidates) + 1:04d}")
        emotion = label if source_dataset == "go_emotions" else "UNSPECIFIED"
        response_act = label if source_dataset == "swda" else "UNSPECIFIED"
        candidates.append(
            {
                "id": item_id(source_dataset, label, source_item_id, text),
                "text": text,
                "plain_text": text,
                "emotion": emotion,
                "response_act": response_act,
                "source_dataset": source_dataset,
                "source_item_id": source_item_id,
                "source_label": label,
                "source": raw_item.get("source") or source_dataset,
                "raw_dialog_act": raw_item.get("raw_dialog_act"),
                "cell_id": f"{source_dataset}_{label.lower()}",
                "tts_engine": "stylebert_vits2",
                "voice_model": config.STYLEBERT_VITS2_MODEL_NAME,
            }
        )

    go_buckets = payload.get("go_emotions", {}).get("buckets", {}) or {}
    swda_buckets = payload.get("swda", {}).get("buckets", {}) or {}
    for label in EMOTIONS:
        for raw_item in go_buckets.get(label, []) or []:
            add_item(source_dataset="go_emotions", label=label, raw_item=raw_item)
    for label in RESPONSE_ACTS:
        for raw_item in swda_buckets.get(label, []) or []:
            add_item(source_dataset="swda", label=label, raw_item=raw_item)
    if args.limit:
        candidates = candidates[: max(0, args.limit)]
    return candidates


def manifest_payload(args: argparse.Namespace, items: list[dict[str, Any]], failures: int) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "AI_NPC_System/scripts/build_fasttrack_stylebert_prebuilt_bundle.py",
        "kind": "fasttrack_filtered_pool_stylebert_language_bundle",
        "dataset_pool": str(args.pool),
        "output_dir": str(args.output_dir),
        "tts_reference": {
            "engine": "stylebert_vits2",
            "voice_model": config.STYLEBERT_VITS2_MODEL_NAME,
            "model_id": config.STYLEBERT_VITS2_MODEL_ID,
            "speaker_id": config.STYLEBERT_VITS2_SPEAKER_ID,
            "style": config.STYLEBERT_VITS2_STYLE,
            "style_weight": config.STYLEBERT_VITS2_STYLE_WEIGHT,
            "sdp_ratio": config.STYLEBERT_VITS2_SDP_RATIO,
            "noise": config.STYLEBERT_VITS2_NOISE,
            "noisew": config.STYLEBERT_VITS2_NOISEW,
            "length": config.STYLEBERT_VITS2_LENGTH,
            "language": config.STYLEBERT_VITS2_LANGUAGE,
            "request_text_edge_padding_spaces": max(0, int(args.tts_edge_padding_spaces)),
            "request_text_edges_preserved": True,
            "request_text_terminal_punctuation": str(args.tts_terminal_punctuation or ""),
            "trailing_silence_ms": max(0, int(args.tts_trailing_silence_ms)),
        },
        "source_policy": {
            "separate_source_datasets": True,
            "uses_filtered_dataset_pool": True,
            "no_runtime_text_composition": True,
            "no_fallback_text_on_tts_failure": True,
            "failure_log": "failures.jsonl",
        },
        "summary": {
            "items": len(items),
            "failures": failures,
        },
        "items": items,
    }


def write_failure(output_dir: Path, item: dict[str, Any], error: Exception) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "id": item.get("id"),
        "text": item.get("text"),
        "emotion": item.get("emotion"),
        "response_act": item.get("response_act"),
        "source_dataset": item.get("source_dataset"),
        "source_item_id": item.get("source_item_id"),
        "error": repr(error),
    }
    with (output_dir / "failures.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def target_audio_path(output_dir: Path, item: dict[str, Any]) -> Path:
    return (
        output_dir
        / "audio"
        / item["source_dataset"]
        / str(item["source_label"]).lower()
        / f"{item['id']}.wav"
    )


def synthesize_items(args: argparse.Namespace, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    completed: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    failures = 0
    for item in candidates:
        if is_incomplete_sentence(str(item.get("text") or "")):
            failures += 1
            write_failure(args.output_dir, item, ValueError("candidate text is empty or incomplete"))
            continue

        target = target_audio_path(args.output_dir, item)
        relative_audio_path = target.relative_to(args.output_dir).as_posix()
        if target.exists() and args.skip_existing and not args.force:
            try:
                ready = dict(item)
                ready["audio_path"] = relative_audio_path
                ready["duration_ms"] = duration_ms(target)
                ready["tts_request_edge_padding_spaces"] = max(0, int(args.tts_edge_padding_spaces))
                ready["tts_request_terminal_punctuation_added"] = (
                    synthesis_request_text(
                        str(item["plain_text"]),
                        padding_spaces=max(0, int(args.tts_edge_padding_spaces)),
                        terminal_punctuation=str(args.tts_terminal_punctuation or ""),
                    )[1]
                )
                ready["tts_trailing_silence_ms"] = max(0, int(args.tts_trailing_silence_ms))
                completed.append(ready)
                print(f"reuse: {item['id']} -> {relative_audio_path}")
                continue
            except Exception as exc:
                failures += 1
                write_failure(args.output_dir, item, exc)
                continue
        pending.append(item)

    if not pending:
        return completed, failures

    client = StyleBertVITS2Client(
        StyleBertVITS2Config(trailing_silence_ms=max(0, int(args.tts_trailing_silence_ms)))
    )
    if not client.is_healthy():
        error = RuntimeError(f"StyleBERT-VITS2 server is not reachable at {client.cfg.health_url}")
        for item in pending:
            failures += 1
            write_failure(args.output_dir, item, error)
        print(f"FAILED: {error}", file=sys.stderr)
        return completed, failures

    consecutive_failures = 0
    for item in pending:
        target = target_audio_path(args.output_dir, item)
        relative_audio_path = target.relative_to(args.output_dir).as_posix()
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            synthesis_text, punctuation_added = synthesis_request_text(
                str(item["plain_text"]),
                padding_spaces=max(0, int(args.tts_edge_padding_spaces)),
                terminal_punctuation=str(args.tts_terminal_punctuation or ""),
            )
            generated = client.synthesize_to_file(
                synthesis_text,
                prefix=item["id"],
                style="Neutral",
                preserve_text_edges=True,
            )
            generated.replace(target)
            ready = dict(item)
            ready["audio_path"] = relative_audio_path
            ready["duration_ms"] = duration_ms(target)
            ready["tts_request_edge_padding_spaces"] = max(0, int(args.tts_edge_padding_spaces))
            ready["tts_request_terminal_punctuation_added"] = punctuation_added
            ready["tts_trailing_silence_ms"] = max(0, int(args.tts_trailing_silence_ms))
            completed.append(ready)
            consecutive_failures = 0
            print(f"audio: {item['id']} -> {relative_audio_path}")
            sleep_ms = max(0, int(args.request_sleep_ms))
            if sleep_ms:
                time.sleep(sleep_ms / 1000.0)
        except Exception as exc:
            failures += 1
            consecutive_failures += 1
            write_failure(args.output_dir, item, exc)
            print(f"FAILED: {item['id']}: {exc}", file=sys.stderr)
            max_consecutive = max(0, int(args.max_consecutive_failures))
            if max_consecutive and consecutive_failures >= max_consecutive:
                print(
                    f"STOPPED: {consecutive_failures} consecutive StyleBERT failures; "
                    "restart the server and rerun with --skip-existing.",
                    file=sys.stderr,
                )
                break
    return completed, failures


def main() -> int:
    args = parse_args()
    candidates = collect_candidates(args)
    print(f"selected_candidates={len(candidates)} pool={args.pool}")
    if args.dry_run:
        by_cell: dict[str, int] = {}
        for item in candidates:
            by_cell[item["cell_id"]] = by_cell.get(item["cell_id"], 0) + 1
        for cell_id, count in sorted(by_cell.items()):
            print(f"{cell_id}={count}")
        return 0

    failure_log = args.output_dir / "failures.jsonl"
    if failure_log.exists():
        failure_log.unlink()
    started = time.perf_counter()
    items, failures = synthesize_items(args, candidates)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    if not items and failures:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        print(f"No manifest written because no audio items were generated or reused: {manifest_path}")
        print(f"items=0, failures={failures}, elapsed_ms={elapsed_ms}")
        return 1
    payload = manifest_payload(args, items, failures)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    print(f"Wrote FastTrack StyleBERT prebuilt manifest: {manifest_path}")
    print(f"items={len(items)}, failures={failures}, elapsed_ms={elapsed_ms}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
