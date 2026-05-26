# CREDO: A Latency-Cover Architecture For Interactive AI VTuber Streaming

작성일: 2026-05-26 KST
최종 업데이트: 2026-05-27 KST
상태: 실험 결과 제외 논문 초안
대상 시스템: CREDO / Open-LLM-VTuber integration

## Abstract

대규모 언어 모델 기반 AI VTuber는 자연스러운 장문 응답을 생성할 수 있지만,
실시간 방송 상황에서는 LLM 추론, 음성 합성, Live2D 렌더링이 누적되며
시청자가 체감하는 침묵 구간이 길어진다. 본 연구는 고품질 TTS 자체의
품질을 높이는 대신, 방송 대화의 인지적 공백을 완화하는 latency-cover
구조를 제안한다. 제안 시스템 CREDO는 입력 채팅을 감정과 대화 행위로
분석한 뒤, 데이터셋 기반의 짧은 FastTrack 반응과 로컬 LLM 기반의
SlowTrack 본문 응답을 병렬적으로 운용한다. FastTrack은 GoEmotions
기반 4대 감정 라벨과 SWDA 기반 대화 행위 전이 라벨을 사용하되, 두
원본 데이터셋을 하나의 정적 반응 manifest로 합치지 않는다. 대신 각
데이터셋을 별도의 필터링된 evidence pool로 보존하고, 런타임에서 감정
근거와 대응 의도 근거를 검색한 뒤 짧은 persona-consistent cover 문장을
조합한다. 별도의 순수 비언어 감탄사 오디오는 활성 FastTrack 경로에서
제거하고, 사용자 발화에서 분석된 감정 라벨을 기반으로 답변 전체에
Live2D 표정과 몸 모션을 적용한다. 입 파라미터는 오디오 기반 lip-sync가
독점하도록 분리하여, 표정이 유지되는 동안에도 대사에 맞는 입 움직임이
계속 출력되게 한다. SlowTrack은 로컬 LLM, 경량 메모리, 실시간
StyleBERT-VITS2 TTS를 사용하여 본문 발화를 생성한다. 또한 현재 발화 재생 중 다음 발화를 백그라운드에서
준비하는 병렬 프리페치 스케줄링을 도입하여, 물리적 지연이 체감 대기
시간으로 직접 노출되는 정도를 줄인다. 본 논문 초안은 결과를 보고하지
않고, 시스템 구조와 실험 설계만을 기술한다. 실험은 FastTrack 텍스트
검색 기준(Contextual Mapping)과 SlowTrack 준비 방식(Scheduling
Architecture)을 독립 변수로 두어, 감정 근거 검색, SWDA 대응 의도 검색,
두 근거의 동시 사용, 맥락 참조 없는 대조군이 VTuber 상호작용의 연속성과
체감 응답성에 미치는 영향을 평가하도록 설계되었다.

## Keywords

AI VTuber, latency cover, real-time dialogue, dialogue act, emotion
classification, asynchronous scheduling, Live2D, text-to-speech

## 1. Introduction

실시간 AI VTuber는 채팅 입력을 해석하고, 캐릭터 페르소나에 맞는 언어
응답을 생성하며, 이를 음성 및 Live2D 표현으로 출력해야 한다. 이 과정은
일반적인 챗봇보다 시간 제약이 강하다. 텍스트 응답만 제공하는 환경에서는
수 초의 지연이 허용될 수 있지만, 방송형 인터페이스에서는 캐릭터가
침묵하는 순간 자체가 상호작용 품질 저하로 인식된다.

기존 접근은 주로 더 좋은 LLM, 더 자연스러운 TTS, 더 강한 음성 복제 모델에
초점을 둔다. 그러나 고품질 생성형 TTS는 실제 인터랙션에서 수십 초 수준의
지연을 보일 수 있으며, 이 경우 짧은 filler만으로 지연을 숨기는 것은
현실적으로 어렵다. 따라서 본 연구는 다음 질문에서 출발한다.

> 장문의 LLM 응답을 기다리는 동안, 데이터셋 기반의 짧은 반응과 비동기
> 발화 준비를 결합하면 AI VTuber의 체감 응답성과 방송 연속성을 개선할 수
> 있는가?

