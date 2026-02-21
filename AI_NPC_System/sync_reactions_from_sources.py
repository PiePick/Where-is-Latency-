import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reaction_sources" / "reaction_candidates_v01.json"
DST = Path(__file__).resolve().parent / "reactions_v01.json"


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    out = {
        "meta": {"version": "upgrade-v01", "source": str(SRC)},
        "emotion_first": data.get("positive", [])[:2] + data.get("negative", [])[:2],
        "echo_first": ["Got it—", "Okay, about that—", "Right, on that—"],
        "bridge": data.get("bridge", []),
        "neutral_minimal": data.get("neutral", [])[:4],
        "positive": data.get("positive", []),
        "negative": data.get("negative", []),
        "ambiguous": data.get("ambiguous", []),
        "neutral": data.get("neutral", []),
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"synced: {DST}")


if __name__ == "__main__":
    main()
