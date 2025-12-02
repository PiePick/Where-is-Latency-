# check_models.py
import google.generativeai as genai
import config

# config.py에서 설정을 가져옴
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    print(f"API Key 확인됨 (앞 5자리): {config.GEMINI_API_KEY[:5]}...")
else:
    print("API Key가 설정되지 않았습니다.")
    exit()

print("\n🔍 사용 가능한 모델 목록을 조회합니다...")

try:
    available_models = []
    # generateContent 기능을 지원하는 모델만 필터링
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  {m.name}")
            available_models.append(m.name)

    if not available_models:
        print("\n 사용 가능한 모델이 없습니다. API 키 권한이나 지역 제한을 확인하세요.")
    else:
        print("\n 위 목록 중 하나를 골라 config.py에 복사해 넣으세요.")
        print("   (보통 'models/' 부분을 뺀 뒷부분만 써도 되지만, 안 되면 전체를 넣으세요)")

except Exception as e:
    print(f"\n 에러 발생: {e}")