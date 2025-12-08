# fast_lane.py
import json
import random
import time
import os
import spacy
from transformers import pipeline
import config

print("⚡ [Fast Lane] 모델 로딩 중...")

# 1. 모델 초기화
try:
    # top_k=None으로 설정하여 28개 감정의 모든 점수를 다 받아옵니다.
    emotion_pipeline = pipeline("text-classification", model=config.EMOTION_MODEL_NAME, top_k=None)
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"모델 로드 실패: {e}")
    exit()

# 2. 리액션 DB 로드
DB_FILE = "reactions.json"
DEFAULT_REACTIONS = ["I see.", "I hear you.", "Please go on."]

def load_reactions():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

REACTION_DB = load_reactions()

# ★ 4개 카테고리 정의 (점수 합산용)
EMOTION_CATEGORIES = {
    "positive": [
        "admiration", "amusement", "approval", "caring", "desire", "excitement", 
        "gratitude", "joy", "love", "optimism", "pride", "relief"
    ],
    "negative": [
        "anger", "annoyance", "disappointment", "disapproval", "disgust", 
        "embarrassment", "fear", "grief", "nervousness", "remorse", "sadness"
    ],
    "ambiguous": [
        "confusion", "curiosity", "realization", "surprise"
    ],
    "neutral": [
        "neutral"
    ]
}

def analyze_and_react(text):
    # --- A. 감정 분석 (점수 합산 방식) ---
    t0 = time.time()
    final_emotion = "neutral"
    
    try:
        short_text = text[:512]
        # 1. 모델에서 28개 감정 점수 모두 가져오기
        all_scores = emotion_pipeline(short_text)[0] # List of dicts [{'label': 'joy', 'score': 0.9}, ...]
        
        # 2. 4개 카테고리 점수판 초기화
        category_scores = {
            "positive": 0.0,
            "negative": 0.0,
            "ambiguous": 0.0,
            "neutral": 0.0
        }
        
        # 3. 점수 합산 (Aggregation)
        # 예: joy(0.3) + excitement(0.4) => positive(0.7)
        for item in all_scores:
            label = item['label']
            score = item['score']
            
            # 해당 라벨이 속한 카테고리를 찾아서 점수 더하기
            for category, labels in EMOTION_CATEGORIES.items():
                if label in labels:
                    category_scores[category] += score
                    break
        
        # 4. 가장 높은 점수의 카테고리 선정 (Winner Takes All)
        final_emotion = max(category_scores, key=category_scores.get)
        
        # 디버깅용: 점수 확인
        # print(f"Scores: {category_scores}") 

    except Exception as e:
        print(f"감정 분석 에러: {e}")
        final_emotion = "neutral"
        
    bert_time = time.time() - t0
    
    # --- B. 키워드 추출 (SpaCy) ---
    t1 = time.time()
    keyword = None
    echo_text = ""
    
    try:
        doc = nlp(text)
        keywords = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
        if keywords:
            keyword = keywords[-1]
            echo_text = f"{keyword}?"
    except:
        pass
    spacy_time = time.time() - t1
    
    # --- C. 리액션 선택 ---
    possible_reactions = REACTION_DB.get(final_emotion, DEFAULT_REACTIONS)
    reaction = random.choice(possible_reactions)
    
    return {
        "emotion_label": final_emotion, # positive, negative, ...
        "reaction": reaction,
        "keyword": keyword,
        "echo_text": echo_text,
        "bert_time": f"{bert_time:.4f}s",
        "spacy_time": f"{spacy_time:.4f}s"
    }

if __name__ == "__main__":
    # 테스트
    print(analyze_and_react("I passed the exam! I am so happy!"))