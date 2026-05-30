# CREDO 정량 레이턴시 데이터 설명 보고서

## 1. 보고서 목적

이 보고서는 `latency_sensitivity_study_20260529` 데이터셋이 무엇을 측정했는지, 어떤 조건에서 생성되었는지, 논문에서 어떻게 해석해야 하는지를 정리한다.

중요한 점은 이 데이터가 단순 추정값이 아니라, 실제 실행 중 기록된 모듈별 레이턴시 로그를 기반으로 만든 경험적 부트스트랩 시뮬레이션이라는 것이다. 다만 참가자 실험 결과나 브라우저 최종 청각 출력 시점의 직접 측정값은 아니므로, 논문에서는 다음 표현을 사용하는 것이 안전하다.

> recorded module logs 기반 empirical bootstrap sensitivity simulation

## 2. 데이터 출처

원본 로그는 다음 파일이다.

`AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`

사용한 clean window는 다음 시각 이후의 행이다.

`2026-05-29T03:36:00+09:00`

이 window에서 사용한 원본 모듈 이벤트는 508개이며, 이 이벤트들의 분포를 재표본추출하여 다양한 실험 조건으로 확장했다.

## 3. 생성된 파일

| 파일 | 설명 |
| --- | --- |
| `simulated_turns_wide.csv` | 턴 단위 raw 데이터. 480,000행. 각 행에 모든 모듈 latency가 컬럼으로 기록됨. |
| `condition_summary.csv` | 120개 실험 조건별 요약 통계. 논문 표 작성에 가장 적합함. |
| `module_summary.csv` | 조건별/모듈별 latency 요약. 병목 분석에 적합함. |
| `assumptions.json` | 시뮬레이션 조건, 배율, 프론트엔드 오버헤드 가정. |
| `summary.md` | 핵심 결과 요약. |

## 4. 실험 조건 구조

총 120개 조건을 생성했다.

`5 FastTrack policies x 4 SlowTrack load profiles x 3 frontend profiles x 2 scenario profiles = 120`

각 조건은 500회 반복했고, 반복마다 8턴을 생성했다. 따라서 조건당 4,000턴, 전체 480,000턴의 시뮬레이션 데이터가 생성되었다.

### 4.1 FastTrack 정책

| 정책 | 의미 |
| --- | --- |
| `grounded` | 감정과 response act를 모두 반영한 FastTrack |
| `emotion_only` | 감정만 반영한 FastTrack |
| `response_act_only` | SWDA 기반 response act만 반영한 FastTrack |
| `neutral_random` | 맥락 조건을 약화한 무작위성 기반 FastTrack |
| `slowtrack_only` | FastTrack 없이 SlowTrack만 사용하는 대조군 |

### 4.2 SlowTrack 부하 조건

| 조건 | 의미 | LLM 배율 | TTS 배율 |
| --- | --- | ---: | ---: |
| `current_prompt` | 현재 프롬프트와 현재 응답 길이 | 1.0 | 1.0 |
| `expanded_memory` | 페르소나, 최근 기억, 시청자 요약이 더해진 프롬프트 | 1.6 | 1.1 |
| `heavy_context` | 세계관, 주제 기억, 긴 답변 생성 | 2.4 | 1.25 |
| `stress_context` | 밀도 높은 기억과 긴 응답을 넣은 stress test | 3.4 | 1.4 |

### 4.3 프론트엔드 오버헤드 조건

| 조건 | 의미 |
| --- | --- |
| `backend_ready` | 서버 준비 시점 중심. 프론트엔드 오버헤드 최소. |
| `local_browser` | 로컬 브라우저 audio dispatch/start 오버헤드 포함. |
| `capture_stress` | OBS/capture/browser 부하를 가정한 stress 조건. |

### 4.4 시나리오 조건

| 조건 | 의미 |
| --- | --- |
| `chat_only` | 일반 채팅 턴만 존재 |
| `donation_mix` | 도네이션 readout gate가 섞인 방송형 조건 |

## 5. 주요 지표 정의

| 지표 | 의미 |
| --- | --- |
| `fasttrack_analysis_ms` | 감정/의도 분석 및 FastTrack routing latency |
| `emotion_motion_payload_ms` | 감정/표정/모션 payload 준비 latency |
| `fasttrack_audio_lookup_ms` | 사전 생성 FastTrack 음성 파일 lookup latency |
| `donation_readout_tts_ms` | 도네이션 메시지 readout TTS latency |
| `slowtrack_llm_ms` | SlowTrack 본문 생성을 위한 LLM latency |
| `slowtrack_tts_ms` | SlowTrack 본문 음성 합성 latency |
| `frontend_audio_overhead_ms` | 브라우저/오디오 시작 오버헤드 가정값 |
| `fasttrack_ready_ms` | FastTrack이 재생 준비되기까지 걸린 시간 |
| `first_response_ready_ms` | 사용자가 첫 반응을 들을 수 있다고 보는 준비 시점 |
| `full_answer_ready_ms` | SlowTrack 본문 답변이 준비되는 시점 |
| `hidden_latency_ms` | FastTrack이 가려주는 SlowTrack 대기 시간 |

