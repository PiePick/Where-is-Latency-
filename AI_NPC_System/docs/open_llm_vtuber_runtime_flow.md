# Open-LLM-VTuber 기반 CREDO 런타임 구조

이 문서는 현재 프로젝트가 Open-LLM-VTuber 위에서 어떻게 실행되는지, 그리고 논문에서 시스템 구조를 설명할 때 어떤 단위로 나누어 쓰면 되는지를 정리한다.

## 핵심 정의

현재 시스템은 Open-LLM-VTuber를 화면, 채팅, Live2D, ASR, WebSocket 루프를 담당하는 플랫폼으로 사용한다. CREDO의 연구 기여점은 Open-LLM-VTuber 내부에 새 conversation agent를 추가하여, 일반적인 LLM 응답 전에 감정 기반 레이턴시 커버를 먼저 출력하는 것이다.

즉, Open-LLM-VTuber를 새로 만드는 것이 아니라 다음 연구 모듈을 얹는다.

```text
Viewer input
  -> Open-LLM-VTuber ASR/chat input
  -> CREDO latency-cover agent
  -> FastTrack: emotion, source choice, cached short audio, expression
  -> SlowTrack: local LLM continuation, optional Fish Speech synthesis
  -> Open-LLM-VTuber output queue
  -> Live2D motion/expression + audio + displayed text
```

## 실행 진입점

프로젝트 루트에서 실행한다.

```bash
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

처음 설치 또는 재설치가 필요하면 먼저 실행한다.

```bash
AI_NPC_System/scripts/install_open_llm_vtuber_runtime.sh
```

간단한 상태 확인은 다음 스크립트를 사용한다.

```bash
AI_NPC_System/scripts/smoke_open_llm_vtuber_credo.sh
```

서버가 정상 기동되면 브라우저에서 `http://localhost:12393`을 연다.

## 외부 서버 의존성

Open-LLM-VTuber 자체 서버는 위 스크립트로 실행된다. 다만 SlowTrack 품질을 위해 로컬 LLM 서버와 Fish Speech 서버를 함께 사용하는 구성이 기본이다.

```text
Open-LLM-VTuber server: http://localhost:12393
Primary local LLM:      http://127.0.0.1:8002/v1, llama3.3:70b-awq
Fallback local LLM:     http://127.0.0.1:8001/v1, qwen2.5:7b
Fish Speech TTS API:    http://127.0.0.1:8080/v1/tts
```

환경변수로 모델과 포트를 바꿀 수 있다.

```bash
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1 \
LOCAL_LLM_MODEL=qwen2.5:7b \
AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh
```

Fish Speech 서버가 꺼져 있어도 Open-LLM-VTuber의 기본 TTS fallback이 동작하도록 설계되어 있다. 다만 논문 실험에서 비언어 태그 TTS를 다룰 때는 Fish Speech 서버를 켜고 조건을 고정해야 한다.

## 런타임 파일 역할

```text
AI_NPC_System/fast_track.py
  안정적인 FastTrack facade. 외부 agent는 이 파일의 analyze_and_react를 호출한다.

AI_NPC_System/fast_track_engine.py
  DistilBERT 감정 분류, spaCy 명사 키워드 추출, everyday/stream 반응 선택,
  Fish Speech 비언어 cue 결합, 사전 생성 오디오 cache 조회를 담당한다.

AI_NPC_System/hybrid_reactions.json
  DailyDialog와 GoEmotions에서 추출한 짧은 반응문을 4개 감정 범주와
  everyday/stream 출처로 나눈 최종 반응 리스트다.

AI_NPC_System/fish_speech_nonverbal_cues.json
  Fish Speech에 넣을 수 있는 비언어 태그를 감정 범주별로 정리한 리스트다.

AI_NPC_System/fast_track_audio_cache/manifest.json
  FastTrack에서 즉시 재생할 수 있도록 미리 생성한 짧은 wav 파일의 인덱스다.

AI_NPC_System/slow_track.py
  FastTrack 직후 이어질 고품질 본문 응답을 로컬 OpenAI-compatible LLM에 요청한다.

AI_NPC_System/tts_client.py
  Fish Speech HTTP API에 텍스트를 보내고 wav 파일로 저장한다.

AI_NPC_System/memory_store.py
  LLM 자체 기억이 아니라 외부 JSON 메모리를 관리한다.
```

## Open-LLM-VTuber에 추가되는 부분

통합 스크립트는 `vendor/open-llm-vtuber`에 다음 항목을 적용한다.

