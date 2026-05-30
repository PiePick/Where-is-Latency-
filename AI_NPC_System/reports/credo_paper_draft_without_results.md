# CREDO: A Latency-Cover Architecture For Interactive AI VTuber Streaming

작성일: 2026-05-26 KST
최종 업데이트: 2026-05-29 KST
상태: 실험 결과 제외 논문 초안
대상 시스템: CREDO / Open-LLM-VTuber integration

## Abstract

대규모 언어 모델 기반 AI VTuber는 자연스러운 장문 응답을 생성할 수 있지만,
실시간 방송 상황에서는 LLM 추론, 음성 합성, Live2D 렌더링이 누적되며
시청자가 체감하는 침묵 구간이 길어진다. 본 연구는 고품질 TTS 자체의
품질을 높이는 대신, 방송 대화의 인지적 공백을 완화하는 latency-cover
구조를 제안한다. 제안 시스템 CREDO는 입력 채팅을 감정과 대화 행위로
분석한 뒤, 데이터셋 기반의 짧은 FastTrack 반응과 로컬 LLM 기반의
SlowTrack 본문 응답을 분리 운용한다. FastTrack은 GoEmotions
기반 4대 감정 라벨과 SWDA 기반 대화 행위 전이 라벨을 사용하되, 두
원본 데이터셋을 하나의 정적 반응 manifest로 합치지 않는다. 대신 각
데이터셋을 별도의 필터링된 evidence pool로 보존하고, 오프라인 빌드
단계에서 감정 근거와 대응 의도 근거를 검색한 뒤 짧은
persona-consistent cover 문장을 생성한다. 생성된 FastTrack 문장은 같은
StyleBERT-VITS2 음성 모델로 사전 음성화되어, 런타임에서는 텍스트를 다시
합성하지 않고 조건에 맞는 음성 파일을 즉시 선택한다. 이 자산 manifest는
데이터셋을 합친 정적 반응 corpus가 아니라, 각 음성 파일이 어떤 감정 근거와
SWDA 대응 의도 근거에서 나왔는지 보존하는 audio index로 사용된다. 별도의 순수 비언어 감탄사 오디오는 활성 FastTrack 경로에서
제거하고, 사용자 발화에서 분석된 감정 라벨을 기반으로 답변 전체에
Live2D 표정과 몸 모션을 적용한다. 입 파라미터는 오디오 기반 lip-sync가
독점하도록 분리하여, 표정이 유지되는 동안에도 대사에 맞는 입 움직임이
계속 출력되게 한다. SlowTrack은 로컬 LLM, 확장된 연구실 메이드 페르소나,
최근 대화/시청자 맥락/방송 주제 메모리, 실시간 StyleBERT-VITS2 TTS를
사용하여 본문 발화를 생성한다. 병렬 프리페치 스케줄링은 구현 후보로
보존하되, 본 초안의 주 실험에서는 일단 제외하고 직렬 응답 구조에서
FastTrack의 인지적 latency-cover 효과를 먼저 평가한다. 본 논문 초안은
결과를 보고하지 않고, 시스템 구조와 실험 설계만을 기술한다. 실험은
FastTrack 텍스트 검색 기준(Contextual Mapping)과 FastTrack 유무를 중심으로,
감정 근거 검색, SWDA 대응 의도 검색, 두 근거의 동시 사용, 맥락 참조 없는
Neutral Random 대조군, SlowTrack-only 절대 대조군이 VTuber 상호작용의
연속성과 체감 응답성에 미치는 영향을 평가하도록 설계되었다. 실험 자극은
대학원 고민상담 방송 형식으로 고정되며, 도네이션 메시지는 별도의 남성
readout TTS가 끝난 뒤에야 VTuber 입력으로 전달되어 실제 방송에서
후원 음성을 듣고 반응하는 시간 구조를 보존한다.

## Keywords

AI VTuber, latency cover, real-time dialogue, dialogue act, emotion
classification, pre-generated speech assets, Live2D, text-to-speech

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

> 장문의 LLM 응답을 기다리는 동안, 데이터셋 기반으로 사전 음성화된 짧은
> 반응을 먼저 출력하면 AI VTuber의 체감 응답성과 방송 연속성을 개선할 수
> 있는가?

CREDO는 이 질문에 답하기 위한 실험 플랫폼이다. 핵심은 단일 응답 생성
경로가 아니라, 즉시 반응하는 FastTrack과 심층 응답을 담당하는 SlowTrack을
분리하고 두 경로를 방송 타이밍에 맞게 스케줄링하는 것이다.

