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
    "live": ("fish", "llm", "piper", "open-llm"),
    "live-no-piper": ("fish", "llm", "open-llm"),
    "cache": ("fish",),
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
    log_path = LOG_DIR / f"{service.name}.log"
    log_file = log_path.open("ab")
    log(f"{service.name}: starting -> {' '.join(service.command)}")
    log(f"{service.name}: log -> {log_path}")
    process = subprocess.Popen(
        list(service.command),
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
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
        help="Per-health-check timeout. Keep this above Fish Speech single-request latency to avoid busy/dead confusion.",
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
        return monitor(
            runtimes,
            interval=args.monitor_interval,
            max_restarts=args.max_restarts,
            no_restart=args.no_restart,
            http_timeout=args.health_timeout,
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
