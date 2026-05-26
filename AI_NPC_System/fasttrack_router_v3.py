"""Async FastTrack router with prefetch bypass and separated dataset-pool lookup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import random
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from . import config
    from .fast_track_audio_cache import normalize_response_act
    from .intent_transition_matrix import DISALLOWED_RESPONSE_INTENTS, IntentTransitionPlanner
except ImportError:
    import config  # type: ignore
    from fast_track_audio_cache import normalize_response_act  # type: ignore
    from intent_transition_matrix import DISALLOWED_RESPONSE_INTENTS, IntentTransitionPlanner  # type: ignore


INTENT_MODEL_DIR = ROOT / "fasttrack_assets" / "models" / "setfit_swda_intent_minilm_optimized"
VECTOR_DIM = 384


@dataclass(frozen=True)
class ClassifierResult:
    label: str
    confidence: float
    scores: dict[str, float]
    latency_ms: float


class SeparatedDatasetPoolStore:
    """Search GoEmotions and SWDA as separate filtered source pools."""

    FALLBACK_GO = {
        "POSITIVE": [{"id": "fallback_go_positive", "text": "That sounds good.", "label": "POSITIVE"}],
        "NEGATIVE": [{"id": "fallback_go_negative", "text": "That sounds difficult.", "label": "NEGATIVE"}],
        "SURPRISE": [{"id": "fallback_go_surprise", "text": "That is unexpected.", "label": "SURPRISE"}],
        "NEUTRAL": [{"id": "fallback_go_neutral", "text": "That part is noted.", "label": "NEUTRAL"}],
    }
    FALLBACK_SWDA = {
        "INFORM": [{"id": "fallback_swda_inform", "text": "That makes sense.", "label": "INFORM"}],
        "ACKNOWLEDGE": [{"id": "fallback_swda_acknowledge", "text": "All right.", "label": "ACKNOWLEDGE"}],
        "DIRECTIVE": [{"id": "fallback_swda_directive", "text": "Let's keep going.", "label": "DIRECTIVE"}],
        "EXPRESSIVE": [{"id": "fallback_swda_expressive", "text": "That sounds good.", "label": "EXPRESSIVE"}],
        "REJECT": [{"id": "fallback_swda_reject", "text": "That is not quite right.", "label": "REJECT"}],
    }

    def __init__(self, pool_path: Path) -> None:
        self.pool_path = pool_path
        if pool_path.exists():
            self.payload = json.loads(pool_path.read_text(encoding="utf-8"))
            self.go_buckets = {
                str(label).upper(): list(items)
                for label, items in (self.payload.get("go_emotions", {}).get("buckets", {}) or {}).items()
            }
            self.swda_buckets = {
                str(label).upper(): list(items)
                for label, items in (self.payload.get("swda", {}).get("buckets", {}) or {}).items()
            }
        else:
            self.payload = {"version": "fallback-separated-dataset-pool"}
            self.go_buckets = {key: list(value) for key, value in self.FALLBACK_GO.items()}
            self.swda_buckets = {key: list(value) for key, value in self.FALLBACK_SWDA.items()}
        self._vectors: dict[tuple[str, str], np.ndarray] = {}
        self._faiss_indices: dict[tuple[str, str], tuple[Any, list[dict[str, Any]]]] = {}
        self.faiss_available = False
        self._build_indices()

    @staticmethod
    def _item_text(item: dict[str, Any]) -> str:
        return str(item.get("text") or "")

    @staticmethod
    def _hash_token(token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "little")

    def _embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), VECTOR_DIM), dtype="float32")
        for row, text in enumerate(texts):
            tokens = re.findall(r"[A-Za-z0-9']+", str(text).lower())
            for token in tokens:
                hashed = self._hash_token(token)
                column = hashed % VECTOR_DIM
                sign = 1.0 if (hashed >> 8) & 1 else -1.0
                matrix[row, column] += sign
            norm = float(np.linalg.norm(matrix[row]))
            if norm:
                matrix[row] /= norm
        return matrix

    def _build_indices(self) -> None:
        try:
            import faiss
        except Exception:
            faiss = None
        for source_name, buckets in (("go_emotions", self.go_buckets), ("swda", self.swda_buckets)):
            for label, items in buckets.items():
                vectors = self._embed([self._item_text(item) for item in items])
                self._vectors[(source_name, label)] = vectors
                if faiss is not None and len(items):
                    index = faiss.IndexFlatIP(vectors.shape[1])
                    index.add(vectors)
                    self._faiss_indices[(source_name, label)] = (index, items)
                    self.faiss_available = True

    def _search_bucket(self, source_name: str, label: str, query: str, top_k: int) -> list[tuple[dict[str, Any], float]]:
        buckets = self.go_buckets if source_name == "go_emotions" else self.swda_buckets
        label_key = str(label or "").upper()
        items = buckets.get(label_key) or buckets.get("NEUTRAL") or buckets.get("ACKNOWLEDGE") or []
        if not items:
            return []
        query_vector = self._embed([query])
        if (source_name, label_key) in self._faiss_indices:
            index, indexed_items = self._faiss_indices[(source_name, label_key)]
            scores, indices = index.search(query_vector, min(len(indexed_items), max(1, top_k)))
            return [
                (indexed_items[int(index)], float(score))
                for score, index in zip(scores[0], indices[0])
                if int(index) >= 0
            ]
        vectors = self._vectors.get((source_name, label_key))
        if vectors is None or not len(vectors):
            vectors = self._embed([self._item_text(item) for item in items])
        raw_scores = np.matmul(vectors, query_vector[0])
        ranked = np.argsort(-raw_scores)[: max(1, top_k)]
        return [(items[int(index)], float(raw_scores[int(index)])) for index in ranked]

    @staticmethod
    def _emotion_key(emotion: str) -> str:
        emotion_key = str(emotion or "Neutral").upper()
        return "SURPRISE" if emotion_key == "AMBIGUOUS" else emotion_key

    @staticmethod
    def _fallback_core(response_act: str) -> str:
        return {
            "INFORM": "that part makes sense",
            "ACKNOWLEDGE": "that part is noted",
            "DIRECTIVE": "we can keep it moving",
            "EXPRESSIVE": "that feeling is logged",
            "REJECT": "that route needs a tiny correction",
        }.get(normalize_response_act(response_act), "that part is noted")

    def _clean_core(self, text: str, response_act: str) -> str:
        core = re.sub(r"[^A-Za-z0-9',.! ]+", " ", str(text or ""))
        core = re.sub(r"\s+", " ", core).strip(" ,.!?")
        lowered = core.lower()
        if not core or len(core.split()) < 2 or len(core) > 88:
            return self._fallback_core(response_act)
        if lowered.startswith(("oh,", "is ", "are ", "do ", "does ", "did ", "can ", "could ", "would ", "will ", "what ", "why ", "how ")):
            return self._fallback_core(response_act)
        if re.search(r"(?i)\b(?:you|your|twine|where|call|personnel|television|fishing|golf|stereo)\b", core):
            return self._fallback_core(response_act)
        response_key = normalize_response_act(response_act)
        safe_patterns = {
            "INFORM": r"(?i)\b(?:makes sense|possible|probably|helps|factor|not always|true|impressed|ambivalent|whole thing)\b",
            "ACKNOWLEDGE": r"(?i)\b(?:okay|right|sure|yeah|yes|all right|got it|noted)\b",
            "DIRECTIVE": r"(?i)\b(?:go ahead|keep going|try|let's|we can|handle|start)\b",
            "EXPRESSIVE": r"(?i)\b(?:sounds good|enjoyed|sorry|interesting|thank|nice|good luck|take care)\b",
            "REJECT": r"(?i)\b(?:not true|not right|don't think|not sure|not always|cannot|can't|no)\b",
        }
        if not re.search(safe_patterns.get(response_key, r"(?i)\b(?:that|this|it)\b"), core):
            return self._fallback_core(response_key)
        return core[0].lower() + core[1:] if core and core[0].isupper() else core

    def _compose_text(
        self,
        *,
        emotion: str,
        response_act: str,
        go_item: dict[str, Any] | None,
        swda_item: dict[str, Any] | None,
        rank: int,
        selection_policy: str,
    ) -> str:
        emotion_key = self._emotion_key(emotion)
        response_key = normalize_response_act(response_act)
        if selection_policy == "emotion_only":
            core = self._clean_core(str((go_item or {}).get("text") or ""), "ACKNOWLEDGE")
        else:
            core = self._clean_core(str((swda_item or {}).get("text") or ""), response_key)

        if selection_policy == "response_act_only":
            emotion_key = "NEUTRAL"

        templates = {
            "INFORM": [
                "Tiny lab-maid report: {core}. The clipboard logged it beside the coffee.",
                "Observation saved: {core}. Beep, the lab notebook is awake.",
                "Lab note: {core}. The paper stack can stop arguing for one second.",
            ],
            "ACKNOWLEDGE": [
                "Ack, understood. {core}. Ding, the lab maid placed it beside the coffee.",
                "Mm, noted. {core}. The tiny clipboard accepts this entry.",
                "Got it. {core}. Today's peace remains mostly intact.",
            ],
            "DIRECTIVE": [
                "Let's handle it softly: {core}. Then the lab maid can stamp it done.",
                "First coffee, then {core}. Beep, practical route selected.",
                "Tiny order from the lab maid: {core}. One step before the deadline bell.",
            ],
            "EXPRESSIVE": [
                "Beep, mood detected: {core}. The lab beaker blinked first.",
                "Tiny reaction logged: {core}. Even the coffee paused.",
                "The lab maid has feelings about this: {core}. The final file pile noticed.",
            ],
            "REJECT": [
                "Rejected softly: {core}. It smells like a fake final file.",
                "Mm-mm, {core}. That route will not pass today's lab inspection.",
                "Not that route: {core}. The paper files would start arguing again.",
            ],
        }
        if emotion_key == "NEGATIVE" and response_key == "EXPRESSIVE":
            choices = [
                f"Ack, {core}. Today's peace just got called into Professor's office.",
                f"Small trouble logged: {core}. The coffee cup has entered emergency mode.",
                f"Oh no, {core}. The lab notebook is quietly trembling.",
            ]
            return choices[(max(rank, 1) - 1) % len(choices)]
        if emotion_key == "SURPRISE" and response_key == "EXPRESSIVE":
            choices = [
                f"Ding, unexpected result: {core}. Even the coffee paused.",
                f"Ack, surprise logged: {core}. The beaker blinked first.",
                f"Tiny lab shock detected: {core}. The clipboard stood up straight.",
            ]
            return choices[(max(rank, 1) - 1) % len(choices)]
        if emotion_key == "POSITIVE" and response_key == "EXPRESSIVE":
            choices = [
                f"Tiny celebration logged: {core}. The lab maid is almost sparkling.",
                f"Beep, happy result saved: {core}. The coffee machine approves.",
                f"Small lab victory: {core}. The final file pile behaved for once.",
            ]
            return choices[(max(rank, 1) - 1) % len(choices)]
        choices = templates.get(response_key, templates["ACKNOWLEDGE"])
        return choices[(max(rank, 1) - 1) % len(choices)].format(core=core).replace("..", ".")

    def search(
        self,
        query: str,
        *,
        emotion: str,
        response_act: str,
        top_k: int = 3,
        selection_policy: str = "grounded",
    ) -> list[dict[str, Any]]:
        emotion_key = self._emotion_key(emotion)
        response_key = normalize_response_act(response_act)
        policy = str(selection_policy or "grounded").lower()
        use_go = policy in {"grounded", "emotion_only", "neutral_random"}
        use_swda = policy in {"grounded", "response_act_only", "neutral_random"}
        go_hits = self._search_bucket("go_emotions", emotion_key if policy != "neutral_random" else "NEUTRAL", query, top_k) if use_go else []
        swda_hits = self._search_bucket("swda", response_key if policy != "neutral_random" else "ACKNOWLEDGE", query, top_k) if use_swda else []
        if not go_hits:
            go_hits = [(self.FALLBACK_GO.get(emotion_key, self.FALLBACK_GO["NEUTRAL"])[0], 0.0)]
        if not swda_hits:
            swda_hits = [(self.FALLBACK_SWDA.get(response_key, self.FALLBACK_SWDA["ACKNOWLEDGE"])[0], 0.0)]

        results: list[dict[str, Any]] = []
        for rank in range(max(1, int(top_k))):
            go_item, go_score = go_hits[rank % len(go_hits)]
            swda_item, swda_score = swda_hits[rank % len(swda_hits)]
            score_parts = ([go_score] if use_go else []) + ([swda_score] if use_swda else [])
            score = sum(score_parts) / len(score_parts) if score_parts else 0.0
            text = self._compose_text(
                emotion=emotion_key,
                response_act=response_key,
                go_item=go_item if use_go else None,
                swda_item=swda_item if use_swda else None,
                rank=rank + 1,
                selection_policy=policy,
            )
            results.append(
                {
                    "item_id": f"runtime_{go_item.get('id', 'no_go')}__{swda_item.get('id', 'no_swda')}",
                    "cell_id": f"{emotion_key.lower()}_{response_key.lower()}",
                    "text": text,
                    "emotion": emotion_key.title(),
                    "response_act": response_key,
                    "score": score,
                    "index": rank,
                    "source": "separated_dataset_pool_runtime",
                    "selection_policy": policy,
                    "go_emotions_item": go_item if use_go else None,
                    "swda_item": swda_item if use_swda else None,
                }
            )
        return results


class RouterV3Runtime:
    """Owns lazy model/index state for analyze_and_route_chat_v3."""

    def __init__(self) -> None:
        self.threshold = float(getattr(config, "FASTTRACK_ROUTER_V3_CONFIDENCE_THRESHOLD", 0.6))
        self.top_k = int(getattr(config, "FASTTRACK_ROUTER_V3_TOP_K", 3))
        self.rng = random.Random(20260526)
        self.intent_model = None
        self.intent_labels: dict[int, str] = {}
        self.intent_checked = False
        self.intent_loading_started = False
        self.emotion_pipeline = None
        self.emotion_checked = False
        self.transition = IntentTransitionPlanner()
        pool_path = getattr(config, "FAST_TRACK_DATASET_POOL_PATH", getattr(config, "FAST_TRACK_PERSONA_BUNDLE_PATH"))
        self.store = SeparatedDatasetPoolStore(pool_path)

    def _load_emotion_pipeline(self) -> None:
        if self.emotion_checked:
            return
        self.emotion_checked = True
        model_name = str(getattr(config, "EMOTION_MODEL_NAME", ""))
        if not model_name or not Path(model_name).expanduser().exists():
            return
        try:
            previous_offline = os.environ.get("TRANSFORMERS_OFFLINE")
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(model_name, local_files_only=True)
            self.emotion_pipeline = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                top_k=None,
                device=-1,
            )
        except Exception:
            self.emotion_pipeline = None
        finally:
            if previous_offline is None:
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
            else:
                os.environ["TRANSFORMERS_OFFLINE"] = previous_offline

    @staticmethod
    def _bucket_emotion_label(label: str) -> str:
        label = str(label or "").lower()
        if label in {"joy", "love", "admiration", "approval", "amusement", "optimism", "gratitude", "caring", "relief", "pride"}:
            return "POSITIVE"
        if label in {"anger", "annoyance", "disapproval", "disgust", "fear", "grief", "nervousness", "remorse", "sadness", "embarrassment"}:
            return "NEGATIVE"
        if label in {"surprise", "confusion", "curiosity", "realization"}:
            return "SURPRISE"
        return "NEUTRAL"

    def infer_emotion(self, text: str) -> ClassifierResult:
        started = time.perf_counter()
        self._load_emotion_pipeline()
        scores = self._rule_emotion_scores(text)
        if self.emotion_pipeline is not None:
            try:
                raw = self.emotion_pipeline(text)
                rows = raw[0] if raw and isinstance(raw[0], list) else raw
                bucket_scores = {"POSITIVE": 0.0, "NEGATIVE": 0.0, "SURPRISE": 0.0, "NEUTRAL": 0.0}
                for row in rows:
                    bucket = self._bucket_emotion_label(str(row.get("label") or "neutral"))
                    bucket_scores[bucket] += float(row.get("score") or 0.0)
                total = sum(max(value, 0.0) for value in bucket_scores.values()) or 1.0
                scores = {key: value / total for key, value in bucket_scores.items()}
            except Exception:
                pass
        label, confidence = max(scores.items(), key=lambda item: item[1])
        return ClassifierResult(label, confidence, scores, (time.perf_counter() - started) * 1000.0)

    @staticmethod
    def _rule_emotion_scores(text: str) -> dict[str, float]:
        normalized = str(text or "").lower()
        if any(token in normalized for token in ("wow", "what", "really", "omg", "no way", "surprise")):
            return {"POSITIVE": 0.05, "NEGATIVE": 0.05, "SURPRISE": 0.75, "NEUTRAL": 0.15}
        if any(token in normalized for token in ("great", "amazing", "love", "awesome", "fun", "happy", "nice")):
            return {"POSITIVE": 0.75, "NEGATIVE": 0.05, "SURPRISE": 0.1, "NEUTRAL": 0.1}
        if any(token in normalized for token in ("bad", "sad", "angry", "hate", "wrong", "tired", "ugh")):
            return {"POSITIVE": 0.05, "NEGATIVE": 0.75, "SURPRISE": 0.05, "NEUTRAL": 0.15}
        return {"POSITIVE": 0.1, "NEGATIVE": 0.1, "SURPRISE": 0.1, "NEUTRAL": 0.7}

    def _load_intent_model(self) -> None:
        if self.intent_checked:
            return
        self.intent_checked = True
        if not INTENT_MODEL_DIR.exists():
            return
        try:
            previous_offline = os.environ.get("TRANSFORMERS_OFFLINE")
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            from setfit import SetFitModel

            self.intent_model = SetFitModel.from_pretrained(str(INTENT_MODEL_DIR), local_files_only=True)
            metadata_path = INTENT_MODEL_DIR / "fasttrack_setfit_metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.intent_labels = {int(key): value for key, value in metadata.get("id_to_label", {}).items()}
        except Exception:
            self.intent_model = None
        finally:
            if previous_offline is None:
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
            else:
                os.environ["TRANSFORMERS_OFFLINE"] = previous_offline

    def ensure_intent_model_loading(self) -> None:
        if self.intent_checked or self.intent_loading_started:
            return
        if not bool(getattr(config, "FASTTRACK_ROUTER_V3_BACKGROUND_LOAD_SETFIT", False)):
            return
        self.intent_loading_started = True
        threading.Thread(target=self._load_intent_model, name="fasttrack-setfit-loader", daemon=True).start()

    def infer_intent(self, text: str) -> ClassifierResult:
        started = time.perf_counter()
        if self.intent_model is not None:
            try:
                raw_label = self.intent_model.predict([text])[0]
                try:
                    label = self.intent_labels.get(int(raw_label), str(raw_label)).upper()
                except Exception:
                    label = str(raw_label).upper()
                scores: dict[str, float] = {}
                try:
                    probabilities = self.intent_model.predict_proba([text])[0]
                    for index, score in enumerate(probabilities):
                        scores[self.intent_labels.get(index, str(index)).upper()] = float(score)
                    confidence = float(scores.get(label, max(scores.values()) if scores else 0.0))
                except Exception:
                    scores = {label: 1.0}
                    confidence = 1.0
                return ClassifierResult(label, confidence, scores, (time.perf_counter() - started) * 1000.0)
            except Exception:
                pass
        label = self._rule_intent(text)
        return ClassifierResult(label, 0.61, {label: 0.61}, (time.perf_counter() - started) * 1000.0)

    @staticmethod
    def _rule_intent(text: str) -> str:
        normalized = " ".join(str(text or "").lower().split())
        first = normalized.split(" ", 1)[0] if normalized else ""
        if (
            normalized.startswith(("no ", "no,", "nah ", "nah,", "never ", "don't ", "do not "))
            or " disagree" in normalized
            or " do not agree" in normalized
            or " don't agree" in normalized
            or normalized in {"no", "nope", "nah"}
        ):
            return "REJECT"
        if normalized in {"yes", "yeah", "yep", "ok", "okay", "sure", "right"}:
            return "ACKNOWLEDGE"
        if normalized.startswith(("please ", "show ", "tell ", "look ", "read ", "play ", "stop ", "try ")):
            return "DIRECTIVE"
        if normalized.endswith("?") or first in {"who", "what", "when", "where", "why", "how", "can", "could", "do", "does", "did", "is", "are"}:
            return "QUESTION"
        if any(token in normalized for token in ("lol", "haha", "wow", "omg", "awesome", "sad", "angry", "love")):
            return "EXPRESSIVE"
        return "INFORM"

    async def route(self, text: str, prefetch_queue: Any = None) -> dict[str, Any] | None:
        bypass = _ready_prefetch(prefetch_queue)
        if bypass is not None:
            return {"bypass": True, "prefetched": bypass}
        cleaned = " ".join(str(text or "").split()).strip()
        if not cleaned:
            return None
        self.ensure_intent_model_loading()
        emotion_task = asyncio.to_thread(self.infer_emotion, cleaned)
        intent_task = asyncio.to_thread(self.infer_intent, cleaned)
        emotion, intent = await asyncio.gather(emotion_task, intent_task)
        if emotion.confidence < self.threshold or intent.confidence < self.threshold:
            return None
        transition = self.transition.choose(intent.label, emotion=emotion.label.lower(), rng=self.rng)
        query = f"{emotion.label} {transition.response_intent} {cleaned}"
        selection_policy = str(getattr(config, "CREDO_FASTTRACK_SELECTION_POLICY", "grounded")).lower()
        top3 = self.store.search(
            query,
            emotion=emotion.label,
            response_act=transition.response_intent,
            top_k=self.top_k,
            selection_policy=selection_policy,
        )
        return {
            "bypass": False,
            "text": cleaned,
            "emotion": {
                "label": emotion.label,
                "confidence": round(emotion.confidence, 6),
                "scores": {key: round(value, 6) for key, value in emotion.scores.items()},
                "latency_ms": round(emotion.latency_ms, 3),
            },
            "intent": {
                "label": intent.label,
                "confidence": round(intent.confidence, 6),
                "scores": {key: round(value, 6) for key, value in intent.scores.items()},
                "latency_ms": round(intent.latency_ms, 3),
            },
            "response_act": transition.response_intent,
            "route_query": query,
            "faiss_available": self.store.faiss_available,
            "dataset_pool_path": str(self.store.pool_path),
            "selection_policy": selection_policy,
            "top3_reactions": top3,
        }


def _ready_prefetch(prefetch_queue: Any) -> Any | None:
    if prefetch_queue is None:
        return None
    if hasattr(prefetch_queue, "done") and callable(prefetch_queue.done):
        if prefetch_queue.done():
            try:
                return prefetch_queue.result()
            except Exception:
                return None
        return None
    if hasattr(prefetch_queue, "empty") and hasattr(prefetch_queue, "get_nowait"):
        try:
            if not prefetch_queue.empty():
                return prefetch_queue.get_nowait()
        except Exception:
            return None
    if isinstance(prefetch_queue, list) and prefetch_queue:
        return prefetch_queue.pop(0)
    return None


_RUNTIME: RouterV3Runtime | None = None


def _get_runtime() -> RouterV3Runtime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = RouterV3Runtime()
    return _RUNTIME


async def analyze_and_route_chat_v3(text: str, prefetch_queue: Any = None) -> dict[str, Any] | None:
    """Bypass on ready SlowTrack; otherwise parallel-classify and FAISS-route."""
    return await _get_runtime().route(text, prefetch_queue)
