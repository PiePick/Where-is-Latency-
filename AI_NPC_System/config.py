# config.py
import os

# ==========================================
# 🔑 API 키 파일 경로 설정
# ==========================================
# 1. 방금 만든 txt 파일의 '전체 경로'를 아래 따옴표 안에 적으세요.
# (주의: 윈도우 경로라도 역슬래시(\) 대신 슬래시(/)를 쓰는 게 에러가 없습니다.)
# 예시: "C:/Users/Public/gemini_key.txt"
KEY_FILE_PATH = "C:/Users/my coms/Desktop/gemini_key.txt" 


def load_api_key(filepath):
    """지정된 경로의 텍스트 파일을 읽어 API 키를 반환하는 함수"""
    print(f"[Config] 키 파일 로딩 중... ({filepath})")
    
    if not os.path.exists(filepath):
        print(f"[Error] 파일을 찾을 수 없습니다! 경로를 확인해주세요: {filepath}")
        return None
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            # 파일 내용을 읽고 앞뒤 공백/줄바꿈을 제거(.strip)
            key = f.read().strip()
            
        if not key:
            print("[Warning] 파일이 비어 있습니다.")
            return None
            
        print("[Config] API 키 로드 완료!")
        return key
        
    except Exception as e:
        print(f"[Error] 키 파일을 읽는 중 오류 발생: {e}")
        return None

# ==========================================
# ⚙️ 모델 설정
# ==========================================

# 파일에서 키를 읽어와 변수에 저장
GEMINI_API_KEY = load_api_key(KEY_FILE_PATH)

# 사용할 모델 이름
GEMINI_MODEL_NAME = "gemini-2.5-flash"
EMOTION_MODEL_NAME = "joeddav/distilbert-base-uncased-go-emotions-student"