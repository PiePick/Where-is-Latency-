# CREDO User Study Protocol Draft

작성 기준: 2026-05-23 KST

## 목적

사용자가 AI VTuber와 상호작용할 때, FastTrack latency cover가 체감 응답성,
감정 적합성, 대화 자연스러움, 캐릭터 실재감에 미치는 영향을 비교한다.

## 참가자 과제

참가자는 각 조건에서 동일한 종류의 짧은 채팅을 입력한다.

권장 입력 유형:

1. 긍정 질문: "That sounds fun, can you tell me more?"
2. 부정 정보: "I had a rough day today."
3. 애매한 질문: "Wait, what do you mean by that?"
4. 중립 정보: "I am watching while working on homework."
5. 지시형 입력: "Try reacting like a streamer."
6. 감탄형 입력: "Wow, that was really unexpected!"

각 입력은 실제 데모 중 자연스럽게 바꿔도 되지만, 조건 간 비교에서는 같은 입력 세트를 유지한다.

## 조건 순서

순서 효과를 줄이기 위해 참가자마다 조건 순서를 바꾼다.

```text
participant 1: no-cover -> piper-realtime -> affective-cached-fish
participant 2: piper-realtime -> affective-cached-fish -> no-cover
participant 3: affective-cached-fish -> no-cover -> piper-realtime
```

## 실행 명령

```bash
AI_NPC_System/scripts/run_experiment_condition.sh no-cover --profile live
AI_NPC_System/scripts/run_experiment_condition.sh piper-realtime --profile live-piper
AI_NPC_System/scripts/run_experiment_condition.sh affective-cached-fish --profile live
```

각 조건 전에는 기존 stack을 종료하고 새 조건으로 다시 시작한다. Open-LLM-VTuber frontend는
`http://127.0.0.1:12393`에서 동일하게 사용한다.

## 평가 문항

각 조건이 끝난 뒤 1-5점으로 평가한다.

| 번호 | 문항 | 1점 | 5점 |
| --- | --- | --- | --- |
| Q1 | 캐릭터가 빠르게 반응하기 시작한 것처럼 느껴졌다. | 전혀 아니다 | 매우 그렇다 |
| Q2 | 기다리는 동안 시스템이 멈춘 것처럼 느껴지지 않았다. | 전혀 아니다 | 매우 그렇다 |
| Q3 | 첫 짧은 반응이 내 입력 감정과 잘 맞았다. | 전혀 아니다 | 매우 그렇다 |
| Q4 | 짧은 반응과 이어지는 긴 답변이 하나의 자연스러운 발화처럼 느껴졌다. | 전혀 아니다 | 매우 그렇다 |
| Q5 | 목소리와 Live2D 모션이 캐릭터 감정과 잘 맞았다. | 전혀 아니다 | 매우 그렇다 |
| Q6 | 전체 상호작용이 실제 VTuber와 대화하는 느낌에 가까웠다. | 전혀 아니다 | 매우 그렇다 |
| Q7 | 이 조건의 응답 지연은 수용 가능했다. | 전혀 아니다 | 매우 그렇다 |

자유서술:

```text
가장 자연스러웠던 순간:
가장 어색했던 순간:
목소리/모션/반응 타이밍에서 고칠 점:
```

## 시스템 로그와 매칭할 항목

사용자 평가 row에는 최소한 다음 메타데이터를 같이 기록한다.

```text
participant_id
condition
trial_index
input_text
emotion_label
user_intent
sampled_response_act
style_tag
fast_audio_id
time_to_first_audio_ms
slow_track_llm_ms
slow_track_tts_ms
turn_total_ms
```

## 제외 기준

다음 경우 해당 trial은 별도 표시하거나 제외한다.

- Fish Speech 서버가 busy 상태로 이전 요청을 10초 이상 끌고 간 경우
- Open-LLM-VTuber websocket이 끊긴 경우
- FastTrack cached audio가 없어 fallback 경로로 간 경우
- 사용자가 입력 도중 조건을 착각하거나 다른 언어 정책을 테스트한 경우
- 음성 파일 자체가 잘리거나 재생되지 않은 경우

## 분석 계획

정량 분석:

- 조건별 Q1-Q7 평균과 표준편차
- 조건별 `time_to_first_audio_ms`, `turn_total_ms`
- `time_to_first_audio_ms`와 perceived responsiveness 점수 간 상관
- FastTrack 감정 일치 실패 trial의 평가 점수 비교

정성 분석:

- 자유서술에서 반복적으로 언급되는 어색함 분류
- 음성 레퍼런스 문제와 latency-cover 구조 문제를 분리해 코딩
- 모션 강도 과다/부족 사례 분류

