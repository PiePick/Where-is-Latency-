# AI NPC System

This folder contains the Python side of the FastTrack/SlowTrack VTuber NPC prototype.

## Runtime Files

```text
main.py                 Local text chat loop.
tcp_server.py           TCP server for Unity or another local client.
fast_track.py           Stable FastTrack facade.
fast_track_engine.py    DistilBERT, spaCy, reaction sampling, and TTS cue mixing.
slow_track.py           Local OpenAI-compatible LLM caller.
tts_client.py           Fish Speech HTTP TTS client and local playback helper.
tts_cues.py             Emotion-aware Fish Speech cue selector.
config.py               Environment-variable based runtime settings.
```

## Data Files

```text
hybrid_reactions.json               Final FastTrack reaction list.
fish_speech_nonverbal_cues.json     Fish Speech nonverbal cue buckets.
```

## Scripts

```text
scripts/build_reaction_dataset.py       Rebuild hybrid_reactions.json.
scripts/build_tts_cues.py               Rebuild fish_speech_nonverbal_cues.json.
scripts/benchmark_tts_latency.py        Measure Fish Speech /v1/tts latency.
scripts/start_fish_speech_server.sh     Start the local Fish Speech API server.
scripts/start_llama70b_judge_server.sh  Start the local Llama 70B judge server.
scripts/requirements.txt                Dataset/FastTrack build dependencies.
```

## Common Commands

```bash
python3 -m pip install -r AI_NPC_System/scripts/requirements.txt
python3 -m spacy download en_core_web_sm
FAST_TRACK_DEVICE=cpu python3 AI_NPC_System/main.py
python3 AI_NPC_System/tcp_server.py
AI_NPC_System/scripts/start_fish_speech_server.sh
```
