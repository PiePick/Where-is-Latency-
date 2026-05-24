# CREDO Research Methodology And Experiment Plan

작성 기준: 2026-05-23 KST

## 연구 문제

CREDO의 핵심 연구 질문은 다음과 같다.

```text
로컬 LLM과 고품질 TTS가 만드는 긴 응답 지연을, 감정 기반의 짧은 선행 반응과
캐릭터 모션으로 덮으면 사용자가 느끼는 대기감과 상호작용 자연스러움이 개선되는가?
```

현재 구현은 Open-LLM-VTuber를 화면, WebSocket, Live2D, 입력 인터페이스로 사용하고,
그 위에 CREDO latency-cover agent를 삽입한다. 한 턴은 FastTrack과 SlowTrack으로
분리된다.

```text
viewer input
  -> FastTrack: emotion + user intent + sampled response act + cached Fish audio + Live2D motion
  -> SlowTrack: local LLM continuation + Fish Speech TTS
  -> embodied output: audio, transcript, expression, motion profile
```

## 연구 기여점 후보

논문에서 주장할 수 있는 기여점은 다음 네 가지로 정리한다.

1. 로컬 LLM/TTS 기반 VTuber 시스템에서 체감 지연을 줄이기 위한 two-stage response architecture
2. 사용자 감정과 대화 의도 전이 확률을 결합한 dataset-grounded FastTrack reaction selection
3. 사전 생성 Fish Speech 음성 번들과 Live2D motion profile을 결합한 embodied latency cover
4. 실시간 시스템 안정성을 위한 GPU 분리, preflight 검증, cached-bundle runtime design

## 시스템 조건

현재 기본 실험 조건은 다음과 같다.

| 항목 | 값 |
| --- | --- |
| UI/runtime | Open-LLM-VTuber |
| FastTrack emotion | GoEmotions 기반 4범주 |
| FastTrack user intent | SWDA coarse intent 6범주 |
| FastTrack response act | SWDA 화자 전환 확률 기반 sampling |
| FastTrack TTS | Fish Speech 사전 생성 wav 600개 |
| SlowTrack LLM | OpenAI-compatible local vLLM, `qwen2.5:7b` |
| SlowTrack TTS | Fish Speech |
| Fish GPU | physical GPU 0 |
| LLM GPU | physical GPU 1 |
| Live2D motion | emotion + style motion profile |
| Memory | JSON 기반 lightweight memory |

## 실험 조건 설계

조건 실행 wrapper:

```bash
AI_NPC_System/scripts/run_experiment_condition.sh affective-cached-fish --profile live
AI_NPC_System/scripts/run_experiment_condition.sh no-cover --profile live
AI_NPC_System/scripts/run_experiment_condition.sh piper-realtime --profile live-piper
```

### 조건 A: No Cover

FastTrack을 끄고 SlowTrack 결과가 준비될 때까지 기다린다.

목적:
레이턴시 커버가 없는 baseline을 만든다.

설정:

