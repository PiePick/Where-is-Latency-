# fast_lane.py
import random
import spacy
from transformers import pipeline
import config  # 설정 파일 불러오기

print("⚡ [Fast Lane] 모델 로딩 중... (잠시만 기다려주세요)")

# 1. 모델 초기화
emotion_pipeline = pipeline("text-classification", model=config.EMOTION_MODEL_NAME, top_k=1)
nlp = spacy.load("en_core_web_sm")

# 2. 감정 매핑 (28개 -> 3개)
EMOTION_MAP = {
    # 긍정
    "admiration": "POSITIVE", "amusement": "POSITIVE", "excitement": "POSITIVE",
    "joy": "POSITIVE", "love": "POSITIVE", "pride": "POSITIVE", "relief": "POSITIVE",
    # 부정
    "anger": "NEGATIVE", "annoyance": "NEGATIVE", "disappointment": "NEGATIVE",
    "fear": "NEGATIVE", "sadness": "NEGATIVE", "remorse": "NEGATIVE",
    # 중립
    "confusion": "NEUTRAL", "curiosity": "NEUTRAL", "neutral": "NEUTRAL", "surprise": "NEUTRAL"
}

# 3. 리액션 텍스트 (오디오 파일 대신 텍스트로 시뮬레이션)
REACTION_TEXTS = {
    "POSITIVE": ["Wow!", "Amazing!", "That's great!"],
    "NEGATIVE": ["Oh no...", "That's terrible.", "Hmm..."],
    "NEUTRAL":  ["I see.", "Okay.", "Interesting."]
}

# === 메인 함수 ===
def analyze_and_react(text):
    # (1) 감정 분석
    raw_emotion = emotion_pipeline(text)[0][0]['label']
    category = EMOTION_MAP.get(raw_emotion, "NEUTRAL")
    
    # (2) 키워드 추출
    doc = nlp(text)
    keywords = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
    keyword = keywords[-1] if keywords else None
    
    # (3) 리액션 선택
    reaction = random.choice(REACTION_TEXTS[category])
    
    return {
        "emotion_detail": raw_emotion,
        "category": category,
        "reaction": reaction,
        "keyword": keyword
    }