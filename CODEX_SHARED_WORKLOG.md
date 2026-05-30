# CREDO Codex Shared Worklog

이 파일은 여러 Codex 채팅이 같은 CREDO 프로젝트에서 작업할 때 공유하는
단일 핸드오프 로그다. Notion 커넥터가 불안정해도 이 파일은 repo 안에서
항상 읽고 갱신할 수 있다.

## Working Rule

새 Codex 채팅은 작업 시작 전에 이 파일을 먼저 읽는다. 작업을 마치거나
중요한 결정을 내리면 아래 형식으로 최신 항목을 위에 추가한다.

```text
## YYYY-MM-DD HH:MM KST - Scope

- Owner/chat: framework/runtime | voice/TTS | docs/report | cleanup | other
- User request:
- Done:
- Verification:
- Files touched:
- Next handoff:
- Do not touch:
```

규칙:

- 긴 터미널 로그를 붙이지 말고 핵심 수치와 파일 경로만 남긴다.
- 다른 채팅이 맡은 범위는 건드리지 않는다.
- dirty worktree에서 사용자/다른 채팅 변경을 되돌리지 않는다.
- 음성 샘플, VoiceSample, 음색 비교는 voice/TTS 채팅 범위다.
- framework/runtime 채팅은 페르소나, 매니페스트, 라우터, Open-LLM-VTuber
  통합, 실행 안정성만 다룬다.

## 2026-05-29 03:35 KST - Paper Draft Dataset Filtering Update

- Owner/chat: framework/runtime
- User request:
  - Summarize all filtering criteria just applied and update the paper.
- Done:
  - Updated `AI_NPC_System/reports/credo_paper_draft_without_results.md` with a
    dedicated `Dataset Quality Filtering Protocol` subsection.
  - Updated `AI_NPC_System/docs/research_methodology_experiment_plan.md` with
    the same method-level criteria and latest bucket counts.
  - Current paper-visible counts: GoEmotions `385`
    (`POSITIVE=141`, `NEGATIVE=133`, `SURPRISE=23`, `NEUTRAL=88`) and SWDA
    `244` (`INFORM=199`, `ACKNOWLEDGE=3`, `DIRECTIVE=18`, `EXPRESSIVE=14`,
    `REJECT=10`).
  - Paper now explicitly records provenance preservation, non-question
    response-act policy, specificity/safety/greeting/filler/fragment/context
    filters, local LLM quality pass, audio-index alignment, and greeting scan
    `0` remaining hits.

## 2026-05-29 04:25 KST - Paper Latency Bootstrap Simulation

- Owner/chat: framework/runtime
- User request:
  - Simulate the experiment from the beginning and produce quantitative latency
    statistics for paper writing.
- Done:
  - Added `AI_NPC_System/scripts/simulate_paper_latency_from_logs.py`.
  - Ran empirical bootstrap simulation from
    `AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`.
  - Primary clean window: `2026-05-29T03:36:00+09:00` onward, `508` source log
    rows.
  - Simulation setup: `5000` full experiment repetitions x `8` turns per case,
    total `200000` simulated turn rows, seed `20260529`.
- Outputs:
  - `AI_NPC_System/reports/latency_simulation_paper_20260529/summary.md`
  - `AI_NPC_System/reports/latency_simulation_paper_20260529/simulation_turn_summary.csv`
  - `AI_NPC_System/reports/latency_simulation_paper_20260529/simulation_run_summary.csv`
  - raw simulated turn/run CSVs in the same folder.
- Core simulated result:
  - FastTrack first-response readiness median: `14.591 ms` (`n=160000`,
    p75 `17.334 ms`, p95 `37.577 ms`).
  - SlowTrack-only first-response readiness median: `2303.285 ms` (`n=40000`,
    p75 `2325.851 ms`, p95 `2510.694 ms`).
  - Simulated median improvement: `2288.7 ms`, relative reduction `99.4%`,
    about `157.9x` faster by median.
  - P(FastTrack first response <100 ms): `97.2%`; P(SlowTrack-only first
    response >2000 ms): `91.0%`.
- Caveat:
  - This is a recorded-log bootstrap simulation, not a browser audible-onset
    experiment. Use it for methods/results planning; final perceptual latency
    claims still need frontend `audio_play_started` timing.

## 2026-05-29 03:20 KST - Active FastTrack Dataset Pool Filtering

- Owner/chat: framework/runtime
- User request:
  - Do not treat the prebuilt manifest as the source dataset.
  - Read the MD files and filter the actual separated FastTrack datasets/pool.
  - Remove overly specific, unclear, greeting/closing, filler, and unusable
    lines from each dataset source.
- Done:
  - Confirmed active source is the separated dataset pool:
    `AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`.
  - Added `AI_NPC_System/scripts/filter_fasttrack_dataset_pool_with_local_llm.py`.
  - Applied LLM and deterministic cleanup passes to the active GoEmotions/SWDA
    pool while keeping the source buckets separate.
  - Added persistent builder/validator blocks for greetings, closings, common
    greeting variants (`yo`, `how are you`, `what's up`, `long time no see`,
    `cheers`), filler, lowercase fragments, specific internet/media objects,
    and SWDA phone-call remnants.
  - Aligned the pool with available prebuilt audio source IDs so router-v3 no
    longer selects pool rows with missing derived audio.
  - Router-v3 now inserts punctuation between prebuilt segment texts for cleaner
    subtitles/logging.
- Current pool counts:
  - GoEmotions: `385` total
    (`POSITIVE=141`, `NEGATIVE=133`, `SURPRISE=23`, `NEUTRAL=88`).
  - SWDA: `244` total
    (`INFORM=199`, `ACKNOWLEDGE=3`, `DIRECTIVE=18`, `EXPRESSIVE=14`, `REJECT=10`).
- Verification:
  - `validate_fasttrack_dataset_pool.py`: OK.
  - `smoke_fasttrack_prebuilt_runtime.py`: OK for 3 representative inputs,
    missing-audio no-fallback guard, and serial-order guard.
  - Greeting/closing scan: `0` remaining hits.
  - `check_runtime_readiness.py`: PARTIAL only because optional local LLM and
    Open-LLM web endpoints were not running; required data/code checks passed.
- Files touched:
  - `AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`
  - `AI_NPC_System/scripts/filter_fasttrack_dataset_pool_with_local_llm.py`
  - `AI_NPC_System/scripts/build_fasttrack_dataset_pools.py`
  - `AI_NPC_System/scripts/validate_fasttrack_dataset_pool.py`
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/docs/persona_reaction_bundle.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - If more natural language is needed, rebuild or curate SWDA response-act
    evidence; the current clean SWDA ACK bucket is intentionally small.
  - Do not re-expand the pool from raw JSONL without re-running the new
    filtering script.

## 2026-05-29 00:34 KST - Donation Timeline Tightening And Internet Chat Burst

- Owner/chat: scenario/frontend
- User request:
  - Keep the first donation timing, but move the later donation beats 2 seconds
    earlier.
  - Make two recurring chatters behave more like real internet chat with many
    `lol`/`lmao` and emoji reactions.
- Done:
  - Kept first donation at T+1s.
  - Moved later donation blocks from T+40/T+80/T+110 to T+38/T+78/T+108.
  - Shifted each affected reaction-chat block by the same 2 seconds so the
    surrounding chat remains aligned with its donation.
  - Updated `LOLByte` and `EmojiRush` generated chatter lines to use heavier
    internet-style short reactions with `lol`, `LMAO`, and emojis.
  - Updated timing references in current live guide and methodology docs.
  - Re-applied Open-LLM-VTuber integration so the vendor frontend copy matches
    the source frontend.
- Verification:
  - `node.exe --check` passed for source and vendor frontend files.
  - Source and vendor frontend files are byte-identical after integration.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `CODEX_SHARED_WORKLOG.md`

## 2026-05-29 00:10 KST - Paper Latency Log Session And Methodology

- Owner/chat: methodology/logging
- User request:
  - Create a fresh log file for quantitative latency analysis in the paper and
    organize the measurement methodology.
- Done:
  - Created new active session stem `paper_latency_20260529_000308`.
  - Updated `AI_NPC_System/project_config.sh` so the next runtime execution
    writes to the new session.
  - Initialized ignored runtime log files:
    - `AI_NPC_System/latency_logs/paper_latency_20260529_000308.events.jsonl`
    - `AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`
    - `AI_NPC_System/latency_logs/paper_latency_20260529_000308.latest_summary.md`
    - `AI_NPC_System/latency_logs/paper_latency_20260529_000308.session.json`
  - Added reusable session creation and summary scripts.
  - Added `AI_NPC_System/docs/latency_quantitative_methodology.md`.
- Verification:
  - New scripts compile.
  - Empty session summary generation works and produces a zero-row report.
- Next handoff:
  - Run participant/scenario recordings normally; analyze after recording with
    `summarize_latency_session.py --session-stem paper_latency_20260529_000308`.
  - Exclude cold-start, setup, unlabeled, wrong-scenario, and debug rows during
    paper analysis.

## 2026-05-29 00:02 KST - Donation Reality Check Scenario Rewrite

- Owner/chat: framework/runtime
- User request:
  - `shared_2m30` 시나리오를 네 개의 도네이션 중심으로 교체. 모든 도네이션/채팅은 영어로 작성하고, 2번과 3번 도네이션은 감정적으로 더 격하게 작성. 채팅 반응도 각 도네이션 내용을 따라가게 구현.
- Done:
  - Scenario label/topic changed to `Lab Maid Donation Reality Check`.
  - Donation timeline now uses:
    - T+1s: cute maid / katana-like healing-stream critique.
    - T+40s: senior stole the viewer's lab-meeting idea, written as intense betrayal.
    - T+80s: overexcited professor admiration, written as intense positive overinvestment.
    - T+110s: professor is watching the stream right now.
  - Replaced the scripted virtual chat with English-only reactions tailored to each donation.
  - Removed old deleted-log, figure/script, stipend/pizza scenario text and long laughter strings from the active scenario block.
  - Updated scenario references in methodology/live guide/runtime flow/user protocol docs and Open-LLM-VTuber README.
  - `apply_integration.py --activate` copied the updated frontend to vendor Open-LLM-VTuber.
- Verification:
  - Windows Node syntax check passed for source and vendor `credo-vtuber-mode.js`.
  - Source and vendor frontend files are byte-identical after integration.
  - Scenario block smoke confirmed 4 donations, all new anchors present, old scenario anchors absent, no `HAHAHAHA`, and no non-ASCII characters in the scenario block.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Runtime servers were not started. Browser reload is needed next time the Open-LLM frontend is running.
- Do not touch:
  - FastTrack router/prebuilt audio/manifest work unless explicitly reopened.

## 2026-05-28 23:59 KST - Rename SlowTrack-Only Case To Case 5

- Owner/chat: current experiment settings/UI cleanup
- User request:
  - After removing the old Grounded/Parallel Case 5, rename the remaining
    SlowTrack-only Case 6 to Case 5.
- Done:
  - Frontend preset id changed from `case_6_slowtrack_only` to
    `case_5_slowtrack_only`.
  - Browser button text changed from `Case 6 · None / SlowTrack Only` to
    `Case 5 · None / SlowTrack Only`.
  - Added a frontend alias so stale localStorage/status values for
    `case_6_slowtrack_only` normalize to `case_5_slowtrack_only`.
  - Current usage/method/protocol/runtime docs now list five cases as
    Case 1 through Case 5.
  - Ran `apply_integration.py --activate` so the active vendor frontend matches
    the source frontend hook.
- Do not touch:
  - Parallel backend/research code remains future/deferred work.
  - FastTrack prebuilt audio router and SlowTrack prompt expansion remain owned
    by other chats.

## 2026-05-28 23:48 KST - Remove Case 5 And Parallel Buttons From Current UI

- Owner/chat: current experiment settings/UI cleanup
- User/professor-facing request:
  - Remove Case 5 from the visible experiment case list.
  - Remove Parallel/async scheduling buttons from the current browser panel.
- Implemented:
  - Frontend experiment presets now expose only Case 1, Case 2, Case 3,
    Case 4, and Case 6.
  - Removed the disabled `case_5_grounded_parallel` button from the panel.
  - Removed the disabled `Parallel · Deferred` scheduling architecture button.
  - Manual architecture controls now show only `Serial` and `No FastTrack`.
  - Frontend scheduling normalization remains locked to `serial` for the
    current study UI.
- Documentation updated:
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
- Important boundary:
  - Parallel backend/research code was not deleted. It remains a future
    architecture candidate, but the current scenario UI no longer lets the
    operator select it.
  - This pass did not touch the FastTrack prebuilt audio router or SlowTrack
    prompt expansion work owned by other chats.

## 2026-05-28 23:35 KST - Runtime Readiness and Conservative FastTrack Cleanup

- Owner/chat: framework/runtime cleanup
- User request:
  - Read the shared worklog, check whether current execution/FastTrack is safe,
    give usage instructions, conservatively clean up, then commit.
- Done:
  - Confirmed current stack status reports StyleBERT, local LLM, and Open-LLM
    endpoints healthy.
  - Confirmed source and vendor Open-LLM CREDO agent/frontend copies are
    byte-identical after `apply_integration.py --activate`.
  - Added an explicit readiness check for the active prebuilt StyleBERT
    FastTrack manifest.
  - Removed 9 unsafe/topic-specific source-dataset remnants from the prebuilt
    FastTrack manifest and deleted their generated wav files:
    dog/video/politics/self-harm/assault/mental-illness style lines.
  - Removed generated Python `__pycache__` folders under `AI_NPC_System`.
- Verification:
  - `check_runtime_readiness.py` reports `READY`.
  - Prebuilt manifest readiness: `usable_audio=2171/2171`,
    `go_emotions=1122`, `swda=1049`, `voice_model=credo_voice_sample_en`.
  - `validate_fasttrack_stylebert_prebuilt_bundle.py --strict-voice-model
    --min-items 2171` passed.
  - `smoke_fasttrack_prebuilt_runtime.py` passed:
    prebuilt lookup hit, missing-audio no realtime TTS fallback, serial guard.
  - Python compile passed for router, readiness, build/validate/smoke scripts.
  - JS syntax check passed for source and vendor frontend hooks.
  - `git diff --check` passed.
- Files touched:
  - `AI_NPC_System/scripts/check_runtime_readiness.py`
  - `AI_NPC_System/scripts/build_fasttrack_stylebert_prebuilt_bundle.py`
  - `AI_NPC_System/scripts/validate_fasttrack_stylebert_prebuilt_bundle.py`
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/fasttrack_assets/audio/prebuilt_stylebert_v1/`
  - `AI_NPC_System/reports/runtime_readiness_latest.{json,md}`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Functionally, FastTrack is wired to prebuilt wav and does not use realtime
    TTS fallback. Content is still raw filtered dataset speech, so future
    quality work should curate/rebuild the bundle rather than silently falling
    back at runtime.
- Do not touch:
  - `AI_NPC_System/VoiceSample/` and StyleBERT model assets.

## 2026-05-28 23:03 KST - Lab Maid Reality-Check Personality

- Owner/chat: framework/runtime
- User request:
  - 성격을 `잘 들어주는 척 하다가 팩폭 때리는` 방향으로 조정.
- Done:
  - Persona/prompt에 `warm listening beat -> cute but blunt reality check` 성격 리듬을 추가.
  - 팩폭은 시청자 인격이 아니라 상황, 핑계, 마감, 대학원 함정을 겨냥하도록 제한.
  - `Avoid cruelty` 가드를 추가해 상담 방송 톤이 공격적으로 흐르지 않게 함.
  - `apply_integration.py --activate`로 vendor Open-LLM-VTuber runtime files에 반영. 서버는 재시작하지 않음.
- Verification:
  - Python compile passed for source and vendored CREDO agent plus `slow_track.py` and `config.py`.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - Offline prompt smoke confirmed `warm listening beat`, `blunt reality check`, `never insult the viewer`, and `Avoid cruelty` are present in assembled SlowTrack/persona prompts.
- Files touched:
  - `AI_NPC_System/docs/professor_lab_maid_persona.md`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Actual LLM output was not run because servers remain stopped by user request.
- Do not touch:
  - FastTrack router/prebuilt audio/manifest work unless explicitly reopened.

## 2026-05-28 22:12 KST - Case 5 Excluded From Current Experiment Plan

- Owner/chat: docs/report
- User request:
  - 현 실험에서는 `case_5_grounded_parallel`을 제외할 가능성이 높으므로 현황 공유 MD에 기록.
- Done:
  - 현재 실험 운영 기준을 Case 1-4 + Case 6 중심으로 공유.
  - `case_5_grounded_parallel`은 Parallel scheduling 조건이므로 이번 실험 본 세트에서 제외/보류 예정으로 명시.
  - Case 5 관련 코드, 식별자, 기존 문서 흔적은 즉시 삭제하지 않고 follow-up/deferred 조건으로 보존하는 방향.
- Verification:
  - 문서 메모만 추가. 런타임/코드 검증은 해당 없음.
- Files touched:
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - 후속 문서 정리 시 `README.md`, `AI_NPC_System/docs/credo_live_usage_guide.md`, `AI_NPC_System/docs/research_methodology_experiment_plan.md`, `AI_NPC_System/docs/user_study_protocol.md`, 논문 초안의 primary run set을 Case 1-4 + Case 6 기준으로 맞출 것.
- Do not touch:
  - Case 5/Parallel 구현을 삭제하지 말 것. 현재는 제외/보류 기록만 남긴다.

## 2026-05-28 22:09 KST - SlowTrack Three-Sentence Allowance And Lab Anecdote

- Owner/chat: framework/runtime
- User request:
  - 실제 SlowTrack 출력은 3문장까지 허용. 프롬프트 안에 깨끗한 유명 대학원 유머 기반 연구실 썰을 캐릭터의 썰로 추가.
- Done:
  - SlowTrack 출력 규칙을 1-2문장에서 1-3문장, 보통 18-55 words로 완화.
  - VTuber 후처리도 최대 3문장, 55 words까지 유지하도록 조정.
  - `CREDO_VTUBER_MAX_SPOKEN_WORDS` 기본값과 project config 값을 `55`로 변경.
  - `Lego Grad Student`/`PhD Comics` 계열의 깨끗한 대학원 유머를 바탕으로, 랩미팅에서 주말 내내 준비한 코멘트를 선배가 먼저 말해버려 `peer-reviewed silence`라고 부르는 연구실 썰을 persona/prompt에 추가.
  - `apply_integration.py --activate`로 vendor Open-LLM-VTuber runtime files에 반영. 서버는 재시작하지 않음.
- Verification:
  - Python compile passed for source and vendored CREDO agent plus `slow_track.py` and `config.py`.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - Offline prompt smoke confirmed `peer-reviewed silence` and the 3-sentence rule are present in the assembled SlowTrack prompt.
- Files touched:
  - `AI_NPC_System/docs/professor_lab_maid_persona.md`
  - `AI_NPC_System/slow_track.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Actual LLM output was not run because servers remain stopped by user request.
- Do not touch:
  - FastTrack router/prebuilt audio/manifest work unless explicitly reopened.

## 2026-05-28 21:53 KST - SlowTrack Prompt And Memory Expansion

- Owner/chat: framework/runtime
- User request:
  - SlowTrack 프롬프트와 메모리만 확장. Professor's Lab Maid 세계관을 컴퓨터그래픽스 연구실/대학원 상담 방송 중심으로 강화하고, 최근 채팅/도네이션/시청자별 기억/방송 사건을 SlowTrack private context에 넣기.
- Done:
  - `docs/professor_lab_maid_persona.md`를 컴퓨터그래픽스 연구실 메이드, 대학원 고민상담소, rendering/shaders/animation/simulation/paper revision/deadlines/lab meeting/advisor messages 중심으로 확장.
  - `slow_track.py`가 `SLOW_TRACK_SYSTEM_PROMPT`와 persona bible, structured memory context를 함께 쓰도록 변경. 실제 발화는 여전히 영어 1-2문장 중심으로 제한.
  - `memory_store.py` schema를 v2로 확장해 viewer nickname memory, recent donations, recent stream events를 저장/프롬프트화.
  - Open-LLM-VTuber CREDO agent가 metadata의 topic, last_chat, donation_amount, viewer_name, vtuber_event를 runtime/persistent memory에 넘기도록 확장.
  - `project_config.sh`, `config.py`, Open-LLM-VTuber character yaml의 persona/prompt를 새 연구실 메이드 설정으로 갱신.
  - `apply_integration.py --activate`로 vendor Open-LLM-VTuber agent/config에 반영. 서버는 재시작하지 않음.
- Verification:
  - `python3 -m py_compile` passed for `slow_track.py`, `memory_store.py`, `config.py`, source CREDO agent, and vendored CREDO agent.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - Offline prompt smoke: context `1854` chars, assembled SlowTrack system prompt `3837` chars; confirmed viewer memory, recent donation, recent stream events, private context block, routing privacy, and spoken output constraint are present.
  - Actual LLM generation was not run because the user requested servers remain stopped.
- Files touched:
  - `AI_NPC_System/docs/professor_lab_maid_persona.md`
  - `AI_NPC_System/slow_track.py`
  - `AI_NPC_System/memory_store.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - 다음 런타임 검증은 LLM/StyleBERT/Open-LLM 서버를 명시적으로 다시 켠 뒤 실제 생성문이 1-2문장으로 유지되는지 확인하면 된다.
- Do not touch:
  - FastTrack router/prebuilt audio/manifest work unless the user explicitly reopens that scope.

## 2026-05-27 17:12 KST - VTuber UI, Repetition, And Motion Hotfix

- Owner/chat: framework/runtime
- User request:
  - VTuber mode panel/model disappeared, speech repeated `I understood`/`I hear you`/`think`/coffee lines, and expression/idle motion was not applying.
- Done:
  - Fixed the CREDO overlay CSS so the panel stays inside the viewport instead of being positioned above the screen.
  - Hardened Live2D motion lookup against early model-load null errors.
  - Restored spaCy keyword echo by removing an accidental unconditional empty return.
  - Expanded FastTrack/SlowTrack speech hygiene to block low-value openings (`I hear you`, `understood`, `got it`, `let me think`, `I think`) and repeated coffee phrasing.
  - Applied SlowTrack hygiene to direct chat as well as VTuber-mode turns.
  - Fixed suffix duplication after cleaning generated SlowTrack text.
  - Removed the repeated drink topic from active prompts and the virtual scenario seed chat.
  - Reordered Live2D expressions so a real expression remains first and CREDO motion tags are appended instead of being treated as base expressions.
  - Updated frontend audio handling to play both speech emotion motion and style motion tags.
  - Fixed idle motion fallback: the model has `Idle`, not `Idle_Motion`, so the idle loop now falls back correctly.
  - Re-applied integration and restarted Open-LLM only; existing LLM and StyleBERT servers were preserved.
- Verification:
  - Python compile passed for source and vendored CREDO agent plus integration script.
  - JS syntax passed for source and vendored `credo-vtuber-mode.js`.
  - Unit smoke confirmed repeated phrases/coffee are removed, spaCy echo prefixes the FastTrack reaction, and CREDO motion tags are appended after a base expression.
  - Playwright UI smoke passed: overlay visible at `x=18,y=18,w=330,h=684`, canvas visible, Live2D model loaded in the main UI check.
  - Direct chat smoke: FastTrack text `That was a sudden lab alarm.` and SlowTrack text `Oh no, that's a real bummer! Don't worry, let's take one steady breath and start fresh...` were queued without `coffee`, `I hear you`, `understood`, or duplicated suffix.
  - Motion group check: model reports `Idle=1`, `Talk=1`, `Positive=2`; manual `Idle` start succeeded.
  - Final Playwright smoke after restart: overlay visible, canvas visible, `Idle=1`, `Talk=1`, `Positive=2`; direct-chat audio queue contained no repeated drink topic or low-value filler openings.
  - Open-LLM restarted detached and persistent as PID `155968`; StyleBERT and vLLM remained running.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - `AI_NPC_System/project_config.sh`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Browser reload is enough for the frontend patch, but Python agent changes require Open-LLM restart if another chat re-applies integration.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets unless the voice/TTS chat resumes that scope.

## 2026-05-27 17:54 KST - Six Experiment Case Runtime Validation

- Owner/chat: framework/runtime
- User request:
  - Commit the current state and properly test whether all six experiment cases work.
- Done:
  - Found that earlier smoke tests were not strict enough: cases 4-6 could fall back to `The lab maid has the thread` because the local 2K-token LLM hit context-length errors.
  - Lowered default local LLM output budget to 64 tokens and added progressive retry for context-length HTTP 400 errors (`64 -> 48 -> 32`).
  - Reduced runtime memory injection to keep the local Qwen 2K context stable.
  - Normalized `kyo-shu-zin-sama` suffix variants so generated text keeps only one final `kyo-shu-zin- sama`.
  - Re-ran Open-LLM with the patched code.
- Verification:
  - Python compile passed for `AI_NPC_System/slow_track.py`, `AI_NPC_System/config.py`, source CREDO agent, and vendored CREDO agent.
  - Direct SlowTrack local LLM smoke succeeded against `qwen2.5:7b`.
  - Playwright six-case runtime test passed in 1.7 minutes.
  - Test covered:
    - Case 1: Grounded / Serial, 2 audio tasks.
    - Case 2: Emotion Only / Serial, 2 audio tasks.
    - Case 3: Intent Only / Serial, 2 audio tasks.
    - Case 4: Neutral Random / Serial, 2 audio tasks.
    - Case 5: Grounded / Parallel, 2 audio tasks.
    - Case 6: None / SlowTrack Only, 1 audio task.
  - Test assertions included overlay/canvas visibility, `Idle=1`, `Talk=1`, `Positive=2`, expected case policy/scheduling/component state, audio task count, expression logs, no runtime page errors, no `coffee`, no `I hear you`, no `understood`, no `let me think`, no fallback `The lab maid has the thread`, and suffix appears at most once per audio task.
