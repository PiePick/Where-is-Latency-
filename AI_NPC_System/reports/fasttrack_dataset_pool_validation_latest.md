# FastTrack Dataset Pool Validation

- status: OK
- active text source: separated dataset pool
- pool: `/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`
- static persona manifest: disabled for active runtime
- personality_id: `professor_lab_maid_v1`

## Counts

- GoEmotions kept: `1131`
  - `POSITIVE`: `320`
  - `NEGATIVE`: `320`
  - `SURPRISE`: `171`
  - `NEUTRAL`: `320`
- SWDA kept: `1049`
  - `INFORM`: `320`
  - `ACKNOWLEDGE`: `158`
  - `DIRECTIVE`: `173`
  - `EXPRESSIVE`: `320`
  - `REJECT`: `78`

## Policy

- GoEmotions and SWDA are not merged into one manifest.
- GoEmotions is used only as the emotion evidence pool.
- SWDA is used only as the response-act evidence pool.
- SWDA `QUESTION` is excluded from FastTrack response acts.
- Runtime router v3 composes the short Professor's Lab Maid FastTrack line on demand.
