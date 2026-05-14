# YouTube Live Chat Bridge

This bridge prepares YouTube Live Chat as an input source for the CREDO
Open-LLM-VTuber runtime.

## Role

The bridge does not make the model understand the YouTube video screen. It reads
live chat text and forwards selected comments into Open-LLM-VTuber as normal
viewer text input.

Runtime path:

```text
YouTube Live Chat
  -> YouTube Data API
  -> AI_NPC_System/scripts/youtube_live_chat_bridge.py
  -> ws://localhost:12393/proxy-ws
  -> {"type": "text-input", "text": "..."}
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

Add author names when needed:

```bash
AI_NPC_System/scripts/run_youtube_live_chat_bridge.sh --video-id "YOUTUBE_VIDEO_ID" --include-author
```

## Notes

- `--ignore-first-page` prevents the avatar from reading old chat backlog when
  the bridge starts.
- `--send-gap` controls the minimum delay between forwarded comments.
- `--min-chars` filters extremely short messages.
- The bridge follows the polling interval suggested by YouTube's API response,
  with a local minimum interval to avoid excessive calls.

## Current Limitation

This is chat ingestion only. Screen mode sends image data to the backend, but the
current CREDO agent does not process images and `qwen2.5:7b` is not a vision
model. For screen understanding, the system needs a VLM path such as
Qwen2.5-VL or another OpenAI-compatible vision model.