본 연구는 FastTrack을 무조건적으로 유익한 기능으로 가정하지 않는다.
FastTrack의 효능성은 단순한 물리적 속도 개선이 아니라, 지각된 지연을
줄이면서도 맥락 적합성과 자연스러움을 유의하게 손상시키지 않는지로
정의한다. 따라서 본 연구의 가설은 다음과 같다.

| Hypothesis | Statement |
| --- | --- |
| H1 | 통합 FastTrack은 SlowTrack only보다 perceived latency를 낮춘다. |
| H2 | 통합 FastTrack은 단일 신호 기반 FastTrack보다 맥락 적합성과 자연스러움이 높다. |
| H3 | 사전 음성화된 FastTrack은 실시간 FastTrack TTS보다 첫 audible reaction의 안정성을 높인다. |
| H4 | 맥락 적합성이 낮은 FastTrack은 빠르더라도 어색함을 증가시킬 수 있다. |

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
     -> prebuilt audio lookup from separated GoEmotions/SWDA provenance
     -> immediate StyleBERT wav playback
     -> viewer-emotion Live2D expression/body motion
  -> SlowTrack generation
     -> local LLM persona response
     -> expanded persona / audience / recent-turn memory context
     -> realtime language TTS
  -> playback / mouth-only lip-sync / chat buffering
```

이 구조에서 FastTrack은 “정답”을 말하는 경로가 아니라 방송 공백을 덜
어색하게 만드는 짧은 반응 경로다. SlowTrack은 더 긴 문맥과 캐릭터성을
반영하는 본문 발화 경로다. 두 경로는 같은 턴 안에서 순차적으로 들린다.
병렬 프리페치는 후속 조건으로 보존하지만, 주 실험에서는 FastTrack 자체의
효과를 먼저 분리하기 위해 Serial 구조를 기본으로 둔다.

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

필터링은 persona 문체를 덧씌우기 전에 수행한다. 이는 런타임 조합의 근거가
되는 데이터셋 텍스트 자체의 일반성을 유지하고, 특정 캐릭터 문체가
데이터셋 품질 문제를 가리는 것을 방지하기 위한 절차다. 본 연구는
GoEmotions와 SWDA를 하나의 corpus로 병합하지 않고, source dataset별
provenance를 유지한 상태에서 각 bucket 내부의 후보만 제거한다.

### 4.1.1 Dataset Quality Filtering Protocol

FastTrack evidence pool은 다음 기준을 순차적으로 적용해 정제했다.

| Filter category | Exclusion rule | Rationale |
| --- | --- | --- |
| Provenance preservation | GoEmotions와 SWDA를 병합하지 않고 각 source bucket 안에서만 제거 | 감정 근거와 대화 행위 근거의 기여를 분리해 해석하기 위함 |
| Response-act safety | SWDA `QUESTION`은 output response act에서 제외 | 짧은 cover 발화가 질문으로 끝나 SlowTrack 답변과 충돌하는 문제 방지 |
| Specificity filter | 고유명사, 브랜드/플랫폼명, 날짜, 금액, 숫자, 스포츠·게임·영화·정치·뉴스 등 특정 상황 의존 표현 제거 | 일반적인 VTuber 방송 상황에서 재사용 가능한 반응만 유지 |
| Safety filter | 욕설, 선정적 표현, 폭력·자해·혐오 표현 제거 | 실험 자극의 안전성과 IRB/설문 적합성 확보 |
| Greeting/closing filter | `hi`, `hello`, `hey`, `yo`, `sup`, `good morning`, `how are you`, `what's up`, `long time no see`, `goodbye`, `see you`, `take care`, `thanks`, `cheers` 등 대표 인사말과 마무리 표현 제거 | FastTrack은 방송 시작/종료 인사가 아니라 현재 채팅에 대한 짧은 반응이어야 함 |
| Filler/laughter filter | `ah`, `oh`, `um`, `hm`, `haha`, `ahaha`, `lol`, `lmao`, 이모티콘, 독립 감탄사 제거 | 별도 감탄사 오디오와 혼동되는 비언어 filler를 제거하고 언어 반응만 남김 |
| Fragment/noise filter | 소문자로 시작하는 파편, 미완성 문장, 철자 손상, 의미가 끊긴 문장, 전화 대화 잔여 표현 제거 | 자막/음성으로 송출될 때 문장 완결성과 이해 가능성 보장 |
| Hidden-context filter | 특정 인물, 이전 대화, 외부 사건을 알아야만 이해되는 발화 제거 | 150초 고정 방송 시나리오 안에서 독립적으로 이해 가능한 반응 유지 |
| Local LLM quality pass | 로컬 LLM이 standalone FastTrack 반응으로 부적절하다고 판단한 후보 제거 | 규칙 기반 필터가 놓치는 맥락 의존성, 부자연스러운 문장, 일반성 부족 보완 |
| Audio-index alignment | 남은 source item이 파생 prebuilt audio index와 연결될 수 있는지 확인 | 텍스트 선택 후 런타임에서 missing audio fallback이 발생하지 않도록 보장 |

