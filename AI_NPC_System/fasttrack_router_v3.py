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
BLOCKED_PREBUILT_SURFACE_RE = re.compile(
    r"(?i)(assault|dangerous fantasy|mental illness|mental illnesses|\bowner\b|\bdog\b|\bvideo\b|"
    r"\btrump\b|\bbiden\b|\bkill\b|\bdie\b|\bsuicide\b|\bfuck\b|\bshit\b|\bsex\b|\bporn\b|"
    r"\bhell\b|\bthis guy\b|\bthat guy\b|\bthis man\b|\bthat man\b|\bthis woman\b|\bthat woman\b|"
    r"\blady\b|\bphoto\b|\bpicture\b|\bshow\b|\balbum\b|\bsong\b|\btitle\b|\bface\b|\bspider\b|"
    r"\bteam\b|cake day|anniversary|\bcop\b|\burinal\b|microplastics|\bdayz\b|\bcomic\b|"
    r"\bboyfriend\b|\bwifey\b|\bmother\b|\bdamn\b|\bshoe\b|\bleather\b|\bclown\b|"
    r"\bfurniture\b|polyamory|assholery|\bthigh\b|\bhoodie\b|\bzebra\b|\bliar\b|\bcheater\b|"
    r"\bwitch\b|\bcigarette\b|\bkindergarten\b|\bsoap\b|\bpopulism\b|terrorists|hentaipoon|"
    r"cromulent|calamari|baloney|parvo|foreign money)"
)


@dataclass(frozen=True)
class ClassifierResult:
    label: str
    confidence: float
    scores: dict[str, float]
    latency_ms: float


