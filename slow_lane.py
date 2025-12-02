# slow_lane.py
import google.generativeai as genai
import config

# 1. Gemini 설정 (config.py에서 키를 가져옴)
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except AttributeError:
    print("config.py에 GEMINI_API_KEY가 없습니다.")

# 2. 모델 초기화 (비동기 지원)
model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)

async def generate_response(user_text, fast_reaction_text):
    """
    Gemini를 사용하여 사용자의 말에 대한 심층 답변을 생성합니다.
    (Fast Lane의 리액션을 중복하지 않도록 지시)
    """
    
    # 시스템 프롬프트 구성
    system_prompt = f"""
    You are an empathetic AI NPC engaged in a conversation.
    
    Current situation:
    - User said: "{user_text}"
    - You (Instinctively) reacted: "{fast_reaction_text}"
    
    Task:
    - Provide a natural follow-up response to deepen the conversation.
    - Do NOT repeat the instinctive reaction exactly.
    - Keep it concise (1 or 2 sentences).
    - Be supportive and warm.
    """

    try:
        # 3. 비동기 호출 (generate_content_async 사용)
        # 이 함수는 await를 통해 응답이 올 때까지 기다리지만, 서버 전체를 멈추지는 않습니다.
        response = await model.generate_content_async(system_prompt)
        
        # 결과 텍스트 반환
        return response.text.strip()
        
    except Exception as e:
        error_msg = f"Gemini Error: {str(e)}"
        print(f"{error_msg}")
        return "I am listening... (nodding)"