필터링 이후 현재 검증된 separated evidence pool은 GoEmotions `385`개,
SWDA `244`개 항목이다. GoEmotions bucket은 `POSITIVE=141`,
`NEGATIVE=133`, `SURPRISE=23`, `NEUTRAL=88`로 구성되며, SWDA bucket은
`INFORM=199`, `ACKNOWLEDGE=3`, `DIRECTIVE=18`, `EXPRESSIVE=14`,
`REJECT=10`으로 구성된다. SWDA `QUESTION` output 항목은 `0`개다.
대표 인사말/마무리 표현 잔존 스캔은 `0`건으로 확인되었다. 이 수치는
실험 결과가 아니라 방법론적 데이터 준비 상태를 나타내는 재현성 정보다.

### 4.2 Build-Time Persona Cover And Audio Assetization

FastTrack 텍스트는 원본 데이터셋 문장을 그대로 읽지 않는다. 오프라인
빌드 단계에서 다음 순서로 후보 문장을 만들고, 동일한 StyleBERT-VITS2
음성 모델로 wav 파일을 사전 생성한다.

```text
detected emotion
  + transitioned non-question response act
  + retrieved GoEmotions evidence
  + retrieved SWDA evidence
  -> Professor's Lab Maid cover template
  -> short spoken FastTrack text
  -> prebuilt StyleBERT wav + provenance metadata
```

persona는 실존 캐릭터 모방 대신 “교수님의 연구실에서 일하는 랩실 메이드”
설정으로 일반화했다. 발화는 논문, 실험, 교수님 메시지, 커피, 마감, 연구실
노트 같은 소재를 가볍게 사용하지만, 정적 접미사나 강제 catchphrase를
사용하지 않는다. 이 방식은 데이터셋 근거와 persona 표현을 분리한다는 점에서
학술적으로 중요하다. 감정 및 대화 행위의 근거는 원본 데이터셋에서 오고,
캐릭터성은 별도의 realization layer에서 적용되므로, 실험자가 어느 층이
체감 응답성에 기여했는지 더 명확히 분석할 수 있다.

교수 피드백 이후의 핵심 변경은 FastTrack을 더 이상 매 턴 실시간 TTS로
합성하지 않는다는 점이다. 런타임에서는 선택된 FastTrack 텍스트와 연결된
사전 생성 wav를 즉시 전달한다. 따라서 FastTrack의 time-to-first-audio는
TTS 서버 warm/cold 상태에 덜 의존하며, 실험 조건 간 차이는 음성 합성
지연이 아니라 어떤 근거로 짧은 반응을 골랐는지에 더 집중된다. 다만 이
audio manifest는 예전의 600문장 정적 persona manifest와 다르다. 각 항목은
`emotion`, `response_act`, `selection_policy`, `source_item_ids`,
`audio_path`를 보존하는 재현성 index이며, GoEmotions와 SWDA 근거를 하나의
원본 데이터셋으로 합치지 않는다.

FastTrack 텍스트 선택은 네 가지 방식으로 전환된다.

| Condition | Lookup basis |
| --- | --- |
| Grounded | emotion + transitioned response act |
| Emotion Only | emotion only |
| Intent Only | transitioned response act only |
| Neutral Random | context-free neutral FastTrack control without emotion/intent lookup |

Grounded 조건에서는 GoEmotions 감정 pool과 SWDA 대응 의도 pool을 모두
검색한다. Emotion Only는 SWDA 대응 의도 근거를 제거하고 DistilBERT /
GoEmotions 감정 신호와 감정 evidence pool만을 사용한다. Intent Only는
감정 근거를 제거하고 SWDA intent classifier 및 전이된 response act에
해당하는 evidence pool만을 사용한다. Neutral Random은 FastTrack을 끄는
조건이 아니라, 감정/의도 맥락 참조를 제거하고 neutral 계열 후보를 사용하는
낮은 맥락 적합성 대조군이다. FastTrack을 완전히 제거하는 조건은 별도의
SlowTrack-only 절대 대조군으로 둔다.