CREDO는 이 질문에 답하기 위한 실험 플랫폼이다. 핵심은 단일 응답 생성
경로가 아니라, 즉시 반응하는 FastTrack과 심층 응답을 담당하는 SlowTrack을
분리하고 두 경로를 방송 타이밍에 맞게 스케줄링하는 것이다.

## 2. System Overview

CREDO는 Open-LLM-VTuber를 기반 플랫폼으로 사용한다. Open-LLM-VTuber는
웹 UI, WebSocket 대화 루프, Live2D 표시, 립싱크, 기본 TTS 연결을 제공한다.
CREDO는 이 위에 다음 모듈을 추가한다.

```text
chat batch or idle trigger
  -> FastTrack router
     -> emotion classification
     -> incoming intent classification
     -> SWDA transition-based response-act sampling
     -> separated GoEmotions/SWDA dataset-pool retrieval
     -> runtime persona cover composition
     -> realtime language TTS
     -> viewer-emotion Live2D expression/body motion
  || SlowTrack generation
     -> local LLM persona response
     -> lightweight memory context
     -> realtime language TTS
  -> playback / mouth-only lip-sync / chat buffering / optional next-turn prefetch
```

이 구조에서 FastTrack은 “정답”을 말하는 경로가 아니라 방송 공백을 덜
어색하게 만드는 짧은 반응 경로다. SlowTrack은 더 긴 문맥과 캐릭터성을
반영하는 본문 발화 경로다. 두 경로는 같은 턴 안에서 순차적으로 들릴 수
있지만, 계산은 가능한 한 병렬로 진행된다.

## 3. FastTrack Analysis Layer

### 3.1 Emotion Classification

FastTrack은 먼저 사용자 발화의 정서적 뉘앙스를 4개 라벨로 압축한다.

| Label | Meaning |
| --- | --- |
| POSITIVE | 호의, 즐거움, 동의, 긍정적 감정 |
| NEGATIVE | 불만, 슬픔, 피로, 반감 |
| SURPRISE | 놀람, 의문, 예기치 못한 반응 |
| NEUTRAL | 정보 전달 또는 정서가 약한 발화 |

구현상으로는 로컬에 사용 가능한 GoEmotions 계열 DistilBERT 모델이 있으면
이를 사용하고, 모델 로딩 실패나 오프라인 환경에서는 규칙 기반 fallback을
사용한다. fallback은 연구 목적의 안정성을 위해 중요하다. 모델 의존성
문제로 방송 루프가 멈추면 실험 조건 자체가 깨지기 때문이다.

### 3.2 Incoming Intent Classification

사용자 발화는 SWDA의 대화 행위 체계에서 압축한 6개 라벨 중 하나로
분류된다.

| Incoming intent | Description |
| --- | --- |
| QUESTION | 질문 |
| INFORM | 정보 제공 |
| ACKNOWLEDGE | 수용, 확인, 짧은 응답 |
| DIRECTIVE | 요청, 지시 |
| EXPRESSIVE | 감정 표현 |
| REJECT | 거절, 반박 |

SetFit 기반 intent classifier가 로컬 모델로 사용되며, 사용 불가능한 경우
문장부호와 표면 패턴을 이용한 규칙 기반 분류로 대체된다. 이 fallback 역시
실시간 상호작용의 정지 방지를 위한 설계다.

### 3.3 Response-Act Transition

중요한 점은 사용자 의도를 그대로 에이전트 응답 의도로 복사하지 않는다는
것이다. 예를 들어 사용자가 질문을 했다고 해서 FastTrack도 질문으로
응답하면 대화가 반복되거나 회피처럼 보일 수 있다. CREDO는 SWDA의 인접
발화 쌍에서 도출한 전이 행렬을 사용해, 사용자 incoming intent에서
시스템 response act로 확률적으로 전이한다.

