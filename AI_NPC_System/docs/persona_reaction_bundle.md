# FastTrack Dataset Pool

작성 기준: 2026-05-29 KST

## Purpose

The active FastTrack language path no longer uses a prewritten 500/600-line
persona reaction manifest. The runtime keeps the two prepared source datasets
separate, filters them, searches them on demand, and composes a short
Professor's Lab Maid latency-cover line in real time.

```text
GoEmotions filtered pool -> emotion evidence
SWDA filtered pool       -> response-act evidence
router v3                -> runtime composition + StyleBERT realtime TTS
```

`QUESTION` is still allowed as an incoming user intent label, but it is
disallowed as a FastTrack response act because short cover questions often
conflict with the pending SlowTrack answer.

## Active Data Construction

1. `go_emotions_coarse.jsonl` supplies four emotion buckets:
   `POSITIVE`, `NEGATIVE`, `SURPRISE`, `NEUTRAL`.
2. `swda_intent_coarse.jsonl` supplies response-act evidence:
   `INFORM`, `ACKNOWLEDGE`, `DIRECTIVE`, `EXPRESSIVE`, `REJECT`.
3. SWDA `QUESTION` is filtered out for FastTrack output.
4. Source text with proper nouns, brands, dates, numbers, political/news
   references, profanity, sexual wording, greetings/closings, emoticons,
   laughter/filler strings, lowercase fragments, SWDA phone-call closings, or
   highly specific situations is rejected.
5. A local LLM quality pass can additionally remove candidates that are unclear
   without hidden context or unsuitable as standalone VTuber FastTrack speech.
6. Runtime router v3 retrieves from the relevant separated pool(s), records
   the source item IDs as metadata, and only then composes the spoken cover.

Current curated pool size after the 2026-05-29 filtering pass:

```text
GoEmotions: 385 items
  POSITIVE 141 / NEGATIVE 133 / SURPRISE 23 / NEUTRAL 88
SWDA: 244 items
  INFORM 199 / ACKNOWLEDGE 3 / DIRECTIVE 18 / EXPRESSIVE 14 / REJECT 10
```

## Runtime Lookup

```text
viewer chat
  -> GoEmotions-style emotion classification
  -> SWDA incoming intent classification
  -> SWDA transition matrix chooses non-question response act
  -> contextual mapping policy selects separated pool search
  -> runtime Professor's Lab Maid composition
  -> StyleBERT realtime TTS + Live2D motion
```

The primary study disables keyword echo. spaCy keywords may still be logged as
analysis metadata, but they should not create an extra utterance in the current
experiment.

## Canonical Files

```text
AI_NPC_System/fasttrack_assets/datasets/prepared_fasttrack_data/go_emotions_coarse.jsonl
AI_NPC_System/fasttrack_assets/datasets/prepared_fasttrack_data/swda_intent_coarse.jsonl
AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json
AI_NPC_System/scripts/build_fasttrack_dataset_pools.py
AI_NPC_System/scripts/filter_fasttrack_dataset_pool_with_local_llm.py
AI_NPC_System/scripts/validate_fasttrack_dataset_pool.py
```

Legacy persona manifests were removed from active documentation. If an old
manifest is needed for reproducibility, use `AI_NPC_System/archive/` or git
history rather than treating it as a live source.

## Regenerating Text Evidence

```bash
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/build_fasttrack_dataset_pools.py

vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/validate_fasttrack_dataset_pool.py
```

Do not start Fish Speech or synthesize language wav files for the active live
language FastTrack method.
