#!/usr/bin/env python3
"""Select the CREDO/Open-LLM-VTuber TTS engines from one command.

This script intentionally edits only the small config lines needed for engine
selection. It avoids rewriting the whole YAML file so local Open-LLM-VTuber
comments and unrelated settings survive repeated experiments.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AI_NPC_DIR = ROOT / "AI_NPC_System"
OLV_DIR = ROOT / "vendor" / "open-llm-vtuber"
CONF_PATH = OLV_DIR / "conf.yaml"
PROJECT_CONFIG_PATH = AI_NPC_DIR / "project_config.sh"
OPEN_LLM_VENV_PYTHON = OLV_DIR / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class Engine:
    name: str
    open_llm_tts_model: str | None
    fast_track_tts_mode: str | None
    description: str
    health_url: str | None = None
    start_command: str | None = None


ENGINES: dict[str, Engine] = {
    "edge": Engine(
        name="edge",
        open_llm_tts_model="edge_tts",
        fast_track_tts_mode="edge_tts",
        description="Open-LLM-VTuber 기본 TTS인 Microsoft Edge TTS. FastTrack/SlowTrack 실시간 영어 경로이며 voice clone은 안 된다.",
    ),
    "cosyvoice2": Engine(
        name="cosyvoice2",
        open_llm_tts_model="cosyvoice2_tts",
        fast_track_tts_mode=None,
        description="CosyVoice2 zero-shot reference voice. 영어 reference를 반영할 수 있고 Fish Speech보다 빠른 중간 지점 후보.",
        health_url="http://127.0.0.1:50000/",
        start_command="AI_NPC_System/scripts/start_cosyvoice2_server.sh",
    ),
    "piper": Engine(
        name="piper",
        open_llm_tts_model=None,
        fast_track_tts_mode="piper_tts",
        description="FastTrack용 경량 영어 TTS. 매우 빠르지만 reference voice clone과 스타일 태그는 없다.",
        health_url="http://127.0.0.1:5001/health",
        start_command="AI_NPC_System/scripts/start_piper_fasttrack_tts_server.sh",
    ),
    "fish": Engine(
        name="fish",
        open_llm_tts_model=None,
        fast_track_tts_mode="fish_speech",
        description="CREDO slow/experimental Fish Speech path. reference와 스타일 실험은 가능하지만 latency가 길다.",
        health_url="http://127.0.0.1:8080/v1/health",
        start_command="AI_NPC_System/scripts/start_fish_speech_server.sh",
    ),
    "stylebert": Engine(
        name="stylebert",
        open_llm_tts_model="stylebert_vits2",
        fast_track_tts_mode="stylebert_vits2",
        description="CREDO VoiceSample-finetuned English StyleBERT voice for both FastTrack and Open-LLM SlowTrack.",
        health_url="http://127.0.0.1:5000/docs",
        start_command="AI_NPC_System/scripts/start_stylebert_vits2_server.sh",
    ),
    "melo": Engine(
        name="melo",
        open_llm_tts_model="melo_tts",
        fast_track_tts_mode=None,
        description="Open-LLM-VTuber 내장 Melo TTS. 영어 가능하지만 voice clone은 아니다.",
    ),
    "coqui": Engine(
        name="coqui",
        open_llm_tts_model="coqui_tts",
        fast_track_tts_mode=None,
        description="Open-LLM-VTuber 내장 Coqui TTS 설정으로 전환한다. 로컬 모델 준비 상태는 별도 확인 필요.",
    ),
}

ALIASES = {
    "edge_tts": "edge",
    "cosy": "cosyvoice2",
    "cosyvoice": "cosyvoice2",
    "cosyvoice2_tts": "cosyvoice2",
    "piper_tts": "piper",
    "fish_speech": "fish",
    "fishspeech": "fish",
    "stylebert_vits2": "stylebert",
    "style-bert-vits2": "stylebert",
    "melo_tts": "melo",
    "coqui_tts": "coqui",
}


def resolve_engine(name: str) -> Engine:
    key = name.strip().lower().replace("_tts", "_tts")
    key = ALIASES.get(key, key)
    if key not in ENGINES:
        available = ", ".join(sorted(ENGINES))
        raise SystemExit(f"Unknown TTS engine '{name}'. Available: {available}")
    return ENGINES[key]


def read_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def write_text_if_changed(path: Path, new_text: str, dry_run: bool) -> bool:
    old_text = read_text(path)
    if old_text == new_text:
        return False
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def set_open_llm_tts_model(conf_text: str, model: str) -> str:
    marker = "  tts_config:\n"
    start = conf_text.find(marker)
    if start < 0:
        raise SystemExit(f"Could not find tts_config block in {CONF_PATH}")
    match = re.search(r"(?m)^    tts_model:\s*.*$", conf_text[start:])
    if not match:
        raise SystemExit(f"Could not find tts_model line in {CONF_PATH}")
    absolute_start = start + match.start()
    absolute_end = start + match.end()
    return conf_text[:absolute_start] + f"    tts_model: {model}" + conf_text[absolute_end:]


def replace_yaml_key_in_block(conf_text: str, block_name: str, key: str, value: str) -> str:
    block_match = re.search(rf"(?m)^    {re.escape(block_name)}:\n", conf_text)
    if not block_match:
        return conf_text
    block_start = block_match.end()
    next_block = re.search(r"(?m)^    [A-Za-z0-9_]+:\n", conf_text[block_start:])
    block_end = block_start + next_block.start() if next_block else len(conf_text)
    block = conf_text[block_start:block_end]
    key_pattern = re.compile(rf"(?m)^      {re.escape(key)}:\s*.*$")
    replacement = f"      {key}: {value}"
    if key_pattern.search(block):
        block = key_pattern.sub(replacement, block, count=1)
    else:
        block += replacement + "\n"
    return conf_text[:block_start] + block + conf_text[block_end:]


def ensure_yaml_block_in_tts_config(conf_text: str, block_name: str) -> str:
    if re.search(rf"(?m)^    {re.escape(block_name)}:\n", conf_text):
        return conf_text
    marker = "  tts_config:\n"
    start = conf_text.find(marker)
    if start < 0:
        raise SystemExit(f"Could not find tts_config block in {CONF_PATH}")
    tts_model = re.search(r"(?m)^    tts_model:\s*.*$", conf_text[start:])
    if not tts_model:
        raise SystemExit(f"Could not find tts_model line in {CONF_PATH}")
    insert_at = start + tts_model.end()
    return conf_text[:insert_at] + f"\n    {block_name}:\n" + conf_text[insert_at:]


def set_project_export(text: str, key: str, value: str) -> str:
    line = f'export {key}="{value}"'
    pattern = re.compile(rf"(?m)^export {re.escape(key)}=.*$")
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    return text.rstrip() + "\n" + line + "\n"


def current_open_llm_tts_model() -> str | None:
    text = read_text(CONF_PATH)
    marker = "  tts_config:\n"
    start = text.find(marker)
    if start < 0:
        return None
    match = re.search(r"(?m)^    tts_model:\s*(\S+)", text[start:])
    return match.group(1) if match else None


def current_fast_track_tts_mode() -> str | None:
    text = read_text(PROJECT_CONFIG_PATH)
    match = re.search(r'(?m)^export FAST_TRACK_TTS_MODE="([^"]+)"', text)
    return match.group(1) if match else None


def url_is_reachable(url: str, timeout: float = 1.5) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout).close()
        return True
    except Exception:
        return False


def module_available(module: str) -> bool:
    if not OPEN_LLM_VENV_PYTHON.exists():
        return False
    result = subprocess.run(
        [str(OPEN_LLM_VENV_PYTHON), "-c", f"import {module}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def check_engine(engine: Engine) -> list[str]:
    notes: list[str] = []
    if engine.open_llm_tts_model == "edge_tts":
        notes.append("edge_tts Python module: " + ("ok" if module_available("edge_tts") else "missing"))
    if engine.open_llm_tts_model == "cosyvoice2_tts":
        cosy_dir = ROOT / "vendor" / "CosyVoice"
        cosy_python = Path("/home/ysree/miniconda3/envs/cosyvoice/bin/python")
        model_dir = cosy_dir / "pretrained_models" / "CosyVoice2-0.5B"
        ref_wav = AI_NPC_DIR / "VoiceSample" / "cosyvoice_refs" / "second_try_16k.wav"
        notes.append(f"CosyVoice repo: {'ok' if cosy_dir.exists() else 'missing'} ({cosy_dir})")
        notes.append(f"CosyVoice conda python: {'ok' if cosy_python.exists() else 'missing'} ({cosy_python})")
        notes.append(f"CosyVoice2 model: {'ok' if model_dir.exists() else 'missing'} ({model_dir})")
        notes.append(f"reference wav: {'ok' if ref_wav.exists() else 'missing'} ({ref_wav})")
    if engine.health_url:
        reachable = url_is_reachable(engine.health_url)
        notes.append(f"server health {engine.health_url}: {'ok' if reachable else 'not running'}")
        if not reachable and engine.start_command:
            notes.append(f"start command: {engine.start_command}")
    return notes


def apply_selection(args: argparse.Namespace, engine: Engine) -> dict[str, object]:
    changed: list[str] = []
    if engine.open_llm_tts_model:
        conf_text = read_text(CONF_PATH)
        conf_text = set_open_llm_tts_model(conf_text, engine.open_llm_tts_model)
        if engine.open_llm_tts_model == "cosyvoice2_tts":
            ref_wav = AI_NPC_DIR / "VoiceSample" / "cosyvoice_refs" / "second_try_16k.wav"
            prompt_text = (
                '"I’m just like any other mom. My kids are a handful, my husband works shifts, '
                'and I have no time to myself. I wonder, Could time grow on trees?"'
            )
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "client_url", "http://127.0.0.1:50000/")
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "mode_checkbox_group", "3s极速复刻")
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "prompt_text", prompt_text)
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "prompt_wav_upload_url", str(ref_wav))
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "prompt_wav_record_url", str(ref_wav))
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "stream", "false")
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "seed", "20260520")
            conf_text = replace_yaml_key_in_block(conf_text, "cosyvoice2_tts", "speed", "1.0")
        if engine.open_llm_tts_model == "stylebert_vits2":
            conf_text = ensure_yaml_block_in_tts_config(conf_text, "stylebert_vits2")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "base_url", "http://127.0.0.1:5000")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "voice_url", "http://127.0.0.1:5000/voice")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "health_url", "http://127.0.0.1:5000/docs")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "output_dir", str(AI_NPC_DIR / "tts_outputs" / "stylebert_fast"))
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "timeout", "30.0")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "model_id", "0")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "model_name", "credo_voice_sample_en")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "speaker_id", "0")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "style", "Neutral")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "style_weight", "1.0")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "sdp_ratio", "0.2")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "noise", "0.55")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "noisew", "0.7")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "length", "0.95")
            conf_text = replace_yaml_key_in_block(conf_text, "stylebert_vits2", "language", "EN")
        if write_text_if_changed(CONF_PATH, conf_text, args.dry_run):
            changed.append(str(CONF_PATH))

        project_text = read_text(PROJECT_CONFIG_PATH)
        project_text = set_project_export(project_text, "OPEN_LLM_VTUBER_TTS_MODEL", engine.open_llm_tts_model)
        if engine.open_llm_tts_model == "edge_tts":
            project_text = set_project_export(project_text, "OPEN_LLM_VTUBER_SLOW_TTS_MODE", "edge_tts")
            project_text = set_project_export(project_text, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", "0")
        elif engine.open_llm_tts_model == "stylebert_vits2":
            project_text = set_project_export(project_text, "OPEN_LLM_VTUBER_SLOW_TTS_MODE", "open_llm")
            project_text = set_project_export(project_text, "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", "1")
        if write_text_if_changed(PROJECT_CONFIG_PATH, project_text, args.dry_run):
            changed.append(str(PROJECT_CONFIG_PATH))

    if engine.fast_track_tts_mode:
        project_text = read_text(PROJECT_CONFIG_PATH)
        project_text = set_project_export(project_text, "FAST_TRACK_TTS_MODE", engine.fast_track_tts_mode)
        if engine.fast_track_tts_mode == "stylebert_vits2":
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_MODEL_NAME", "credo_voice_sample_en")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_LANGUAGE", "EN")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_DEVICE", "cuda")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_STYLE_WEIGHT", "1.0")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_SDP_RATIO", "0.2")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_NOISE", "0.55")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_NOISEW", "0.7")
            project_text = set_project_export(project_text, "STYLEBERT_VITS2_LENGTH", "0.95")
        if engine.fast_track_tts_mode == "edge_tts":
            project_text = set_project_export(project_text, "FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK", "0")
            project_text = set_project_export(project_text, "FAST_TRACK_PREBUILT_ONLY", "0")
        if write_text_if_changed(PROJECT_CONFIG_PATH, project_text, args.dry_run):
            changed.append(str(PROJECT_CONFIG_PATH))

    return {
        "engine": engine.name,
        "changed": sorted(set(changed)),
        "dry_run": args.dry_run,
        "open_llm_tts_model": engine.open_llm_tts_model or current_open_llm_tts_model(),
        "fast_track_tts_mode": engine.fast_track_tts_mode or current_fast_track_tts_mode(),
        "checks": check_engine(engine) if args.check else [],
    }


def print_status(as_json: bool = False) -> None:
    status = {
        "open_llm_tts_model": current_open_llm_tts_model(),
        "fast_track_tts_mode": current_fast_track_tts_mode(),
        "conf_path": str(CONF_PATH),
        "project_config_path": str(PROJECT_CONFIG_PATH),
    }
    if as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"Open-LLM-VTuber TTS: {status['open_llm_tts_model']}")
        print(f"FastTrack TTS: {status['fast_track_tts_mode']}")
        print(f"conf: {status['conf_path']}")
        print(f"project_config: {status['project_config_path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch CREDO/Open-LLM-VTuber TTS engines.")
    parser.add_argument("engine", nargs="?", help="edge, cosyvoice2, piper, fish, stylebert, melo, coqui")
    parser.add_argument("--list", action="store_true", help="List known engine names and exit.")
    parser.add_argument("--status", action="store_true", help="Print current TTS selection and exit.")
    parser.add_argument("--check", action="store_true", help="Print readiness checks for the selected engine.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    if args.list:
        rows = [
            {
                "name": engine.name,
                "open_llm_tts_model": engine.open_llm_tts_model,
                "fast_track_tts_mode": engine.fast_track_tts_mode,
                "description": engine.description,
            }
            for engine in ENGINES.values()
        ]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"{row['name']}: {row['description']}")
        return 0

    if args.status:
        print_status(args.json)
        return 0

    if not args.engine:
        parser.error("engine is required unless --list or --status is used")

    engine = resolve_engine(args.engine)
    result = apply_selection(args, engine)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"selected: {engine.name}")
        print(f"Open-LLM-VTuber TTS: {result['open_llm_tts_model']}")
        print(f"FastTrack TTS: {result['fast_track_tts_mode']}")
        if result["changed"]:
            print("changed:")
            for path in result["changed"]:
                print(f"  {path}")
        else:
            print("changed: none")
        for note in result["checks"]:
            print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
