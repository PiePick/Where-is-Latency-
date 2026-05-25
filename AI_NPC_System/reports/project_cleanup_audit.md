# CREDO Project Cleanup Audit

작성 기준: 2026-05-24 KST

이 문서는 바로 삭제하지 않고 정리 후보를 분류하기 위한 감사 기록이다. 대형 vendor,
모델, 음성 산출물은 재설치 비용이 크므로 삭제 전 확인이 필요하다.

## 용량 상위 항목

| 경로 | 대략 용량 | 판단 |
| --- | ---: | --- |
| `vendor/fish-speech` | 18G | 유지. 현재 Fish Speech 서버와 checkpoint가 필요하다. |
| `vendor/Style-Bert-VITS2` | 14G | 보류. 현재 기본 경로는 아니지만 TTS 비교 실험 후보라 즉시 삭제 비추천. |
| `vendor/open-llm-vtuber` | 9.7G | 유지. UI/runtime 본체다. |
| `vendor/CosyVoice` | 4.6G | 삭제 완료. 현재 기본 경로에서 제외되었고 untracked 실험 폴더였으므로 제거했다. |
| `vendor/piper-tts` | 221M | 보류. `live-piper` 실험과 lightweight TTS baseline에 필요할 수 있다. |
| `AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1` | 116M | 유지. 현재 FastTrack 기본 cached Fish bundle이다. |
| `AI_NPC_System/fasttrack_assets/models` | 176M | 유지. SetFit intent model이 readiness 필수 항목이다. |
| `AI_NPC_System/tts_outputs` | 16M | 정리 가능. 대부분 임시 TTS 출력이다. 필요한 대표 샘플만 reports 또는 style_examples로 보존. |
| `AI_NPC_System/runtime` | 1.6M | 커밋 제외. 실행 로그/pid/state이며 재생성된다. `.gitignore`에 추가했다. |
| `__pycache__` 계열 | 수백 KB | 정리 가능. 재생성된다. |

## 삭제 전 확인이 필요한 항목

### `vendor/CosyVoice`

기본 실행은 Fish cached bundle로 정리되었기 때문에 필수는 아니다. 4.6GB untracked
실험 폴더였고 현재 런타임/논문 기본 조건에서 제외되어 삭제했다.

권장:

```text
재실험이 필요하면 별도 설치 스크립트/외부 저장소에서 재설치
```

### `vendor/Style-Bert-VITS2`

현재 기본값은 아니지만, 중간 지점 TTS 후보로 검토한 이력이 있다. 영어 모델 자산이 확정되지
않았으므로 현재는 legacy 후보로 분류한다.

권장:

```text
보류. 논문 실험 TTS 조건에서 제외하기로 확정되면 삭제 또는 외부 드라이브로 이동
```

### `AI_NPC_System/archive/legacy_manifests/persona_reaction_bundle_response_act_probe`

작은 probe manifest다. 재현성에는 큰 가치가 낮아 runtime 루트에서 archive로 이동했다.

권장:

```text
archive에 보존. 현재 실행 경로에서는 사용하지 않음
```

## 바로 정리해도 안전한 후보

다음 항목은 실행 시 재생성되거나 임시 산출물 성격이 강하다.

```text
AI_NPC_System/__pycache__/
AI_NPC_System/scripts/__pycache__/
vendor/Style-Bert-VITS2/__pycache__/
AI_NPC_System/runtime/pids/
AI_NPC_System/runtime/logs/
```

주의: runtime 로그는 장애 분석에는 유용하지만 커밋 대상은 아니다.

## 보존해야 하는 연구 산출물

```text
AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/
AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/
AI_NPC_System/reports/intent_transition_matrix_from_swda.*
AI_NPC_System/reports/setfit_intent_evaluation_summary.json
AI_NPC_System/reports/latency_prediction_model.*
AI_NPC_System/docs/
AI_NPC_System/latency_logs/
reaction_sources/
```

## 2026-05-24 정리 반영

```text
삭제: vendor/CosyVoice/
archive 이동: AI_NPC_System/expressive_audio_pool/ -> AI_NPC_System/archive/legacy_audio/expressive_audio_pool/
archive 이동: AI_NPC_System/persona_reaction_bundle_response_act_probe/ -> AI_NPC_System/archive/legacy_manifests/persona_reaction_bundle_response_act_probe/
archive 이동: AI_NPC_System/scripts/build_extreme_nonverbal_reactions.py -> AI_NPC_System/archive/legacy_scripts/build_extreme_nonverbal_reactions.py
archive 이동: AI_NPC_System/tts_style_examples/ -> AI_NPC_System/archive/tts_style_examples/
유지: AI_NPC_System/fasttrack_assets/audio/persona_reaction_bundle_response_act_v1/
유지: AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/
커밋 제외: AI_NPC_System/runtime/
```

## 권장 정리 순서

1. 현재 작업을 커밋한다.
2. 논문 실험에 쓸 TTS 후보를 Fish/Piper/Edge/CosyVoice/StyleBERT 중 확정한다.
3. 제외된 vendor는 삭제하거나 외부 저장소로 이동한다.
4. 임시 `tts_outputs`는 대표 샘플만 남기고 나머지를 삭제한다.
5. runtime logs는 오류 분석이 끝난 뒤 archive 또는 삭제한다.
