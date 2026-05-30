#!/usr/bin/env python3
"""Run and supervise the full CREDO local runtime stack.

This is the intended one-command entrypoint for a live CREDO session. It starts
services in dependency order, waits for their health endpoints, writes logs/pids,
and keeps watching child processes so server crashes are visible immediately.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
AI_NPC_DIR = ROOT / "AI_NPC_System"
RUNTIME_DIR = AI_NPC_DIR / "runtime"
LOG_DIR = RUNTIME_DIR / "logs"
PID_DIR = RUNTIME_DIR / "pids"
STATE_PATH = RUNTIME_DIR / "credo_stack_state.json"
PROJECT_CONFIG_PATH = AI_NPC_DIR / "project_config.sh"


@dataclass(frozen=True)
class StackService:
    name: str
    command: tuple[str, ...]
    health_url: str
    startup_timeout: float
    required: bool = True
    restart: bool = True


@dataclass
class RuntimeProcess:
    service: StackService
    process: subprocess.Popen[bytes] | None
    external: bool
    restarts: int = 0
    last_start_unix: float = 0.0


SERVICES: dict[str, StackService] = {
    "fish": StackService(
        name="fish",
        command=("AI_NPC_System/scripts/start_fish_speech_server.sh",),
        health_url="http://127.0.0.1:8080/v1/health",
        startup_timeout=480.0,
    ),
    "llm": StackService(
        name="llm",
        command=("AI_NPC_System/scripts/start_local_llm_server.sh",),
        health_url="http://127.0.0.1:8001/v1/models",
        startup_timeout=600.0,
    ),
    "stylebert": StackService(
        name="stylebert",
        command=("AI_NPC_System/scripts/start_stylebert_vits2_server.sh",),
        health_url="http://127.0.0.1:5000/docs",
        startup_timeout=240.0,
    ),
    "piper": StackService(
        name="piper",
        command=("AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh",),
        health_url="http://127.0.0.1:5001/health",
        startup_timeout=90.0,
        required=False,
    ),
    "open-llm": StackService(
        name="open-llm",
        command=("AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh",),
        health_url="http://127.0.0.1:12393/",
        startup_timeout=180.0,
        restart=False,
    ),
}

PROFILES = {
    "live": ("stylebert", "llm", "open-llm"),
    "live-piper": ("llm", "piper", "open-llm"),
    "live-no-piper": ("llm", "open-llm"),
    "live-stylebert": ("stylebert", "llm", "open-llm"),
    "cache": ("fish",),
    "stylebert-only": ("stylebert",),
    "llm-only": ("llm",),
}


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def health_ok(url: str, timeout: float = 15.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def load_project_env() -> dict[str, str]:
    """Read simple `export KEY=value` entries from project_config.sh."""
    env = dict(os.environ)
    if not PROJECT_CONFIG_PATH.exists():
        return env
    for raw_line in PROJECT_CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("export ") or "=" not in line:
            continue
        key, value = line[len("export ") :].split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            env[key] = value
    return env


def post_json(url: str, payload: dict[str, object], *, timeout: float) -> dict[str, object]:
    """POST JSON and parse a JSON response when present."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    if not body.strip():
        return {}
    return json.loads(body)


def warmup_stylebert(*, timeout: float) -> None:
    """Eliminate StyleBERT cold first-synthesis latency before live use."""
    env = load_project_env()
    voice_url = env.get("STYLEBERT_VITS2_VOICE_URL") or f"{env.get('STYLEBERT_VITS2_BASE_URL', 'http://127.0.0.1:5000')}/voice"
    params = {
        "text": env.get("CREDO_STYLEBERT_WARMUP_TEXT", "Warmup."),
        "model_id": env.get("STYLEBERT_VITS2_MODEL_ID", "0"),
        "speaker_id": env.get("STYLEBERT_VITS2_SPEAKER_ID", "0"),
        "style": env.get("STYLEBERT_VITS2_STYLE", "Neutral"),
        "style_weight": env.get("STYLEBERT_VITS2_STYLE_WEIGHT", "1.0"),
        "sdp_ratio": env.get("STYLEBERT_VITS2_SDP_RATIO", "0.1"),
        "noise": env.get("STYLEBERT_VITS2_NOISE", "0.35"),
        "noisew": env.get("STYLEBERT_VITS2_NOISEW", "0.45"),
        "length": env.get("STYLEBERT_VITS2_LENGTH", "0.95"),
        "language": env.get("STYLEBERT_VITS2_LANGUAGE", "EN"),
    }
    model_name = env.get("STYLEBERT_VITS2_MODEL_NAME", "")
    if model_name:
        params["model_name"] = model_name
    separator = "&" if "?" in voice_url else "?"
    url = f"{voice_url}{separator}{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "audio/wav"}, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        audio = response.read()
    elapsed = (time.perf_counter() - started) * 1000.0
    if response.status >= 400 or len(audio) < 128:
        raise RuntimeError(f"StyleBERT warmup returned status={response.status}, bytes={len(audio)}")
    log(f"stylebert: warmup synthesized {len(audio)} bytes in {elapsed:.1f} ms")


