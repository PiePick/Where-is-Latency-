"""Non-parametric latency prediction from observed CREDO latency logs."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_PATH = ROOT / "latency_logs" / "events.jsonl"
DEFAULT_MODEL_PATH = ROOT / os.getenv("LATENCY_PREDICTOR_MODEL_FILE", "reports/latency_prediction_model.json")
FEATURE_SCHEMA = [
    "char_len_200",
    "word_count_40",
    "tag_count_8",
    "punct_count_10",
    "sentence_count_6",
    "avg_word_len_12",
    "engine_fish_speech",
    "engine_stylebert_vits2",
    "engine_open_llm_tts",
    "engine_default",
    "stage_slow_tts",
    "stage_fast_tts",
    "stage_nonverbal_tts",
    "stage_length_sweep_tts",
    "stage_other_tts",
]


@dataclass(frozen=True)
class LatencyPrediction:
    """Predicted latency for a future TTS request."""

    predicted_ms: float
    neighbors: int
    method: str
    fallback: bool = False
    source: str = ""
    engine_key: str = ""
    stage_key: str = ""
    neighbor_ms: list[float] = field(default_factory=list)


class LatencyPredictor:
    """Predict TTS latency with kNN/FAISS over measured examples.

    This is an instance-based estimator: completed synthesis calls are stored as
    points, and future text is compared against nearby points using numeric text,
    engine, and stage features. If local logs are unavailable, the committed
    latency artifact supplies the kNN records so teammates still get real kNN
    behavior after cloning the repo.
    """

    feature_schema = FEATURE_SCHEMA

    def __init__(
        self,
        log_path: Path = DEFAULT_LOG_PATH,
        *,
        stage: str = "tts",
        model_path: Path = DEFAULT_MODEL_PATH,
    ) -> None:
        self.log_path = log_path
        self.model_path = model_path
        self.stage = stage
        self.artifact = self._load_artifact()
        live_records = self._load_live_records()
        artifact_records = self._load_artifact_records()
        self.records = live_records or artifact_records
        self.record_source = "live_log" if live_records else ("artifact" if artifact_records else "fallback")

    def predict(self, text: str, *, engine: str = "", stage: str = "tts", k: int = 5) -> LatencyPrediction:
        """Predict milliseconds for a text/engine/stage tuple."""
        engine_key = self.engine_key(engine)
        stage_key = self.stage_key(stage)
        candidates = self._candidate_records(engine_key=engine_key, stage_key=stage_key, min_count=max(1, k))
        if not candidates:
            return LatencyPrediction(
                predicted_ms=self._fallback_ms(text, engine=engine),
                neighbors=0,
                method="artifact_fallback",
                fallback=True,
                source=self.record_source,
                engine_key=engine_key,
                stage_key=stage_key,
            )

        features, targets = self._build_arrays(candidates)
        if len(targets) == 0:
            return LatencyPrediction(
                predicted_ms=self._fallback_ms(text, engine=engine),
                neighbors=0,
                method="artifact_fallback",
                fallback=True,
                source=self.record_source,
                engine_key=engine_key,
                stage_key=stage_key,
            )

        vector = self.features_for_text(text, engine=engine_key, stage=stage_key)
        k = max(1, min(k, len(targets)))
        faiss_index = self._build_faiss_index(features)
        if faiss_index is not None:
            distances, indices = faiss_index.search(np.array([vector], dtype="float32"), k)
            weights = self._distance_weights(distances[0])
            values = targets[indices[0]]
            return LatencyPrediction(
                predicted_ms=float(np.average(values, weights=weights)),
                neighbors=k,
                method=f"faiss_knn_{self.record_source}",
                source=self.record_source,
                engine_key=engine_key,
                stage_key=stage_key,
                neighbor_ms=[round(float(value), 3) for value in values.tolist()],
            )

        distances = np.linalg.norm(features - vector, axis=1)
        order = np.argsort(distances)[:k]
        weights = self._distance_weights(distances[order])
        values = targets[order]
        return LatencyPrediction(
            predicted_ms=float(np.average(values, weights=weights)),
            neighbors=k,
            method=f"numpy_knn_{self.record_source}",
            source=self.record_source,
            engine_key=engine_key,
            stage_key=stage_key,
            neighbor_ms=[round(float(value), 3) for value in values.tolist()],
        )

    @classmethod
    def features_for_text(cls, text: str, *, engine: str = "", stage: str = "tts") -> np.ndarray:
        """Map text into latency-oriented numeric features."""
        text = str(text or "")
        words = text.split()
        word_lengths = [len(word) for word in words]
        engine_key = cls.engine_key(engine)
        stage_key = cls.stage_key(stage)
        punct_count = sum(1 for ch in text if ch in ".!?")
        sentence_count = max(1, punct_count) if text.strip() else 0
        avg_word_len = (sum(word_lengths) / len(word_lengths)) if word_lengths else 0.0
        return np.array(
            [
                len(text) / 200.0,
                len(words) / 40.0,
                text.count("[") / 8.0,
                punct_count / 10.0,
                sentence_count / 6.0,
                avg_word_len / 12.0,
                1.0 if engine_key == "fish_speech" else 0.0,
                1.0 if engine_key == "stylebert_vits2" else 0.0,
                1.0 if engine_key == "open_llm_tts" else 0.0,
                1.0 if engine_key == "default" else 0.0,
                1.0 if stage_key == "slow_tts" else 0.0,
                1.0 if stage_key == "fast_tts" else 0.0,
                1.0 if stage_key == "nonverbal_tts" else 0.0,
                1.0 if stage_key == "length_sweep_tts" else 0.0,
                1.0 if stage_key == "other_tts" else 0.0,
            ],
            dtype="float32",
        )

    @classmethod
    def engine_key(cls, engine: str) -> str:
        engine = str(engine or "").lower()
        if "fish" in engine:
            return "fish_speech"
        if "stylebert" in engine or "style-bert" in engine:
            return "stylebert_vits2"
        if "open_llm" in engine or "edge" in engine or "open-llm" in engine:
            return "open_llm_tts"
        return "default"

    @classmethod
    def stage_key(cls, stage: str) -> str:
        stage = str(stage or "").lower()
        if "slow" in stage and "tts" in stage:
            return "slow_tts"
        if "fast" in stage and "tts" in stage:
            return "fast_tts"
        if "nonverbal" in stage or "extreme" in stage:
            return "nonverbal_tts"
        if "length_sweep" in stage or "sweep" in stage:
            return "length_sweep_tts"
        if "tts" in stage:
            return "other_tts"
        return "other_tts"

    def _load_artifact(self) -> dict[str, Any]:
        if not self.model_path.exists():
            return {}
        try:
            return json.loads(self.model_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _load_live_records(self) -> list[dict[str, Any]]:
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
            row["_source"] = "live_log"
            row["engine_key"] = self.engine_key(str(row.get("engine", "")))
            row["stage_key"] = self.stage_key(str(row.get("stage", "")))
            records.append(row)
        return records

    def _load_artifact_records(self) -> list[dict[str, Any]]:
        raw_records = self.artifact.get("knn_records", []) if isinstance(self.artifact, dict) else []
        records = []
        for row in raw_records:
            try:
                elapsed_ms = float(row.get("elapsed_ms") or 0.0)
            except (TypeError, ValueError):
                continue
            if elapsed_ms <= 0:
                continue
            record = dict(row)
            record["elapsed_ms"] = elapsed_ms
            record["_source"] = "artifact"
            record["engine_key"] = self.engine_key(str(row.get("engine_key") or row.get("engine", "")))
            record["stage_key"] = self.stage_key(str(row.get("stage_key") or row.get("stage", "")))
            records.append(record)
        return records

    def _candidate_records(self, *, engine_key: str, stage_key: str, min_count: int) -> list[dict[str, Any]]:
        exact = [row for row in self.records if row.get("engine_key") == engine_key and row.get("stage_key") == stage_key]
        if len(exact) >= min_count:
            return exact
        same_engine = [row for row in self.records if row.get("engine_key") == engine_key]
        if len(same_engine) >= min_count:
            return same_engine
        same_stage = [row for row in self.records if row.get("stage_key") == stage_key]
        if len(same_stage) >= min_count:
            return same_stage
        return self.records

    def _build_arrays(self, records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        features = []
        targets = []
        for row in records:
            stored = row.get("features")
            if isinstance(stored, list) and len(stored) == len(FEATURE_SCHEMA):
                features.append(np.array(stored, dtype="float32"))
            else:
                features.append(
                    self.features_for_text(
                        str(row.get("text", "")),
                        engine=str(row.get("engine_key") or row.get("engine", "")),
                        stage=str(row.get("stage_key") or row.get("stage", "")),
                    )
                )
            targets.append(float(row.get("elapsed_ms", 0.0)))
        if not features:
            return np.zeros((0, len(FEATURE_SCHEMA)), dtype="float32"), np.zeros((0,), dtype="float32")
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
        key = self.engine_key(engine)
        params = by_engine.get(key) or by_engine.get("default") or {}
        intercept = float(params.get("intercept_ms", 3500.0))
        char_ms = float(params.get("char_ms", 65.0))
        tag_ms = float(params.get("tag_ms", 450.0))
        return intercept + len(text) * char_ms + text.count("[") * tag_ms
