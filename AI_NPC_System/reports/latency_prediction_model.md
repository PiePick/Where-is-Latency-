# CREDO Latency Prediction Model

Generated: 2026-05-17T22:28:52.165477+00:00
Source records: 204
TTS records: 114

## Fallback Coefficients

| Engine | Records | Intercept ms | ms/char | ms/tag |
| --- | ---: | ---: | ---: | ---: |
| default | 109 | 100.0 | 10.429 | 3000.0 |
| fish_speech | 78 | 181.567 | 314.999 | 0.0 |
| stylebert_vits2 | 17 | 100.0 | 5.0 | 0.179 |

## Stage Medians

| Stage | Median ms |
| --- | ---: |
| fast_track_analysis | 47.555 |
| fast_track_tts_or_cache | 41.722 |
| fish_speech_extreme_nonverbal_tts | 14369.349 |
| fish_speech_length_sweep_tts | 27600.584 |
| slow_track_llm | 744.387 |
| slow_track_tts | 120069.893 |
| turn_total | 121097.827 |
