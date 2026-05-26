#!/usr/bin/env python3
"""Write a compact inventory for the canonical FastTrack asset folder."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "fasttrack_assets"


@dataclass(frozen=True)
class AssetEntry:
    name: str
    path: Path
    purpose: str


def build_entries(asset_root: Path) -> list[AssetEntry]:
    """Return the canonical FastTrack asset map."""
    return [
        AssetEntry(
            "prepared_datasets",
            asset_root / "datasets" / "prepared_fasttrack_data",
            "GoEmotions/SWDA prepared JSONL files for FastTrack classification and routing.",
        ),
        AssetEntry(
            "swda_intent_model_optimized",
            asset_root / "models" / "setfit_swda_intent_minilm_optimized",
            "Optimized SetFit model for SWDA coarse intent classification.",
        ),
        AssetEntry(
            "swda_intent_model_baseline",
            asset_root / "models" / "setfit_swda_intent_minilm",
            "Baseline SetFit SWDA intent model kept for comparison.",
        ),
        AssetEntry(
            "active_separated_dataset_pool",
            asset_root / "text" / "professor_lab_maid_dataset_pool_v1",
            "Active separated GoEmotions/SWDA filtered pool used for runtime FastTrack search and composition.",
        ),
        AssetEntry(
            "interjection_motion_audio",
            asset_root / "audio" / "expressive_interjection_bundle",
            "Pure interjection/filler audio aligned with FastTrack Live2D motion tags.",
        ),
        AssetEntry(
            "runtime_config",
            ROOT / "config.py",
            "FastTrack/SlowTrack runtime configuration defaults.",
        ),
        AssetEntry(
            "intent_transition_matrix",
            ROOT / "intent_transition_matrix.py",
            "SWDA-derived user-intent to response-act transition logic.",
        ),
        AssetEntry(
            "fast_track_facade",
            ROOT / "fast_track.py",
            "Stable FastTrack facade used by integrations.",
        ),
        AssetEntry(
            "fasttrack_router_v3",
            ROOT / "fasttrack_router_v3.py",
            "Async FastTrack router with prefetch bypass and separated dataset-pool lookup.",
        ),
    ]


def rel(path: Path) -> str:
    """Return a repository-relative display path when possible."""
    try:
        return path.relative_to(ROOT.parent).as_posix()
    except ValueError:
        return str(path)


def count_files(path: Path, pattern: str) -> int:
    """Count files under a path."""
    if path.is_file():
        return 1 if path.match(pattern) else 0
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def entry_index(entry: AssetEntry) -> dict:
    """Build index metadata for one FastTrack asset."""
    return {
        "name": entry.name,
        "purpose": entry.purpose,
        "path": rel(entry.path),
        "exists": entry.path.exists(),
        "counts": {
            "wav": count_files(entry.path, "*.wav"),
            "jsonl": count_files(entry.path, "*.jsonl"),
            "json": count_files(entry.path, "*.json"),
            "safetensors": count_files(entry.path, "*.safetensors"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index CREDO FastTrack assets.")
    parser.add_argument("--asset-root", type=Path, default=ASSET_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.asset_root.mkdir(parents=True, exist_ok=True)
    entries = [entry_index(entry) for entry in build_entries(args.asset_root)]
    index = {
        "asset_root": rel(args.asset_root),
        "entries": entries,
    }
    index_path = args.asset_root / "INDEX.generated.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote FastTrack asset index: {index_path}")
    for entry in entries:
        status = "ok" if entry["exists"] else "missing"
        print(f"{status}: {entry['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
