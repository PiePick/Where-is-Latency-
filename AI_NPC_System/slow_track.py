"""Slow Track response generation through local OpenAI-compatible LLMs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


def _system_prompt(fast_reaction: str | None, strategy: str | None) -> str:
    """Build the local LLM prompt for continuation after latency cover."""
    prompt = (
        "You are the SlowTrack continuation writer for an English-speaking AI VTuber. "
        "The viewer has already heard a short pre-generated latency-cover reaction, "
        "which may include a nonverbal voice tag such as [sigh], [chuckle], or [short pause]. "
        "Continue from that cover as if it was the first beat of the same response. "
        "Do not restart the conversation, do not greet the viewer, and do not repeat the cover line. "
        "Write 1 or 2 concise spoken sentences, usually under 35 words total. "
        "Keep the emotional stance consistent with the cover and the viewer's message. "
        "Use concrete empathy or curiosity instead of generic filler. "
        "Avoid markdown, stage directions, roleplay narration, and explanations. "
        "Fish Speech supports inline paralinguistic tags, but the latency cover already handles most nonverbal cues. "
        "Use at most one approved tag only when it is essential for continuity: "
        "[pause], [short pause], [emphasis], [inhale], [exhale], [chuckle], [laughing], "
        "[excited], [sigh], [soft sigh], [sad sigh], [whisper], [surprised], [shocked]. "
        "Do not output tags as labels; they must be part of the spoken TTS text only."
    )
    if fast_reaction:
        prompt += f" The already-played latency cover was: {fast_reaction!r}."
    if strategy:
        prompt += f" Cover selection metadata: {strategy}."
    return prompt


async def _call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float,
    user_input: str,
    fast_reaction: str | None,
    strategy: str | None,
) -> str:
    """Call an OpenAI-compatible local server with only stdlib HTTP."""
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt(fast_reaction, strategy)},
            {"role": "user", "content": user_input},
        ],
        "temperature": config.LOCAL_LLM_TEMPERATURE,
        "max_tokens": config.LOCAL_LLM_MAX_TOKENS,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            obj = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"local LLM server unreachable at {endpoint}: {exc}") from exc

    content = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content.strip() or "I hear you."


async def generate_response(user_input, fast_reaction=None, strategy=None):
    """Generate the Slow Track answer.

    Primary model is the higher-quality local Llama 70B AWQ vLLM server.
    The Qwen vLLM server is kept as a lighter local fallback.
    """

    primary = (
        config.LOCAL_LLM_BASE_URL,
        config.LOCAL_LLM_API_KEY,
        config.LOCAL_LLM_MODEL,
        config.LOCAL_LLM_TIMEOUT,
    )
    fallback = (
        config.FALLBACK_LOCAL_LLM_BASE_URL,
        config.FALLBACK_LOCAL_LLM_API_KEY,
        config.FALLBACK_LOCAL_LLM_MODEL,
        config.FALLBACK_LOCAL_LLM_TIMEOUT,
    )

    # Prefer the quality model, then fall back to the smaller local server.
    for base_url, api_key, model, timeout in (primary, fallback):
        try:
            reply = await _call_openai_compatible(
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
                user_input=user_input,
                fast_reaction=fast_reaction,
                strategy=strategy,
            )
            print(f"[Slow Track] Used local LLM: {model} ({base_url})")
            return reply
        except Exception as exc:
            print(f"[Slow Track] Local LLM failed: {model} ({base_url})")
            print(f"  error: {exc}")

    if config.GEMINI_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(config.GEMINI_MODEL)
            full_prompt = f"{_system_prompt(fast_reaction, strategy)}\n\nUser: {user_input}"
            response = await model.generate_content_async(full_prompt)
            print(f"[Slow Track] Used cloud Gemini: {config.GEMINI_MODEL}")
            return response.text.strip()
        except Exception as exc:
            print(f"[Slow Track] Gemini fallback failed: {exc}")

    return "I hear you."
