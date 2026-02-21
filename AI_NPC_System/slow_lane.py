# slow_lane.py
import config
from openai import OpenAI


async def generate_response(user_input, fast_reaction=None, strategy=None):
    """
    Slow Lane: Ollama 우선 -> 실패 시 Gemini fallback
    """
    system_prompt = (
        "You are a helpful and friendly NPC. "
        "Keep your response concise (within 2-3 sentences). "
        "Speak naturally like a human."
    )
    if fast_reaction:
        system_prompt += f" You already reacted with '{fast_reaction}'. Continue naturally."
    if strategy:
        system_prompt += f" Fast strategy was {strategy}; keep coherence with it."

    # 1) Local Ollama
    try:
        client = OpenAI(
            base_url=config.OLLAMA_URL,
            api_key="ollama",
            timeout=1.0,
        )
        response = client.chat.completions.create(
            model=config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.7,
        )
        print(f"🐢 [Slow Lane] ✅ Used Model: Local Ollama ({config.OLLAMA_MODEL})")
        return response.choices[0].message.content
    except Exception:
        pass

    # 2) Cloud Gemini (현재 비활성화)
    try:
        if not config.GEMINI_API_KEY:
            print("⚠️ [Slow Lane] Ollama 실패 + Gemini 비활성화 상태")
            return "..."

        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        full_prompt = f"{system_prompt}\n\nUser Input: {user_input}"
        response = await model.generate_content_async(full_prompt)
        print(f"🐢 [Slow Lane] ✅ Used Model: Cloud Gemini ({config.GEMINI_MODEL})")
        return response.text.strip()
    except Exception as e:
        print(f"❌ [Fatal Error] All models failed: {e}")
        return "..."
