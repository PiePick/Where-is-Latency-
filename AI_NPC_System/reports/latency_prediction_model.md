# CREDO Latency Prediction Model

Generated: 2026-05-17T23:21:59.466526+00:00
Source records: 204
TTS records: 114
kNN records: 114
Method: artifact_backed_stage_aware_knn_with_engine_fallback

## Fallback Coefficients

| Engine | Records | Intercept ms | ms/char | ms/tag |
| --- | ---: | ---: | ---: | ---: |
| default | 109 | 100.0 | 10.429 | 3000.0 |
| fish_speech | 78 | 181.567 | 314.999 | 0.0 |
| stylebert_vits2 | 17 | 100.0 | 5.0 | 0.179 |

## kNN Feature Schema

char_len_200, word_count_40, tag_count_8, punct_count_10, sentence_count_6, avg_word_len_12, engine_fish_speech, engine_stylebert_vits2, engine_open_llm_tts, engine_default, stage_slow_tts, stage_fast_tts, stage_nonverbal_tts, stage_length_sweep_tts, stage_other_tts

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
