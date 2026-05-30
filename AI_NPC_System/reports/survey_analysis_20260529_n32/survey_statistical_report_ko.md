# CREDO 설문 및 정량 레이턴시 결과 검토 보고서 (n32)

## 1. 분석 전제

- 설문 응답자 수: 32명.
- 설문은 5개 영상을 모두 평가한 within-subject 구조로 분석했다.
- 실제 영상 순서는 `case 3-1-5-2-4`로 반영했다.
- 부정 문항인 침묵/공백 답답함, 무작위 반응 지각 문항은 역코딩했다.
- SlowTrack Only를 기준으로 paired t-test를 수행했고, 같은 지표 내 4개 비교에는 Holm 보정값을 함께 제공했다.

## 2. 전체 응답자 조건별 평균

| case_no | condition | n | Overall_mean | Perceived Latency_mean | Reaction Appropriateness_mean | Conversational Naturalness_mean | Social Presence_mean | Character Appeal_mean | Engagement_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Grounded | 32 | 4.95 | 5.47 | 4.83 | 4.75 | 5.3 | 4.44 | 4.72 |
| 2 | Emotion Only | 32 | 4.91 | 5.24 | 4.79 | 4.84 | 5.27 | 4.67 | 4.53 |
| 3 | Intent Only | 32 | 4.81 | 5.26 | 4.93 | 4.58 | 5.31 | 4.05 | 4.45 |
| 4 | Neutral Random | 32 | 4.69 | 5.12 | 4.73 | 4.3 | 4.86 | 4.56 | 4.33 |
| 5 | SlowTrack Only | 32 | 4.48 | 4.71 | 4.74 | 4.25 | 4.78 | 4.09 | 4.05 |

### 해석

- 전체 평균이 가장 높은 조건은 Case 1 `Grounded`이며 평균은 4.95점이다.
- Perceived Latency가 가장 높은 조건은 Case 1 `Grounded`이며 평균은 5.47점이다.
- Conversational Naturalness가 가장 높은 조건은 Case 2 `Emotion Only`이며 평균은 4.84점이다.

## 3. 영어 콘텐츠 저시청자 제외 결과

- 영어 콘텐츠 시청 빈도 1-3점을 저시청자로 보고 제외했다.
- 영어 콘텐츠 시청 빈도 4점 이상 응답자 기준 결과는 다음과 같다.

| case_no | condition | n | Overall_mean | Perceived Latency_mean | Reaction Appropriateness_mean | Conversational Naturalness_mean | Social Presence_mean | Character Appeal_mean | Engagement_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Grounded | 19 | 4.65 | 5.19 | 4.61 | 4.42 | 4.92 | 4.11 | 4.39 |
| 2 | Emotion Only | 19 | 5.04 | 5.28 | 4.86 | 5.11 | 5.45 | 4.74 | 4.79 |
| 3 | Intent Only | 19 | 4.76 | 5.16 | 4.89 | 4.53 | 5.32 | 3.87 | 4.5 |
| 4 | Neutral Random | 19 | 4.64 | 5.04 | 4.68 | 4.18 | 4.82 | 4.61 | 4.26 |
| 5 | SlowTrack Only | 19 | 4.33 | 4.42 | 4.81 | 4.03 | 4.74 | 3.89 | 3.84 |

- 더 강한 필터인 영어 콘텐츠 시청 빈도 5점 이상 응답자 기준 결과는 다음과 같다.

| case_no | condition | n | Overall_mean | Perceived Latency_mean | Reaction Appropriateness_mean | Conversational Naturalness_mean | Social Presence_mean | Character Appeal_mean | Engagement_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Grounded | 17 | 4.68 | 5.25 | 4.65 | 4.5 | 4.94 | 4.09 | 4.41 |
| 2 | Emotion Only | 17 | 5.06 | 5.33 | 4.82 | 5.21 | 5.5 | 4.68 | 4.79 |
| 3 | Intent Only | 17 | 4.79 | 5.22 | 4.92 | 4.59 | 5.29 | 3.82 | 4.59 |
| 4 | Neutral Random | 17 | 4.62 | 5 | 4.67 | 4.15 | 4.82 | 4.62 | 4.26 |
| 5 | SlowTrack Only | 17 | 4.37 | 4.37 | 4.9 | 4.06 | 4.88 | 3.88 | 3.82 |

