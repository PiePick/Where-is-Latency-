"""TCP bridge for Unity or another local client.

The server sends two JSON packets per user message:
1. FastTrack packet for immediate reaction text.
2. SlowTrack packet for the deeper local LLM response.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import fast_lane
import slow_lane


HOST = "127.0.0.1"
PORT = 5000


def build_fast_packet(fast_result: dict[str, Any], total_latency: float) -> dict[str, Any]:
    """Convert FastTrack output into the TCP packet schema."""
    tts_text = fast_result.get("tts_text") or fast_result["reaction"]
    return {
        "schema_version": 2,
        "type": "fast",
        "emotion": fast_result["emotion_label"],
        "reaction": tts_text,
        "raw_reaction": fast_result["reaction"],
        "tts_text": tts_text,
        "plain_tts_text": fast_result.get("plain_tts_text", tts_text),
        "fish_speech_cue": fast_result.get("fish_speech_cue"),
        "echo_text": fast_result["echo_text"],
        "reaction_source": fast_result.get("reaction_source"),
        "bert_time": fast_result["bert_time"],
        "spacy_time": fast_result["spacy_time"],
        "strategy": fast_result.get("strategy"),
        "confidence_band": fast_result.get("confidence_band"),
        "top1": fast_result.get("top1"),
        "margin": fast_result.get("margin"),
        "entropy": fast_result.get("entropy"),
        "latency": f"{total_latency:.4f}s",
        "latency_ms": int(total_latency * 1000),
    }


def build_slow_packet(llm_reply: str, total_latency: float) -> dict[str, Any]:
    """Convert SlowTrack output into the TCP packet schema."""
    return {
        "schema_version": 2,
        "type": "slow",
        "npc_reply": llm_reply,
        "latency": f"{total_latency:.4f}s",
        "latency_ms": int(total_latency * 1000),
    }


def log_fast_result(fast_result: dict[str, Any], total_latency: float, tts_text: str) -> None:
    """Print compact timing and routing details for experiments."""
    print("   [Fast Log]")
    print(
        "   |- Time: "
        f"{total_latency:.4f}s "
        f"(BERT: {fast_result['bert_time']}, SpaCy: {fast_result['spacy_time']})"
    )
    print(f"   |- Emotion: {fast_result['emotion_label']} ({fast_result.get('confidence_band')})")
    print(
        "   |- Strategy: "
        f"{fast_result.get('strategy')} / "
        f"top1={fast_result.get('top1')} "
        f"margin={fast_result.get('margin')} "
        f"entropy={fast_result.get('entropy')}"
    )
    print(f"   |- Reaction: \"{tts_text}\"")
    if fast_result["echo_text"]:
        print(f"   `- Echoing:  \"{fast_result['echo_text']}\"")


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Process one TCP client until it disconnects."""
    addr = writer.get_extra_info("peername")
    print(f"[Server] Client connected: {addr}")

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            user_text = data.decode("utf-8").strip()
            if not user_text:
                continue

            print(f"\n User Input: {user_text}")
            print("-" * 30)

            # FastTrack runs first so TTS/UI can react before the local LLM finishes.
            start_time = time.time()
            fast_result = fast_lane.analyze_and_react(user_text)
            fast_latency = time.time() - start_time
            tts_text = fast_result.get("tts_text") or fast_result["reaction"]

            await send_json(writer, build_fast_packet(fast_result, fast_latency))
            log_fast_result(fast_result, fast_latency, tts_text)

            # SlowTrack follows with a more natural local LLM answer.
            print("[Slow Track] Local LLM generating...")
            llm_reply = await slow_lane.generate_response(
                user_text,
                tts_text,
                fast_result.get("strategy"),
            )

            latency_slow = time.time() - start_time
            await send_json(writer, build_slow_packet(llm_reply, latency_slow))
            print(f"[Slow Sent] {llm_reply} (Total: {latency_slow:.4f}s)")
            print("=" * 30)

    except Exception as exc:
        print(f"Connection Error: {exc}")
    finally:
        print(f"Client disconnected: {addr}")
        writer.close()
        await writer.wait_closed()


async def send_json(writer: asyncio.StreamWriter, data_dict: dict[str, Any]) -> None:
    """Send one newline-delimited JSON packet."""
    message = json.dumps(data_dict, ensure_ascii=False) + "\n"
    writer.write(message.encode("utf-8"))
    await writer.drain()


async def main() -> None:
    """Start the localhost TCP server."""
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"[Pipeline Server] running at {HOST}:{PORT}")
    print("   Waiting for Unity or local client...")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
