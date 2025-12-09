# slow_lane.py
import config
from openai import OpenAI
import google.generativeai as genai
import asyncio

async def generate_response(user_input, fast_reaction=None):
    """
    Slow Lane: '조용히' Ollama 시도 -> 실패 시 '조용히' Gemini 전환 -> 성공한 모델만 로그 출력
    """
    
    # 시스템 프롬프트 구성
    system_prompt = (
        "You are a helpful and friendly NPC. "
        "Keep your response concise (within 2-3 sentences). "
        "Speak naturally like a human."
    )
    if fast_reaction:
        system_prompt += f" You already reacted with '{fast_reaction}'. Continue naturally."

    # ==========================================
    # 🥇 시도 1: 로컬 Ollama (Silent Try)
    # ==========================================
    try:
        # 타임아웃 1.0초 설정: 안 켜져 있으면 1초 만에 바로 포기하고 넘어감
        client = OpenAI(
            base_url=config.OLLAMA_URL,
            api_key='ollama',
            timeout=1.0 
        )

        response = client.chat.completions.create(
            model=config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
        )
        
        # ★ 성공 시에만 로그 출력
        print(f"🐢 [Slow Lane] ✅ Used Model: Local Ollama ({config.OLLAMA_MODEL})")
        return response.choices[0].message.content

    except Exception:
        # 실패하면 아무 말도 안 하고(pass) 바로 다음으로 넘어감
        pass

    # ==========================================
    # 🥈 시도 2: 클라우드 Gemini (Silent Try)
    # ==========================================
    try:
        if not config.GEMINI_API_KEY:
            return "❌ Error: No Models Available."

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        full_prompt = f"{system_prompt}\n\nUser Input: {user_input}"
        
        # 비동기 호출
        response = await model.generate_content_async(full_prompt)
        
        # ★ 성공 시에만 로그 출력
        print(f"🐢 [Slow Lane] ✅ Used Model: Cloud Gemini ({config.GEMINI_MODEL})")
        return response.text.strip()

    except Exception as e:
        print(f"❌ [Fatal Error] All models failed: {e}")
        return "..."# slow_lane.py
import config
from openai import OpenAI
import google.generativeai as genai
import asyncio

async def generate_response(user_input, fast_reaction=None):
    """
    Slow Lane: '조용히' Ollama 시도 -> 실패 시 '조용히' Gemini 전환 -> 성공한 모델만 로그 출력
    """
    
    # 시스템 프롬프트 구성
    system_prompt = (
        "You are a helpful and friendly NPC. "
        "Keep your response concise (within 2-3 sentences). "
        "Speak naturally like a human."
    )
    if fast_reaction:
        system_prompt += f" You already reacted with '{fast_reaction}'. Continue naturally."

    # ==========================================
    # 🥇 시도 1: 로컬 Ollama (Silent Try)
    # ==========================================
    try:
        # 타임아웃 1.0초 설정: 안 켜져 있으면 1초 만에 바로 포기하고 넘어감
        client = OpenAI(
            base_url=config.OLLAMA_URL,
            api_key='ollama',
            timeout=1.0 
        )

        response = client.chat.completions.create(
            model=config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
        )
        
        # ★ 성공 시에만 로그 출력
        print(f"🐢 [Slow Lane] ✅ Used Model: Local Ollama ({config.OLLAMA_MODEL})")
        return response.choices[0].message.content

    except Exception:
        # 실패하면 아무 말도 안 하고(pass) 바로 다음으로 넘어감
        pass

    # ==========================================
    # 🥈 시도 2: 클라우드 Gemini (Silent Try)
    # ==========================================
    try:
        if not config.GEMINI_API_KEY:
            return "❌ Error: No Models Available."

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        full_prompt = f"{system_prompt}\n\nUser Input: {user_input}"
        
        # 비동기 호출
        response = await model.generate_content_async(full_prompt)
        
        # ★ 성공 시에만 로그 출력
        print(f"🐢 [Slow Lane] ✅ Used Model: Cloud Gemini ({config.GEMINI_MODEL})")
        return response.text.strip()

    except Exception as e:
        print(f"❌ [Fatal Error] All models failed: {e}")
        return "..."