## 4. 최종 선택 문항 결과

### 전체 응답자

| case_no | condition | n | best_flow_yes | most_uncomfortable_yes | best_context_reaction_yes |
| --- | --- | --- | --- | --- | --- |
| 1 | Grounded | 32 | 20 | 10 | 21 |
| 2 | Emotion Only | 32 | 18 | 6 | 17 |
| 3 | Intent Only | 32 | 22 | 8 | 23 |
| 4 | Neutral Random | 32 | 14 | 6 | 14 |
| 5 | SlowTrack Only | 32 | 12 | 14 | 15 |

### 영어 콘텐츠 4점 이상 응답자

| case_no | condition | n | best_flow_yes | most_uncomfortable_yes | best_context_reaction_yes |
| --- | --- | --- | --- | --- | --- |
| 1 | Grounded | 19 | 10 | 8 | 10 |
| 2 | Emotion Only | 19 | 11 | 3 | 11 |
| 3 | Intent Only | 19 | 13 | 4 | 14 |
| 4 | Neutral Random | 19 | 9 | 3 | 10 |
| 5 | SlowTrack Only | 19 | 6 | 10 | 7 |

## 5. SlowTrack Only 대비 paired t-test

아래 표의 mean_diff는 `각 FastTrack 조건 - SlowTrack Only`이다. 양수이면 SlowTrack Only보다 해당 조건이 높게 평가되었다는 뜻이다.

### Overall

| comparison | n | mean_diff | t | df | p_two_tailed | p_holm_within_metric | cohen_dz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded - SlowTrack Only | 32 | 0.473 | 2.291 | 31 | 0.029 | 0.087 | 0.405 |
| Emotion Only - SlowTrack Only | 32 | 0.431 | 2.606 | 31 | 0.014 | 0.056 | 0.461 |
| Intent Only - SlowTrack Only | 32 | 0.333 | 1.757 | 31 | 0.089 | 0.178 | 0.311 |
| Neutral Random - SlowTrack Only | 32 | 0.212 | 1.209 | 31 | 0.236 | 0.236 | 0.214 |

### Perceived Latency

| comparison | n | mean_diff | t | df | p_two_tailed | p_holm_within_metric | cohen_dz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded - SlowTrack Only | 32 | 0.76 | 3.068 | 31 | 0.004 | 0.018 | 0.542 |
| Emotion Only - SlowTrack Only | 32 | 0.531 | 1.957 | 31 | 0.059 | 0.119 | 0.346 |
| Intent Only - SlowTrack Only | 32 | 0.552 | 2.325 | 31 | 0.027 | 0.08 | 0.411 |
| Neutral Random - SlowTrack Only | 32 | 0.417 | 1.73 | 31 | 0.094 | 0.119 | 0.306 |

### Reaction Appropriateness

| comparison | n | mean_diff | t | df | p_two_tailed | p_holm_within_metric | cohen_dz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded - SlowTrack Only | 32 | 0.094 | 0.377 | 31 | 0.709 | 1 | 0.067 |
| Emotion Only - SlowTrack Only | 32 | 0.052 | 0.25 | 31 | 0.804 | 1 | 0.044 |
| Intent Only - SlowTrack Only | 32 | 0.187 | 0.849 | 31 | 0.403 | 1 | 0.15 |
| Neutral Random - SlowTrack Only | 32 | -0.01 | -0.049 | 31 | 0.961 | 1 | -0.009 |

### Conversational Naturalness

