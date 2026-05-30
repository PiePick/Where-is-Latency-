#!/usr/bin/env python3
"""Check whether the CREDO runtime can run a stable demo.

The script is intentionally read-only. It verifies local files, Python
dependencies, HTTP endpoints, avatar motion wiring, and research artifacts, then
writes a compact Markdown/JSON readiness report for experiment logs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DEFAULT_JSON = ROOT / "reports" / "runtime_readiness_latest.json"
DEFAULT_MD = ROOT / "reports" / "runtime_readiness_latest.md"


def ensure_runtime_python() -> None:
    """Run checks in the Open-LLM venv so dependency checks match the demo."""
    if os.getenv("CREDO_READINESS_NO_REEXEC"):
        return
    runtime_python = PROJECT_ROOT / "vendor" / "open-llm-vtuber" / ".venv" / "bin" / "python"
    if not runtime_python.exists():
        return
    if Path(sys.executable).absolute() == runtime_python.absolute():
        return
    os.execv(str(runtime_python), [str(runtime_python), *sys.argv])


@dataclass
class CheckResult:
    """One readiness check result."""

    name: str
    status: str
    detail: str
    required: bool = True


def load_config() -> Any:
    sys.path.insert(0, str(ROOT))
    import config

    return config


def ok(name: str, detail: str, *, required: bool = True) -> CheckResult:
    return CheckResult(name=name, status="OK", detail=detail, required=required)


def warn(name: str, detail: str, *, required: bool = True) -> CheckResult:
    return CheckResult(name=name, status="WARN", detail=detail, required=required)


def skip(name: str, detail: str, *, required: bool = False) -> CheckResult:
    return CheckResult(name=name, status="SKIP", detail=detail, required=required)


def fail(name: str, detail: str, *, required: bool = True) -> CheckResult:
    return CheckResult(name=name, status="FAIL", detail=detail, required=required)


def check_path(name: str, path: Path, *, required: bool = True, executable: bool = False) -> CheckResult:
    if not path.exists():
        return fail(name, f"missing: {path}", required=required)
    if executable and not os.access(path, os.X_OK):
        return fail(name, f"not executable: {path}", required=required)
    return ok(name, str(path), required=required)


def check_import(module_name: str, *, required: bool = True) -> CheckResult:
    if importlib.util.find_spec(module_name) is None:
        return fail(f"python import: {module_name}", "module is not importable", required=required)
    return ok(f"python import: {module_name}", "importable", required=required)


def check_http(name: str, url: str, *, required: bool = False, timeout: float = 2.0) -> CheckResult:
    try:
        req = urllib.request.Request(url, method="GET")
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed = (time.perf_counter() - started) * 1000.0
            if 200 <= response.status < 500:
                return ok(name, f"{url} responded HTTP {response.status} in {elapsed:.1f} ms", required=required)
            return warn(name, f"{url} responded HTTP {response.status}", required=required)
    except urllib.error.URLError as exc:
        return fail(name, f"unreachable: {url} ({exc})", required=required)
    except Exception as exc:
        return fail(name, f"error: {url} ({exc})", required=required)


def check_tcp(name: str, host: str, port: int, *, required: bool = False, timeout: float = 1.0) -> CheckResult:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ok(name, f"{host}:{port} accepts TCP connections", required=required)
    except OSError as exc:
        return fail(name, f"{host}:{port} is closed or unreachable ({exc})", required=required)


def check_intent_matrix() -> CheckResult:
    path = ROOT / "reports" / "intent_transition_matrix_from_swda.json"
    if not path.exists():
        return fail("SWDA intent transition matrix", f"missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    matrix = payload.get("matrix") or {}
    question = matrix.get("QUESTION") or {}
    if "INFORM" not in question or "ACKNOWLEDGE" not in question:
        return fail("SWDA intent transition matrix", "QUESTION row is incomplete")
    detail = (
        f"{path}; cross-speaker pairs={payload.get('cross_speaker_adjacent_pairs')}; "
        f"QUESTION->INFORM={question.get('INFORM')}, "
        f"QUESTION->ACKNOWLEDGE={question.get('ACKNOWLEDGE')}"
    )
    return ok("SWDA intent transition matrix", detail)


def check_motion_groups() -> CheckResult:
    path = PROJECT_ROOT / "vendor" / "open-llm-vtuber" / "live2d-models" / "credo_avatar" / "credo_avatar.model3.json"
    if not path.exists():
        return fail("Live2D motion groups", f"missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = data.get("FileReferences", {}).get("Motions", {})
    required_groups = {"Idle", "Talk", "Positive", "Negative", "Ambiguous", "Neutral"}
    missing = sorted(required_groups - set(groups))
    if missing:
        return fail("Live2D motion groups", f"missing groups: {missing}")
    return ok("Live2D motion groups", ", ".join(sorted(groups)))


def check_youtube_bridge_dependency() -> CheckResult:
    venv_python = PROJECT_ROOT / "vendor" / "open-llm-vtuber" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        return fail("YouTube bridge runtime", f"missing python: {venv_python}", required=False)
    code = "import websockets; print(websockets.__version__)"
    import subprocess

    proc = subprocess.run(
        [str(venv_python), "-c", code],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return fail("YouTube bridge dependency", proc.stderr.strip() or "websockets import failed", required=False)
    return ok("YouTube bridge dependency", f"websockets {proc.stdout.strip()}", required=False)

def check_open_llm_module(module: str, *, required: bool = True) -> CheckResult:
    """Verify a Python dependency in the Open-LLM-VTuber runtime environment."""
    venv_python = PROJECT_ROOT / "vendor" / "open-llm-vtuber" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        return fail(f"Open-LLM module: {module}", f"missing python: {venv_python}", required=required)
    import subprocess

    proc = subprocess.run(
        [str(venv_python), "-c", f"import {module}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return fail(f"Open-LLM module: {module}", proc.stderr.strip() or "import failed", required=required)
    return ok(f"Open-LLM module: {module}", "importable", required=required)



def check_piper_tts(cfg: object) -> list[CheckResult]:
    """Verify the Piper FastTrack CLI and English voice files."""
    binary = Path(getattr(cfg, "PIPER_TTS_BIN", PROJECT_ROOT / "vendor" / "piper-tts" / ".venv" / "bin" / "piper"))
    model = Path(getattr(cfg, "PIPER_TTS_MODEL_PATH", PROJECT_ROOT / "vendor" / "piper-tts" / "voices" / "en_US-lessac-medium.onnx"))
    voice_config = Path(getattr(cfg, "PIPER_TTS_CONFIG_PATH", Path(f"{model}.json")))
    return [
        check_path("Piper FastTrack executable", binary, executable=True),
        check_path("Piper FastTrack English voice model", model),
        check_path("Piper FastTrack voice config", voice_config),
        check_http("Piper FastTrack endpoint", getattr(cfg, "PIPER_TTS_HEALTH_URL", "http://127.0.0.1:5001/health"), required=False),
    ]


def check_stylebert_model_name(cfg: object, model_assets_dir: Path) -> CheckResult:
    model_name = str(getattr(cfg, "STYLEBERT_VITS2_MODEL_NAME", "") or "").strip()
    language = str(getattr(cfg, "STYLEBERT_VITS2_LANGUAGE", "EN") or "EN").upper()
    if language == "JP":
        return skip("Style-Bert-VITS2 explicit English model", "STYLEBERT_VITS2_LANGUAGE=JP smoke-test mode", required=False)
    if not model_name:
        return fail(
            "Style-Bert-VITS2 explicit English model",
            "STYLEBERT_VITS2_MODEL_NAME is empty; set it to the English model directory under vendor/Style-Bert-VITS2/model_assets",
            required=False,
        )
    config_path = model_assets_dir / model_name / "config.json"
    if not config_path.exists():
        return fail(
            "Style-Bert-VITS2 explicit English model",
            f"missing {config_path}",
            required=False,
        )
    return ok("Style-Bert-VITS2 explicit English model", f"{model_name} ({config_path})", required=False)


def check_stylebert_device(cfg: object) -> CheckResult:
    device = str(getattr(cfg, "STYLEBERT_VITS2_DEVICE", "cpu") or "cpu").strip().lower()
    if device not in {"cpu", "cuda"}:
        return fail(
            "Style-Bert-VITS2 device",
            f"STYLEBERT_VITS2_DEVICE must be cpu or cuda, got: {device}",
            required=False,
        )
    if device == "cpu":
        return ok("Style-Bert-VITS2 device", "cpu (system RAM mode; no VRAM reserved for FastTrack TTS)", required=False)
    cuda_devices = str(getattr(cfg, "STYLEBERT_VITS2_CUDA_VISIBLE_DEVICES", "0") or "0")
    return ok("Style-Bert-VITS2 device", f"cuda on CUDA_VISIBLE_DEVICES={cuda_devices}", required=False)


def check_fish_reference_voice(reference_dir: Path) -> CheckResult:
    """Verify that Fish Speech has at least one wav/lab reference pair."""
    if not reference_dir.exists():
        return fail("Fish Speech reference voice", f"missing: {reference_dir}")

    pairs = []
    for wav_path in sorted(reference_dir.glob("*.wav")):
        lab_path = wav_path.with_suffix(".lab")
        if lab_path.exists() and lab_path.read_text(encoding="utf-8").strip():
            pairs.append(wav_path.name)

    if not pairs:
        return fail("Fish Speech reference voice", f"no wav/lab pairs in: {reference_dir}")
    return ok("Fish Speech reference voice", f"{reference_dir} ({len(pairs)} pairs)")


def check_fast_track_audio_cache(cfg: Any) -> CheckResult:
    """Verify that cached FastTrack audio matches the configured reference."""
    manifest_path = cfg.FAST_TRACK_AUDIO_CACHE_PATH
    if not cfg.FAST_TRACK_AUDIO_CACHE_ENABLED:
        return skip("FastTrack audio cache", "disabled by FAST_TRACK_AUDIO_CACHE_ENABLED=0", required=False)
    if not manifest_path.exists():
        return fail("FastTrack audio cache", f"missing: {manifest_path}", required=False)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = payload.get("tts_reference", {}) if isinstance(payload, dict) else {}
    reference_id = str(metadata.get("reference_id", "")).strip()
    expected = str(cfg.FAST_TRACK_AUDIO_CACHE_REFERENCE_ID or "").strip()
    if expected and reference_id != expected:
        return fail(
            "FastTrack audio cache",
            f"reference mismatch: manifest={reference_id!r}, expected={expected!r}",
            required=False,
        )

    root = manifest_path.parent
    usable = 0
    for item in payload.get("items", []):
        audio_path = Path(str(item.get("audio_path", "")))
        if not audio_path.is_absolute():
            audio_path = root / audio_path
        if audio_path.exists():
            usable += 1

    if usable == 0:
        return fail("FastTrack audio cache", f"no usable audio items in {manifest_path}", required=False)
    return ok("FastTrack audio cache", f"{manifest_path}; reference={reference_id}; usable_items={usable}", required=False)


def check_prebuilt_stylebert_fasttrack_manifest(cfg: Any) -> CheckResult:
    """Verify the active pre-generated StyleBERT FastTrack wav manifest."""
    manifest_path = Path(getattr(cfg, "FASTTRACK_PREBUILT_MANIFEST_PATH", ""))
    if not manifest_path.exists():
        return fail("Prebuilt StyleBERT FastTrack manifest", f"missing: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail("Prebuilt StyleBERT FastTrack manifest", f"invalid json: {manifest_path} ({exc})")

    items = list(payload.get("items") or [])
    if not items:
        return fail("Prebuilt StyleBERT FastTrack manifest", f"no items in {manifest_path}")

    root = manifest_path.parent
    usable_audio = 0
    source_counts: dict[str, int] = {}
    missing_examples: list[str] = []
    for item in items:
        source = str(item.get("source_dataset") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        raw_audio_path = str(item.get("audio_path") or "").strip()
        if not raw_audio_path:
            if len(missing_examples) < 3:
                missing_examples.append(str(item.get("id") or "missing-audio-path"))
            continue
        audio_path = Path(raw_audio_path)
        if not audio_path.is_absolute():
            audio_path = root / audio_path
        if audio_path.exists() and audio_path.stat().st_size > 44:
            usable_audio += 1
        elif len(missing_examples) < 3:
            missing_examples.append(raw_audio_path)

    if usable_audio == 0:
        return fail("Prebuilt StyleBERT FastTrack manifest", f"no usable wav files in {manifest_path}")
    if usable_audio != len(items):
        return fail(
            "Prebuilt StyleBERT FastTrack manifest",
            f"{manifest_path}; usable_audio={usable_audio}/{len(items)}; missing_examples={missing_examples}",
        )

    expected_voice = str(getattr(cfg, "STYLEBERT_VITS2_MODEL_NAME", "") or "")
    manifest_voice = str((payload.get("tts_reference") or {}).get("voice_model") or "")
    voice_detail = f"; voice_model={manifest_voice}" if manifest_voice else ""
    if expected_voice and manifest_voice and manifest_voice != expected_voice:
        return fail(
            "Prebuilt StyleBERT FastTrack manifest",
            f"voice mismatch: manifest={manifest_voice!r}, expected={expected_voice!r}",
        )

    source_detail = ", ".join(f"{key}={value}" for key, value in sorted(source_counts.items()))
    return ok(
        "Prebuilt StyleBERT FastTrack manifest",
        f"{manifest_path}; usable_audio={usable_audio}/{len(items)}; {source_detail}{voice_detail}",
    )


def check_persona_reaction_bundle(cfg: Any) -> CheckResult:
    """Verify that the configured FastTrack text source can serve selection."""
    pool_path = getattr(cfg, "FAST_TRACK_DATASET_POOL_PATH", None)
    if pool_path and Path(pool_path).exists():
        payload = json.loads(Path(pool_path).read_text(encoding="utf-8"))
        go_buckets = payload.get("go_emotions", {}).get("buckets", {})
        swda_buckets = payload.get("swda", {}).get("buckets", {})
        go_count = sum(len(items) for items in go_buckets.values() if isinstance(items, list))
        swda_count = sum(len(items) for items in swda_buckets.values() if isinstance(items, list))
        question_count = len(swda_buckets.get("QUESTION", [])) if isinstance(swda_buckets, dict) else 0
        if go_count == 0 or swda_count == 0:
            return fail("FastTrack separated dataset pool", f"empty source pool: {pool_path}")
        if question_count:
            return fail("FastTrack separated dataset pool", f"QUESTION response-act items are not allowed: {question_count}")
        return ok(
            "FastTrack separated dataset pool",
            f"{pool_path}; go_emotions={go_count}; swda={swda_count}; separated_sources=true",
        )

    if not getattr(cfg, "FAST_TRACK_PERSONA_BUNDLE_ENABLED", False):
        return skip("FastTrack persona bundle", "disabled by FAST_TRACK_PERSONA_BUNDLE_ENABLED=0", required=False)
    manifest_path = cfg.FAST_TRACK_PERSONA_BUNDLE_PATH
    if not manifest_path.exists():
        return fail("FastTrack persona bundle", f"missing: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata = payload.get("tts_reference", {}) if isinstance(payload, dict) else {}
    reference_id = str(metadata.get("reference_id", "")).strip()
    uses_cached_audio = str(getattr(cfg, "FAST_TRACK_TTS_MODE", "")) == "cached_fish_bundle"
    expected = str(getattr(cfg, "FAST_TRACK_AUDIO_CACHE_REFERENCE_ID", "") or "").strip()
    if uses_cached_audio and expected and reference_id != expected:
        return fail(
            "FastTrack persona bundle",
            f"reference mismatch: manifest={reference_id!r}, expected={expected!r}",
        )

    personality_id = str(payload.get("personality_id", "")).strip()
    expected_personality = str(getattr(cfg, "FAST_TRACK_PERSONA_ID", "") or "").strip()
    if expected_personality and personality_id != expected_personality:
        return fail(
            "FastTrack persona bundle",
            f"personality mismatch: manifest={personality_id!r}, expected={expected_personality!r}",
        )

    root = manifest_path.parent
    total = 0
    usable_audio = 0
    usable_text = 0
    for item in payload.get("items", []):
        total += 1
        if str(item.get("plain_tts_text") or item.get("reaction") or "").strip():
            usable_text += 1
        raw_audio_path = str(item.get("audio_path") or "").strip()
        if raw_audio_path:
            audio_path = Path(raw_audio_path)
            if not audio_path.is_absolute():
                audio_path = root / audio_path
            if audio_path.exists():
                usable_audio += 1

    if uses_cached_audio and usable_audio == 0:
        return fail("FastTrack persona bundle", f"no usable audio_path files in {manifest_path}")
    if usable_text == 0:
        return fail("FastTrack persona text pool", f"no usable text items in {manifest_path}")
    return ok(
        "FastTrack persona text pool",
        f"{manifest_path}; usable_text={usable_text}/{total}; legacy_audio={usable_audio}/{total}",
    )


def check_interjection_audio_bundle(cfg: Any) -> CheckResult:
    """Verify legacy prebuilt interjection audio only when the live path enables it."""
    manifest_path = getattr(
        cfg,
        "CREDO_INTERJECTION_AUDIO_BUNDLE_PATH",
        ROOT / "fasttrack_assets" / "audio" / "expressive_interjection_bundle" / "manifest.json",
    )
    component_mode = str(getattr(cfg, "CREDO_FASTTRACK_COMPONENT_MODE", "both")).strip().lower()
    enabled = bool(getattr(cfg, "CREDO_NONVERBAL_FASTTRACK_ENABLED", False))
    required = enabled and component_mode in {"both", "nonverbal_only"}
    if not enabled:
        return skip(
            "Interjection audio bundle",
            "disabled by CREDO_NONVERBAL_FASTTRACK_ENABLED=0; live FastTrack uses speech + emotion motion",
        )
    if not manifest_path.exists():
        return fail("Interjection audio bundle", f"missing: {manifest_path}", required=required)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    tts_reference = payload.get("tts_reference") or {}
    reference_id = str(tts_reference.get("reference_id") or "")
    reference_engine = str(tts_reference.get("engine") or "fish_speech")
    expected_reference_id = str(getattr(cfg, "FISH_SPEECH_REFERENCE_ID", "") or "")
    if required and reference_engine == "fish_speech" and expected_reference_id and reference_id != expected_reference_id:
        return fail(
            "Interjection audio bundle",
            f"{manifest_path}; reference mismatch: manifest={reference_id!r}, "
            f"expected={expected_reference_id!r}",
            required=True,
        )
    carriers = [str(item.get("carrier") or "").strip() for item in items]
    if not any(carriers):
        return fail("Interjection audio bundle", f"no carrier text in {manifest_path}", required=required)
    audio_count = 0
    for item in items:
        audio_path = Path(str(item.get("audio_path") or ""))
        if not audio_path.is_absolute():
            audio_path = manifest_path.parent / audio_path
        if audio_path.exists():
            audio_count += 1
    if required and audio_count != len(items):
        return fail(
            "Interjection audio bundle",
            f"{manifest_path}; prebuilt_audio={audio_count}/{len(items)}",
            required=True,
        )
    return ok(
        "Interjection audio bundle",
        f"{manifest_path}; prebuilt_audio={audio_count}/{len(items)}; "
        f"engine={reference_engine}; reference_id={reference_id}",
        required=required,
    )


def collect_checks() -> list[CheckResult]:
    cfg = load_config()
    open_llm_dir = PROJECT_ROOT / "vendor" / "open-llm-vtuber"
    stylebert_dir = PROJECT_ROOT / "vendor" / "Style-Bert-VITS2"

    checks = [
        check_path("Open-LLM-VTuber runtime", open_llm_dir / ".venv" / "bin" / "python", executable=True),
        check_open_llm_module("edge_tts"),
        check_path("SetFit optimized intent model", ROOT / "fasttrack_assets" / "models" / "setfit_swda_intent_minilm_optimized" / "model_head.pkl"),
        check_path("Hybrid reaction list", ROOT / "hybrid_reactions.json"),
        check_interjection_audio_bundle(cfg),
        check_path("Legacy expressive audio manifest", ROOT / "archive" / "legacy_audio" / "expressive_audio_pool" / "manifest.json", required=False),
        check_fast_track_audio_cache(cfg),
        check_persona_reaction_bundle(cfg),
        check_intent_matrix(),
        check_motion_groups(),
        check_import("spacy"),
        check_import("transformers"),
        check_import("setfit", required=False),
        check_import("faiss", required=False),
        check_import("websockets", required=False),
        check_youtube_bridge_dependency(),
        check_http("Local LLM endpoint", f"{cfg.LOCAL_LLM_BASE_URL.rstrip('/')}/models", required=False),
        check_tcp("Open-LLM-VTuber web server", "127.0.0.1", 12393, required=False),
    ]
    if not getattr(cfg, "FAST_TRACK_ENABLED", True):
        checks.append(skip("FastTrack", "disabled by FAST_TRACK_ENABLED=0 for SlowTrack-only experiment"))
        checks.append(skip("FastTrack realtime TTS", "not required when FastTrack is disabled"))
    elif cfg.FAST_TRACK_TTS_MODE == "edge_tts":
        checks.append(ok("FastTrack realtime TTS", f"Edge TTS voice={cfg.OPEN_LLM_VTUBER_EDGE_TTS_VOICE}"))
    elif cfg.FAST_TRACK_TTS_MODE == "piper_tts":
        checks.extend(check_piper_tts(cfg))
        checks.append(skip("Style-Bert-VITS2", "legacy backend disabled by FAST_TRACK_TTS_MODE=piper_tts"))
    elif cfg.FAST_TRACK_TTS_MODE == "stylebert_vits2":
        checks.extend(
            [
                check_path("Style-Bert-VITS2 repo", stylebert_dir, required=False),
                check_path(
                    "Style-Bert-VITS2 runtime",
                    stylebert_dir / ".venv" / "bin" / "python",
                    required=False,
                    executable=True,
                ),
                check_path("Style-Bert-VITS2 model assets", stylebert_dir / "model_assets", required=False),
                check_stylebert_model_name(cfg, stylebert_dir / "model_assets"),
                check_stylebert_device(cfg),
                check_http("Style-Bert-VITS2 endpoint", cfg.STYLEBERT_VITS2_HEALTH_URL, required=False),
            ]
        )
    elif cfg.FAST_TRACK_TTS_MODE == "prebuilt_stylebert_manifest":
        checks.append(check_prebuilt_stylebert_fasttrack_manifest(cfg))
    else:
        checks.append(skip("FastTrack realtime TTS", f"disabled by FAST_TRACK_TTS_MODE={cfg.FAST_TRACK_TTS_MODE}"))
    return checks


def summarize(checks: list[CheckResult]) -> dict[str, Any]:
    required_failed = [item for item in checks if item.required and item.status == "FAIL"]
    optional_failed = [item for item in checks if not item.required and item.status == "FAIL"]
    warnings = [item for item in checks if item.status == "WARN"]
    if required_failed:
        readiness = "BLOCKED"
    elif optional_failed or warnings:
        readiness = "PARTIAL"
    else:
        readiness = "READY"
    return {
        "readiness": readiness,
        "required_failed": len(required_failed),
        "optional_failed": len(optional_failed),
        "warnings": len(warnings),
        "checked_at_unix": time.time(),
    }


def write_markdown(path: Path, summary: dict[str, Any], checks: list[CheckResult]) -> None:
    lines = [
        "# CREDO Runtime Readiness",
        "",
        f"- readiness: {summary['readiness']}",
        f"- required_failed: {summary['required_failed']}",
        f"- optional_failed: {summary['optional_failed']}",
        f"- warnings: {summary['warnings']}",
        "",
        "## Checks",
        "| status | required | item | detail |",
        "| --- | --- | --- | --- |",
    ]
    for item in checks:
        detail = item.detail.replace("|", "\\|")
        lines.append(f"| {item.status} | {item.required} | {item.name} | {detail} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- READY: the full configured demo stack is reachable.",
            "- PARTIAL: the core code/data exists, but at least one optional server or feature is not running.",
            "- BLOCKED: a required model, dataset artifact, avatar asset, or Python runtime is missing.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_runtime_python()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--print", action="store_true", help="Print the markdown report to stdout.")
    args = parser.parse_args()

    checks = collect_checks()
    summary = summarize(checks)
    payload = {"summary": summary, "checks": [asdict(item) for item in checks]}

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(args.markdown, summary, checks)

    if args.print:
        print(args.markdown.read_text(encoding="utf-8"))
    else:
        print(f"Readiness: {summary['readiness']}")
        print(f"Wrote {args.json}")
        print(f"Wrote {args.markdown}")


if __name__ == "__main__":
    main()