- Files touched:
  - `AI_NPC_System/slow_track.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - If a future test uses a much longer scenario prompt, keep watching local LLM context length because the active vLLM server is still capped at 2048 tokens.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets unless the voice/TTS chat resumes that scope.

## 2026-05-27 16:03 KST - Concurrent Runtime Conflict Cleanup

- Owner/chat: framework/runtime
- User request:
  - 여러 Codex 작업이 겹치면서 생긴 런타임 충돌을 검토하고 해결.
- Done:
  - `apply_integration.py --activate`가 다시 실행되어도 현재 정책이 유지되도록 통합 스크립트를 정리.
  - Open-LLM-VTuber idle/chat/manual 프롬프트를 English-only Professor's Lab Maid 기준으로 통일.
  - chat batch buffer가 선택되지 않은 메시지까지 소비하던 문제를 고쳐, 실제 선택된 메시지만 consumed 처리.
  - StyleBERT-VITS2 FastTrack 합성이 latency CSV에서 `realtime_synthesized=true`로 기록되도록 수정.
  - StyleBERT config/schema 기본값을 현재 VoiceSample fine-tune 설정(`sdp_ratio=0.1`, `noise=0.35`, `noisew=0.45`)과 맞춤.
  - `select_tts_engine.py stylebert`와 stack warmup fallback도 같은 StyleBERT 값으로 맞춰, TTS 선택 스크립트 재실행 시 예전 값으로 돌아가지 않게 정리.
  - spaCy Echo는 최신 요구사항 기준으로 FastTrack reaction 앞단에 다시 활성화:
    `FAST_TRACK_KEYWORD_ECHO_ENABLED=1`, `FAST_TRACK_KEYWORD_ECHO_PROBABILITY=1.0`.
  - Live2D `Idle_Motion.motion3.json` 자산은 source와 `reaction_sources/AvatarMotion`에 존재함을 확인.
- Verification:
  - `apply_integration.py --activate` 재실행 성공.
  - Python compile passed: router v3, transition matrix, config, integration script, CREDO agent, vendored routes/websocket/TTS config.
  - JS syntax passed for source and vendored `credo-vtuber-mode.js`.
  - JSON validation passed for source/vendor Live2D model JSON and Idle motion JSON.
  - FastTrack dataset pool validation passed: `go_emotions=1131`, `swda=1049`.
  - Router v3 smoke passed: QUESTION input mapped to `ACKNOWLEDGE`, Top-3 contained no `QUESTION`, spaCy keyword echo returned `server`/`coffee`.
  - `select_tts_engine.py --status` and `select_tts_engine.py stylebert --dry-run` passed; selected TTS remains `stylebert_vits2` and changed files were `none`.
  - `run_credo_stack.sh --profile live --status` reports the expected target services: `stylebert`, `llm`, `open-llm`; all were offline because the stack is not currently running.
  - Runtime readiness: `PARTIAL`, required_failed=0, optional_failed=3, warnings=0;
    LLM, Open-LLM-VTuber web, and StyleBERT endpoints were not running during the final check.
- Files touched:
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/scripts/run_credo_stack.py`
  - `AI_NPC_System/scripts/select_tts_engine.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - regenerated vendor Open-LLM-VTuber runtime files
  - `AI_NPC_System/reports/runtime_readiness_latest.{json,md}`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart the stack before browser testing so route/websocket/agent changes are loaded.
  - Include the two currently untracked `Idle_Motion.motion3.json` source files in the next commit; the vendor copy is ignored by vendor `.gitignore`.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets unless the user explicitly resumes voice/TTS work.

## 2026-05-27 15:58 KST - Interjection/Tic Emission Hotfix Applied

- Owner/chat: framework/runtime
- User request:
  - Runtime was still speaking repeated interjections like `ha-ha`, `ahaha`,
    `hee-hee`, and unstable FastTrack snippets instead of answering normally.
- Done:
  - Confirmed the active runtime logs contained old `fasttrack_interjection_dispatch`
    rows and SlowTrack text with `HA-HA-HA-HA`.
  - Confirmed the running Open-LLM-VTuber process was an old `run_server.py`
    process from 03:19 KST, so prior code changes were not loaded.
  - Disabled spaCy keyword echo in `AI_NPC_System/config.py` and
    `AI_NPC_System/project_config.sh`.
  - Added runtime speech cleanup for repeated laughter/interjection strings
    before TTS.
  - Added FastTrack stabilization so unstable pool snippets such as
    `Nuh-uh`, `Here is the genius answer`, and `what's your take` are replaced
    with quiet one-sentence covers.
  - Hard-returned spoken thinking bridge and extra cover speech paths.
  - Updated `apply_integration.py` so future activation removes
    `prepare_audio_payload` from CREDO interjection routes and keeps
    `/credo/interjections` playback hard-locked.
  - Re-applied the Open-LLM-VTuber integration and restarted Open-LLM-VTuber.
- Verification:
  - `python3 -m py_compile` passed for config, CREDO agent source, vendored
    agent, vendored routes, and `apply_integration.py`.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - CREDO agent source and vendored agent copy are byte-identical.
  - `GET http://127.0.0.1:12393/credo/interjections` returns
    `{"items":[],"disabled":true,...}`.
  - `POST http://127.0.0.1:12393/credo/interjections/play` returns `423` and
    `played=false`.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned
    `READY`.
  - New Open-LLM-VTuber process is running as pid `131226`, started
    15:54 KST.
- Files touched:
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `AI_NPC_System/reports/runtime_readiness_latest.json`
  - `AI_NPC_System/reports/runtime_readiness_latest.md`
- Next handoff:
  - Old `module_events.csv` rows before 15:54 KST still show the bad behavior;
    ignore those for new validation.
  - If interjections appear again, first check whether an older `run_server.py`
    process is still running and restart Open-LLM-VTuber.
- Do not touch:
  - Do not re-enable standalone interjection playback or keyword echo unless a
    new experiment explicitly requires it.

## 2026-05-27 KST - spaCy Echo Reconnected To Router v3 FastTrack

- Owner/chat: framework/runtime
- User request:
  - Router v3 primary path must include spaCy echo.
  - Echo must be inside the FastTrack reaction, not a separate utterance.
- Done:
  - Added spaCy noun/proper-noun/verb keyword extraction to
    `AI_NPC_System/fasttrack_router_v3.py`.
  - Router v3 now runs emotion, intent, and keyword extraction together with
    `asyncio.gather`.
  - Router v3 includes keywords in the retrieval query and returns
    `keywords` / `keyword_echo`.
  - The Open-LLM-VTuber CREDO agent now prefixes the selected FastTrack reaction
    with the first spaCy keyword inside the same StyleBERT TTS text.
  - Removed the old separate `fast_track_keyword_echo` output path from the
    active turn sequence.
  - Enabled keyword echo by default in `project_config.sh` and `config.py`
    with probability `1.0`.
- Verification:
  - Python compile passed for Router v3, CREDO agent source, vendored CREDO
    agent copy, and config.
  - Smoke test input `The lab server deleted my thesis backup and coffee is
    gone.` returned `keywords=['server', 'thesis', 'backup', 'coffee',
    'deleted']` and `keyword_echo=server`.
  - Agent prefix smoke test produced
    `server. Tiny lab-maid report: that part is noted.`
  - `apply_integration.py --activate` synced the vendored agent copy.
- Files touched:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
- Next handoff:
  - Restart Open-LLM-VTuber for the running server to load the updated agent.
  - In the pipeline diagram, spaCy belongs inside the FastTrack branch as an
    echo prefix, not as a separate branch or output component.

## 2026-05-27 07:00 KST - Active Scenario Chat And Donation SFX Fallback

- Owner/chat: framework/runtime
- User request:
  - Scenario chat automation should feel more active.
  - Replace stiff placeholder nicknames with more believable stream names.
  - Make normal chat mostly reactions, not questions, and keep it contextual.
  - Donation alert sound was not applying.
- Done:
  - Expanded the 150-second scenario from 12 normal chat events to 28 normal
    chat events while keeping the 3 donation anchors at 30s, 70s, and 110s.
  - Replaced `Viewer_A` style nicknames with stream-like lab/research names:
    `CoffeeCalibrator`, `KernelPanicKim`, `FridgeForensics`,
    `LabFridgeLawyer`, `SyntaxSasha`, `FinalSlideFaye`, etc.
  - Rewrote normal chat messages as contextual reactions with no question marks.
  - Added static donation SFX fallback:
    - `apply_integration.py --activate` now copies
      `AI_NPC_System/fasttrack_assets/audio/Donatiion_SFX.mp3` to
      `vendor/open-llm-vtuber/frontend/credo-donation-sfx.mp3`.
    - Frontend now tries `./credo-donation-sfx.mp3` first, then
      `/credo-donation-sfx.mp3`, then `/credo/vtuber-mode/donation-sfx`.
    - `Start Scenario` preloads the donation SFX before scheduled donations.
- Verification:
  - `curl -I http://127.0.0.1:12393/credo-donation-sfx.mp3` returned `200 OK`
    with `content-type: audio/mpeg`, so the SFX is served by the running server
    without requiring the backend route to reload.
  - Source and vendored overlay JS are identical.
  - JS syntax check passed for source and vendored overlay JS.
  - Static scenario check confirmed `chatCount=28`, `donationCount=3`, SFX
    fallback URLs, `primeDonationSfx()`, and WebSocket chat buffering metadata.
  - Running server served updated `/credo-vtuber-mode.js` containing the new
    nicknames and SFX fallback.
  - `git diff --check` passed for touched files.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/frontend/credo-donation-sfx.mp3`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Browser page reload is enough for the updated static JS/SFX fallback.
  - Full Open-LLM-VTuber restart is still recommended if backend route changes
    need to be evaluated, but SFX playback no longer depends on that route.
- Do not touch:
  - Existing voice/TTS asset work unless explicitly assigned.

## 2026-05-27 06:51 KST - StyleBERT Voice Artifact Mitigation

- Owner/chat: voice/TTS + framework/runtime
- User request:
  - 목소리가 조금 깨지고, 음원 마지막에 "으아바바바밥" 같은 artifact가
    들리는 것이 괜찮은지 확인.
- Done:
  - 실험 영상용이면 audible clipping/tail artifact는 괜찮다고 보기 어렵다고
    판단.
  - StyleBERT stochastic synthesis 값을 안정 쪽으로 낮춤:
    `sdp_ratio=0.1`, `noise=0.35`, `noisew=0.45`.
  - FastTrack StyleBERT client와 Open-LLM-VTuber StyleBERT TTS adapter에
    WAV 후처리 추가:
    - 0.88 peak target으로 down-normalize.
    - 0.9s보다 긴 출력은 마지막 80ms를 짧게 trim.
    - 8ms fade-in, 80ms fade-out 적용.
  - `apply_integration.py --activate`로 vendored Open-LLM-VTuber TTS adapter와
    character/conf YAML에 새 설정을 반영.
- Verification:
  - Python compile passed for StyleBERT client, integration TTS adapter,
    vendored TTS adapter, config, and patcher.
  - `diff -q` confirmed source/vendored StyleBERT TTS adapter are identical.
  - Vendored YAML now contains `sdp_ratio: 0.1`, `noise: 0.35`, `noisew: 0.45`.
  - Test synthesis to `/tmp` changed peak from full-scale clipping risk to
    `peak=28834`, `clipped_samples=0`; final 20ms RMS measured about
    `-31.86 dBFS`.
  - `git diff --check` passed for touched source/config files.
- Files touched:
  - `AI_NPC_System/stylebert_vits2_client.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/stylebert_vits2_tts.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/tts/stylebert_vits2_tts.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/characters/credo_latency_cover.yaml`
  - `vendor/open-llm-vtuber/conf.credo.yaml`
  - `vendor/open-llm-vtuber/conf.yaml`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber before judging the change; running processes will
    not reload the TTS adapter/YAML automatically.
  - If artifact is still audible after restart, inspect the exact generated WAV
    in `AI_NPC_System/tts_outputs/stylebert_fast/` and consider stronger
    sentence splitting or switching the recording TTS route for final videos.
- Do not touch:
  - Do not retrain or replace the selected voice model unless explicitly
    requested.

## 2026-05-27 06:25 KST - English 150-Second Automation Timeline

- Owner/chat: framework/runtime + docs/report
- User request:
  - Runtime prompts, scenario text, chat payloads, and donation payloads must be
    English. Korean should remain only in paper/work documents.
  - Replace the prior 150-second scenario with the provided four-scene
    automation test timeline.
  - General chat events should go through the Open-LLM-VTuber WebSocket channel;
    donation events should stay on HTTP POST `/credo/vtuber-mode/donation`.
- Done:
  - Replaced `shared_2m30` label/topic with English:
    `Shared 150-second scenario: Graduate School Survival Counseling Center`.
  - Replaced scenario `broadcast_direction` with English-only instructions for
    Scene 1 taunting, Scene 2 catastrophe, Scene 3 mischief, and Scene 4
    rejection.
  - Replaced all timeline authors/messages/amounts with the user-provided
    English timeline:
    `Viewer_A/B/C`, `LabSlave99`, `Viewer_D/E/F`, `PuddingThief`,
    `Viewer_G/H/I`, `SleepCoder`, `Viewer_J/K/L`.
  - Added `durationSeconds: 150`; scenario completion now waits until 150s even
    though the last chat payload is at 122s.
  - Changed `sendVirtualChat()` to send normal chat over the browser
    Open-LLM-VTuber WebSocket as `text-input` with
    `vtuber_live_chat_batch=true`, buffering chat while SlowTrack is speaking.
    HTTP `/credo/vtuber-mode/virtual-chat` remains only as a no-WebSocket
    fallback.
  - Kept donations on HTTP POST `/credo/vtuber-mode/donation` with
    `priority=true`, donation overlay, and local SFX.
  - Removed Korean fallback strings from runtime donation overlay/defaults.
  - Updated non-paper runtime docs/README snippets to use the English scenario
    label and WebSocket-vs-HTTP automation rule.
  - Re-ran `apply_integration.py --activate` so vendored Open-LLM-VTuber
    frontend has the same JS.
- Verification:
  - JS syntax check passed for source and vendored `credo-vtuber-mode.js`.
  - `diff -q` confirmed source and vendored overlay JS are identical.
  - `rg "[가-힣]"` found no Korean text in runtime JS, vendored runtime JS,
    vendored CREDO routes, vendored CREDO agent, or integration patcher.
  - Static scenario checks confirmed the 150-second label, three donation
    anchors, WebSocket chat metadata, donation POST, and 150s completion timer.
  - Running server served the updated `/credo-vtuber-mode.js` containing the
    English label, `LabSlave99`, `SleepCoder`, and `vtuber_live_chat_batch`.
  - `git diff --check` passed for touched source/docs files.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Reload the browser page before recording so the English overlay JS is used.
  - Keep research/paper documents bilingual/Korean as needed, but keep runtime
    prompts, UI scenario text, chat payloads, and donations in English.
- Do not touch:
  - Existing voice/TTS asset changes in the dirty worktree unless explicitly
    assigned.

## 2026-05-27 05:57 KST - 150-Second Shared Scenario

- Owner/chat: framework/runtime + docs/report
- User request:
  - 6개 실험 영상 길이를 모두 2분 30초로 늘리기.
  - 완료 후 Codex 공유 현황 파일에 업데이트.
- Done:
  - 공통 시나리오 ID를 `shared_2m30`으로 정리하고, 기존 localStorage의
    `shared_2min` 값은 `shared_2m30`으로 호환 매핑되게 처리.
  - 6개 `Experiment cases`가 모두 `shared_2m30`을 사용하도록 변경.
  - 시나리오 라벨을
    `공통 2분 30초 시나리오: 대학원 생존 고민상담소`로 변경.
  - 마지막 30초 구간에 반응 채팅 3개와 긴 고민 도네이션 1개를 추가.
    마지막 이벤트는 149초이며 scenario complete 타이머는 150초 근처에서
    종료됨.
  - source overlay JS를 수정한 뒤 `apply_integration.py --activate`로
    vendored Open-LLM-VTuber frontend에 재적용.
  - README, live usage guide, methodology, user study protocol, runtime flow,
    integration README의 2분/`shared_2min` 표기를 150초/`shared_2m30` 기준으로
    갱신.
- Verification:
  - JS syntax check passed for source and vendored
    `credo-vtuber-mode.js`.
  - `diff -q` confirmed source and vendored overlay JS are identical.
  - `git diff --check` passed for touched source/docs files.
  - Running server root responded with HTTP 200. Browser plugin is unavailable
    in this session and Playwright is not installed locally, so no new browser
    dependency was installed for rendered automation.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Reload the overlay page before recording so the browser picks up the new
    `shared_2m30` frontend JS. Restart Open-LLM-VTuber if backend route changes
    from the previous donation update have not been loaded yet.
- Do not touch:
  - Existing voice/TTS asset changes in the dirty worktree unless explicitly
    assigned.

## 2026-05-27 05:51 KST - Survival Counseling Donation Scenario

- Owner/chat: framework/runtime + docs/report
- User request:
  - 6개 case가 모두 `대학원 생존 고민상담소` 시나리오를 쓰도록 통일.
  - 일반 채팅은 반응 위주로 다양하게 넣고, 긴 고민 상담은 도네이션으로
    넣기.
  - 도네이션은 치지직/Twitch처럼 별도 창으로 약 20초 표시.
  - 도네이션 도착 시 `AI_NPC_System/fasttrack_assets/Donatiion_SFX` 경로의
    SFX를 재생.
  - 도네이션을 우선 답변하고 이후 채팅들을 종합 반응하게 만들기.
- Done:
  - `shared_2min` 시나리오 label/topic을
    `공통 2분 시나리오: 대학원 생존 고민상담소` /
    `대학원 생존 고민상담소`로 변경.
  - 2분 타임라인을 반응 채팅 + 3개 긴 고민 도네이션으로 재작성.
  - Frontend에 `#credo-donation-overlay`를 추가해 도네이션 도착 시
    name/amount/message를 20초 표시.
  - Donation SFX 재생을 `/credo/vtuber-mode/donation-sfx`로 연결.
    실제 파일은 현재 repo에
    `AI_NPC_System/fasttrack_assets/audio/Donatiion_SFX.mp3`로 존재하며,
    route는 사용자가 말한 `fasttrack_assets/Donatiion_SFX` 경로도 함께 탐색.
  - Manual Donation 버튼과 scenario donation event 모두 같은
    `sendDonation()` 경로를 사용하며 `priority=true`를 전송.
  - Backend donation route가 priority donation을 받을 때 진행 중인 VTuber
    turn task를 취소하고 donation을 먼저 `trigger_text_input`하도록 수정.
  - Donation instruction에 "donation 먼저 답변, 주변 chat은 이후 batch에서
    요약" 지시 추가. 기존 virtual chat buffer는 유지되어 donation 이후 idle
    loop에서 batch 반응으로 소비됨.
  - Docs updated: live usage guide, methodology, protocol, runtime flow,
    root README, AI_NPC_System README, integration README.
- Verification:
  - `apply_integration.py --activate` completed.
  - Python compile passed for vendored routes, vendored agent, and patcher.
  - JS syntax check passed for source and vendored overlay JS.
  - Playwright rendered the panel and confirmed the scenario dropdown shows
    `공통 2분 시나리오: 대학원 생존 고민상담소`.
  - Playwright with mocked fetch/audio clicked `Donation`; observed
    `/credo/vtuber-mode/donation` payload with `priority:true`, SFX URL
    `/credo/vtuber-mode/donation-sfx?...`, and visible donation overlay.
  - Current running server has not been restarted; direct curl to
    `/credo/vtuber-mode/donation-sfx` returned 404 from the old process.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber before recording so `/credo/vtuber-mode/donation-sfx`
    and priority donation route logic are active.
  - After restart, click one case and `Start Scenario`; first donation should
    show overlay, play SFX, and be answered before buffered chat summary.
- Do not touch:
  - `AI_NPC_System/VoiceSample/` and voice/TTS sample assets unless the user
    explicitly asks in the voice/TTS thread.

## 2026-05-27 05:01 KST - Six Case 2-Minute Scenario Playback

- Owner/chat: framework/runtime + docs/report
- User request:
  - 이미지 표 기준으로 실험 영상을 6개 case로 줄이고, 모든 case가 동일한
    2분 시나리오를 쓰도록 즉시 실험 가능한 프론트 패널로 수정.
- Done:
  - `Experiment run presets`를 `Experiment cases` 6개로 교체:
    `case_1_grounded_serial`, `case_2_emotion_only_serial`,
    `case_3_intent_only_serial`, `case_4_neutral_random_serial`,
    `case_5_grounded_parallel`, `case_6_slowtrack_only`.
  - 모든 case의 `scenario`를 `shared_2min`으로 통일.
  - Virtual Broadcast 패널에 단일 시나리오
    `공통 2분 시나리오: 교수님의 메이드`와 `Start Scenario` /
    `Stop Scenario`를 추가.
  - `Start Scenario`가 현재 case 값을 유지한 채
    `/credo/vtuber-mode/start` -> `/credo/vtuber-mode/monologue` ->
    약 2분 타임라인 virtual chat 자동 주입 순서로 실행되도록 구현.
  - `Stop Scenario`가 남은 `setTimeout` 타이머를 취소하도록 구현.
  - Case 6은 `component_mode=none`, `scheduling_mode=serial`이며 UI meta에서
    contextual mapping을 `none`으로 표시. Neutral Random은 FastTrack ON인
    별도 Case 4로 유지.
  - Scenario `broadcast_direction`이 한국어 진행을 지시할 수 있도록
    Open-LLM-VTuber runtime prompt 문구를 완화.
  - Docs updated: live usage guide, methodology, protocol, runtime flow,
    root README, AI_NPC_System README, integration README, docs index.
- Verification:
  - `apply_integration.py --activate` completed.
  - Python compile passed for vendored routes and patcher.
  - JS syntax check passed for source and vendored overlay JS.
  - Playwright CLI rendered `http://127.0.0.1:12393` and showed the scenario
    controls.
  - With fetch mocked to avoid real LLM/TTS, clicked Neutral Random and
    `Start Scenario`; observed payload order:
    `/credo/experiment-mode`, `/credo/vtuber-mode/start`,
    `/credo/vtuber-mode/monologue`, then timed `/virtual-chat`.
  - Clicked `Stop Scenario` before the first timed chat in a separate mocked
    run; no virtual-chat calls were emitted afterward.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `AI_NPC_System/docs/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber before live recording so route and overlay changes
    are loaded by the running server process.
  - Record six videos by clicking one `Experiment cases` button, then
    `Start Scenario`, then OBS recording for each case.
- Do not touch:
  - `AI_NPC_System/VoiceSample/` and voice/TTS sample assets unless the user
    explicitly asks in the voice/TTS thread.

## 2026-05-27 03:59 KST - Seven Run Preset Buttons

- Owner/chat: framework/runtime + docs/report
- User request:
  - YAML에 제시한 7개 run preset을 클릭하면 해당 실험 설정이 한 번에
    바뀌도록 구현했는지 확인.
- Done:
  - 기존 구현은 개별 factor 버튼 방식이었음을 확인하고, 다음 preset
    버튼을 추가:
    `f1_grounded_serial`, `f1_emotion_only_serial`,
    `f1_intent_only_serial`, `f1_neutral_random_serial`,
    `f2_grounded_parallel`, `f2_grounded_serial`, `f2_no_fasttrack`.
  - 각 preset 클릭 시 `component_mode`, `selection_policy`,
    `scheduling_mode`, `experiment_run_id`, `experiment_factor`, `scenario`가
    함께 전송되도록 프론트엔드 payload 갱신.
  - Backend status/factor update route가 `experiment_run_id`,
    `experiment_factor`, `scenario`를 저장하고 agent config에 반영하도록
    `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py` 갱신.
  - Agent latency metadata와 `module_events.csv` schema에
    `experiment_run_id`, `experiment_factor`, `scenario` 컬럼 추가.
  - `apply_integration.py`도 같은 route patch를 재적용할 수 있도록 갱신.
  - Docs updated: usage guide, methodology, protocol, runtime flow, README.
- Verification:
  - `apply_integration.py --activate` completed.
  - Python compile passed for routes, agent, patcher, config, latency observer.
  - JS syntax check passed for source and vendored overlay JS.
  - `git diff --check` passed for touched files.
  - Playwright CLI rendered `http://127.0.0.1:12393`; preset buttons visible.
  - Clicked `f2_no_fasttrack`; UI marked that preset active and switched
    architecture to `No FastTrack` with meta text showing `f2_no_fasttrack`.
  - Current running backend is still pre-restart: `/credo/vtuber-mode/status`
    reflects `component_mode=none`, `scheduling_mode=serial`, but does not yet
    return `experiment_run_id` fields until Open-LLM-VTuber is restarted.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/latency_observer.py`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `AI_NPC_System/docs/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber before backend route verification.
  - After restart, click a preset and confirm `/credo/vtuber-mode/status`
    returns `experiment_run_id`, `experiment_factor`, and `scenario`.
  - Confirm new `module_events.csv` rows include the same three fields.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets or generated audio bundles unless explicitly asked.

## 2026-05-27 03:27 KST - Two-Factor UI And Broadcast Direction

- Owner/chat: framework/runtime + docs/report
- User request:
  - Virtual Broadcast 실험 선택 UI를 개정된 2요인 방법론에 맞춤.
  - Contextual Mapping에 Neutral Random을 추가하고, No FastTrack을
    Scheduling & Architecture 절대 대조군으로 이동.
  - LLM 방송 디렉션 프롬프트 입력창을 추가하고, 기본 VTuber LLM 발화를
    50자 이상으로 유도.
- Done:
  - Frontend overlay:
    - Contextual mapping: Grounded / Emotion only / Intent only / Neutral random.
    - Scheduling architecture: Parallel / Serial / No FastTrack.
    - `LLM Settings` 패널과 broadcast direction textarea/Apply 버튼 추가.
  - Backend/runtime:
    - `selection_policy=neutral_random` 허용.
    - Neutral Random은 실제 감정/의도를 무시하고 Neutral 후보에서 랜덤 선택.
    - No FastTrack은 `component_mode=none`, `scheduling_mode=serial`로 정규화.
    - `/credo/vtuber-mode/config` 추가.
    - broadcast direction을 idle, live chat batch, manual monologue, donation
      metadata/prompt에 전달.
  - LLM defaults:
    - `CREDO_VTUBER_LLM_MAX_TOKENS=96`
    - `CREDO_VTUBER_MAX_SPOKEN_WORDS=40`
    - VTuber prompt에 at least 50 characters / 18-40 spoken words 기준 반영.
  - Integration reapplied to `vendor/open-llm-vtuber`.
  - Docs updated for 4 x 3 condition grid and new operation path.