현재 검증된 separated pool은 GoEmotions 385개 항목과 SWDA 244개 항목으로
구성된다. 따라서 Grounded 조건에서 FastTrack 후보가 짧은 시간
안에 반복되는 현상은 정상적인 조합 공간의 한계라기보다, 검색 후보를 너무
좁게 순회했거나 필터링 후 남는 spoken realization 품질이 부족하다는 신호로
해석해야 한다. 본 연구에서 Grounded lookup은 같은 rank의 감정 후보와
대응 행위 후보를 단순히 1:1로 묶는 방식이 아니라, 감정 evidence와
response-act evidence의 cross-pair 공간을 순회한 뒤 짧은 발화로 실현하는
방식으로 정의한다.

### 4.3 Vector Search And Runtime Audio Lookup

각 source pool 항목은 간단한 해시 기반 벡터로 임베딩되며, FAISS가 사용
가능한 환경에서는 라벨별 IndexFlatIP 인덱스를 사용한다. FAISS가 없으면
동일 벡터에 대한 NumPy 내적 검색으로 대체된다. 이는 외부 모델 다운로드
없이도 재현 가능한 in-memory 검색을 보장하기 위한 선택이다.

검색은 각 pool에서 충분한 폭의 후보 근거를 반환하고, build-time composer는
선택 정책에 따라 짧은 반응 후보와 해당 음성 파일을 만든다. Grounded 정책에서는
GoEmotions 후보와 SWDA 후보를 같은 순위끼리만 결합하지 않고, 두 후보
목록의 cross-pair를 순회한다. 반환 metadata에는 사용된 GoEmotions 항목과
SWDA 항목의 ID가 분리되어 남는다. 이 구조는 단순 random 선택보다 입력
발화와 근거 텍스트 간의 어휘적 관련성을 보존하면서, 런타임에서는 해당
후보의 wav를 즉시 선택할 수 있게 한다.

반복 후보 처리는 스케줄링 요인과 분리한다. Serial 조건에서는 최근 후보와
겹친다는 이유만으로 FastTrack을 생략하지 않는다. 그렇지 않으면 Case 1-4의
비교가 "어떤 mapping이 더 적합한가"가 아니라 "어떤 조건에서 FastTrack이
나왔는가"로 오염되기 때문이다. Parallel 조건의 FastTrack 우회와 prefetch
queue 사용은 구현 후보로 남기지만, 본 초안의 주 실험 해석에서는 제외한다.

spaCy 기반 키워드 추출은 현재 입력 grounded metadata 및 source-bias
신호로만 유지한다. 이전 구현의 spoken keyword echo prefix는 현재 primary
study에서 중단되어 있으며, FastTrack 발화 앞에 별도의 키워드 반복 문장을
붙이지 않는다. 이는 Emotion Only / Intent Only / Neutral Random 조건을
해석할 때 추가적인 lexical echo 변수가 섞이지 않게 하기 위한 통제다.

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

교수 피드백 이후 SlowTrack은 지나치게 짧은 챗봇 프롬프트가 아니라
방송형 VTuber의 실제 생성 부담을 반영하도록 확장된다. 프롬프트는
연구실 메이드 페르소나, computer graphics 연구실 세계관, 대학원
고민상담 방송 형식, 최근 도네이션/채팅 요약, 시청자별 반복 주제, 진행 중인
방송 segment, 금지된 filler/catchphrase 규칙을 함께 포함한다. 이 변화는
임의로 sleep을 넣어 지연을 만드는 것이 아니라, 실제 VTuber 에이전트가
세계관 일관성, 기억, 대상 시청자 인식, 방송 흐름을 유지하기 위해 처리해야
하는 문맥 부하를 모델링하기 위한 것이다. 따라서 SlowTrack 지연은 단순한
결함이 아니라 FastTrack latency-cover가 필요한 연구 상황의 일부로 정의된다.

