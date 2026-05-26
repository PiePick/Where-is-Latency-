# StyleBERT-VITS2 VoiceSample Finetune Trial

Date: 2026-05-26

## Goal

Use the provided CREDO `VoiceSample` files as actual StyleBERT-VITS2 training data instead of `reference_audio_path`, because reference audio only changes style/prosody and does not clone the speaker timbre.

## Input Voice Samples

- `/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/VoiceSample/first try.m4a` - 22.175s
- `/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/VoiceSample/second try.m4a` - 14.827s
- `/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/VoiceSample/third try.m4a` - 13.205s

Total source audio: about 50.2s.

## Final Kept Model

- Inference model assets: `/mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en`
- Final checkpoint: `/mnt/c/Users/CGLAB/Desktop/CREDO/vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en/credo_voice_sample_en_e160_s323.safetensors`
- Required side files: `config.json`, `style_vectors.npy`
- Speaker name: `credo_voice_sample_en`
- Language: `EN`

The temporary training dataset and intermediate checkpoints were removed after final selection.

## Runtime Commands

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/start_stylebert_vits2_server.sh
```

Then run CREDO/Open-LLM-VTuber:

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Current CREDO defaults:

```bash
FAST_TRACK_TTS_MODE=stylebert_vits2
STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en
STYLEBERT_VITS2_LANGUAGE=EN
STYLEBERT_VITS2_DEVICE=cuda
STYLEBERT_VITS2_STYLE_WEIGHT=1.0
STYLEBERT_VITS2_SDP_RATIO=0.2
STYLEBERT_VITS2_NOISE=0.55
STYLEBERT_VITS2_NOISEW=0.7
STYLEBERT_VITS2_LENGTH=0.95
```

## Sample Files

Output directory:

`/mnt/c/Users/CGLAB/Desktop/CREDO/AI_NPC_System/reports/stylebert_vits2_voice_sample_finetune_2026-05-26/e160_s323`

| Sample | Text | Duration | Latency |
|---|---|---:|---:|
| `01_train_like_fun.wav` | Wow, today is going to be so much fun! | 2.879s | 11.701s cold |
| `02_train_like_day.wav` | Hey, how is your day going? | 1.869s | 0.176s |
| `03_short_react.wav` | Please don't tease me like that. | 1.846s | 0.162s |
| `04_keep_going.wav` | Let's keep going and enjoy every minute together! | 3.262s | 0.181s |
| `05_come_back.wav` | Will you come back next time? | 1.637s | 0.156s |
| `06_stream_line.wav` | You are finally here. Let's make this stream fun today. | 3.506s | 0.170s |

Warm synthesis mean, excluding first cold request: 0.169s.

## Notes

- This is a real finetune from the provided samples, not style-reference inference.
- The dataset is extremely small, so the model may overfit training-like phrases and may still pronounce unseen text inconsistently.
- `reference_audio_path` should not be used as evidence of voice cloning in StyleBERT-VITS2; it mainly affects speaking style.
- For Open-LLM-VTuber / CREDO testing, use `FAST_TRACK_TTS_MODE=stylebert_vits2` and StyleBERT `model_name=credo_voice_sample_en`, `speaker_name=credo_voice_sample_en`, `language=EN`.