- Verification:
  - `apply_integration.py --activate` completed.
  - Python compile passed for routes, agent, integration patcher, config, and cache modules.
  - JS syntax check passed for source and vendored `credo-vtuber-mode.js`.
  - `git diff --check` passed for touched files.
  - Playwright CLI rendered `http://127.0.0.1:12393`; confirmed visible controls:
    Neutral random, No FastTrack, LLM Settings, broadcast direction textarea.
  - Console still shows expected mic/VAD permission warning and early
    `/undefined/undefined.model3.json` 404; Live2D later loads.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/fast_track_audio_cache.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `AI_NPC_System/docs/README.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber before backend route testing. The currently running
    server was started before this patch; its `/credo/vtuber-mode/status`
    response did not yet include `broadcast_direction`.
  - After restart, verify:
    - `/credo/vtuber-mode/status` includes `broadcast_direction`.
    - `/credo/vtuber-mode/config` accepts broadcast direction.
    - `Neutral random` logs `selection_policy=neutral_random`.
    - `No FastTrack` logs `component_mode=none`, `scheduling_mode=serial`.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets or generated audio bundles unless explicitly asked.

## 2026-05-27 03:05 KST - StyleBERT Short Interjection Bundle

- Owner/chat: voice/TTS
- User request:
  - Long `HAHAHAHA`/repeated nonverbal laughter is uncanny; do not use it.
  - Regenerate nonverbal/short interjection expressions with current TTS.
- Done:
  - Replaced interjection carrier set with short safe carriers only:
    `Aw!`, `Eh?`, `Heh.`, `Hm.`, `Huh?`, `Mm.`, `Oh!`, `Oh.`, `Oh...`,
    `Oh?`, `Ugh.`, `Yay!`.
  - Updated generation script to support `--engine stylebert_vits2` and make
    StyleBERT the default interjection engine.
  - Regenerated the active bundle in-place:
    `AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/`.
  - Updated prompt defaults/profile text to avoid long laughter strings and use
    at most one short `Heh.` token when amusement is natural.
  - Updated readiness check label from Fish-specific interjection bundle to
    generic interjection audio bundle and accepted StyleBERT reference metadata.
  - Updated docs/README references from active Fish nonverbal bundle to active
    StyleBERT short interjection bundle.
  - Wrote report:
    `AI_NPC_System/reports/stylebert_interjection_bundle_2026-05-27/summary.md`.
- Verification:
  - `items=65`, `cells=20`, `missing_audio=0`, bad repeated-laugh text count `0`.
  - Audio durations: min `0.372 s`, median `0.499 s`, max `0.639 s`.
  - StyleBERT synthesis latency: min `64.079 ms`, median `73.814 ms`,
    max `313.005 ms`.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` result:
    `READY`; interjection bundle detail shows
    `engine=stylebert_vits2; reference_id=credo_voice_sample_en`.
- Files touched:
  - `AI_NPC_System/scripts/build_interjection_audio_bundle.py`
  - `AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/manifest.json`
  - `AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/audio/`
  - `AI_NPC_System/cover_composer.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/docs/usada_pekora_persona.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - `vendor/open-llm-vtuber/characters/credo_latency_cover.yaml`
  - `AI_NPC_System/scripts/check_runtime_readiness.py`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/integrations/open_llm_vtuber/README.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/docs/runtime_stack_stability.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `AI_NPC_System/docs/fish_speech_integration.md`
  - `AI_NPC_System/reports/runtime_readiness_latest.{json,md}`
  - `AI_NPC_System/reports/stylebert_interjection_bundle_2026-05-27/`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Use the same manifest path; runtime route does not need path changes.
  - Do not reintroduce long laugh strings into prompts, carrier lists, or
    generated interjection text.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`

## 2026-05-27 00:09 KST - None Control Correction

- Owner/chat: docs/report validation
- User request:
  - `None` 대조군은 FastTrack 미사용/SlowTrack-only가 아니라,
    맥락 참조 없이 `Neutral` 후보에서 랜덤 추출하는 조건이라고 정정.
- Done:
  - 원인 확인:
    이전 보고서가 실험 요인 `None`을 기존 UI의 `No FastTrack`
    (`component_mode=none`)에 잘못 매핑했음.
  - 새 정정 보고서 작성:
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-27/report.md`.
  - 이전 보고서
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/report.md`
    전체를 superseded 포인터로 축소.
  - live usage guide, runtime flow, paper draft의 `No FastTrack` 표기를
    정정/경고 처리해서 study `None`과 component ablation을 분리.
  - user study protocol의 `no FastTrack` 예외 문구를 Neutral 랜덤
    FastTrack 정의로 정정.
  - `benchmark_experiment_factors.py`의 simulation 정의를 정정:
    `none`도 `component_mode=both`, `selection_policy=neutral_random`으로
    모델링하며 FastTrack을 끄지 않음.
  - 새 100-trial deterministic benchmark 생성:
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-27/benchmark_assumption/`.
  - 이전 잘못된 SlowTrack-only benchmark 출력
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/benchmark_assumption/`
    삭제.
- Verification:
  - Corrected CSV rows show `none` as:
    `component_mode=both`, `mapping_level=none`,
    `selection_policy=neutral_random`.
  - Corrected `none + parallel` first-audio median:
    `80.239 ms`, not the old erroneous ~3.3 s SlowTrack-only value.
  - Current runtime mismatch remains:
    frontend button still says `No FastTrack` and sends `component_mode=none`;
    backend currently accepts only `grounded`, `emotion_only`,
    `response_act_only`; agent would need a distinct `neutral_random`
    selection policy to run the corrected live condition.
- Files touched:
  - `AI_NPC_System/scripts/benchmark_experiment_factors.py`
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-27/report.md`
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-27/benchmark_assumption/`
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/report.md`
  - deleted `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/benchmark_assumption/`
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `AI_NPC_System/docs/user_study_protocol.md`
  - `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Do not use current `No FastTrack` as the experiment `None` condition.
  - Runtime fix should add a separate `neutral_random` mapping policy with
    FastTrack enabled and Neutral-bucket random selection.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
    unless the user explicitly authorizes the runtime behavior patch.
  - `AI_NPC_System/VoiceSample/`

## 2026-05-26 22:53 KST - Corrected Six Factor-Level Report

- Owner/chat: voice/TTS + docs/report validation
- User request:
  - 이전 "6가지 케이스"는 manifest `response_act` 6종이 아니라 실험 요인
    6수준을 뜻한다고 정정:
    Contextual Mapping (`Grounded`, `Emotion Only`, `Intent Only`, `None`) +
    Scheduling Architecture (`Parallel`, `Serial`).
  - 현황을 다시 파악하고 이 기준으로 테스트/보고서 작성.
- Done:
  - 기존 22:29 `Manifest Six-Case StyleBERT TTS Test`는 음성/manifest
    샘플 검증으로는 남기되, 이번 실험 6케이스 보고서로는 superseded 처리.
  - 현재 기본값 확인:
    `FAST_TRACK_ENABLED=1`, `FAST_TRACK_TTS_MODE=stylebert_vits2`,
    `CREDO_FASTTRACK_COMPONENT_MODE=both`,
    `CREDO_FASTTRACK_SELECTION_POLICY=grounded`,
    `CREDO_CONTEXT_SCHEDULING_MODE=parallel`,
    `STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en`.
  - UI/backend/agent가 6수준을 지원하는지 확인:
    `Grounded`, `Emotion only`, `Intent only`, `No FastTrack`,
    `Parallel`, `Serial`.
  - 보고서 작성:
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/report.md`.
  - 혼동 방지를 위해 의존성 fallback 값이 섞인 임시 `benchmark/` 출력은 삭제하고,
    보고서에서 쓰는 deterministic assumption benchmark만 보존.
- Verification:
  - 100-trial simulation CSV:
    `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/benchmark_assumption/factor_simulation.csv`.
  - Full factorial은 4 mapping levels x 2 scheduling levels = 8 recorded cells.
  - `None`은 FastTrack 미사용 대조군이라 `selection_policy`가 행동적으로 무효.
  - 현재 셸에서는 FastTrack live probe가 `spacy`/ML 의존성 부족으로 fallback되어
    실제 성능 근거로 쓰지 않음.
- Files touched:
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/report.md`
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/benchmark_assumption/`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - 실험 UI/분석에서는 6개 label을 요인 수준으로 쓰고, 기록 데이터는 8-cell grid로 분석.
  - 실제 runtime 성능은 정상 스택 실행 후
    `AI_NPC_System/latency_logs/module_events.csv`의
    `component_mode`, `selection_policy`, `scheduling_mode` 열로 검증.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/VoiceSample/`

## 2026-05-26 22:39 KST - Live Usage Guide

- Owner/chat: docs/report + framework/runtime handoff
- User request:
  - 최신 현황을 확인하고, 현재 CREDO live runtime 사용법을 정리.
- Done:
  - 최신 공유 현황 확인:
    21:30 기준으로 UI는 `Contextual mapping x Scheduling architecture`
    구조이며, forced `peko` speech rule은 제거됨.
  - 현재 `http://127.0.0.1:12393` Open-LLM-VTuber 서버는 실행 중이 아님.
  - 새 사용법 문서 작성:
    `AI_NPC_System/docs/credo_live_usage_guide.md`.
  - 가이드에 다음을 정리:
    quick start, status check, browser panel, 1:1 Chat, Virtual Broadcast,
    YouTube Live, donation, manual reactions, experiment controls, logs,
    troubleshooting.
  - `README.md`와 `AI_NPC_System/README.md`에서 새 사용법 가이드를 안내하도록 갱신.
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`의 runtime mode,
    contextual mapping, scheduling 설명을 최신 구조로 보정.
- Verification:
  - `git diff --check` passed for the usage guide and updated README/runtime-flow docs.
  - Current status probe:
    `curl http://127.0.0.1:12393/credo/vtuber-mode/status` failed because the server is not running.
- Files touched:
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
  - `README.md`
  - `AI_NPC_System/README.md`
  - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - For live testing, start:
    `AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45`.
  - Then open `http://127.0.0.1:12393` and follow
    `AI_NPC_System/docs/credo_live_usage_guide.md`.
  - Verify `/credo/vtuber-mode/status` returns the current `mode`,
    mapping, and scheduling values after restart.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets unless the user explicitly asks for voice/TTS work.

## 2026-05-26 22:29 KST - Manifest Six-Case StyleBERT TTS Test

- Owner/chat: voice/TTS validation
- User request:
  - 현재 manifest/페르소나/TTS 현황을 파악하고 6가지 케이스를 테스트해 보고서 작성.
  - 스타일 태그는 없는 것으로 보고, manifest 감정 라벨링 유지 여부 확인.
- Done:
  - 현재 설정 확인:
    `FAST_TRACK_TTS_MODE=stylebert_vits2`,
    `STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en`,
    `STYLEBERT_VITS2_LANGUAGE=EN`,
    `STYLEBERT_VITS2_STYLE=Neutral`.
  - manifest 확인:
    `personality_id=usada_pekora_v1`, `items=600`, `cells=24`,
    `style_tags_removed=true`.
  - 6개 `response_act` 대표 케이스를 기존 manifest에서 선택해 최종
    StyleBERT VoiceSample 모델로 실제 wav 합성.
  - 테스트 리포트 작성:
    `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/report.md`.
- Verification:
  - `validate_persona_bundle.py` result: `OK`.
  - Emotion labels preserved:
    `Positive`, `Negative`, `Surprise`, `Neutral`; each 150 items.
  - Response act labels preserved:
    `QUESTION`, `INFORM`, `ACKNOWLEDGE`, `DIRECTIVE`, `EXPRESSIVE`, `REJECT`;
    each 100 items.
  - Style tag count: `0`; bracket-style TTS cue count: `0`.
  - 6-case synthesis:
    cold first request `13.853s`; warm mean `0.198s`;
    warm min/max `0.156s / 0.249s`.
  - Generated audio:
    `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/*.wav`.
- Files touched:
  - `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/report.md`
  - `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/results.json`
  - `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/results.tsv`
  - `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/persona_bundle_validation.{json,md}`
  - six generated wav files under the same report directory
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Treat manifest emotion/response labels as routing metadata.
  - Treat StyleBERT TTS as plain-text synthesis using `Neutral`; no style tags.
  - If persona no longer wants frequent `peko`, regenerate manifest text later;
    current manifest is technically valid but still Pekora/peko-heavy.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/VoiceSample/`

## 2026-05-26 21:30 KST - Contextual Mapping UI And Natural Speech

- Owner/chat: framework/runtime
- User request:
  - Current experiment design is 2 factors:
    Contextual Mapping (`Grounded`, `Emotion Only`, `Intent Only`, `None`) x
    Scheduling Architecture (`Parallel`, `Serial`).
  - Update shared live-status markdown.
  - Make the web UI switch these conditions by clicking.
  - Stop forcing persona suffixes such as `peko`; define a subtler speech rule later.
- Done:
  - UI labels updated:
    `Contextual mapping` with `Grounded`, `Emotion only`, `Intent only`, `No FastTrack`;
    `Scheduling architecture` with `Parallel`, `Serial`.
  - Backend factor values remain stable for CSV/API compatibility:
    `grounded`, `emotion_only`, `response_act_only`, `component_mode=none`,
    `parallel`, `serial`.
  - SlowTrack/persona prompts no longer request forced `peko` suffixes.
  - Runtime speech sanitizer strips legacy `peko` tokens before display/TTS, so existing manifest text can be reused without rebuilding 600 items immediately.
  - `build_pekora_reaction_manifest.py` no longer adds forced `peko` suffixes if the manifest is regenerated later.
  - Docs updated with the 2-factor design and natural-speech note.
- Verification:
  - Integration reapplied to `vendor/open-llm-vtuber`.
  - Vendor character prompt no longer asks for `peko`.
  - Vendor idle prompt no longer asks for `peko`.
  - UI source and vendor copy show the new clickable labels.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/docs/usada_pekora_persona.md`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - docs/reports for methodology/status
  - regenerated vendor Open-LLM-VTuber files
- Next handoff:
  - Restart stack before UI testing.
  - Run `AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45`.
  - Verify a live FastTrack sentence does not audibly include `peko`.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - StyleBERT model assets unless user moves back to voice/TTS work.

## 2026-05-26 21:10 KST - Remove Dynamic FastTrack Assembly Factor

- Owner/chat: framework/runtime
- User request:
  - 확률적 전이 기반 분석 구조는 유지하되, `spaCy` 키워드 유무와 큐 상태로 A/B/C를 실시간 조립하는 Dynamic 조합 요인은 제외.
  - 구현 상태 확인 후 필요 없는 실험 조건과 표현 정리.
- Done:
  - Primary study factors reduced to mapping basis x scheduling:
    `grounded`, `emotion_only`, `response_act_only`, `none` crossed with `parallel`, `serial`.
  - UI no longer exposes `random`, `language_only`, or `nonverbal_only` as primary experiment buttons.
  - Backend `/credo/experiment-mode` accepts only `component_mode in {"both", "none"}` and `selection_policy in {"grounded", "emotion_only", "response_act_only"}`.
  - Runtime agent supports emotion-only and response-act-only persona lookup while preserving the grounded router-v3 path.
  - `FAST_TRACK_KEYWORD_ECHO_ENABLED=0`; spaCy keyword extraction remains metadata only and no longer emits an extra echo utterance by default.
  - Benchmark script updated to simulate the current 8-cell mapping/scheduling grid and StyleBERT language TTS labels.
  - Docs/reports updated:
    `AI_NPC_System/docs/research_methodology_experiment_plan.md`,
    `AI_NPC_System/docs/user_study_protocol.md`,
    `AI_NPC_System/integrations/open_llm_vtuber/README.md`,
    `AI_NPC_System/reports/current_status_2026-05-26.md`,
    `AI_NPC_System/reports/methodology_update_2026-05-26.md`.
- Verification:
  - `apply_integration.py --activate` completed and regenerated vendor files.
  - Python compile passed for modified source/vendor runtime files.
  - Shell syntax passed for project config and experiment/run scripts.
  - Frontend JS syntax passed for source and vendor overlay files.
  - Persona bundle smoke:
    grounded, emotion-only, and response-act-only lookups all returned valid Pekora text.
  - Pekora manifest validation:
    `OK`, 24 cells, 600 items, duplicate warnings 0, style tag count `"": 600`.
  - Benchmark smoke wrote 8 mapping/scheduling rows to `/tmp/credo_mapping_benchmark_smoke`.
- Files touched:
  - `AI_NPC_System/fast_track_audio_cache.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/scripts/benchmark_experiment_factors.py`
  - `AI_NPC_System/scripts/run_experiment_condition.sh`
  - docs/reports listed above
  - regenerated vendor Open-LLM-VTuber files
- Next handoff:
  - Restart the stack before testing UI because route/frontend changes require a fresh Open-LLM process.
  - Run `AI_NPC_System/scripts/run_credo_stack.sh --profile live --health-timeout 45`.
  - Test `/credo/experiment-mode` with `grounded`, `emotion_only`, `response_act_only`, and `component_mode=none`.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - voice model selection/fine-tuning assets unless user explicitly moves back to voice/TTS work.

## 2026-05-26 20:55 KST - Voice/TTS Cleanup Finalization

- Owner/chat: voice/TTS cleanup
- User request:
  - 최종 선택한 VoiceSample-finetuned StyleBERT 목소리만 남기고, 그동안 생성한
    후보 샘플/자료/중간 산출물은 영구 삭제.
  - 진행 상황을 `CODEX_SHARED_WORKLOG.md`로 공유.
- Done:
  - 최종 VoiceSample StyleBERT 모델만 유지:
    `vendor/Style-Bert-VITS2/model_assets/credo_voice_sample_en/`.
  - 유지 파일:
    `config.json`, `style_vectors.npy`,
    `credo_voice_sample_en_e160_s323.safetensors`.
  - 최종 샘플/레이턴시/요약만 유지:
    `AI_NPC_System/reports/stylebert_vits2_voice_sample_finetune_2026-05-26/`.
  - 삭제한 이전 후보 리포트:
    `edge_voice_selection_2026-05-26`,
    `voice_tts_selection_2026-05-26`,
    `stylebert_vits2_voice_sample_2026-05-26`,
    `stylebert_vits2_english_rikka_2026-05-26`,
    `stylebert_vits2_hf_english_candidates_2026-05-26`.
  - 삭제한 이전 후보 모델:
    `rikka_botan_english`, `thepioneer_myvoiceclone`, `mofa_girl_jpextra`.
  - 삭제한 중간/학습 부산물:
    `vendor/Style-Bert-VITS2/Data/credo_voice_sample_en`,
    `vendor/Style-Bert-VITS2/pretrained`,
    `vendor/Style-Bert-VITS2/pretrained_jp_extra`,
    `vendor/Style-Bert-VITS2/slm/wavlm-base-plus/pytorch_model.bin`,
    최종 모델 폴더 안의 중간 `credo_voice_sample_en_e*.safetensors`.
  - `AI_NPC_System/reports/stylebert_vits2_voice_sample_finetune_2026-05-26/summary.md`
    를 정리 후 실제 상태 기준으로 갱신.
- Verification:
  - 최종 모델 폴더에는 3개 파일만 남음:
    `config.json`, `style_vectors.npy`,
    `credo_voice_sample_en_e160_s323.safetensors`.
  - 최종 리포트 폴더에는 `summary.md`, `e160_s323/` 샘플 6개,
    `e160_s323/latency.tsv`만 남음.
  - 이전 후보 리포트/후보 모델/pretrained/training data 경로는 더 이상 없음.
  - Python compile passed:
    `AI_NPC_System/config.py`,
    `AI_NPC_System/stylebert_vits2_client.py`,
    `AI_NPC_System/scripts/select_tts_engine.py`.
  - Shell syntax passed:
    `AI_NPC_System/project_config.sh`,
    `AI_NPC_System/scripts/start_stylebert_vits2_server.sh`,
    `AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh`.
  - Current config check:
    `FAST_TRACK_TTS_MODE=stylebert_vits2`,
    `STYLEBERT_VITS2_MODEL_NAME=credo_voice_sample_en`,
    `STYLEBERT_VITS2_LANGUAGE=EN`,
    `STYLEBERT_VITS2_DEVICE=cuda`.
  - `AI_NPC_System/scripts/select_tts_engine.py --status` currently reports
    Open-LLM-VTuber TTS `edge_tts`, FastTrack TTS `stylebert_vits2`.
- Files touched:
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/stylebert_vits2_client.py`
  - `AI_NPC_System/scripts/start_stylebert_vits2_server.sh`
  - `AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh`
  - `AI_NPC_System/scripts/select_tts_engine.py`
  - `AI_NPC_System/reports/stylebert_vits2_voice_sample_finetune_2026-05-26/summary.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Start voice server with:
    `AI_NPC_System/scripts/start_stylebert_vits2_server.sh`.
  - Then run:
    `AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh`.
  - If the goal is still “all TTS including SlowTrack/Open-LLM default TTS must use
    StyleBERT,” re-check the Open-LLM config because current `--status` reports
    Open-LLM-VTuber TTS as `edge_tts` while FastTrack is `stylebert_vits2`.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/VoiceSample/`

## 2026-05-26 20:55 KST - VTuber Frontend Mode UI

- Owner/chat: framework/runtime + frontend overlay
- User request:
  - 프론트엔드에서 세 가지 모드 제공:
    YouTube live connection, virtual broadcast, 1:1 conversation.
  - YouTube live mode에서는 YouTube가 채팅을 제공하므로 가상 채팅 UI 제거.
  - Virtual broadcast mode에서는 오른쪽 사이드에 Twitch식 가상 채팅 로그 표시.
  - 가상 donation 버튼 입력이 리액션 프롬프트로 들어가게 연결.
  - TTS 발화 중 입모양이 다시 움직이게 하고, 평상시 몸도 은근히 흔들리게 함.
- Done:
  - `credo-vtuber-mode.js` 오버레이에 `YouTube Live`, `Virtual Broadcast`, `1:1 Chat` 런타임 모드 버튼 추가.
  - `Virtual Broadcast` 선택 시 오른쪽 fixed dock `Virtual Broadcast Chat`을 표시하고, 가상 채팅/도네이션 로그를 append하도록 구현.
  - `YouTube Live` 선택 시 가상 채팅 dock을 숨기고 YouTube 연결 입력만 보이도록 구현.
  - `1:1 Chat` 선택 시 방송 채팅 UI 없이 WebSocket `text-input`으로 직접 대화 입력을 보내도록 구현.
  - donation 입력 필드 `donor / amount / message`를 추가하고 `/credo/vtuber-mode/donation`으로 전달하도록 연결.
  - `routes.py`의 `vtuber_mode`에 `mode` 상태를 추가:
    `direct_chat`, `virtual_broadcast`, `youtube_live`.
  - `/credo/vtuber-mode/start`가 요청 mode를 받아 YouTube bridge 시작 여부를 분기.
  - YouTube mode에서 `/credo/vtuber-mode/virtual-chat` 호출 시 409로 막아 가상 채팅이 섞이지 않게 함.
  - `/credo/vtuber-mode/stop`은 `direct_chat`으로 되돌리고 bridge 참조를 정리.
  - TTS audio payload의 `volumes`가 있으면 `ParamMouthOpenY`를 항상 볼륨 기반으로 움직이도록 보정.
  - `startAmbientIdlePulse()`를 추가해 발화 중이 아닐 때도 Live2D angle/body/breath parameter가 미세하게 흔들리도록 함.
  - 구버전 localStorage experiment mode alias(`live_edge_cover`, `fish_cover`, `fish_no_cover`, `fast_no_cover`)를 현재 Edge mode로 normalize.
  - `apply_integration.py --activate` 재실행 후에도 위 frontend/route 변경이 유지되도록 patch logic 반영.
- Verification:
  - JS syntax passed using Windows Node:
    `node.exe --check` on integration frontend and vendored frontend copies.
  - Python compile passed:
    `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`,
    `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`.
  - `git diff --check` passed for touched frontend/integration files.
  - Playwright browser smoke against running `http://127.0.0.1:12393`:
    1:1 Chat panel rendered, Virtual Broadcast showed right chat dock, YouTube Live hid the dock and showed YouTube inputs.
  - Console showed expected mic/VAD permission warning in headless/automation context and existing non-blocking early `/undefined/undefined.model3.json` 404 before model initialization.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js` was refreshed from the integration frontend copy but appears git-ignored/untracked by status scope.
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py` was updated in the live vendor runtime but appears git-ignored/untracked by status scope.
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - Restart Open-LLM-VTuber/CREDO stack before relying on new backend route state; the currently running server was loaded before this route change and still returned old status fields such as `live_edge_cover`.
  - After restart, verify `/credo/vtuber-mode/status` returns `mode`.
  - Run one live smoke per mode:
    1:1 direct text, Virtual Broadcast chat buffer + donation, YouTube mode bridge start/no virtual chat dock.
  - If visual QA continues, use browser screenshots to confirm the right dock does not overlap the existing Open-LLM side panel on narrow screens.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - voice sample selection or StyleBERT model training assets
  - FastTrack router/manifest/persona logic unless explicitly requested

## 2026-05-26 20:02 KST - StyleBERT Runtime Smoke

- Owner/chat: runtime verification + cleanup
- User request:
  - StyleBERT을 전체 TTS로 세팅한 뒤 전체적으로 잘 구동되는지 검토하고 테스트.
- Done:
  - StyleBERT `/voice` 호출 방식 수정: 서버가 요구하는 query parameter 기반 POST로 AI_NPC client와 Open-LLM TTS adapter를 맞춤.
  - `vendor/Style-Bert-VITS2/config.yml` `server.limit=-1`로 설정해 SlowTrack 장문 발화가 100자 제한에 막히지 않게 함.
  - `check_runtime_readiness.py`가 Open-LLM venv Python으로 재실행되도록 수정해 `transformers missing` 오탐 제거.
  - `run_credo_stack.py --profile live --health-timeout 45`로 StyleBERT -> LLM -> Open-LLM-VTuber 전체 스택 실행 검증.
  - 실제 브라우저에서 CREDO overlay의 1:1 Chat, Virtual Broadcast, YouTube Live 모드 전환 확인.
  - 1:1 Chat 입력으로 FastTrack + SlowTrack audio payload와 lip sync/expression playback 확인.
  - 최신 smoke report 작성:
    `AI_NPC_System/reports/runtime_smoke_latest.md`.
- Verification:
  - Runtime readiness: `READY` while stack was running.
  - Services healthy:
    StyleBERT `/docs`, LLM `/v1/models`, Open-LLM `/`.
  - `/credo/interjections`: 65 items returned.
  - `/credo/experiment-modes`: StyleBERT labels, `slow_tts_mode=open_llm`, fallback enabled.
  - Open-LLM TTS factory: `stylebert_vits2` instantiated with `credo_voice_sample_en`.
  - Open-LLM StyleBERT TTS smoke: wav 311,340 bytes, 19.372 s cold-ish first call.
  - AI_NPC FastTrack StyleBERT smoke: wav 179,244 bytes, 0.360 s warm call.
  - End-to-end text-input smoke produced:
    `Fine, I heard you, huh peko!` followed by a Pekora-style SlowTrack joke response.
- Files touched:
  - `AI_NPC_System/stylebert_vits2_client.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/stylebert_vits2_tts.py`
  - `AI_NPC_System/scripts/check_runtime_readiness.py`
  - `vendor/open-llm-vtuber/src/open_llm_vtuber/tts/stylebert_vits2_tts.py`
  - `vendor/Style-Bert-VITS2/config.yml`
  - `AI_NPC_System/reports/runtime_smoke_latest.md`
  - `CODEX_SHARED_WORKLOG.md`
- Next handoff:
  - If testing from a fresh shell, run:
    `AI_NPC_System/scripts/run_credo_stack.py --profile live --health-timeout 45`.
  - Browser automation leaves expected mic/VAD permission warnings unless mic permission is granted.
  - There is still a non-blocking early `/undefined/undefined.model3.json` 404 before the configured Live2D model initializes.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - FastTrack router/manifest/persona/async-loop logic unless the user explicitly asks.

## 2026-05-26 19:29 KST - StyleBERT All-TTS Wiring

