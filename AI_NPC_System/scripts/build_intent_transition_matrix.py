"""Build a data-derived intent transition matrix from raw SWDA files.

The matrix estimates how a VTuber response intent should follow a user's
detected intent. It counts adjacent utterance pairs from the same conversation
only when the speaker changes, then normalizes the target-label counts.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DEFAULT_SWDA_ZIP = PROJECT_ROOT / "reaction_sources" / "swda" / "swda.zip"
DEFAULT_JSON = ROOT / "reports" / "intent_transition_matrix_from_swda.json"
DEFAULT_MD = ROOT / "reports" / "intent_transition_matrix_from_swda.md"

INTENTS = ("QUESTION", "INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")

SWDA_TO_COARSE = {
    "qw": "QUESTION",
    "qy": "QUESTION",
    "qo": "QUESTION",
    "qh": "QUESTION",
    "sd": "INFORM",
    "sv": "INFORM",
    "b": "ACKNOWLEDGE",
    "bh": "ACKNOWLEDGE",
    "ny": "ACKNOWLEDGE",
    "nn": "ACKNOWLEDGE",
    "ad": "DIRECTIVE",
    "co": "DIRECTIVE",
    "fc": "EXPRESSIVE",
    "fp": "EXPRESSIVE",
    "fa": "EXPRESSIVE",
    "ft": "EXPRESSIVE",
    "ar": "REJECT",
    "nd": "REJECT",
}


@dataclass(frozen=True)
class Utterance:
    conversation_no: str
    transcript_index: int
    caller: str
    raw_tag: str
    coarse_label: str
    text: str


def normalize_swda_tag(raw_tag: str) -> str:
    """Return the first usable SWDA act tag from compound annotations."""
    tag = str(raw_tag or "").strip().lower()
    if not tag:
        return ""
    tag = tag.split("^", 1)[0]
    tag = tag.split(".", 1)[0]
    return tag


def map_swda_tag(raw_tag: str) -> str | None:
    """Map an SWDA act tag to the six FastTrack coarse intents."""
    return SWDA_TO_COARSE.get(normalize_swda_tag(raw_tag))


def read_swda_utterances(swda_zip: Path) -> list[Utterance]:
    """Read mapped utterances from the raw SWDA zip archive."""
    utterances: list[Utterance] = []
    with zipfile.ZipFile(swda_zip) as archive:
        names = sorted(
            name for name in archive.namelist()
            if name.startswith("swda/") and name.endswith(".utt.csv")
        )
        for name in names:
            with archive.open(name) as raw_file:
                text_file = io.TextIOWrapper(raw_file, encoding="utf-8", errors="replace", newline="")
                for row in csv.DictReader(text_file):
                    coarse = map_swda_tag(row.get("act_tag", ""))
                    if coarse is None:
                        continue
                    try:
                        transcript_index = int(row.get("transcript_index") or 0)
                    except ValueError:
                        transcript_index = 0
                    utterances.append(
                        Utterance(
                            conversation_no=str(row.get("conversation_no", "")).strip(),
                            transcript_index=transcript_index,
                            caller=str(row.get("caller", "")).strip(),
                            raw_tag=str(row.get("act_tag", "")).strip(),
                            coarse_label=coarse,
                            text=str(row.get("text", "")).strip(),
                        )
                    )
    utterances.sort(key=lambda item: (item.conversation_no, item.transcript_index))
    return utterances


def build_transition_counts(utterances: list[Utterance]) -> tuple[dict[str, Counter[str]], int, int]:
    """Count cross-speaker adjacent coarse-label transitions."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    total_adjacent = 0
    total_cross_speaker = 0
    previous: Utterance | None = None

    for current in utterances:
        if previous and previous.conversation_no == current.conversation_no:
            total_adjacent += 1
            if previous.caller != current.caller:
                counts[previous.coarse_label][current.coarse_label] += 1
                total_cross_speaker += 1
        previous = current

    for intent in INTENTS:
        counts.setdefault(intent, Counter())
    return counts, total_adjacent, total_cross_speaker


