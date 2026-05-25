# CREDO FastTrack Assets

This folder is the single navigation point for FastTrack research/runtime assets.
FastTrack datasets, trained intent models, and prebuilt audio bundles live here
as canonical files so the project root stays readable.

## Layout

- `datasets/`
  - Prepared GoEmotions 4-way emotion data.
  - Prepared SWDA coarse intent data.
- `models/`
  - SetFit SWDA intent classifiers used by FastTrack intent routing.
- `audio/`
  - Prebuilt Fish Speech persona reaction bundle.
  - Pure interjection + motion bundle.
  - Thinking bridge bundle such as `Let me think about it.`
  - Professor Jinsama callout bundle.

Runtime source files such as `config.py`, `fast_track.py`, and
`fast_track_engine.py` remain at the `AI_NPC_System/` root because importing
them from their existing module paths is simpler and less fragile. They are
listed in `INDEX.generated.json`, but they are not duplicated here.

## Refresh

After generating new audio, refresh this folder:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/collect_fasttrack_assets.py \
```

The script writes `INDEX.generated.json` with file counts and canonical paths.