| comparison | n | mean_diff | t | df | p_two_tailed | p_holm_within_metric | cohen_dz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded - SlowTrack Only | 32 | 0.5 | 1.688 | 31 | 0.101 | 0.304 | 0.298 |
| Emotion Only - SlowTrack Only | 32 | 0.594 | 2.289 | 31 | 0.029 | 0.116 | 0.405 |
| Intent Only - SlowTrack Only | 32 | 0.328 | 1.161 | 31 | 0.255 | 0.509 | 0.205 |
| Neutral Random - SlowTrack Only | 32 | 0.047 | 0.211 | 31 | 0.835 | 0.835 | 0.037 |

### 영어 콘텐츠 4점 이상 표본: Overall

| comparison | n | mean_diff | t | df | p_two_tailed | p_holm_within_metric | cohen_dz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded - SlowTrack Only | 19 | 0.316 | 1.082 | 18 | 0.293 | 0.519 | 0.248 |
| Emotion Only - SlowTrack Only | 19 | 0.707 | 3.138 | 18 | 0.006 | 0.023 | 0.72 |
| Intent Only - SlowTrack Only | 19 | 0.421 | 1.529 | 18 | 0.144 | 0.431 | 0.351 |
| Neutral Random - SlowTrack Only | 19 | 0.301 | 1.164 | 18 | 0.26 | 0.519 | 0.267 |

## 6. 신뢰도: Cronbach alpha

### 전체 응답자, 5개 조건 stacked 처리

| scale | n_rows | items | cronbach_alpha |
| --- | --- | --- | --- |
| Overall_14_items | 160 | 14 | 0.93 |
| Perceived Latency | 160 | 3 | 0.693 |
| Conversational Naturalness | 160 | 2 | 0.79 |
| Reaction Appropriateness | 160 | 3 | 0.557 |
| Social Presence | 160 | 2 | 0.916 |
| Character Appeal | 160 | 2 | 0.846 |
| Engagement | 160 | 2 | 0.799 |

### 영어 콘텐츠 4점 이상 표본, 5개 조건 stacked 처리

| scale | n_rows | items | cronbach_alpha |
| --- | --- | --- | --- |
| Overall_14_items | 95 | 14 | 0.92 |
| Perceived Latency | 95 | 3 | 0.66 |
| Conversational Naturalness | 95 | 2 | 0.744 |
| Reaction Appropriateness | 95 | 3 | 0.439 |
| Social Presence | 95 | 2 | 0.919 |
| Character Appeal | 95 | 2 | 0.809 |
| Engagement | 95 | 2 | 0.775 |

## 7. Omnibus 검정: Friedman test

| metric | chi_square | df | p | kendall_w |
| --- | --- | --- | --- | --- |
| Overall | 7.373 | 4 | 0.117 | 0.058 |
| Perceived Latency | 8.979 | 4 | 0.062 | 0.07 |
| Conversational Naturalness | 8.233 | 4 | 0.083 | 0.064 |
| Reaction Appropriateness | 0.808 | 4 | 0.937 | 0.006 |
| Social Presence | 5.488 | 4 | 0.241 | 0.043 |
| Character Appeal | 13.637 | 4 | 0.009 | 0.107 |
| Engagement | 4.647 | 4 | 0.326 | 0.036 |

## 8. 해석 요약

- 결과는 특정 조건의 압도적 승리라기보다, FastTrack latency-cover 구조에 대한 탐색적 근거로 해석하는 것이 안전하다.
- Grounded는 Perceived Latency와 최종 선택 문항에서 중요한 신호를 제공한다.
- Intent Only가 맥락 적합성 선택에서 강하게 유지된다면 SWDA response-act mapping의 방법론적 가치가 커진다.
- Emotion Only가 자연스러움/전체 평균에서 높게 나오는 경향은, 감정 기반 반응이 사용자에게 직관적으로 자연스럽게 받아들여졌을 가능성을 시사한다.
- SlowTrack Only가 어색함 선택에서 높다면, FastTrack이 무반응 구간을 줄이는 장치로 기능한다는 주장을 보조한다.
- 레이턴시 48만 row 데이터는 실제 48만 회 실행이 아니라 recorded-log bootstrap sensitivity simulation임을 계속 분리해서 써야 한다.