```text
src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py
  Open-LLM-VTuber용 CREDO adapter.

characters/credo_latency_cover.yaml
  CREDO character preset. Live2D 모델, agent 선택, expression map을 포함한다.

conf.credo.yaml, conf.yaml
  Open-LLM-VTuber가 CREDO agent를 기본 agent로 사용하도록 하는 설정 파일.
```

원본 Open-LLM-VTuber 코드는 플랫폼이고, CREDO agent가 연구 로직의 연결부다. 논문에는 이 지점을 “platform-level agent injection” 또는 “latency-cover agent layer”로 설명하면 된다.

## 한 턴의 처리 순서

1. 사용자가 채팅 또는 음성으로 입력한다.
2. Open-LLM-VTuber가 텍스트 입력을 CREDO agent에 전달한다.
3. CREDO agent가 `fast_track.analyze_and_react(user_text)`를 먼저 실행한다.
4. FastTrack은 DistilBERT로 4분류 감정을 계산한다.
5. spaCy는 명사/고유명사 키워드를 뽑는다.
6. 키워드는 직접 발화에 붙이지 않고, everyday/stream 반응 출처를 고르는 약한 힌트로만 쓴다.
7. 감정 범주에 맞는 짧은 반응문과 Fish Speech 비언어 cue를 고른다.
8. 사전 생성된 wav가 있으면 바로 `AudioOutput`으로 반환한다.
9. 동시에 같은 감정 범주에 대응하는 Live2D expression action을 같이 보낸다.
10. SlowTrack은 로컬 LLM에 본문 응답을 요청한다.
11. Fish Speech가 켜져 있으면 SlowTrack 텍스트를 wav로 합성한다.
12. 합성 실패 또는 서버 부재 시 Open-LLM-VTuber 기본 TTS로 fallback한다.
13. memory가 켜져 있으면 사용자 입력, FastTrack 반응, SlowTrack 응답, 감정, 키워드를 JSON에 저장한다.

## 논문 관점의 모듈 분리

논문에서는 전체 시스템을 다음 5개 모듈로 나누는 것이 가장 명확하다.

```text
Input interface
  Open-LLM-VTuber chat/ASR input.

Affective interpreter
  DistilBERT GoEmotions 기반 4범주 감정 추론.

Latency-cover selector
  DailyDialog/GoEmotions 반응 리스트, source mix, keyword hint,
  pre-generated TTS cache, nonverbal tag selection.

High-quality response generator
  local LLM SlowTrack, memory context, Fish Speech-aware prompt.

Embodied output layer
  Fish Speech TTS, cached wav, Live2D expression/action, displayed text.
```

이 구조에서 연구의 독립변수는 latency-cover selector의 정책이다. 예를 들면 다음 세 조건을 비교할 수 있다.

```text
No cover
  LLM과 TTS가 끝날 때까지 무반응으로 대기.

Non-affective cover
  감정을 고려하지 않고 고정 또는 무작위 짧은 반응을 출력.

Affective cover
  DistilBERT 감정 범주, source mix, 비언어 태그, Live2D expression을 함께 사용.
```

## 어디를 수정하면 되는가

반응 리스트 정책을 바꾸려면:

```text
AI_NPC_System/fast_track_engine.py
AI_NPC_System/hybrid_reactions.json
```

비언어 태그 정책을 바꾸려면:

```text
AI_NPC_System/tts_cues.py
AI_NPC_System/fish_speech_nonverbal_cues.json
```

SlowTrack LLM 프롬프트를 바꾸려면:

```text
AI_NPC_System/slow_track.py
```

Live2D 감정별 표정 또는 모션을 바꾸려면:

```text
AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml
vendor/open-llm-vtuber/live2d-models/<model>/model_dict.json
```

Open-LLM-VTuber와 CREDO 사이의 연결 방식을 바꾸려면:

```text
AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py
AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py
```

## 유지해야 하는 자료와 정리 가능한 자료

유지해야 하는 자료:

```text
AI_NPC_System/hybrid_reactions.json
AI_NPC_System/fish_speech_nonverbal_cues.json
AI_NPC_System/fast_track_audio_cache/
reaction_sources/raw/
reaction_sources/merged/
vendor/open-llm-vtuber/
vendor/fish-speech/
```

정리해도 되는 자료:

```text
__pycache__/
AI_NPC_System/tts_outputs/
vendor/open-llm-vtuber/logs/
vendor/open-llm-vtuber/conf.yaml.backup
agent_reports/
```

`reaction_sources/raw`는 논문 재현성과 데이터 출처 확인을 위해 보존한다. `vendor/open-llm-vtuber/.venv`와 `vendor/open-llm-vtuber/models`는 용량이 크지만 실행 시간을 줄이기 위해 유지한다.
