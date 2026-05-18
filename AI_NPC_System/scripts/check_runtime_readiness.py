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


def collect_checks() -> list[CheckResult]:
    cfg = load_config()
    open_llm_dir = PROJECT_ROOT / "vendor" / "open-llm-vtuber"
    fish_dir = PROJECT_ROOT / "vendor" / "fish-speech"
    stylebert_dir = PROJECT_ROOT / "vendor" / "Style-Bert-VITS2"
    fish_reference_dir = fish_dir / "references" / str(cfg.FISH_SPEECH_REFERENCE_ID)

    checks = [
        check_path("Open-LLM-VTuber runtime", open_llm_dir / ".venv" / "bin" / "python", executable=True),
        check_path("Fish Speech checkpoint", fish_dir / "checkpoints" / os.getenv("FISH_SPEECH_CHECKPOINT_NAME", "s2-pro")),
        check_fish_reference_voice(fish_reference_dir),
        check_path("SetFit optimized intent model", ROOT / "models" / "setfit_swda_intent_minilm_optimized" / "model_head.pkl"),
        check_path("Hybrid reaction list", ROOT / "hybrid_reactions.json"),
        check_path("Expressive audio manifest", ROOT / "expressive_audio_pool" / "manifest.json", required=False),
        check_fast_track_audio_cache(cfg),
        check_intent_matrix(),
        check_motion_groups(),
        check_import("spacy"),
        check_import("transformers"),
        check_import("setfit", required=False),
        check_import("faiss", required=False),
        check_import("websockets", required=False),
        check_youtube_bridge_dependency(),
        check_http("Local LLM endpoint", f"{cfg.LOCAL_LLM_BASE_URL.rstrip('/')}/models", required=False),
        check_http("Fish Speech endpoint", cfg.FISH_SPEECH_HEALTH_URL, required=False),
        check_tcp("Open-LLM-VTuber web server", "127.0.0.1", 12393, required=False),
    ]
    if cfg.FAST_TRACK_TTS_MODE == "piper_tts":
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
