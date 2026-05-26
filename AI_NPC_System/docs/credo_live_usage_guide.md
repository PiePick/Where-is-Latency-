# CREDO Live Runtime Usage Guide

작성 기준: 2026-05-27 KST

## Current Status

- Active runtime target: Open-LLM-VTuber web UI + CREDO latency-cover agent.
- Language TTS: `stylebert_vits2` with `credo_voice_sample_en`.
- FastTrack language and SlowTrack both route through the active StyleBERT voice.
- Prebuilt StyleBERT audio is kept for manual short nonverbal interjections and matching Live2D motion.
- Current study controls are:
  - Six `Experiment cases` for immediate two-and-a-half-minute video recording.
  - Manual contextual mapping: `Grounded`, `Emotion only`, `Intent only`, `Neutral random`
  - Manual scheduling architecture: `Parallel`, `Serial`, `No FastTrack`
- Current browser modes are:
  - `YouTube Live`
  - `Virtual Broadcast`
  - `1:1 Chat`
- The server is not assumed to be running. Start or restart the stack before a live test.

## Quick Start

Run from WSL:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45
```

`--health-timeout 45` is optional now. The live launcher performs startup
warmup by default after health checks: one real StyleBERT synthesis, one local
LLM chat completion, and one Open-LLM-VTuber CREDO status request. For normal
live runs this shorter command is enough:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

Open the browser UI:

```text
http://127.0.0.1:12393
```

Check service health without starting the stack:

```bash
AI_NPC_System/scripts/run_credo_stack.sh --profile live --status
```

The `live` profile starts:

```text
stylebert -> local LLM -> Open-LLM-VTuber
```

Stop the stack with `Ctrl+C` in the terminal running `run_credo_stack.sh`.

## Browser Panel

The browser shows a `CREDO VTuber Mode` panel near the lower-left corner.

- `Hide` collapses the panel.
- `Reactions` opens manual prebuilt interjection + motion playback.
- The status line shows the selected mode, browser connection state, YouTube bridge state, mapping, scheduling, idle time, and idle turn count.

If the UI was already open before code changes, hard-refresh the page after restarting the stack.

## Runtime Modes

### 1:1 Chat

Use this for direct testing without a broadcast chat layout.

1. Select `1:1 Chat`.
2. Type a message in `Message to VTuber`.
3. Click `Send`.

The message is sent over the active browser WebSocket as normal text input.

### Virtual Broadcast

Use this for simulated live-stream chat.

1. Select `Virtual Broadcast`.
2. Click `Start Broadcast`.
3. Use `Viewer` and `Virtual live chat message` to enter fake viewer chat.
4. Click `Send`.

Expected UI behavior:

- A right-side `Virtual Broadcast Chat` dock appears.
- Sent virtual messages are appended like a Twitch-style chat log.
- While the avatar is speaking, chat is buffered and used at the next scheduling point.

Donation test:

1. Fill `Donor`, `Amount`, and `Donation message`.
2. Click `Donation`.

The donation is sent to `/credo/vtuber-mode/donation` and enters the reaction prompt as a donation event. It is also shown in the virtual chat dock.

### YouTube Live

Use this when real YouTube live chat should be the chat source.

1. Select `YouTube Live`.
2. Fill `Stream topic`.
3. Fill either `YouTube video ID` or `YouTube live chat ID`.
4. Fill `YouTube API key`, unless `YOUTUBE_API_KEY` is already set in the environment.
5. Click `Connect YouTube`.

Expected UI behavior:

- The virtual chat dock is hidden.
- Virtual chat input is disabled at the backend while YouTube mode is active.
- The local YouTube bridge forwards live chat through the Open-LLM-VTuber proxy path.

Manual stream continuation:

- Click `Monologue` to queue one short streamer-style line.
- Click `Disconnect` to stop VTuber mode and return to `1:1 Chat`.

More bridge details are in `AI_NPC_System/docs/youtube_live_chat_bridge.md`.

## Experiment Controls

For the primary study, use the `Experiment cases` buttons. A case applies
`run_id`, `factor`, the shared 150-second `scenario`, `component_mode`,
`selection_policy`, and `scheduling_mode` in one click.

| Case | Factor | Scenario | Component | Selection | Scheduling |
| --- | --- | --- | --- | --- | --- |
| `case_1_grounded_serial` | `contextual_mapping` | `shared_2m30` | `both` | `grounded` | `serial` |
| `case_2_emotion_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `emotion_only` | `serial` |
| `case_3_intent_only_serial` | `contextual_mapping` | `shared_2m30` | `both` | `response_act_only` | `serial` |
| `case_4_neutral_random_serial` | `contextual_mapping` | `shared_2m30` | `both` | `neutral_random` | `serial` |
| `case_5_grounded_parallel` | `scheduling_architecture` | `shared_2m30` | `both` | `grounded` | `parallel` |
| `case_6_slowtrack_only` | `scheduling_architecture` | `shared_2m30` | `none` | `none` | `serial` |

