#!/usr/bin/env python3
"""Forward YouTube Live Chat messages into Open-LLM-VTuber.

The bridge uses the official YouTube Data API and sends each selected chat
message to Open-LLM-VTuber's proxy websocket as:

    {"type": "text-input", "text": "..."}

This keeps YouTube chat as an external input source while preserving the CREDO
FastTrack/SlowTrack pipeline unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import websockets
except ImportError as exc:  # pragma: no cover - runtime guidance
    raise SystemExit(
        "Missing dependency: websockets. Run this with vendor/open-llm-vtuber/.venv/bin/python "
        "or install websockets in the active Python environment."
    ) from exc


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
DEFAULT_PROXY_URL = os.getenv("YOUTUBE_CHAT_PROXY_URL", "ws://localhost:12393/proxy-ws")
DEFAULT_SOURCE_LABEL = os.getenv("YOUTUBE_CHAT_SOURCE_LABEL", "YouTube")
DEFAULT_AUTHOR_MODE = os.getenv("YOUTUBE_CHAT_AUTHOR_MODE", "none")


@dataclass(frozen=True)
class ChatMessage:
    """One normalized YouTube live chat message."""

    message_id: str
    author: str
    text: str
    published_at: str


class YouTubeAPIError(RuntimeError):
    """Raised when the YouTube API returns an unusable response."""


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    """Load a JSON object with a useful error message."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise YouTubeAPIError(f"YouTube API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise YouTubeAPIError(f"YouTube API unreachable: {exc}") from exc


def resolve_live_chat_id(
    *,
    api_key: str,
    video_id: str,
    timeout: float,
) -> str:
    """Resolve activeLiveChatId from a live video ID."""
    query = urllib.parse.urlencode(
        {
            "part": "liveStreamingDetails",
            "id": video_id,
            "key": api_key,
        }
    )
    data = _get_json(f"{YOUTUBE_API}/videos?{query}", timeout=timeout)
    items = data.get("items") or []
    if not items:
        raise YouTubeAPIError(f"No video found for id={video_id!r}.")

    details = items[0].get("liveStreamingDetails") or {}
    live_chat_id = details.get("activeLiveChatId")
    if not live_chat_id:
        raise YouTubeAPIError(
            "The video has no activeLiveChatId. The stream may be offline, not live, "
            "or live chat may be disabled."
        )
    return live_chat_id


def fetch_chat_page(
    *,
    api_key: str,
    live_chat_id: str,
    page_token: str | None,
    timeout: float,
) -> tuple[list[ChatMessage], str | None, float]:
    """Fetch one page of chat messages and the next polling interval."""
    params = {
        "part": "id,snippet,authorDetails",
        "liveChatId": live_chat_id,
        "key": api_key,
    }
    if page_token:
        params["pageToken"] = page_token

    data = _get_json(
        f"{YOUTUBE_API}/liveChat/messages?{urllib.parse.urlencode(params)}",
        timeout=timeout,
    )
    interval_ms = data.get("pollingIntervalMillis", 5000)
    next_page_token = data.get("nextPageToken")

    messages: list[ChatMessage] = []
    for item in data.get("items") or []:
        snippet = item.get("snippet") or {}
        author = item.get("authorDetails") or {}
        text = (snippet.get("displayMessage") or "").strip()
        if not text:
            continue
        messages.append(
            ChatMessage(
                message_id=str(item.get("id") or ""),
                author=str(author.get("displayName") or "viewer"),
                text=text,
                published_at=str(snippet.get("publishedAt") or ""),
            )
        )
    return messages, next_page_token, max(float(interval_ms) / 1000.0, 1.0)


def format_for_vtuber(
    message: ChatMessage,
    *,
    author_mode: str,
    source_label: str,
    role_context: bool,
) -> str:
    """Format a chat message as a VTuber text input.

    The CREDO adapter can only send a normal text-input event through the
    Open-LLM-VTuber proxy, so role context is embedded in the text itself.
    This avoids the model confusing a live viewer comment with its own speech.
    """
    text = message.text.strip()
    if not role_context:
        if author_mode == "display":
            return f"Viewer {message.author} says: {text}"
        if author_mode == "anonymous":
            return f"Viewer says: {text}"
        return text

    if author_mode == "display":
        speaker = f'viewer "{message.author}"'
    elif author_mode == "anonymous":
        speaker = "an anonymous viewer"
    else:
        speaker = "a viewer"

    return (
        f"[Live chat: {source_label}] {speaker} says: \"{text}\" "
        f"Respond as CREDO to the stream. Do not speak as the viewer."
    )