예를 들어 QUESTION 입력은 ACKNOWLEDGE 또는 INFORM으로 전이될 가능성이
높고, DIRECTIVE 입력은 ACKNOWLEDGE로 응답하는 것이 자연스러울 가능성이
높다. 감정 라벨은 전이 확률에 약한 bias로 반영된다. 부정 감정에서는
ACKNOWLEDGE 비중을 높여 공감적 확인을 유도하고, 긍정 감정에서는
EXPRESSIVE와 ACKNOWLEDGE를 강화한다. `QUESTION`은 incoming intent로는
분석되지만 FastTrack output response act에서는 제거한 뒤 재정규화한다.

## 4. FastTrack Output Asset Layer

### 4.1 Separated Dataset Pools

초기 구현은 감정과 대응 의도 조합별로 완성된 FastTrack 문장을 미리
생성하는 정적 manifest 구조를 사용했다. 그러나 이 방식은 두 가지 문제가
있다. 첫째, GoEmotions와 SWDA라는 서로 다른 목적의 데이터셋을 최종 문장
단위로 조기에 결합해 버리므로, 실험에서 감정 근거와 대화 행위 근거의
기여를 분리해서 해석하기 어렵다. 둘째, persona rewrite가 데이터셋 근거를
과도하게 덮어쓰면 학술적으로 “데이터셋 기반 반응”이라는 설명력이 약해진다.

따라서 현재 활성 구조는 정적 reaction manifest를 사용하지 않는다. 두
원본 데이터셋은 다음과 같이 별도의 필터링된 evidence pool로 유지된다.

| Pool | Source dataset | Runtime role |
| --- | --- | --- |
| Emotion evidence pool | GoEmotions | 사용자 발화의 정서 방향과 유사한 짧은 근거 텍스트 검색 |
| Response-act evidence pool | SWDA | 전이된 시스템 대응 의도에 맞는 대화 행위 근거 텍스트 검색 |

GoEmotions pool은 `POSITIVE`, `NEGATIVE`, `SURPRISE`, `NEUTRAL`로
구성되며, SWDA pool은 `INFORM`, `ACKNOWLEDGE`, `DIRECTIVE`,
`EXPRESSIVE`, `REJECT`로 구성된다. SWDA의 `QUESTION`은 incoming intent
분류에는 남아 있지만, FastTrack output response act에서는 제외된다. 이는
짧은 latency-cover 발화가 질문으로 끝날 경우 사용자가 실제 SlowTrack
답변을 기다리는 상황과 충돌하기 때문이다.

필터링 단계에서는 고유명사, 브랜드/플랫폼명, 날짜와 숫자, 정치·뉴스·스포츠
등 일반 방송 상황에 쏠린 주제, 욕설, 선정적 표현, 폭력적 표현, 이모티콘,
긴 웃음 문자열, 미완성 문장, 특정 외부 맥락 없이는 이해하기 어려운 발화를
제거한다. 이 필터링은 persona 문체를 덧씌우기 전에 수행되므로, 런타임
조합의 근거가 되는 데이터셋 텍스트 자체의 일반성을 유지한다.

현재 pool 검증 결과는 GoEmotions `1131`개, SWDA `1049`개 항목을 유지한다.
SWDA `QUESTION` output 항목은 `0`개다. 이 수치는 실험 결과가 아니라
방법론적 데이터 준비 상태를 나타내는 재현성 정보다.

### 4.2 Runtime Persona Cover Composition

FastTrack 텍스트는 완성 문장을 manifest에서 고르는 대신, 런타임에서 다음
순서로 조합된다.

```text
detected emotion
  + transitioned non-question response act
  + retrieved GoEmotions evidence
  + retrieved SWDA evidence
  -> Professor's Lab Maid cover template
  -> short spoken FastTrack text
```

persona는 실존 캐릭터 모방 대신 “교수님의 연구실에서 일하는 랩실 메이드”
설정으로 일반화했다. 발화는 논문, 실험, 교수님 메시지, 커피, 마감, 연구실
노트 같은 소재를 가볍게 사용하지만, 정적 접미사나 강제 catchphrase를
사용하지 않는다. 이 방식은 데이터셋 근거와 persona 표현을 분리한다는 점에서
학술적으로 중요하다. 감정 및 대화 행위의 근거는 원본 데이터셋에서 오고,
캐릭터성은 별도의 runtime realization layer에서 적용되므로, 실험자가
어느 층이 체감 응답성에 기여했는지 더 명확히 분석할 수 있다.

