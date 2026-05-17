"""
Runtime hybrid Fast Track reaction generator.

Install:
  python3 -m pip install -r AI_NPC_System/scripts/requirements.txt
  python3 -m spacy download en_core_web_sm

Build the reaction JSON first:
  python3 AI_NPC_System/scripts/build_reaction_dataset.py

CLI smoke test:
  python3 AI_NPC_System/fast_track_engine.py --text "I passed the exam today"
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fast_track_audio_cache import FastTrackAudioCache
from tts_cues import DEFAULT_CUE_PATH, FishSpeechCueSelector


ROOT = Path(__file__).resolve().parent
DEFAULT_REACTION_PATH = ROOT / "hybrid_reactions.json"
DEFAULT_FAST_TRACK_AUDIO_CACHE_PATH = ROOT / "fast_track_audio_cache" / "manifest.json"
MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"

LABEL_TO_CATEGORY = {
    "admiration": "Positive",
    "amusement": "Positive",
    "approval": "Positive",
    "caring": "Positive",
    "desire": "Positive",
    "excitement": "Positive",
    "gratitude": "Positive",
    "joy": "Positive",
    "love": "Positive",
    "optimism": "Positive",
    "pride": "Positive",
    "relief": "Positive",
    "anger": "Negative",
    "annoyance": "Negative",
    "disappointment": "Negative",
    "disapproval": "Negative",
    "disgust": "Negative",
    "embarrassment": "Negative",
    "fear": "Negative",
    "grief": "Negative",
    "nervousness": "Negative",
    "remorse": "Negative",
    "sadness": "Negative",
    "confusion": "Ambiguous",
    "curiosity": "Ambiguous",
    "realization": "Ambiguous",
    "surprise": "Ambiguous",
    "neutral": "Neutral",
}

FALLBACK_REACTIONS = {
    "Positive": ["Nice.", "Huge W.", "Glad to hear it."],
    "Negative": ["That's rough.", "I hear you.", "That hurts."],
    "Ambiguous": ["Wait, really?", "Interesting.", "What happened?"],
    "Neutral": ["Got it.", "I see.", "Okay."],
}

SOURCE_KEYWORD_HINTS = {
    "stream": {
        "chat", "stream", "viewer", "clip", "meme", "game", "rank", "match", "boss",
        "level", "win", "loss", "queue", "lag", "server", "discord", "youtube", "twitch",
        "subs", "donation", "raid", "pog", "gg", "npc", "vtuber",
    },
    "everyday": {
        "mom", "dad", "mother", "father", "sister", "brother", "friend", "family", "money",
        "school", "class", "exam", "homework", "work", "job", "teacher", "doctor",
        "health", "sleep", "food", "relationship", "birthday", "house", "home",
    },
}


@dataclass(frozen=True)
class HybridFastTrackConfig:
    reaction_path: Path = DEFAULT_REACTION_PATH
    model_name: str = MODEL_NAME
    device: str = "auto"
    seed: int | None = None
    min_runtime_score: float = 0.0
    spacy_model: str = "en_core_web_sm"
    everyday_weight: float = 0.60
    stream_weight: float = 0.40
    fish_speech_cue_path: Path = DEFAULT_CUE_PATH
    fish_speech_cues_enabled: bool = True
    fish_speech_cue_probability: float = 0.65
    audio_cache_path: Path = DEFAULT_FAST_TRACK_AUDIO_CACHE_PATH
    audio_cache_enabled: bool = True
    keyword_source_bias_enabled: bool = True


@dataclass(frozen=True)
class CoverChoice:
    """One FastTrack cover selected from cache or live text fallback."""

    reaction: str
    source: str
    plain_tts_text: str
    tts_text: str
    cue: dict[str, Any] | None
    audio_path: str | None = None
    cache_id: str | None = None

    @property
    def cache_hit(self) -> bool:
        """Return true when this cover points to a pre-generated wav file."""
        return self.audio_path is not None


def require_runtime_deps() -> tuple[Any, Any, Any]:
    """Import optional ML dependencies only when the runtime is used."""
    try:
        import spacy
        import torch
        from transformers import pipeline
    except ImportError as exc:
        print("Missing dependency. Install with:")
        print("  python3 -m pip install -r AI_NPC_System/scripts/requirements.txt")
        print("  python3 -m spacy download en_core_web_sm")
        raise RuntimeError("FastTrack ML runtime dependencies are missing.") from exc
    return spacy, torch, pipeline


def choose_device(torch: Any, requested: str) -> int:
    """Map a human-readable device option to a Transformers pipeline device."""
    if requested == "cpu":
        return -1
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false.")
        return 0
    return 0 if torch.cuda.is_available() else -1


def load_reaction_db(path: Path) -> dict[str, Any]:
    """Load the prebuilt reaction list, or let runtime fallbacks handle misses."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_score_list(raw: Any) -> list[dict[str, Any]]:
    """Normalize Transformers output across old and new pipeline shapes."""
    if isinstance(raw, list):
        if raw and isinstance(raw[0], list):
            return raw[0] if raw[0] else [{"label": "neutral", "score": 0.0}]
        return raw if raw else [{"label": "neutral", "score": 0.0}]
    return [raw]