- Owner/chat: voice/TTS + runtime config boundary
- User request:
  - 최종 선택된 `credo_voice_sample_en` StyleBERT-VITS2 모델을 모든 TTS 경로에 사용하도록 세팅.
  - FastTrack 라우터/매니페스트/페르소나/비동기 루프/UI/데이터셋 구조는 변경 금지.
- Done:
  - Open-LLM-VTuber TTS 엔진으로 `stylebert_vits2` 어댑터 추가.
  - `OPEN_LLM_VTUBER_TTS_MODEL=stylebert_vits2`로 SlowTrack 기본 TTS를 StyleBERT로 전환.
  - `OPEN_LLM_VTUBER_SLOW_TTS_MODE=open_llm` 및 `SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK=1`로 CREDO agent가 SlowTrack 음성을 Open-LLM TTS 엔진에서 합성하도록 연결.
  - `FAST_TRACK_TTS_MODE=stylebert_vits2` 유지. FastTrack/SlowTrack 모두 같은 최종 모델 `credo_voice_sample_en` 사용.
  - `apply_integration.py --activate` 재실행 시에도 StyleBERT TTS schema/factory/character config가 유지되도록 반영.
  - `run_credo_stack.py --profile live`가 `stylebert -> llm -> open-llm` 순서로 실행되도록 수정.
- Verification:
  - Python compile passed:
    StyleBERT adapter, Open-LLM TTS factory/schema, integration script, config, stack runner.
  - Shell syntax passed:
    `project_config.sh`, `run_open_llm_vtuber_credo.sh`, `start_stylebert_vits2_server.sh`.
  - Open-LLM config validation passed:
    `tts_model=stylebert_vits2`, `stylebert_model=credo_voice_sample_en`, `slow_tts_mode=open_llm`.
  - TTS factory instantiate passed:
    `TTSFactory.get_tts_engine("stylebert_vits2", ...)`.
  - `select_tts_engine.py --status` reports:
    Open-LLM-VTuber TTS `stylebert_vits2`, FastTrack TTS `stylebert_vits2`.
  - Runtime services were not started in this handoff; status showed StyleBERT/LLM/Open-LLM all not running.
- Files touched:
  - `AI_NPC_System/integrations/open_llm_vtuber/stylebert_vits2_tts.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_character.yaml`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/scripts/select_tts_engine.py`
  - `AI_NPC_System/scripts/run_open_llm_vtuber_credo.sh`
  - `AI_NPC_System/scripts/run_credo_stack.py`
  - Generated vendored files under `vendor/open-llm-vtuber/`.
- Next handoff:
  - Start with `AI_NPC_System/scripts/run_credo_stack.py --profile live`.
  - If Open-LLM was already running, restart it; old processes will not pick up the new `stylebert_vits2` backend route/config.
  - If StyleBERT server is not healthy, start/check `AI_NPC_System/scripts/start_stylebert_vits2_server.sh`.
- Do not touch:
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/VoiceSample/`

## 2026-05-26 17:45 KST - Framework Runtime Handoff

- Owner/chat: framework/runtime
- User request:
  - 목소리 실험은 다른 채팅으로 분리.
  - 이 채팅은 CREDO 프레임워크/런타임/페르소나/라우터만 유지.
  - 페르소나는 Usada Pekora, 언어 style tags 제거, FastTrack language는
    prebuilt wav 검색이 아니라 선택 텍스트의 빠른 TTS 실시간 합성 방향.
- Done:
  - Active language manifest:
    `AI_NPC_System/fasttrack_assets/text/pekora_reaction_bundle_v1/manifest.json`
  - Manifest structure:
    `4 emotions x 6 response acts x 25 variants = 600`.
  - Active emotions:
    `Positive`, `Negative`, `Surprise`, `Neutral`.
  - Active response acts:
    `QUESTION`, `INFORM`, `ACKNOWLEDGE`, `DIRECTIVE`, `EXPRESSIVE`, `REJECT`.
  - All active language reactions include `peko`; style tag fields are absent
    from active language items.
  - `AI_NPC_System/fasttrack_router_v3.py` added and stabilized.
  - `analyze_and_route_chat_v3(text, prefetch_queue)` behavior:
    ready SlowTrack prefetch returns `{"bypass": true}` and skips FastTrack;
    otherwise routes through emotion/intent fallback and cell-local FAISS Top-3.
  - SetFit/Torch background loading disabled by default:
    `FASTTRACK_ROUTER_V3_BACKGROUND_LOAD_SETFIT=0`.
  - Open-LLM-VTuber integration reapplied after source changes.
  - Current report updated:
    `AI_NPC_System/reports/current_status_2026-05-26.md`.
- Verification:
  - Manifest validation: `OK`.
  - Manifest counts: `24` cells, `600` items, `25` variants per cell.
  - Duplicate warnings: `0`.
  - Style count: `"": 600`.
  - Active text scan: no `style_tag` field in active language items, no missing
    `peko`.
  - Router smoke: positive question sample returned in about `77 ms`; Top-3
    all from `positive_acknowledge`; all contained `peko`.
  - Bypass smoke: completed future returned `{"bypass": true}`.
  - Python/shell syntax checks passed for touched runtime files.
- Files touched:
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/project_config.sh`
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/fast_track_audio_cache.py`
  - `AI_NPC_System/cover_composer.py`
  - `AI_NPC_System/scripts/build_pekora_reaction_manifest.py`
  - `AI_NPC_System/scripts/validate_persona_bundle.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
  - `AI_NPC_System/reports/current_status_2026-05-26.md`
  - `AI_NPC_System/reports/persona_bundle_validation_latest.{json,md}`
  - Vendored Open-LLM-VTuber files regenerated by `apply_integration.py`.
- Next handoff:
  - Start stack and run browser/UI smoke after restart.
  - Confirm CREDO VTuber mode order:
    nonverbal interjection+motion -> realtime FastTrack language -> SlowTrack,
    unless ready prefetch exists, in which case FastTrack is bypassed.
  - Confirm latency CSV rows include current factor labels.
- Do not touch:
  - `AI_NPC_System/VoiceSample/`
  - voice sample reports and voice candidate experiments
  - TTS 음색/voice-pack 선택 작업

## 2026-05-26 17:45 KST - Voice/TTS Split

- Owner/chat: voice/TTS
- User request:
  - 목소리 관련 작업은 다른 채팅으로 분리.
- Done:
  - framework/runtime 채팅에서는 음색 샘플 선택, VoiceSample 처리, TTS 후보
    비교를 중단하기로 결정.
- Verification:
  - 없음. 범위 분리 결정만 기록.
- Files touched:
  - none for voice work in framework chat.
- Next handoff:
  - voice/TTS 채팅은 사용할 음성 후보, 샘플 생성, 레이턴시 비교, 실제 voice
    config 변경 제안을 별도 로그 항목으로 남긴다.
- Do not touch:
  - framework/runtime 작업 중에는 VoiceSample과 음색 실험 파일을 수정하지 않는다.

## 2026-05-26 21:50 KST - 2-Factor FastTrack Experiment UI

- Owner/chat: framework/runtime
- User request:
  - 실험 요인을 `Contextual Mapping`과 `Scheduling Architecture` 두 축으로 정리.
  - 웹 UI에서 클릭으로 바로 전환 가능하게 수정.
  - 페르소나 접미사 `peko` 강제 규칙은 제거하고, 자연스러운 말투 규칙은 추후 재정의.
- Decision:
  - 현재 연구 설계는 4 x 2 구조로 고정한다.
  - Factor 1 `Contextual Mapping`:
    `Grounded`, `Emotion only`, `Intent only`, `No FastTrack`.
  - Factor 2 `Scheduling Architecture`:
    `Parallel`, `Serial`.
  - 이전의 동적 A/B/C 조합 요인은 현 단계에서 제외한다.
- Done:
  - CREDO overlay UI에 위 4 x 2 실험 버튼 반영.
  - `/credo/experiment-mode`와 UI payload를 새 factor 값에 맞춤.
  - runtime agent에서 지원 정책을 `grounded`, `emotion_only`,
    `response_act_only`, `none`으로 정리.
  - `random` selection policy는 더 이상 허용하지 않음.
  - 페르소나/SlowTrack/Open-LLM prompt에서 `peko` 강제 요구 제거.
  - manifest builder의 접미사 추가 함수명을 일반 punctuation 처리로 변경.
  - legacy manifest에 남은 `peko` 토큰은 runtime display/TTS 직전
    `_clean_spoken_text()`에서 제거.
  - source integration과 vendored Open-LLM-VTuber runtime copy 모두 갱신.
- Verification:
  - API accepted:
    `both + grounded + parallel`.
  - API accepted:
    `both + emotion_only + parallel`.
  - API accepted:
    `both + response_act_only + serial`.
  - API accepted:
    `none + grounded + serial`.
  - API rejected:
    `selection_policy=random` -> HTTP `404`, `unknown selection policy`.
  - Runtime readiness:
    `READY`.
  - Interjection Fish audio bundle:
    `65/65` prebuilt audio present.
  - FastTrack persona text pool:
    `600/600` usable text, `legacy_audio=0/600`.
  - Current reset state after smoke:
    `component_mode=both`, `selection_policy=grounded`,
    `scheduling_mode=parallel`.
  - Source prompt scan:
    no forced `peko`/`Feco` prompt remains in active runtime config; only a
    legacy cleanup regex remains in the manifest builder.
- Notes:
  - FastTrack nonverbal interjection + face/motion elements remain active in
    all non-control conditions.
  - `No FastTrack` is the only condition that skips FastTrack analysis, text,
    audio, and motion.

## 2026-05-26 22:45 KST - Paper Draft And Cleanup

- Owner/chat: framework/runtime
- User request:
  - 실험 결과를 제외한 논문 초안 작성.
  - 루트부터 불필요 파일과 자료를 정리하고 폴더 구조를 정돈.
- Done:
  - Added paper draft:
    `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`.
  - Updated active setup/runtime docs to StyleBERT-VITS2
    `credo_voice_sample_en`, then-current 24-cell text manifest, prebuilt Fish nonverbal
    bundle, and 2-factor UI.
  - Moved old Lera Mei persona profile into archive:
    `AI_NPC_System/archive/legacy_docs/lera_mei_persona.md`.
  - Moved obsolete Professor Jinsama callout builder into archive:
    `AI_NPC_System/archive/legacy_scripts/build_professor_jinsama_call_bundle.py`.
  - Removed regenerated/transient artifacts:
    `AI_NPC_System/tts_outputs/`,
    `AI_NPC_System/reports/manifest_six_case_tts_test_2026-05-26/`,
    root `output/`, runtime logs/pids/state, and Python `__pycache__`.
  - Updated FastTrack asset index generator and regenerated
    `AI_NPC_System/fasttrack_assets/INDEX.generated.json`.
- Retained:
  - `AI_NPC_System/VoiceSample/`
  - `AI_NPC_System/fasttrack_assets/text/pekora_reaction_bundle_v1/manifest.json`
  - `AI_NPC_System/fasttrack_assets/text/persona_reaction_bundle_response_act_v1/manifest.json`
  - `AI_NPC_System/fasttrack_assets/audio/expressive_interjection_bundle/`
  - `AI_NPC_System/reports/stylebert_vits2_voice_sample_finetune_2026-05-26/`
  - `vendor/Style-Bert-VITS2`, `vendor/open-llm-vtuber`, `vendor/fish-speech`
- Notes:
  - No experimental results were added to the paper draft.
  - Deleted TTS output files were runtime/generated artifacts; source data,
    active manifests, active nonverbal wav files, and final StyleBERT report
    were preserved.

## 2026-05-27 KST - Startup Warmup For Cold Path

- Owner/chat: framework/runtime
- User request:
  - 첫 시작 때 cold 상태를 워밍업으로 제거한 뒤 live turn에 들어가게 만들기.
- Done:
  - `run_credo_stack.py`에 기본-on startup warmup 추가.
  - StyleBERT health 통과 후 실제 `/voice` 요청 1회 수행.
  - LLM health 통과 후 실제 `/v1/chat/completions` 요청 1회 수행.
  - Open-LLM-VTuber 기동 후 CREDO status route 1회 호출.
  - stack runner가 child service를 재시작할 때도 같은 warmup을 다시 실행.
  - `--no-warmup`과 `--warmup-timeout` 옵션 추가.
  - docs updated:
    `README.md`, `CODEX_SETUP.md`,
    `AI_NPC_System/README.md`,
    `AI_NPC_System/docs/runtime_stack_stability.md`,
    `AI_NPC_System/docs/credo_live_usage_guide.md`.
- Usage:
  - Normal live run:
    `AI_NPC_System/scripts/run_credo_stack.sh --profile live`.
  - Debug startup without warmup:
    `AI_NPC_System/scripts/run_credo_stack.sh --profile live --no-warmup`.

## 2026-05-27 KST - FastTrack Question Response Removal

- Owner/chat: framework/runtime
- User request:
  - FastTrack manifest and response-act mapping must not output questions.
  - If `QUESTION` would be the top SWDA response-act transition, select the
    next allowed response act instead.
- Done:
  - Rebuilt active manifest as no-question text pool:
    `AI_NPC_System/fasttrack_assets/text/pekora_reaction_bundle_v1/manifest.json`.
  - New manifest version:
    `credo-pekora-reaction-bundle-v1-no-question`.
  - Active count:
    `20` cells, `500` items.
  - Active response acts:
    `INFORM`, `ACKNOWLEDGE`, `DIRECTIVE`, `EXPRESSIVE`, `REJECT`.
  - Removed all `QUESTION` response-act items and all `?` / direct question-like
    FastTrack text from the active manifest.
  - `IntentTransitionPlanner` now removes `QUESTION` before normalizing
    transition probabilities.
  - `PersonaReactionBundle`, router v3, and Open-LLM-VTuber CREDO agent now
    normalize any accidental `QUESTION` response act to a safe non-question
    route.
- Verification:
  - Manifest validation:
    `OK`, `20` cells, `500` items, `0` warnings.
  - Manifest scan:
    `question_act_items=0`, strict question-like text hits `0`.
  - Transition forced test:
    matrix with `QUESTION=0.9`, `INFORM=0.1` always selected `INFORM`.

## 2026-05-27 KST - Separated Dataset Pool Runtime Routing

- Owner/chat: framework/runtime
- User correction:
  - A static 500/600-line persona `manifest.json` is not necessary for the
    active FastTrack language path.
  - The two original prepared text datasets must not be arbitrarily merged.
    Keep GoEmotions and SWDA separate, filter them, search them at runtime,
    and compose the short FastTrack utterance on demand.
- Done:
  - Added separated pool builder:
    `AI_NPC_System/scripts/build_fasttrack_dataset_pools.py`.
  - Active separated pool:
    `AI_NPC_System/fasttrack_assets/text/professor_lab_maid_dataset_pool_v1/pool.json`.
  - Pool keeps source roles separate:
    GoEmotions = emotion evidence, SWDA = response-act evidence.
  - Added validator:
    `AI_NPC_System/scripts/validate_fasttrack_dataset_pool.py`.
  - Router v3 now loads `FAST_TRACK_DATASET_POOL_PATH` and uses
    separated runtime retrieval/composition instead of a prewritten
    persona reaction manifest.
  - `FAST_TRACK_PERSONA_BUNDLE_ENABLED=0` in active config; old manifest path
    remains only as legacy compatibility/fallback.
  - Persona defaults changed from Pekora to `Professor's Lab Maid`.
  - Added persona profile:
    `AI_NPC_System/docs/professor_lab_maid_persona.md`.
- Current pool counts:
  - GoEmotions kept: `1131`
    (`POSITIVE=320`, `NEGATIVE=320`, `SURPRISE=171`, `NEUTRAL=320`)
  - SWDA kept: `1049`
    (`INFORM=320`, `ACKNOWLEDGE=158`, `DIRECTIVE=173`,
    `EXPRESSIVE=320`, `REJECT=78`)
  - SWDA `QUESTION` response-act pool is excluded.
- Verification:
  - Dataset pool validation: `OK`.
  - Router smoke across `grounded`, `emotion_only`, `response_act_only`,
    `neutral_random`: no `?`, no `peko`.
  - Runtime readiness: `READY`, required failures `0`, warnings `0`.

## 2026-05-27 KST - Paper Draft Methodology Update

- Owner/chat: framework/runtime
- Done:
  - Updated `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`
    to reflect the separated dataset-pool method.
  - Replaced static 500/600-line manifest descriptions with:
    GoEmotions emotion evidence pool + SWDA response-act evidence pool +
    runtime persona cover composition.
  - Added the academic rationale: separating source evidence from persona
    realization makes emotion grounding, dialogue-act grounding, and persona
    style easier to analyze independently.
  - Updated controlled variables and reproducibility notes to document
    dataset source separation, filter policy, runtime composition templates,
    and no-question response-act handling.

## 2026-05-27 KST - Documentation Cleanup

- Owner/chat: framework/runtime
- User request:
  - Remove unnecessary documents and keep only current-method documentation.
- Deleted obsolete active-doc/report files:
  - `AI_NPC_System/docs/usada_pekora_persona.md`
  - `AI_NPC_System/reports/current_status_2026-05-26.md`
  - `AI_NPC_System/reports/methodology_update_2026-05-26.md`
  - `AI_NPC_System/reports/runtime_smoke_latest.md`
  - `AI_NPC_System/reports/ana_pipeline_order_smoke_2026-05-26.json`
  - `AI_NPC_System/reports/six_factor_cases_status_2026-05-26/report.md`
  - `AI_NPC_System/reports/project_cleanup_audit.md`
- Updated surviving docs to the current method:
  - active language source = separated GoEmotions/SWDA dataset pool
  - active persona = Professor's Lab Maid
  - active TTS/interjection live assets = StyleBERT
  - static Pekora/persona manifests = not current runtime guidance

## 2026-05-27 KST - Final Runtime Cleanup Before Commit

- Owner/chat: framework/runtime
- Cleanup:
  - Removed stale untracked static text manifest folders under
    `AI_NPC_System/fasttrack_assets/text/`; only
    `professor_lab_maid_dataset_pool_v1/pool.json` remains there.
  - Moved legacy static persona-manifest builders to
    `AI_NPC_System/archive/legacy_scripts/`.
  - Removed old local generated TTS cache files and Python `__pycache__`
    directories from the workspace.
  - Renamed latest validation report from persona-bundle wording to
    `AI_NPC_System/reports/fasttrack_dataset_pool_validation_latest.*`.
  - Updated usage/setup docs, asset index, frontend scenario text, and
    integration patcher wording to match Professor's Lab Maid + StyleBERT +
    separated dataset-pool runtime.
- Verification:
  - `validate_fasttrack_dataset_pool.py`: OK
    (`go_emotions=1131`, `swda=1049`).
  - `check_runtime_readiness.py`: READY.
  - Python compile check passed for active runtime/scripts.
  - Node syntax check passed for source and vendored
    `credo-vtuber-mode.js`.
  - Interjection manifest: `65` items, missing audio `0`,
    engine `stylebert_vits2`.

## 2026-05-27 KST - Live2D Motion Blending Diagnosis

- Owner/chat: motion/runtime
- User question:
  - Lip-sync moves during speech, but adding another expression/motion causes only one motion to appear instead of both blending.
- Findings:
  - `credo_avatar.model3.json` has a `LipSync` group, but its `Ids` array is empty.
  - CREDO frontend currently drives mouth opening directly from audio volume via `ParamMouthOpenY`.
  - Speech tags map to `PositiveTalk`, `NegativeTalk`, `AmbiguousTalk`, and `NeutralTalk`.
  - The `*_talk.motion3.json` files do not key `ParamMouthOpenY`/`ParamMouthForm`, so they are speech-safe.
  - Non-talk expression/body motions such as `positive_1.motion3.json`,
    `negative_1(sigh).motion3.json`, and `ambiguous_1.motion3.json` still key
    `ParamMouthOpenY` and/or `ParamMouthForm`.
  - The frontend calls `adapter.startMotion(...)` for speech, style, event, and fast motions. If the Cubism runtime uses a single motion manager, a later event/expression motion can interrupt the active speech motion instead of layering with it.
- Practical next fix:
  - Keep audio lip-sync as parameter-driven mouth movement.
  - Use talk/body motions that do not touch mouth parameters during speech.
  - Do not fire non-talk expression motions during speech unless their mouth curves are stripped.
  - For true blending, split runtime control into layers: mouth lip-sync parameters, face expression overlay, body gesture motion, and idle/body pulse.

## 2026-05-27 KST - Live2D Mouth-Safe Motion Layering Implemented

- Owner/chat: motion/runtime
- User request:
  - Make lip-sync continue matching speech while other expressions/body motions can be applied.
- Implemented:
  - Updated CREDO frontend motion hook in both copies:
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - Added parameter-only event accents for `laugh`, `surprise`, `thinking`, and `sigh`.
    These accents affect eyes, brows, cheek, head/body angles, and breath, but never
    `ParamMouthOpenY` or `ParamMouthForm`.
  - During speech audio, event tags now use the parameter accent layer instead of
    starting another Cubism motion that can interrupt the active speech/body motion.
  - Kept audio-volume lip-sync as the sole owner of mouth opening.
  - Removed mouth curves from all CREDO motion3 files in both active model copies:
    `ParamMouthOpenY` and `ParamMouthForm` are no longer keyed by any checked motion.
- Verification:
  - Windows Node parse check passed for both frontend hook files.
  - Checked `46` CREDO `*.motion3.json` files across both model copies:
    mouth curve errors `0`, `CurveCount` metadata errors `0`.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned `READY`.
- Notes:
  - This preserves the current volume-based lip-sync. It is not phoneme/viseme-level
    mouth shaping yet, but it prevents expression/body motion from stealing mouth control.

## 2026-05-27 KST - FastTrack Nonverbal Interjections Removed From Active Runtime

- Owner/chat: motion/runtime
- User request:
  - Remove nonverbal expression clips from FastTrack.
  - Keep lip-sync active.
  - Let the avatar expression/body tone follow the detected emotion of the viewer
    utterance throughout the answer.
  - Update the paper draft and this shared worklog.
- Implemented:
  - Added `CREDO_NONVERBAL_FASTTRACK_ENABLED=0` to the active config.
  - Disabled active initial interjection audio, waiting cover audio, thinking bridge
    audio, and extra cover audio defaults:
    `CREDO_ENABLE_INITIAL_INTERJECTION_AUDIO=0`,
    `CREDO_ENABLE_WAITING_COVER_AUDIO=0`,
    `CREDO_ENABLE_THINKING_BRIDGE_AUDIO=0`,
    `CREDO_ENABLE_EXTRA_COVER_AUDIO=0`.
  - Updated both CREDO agent copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
    - `vendor/open-llm-vtuber/src/open_llm_vtuber/agent/agents/credo_latency_cover_agent.py`
  - `_nonverbal_fasttrack_enabled()` now requires explicit opt-in and defaults off.
  - `_speech_actions()` now keeps one viewer-emotion speech motion layer for the
    whole answer instead of adding event motions from spoken filler words.
  - Added `emotion_motion_payload` latency events with `mouth_owner=audio_lipsync`
    and the emitted Live2D action list.
  - Updated runtime readiness so the interjection bundle is `SKIP` when
    nonverbal FastTrack is disabled.
  - Updated paper draft:
    `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`.
- Verification:
  - `python3 -m py_compile` passed for agent/config/readiness files.
  - The integration and vendor agent copies are byte-identical after the change.
  - Config import reports all nonverbal FastTrack toggles as `False` and
    `CREDO_SPEECH_EMOTION_MOTION_ENABLED=True`.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned `READY`;
    `Interjection audio bundle` is now reported as `SKIP`.
- Notes:
  - The prebuilt interjection asset files were not deleted; they are no longer
    required for the active live path and remain archived only.
  - FastTrack still provides the short language reaction. The expression layer now
    follows the analyzed viewer emotion while mouth movement remains audio-driven.

## 2026-05-27 KST - Manual Interjection Playback Sealed

- Owner/chat: motion/runtime
- User correction:
  - Interjections were still reachable through the manual playback feature.
  - Seal interjection playback for now.
- Implemented:
  - Removed the `Reactions` button, manual interjection panel, startup reaction
    loading, and `/credo/interjections` frontend fetch from both CREDO frontend
    hook copies:
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
  - Locked backend manual playback in
    `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`:
    - `GET /credo/interjections` returns an empty disabled list.
    - `POST /credo/interjections/play` returns `423` with `played=false`.
    - Removed the interjection manifest loader and audio payload send path from
      the active route file.
  - Hardened both CREDO agent copies:
    - `_nonverbal_fasttrack_enabled()` now returns `False` unconditionally.
    - Initial interjection generation calls were removed from the turn path.
    - `_build_initial_interjection_outputs()` returns `[]`.
    - `_yield_waiting_cover_audio()` exits immediately.
  - Updated config comments to reflect that standalone interjection playback is
    sealed, not merely disabled by default.
- Active behavior:
  - FastTrack language reactions still work for the six experiment cases.
  - Standalone gasp/laugh/hm/sigh-style audio clips are not emitted by FastTrack,
    waiting cover, initial cover, manual UI, or manual backend playback.
  - Viewer-emotion expression/body motion remains active while mouth movement is
    still owned by audio lip-sync.
- Verification:
  - Windows Node parse check passed for both frontend hook files.
  - `python3 -m py_compile` passed for both agent copies, `routes.py`, config,
    and runtime readiness script.
  - Frontend hook copies are byte-identical; agent copies are byte-identical.
  - Search check found no active frontend `Reactions`, `Manual interjection`,
    `play-interjection`, `toggle-interjections`, reaction load/fetch, or agent
    `fast_track_interjection` send path.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned `READY`.

## 2026-05-27 KST - Viewer Address Suffix Persona Rule

- Owner/chat: persona/runtime
- User request:
  - Add a speech-style rule for LLM-generated viewer-facing lines.
  - Initial idea was to place `kyo-shu-zin- sama` at the front, then corrected to
    place it at the end.
- Implemented:
  - Added `CREDO_VIEWER_ADDRESS_SUFFIX="kyo-shu-zin- sama"` to active config.
  - Updated persona, SlowTrack, VTuber stream, Open-LLM-VTuber character, and
    scenario direction prompts to require generated viewer-facing speech to end
    with exactly `kyo-shu-zin- sama`.
  - Added deterministic runtime post-processing in both CREDO agent copies:
    - `_ensure_viewer_address_suffix()` appends the suffix before final
      punctuation if the LLM omits it.
    - If stale prompt output puts the phrase at the front, the helper strips it
      and re-appends it at the end.
  - Applied the suffix guard to VTuber SlowTrack, proactive monologue, prefetch,
    and SlowTrack-only output paths.
- Active behavior:
  - LLM-generated main speech now ends like:
    `The clipboard is already shaking, kyo-shu-zin- sama.`
  - FastTrack fixed reaction text is unchanged unless it goes through a SlowTrack
    generated path; this keeps the six experiment cases' FastTrack comparison
    surface stable.
