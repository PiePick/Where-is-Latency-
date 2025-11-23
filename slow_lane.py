# slow_lane.py
from openai import AsyncOpenAI
import config

# 비동기 클라이언트 생성
client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

async def generate_response(user_text, fast_reaction_text):
    # 시스템 프롬프트: Fast Lane이 이미 한 말을 반복하지 말라고 지시
    system_prompt = f"""
    You are a helpful NPC.
    Your reflex system has already reacted with: "{fast_reaction_text}".
    Do NOT repeat that reaction.
    Continue the conversation naturally based on the user's input.
    Keep your response concise (1-2 sentences).
    """

    try:
        # ★ 핵심: await를 써서 기다리는 동안 다른 작업을 허용함
        response = await client.chat.completions.create(
            model=config.GPT_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error: {str(e)}"