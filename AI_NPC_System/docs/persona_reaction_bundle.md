# Persona Reaction Bundle

This pipeline builds an offline FastTrack reaction bundle from the research
grid proposed by the advisor:

```text
4 emotions x 6 response intents x 5 style tags x 5 persona-filtered variants
= 600 short FastTrack reaction candidates
```

The local LLM is used offline only as a filter/re-writer over labeled dataset
seeds. Before the LLM sees any seed text, the generator removes examples that are
too specific for reusable live-chat reactions: proper names, brands, places,
dates, numbers, politics/news terms, URLs, handles, and event-specific details.
Each cell samples 30 same-emotion GoEmotions examples and 30 same-intent SWDA
examples from that filtered pool, pairs them, then asks the LLM to
select/rewrite 5 reactions that match the single dataset-grounded VTuber
persona. Fish Speech is then used offline to synthesize the selected sentences
with the configured CREDO reference voice. Runtime should retrieve from the
resulting manifest instead of calling the LLM or Fish Speech in the live
FastTrack path.

## Dimensions

```text
emotions: Positive, Negative, Ambiguous, Neutral
intents: QUESTION, INFORM, ACKNOWLEDGE, DIRECTIVE, EXPRESSIVE, REJECT
style_tags: high-pitched, playful, energetic, smug, cute
personality: dataset_grounded_playful_vtuber unless overridden
variants_per_cell: 5
```

The spoken sentence never contains bracketed style tags. The cell `style_tag`
represents one personality style axis, and synthesis expands that axis into a
small chain of Fish Speech prosody cues. Those cues are limited to pitch, energy,
pace, tension, and attitude. Nonverbal events such as laughs, giggles, sighs,
sobs, or gasps are excluded from manifest text and inline TTS tags; they should
be handled by separate timed motion/audio events. The generator also validates
LLM outputs with the same generic-context filter used for source seeds, so
proper nouns or event-specific reactions are rejected before entering the
manifest.

## Commands

Start the local LLM server first:

```bash
AI_NPC_System/scripts/start_local_llm_server.sh
```

Generate or refresh the text manifest:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --skip-existing
```

Start Fish Speech before audio synthesis:

```bash
AI_NPC_System/scripts/start_fish_speech_server.sh
```

Synthesize missing audio. This is resumable and can be stopped/restarted:

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --skip-existing --synthesize
```

For a small smoke test:

```bash
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --output-dir /tmp/credo_persona_bundle_test --limit-cells 1
```

```bash
FISH_SPEECH_AUTO_PLAY=0 \
vendor/open-llm-vtuber/.venv/bin/python AI_NPC_System/scripts/build_persona_reaction_bundle.py --output-dir /tmp/credo_persona_bundle_test --skip-existing --synthesize --audio-limit 2
```

## Output

```text
AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/manifest.json
AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/audio/<emotion>/<response_act>/<style_tag>/*.wav
```

The manifest is intentionally compact. Global metadata such as personality, style-tag definitions, dataset sources, LLM filter settings, and Fish Speech reference settings is stored once at the top level. Each cell stores its dimensions plus `item_ids`; each runtime item stores only item-specific data:

```text
id
cell_id
reaction
audio_path
```

`tts_text` is omitted when it is identical to `reaction`. Runtime loaders recover `emotion`, `response_act`, and `style_tag` from the owning cell to avoid duplicating the same dimensions across every item.

`style_tts_cue_chains` records how the five personality style axes expand into multiple Fish Speech prosody cues. The manifest records `use_memory_cache: off` for Fish Speech reference safety.

## Runtime Selection

Runtime does not treat the detected user intent as the response intent. It first
classifies the incoming user intent, then samples a response act from the SWDA
speaker-transition matrix before choosing a prebuilt audio item. This keeps the
FastTrack reaction probabilistic and conversational:

```text
viewer text
  -> emotion label
  -> user intent label
  -> sampled response act
  -> emotion + response act + style tag cell
  -> cached Fish Speech wav
```

This distinction matters for research validity. The bundle items are
dataset-grounded response candidates, not direct labels for the viewer's current
utterance.