FastTrack 텍스트 선택은 네 가지 방식으로 전환된다.

| Condition | Lookup basis |
| --- | --- |
| Grounded | emotion + transitioned response act |
| Emotion Only | emotion only |
| Intent Only | transitioned response act only |
| None | Context-free FastTrack control without emotion/intent lookup |

Grounded 조건에서는 GoEmotions 감정 pool과 SWDA 대응 의도 pool을 모두
검색한다. Emotion Only는 SWDA 대응 의도 근거를 제거하고 감정 근거만
사용하며, Intent Only는 감정 근거를 제거하고 SWDA 대응 의도 근거만 사용한다.
None은 FastTrack을 끄는 조건이 아니라, 감정/의도 맥락 참조를 제거한
대조군이다.

### 4.3 Vector Search

각 source pool 항목은 간단한 해시 기반 벡터로 임베딩되며, FAISS가 사용
가능한 환경에서는 라벨별 IndexFlatIP 인덱스를 사용한다. FAISS가 없으면
동일 벡터에 대한 NumPy 내적 검색으로 대체된다. 이는 외부 모델 다운로드
없이도 재현 가능한 in-memory 검색을 보장하기 위한 선택이다.

검색은 각 pool에서 Top-k 근거를 반환하고, 런타임 composer는 선택 정책에
따라 하나의 짧은 반응을 만든다. 반환 metadata에는 사용된 GoEmotions 항목과
SWDA 항목의 ID가 분리되어 남는다. 이 구조는 단순 random 선택보다 입력
발화와 근거 텍스트 간의 어휘적 관련성을 보존하면서, 실시간성을 유지한다.

### 4.4 Viewer-Emotion Motion Layer

활성 런타임에서는 FastTrack의 순수 비언어 감탄사 wav와 이에 결합된
독립 모션을 제거한다. 짧은 감탄사 오디오가 반복될 경우 방송 맥락과
무관한 filler처럼 느껴질 수 있고, 본 연구의 핵심 변수인 FastTrack 텍스트
선택 기준을 흐릴 수 있기 때문이다.

대신 사용자 발화에서 분석된 감정 라벨을 Live2D 표현 레이어에 직접 연결한다.
`POSITIVE`, `NEGATIVE`, `SURPRISE/AMBIGUOUS`, `NEUTRAL` 라벨은 각각
speech-safe 모션 그룹과 motion profile로 변환되며, FastTrack 짧은 발화와
SlowTrack 본문 발화 전체에 동일한 감정 톤을 유지한다. 이때 표정과 몸 모션은
입 파라미터를 제어하지 않는다. CREDO의 Live2D 모션 파일에서
`ParamMouthOpenY`와 `ParamMouthForm` 커브를 제거하고, 입 여닫기는 오디오
volume 기반 lip-sync가 담당하도록 분리한다.

이 설계는 “감정적으로 반응하는 아바타”와 “대사에 맞춰 움직이는 입”을
분리한다. 따라서 대화 상대의 발화가 부정적이면 답변 내내 걱정/공감 톤의
표정과 몸 움직임을 유지하면서도, 실제 음성의 세기에 맞춰 입이 계속
움직인다. 이는 별도 비언어 감탄사 삽입 없이도 latency cover 발화가
방송형 캐릭터 반응으로 보이게 하는 표현 계층이다.

## 5. SlowTrack Generation Layer

SlowTrack은 캐릭터가 실제로 말할 본문 응답을 생성하는 경로다. 로컬 LLM은
시스템 프롬프트, 현재 채팅 batch, 최근 대화 memory를 바탕으로 응답을
생성한다. memory는 장기 semantic memory가 아니라, JSON 기반의 경량
프로필/최근 턴/감정 이벤트 저장소다. 이는 latency를 크게 늘리지 않는
범위에서 최소한의 맥락 지속성을 제공하기 위한 타협이다.