```bash
FAST_TRACK_ENABLED=0 AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

기대 결과:
첫 반응까지의 시간이 가장 길고, 사용자가 시스템이 멈춘 것으로 느낄 가능성이 크다.

### 조건 B: Text/Motion Cover

FastTrack 분석과 Live2D motion은 켜되, 사전 생성 음성은 끈다.

목적:
시각적 반응만으로 체감 지연을 줄일 수 있는지 분리해서 본다.

측정:
첫 motion 시점, 첫 텍스트 표시 시점, SlowTrack 음성 시작 시점.

### 조건 C: Non-Affective Audio Cover

감정과 무관하게 고정 또는 무작위 짧은 음성을 먼저 재생한다.

목적:
단순히 소리가 빨리 나오는 효과와 감정 일치 효과를 분리한다.

주의:
현재 기본 구현에는 이 조건이 명시적으로 분리되어 있지 않다. 실험용 flag를 추가하거나
bundle 선택에서 emotion을 neutral로 고정하는 ablation path가 필요하다.

### 조건 D: Affective Cached Fish Cover

현재 기본 조건이다.

동작:
감정, 사용자 의도, sampled response act, 스타일 축을 이용해 600개 사전 생성 wav 중 하나를
즉시 재생한다.

설정:

```bash
FAST_TRACK_ENABLED=1
FAST_TRACK_TTS_MODE=cached_fish_bundle
FAST_TRACK_PERSONA_BUNDLE_ENABLED=1
FAST_TRACK_PERSONA_BUNDLE_FILE=persona_reaction_bundle_response_act_v1/manifest.json
```

기대 결과:
첫 오디오 반응이 가장 빠르며, SlowTrack Fish Speech가 느려도 사용자가 기다리는 동안
캐릭터가 반응 중이라는 신호를 받는다.

## 독립변수

| 독립변수 | 수준 |
| --- | --- |
| latency cover 방식 | none, motion-only, random-audio, affective-audio |
| FastTrack 감정 일치 여부 | matched, neutral, random |
| response act sampling 여부 | copied user intent, SWDA sampled response act |
| TTS 방식 | cached Fish, realtime Fish, lightweight TTS |
| motion 강도 | steady, bright, playful, energetic, low |

## 종속변수

### 시스템 로그 기반

| 지표 | 설명 |
| --- | --- |
| time_to_first_feedback_ms | 사용자 입력부터 첫 텍스트/모션/오디오 중 가장 빠른 feedback까지 |
| time_to_first_audio_ms | 사용자 입력부터 첫 audible output까지 |
| fast_track_analysis_ms | 감정/의도/선택 처리 시간 |
| fast_track_audio_lookup_ms | cached wav 선택 및 반환 시간 |
| slow_track_llm_ms | 로컬 LLM 응답 생성 시간 |
| slow_track_tts_ms | Fish Speech 합성 시간 |
| turn_total_ms | 전체 turn 완료 시간 |
| interruption_count | 사용자가 기다리다 중간에 새 입력을 보낸 횟수 |
| fish_busy_wait_ms | 이전 Fish 요청 때문에 대기한 시간 |

### 사용자 평가 기반

5점 Likert scale로 측정한다.

| 문항 | 측정 의도 |
| --- | --- |
| 응답이 빠르게 시작된 것처럼 느껴졌다 | perceived responsiveness |
| 캐릭터가 내 말에 즉시 반응한다고 느꼈다 | immediacy |
| 선행 반응이 내 입력 감정과 어울렸다 | affective fit |
| 전체 응답이 하나의 자연스러운 turn처럼 느껴졌다 | coherence |
| 목소리와 모션이 캐릭터답게 느껴졌다 | embodiment |
| 기다리는 동안 시스템이 멈춘 것처럼 느껴지지 않았다 | waiting tolerance |

## 로그 포맷

실험 로그는 최소한 다음 구조를 가져야 한다.

```json
{
  "turn_id": "uuid",
  "condition": "affective_cached_fish",
  "input_source": "keyboard|youtube|asr",
  "user_text": "viewer utterance",
  "emotion": "positive|negative|ambiguous|neutral",
  "user_intent": "QUESTION|INFORM|ACKNOWLEDGE|DIRECTIVE|EXPRESSIVE|REJECT",
  "response_act": "QUESTION|INFORM|ACKNOWLEDGE|DIRECTIVE|EXPRESSIVE|REJECT",
  "style_tag": "high-pitched|playful|energetic|smug|cute",
  "fast_audio_path": "...wav",
  "slow_text": "generated continuation",
  "latency": {
    "fast_track_analysis_ms": 0,
    "fast_track_audio_lookup_ms": 0,
    "slow_track_llm_ms": 0,
    "slow_track_tts_ms": 0,
    "turn_total_ms": 0
  }
}
```

## 데이터셋 정당화

FastTrack reaction bundle은 직접 창작한 문장만으로 구성하지 않는다. 연구 재현성을 위해
다음 구조를 따른다.

1. 감정 축은 GoEmotions coarse label에서 가져온다.
2. 의도/응답 행위 축은 SWDA coarse intent에서 가져온다.
3. 사용자 intent를 response act로 그대로 복사하지 않는다.
4. SWDA의 인접 화자 전환 통계에서 response act sampling 분포를 만든다.
5. 고유명사, 브랜드, 장소, 정치/뉴스, 날짜, 숫자, URL, 특정 사건 의존 문장은 필터링한다.
6. LLM은 새 데이터를 무제한 생성하는 역할이 아니라, 필터링된 seed를 짧은 일반 반응으로
   고르는 offline filter/re-writer로 제한한다.
7. Fish Speech는 offline synthesis에 사용하고, runtime에서는 cached wav만 재생한다.

## 현재 구현과 논문 작성 시 주의점

- Fish Speech는 실시간 TTS로는 느리다. 논문에서는 realtime TTS가 아니라 cached expressive
  audio cover로 위치시키는 것이 정확하다.
- FastTrack 텍스트의 `response_act`는 사용자 입력 라벨이 아니라 시스템이 선택한 응답 행위다.
- 스타일 태그는 runtime에 읽히는 텍스트가 아니라 offline synthesis cue다.
- 웃음, 한숨, 감탄사 같은 비언어 이벤트는 bundle 문장에 넣지 않고 별도 timed audio/motion으로
  분리하는 것이 안정적이다.
- 현재 memory는 lightweight JSON injection이며 장기 의미 검색 시스템이 아니다.
- GPU 분리는 `CUDA_VISIBLE_DEVICES`로 Fish와 LLM 프로세스를 분리하는 방식이다.

## 다음 구현 필요 항목

논문 실험 전에 필요한 소프트웨어 작업은 다음 순서가 적절하다.

1. turn-level latency JSONL logger 보강
2. FastTrack response act와 선택된 bundle item을 로그에 명시
3. Fish busy wait와 interrupt event를 별도 지표로 기록
4. 브라우저에서 실제 first audio/motion timestamp를 수집
5. 사용자 평가 form 또는 CSV 템플릿 작성
6. 600개 cached wav 청취 평가용 sample sheet 생성