언어 TTS는 현재 StyleBERT-VITS2 `credo_voice_sample_en` 모델을 사용한다.
Fish Speech와 CosyVoice2는 음색 품질 실험에는 유용했지만, 실시간 방송
상호작용에서는 지연이 커 primary live 조건에서 제외했다. StyleBERT-VITS2는
FastTrack 사전 생성 wav와 SlowTrack 실시간 합성에 동일한 음색 경로를
제공하여, 짧은 반응과 본문 발화 사이의 음성 일관성을 유지한다.

## 6. Scheduling Architecture

CREDO는 병렬 프리페치 구조를 구현 후보로 보유하지만, 현재 주 실험에서는
일단 제외한다. 이유는 FastTrack을 사전 음성화한 이후에는 첫 반응 지연의
가장 큰 변수가 스케줄링보다 “어떤 근거로 어떤 FastTrack을 선택했는가”로
이동했기 때문이다. 또한 병렬 프리페치는 FastTrack이 생략되거나 우회되는
턴을 만들 수 있어, Contextual Mapping 효과를 먼저 검증하는 단계에서는
해석을 오염시킬 수 있다.

| Scheduling condition | Definition |
| --- | --- |
| Serial | 주 실험 조건. 현재 발화가 끝난 뒤 다음 입력 처리와 응답 생성을 시작 |
| Parallel | 후속 확장 조건. 현재 오디오 재생 중 다음 SlowTrack 발화를 백그라운드에서 준비 |

Serial 조건은 본 연구의 기본 관찰 조건이다. 발화가 종료된 후에야 다음
입력을 처리하고 본문을 생성하므로, 사전 음성화 FastTrack이 실제 침묵
구간을 얼마나 줄이는지 가장 직접적으로 관찰할 수 있다.

Parallel 조건은 폐기하지 않는다. SlowTrack이 재생되는 동안 채팅을 buffer에
누적하고 다음 idle/context 발화를 준비하는 구조는 방송형 에이전트에 여전히
유용하다. 다만 본 초안에서는 이를 주 비교 조건에서 빼고, FastTrack
매핑과 사전 음성화의 효과를 확인한 뒤 후속 연구 또는 부가 실험으로 다룬다.

도네이션 이벤트는 별도의 temporal gate를 갖는다. 브라우저는 먼저
도네이션 overlay와 남성 Edge TTS readout을 재생하고, readout 재생이
완료된 이후에만 `/credo/vtuber-mode/donation`으로 VTuber 입력을 보낸다.
따라서 도네이션 조건에서 측정되는 응답 지연은 “후원 음성 청취 후 캐릭터가
답변을 준비하는” 방송형 상호작용 절차를 모사한다. readout 생성 또는 재생이
실패하면 해당 도네이션의 VTuber 답변은 큐에 넣지 않는다.

## 7. Experiment Design

본 연구의 주요 실험은 FastTrack의 맥락 매핑 기준을 비교하는 조건과
FastTrack을 제거한 절대 대조군으로 구성된다. 병렬 프리페치 조건은 구현
후보로 유지하지만, 현재 초안의 주 실험에서는 제외한다. 모든 조건은 동일한
150초 방송 시나리오를 사용하고, 차이는 사전 음성화 FastTrack을 어떤
근거로 선택하는지와 FastTrack을 사용할지 여부에만 둔다.

### 7.1 Factor 1: Contextual Mapping

FastTrack 텍스트를 선택할 때 어떤 정보를 기준으로 사용할지 비교한다.

| Level | Description |
| --- | --- |
| Emotion Only | 감정 라벨만 사용 |
| Intent Only | SWDA 전이 기반 대응 의도만 사용 |
| Grounded | 감정과 대응 의도를 모두 사용 |
| Neutral Random | 감정/의도 참조 없이 neutral 후보에서 FastTrack 생성 |

이 요인은 짧은 cover 반응의 내용 적합성을 평가한다. 감정만 맞는 반응이
충분한지, 대화 행위만 맞아도 자연스러운지, 둘을 결합할 때 가장 나은지
검증할 수 있다. 또한 Neutral Random 조건은 H4를 검증하기 위해 포함된다.
즉, 빠른 반응이더라도 맥락 적합성이 낮으면 침묵보다 더 어색할 수 있는지
관찰한다.

이 비교에서 핵심 종속 변수는 FastTrack의 단순 발생 횟수가 아니라, 지각된
지연 감소와 맥락 적합성의 균형이다. 따라서 Case 1-4의 Serial 조건에서는
후보 반복을 이유로 FastTrack 자체를 생략하지 않는다. 반복 빈도는 별도의
품질 로그로 남기되, mapping 조건 간 주효과를 FastTrack on/off 차이와
혼동하지 않도록 통제한다.

