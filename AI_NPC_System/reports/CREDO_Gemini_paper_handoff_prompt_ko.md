# CREDO Gemini 논문 작성 공유 프롬프트

아래 프롬프트를 Gemini에 그대로 붙여넣고, 같은 폴더의 자료를 함께 업로드한다.

## Gemini 입력 프롬프트

```text
너는 HCI/AI 에이전트/가상 캐릭터 상호작용 논문 작성 보조자다.
아래 제공 자료를 바탕으로 CREDO 프로젝트 논문 작성을 도와줘.

중요 제약:
1. 최종 설문 분석 기준은 n=32이다.
   원본 CSV에는 33번째 응답이 있을 수 있지만, 본 논문 결과는 첫 32명 기준으로 고정한다.
2. 통계값, p값, 평균, 표준편차, 지연시간 수치는 제공된 표의 값만 사용한다.
   수치를 임의로 재계산하거나 바꾸지 마라.
3. paired t-test 표기는 n=32이므로 t(31)로 쓰는 것이 맞다.
4. 결과를 과장하지 마라.
   대부분의 omnibus Friedman test는 유의하지 않으므로,
   핵심 주장은 planned comparison과 성능 지표의 수렴 근거로 제한한다.
5. FastTrack의 핵심 주장은 "SlowTrack의 계산 시간을 제거한다"가 아니라
   "초기 무응답 구간을 짧은 반응으로 완화한다"이다.
6. 논문 문체는 한국어 학술 논문 스타일로 작성하되, 필요한 기술 용어는 영어 병기를 허용한다.
7. 개인정보가 들어갈 수 있는 원본 응답 내용은 사용하지 말고, 집계 표와 보고서만 사용한다.

프로젝트 요약:
- CREDO는 AI VTuber 상호작용에서 LLM 및 TTS로 인한 응답 지연을 완화하기 위한 dual-track response generation pipeline이다.
- 시스템은 두 경로로 나뉜다.
  1. FastTrack: 사용자 입력 직후 감정/대화행위 기반의 짧은 반응을 검색하여 즉시 출력한다.
  2. SlowTrack: 페르소나, 메모리, 방송 맥락을 포함한 프롬프트를 구성하고 Local LLM과 TTS로 본문 응답을 생성한다.
- 두 출력은 순차적으로 조정되어 FastTrack 반응이 먼저 나오고 SlowTrack 본문 응답이 이어진다.
- 실험 조건은 다음과 같다.
  - Grounded: 감정 + SWDA response-act 정보를 모두 사용한 FastTrack
  - Emotion Only: 감정 정보만 사용한 FastTrack
  - Intent Only: SWDA response-act 정보만 사용한 FastTrack
  - Neutral Random: 맥락 정보 없이 중립/무작위에 가까운 FastTrack
  - SlowTrack Only: FastTrack 없이 본문 응답만 출력하는 대조군

설문 설계:
- within-subject 설계
- 참가자 수: n=32
- 영상 제시 순서는 실제 case 번호와 달라 case 3-1-5-2-4로 재매핑되었다.
- 7점 Likert 척도 사용
- 주요 지표:
  - Perceived Latency
  - Reaction Appropriateness
  - Conversational Naturalness
  - Social Presence
  - Engagement
  - Character Appeal
- 일부 부정 문항은 점수가 높을수록 긍정적 의미가 되도록 역코딩되었다.

핵심 결과:
1. Grounded는 SlowTrack Only보다 Perceived Latency가 유의하게 높았다.
   mean diff=0.760, t(31)=3.068, p=.00445, Holm p=.01779, dz=.542.
   이는 Grounded FastTrack이 체감 지연 시간을 완화했다는 핵심 근거다.
2. Grounded는 Engagement에서도 SlowTrack Only보다 유의하게 높았다.
   mean diff=0.672, t(31)=2.760, p=.00963, Holm p=.0385, dz=.488.
3. Emotion Only는 Character Appeal에서 SlowTrack Only보다 유의하게 높았다.
   mean diff=0.578, t(31)=2.713, p=.0108, Holm p=.0432, dz=.480.
4. Friedman omnibus test는 대부분 유의하지 않으며, Character Appeal만 유의하다.
   따라서 "모든 조건에서 전면적 우수성"이라고 쓰면 안 된다.
5. 최종 선택 문항에서는 Intent Only와 Grounded가 대화 흐름/맥락 적합성에서 높은 선택을 받았고,
   SlowTrack Only는 가장 어색하거나 불편한 조건으로 가장 많이 선택되었다.

성능 결과:
- 최신 성능표는 `CREDO_FastTrack_SlowTrack_직관형_mean_ms_통합.csv`와
  `CREDO_FastTrack_vs_SlowTrack_성능비교_요약.csv`를 기준으로 사용한다.
- 길이 구간별로 FastTrack과 SlowTrack의 mean_ms를 비교한다.
- FastTrack은 감정 분석, 의도 분석, response-act transition, 텍스트 조회, prebuilt audio match를 포함한다.
- SlowTrack은 LLM 생성과 TTS 합성을 포함한다.
- 성능 해석은 FastTrack이 SlowTrack보다 매우 짧은 초기 반응 경로를 제공한다는 점에 초점을 둔다.

Gemini에게 요청하는 작업:
1. 위 내용을 바탕으로 논문 초안의 결과 파트와 성능지표 파트를 더 학술적으로 다듬어줘.
2. 연구 질문/가설, 방법론, 시스템 파이프라인 설명, 실험 설계, 결과 해석, 한계점, 향후 연구를 논문 문체로 정리해줘.
3. 통계 결과는 p값이 의미 있는 결과 중심으로 쓰되, 유의하지 않은 omnibus 결과도 정직하게 언급해줘.
4. FastTrack의 기여를 "지연시간 자체 제거"가 아니라 "인지적 초기 공백 완화"로 표현해줘.
5. Figure caption과 Table caption도 제안해줘.
6. 제공 자료 사이에 수치 충돌이 있으면, 최신 통합 성능표와 n=32 설문 분석을 우선하고, 충돌 사항을 명시해줘.
```

