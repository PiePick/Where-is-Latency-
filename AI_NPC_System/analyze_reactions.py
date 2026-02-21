import csv
from pathlib import Path

import fast_lane

TEST_TEXTS = [
    "I just got promoted at work and I feel amazing.",
    "I am really upset because my best friend ignored me.",
    "I am drinking water and reading emails right now.",
    "I feel terrified about tomorrow.",
    "That was a wonderful surprise for me.",
    "Can you explain this again?",
    "I feel confused and not sure what to do.",
    "Everything is normal and calm today.",
]


FIELDS = [
    "text",
    "emotion_label",
    "strategy",
    "reaction",
    "echo_text",
    "confidence_band",
    "top1",
    "margin",
    "entropy",
    "calibration_temp",
    "effective_temperature",
    "p_emotion_first",
    "p_echo_first",
    "p_bridge",
    "p_neutral_minimal",
]


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def run_tests():
    rows = []
    for t in TEST_TEXTS:
        r = fast_lane.analyze_and_react(t)
        probs = r.get("action_probs", {}) or {}
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
            "calibration_temp": r.get("calibration_temp"),
            "effective_temperature": r.get("effective_temperature"),
            "p_emotion_first": probs.get("emotion_first"),
            "p_echo_first": probs.get("echo_first"),
            "p_bridge": probs.get("bridge"),
            "p_neutral_minimal": probs.get("neutral_minimal"),
        }
        rows.append(row)
    return rows


def write_outputs(rows, out_dir: Path):
    csv_path = out_dir / "reaction_analysis_v01.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    md_path = out_dir / "reaction_analysis_v01.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Reaction Analysis v01 (Detailed)\n\n")
        f.write("| text | emotion | strategy | reaction | echo | top1 | margin | entropy | calib_T | eff_T | p(emotion) | p(echo) | p(bridge) | p(neutral) |\n")
        f.write("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for r in rows:
            text = str(r['text']).replace('|', ' ')
            reaction = str(r['reaction']).replace('|', ' ')
            echo = str(r['echo_text']).replace('|', ' ')
            f.write(
                f"| {text} | {r['emotion_label']} | {r['strategy']} | {reaction} | {echo} | {r['top1']} | {r['margin']} | {r['entropy']} | {r['calibration_temp']} | {r['effective_temperature']} | {r['p_emotion_first']} | {r['p_echo_first']} | {r['p_bridge']} | {r['p_neutral_minimal']} |\n"
            )

    png_path = out_dir / "reaction_strategy_distribution_v01.png"
    try:
        import matplotlib.pyplot as plt
        from collections import Counter

        cnt = Counter([r["strategy"] for r in rows])
        labels = list(cnt.keys())
        values = [cnt[k] for k in labels]

        plt.figure(figsize=(8, 4))
        plt.bar(labels, values)
        plt.title("Fast-track Strategy Distribution (v01)")
        plt.xlabel("Strategy")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(png_path)
        plt.close()
    except Exception as e:
        print(f"graph skipped: {e}")

    return csv_path, md_path, png_path


def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "analysis_outputs"
    ensure_dir(out_dir)
    rows = run_tests()
    csv_path, md_path, png_path = write_outputs(rows, out_dir)
    print(f"csv: {csv_path}")
    print(f"md: {md_path}")
    print(f"png: {png_path}")


if __name__ == "__main__":
    main()