### 7.2 Secondary Factor: Scheduling Architecture

SlowTrack 준비를 언제 시작할지 비교한다.

| Level | Description |
| --- | --- |
| Serial | 주 실험 기본값. 재생 종료 후 다음 응답 준비 |
| Parallel | 후속 확장. 재생 중 다음 응답 준비 |
| SlowTrack Only | FastTrack 없이 SlowTrack 본문 생성만 사용 |

이 요인은 실제 물리적 latency와 사용자의 인지적 대기 시간을 분리해서
관찰하기 위한 보조 요인이다.

Parallel 조건은 도네이션 반응을 즉시 수행하는 동안 최근 채팅을 모아 다음
SlowTrack 발화를 준비하는 구조를 모델링한다. 사람이 라이브 방송에서 짧게
반응하면서도 다음 설명을 생각하는 과정과 유사한 아키텍처적 강점을 검증하기
위한 조건이다. 이때 준비된 SlowTrack이 바로 이어지면 FastTrack이 생략되거나
짧게 우회될 수 있으며, 이는 Contextual Mapping 요인이 아니라 Scheduling
Architecture 요인으로 기록한다. 다만 본 연구의 첫 평가에서는 이 변수를
고정하거나 제외하여, 사전 생성 FastTrack audio의 효과를 우선 확인한다.

### 7.3 Primary Run Set

실제 녹화 및 1차 평가에 사용하는 조건은 다음 5개다.

| Case | Condition | Role |
| --- | --- | --- |
| 1 | Grounded + Serial | 통합 FastTrack 기본형 |
| 2 | Emotion Only + Serial | 감정 단일 신호 대조군 |
| 3 | Intent Only + Serial | 의도/대응 행위 단일 신호 대조군 |
| 4 | Neutral Random + Serial | 낮은 맥락 적합성 / 실패 조건 |
| 5 | SlowTrack Only | FastTrack 없음 / 절대 대조군 |

`Grounded + Parallel`은 현재 구현상 유지할 수 있는 후속 비교 조건이지만,
교수 피드백 이후 1차 실험에서는 보류한다.

### 7.4 Shared Broadcast Scenario

모든 조건은 동일한 약 150초 길이의 가상 방송 시나리오를 사용한다. 시나리오는
오프닝 독백을 생략하고 약 3초 지점의 첫 도네이션 고민상담으로 시작한다.
현재 시나리오는 고정된 10명의 반복 시청자 닉네임을 사용하며, 도네이션은
짧은 방송용 문장으로 제한한다. 핵심 입력은 다음과 같다.

| Time | Event | Summary |
| --- | --- | --- |
| T+3s | Donation | `I deleted the experiment logs. Should I confess before the professor reaches my desk?` |
| T+60s | Donation | `He rejected my figure. Then he fixed my dataset script.` |
| T+60.4s-62.4s | Chat wave | `LOL`, `lmao`, `HAHAHAHA`, `XD XD XD`, `www` 등 웃음 반응 |
| T+90s | Donation | `My stipend vanished into rent and conference fees. Is free seminar pizza the official grad school meal plan?` |
| T+96s-142s | Chat reactions | 걱정, 공감, 조언 수용, 종료 반응 |

이 시나리오는 “대학원 고민상담 콘텐츠”라는 상위 형식을 유지하되, 페르소나의
기본 주제를 교수 연구실, 특히 computer graphics research lab으로 고정한다.
따라서 idle 또는 topic이 불명확한 구간에서도 게임, 영화, 일반 취미가 아니라
rendering, shaders, animation, simulation, paper revision, professor message,
deadline bell 같은 연구실 소재로 발화를 이어 가도록 설계된다. 도네이션은
별도의 queue를 통해 순차 재생되며, 남성 readout 중 도착한 VTuber audio
payload는 motion/subtitle scheduling 전에 폐기된다. 도네이션이 기존 VTuber
발화를 중단할 때는 오디오뿐 아니라 Live2D 입 파라미터 pulse도 즉시 중단하여
음성이 끊긴 뒤 입 모양이 뒤늦게 움직이는 현상을 방지한다.

### 7.5 Controlled Variables

실험 간 비교 가능성을 위해 다음 요소는 고정한다.

