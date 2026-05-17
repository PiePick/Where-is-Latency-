"""Non-parametric latency prediction from observed CREDO latency logs."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_PATH = ROOT / "latency_logs" / "events.jsonl"
DEFAULT_MODEL_PATH = ROOT / os.getenv("LATENCY_PREDICTOR_MODEL_FILE", "reports/latency_prediction_model.json")


@dataclass(frozen=True)
class LatencyPrediction:
    """Predicted latency for a future TTS request."""

    predicted_ms: float
    neighbors: int
    method: str
    fallback: bool = False


class LatencyPredictor:
    """Predict TTS latency with kNN/FAISS over measured examples.

    This is not supervised model training. It is an instance-based estimator:
    every completed synthesis is stored as a point, and future text is compared
    with nearby points using simple numeric features.
    """

    def __init__(self, log_path: Path = DEFAULT_LOG_PATH, *, stage: str = "tts", model_path: Path = DEFAULT_MODEL_PATH) -> None:
        self.log_path = log_path
        self.model_path = model_path
        self.stage = stage
        self.artifact = self._load_artifact()
        self.records = self._load_records()
        self.features, self.targets = self._build_arrays(self.records)
        self.faiss_index = self._build_faiss_index(self.features)

    def predict(self, text: str, *, engine: str = "", k: int = 5) -> LatencyPrediction:
        """Predict milliseconds for a text/engine pair."""
        vector = self.features_for_text(text, engine=engine)
        if len(self.targets) == 0:
            return LatencyPrediction(predicted_ms=self._fallback_ms(text, engine=engine), neighbors=0, method="artifact_fallback", fallback=True)

        k = max(1, min(k, len(self.targets)))
        if self.faiss_index is not None:
            distances, indices = self.faiss_index.search(np.array([vector], dtype="float32"), k)
            weights = self._distance_weights(distances[0])
            values = self.targets[indices[0]]
            return LatencyPrediction(
                predicted_ms=float(np.average(values, weights=weights)),
                neighbors=k,
                method="faiss_knn",
            )

        distances = np.linalg.norm(self.features - vector, axis=1)
        order = np.argsort(distances)[:k]
        weights = self._distance_weights(distances[order])
        return LatencyPrediction(
            predicted_ms=float(np.average(self.targets[order], weights=weights)),
            neighbors=k,
            method="numpy_knn",
        )

    def features_for_text(self, text: str, *, engine: str = "") -> np.ndarray:
        """Map text into latency-oriented numeric features."""
        words = text.split()
        engine_bucket = 1.0 if "fish" in engine.lower() else 0.0
        return np.array(
            [
                len(text) / 200.0,
                len(words) / 40.0,
                text.count("[") / 8.0,
                sum(1 for ch in text if ch in ".!?") / 10.0,
                engine_bucket,
            ],
            dtype="float32",
        )

    def _load_artifact(self) -> dict[str, Any]:
        if not self.model_path.exists():
            return {}
        try:
            return json.loads(self.model_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        records = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if self.stage not in str(row.get("stage", "")):
                continue
            if float(row.get("elapsed_ms", 0.0)) <= 0:
                continue
            records.append(row)
        return records

    def _build_arrays(self, records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        features = []
        targets = []
        for row in records:
            features.append(self.features_for_text(str(row.get("text", "")), engine=str(row.get("engine", ""))))
            targets.append(float(row.get("elapsed_ms", 0.0)))
        if not features:
            return np.zeros((0, 5), dtype="float32"), np.zeros((0,), dtype="float32")
        return np.vstack(features).astype("float32"), np.array(targets, dtype="float32")

    def _build_faiss_index(self, features: np.ndarray) -> Any | None:
        if len(features) == 0:
            return None
        try:
            import faiss
        except Exception:
            return None
        index = faiss.IndexFlatL2(features.shape[1])
        index.add(features)
        return index

    def _distance_weights(self, distances: np.ndarray) -> np.ndarray:
        return np.array([1.0 / max(math.sqrt(float(dist)), 1e-4) for dist in distances], dtype="float32")

    def _fallback_ms(self, text: str, *, engine: str = "") -> float:
        by_engine = self.artifact.get("fallback_by_engine", {}) if isinstance(self.artifact, dict) else {}
        key = self._engine_key(engine)
        params = by_engine.get(key) or by_engine.get("default") or {}
        intercept = float(params.get("intercept_ms", 3500.0))
        char_ms = float(params.get("char_ms", 65.0))
        tag_ms = float(params.get("tag_ms", 450.0))
        return intercept + len(text) * char_ms + text.count("[") * tag_ms

    def _engine_key(self, engine: str) -> str:
        engine = str(engine or "").lower()
        if "fish" in engine:
            return "fish_speech"
        if "stylebert" in engine or "style-bert" in engine:
            return "stylebert_vits2"
        return "default"
