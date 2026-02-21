import json
import math
from pathlib import Path

import config
import fast_lane
import merge_policy

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "calibration_dataset_v012.json"
OUT_PARAM = ROOT / "calibration_params_v012.json"
OUT_REPORT = ROOT / "analysis_outputs" / "calibration_report_v012.md"


def softmax(scores, temp):
    t = max(1e-6, float(temp))
    vals = {k: float(v) / t for k, v in scores.items()}
    m = max(vals.values())
    exps = {k: math.exp(v - m) for k, v in vals.items()}
    s = sum(exps.values())
    return {k: exps[k] / s for k in exps}


def category_scores_for(text):
    if not fast_lane.MODEL_READY:
        return {"positive": 0.0, "negative": 0.0, "ambiguous": 0.0, "neutral": 1.0}, False
    all_scores = fast_lane.emotion_pipeline(text[:512])[0]
    cat = fast_lane._aggregate_category_scores(all_scores)
    has_kw = False
    if fast_lane.nlp is not None:
        doc = fast_lane.nlp(text)
        kws = [t.text for t in doc if t.pos_ in ["NOUN", "PROPN"]]
        has_kw = bool(kws)
    return cat, has_kw


def nll_for_temp(dataset, temp):
    total = 0.0
    n = 0
    for x in dataset:
        text = x["text"]
        target = x["target_strategy"]
        cat, has_kw = category_scores_for(text)
        f = merge_policy.compute_confidence_features(cat)
        scores = merge_policy._strategy_scores(f, has_kw, text, llm_eta_ms=getattr(config, "EXPECTED_SLOW_LANE_MS", 0))
        probs = softmax(scores, temp)
        p = max(1e-9, probs.get(target, 1e-9))
        total += -math.log(p)
        n += 1
    return total / max(1, n)


def ece_for_temp(dataset, temp, bins=10):
    bucket = [{"conf": [], "acc": []} for _ in range(bins)]
    for x in dataset:
        text = x["text"]
        target = x["target_strategy"]
        cat, has_kw = category_scores_for(text)
        f = merge_policy.compute_confidence_features(cat)
        scores = merge_policy._strategy_scores(f, has_kw, text, llm_eta_ms=getattr(config, "EXPECTED_SLOW_LANE_MS", 0))
        probs = softmax(scores, temp)
        pred = max(probs, key=probs.get)
        conf = probs[pred]
        correct = 1.0 if pred == target else 0.0
        idx = min(bins - 1, int(conf * bins))
        bucket[idx]["conf"].append(conf)
        bucket[idx]["acc"].append(correct)

    n = len(dataset)
    ece = 0.0
    for b in bucket:
        if not b["conf"]:
            continue
        c = sum(b["conf"]) / len(b["conf"])
        a = sum(b["acc"]) / len(b["acc"])
        ece += (len(b["conf"]) / n) * abs(a - c)
    return ece


def main():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cands = [round(0.5 + i * 0.05, 2) for i in range(51)]  # 0.5~3.0

    best_t = None
    best_nll = 1e9
    for t in cands:
        nll = nll_for_temp(dataset, t)
        if nll < best_nll:
            best_nll = nll
            best_t = t

    before_t = float(getattr(config, "CALIBRATION_TEMPERATURE", 1.0))
    before_nll = nll_for_temp(dataset, before_t)
    before_ece = ece_for_temp(dataset, before_t)
    after_nll = nll_for_temp(dataset, best_t)
    after_ece = ece_for_temp(dataset, best_t)

    OUT_PARAM.write_text(json.dumps({
        "version": "v01.2",
        "best_temperature": best_t,
        "objective": "min_nll",
        "dataset_size": len(dataset)
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(
        "\n".join([
            "# Calibration Report v01.2",
            "",
            f"- dataset size: {len(dataset)}",
            f"- default temperature: {before_t}",
            f"- fitted temperature: {best_t}",
            f"- NLL (before): {before_nll:.6f}",
            f"- NLL (after): {after_nll:.6f}",
            f"- ECE (before): {before_ece:.6f}",
            f"- ECE (after): {after_ece:.6f}",
            "",
            "## Note",
            "- Temperature scaling calibrates confidence without changing model architecture.",
            "- Runtime overhead is negligible (single scalar operation in softmax temperature).",
        ]),
        encoding="utf-8",
    )

    print(f"best_temperature={best_t}")
    print(f"report={OUT_REPORT}")
    print(f"params={OUT_PARAM}")


if __name__ == "__main__":
    main()
