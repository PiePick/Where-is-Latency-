# CREDO Latency Data Reliability Note

## 핵심 결론

현재 `latency_sensitivity_study_20260529` 데이터는 실제 VTuber 시스템을 480,000번 end-to-end 실행한 결과가 아니다.

이 데이터는 실제 실행 중 기록된 모듈별 latency 로그를 기반으로 만든 경험적 부트스트랩 시뮬레이션이다. 따라서 학술적으로 사용할 수는 있지만, 반드시 `simulation` 또는 `sensitivity analysis`로 표기해야 한다.

## 왜 짧은 시간에 480,000행이 생성되었는가

시뮬레이션은 다음 작업만 수행한다.

1. 실제 로그에서 모듈별 latency 샘플을 읽는다.
2. 조건별로 샘플을 무작위 재표본추출한다.
3. LLM/TTS 부하 배율과 프론트엔드 오버헤드 가정을 적용한다.
4. 각 턴의 `first_response_ready_ms`, `full_answer_ready_ms`, `hidden_latency_ms`를 계산한다.
5. CSV로 저장한다.

즉, 매 row마다 실제 LLM 서버 호출, TTS 합성, 브라우저 재생, Live2D 렌더링을 수행하지 않는다. 그래서 480,000행이 빠르게 생성되는 것이 정상이다.

## 믿을 수 있는 부분

다음 주장은 가능하다.

1. 실제 기록된 모듈 latency 분포를 기반으로 한 조건별 시뮬레이션이다.
2. FastTrack audio lookup은 실제 로그상 매우 짧은 모듈로 관측되었고, 이 분포가 시뮬레이션에 반영되었다.
3. SlowTrack LLM/TTS가 병목이라는 구조적 결론은 로그와 시뮬레이션 양쪽에서 일관된다.
4. 프롬프트와 메모리가 무거워질수록 SlowTrack-only 대기 시간이 증가하고, FastTrack first response는 상대적으로 안정적이라는 민감도 분석은 가능하다.

## 아직 믿으면 안 되는 부분

다음처럼 쓰면 안 된다.

1. “480,000번 실제 실행했다.”
2. “사용자가 실제로 이 latency를 체감했다.”
3. “브라우저에서 실제 소리가 귀에 들린 시점을 측정했다.”
4. “참가자 실험에서 FastTrack이 더 자연스럽다고 증명되었다.”

현재 데이터는 backend/module readiness 중심의 시뮬레이션이며, 실제 perceptual latency 주장은 사용자 실험과 browser audible-onset 로그가 필요하다.

## 논문에서 안전한 표현

사용 가능한 표현:

> We conducted an empirical bootstrap sensitivity simulation from recorded module-level runtime logs.

한국어 설명:

> 본 연구는 실제 런타임에서 수집한 모듈별 latency 로그를 기반으로 경험적 부트스트랩 민감도 분석을 수행하였다.

피해야 할 표현:

> We measured 480,000 real end-to-end VTuber interactions.

## 실제 실측으로 보강하려면 필요한 것

논문 설득력을 높이려면 시뮬레이션과 별도로 작은 규모의 실제 실행 검증을 붙이는 것이 좋다.

권장 실측 설계:

1. 6개 실험 케이스를 실제 런타임으로 실행한다.
2. 케이스당 10턴 정도를 실행한다.
3. 총 60턴의 actual end-to-end log를 남긴다.
4. 각 턴에서 다음 timestamp를 기록한다.
   - chat input accepted
   - FastTrack routing start/end
   - FastTrack audio selected
   - frontend audio play event
   - SlowTrack LLM start/end
   - SlowTrack TTS start/end
   - SlowTrack audio play event
5. 시뮬레이션 결과와 실제 실행 subset이 같은 경향을 보이는지 비교한다.

이렇게 하면 논문에서는 다음 구조로 방어할 수 있다.

1. 실제 모듈 로그 기반 시뮬레이션으로 넓은 조건을 분석했다.
2. 별도의 작은 실제 실행 benchmark로 시뮬레이션 경향을 검증했다.
3. 최종 perceptual quality는 사용자 설문으로 평가했다.

## 현재 데이터의 적절한 위치

현재 데이터는 논문에서 `System Evaluation`, `Latency Sensitivity Analysis`, `Computational Simulation`에 들어가는 것이 적절하다.

최종 사용자 체감 결과는 `User Study` 섹션에서 별도로 다뤄야 한다.
