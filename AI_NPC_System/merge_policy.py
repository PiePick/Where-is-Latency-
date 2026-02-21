import math
import random


ACTIONS = ["emotion_first", "echo_first", "bridge", "neutral_minimal"]


def safe_entropy(prob_map):
    vals = [max(0.0, float(v)) for v in prob_map.values()]
    s = sum(vals)
    if s <= 0:
        return 1.0
    h = 0.0
    for v in vals:
        p = v / s
        if p > 0:
            h -= p * math.log(p, 2)
    max_h = math.log(len(vals), 2) if len(vals) > 1 else 1.0
    return h / max_h if max_h > 0 else 0.0


def compute_confidence_features(category_scores):
    items = sorted(category_scores.items(), key=lambda kv: kv[1], reverse=True)
    if not items:
        return {
            "top1_label": "neutral",
            "top1": 0.0,
            "top2": 0.0,
            "margin": 0.0,
            "entropy": 1.0,
        }

    top1_label, top1 = items[0]
    top2 = items[1][1] if len(items) > 1 else 0.0
    margin = float(top1) - float(top2)
    entropy = safe_entropy(category_scores)
    return {
        "top1_label": top1_label,
        "top1": float(top1),
        "top2": float(top2),
        "margin": float(margin),
        "entropy": float(entropy),
    }


def confidence_band(top1, margin, entropy):
    if top1 >= 0.62 and margin >= 0.25 and entropy <= 0.50:
        return "high"
    if top1 >= 0.50 and margin >= 0.10 and entropy <= 0.75:
        return "medium"
    return "low"


def _softmax(score_map, temperature=1.0):
    t = max(1e-6, float(temperature))
    vals = {k: float(v) / t for k, v in score_map.items()}
    m = max(vals.values()) if vals else 0.0
    exps = {k: math.exp(v - m) for k, v in vals.items()}
    s = sum(exps.values())
    if s <= 0:
        return {k: 1.0 / len(score_map) for k in score_map}
    return {k: exps[k] / s for k in exps}


def _weighted_choice(prob_map):
    r = random.random()
    cum = 0.0
    for k, p in prob_map.items():
        cum += p
        if r <= cum:
            return k
    return list(prob_map.keys())[-1]


def _strategy_scores(features, has_keyword, user_text, llm_eta_ms=0):
    top1 = features["top1"]
    margin = features["margin"]
    entropy = features["entropy"]
    top1_label = features["top1_label"]

    question_flag = str(user_text).strip().endswith("?")
    eta_pressure = min(1.5, max(0.0, (float(llm_eta_ms) - 1200.0) / 1200.0))

    scores = {k: 0.0 for k in ACTIONS}

    # emotion_first: high confidence + clear positive/negative
    scores["emotion_first"] = (1.8 * top1) + (1.2 * margin) - (1.0 * entropy)
    if top1_label in {"positive", "negative"}:
        scores["emotion_first"] += 0.6

    # echo_first: question/keyword driven
    scores["echo_first"] = (1.0 * margin) + (0.6 * top1) - (0.4 * entropy)
    if has_keyword:
        scores["echo_first"] += 0.7
    if question_flag:
        scores["echo_first"] += 0.5

    # bridge: uncertainty or high ETA pressure
    scores["bridge"] = (1.2 * entropy) + (1.1 * eta_pressure) - (0.4 * margin)
    if top1_label == "ambiguous":
        scores["bridge"] += 0.4

    # neutral_minimal: low confidence / neutral content
    scores["neutral_minimal"] = (1.1 * entropy) + (0.7 * (1 - top1))
    if top1_label == "neutral":
        scores["neutral_minimal"] += 0.5
    if not has_keyword:
        scores["neutral_minimal"] += 0.2

    return scores


def select_strategy(
    category_scores,
    has_keyword,
    user_text,
    llm_eta_ms=0,
    temperature=0.9,
    sample=True,
    calibration_temp=1.0,
):
    f = compute_confidence_features(category_scores)
    band = confidence_band(f["top1"], f["margin"], f["entropy"])

    scores = _strategy_scores(f, has_keyword, user_text, llm_eta_ms=llm_eta_ms)
    effective_temp = max(1e-6, float(temperature) * float(calibration_temp))
    probs = _softmax(scores, temperature=effective_temp)

    if sample:
        strategy = _weighted_choice(probs)
    else:
        strategy = max(probs, key=probs.get)

    f["confidence_band"] = band
    f["strategy"] = strategy
    f["strategy_scores"] = {k: round(v, 6) for k, v in scores.items()}
    f["action_probs"] = {k: round(v, 6) for k, v in probs.items()}
    f["calibration_temp"] = round(float(calibration_temp), 6)
    f["effective_temperature"] = round(float(effective_temp), 6)
    return f