논문 해석에서는 `first_response_ready_ms`와 `full_answer_ready_ms`를 구분해야 한다. FastTrack의 목적은 SlowTrack 계산 시간을 없애는 것이 아니라, 시청자가 무반응으로 기다리는 시간을 줄이는 것이다.

## 6. 핵심 결과

### 6.1 대표 조건 비교

| 조건 | FastTrack median first response | SlowTrack-only median first response | 개선량 | 감소율 | hidden latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current prompt / local browser / donation mix | 76.0 ms | 2330.6 ms | 2254.6 ms | 96.7% | 2400.0 ms |
| Heavy context / local browser / donation mix | 76.5 ms | 4597.7 ms | 4521.1 ms | 98.3% | 4739.0 ms |
| Stress context / capture stress / donation mix | 195.4 ms | 6318.7 ms | 6123.3 ms | 96.9% | 6379.3 ms |

해석: SlowTrack의 프롬프트가 무거워질수록 본문 응답은 더 늦어지지만, FastTrack의 첫 반응 latency는 거의 영향을 받지 않는다. 따라서 FastTrack은 복잡한 페르소나, 메모리, 세계관 프롬프트가 들어갈수록 더 큰 효과를 보인다.

### 6.2 Current prompt / local browser / donation mix에서 정책별 비교

| 정책 | median first response | p95 first response | 100ms 미만 비율 | 500ms 미만 비율 | 2초 초과 비율 | median full answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `grounded` | 76.0 ms | 338.4 ms | 82.4% | 100.0% | 0.0% | 2494.2 ms |
| `emotion_only` | 65.7 ms | 93.2 ms | 99.0% | 100.0% | 0.0% | 2358.0 ms |
| `response_act_only` | 63.1 ms | 89.8 ms | 99.5% | 100.0% | 0.0% | 2264.7 ms |
| `neutral_random` | 64.6 ms | 92.2 ms | 99.4% | 100.0% | 0.0% | 2354.8 ms |
| `slowtrack_only` | 2330.6 ms | 2569.2 ms | 0.0% | 0.0% | 95.3% | 2330.6 ms |

해석: FastTrack이 있는 모든 조건은 첫 반응이 500ms 미만으로 준비되었다. 반면 SlowTrack-only는 같은 조건에서 95.3%의 턴이 2초를 초과했다. `grounded`는 분석 단계가 더 많아 p95가 높지만, median 기준으로는 여전히 100ms 이하에 가깝다.

### 6.3 프론트엔드 부하에 따른 FastTrack 민감도

`grounded / current_prompt / donation_mix` 기준이다.

| 프론트엔드 조건 | median first response | p95 first response | median hidden latency |
| --- | ---: | ---: | ---: |
| `backend_ready` | 27.6 ms | 288.4 ms | 2403.5 ms |
| `local_browser` | 76.0 ms | 338.4 ms | 2400.0 ms |
| `capture_stress` | 196.1 ms | 459.4 ms | 2408.3 ms |

해석: FastTrack의 backend 준비 자체는 매우 짧지만, 실제 사용 환경에서는 브라우저와 capture pipeline 오버헤드가 첫 반응 latency를 지배할 수 있다. 그래도 stress 조건에서도 median은 200ms 전후로 유지된다.

### 6.4 SlowTrack 부하 증가에 따른 효과

`grounded / local_browser / donation_mix` 기준이다.

| SlowTrack 부하 | FastTrack median first response | SlowTrack-only median first response | median hidden latency | median full answer |
| --- | ---: | ---: | ---: | ---: |
| `current_prompt` | 76.0 ms | 2330.6 ms | 2400.0 ms | 2494.2 ms |
| `expanded_memory` | 76.0 ms | 3286.2 ms | 3398.6 ms | 3494.8 ms |
| `heavy_context` | 76.5 ms | 4597.7 ms | 4739.0 ms | 4837.6 ms |
| `stress_context` | 76.6 ms | 6198.0 ms | 6379.7 ms | 6480.6 ms |

