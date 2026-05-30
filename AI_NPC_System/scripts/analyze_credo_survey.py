#!/usr/bin/env python3
"""Analyze CREDO within-subject survey CSV/ZIP exports.

The script intentionally excludes name/email columns from outputs and uses
column positions for repeated video blocks because Google Forms duplicates the
same item labels for each video.
"""

from __future__ import annotations

import argparse
import io
import math
import shutil
from pathlib import Path
from zipfile import ZipFile

import mpmath as mp
import numpy as np
import pandas as pd


CASE_META = {
    1: {"condition": "Grounded", "policy": "Emotion + SWDA response act"},
    2: {"condition": "Emotion Only", "policy": "Emotion only"},
    3: {"condition": "Intent Only", "policy": "SWDA response act only"},
    4: {"condition": "Neutral Random", "policy": "Random/neutral FastTrack"},
    5: {"condition": "SlowTrack Only", "policy": "No FastTrack baseline"},
}

QUESTION_NAMES = [
    "q1_latency_short",
    "q2_reacting_not_stopped",
    "q3_frustration_reversed",
    "q4_conversation_flow",
    "q5_broadcast_naturalness",
    "q6_meaningful_reaction",
    "q7_randomness_reversed",
    "q8_reaction_to_answer_transition",
    "q9_listening",
    "q10_interacting",
    "q11_character_appeal",
    "q12_character_reinforcement",
    "q13_immersion",
    "q14_want_more",
]

GROUPS = {
    "Perceived Latency": [0, 1, 2],
    "Conversational Naturalness": [3, 4],
    "Reaction Appropriateness": [5, 6, 7],
    "Social Presence": [8, 9],
    "Character Appeal": [10, 11],
    "Engagement": [12, 13],
}