async def send_to_proxy(proxy_url: str, text: str, *, metadata: dict[str, Any] | None = None) -> None:
    """Send one text-input event to Open-LLM-VTuber's proxy websocket."""
    async with websockets.connect(proxy_url, ping_interval=20, ping_timeout=10) as ws:
        payload = {"type": "text-input", "text": text}
        if metadata:
            payload["metadata"] = metadata
        await ws.send(json.dumps(payload))


def format_batch_for_vtuber(
    messages: list[ChatMessage],
    *,
    author_mode: str,
    source_label: str,
    max_items: int,
) -> str:
    """Format several live chat messages as one VTuber reading segment."""
    selected = messages[-max(1, max_items):]
    lines = []
    for index, message in enumerate(selected, start=1):
        text = message.text.strip()
        if not text:
            continue
        if author_mode == "display":
            speaker = f'{message.author}'
        elif author_mode == "anonymous":
            speaker = "anonymous viewer"
        else:
            speaker = f"viewer {index}"
        lines.append(f"- {speaker}: {text}")

    joined = "\n".join(lines)
    return (
        f"[Live chat batch: {source_label}]\n"
        f"Recent chat messages:\n{joined}\n"
        "Respond as CREDO to the overall stream context, not line-by-line. "
        "Pick one or two representative points, acknowledge the room naturally, and keep the stream moving."
    )


async def flush_chat_batch(
    *,
    pending: list[ChatMessage],
    proxy_url: str,
    author_mode: str,
    source_label: str,
    max_batch: int,
) -> None:
    """Send the current chat batch if it has any messages."""
    if not pending:
        return
    text = format_batch_for_vtuber(
        pending,
        author_mode=author_mode,
        source_label=source_label,
        max_items=max_batch,
    )
    print(f"[{time.strftime('%H:%M:%S')}] forwarding {len(pending[-max_batch:])} chat messages as one batch")
    await send_to_proxy(
        proxy_url,
        text,
        metadata={
            "vtuber_mode": True,
            "vtuber_live_chat_batch": True,
            "source": "youtube_live_chat",
        },
    )
    pending.clear()


