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
    emotion_pipeline = pipeline("text-classification", model=config.EMOTION_MODEL_NAME, top_k=1)
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"모델 로드 실패: {e}")
    exit()

# 2. 리액션 DB 로드 (JSON 파일)
DB_FILE = "reactions.json"
DEFAULT_REACTIONS = ["I see.", "I hear you.", "Please go on."]

def load_reactions():
    if not os.path.exists(DB_FILE):
        print(f"{DB_FILE} 파일이 없습니다. 기본값만 사용합니다.")
        return {}
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"JSON 로드 에러: {e}")
        return {}

# 전역 변수로 DB 로드
REACTION_DB = load_reactions()

def analyze_and_react(text):
    # --- A. 감정 분석 (DistilBERT) ---
    t0 = time.time()
    try:
        # 텍스트가 너무 길면 잘라서 처리 (오류 방지)
        short_text = text[:512]
        raw_emotion = emotion_pipeline(short_text)[0][0]['label']
    except:
        raw_emotion = "neutral"
    bert_time = time.time() - t0
    
    # --- B. 키워드 추출 (SpaCy) - 에코잉 복구 ---
    t1 = time.time()
    keyword = None
    echo_text = ""
    
    try:
        doc = nlp(text)
        # 명사(NOUN)나 고유명사(PROPN) 중 가장 마지막 단어 추출
        keywords = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
        if keywords:
            keyword = keywords[-1]
            # ★ 에코잉 텍스트 생성 (예: "Wallet?")
            echo_text = f"{keyword}?"
    except:
        pass
    spacy_time = time.time() - t1
    
    # --- C. 리액션 선택 ---
    possible_reactions = REACTION_DB.get(raw_emotion, DEFAULT_REACTIONS)
    reaction = random.choice(possible_reactions)
    
    return {
        "emotion_label": raw_emotion,
        "reaction": reaction,
        "keyword": keyword,     # 원본 키워드
        "echo_text": echo_text, # ★ 복구된 에코잉 대사
        "bert_time": f"{bert_time:.4f}s",
        "spacy_time": f"{spacy_time:.4f}s"
    }

if __name__ == "__main__":
    # 테스트
    print(analyze_and_react("My sister stole my wallet."))