METRICS = ["Overall", *GROUPS.keys()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Google Forms CSV or ZIP containing one CSV.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--case-order", default="3,1,5,2,4")
    parser.add_argument(
        "--desktop-copy-dir",
        default="/mnt/c/Users/CGLAB/Desktop/결과 분석",
        help="Optional directory for convenience copies. Use empty string to skip.",
    )
    parser.add_argument("--label", default="n30")
    return parser.parse_args()


def read_csv_or_zip(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(csv_names) != 1:
                raise RuntimeError(f"Expected exactly one CSV in ZIP, found {len(csv_names)}")
            data = archive.read(csv_names[0])
        return pd.read_csv(io.BytesIO(data))
    return pd.read_csv(path)


def t_cdf(t: float, df: int) -> float:
    if df <= 0 or math.isnan(t):
        return float("nan")
    x = df / (df + t * t)
    ib = mp.betainc(df / 2, 0.5, 0, x, regularized=True)
    if t >= 0:
        return float(1 - 0.5 * ib)
    return float(0.5 * ib)


def norm_cdf(z: float) -> float:
    return float(0.5 * (1 + mp.erf(z / mp.sqrt(2))))


def chi2_sf(x: float, df: int) -> float:
    return float(mp.gammainc(df / 2, x / 2, mp.inf) / mp.gamma(df / 2))


def rank_average(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    order = np.argsort(arr)
    ranks = np.empty(len(arr), dtype=float)
    index = 0
    while index < len(arr):
        end = index
        while end + 1 < len(arr) and arr[order[end + 1]] == arr[order[index]]:
            end += 1
        avg = (index + 1 + end + 1) / 2
        for pos in range(index, end + 1):
            ranks[order[pos]] = avg
        index = end + 1
    return ranks


def paired_t(a: pd.Series, b: pd.Series) -> dict[str, float]:
    diff = (a - b).dropna().astype(float)
    n = len(diff)
    if n < 2:
        return {
            "n": n,
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t": float("nan"),
            "df": n - 1,
            "p_two_tailed": float("nan"),
            "cohen_dz": float("nan"),
        }
    mean = float(diff.mean())
    sd = float(diff.std(ddof=1))
    if sd == 0:
        t = math.inf if mean > 0 else -math.inf if mean < 0 else 0.0
        p = 0.0 if mean != 0 else 1.0
        dz = t
    else:
        t = mean / (sd / math.sqrt(n))
        p = 2 * (1 - t_cdf(abs(t), n - 1))
        dz = mean / sd
    return {
        "n": n,
        "mean_diff": mean,
        "sd_diff": sd,
        "t": t,
        "df": n - 1,
        "p_two_tailed": p,
        "cohen_dz": dz,
    }


def holm(pvals: list[float]) -> list[float]:
    valid = sorted(
        [(i, p) for i, p in enumerate(pvals) if not math.isnan(p)],
        key=lambda item: item[1],
    )
    adjusted = [float("nan")] * len(pvals)
    running = 0.0
    total = len(valid)
    for rank, (index, pval) in enumerate(valid, start=1):
        value = min(1.0, (total - rank + 1) * pval)
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def cronbach_alpha(frame: pd.DataFrame) -> float:
    data = frame.dropna().astype(float)
    item_count = data.shape[1]
    if item_count < 2 or len(data) < 2:
        return float("nan")
    item_var = data.var(axis=0, ddof=1).sum()
    total_var = data.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return float(item_count / (item_count - 1) * (1 - item_var / total_var))


def friedman(wide: pd.DataFrame) -> dict[str, float]:
    mat = wide.dropna().to_numpy(float)
    n, k = mat.shape
    ranks = np.vstack([rank_average(row) for row in mat])
    rank_sums = ranks.sum(axis=0)
    chi_square = 12 / (n * k * (k + 1)) * np.sum(rank_sums**2) - 3 * n * (k + 1)
    tie_sum = 0
    for row in mat:
        _, counts = np.unique(row, return_counts=True)
        tie_sum += sum(count**3 - count for count in counts if count > 1)
    correction = 1 - tie_sum / (n * (k**3 - k)) if n * (k**3 - k) else 1
    if correction > 0:
        chi_square /= correction
    return {
        "n": n,
        "k": k,
        "chi_square": float(chi_square),
        "df": k - 1,
        "p": chi2_sf(float(chi_square), k - 1),
        "kendall_w": float(chi_square / (n * (k - 1))),
    }


def wilcoxon(a: pd.Series, b: pd.Series) -> dict[str, float]:
    diff = (a - b).dropna().to_numpy(float)
    diff = diff[diff != 0]
    n = len(diff)
    if n < 2:
        return {"n": n, "W_plus": float("nan"), "z": float("nan"), "p": float("nan"), "r": float("nan")}
    ranks = rank_average(np.abs(diff))
    w_plus = float(ranks[diff > 0].sum())
    mean = n * (n + 1) / 4
    _, counts = np.unique(np.abs(diff), return_counts=True)
    tie_sum = sum(count**3 - count for count in counts if count > 1)
    var = n * (n + 1) * (2 * n + 1) / 24 - tie_sum / 48
    if var <= 0:
        z = 0.0
        pval = 1.0
    else:
        cc = 0.5 if w_plus > mean else -0.5 if w_plus < mean else 0.0
        z = (w_plus - mean - cc) / math.sqrt(var)
        pval = 2 * (1 - norm_cdf(abs(z)))
    return {"n": n, "W_plus": w_plus, "z": z, "p": pval, "r": abs(z) / math.sqrt(n)}


def md_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    rows = ["| " + " | ".join(str(col) for col in columns) + " |"]
    rows.append("| " + " | ".join("---" for _ in columns) + " |")
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}".rstrip("0").rstrip("."))
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def build_long(raw: pd.DataFrame, case_order: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_col = 8
    block_size = 17
    records: list[dict[str, object]] = []
    choices: list[dict[str, object]] = []
    for video_index, case_no in enumerate(case_order, start=1):
        start = base_col + block_size * (video_index - 1)
        likert_cols = list(raw.columns[start : start + 14])
        choice_cols = list(raw.columns[start + 14 : start + 17])
        likert = raw[likert_cols].apply(pd.to_numeric, errors="coerce")
        adjusted = likert.copy()
        adjusted.iloc[:, 2] = 8 - adjusted.iloc[:, 2]
        adjusted.iloc[:, 6] = 8 - adjusted.iloc[:, 6]
        for respondent in raw.index:
            meta = CASE_META[case_no]
            record: dict[str, object] = {
                "respondent_id": int(respondent) + 1,
                "video_order": video_index,
                "case_no": case_no,
                "condition": meta["condition"],
                "policy": meta["policy"],
                "english_exposure": pd.to_numeric(
                    raw.loc[respondent, "평소에 영어로된 콘텐츠를 얼마나 시청하십니까? "],
                    errors="coerce",
                ),
                "vtuber_familiarity": pd.to_numeric(
                    raw.loc[respondent, "평소, V-tuber 콘텐츠에 대해 잘 알고 있나요 ?"],
                    errors="coerce",
                ),
            }
            for idx, qname in enumerate(QUESTION_NAMES):
                record[qname] = float(adjusted.iloc[respondent, idx])
                record[qname.replace("_reversed", "") + "_raw"] = float(likert.iloc[respondent, idx])
            record["Overall"] = float(adjusted.iloc[respondent].mean())
            for group_name, item_indexes in GROUPS.items():
                record[group_name] = float(adjusted.iloc[respondent, item_indexes].mean())
            records.append(record)
            choices.append(
                {
                    "respondent_id": int(respondent) + 1,
                    "video_order": video_index,
                    "case_no": case_no,
                    "condition": meta["condition"],
                    "best_flow": raw.loc[respondent, choice_cols[0]] == "예",
                    "most_uncomfortable": raw.loc[respondent, choice_cols[1]] == "예",
                    "best_context_reaction": raw.loc[respondent, choice_cols[2]] == "예",
                    "english_exposure": pd.to_numeric(
                        raw.loc[respondent, "평소에 영어로된 콘텐츠를 얼마나 시청하십니까? "],
                        errors="coerce",
                    ),
                }
            )
    return pd.DataFrame(records), pd.DataFrame(choices)


def summarize(long: pd.DataFrame, sample: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for case_no, group in long.groupby("case_no"):
        row: dict[str, object] = {
            "sample": sample,
            "case_no": int(case_no),
            "condition": CASE_META[int(case_no)]["condition"],
            "n": group["respondent_id"].nunique(),
        }
        for metric in METRICS:
            row[f"{metric}_mean"] = group[metric].mean()
            row[f"{metric}_sd"] = group[metric].std(ddof=1)
            row[f"{metric}_median"] = group[metric].median()
        rows.append(row)
    return pd.DataFrame(rows).sort_values("case_no")


def m_sd_table(long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for case_no, group in long.groupby("case_no"):
        row: dict[str, object] = {"case_no": int(case_no), "condition": CASE_META[int(case_no)]["condition"]}
        for metric in METRICS:
            row[metric] = f"{group[metric].mean():.2f} ({group[metric].std(ddof=1):.2f})"
        rows.append(row)
    return pd.DataFrame(rows).sort_values("case_no")


def ttests_vs_baseline(long: pd.DataFrame, sample: str, baseline_case: int = 5) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric in METRICS:
        wide = long.pivot(index="respondent_id", columns="case_no", values=metric)
        baseline = wide[baseline_case]
        metric_rows: list[dict[str, object]] = []
        for case_no in [1, 2, 3, 4]:
            result = paired_t(wide[case_no], baseline)
            metric_rows.append(
                {
                    "sample": sample,
                    "metric": metric,
                    "comparison": f"{CASE_META[case_no]['condition']} - {CASE_META[baseline_case]['condition']}",
                    "case_no": case_no,
                    "baseline_case_no": baseline_case,
                    **result,
                }
            )
        adjusted = holm([float(row["p_two_tailed"]) for row in metric_rows])
        for row, p_adjusted in zip(metric_rows, adjusted):
            row["p_holm_within_metric"] = p_adjusted
            rows.append(row)
    return pd.DataFrame(rows)


def reliability(long: pd.DataFrame, sample: str) -> pd.DataFrame:
    item_map = {"Overall_14_items": QUESTION_NAMES}
    for group_name, indexes in GROUPS.items():
        item_map[group_name] = [QUESTION_NAMES[index] for index in indexes]
    rows: list[dict[str, object]] = []
    for scale_name, item_names in item_map.items():
        rows.append(
            {
                "sample": sample,
                "scope": "stacked_all_cases",
                "scale": scale_name,
                "n_rows": len(long),
                "items": len(item_names),
                "cronbach_alpha": cronbach_alpha(long[item_names]),
            }
        )
        for case_no, group in long.groupby("case_no"):
            rows.append(
                {
                    "sample": sample,
                    "scope": f"case_{int(case_no)}_{CASE_META[int(case_no)]['condition']}",
                    "scale": scale_name,
                    "n_rows": len(group),
                    "items": len(item_names),
                    "cronbach_alpha": cronbach_alpha(group[item_names]),
                }
            )
    return pd.DataFrame(rows)


def choice_summary(choices: pd.DataFrame, sample: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for case_no, group in choices.groupby("case_no"):
        row: dict[str, object] = {
            "sample": sample,
            "case_no": int(case_no),
            "condition": CASE_META[int(case_no)]["condition"],
            "n": group["respondent_id"].nunique(),
        }
        for column in ["best_flow", "most_uncomfortable", "best_context_reaction"]:
            row[f"{column}_yes"] = int(group[column].sum())
            row[f"{column}_pct"] = 100 * group[column].mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values("case_no")


def friedman_tests(long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric in METRICS:
        wide = long.pivot(index="respondent_id", columns="case_no", values=metric)[[1, 2, 3, 4, 5]]
        rows.append({"metric": metric, **friedman(wide)})
    return pd.DataFrame(rows)


def wilcoxon_tests(long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric in METRICS:
        wide = long.pivot(index="respondent_id", columns="case_no", values=metric)[[1, 2, 3, 4, 5]]
        metric_rows = []
        for case_no in [1, 2, 3, 4]:
            result = wilcoxon(wide[case_no], wide[5])
            metric_rows.append(
                {
                    "metric": metric,
                    "comparison": f"{CASE_META[case_no]['condition']} - SlowTrack Only",
                    "case_no": case_no,
                    **result,
                }
            )
        adjusted = holm([float(row["p"]) for row in metric_rows])
        for row, p_adjusted in zip(metric_rows, adjusted):
            row["p_holm_within_metric"] = p_adjusted
            rows.append(row)
    return pd.DataFrame(rows)


def format_float(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.{digits}f}"


def build_ko_report(
    *,
    label: str,
    summary_all: pd.DataFrame,
    summary_eng4: pd.DataFrame,
    summary_eng5: pd.DataFrame,
    choices_all: pd.DataFrame,
    choices_eng4: pd.DataFrame,
    tests_all: pd.DataFrame,
    tests_eng4: pd.DataFrame,
    rel_all: pd.DataFrame,
    rel_eng4: pd.DataFrame,
    friedman_all: pd.DataFrame,
    respondent_count: int,
) -> str:
    condition_cols = [
        "case_no",
        "condition",
        "n",
        "Overall_mean",
        "Perceived Latency_mean",
        "Reaction Appropriateness_mean",
        "Conversational Naturalness_mean",
        "Social Presence_mean",
        "Character Appeal_mean",
        "Engagement_mean",
    ]

    def condition_table(frame: pd.DataFrame) -> str:
        return md_table(frame[condition_cols].round(2))

    def choice_table(frame: pd.DataFrame) -> str:
        return md_table(
            frame[
                [
                    "case_no",
                    "condition",
                    "n",
                    "best_flow_yes",
                    "most_uncomfortable_yes",
                    "best_context_reaction_yes",
                ]
            ]
        )

    def t_table(metric: str, frame: pd.DataFrame) -> str:
        sub = frame[frame["metric"] == metric].copy()
        return md_table(
            sub[
                [
                    "comparison",
                    "n",
                    "mean_diff",
                    "t",
                    "df",
                    "p_two_tailed",
                    "p_holm_within_metric",
                    "cohen_dz",
                ]
            ].round(
                {
                    "mean_diff": 3,
                    "t": 3,
                    "p_two_tailed": 4,
                    "p_holm_within_metric": 4,
                    "cohen_dz": 3,
                }
            )
        )

    rel_summary = rel_all[rel_all["scope"] == "stacked_all_cases"][
        ["scale", "n_rows", "items", "cronbach_alpha"]
    ].round({"cronbach_alpha": 3})
    rel_eng_summary = rel_eng4[rel_eng4["scope"] == "stacked_all_cases"][
        ["scale", "n_rows", "items", "cronbach_alpha"]
    ].round({"cronbach_alpha": 3})

    top_overall = summary_all.sort_values("Overall_mean", ascending=False).iloc[0]
    top_latency = summary_all.sort_values("Perceived Latency_mean", ascending=False).iloc[0]
    top_natural = summary_all.sort_values("Conversational Naturalness_mean", ascending=False).iloc[0]

    return "\n".join(
        [
            f"# CREDO 설문 및 정량 레이턴시 결과 검토 보고서 ({label})",
            "",
            "## 1. 분석 전제",
            "",
            f"- 설문 응답자 수: {respondent_count}명.",
            "- 설문은 5개 영상을 모두 평가한 within-subject 구조로 분석했다.",
            "- 실제 영상 순서는 `case 3-1-5-2-4`로 반영했다.",
            "- 부정 문항인 침묵/공백 답답함, 무작위 반응 지각 문항은 역코딩했다.",
            "- SlowTrack Only를 기준으로 paired t-test를 수행했고, 같은 지표 내 4개 비교에는 Holm 보정값을 함께 제공했다.",
            "",
            "## 2. 전체 응답자 조건별 평균",
            "",
            condition_table(summary_all),
            "",
            "### 해석",
            "",
            f"- 전체 평균이 가장 높은 조건은 Case {int(top_overall.case_no)} `{top_overall.condition}`이며 평균은 {format_float(top_overall.Overall_mean)}점이다.",
            f"- Perceived Latency가 가장 높은 조건은 Case {int(top_latency.case_no)} `{top_latency.condition}`이며 평균은 {format_float(top_latency['Perceived Latency_mean'])}점이다.",
            f"- Conversational Naturalness가 가장 높은 조건은 Case {int(top_natural.case_no)} `{top_natural.condition}`이며 평균은 {format_float(top_natural['Conversational Naturalness_mean'])}점이다.",
            "",
            "## 3. 영어 콘텐츠 저시청자 제외 결과",
            "",
            "- 영어 콘텐츠 시청 빈도 1-3점을 저시청자로 보고 제외했다.",
            "- 영어 콘텐츠 시청 빈도 4점 이상 응답자 기준 결과는 다음과 같다.",
            "",
            condition_table(summary_eng4),
            "",
            "- 더 강한 필터인 영어 콘텐츠 시청 빈도 5점 이상 응답자 기준 결과는 다음과 같다.",
            "",
            condition_table(summary_eng5),
            "",
            "## 4. 최종 선택 문항 결과",
            "",
            "### 전체 응답자",
            "",
            choice_table(choices_all),
            "",
            "### 영어 콘텐츠 4점 이상 응답자",
            "",
            choice_table(choices_eng4),
            "",
            "## 5. SlowTrack Only 대비 paired t-test",
            "",
            "아래 표의 mean_diff는 `각 FastTrack 조건 - SlowTrack Only`이다. 양수이면 SlowTrack Only보다 해당 조건이 높게 평가되었다는 뜻이다.",
            "",
            "### Overall",
            "",
            t_table("Overall", tests_all),
            "",
            "### Perceived Latency",
            "",
            t_table("Perceived Latency", tests_all),
            "",
            "### Reaction Appropriateness",
            "",
            t_table("Reaction Appropriateness", tests_all),
            "",
            "### Conversational Naturalness",
            "",
            t_table("Conversational Naturalness", tests_all),
            "",
            "### 영어 콘텐츠 4점 이상 표본: Overall",
            "",
            t_table("Overall", tests_eng4),
            "",
            "## 6. 신뢰도: Cronbach alpha",
            "",
            "### 전체 응답자, 5개 조건 stacked 처리",
            "",
            md_table(rel_summary),
            "",
            "### 영어 콘텐츠 4점 이상 표본, 5개 조건 stacked 처리",
            "",
            md_table(rel_eng_summary),
            "",
            "## 7. Omnibus 검정: Friedman test",
            "",
            md_table(
                friedman_all[["metric", "chi_square", "df", "p", "kendall_w"]].round(
                    {"chi_square": 3, "p": 4, "kendall_w": 3}
                )
            ),
            "",
            "## 8. 해석 요약",
            "",
            "- 결과는 특정 조건의 압도적 승리라기보다, FastTrack latency-cover 구조에 대한 탐색적 근거로 해석하는 것이 안전하다.",
            "- Grounded는 Perceived Latency와 최종 선택 문항에서 중요한 신호를 제공한다.",
            "- Intent Only가 맥락 적합성 선택에서 강하게 유지된다면 SWDA response-act mapping의 방법론적 가치가 커진다.",
            "- Emotion Only가 자연스러움/전체 평균에서 높게 나오는 경향은, 감정 기반 반응이 사용자에게 직관적으로 자연스럽게 받아들여졌을 가능성을 시사한다.",
            "- SlowTrack Only가 어색함 선택에서 높다면, FastTrack이 무반응 구간을 줄이는 장치로 기능한다는 주장을 보조한다.",
            "- 레이턴시 48만 row 데이터는 실제 48만 회 실행이 아니라 recorded-log bootstrap sensitivity simulation임을 계속 분리해서 써야 한다.",
            "",
        ]
    )


def build_results_section_ko(
    *,
    label: str,
    summary_all: pd.DataFrame,
    choices_all: pd.DataFrame,
    tests_all: pd.DataFrame,
    rel_all: pd.DataFrame,
    friedman_all: pd.DataFrame,
    m_sd: pd.DataFrame,
    respondent_count: int,
) -> str:
    overall_alpha = rel_all[
        (rel_all["scope"] == "stacked_all_cases") & (rel_all["scale"] == "Overall_14_items")
    ]["cronbach_alpha"].iloc[0]
    perceived_alpha = rel_all[
        (rel_all["scope"] == "stacked_all_cases") & (rel_all["scale"] == "Perceived Latency")
    ]["cronbach_alpha"].iloc[0]
    reaction_alpha = rel_all[
        (rel_all["scope"] == "stacked_all_cases") & (rel_all["scale"] == "Reaction Appropriateness")
    ]["cronbach_alpha"].iloc[0]

    def metric_test(metric: str, comparison_prefix: str) -> pd.Series:
        rows = tests_all[(tests_all["metric"] == metric) & tests_all["comparison"].str.startswith(comparison_prefix)]
        return rows.iloc[0]

    grounded_latency = metric_test("Perceived Latency", "Grounded")
    emotion_natural = metric_test("Conversational Naturalness", "Emotion Only")

    flow_grounded = int(choices_all[choices_all["condition"] == "Grounded"]["best_flow_yes"].iloc[0])
    flow_intent = int(choices_all[choices_all["condition"] == "Intent Only"]["best_flow_yes"].iloc[0])
    context_grounded = int(choices_all[choices_all["condition"] == "Grounded"]["best_context_reaction_yes"].iloc[0])
    context_intent = int(choices_all[choices_all["condition"] == "Intent Only"]["best_context_reaction_yes"].iloc[0])
    awkward_slow = int(choices_all[choices_all["condition"] == "SlowTrack Only"]["most_uncomfortable_yes"].iloc[0])

    friedman_text = []
    for _, row in friedman_all.iterrows():
        friedman_text.append(
            f"{row['metric']}: chi-square(4) = {row['chi_square']:.2f}, p = {row['p']:.3f}, W = {row['kendall_w']:.3f}"
        )

    table = md_table(m_sd.drop(columns=["case_no"]))

    return "\n".join(
        [
            f"# 논문 결과 파트 초안 ({label})",
            "",
            "## 6. 실험 결과",
            "",
            "### 6.1 참가자 및 조건 매핑",
            "",
            f"총 {respondent_count}명의 유효 설문 응답을 수집하였다. 본 실험은 동일한 참가자가 모든 실험 조건을 평가하는 within-subject 설계로 진행되었다. 설문에서 제시된 영상 순서는 기존 case 번호 순서와 다르게 구성되었으므로, 분석 전에 각 영상 블록을 실제 실험 조건에 맞게 재매핑하였다. 실제 매핑은 CSV의 첫 번째 영상 블록 = Intent Only, 두 번째 영상 블록 = Grounded, 세 번째 영상 블록 = SlowTrack Only, 네 번째 영상 블록 = Emotion Only, 다섯 번째 영상 블록 = Neutral Random이다.",
            "",
            "모든 문항은 7점 Likert 척도로 측정하였다. 부정 문항인 침묵/공백 답답함 문항과 무작위 반응 지각 문항은 점수가 높을수록 긍정적인 평가가 되도록 역코딩하였다.",
            "",
            "### 6.2 설문 척도 신뢰도",
            "",
            f"전체 14개 문항을 하나의 종합 척도로 보았을 때 Cronbach's alpha는 {overall_alpha:.3f}로 높게 나타났다. Perceived Latency의 alpha는 {perceived_alpha:.3f}였고, Reaction Appropriateness의 alpha는 {reaction_alpha:.3f}로 상대적으로 낮게 나타났다. 따라서 Reaction Appropriateness는 평균 점수만으로 강하게 해석하기보다 최종 선택 문항과 함께 보조적으로 해석하였다.",
            "",
            "### 6.3 조건별 기술통계",
            "",
            "표 1은 각 조건에 대한 평균과 표준편차를 나타낸다.",
            "",
            "**표 1. 조건별 주관 평가 평균 및 표준편차, M (SD).**",
            "",
            table,
            "",
            "### 6.4 조건 간 차이에 대한 Omnibus 검정",
            "",
            "5개 조건 전체의 차이를 확인하기 위해 Friedman test를 수행하였다. 주요 결과는 다음과 같다.",
            "",
            "\n".join(f"- {item}" for item in friedman_text),
            "",
            "이 결과는 대부분의 주관 평가 지표에서 5개 조건 간 차이가 강하게 벌어지지는 않았음을 의미한다. 따라서 조건 간 비교는 특정 조건의 전면적 우수성을 입증하는 분석이라기보다, CREDO의 latency-cover 메커니즘이 일부 지표에서 어떤 방향의 경향을 보였는지 확인하는 탐색적 분석으로 해석하는 것이 적절하다.",
            "",
            "### 6.5 SlowTrack Only 대비 계획 비교",
            "",
            f"Grounded 조건은 SlowTrack Only 조건보다 Perceived Latency 점수가 높게 나타났다. 평균 차이는 {grounded_latency['mean_diff']:.3f}점이었으며, t({int(grounded_latency['df'])}) = {grounded_latency['t']:.2f}, p = {grounded_latency['p_two_tailed']:.3f}, Cohen's dz = {grounded_latency['cohen_dz']:.2f}로 나타났다. 같은 지표 내 4개 비교에 대한 Holm 보정 후에도 p값은 {grounded_latency['p_holm_within_metric']:.3f}으로 .05보다 낮았다. 따라서 이 planned comparison은 Grounded FastTrack이 지각된 대기 시간 평가를 개선했다는 비교적 강한 근거로 해석할 수 있다.",
            "",
            f"Emotion Only 조건은 Conversational Naturalness에서 SlowTrack Only보다 높은 경향을 보였다. 평균 차이는 {emotion_natural['mean_diff']:.3f}점, t({int(emotion_natural['df'])}) = {emotion_natural['t']:.2f}, p = {emotion_natural['p_two_tailed']:.3f}, dz = {emotion_natural['cohen_dz']:.2f}로 나타났다.",
            "",
            "### 6.6 최종 선택 문항 결과",
            "",
            f"가장 대화 흐름이 자연스러웠던 영상으로는 Grounded 조건이 {flow_grounded}명, Intent Only 조건이 {flow_intent}명에게 선택되었다. 리액션이 가장 맥락에 잘 어울렸던 영상 역시 Grounded 조건이 {context_grounded}명, Intent Only 조건이 {context_intent}명에게 선택되었다. 반면 SlowTrack Only는 가장 어색하거나 불편했던 영상으로 {awkward_slow}명에게 선택되었다.",
            "",
            "### 6.7 결과 요약",
            "",
            "종합하면, 본 실험 결과는 CREDO의 latency-cover 접근법에 대한 탐색적 근거를 제공한다. 정량 레이턴시 분석은 FastTrack이 첫 반응 준비 시간을 크게 줄인다는 시스템 수준의 근거를 제공하고, 설문 결과는 Grounded 및 Intent 기반 조건이 대화 흐름과 맥락 적합성에서 긍정적으로 평가될 가능성을 보여준다. 특히 Grounded 조건의 Perceived Latency planned comparison은 Holm 보정 후에도 SlowTrack Only보다 유의하게 높았다. 그러나 대부분의 omnibus 검정은 유의하지 않았으므로, 본 결과는 특정 조건의 전면적 우수성을 주장하기보다 FastTrack 기반 초기 반응이 AI VTuber 상호작용에서 유망한 latency-cover 설계 방향임을 보여주는 근거로 해석하는 것이 적절하다.",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_order = [int(value.strip()) for value in args.case_order.split(",") if value.strip()]
    raw = read_csv_or_zip(input_path)
    long, choices = build_long(raw, case_order)
    respondent_count = raw.shape[0]

    english4_ids = set(long.loc[long["english_exposure"] >= 4, "respondent_id"].unique())
    english5_ids = set(long.loc[long["english_exposure"] >= 5, "respondent_id"].unique())
    long_eng4 = long[long["respondent_id"].isin(english4_ids)].copy()
    long_eng5 = long[long["respondent_id"].isin(english5_ids)].copy()
    choices_eng4 = choices[choices["respondent_id"].isin(english4_ids)].copy()

    summary_all = summarize(long, f"all_{args.label}")
    summary_eng4 = summarize(long_eng4, "english_ge4")
    summary_eng5 = summarize(long_eng5, "english_ge5")
    choices_all = choice_summary(choices, f"all_{args.label}")
    choices_eng4 = choice_summary(choices_eng4, "english_ge4")
    tests_all = ttests_vs_baseline(long, f"all_{args.label}")
    tests_eng4 = ttests_vs_baseline(long_eng4, "english_ge4")
    rel_all = reliability(long, f"all_{args.label}")
    rel_eng4 = reliability(long_eng4, "english_ge4")
    friedman_all = friedman_tests(long)
    wilcoxon_all = wilcoxon_tests(long)
    msd = m_sd_table(long)

    outputs = {
        "survey_long_scores_case_order_31524.csv": long,
        "condition_summary_all.csv": summary_all,
        "condition_summary_english_ge4.csv": summary_eng4,
        "condition_summary_english_ge5.csv": summary_eng5,
        "choice_summary_all.csv": choices_all,
        "choice_summary_english_ge4.csv": choices_eng4,
        "paired_ttests_vs_slowtrack_all.csv": tests_all,
        "paired_ttests_vs_slowtrack_english_ge4.csv": tests_eng4,
        "cronbach_alpha_all.csv": rel_all,
        "cronbach_alpha_english_ge4.csv": rel_eng4,
        "friedman_tests_all.csv": friedman_all,
        "wilcoxon_vs_slowtrack_all.csv": wilcoxon_all,
        "condition_summary_all_m_sd_table.csv": msd,
    }
    for filename, frame in outputs.items():
        frame.to_csv(output_dir / filename, index=False)

    ko_report = build_ko_report(
        label=args.label,
        summary_all=summary_all,
        summary_eng4=summary_eng4,
        summary_eng5=summary_eng5,
        choices_all=choices_all,
        choices_eng4=choices_eng4,
        tests_all=tests_all,
        tests_eng4=tests_eng4,
        rel_all=rel_all,
        rel_eng4=rel_eng4,
        friedman_all=friedman_all,
        respondent_count=respondent_count,
    )
    results_ko = build_results_section_ko(
        label=args.label,
        summary_all=summary_all,
        choices_all=choices_all,
        tests_all=tests_all,
        rel_all=rel_all,
        friedman_all=friedman_all,
        m_sd=msd,
        respondent_count=respondent_count,
    )
    (output_dir / "survey_statistical_report_ko.md").write_text(ko_report, encoding="utf-8")
    (output_dir / "paper_results_section_draft_ko.md").write_text(results_ko, encoding="utf-8")

    if args.desktop_copy_dir:
        copy_dir = Path(args.desktop_copy_dir)
        copy_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_dir / "survey_statistical_report_ko.md", copy_dir / f"CREDO_설문_통계_분석_보고서_{args.label}.md")
        shutil.copy2(output_dir / "paper_results_section_draft_ko.md", copy_dir / f"CREDO_논문_결과파트_초안_{args.label}_ko.md")

    print(f"respondents={respondent_count}")
    print(f"english_ge4={len(english4_ids)}")
    print(f"english_ge5={len(english5_ids)}")
    print(f"output_dir={output_dir}")
    print(
        summary_all[
            [
                "case_no",
                "condition",
                "Overall_mean",
                "Perceived Latency_mean",
                "Reaction Appropriateness_mean",
                "Conversational Naturalness_mean",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
