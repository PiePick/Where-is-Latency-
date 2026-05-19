# YouTube Live Chat Bridge

This bridge prepares YouTube Live Chat as an input source for the CREDO
Open-LLM-VTuber runtime.

## Role

The bridge does not make the model understand the YouTube video screen. It reads
live chat text and forwards selected comments into Open-LLM-VTuber as viewer
events with explicit role context. This matters because livestream input has
multiple speakers: the streamer/operator, the AI character, and viewers in chat.

Runtime path:

```text
YouTube Live Chat
  -> YouTube Data API
  -> AI_NPC_System/scripts/youtube_live_chat_bridge.py
  -> ws://localhost:12393/proxy-ws
  -> {"type": "text-input", "text": "[Live chat: YouTube] a viewer says: ..."}
  -> Open-LLM-VTuber conversation handler
  -> CREDO FastTrack / SlowTrack
```

## Requirements

- Open-LLM-VTuber server running at `http://localhost:12393`
- YouTube Data API key in `YOUTUBE_API_KEY`
- A currently live YouTube video ID, or a known `activeLiveChatId`

## Commands

Start Open-LLM-VTuber first:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

In another WSL terminal, start the YouTube chat bridge:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
export YOUTUBE_API_KEY="YOUR_YOUTUBE_DATA_API_KEY"
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id "YOUTUBE_VIDEO_ID" --ignore-first-page
```

If the active live chat ID is already known:

```bash
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --live-chat-id "ACTIVE_LIVE_CHAT_ID"
```

By default, forwarded comments are wrapped as role-context text so the model
knows the text came from a live viewer, not from the streamer or the AI itself:

```text
[Live chat: YouTube] a viewer says: "Nice dodge!" Respond as CREDO to the stream. Do not speak as the viewer.
```

Control author names when needed:

```bash
# Show the viewer display name in the prompt.
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id "YOUTUBE_VIDEO_ID" --author-mode display

# Keep names hidden but still mark the input as live chat.
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id "YOUTUBE_VIDEO_ID" --author-mode anonymous

# Backward-compatible alias for display names.
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id "YOUTUBE_VIDEO_ID" --include-author
```

Use `--legacy-raw-text` only for comparison tests against the old behavior.

## Notes

- `--ignore-first-page` prevents the avatar from reading old chat backlog when
  the bridge starts.
- `--send-gap` controls the minimum delay between forwarded comments.
- `--min-chars` filters extremely short messages.
- `--author-mode none|display|anonymous` controls whether viewer names are sent.
- `--source-label` changes the embedded source label if the bridge is reused for
  another live chat source.
- `--legacy-raw-text` disables role-context wrapping for ablation tests.
- The bridge follows the polling interval suggested by YouTube's API response,
  with a local minimum interval to avoid excessive calls.

## Current Limitation

This is chat ingestion only. Screen mode sends image data to the backend, but the
current CREDO agent does not process images and `qwen2.5:7b` is not a vision
model. For screen understanding, the system needs a VLM path such as
Qwen2.5-VL, Gemini, Claude, or another OpenAI-compatible vision model.

When that path is added, prefer a short rolling frame buffer instead of a single
screenshot. The Siro AI guide/video shows that several recent frames help the
model infer game state changes and player actions that are invisible in one
static image. Keep this separate from chat ingestion so text-only streaming still
runs on the low-latency path.