해석: 프롬프트와 메모리가 무거워져도 FastTrack first response는 거의 변하지 않는다. 대신 숨겨지는 latency가 2.4초에서 6.4초까지 증가한다. 이는 FastTrack이 복잡한 VTuber 에이전트 설계에서 특히 유효하다는 근거가 된다.

## 7. 모듈별 병목 분석

`grounded / current_prompt / local_browser / donation_mix` 기준 모듈별 median은 다음과 같다.

| 모듈 | n | median | p75 | p95 |
| --- | ---: | ---: | ---: | ---: |
| `fasttrack_analysis_ms` | 4000 | 22.5 ms | 23.8 ms | 283.1 ms |
| `fasttrack_audio_lookup_ms` | 4000 | 1.8 ms | 1.9 ms | 2.2 ms |
| `frontend_audio_overhead_ms` | 4000 | 50.4 ms | 62.1 ms | 77.5 ms |
| `slowtrack_llm_ms` | 4000 | 1501.5 ms | 1578.3 ms | 1694.4 ms |
| `slowtrack_tts_ms` | 4000 | 939.3 ms | 1007.3 ms | 1091.1 ms |
| `donation_readout_tts_ms` | 1805 | 477.7 ms | 488.2 ms | 533.7 ms |
| `donation_emotion_motion_ms` | 1805 | 0.013 ms | 0.013 ms | 0.181 ms |

주요 병목은 SlowTrack LLM과 SlowTrack TTS이다. FastTrack 음성 lookup은 median 1.8ms로 매우 작다. 따라서 사전 생성 FastTrack 음성을 사용하는 현재 구조는 실시간 FastTrack TTS보다 학술적으로 더 방어 가능하다.

## 8. 논문에서 주장할 수 있는 내용

이 데이터로 강하게 주장할 수 있는 것은 다음이다.

1. FastTrack은 SlowTrack의 계산 시간을 직접 줄이지는 않지만, 첫 반응 준비 시간을 초 단위에서 수십 ms 단위로 낮춘다.
2. 사전 생성 FastTrack 음성 lookup은 latency 측면에서 거의 무시 가능한 수준이다.
3. LLM 프롬프트가 길어지고 메모리/세계관 정보가 많아질수록 SlowTrack-only 조건의 대기 시간은 증가하지만, FastTrack 조건의 첫 반응 시간은 안정적으로 유지된다.
4. 따라서 FastTrack은 단순 속도 최적화가 아니라, 장문 LLM 응답과 고품질 TTS가 필요한 VTuber 시스템에서 무반응 구간을 은닉하는 interaction design layer로 볼 수 있다.

## 9. 논문에서 아직 주장하면 안 되는 내용

다음은 아직 조심해야 한다.

1. 이 데이터만으로 사용자가 실제로 더 자연스럽게 느꼈다고 주장하면 안 된다.
2. 이 데이터는 실제 브라우저에서 소리가 귀에 도달한 시점을 직접 측정한 것은 아니다.
3. Social presence, engagement, character appeal은 별도의 사용자 설문 결과가 필요하다.
4. Perceived latency 역시 최종적으로는 설문/사용자 실험 결과와 연결해야 한다.

## 10. 논문 문장 예시

다음 문장을 논문 방법론에 사용할 수 있다.

> We performed an empirical bootstrap sensitivity simulation using recorded module-level latency logs from the CREDO runtime. The simulation sampled observed latency distributions for FastTrack routing, prebuilt audio lookup, SlowTrack LLM generation, SlowTrack TTS synthesis, donation readout, and frontend audio dispatch overhead. We evaluated 120 conditions across FastTrack policy, SlowTrack prompt load, frontend overhead, and broadcast scenario profile.

결과 설명에는 다음 문장을 사용할 수 있다.

> Under the current-prompt, local-browser, donation-mix condition, the grounded FastTrack policy reduced median first-response readiness from 2330.6 ms in the SlowTrack-only baseline to 76.0 ms. This corresponds to a 2254.6 ms reduction in initial response delay, while the full SlowTrack answer remained available after approximately 2494.2 ms.

## 11. 결론

이 정량 데이터는 CREDO 시스템의 핵심 가설을 뒷받침한다. 즉, VTuber 에이전트에서 가장 중요한 문제는 전체 답변 생성을 항상 빠르게 끝내는 것이 아니라, 시청자가 무반응으로 기다리는 구간을 줄이는 것이다.

현재 결과는 FastTrack이 이 무반응 구간을 효과적으로 줄이며, 특히 프롬프트와 메모리가 복잡해질수록 그 가치가 커진다는 것을 보여준다. 단, 최종 학술 주장은 이 시스템 로그 기반 정량 분석에 사용자 설문 결과를 결합해야 완성된다.