- Verification:
  - Windows Node parse check passed for both frontend hook files.
  - `python3 -m py_compile` passed for config and both agent copies.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - YAML parse check passed for the character YAML and vendored `conf.yaml`.
  - Runtime config import reports suffix `kyo-shu-zin- sama`.
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned `READY`.

## 2026-05-27 KST - Usage Documentation Updated

- Owner/chat: docs/runtime
- User request:
  - Update usage instructions and provide the current operator-facing usage.
- Updated:
  - `AI_NPC_System/docs/credo_live_usage_guide.md`
    - Current status now states standalone interjection playback is sealed.
    - Browser panel instructions no longer mention a usable `Reactions` button.
    - Added the active persona speech rule: generated main speech ends with
      `kyo-shu-zin- sama`.
    - Manual Reactions section now documents the sealed API/UI behavior.
  - `README.md` and `AI_NPC_System/README.md`
    - Replaced active interjection claims with archived/sealed wording.
    - Added the `CREDO_VIEWER_ADDRESS_SUFFIX` operator setting.
  - Supporting docs updated for consistency:
    - `AI_NPC_System/docs/open_llm_vtuber_runtime_flow.md`
    - `AI_NPC_System/docs/runtime_stack_stability.md`
    - `AI_NPC_System/docs/user_study_protocol.md`
    - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
    - `AI_NPC_System/docs/tts_engine_routing.md`
    - `AI_NPC_System/docs/fish_speech_integration.md`
- Current operator summary:
  - Start with `AI_NPC_System/scripts/run_credo_stack.sh --profile live`.
  - Open `http://127.0.0.1:12393`.
  - Select one of six `Experiment cases`, then click `Start Scenario`.
  - Do not use standalone interjection playback; it is sealed.
  - SlowTrack/proactive generated speech should end with `kyo-shu-zin- sama`.

## 2026-05-27 07:10 KST - Live2D Expression Hold Extended

- Owner/chat: frontend/motion
- User request:
  - Face expressions felt too short.
  - Keep expressions usable for roughly 10 seconds.
- Implemented:
  - Updated both frontend hook copies through the integration source and vendor
    activation:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Added a 10 second `EXPRESSION_HOLD_MS` path for event facial accents.
  - Replaced the old short sine envelope with attack/hold/release timing so the
    expression reaches quickly, stays visible, then fades out near the end.
  - Added event accent cancellation tokens so a new expression overrides the
    previous 10 second expression instead of stacking conflicting face
    parameters.
  - Extended the related Live2D motion idle-return duration to at least the same
    expression window while keeping mouth movement tied to the actual TTS audio
    duration.
- Verification:
  - `python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate`
    copied the frontend hook into the active Open-LLM-VTuber vendor frontend.
  - Windows Node parse check passed for both frontend hook files.
  - Source and vendor frontend hook files are byte-identical.
  - `git diff --check` passed for the edited frontend hook files.
  - The running static server at `http://127.0.0.1:12393/credo-vtuber-mode.js`
    is serving the new `EXPRESSION_HOLD_MS = 10000` frontend code.
- Notes:
  - This is a browser-side frontend change. A hard refresh of the Open-LLM-VTuber
    page is enough to pick it up; Python backend restart is not required for this
    specific expression-duration change.

## 2026-05-27 14:31 KST - Scenario Viewer Pool Fixed To Ten Recurring Chatters

- Owner/chat: frontend/scenario automation
- User request:
  - The virtual broadcast chat should not look like every message comes from a
    brand-new viewer.
  - Treat the stream as a room of about 10 viewers.
  - Make those same 10 viewers repeatedly chat during the scenario.
- Implemented:
  - Updated the shared 150-second scenario in:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Fixed the recurring viewer pool to exactly 10 English handles:
    `CtrlAltDefeat`, `CoffeeCalibrator`, `NullPointerNina`,
    `PipettePanic`, `DeadlineDodger`, `OverfitOwen`, `StackTraceSam`,
    `BackupBard`, `KernelPanicKim`, and `ReviewerTwo`.
  - Replaced one-off chat handles such as `LabSlave99`, `PuddingThief`,
    `SleepCoder`, and other single-use names with repeated messages from the
    same 10-viewer pool.
  - Kept donations inside the same viewer pool:
    - `StackTraceSam` sends the rm-rf server disaster donation.
    - `PipettePanic` sends the capsaicin pudding donation.
    - `CoffeeCalibrator` sends the delusional professor-code donation.
  - Updated the scenario direction prompt so the LLM understands this is a
    fixed small room of 10 recurring viewers.
- Verification:
  - `python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate`
    copied the scenario changes into the active Open-LLM-VTuber vendor frontend.
  - Windows Node parse check passed for both frontend hook files.
  - Source and vendor frontend hook files are byte-identical.
  - `git diff --check` passed for the edited frontend hook files.
  - Static timeline audit reports:
    - 36 total timeline events.
    - 33 chat events.
    - 3 donation events.
    - Exactly 10 unique viewers.
    - All 10 viewers appear in normal chat, not only donation.
    - Each viewer appears 3 to 4 times.
  - Hangul search found no Korean text in the frontend hook files.
  - The running static server at `http://127.0.0.1:12393/credo-vtuber-mode.js`
    is serving the updated 10-viewer scenario code.

## 2026-05-27 15:12 KST - VTuber Longer Answers And 20-Second Post-Donation Chat Window

- Owner/chat: backend VTuber runtime / frontend scenario support
- User request:
  - VTuber generated speech should not be too short.
  - LLM-generated spoken sentences must not contain filler sentences.
  - Donation counseling must take priority.
  - After the donation answer finishes, the VTuber should answer while looking
    at recent chat.
  - Recent chat should be gathered from the last 20 seconds.
- Implemented:
  - Updated active CREDO config defaults:
    - `CREDO_VTUBER_CHAT_BATCH_MAX_ITEMS=10`
    - `CREDO_VTUBER_CHAT_BATCH_WINDOW_SECONDS=20`
    - `CREDO_VTUBER_LLM_MAX_TOKENS=144`
    - `CREDO_VTUBER_MIN_SPOKEN_WORDS=32`
    - `CREDO_VTUBER_MAX_SPOKEN_WORDS=70`
  - Updated `CREDO_VTUBER_SYSTEM_PROMPT` to require longer concrete spoken
    segments and prohibit filler openings / filler-only sentences such as
    `well`, `okay`, `alright`, `anyway`, `um`, `uh`, and `hmm`.
  - Updated the CREDO Open-LLM-VTuber agent source and active vendor copy:
    - Adds filler sentence stripping before TTS.
    - Enforces min/max spoken-word rules in VTuber prompt construction.
    - Appends a concrete event-specific sentence if the LLM returns an unusably
      short VTuber line.
    - Keeps donation turns from answering unrelated chat directly.
    - Keeps `live_chat_batch` and `donation` excluded from SlowTrack prefetch
      reuse so these turns always use the newest context.
  - Updated active Open-LLM-VTuber routes:
    - Idle loop now consumes buffered VTuber chat with
      `since_seconds=20.0`.
    - Chat batch prompt explicitly describes the most recent 20-second chat
      window after priority donation or stream speech.
    - Donation prompt says to answer donation first, then let the next chat
      batch summarize the most recent 20 seconds of surrounding chat.
  - Updated active websocket handler:
    - VTuber chat buffer now stores monotonic timestamps per chat message.
    - `consume_vtuber_chat_context()` supports `since_seconds`.
    - Stale chat outside the selected window is dropped instead of being reused.
  - Updated `apply_integration.py` so future activation keeps the new longer
    answer rules and timestamped 20-second chat buffer behavior.
- Verification:
  - `python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate`
    completed successfully.
  - `python3 -m py_compile` passed for:
    - `AI_NPC_System/config.py`
    - `AI_NPC_System/slow_track.py`
    - CREDO agent source and active vendor copy
    - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
    - active vendor `routes.py`
    - active vendor `websocket_handler.py`
  - CREDO agent source and vendor copy are byte-identical.
  - Config import reports:
    - `batch_max_items=10`
    - `batch_window=20.0`
    - `llm_max_tokens=144`
    - `min_words=32`
    - `max_words=70`
  - `python3 AI_NPC_System/scripts/check_runtime_readiness.py` returned
    `READY`.
  - `git diff --check` passed for the edited source/config/runtime files.
- Notes:
  - This change touches Python backend runtime files. Restart the
    Open-LLM-VTuber server to load the new route, websocket buffer, and agent
    behavior. Browser hard refresh alone is not enough for this change.

## 2026-05-27 15:33 KST - Idle_Motion Registered And Kept Running Before Speech

- Owner/chat: frontend/Live2D motion
- User request:
  - A new `Idle_Motion.motion3` motion was added.
  - The avatar should keep using this idle motion before speaking.
- Implemented:
  - Updated `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
    so the CREDO Live2D `Idle` motion group is now:
    `motions/Idle_Motion.motion3.json`.
  - Ran integration activation so both source and active vendor model files now
    register the new idle motion:
    - `AI_NPC_System/integrations/open_llm_vtuber/live2d_models/credo_avatar/credo_avatar.model3.json`
    - `vendor/open-llm-vtuber/live2d-models/credo_avatar/credo_avatar.model3.json`
  - Confirmed `Idle_Motion.motion3.json` is copied into both Live2D model
    `motions/` directories.
  - Updated `credo-vtuber-mode.js` so the browser starts the idle motion shortly
    after load and keeps restarting it while TTS/lip-sync is not active.
  - After speech or expressive talk motions, idle return now schedules the
    dedicated idle loop instead of a one-shot random `Idle` call.
- Verification:
  - `python3 AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py --activate`
    completed successfully.
  - Windows Node parse check passed for both frontend hook files.
  - `python3 -m py_compile` passed for `apply_integration.py`.
  - Source and vendor frontend hook files are byte-identical.
  - Source and vendor `credo_avatar.model3.json` files are byte-identical.
  - JSON audit confirms `Idle` is exactly
    `[{ "File": "motions/Idle_Motion.motion3.json" }]`.
  - Motion audit confirms `Idle_Motion.motion3.json` has
    `Duration=9.633` and `Loop=true`.
  - Running static server confirms:
    - `/credo-vtuber-mode.js` contains the idle loop code.
    - `/live2d-models/credo_avatar/credo_avatar.model3.json` references
      `Idle_Motion.motion3.json`.
    - `/live2d-models/credo_avatar/motions/Idle_Motion.motion3.json`
      returns HTTP 200.
  - `git diff --check` passed for the edited frontend/model/integration files.
- Notes:
  - This is a frontend/model asset behavior change. The running server is
    already serving the updated static files, but the browser page should be
    hard-refreshed so the Live2D model JSON and frontend hook reload together.

## 2026-05-27 16:50 KST - Removed Virtual Chat Placeholder Message

- Owner/chat: frontend/virtual chat UI
- User request:
  - Remove the default `viewer Say something to test FastTrack.` placeholder.
- Implemented:
  - Removed the initial placeholder chat row from both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - The virtual chat list now starts empty and only shows real manual or
    scenario-injected virtual chat messages.
- Verification:
  - Search confirms `Say something to test FastTrack.` no longer appears in
    either frontend hook file.
  - Windows Node parse check passed for both frontend hook files.
  - Source and vendor frontend hook files are byte-identical.

## 2026-05-27 20:23 KST - Enlarged Virtual Chat Dock And Per-Viewer Colors

- Owner/chat: frontend/virtual broadcast chat UI
- User request:
  - Make the virtual chat window larger.
  - Give each viewer nickname a different color.
- Implemented:
  - Updated both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Increased the right-side virtual chat dock from `340px x 620px` to
    `430px x 760px`, with responsive viewport caps.
  - Increased chat dock text size and spacing for better OBS readability.
  - Added a deterministic 10-color nickname palette. The same author string
    always maps to the same color during manual chat, scenario chat, and
    donation chat rows.
  - Increased retained visible chat rows from 24 to 48.
- Verification:
  - Source and vendor frontend hook files are byte-identical.
  - `git diff --check` passed for both frontend hook files.
  - Node syntax check could not be run in this shell because `node` is not
    available in WSL or the current Windows PowerShell PATH.

## 2026-05-27 20:32 KST - Donation Overlay Repositioned To B-1

- Owner/chat: frontend/OBS overlay layout
- User request:
  - Make the donation overlay larger.
  - Move the donation overlay left into the B-1 position of a 4x4 screen grid.
  - Move the upper-left Connected status button.
- Implemented:
  - Updated both CREDO frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Moved the donation overlay from top-center to a B-1 anchored position:
    `left: calc(25vw + 18px)`, `top: 36px`.
  - Enlarged the donation overlay to `min(720px, calc(50vw - 36px))`, added
    minimum height, larger padding, and larger donation title/amount/author text.
  - Added a small-screen fallback so the donation overlay uses left/right margins
    instead of overflowing below 900px viewport width.
  - Moved the CREDO control panel down from `top: 18px` to `top: 132px` so the
    upper-left screen space is less crowded during recording.
  - Updated the active Open-LLM-VTuber built frontend bundle so the WebSocket
    `Connected` status chip moves from `top: 20px; left: 20px` to
    `top: 84px; left: 24px`.
- Verification:
  - Source and vendor CREDO frontend hook files are byte-identical.
  - `git diff --check` passed for the edited frontend hook files and active
    frontend bundle.
  - Static bundle audit confirms the new `top:"84px",left:"24px"` Connected
    status position is present and the old `top:"20px",left:"20px"` position is gone.
- Notes:
  - The active built bundle is under `vendor/open-llm-vtuber/frontend/assets/` and
    is not shown by `git status`, but the local runtime file was updated.
  - Hard-refresh the browser after restarting or reloading the Open-LLM-VTuber page.

## 2026-05-27 22:46 KST - Prevented Overlapping VTuber Audio Playback

- Owner/chat: Open-LLM-VTuber frontend audio manager and CREDO donation priority route
- User report:
  - Multiple TTS/audio clips can play at the same time, especially around priority
    donation responses.
- Root cause found:
  - The browser-side `AudioManager.setCurrentAudio(...)` replaced the tracked audio
    object without stopping the previous audio element first.
  - The donation priority route cancelled the active backend conversation task, but
    did not also clear audio already queued or playing in the browser client.
- Implemented:
  - Updated the active built frontend bundle:
    - `vendor/open-llm-vtuber/frontend/assets/main-nu7uwxNJ.js`
  - `AudioManager.setCurrentAudio(...)` now stops the currently tracked audio and
    lip-sync before registering a different new audio element.
  - Updated the active backend route:
    - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - Donation priority handling now sends an `interrupt-signal` to the connected
    browser client before cancelling the active VTuber task and answering the
    donation.
  - Updated the integration patcher so future `--activate` runs preserve the
    donation priority frontend queue clear:
    - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py`
- Verification:
  - Python compile check passed for `apply_integration.py` and active `routes.py`.
  - Static bundle audit confirms the guarded `setCurrentAudio(...)` exists and the
    old unguarded setter is gone.
  - Route and integration audits confirm the donation priority `interrupt-signal`
    logic exists in both places.
  - `git diff --check` passed for the edited Python files and shared worklog.
- Notes:
  - Restart the Open-LLM-VTuber backend and hard-refresh the browser page before
    testing this fix, because both the backend route and built frontend bundle were
    changed.

## 2026-05-27 22:51 KST - Enlarged Virtual Chat Dock Again

- Owner/chat: frontend/virtual broadcast chat UI
- User request:
  - Make the virtual chat window even larger.
- Implemented:
  - Updated both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Increased the virtual chat dock from `430px x 760px` to `560px x 860px`, still capped by viewport size.
  - Increased chat dock base text from `14px` to `15px`, with larger title/list padding and row spacing.
  - Increased retained chat rows from 48 to 64 so the taller dock stays populated during active scenario playback.
- Verification:
  - Source and vendor frontend hook files are byte-identical.
  - Static search confirms the new dock size and retained row count are present in both hook files.

## 2026-05-27 23:16 KST - Moved Connected Status Chip Near Left Toggle UI

- Owner/chat: Open-LLM-VTuber built frontend status overlay
- User request:
  - Move the green `Connected` WebSocket status chip to the left toggle UI position.
- Implemented:
  - Updated the active built frontend bundle:
    - `vendor/open-llm-vtuber/frontend/assets/main-nu7uwxNJ.js`
  - Changed the WebSocket status chip from an absolute main-content overlay at
    `top: 84px; left: 24px` to a viewport-fixed position near the CREDO left
    toggle area: `top: 132px; left: 64px`.
  - Set the chip z-index to `9998`, below the CREDO control panel (`9999`), so it
    does not cover the panel when the panel is open.
- Verification:
  - Static bundle audit confirms the old status position is gone and the new fixed
    status position is present.
- Notes:
  - The active built bundle is under `vendor/open-llm-vtuber/frontend/assets/` and
    may not appear in `git status`. Hard-refresh the browser page to load the new
    bundle position.

## 2026-05-27 23:43 KST - Fixed Scenario Stop/Reset And Recovered StyleBERT Startup

- Owner/chat: virtual broadcast scenario controls, Open-LLM-VTuber stop route, local runtime stack
- User reports:
  - `Stop Scenario` did not actually stop the running scenario/audio.
  - A subsequent `run_credo_stack.sh --profile live` failed during StyleBERT warmup with HTTP 500.
- Findings:
  - The old `Stop Scenario` only cleared frontend `setTimeout` timers. It did not stop the active backend conversation task, queued browser audio, donation overlay/SFX, or buffered virtual chat context.
  - The stack failure was not caused by the Stop/Reset frontend edits. StyleBERT was already in a bad CUDA inference state: `/docs` still looked healthy, but `/voice` failed with `RuntimeError: CUDA error: an illegal memory access was encountered`.
  - The stale Open-LLM process was also still generating idle/scenario TTS traffic, which kept hitting StyleBERT while we were trying to recover the stack.
- Implemented:
  - Added a `Reset` button next to `Start Scenario` / `Stop Scenario` in both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - `Stop Scenario` now:
    - clears all scenario timers,
    - hides donation overlay,
    - stops donation SFX playback,
    - sends a WebSocket `interrupt-signal`,
    - calls `/credo/vtuber-mode/stop`,
    - switches the UI back to direct chat mode.
  - `Reset` now performs the same stop sequence and additionally clears the virtual chat dock and resets scenario selection content.
  - Updated active backend route:
    - `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`
  - `/credo/vtuber-mode/stop` now sends an `interrupt-signal` to the connected browser, cancels the active conversation task, clears buffered virtual chat context, and cancels VTuber SlowTrack prefetch tasks.
  - Updated `apply_integration.py` so future `--activate` runs preserve the backend stop cleanup.
  - Terminated the corrupted StyleBERT/Open-LLM processes, re-applied integration, and restarted the live stack cleanly.
- Verification:
  - `apply_integration.py` and active `routes.py` compile successfully.
  - Source/vendor frontend hook files are byte-identical.
  - Static search confirms `Reset`, `stopScenarioRuntime`, and backend stop cleanup are present after `--activate`.
  - `/credo/vtuber-mode/stop` returned HTTP 200 from the restarted Open-LLM server.
  - `run_credo_stack.sh --profile live --health-timeout 45` now passes StyleBERT warmup, LLM warmup, Open-LLM warmup, and enters monitor loop.
  - Observed the monitor for about 30 seconds after startup with no new unhealthy messages.
- Notes:
  - Browser must be hard-refreshed so the updated CREDO frontend hook and built bundle are loaded.
  - The initial StyleBERT 500 was a CUDA inference failure in the existing StyleBERT process, not a frontend UI error.
## 2026-05-28 - StyleBERT pacing update
- Slowed CREDO StyleBERT speech by changing `STYLEBERT_VITS2_LENGTH` from `0.95` to `1.18` (roughly 0.85x speed).
- Added `STYLEBERT_VITS2_SENTENCE_PAUSE_MS=220` and sentence-split WAV concatenation so multi-sentence TTS inserts physical silence instead of spoken pause tags.
- Applied integration to vendored Open-LLM-VTuber and smoke-tested a two-sentence sample: `AI_NPC_System/tts_outputs/stylebert_fast/pause_smoke_1779895750191.wav`, duration 4.472s.
## 2026-05-28 - Virtual Broadcast UI restyle
- Restyled CREDO Virtual Broadcast mode toward a soft livestream overlay format: left-side rounded chat bubbles, small decorative viewer badges, subtle pastel screen wash, and bottom-right donation lower-third.
- In Virtual Broadcast mode, the operator panel moves to the top-right with a softer pastel skin so it does not compete with the left chat column.
- Applied integration to vendored Open-LLM-VTuber and checked JS syntax for source/runtime copies.
- Playwright smoke opened `http://127.0.0.1:12393`, selected Virtual Broadcast, sent sample virtual chats/donation, and saved screenshot `output/playwright/virtual-broadcast-redesign.png`. Existing console errors were unrelated mic permission/model lookup warnings.

## 2026-05-28 - Donation readout/subtitle update and operator panel rollback
- Corrected scope after user feedback: removed the Virtual Broadcast-specific styling that changed the CREDO operator panel position/skin. The control panel stays in its original dark left-side style; only the broadcast chat dock and donation overlay remain styled.
- Added backgroundless large speech subtitles driven by Open-LLM-VTuber audio payload `display_text`; subtitles hold for audio/estimated duration and do not disappear mid-utterance.
- Slowed StyleBERT speech further by setting `STYLEBERT_VITS2_LENGTH=1.33` for roughly 0.75x pacing.
- Donation popup duration is now 15s. Donation flow is now: show popup -> interrupt current VTuber audio -> Edge TTS male donation readout (`en-US-GuyNeural`) -> queue donation answer.
- Added `/credo/vtuber-mode/donation-readout` to the active backend and `apply_integration.py` so future activation preserves it.
- Scenario timeline now has two donations, spaced at 44s and 116s.
- Verification: JS syntax checks passed for source/runtime frontend copies; Python compile passed for `apply_integration.py`, active `routes.py`, config, and TTS selector; `edge_tts` imports in the Open-LLM venv. Current running Open-LLM process still needs restart before the new backend route becomes live.

## 2026-05-28 - Experiment case logging hardening
- Confirmed agent-side latency rows already include `experiment_run_id`, `experiment_factor`, `scenario`, `component_mode`, `selection_policy`, and `scheduling_mode`.
- Extended `AI_NPC_System/latency_observer.py` so `module_events.csv` also includes `runtime_mode` and `event`, and `latest_summary.md` now surfaces run/mapping/scheduling columns for quick inspection.
- Added route-level runtime events to the same latency CSV/log stream: `experiment_case_set`, `experiment_mode_post`, `vtuber_mode_start`, `vtuber_mode_stop`, `virtual_chat_buffered`, `vtuber_turn_queued`, `vtuber_turn_deferred`, `vtuber_turn_blocked`, `donation_readout_tts`, and `donation_answer_queued`.
- Updated `apply_integration.py` so the route-level logging survives future `--activate` runs.
- Verification: `apply_integration.py --activate` passed; Python compile passed for `latency_observer.py`, `apply_integration.py`, and active `routes.py`; temp CSV smoke confirmed case/mapping/scheduling/runtime/event fields are written.
- Inspect during experiments with: `tail -f AI_NPC_System/latency_logs/module_events.csv` or read `AI_NPC_System/latency_logs/latest_summary.md`.

## 2026-05-28 02:33 KST - Server Shutdown Handoff Note

- Owner/chat: runtime stack handoff
- User request:
  - Shut down all currently running CREDO servers.
  - Summarize the state for cross-Codex handoff.
- Actions taken:
  - Inspected CREDO-related processes and ports before shutdown.
  - Found and terminated the running local services from the previous stack session:
    - vLLM local LLM on `127.0.0.1:8001`
    - StyleBERT-VITS2 on `0.0.0.0:5000`
    - Open-LLM-VTuber on `127.0.0.1:12393`
  - A new `run_server.py` process briefly appeared after the first shutdown pass and was also terminated before the user clarified that newly created work processes should not be killed.
- Current observed state at 2026-05-28 02:33 KST:
  - No matching CREDO runtime processes were found by the non-destructive process check.
  - No listeners were found on CREDO ports `12393`, `5000`, `8001`, `8080`, `5001`, or `7861`.
- Important handoff instruction:
  - The user clarified: if a new process appears because another task/Codex is working, do not shut it down now.
  - Future agents should only inspect runtime status unless the user explicitly asks again to terminate processes.
- Recent implemented feature state to preserve:
  - `Stop Scenario` now calls the real runtime stop path instead of only clearing frontend timers.
  - `Reset` was added and clears scenario timers, donation overlay/SFX state, and the virtual chat dock.
  - Backend `/credo/vtuber-mode/stop` now interrupts browser audio, cancels the active conversation task, clears buffered virtual chat context, and cancels VTuber SlowTrack prefetch tasks.
  - These changes are present in the source frontend hook, active vendor frontend hook, active vendor `routes.py`, and `apply_integration.py` so `--activate` preserves them.
- Verification already completed before shutdown:
  - `apply_integration.py` and active `routes.py` compiled successfully.
  - `git diff --check` passed for the edited frontend/backend/worklog files.
  - Before shutdown, the clean stack had passed StyleBERT warmup, LLM warmup, and Open-LLM warmup.

## 2026-05-28 03:25 KST - Runtime Voice/FastTrack Smoke Verification

- Restarted CREDO live stack after another chat had shut it down: StyleBERT-VITS2, local vLLM, and Open-LLM-VTuber are healthy.
- GPU split observed after restart: GPU0 ~4.5 GB for StyleBERT/TTS, GPU1 ~19.8 GB for vLLM.
- Removed forced spoken suffix behavior from active config/character/frontend scenario text; `kyo-shu-zin-sama` is no longer required or injected by default.
- Hardened FastTrack Router v3 filtering: blocks unstable echo phrases, profanity-like snippets, overly specific source-dataset nouns, and recently repeated FastTrack candidates while still using dataset candidates rather than arbitrary hardcoded fallback.
- Donation male EdgeTTS route verified live: `/credo/vtuber-mode/donation-readout` returned MP3, 33,984 bytes, about 716 ms.
- StyleBERT voice route verified live: generated WAV, 292,908 bytes, 3.32 s audio, about 465 ms.
- Six experiment-case API switches verified after restart; all returned `ok=true` and the runtime was left on `case_5_grounded_parallel` (`both` / `grounded` / `parallel`).
- Browser smoke connected to Open-LLM; status showed a non-null `connected_client`.
- Active VTuber mode smoke: `/credo/vtuber-mode/start` set `active=true`; monologue queued with `queued=true`; `speech_busy_seconds` counted down from ~18 s to 0.
- Runtime logs confirmed: FastTrack analysis, emotion-motion payload, StyleBERT FastTrack audio, SlowTrack LLM, StyleBERT SlowTrack TTS, sequential speech guard, prefetch generation, and FastTrack bypass from prefetched SlowTrack.
- After smoke test, VTuber active loop was stopped and the stack was left running in inactive standby with `case_5_grounded_parallel` selected.

