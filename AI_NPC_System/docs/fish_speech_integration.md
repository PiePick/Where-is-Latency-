# Fish Speech Integration Archive Note

작성 기준: 2026-05-27 KST

Fish Speech was evaluated for expressive reference-voice generation and
prebuilt FastTrack assets. It is no longer a live synthesis engine, and the
active short interjection bundle has been regenerated with StyleBERT-VITS2.

## Reason For Removal From Live Runtime

Measured live results included:

| Measurement | Result |
| --- | ---: |
| 20-word Fish SlowTrack synthesis | about `49.7 s` |
| corresponding completed turn | about `51.1 s` |
| earlier 26-word synthesis | about `68.7 s` |
| earlier 43-word synthesis | about `88.2 s` |

This latency cannot be usefully hidden by a short reaction in a conversational
broadcast loop. The default route therefore uses StyleBERT-VITS2 for language
FastTrack, SlowTrack, and short prebuilt interjection clips.

## Retained Historical Assets

The following may be kept only to reproduce prior quality/cache work:

```text
vendor/fish-speech/
vendor/fish-speech/references/
AI_NPC_System/tts_client.py
AI_NPC_System/tts_cues.py
AI_NPC_System/fasttrack_assets/audio/*/
```

The active language path no longer depends on a static persona manifest or its
generated Fish wav files. It uses the separated GoEmotions/SWDA dataset pool at
`fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json` for
runtime retrieval and persona-cover composition. The active interjection bundle is
`fasttrack_assets/audio/expressive_interjection_bundle/manifest.json`; its
`65` wav files are now StyleBERT-generated and required when interjection
FastTrack is enabled.

## Reproduction Only

If Fish quality experiments or nonverbal bundle regeneration are required, use
the bundle builders explicitly; do not add the Fish server to
`run_credo_stack.sh --profile live`.
Fish license/voice-consent requirements continue to apply to retained audio.

## Historical Fish Regeneration

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
source AI_NPC_System/project_config.sh
FISH_SPEECH_AUTO_PLAY=0 vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/build_interjection_audio_bundle.py \
  --engine fish_speech --synthesize --force --max-new-tokens 96
```

This is for reproducing historical Fish assets only. For the active bundle, use
StyleBERT:

```bash
python3 AI_NPC_System/scripts/build_interjection_audio_bundle.py \
  --engine stylebert_vits2 --synthesize --force
```
