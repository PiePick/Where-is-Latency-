#!/usr/bin/env python3
"""Collect CREDO FastTrack assets into one navigable folder.

The default mode creates symlinks so runtime paths remain unchanged and the
large audio/model assets are not duplicated. Use --mode copy only when a
portable snapshot is needed.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "fasttrack_assets"


@dataclass(frozen=True)
class AssetLink:
    name: str
    source: Path
    destination: Path
    purpose: str


def build_assets(asset_root: Path) -> list[AssetLink]:
    """Return the FastTrack asset map for a chosen destination root."""
    return [
    AssetLink(
        "prepared_datasets",
        ROOT / "prepared_fasttrack_data",
        asset_root / "datasets" / "prepared_fasttrack_data",
        "GoEmotions/SWDA prepared JSONL files for FastTrack classification and routing.",
    ),
    AssetLink(
        "swda_intent_model_optimized",
        ROOT / "models" / "setfit_swda_intent_minilm_optimized",
        asset_root / "models" / "setfit_swda_intent_minilm_optimized",
        "Optimized SetFit model for SWDA coarse intent classification.",
    ),
    AssetLink(
        "swda_intent_model_baseline",
        ROOT / "models" / "setfit_swda_intent_minilm",
        asset_root / "models" / "setfit_swda_intent_minilm",
        "Baseline SetFit SWDA intent model kept for comparison.",
    ),
    AssetLink(
        "persona_reaction_audio",
        ROOT / "persona_reaction_bundle_response_act_v1",
        asset_root / "audio" / "persona_reaction_bundle_response_act_v1",
        "600 prebuilt persona-filtered FastTrack reaction wav files and manifest.",
    ),
    AssetLink(
        "interjection_motion_audio",
        ROOT / "expressive_interjection_bundle",
        asset_root / "audio" / "expressive_interjection_bundle",
        "Pure interjection/filler audio aligned with FastTrack Live2D motion tags.",
    ),
    AssetLink(
        "thinking_bridge_audio",
        ROOT / "thinking_bridge_bundle",
        asset_root / "audio" / "thinking_bridge_bundle",
        "Short spoken thinking bridges after FastTrack while SlowTrack is pending.",
    ),
    AssetLink(
        "professor_jinsama_callout_audio",
        ROOT / "professor_jinsama_call_bundle",
        asset_root / "audio" / "professor_jinsama_call_bundle",
        "Special FastTrack callout bundle for Professor Jinsama.",
    ),
    AssetLink(
        "runtime_config",
        ROOT / "config.py",
        asset_root / "runtime" / "config.py",
        "FastTrack/SlowTrack runtime configuration defaults.",
    ),
    AssetLink(
        "intent_transition_matrix",
        ROOT / "intent_transition_matrix.py",
        asset_root / "runtime" / "intent_transition_matrix.py",
        "SWDA-derived user-intent to response-act transition logic.",
    ),
    AssetLink(
        "fast_track_facade",
        ROOT / "fast_track.py",
        asset_root / "runtime" / "fast_track.py",
        "Stable FastTrack facade used by integrations.",
    ),
    AssetLink(
        "fast_track_engine",
        ROOT / "fast_track_engine.py",
        asset_root / "runtime" / "fast_track_engine.py",
        "Hybrid FastTrack classifier/router implementation.",
    ),
    ]


def rel(path: Path) -> str:
    """Return a repository-relative display path when possible."""
    try:
        return path.relative_to(ROOT.parent).as_posix()
    except ValueError:
        return str(path)


def remove_destination(path: Path) -> None:
    """Remove an existing generated link/copy destination."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def link_asset(asset: AssetLink, *, mode: str, force: bool) -> dict:
    """Create one link/copy and return index metadata."""
    asset.destination.parent.mkdir(parents=True, exist_ok=True)
    exists = asset.source.exists()
    if asset.destination.exists() or asset.destination.is_symlink():
        if force:
            remove_destination(asset.destination)
        else:
            action = "symlink" if asset.destination.is_symlink() else "copy"
            return asset_index(asset, exists=exists, action=action)

    if exists:
        if mode == "copy":
            if asset.source.is_dir():
                shutil.copytree(asset.source, asset.destination)
            else:
                shutil.copy2(asset.source, asset.destination)
        else:
            up_levels = len(asset.destination.parent.relative_to(ASSET_ROOT).parts) + 1
            target = Path("../" * up_levels) / asset.source.relative_to(ROOT)
            asset.destination.symlink_to(target, target_is_directory=asset.source.is_dir())
        action = mode
    else:
        action = "missing"
    return asset_index(asset, exists=exists, action=action)


def count_files(path: Path, pattern: str) -> int:
    """Count files under a source path."""
    if path.is_file():
        return 1 if path.match(pattern) else 0
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def asset_index(asset: AssetLink, *, exists: bool, action: str) -> dict:
    """Build index metadata for one FastTrack asset."""
    return {
        "name": asset.name,
        "purpose": asset.purpose,
        "source": rel(asset.source),
        "destination": rel(asset.destination),
        "exists": exists,
        "action": action,
        "counts": {
            "wav": count_files(asset.source, "*.wav"),
            "jsonl": count_files(asset.source, "*.jsonl"),
            "json": count_files(asset.source, "*.json"),
            "safetensors": count_files(asset.source, "*.safetensors"),
        },
    }


def write_index(entries: list[dict], *, mode: str) -> Path:
    """Write a compact generated inventory for the organized asset folder."""
    index = {
        "mode": mode,
        "asset_root": rel(ASSET_ROOT),
        "entries": entries,
    }
    path = ASSET_ROOT / "INDEX.generated.json"
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect CREDO FastTrack assets into one folder.")
    parser.add_argument("--asset-root", type=Path, default=ASSET_ROOT)
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    global ASSET_ROOT
    args = parse_args()
    ASSET_ROOT = args.asset_root
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)

    entries = [link_asset(asset, mode=args.mode, force=args.force) for asset in build_assets(ASSET_ROOT)]
    index_path = write_index(entries, mode=args.mode)
    print(f"Wrote FastTrack asset index: {index_path}")
    for entry in entries:
        print(f"{entry['action']}: {entry['destination']} <- {entry['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
