"""Slow Track response generation through local OpenAI-compatible LLMs."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import config


def _system_prompt(
    fast_reaction: str | None,
    strategy: str | None,
    memory_context: str | None = None,
    mode: str | None = None,
) -> str:
    """Build the local LLM prompt for continuation after latency cover."""
    if mode == "vtuber_monologue":
        prompt = config.CREDO_VTUBER_SYSTEM_PROMPT.strip()
    else:
        prompt = config.SLOW_TRACK_SYSTEM_PROMPT.strip()
    if getattr(config, "CREDO_ENGLISH_ONLY_OUTPUT", True):
        policy = getattr(config, "CREDO_LANGUAGE_POLICY", "").strip()
        if policy and policy not in prompt:
            prompt += f" {policy}"
    if memory_context:
        prompt += (
            " The following memory is external context, not a script. "
            "Use it only if it is relevant to the viewer's current message or stream context:\n"
            f"{memory_context}"
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
    max_tokens: int | None,
    user_input: str,
    fast_reaction: str | None,
    strategy: str | None,
    memory_context: str | None,
    mode: str | None,
) -> str:
    """Call an OpenAI-compatible local server with only stdlib HTTP."""
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": _system_prompt(fast_reaction, strategy, memory_context, mode),
            },
            {"role": "user", "content": user_input},
        ],
        "temperature": config.LOCAL_LLM_TEMPERATURE,
        "max_tokens": max_tokens or config.LOCAL_LLM_MAX_TOKENS,
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
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                obj = json.loads(response.read().decode("utf-8"))
                break
        except urllib.error.HTTPError as exc:
            last_error = exc
            if 500 <= exc.code < 600 and attempt < 3:
                time.sleep(0.75 * attempt)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"local LLM server failed at {endpoint}: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(0.75 * attempt)
                continue
            raise RuntimeError(f"local LLM server unreachable at {endpoint}: {exc}") from exc
    else:
        raise RuntimeError(f"local LLM server failed after retries at {endpoint}: {last_error}")

    content = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content.strip() or "I hear you."


async def generate_response(
    user_input,
    fast_reaction=None,
    strategy=None,
    memory_context=None,
    *,
    mode=None,
    max_tokens=None,
):
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
                max_tokens=max_tokens,
                user_input=user_input,
                fast_reaction=fast_reaction,
                strategy=strategy,
                memory_context=memory_context,
                mode=mode,
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
            full_prompt = (
                f"{_system_prompt(fast_reaction, strategy, memory_context, mode)}\n\n"
                f"User: {user_input}"
            )
            response = await model.generate_content_async(full_prompt)
            print(f"[Slow Track] Used cloud Gemini: {config.GEMINI_MODEL}")
            return response.text.strip()
        except Exception as exc:
            print(f"[Slow Track] Gemini fallback failed: {exc}")

    return "I hear you."