def aggregate_category_scores(score_items: list[dict[str, Any]]) -> dict[str, float]:
    """Collapse GoEmotions labels into the four FastTrack categories."""
    scores = {"Positive": 0.0, "Negative": 0.0, "Ambiguous": 0.0, "Neutral": 0.0}
    for item in score_items:
        label = str(item.get("label", "neutral")).lower()
        category = LABEL_TO_CATEGORY.get(label)
        if category:
            scores[category] += float(item.get("score", 0.0))
    return scores


def ranked_label_scores(score_items: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Return DistilBERT labels from highest to lowest confidence."""
    ranked = [
        (str(item.get("label", "neutral")).lower(), float(item.get("score", 0.0)))
        for item in score_items
    ]
    return sorted(ranked, key=lambda item: item[1], reverse=True)


class HybridFastTrack:
    """Fast reaction engine: DistilBERT emotion, spaCy keywords, reaction mix."""

    def __init__(self, config: HybridFastTrackConfig | None = None) -> None:
        self.config = config or HybridFastTrackConfig()
        spacy, torch, pipeline = require_runtime_deps()

        self.rng = random.Random(self.config.seed)
        self.reactions = load_reaction_db(self.config.reaction_path)
        self.cue_selector = FishSpeechCueSelector(
            self.config.fish_speech_cue_path,
            enabled=self.config.fish_speech_cues_enabled,
            probability=self.config.fish_speech_cue_probability,
            seed=self.config.seed,
        )
        self.audio_cache = FastTrackAudioCache(
            self.config.audio_cache_path,
            enabled=self.config.audio_cache_enabled,
            seed=self.config.seed,
            expected_reference_id=os.getenv(
                "FAST_TRACK_AUDIO_CACHE_REFERENCE_ID",
                os.getenv("FISH_SPEECH_REFERENCE_ID"),
            ),
        )
        self.device = choose_device(torch, self.config.device)
        self.classifier = pipeline(
            "text-classification",
            model=self.config.model_name,
            tokenizer=self.config.model_name,
            top_k=None,
            device=self.device,
        )
        self.nlp = spacy.load(
            self.config.spacy_model,
            disable=["parser", "ner", "lemmatizer"],
        )
        self._warmup()

    def _warmup(self) -> None:
        """Pay first-call model overhead before live traffic arrives."""
        self.classifier("warm up", truncation=True)
        self.nlp("warm up")

    def classify_emotion(self, text: str) -> dict[str, Any]:
        """Classify text with top-1 GoEmotions label and mapped category."""
        raw = self.classifier(text[:512], truncation=True)
        score_items = normalize_score_list(raw)
        ranked_labels = ranked_label_scores(score_items)
        label, score = ranked_labels[0]
        second_score = ranked_labels[1][1] if len(ranked_labels) > 1 else 0.0
        margin = score - second_score
        category_scores = aggregate_category_scores(score_items)
        category = LABEL_TO_CATEGORY.get(label, "Neutral")

        if score < self.config.min_runtime_score:
            category = "Neutral"
        return {
            "category": category,
            "label": label,
            "score": score,
            "margin": margin,
            "category_scores": category_scores,
        }

    def extract_keywords(self, text: str) -> list[str]:
        """Extract noun-like terms for source-selection hints."""
        doc = self.nlp(text)
        keywords = []
        for token in doc:
            if token.pos_ in {"NOUN", "PROPN"} and not token.is_stop:
                keywords.append(token.text)
        return keywords

    def preferred_source_from_keywords(self, keywords: list[str]) -> str | None:
        """Use keywords as a source-selection hint without echoing them."""
        if not self.config.keyword_source_bias_enabled:
            return None
        normalized = {kw.strip(".,!?;:\"'()").lower() for kw in keywords}
        normalized.discard("")
        for source, hints in SOURCE_KEYWORD_HINTS.items():
            if normalized & hints:
                return source
        return None

    def choose_reaction(self, category: str, preferred_source: str | None = None) -> tuple[str, str]:
        """Sample a reaction, optionally biased by keyword-derived source hints."""
        bucket = self.reactions.get(category, {})
        if isinstance(bucket, dict):
            source_lists = {
                "everyday": bucket.get("everyday") or [],
                "stream": bucket.get("stream") or [],
            }
            if preferred_source in source_lists and source_lists[preferred_source]:
                return self.rng.choice(source_lists[preferred_source]), preferred_source

            everyday = source_lists["everyday"]
            stream = source_lists["stream"]
            if everyday and stream:
                total_weight = max(0.0, self.config.everyday_weight) + max(0.0, self.config.stream_weight)
                everyday_probability = self.config.everyday_weight / total_weight if total_weight else 0.5
                source = "everyday" if self.rng.random() < everyday_probability else "stream"
                return self.rng.choice(source_lists[source]), source
            for source, candidates in source_lists.items():
                if candidates:
                    return self.rng.choice(candidates), source

        candidates = FALLBACK_REACTIONS.get(category, FALLBACK_REACTIONS["Neutral"])
        return self.rng.choice(candidates), "fallback"

    def choose_cover(self, category: str, keywords: list[str]) -> tuple[CoverChoice, str | None]:
        """Select a cached audio cover when possible, otherwise build live text."""
        preferred_source = self.preferred_source_from_keywords(keywords)
        cached = self.audio_cache.choose(category, preferred_source=preferred_source)
        if cached:
            return (
                CoverChoice(
                    reaction=cached.reaction,
                    source=cached.source,
                    plain_tts_text=cached.plain_tts_text,
                    tts_text=cached.tts_text,
                    cue=cached.cue,
                    audio_path=str(cached.audio_path),
                    cache_id=cached.cache_id,
                ),
                preferred_source,
            )

        reaction, source = self.choose_reaction(category, preferred_source)
        selected_cue = self.cue_selector.choose(category)
        plain_tts_text = reaction.strip()
        return (
            CoverChoice(
                reaction=reaction,
                source=source,
                plain_tts_text=plain_tts_text,
                tts_text=self.cue_selector.apply(plain_tts_text, selected_cue),
                cue=self.cue_selector.cue_to_dict(selected_cue),
            ),
            preferred_source,
        )

    def generate(self, user_text: str) -> dict[str, Any]:
        """Generate a complete FastTrack packet and timing metrics."""
        started = time.perf_counter()

        emotion_started = time.perf_counter()
        emotion = self.classify_emotion(user_text)
        emotion_ms = (time.perf_counter() - emotion_started) * 1000.0

        keyword_started = time.perf_counter()
        keywords = self.extract_keywords(user_text)
        keyword_ms = (time.perf_counter() - keyword_started) * 1000.0

        cover, preferred_source = self.choose_cover(emotion["category"], keywords)
        total_ms = (time.perf_counter() - started) * 1000.0

        return {
            "tts_text": cover.tts_text,
            "plain_tts_text": cover.plain_tts_text,
            "reaction": cover.reaction,
            "reaction_source": cover.source,
            "fish_speech_cue": cover.cue,
            "fast_audio_path": cover.audio_path,
            "fast_audio_cache_id": cover.cache_id,
            "fast_audio_cache_hit": cover.cache_hit,
            "keyword_selection_source": preferred_source,
            "keyword": keywords[-1] if keywords else None,
            "keywords": keywords,
            "emotion": emotion["category"],
            "emotion_label": emotion["label"],
            "emotion_score": round(emotion["score"], 4),
            "emotion_margin": round(emotion["margin"], 4),
            "category_scores": {key: round(value, 4) for key, value in emotion["category_scores"].items()},
            "latency_ms": round(total_ms, 3),
            "emotion_ms": round(emotion_ms, 3),
            "keyword_ms": round(keyword_ms, 3),
        }


_DEFAULT_ENGINE: HybridFastTrack | None = None


def get_default_engine() -> HybridFastTrack:
    """Expose a lazy singleton for scripts that need one-line FastTrack calls."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = HybridFastTrack()
    return _DEFAULT_ENGINE


def generate_fast_tts_text(user_text: str) -> str:
    """Return only the TTS-ready FastTrack text."""
    return get_default_engine().generate(user_text)["tts_text"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hybrid Fast Track once.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--reaction-path", type=Path, default=DEFAULT_REACTION_PATH)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-runtime-score", type=float, default=0.0)
    parser.add_argument("--everyday-weight", type=float, default=0.60)
    parser.add_argument("--stream-weight", type=float, default=0.40)
    parser.add_argument("--disable-fish-speech-cues", action="store_true")
    parser.add_argument("--fish-speech-cue-probability", type=float, default=0.65)
    parser.add_argument("--audio-cache-path", type=Path, default=DEFAULT_FAST_TRACK_AUDIO_CACHE_PATH)
    parser.add_argument("--disable-audio-cache", action="store_true")
    parser.add_argument("--disable-keyword-source-bias", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = HybridFastTrack(
        HybridFastTrackConfig(
            reaction_path=args.reaction_path,
            device=args.device,
            seed=args.seed,
            min_runtime_score=args.min_runtime_score,
            everyday_weight=args.everyday_weight,
            stream_weight=args.stream_weight,
            fish_speech_cues_enabled=not args.disable_fish_speech_cues,
            fish_speech_cue_probability=args.fish_speech_cue_probability,
            audio_cache_path=args.audio_cache_path,
            audio_cache_enabled=not args.disable_audio_cache,
            keyword_source_bias_enabled=not args.disable_keyword_source_bias,
        )
    )
    print(json.dumps(engine.generate(args.text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