def warmup_llm(*, timeout: float) -> None:
    """Eliminate local LLM cold first-token/model-load latency before live use."""
    env = load_project_env()
    base_url = env.get("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
    model = env.get("LOCAL_LLM_MODEL", "qwen2.5:7b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a startup warmup probe. Reply with OK only."},
            {"role": "user", "content": "warmup"},
        ],
        "max_tokens": 4,
        "temperature": 0.0,
        "stream": False,
    }
    started = time.perf_counter()
    response = post_json(f"{base_url}/chat/completions", payload, timeout=timeout)
    elapsed = (time.perf_counter() - started) * 1000.0
    choices = response.get("choices") if isinstance(response, dict) else None
    if not choices:
        raise RuntimeError("LLM warmup returned no choices")
    log(f"llm: warmup chat completion finished in {elapsed:.1f} ms")


def warmup_open_llm(*, timeout: float) -> None:
    """Touch the Open-LLM-VTuber CREDO status route after server startup."""
    url = "http://127.0.0.1:12393/credo/vtuber-mode/status"
    started = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        response.read()
    elapsed = (time.perf_counter() - started) * 1000.0
    if response.status >= 400:
        raise RuntimeError(f"Open-LLM status warmup returned HTTP {response.status}")
    log(f"open-llm: warmup status route finished in {elapsed:.1f} ms")


def warmup_service(name: str, *, timeout: float, required: bool) -> None:
    """Run service-specific warmup probes so first live turn is not cold."""
    warmers = {
        "stylebert": warmup_stylebert,
        "llm": warmup_llm,
        "open-llm": warmup_open_llm,
    }
    warmer = warmers.get(name)
    if warmer is None:
        return
    log(f"{name}: warmup starting")
    try:
        warmer(timeout=timeout)
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        if required:
            raise RuntimeError(f"{name}: warmup failed ({detail})") from exc
        log(f"{name}: optional warmup failed ({detail})")


def tcp_open(url: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_health(service: StackService, timeout: float | None = None, http_timeout: float = 15.0) -> bool:
    deadline = time.time() + (timeout if timeout is not None else service.startup_timeout)
    while time.time() < deadline:
        if health_ok(service.health_url, timeout=http_timeout):
            return True
        time.sleep(3.0)
    return False


def start_service(service: StackService, *, http_timeout: float = 15.0) -> RuntimeProcess:
    if health_ok(service.health_url, timeout=http_timeout):
        log(f"{service.name}: already healthy at {service.health_url}; reusing external process")
        return RuntimeProcess(service=service, process=None, external=True)
    if tcp_open(service.health_url):
        log(f"{service.name}: port is open but health is busy/slow at {service.health_url}; reusing external process")
        return RuntimeProcess(service=service, process=None, external=True)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    env = load_project_env()
    runtime_log_stem = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in str(env.get("CREDO_RUNTIME_LOG_STEM") or "").strip()
    )
    log_path = LOG_DIR / f"{service.name}.{runtime_log_stem}.log" if runtime_log_stem else LOG_DIR / f"{service.name}.log"
    log_file = log_path.open("ab")
    log(f"{service.name}: starting -> {' '.join(service.command)}")
    log(f"{service.name}: log -> {log_path}")
    process = subprocess.Popen(
        list(service.command),
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    (PID_DIR / f"{service.name}.pid").write_text(str(process.pid), encoding="utf-8")
    runtime = RuntimeProcess(service=service, process=process, external=False, last_start_unix=time.time())
    if not wait_health(service, http_timeout=http_timeout):
        exit_code = process.poll()
        detail = f"process exited with {exit_code}" if exit_code is not None else "health timeout"
        if service.required:
            raise RuntimeError(f"{service.name}: failed startup ({detail}); see {log_path}")
        log(f"{service.name}: optional service not ready ({detail})")
    else:
        log(f"{service.name}: healthy at {service.health_url}")
    return runtime


def stop_runtime(runtime: RuntimeProcess) -> None:
    if runtime.external or runtime.process is None:
        return
    if runtime.process.poll() is not None:
        return
    service = runtime.service
    log(f"{service.name}: stopping pid={runtime.process.pid}")
    try:
        os.killpg(runtime.process.pid, signal.SIGTERM)
    except Exception:
        runtime.process.terminate()


def write_state(runtimes: dict[str, RuntimeProcess], *, http_timeout: float = 15.0) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at_unix": time.time(),
        "services": {
            name: {
                "health_url": runtime.service.health_url,
                "external": runtime.external,
                "pid": runtime.process.pid if runtime.process is not None else None,
                "poll": runtime.process.poll() if runtime.process is not None else None,
                "restarts": runtime.restarts,
                "healthy": health_ok(runtime.service.health_url, timeout=http_timeout),
                "tcp_open": tcp_open(runtime.service.health_url),
            }
            for name, runtime in runtimes.items()
        },
    }
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def monitor(
    runtimes: dict[str, RuntimeProcess],
    *,
    interval: float,
    max_restarts: int,
    no_restart: bool,
    http_timeout: float,
    warmup_enabled: bool,
    warmup_timeout: float,
) -> int:
    log("stack: entering monitor loop")
    while True:
        write_state(runtimes, http_timeout=http_timeout)
        for name, runtime in list(runtimes.items()):
            service = runtime.service
            healthy = health_ok(service.health_url, timeout=http_timeout)
            if runtime.external:
                if not healthy and service.required:
                    log(f"{name}: external service became unhealthy at {service.health_url}")
                continue

            process = runtime.process
            if process is None:
                continue
            exit_code = process.poll()
            if exit_code is None and healthy:
                continue
            if exit_code is None and not healthy and tcp_open(service.health_url):
                log(f"{name}: process alive; health is busy/slow but TCP port is open")
                continue
            if exit_code is None and not healthy:
                log(f"{name}: process alive but health check failed and TCP port is closed")
                continue

            log(f"{name}: process exited with {exit_code}")
            if no_restart or not service.restart or runtime.restarts >= max_restarts:
                if service.required:
                    return exit_code if exit_code is not None else 1
                continue

            runtime.restarts += 1
            log(f"{name}: restarting ({runtime.restarts}/{max_restarts})")
            restarted = start_service(service, http_timeout=http_timeout)
            if warmup_enabled:
                warmup_service(name, timeout=warmup_timeout, required=service.required)
            restarted.restarts = runtime.restarts
            runtimes[name] = restarted
        time.sleep(interval)


