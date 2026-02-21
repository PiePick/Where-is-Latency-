import math


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


def select_strategy(category_scores, has_keyword, user_text, llm_eta_ms=0):
    f = compute_confidence_features(category_scores)
    band = confidence_band(f["top1"], f["margin"], f["entropy"])

    question_flag = str(user_text).strip().endswith("?")
    if llm_eta_ms >= 2200:
        strategy = "bridge"
    elif band == "low":
        strategy = "neutral_minimal"
    elif question_flag and has_keyword:
        strategy = "echo_first"
    elif band == "high" and f["top1_label"] in {"positive", "negative"}:
        strategy = "emotion_first"
    elif has_keyword and band == "medium":
        strategy = "echo_first"
    elif f["top1_label"] == "ambiguous":
        strategy = "bridge"
    else:
        strategy = "neutral_minimal"

    f["confidence_band"] = band
    f["strategy"] = strategy
    return f
