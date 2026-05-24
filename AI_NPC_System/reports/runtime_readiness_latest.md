# CREDO Runtime Readiness

- readiness: PARTIAL
- required_failed: 0
- optional_failed: 3
- warnings: 0

## Checks
| status | required | item | detail |
| --- | --- | --- | --- |
| OK | True | Open-LLM-VTuber runtime | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/open-llm-vtuber/.venv/bin/python |
| OK | True | Fish Speech checkpoint | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/fish-speech/checkpoints/s2-pro |
| OK | True | Fish Speech reference voice | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/fish-speech/references/credo_eunice_english_v2 (3 pairs) |
| OK | True | SetFit optimized intent model | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/models/setfit_swda_intent_minilm_optimized/model_head.pkl |
| OK | True | Hybrid reaction list | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/hybrid_reactions.json |
| OK | False | Interjection audio bundle | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/expressive_interjection_bundle/manifest.json |
| OK | False | Legacy expressive audio manifest | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/archive/legacy_audio/expressive_audio_pool/manifest.json |
| SKIP | False | FastTrack audio cache | disabled by FAST_TRACK_AUDIO_CACHE_ENABLED=0 |
| OK | True | FastTrack persona bundle | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/persona_reaction_bundle_response_act_v1/manifest.json; reference=credo_eunice_english_v2; usable_items=600/600 |
| OK | True | SWDA intent transition matrix | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/reports/intent_transition_matrix_from_swda.json; cross-speaker pairs=78439; QUESTION->INFORM=0.472856, QUESTION->ACKNOWLEDGE=0.471845 |
| OK | True | Live2D motion groups | Ambiguous, AmbiguousTalk, Idle, Negative, NegativeTalk, Neutral, NeutralTalk, Positive, PositiveTalk, Talk |
| OK | True | python import: spacy | importable |
| OK | True | python import: transformers | importable |
| OK | False | python import: setfit | importable |
| OK | False | python import: faiss | importable |
| OK | False | python import: websockets | importable |
| OK | False | YouTube bridge dependency | websockets 16.0 |
| FAIL | False | Local LLM endpoint | unreachable: http://127.0.0.1:8001/v1/models (<urlopen error [Errno 1] Operation not permitted>) |
| FAIL | False | Fish Speech endpoint | unreachable: http://127.0.0.1:8080/v1/health (<urlopen error [Errno 1] Operation not permitted>) |
| FAIL | False | Open-LLM-VTuber web server | 127.0.0.1:12393 is closed or unreachable ([Errno 1] Operation not permitted) |
| SKIP | False | FastTrack realtime TTS | disabled by FAST_TRACK_TTS_MODE=cached_fish_bundle |

## Interpretation
- READY: the full configured demo stack is reachable.
- PARTIAL: the core code/data exists, but at least one optional server or feature is not running.
- BLOCKED: a required model, dataset artifact, avatar asset, or Python runtime is missing.