## 2026-05-28 04:12 KST - Runtime Recheck After External Shutdown
- Reconfirmed StyleBERT-VITS2, local vLLM, and Open-LLM-VTuber runtime after another chat stopped services.
- Current service state: StyleBERT `5000` up, vLLM `8001` up, Open-LLM `12393` up; VTuber mode standby with `both / grounded / parallel` restored.
- GPU split observed: GPU0 used by StyleBERT/Open-LLM side (~5.1 GiB), GPU1 used by vLLM (~19.8 GiB).
- Donation readout endpoint returned audio/mpeg in 693.7 ms. StyleBERT cold request was 11.24 s, warm requests were 345.6 ms and 178.6 ms.
- Six experiment cases accepted through `/credo/experiment-mode`; each returned `ok=true` and updated one active agent.
- Tightened FastTrack Router v3 filtering against repeated filler/noisy dataset snippets; no arbitrary text fallback was added.

## 2026-05-28 04:35 KST - Explicit Runtime Shutdown Completed

- Owner/chat: runtime stack handoff
- User request:
  - Explicitly shut down the servers now.
- Processes found and terminated:
  - StyleBERT-VITS2 parent server on `0.0.0.0:5000`
  - StyleBERT pyopenjtalk worker on `127.0.1.1:7861`
  - vLLM local LLM on `127.0.0.1:8001`
  - Open-LLM-VTuber on `127.0.0.1:12393`
  - Detached launcher shell parents for local LLM and Open-LLM-VTuber
- Verification:
  - Follow-up process check found no matching CREDO runtime processes.
  - Follow-up port check found no listeners on `12393`, `5000`, `8001`, `8080`, `5001`, or `7861`.
- Handoff note:
  - This shutdown was explicitly requested by the user at this time, superseding the earlier caution not to kill newly spawned work processes.

## 2026-05-28 07:28 KST - Donation-Gated Counseling Scenario And Persona Topic Lock

- Owner/chat: framework/runtime + docs/report
- User request:
  - Donation text should enter the VTuber only after the donation TTS readout finishes.
  - Replace the generic scenario with a graduate-school counseling broadcast:
    first donation at ~3s, conflicted professor donation at ~60s with a laugh
    chat wave, and a third counseling donation at ~90s.
  - Remove topic drift toward games; the default persona/topic should be a
    professor's computer-graphics research lab maid.
- Runtime changes:
  - `sendDonation()` now awaits the male Edge TTS readout before POSTing
    `/credo/vtuber-mode/donation`.
  - If donation readout fails, the VTuber donation answer is not queued.
  - Donation POST payload records `donation_readout_completed`,
    `donation_readout_completed_at`, and `donation_input_after_readout`; route
    logs include the same fields for experiment audit.
  - `Start Scenario` no longer triggers the initial monologue; the first
    scenario input is the scheduled donation at ~3s.
  - Shared scenario now uses three counseling donations and a 1-minute
    simultaneous laughter/chat-wave segment.
  - Default topic/prompt guard now steers quiet or unclear turns toward computer
    graphics research lab material: rendering, shaders, animation, simulation,
    paper revisions, experiments, professor messages, and deadline bells.
- Docs/report updates:
  - Updated live usage guide and README scenario description.
  - Updated paper draft `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`
    with donation temporal gating, shared broadcast scenario, and CG lab topic
    lock.
- Verification:
  - Python compile passed for the active route, integration patcher, config,
    SlowTrack, and source/runtime CREDO agent files.
  - JS syntax checks passed for source/runtime frontend copies after WSL interop
    retry.
  - Source/runtime frontend and agent copies match (`frontend_cmp=0`,
    `agent_cmp=0`).
  - Static scenario check confirmed donation anchors at `3.0`, `60.0`, and
    `90.0`, laugh-wave chat lines, and no automatic scenario-start monologue
    call before `scheduleScenarioTimeline()`.

## 2026-05-28 07:55 KST - Donation Emotion Motion Uses DistilBERT

- Owner/chat: framework/runtime
- User request:
  - Donation readout should show the emotion expression motion inferred from
    the donation text.
  - The user-provided Idle motion should keep running during VTuber speech
    together with lip-sync.
  - Donation answer emotion must not be hard-coded as positive; it must be
    inferred by DistilBERT.
- Runtime changes:
  - Added `/credo/vtuber-mode/donation-emotion` for readout-time donation text
    emotion analysis via `fasttrack_router_v3` DistilBERT/GoEmotions.
  - Donation readout playback now starts emotion motion while the male
    donation TTS is playing.
  - `/credo/vtuber-mode/donation` ignores frontend emotion payloads and
    re-runs DistilBERT/GoEmotions on the donation message immediately before
    queueing the VTuber answer.
  - Removed remaining route-level `emotion: positive` hard overrides for
    idle/chat/manual VTuber turns.
  - Idle motion replay is allowed during speech, while the existing volume
    pulse continues to drive lip-sync.
- Verification:
  - Python compile passed for route, integration patcher, and source/runtime
    CREDO agent files.
  - JS syntax check passed for the frontend overlay after WSL interop retry.
  - Source/runtime frontend and agent copies match.

## 2026-05-28 09:01 KST - Pause spaCy Spoken Keyword Echo

- Owner/chat: framework/runtime
- User request:
  - Temporarily suspend the spaCy echoing feature while keeping the broader
    experiment intact.
- Runtime changes:
  - Set the live profile override to `FAST_TRACK_KEYWORD_ECHO_ENABLED=0` and
    `FAST_TRACK_KEYWORD_ECHO_PROBABILITY=0.0` in `AI_NPC_System/project_config.sh`.
  - Kept `FAST_TRACK_KEYWORD_SOURCE_BIAS=1`, so spaCy keyword extraction remains
    available for metadata/source bias rather than spoken output.
  - Added a runtime guard in the source and vendor CREDO agent copies so a
    disabled echo setting removes any stale `keyword_echo_prefix`, records
    `keyword_echo_disabled=true`, and returns the original FastTrack text.
- Docs:
  - Updated the TTS routing, runtime-flow, and research-methodology docs to
    describe spaCy keywords as metadata/source-bias signals with spoken echo
    paused.
- Verification:
  - Python compile passed for the source and vendor CREDO agent files.
  - No services were started.

## 2026-05-28 09:23 KST - Six-Case Virtual Broadcast UI Review

- Owner/chat: experiment UI review
- User request:
  - Verify that the virtual broadcast UI and functions match the six-case
    design: Grounded Serial, Emotion Only Serial, Intent Only Serial, Neutral
    Random Serial, Grounded Parallel, and SlowTrack Only.
- Findings:
  - The source and vendor frontend hook files are byte-identical.
  - The UI exposes six `Experiment cases` buttons with the expected payloads:
    `case_1_grounded_serial`, `case_2_emotion_only_serial`,
    `case_3_intent_only_serial`, `case_4_neutral_random_serial`,
    `case_5_grounded_parallel`, and `case_6_slowtrack_only`.
  - `Start Scenario` preserves and re-sends the selected experiment payload to
    `/credo/vtuber-mode/start`; the backend start route reapplies those factors
    through `_apply_experiment_factors(payload)`.
  - Backend factor normalization accepts `grounded`, `emotion_only`,
    `response_act_only`, `neutral_random`, and `none`; `none` forces
    `component_mode=none` and `scheduling_mode=serial`.
  - The shared scenario remains 150 seconds with ten recurring viewer names and
    donation anchors at 3s, 60s, and 90s.
- Verification:
  - Static validation script passed for case presets, UI button ids, backend
    allowed values, scenario duration, ten fixed viewers, and donation anchors.
  - Python compile passed for active `routes.py` and `apply_integration.py`.
  - Runtime/browser click validation was not run because the Open-LLM server is
    currently not listening on `127.0.0.1:12393`; no services were started.

## 2026-05-28 09:40 KST - Scenario Valence Sharpening

- Owner/chat: virtual broadcast scenario
- User request:
  - Make two donation counseling prompts and surrounding chat lean more clearly
    positive or negative for cleaner Emotion Only interpretation.
- Implemented:
  - Updated both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Kept the shared 150-second scenario, ten recurring viewer names, and
    donation anchors unchanged.
  - Rewrote the 60s `CoffeeCalibrator` donation as a clearly positive/relieved
    lab-win counseling prompt, with supportive positive chat responses.
  - Rewrote the 90s `PipettePanic` donation as a clearly negative/anxious
    burnout counseling prompt, with worried negative-support chat responses.
  - Updated scenario direction text to tell the VTuber that the second donation
    is positive/relieved and the third is negative/anxious without mentioning
    the experiment.
- Verification:
  - Source/vendor frontend hook files are byte-identical.
  - Static scenario validation passed for 150s duration, ten fixed viewers,
    donation anchors at 3s/60s/90s, and the new positive/negative valence
    phrases.
  - `git diff --check` passed for the edited frontend files.
  - JS syntax check was not run because Node is not available in the current WSL
    session; no services were started.

## 2026-05-28 09:54 KST - Broadcast-Style Counseling Scenario Rebuild

- Owner/chat: virtual broadcast scenario
- User correction:
  - The scenario should follow the newly specified broadcast structure:
    no intro monologue, first donation at ~3s, the `I hate my prof but I have
    to love him....` donation at ~60s, a burst of laughter/emote-style chat,
    a new concern donation at ~90s, response chat, then ending chat.
- Implemented:
  - Rebuilt the shared 150-second timeline in both frontend hook copies:
    - `AI_NPC_System/integrations/open_llm_vtuber/frontend/credo-vtuber-mode.js`
    - `vendor/open-llm-vtuber/frontend/credo-vtuber-mode.js`
  - Kept the newer fixed ten-viewer room:
    `CGLAPER`, `ICE-TLAB`, `Hebongbong`, `FrogYang`, `ElonMuscuba`,
    `ZizonJunsu`, `QueenYeseul`, `HoneyPeace`, `YoungKK`, `SolarSido`.
  - First donation at 3s is now high-negative panic about deleted lab logs.
  - Second donation at 60s now contains the requested phrase and presents a
    conflicted love-hate professor story.
  - Added a dense 60.4s-62.4s laughter wave with repeated room viewers using
    `LOL`, `lmao`, `HAHAHAHA`, `XD XD XD`, `www`, and related chat reactions.
  - Third donation at 90s is a new negative/anxious simulation/reviewer/lab
    meeting concern, followed by supportive worried chat and an ending message.
  - Scenario direction now explicitly describes the first donation as negative
    panic, the second as love-hate comedy with laughter wave, and the third as
    negative/anxious.
- Verification:
  - Source/vendor frontend hook files are byte-identical.
  - Static scenario validation passed for 150s duration, ten fixed viewers,
    donation anchors at 3s/60s/90s, required phrase presence, laughter-wave
    strings, and no Korean characters in the timeline.
  - `git diff --check` passed for the edited frontend files.
  - Runtime/browser validation and JS syntax check were not run because the
    server remains off and Node is unavailable in the current WSL session.

## 2026-05-28 10:08 KST - Donation Prompt Length Correction

- Owner/chat: virtual broadcast scenario
- User correction:
  - Donation contents were too long and the 60s `I hate my prof but I have to
    love him....` donation needed to be placed exactly at the one-minute
    donation point.
- Implemented:
  - Shortened all three scenario donation messages to at most three sentences.
  - Kept the 3s/60s/90s donation anchors unchanged.
  - Ensured the 60s `ICE-TLAB` donation starts exactly with
    `I hate my prof but I have to love him....`.
  - Applied the same text to source and active vendor frontend hook copies.
- Verification:
  - Source/vendor frontend hook files are byte-identical.
  - Static validation passed: each donation is 3 sentences, all are under 240
    characters, the 60s donation starts with the requested phrase, and no Korean
    characters appear in the scenario timeline.
  - `git diff --check` passed for the edited frontend files.
  - No services were started.

## 2026-05-28 10:29 KST - Stop Mouth Pulse On Donation Interrupt

- Owner/chat: frontend Live2D/audio interrupt
- User report:
  - When a donation interrupts active VTuber speech, audio stops immediately
    but the mouth animation keeps moving briefly before stopping.
- Root cause:
  - The VTuber audio element was paused, but the separate CREDO speech
    parameter pulse loop continued until its original audio-volume duration
    expired.
- Implemented:
  - Added `stopSpeechParameterPulse()` to cancel the active
    `requestAnimationFrame` mouth/body pulse, invalidate stale pulse frames via
    `parameterPulseToken`, zero `ParamMouthOpenY`, and optionally return to idle
    motion.
  - Wired that stop path into donation readout start, local interrupt send,
    received `interrupt-signal`, non-donation audio `pause`, non-donation audio
    `ended`, and dropped VTuber audio payloads during donation readout.
  - Applied the same changes to source and active vendor frontend hook copies.
- Verification:
  - Source/vendor frontend hook files are byte-identical.
  - Static validation confirmed the mouth-pulse stop hooks and stale-frame token
    guard are present.
  - `git diff --check` passed for the edited frontend/worklog files.
  - Runtime/browser validation and JS syntax check were not run because the
    server remains off and Node is unavailable in the current WSL session.

## 2026-05-28 13:28 KST - Paper Draft Updated To Current Experiment State

- Owner/chat: research writing
- User request:
  - Reflect the recent implementation and methodology state in the paper draft.
- Updated:
  - `AI_NPC_System/reports/credo_paper_draft_without_results_2026-05-26.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
- Paper/methodology changes:
  - Added the current conditional FastTrack hypothesis set H1-H4.
  - Replaced older `None` contextual-control wording with `Neutral Random`
    for low-context FastTrack and kept `SlowTrack Only` as the separate
    absolute control.
  - Documented the six primary run cases:
    Grounded Serial, Emotion Only Serial, Intent Only Serial, Neutral Random
    Serial, Grounded Parallel, and SlowTrack Only.
  - Updated the shared 150-second graduate-school counseling scenario anchors:
    3s deleted logs donation, 60s `I hate my prof but I have to love him....`
    donation with laughter chat wave, 90s simulation-crash donation, then
    reaction/end chat.
  - Added the current spaCy status: keyword extraction remains metadata/source
    bias only; spoken keyword echo is paused.
  - Added donation readout/queue and mouth-pulse interrupt behavior to the
    paper draft implementation description.
  - Updated measurement text to include `experiment_run_id`,
    `experiment_factor`, `scenario`, `runtime_mode`, and `event` logging fields.
- Verification:
  - `git diff --check` passed for the edited paper/methodology/worklog files.
  - Search found no remaining old `4 x 2`, `visually intuitive`, or old
    `None` contextual-control wording in the updated draft/methodology files.
  - No services were started.

## 2026-05-28 KST - Viewer Address Honorific Restored

- Owner/chat: current CREDO VTuber persona/runtime thread
- User request:
  - Restore the concept phrase at the end of VTuber answers.
  - Address the current target as `<nickname> kyo-shu-zin-sa-ma`, not only a
    bare suffix.
  - Add maid-cafe wordplay guidance to the Professor's Lab Maid persona.
- Changes:
  - Set `CREDO_VIEWER_ADDRESS_SUFFIX` default/profile value to
    `kyo-shu-zin-sa-ma`.
  - Updated SlowTrack, Open-LLM-VTuber persona, compact LLM prompt, character
    YAML, and persona docs to allow the honorific and remove the old
    "do not append fixed catchphrases" rule.
  - Added route metadata so idle/chat/manual turns target `chat`, and donation
    turns target the donor nickname. The agent post-processor appends
    `<target> kyo-shu-zin-sa-ma` after cleaning duplicates.
  - Added maid-cafe wordplay guidance for phrases such as welcome home, order
    received, service bell, omurice spell, and special menu, adapted into lab
    jokes.
- Verification:
  - `apply_integration.py --activate` completed and kept source/runtime agent
    and frontend copies byte-identical.
  - Python compile passed for config, SlowTrack, integration patcher, source
    and runtime CREDO agent, and active Open-LLM-VTuber routes.
  - `bash -n AI_NPC_System/project_config.sh` passed.
  - Windows `node.exe --check` passed for the changed VTuber frontend.
  - Direct post-processor smoke test produced
    `StackTraceSam kyo-shu-zin-sa-ma` and did not duplicate an existing suffix.

## 2026-05-28 KST - Fixed Scenario Viewers And Non-Mechanical Addressing

- Owner/chat: current CREDO VTuber persona/runtime thread
- User request:
  - Replace the virtual broadcast's ten recurring viewer nicknames with:
    `CGLAPER`, `ICE-TLAB`, `Hebongbong`, `FrogYang`, `ElonMuscuba`,
    `ZizonJunsu`, `QueenYeseul`, `HoneyPeace`, `YoungKK`, and `SolarSido`.
  - If the VTuber answers one specific chat, use that author's nickname plus
    `kyo-shu-zin-sa-ma`.
  - If the VTuber summarizes multiple chat messages, do not mention every
    nickname.
  - Make this a prompt behavior rather than a mechanical suffix appended to
    every answer.
- Changes:
  - Updated the shared 150-second virtual broadcast scenario to use the new ten
    nicknames in source and runtime frontend copies.
  - Changed live-chat batch metadata to target `chat` instead of mechanically
    selecting the first chat author.
  - Changed the CREDO agent prompt so direct targets such as donation authors
    get a strong address rule, while chat batches tell the LLM to choose at most
    one focused author or address the room naturally.
  - Changed the suffix post-processor so it only appends the honorific when
    explicit `enforce_viewer_address_suffix` metadata is present; normal VTuber
    turns now rely on prompt behavior.
- Verification:
  - `apply_integration.py --activate` completed and kept source/runtime agent
    and frontend copies byte-identical.
  - No old scenario viewer nicknames remain in the source/runtime frontend or
    active route/agent copies.
  - Python compile passed for config, SlowTrack, integration patcher, source
    and runtime CREDO agent, and active Open-LLM-VTuber routes.
  - `bash -n AI_NPC_System/project_config.sh`, `git diff --check`, and Windows
    `node.exe --check` passed.
  - Direct smoke test confirmed default post-processing does not append the
    suffix mechanically, while explicit enforcement still produces
    `QueenYeseul kyo-shu-zin-sa-ma`.

## 2026-05-28 KST - Donation Readout Subtitle Gate

- Owner/chat: current CREDO VTuber frontend/runtime thread
- User request:
  - VTuber subtitles were appearing before the male donation readout voice had
    finished.
- Fix:
  - Added a frontend guard in `handleCredoAudioPayload()` so any VTuber audio
    payload arriving while `donationReadoutActive` is true is dropped before
    motion/subtitle scheduling.
  - The guard also hides the current VTuber subtitle and logs
    `CREDO dropped VTuber audio payload during donation readout.` for debugging.
  - Source and runtime frontend copies were synced through
    `apply_integration.py --activate`.
- Verification:
  - Source/runtime frontend files are byte-identical.
  - `git diff --check` passed for both frontend copies.
  - Windows `node.exe --check` passed.

## 2026-05-28 KST - Targeted Chat Honorific Prompt Strengthened

- Owner/chat: current CREDO VTuber persona/runtime thread
- User request:
  - The model was not reliably ending a targeted chat answer with
    `<author> kyo-shu-zin-sa-ma`.
  - Keep the behavior prompt-based, not a mechanical suffix on every answer.
- Changes:
  - Strengthened the live-chat batch route prompt:
    chat lines are explained as `Viewer AUTHOR says: MESSAGE`; if the model
    directly answers one specific chat line, the final sentence must end exactly
    with `AUTHOR kyo-shu-zin-sa-ma`.
  - Strengthened the CREDO agent prompt:
    one clear target gets an exact final-address rule; chat batches must choose
    at most one author or summarize the room without the honorific.
  - Strengthened config/profile prompts and the shared scenario direction with
    the same conditional rule.
  - Donation turns now also include an explicit final-address instruction using
    the donor name.
- Verification:
  - `apply_integration.py --activate` completed.
  - Source/runtime agent and frontend copies are byte-identical.
  - Python compile passed for config, SlowTrack, integration patcher, source
    and runtime agent, and active Open-LLM-VTuber routes.
  - `bash -n`, `git diff --check`, and Windows `node.exe --check` passed.
  - Direct prompt smoke test showed the live-chat batch prompt contains the
    exact `AUTHOR kyo-shu-zin-sa-ma` final-sentence rule.

## 2026-05-28 KST - Conditional Honorific Postprocessor

- Owner/chat: current CREDO VTuber persona/runtime thread
- User request:
  - Prompt-only handling still failed to keep the final target nickname plus
    `kyo-shu-zin-sa-ma` at the end of the VTuber answer.
- Root cause:
  - `_clean_vtuber_slow_text()` strips honorific variants before TTS cleanup.
    The old `_ensure_viewer_address_suffix()` only re-added the address when an
    explicit force flag existed, so prompt-compliant endings could disappear.
- Fix:
  - Added conditional final-address enforcement in the CREDO agent.
  - Direct named targets such as donation authors now end with exactly
    `<target> kyo-shu-zin-sa-ma`.
  - Live-chat batches only get the suffix when the final generated text mentions
    exactly one author from the `Viewer AUTHOR says:` chat context.
  - Multi-author and room-summary answers remain natural and do not receive a
    mechanical suffix.
  - The postprocessor also removes a trailing duplicate nickname left after
    cleanup, preventing output like `QueenYeseul, QueenYeseul
    kyo-shu-zin-sa-ma`.
- Verification:
  - `apply_integration.py --activate` completed and source/runtime agent copies
    are byte-identical.
  - Python compile passed for the source and runtime CREDO agent, integration
    patcher, and active Open-LLM-VTuber routes.
  - Direct smoke tests confirmed:
    donation target -> `QueenYeseul kyo-shu-zin-sa-ma`;
    one mentioned chat author -> `CGLAPER kyo-shu-zin-sa-ma`;
    multiple or zero mentioned chat authors -> no suffix.

## 2026-05-28 KST - Scenario Donation Timing And Two-Sentence Repair

- Owner/chat: current CREDO VTuber virtual broadcast scenario
- User report:
  - The shared scenario still appeared to use long donation counseling prompts.
  - The one-minute donation was not visibly appearing during the run.
- Root cause:
  - The active scenario text still had older long donation messages; the 60s
    donation had not been reduced to the requested two-sentence form.
  - The frontend cache-buster in the injected script tag still used an older
    `20260527-ui-fix` version, so a browser could keep loading stale scenario
    JavaScript after file edits.
  - Scenario status only updated after `await sendDonation()`, making a delayed
    or failed donation readout look like the scheduled event never started.
- Fix:
  - Reduced all three scenario donation messages to exactly two sentences.
  - Kept the required donation anchors at 3s, 60s, and 90s; the 60s donation
    now starts with `I hate my prof but I have to love him....`.
  - Updated the injected frontend script URL to
    `credo-vtuber-mode.js?v=20260528-scenario-2sentence`.
  - Added `CREDO scenario scheduled`, `CREDO scenario donation start`, and
    `CREDO scenario chat` console logs, and moved the donation-start status
    before the donation readout await.
- Verification:
  - `apply_integration.py --activate` completed and source/runtime frontend
    files are byte-identical.
  - Static validation confirmed donation anchors `[3.0, 60.0, 90.0]`, three
    donations, and exactly two sentence-terminated segments per donation.
  - `vendor/open-llm-vtuber/frontend/index.html` now references the new cache
    version.
  - `git diff --check` passed and Windows `node.exe --check` passed for both
    source and runtime frontend files.
  - Runtime browser validation was not run because `127.0.0.1:12393` is not
    currently listening.

## 2026-05-28 KST - Donation Queue And Subtitle Stability

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User report:
  - VTuber subtitles could suddenly disappear during testing.
  - Overlapping donations should play slowly in order instead of interrupting
    each other.
  - Scenario donation prompts were still too long and should be short
    two-sentence prompts.
- Fix:
  - Added a frontend donation promise queue so only one donation readout/post
    sequence runs at a time. Later donations log `CREDO donation queued` and
    wait behind the active one.
  - Added a donation queue token so scenario stop/reset cancels queued
    donation work and stops the current readout audio.
  - Tightened subtitle hiding: unrelated audio pause/end events no longer hide
    the current VTuber subtitle unless they carry the matching subtitle token.
  - Extended subtitle lifetime when no reliable audio duration is present, while
    still allowing matching audio end/pause to clear it.
  - Shortened the three scenario donations to compact two-sentence prompts:
    `QueenYeseul` at 3s, `ICE-TLAB` at 60s, and `Hebongbong` at 90s.
  - Updated the injected frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-donation-queue-subtitle`.
- Verification:
  - `apply_integration.py --activate` completed and source/runtime frontend
    files are byte-identical.
  - Static validation confirmed donation anchors `[3.0, 60.0, 90.0]`, exactly
    three donation events, exactly two sentence-terminated segments per
    donation, and message length <= 105 characters.
  - `vendor/open-llm-vtuber/frontend/index.html` references the new cache
    version.
  - `git diff --check` passed and Windows `node.exe --check` passed for both
    source and runtime frontend files.
  - Runtime browser validation was not run because the user had requested the
    server be off.

## 2026-05-28 KST - Scenario Donation Copy Tuning

- Owner/chat: current CREDO VTuber virtual broadcast scenario
- User request:
  - Remove the first sentence from the 60s donation and keep only the
    figure/script contrast.
  - Make the 90s donation more comedic with a recognizable US graduate-school
    joke.
- Changes:
  - 60s `ICE-TLAB` donation now reads:
    `He rejected my figure. Then he fixed my dataset script.`
  - 90s `Hebongbong` donation now uses a stipend/free-seminar-pizza joke:
    `My stipend vanished into rent and conference fees. Is free seminar pizza
    the official grad school meal plan?`
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-grad-joke-scenario`.
- Verification:
  - `apply_integration.py --activate` completed and source/runtime frontend
    files are byte-identical.
  - Static validation confirmed donation anchors `[3.0, 60.0, 90.0]`, exactly
    two sentence-terminated segments per donation, removal of
    `I hate my prof but I have to love him`, and presence of the free seminar
    pizza joke.
  - `git diff --check` passed and Windows `node.exe --check` passed for both
    source and runtime frontend files.

## 2026-05-28 KST - Donation SFX Always Plays

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User request:
  - The donation popup effect sound was not playing; make it play every time a
    donation window appears.
- Root cause:
  - `sendDonation()` still skipped `playDonationSfx()` when the active
    experiment was SlowTrack-only / no-FastTrack.
- Fix:
  - Removed the `slowTrackOnly` gate around donation SFX.
  - Moved `playDonationSfx()` immediately after `showDonationOverlay(...)`, so
    the sound is attempted for every donation popup independent of experiment
    condition.
  - Added console diagnostics:
    `CREDO donation SFX play`, `CREDO donation SFX blocked`, and
    `CREDO donation SFX failed`.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-donation-sfx-always`.
- Verification:
  - `apply_integration.py --activate` completed and source/runtime frontend
    files are byte-identical.
  - Static validation confirmed no `slowTrackOnly` SFX skip remains, SFX is
    invoked immediately after the donation overlay appears, and the runtime
    `credo-donation-sfx.mp3` asset exists.
  - Active routes still expose `/credo/vtuber-mode/donation-sfx`.
  - `git diff --check` passed and Windows `node.exe --check` passed for both
    source and runtime frontend files.

