"""Slow Track response generation through local OpenAI-compatible LLMs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


def _system_prompt(fast_reaction: str | None, strategy: str | None) -> str:
    """Build the persona and Fish Speech cue policy sent to the local LLM."""
    prompt = (
        "You are a natural, friendly English-speaking VTuber NPC. "
        "Reply to the viewer in 2 concise sentences or fewer. "
        "Be emotionally coherent with the viewer's message. "
        "Do not repeat the exact fast reaction unless it is needed for coherence. "
        "Avoid long explanations, roleplay narration, and markdown. "
        "The TTS engine is Fish Speech and supports inline paralinguistic tags. "
        "You may use at most one short tag per sentence when it makes the voice more natural. "
        "Allowed tags: [sigh], [soft sigh], [relieved sigh], [excited], [excited inhale], "
        "[laughing], [chuckle], [delight], [surprised], [surprised gasp], [shocked], "
        "[pause], [short pause], [whisper], [low voice], [exhale], [inhale]. "
        "Use tags as vocal direction only; do not explain the tags."
    )
    if fast_reaction:
        prompt += f" The Fast Track already said: {fast_reaction!r}."
    if strategy:
        prompt += f" Fast Track strategy/source: {strategy}."
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
