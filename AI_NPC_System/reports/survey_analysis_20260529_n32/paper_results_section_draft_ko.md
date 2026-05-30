# 논문 결과 파트 초안 (n32)

## 6. 실험 결과

### 6.1 참가자 및 조건 매핑

총 32명의 유효 설문 응답을 수집하였다. 본 실험은 동일한 참가자가 모든 실험 조건을 평가하는 within-subject 설계로 진행되었다. 설문에서 제시된 영상 순서는 기존 case 번호 순서와 다르게 구성되었으므로, 분석 전에 각 영상 블록을 실제 실험 조건에 맞게 재매핑하였다. 실제 매핑은 CSV의 첫 번째 영상 블록 = Intent Only, 두 번째 영상 블록 = Grounded, 세 번째 영상 블록 = SlowTrack Only, 네 번째 영상 블록 = Emotion Only, 다섯 번째 영상 블록 = Neutral Random이다.

모든 문항은 7점 Likert 척도로 측정하였다. 부정 문항인 침묵/공백 답답함 문항과 무작위 반응 지각 문항은 점수가 높을수록 긍정적인 평가가 되도록 역코딩하였다.

### 6.2 설문 척도 신뢰도

전체 14개 문항을 하나의 종합 척도로 보았을 때 Cronbach's alpha는 0.930로 높게 나타났다. Perceived Latency의 alpha는 0.693였고, Reaction Appropriateness의 alpha는 0.557로 상대적으로 낮게 나타났다. 따라서 Reaction Appropriateness는 평균 점수만으로 강하게 해석하기보다 최종 선택 문항과 함께 보조적으로 해석하였다.

### 6.3 조건별 기술통계

표 1은 각 조건에 대한 평균과 표준편차를 나타낸다.

**표 1. 조건별 주관 평가 평균 및 표준편차, M (SD).**

| condition | Overall | Perceived Latency | Conversational Naturalness | Reaction Appropriateness | Social Presence | Character Appeal | Engagement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Grounded | 4.95 (1.11) | 5.47 (1.00) | 4.75 (1.49) | 4.83 (1.10) | 5.30 (1.24) | 4.44 (1.57) | 4.72 (1.53) |
| Emotion Only | 4.91 (1.24) | 5.24 (1.33) | 4.84 (1.66) | 4.79 (1.25) | 5.27 (1.31) | 4.67 (1.73) | 4.53 (1.67) |
| Intent Only | 4.81 (0.95) | 5.26 (1.05) | 4.58 (1.29) | 4.93 (0.89) | 5.31 (1.38) | 4.05 (1.54) | 4.45 (1.42) |
| Neutral Random | 4.69 (1.30) | 5.12 (1.03) | 4.30 (1.47) | 4.73 (1.33) | 4.86 (1.53) | 4.56 (1.83) | 4.33 (1.78) |
| SlowTrack Only | 4.48 (1.28) | 4.71 (1.42) | 4.25 (1.66) | 4.74 (1.19) | 4.78 (1.55) | 4.09 (1.79) | 4.05 (1.75) |

### 6.4 조건 간 차이에 대한 Omnibus 검정

5개 조건 전체의 차이를 확인하기 위해 Friedman test를 수행하였다. 주요 결과는 다음과 같다.

- Overall: chi-square(4) = 7.37, p = 0.117, W = 0.058
- Perceived Latency: chi-square(4) = 8.98, p = 0.062, W = 0.070
- Conversational Naturalness: chi-square(4) = 8.23, p = 0.083, W = 0.064
- Reaction Appropriateness: chi-square(4) = 0.81, p = 0.937, W = 0.006
- Social Presence: chi-square(4) = 5.49, p = 0.241, W = 0.043
- Character Appeal: chi-square(4) = 13.64, p = 0.009, W = 0.107
- Engagement: chi-square(4) = 4.65, p = 0.326, W = 0.036

이 결과는 대부분의 주관 평가 지표에서 5개 조건 간 차이가 강하게 벌어지지는 않았음을 의미한다. 따라서 조건 간 비교는 특정 조건의 전면적 우수성을 입증하는 분석이라기보다, CREDO의 latency-cover 메커니즘이 일부 지표에서 어떤 방향의 경향을 보였는지 확인하는 탐색적 분석으로 해석하는 것이 적절하다.

### 6.5 SlowTrack Only 대비 계획 비교

Grounded 조건은 SlowTrack Only 조건보다 Perceived Latency 점수가 높게 나타났다. 평균 차이는 0.760점이었으며, t(31) = 3.07, p = 0.004, Cohen's dz = 0.54로 나타났다. 같은 지표 내 4개 비교에 대한 Holm 보정 후에도 p값은 0.018으로 .05보다 낮았다. 따라서 이 planned comparison은 Grounded FastTrack이 지각된 대기 시간 평가를 개선했다는 비교적 강한 근거로 해석할 수 있다.

Emotion Only 조건은 Conversational Naturalness에서 SlowTrack Only보다 높은 경향을 보였다. 평균 차이는 0.594점, t(31) = 2.29, p = 0.029, dz = 0.40로 나타났다.

### 6.6 최종 선택 문항 결과

가장 대화 흐름이 자연스러웠던 영상으로는 Grounded 조건이 20명, Intent Only 조건이 22명에게 선택되었다. 리액션이 가장 맥락에 잘 어울렸던 영상 역시 Grounded 조건이 21명, Intent Only 조건이 23명에게 선택되었다. 반면 SlowTrack Only는 가장 어색하거나 불편했던 영상으로 14명에게 선택되었다.

### 6.7 결과 요약

종합하면, 본 실험 결과는 CREDO의 latency-cover 접근법에 대한 탐색적 근거를 제공한다. 정량 레이턴시 분석은 FastTrack이 첫 반응 준비 시간을 크게 줄인다는 시스템 수준의 근거를 제공하고, 설문 결과는 Grounded 및 Intent 기반 조건이 대화 흐름과 맥락 적합성에서 긍정적으로 평가될 가능성을 보여준다. 특히 Grounded 조건의 Perceived Latency planned comparison은 Holm 보정 후에도 SlowTrack Only보다 유의하게 높았다. 그러나 대부분의 omnibus 검정은 유의하지 않았으므로, 본 결과는 특정 조건의 전면적 우수성을 주장하기보다 FastTrack 기반 초기 반응이 AI VTuber 상호작용에서 유망한 latency-cover 설계 방향임을 보여주는 근거로 해석하는 것이 적절하다.
