# CREDO Runtime Readiness

- readiness: PARTIAL
- required_failed: 0
- optional_failed: 2
- warnings: 0

## Checks
| status | required | item | detail |
| --- | --- | --- | --- |
| OK | True | Open-LLM-VTuber runtime | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/open-llm-vtuber/.venv/bin/python |
| OK | True | Open-LLM module: edge_tts | importable |
| OK | True | SetFit optimized intent model | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/fasttrack_assets/models/setfit_swda_intent_minilm_optimized/model_head.pkl |
| OK | True | Hybrid reaction list | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/hybrid_reactions.json |
| SKIP | False | Interjection audio bundle | disabled by CREDO_NONVERBAL_FASTTRACK_ENABLED=0; live FastTrack uses speech + emotion motion |
| OK | False | Legacy expressive audio manifest | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/archive/legacy_audio/expressive_audio_pool/manifest.json |
| SKIP | False | FastTrack audio cache | disabled by FAST_TRACK_AUDIO_CACHE_ENABLED=0 |
| OK | True | FastTrack separated dataset pool | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json; go_emotions=385; swda=244; separated_sources=true |
| OK | True | SWDA intent transition matrix | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/reports/intent_transition_matrix_from_swda.json; cross-speaker pairs=78439; QUESTION->INFORM=0.472856, QUESTION->ACKNOWLEDGE=0.471845 |
| OK | True | Live2D motion groups | Ambiguous, AmbiguousTalk, Idle, Negative, NegativeTalk, Neutral, NeutralTalk, Positive, PositiveTalk, Talk |
| OK | True | python import: spacy | importable |
| OK | True | python import: transformers | importable |
| OK | False | python import: setfit | importable |
| OK | False | python import: faiss | importable |
| OK | False | python import: websockets | importable |
| OK | False | YouTube bridge dependency | websockets 16.0 |
| FAIL | False | Local LLM endpoint | unreachable: http://127.0.0.1:8001/v1/models (<urlopen error [Errno 111] Connection refused>) |
| FAIL | False | Open-LLM-VTuber web server | 127.0.0.1:12393 is closed or unreachable ([Errno 111] Connection refused) |
| OK | True | Prebuilt StyleBERT FastTrack manifest | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/fasttrack_assets/audio/prebuilt_stylebert_v1/manifest.json; usable_audio=1816/1816; go_emotions=917, swda=899; voice_model=credo_voice_sample_en |

## Interpretation
- READY: the full configured demo stack is reachable.
- PARTIAL: the core code/data exists, but at least one optional server or feature is not running.
- BLOCKED: a required model, dataset artifact, avatar asset, or Python runtime is missing.
