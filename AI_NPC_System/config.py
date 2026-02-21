# config.py
import os

# ==========================================
# 🔑 API 키 파일 경로 (자동 인식)
# ==========================================
# 사용자 홈 디렉토리(예: C:\Users\my coms)를 자동으로 찾아서 Desktop 경로와 합칩니다.
# 이제 경로 때문에 에러 날 일이 없습니다!
# KEY_FILE_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "gemini_key.txt")
#
# def load_api_key(filepath):
#     """파일이 있으면 읽고, 없으면 None 반환"""
#     print(f"📂 [Config] 키 파일 찾는 중... ({filepath})")
#
#     if not os.path.exists(filepath):
#         print("⚠️ 키 파일이 없습니다. (Ollama만 사용 가능)")
#         return None
#
#     try:
#         with open(filepath, "r", encoding="utf-8") as f:
#             key = f.read().strip()
#             print("Gemini API 키 로드 완료!")
#             return key
#     except Exception as e:
#         print(f"키 파일 읽기 실패: {e}")
#         return None

# Ollama 메인 운영: Gemini key 입력/로드 비활성화
GEMINI_API_KEY = None


# ==========================================
# 🤖 모델 설정 (Failover)
# ==========================================

# 1순위: 로컬 Ollama
OLLAMA_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = "gemma3:1b"  # 설치된 모델명 (llama3, mistral 등)

# 2순위: 클라우드 Gemini (백업용)
GEMINI_MODEL = "gemini-2.5-flash"

# 감정 분석 모델 (Fast Lane용)
EMOTION_MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"

# Fast Lane reaction DB 파일명 (AI_NPC_System 폴더 기준)
REACTION_DB_FILE = "reactions_v03.json"

# Slow lane 예상 지연(밀리초) - bridge 전략 힌트용
EXPECTED_SLOW_LANE_MS = 2800

# Fast Lane 전략 선택: 확률 샘플링 설정
ACTION_SAMPLING_ENABLED = True
ACTION_SAMPLING_TEMPERATURE = 0.9

# v01.2 Calibration (Temperature Scaling)
CALIBRATION_ENABLED = True
CALIBRATION_TEMPERATURE = 1.15
CALIBRATION_PARAM_FILE = "calibration_params_v012.json"