Manual factor buttons remain available for debugging, but participant runs
should use the case buttons so `experiment_run_id`, `experiment_factor`, and
`scenario` are logged.

### 150-Second Scenario Playback

All six cases use the same scenario: `shared_2m30`, shown in the panel as
`Shared 150-second scenario: Graduate School Survival Counseling Center`.

1. Click one `Experiment cases` button.
2. Confirm the scenario dropdown shows the shared 150-second scenario.
3. Click `Start Scenario`.
4. Start OBS recording.

`Start Scenario` automatically switches to `Virtual Broadcast`, sends
`/credo/vtuber-mode/start` with the current case values, sets the scenario
topic and `broadcast_direction`, triggers `/credo/vtuber-mode/monologue`, then
injects timed virtual chat and donation events for roughly two minutes and 30 seconds.
Reaction-style chat lines are sent through the Open-LLM-VTuber browser
WebSocket as `text-input` messages with `vtuber_live_chat_batch=true`, so they
are buffered even while a SlowTrack response is playing. Donation events use
HTTP POST `/credo/vtuber-mode/donation`, appear in a separate broadcast overlay
for about 20 seconds, play
`AI_NPC_System/fasttrack_assets/audio/Donatiion_SFX.mp3` through
`/credo/vtuber-mode/donation-sfx`, and are sent with `priority=true` so the
agent answers the donation before returning to buffered chat. `Stop Scenario`
cancels any remaining scheduled events.

### Contextual Mapping

These buttons change how FastTrack selects the short reaction text.

| UI label | Backend value | Meaning |
| --- | --- | --- |
| `Grounded` | `selection_policy=grounded`, `component_mode=both` | Uses emotion + response-act routing + separated dataset-pool retrieval. This is the default candidate. |
| `Emotion only` | `selection_policy=emotion_only`, `component_mode=both` | Uses emotion as the main mapping basis. |
| `Intent only` | `selection_policy=response_act_only`, `component_mode=both` | Uses response-act / intent transition as the main mapping basis. |
| `Neutral random` | `selection_policy=neutral_random`, `component_mode=both` | Study control: keeps FastTrack enabled but ignores emotion and intent grounding. |

### Scheduling Architecture

| UI label | Backend value | Meaning |
| --- | --- | --- |
| `Parallel` | `scheduling_mode=parallel` | Prepares the next SlowTrack/idle continuation while current audio is playing. |
| `Serial` | `component_mode=both`, `scheduling_mode=serial` | Keeps FastTrack reactions but waits until the current utterance ends before the next turn computation. |
| `No FastTrack` | `component_mode=none`, `scheduling_mode=serial` | Case 6 SlowTrack-only control. FastTrack is disabled, so contextual mapping is effectively `None`. |

Rows in `AI_NPC_System/latency_logs/module_events.csv` include these labels plus
`experiment_run_id`, `experiment_factor`, and `scenario`, so recorded sessions
can be grouped by preset.

## Broadcast Direction Prompt

Open `LLM Settings`, type the broadcast direction, then click `Apply`.
The same direction is sent with Virtual Broadcast, YouTube Live, manual
monologue, and donation events. It steers the topic and tone while preserving
the configured persona and language rules.

## Manual Reactions

Use this for motion/audio checks without waiting for model generation.

1. Click `Reactions`.
2. Choose an interjection/motion item.
3. Click `Play`.

The selected prebuilt nonverbal wav is sent with Live2D motion tags. This path is useful for checking avatar motion, expression actions, and audio playback.

## Logs And Reports

Useful files during a run:

```text
AI_NPC_System/runtime/logs/
AI_NPC_System/runtime/credo_stack_state.json
AI_NPC_System/latency_logs/module_events.csv
AI_NPC_System/reports/runtime_readiness_latest.md
CODEX_SHARED_WORKLOG.md
```

Use `CODEX_SHARED_WORKLOG.md` first when handing work to another Codex chat.

## Troubleshooting

- If `http://127.0.0.1:12393` does not open, the Open-LLM-VTuber server is not running. Start the stack again.
- If the overlay shows old labels or old route status, restart the stack and hard-refresh the browser. Running Python processes do not pick up route changes automatically.
- Browser automation often logs a mic/VAD permission warning. That is expected unless microphone permission is granted.
- A brief early `/undefined/undefined.model3.json` 404 has been observed before the configured Live2D model initializes. It is non-blocking if the avatar then loads normally.
- If StyleBERT startup is slow, increase `--warmup-timeout` for the first real
  synthesis request. `--health-timeout` only controls health probe waiting.
- Use `--no-warmup` only while debugging startup; it can make the first live
  utterance pay cold TTS/LLM latency.
- Do not modify `AI_NPC_System/VoiceSample/` or StyleBERT model assets while doing framework/runtime UI work.