## Gemini에 업로드할 추천 자료

1. `CREDO_논문_초안.doc`
   - 기존 논문 초안.
2. `CREDO_논문_결과파트_초안_ko.md`
   - n=32 기준 결과 파트 초안.
3. `CREDO_성능지표_파트_초안_ko.md`
   - 성능지표 파트 초안.
4. `CREDO_설문_통계_분석_보고서.md`
   - 전체 설문 통계 보고서.
5. `CREDO_논문용_CSV_표모음_n32/00_p값_중심_핵심결과_전체_n32.csv`
   - p값 중심 핵심 통계표.
6. `CREDO_논문용_CSV_표모음_n32/01_조건별_평균_표_M_SD_n32.csv`
   - 조건별 평균/표준편차.
7. `CREDO_논문용_CSV_표모음_n32/03_SlowTrack대비_paired_ttest_전체_n32.csv`
   - paired t-test 전체표.
8. `CREDO_논문용_CSV_표모음_n32/05_Friedman_omnibus_검정_n32.csv`
   - Friedman omnibus 검정.
9. `CREDO_논문용_CSV_표모음_n32/07_Cronbach_alpha_신뢰도_n32.csv`
   - 신뢰도 분석.
10. `CREDO_논문용_CSV_표모음_n32/08_최종선택문항_전체_n32.csv`
   - 최종 선택 문항.
11. `CREDO_FastTrack_SlowTrack_직관형_mean_ms_통합.csv`
   - 최신 FastTrack/SlowTrack 길이 구간별 성능표.
12. `CREDO_FastTrack_vs_SlowTrack_성능비교_요약.csv`
   - 성능 비교 요약.
13. `ChatGPT Image 2026년 5월 29일 오후 08_34_20.png`
   - 논문용 파이프라인 Figure 후보.

## 업로드하지 않는 것을 권장하는 자료

- 원본 설문 CSV: 개인정보 또는 원자료 식별 가능성이 있으므로 Gemini에는 우선 업로드하지 않는 것을 권장한다.
- `before_*`, `*.before_*`, 이전 n31/n33 산출물: 현재 최종 기준과 혼동될 수 있다.
- 개발 로그 전체: 논문 작성에는 집계 결과와 방법론 설명만 사용한다.
