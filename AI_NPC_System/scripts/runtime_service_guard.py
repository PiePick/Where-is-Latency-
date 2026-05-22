#!/usr/bin/env python3
"""Runtime service guard for CREDO local servers.

The guard gives the project one consistent way to check, wait for, and
optionally start local services used by the Open-LLM-VTuber pipeline. It does
not restart anything unless --ensure is explicitly used.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
AI_NPC_DIR = ROOT / "AI_NPC_System"
REPORT_DIR = AI_NPC_DIR / "reports"
RUNTIME_DIR = AI_NPC_DIR / "runtime"
LOG_DIR = RUNTIME_DIR / "logs"
PID_DIR = RUNTIME_DIR / "pids"
PYTHON = ROOT / "vendor" / "open-llm-vtuber" / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class Service:
    name: str
    url: str
    start_command: tuple[str, ...]
    required_for: str


@dataclass
class ServiceStatus:
    name: str
    ok: bool
    url: str
    detail: str
    elapsed_ms: float | None = None
    pid: int | None = None
    tcp_open: bool = False


SERVICES = {
    "fish": Service(
        name="fish",
        url="http://127.0.0.1:8080/v1/health",
        start_command=("AI_NPC_System/scripts/start_fish_speech_server.sh",),
        required_for="Fish Speech offline cache generation and Fish slow TTS",
    ),
    "llm": Service(
        name="llm",
        url="http://127.0.0.1:8001/v1/models",
        start_command=("AI_NPC_System/scripts/start_local_llm_server.sh",),
        required_for="SlowTrack LLM and manifest LLM filtering",
    ),
    "piper": Service(
        name="piper",
        url="http://127.0.0.1:5001/health",
        start_command=("AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh",),
        required_for="Piper FastTrack realtime fallback",
    ),
    "cosyvoice2": Service(
        name="cosyvoice2",
        url="http://127.0.0.1:50000/",
        start_command=("AI_NPC_System/scripts/start_cosyvoice2_server.sh",),
        required_for="CosyVoice2 experimental Open-LLM-VTuber TTS",
    ),
    "open-llm": Service(
        name="open-llm",
        url="http://127.0.0.1:12393/",
        start_command=("AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh",),
        required_for="Open-LLM-VTuber web runtime",
    ),
}


def service_names(raw: str | None) -> list[str]:
    if not raw or raw == "all":
        return list(SERVICES)
    names = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [item for item in names if item not in SERVICES]
    if unknown:
        raise SystemExit(f"Unknown service(s): {', '.join(unknown)}. Available: {', '.join(SERVICES)}")
    return names


def read_pid(name: str) -> int | None:
    pid_path = PID_DIR / f"{name}.pid"
    try:
        return int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def process_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def tcp_is_open(url: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_service(service: Service, timeout: float) -> ServiceStatus:
    req = urllib.request.Request(service.url, method="GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed = (time.perf_counter() - started) * 1000.0
            ok = 200 <= response.status < 500
            detail = f"HTTP {response.status}"
            return ServiceStatus(service.name, ok, service.url, detail, round(elapsed, 1), read_pid(service.name), True)
    except urllib.error.URLError as exc:
        return ServiceStatus(
            service.name,
            False,
            service.url,
            f"unreachable: {exc}",
            None,
            read_pid(service.name),
            tcp_is_open(service.url),
        )
    except Exception as exc:
        return ServiceStatus(
            service.name,
            False,
            service.url,
            f"error: {exc}",
            None,
            read_pid(service.name),
            tcp_is_open(service.url),
        )


def start_service(service: Service) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{service.name}.log"
    log_file = log_path.open("ab")
    proc = subprocess.Popen(
        list(service.start_command),
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    (PID_DIR / f"{service.name}.pid").write_text(str(proc.pid), encoding="utf-8")
    return proc.pid


def wait_for_services(names: list[str], timeout: float, interval: float, http_timeout: float) -> list[ServiceStatus]:
    deadline = time.time() + timeout
    last_statuses: list[ServiceStatus] = []
    while True:
        last_statuses = [check_service(SERVICES[name], http_timeout) for name in names]
        if all(item.ok for item in last_statuses):
            return last_statuses
        if time.time() >= deadline:
            return last_statuses
        time.sleep(interval)


def write_report(statuses: list[ServiceStatus]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "runtime_services_latest.json"
    payload = {
        "checked_at_unix": time.time(),
        "all_ok": all(item.ok for item in statuses),
        "services": [asdict(item) for item in statuses],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def print_table(statuses: list[ServiceStatus]) -> None:
    for item in statuses:
        state = "OK" if item.ok else ("BUSY" if item.tcp_open else "FAIL")
        elapsed = f"{item.elapsed_ms} ms" if item.elapsed_ms is not None else "-"
        pid = f" pid={item.pid}" if item.pid else ""
        alive = " alive" if process_alive(item.pid) else ""
        print(f"{state:4} {item.name:10} {elapsed:>10} {item.url} {item.detail}{pid}{alive}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--services", default="fish,llm,piper", help="Comma list or all.")
    parser.add_argument("--status", action="store_true", help="Check once and exit.")
    parser.add_argument("--wait", action="store_true", help="Wait until selected services are healthy.")
    parser.add_argument("--ensure", action="store_true", help="Start unhealthy selected services, then wait.")
    parser.add_argument("--watch", action="store_true", help="Continuously check selected services.")
    parser.add_argument("--timeout", type=float, default=600.0, help="Total wait timeout in seconds.")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds.")
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=15.0,
        help="Single HTTP timeout in seconds. Fish Speech can block health while a TTS request is active.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table.")
    args = parser.parse_args()

    names = service_names(args.services)
    if not (args.status or args.wait or args.ensure or args.watch):
        args.status = True

    statuses = [check_service(SERVICES[name], args.http_timeout) for name in names]

    if args.ensure:
        for status in statuses:
            if status.ok:
                continue
            pid = read_pid(status.name)
            if process_alive(pid) or status.tcp_open:
                continue
            started_pid = start_service(SERVICES[status.name])
            print(f"started {status.name} pid={started_pid}", file=sys.stderr)
        statuses = wait_for_services(names, args.timeout, args.interval, args.http_timeout)
    elif args.wait:
        statuses = wait_for_services(names, args.timeout, args.interval, args.http_timeout)
    elif args.watch:
        try:
            while True:
                statuses = [check_service(SERVICES[name], args.http_timeout) for name in names]
                write_report(statuses)
                print(time.strftime("%Y-%m-%d %H:%M:%S"))
                print_table(statuses)
                print("", flush=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return 130

    report_path = write_report(statuses)
    if args.json:
        print(json.dumps({"report": str(report_path), "services": [asdict(item) for item in statuses]}, ensure_ascii=False, indent=2))
    else:
        print_table(statuses)
        print(f"report: {report_path}")
    return 0 if all(item.ok for item in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