def normalize_counts(counts: dict[str, Counter[str]], smoothing: float = 1.0) -> dict[str, dict[str, float]]:
    """Normalize counts into a probability matrix with additive smoothing."""
    matrix: dict[str, dict[str, float]] = {}
    for source in INTENTS:
        smoothed = {target: counts[source][target] + smoothing for target in INTENTS}
        total = sum(smoothed.values())
        matrix[source] = {target: round(value / total, 6) for target, value in smoothed.items()}
    return matrix


def write_markdown_report(
    path: Path,
    *,
    source_zip: Path,
    utterance_count: int,
    total_adjacent: int,
    total_cross_speaker: int,
    counts: dict[str, Counter[str]],
    matrix: dict[str, dict[str, float]],
) -> None:
    """Write a compact method and result report for paper archiving."""
    lines = [
        "# SWDA 기반 의도 전이 행렬 산출 기록",
        "",
        "## 목적",
        "사용자 의도 라벨을 FastTrack 응답 의도로 그대로 복사하지 않기 위해, 실제 대화에서 관찰되는 인접 화자 전환 패턴을 전이 확률로 산출한다.",
        "",
        "## 데이터 및 산출 방식",
        f"- 원본 데이터: `{source_zip}`",
        "- 입력 단위: Switchboard Dialog Act Corpus의 `.utt.csv` 발화 행",
        "- 사용 라벨: QUESTION, INFORM, ACKNOWLEDGE, DIRECTIVE, EXPRESSIVE, REJECT",
        "- 제외 기준: 6개 coarse intent로 매핑되지 않는 SWDA act tag",
        "- 전이 기준: 동일 conversation 안에서 transcript_index 순서상 인접하고 caller가 바뀐 발화쌍",
        "- 정규화: target intent count에 additive smoothing 1.0 적용 후 행 단위 확률화",
        "",
        "## 규모",
        f"- 매핑된 발화 수: {utterance_count}",
        f"- 동일 대화 내 인접 발화쌍 수: {total_adjacent}",
        f"- 화자 전환 인접 발화쌍 수: {total_cross_speaker}",
        "",
        "## 전이 행렬",
        "| user_intent | response_intent 확률 | 관측 전이 수 |",
        "| --- | --- | --- |",
    ]
    for source in INTENTS:
        probs = ", ".join(f"{target}: {matrix[source][target]:.3f}" for target in INTENTS)
        observed = ", ".join(f"{target}: {counts[source][target]}" for target in INTENTS)
        lines.append(f"| {source} | {probs} | {observed} |")

    lines.extend(
        [
            "",
            "## 해석상 주의",
            "이 행렬은 SWDA 대화쌍의 화자 전환 통계에서 직접 산출한 초기 전이 정책이다. 실제 VTuber 방송 문맥에서는 채팅 밀도, 도네이션, 화면 상황, 캐릭터 성격에 따라 보정이 필요하다.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_payload(swda_zip: Path, smoothing: float) -> dict[str, object]:
    utterances = read_swda_utterances(swda_zip)
    counts, total_adjacent, total_cross_speaker = build_transition_counts(utterances)
    matrix = normalize_counts(counts, smoothing=smoothing)
    return {
        "method": "cross_speaker_adjacent_transitions",
        "source": str(swda_zip),
        "label_set": list(INTENTS),
        "smoothing": smoothing,
        "utterance_count": len(utterances),
        "same_conversation_adjacent_pairs": total_adjacent,
        "cross_speaker_adjacent_pairs": total_cross_speaker,
        "counts": {source: {target: counts[source][target] for target in INTENTS} for source in INTENTS},
        "matrix": matrix,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swda-zip", type=Path, default=DEFAULT_SWDA_ZIP)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--smoothing", type=float, default=1.0)
    args = parser.parse_args()

    payload = build_payload(args.swda_zip, args.smoothing)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = {
        source: Counter(payload["counts"][source])  # type: ignore[index]
        for source in INTENTS
    }
    write_markdown_report(
        args.output_md,
        source_zip=args.swda_zip,
        utterance_count=int(payload["utterance_count"]),
        total_adjacent=int(payload["same_conversation_adjacent_pairs"]),
        total_cross_speaker=int(payload["cross_speaker_adjacent_pairs"]),
        counts=counts,
        matrix=payload["matrix"],  # type: ignore[arg-type]
    )

    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")


if __name__ == "__main__":
    main()