## 2026-05-28 KST - True Data Log Session Split

- Owner/chat: current CREDO experiment logging thread
- User request:
  - Start a fresh log file from now on because newly accumulated logs are the
    real experiment data.
- Changes:
  - Created new canonical latency log session id:
    `true_data_20260528_143735`.
  - Added `CREDO_LATENCY_LOG_STEM`, `CREDO_LATENCY_LOG_DIR`, and
    `CREDO_RUNTIME_LOG_STEM` to `AI_NPC_System/project_config.sh`.
  - Updated `LatencyLogger` so environment variables can route JSONL, module
    CSV, and Markdown summary outputs to a fresh session file.
  - Updated `run_credo_stack.py` so service logs also use the runtime log stem,
    for example `runtime/logs/open-llm.true_data_20260528_143735.log`.
- New latency files:
  - `AI_NPC_System/latency_logs/true_data_20260528_143735.events.jsonl`
  - `AI_NPC_System/latency_logs/true_data_20260528_143735.module_events.csv`
  - `AI_NPC_System/latency_logs/true_data_20260528_143735.latest_summary.md`
- Verification:
  - Fresh files were initialized; JSONL is empty and the module CSV contains
    only the schema header.
  - Python compile passed for `latency_observer.py` and `run_credo_stack.py`.
  - `bash -n` passed for the project config and stack launch scripts.

## 2026-05-28 14:02 KST - Restore VTuber Subtitles After Status Hide

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User report:
  - VTuber subtitles were not appearing again.
- Root cause:
  - The frontend hook hid the Open-LLM-VTuber subtitle/status shell when it saw
    placeholder text such as `Thinking...` or `New Conversation Started`, but it
    never restored that same shell when real spoken subtitle text replaced the
    placeholder.
  - SlowTrack-only VTuber turns were also passing empty `display_text` because
    the agent used `hide_display=True` whenever `metadata.vtuber_mode` was set.
- Fix:
  - Added explicit marker attributes for status-hidden subtitle shells.
  - Preserved the previous inline `display` and `aria-hidden` values before
    hiding a status shell.
  - Restores the shell automatically when the text becomes real spoken content,
    while still suppressing placeholder status text.
  - SlowTrack-only VTuber turns now keep `display_text` populated, so Case 6
    can display subtitles instead of sending an empty display payload.
  - Updated the injected frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-subtitle-restore`.
- Verification:
  - Source and runtime frontend hook files are byte-identical.
  - Source and runtime CREDO latency-cover agent files are byte-identical.
  - Python AST parsing passed for both agent files.
  - `git diff --check` passed for the touched frontend, integration, agent,
    and worklog files.
  - Node is not available in the current WSL shell, so JS syntax/runtime browser
    validation was not run in this turn.

## 2026-05-28 14:32 KST - Natural Viewer Addressing and Donation Follow-Up Chat

- Owner/chat: current CREDO VTuber virtual broadcast runtime
- User report:
  - The VTuber awkwardly pronounced the English romanized viewer suffix
    `kyo-shu-zin-sa-ma`.
  - It seemed to answer donations but not normal comments afterward.
  - Donation responses sometimes began with a stray short audio such as `uh`
    before the real answer started about a second later.
- Root causes:
  - `project_config.sh` and generated Open-LLM-VTuber character configs still
    forced the romanized honorific even after other prompt edits.
  - Donation turns still allowed spoken FastTrack audio, so a short urgent
    FastTrack reaction could play immediately before the main donation answer.
  - Normal chat batching used a recent-time window and could be consumed or
    expire while the donation answer was still occupying the VTuber turn.
- Fix:
  - Removed the forced romanized viewer suffix from CREDO defaults and active
    project prompts; viewer addressing is now natural and optional.
  - Added a guard that sanitizes legacy romanized suffix environment values if
    an old shell still exports them.
  - Donation turns now pass `suppress_fasttrack_audio=True`, so FastTrack can
    still provide internal context but does not emit the stray spoken reaction
    before the main donation answer.
  - Added a post-donation chat follow-up scheduler that waits until the
    donation answer finishes, drains buffered chat, and queues a separate
    response to recent chat context.
  - Updated `apply_integration.py` so these runtime route, prompt, and cache
    changes survive future `--activate` runs.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-donation-chat-natural-speech`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical, and source/runtime
    CREDO latency-cover agent files are byte-identical.
  - Python AST parsing passed for `config.py`, `slow_track.py`,
    `apply_integration.py`, both CREDO latency-cover agent files, and the
    active Open-LLM-VTuber `routes.py`.
  - Static checks confirmed empty default viewer suffix, donation FastTrack
    audio suppression, post-donation chat follow-up scheduling, and updated
    frontend cache-buster.
  - Active code/config grep found no remaining live references to the old
    romanized suffix prompt.
  - `git diff --check` passed for the touched source/config/worklog files.
  - No browser/server runtime test was run in this turn; backend changes require
    restarting the Open-LLM-VTuber stack before manual validation.

## 2026-05-28 14:47 KST - Denser Scenario Chat and FastTrack Subtitle Marking

- Owner/chat: current CREDO VTuber virtual broadcast frontend/runtime
- User report:
  - Scenario chat was too slow; the middle donation needs simultaneous `lol`
    style reactions and more frequent short chat messages.
  - Subtitles disappear in the SlowTrack-only case UI state and should stay on
    consistently.
  - FastTrack subtitles should be visually distinguishable.
  - Repeated FastTrack lines are not acceptable for the large dataset-pool
    setup.
- Fix:
  - Reworked the shared 150-second scenario to 3 donations plus 57 short chat
    events from the same ten recurring viewers.
  - Added a dense middle-donation laughter burst from T+60.1 to T+61.0 with
    short `LOL`, `lmao`, `HAHAHAHA`, `XD`, and emoji-style reactions.
  - Increased the visible virtual chat retention from 11 to 16 messages so the
    faster chat cadence reads as a live room instead of disappearing too soon.
  - Added CREDO subtitle stage metadata from the agent to the browser payload.
    FastTrack subtitle text now gets a cyan color and a `FASTTRACK` badge.
  - Changed the custom subtitle layer to keep the last spoken subtitle visible
    until the next subtitle or an explicit interrupt/stop, which prevents
    SlowTrack-only mode from appearing subtitle-less between audio events.
  - Expanded FastTrack duplicate avoidance:
    `FASTTRACK_ROUTER_V3_RECENT_TEXT_WINDOW=2048` and
    `FASTTRACK_AGENT_RECENT_TEXT_WINDOW=512`.
  - Removed duplicate fallback in router/agent selection; if all routed
    candidates are recent repeats, the system skips FastTrack for that turn
    instead of replaying a repeated line.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-chatburst-subtitle-fasttrack`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical, and source/runtime
    CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `config.py`, `fasttrack_router_v3.py`,
    `apply_integration.py`, both CREDO latency-cover agent files, and related
    source files.
  - `git diff --check` passed for the touched source/config/worklog files.
  - Static scenario check confirmed 57 chat events, 3 donation events, and all
    T+60.1 through T+61.0 burst anchors.
  - Windows `node.exe --check` could not run from the current WSL session due
    to `UtilBindVsockAnyPort: socket failed 1`.
  - No browser/server runtime test was run in this turn; backend/frontend
    changes require restarting the Open-LLM-VTuber stack and hard-refreshing
    the browser before manual validation.

## 2026-05-28 15:01 KST - Revert Added Subtitle Frame, Keep CREDO Subtitle Layer

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User correction:
  - "Existing subtitle" means the CREDO custom subtitle layer that was already
    built for this project, not Open-LLM-VTuber's default black subtitle frame.
  - The newly visible framed/default subtitle layer should be removed.
- Fix:
  - Kept the CREDO custom subtitle layer enabled:
    `CREDO_SPEECH_SUBTITLES_ENABLED=true`.
  - Suppressed Open-LLM-VTuber default subtitle/status frames:
    `SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES=true`.
  - Removed the added visible `FASTTRACK` subtitle badge/frame path. FastTrack
    can still be distinguished by the same subtitle text changing color, without
    adding a separate label or box.
  - Ensured old duplicate `#credo-speech-subtitle` nodes are removed before the
    active CREDO subtitle layer is appended.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-credo-subtitle-no-frame`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - Static grep confirmed no `subtitle-stage` or visible `FASTTRACK` badge text
    remains in the frontend hook.
  - `git diff --check` passed for the touched frontend, integration, and
    worklog files.
  - No browser/server runtime test was run in this turn; manual validation needs
    a stack restart or browser hard refresh so the new cache-buster is loaded.

## 2026-05-28 15:09 KST - Restore Overlay UI After Overbroad Subtitle Suppression

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User report:
  - Overlay UI disappeared after the subtitle-frame suppression change.
- Root cause:
  - `SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES=true` made the mutation observer hide
    any dark lower overlay that looked subtitle-shaped. That heuristic was too
    broad and could hide CREDO UI surfaces.
- Fix:
  - Set `SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES=false` to stop broad DOM hiding.
  - Kept `CREDO_SPEECH_SUBTITLES_ENABLED=true`, so the CREDO custom subtitle
    layer remains active.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-ui-restore`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - `git diff --check` passed for the touched frontend, integration, and
    worklog files.
  - No browser/server runtime test was run in this turn; manual validation needs
    a browser hard refresh so the hidden live DOM is recreated from the restored
    script.

## 2026-05-28 15:22 KST - Target Duplicate Subtitle and Preserve Serial FastTrack

- Owner/chat: current CREDO VTuber virtual broadcast frontend/runtime
- User request:
  - Remove only the duplicate lower subtitle window.
  - In Case 1 / Serial conditions, do not skip FastTrack just because recent
    candidates repeat.
  - Prevent the VTuber from saying viewer names with an `@` prefix.
  - Commit the completed fix.
- Fix:
  - Re-enabled duplicate default subtitle suppression, but narrowed it to only
    Open-LLM subtitle frames whose text matches the current CREDO subtitle text.
    This avoids hiding unrelated CREDO overlay UI.
  - Inspected the active FastTrack dataset pool: GoEmotions has 1,131 items and
    SWDA has 1,049 items, so frequent repeat selection should not be treated as
    normal.
  - Changed Grounded routing from rank-aligned Go/SWDA pairing to cross-pair
    traversal, so it samples a much larger portion of the emotion x response-act
    candidate space before declaring candidates exhausted.
  - Serial FastTrack now reuses a recent candidate if every routed candidate is
    recent; only Parallel mode may skip a repeated FastTrack candidate.
  - Router-level duplicate fallback follows the same rule: repeated candidates
    are allowed again outside Parallel scheduling.
  - Added prompt and cleanup guards so `@ViewerName` becomes `ViewerName` before
    TTS/display output.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-subtitle-targeted-ft-serial`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical, and source/runtime
    CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `fasttrack_router_v3.py`,
    `apply_integration.py`, both CREDO latency-cover agent files, and related
    touched Python files.
  - Static checks confirmed targeted subtitle suppression is present, the old
    broad text suppression pattern is gone, Serial FastTrack reuse is present,
    and `@` cleanup is present.
  - `git diff --check` passed for the touched frontend/runtime/worklog files.
  - Browser/runtime validation was not run in this turn.

## 2026-05-28 15:36 KST - Document FastTrack Combinatorial Interpretation

- Owner/chat: current CREDO experiment methodology / paper draft
- User request:
  - Reflect the FastTrack repetition/combinatorial-space clarification in the
    paper draft and Codex shared status report.
- Methodology clarification:
  - The active evidence pools are GoEmotions 1,131 items and SWDA 1,049 items,
    so frequent repeated FastTrack candidates should not be interpreted as a
    normal limitation of the available combination space.
  - Grounded FastTrack should be described as cross-pair traversal between
    emotion evidence and response-act evidence, not same-rank 1:1 pairing.
  - Repetition is a retrieval/filtering/spoken-realization quality signal.
  - Serial conditions must not suppress FastTrack solely because a candidate is
    recent; otherwise Case 1-4 would mix contextual mapping quality with
    FastTrack presence/absence.
  - Parallel conditions may bypass or shorten FastTrack when a prepared
    SlowTrack response is available; that behavior belongs to the scheduling
    architecture factor.
- Files updated:
  - `AI_NPC_System/reports/credo_paper_draft_without_results.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
  - `CODEX_SHARED_WORKLOG.md`
- Verification:
  - Documentation-only update. No runtime/browser test was run.
  - `git diff --check` passed for the paper draft, methodology doc, and shared
    worklog paths.

## 2026-05-28 15:50 KST - Preserve Donation FastTrack Order and Suppress Scenario Autostart Speech

- Owner/chat: current CREDO VTuber virtual broadcast scenario/runtime
- User report:
  - When a donation interrupts ongoing VTuber speech, the follow-up order did
    not feel preserved.
  - Start Scenario must not be treated like a viewer/LLM input, because the
    first scripted donation arrives within 3 seconds.
- Fix:
  - Removed donation-turn `suppress_fasttrack_audio` from the active VTuber
    route generation path, so donation answers restart as FastTrack then
    SlowTrack after the readout/interrupt.
  - Donation handling now cancels any prepared VTuber SlowTrack prefetch before
    triggering the donation answer. This prevents a stale prepared continuation
    from bypassing the fresh donation FastTrack sequence.
  - Added `idle_suppressed_until` to VTuber mode state. Start Scenario sends
    `scenario_start_only=true` and `idle_grace_seconds=8`, so `/start` applies
    mode/topic/broadcast direction but does not immediately generate an idle
    monologue from that setup prompt.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-scenario-idle-donation-ft`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical, and source/runtime
    CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `apply_integration.py`, active
    `routes.py`, and source/runtime CREDO latency-cover agent files.
  - `git diff --check` passed for the touched integration/frontend paths.
  - JavaScript syntax check could not run in this WSL shell because `node` /
    `nodejs` is not installed.
  - Browser/runtime scenario validation was not run in this turn.

## 2026-05-28 16:02 KST - Enforce Real Grounded Composition and Donation FastTrack

- Owner/chat: current CREDO FastTrack router / VTuber donation sequence
- User report:
  - Grounded appeared to pick only one dataset line instead of composing from
    both GoEmotions and SWDA evidence.
  - After a donation, FastTrack did not audibly appear; a short stray sound
    appeared before SlowTrack.
- Root cause:
  - Grounded metadata carried both source items, but spoken text could fall back
    to only the SWDA or only the GoEmotions clause if the other clause was
    filtered out.
  - The agent passed the ready SlowTrack prefetch task into router-v3 even for
    donation/live-chat turns. Router-v3 could therefore return a prefetch
    bypass before FastTrack, while the donation turn later refused to consume
    that prefetch.
  - The donation route also sent a second frontend `interrupt-signal` after the
    donation readout, which could race against the fresh FastTrack output.
- Fix:
  - Added a separate GoEmotions affect-clause cleaner and changed Grounded
    composition so spoken Grounded candidates require both a GoEmotions clause
    and an SWDA response-act clause.
  - Added `composition_sources=["go_emotions", "swda"]` metadata for Grounded
    candidates.
  - Agent now passes a prefetch queue into router-v3 only when the current
    VTuber event is eligible for prefetch bypass. Donation and live-chat batch
    turns always route FastTrack normally.
  - Donation route skips the second backend interrupt when the browser already
    posted the donation after readout (`donation_input_after_readout=true`).
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `fasttrack_router_v3.py`,
    `apply_integration.py`, active `routes.py`, and source/runtime CREDO
    latency-cover agent files.
  - Direct router store sample confirmed Grounded candidates now include both
    `go_emotions_item` and `swda_item` in the spoken text and metadata.
  - `git diff --check` passed for the touched files.
  - A full `analyze_and_route_chat_v3` smoke call was attempted but hung during
    local model loading in this shell, so browser/server runtime validation is
    still needed.

## 2026-05-28 16:26 KST - Pace CREDO Speech Subtitles By Audio Duration

- Owner/chat: current CREDO VTuber frontend subtitle layer
- User request:
  - Cut subtitles into smaller pieces and display them in sync with the spoken
    audio speed.
- Fix:
  - Reduced subtitle cue length to short chunks (`48` chars for SlowTrack,
    `54` chars for FastTrack) instead of pairing two long sentences on one
    subtitle screen.
  - Changed subtitle scheduling to use the actual audio duration when available.
    Cue start times are distributed proportionally across the audio duration,
    so long generated text no longer forces the subtitle timeline to lag behind
    speech.
  - Added a fallback duration estimator for payloads without audio volume
    metadata.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-paced-subtitles`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - Static grep confirmed the paced subtitle helpers and new cache-buster are
    present in source/runtime.
  - `git diff --check` passed for the touched integration/frontend/worklog
    paths.
  - JavaScript syntax check was not run because `node` / `nodejs` is not
    available in this WSL shell.

## 2026-05-28 16:37 KST - Restore Donation FastTrack Subtitles and Add FastTrack Gap

- Owner/chat: current CREDO VTuber donation FastTrack playback
- User report:
  - After a donation, FastTrack audio seemed to play or partially collide with
    SlowTrack, but the FastTrack subtitle did not appear.
- Root cause found in logs/code:
  - Latest `open-llm.true_data_20260528_143735.log` showed donation turns
    entering the FastTrack-first path, then logging
    `CREDO suppressed spoken FastTrack audio for this VTuber turn.`
  - `credo_latency_cover_agent.py` still forced
    `suppress_fasttrack_audio=True` whenever `vtuber_event == "donation"`.
    That meant donation FastTrack analysis/text could exist, but no FastTrack
    `AudioOutput` was sent to the frontend, so no FastTrack subtitle payload
    could appear.
- Fix:
  - Removed the hard-coded donation FastTrack suppression. Donation turns now
    only suppress FastTrack when metadata explicitly sets
    `suppress_fasttrack_audio`.
  - Added `CREDO_FASTTRACK_TO_SLOWTRACK_GAP_SECONDS` with default/export value
    `0.65`, and made the sequential speech guard use at least that much gap
    after FastTrack audio before SlowTrack is sent.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for source/runtime CREDO latency-cover
    agent, active routes, `apply_integration.py`, and `config.py`.
  - Static grep confirmed the runtime agent no longer contains the
    `vtuber_event == "donation"` FastTrack suppression condition.
  - Browser/runtime scenario validation still needs a fresh server restart and
    scenario run.

## 2026-05-28 16:43 KST - Prevent SlowTrack Opening Echo

- Owner/chat: current CREDO VTuber FastTrack-to-SlowTrack continuation
- User report:
  - SlowTrack sometimes repeats the beginning of the response twice.
- Root cause/interpretation:
  - Recent logs showed SlowTrack outputs beginning with stock phrases similar
    to the already-played FastTrack line, e.g. a short reaction-like opening
    followed by the actual answer.
  - `slow_track.py` passed the FastTrack text as an already-played line, but
    the wording could still invite the local LLM to reuse that opening.
- Fix:
  - Changed the SlowTrack system prompt wording so the already-spoken opening is
    explicitly continuity-only and must not be repeated, quoted, paraphrased, or
    used as the response beginning.
  - Added SlowTrack output cleanup in the latency-cover agent:
    - removes a duplicated first clause/sentence when the first two chunks are
      near-identical;
    - removes the leading 1-3 SlowTrack chunks if they are too similar to the
      just-played FastTrack text.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `slow_track.py`, source/runtime
    CREDO latency-cover agent, and active routes.
  - Static grep confirmed the runtime agent has the new
    `_strip_slowtrack_repeated_opening` cleanup.
  - Browser/runtime scenario validation still needs a fresh server restart and
    scenario run.

## 2026-05-28 16:47 KST - Update Scenario Donation Authors

- Owner/chat: current CREDO VTuber scenario timeline
- User request:
  - Make the first scenario donation come from `ElonMuscuba`.
  - Make the second scenario donation come from `Honeypeace`.
- Fix:
  - Updated the first donation at T+3.0s from `QueenYeseul` to `ElonMuscuba`.
  - Updated the second donation at T+60.0s from `ICE-TLAB` to `Honeypeace`.
  - Normalized the fixed audience list and `HoneyPeace` chat entries to
    `Honeypeace` so the recurring viewer identity is consistent.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-donation-authors`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - Active `frontend/index.html` references the new cache-buster.
  - Python bytecode compilation passed for `apply_integration.py` and active
    routes.

## 2026-05-28 16:57 KST - Randomize FastTrack Within Mapped Cells

- Owner/chat: current CREDO FastTrack router-v3
- User request:
  - FastTrack candidates still repeat too often.
  - Once emotion/intent mapping selects the valid dataset cell, choose randomly
    from the mapped candidates instead of repeatedly taking the same high-ranked
    items.
  - Continue filtering unusable dataset fragments.
- Fix:
  - Changed router-v3 bucket retrieval from similarity-ranked top hits to a
    shuffled bucket traversal. The router now samples uniformly from the
    emotion/response-act mapped pool after filtering.
  - Passed the runtime RNG into the store search and logged
    `candidate_selection="uniform_random_within_mapped_bucket"`.
  - Kept Grounded composition strict: GoEmotions and SWDA clauses are still both
    required for Grounded.
  - Added final-surface filters for unrelated or unusable dataset fragments
    observed during smoke samples, including unrelated media/food/sports terms,
    dataset outro phrases, and malformed stock phrases.
  - Recent-use tracking now stores both the full FastTrack text and individual
    semicolon/sentence clauses, so a reused first half of a composed Grounded
    candidate is also treated as recent.
- Verification:
  - `fasttrack_router_v3.py` bytecode compilation passed.
  - `git diff --check` passed for `fasttrack_router_v3.py`.
  - Direct store smoke samples for negative/reject and positive/expressive
    Grounded searches returned unique candidates across repeated calls.
  - Live server/browser validation still requires a server restart.

## 2026-05-28 17:22 KST - Identify and Guard Unknown Post-Donation Voice

- Owner/chat: current CREDO VTuber donation priority pipeline
- User report:
  - After a donation, an unidentified voice plays immediately without the normal
    VTuber subtitle.
- Root cause/interpretation:
  - Runtime logs show `donation_readout_tts` first, then a `live_chat_batch`
    turn can be queued before `/credo/vtuber-mode/donation` queues the actual
    donation answer.
  - The scenario chats are correctly buffered, but the server idle loop could
    consume that buffer during the donation readout window. This makes a chat
    batch voice appear between the donation readout and the donation answer,
    so it feels like an unlabeled extra reaction.
- Fix:
  - Added `donation_priority_until` to VTuber mode state.
  - `/credo/vtuber-mode/donation-readout` now opens a short donation-priority
    guard window based on readout length.
  - The idle loop now skips live-chat batch consumption while the donation
    priority guard is active, preserving the order:
    donation SFX/readout -> donation FastTrack/SlowTrack answer -> buffered
    chat follow-up.
  - Stop/reset clears the donation priority guard.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Active routes contain the new guard and priority check.
  - Python bytecode compilation passed for active routes and
    `apply_integration.py`.
  - Live scenario validation still needs a fresh server restart and browser run.

## 2026-05-28 17:35 KST - Increase Scenario Chat Pace and Shift Overlays Left

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User request:
  - Add about two more internet-style viewers who overuse `lol`, `lmao`, and
    emoji-style reactions.
  - Make scenario chat appear about twice as quickly.
  - Move the donation overlay and speech subtitle left by one-twelfth of the
    screen width.
- Fix:
  - Added recurring internet-style chatters `LOLByte` and `EmojiRush`.
  - Added deterministic `withInternetChatter(...)` timeline expansion: every
    scripted chat gets one extra short meme-style reaction roughly 0.38 seconds
    later, making the scenario chat cadence close to 2x without rewriting the
    donation timings.
  - Updated scenario direction so the LLM knows these two viewers are
    internet-style chatters.
  - Moved `#credo-donation-overlay` left by `8.333vw`.
  - Moved `#credo-speech-subtitle` left by `8.333vw`.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-fast-chat-left-shift`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - Active `frontend/index.html` references the new cache-buster.
  - Python bytecode compilation passed for `apply_integration.py`.
  - `git diff --check` passed for the touched frontend/integration paths.
  - Browser/runtime visual validation was not run in this turn.

## 2026-05-28 17:48 KST - Restore Final Professor Catchphrase

- Owner/chat: current CREDO VTuber SlowTrack speech cleanup
- User request:
  - Restore the English-pronounced `교수진사마!` style phrase at the end of
    VTuber speech.
- Root cause/interpretation:
  - The phrase disappeared because earlier cleanup removed forced romanized
    honorific/catchphrase behavior after the pronunciation was reported as
    awkward.
  - The agent also explicitly stripped `kyoshuzinsama`-style suffixes, so a
    prompt-only change could still be removed by speech cleanup.
- Fix:
  - Added `CREDO_VTUBER_FINAL_CATCHPHRASE`.
  - Set the project default to `Kyo-soo-jin-sama!` for a clearer English TTS
    pronunciation.
  - Added deterministic SlowTrack post-processing that strips duplicate
    catchphrase variants from the tail and appends exactly one
    `Kyo-soo-jin-sama!` at the end of VTuber SlowTrack speech.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime CREDO latency-cover agent files are byte-identical.
  - Python bytecode compilation passed for `config.py` and source/runtime CREDO
    latency-cover agent files.
  - `git diff --check` passed for the touched config/agent paths.
  - Live server/browser validation still requires a server restart.

## 2026-05-28 18:02 KST - Subtitle Position and FastTrack Color Toggle

- Owner/chat: current CREDO VTuber virtual broadcast frontend
- User request:
  - Move the speech subtitle one twenty-fourth of the screen width to the
    right.
  - Add a virtual-broadcast-mode button that can make FastTrack subtitle text
    use the same color as normal subtitles, then turn the highlight back on.
- Fix:
  - Moved `#credo-speech-subtitle` from the previous shifted position by
    `+4.167vw`.
  - Added a `FastTrack Color On/Off` toggle in the virtual broadcast panel.
  - The toggle persists in `localStorage` under
    `credo-vtuber-mode:fasttrackSubtitleHighlight`.
  - When off, the existing subtitle frame is still used, but the FastTrack cyan
    color/glow is overridden to the normal white subtitle style.
  - Updated the frontend cache-buster to
    `credo-vtuber-mode.js?v=20260528-subtitle-highlight-toggle`.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook files are byte-identical.
  - Active `frontend/index.html` references the new cache-buster.
  - Python bytecode compilation passed for `apply_integration.py`.
  - `git diff --check` passed for the touched frontend/integration paths.
  - Browser/runtime visual validation was not run in this turn.

## 2026-05-28 18:19 KST - Quarantine Stray Audio During Donation Priority

- Owner/chat: current CREDO VTuber donation interruption pipeline
- User report:
  - After a donation, a stray utterance still plays before the intended donation
    answer. It may be leftover audio from the interrupted speech.