- 동일한 Open-LLM-VTuber frontend 및 Live2D 출력 경로
- 동일한 StyleBERT-VITS2 음색 모델
- 동일한 사전 생성 FastTrack audio bundle
- 동일한 SlowTrack LLM 설정과 persona prompt
- 동일한 분리 필터링 데이터셋 pool
- 동일한 사용자 감정 기반 mouth-safe Live2D expression/motion mapping
- 동일한 latency logging schema

## 8. Measurement Plan

객관 지표는 session-stamped
`AI_NPC_System/latency_logs/<session>.module_events.csv`에 기록된다.
각 row에는 `experiment_run_id`, `experiment_factor`, `scenario`,
`component_mode`, `selection_policy`, `scheduling_mode`, `runtime_mode`,
`event`가 함께 저장되어 실험 조건이 섞이지 않게 한다.

주요 모듈 지표는 다음과 같다.

| Metric | Meaning |
| --- | --- |
| fasttrack_analysis | 감정/의도/전이/검색 시간 |
| fasttrack_audio | 사전 생성 FastTrack wav lookup 및 전달 |
| emotion_motion_payload | 감정 기반 표정/몸 모션 action 전달 |
| slowtrack_llm | 본문 LLM 응답 생성 |
| slowtrack_tts | 본문 TTS 합성 |
| turn_total | 전체 턴 완료 시간 |
| time to first audible reaction | 브라우저 재생 기준 첫 audible onset |

### 8.1 Subjective Questionnaire

객관 latency log만으로는 FastTrack의 핵심 효과를 충분히 설명할 수 없다.
본 연구가 측정하려는 것은 실제 처리 시간이 아니라, 시청자가 방송 흐름을
어떻게 지각하는지이기 때문이다. 따라서 각 실험 영상 시청 직후 7점 Likert
척도 설문을 수행한다. 척도는 1점 “전혀 그렇지 않다”, 4점 “보통이다”,
7점 “매우 그렇다”로 정의한다. 모든 영상을 시청한 뒤에는 조건 간 직접
비교 문항에 응답한다.

핵심 주관 지표는 다음 여섯 가지다.

| Priority | Construct | Meaning |
| --- | --- | --- |
| 1 | Perceived Latency / 체감 지연 시간 | 응답 대기 시간이 얼마나 짧고 자연스럽게 느껴졌는가 |
| 2 | Reaction Appropriateness / 리액션 적절성 | FastTrack 리액션이 사용자 발화의 의미와 맥락에 맞는가 |
| 3 | Conversational Naturalness / 대화 자연스러움 | FastTrack과 SlowTrack을 포함한 전체 대화 흐름이 자연스럽게 이어지는가 |
| 4 | Social Presence / 사회적 존재감 | VTuber가 실제로 듣고 반응하는 존재처럼 느껴지는가 |
| 5 | Engagement / 몰입 및 지속 시청 의도 | 시청자가 대화 상황에 몰입하고 계속 보고 싶어 하는가 |
| 6 | Character Appeal / 캐릭터 매력도 | 리액션과 응답이 캐릭터성 및 호감도를 강화하는가 |

문항-지표 매핑은 다음과 같다.

| Construct | Items | Questionnaire statements |
| --- | --- | --- |
| Perceived Latency | q1-q3 | q1: 사용자 채팅 이후 기다리는 시간이 짧게 느껴졌다. q2: AI VTuber가 멈춘 것이 아니라 반응하고 있다는 느낌이 들었다. q3: 대화 중 침묵이나 공백 때문에 답답했다. q3는 역문항이다. |
| Conversational Naturalness | q4-q5 | q4: AI VTuber와 시청자 사이의 대화 흐름이 자연스럽게 느껴졌다. q5: 전체 대화 장면이 실제 방송 상황처럼 자연스럽게 보였다. |
| Reaction Appropriateness | q6-q8 | q6: 리액션이 단순한 시간 끌기가 아니라 의미 있는 반응처럼 느껴졌다. q7: 리액션이 무작위로 나온 것처럼 느껴졌다. q7은 역문항이다. q8: 짧은 리액션이 이후 본 응답으로 자연스럽게 이어졌다. |
| Social Presence | q9-q10 | q9: AI VTuber가 시청자의 말을 실제로 듣고 있는 것처럼 느껴졌다. q10: AI VTuber가 실제 방송자처럼 상호작용하고 있는 것처럼 느껴졌다. |
| Character Appeal | q11-q12 | q11: AI VTuber가 캐릭터로서 매력적으로 느껴졌다. q12: AI VTuber의 리액션이 캐릭터성을 강화했다. |
| Engagement | q13-q14 | q13: 영상을 보는 동안 대화 상황에 몰입할 수 있었다. q14: 영상 속 AI VTuber의 반응을 더 보고 싶었다. |

