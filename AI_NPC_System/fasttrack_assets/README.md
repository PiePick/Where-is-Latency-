# CREDO FastTrack Assets

This folder keeps the dataset and artifact evidence used by FastTrack.

## Layout

```text
datasets/  Prepared GoEmotions emotion and SWDA dialogue-act data.
models/    SetFit SWDA intent classifier used at runtime.
text/      Active separated filtered dataset pools.
audio/     Active StyleBERT nonverbal bundle.
```

## Current Runtime Use

The current StyleBERT realtime path reads
`text/professor_lab_maid_dataset_pool_v1/pool.json`. This is not a static
persona reaction manifest. It keeps the two prepared source datasets separate:

- GoEmotions: emotion evidence pool.
- SWDA: response-act evidence pool, with `QUESTION` excluded.

Runtime router v3 searches the relevant separated pool(s), records the selected
source items as metadata, and composes a short Professor's Lab Maid FastTrack
line on demand. The contextual mapping policies are:

- `grounded`: emotion + sampled response act
- `emotion_only`: emotion only
- `response_act_only`: SWDA-transitioned response act only
- `none`: FastTrack control condition

Legacy static text manifests are kept under `AI_NPC_System/archive/` if needed
for reproducibility. They are not the active language FastTrack source.

`audio/expressive_interjection_bundle/manifest.json` provides pure nonverbal
StyleBERT wav files. These files are played with motion without live
synthesis.

The trained models, filtered dataset pool, and active interjection wav bundle
must be retained for experimental reproducibility. Other generated wav folders
can be archived or removed after any required analysis is preserved.
