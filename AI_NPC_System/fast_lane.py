# fast_lane.py
import json
import random
import time
import os
from pathlib import Path

import spacy
from transformers import pipeline

import config
import merge_policy

print("⚡ [Fast Lane] 모델 로딩 중...")

MODEL_READY = True
MODEL_ERROR = None

try:
    emotion_pipeline = pipeline("text-classification", model=config.EMOTION_MODEL_NAME, top_k=None)
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    MODEL_READY = False
    MODEL_ERROR = str(e)
    emotion_pipeline = None
    nlp = None
    print("❌ [Fast Lane] 모델 로딩 실패")
    print(f"   ├─ EMOTION_MODEL_NAME: {getattr(config, 'EMOTION_MODEL_NAME', 'unknown')}")
    print(f"   ├─ spaCy model: en_core_web_sm")
    print(f"   └─ error: {MODEL_ERROR}")
    print("⚠️ [Fast Lane] 중립 fallback 모드로 계속 실행합니다.")

DEFAULT_REACTIONS = ["I see.", "I hear you.", "Please go on."]

EMOTION_CATEGORIES = {
    "positive": [
        "admiration", "amusement", "approval", "caring", "desire", "excitement",
        "gratitude", "joy", "love", "optimism", "pride", "relief"
    ],
    "negative": [
        "anger", "annoyance", "disappointment", "disapproval", "disgust",
        "embarrassment", "fear", "grief", "nervousness", "remorse", "sadness"
    ],
    "ambiguous": ["confusion", "curiosity", "realization", "surprise"],
    "neutral": ["neutral"],
}


def _candidate_db_paths():
    root = Path(__file__).resolve().parent
    default_name = getattr(config, "REACTION_DB_FILE", "reactions.json")
    yield root / default_name
    yield root / "reactions.json"


def load_reactions():
    for p in _candidate_db_paths():
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return {}


REACTION_DB = load_reactions()


def _aggregate_category_scores(all_scores):
    category_scores = {"positive": 0.0, "negative": 0.0, "ambiguous": 0.0, "neutral": 0.0}
    for item in all_scores:
        label = item["label"]
        score = float(item["score"])
        for category, labels in EMOTION_CATEGORIES.items():
            if label in labels:
                category_scores[category] += score
                break
    return category_scores


def _pick_reaction(emotion_label, strategy):
    # strategy-specific list 우선
    if strategy in REACTION_DB and isinstance(REACTION_DB.get(strategy), list):
        arr = REACTION_DB.get(strategy) or DEFAULT_REACTIONS
        return random.choice(arr)

    arr = REACTION_DB.get(emotion_label, DEFAULT_REACTIONS)
    return random.choice(arr)


def analyze_and_react(text):
    t0 = time.time()
    final_emotion = "neutral"
    category_scores = {"positive": 0.0, "negative": 0.0, "ambiguous": 0.0, "neutral": 1.0}

    if not MODEL_READY:
        print("⚠️ [Fast Lane] fallback 중: 모델 미준비 상태로 neutral 처리")
        if MODEL_ERROR:
            print(f"   └─ last_error: {MODEL_ERROR}")
    else:
        try:
            short_text = text[:512]
            all_scores = emotion_pipeline(short_text)[0]
            category_scores = _aggregate_category_scores(all_scores)
            final_emotion = max(category_scores, key=category_scores.get)
        except Exception as e:
            print(f"감정 분석 에러: {e}")

    bert_time = time.time() - t0

    t1 = time.time()
    keyword = None
    echo_text = ""
    try:
        if nlp is not None:
            doc = nlp(text)
            keywords = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
            if keywords:
                keyword = keywords[-1]
                echo_text = f"{keyword}?"
    except Exception as e:
        print(f"spaCy 키워드 추출 에러: {e}")
    spacy_time = time.time() - t1

    policy = merge_policy.select_strategy(
        category_scores=category_scores,
        has_keyword=bool(keyword),
        user_text=text,
        llm_eta_ms=getattr(config, "EXPECTED_SLOW_LANE_MS", 0),
    )

    strategy = policy["strategy"]

    # 중립 최소 모드면 에코잉 억제
    if strategy == "neutral_minimal":
        echo_text = ""

    reaction = _pick_reaction(final_emotion, strategy)

    return {
        "emotion_label": final_emotion,
        "emotion_detail": final_emotion,
        "reaction": reaction,
        "keyword": keyword,
        "echo_text": echo_text,
        "strategy": strategy,
        "top1": round(policy["top1"], 4),
        "margin": round(policy["margin"], 4),
        "entropy": round(policy["entropy"], 4),
        "confidence_band": policy["confidence_band"],
        "category_scores": {k: round(v, 4) for k, v in category_scores.items()},
        "bert_time": f"{bert_time:.4f}s",
        "spacy_time": f"{spacy_time:.4f}s",
    }


if __name__ == "__main__":
    print(analyze_and_react("I passed the exam! I am so happy!"))