언어 TTS는 현재 StyleBERT-VITS2 `credo_voice_sample_en` 모델을 사용한다.
Fish Speech와 CosyVoice2는 음색 품질 실험에는 유용했지만, 실시간 방송
상호작용에서는 지연이 커 primary live 조건에서 제외했다. StyleBERT-VITS2는
동일한 음색 경로를 FastTrack과 SlowTrack에 제공하여, 짧은 반응과 본문
발화 사이의 음성 일관성을 유지한다.

## 6. Scheduling Architecture

CREDO의 두 번째 핵심 변수는 발화 준비 시점이다.

| Scheduling condition | Definition |
| --- | --- |
| Parallel | 현재 오디오 재생 중 다음 SlowTrack 발화를 백그라운드에서 준비 |
| Serial | 현재 발화가 끝난 뒤 다음 입력 처리와 응답 생성을 시작 |

Parallel 조건에서는 SlowTrack이 재생되는 동안 채팅이 즉시 응답되지 않고
buffer에 누적된다. 동시에 다음 idle 발화 또는 다음 context 발화를 준비할
수 있다. 현재 발화가 종료될 때 prefetch queue에 준비된 SlowTrack wav가
있으면 FastTrack을 생략하고 바로 본문 발화를 이어 간다. 이는 불필요한
짧은 반응 남발을 줄이고, 준비된 장문 발화가 있을 때는 방송 흐름을 더
자연스럽게 유지하기 위한 예외 처리다.

Serial 조건은 대조군 역할을 한다. 발화가 종료된 후에야 다음 입력을 처리하고
본문을 생성하므로, 병렬 준비가 체감 공백을 얼마나 줄이는지 비교할 수 있다.

## 7. Experiment Design

본 연구의 주요 실험은 2요인 설계다.

### 7.1 Factor 1: Contextual Mapping

FastTrack 텍스트를 선택할 때 어떤 정보를 기준으로 사용할지 비교한다.

| Level | Description |
| --- | --- |
| Emotion Only | 감정 라벨만 사용 |
| Intent Only | SWDA 전이 기반 대응 의도만 사용 |
| Grounded | 감정과 대응 의도를 모두 사용 |
| None | 감정/의도 참조 없이 맥락 비참조 FastTrack 생성 |

이 요인은 짧은 cover 반응의 내용 적합성을 평가한다. 감정만 맞는 반응이
충분한지, 대화 행위만 맞아도 자연스러운지, 둘을 결합할 때 가장 나은지
검증할 수 있다.

### 7.2 Factor 2: Scheduling Architecture

SlowTrack 준비를 언제 시작할지 비교한다.

| Level | Description |
| --- | --- |
| Parallel | 재생 중 다음 응답 준비 |
| Serial | 재생 종료 후 다음 응답 준비 |

이 요인은 실제 물리적 latency와 사용자의 인지적 대기 시간을 분리해서
관찰하기 위한 것이다.

### 7.3 Controlled Variables

실험 간 비교 가능성을 위해 다음 요소는 고정한다.

- 동일한 Open-LLM-VTuber frontend 및 Live2D 출력 경로
- 동일한 StyleBERT-VITS2 TTS 모델
- 동일한 SlowTrack LLM 설정과 persona prompt
- 동일한 분리 필터링 데이터셋 pool
- 동일한 사용자 감정 기반 mouth-safe Live2D expression/motion mapping
- 동일한 latency logging schema

## 8. Measurement Plan

객관 지표는 `AI_NPC_System/latency_logs/module_events.csv`에 기록된다.
각 row에는 `component_mode`, `selection_policy`, `scheduling_mode`가 함께
저장되어 실험 조건이 섞이지 않게 한다.

주요 모듈 지표는 다음과 같다.

| Metric | Meaning |
| --- | --- |
| fasttrack_analysis | 감정/의도/전이/검색 시간 |
| fasttrack_audio | 언어 FastTrack TTS 준비 또는 전달 |
| emotion_motion_payload | 감정 기반 표정/몸 모션 action 전달 |
| slowtrack_llm | 본문 LLM 응답 생성 |
| slowtrack_tts | 본문 TTS 합성 |
| turn_total | 전체 턴 완료 시간 |
| time to first audible reaction | 브라우저 재생 기준 첫 audible onset |

