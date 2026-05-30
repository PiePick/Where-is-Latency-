# TTS Engine Routing

작성 기준: 2026-05-26 KST

## Active Selection

현재 live 언어 경로는 FastTrack과 SlowTrack 모두 StyleBERT-VITS2
`credo_voice_sample_en`을 사용한다. Fish Speech는 실시간 언어 합성에서
제외한다. 순수 비언어 감탄사 wav는 보관/재현용 오프라인 산출물이며,
현재 live 재생 경로는 봉인되어 있다.

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/select_tts_engine.py stylebert --check
AI_NPC_System/scripts/select_tts_engine.py --status
```

Active values:

```text
FAST_TRACK_TTS_MODE=stylebert_vits2
FAST_TRACK_PREBUILT_ONLY=0
FAST_TRACK_KEYWORD_ECHO_ENABLED=0
STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en
STYLEBERT_VITS2_LANGUAGE=EN
STYLEBERT_VITS2_DEVICE=cuda
OPEN_LLM_VTUBER_TTS_MODEL=stylebert_vits2
OPEN_LLM_VTUBER_SLOW_TTS_MODE=open_llm
CREDO_INTERJECTION_AUDIO_BUNDLE_FILE=fasttrack_assets/audio/expressive_interjection_bundle/manifest.json
```

## Why StyleBERT-VITS2

| Candidate | Observed issue | Runtime decision |
| --- | --- | --- |
| Fish Speech | about 49.7 s for a 20-word SlowTrack line | exclude from live language path |
| CosyVoice2 | short sample about 4.0 s; longer bright sample about 27.7 s | exclude from primary live path |
| Piper | fast local baseline but weaker practical voice quality | optional legacy baseline |
| Edge TTS | low latency but cannot use the project voice sample pack | historical fallback/comparison |
| StyleBERT-VITS2 | selected VoiceSample fine-tune, warm path suitable for live turns | current default |

StyleBERT-VITS2 is not a perfect voice clone, but it is the current compromise
between local control, voice consistency, and live latency. It does not interpret
Fish style tags. Persona style belongs in text selection, prompt policy, and
Live2D motion metadata rather than bracketed TTS tags.

Standalone nonverbal FastTrack reactions are not active in the current runtime.
The generated bundle is kept only for archive/reproduction unless a future
experiment explicitly reopens interjection playback.

## Historical Engines

`fish`, `cosyvoice2`, `piper`, and `edge` selector entries may remain to
reproduce older measurements. They must be explicitly selected and are not the
current primary live configuration. Regenerating a nonverbal wav bundle is a
separate offline task, not part of the live participant path.
