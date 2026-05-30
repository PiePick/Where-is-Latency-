#!/usr/bin/env python3
"""Measure FastTrack classifier, response-act, and prebuilt-audio stages by input length bin."""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))

from fast_track_audio_cache import normalize_response_act  # noqa: E402
from fasttrack_router_v3 import RouterV3Runtime  # noqa: E402
import config  # noqa: E402


BINS = (
    ("10-100자", 10, 100),
    ("100-200자", 100, 200),
    ("200-500자", 200, 500),
    ("500-1000자", 500, 1000),
)


SEEDS = (
    "I hate my professor but I have to love him, and the whole chat is laughing at my thesis pain.",
    "My lab presentation collapsed today, yet the viewers are spamming lol because the disaster is too familiar.",
    "Professor Jin-sama just asked for a quick look, and every graduate student in chat immediately understood the threat.",
    "The donation says the shared server is gone, the room is silent, and the VTuber needs a sharp reaction now.",
    "Everyone is joking about survival coffee, deadline trauma, and the strange dignity of a maid researcher.",
    "The chat is cheering and roasting me at the same time while I try to save the experiment log.",
)


GOEMOTIONS_CACHE_CANDIDATES = (
    Path("/home/ysree/.cache/huggingface/hub/models--joeddav--distilbert-base-uncased-go-emotions-student/snapshots/82114042047aaa39717090cfb20f3403b73b0215"),
    Path("/mnt/c/Users/CGLAB/.cache/huggingface/hub/models--joeddav--distilbert-base-uncased-go-emotions-student/snapshots/82114042047aaa39717090cfb20f3403b73b0215"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials-per-bin", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        default="/mnt/c/Users/CGLAB/Desktop/결과 분석/fasttrack_length_benchmark_20260529",
    )
    parser.add_argument(
        "--emotion-model-path",
        default="",
        help="Optional local GoEmotions DistilBERT snapshot path. If omitted, a local HF cache snapshot is used when available.",
    )
    return parser.parse_args()


def configure_local_models(args: argparse.Namespace) -> dict[str, str]:
    """Point the benchmark at local classifier artifacts when they are present."""
    emotion_model = Path(args.emotion_model_path).expanduser() if args.emotion_model_path else None
    if not emotion_model:
        emotion_model = next((path for path in GOEMOTIONS_CACHE_CANDIDATES if path.exists()), None)
    if emotion_model and emotion_model.exists():
        os.environ["EMOTION_MODEL_NAME"] = str(emotion_model)
        config.EMOTION_MODEL_NAME = str(emotion_model)

    return {
        "emotion_model": str(getattr(config, "EMOTION_MODEL_NAME", "")),
        "intent_model_dir": str(ROOT / "fasttrack_assets" / "models" / "setfit_swda_intent_minilm_optimized"),
        "selection_policy": str(getattr(config, "CREDO_FASTTRACK_SELECTION_POLICY", "grounded")).lower(),
        "prebuilt_manifest": str(getattr(config, "FASTTRACK_PREBUILT_MANIFEST_PATH", "")),
        "dataset_pool": str(getattr(config, "FAST_TRACK_DATASET_POOL_PATH", "")),
    }


def fit_text(seed: str, low: int, high: int, index: int) -> str:
    suffixes = [
        " Chat says lol lol and keeps the pressure high.",
        " The lab-maid broadcast needs a fast contextual reaction before the main answer.",
        " Viewers are spamming skulls, thesis jokes, and deadline panic in short bursts.",
        " The donation is emotional, dramatic, and tied to professor survival comedy.",
    ]
    text = seed
    suffix_index = 0
    while len(text) < low:
        text = f"{text}{suffixes[(index + suffix_index) % len(suffixes)]}"
        suffix_index += 1
    if len(text) >= high:
        text = text[: high - 2].rstrip(" ,.;") + "."
    return text


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def stats(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "n": 0,
            "mean_ms": "NA",
            "sd_ms": "NA",
            "median_ms": "NA",
            "p95_ms": "NA",
            "min_ms": "NA",
            "max_ms": "NA",
        }
    return {
        "n": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "sd_ms": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 95), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def existing_audio_paths(route_result: dict[str, Any]) -> list[str]:
    audio_paths = [str(item.get("audio_path") or "") for item in route_result.get("audio_sequence") or []]
    if not audio_paths and route_result.get("selected_audio_path"):
        audio_paths = [str(route_result.get("selected_audio_path"))]
    return [path for path in audio_paths if path]


async def measure_one(runtime: RouterV3Runtime, text: str) -> dict[str, object]:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        raise RuntimeError("empty benchmark input")

    stage_started = time.perf_counter()
    emotion = await asyncio.to_thread(runtime.infer_emotion, cleaned)
    emotion_ms = (time.perf_counter() - stage_started) * 1000.0

    stage_started = time.perf_counter()
    intent = await asyncio.to_thread(runtime.infer_intent, cleaned)
    intent_ms = (time.perf_counter() - stage_started) * 1000.0

    stage_started = time.perf_counter()
    keywords = await asyncio.to_thread(runtime.extract_keywords, cleaned)
    keyword_ms = (time.perf_counter() - stage_started) * 1000.0

    would_route_by_threshold = emotion.confidence >= runtime.threshold and intent.confidence >= runtime.threshold

    stage_started = time.perf_counter()
    transition = runtime.transition.choose(intent.label, emotion=emotion.label.lower(), rng=runtime.rng)
    response_act = normalize_response_act(transition.response_intent)
    transition_ms = (time.perf_counter() - stage_started) * 1000.0

    keyword_query = " ".join(keywords[:3])
    query = f"{emotion.label} {response_act} {keyword_query} {cleaned}".strip()
    selection_policy = str(getattr(config, "CREDO_FASTTRACK_SELECTION_POLICY", "grounded")).lower()

    stage_started = time.perf_counter()
    raw_candidates = runtime.store.search_prebuilt_units(
        query,
        emotion=emotion.label,
        response_act=response_act,
        top_k=runtime.top_k,
        selection_policy=selection_policy,
        rng=runtime.rng,
    )
    dataset_lookup_ms = (time.perf_counter() - stage_started) * 1000.0

    stage_started = time.perf_counter()
    top3 = [runtime.prebuilt_manifest.attach_sequence(candidate) for candidate in raw_candidates]
    manifest_match_ms = (time.perf_counter() - stage_started) * 1000.0

    selected = next((candidate for candidate in top3 if candidate.get("prebuilt_hit")), top3[0] if top3 else {})
    if not selected or not selected.get("prebuilt_hit"):
        raise RuntimeError(f"FastTrack prebuilt audio missing for input: {text!r}")

    stage_started = time.perf_counter()
    audio_paths = existing_audio_paths(selected)
    audio_ready = all(Path(path).exists() for path in audio_paths)
    audio_path_verify_ms = (time.perf_counter() - stage_started) * 1000.0
    if not audio_ready:
        raise RuntimeError(f"FastTrack audio path missing: {audio_paths}")

    parallel_classifier_critical_ms = max(emotion_ms, intent_ms, keyword_ms)
    prebuilt_audio_match_ms = dataset_lookup_ms + manifest_match_ms
    total_ms = parallel_classifier_critical_ms + transition_ms + prebuilt_audio_match_ms + audio_path_verify_ms

    return {
        "emotion_distilbert_goemotions_ms": round(emotion_ms, 3),
        "intent_swda_setfit_ms": round(intent_ms, 3),
        "keyword_extract_ms": round(keyword_ms, 3),
        "parallel_classifier_critical_path_ms": round(parallel_classifier_critical_ms, 3),
        "response_act_transition_ms": round(transition_ms, 3),
        "dataset_text_lookup_ms": round(dataset_lookup_ms, 3),
        "prebuilt_wav_manifest_match_ms": round(manifest_match_ms, 3),
        "prebuilt_audio_match_ms": round(prebuilt_audio_match_ms, 3),
        "audio_path_verify_ms": round(audio_path_verify_ms, 3),
        "total_ms": round(total_ms, 3),
        "selected_text": selected.get("text") or "",
        "selected_audio_paths": ";".join(audio_paths),
        "emotion": emotion.label,
        "emotion_confidence": round(emotion.confidence, 6),
        "intent": intent.label,
        "intent_confidence": round(intent.confidence, 6),
        "would_route_by_threshold": would_route_by_threshold,
        "response_act": response_act,
        "selection_policy": selection_policy,
        "candidate_count": len(top3),
        "composition_sources": ";".join(str(item) for item in selected.get("composition_sources") or []),
    }


async def warm_runtime(runtime: RouterV3Runtime) -> dict[str, object]:
    """Load model artifacts before benchmark trials so cold-start loading is excluded."""
    load_started = time.perf_counter()
    await asyncio.to_thread(runtime._load_emotion_pipeline)
    emotion_load_ms = (time.perf_counter() - load_started) * 1000.0

    load_started = time.perf_counter()
    await asyncio.to_thread(runtime._load_intent_model)
    intent_load_ms = (time.perf_counter() - load_started) * 1000.0

    warm_text = "Warmup: Professor Jin-sama asked for a quick look and chat is laughing at graduate school pain."
    await measure_one(runtime, warm_text)
    return {
        "emotion_backend": "distilbert_goemotions" if runtime.emotion_pipeline is not None else "rule_fallback",
        "intent_backend": "setfit_swda" if runtime.intent_model is not None else "rule_fallback",
        "emotion_model_load_ms": round(emotion_load_ms, 3),
        "intent_model_load_ms": round(intent_load_ms, 3),
    }


async def run() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    model_config = configure_local_models(args)
    runtime = RouterV3Runtime()
    backend_status = await warm_runtime(runtime)

    rows: list[dict[str, object]] = []
    for label, low, high in BINS:
        for trial in range(1, args.trials_per_bin + 1):
            seed = SEEDS[(trial - 1) % len(SEEDS)]
            text = fit_text(seed, low, high, trial)
            measured = await measure_one(runtime, text)
            row = {
                "trial_index": trial,
                "length_bin": label,
                "char_len": len(text),
                **backend_status,
                **measured,
                "input_text": text,
            }
            rows.append(row)
            print(
                f"{label} {trial}/{args.trials_per_bin}: chars={len(text)} "
                f"emotion={row['emotion_distilbert_goemotions_ms']}ms "
                f"intent={row['intent_swda_setfit_ms']}ms "
                f"transition={row['response_act_transition_ms']}ms "
                f"prebuilt={row['prebuilt_audio_match_ms']}ms "
                f"total={row['total_ms']}ms",
                flush=True,
            )

    write_csv(output_dir / "fasttrack_length_bin_raw.csv", rows)

    modules = (
        ("FastTrack 감정 분류(DistilBERT/GoEmotions)", "emotion_distilbert_goemotions_ms"),
        ("FastTrack 의도 분류(SWDA SetFit)", "intent_swda_setfit_ms"),
        ("FastTrack 키워드 추출(spaCy/fallback)", "keyword_extract_ms"),
        ("FastTrack 병렬 분류 critical path", "parallel_classifier_critical_path_ms"),
        ("FastTrack 대응 의도 전이(SWDA transition matrix)", "response_act_transition_ms"),
        ("FastTrack 데이터셋 텍스트 후보 검색", "dataset_text_lookup_ms"),
        ("FastTrack prebuilt wav manifest 매칭", "prebuilt_wav_manifest_match_ms"),
        ("FastTrack prebuilt audio 매칭 합계", "prebuilt_audio_match_ms"),
        ("FastTrack audio path 검증", "audio_path_verify_ms"),
        ("FastTrack 합계", "total_ms"),
    )

    summary_rows: list[dict[str, object]] = []
    compact_rows: list[dict[str, object]] = []
    for label, *_rest in BINS:
        bin_rows = [row for row in rows if row["length_bin"] == label]
        for module_label, key in modules:
            values = [float(row[key]) for row in bin_rows]
            summary_rows.append({"module_label": module_label, "length_bin": label, **stats(values)})
        routeable = sum(1 for row in bin_rows if str(row["would_route_by_threshold"]).lower() == "true")
        compact_rows.append(
            {
                "track": "FastTrack",
                "length_bin": label,
                "n_turns": len(bin_rows),
                "n_routeable_by_threshold": routeable,
                "Emotion_DistilBERT_GoEmotions_mean_ms": round(statistics.fmean(float(row["emotion_distilbert_goemotions_ms"]) for row in bin_rows), 1),
                "Intent_SWDA_SetFit_mean_ms": round(statistics.fmean(float(row["intent_swda_setfit_ms"]) for row in bin_rows), 1),
                "Keyword_Extract_mean_ms": round(statistics.fmean(float(row["keyword_extract_ms"]) for row in bin_rows), 1),
                "Parallel_Classifier_Critical_Path_mean_ms": round(statistics.fmean(float(row["parallel_classifier_critical_path_ms"]) for row in bin_rows), 1),
                "ResponseAct_Transition_mean_ms": round(statistics.fmean(float(row["response_act_transition_ms"]) for row in bin_rows), 3),
                "Dataset_Text_Lookup_mean_ms": round(statistics.fmean(float(row["dataset_text_lookup_ms"]) for row in bin_rows), 1),
                "Prebuilt_Wav_Manifest_Match_mean_ms": round(statistics.fmean(float(row["prebuilt_wav_manifest_match_ms"]) for row in bin_rows), 1),
                "Prebuilt_Audio_Match_mean_ms": round(statistics.fmean(float(row["prebuilt_audio_match_ms"]) for row in bin_rows), 1),
                "Audio_Path_Verify_mean_ms": round(statistics.fmean(float(row["audio_path_verify_ms"]) for row in bin_rows), 3),
                "Total_mean_ms": round(statistics.fmean(float(row["total_ms"]) for row in bin_rows), 1),
                "emotion_backend": backend_status["emotion_backend"],
                "intent_backend": backend_status["intent_backend"],
            }
        )

    write_csv(output_dir / "FastTrack_입력길이별_모듈지연시간_상세_filled.csv", summary_rows)
    write_csv(output_dir / "FastTrack_직관형_mean_ms_filled.csv", compact_rows)

    report_lines = [
        "# FastTrack Stage Latency Benchmark",
        "",
        f"- Trials per bin: {args.trials_per_bin}",
        f"- Emotion backend: {backend_status['emotion_backend']}",
        f"- Intent backend: {backend_status['intent_backend']}",
        f"- Emotion model load excluded from trial latency: {backend_status['emotion_model_load_ms']} ms",
        f"- Intent model load excluded from trial latency: {backend_status['intent_model_load_ms']} ms",
        f"- Emotion model path: {model_config['emotion_model']}",
        f"- Intent model dir: {model_config['intent_model_dir']}",
        f"- Selection policy: {model_config['selection_policy']}",
        "- Total_mean_ms uses the runtime critical path: max(emotion, intent, keyword) + response-act transition + prebuilt audio matching + audio path verification.",
        "- No realtime TTS synthesis is performed for FastTrack; wav files are prebuilt StyleBERT assets.",
        "",
        "## Compact Mean Table",
        "",
        "| track | length_bin | n_turns | Emotion | Intent | Keyword | Classifier critical path | ResponseAct | Dataset lookup | Wav manifest | Prebuilt match | Audio path | Total |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in compact_rows:
        report_lines.append(
            f"| {row['track']} | {row['length_bin']} | {row['n_turns']} | "
            f"{row['Emotion_DistilBERT_GoEmotions_mean_ms']} | {row['Intent_SWDA_SetFit_mean_ms']} | "
            f"{row['Keyword_Extract_mean_ms']} | {row['Parallel_Classifier_Critical_Path_mean_ms']} | "
            f"{row['ResponseAct_Transition_mean_ms']} | {row['Dataset_Text_Lookup_mean_ms']} | "
            f"{row['Prebuilt_Wav_Manifest_Match_mean_ms']} | {row['Prebuilt_Audio_Match_mean_ms']} | "
            f"{row['Audio_Path_Verify_mean_ms']} | {row['Total_mean_ms']} |"
        )
    (output_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