def resolve_services(profile: str, only: str | None, skip: str | None) -> list[str]:
    if only:
        names = tuple(item.strip() for item in only.split(",") if item.strip())
    else:
        names = PROFILES[profile]
    skip_set = {item.strip() for item in (skip or "").split(",") if item.strip()}
    unknown = [item for item in names if item not in SERVICES]
    if unknown:
        raise SystemExit(f"Unknown service(s): {', '.join(unknown)}")
    return [item for item in names if item not in skip_set]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="live")
    parser.add_argument("--only", help="Comma-separated service override.")
    parser.add_argument("--skip", help="Comma-separated services to skip.")
    parser.add_argument("--status", action="store_true", help="Only print health status.")
    parser.add_argument("--no-restart", action="store_true", help="Do not restart crashed child services.")
    parser.add_argument("--max-restarts", type=int, default=2)
    parser.add_argument("--monitor-interval", type=float, default=10.0)
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=30.0,
        help="Per-health-check timeout. Increase this only for archived cache generation while Fish Speech is busy.",
    )
    parser.add_argument(
        "--warmup-timeout",
        type=float,
        default=120.0,
        help="Timeout for first-request warmup probes after service health is ready.",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip first-request warmup probes. Not recommended for live experiments.",
    )
    args = parser.parse_args()

    services = resolve_services(args.profile, args.only, args.skip)
    if args.status:
        rows = []
        for name in services:
            service = SERVICES[name]
            rows.append(
                {
                    "name": name,
                    "url": service.health_url,
                    "healthy": health_ok(service.health_url, timeout=args.health_timeout),
                    "tcp_open": tcp_open(service.health_url),
                }
            )
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0 if all(row["healthy"] or not SERVICES[row["name"]].required for row in rows) else 1

    runtimes: dict[str, RuntimeProcess] = {}
    try:
        for name in services:
            runtimes[name] = start_service(SERVICES[name], http_timeout=args.health_timeout)
            if not args.no_warmup:
                warmup_service(name, timeout=args.warmup_timeout, required=SERVICES[name].required)
        return monitor(
            runtimes,
            interval=args.monitor_interval,
            max_restarts=args.max_restarts,
            no_restart=args.no_restart,
            http_timeout=args.health_timeout,
            warmup_enabled=not args.no_warmup,
            warmup_timeout=args.warmup_timeout,
        )
    except KeyboardInterrupt:
        log("stack: interrupted")
        return 130
    finally:
        for runtime in reversed(list(runtimes.values())):
            stop_runtime(runtime)
        write_state(runtimes, http_timeout=args.health_timeout)


if __name__ == "__main__":
    raise SystemExit(main())
