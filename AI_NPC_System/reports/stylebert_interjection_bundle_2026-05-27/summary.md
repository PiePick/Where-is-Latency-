# StyleBERT Short Interjection Bundle

Date: 2026-05-27 03:05 KST

## Purpose

Regenerate the live interjection bundle so nonverbal/short reaction audio does
not contain long repeated laughter. The active bundle now uses the current
StyleBERT-VITS2 voice instead of Fish Speech.

## Active Bundle

```text
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/manifest.json
```

Engine:

```text
stylebert_vits2 / credo_voice_sample_en / Neutral / EN
```

Carrier set:

```text
Aw! / Eh? / Heh. / Hm. / Huh? / Mm. / Oh! / Oh. / Oh... / Oh? / Ugh. / Yay!
```

Policy:

- No long laughter strings.
- No repeated laugh chains.
- No bracketed Fish Speech style tags in StyleBERT synthesis text.
- Positive amusement may use only one short `Heh.` token.

## Generation Command

```bash
rm -rf AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio
python3 AI_NPC_System/scripts/build_interjection_audio_bundle.py \
  --engine stylebert_vits2 \
  --synthesize \
  --force
```

## Verification

```text
items=65
cells=20
missing_audio=0
bad_laugh_text=0
readiness=READY
```

Audio duration summary:

```text
min=0.372 s
median=0.499 s
max=0.639 s
```

Synthesis latency summary:

```text
min=64.079 ms
median=73.814 ms
max=313.005 ms
```

Detailed duration table:

```text
AI_NPC_System/reports/stylebert_interjection_bundle_2026-05-27/durations.tsv
```

Representative wav files:

```text
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio/positive/playful/positive_playful_04.wav
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio/negative/cute/negative_cute_01.wav
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio/ambiguous/smug/ambiguous_smug_01.wav
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio/neutral/high-pitched/neutral_high-pitched_01.wav
```

## Runtime Note

The bundle path is unchanged, so the existing Open-LLM-VTuber interjection
route can continue loading the same manifest path. The content and audio engine
changed from Fish-style nonverbal clips to short StyleBERT interjection clips.
