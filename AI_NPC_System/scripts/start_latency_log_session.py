#!/usr/bin/env python3
"""Create a fresh CREDO latency logging session.

The runtime already writes session-scoped logs when CREDO_LATENCY_LOG_STEM is
set. This helper initializes the files up front and can also update
project_config.sh so the next stack run writes to the new session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG = ROOT / "project_config.sh"
DEFAULT_LOG_DIR = ROOT / "latency_logs"

sys.path.insert(0, str(ROOT))
from latency_observer import LatencyLogger  # noqa: E402


def sanitize_stem(raw: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", raw.strip())
    stem = stem.strip("_")
    if not stem:
        raise ValueError("empty latency session stem")
    return stem


def replace_export(text: str, name: str, value: str) -> str:
    line = f'export {name}="{value}"'
    pattern = re.compile(rf'^export {re.escape(name)}="[^"]*"$', re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(line, text)
    return text.rstrip() + "\n" + line + "\n"


def update_project_config(stem: str, log_dir: str) -> None:
    text = PROJECT_CONFIG.read_text(encoding="utf-8")
    text = replace_export(text, "CREDO_LOG_SESSION_ID", stem)
    text = replace_export(text, "CREDO_LATENCY_LOG_STEM", stem)
    text = replace_export(text, "CREDO_LATENCY_LOG_DIR", log_dir)
    text = replace_export(text, "CREDO_RUNTIME_LOG_STEM", stem)
    PROJECT_CONFIG.write_text(text, encoding="utf-8")


def write_session_note(stem: str, logger: LatencyLogger, profile: str) -> Path:
    note_path = logger.module_csv_path.with_name(f"{stem}.session.json")
    payload = {
        "session_id": stem,
        "created_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "profile": profile,
        "jsonl": str(logger.jsonl_path),
        "module_csv": str(logger.module_csv_path),
        "summary_md": str(logger.markdown_path),
        "analysis_note": (
            "Use warm participant/session rows only. Exclude cold-start, failed "
            "server-start, and operator-debug rows before statistical analysis."
        ),
    }
    note_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return note_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stem",
        default="",
        help="Session stem. Defaults to paper_latency_YYYYMMDD_HHMMSS.",
    )
    parser.add_argument(
        "--log-dir",
        default="latency_logs",
        help="Log directory relative to AI_NPC_System, or an absolute path.",
    )
    parser.add_argument(
        "--profile",
        default="paper-latency-quant",
        help="Short metadata label stored in the session json.",
    )
    parser.add_argument(
        "--update-config",
        action="store_true",
        help="Persist the session stem in AI_NPC_System/project_config.sh.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stem = sanitize_stem(args.stem or datetime.now().strftime("paper_latency_%Y%m%d_%H%M%S"))
    log_dir = args.log_dir.strip() or "latency_logs"

    os.environ["CREDO_LATENCY_LOG_STEM"] = stem
    os.environ["CREDO_LATENCY_LOG_DIR"] = log_dir

    if args.update_config:
        update_project_config(stem, log_dir)

    logger = LatencyLogger()
    logger.initialize_files()
    note_path = write_session_note(stem, logger, args.profile)

    print(f"session_id={stem}")
    print(f"jsonl={logger.jsonl_path}")
    print(f"module_csv={logger.module_csv_path}")
    print(f"summary_md={logger.markdown_path}")
    print(f"session_note={note_path}")
    if args.update_config:
        print(f"updated_config={PROJECT_CONFIG}")
    else:
        print("config_not_updated=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
