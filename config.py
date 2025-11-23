# config.py

# OpenAI API 키 (따옴표 안에 본인 키 입력)
OPENAI_API_KEY = "" 

# 사용할 모델 (가격표 보고 결정한 것)
# 실제 API에 'gpt-5-mini'가 있다면 그대로 쓰시고, 안 되면 'gpt-4o-mini' 추천
GPT_MODEL_NAME = "gpt-5-mini" 

# 감정 분석 모델 (DistilBERT GoEmotions)
EMOTION_MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"