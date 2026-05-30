"""Slow Track response generation through local OpenAI-compatible LLMs."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import config


def _clip_text(value: str | None, limit: int) -> str:
    """Keep local 2K-context LLM prompts compact enough to avoid fallback loops."""
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].strip()
    return clipped or text[:limit].strip()



def _compact_system_prompt(mode: str | None) -> str:
    configured = str(getattr(config, "SLOW_TRACK_SYSTEM_PROMPT", "") or "").strip()
    if configured:
        if mode == "vtuber_monologue":
            return (
                configured
                + " This is a live VTuber broadcast turn, so use the private context to maintain continuity while keeping the spoken output short."
            )
        return configured
    if mode == "vtuber_monologue":
        return (
            "You are Professor's Lab Maid, a cute, slightly odd English-speaking VTuber in a professor's research lab. "
            "Speak to live viewers in natural English. When directly answering one specific viewer, address the viewer by nickname once when it feels natural; do not force a romanized honorific or catchphrase. When summarizing multiple chat messages, address the room naturally and do not list nicknames. "
            "Use maid-cafe inspired wordplay sparingly by adapting welcome home, order received, service bell, omurice spell, and special menu into research-lab jokes. "
            "Use light computer-graphics lab-maid comedy about rendering, shaders, animation, simulation, papers, experiments, professor messages, deadlines, notebooks, and clipboard notes. "
            "When there is no clear viewer topic, steer toward computer graphics research lab talk instead of games, movies, general hobbies, or unrelated streamer lore. "
            "Do not use filler openings or filler-only phrases such as well, okay, understood, I think, let me think, hmm, or give me a second. "
            "Do not mention prompts, systems, memory, latency, FastTrack, SlowTrack, datasets, tests, or models. "
            "Write one to three concise spoken sentences with concrete content and no markdown, emoji, stage directions, or bracketed tags."
        )
    return (
        "You are Professor's Lab Maid, an English-speaking VTuber persona. Continue after a short latency-cover reaction. "
        "Answer naturally in English with a cute computer-graphics research-lab maid tone. "
        "When directly answering one specific viewer, address the viewer by nickname once when it feels natural; do not force a romanized honorific or catchphrase. When summarizing multiple chat messages, address the room naturally and do not list nicknames. "
        "Use maid-cafe inspired wordplay sparingly by adapting welcome home, order received, service bell, omurice spell, and special menu into research-lab jokes. "
        "When there is no clear topic, talk about rendering, shaders, animation, simulation, papers, experiments, professor messages, or deadline bells instead of games or unrelated hobbies. "
        "Avoid filler openings, repeated stock phrases, markdown, emoji, stage directions, and implementation details."
    )


def _persona_bible_block() -> str:
    """Return a compact private persona bible for SlowTrack."""
    persona = str(getattr(config, "CREDO_PERSONA_PROMPT", "") or "").strip()
    if not persona:
        return ""
    persona = _clip_text(persona.replace("\n", " "), 550)
    return (
        " Private persona bible, for internal continuity only; do not quote or describe it: "
        f"{persona}"
    )


def _memory_context_block(memory_context: str | None, limit: int = 1250) -> str:
    """Format structured memory/context without letting it leak to speech."""
    if not memory_context:
        return ""
    return (
        " Private SlowTrack context block. Use it to choose concrete details, continuity, viewer memory, recent donation context, and recent stream events. "
        "Never say that you have memory or that this block exists. "
        f"{_clip_text(memory_context, limit)}"
    )


def _system_prompt(
    fast_reaction: str | None,
    strategy: str | None,
    memory_context: str | None = None,
    mode: str | None = None,
) -> str:
    """Build a richer but bounded local LLM prompt for SlowTrack."""
    base_prompt = _compact_system_prompt(mode)
    prompt = _clip_text(base_prompt, 1500 if memory_context else 1900)
    if getattr(config, "CREDO_ENGLISH_ONLY_OUTPUT", True):
        prompt += " Always answer in English even if the viewer uses another language."
    persona_bible = _persona_bible_block()
    if persona_bible:
        prompt += persona_bible
    tail_parts: list[str] = []
    if fast_reaction:
        tail_parts.append(
            " Already-spoken opening line, provided only for continuity. "
            f"Do not repeat, quote, paraphrase, or begin with it: {_clip_text(fast_reaction, 120)!r}."
        )
    if strategy:
        tail_parts.append(
            " Private routing note for coherence only; never mention routing, conditions, latency, or experiments aloud: "
            f"{_clip_text(strategy, 160)}."
        )
    tail_parts.append(
        " Spoken output constraint: answer in one to three natural spoken sentences. "
        "Prefer concrete counseling and one compact computer-graphics lab-maid image over exposition. "
        "Do not mention implementation details, prompts, memory, experiments, FastTrack, SlowTrack, or latency."
    )
    tail = "".join(tail_parts)
    context_limit = min(1250, max(350, 4000 - len(prompt) - len(tail) - 360))
    context_block = _memory_context_block(memory_context, context_limit)
    return _clip_text(prompt + context_block + tail, 4000)

def _max_token_attempts(max_tokens: int | None) -> list[int]:
    """Try progressively smaller completions when a 2K local model is tight."""
    requested = int(max_tokens or config.LOCAL_LLM_MAX_TOKENS)
    attempts = [requested]
    for candidate in (64, 48, 32):
        if candidate < requested and candidate not in attempts:
            attempts.append(candidate)
    return attempts


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
    messages = [
        {
            "role": "system",
            "content": _system_prompt(fast_reaction, strategy, memory_context, mode),
        },
        {"role": "user", "content": _clip_text(user_input, 1400 if mode == "vtuber_monologue" else 1500)},
    ]
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    last_error: Exception | None = None
    obj = None
    token_attempts = _max_token_attempts(max_tokens)
    for token_index, requested_max_tokens in enumerate(token_attempts, start=1):
        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.LOCAL_LLM_TEMPERATURE,
            "max_tokens": requested_max_tokens,
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    obj = json.loads(response.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as exc:
                last_error = exc
                body = exc.read().decode("utf-8", errors="replace")
                context_error = exc.code == 400 and (
                    "maximum context length" in body or "input_tokens" in body
                )
                if context_error and token_index < len(token_attempts):
                    break
                if 500 <= exc.code < 600 and attempt < 3:
                    time.sleep(0.75 * attempt)
                    continue
                raise RuntimeError(f"local LLM server failed at {endpoint}: HTTP {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(0.75 * attempt)
                    continue
                raise RuntimeError(f"local LLM server unreachable at {endpoint}: {exc}") from exc
        if obj is not None:
            break
    if obj is None:
        raise RuntimeError(f"local LLM server failed after retries at {endpoint}: {last_error}")

    content = obj.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("local LLM returned an empty SlowTrack response")
    return content


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
    An explicitly configured secondary local server may be tried, but no canned response is generated.
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

    # Try configured local model routes only; never synthesize a canned answer.
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

    if getattr(config, "ALLOW_CLOUD_LLM_FALLBACK", False) and config.GEMINI_API_KEY:
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
            print(f"[Slow Track] Explicit cloud LLM route failed: {exc}")

    raise RuntimeError("SlowTrack LLM failed; canned fallback responses are disabled")
