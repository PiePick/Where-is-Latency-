# Reaction Sources

This folder keeps the raw source datasets and the current merged FastTrack
reaction artifacts in one place.

## Layout

```text
raw/daily_dialog/
  train.zip
  validation.zip
  test.zip
  README.md

raw/go_emotions/
  goemotions_1.csv
  goemotions_2.csv
  goemotions_3.csv
  README.md

merged/
  hybrid_reactions.json
  fish_speech_nonverbal_cues.json
  source_verification.json

scripts/
  build_reaction_dataset.py
  build_tts_cues.py
  verify_merged_sources.py

SHA256SUMS.txt
```

## Source Meaning

`hybrid_reactions.json` keeps the runtime data compact:

- `everyday` buckets are extracted from DailyDialog.
- `stream` buckets are extracted from GoEmotions raw text.

The file does not store row-level metadata because FastTrack needs a light
runtime list. To verify that the current merged strings exist in the downloaded
raw files, run:

```bash
python3 reaction_sources/scripts/verify_merged_sources.py
```

The latest verification summary is stored at:

```text
reaction_sources/merged/source_verification.json
```

All current merged reactions were found in their expected local raw source
dataset at bucket level.
