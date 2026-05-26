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