- Root cause/interpretation:
  - Logs still showed cases where `live_chat_batch` was queued shortly after
    `donation_readout_tts` and before the actual `donation` turn.
  - The server guard window was too short for some donation readout plus HTTP
    donation-answer delay paths, and the frontend only blocked audio while the
    readout flag itself was active.
- Fix:
  - Extended the server donation priority guard to 24-36 seconds based on
    readout length, preventing idle/chat-batch consumption before the donation
    answer has a chance to queue.
  - Added `credo_event` metadata to CREDO audio display payloads.
  - Added a frontend donation audio quarantine:
    - starts as soon as a donation begins;
    - blocks non-donation VTuber audio payloads and non-donation audio element
      playback while the donation answer is pending;
    - clears only when a `credo_event="donation"` audio payload arrives or when
      the donation/reset flow is cancelled.
- Verification:
  - `apply_integration.py --activate` completed successfully.
  - Source/runtime frontend hook and CREDO latency-cover agent files are
    byte-identical.
  - Active routes contain the extended donation priority guard.
  - Python bytecode compilation passed for `apply_integration.py`, active
    routes, and source/runtime CREDO latency-cover agent files.
  - `git diff --check` passed for the touched frontend/agent/integration paths.
  - Live scenario validation still requires a server restart and browser run.

## 2026-05-28 21:45 KST - Defer Parallel and Lock Current Study to Serial

- Owner/chat: current experiment settings/UI cleanup
- 교수님 피드백 반영:
  - 비동기 Parallel scheduling은 좋은 방향이지만 현재 실험에서는 보류.
  - 현재 실험은 Serial 구조와 FastTrack prebuilt audio 조건에 집중.
- 변경 방향:
  - Parallel 관련 코드와 `case_5_grounded_parallel` 식별자는 보존.
  - UI에서는 Case 5와 Parallel factor 버튼을 `Deferred/disabled`로 표시.
  - 기본 scheduling은 `serial`로 정규화.
  - Start Scenario 및 backend factor request는 현재 연구 설정에서
    `scheduling_mode=serial`로 남도록 정리.
  - UI에 active condition 라인을 추가해 현재 run/mapping/scheduling을
    명확히 표시.
- 문서 정리:
  - live usage guide, methodology plan, user study protocol, Open-LLM-VTuber
    integration README에 “parallel은 보류, 현재 실험은 serial 기준”으로 반영.
- 주의:
  - FastTrack prebuilt audio 라우터 구현과 SlowTrack prompt 확장은 다른
    담당 작업으로 유지. 이번 변경은 factor/UI/logging 정리만 다룸.

## 2026-05-28 22:10 KST - Add Survey Metrics to Paper Draft

- Owner/chat: current research writing pass
- User provided survey indicator summary image for the AI VTuber FastTrack
  experiment.
- Updated:
  - `AI_NPC_System/reports/credo_paper_draft_without_results.md`
  - `AI_NPC_System/docs/research_methodology_experiment_plan.md`
- Added measurement structure:
  - 7-point Likert ratings after each video.
  - Final comparison questions after all videos.
  - Six constructs: Perceived Latency, Reaction Appropriateness,
    Conversational Naturalness, Social Presence, Engagement, Character Appeal.
  - q1-q14 item mapping plus q15-q17 final comparison questions.
  - Reverse-coded items: q3 and q7.
  - Interpretation anchors:
    - Grounded FastTrack: q6-q8, q15, q17.
    - Prebuilt FastTrack latency-cover: q1-q3 plus browser first-audio timing.
    - SlowTrack-only limitation: low perceived latency and q16 selection.
    - Parallel scheduling remains follow-up/deferred, not primary analysis.
- Verification:
  - `git diff --check` passed for the updated paper/methodology documents.

## 2026-05-28 22:11 KST - Current Handoff: Serial-Only Experiment UI State

- Owner/chat: current experiment settings/UI cleanup
- Current active experiment policy:
  - Parallel scheduling is deferred for the current professor-facing study.
  - Scenario recordings should use `scheduling_mode=serial`.
  - FastTrack prebuilt audio work is owned by another chat; do not refactor that
    router/build pipeline from this cleanup task.
  - SlowTrack prompt expansion is also owned by another chat.
- Implemented in this cleanup pass:
  - Frontend default scheduling now normalizes to `serial`.
  - `case_5_grounded_parallel` remains in the preset list but is disabled and
    labeled `Deferred`.
  - The manual `Parallel` architecture button remains visible but disabled and
    labeled `Parallel · Deferred`.
  - UI active-condition line shows the current run/mapping/scheduling state,
    including `scheduling_mode=serial`.
  - Backend route patch normalizes incoming `scheduling_mode=parallel` requests
    to `serial` and returns/logs `parallel_deferred=true`.
  - `apply_integration.py --activate` was run, and source/vendor
    `credo-vtuber-mode.js` are byte-identical.
- Verification completed:
  - Python compile passed for `apply_integration.py` and active
    `vendor/open-llm-vtuber/src/open_llm_vtuber/routes.py`.
  - `git diff --check` passed for the touched frontend, integration, docs, and
    shared worklog files.
  - Browser/runtime validation was not run because the user had just requested
    all servers be stopped.
- Important workspace note:
  - The worktree also contains unrelated/parallel changes from other chats
    around FastTrack prebuilt assets, memory, persona/prompt docs, and paper
    drafting. Do not revert those. This cleanup only owns experiment
    factor/UI/backend mapping/docs handoff.

## 2026-05-28 22:36 KST - Rename Scenario Viewer To ElonMuscuba

- Owner/chat: current virtual broadcast scenario cleanup
- User/professor request:
  - Remove the previous first-donor viewer name from the experiment scenario.
  - Replace it with the English nickname `ElonMuscuba`.
- Implemented:
  - Updated the fixed audience list in the virtual broadcast scenario direction.
  - Updated the first donation author at T+3.0s.
  - Updated all recurring chat entries that previously used the old viewer name.
  - Ran `apply_integration.py --activate` so the active vendor frontend matches
    the source frontend hook.
- Verification:
  - Search over `AI_NPC_System`, `CODEX_SHARED_WORKLOG.md`, top-level handoff
    docs, and `vendor/open-llm-vtuber/frontend` returns no matches for the old
    viewer name.
  - Source and vendor frontend scenario entries now use `ElonMuscuba`.

## 2026-05-28 23:07 KST - FastTrack Prebuilt Audio Tail Fix And Runtime Mapping

- Owner/chat: FastTrack prebuilt audio/runtime mapping pass.
- User issue:
  - Generated FastTrack wav files sounded bad at the end.
  - The tail was clipped or stopped abruptly, and some lines sounded like they
    did not finish the text.
- Root cause/fix:
  - Removed the StyleBERT wav post-processing that trimmed the final 80ms.
  - Kept manifest/subtitle text clean, but padded only the TTS request text with
    3 leading/trailing spaces.
  - Added terminal punctuation for TTS requests when the source text has no
    strong sentence ending.
  - Added 450ms of physical trailing silence to generated wav files.
- Audio bundle result:
  - Rebuilt `AI_NPC_System/fasttrack_assets/audio/prebuilt_stylebert_v1/`.
  - `manifest.json` contains 2,180 items.
  - Generation failures: 0.
  - Source distribution: `go_emotions=1131`, `swda=1049`.
  - Sample wav checks confirmed the last 450ms is silence.
- Runtime behavior:
  - FastTrack still selects text from the existing filtered GoEmotions/SWDA
    pool; the datasets were not merged into a new text source.
  - Selected text is mapped to the matching prebuilt wav from the manifest.
  - When both emotion and intent are used, playback order is emotion segment
    first, then intent segment.
  - FastTrack does not fall back to realtime StyleBERT TTS when a wav is
    missing; the miss is logged instead.
  - Subtitles/transcripts use the original unpadded segment text.
- Files touched in this pass:
  - `AI_NPC_System/stylebert_vits2_client.py`
  - `AI_NPC_System/config.py`
  - `AI_NPC_System/scripts/build_fasttrack_stylebert_prebuilt_bundle.py`
  - `AI_NPC_System/scripts/validate_fasttrack_stylebert_prebuilt_bundle.py`
  - `AI_NPC_System/fasttrack_router_v3.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/credo_latency_cover_agent.py`
  - `AI_NPC_System/scripts/smoke_fasttrack_prebuilt_runtime.py`
  - `AI_NPC_System/integrations/open_llm_vtuber/apply_integration.py` was run
    so the vendor runtime copy is updated.
- Verification completed:
  - Manifest validation passed for 2,180 items.
  - Wav path existence, empty/incomplete text checks, and distribution reporting
    passed.
  - FastTrack smoke test passed for 3 inputs.
  - Missing wav test confirmed no fallback TTS is used.
  - Serial order guard passed; parallel scheduling remains deferred.
  - Python compile passed for touched source/runtime scripts and vendor copy.
- Important constraints:
  - VoiceSample and final StyleBERT model assets were not modified.
  - SlowTrack TTS behavior was left unchanged.

## 2026-05-29 14:36 KST - Paper Latency Sensitivity Dataset

- Owner/chat: quantitative latency simulation for paper reporting.
- User request:
  - Move beyond rough estimates and generate academically usable quantitative
    latency data under varied conditions.
  - Record all module latencies so the results can support paper analysis.
- Implemented:
  - Added `AI_NPC_System/scripts/simulate_latency_sensitivity_study.py`.
  - Used recorded module log
    `AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`.
  - Used the clean window at/after `2026-05-29T03:36:00+09:00`.
  - Simulated 120 explicit conditions:
    - 5 FastTrack policies: grounded, emotion_only, response_act_only,
      neutral_random, slowtrack_only.
    - 4 SlowTrack load profiles: current_prompt, expanded_memory,
      heavy_context, stress_context.
    - 3 frontend profiles: backend_ready, local_browser, capture_stress.
    - 2 scenario profiles: chat_only, donation_mix.
  - Ran 500 repetitions per condition and 8 turns per repetition.
- Generated dataset:
  - Output folder:
    `AI_NPC_System/reports/latency_sensitivity_study_20260529/`
  - `simulated_turns_wide.csv`: 480,000 simulated turn rows, one row per turn,
    with all module latency columns.
  - `condition_summary.csv`: 120 condition summaries.
  - `module_summary.csv`: module-level summaries by condition.
  - `assumptions.json`: factor definitions and simulation assumptions.
  - `summary.md`: short paper-ready summary and caveat wording.
- Headline values:
  - Current prompt / local browser / donation mix:
    FastTrack median first response 76.0 ms vs SlowTrack-only 2330.6 ms.
  - Heavy context / local browser / donation mix:
    FastTrack median first response 76.5 ms vs SlowTrack-only 4597.7 ms.
  - Stress context / capture stress / donation mix:
    FastTrack median first response 195.4 ms vs SlowTrack-only 6318.7 ms.
- Paper caveat:
  - Describe this as an empirical bootstrap sensitivity simulation from
    recorded module logs.
  - Do not describe it as a participant result or browser audible-onset result.

## 2026-05-29 14:52 KST - Reports Folder Cleanup

- Owner/chat: reports cleanup for current research form.
- User request:
  - Keep only the latest research-facing reports.
  - Delete old reports and no-longer-useful report folders.
- Removed:
  - Intermediate FastTrack LLM/filter report folders from the 2026-05-29
    filtering passes.
  - Older latency benchmark, raw-data package, and first simulation report
    folders now superseded by `latency_sensitivity_study_20260529`.
  - Obsolete six-factor status, interjection bundle report, and old
    StyleBERT voice report folders.
  - Superseded `latency_prediction_model.*` files.
- Kept:
  - Current paper draft.
  - Latest latency sensitivity study dataset and Korean explanation report.
  - Latest FastTrack dataset validation and runtime readiness summaries.
  - SWDA intent transition matrix, SetFit intent evaluation, and user-study
    response template.
- Added:
  - `AI_NPC_System/reports/README.md` documenting the remaining report files
    and cleanup policy.
- Scope:
  - Runtime code, source logs, model assets, VoiceSample data, and FastTrack
    audio assets were not touched by this cleanup.

## 2026-05-29 15:58 KST - Survey Statistics And Result Interpretation

- Owner/chat: survey/paper result review.
- Inputs:
  - Survey CSV:
    `C:/Users/CGLAB/Desktop/결과 분석/[CGLab] AI-based V-tuber 기반 응답생성에 대한 설문.csv`
  - Paper draft:
    `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문_초안.doc`
  - Existing latency sensitivity report:
    `AI_NPC_System/reports/latency_sensitivity_study_20260529/`
- Important correction:
  - User clarified that the displayed video order was `case 3-1-5-2-4`.
  - CSV blocks were remapped as:
    1. Intent Only
    2. Grounded
    3. SlowTrack Only
    4. Emotion Only
    5. Neutral Random
- Analysis produced:
  - `AI_NPC_System/reports/survey_analysis_20260529/survey_statistical_report_ko.md`
  - `survey_long_scores_case_order_31524.csv`
  - condition summaries for all respondents and English-exposure filtered
    subsets.
  - paired t-tests against SlowTrack Only.
  - Cronbach alpha reliability tables.
  - final-choice count summaries.
- Key interpretation:
  - Grounded has the strongest perceived latency tendency.
  - Emotion Only has the strongest overall/naturalness tendency in this sample.
  - Intent Only is strong in final-choice context appropriateness and supports
    response-act mapping value.
  - SlowTrack Only is most often selected as awkward/uncomfortable.
  - The result should be framed as exploratory user-evaluation evidence, not as
    a dominant/significant win across all indicators.

## 2026-05-29 16:18 KST - Reference-Guided Results Section Draft

- Owner/chat: paper results writing pass.
- User request:
  - Check how referenced papers report results and statistical reliability.
  - Draft the experiment results section in a style compatible with those
    references.
- Implemented:
  - Reviewed result-writing patterns from latency/filler, ECA, chatbot, and
    VTuber-related references.
  - Added nonparametric omnibus checks for the within-subject Likert data:
    Friedman tests and Kendall's W.
  - Added Wilcoxon signed-rank robustness outputs against SlowTrack Only.
  - Created:
    - `AI_NPC_System/reports/survey_analysis_20260529/reference_guided_results_method_review.md`
    - `AI_NPC_System/reports/survey_analysis_20260529/paper_results_section_draft.md`
    - `friedman_tests_all_n27.csv`
    - `wilcoxon_vs_slowtrack_all_n27.csv`
    - `condition_summary_all_n27_m_sd_table.csv`
- Key statistical update:
  - Most Friedman omnibus tests are not significant, except Character Appeal
    (`chi-square(4)=12.21`, `p=.016`, `W=.113`).
  - Grounded perceived-latency advantage over SlowTrack Only remains an
    exploratory planned-comparison tendency, not a corrected omnibus-confirmed
    result.
  - Results section now frames findings as converging exploratory evidence:
    latency simulation + preference counts + selected planned comparisons.

## 2026-05-29 17:23 KST - Survey Analysis Updated To N=31

- Owner/chat: latest survey result refresh.
- Input:
  - `C:/Users/CGLAB/Desktop/결과 분석/[CGLab] AI-based V-tuber 기반 응답생성에 대한 설문.csv (1).zip`
- Analysis:
  - Added reusable script `AI_NPC_System/scripts/analyze_credo_survey.py`.
  - Re-ran survey analysis with corrected video order `case 3-1-5-2-4`.
  - New sample size: `n=31`.
  - English-exposure filtered samples:
    - English >= 4: `n=19`
    - English >= 5: `n=17`
- Output folder:
  - `AI_NPC_System/reports/survey_analysis_20260529_n31/`
  - Desktop copies were updated in `C:/Users/CGLAB/Desktop/결과 분석/`.
- Key updates:
  - Grounded is now the highest overall mean condition (`M=4.98`) and highest
    Perceived Latency condition (`M=5.46`).
  - Perceived Latency: Grounded vs SlowTrack Only is now significant after Holm
    correction (`mean diff=0.742`, `t(30)=2.906`, `p=.0068`,
    `p_holm=.0272`, `dz=.522`).
  - Intent Only has the highest forced-choice context reaction count
    (`22/31`) and best-flow count (`21/31`).
  - SlowTrack Only remains most often selected as awkward/uncomfortable
    (`13/31`).
  - Most Friedman omnibus tests remain non-significant except Character Appeal,
    so conclusions should still be framed as exploratory/converging evidence
    rather than broad dominance across all constructs.

## 2026-05-29 18:55 KST - Survey Analysis Updated To N=32 + Length-Binned Performance Tables

- Owner/chat: latest survey result refresh and paper performance-metrics pass.
- Input:
  - `C:/Users/CGLAB/Desktop/결과 분석/[CGLab] AI-based V-tuber 기반 응답생성에 대한 설문.csv`
- Survey analysis:
  - Re-ran `AI_NPC_System/scripts/analyze_credo_survey.py` with corrected video
    order `case 3-1-5-2-4`.
  - New sample size: `n=32`.
  - English-exposure filtered samples:
    - English >= 4: `n=19`
    - English >= 5: `n=17`
  - Output folder:
    - `AI_NPC_System/reports/survey_analysis_20260529_n32/`
  - Desktop copies updated in:
    - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_설문_통계_분석_보고서.md`
    - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문_결과파트_초안_ko.md`
- Key statistical results:
  - Main result is stable versus `n=31`; the added participant did not change
    the interpretation.
  - Grounded Perceived Latency vs SlowTrack Only became slightly stronger:
    `mean diff=0.760`, `t(31)=3.068`, `p=.00445`,
    `p_holm=.01779`, `dz=.542`.
  - Character Appeal: Emotion Only vs SlowTrack Only is Holm-significant:
    `mean diff=0.578`, `t(31)=2.713`, `p=.0108`,
    `p_holm=.0432`, `dz=.480`.
  - Engagement: Grounded vs SlowTrack Only is Holm-significant:
    `mean diff=0.672`, `t(31)=2.760`, `p=.00963`,
    `p_holm=.0385`, `dz=.488`.
  - Friedman omnibus remains mostly non-significant except Character Appeal:
    `chi-square(4)=13.64`, `p=.00855`, `W=.107`.
- Performance table request:
  - Used `AI_NPC_System/latency_logs/paper_latency_20260529_000308.module_events.csv`.
  - Used only stable paper-log window after `2026-05-29T03:36:00+09:00`
    to avoid earlier server-restart/debug contamination.
  - Generated length-binned module latency tables:
    - `AI_NPC_System/reports/performance_metrics_20260529_n32/slowtrack_latency_by_output_length.csv`
    - `AI_NPC_System/reports/performance_metrics_20260529_n32/fasttrack_latency_by_input_length.csv`
    - `AI_NPC_System/reports/performance_metrics_20260529_n32/performance_metrics_report_ko.md`
  - Paper-section drafts:
    - `AI_NPC_System/reports/paper_sections_20260529_n32/paper_results_pvalue_focused_ko.md`
    - `AI_NPC_System/reports/paper_sections_20260529_n32/paper_performance_metrics_section_ko.md`
  - Desktop copies:
    - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_성능지표_파트_초안_ko.md`
    - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_SlowTrack_길이구간별_성능표.csv`
    - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_FastTrack_길이구간별_성능표.csv`
- Performance highlights:
  - SlowTrack 200-500 output chars: LLM mean `1474.9 ms`,
    TTS mean `825.4 ms`, combined mean `2300.3 ms`.
  - FastTrack 500-1000 input chars: total mean `17.3 ms`.
  - SlowTrack 10-100 and 500-1000 output-char bins have no stable-log
    observations; no estimated values were inserted.

## 2026-05-29 19:20 KST - Survey Analysis Updated To N=33 And Report Cleanup

- Owner/chat: latest survey result refresh and document cleanup.
- Input:
  - `C:/Users/CGLAB/Desktop/결과 분석/[CGLab] AI-based V-tuber 기반 응답생성에 대한 설문.csv`
- Survey analysis:
  - Re-ran `AI_NPC_System/scripts/analyze_credo_survey.py` with corrected video
    order `case 3-1-5-2-4`.
  - New sample size: `n=33`.
  - English-exposure filtered samples:
    - English >= 4: `n=19`
    - English >= 5: `n=17`
  - Output folders now kept:
    - `AI_NPC_System/reports/survey_analysis_20260529_n33/`
    - `AI_NPC_System/reports/paper_sections_20260529_n33/`
    - `AI_NPC_System/reports/performance_metrics_20260529_final/`
- Key statistical results:
  - Core interpretation remains stable versus `n=32`.
  - Grounded Perceived Latency vs SlowTrack Only remains Holm-significant:
    `mean diff=0.717`, `t(32)=2.938`, `p=.00608`,
    `p_holm=.0243`, `dz=.511`.
  - Grounded Engagement vs SlowTrack Only remains Holm-significant:
    `mean diff=0.652`, `t(32)=2.751`, `p=.00971`,
    `p_holm=.0388`, `dz=.479`.
  - Emotion Only Character Appeal vs SlowTrack Only is now only a borderline
    exploratory result after correction:
    `mean diff=0.545`, `t(32)=2.608`, `p=.0137`,
    `p_holm=.0549`, `dz=.454`.
  - Friedman omnibus remains significant only for Character Appeal:
    `chi-square(4)=14.06`, `p=.00710`, `W=.107`.
- Desktop report cleanup:
  - Kept current latest files only in `C:/Users/CGLAB/Desktop/결과 분석/`:
    - raw survey CSV
    - `CREDO_논문_초안.doc`
    - `CREDO_설문_통계_분석_보고서.md`
    - `CREDO_논문_결과파트_초안_ko.md`
    - `CREDO_성능지표_파트_초안_ko.md`
    - `CREDO_논문용_CSV_표모음_n33/`
    - professor-facing simple CSVs:
      `CREDO_SlowTrack_직관형_mean_ms.csv`,
      `CREDO_FastTrack_직관형_mean_ms.csv`,
      `CREDO_논문용_핵심요약표_n33.csv`
  - Removed old n32 desktop report copies and old n32 CSV bundle.
  - Removed old generated repo report folders for n31/n32 and kept n33/final
    report folders.

## 2026-05-29 19:56 KST - Final Survey Basis Reverted To N=32

- Owner/chat: paper results final-basis adjustment.
- User decision:
  - Use `n=32` as the final analysis basis.
  - The latest raw CSV still contains 33 responses, but the current reports use
    the first 32 responses and exclude the last-added response.
- Rebuilt:
  - `AI_NPC_System/reports/survey_analysis_20260529_n32/`
  - `AI_NPC_System/reports/paper_sections_20260529_n32/`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문용_CSV_표모음_n32/`
- Current desktop report files now point to n=32:
  - `CREDO_설문_통계_분석_보고서.md`
  - `CREDO_논문_결과파트_초안_ko.md`
  - `CREDO_성능지표_파트_초안_ko.md`
  - `CREDO_논문용_핵심요약표_n32.csv`
  - `CREDO_SlowTrack_직관형_mean_ms.csv`
  - `CREDO_FastTrack_직관형_mean_ms.csv`
- Final n=32 core results:
  - Grounded Perceived Latency vs SlowTrack Only:
    `mean diff=0.760`, `t(31)=3.068`, `p=.00445`,
    `p_holm=.01779`, `dz=.542`.
  - Grounded Engagement vs SlowTrack Only:
    `mean diff=0.672`, `t(31)=2.760`, `p=.00963`,
    `p_holm=.0385`, `dz=.488`.
  - Emotion Only Character Appeal vs SlowTrack Only:
    `mean diff=0.578`, `t(31)=2.713`, `p=.0108`,
    `p_holm=.0432`, `dz=.480`.
- Cleanup:
  - Removed current n33 report folders and desktop n33 CSV bundle.
  - Removed redundant root-level n32-named duplicates because the current
    non-suffixed desktop report files already contain the n=32 analysis.
  - Kept supplemental SlowTrack length-benchmark files because they may help
    fill missing performance-table bins if needed.

## 2026-05-29 20:20 KST - FastTrack/SlowTrack Latency Tables Rebuilt

- Owner/chat: performance-table/report correction.
- User correction:
  - FastTrack must be measured by actual processing stages, not as a single
    router aggregate.
  - Required stages: DistilBERT/GoEmotions emotion classification, SWDA SetFit
    intent classification, SWDA response-act transition, and prebuilt audio
    matching.
- Added benchmark scripts:
  - `AI_NPC_System/scripts/benchmark_slowtrack_length_bins.py`
  - `AI_NPC_System/scripts/benchmark_fasttrack_length_bins.py`
- Rebuilt SlowTrack missing bins with 30 trials per length bin.
  - Current SlowTrack totals:
    - 10-100 chars: 705.7 ms
    - 100-200 chars: 1119.3 ms
    - 200-500 chars: 2089.9 ms
    - 500-1000 chars: 4120.6 ms
- Rebuilt FastTrack with actual model stages using the Open-LLM-VTuber venv.
  - Emotion backend: `distilbert_goemotions`
  - Intent backend: `setfit_swda`
  - Current FastTrack totals:
    - 10-100 chars: 36.7 ms
    - 100-200 chars: 36.4 ms
    - 200-500 chars: 44.0 ms
    - 500-1000 chars: 53.9 ms
- Important implementation finding:
  - With the actual model probabilities and current `threshold=0.6`,
    `n_routeable_by_threshold=0/120` in this benchmark set.
  - This means the latency advantage is measurable, but production use of the
    actual DistilBERT/SetFit route needs threshold calibration, score
    normalization, or separate model-specific thresholds.
- Updated desktop output files:
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_FastTrack_직관형_mean_ms.csv`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_SlowTrack_직관형_mean_ms.csv`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_FastTrack_SlowTrack_직관형_mean_ms_통합.csv`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_FastTrack_vs_SlowTrack_성능비교_요약.csv`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_FastTrack_SlowTrack_성능측정_통합보고서_20260529.md`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_성능지표_파트_초안_ko.md`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문_결과파트_초안_ko.md`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문용_CSV_표모음_n32/11_FastTrack_입력길이별_모듈지연시간_상세.csv`
  - `C:/Users/CGLAB/Desktop/결과 분석/CREDO_논문용_CSV_표모음_n32/13_FastTrack_turn별_raw_합계.csv`

## 2026-05-29 20:29 KST - Presentation Latency Tables Cleaned

- User asked to remove currently unused/confusing fields from the tables.
- Cleaned professor/paper-facing FastTrack tables to keep only the active
  conceptual path:
  - DistilBERT/GoEmotions emotion classification
  - SWDA SetFit intent classification
  - SWDA response-act transition
  - dataset text lookup
  - prebuilt StyleBERT wav manifest matching
  - prebuilt audio matching total
  - overall total
- Removed from presentation tables:
  - `n_routeable_by_threshold`
  - keyword/spaCy extraction
  - parallel classifier critical-path column
  - audio path verification diagnostic
- Raw benchmark CSV still retains diagnostics for traceability:
  `C:/Users/CGLAB/Desktop/결과 분석/fasttrack_length_benchmark_20260529/fasttrack_length_bin_raw.csv`.
