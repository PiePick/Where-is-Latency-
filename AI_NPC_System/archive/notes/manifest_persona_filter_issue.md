# manifest.json Persona Filtering Issue

Status: resolved in the compact persona reaction bundle manifest.

Current behavior:
- The bundle has one top-level `personality_id`: `playful_shark_vtuber`.
- The personality prompt is stored once at the top level, not repeated per item.
- Each of the 120 emotion/intent/style cells has exactly 5 selected reaction item ids.
- Runtime items no longer duplicate persona, style instructions, dataset sources, or cue metadata.

Verification target:
- `cells`: 120
- `items`: 600
- every cell `item_ids`: 5
- per-item duplicated persona fields: absent
