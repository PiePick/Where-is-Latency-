# SWDA 기반 의도 전이 행렬 산출 기록

## 목적
사용자 의도 라벨을 FastTrack 응답 의도로 그대로 복사하지 않기 위해, 실제 대화에서 관찰되는 인접 화자 전환 패턴을 전이 확률로 산출한다.

## 데이터 및 산출 방식
- 원본 데이터: `/mnt/c/Users/CGLAB/Desktop/CREDO/reaction_sources/swda/swda.zip`
- 입력 단위: Switchboard Dialog Act Corpus의 `.utt.csv` 발화 행
- 사용 라벨: QUESTION, INFORM, ACKNOWLEDGE, DIRECTIVE, EXPRESSIVE, REJECT
- 제외 기준: 6개 coarse intent로 매핑되지 않는 SWDA act tag
- 전이 기준: 동일 conversation 안에서 transcript_index 순서상 인접하고 caller가 바뀐 발화쌍
- 정규화: target intent count에 additive smoothing 1.0 적용 후 행 단위 확률화

## 규모
- 매핑된 발화 수: 157571
- 동일 대화 내 인접 발화쌍 수: 156416
- 화자 전환 인접 발화쌍 수: 78439

## 전이 행렬
| user_intent | response_intent 확률 | 관측 전이 수 |
| --- | --- | --- |
| QUESTION | QUESTION: 0.030, INFORM: 0.473, ACKNOWLEDGE: 0.472, DIRECTIVE: 0.003, EXPRESSIVE: 0.001, REJECT: 0.021 | QUESTION: 204, INFORM: 3274, ACKNOWLEDGE: 3267, DIRECTIVE: 23, EXPRESSIVE: 9, REJECT: 143 |
| INFORM | QUESTION: 0.066, INFORM: 0.249, ACKNOWLEDGE: 0.676, DIRECTIVE: 0.003, EXPRESSIVE: 0.002, REJECT: 0.004 | QUESTION: 2927, INFORM: 11069, ACKNOWLEDGE: 30009, DIRECTIVE: 148, EXPRESSIVE: 100, REJECT: 161 |
| ACKNOWLEDGE | QUESTION: 0.048, INFORM: 0.862, ACKNOWLEDGE: 0.079, DIRECTIVE: 0.006, EXPRESSIVE: 0.004, REJECT: 0.001 | QUESTION: 1187, INFORM: 21499, ACKNOWLEDGE: 1971, DIRECTIVE: 140, EXPRESSIVE: 104, REJECT: 29 |
| DIRECTIVE | QUESTION: 0.137, INFORM: 0.482, ACKNOWLEDGE: 0.278, DIRECTIVE: 0.026, EXPRESSIVE: 0.041, REJECT: 0.036 | QUESTION: 52, INFORM: 186, ACKNOWLEDGE: 107, DIRECTIVE: 9, EXPRESSIVE: 15, REJECT: 13 |
| EXPRESSIVE | QUESTION: 0.017, INFORM: 0.025, ACKNOWLEDGE: 0.019, DIRECTIVE: 0.004, EXPRESSIVE: 0.935, REJECT: 0.001 | QUESTION: 27, INFORM: 41, ACKNOWLEDGE: 30, DIRECTIVE: 5, EXPRESSIVE: 1563, REJECT: 1 |
| REJECT | QUESTION: 0.152, INFORM: 0.280, ACKNOWLEDGE: 0.530, DIRECTIVE: 0.015, EXPRESSIVE: 0.008, REJECT: 0.015 | QUESTION: 19, INFORM: 36, ACKNOWLEDGE: 69, DIRECTIVE: 1, EXPRESSIVE: 0, REJECT: 1 |

## 해석상 주의
이 행렬은 SWDA 대화쌍의 화자 전환 통계에서 직접 산출한 초기 전이 정책이다. 실제 VTuber 방송 문맥에서는 채팅 밀도, 도네이션, 화면 상황, 캐릭터 성격에 따라 보정이 필요하다.
