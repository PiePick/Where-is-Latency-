# CREDO Runtime Readiness

- readiness: READY
- required_failed: 0
- optional_failed: 0
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
| OK | True | FastTrack separated dataset pool | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json; go_emotions=1131; swda=1049; separated_sources=true |
| OK | True | SWDA intent transition matrix | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/reports/intent_transition_matrix_from_swda.json; cross-speaker pairs=78439; QUESTION->INFORM=0.472856, QUESTION->ACKNOWLEDGE=0.471845 |
| OK | True | Live2D motion groups | Ambiguous, AmbiguousTalk, Idle, Negative, NegativeTalk, Neutral, NeutralTalk, Positive, PositiveTalk, Talk |
| OK | True | python import: spacy | importable |
| OK | True | python import: transformers | importable |
| OK | False | python import: setfit | importable |
| OK | False | python import: faiss | importable |
| OK | False | python import: websockets | importable |
| OK | False | YouTube bridge dependency | websockets 16.0 |
| OK | False | Local LLM endpoint | http://127.0.0.1:8001/v1/models responded HTTP 200 in 13.6 ms |
| OK | False | Open-LLM-VTuber web server | 127.0.0.1:12393 accepts TCP connections |
| OK | False | Style-Bert-VITS2 repo | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2 |
| OK | False | Style-Bert-VITS2 runtime | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2/.venv/bin/python |
| OK | False | Style-Bert-VITS2 model assets | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2/model_assets |
| OK | False | Style-Bert-VITS2 explicit English model | credo_voice_sample_en (/mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en/config.json) |
| OK | False | Style-Bert-VITS2 device | cuda on CUDA_VISIBLE_DEVICES=0 |
| OK | False | Style-Bert-VITS2 endpoint | http://127.0.0.1:5000/docs responded HTTP 200 in 0.6 ms |

## Interpretation
- READY: the full configured demo stack is reachable.
- PARTIAL: the core code/data exists, but at least one optional server or feature is not running.
- BLOCKED: a required model, dataset artifact, avatar asset, or Python runtime is missing.
