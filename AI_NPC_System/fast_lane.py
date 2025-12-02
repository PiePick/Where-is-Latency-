# fast_lane.py
import random
import spacy
from transformers import pipeline
import config

print("⚡ [Fast Lane] 모델 로딩 중... (잠시만 기다려주세요)")

# 1. 모델 초기화
# GoEmotions 데이터셋은 총 28개(27개 세부 감정 + Neutral)의 라벨을 출력합니다.
emotion_pipeline = pipeline("text-classification", model=config.EMOTION_MODEL_NAME, top_k=1)
nlp = spacy.load("en_core_web_sm")

# 2. 리액션 DB (Carl Rogers의 반영적 경청 기법 적용)
# GoEmotions의 모든 라벨(28개)에 대해 1:1 매칭됩니다.
# 질문은 배제하고, 공감과 반영 평서문만 사용합니다.

REACTION_DB = {
    # === 긍정적 감정 (Positive) ===
    "admiration": [ # 감탄, 존경
        "That is truly impressive.", 
        "You have my full respect for that.", 
        "That sounds absolutely wonderful."
    ],
    "amusement": [ # 즐거움
        "It is great to hear you laugh.", 
        "That is genuinely funny.", 
        "A little humor makes everything better."
    ],
    "approval": [ # 승인, 인정 
        "It sounds like you agree with that.",
        "That seems like a good call.",
        "I can hear your approval in that."
    ],
    "caring": [ # 보살핌 
        "That is very kind of you.",
        "It sounds like you care deeply about this.",
        "Your concern is very touching."
    ],
    "desire": [ # 욕망, 바람 
        "It sounds like you really want that.",
        "I can hear how much you wish for this.",
        "That sounds like a strong goal for you."
    ],
    "excitement": [ # 흥분
        "I can feel your energy and excitement.", 
        "That sounds like a thrilling moment.", 
        "It is wonderful to see you looking forward to this."
    ],
    "gratitude": [ # 감사
        "I appreciate your kind words.", 
        "It sounds like you are feeling very thankful.", 
        "Gratitude is such a powerful feeling."
    ],
    "joy": [ # 기쁨
        "I am so happy for you.", 
        "That sounds like a truly happy moment.", 
        "You deserve this happiness."
    ],
    "love": [ # 사랑
        "That sounds like a very special connection.", 
        "It is beautiful to feel that way.", 
        "Sending warmth your way."
    ],
    "optimism": [ # 낙관
        "It is good to keep a positive outlook.",
        "That sounds very hopeful.",
        "I like your positive spirit."
    ],
    "pride": [ # 자부심
        "You have every right to be proud.", 
        "That is a significant achievement.", 
        "It sounds like your hard work paid off."
    ],
    "relief": [ # 안도
        "That must be a huge weight off your shoulders.", 
        "It is good to know that is resolved.", 
        "I can imagine how relieved you feel."
    ],

    # === 부정적 감정 (Negative) ===
    "anger": [ # 분노
        "I can hear how frustrated you are.", 
        "It is completely understandable to be angry about that.", 
        "That sounds incredibly unfair."
    ],
    "annoyance": [ # 짜증
        "That sounds very bothering.", 
        "I can see how that would get on your nerves.", 
        "It is tough dealing with that kind of irritation."
    ],
    "disappointment": [ # 실망
        "It is really hard when things do not go as planned.", 
        "That sounds like a big letdown.", 
        "I can understand your disappointment."
    ],
    "disapproval": [ # 비난, 못마땅함 
        "It sounds like you are not a fan of that.",
        "I can hear your dissatisfaction.",
        "That definitely does not sit right with you."
    ],
    "disgust": [ # 혐오
        "That sounds really unpleasant.", 
        "I can hear how much that bothers you.", 
        "It is hard to deal with something so off-putting."
    ],
    "embarrassment": [ # 당황, 창피함
        "It happens to the best of us.",
        "That sounds like an awkward moment.",
        "I understand why you feel self-conscious."
    ],
    "fear": [ # 두려움
        "That sounds like a scary situation.", 
        "It is okay to feel afraid right now.", 
        "I am right here with you."
    ],
    "grief": [ # 비탄, 슬픔
        "There are no words for such a loss.", 
        "My thoughts are with you during this time.", 
        "Please take all the time you need."
    ],
    "nervousness": [ # 초조함 
        "It is natural to feel anxious about this.",
        "Take a deep breath. I am here.",
        "I can hear the tension in your words."
    ],
    "remorse": [ # 후회, 자책
        "Please be gentle with yourself.", 
        "We all make mistakes sometimes.", 
        "It sounds like you are being hard on yourself."
    ],
    "sadness": [ # 슬픔
        "I am so sorry you are going through this.", 
        "It sounds like a very heavy moment for you.", 
        "I hear the sadness in your words."
    ],

    # === 모호한/인지적 감정 (Ambiguous) ===
    "confusion": [ # 혼란
        "That does sound very puzzling.", 
        "It sounds like a complicated situation.", 
        "I can see why you are unsure."
    ],
    "curiosity": [ # 호기심
        "That sounds like an intriguing topic.", 
        "Your curiosity is very engaging.", 
        "That is definitely something worth exploring."
    ],
    "realization": [ # 깨달음
        "It sounds like you just had a breakthrough.", 
        "That is a powerful insight.", 
        "It is interesting how things clarify like that."
    ],
    "surprise": [ # 놀람
        "That is completely unexpected.", 
        "I can see why that shocked you.", 
        "That really came out of nowhere."
    ],
    "neutral": [ # 중립
        "I am listening.", 
        "I see.", 
        "I am following what you are saying."
    ]
}

# 기본 리액션 (혹시 모를 예외 처리)
DEFAULT_REACTIONS = ["I see.", "I hear you.", "Please go on."]

def analyze_and_react(text):
    # 1. 감정 분석
    raw_emotion = emotion_pipeline(text)[0][0]['label']
    
    # 2. 키워드 추출
    doc = nlp(text)
    keywords = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
    keyword = keywords[-1] if keywords else None
    
    # 3. 리액션 선택 (질문 없음)
    possible_reactions = REACTION_DB.get(raw_emotion, DEFAULT_REACTIONS)
    reaction = random.choice(possible_reactions)
    
    return {
        "emotion_label": raw_emotion,
        "reaction": reaction,
        "keyword": keyword
    }

if __name__ == "__main__":
    # 테스트 (모델에 있는 'approval' 테스트)
    test_text = "I think that's a great idea."
    result = analyze_and_react(test_text)
    print(f"입력: {test_text}")
    print(f"감정: {result['emotion_label']}")
    print(f"반응: {result['reaction']}")