class PrebuiltFastTrackManifest:
    """Map router-v3 selected text to pre-generated FastTrack wav files."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.root = manifest_path.parent
        self.items: list[dict[str, Any]] = []
        self.by_text: dict[str, list[dict[str, Any]]] = {}
        self.by_cell: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        self.by_emotion: dict[str, list[dict[str, Any]]] = {}
        self.by_response_act: dict[str, list[dict[str, Any]]] = {}
        self.by_source_item_id: dict[str, dict[str, Any]] = {}
        if not manifest_path.exists():
            return
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for raw_item in payload.get("items", []) or []:
            item = dict(raw_item or {})
            raw_text = str(item.get("text") or item.get("plain_text") or "")
            if BLOCKED_PREBUILT_SURFACE_RE.search(raw_text):
                continue
            text_key = self._text_key(raw_text)
            if not text_key:
                continue
            audio_path = Path(str(item.get("audio_path") or ""))
            if audio_path and not audio_path.is_absolute():
                audio_path = (self.root / audio_path).resolve()
            item["resolved_audio_path"] = str(audio_path) if audio_path else ""
            self.items.append(item)
            self.by_text.setdefault(text_key, []).append(item)
            source_item_id = str(item.get("source_item_id") or "")
            if source_item_id:
                self.by_source_item_id[source_item_id] = item
            emotion = str(item.get("emotion") or "").upper()
            response_act = normalize_response_act(str(item.get("response_act") or ""))
            if emotion in {"POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL"}:
                self.by_emotion.setdefault(emotion, []).append(item)
            if response_act in {"INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT"}:
                self.by_response_act.setdefault(response_act, []).append(item)
            cell_key = (
                str(item.get("selection_policy") or "grounded").lower(),
                emotion,
                response_act,
            )
            self.by_cell.setdefault(cell_key, []).append(item)

    @property
    def available(self) -> bool:
        return bool(self.items)

    @staticmethod
    def _text_key(text: str) -> str:
        normalized = re.sub(r"\s+", " ", str(text or "")).strip().lower()
        return normalized

    def _best_item(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        text_key = self._text_key(str(candidate.get("text") or ""))
        matches = list(self.by_text.get(text_key) or [])
        if not matches:
            return None
        emotion = str(candidate.get("emotion") or "").upper()
        response_act = normalize_response_act(str(candidate.get("response_act") or ""))
        policy = str(candidate.get("selection_policy") or "").lower()
        source_dataset = str(candidate.get("source_dataset") or "")
        source_item_id = str(candidate.get("source_item_id") or "")

        def score(item: dict[str, Any]) -> int:
            value = 0
            if source_item_id and str(item.get("source_item_id") or "") == source_item_id:
                value += 16
            if source_dataset and str(item.get("source_dataset") or "") == source_dataset:
                value += 8
            if str(item.get("emotion") or "").upper() == emotion:
                value += 4
            if normalize_response_act(str(item.get("response_act") or "")) == response_act:
                value += 4
            if str(item.get("selection_policy") or "").lower() == policy:
                value += 2
            if Path(str(item.get("resolved_audio_path") or "")).exists():
                value += 1
            return value

        return max(matches, key=score)

    def attach(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Return a candidate enriched with prebuilt audio metadata."""
        enriched = dict(candidate)
        item = self._best_item(enriched)
        if not item:
            enriched.update(
                {
                    "audio_path": None,
                    "selected_audio_path": None,
                    "prebuilt_hit": False,
                    "cache_hit": False,
                    "prebuilt_manifest_path": str(self.manifest_path),
                    "prebuilt_miss_reason": "text_not_in_manifest" if self.manifest_path.exists() else "manifest_missing",
                }
            )
            return enriched
        audio_path = Path(str(item.get("resolved_audio_path") or ""))
        audio_exists = bool(audio_path and audio_path.exists())
        enriched.update(
            {
                "audio_path": str(audio_path) if audio_exists else None,
                "selected_audio_path": str(audio_path) if audio_exists else None,
                "duration_ms": item.get("duration_ms"),
                "tts_engine": item.get("tts_engine") or "stylebert_vits2",
                "voice_model": item.get("voice_model") or "",
                "prebuilt_manifest_item_id": item.get("id"),
                "prebuilt_manifest_path": str(self.manifest_path),
                "prebuilt_hit": audio_exists,
                "cache_hit": audio_exists,
                "prebuilt_miss_reason": "" if audio_exists else "audio_file_missing",
            }
        )
        return enriched

    def attach_sequence(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Attach wav metadata to each already-selected source text segment."""
        enriched = dict(candidate)
        raw_segments = list(enriched.get("segments") or [])
        if not raw_segments:
            return self.attach(enriched)
        audio_sequence: list[dict[str, Any]] = []
        miss_reasons: list[str] = []
        for raw_segment in raw_segments:
            segment = self.attach(dict(raw_segment or {}))
            audio_sequence.append(segment)
            if not segment.get("prebuilt_hit"):
                miss_reasons.append(str(segment.get("prebuilt_miss_reason") or "audio_missing"))
        audio_paths = [str(item.get("audio_path") or "") for item in audio_sequence if item.get("audio_path")]
        all_audio_ready = len(audio_paths) == len(audio_sequence) and not miss_reasons
        enriched.update(
            {
                "segments": audio_sequence,
                "audio_sequence": audio_sequence,
                "audio_path": audio_paths[0] if audio_paths else None,
                "selected_audio_path": audio_paths[0] if audio_paths else None,
                "selected_audio_paths": audio_paths,
                "duration_ms": sum(int(item.get("duration_ms") or 0) for item in audio_sequence),
                "tts_engine": "stylebert_vits2",
                "prebuilt_manifest_path": str(self.manifest_path),
                "prebuilt_hit": all_audio_ready,
                "cache_hit": all_audio_ready,
                "prebuilt_miss_reason": ";".join(reason for reason in miss_reasons if reason),
            }
        )
        return enriched

    def candidates(
        self,
        *,
        emotion: str,
        response_act: str,
        selection_policy: str,
        top_k: int,
        rng: random.Random | None = None,
    ) -> list[dict[str, Any]]:
        """Return audio-backed candidates from the matching manifest cell."""
        policy = str(selection_policy or "grounded").lower()
        emotion_key = str(emotion or "NEUTRAL").upper()
        response_key = normalize_response_act(response_act)
        if policy == "emotion_only":
            items = list(self.by_emotion.get(emotion_key) or [])
        elif policy in {"grounded", "response_act_only"}:
            items = list(self.by_response_act.get(response_key) or [])
        elif policy == "neutral_random":
            items = list(self.by_emotion.get("NEUTRAL") or self.by_response_act.get("ACKNOWLEDGE") or [])
        else:
            items = list(self.by_response_act.get(response_key) or self.by_emotion.get(emotion_key) or [])
        if not items:
            return []
        if rng is None:
            random.shuffle(items)
        else:
            rng.shuffle(items)
        results: list[dict[str, Any]] = []
        for index, item in enumerate(items[: max(1, int(top_k))], start=1):
            audio_path = Path(str(item.get("resolved_audio_path") or ""))
            audio_exists = bool(audio_path and audio_path.exists())
            text = str(item.get("text") or item.get("plain_text") or "").strip()
            results.append(
                {
                    "item_id": str(item.get("id") or f"prebuilt_{index}"),
                    "cell_id": f"{policy}_{emotion_key.lower()}_{response_key.lower()}",
                    "text": text,
                    "emotion": emotion_key.title(),
                    "response_act": response_key,
                    "score": 1.0,
                    "index": index - 1,
                    "source": "prebuilt_stylebert_manifest",
                    "selection_policy": policy,
                    "composition_sources": [str(item.get("source_dataset") or "")],
                    "go_emotions_item": None,
                    "swda_item": None,
                    "source_dataset": item.get("source_dataset"),
                    "source_item_id": item.get("source_item_id"),
                    "source_label": item.get("source_label"),
                    "audio_path": str(audio_path) if audio_exists else None,
                    "selected_audio_path": str(audio_path) if audio_exists else None,
                    "duration_ms": item.get("duration_ms"),
                    "tts_engine": item.get("tts_engine") or "stylebert_vits2",
                    "voice_model": item.get("voice_model") or "",
                    "prebuilt_manifest_item_id": item.get("id"),
                    "prebuilt_manifest_path": str(self.manifest_path),
                    "prebuilt_hit": audio_exists,
                    "cache_hit": audio_exists,
                    "prebuilt_miss_reason": "" if audio_exists else "audio_file_missing",
                }
            )
        return results


class SeparatedDatasetPoolStore:
    """Search GoEmotions and SWDA as separate filtered source pools."""


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
            self.payload = {"version": "missing-separated-dataset-pool"}
            self.go_buckets = {}
            self.swda_buckets = {}
        self._vectors: dict[tuple[str, str], np.ndarray] = {}
        self._faiss_indices: dict[tuple[str, str], tuple[Any, list[dict[str, Any]]]] = {}
        self._recent_text_keys: list[str] = []
        self._recent_text_window = max(32, int(getattr(config, "FASTTRACK_ROUTER_V3_RECENT_TEXT_WINDOW", 2048)))
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
        if not bool(getattr(config, "FASTTRACK_ROUTER_V3_USE_FAISS", False)):
            faiss = None
        else:
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
        items = buckets.get(label_key) or []
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

    def _random_bucket(self, source_name: str, label: str, rng: random.Random | None) -> list[tuple[dict[str, Any], float]]:
        buckets = self.go_buckets if source_name == "go_emotions" else self.swda_buckets
        label_key = str(label or "").upper()
        items = list(buckets.get(label_key) or [])
        if rng is None:
            random.shuffle(items)
        else:
            rng.shuffle(items)
        return [(item, 0.0) for item in items]

    @staticmethod
    def _emotion_key(emotion: str) -> str:
        emotion_key = str(emotion or "Neutral").upper()
        return "SURPRISE" if emotion_key == "AMBIGUOUS" else emotion_key

    @staticmethod
    def _topic_hint(query: str) -> str:
        stopwords = {
            "positive", "negative", "surprise", "neutral", "inform", "acknowledge", "directive", "expressive", "reject",
            "the", "and", "that", "this", "with", "from", "about", "what", "should", "would", "could", "there",
            "chat", "panic", "panicking", "today", "next", "said", "says", "look", "looks", "want", "wants", "really",
            "turn", "part", "idle", "stream", "segment", "message", "current", "conversation",
        }
        words: list[str] = []
        for token in re.findall(r"[A-Za-z][A-Za-z']+", str(query or "").lower()):
            if len(token) < 4 or token in stopwords or token in words:
                continue
            words.append(token)
            if len(words) >= 2:
                break
        return " ".join(words)

    def _clean_core(self, text: str, response_act: str, rank: int = 0, topic: str = "") -> str:
        core = re.sub(r"[^A-Za-z0-9',.! ]+", " ", str(text or ""))
        core = re.sub(r"(?i)\b(?:ha[\s-]*){2,}ha?\b|\b(?:ahaha+|hee[\s-]*hee+|hehe+|lol|lmao|rofl)\b", " ", core)
        core = core.strip(" ,.!?")
        prefix_noise = r"(?i)^\s*(?:ah+|eh+|oh+|w+|th|well|okay|ok|alright|anyway|so|um+|uh+|hmm+|mmm+|ack|got it|understood|i think|let me think)\b[,.!?\s-]*"
        for _ in range(4):
            stripped_core = re.sub(prefix_noise, "", core)
            if stripped_core == core:
                break
            core = stripped_core
        core = re.sub(r"\s+", " ", core).strip(" ,.!?")
        lowered = core.lower()
        words = core.split()
        if not core or len(words) < 3 or len(core) > 88:
            return ""
        if re.fullmatch(r"(?i)(?:and\s+)?(?:yes|yeah|yep|right|sure|okay|ok|well|all right|yes do|yes am to, both questions|yes ma'am)[\s,.!']*", core):
            return ""
        if re.match(r"(?i)^(?:and\s+)?(?:yes|yeah|right|sure|okay|ok|well|all right)\b", core) and len(words) < 6:
            return ""
        if lowered.startswith(("oh,", "oh ", "is ", "are ", "do ", "does ", "did ", "can ", "could ", "would ", "will ", "what ", "why ", "how ")):
            return ""
        if re.search(r"(?i)\b(?:coffee|understood|got it|you know|i mean|let me try|damn|try em|\bem\b|hmm+|haha+|porn|fuck|shit|bitch|sex|jerk|kill|murder|fentanyl|drugs|twine|where|call|personnel|television|fishing|golf|stereo|my word|i'll bet|hot af|af dude|history show|terrifying|turn part|eyepatch|new kid|kid|dude|guy|girl|woman|man|boy|husband|wife|girlfriend|boyfriend|jersey|crawfish|weird eyes|remnants|keep it damp|substantially|doing fine|that recent|fuk|baby|right back|nearby|top men|spacing|wish more people|good luck with work|at least makes sense|to be sure|just making sure|i was confused|work tomorrow|lool|laughed pretty hard|good work if true|good work, if true|thanks|original trust|room buzzes|buzzing with excitement|cutting edge|shader tricks|tech guru|motto is awesome|pretty much yeah|that's right yes)\b", core):
            return ""
        if re.fullmatch(r"(?i)(?:sh+|you go ahead|go ahead|let's start with you|let me try it again)[\s,.!']*", core):
            return ""
        response_key = normalize_response_act(response_act)
        if response_key == "ACKNOWLEDGE" and re.search(r"(?i)\b(?:no|not|n't|sorry)\b", core):
            return ""
        safe_patterns = {
            "INFORM": r"(?i)\b(?:makes sense|possible|probably|looks like|sounds like|seems|means|because|there is|it is)\b",
            "ACKNOWLEDGE": r"(?i)\b(?:right|yes|yeah|sure|okay|ok|makes sense|noted|i see|true|fair|good point|that works|i get)\b|\bthat\s+(?:is|sounds|feels|seems)\s+(?:right|true|fair|good|nice|rough|frustrating)\b",
            "DIRECTIVE": r"(?i)\b(?:let's|keep going|continue|try|go ahead|we can|start)\b",
            "EXPRESSIVE": r"(?i)\b(?:wow|surprise|surprised|great|nice|fun|sorry|love|awesome|amazing|good luck|thank|excited|glad|cracked me up)\b",
            "REJECT": r"(?i)\b(?:no|not|can't|cannot|wrong|not quite|don't|do not)\b",
        }
        if not re.search(safe_patterns.get(response_key, r"(?i)\b(?:that|this|it)\b"), core):
            return ""
        return core[0].lower() + core[1:] if core and core[0].isupper() else core

    def _clean_emotion_core(self, text: str, emotion: str, rank: int = 0, topic: str = "") -> str:
        """Keep a short GoEmotions-derived affect clause for Grounded composition."""
        del rank, topic
        core = re.sub(r"[^A-Za-z0-9',.!? ]+", " ", str(text or ""))
        core = re.sub(r"(?i)\b(?:ha[\s-]*){2,}ha?\b|\b(?:ahaha+|hee[\s-]*hee+|hehe+|lol|lmao|rofl)\b", " ", core)
        core = core.strip(" ,.!?")
        prefix_noise = r"(?i)^\s*(?:ah+|eh+|oh+|w+|th|well|okay|ok|alright|anyway|so|um+|uh+|hmm+|mmm+|ack|i think)\b[,.!?\s-]*"
        for _ in range(3):
            stripped_core = re.sub(prefix_noise, "", core)
            if stripped_core == core:
                break
            core = stripped_core
        core = re.sub(r"\s+", " ", core).strip(" ,.!?")
        words = core.split()
        if not core or len(words) < 2 or len(words) > 12 or len(core) > 72:
            return ""
        if core.endswith("?") or re.match(r"(?i)^(?:is|are|do|does|did|can|could|would|will|what|why|how)\b", core):
            return ""
        if re.search(r"(?i)\b(?:porn|fuck|shit|bitch|sex|jerk|kill|murder|fentanyl|drugs|husband|wife|girlfriend|boyfriend|kid|baby|golf|fishing|television|stereo|crawfish|room buzzes|buzzing with excitement|cutting edge|shader tricks|tech guru|motto is awesome|pretty much yeah|that's right yes)\b", core):
            return ""
        emotion_key = self._emotion_key(emotion)
        if emotion_key == "NEGATIVE" and not re.search(r"(?i)\b(?:bad|terrible|worst|awful|rough|sad|sorry|sucks|wrong|miss|condolences|concerned|eerie|scared|fear|panic|stress|pain|mess|tired)\b", core):
            return ""
        if emotion_key == "POSITIVE" and not re.search(r"(?i)\b(?:good|great|nice|love|glad|happy|fun|awesome|amazing|thanks|thank|cool|works|right|fair|beautiful)\b", core):
            return ""
        if emotion_key == "SURPRISE" and not re.search(r"(?i)\b(?:wow|surprise|surprised|confusing|confused|wild|crazy|unexpected|really|what)\b", core):
            return ""
        return core[0].lower() + core[1:] if core and core[0].isupper() else core

    @staticmethod
    def _text_key(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())[:96]

    def _text_keys(self, text: str) -> list[str]:
        keys: list[str] = []
        for value in [str(text or ""), *re.split(r"[;.!?]+", str(text or ""))]:
            key = self._text_key(value)
            if key and key not in keys:
                keys.append(key)
        return keys

    @staticmethod
    def _bad_surface_text(text: str) -> bool:
        return bool(
            re.search(
                r"(?i)\b(?:"
                r"dude|guy|girl|woman|man|boy|kid|baby|"
                r"gun|guns|mail thing|through the mail|holidays|pats losing|great town|"
                r"black plastic|calamari|singing|watching that show|domestic workers|"
                r"hentaipoon|keep a lookout|that show|this sub|bad at irony|"
                r"not talking about any loss|good looking|have fun doing this|"
                r"playdespacito|happy cake day|plus ultra|car buying|nice work gang|"
                r"it has, it has|nice talking with you|"
                r"lake not far|not all of us|we did not do it right|"
                r"weird thing to be concerned|good riddance|awful rubbish|"
                r"nice talking to you|nice to talk to you|speaking to you|thank you for calling|"
                r"wish could make it|late response|typo|flew off the handle|happy little lies|"
                r"don't know|dont know|do not know|out of control|not so much|do much of it|"
                r"unpopular opinion|legally wrong|bad dude|real bad beat|"
                r"room buzzes|buzzing with excitement|cutting edge|shader tricks|tech guru|"
                r"motto is awesome|pretty much yeah|that's right yes"
                r")\b",
                str(text or ""),
            )
        )

    def _remember_text(self, text: str) -> None:
        keys = self._text_keys(text)
        if not keys:
            return
        key_set = set(keys)
        self._recent_text_keys = [existing for existing in self._recent_text_keys if existing not in key_set]
        self._recent_text_keys[:0] = keys
        del self._recent_text_keys[self._recent_text_window :]

    def _compose_text(
        self,
        *,
        emotion: str,
        response_act: str,
        go_item: dict[str, Any] | None,
        swda_item: dict[str, Any] | None,
        rank: int,
        selection_policy: str,
        query: str = "",
    ) -> str:
        emotion_key = self._emotion_key(emotion)
        response_key = normalize_response_act(response_act)
        topic = self._topic_hint(query)
        if selection_policy == "emotion_only":
            core = self._clean_emotion_core(str((go_item or {}).get("text") or ""), emotion_key, rank, topic)
            text = core
        elif selection_policy == "grounded":
            go_core = self._clean_emotion_core(str((go_item or {}).get("text") or ""), emotion_key, rank, topic)
            swda_core = self._clean_core(str((swda_item or {}).get("text") or ""), response_key, rank, topic)
            if go_core and swda_core and self._text_key(go_core) != self._text_key(swda_core):
                if response_key == "REJECT":
                    text = f"{swda_core}; {go_core}"
                elif response_key == "DIRECTIVE":
                    text = f"{swda_core}; {go_core}"
                else:
                    text = f"{go_core}; {swda_core}"
            else:
                return ""
        else:
            text = self._clean_core(str((swda_item or {}).get("text") or ""), response_key, rank, topic)
        if not text:
            return ""

        if selection_policy == "response_act_only":
            emotion_key = "NEUTRAL"

        text = re.sub(r"\s+", " ", text.replace("..", ".")).strip()
        words = text.split()
        if len(words) > 18:
            text = " ".join(words[:18]).rstrip(" ,;:-")
        if not text.endswith((".", "!", "?")):
            text = f"{text}."
        if self._bad_surface_text(text):
            return ""
        return text

    def search(
        self,
        query: str,
        *,
        emotion: str,
        response_act: str,
        top_k: int = 3,
        selection_policy: str = "grounded",
        rng: random.Random | None = None,
    ) -> list[dict[str, Any]]:
        emotion_key = self._emotion_key(emotion)
        response_key = normalize_response_act(response_act)
        policy = str(selection_policy or "grounded").lower()
        use_go = policy in {"grounded", "emotion_only", "neutral_random"}
        use_swda = policy in {"grounded", "response_act_only", "neutral_random"}
        search_k = max(5000, int(top_k) * 1000, self._recent_text_window + int(top_k) * 24)
        go_hits = self._random_bucket("go_emotions", emotion_key if policy != "neutral_random" else "NEUTRAL", rng) if use_go else []
        swda_hits = self._random_bucket("swda", response_key if policy != "neutral_random" else "ACKNOWLEDGE", rng) if use_swda else []
        if use_go and not go_hits:
            return []
        if use_swda and not swda_hits:
            return []

        results: list[dict[str, Any]] = []
        skipped_recent: list[dict[str, Any]] = []
        if use_go and use_swda and go_hits and swda_hits:
            rank_limit = min(len(go_hits) * len(swda_hits), max(search_k, int(top_k) * 300))
        else:
            rank_limit = max(len(go_hits) if go_hits else 0, len(swda_hits) if swda_hits else 0, max(1, int(top_k)))
        for rank in range(rank_limit):
            if use_go and use_swda and go_hits and swda_hits:
                go_index = rank % len(go_hits)
                swda_index = ((rank * 37) + (rank // len(go_hits))) % len(swda_hits)
                go_item, go_score = go_hits[go_index]
                swda_item, swda_score = swda_hits[swda_index]
            else:
                go_item, go_score = go_hits[rank % len(go_hits)] if use_go and go_hits else ({}, 0.0)
                swda_item, swda_score = swda_hits[rank % len(swda_hits)] if use_swda and swda_hits else ({}, 0.0)
            score_parts = ([go_score] if use_go else []) + ([swda_score] if use_swda else [])
            score = sum(score_parts) / len(score_parts) if score_parts else 0.0
            text = self._compose_text(
                emotion=emotion_key,
                response_act=response_key,
                go_item=go_item if use_go else None,
                swda_item=swda_item if use_swda else None,
                rank=rank + 1,
                selection_policy=policy,
                query=query,
            )
            if not text:
                continue
            candidate = {
                "item_id": f"runtime_{go_item.get('id', 'no_go')}__{swda_item.get('id', 'no_swda')}",
                "cell_id": f"{emotion_key.lower()}_{response_key.lower()}",
                "text": text,
                "emotion": emotion_key.title(),
                "response_act": response_key,
                "score": score,
                "index": rank,
                "source": "separated_dataset_pool_runtime",
                "selection_policy": policy,
                "composition_sources": (
                    ["go_emotions", "swda"]
                    if policy == "grounded"
                    else (["go_emotions"] if use_go and not use_swda else ["swda"] if use_swda and not use_go else [])
                ),
                "go_emotions_item": go_item if use_go else None,
                "swda_item": swda_item if use_swda else None,
            }
            text_keys = self._text_keys(text)
            if any(text_key in self._recent_text_keys for text_key in text_keys) and rank + 1 < rank_limit:
                skipped_recent.append(candidate)
                continue
            results.append(candidate)
            self._remember_text(text)
            if len(results) >= max(1, int(top_k)):
                break
        scheduling_mode = str(getattr(config, "CREDO_CONTEXT_SCHEDULING_MODE", "parallel")).lower()
        if not results and skipped_recent and scheduling_mode != "parallel":
            results = skipped_recent[: max(1, int(top_k))]
            for item in results:
                self._remember_text(str(item.get("text") or ""))
        return results

    def _source_segment(
        self,
        *,
        source_name: str,
        label: str,
        item: dict[str, Any],
        role: str,
        order: int,
        emotion: str,
        response_act: str,
        selection_policy: str,
        score: float,
    ) -> dict[str, Any]:
        text = self._item_text(item).strip()
        return {
            "item_id": str(item.get("id") or f"{source_name}_{label.lower()}_{order}"),
            "cell_id": f"{source_name}_{label.lower()}",
            "text": text,
            "plain_text": text,
            "emotion": emotion if source_name == "go_emotions" else "UNSPECIFIED",
            "response_act": response_act if source_name == "swda" else "UNSPECIFIED",
            "score": score,
            "index": order,
            "source": "separated_dataset_pool_original_text",
            "selection_policy": selection_policy,
            "segment_role": role,
            "segment_order": order,
            "composition_sources": [source_name],
            "go_emotions_item": item if source_name == "go_emotions" else None,
            "swda_item": item if source_name == "swda" else None,
            "source_dataset": source_name,
            "source_item_id": str(item.get("id") or ""),
            "source_label": label,
        }

    def search_prebuilt_units(
        self,
        query: str,
        *,
        emotion: str,
        response_act: str,
        top_k: int = 3,
        selection_policy: str = "grounded",
        rng: random.Random | None = None,
    ) -> list[dict[str, Any]]:
        """Select the original filtered dataset text units before wav lookup."""
        emotion_key = self._emotion_key(emotion)
        response_key = normalize_response_act(response_act)
        policy = str(selection_policy or "grounded").lower()
        go_label = emotion_key if policy != "neutral_random" else "NEUTRAL"
        swda_label = response_key if policy != "neutral_random" else "ACKNOWLEDGE"
        use_go = policy in {"grounded", "emotion_only", "neutral_random"}
        use_swda = policy in {"grounded", "response_act_only", "neutral_random"}
        go_hits = self._random_bucket("go_emotions", go_label, rng) if use_go else []
        swda_hits = self._random_bucket("swda", swda_label, rng) if use_swda else []
        if use_go and not go_hits:
            return []
        if use_swda and not swda_hits:
            return []

        results: list[dict[str, Any]] = []
        rank_limit = max(len(go_hits), len(swda_hits), max(1, int(top_k))) if not (go_hits and swda_hits) else min(
            len(go_hits) * len(swda_hits),
            max(5000, int(top_k) * 1000, self._recent_text_window + int(top_k) * 24),
        )
        for rank in range(rank_limit):
            segments: list[dict[str, Any]] = []
            score_parts: list[float] = []
            if use_go and go_hits:
                go_item, go_score = go_hits[rank % len(go_hits)]
                score_parts.append(go_score)
                segments.append(
                    self._source_segment(
                        source_name="go_emotions",
                        label=go_label,
                        item=go_item,
                        role="emotion",
                        order=0,
                        emotion=emotion_key,
                        response_act=response_key,
                        selection_policy=policy,
                        score=go_score,
                    )
                )
            if use_swda and swda_hits:
                swda_index = ((rank * 37) + (rank // max(1, len(go_hits)))) % len(swda_hits)
                swda_item, swda_score = swda_hits[swda_index]
                score_parts.append(swda_score)
                segments.append(
                    self._source_segment(
                        source_name="swda",
                        label=swda_label,
                        item=swda_item,
                        role="intent",
                        order=len(segments),
                        emotion=emotion_key,
                        response_act=response_key,
                        selection_policy=policy,
                        score=swda_score,
                    )
                )
            segments = [segment for segment in segments if str(segment.get("text") or "").strip()]
            if not segments:
                continue
            text_parts = []
            for segment in segments:
                segment_text = str(segment.get("text") or "").strip()
                if segment_text and not segment_text.endswith((".", "!", "?")):
                    segment_text = f"{segment_text}."
                text_parts.append(segment_text)
            text = " ".join(text_parts).strip()
            text_keys = self._text_keys(text)
            if any(text_key in self._recent_text_keys for text_key in text_keys) and rank + 1 < rank_limit:
                continue
            score = sum(score_parts) / len(score_parts) if score_parts else 0.0
            result = {
                "item_id": "__".join(str(segment.get("item_id") or "") for segment in segments),
                "cell_id": f"{policy}_{emotion_key.lower()}_{response_key.lower()}",
                "text": text,
                "emotion": emotion_key.title(),
                "response_act": response_key,
                "score": score,
                "index": rank,
                "source": "separated_dataset_pool_original_text_sequence",
                "selection_policy": policy,
                "composition_sources": [str(segment.get("source_dataset") or "") for segment in segments],
                "segments": segments,
                "go_emotions_item": next((segment.get("go_emotions_item") for segment in segments if segment.get("go_emotions_item")), None),
                "swda_item": next((segment.get("swda_item") for segment in segments if segment.get("swda_item")), None),
            }
            results.append(result)
            self._remember_text(text)
            if len(results) >= max(1, int(top_k)):
                break
        return results


class RouterV3Runtime:
    """Owns lazy model/index state for analyze_and_route_chat_v3."""

    def __init__(self) -> None:
        self.threshold = float(getattr(config, "FASTTRACK_ROUTER_V3_CONFIDENCE_THRESHOLD", 0.6))
        self.top_k = int(getattr(config, "FASTTRACK_ROUTER_V3_TOP_K", 3))
        self.rng = random.Random(20260526)
        self.nlp = None
        self.spacy_checked = False
        self.intent_model = None
        self.intent_labels: dict[int, str] = {}
        self.intent_checked = False
        self.intent_loading_started = False
        self.emotion_pipeline = None
        self.emotion_checked = False
        self.transition = IntentTransitionPlanner()
        pool_path = getattr(config, "FAST_TRACK_DATASET_POOL_PATH", getattr(config, "FAST_TRACK_PERSONA_BUNDLE_PATH"))
        self.store = SeparatedDatasetPoolStore(pool_path)
        manifest_path = getattr(
            config,
            "FASTTRACK_PREBUILT_MANIFEST_PATH",
            ROOT / "fasttrack_assets" / "audio" / "prebuilt_stylebert_v1" / "manifest.json",
        )
        self.prebuilt_manifest = PrebuiltFastTrackManifest(Path(manifest_path))

    def _load_spacy(self) -> None:
        if self.spacy_checked:
            return
        self.spacy_checked = True
        try:
            import spacy

            model_name = str(getattr(config, "SPACY_MODEL_NAME", "en_core_web_sm") or "en_core_web_sm")
            self.nlp = spacy.load(model_name, disable=["parser", "ner", "lemmatizer"])
        except Exception:
            self.nlp = None

    @staticmethod
    def _keyword_allowed(text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if len(lowered) < 3 or len(lowered) > 36:
            return False
        if re.search(r"[^a-z0-9' -]", lowered):
            return False
        return lowered not in {
            "thing",
            "things",
            "something",
            "anything",
            "everything",
            "today",
            "lab",
            "maid",
            "professor",
            "chat",
            "viewer",
            "stream",
            "really",
            "maybe",
            "please",
            "think",
            "going",
            "doing",
            "make",
            "made",
            "tell",
            "know",
            "want",
            "need",
            "delete",
            "deleted",
            "deleting",
            "lost",
            "panic",
            "panicking",
            "have",
            "does",
            "did",
            "is",
            "are",
            "was",
            "were",
        }

    def extract_keywords(self, text: str) -> list[str]:
        """Extract compact noun/verb anchors for FastTrack echo prefixing."""
        self._load_spacy()
        candidates: list[str] = []
        if self.nlp is not None:
            try:
                doc = self.nlp(text[:512])
                preferred = ("NOUN", "PROPN", "VERB")
                for pos in preferred:
                    for token in doc:
                        if token.pos_ != pos or token.is_stop or token.is_punct or token.like_num:
                            continue
                        keyword = re.sub(r"[^A-Za-z0-9' -]", "", token.text).strip(" -'")
                        if self._keyword_allowed(keyword):
                            candidates.append(keyword)
            except Exception:
                candidates = []
        if not candidates:
            stopwords = {
                "the", "a", "an", "and", "or", "but", "for", "with", "this", "that", "you", "your",
                "me", "my", "we", "our", "they", "their", "can", "could", "would", "should",
            }
            for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,35}", str(text)):
                if token.lower() not in stopwords and self._keyword_allowed(token):
                    candidates.append(token)
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in candidates:
            key = keyword.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(keyword)
        return deduped[:5]

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
        keyword_task = asyncio.to_thread(self.extract_keywords, cleaned)
        emotion, intent, keywords = await asyncio.gather(emotion_task, intent_task, keyword_task)
        if emotion.confidence < self.threshold or intent.confidence < self.threshold:
            return None
        transition = self.transition.choose(intent.label, emotion=emotion.label.lower(), rng=self.rng)
        response_act = normalize_response_act(transition.response_intent)
        keyword_query = " ".join(keywords[:3])
        query = f"{emotion.label} {response_act} {keyword_query} {cleaned}".strip()
        selection_policy = str(getattr(config, "CREDO_FASTTRACK_SELECTION_POLICY", "grounded")).lower()
        lookup_started = time.perf_counter()
        top3 = [
            self.prebuilt_manifest.attach_sequence(candidate)
            for candidate in self.store.search_prebuilt_units(
                query,
                emotion=emotion.label,
                response_act=response_act,
                top_k=self.top_k,
                selection_policy=selection_policy,
                rng=self.rng,
            )
        ]
        selected = next((candidate for candidate in top3 if candidate.get("prebuilt_hit")), top3[0] if top3 else {})
        lookup_latency_ms = (time.perf_counter() - lookup_started) * 1000.0
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
            "response_act": response_act,
            "route_query": query,
            "keywords": keywords,
            "keyword_echo": keywords[0] if keywords else None,
            "faiss_available": self.store.faiss_available,
            "dataset_pool_path": str(self.store.pool_path),
            "prebuilt_manifest_path": str(self.prebuilt_manifest.manifest_path),
            "prebuilt_manifest_available": self.prebuilt_manifest.available,
            "selection_policy": selection_policy,
            "candidate_selection": "uniform_random_within_mapped_bucket",
            "lookup_latency_ms": round(lookup_latency_ms, 3),
            "selected_reaction": selected,
            "selected_text": selected.get("text") if selected else "",
            "selected_audio_path": selected.get("audio_path") if selected else None,
            "selected_audio_paths": selected.get("selected_audio_paths") if selected else [],
            "audio_sequence": selected.get("audio_sequence") if selected else [],
            "prebuilt_hit": bool(selected.get("prebuilt_hit")) if selected else False,
            "cache_hit": bool(selected.get("cache_hit")) if selected else False,
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