주관 평가는 체감 속도, 캐릭터 반응 적합도, 대화 흐름의 끊김, 모션과 음성의
일치감, 시스템이 멈춘 것처럼 보였는지를 포함해야 한다.

## 9. Implementation Notes

시스템은 실험 중 멈추지 않는 것을 우선한다. 따라서 모든 ML 모듈은 가능한
로컬 모델을 사용하되, 실패 시 규칙 기반 fallback으로 내려간다. FAISS가
없으면 NumPy 검색으로 대체된다. TTS 서버와 LLM 서버는 runtime readiness
검사 대상이며, 실패 시 어떤 모듈이 준비되지 않았는지 명시한다.

현재 UI는 실험 요인을 직접 버튼으로 바꿀 수 있도록 구성되어 있다.

```text
Contextual mapping:
  Grounded / Emotion only / Intent only / None

Scheduling architecture:
  Parallel / Serial
```

여기서 `None`은 FastTrack을 끄는 조건이 아니라, 감정/의도 맥락 참조 없이
분리 pool의 기본 후보와 persona composer만 사용하는 대조군이다.
현재 runtime의 `No FastTrack` 버튼은 별도의 component ablation이며, 이
실험의 `None` 조건으로 사용하면 안 된다.

이 UI는 실험자가 조건을 바꾸는 과정에서 config 파일을 직접 수정하지 않게
해 주며, 선택값은 runtime agent와 latency logger에 즉시 반영된다.

## 10. Limitations

본 초안은 실험 결과를 포함하지 않는다. 따라서 어떤 조건이 실제로 우수한지
주장하지 않는다. 또한 현재 memory는 경량 JSON 기반이므로 장기 의미 기억을
대표하지 않는다. Live2D lip-sync는 현재 음소 단위 viseme 추정이 아니라
오디오 volume 기반 mouth parameter 제어이므로, 발화 내용별 정확한 입 모양을
완전히 재현하지는 않는다. StyleBERT-VITS2 모델은 실시간성 측면에서
선택되었으며, 고품질 voice clone과 동일한 음색 정밀도를 보장하지 않는다.

## 11. Ethical And Reproducibility Considerations

VTuber persona는 특정 실존/상업 캐릭터와 유사한 말투를 사용할 수 있으므로,
연구 보고에서는 모방 대상의 저작권과 퍼블리시티 권리를 침해하지 않는
범위의 일반화된 persona rule로 재정의해야 한다. 또한 음성 모델은 동의된
VoiceSample 기반 학습 자산과 공개/허가된 TTS 자산만 사용해야 한다.

재현성을 위해 데이터셋 원천, GoEmotions/SWDA 분리 유지 원칙, 필터링 기준,
runtime composition template, latency logging schema, runtime config, 모델
fallback 정책을 모두 문서화해야 한다.
실험 결과를 보고할 때는 cold-start latency와 warm-turn latency를 분리하고,
시뮬레이션 수치와 실제 브라우저 audible onset을 구분해야 한다.

## 12. Conclusion

CREDO는 AI VTuber 상호작용에서 생성 지연을 단순히 줄이는 대신, 즉시성
있는 짧은 반응과 병렬 준비된 본문 발화를 결합하여 체감 공백을 줄이는
실험 플랫폼이다. 본 논문 초안은 FastTrack/SlowTrack 분리, 감정 및 대화
행위 기반 반응 선택, 사용자 감정 기반 mouth-safe Live2D 표현 레이어,
StyleBERT-VITS2 실시간 합성, 비동기 프리페치, 조건별 latency logging을 하나의 연구 가능한
프레임워크로 정리했다. 특히 정적 reaction manifest 대신 분리된 원본
데이터셋 pool을 런타임 검색 및 조합에 사용하는 구조를 도입하여, 감정 근거,
대화 행위 근거, persona realization layer의 역할을 실험적으로 분리할 수
있게 했다. 다음 단계는 4 x 2 실험 조건에서 객관 latency와
주관 연속성 평가를 수집하여, 어떤 mapping basis와 scheduling architecture가
방송형 AI 캐릭터의 체감 응답성을 가장 안정적으로 개선하는지 검증하는 것이다.
