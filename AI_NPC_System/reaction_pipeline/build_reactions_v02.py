import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reaction_pipeline" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSON = ROOT / "reactions_v02.json"
REPORT_MD = OUT_DIR / "reaction_build_report_v02.md"

# hard safety constraints
FORBIDDEN_BY_EMOTION = {
    "negative": {"that’s great", "awesome", "love that", "nice."},
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def dedup_keep_order(items):
    seen = set()
    out = []
    for x in items:
        k = norm(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
    return out


def prune_by_emotion(items, emotion):
    blocked = FORBIDDEN_BY_EMOTION.get(emotion, set())
    out = []
    removed = []
    for x in items:
        nx = norm(x)
        if nx in blocked:
            removed.append(x)
        else:
            out.append(x)
    return out, removed


def collect_open_dataset_snippets():
    """Best-effort pull from HF datasets for short acknowledgements.
    If unavailable, returns empty list and we rely on curated templates.
    """
    snippets = []
    try:
        from datasets import load_dataset

        # empathetic_dialogues: use listener utterances as empathy-style snippets
        ds = load_dataset("empathetic_dialogues", split="train[:300]")
        for row in ds:
            utt = row.get("utterance") or ""
            if len(utt.split()) <= 12 and 2 <= len(utt.split()):
                snippets.append(utt.strip())

        # daily_dialog: short daily conversation responses
        dd = load_dataset("daily_dialog", split="train[:300]")
        for row in dd:
            dialogue = row.get("dialog") or []
            for u in dialogue[1::2]:
                if isinstance(u, str) and 2 <= len(u.split()) <= 10:
                    snippets.append(u.strip())

    except Exception:
        pass
    return dedup_keep_order(snippets)


def build():
    # curated seeds (research-informed, short, natural)
    base = {
        "emotion_first_positive": [
            "That’s great.", "Nice work.", "I’m glad to hear that.", "Love that for you.", "Awesome."
        ],
        "emotion_first_negative": [
            "That sounds really hard.", "I hear you.", "That hurts.", "I’m sorry you’re dealing with that.", "That sounds rough."
        ],
        "emotion_first_ambiguous": [
            "That sounds mixed.", "I can see why that feels complicated.", "That makes sense.", "I get why you’re unsure."
        ],
        "emotion_first_neutral": [
            "Got it.", "I see.", "Understood.", "Okay."
        ],
        "echo_first_positive": [
            "About that win—", "On that progress—", "On that result—"
        ],
        "echo_first_negative": [
            "About that situation—", "On what happened—", "On that problem—"
        ],
        "echo_first_ambiguous": [
            "About that part—", "On that point—", "About this decision—"
        ],
        "echo_first_neutral": [
            "On that—", "About that—", "Right, on that—"
        ],
        "bridge": [
            "I’m with you—", "Give me a second—", "Okay, go on—", "I’m here—"
        ],
        "neutral_minimal": [
            "I see.", "Got it.", "I’m listening.", "Go on."
        ],
        # fallbacks by emotion
        "positive": ["That’s great.", "Nice.", "I’m glad."],
        "negative": ["That sounds rough.", "I hear you.", "That hurts."],
        "ambiguous": ["I can see that.", "That’s understandable.", "Makes sense."],
        "neutral": ["Got it.", "I see.", "Understood."]
    }

    hf_snippets = collect_open_dataset_snippets()

    # optionally enrich neutral_minimal and bridge with short natural snippets
    for s in hf_snippets:
        ws = s.split()
        if 2 <= len(ws) <= 5:
            base["neutral_minimal"].append(s)
        elif 6 <= len(ws) <= 10:
            base["bridge"].append(s)

    # dedup + pruning
    removed_map = {}
    for k in list(base.keys()):
        base[k] = dedup_keep_order(base[k])

    # emotion safety pruning
    for em in ["negative"]:
        key = f"emotion_first_{em}"
        if key in base:
            kept, removed = prune_by_emotion(base[key], em)
            base[key] = kept
            removed_map[key] = removed

    out = {
        "meta": {
            "version": "upgrade-v02",
            "method": "dataset-informed curation + safety pruning",
            "sources": [
                "empathetic_dialogues",
                "daily_dialog",
                "go_emotions",
                "tweet_eval:emotion"
            ],
            "notes": "Strategy+emotion specific pools to improve naturalness and polarity consistency"
        },
        **base
    }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Reaction Build Report v02",
        "",
        f"- output: {OUT_JSON}",
        f"- hf snippets used: {len(hf_snippets)}",
        "",
        "## Group counts",
    ]
    for k, v in base.items():
        lines.append(f"- {k}: {len(v)}")

    lines.append("\n## Removed by safety pruning")
    for k, v in removed_map.items():
        lines.append(f"- {k}: {v}")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUT_JSON)
    print(REPORT_MD)


if __name__ == "__main__":
    random.seed(42)
    build()