async def run_bridge(args: argparse.Namespace) -> None:
    """Main polling loop."""
    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("Missing YouTube API key. Set YOUTUBE_API_KEY or pass --api-key.")

    live_chat_id = args.live_chat_id
    if not live_chat_id:
        if not args.video_id:
            raise SystemExit("Pass --video-id or --live-chat-id.")
        live_chat_id = resolve_live_chat_id(
            api_key=api_key,
            video_id=args.video_id,
            timeout=args.timeout,
        )

    print(f"YouTube live chat id: {live_chat_id}")
    print(f"Open-LLM-VTuber proxy: {args.proxy_url}")

    stop = asyncio.Event()

    def _stop(*_unused: object) -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _stop)
        except ValueError:
            pass

    seen: set[str] = set()
    next_page_token: str | None = None
    poll_interval = args.min_interval
    first_page = True
    pending_batch: list[ChatMessage] = []
    last_batch_sent_at = time.monotonic()

    while not stop.is_set():
        try:
            messages, next_page_token, suggested_interval = fetch_chat_page(
                api_key=api_key,
                live_chat_id=live_chat_id,
                page_token=next_page_token,
                timeout=args.timeout,
            )
            poll_interval = max(suggested_interval, args.min_interval)
            skip_page = args.ignore_first_page and first_page
            first_page = False

            for message in messages:
                if message.message_id in seen:
                    continue
                seen.add(message.message_id)
                if len(seen) > args.max_seen:
                    seen = set(list(seen)[-args.max_seen // 2 :])

                if len(message.text) < args.min_chars:
                    continue
                if skip_page:
                    continue

                author_mode = "display" if args.include_author else args.author_mode
                print(f"[{time.strftime('%H:%M:%S')}] {message.author}: {message.text}")
                if args.batch_window <= 0 or args.legacy_raw_text:
                    text = format_for_vtuber(
                        message,
                        author_mode=author_mode,
                        source_label=args.source_label,
                        role_context=not args.legacy_raw_text,
                    )
                    await send_to_proxy(args.proxy_url, text)
                    await asyncio.sleep(args.send_gap)
                    continue

                pending_batch.append(message)
                if len(pending_batch) >= args.max_batch:
                    await flush_chat_batch(
                        pending=pending_batch,
                        proxy_url=args.proxy_url,
                        author_mode=author_mode,
                        source_label=args.source_label,
                        max_batch=args.max_batch,
                    )
                    last_batch_sent_at = time.monotonic()

            if (
                args.batch_window > 0
                and pending_batch
                and time.monotonic() - last_batch_sent_at >= args.batch_window
            ):
                author_mode = "display" if args.include_author else args.author_mode
                await flush_chat_batch(
                    pending=pending_batch,
                    proxy_url=args.proxy_url,
                    author_mode=author_mode,
                    source_label=args.source_label,
                    max_batch=args.max_batch,
                )
                last_batch_sent_at = time.monotonic()

        except Exception as exc:
            print(f"Bridge warning: {exc}", file=sys.stderr)
            poll_interval = max(args.error_interval, args.min_interval)

        try:
            await asyncio.wait_for(stop.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forward YouTube Live Chat to Open-LLM-VTuber.")
    parser.add_argument("--api-key", default="", help="YouTube Data API key. Defaults to YOUTUBE_API_KEY.")
    parser.add_argument("--video-id", default="", help="YouTube live video ID.")
    parser.add_argument("--live-chat-id", default="", help="Known activeLiveChatId.")
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL, help="Open-LLM-VTuber proxy websocket URL.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout.")
    parser.add_argument("--min-interval", type=float, default=float(os.getenv("YOUTUBE_CHAT_MIN_INTERVAL", "2.0")), help="Minimum polling interval.")
    parser.add_argument("--error-interval", type=float, default=float(os.getenv("YOUTUBE_CHAT_ERROR_INTERVAL", "10.0")), help="Polling interval after an error.")
    parser.add_argument("--send-gap", type=float, default=float(os.getenv("YOUTUBE_CHAT_SEND_GAP", "1.0")), help="Delay between forwarded messages.")
    parser.add_argument("--batch-window", type=float, default=float(os.getenv("YOUTUBE_CHAT_BATCH_WINDOW", "8.0")), help="Seconds to collect live chat before forwarding one batch. Set 0 for one-by-one forwarding.")
    parser.add_argument("--max-batch", type=int, default=int(os.getenv("YOUTUBE_CHAT_MAX_BATCH", "8")), help="Maximum chat messages per forwarded batch.")
    parser.add_argument("--min-chars", type=int, default=int(os.getenv("YOUTUBE_CHAT_MIN_CHARS", "2")), help="Ignore messages shorter than this.")
    parser.add_argument("--max-seen", type=int, default=2000, help="Deduplication window size.")
    parser.add_argument(
        "--author-mode",
        choices=("none", "display", "anonymous"),
        default=DEFAULT_AUTHOR_MODE,
        help="How viewer names are included in text sent to VTuber. Defaults to YOUTUBE_CHAT_AUTHOR_MODE or none.",
    )
    parser.add_argument(
        "--source-label",
        default=DEFAULT_SOURCE_LABEL,
        help="Source label embedded in role-context text. Defaults to YOUTUBE_CHAT_SOURCE_LABEL or YouTube.",
    )
    parser.add_argument(
        "--legacy-raw-text",
        action="store_true",
        help="Send old plain chat text format without role context.",
    )
    parser.add_argument("--include-author", action="store_true", help="Backward-compatible alias for --author-mode display.")
    parser.add_argument(
        "--ignore-first-page",
        action="store_true",
        help="Skip messages returned by the first API page so old chat backlog is not spoken.",
    )
    return parser.parse_args()


def main() -> None:
    asyncio.run(run_bridge(parse_args()))


if __name__ == "__main__":
    main()
