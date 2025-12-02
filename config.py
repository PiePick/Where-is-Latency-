# config.py

# 1. OpenAI 키는 이제 필요 없지만 에러 방지를 위해 남겨두거나 주석 처리
OPENAI_API_KEY = "sk-..." 

# 2. ★ 여기에 본인의 실제 Gemini API 키를 입력하세요!
# (Unity AIConfig.cs에서 쓰던 그 키를 복사해 오시면 됩니다)
GEMINI_API_KEY = "AIzaSy..." 

# 3. 모델 이름 설정
# Gemini 1.5 Flash가 속도와 성능 밸런스가 좋아 NPC용으로 적합합니다.
GEMINI_MODEL_NAME = "gemini-1.5-flash"
EMOTION_MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"