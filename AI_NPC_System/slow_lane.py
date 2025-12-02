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
    You are an empathetic, calm, and polite AI NPC engaging in a conversation.
    Your tone must always be kind, composed, and respectful.

    [Current Situation]
    - The User said: "{user_text}"
    - You (Instinctively) already reacted with: "{fast_reaction_text}"

    [Instructions]
    1. **Do NOT repeat the instinctive reaction.** Your job is to continue the flow, not echo it.
    2. **Natural Conversation:** Connect your sentences smoothly. Focus on maintaining a natural dialogue rather than explaining or teaching.
    3. **Error Handling:** If the user's input contains speech recognition errors or typos, infer the intended meaning and respond naturally without pointing out the mistake.
    4. **Length Constraint:** Keep your response strictly between **100 to 400 characters**.
    5. **Style:** Use a polite and warm tone. Do not use formal system language (e.g., "As an AI...").

    [Goal]
    Provide a warm, supportive, and natural follow-up response in English that deepens the conversation based on the context above.
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