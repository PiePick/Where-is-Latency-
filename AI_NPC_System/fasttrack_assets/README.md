# CREDO FastTrack Assets

This folder is the single navigation point for FastTrack research/runtime assets.
The actual runtime files stay in their original locations, and this folder links
to them so existing config paths do not break.

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
- `runtime/`
  - FastTrack runtime config and routing helpers.

## Refresh

After generating new audio, refresh this folder:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/collect_fasttrack_assets.py \
  --force
```

The script creates symlinks by default and writes `INDEX.generated.json` with
counts and source paths.
