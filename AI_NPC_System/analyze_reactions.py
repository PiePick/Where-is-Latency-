import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import fast_lane

TEST_TEXTS = [
    "I passed the exam and I feel amazing.",
    "I am scared about tomorrow's interview.",
    "I am just drinking water now.",
    "My friend ignored my message and I feel sad.",
    "Wow, I didn't expect this at all.",
    "Can you explain this one more time?",
    "Everything is fine, just a normal day.",
    "I am angry because my work got rejected.",
    "I feel curious about this project idea.",
    "I am relieved that the surgery ended well.",
]


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "analysis_outputs"
    ensure_dir(out_dir)

    rows = []
    for t in TEST_TEXTS:
        r = fast_lane.analyze_and_react(t)
        row = {
            "text": t,
            "emotion_label": r.get("emotion_label"),
            "strategy": r.get("strategy"),
            "reaction": r.get("reaction"),
            "echo_text": r.get("echo_text"),
            "confidence_band": r.get("confidence_band"),
            "top1": r.get("top1"),
            "margin": r.get("margin"),
            "entropy": r.get("entropy"),
            "action_probs": json.dumps(r.get("action_probs", {}), ensure_ascii=False),
        }
        rows.append(row)

    csv_path = out_dir / "reaction_analysis_v01.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # markdown table summary
    strategy_cnt = Counter([r["strategy"] for r in rows])
    emotion_cnt = Counter([r["emotion_label"] for r in rows])

    md_path = out_dir / "reaction_analysis_v01.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Reaction Analysis v01\n\n")
        f.write("## Strategy Count\n")
        for k, v in strategy_cnt.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n## Emotion Count\n")
        for k, v in emotion_cnt.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n## Per-turn Table\n\n")
        f.write("| text | emotion | strategy | reaction | top1 | margin | entropy |\n")
        f.write("|---|---|---|---|---:|---:|---:|\n")
        for r in rows:
            text = r["text"].replace("|", " ")
            reaction = str(r["reaction"]).replace("|", " ")
            f.write(
                f"| {text} | {r['emotion_label']} | {r['strategy']} | {reaction} | {r['top1']} | {r['margin']} | {r['entropy']} |\n"
            )

    # graph
    png_path = out_dir / "reaction_strategy_distribution_v01.png"
    try:
        import matplotlib.pyplot as plt

        labels = list(strategy_cnt.keys())
        values = [strategy_cnt[k] for k in labels]
        plt.figure(figsize=(8, 4))
        plt.bar(labels, values)
        plt.title("Fast-track Strategy Distribution (v01)")
        plt.xlabel("Strategy")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.close()
        print(f"graph: {png_path}")
    except Exception as e:
        print(f"graph skipped: {e}")

    print(f"csv: {csv_path}")
    print(f"md: {md_path}")


if __name__ == "__main__":
    main()
