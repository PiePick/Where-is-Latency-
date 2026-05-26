# CREDO Team Codex Context

이 프로젝트는 Open-LLM-VTuber 위에 실시간 VTuber latency-cover agent를
구현하는 연구 코드다. `CODEX_SETUP.md`를 설치/실행 기준 문서로 사용한다.

## Shared Worklog

새 Codex 채팅은 작업 전에 반드시 `CODEX_SHARED_WORKLOG.md`를 먼저 읽는다.
작업을 마치거나 중요한 결정을 내리면 같은 파일에 최신 항목을 추가한다.
Notion 접근이 불안정할 때는 이 파일을 채팅 간 핸드오프 기준으로 사용한다.

## Current Decision: 2026-05-27

실시간 언어 TTS는 StyleBERT-VITS2 `credo_voice_sample_en`이다.
Fish Speech와 CosyVoice2의 실시간 언어 합성은 라이브 런타임에서 제외한다.
순수 감탄사+모션도 현재 live 자산은 StyleBERT 기반 사전 생성 음원이다.

- Fish Speech: 20단어 SlowTrack 합성 약 `49.7 s`, 전체 턴 약 `51.1 s`.
- CosyVoice2: 짧은 샘플은 약 `4.0 s`였으나 긴 밝은 샘플은 약 `27.7 s`.
- 결론: 음색 복제보다 지속적인 방송 대화 응답성을 우선한다.

StyleBERT-VITS2는 현재 선택된 빠른 영어 음성 경로이고 Fish 스타일 태그를
사용하지 않는다. 순수 감탄사는 미리 생성하며, 실제 실시간 latency는
라이브 실행 로그로 측정한다.

## Active Architecture

```text
buffered virtual/YouTube chat or idle trigger
  -> FastTrack analysis
     DistilBERT emotion + SetFit/SWDA response-act sampling
     + separated GoEmotions/SWDA dataset-pool retrieval
     + Professor's Lab Maid runtime cover composition
  -> prebuilt StyleBERT nonverbal+motion and/or StyleBERT realtime language speech
  || SlowTrack local LLM generation + StyleBERT synthesis/prefetch
  -> SlowTrack playback
  -> while speaking, buffer chat and prefetch the next idle segment
```

FastTrack 언어 반응은 더 이상 미리 생성한 wav를 검색해 재생하지 않는다.
기존 persona manifest 방식도 active runtime에서 비활성화했다.
`professor_lab_maid_dataset_pool_v1/pool.json`은 GoEmotions와 SWDA를
분리 보존한 데이터셋 기반 evidence pool이며, 선택된 evidence를 현재 persona
cover composer로 감싼 뒤 매 턴 실시간 합성한다.
`spaCy` keyword echo는 primary study에서 비활성화되어 있고, 키워드는 분석
metadata로만 남긴다.
순수 감탄사는 `expressive_interjection_bundle`의 StyleBERT wav를 바로 재생하며,
실시간 언어 TTS 합성 대상으로 보내지 않는다.

## Runtime Rules

- 관객에게 발화하는 문장은 영어만 사용한다.
- `[happy]`, `[playful]`, `[pause]` 같은 태그를 TTS text에 삽입하지 않는다.
- Live2D motion은 감정/스타일 메타데이터로 처리한다.
- `FAST_TRACK_TTS_MODE=stylebert_vits2`
- `FAST_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=0`
- `OPEN_LLM_VTUBER_TTS_MODEL=stylebert_vits2`
- `OPEN_LLM_VTUBER_SLOW_TTS_MODE=open_llm`
- `SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=0`
- `FAST_TRACK_PREBUILT_ONLY=0`
- `FAST_TRACK_KEYWORD_ECHO_ENABLED=0`
- `CREDO_VTUBER_SLOW_PREFETCH_ENABLED=1`

## Required Runtime

- `vendor/open-llm-vtuber/.venv` with `transformers`, `spacy`,
  `setfit`, and `en_core_web_sm`
- `vendor/Style-Bert-VITS2` with `credo_voice_sample_en`
- local OpenAI-compatible LLM at `http://127.0.0.1:8001/v1`, default
  served name `qwen2.5:7b`
- CREDO integration activated into the vendored Open-LLM-VTuber tree

Fish Speech 서버와 checkpoint는 live 실행 중 불필요하지만,
`expressive_interjection_bundle` wav 파일은 비언어 factor의 필수 자산이다.

## Run And Verify

```bash
cd /mnt/c/Users/CGLAB/Desktop/CREDO
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate
vendor/open-llm-vtuber/.venv/bin/python \
  AI_NPC_System/scripts/check_runtime_readiness.py
AI_NPC_System/scripts/run_credo_stack.sh --profile live
```

브라우저에서 `http://127.0.0.1:12393`을 열고 CREDO VTuber panel에서
두 실험 요인을 선택한다. 기본 후보는 `Grounded` contextual mapping과
`Parallel` scheduling이다. 모듈 단위 측정은
선택 요인 라벨과 함께 `AI_NPC_System/latency_logs/module_events.csv`에 누적된다.

## Engineering Guardrails

- 통합 source를 수정한 후 반드시 `apply_integration.py --activate`를 실행한다.
- 현재 연구 조건에서 Fish/Piper 서버를 `live` 프로필의 요구사항으로 되돌리지 않는다.
- separated dataset pool의 라벨/문장 필터링 근거는 보존한다. 비언어 factor가
  활성화된 경우에는 StyleBERT 감탄사 wav 존재 여부를 readiness로 검사한다.
- 메모리는 최근 턴을 prompt에 삽입하는 lightweight JSON memory이며 장기
  지식 저장소로 과장하지 않는다.
