# CREDO Runtime Readiness

- readiness: PARTIAL
- required_failed: 0
- optional_failed: 1
- warnings: 0

## Checks
| status | required | item | detail |
| --- | --- | --- | --- |
| OK | True | Open-LLM-VTuber runtime | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/open-llm-vtuber/.venv/bin/python |
| OK | True | Fish Speech checkpoint | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/fish-speech/checkpoints/s2-pro |
| OK | True | Fish Speech reference voice | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/fish-speech/references/credo_voice_sample (4 pairs) |
| OK | True | SetFit optimized intent model | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/models/setfit_swda_intent_minilm_optimized/model_head.pkl |
| OK | True | Hybrid reaction list | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/hybrid_reactions.json |
| OK | False | Expressive audio manifest | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/expressive_audio_pool/manifest.json |
| SKIP | False | FastTrack audio cache | disabled by FAST_TRACK_AUDIO_CACHE_ENABLED=0 |
| OK | True | SWDA intent transition matrix | /mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/reports/intent_transition_matrix_from_swda.json; cross-speaker pairs=78439; QUESTION->INFORM=0.472856, QUESTION->ACKNOWLEDGE=0.471845 |
| OK | True | Live2D motion groups | Ambiguous, Idle, Negative, Neutral, Positive, Talk |
| OK | True | python import: spacy | importable |
| OK | True | python import: transformers | importable |
| OK | False | python import: setfit | importable |
| OK | False | python import: faiss | importable |
| OK | False | python import: websockets | importable |
| OK | False | YouTube bridge dependency | websockets 16.0 |
| OK | False | Local LLM endpoint | http://127.0.0.1:8001/v1/models responded HTTP 200 in 15.5 ms |
| OK | False | Fish Speech endpoint | http://127.0.0.1:8080/v1/health responded HTTP 200 in 1.2 ms |
| FAIL | False | Open-LLM-VTuber web server | 127.0.0.1:12393 is closed or unreachable ([Errno 111] Connection refused) |
| OK | True | Piper FastTrack executable | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/piper-tts/.venv/bin/piper |
| OK | True | Piper FastTrack English voice model | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/piper-tts/voices/en_US-lessac-medium.onnx |
| OK | True | Piper FastTrack voice config | /mnt/c/Users/CGLAB/Desktop/CREDO/vendor/piper-tts/voices/en_US-lessac-medium.onnx.json |
| OK | False | Piper FastTrack endpoint | http://127.0.0.1:5001/health responded HTTP 200 in 0.6 ms |
| SKIP | False | Style-Bert-VITS2 | legacy backend disabled by FAST_TRACK_TTS_MODE=piper_tts |

## Interpretation
- READY: the full configured demo stack is reachable.
- PARTIAL: the core code/data exists, but at least one optional server or feature is not running.
- BLOCKED: a required model, dataset artifact, avatar asset, or Python runtime is missing.