모든 영상 시청 후에는 세 개의 최종 비교 문항을 추가한다.

| Item | Purpose |
| --- | --- |
| q15 | 가장 대화 흐름이 자연스럽게 느껴진 영상 선택 |
| q16 | 가장 어색하거나 불편했던 영상 선택 |
| q17 | 가장 리액션이 맥락에 잘 맞는 영상 선택 |

해석에서는 construct별 평균을 사용하되, 역문항 q3과 q7은 반전 채점한다.
Grounded FastTrack의 효과는 q6, q7, q8, q15, q17에서 특히 강하게 확인한다.
사전 음성화 FastTrack의 latency-cover 효과는 q1, q2, q3과 objective
time-to-first-audible-reaction 로그를 함께 사용해 해석한다. SlowTrack-only
조건의 한계는 낮은 Perceived Latency 점수와 q16 선택 비율에서 확인한다.
Parallel scheduling 관련 문항 해석은 후속 실험에서만 사용하며, 현재 1차
실험에서는 보조 분석으로 남긴다.

## 9. Implementation Notes

시스템은 실험 중 멈추지 않는 것을 우선한다. 따라서 모든 ML 모듈은 가능한
로컬 모델을 사용하되, 실패 시 규칙 기반 fallback으로 내려간다. FAISS가
없으면 NumPy 검색으로 대체된다. TTS 서버와 LLM 서버는 runtime readiness
검사 대상이며, 실패 시 어떤 모듈이 준비되지 않았는지 명시한다.

현재 UI는 실험 요인을 직접 버튼으로 바꿀 수 있도록 구성되어 있다.

```text
Experiment cases:
  Case 1 Grounded / Serial
  Case 2 Emotion Only / Serial
  Case 3 Intent Only / Serial
  Case 4 Neutral Random / Serial
  Case 5 None / SlowTrack Only

Manual factor controls:
  Contextual mapping: Grounded / Emotion only / Intent only / Neutral random
  Scheduling architecture: Serial / No FastTrack
  Parallel: retained for follow-up, not primary recording
```

실험 녹화에서는 수동 factor 조합보다 Case 버튼을 사용하는 것이 안전하다.
Neutral Random은 FastTrack이 켜진 상태에서 맥락 적합성을 낮춘 대조군이고,
Case 5의 `None / SlowTrack Only`는 FastTrack을 완전히 끄는 절대 대조군이다.
이 둘은 H4 해석에서 반드시 분리되어야 한다.

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
fallback 정책을 모두 문서화해야 한다. 특히 필터링 과정은 단순한 임의 삭제가
아니라 source별 bucket을 보존한 상태에서 적용한 exclusion protocol이므로,
최종 논문에는 제거 기준, 최종 bucket count, greeting/filler 잔존 스캔,
validation 결과를 함께 보고해야 한다.
실험 결과를 보고할 때는 cold-start latency와 warm-turn latency를 분리하고,
시뮬레이션 수치와 실제 브라우저 audible onset을 구분해야 한다.

## 12. Conclusion

CREDO는 AI VTuber 상호작용에서 생성 지연을 단순히 줄이는 대신, 즉시성
있는 짧은 반응과 심층 본문 발화를 분리하여 체감 공백을 줄이는
실험 플랫폼이다. 본 논문 초안은 FastTrack/SlowTrack 분리, 감정 및 대화
행위 기반 반응 선택, 사용자 감정 기반 mouth-safe Live2D 표현 레이어,
StyleBERT-VITS2 기반 사전 생성 FastTrack audio, 확장된 SlowTrack
페르소나/메모리 프롬프트, 조건별 latency logging을 하나의 연구 가능한
프레임워크로 정리했다. 특히 정적 reaction corpus 대신 분리된 원본
데이터셋 pool에서 후보를 만들고 그 provenance를 보존한 audio index를
사용하여, 감정 근거, 대화 행위 근거, persona realization layer의 역할을
실험적으로 분리할 수 있게 했다. 다음 단계는 5개 대표 조건에서 객관
latency와 주관 연속성 평가를
수집하여, FastTrack이 지각된 지연을 낮추면서도 맥락 적합성과 자연스러움을
해치지 않는 조건이 무엇인지 검증하는 것이다.
