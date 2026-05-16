"""FastTrack dual classifier pipeline for an AI VTuber backend.

This single script contains:
1. GoEmotions preprocessing for a 28-label to 4-label emotion taxonomy.
2. SWDA preprocessing for a 42-label to 6-label dialog-act taxonomy.
3. Few-shot SetFit-MiniLM fine-tuning on a small SWDA sample.
4. Async dual inference with DistilBERT emotion and SetFit dialog-act models.
5. FAISS cosine-similarity routing over dummy FastTrack reaction candidates.

Example training:
    python fasttrack_dual_classifier_pipeline.py train-setfit --samples-per-label 180

Example inference:
    python fasttrack_dual_classifier_pipeline.py infer --text "Wait, why did that happen?"
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import random
import re
import sys
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTENT_MODEL_DIR = ROOT / "models" / "setfit_swda_intent_minilm"
DEFAULT_DISTILBERT_EMOTION_MODEL = "./my_distilbert_emotion"
DEFAULT_DISTILBERT_FALLBACK_MODEL = "joeddav/distilbert-base-uncased-go-emotions-student"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_SWDA_ZIP_URL = "https://github.com/cgpotts/swda/raw/master/swda.zip"
DEFAULT_SWDA_ZIP = ROOT.parent / "reaction_sources" / "swda" / "swda.zip"

GOEMOTION_TARGETS = ("POSITIVE", "NEGATIVE", "SURPRISE", "NEUTRAL")
SWDA_TARGETS = ("QUESTION", "INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT")

GOEMOTION_POSITIVE = {"amusement", "joy", "excitement", "admiration", "approval", "love"}
GOEMOTION_NEGATIVE = {
    "anger",
    "annoyance",
    "disapproval",
    "disgust",
    "sadness",
    "disappointment",
}
GOEMOTION_SURPRISE = {"surprise", "confusion", "curiosity"}

SWDA_QUESTION = {"qw", "qy", "qo", "qh"}
SWDA_INFORM = {"sd", "sv"}
SWDA_ACKNOWLEDGE = {"b", "bh", "ny", "nn"}
SWDA_DIRECTIVE = {"ad", "co"}
SWDA_EXPRESSIVE = {"fc", "fp", "fa", "ft"}
SWDA_REJECT = {"ar", "nd"}

DEFAULT_DUMMY_REACTIONS = [
    "아 진짜?",
    "어디 보자...",
    "왜 그러지?",
    "잠깐만.",
    "그건 좀 놀라운데?",
    "맞아, 들었어.",
    "흠, 이해했어.",
    "그럴 수도 있겠다.",
    "조금 더 말해줘.",
    "아, 그런 느낌이구나.",
]


@dataclass(frozen=True)
class ClassificationResult:
    """A single classifier result with label and confidence."""

    label: str
    confidence: float
    scores: dict[str, float]
    latency_ms: float


@dataclass(frozen=True)
class RoutedReaction:
    """One FAISS-routed FastTrack reaction candidate."""

    text: str
    score: float
    index: int


def normalize_swda_tag(raw_tag: str) -> str:
    """Normalize a detailed SWDA tag into the base tag used in mapping rules."""
    tag = str(raw_tag).strip().lower()
    tag = tag.split("+", 1)[0]
    tag = tag.split(".", 1)[0]
    return tag


def map_goemotion_label(label: str) -> str:
    """Map one GoEmotions fine label into the 4-label FastTrack taxonomy."""
    label = str(label).strip().lower()
    if label in GOEMOTION_POSITIVE:
        return "POSITIVE"
    if label in GOEMOTION_NEGATIVE:
        return "NEGATIVE"
    if label in GOEMOTION_SURPRISE:
        return "SURPRISE"
    return "NEUTRAL"


def map_swda_dialog_act(tag: str, *, unknown_policy: str = "exclude") -> str | None:
    """Map one SWDA dialog-act tag into the 6-label intent taxonomy."""
    tag = normalize_swda_tag(tag)
    if tag in SWDA_QUESTION:
        return "QUESTION"
    if tag in SWDA_INFORM:
        return "INFORM"
    if tag in SWDA_ACKNOWLEDGE:
        return "ACKNOWLEDGE"
    if tag in SWDA_DIRECTIVE:
        return "DIRECTIVE"
    if tag in SWDA_EXPRESSIVE:
        return "EXPRESSIVE"
    if tag in SWDA_REJECT:
        return "REJECT"
    if unknown_policy == "expressive":
        return "EXPRESSIVE"
    return None


def clean_text(text: Any) -> str:
    """Normalize whitespace and drop empty transcript fragments."""
    if text is None:
        return ""
    return " ".join(str(text).replace("\n", " ").split()).strip()


def clean_swda_text(text: Any) -> str:
    """Normalize common SWDA transcript markup into plain utterance text."""
    cleaned = clean_text(text)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    cleaned = cleaned.replace("+", " ").replace("--", " ")
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return " ".join(cleaned.split()).strip()


def load_go_emotions(split: str = "train") -> Dataset:
    """Load GoEmotions from Hugging Face with a stable fallback name."""
    from datasets import load_dataset

    try:
        return load_dataset("google-research-datasets/go_emotions", "simplified", split=split)
    except Exception:
        return load_dataset("go_emotions", "simplified", split=split)


def load_swda(split: str = "train") -> Dataset | DatasetDict:
    """Load SWDA from Hugging Face datasets."""
    from datasets import load_dataset

    try:
        return load_dataset("swda", split=split)
    except Exception:
        return load_dataset("swda")


def download_swda_zip(zip_path: Path = DEFAULT_SWDA_ZIP, url: str = DEFAULT_SWDA_ZIP_URL) -> Path:
    """Download the public cgpotts SWDA archive when Hugging Face loading fails."""
    if zip_path.exists() and zip_path.stat().st_size > 0:
        return zip_path
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, zip_path)
    return zip_path


def preprocess_swda_from_zip(
    *,
    zip_path: Path = DEFAULT_SWDA_ZIP,
    unknown_policy: str = "exclude",
    max_words: int | None = None,
) -> pd.DataFrame:
    """Read SWDA utterance CSV files directly from the cgpotts archive."""
    import pandas as pd

    zip_path = download_swda_zip(zip_path)
    rows = []
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".utt.csv")]
        for name in names:
            with archive.open(name) as handle:
                text_stream = io.TextIOWrapper(handle, encoding="utf-8", errors="replace")
                reader = csv.DictReader(text_stream)
                for raw in reader:
                    text = clean_swda_text(raw.get("text", ""))
                    if not text:
                        continue
                    if max_words is not None and len(text.split()) > max_words:
                        continue
                    raw_tag = raw.get("act_tag", "")
                    coarse = map_swda_dialog_act(raw_tag, unknown_policy=unknown_policy)
                    if coarse is None:
                        continue
                    rows.append(
                        {
                            "text": text,
                            "coarse_label": coarse,
                            "source": "swda_cgpotts_zip",
                            "raw_dialog_act": str(raw_tag),
                        }
                    )
    return pd.DataFrame(rows)


def get_label_names(dataset: Dataset, label_column: str) -> list[str]:
    """Read class names from a Hugging Face ClassLabel or Sequence feature."""
    feature = dataset.features[label_column]
    if hasattr(feature, "feature") and hasattr(feature.feature, "names"):
        return list(feature.feature.names)
    if hasattr(feature, "names"):
        return list(feature.names)
    raise ValueError(f"Could not recover label names from column: {label_column}")


def first_existing_column(columns: Iterable[str], candidates: Iterable[str]) -> str:
    """Return the first candidate column that exists."""
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    raise ValueError(f"None of these columns exist: {list(candidates)}")


def goemotion_example_to_label(example: dict[str, Any], label_names: list[str]) -> str:
    """Map a GoEmotions example to one coarse string label."""
    labels = example.get("labels")
    if labels is None:
        labels = example.get("label")
    if labels is None:
        return "NEUTRAL"
    if not isinstance(labels, list):
        labels = [labels]

    coarse_labels = []
    for label_id in labels:
        try:
            fine_label = label_names[int(label_id)]
        except Exception:
            fine_label = str(label_id)
        coarse_labels.append(map_goemotion_label(fine_label))

    for target in GOEMOTION_TARGETS:
        if target in coarse_labels:
            return target
    return "NEUTRAL"


def preprocess_go_emotions(split: str = "train") -> pd.DataFrame:
    """Load and preprocess GoEmotions into text/coarse_label rows."""
    import pandas as pd

    dataset = load_go_emotions(split)
    text_column = first_existing_column(dataset.column_names, ("text", "utterance"))
    label_column = first_existing_column(dataset.column_names, ("labels", "label"))
    label_names = get_label_names(dataset, label_column)

    rows = []
    for example in dataset:
        text = clean_text(example.get(text_column))
        if not text:
            continue
        rows.append(
            {
                "text": text,
                "coarse_label": goemotion_example_to_label(example, label_names),
                "source": "go_emotions",
            }
        )
    return pd.DataFrame(rows)


def preprocess_swda(
    split: str = "train",
    *,
    unknown_policy: str = "exclude",
    max_words: int | None = None,
) -> pd.DataFrame:
    """Load and preprocess SWDA into text/coarse_label rows."""
    from datasets import DatasetDict
    import pandas as pd

    try:
        loaded = load_swda(split)
    except Exception as exc:
        print(
            f"HF SWDA loading failed; falling back to cgpotts/swda zip: {exc}",
            file=sys.stderr,
        )
        return preprocess_swda_from_zip(
            unknown_policy=unknown_policy,
            max_words=max_words,
        )
    if isinstance(loaded, DatasetDict):
        if split in loaded:
            dataset = loaded[split]
        else:
            dataset = next(iter(loaded.values()))
    else:
        dataset = loaded

    text_column = first_existing_column(dataset.column_names, ("text", "utterance", "transcript"))
    tag_column = first_existing_column(
        dataset.column_names,
        ("act_tag", "damsl_act_tag", "dialog_act", "da_tag", "label"),
    )

    rows = []
    for example in dataset:
        text = clean_text(example.get(text_column))
        if not text:
            continue
        if max_words is not None and len(text.split()) > max_words:
            continue
        coarse = map_swda_dialog_act(example.get(tag_column), unknown_policy=unknown_policy)
        if coarse is None:
            continue
        rows.append(
            {
                "text": text,
                "coarse_label": coarse,
                "source": "swda",
                "raw_dialog_act": str(example.get(tag_column)),
            }
        )
    return pd.DataFrame(rows)


def sample_few_shot_dataframe(
    swda_df: pd.DataFrame,
    *,
    samples_per_label: int = 180,
    seed: int = 42,
) -> pd.DataFrame:
    """Sample 150-200 rows per coarse SWDA label for SetFit fine-tuning."""
    import pandas as pd

    if not 150 <= samples_per_label <= 200:
        raise ValueError("samples_per_label must be between 150 and 200.")

    sampled_frames = []
    for label in SWDA_TARGETS:
        label_df = swda_df[swda_df["coarse_label"] == label]
        if label_df.empty:
            raise ValueError(f"No SWDA rows found for label: {label}")
        n = min(samples_per_label, len(label_df))
        sampled_frames.append(label_df.sample(n=n, random_state=seed))

    sampled = pd.concat(sampled_frames, ignore_index=True)
    return sampled.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def dataframe_to_setfit_dataset(df: pd.DataFrame) -> tuple[Dataset, dict[str, int], dict[int, str]]:
    """Convert a pandas DataFrame into a SetFit-compatible Dataset."""
    label_to_id = {label: index for index, label in enumerate(SWDA_TARGETS)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    records = [
        {"text": row["text"], "label": label_to_id[row["coarse_label"]]}
        for _, row in df.iterrows()
    ]
    from datasets import Dataset

    return Dataset.from_list(records), label_to_id, id_to_label


def train_setfit_intent_model(
    *,
    output_dir: Path = DEFAULT_INTENT_MODEL_DIR,
    samples_per_label: int = 180,
    seed: int = 42,
    unknown_policy: str = "exclude",
    max_words: int | None = 30,
    base_model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 16,
    num_epochs: int = 1,
    num_iterations: int = 5,
) -> Path:
    """Fine-tune SetFit-MiniLM on a small SWDA subset and save it locally."""
    from setfit import SetFitModel, Trainer, TrainingArguments

    swda_df = preprocess_swda(
        "train",
        unknown_policy=unknown_policy,
        max_words=max_words,
    )
    train_df = sample_few_shot_dataframe(
        swda_df,
        samples_per_label=samples_per_label,
        seed=seed,
    )
    train_dataset, label_to_id, id_to_label = dataframe_to_setfit_dataset(train_df)

    output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_json(output_dir / "swda_fewshot_train.jsonl", orient="records", lines=True)

    model = SetFitModel.from_pretrained(base_model, labels=list(SWDA_TARGETS))
    args = TrainingArguments(
        output_dir=str(output_dir / "trainer"),
        batch_size=batch_size,
        num_epochs=num_epochs,
        num_iterations=num_iterations,
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        column_mapping={"text": "text", "label": "label"},
    )
    trainer.train()
    model.save_pretrained(str(output_dir))

    metadata = {
        "base_model": base_model,
        "samples_per_label": samples_per_label,
        "seed": seed,
        "unknown_policy": unknown_policy,
        "max_words": max_words,
        "label_to_id": label_to_id,
        "id_to_label": {str(key): value for key, value in id_to_label.items()},
        "swda_mapping": {
            "QUESTION": sorted(SWDA_QUESTION),
            "INFORM": sorted(SWDA_INFORM),
            "ACKNOWLEDGE": sorted(SWDA_ACKNOWLEDGE),
            "DIRECTIVE": sorted(SWDA_DIRECTIVE),
            "EXPRESSIVE": sorted(SWDA_EXPRESSIVE),
            "REJECT": sorted(SWDA_REJECT),
        },
    }
    (output_dir / "fasttrack_setfit_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_dir


class FastTrackReactionRouter:
    """FAISS cosine-similarity router over FastTrack reaction candidates."""

    def __init__(
        self,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        reactions: list[str] | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.reactions = reactions or list(DEFAULT_DUMMY_REACTIONS)
        self.index = self._build_index(self.reactions)

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Encode and L2-normalize texts so inner product equals cosine similarity."""
        vectors = self.embedding_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.astype("float32")

    def _build_index(self, texts: list[str]) -> Any:
        """Build an in-memory FAISS index."""
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError("Missing dependency: faiss. Install faiss-cpu.") from exc

        vectors = self._embed(texts)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return index

    def search(self, query: str, top_k: int = 3) -> list[RoutedReaction]:
        """Search Top-K reaction candidates by cosine similarity."""
        query_vector = self._embed([query])
        scores, indices = self.index.search(query_vector, top_k)
        results = []
        for score, index in zip(scores[0], indices[0]):
            if int(index) < 0:
                continue
            results.append(
                RoutedReaction(
                    text=self.reactions[int(index)],
                    score=float(score),
                    index=int(index),
                )
            )
        return results


class AsyncDualInferencePipeline:
    """Async DistilBERT emotion + SetFit intent inference with FAISS routing."""

    def __init__(
        self,
        *,
        emotion_model_path: str | Path = DEFAULT_DISTILBERT_EMOTION_MODEL,
        intent_model_path: str | Path = DEFAULT_INTENT_MODEL_DIR,
        embedding_model_name: str = DEFAULT_EMBEDDING_MODEL,
        threshold: float = 0.6,
        device: int = -1,
    ) -> None:
        self.threshold = threshold
        from setfit import SetFitModel
        from transformers import pipeline

        emotion_model_path = Path(emotion_model_path)
        model_name = str(emotion_model_path) if emotion_model_path.exists() else DEFAULT_DISTILBERT_FALLBACK_MODEL
        self.emotion_classifier = pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
            top_k=None,
            device=device,
        )
        self.intent_model = SetFitModel.from_pretrained(str(intent_model_path))
        self.intent_id_to_label = self._load_intent_id_to_label(Path(intent_model_path))
        self.router = FastTrackReactionRouter(embedding_model_name)

    @staticmethod
    def _load_intent_id_to_label(model_dir: Path) -> dict[int, str]:
        """Load SetFit id-to-label metadata when available."""
        metadata_path = model_dir / "fasttrack_setfit_metadata.json"
        if not metadata_path.exists():
            return {index: label for index, label in enumerate(SWDA_TARGETS)}
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return {
            int(key): value for key, value in metadata.get("id_to_label", {}).items()
        }

    def infer_emotion(self, text: str) -> ClassificationResult:
        """Run DistilBERT emotion inference and map into 4 coarse labels."""
        started = time.perf_counter()
        raw = self.emotion_classifier(text)
        scores_by_target = {target: 0.0 for target in GOEMOTION_TARGETS}

        items = raw[0] if raw and isinstance(raw[0], list) else raw
        for item in items:
            fine_label = str(item["label"]).lower()
            coarse = map_goemotion_label(fine_label)
            scores_by_target[coarse] += float(item["score"])

        total = sum(scores_by_target.values()) or 1.0
        normalized = {
            label: round(score / total, 6)
            for label, score in scores_by_target.items()
        }
        label, confidence = max(normalized.items(), key=lambda item: item[1])
        latency_ms = (time.perf_counter() - started) * 1000
        return ClassificationResult(label, float(confidence), normalized, latency_ms)

    def infer_intent(self, text: str) -> ClassificationResult:
        """Run SetFit dialog-act inference."""
        started = time.perf_counter()
        raw_label = self.intent_model.predict([text])[0]
        try:
            label = self.intent_id_to_label.get(int(raw_label), str(raw_label))
        except Exception:
            label = str(raw_label)

        scores: dict[str, float] = {}
        try:
            probabilities = self.intent_model.predict_proba([text])[0]
            for index, score in enumerate(probabilities):
                scores[self.intent_id_to_label.get(index, str(index))] = float(score)
            scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
            confidence = float(scores.get(label, max(scores.values()) if scores else 0.0))
        except Exception:
            confidence = 1.0
            scores = {label: 1.0}

        latency_ms = (time.perf_counter() - started) * 1000
        return ClassificationResult(label, confidence, scores, latency_ms)

    async def analyze_and_route_chat(self, text: str) -> dict[str, Any] | None:
        """Analyze chat text asynchronously and return Top-3 FastTrack candidates."""
        cleaned = clean_text(text)
        if not cleaned:
            return None

        emotion_task = asyncio.to_thread(self.infer_emotion, cleaned)
        intent_task = asyncio.to_thread(self.infer_intent, cleaned)
        emotion, intent = await asyncio.gather(emotion_task, intent_task)

        if emotion.confidence < self.threshold or intent.confidence < self.threshold:
            return None

        route_query = f"{emotion.label} {intent.label}"
        routed = self.router.search(route_query, top_k=3)
        return {
            "text": cleaned,
            "emotion": {
                "label": emotion.label,
                "confidence": round(emotion.confidence, 6),
                "scores": emotion.scores,
                "latency_ms": round(emotion.latency_ms, 3),
            },
            "intent": {
                "label": intent.label,
                "confidence": round(intent.confidence, 6),
                "scores": {key: round(value, 6) for key, value in intent.scores.items()},
                "latency_ms": round(intent.latency_ms, 3),
            },
            "route_query": route_query,
            "top3_reactions": [
                {
                    "text": item.text,
                    "score": round(item.score, 6),
                    "index": item.index,
                }
                for item in routed
            ],
        }


_GLOBAL_PIPELINE: AsyncDualInferencePipeline | None = None


def get_pipeline() -> AsyncDualInferencePipeline:
    """Create one lazy global pipeline for the required async API function."""
    global _GLOBAL_PIPELINE
    if _GLOBAL_PIPELINE is None:
        _GLOBAL_PIPELINE = AsyncDualInferencePipeline()
    return _GLOBAL_PIPELINE


async def analyze_and_route_chat(text: str) -> dict[str, Any] | None:
    """Required async FastTrack function for external runtime integration."""
    return await get_pipeline().analyze_and_route_chat(text)


def parse_args() -> argparse.Namespace:
    """Parse CLI mode and options."""
    parser = argparse.ArgumentParser(description="FastTrack dual classifier pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prep = subparsers.add_parser("prepare-data", help="Preprocess datasets and write JSONL files.")
    prep.add_argument("--output-dir", type=Path, default=ROOT / "prepared_fasttrack_data")
    prep.add_argument("--unknown-policy", choices=("exclude", "expressive"), default="exclude")
    prep.add_argument("--max-words", type=int, default=30)

    train = subparsers.add_parser("train-setfit", help="Fine-tune the SetFit-MiniLM intent model.")
    train.add_argument("--output-dir", type=Path, default=DEFAULT_INTENT_MODEL_DIR)
    train.add_argument("--samples-per-label", type=int, default=180)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--unknown-policy", choices=("exclude", "expressive"), default="exclude")
    train.add_argument("--max-words", type=int, default=30)
    train.add_argument("--base-model", default=DEFAULT_EMBEDDING_MODEL)
    train.add_argument("--batch-size", type=int, default=16)
    train.add_argument("--num-epochs", type=int, default=1)
    train.add_argument("--num-iterations", type=int, default=5)

    infer = subparsers.add_parser("infer", help="Run async dual inference and FAISS routing.")
    infer.add_argument("--text", required=True)
    infer.add_argument("--emotion-model", default=DEFAULT_DISTILBERT_EMOTION_MODEL)
    infer.add_argument("--intent-model", type=Path, default=DEFAULT_INTENT_MODEL_DIR)
    infer.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    infer.add_argument("--threshold", type=float, default=0.6)
    infer.add_argument("--device", type=int, default=-1)

    return parser.parse_args()


def run_prepare_data(args: argparse.Namespace) -> int:
    """Write preprocessed GoEmotions and SWDA data for audit and future reuse."""
    args.output_dir.mkdir(parents=True, exist_ok=True)
    go_df = preprocess_go_emotions("train")
    swda_df = preprocess_swda(
        "train",
        unknown_policy=args.unknown_policy,
        max_words=args.max_words,
    )
    go_path = args.output_dir / "go_emotions_coarse.jsonl"
    swda_path = args.output_dir / "swda_intent_coarse.jsonl"
    go_df.to_json(go_path, orient="records", lines=True, force_ascii=False)
    swda_df.to_json(swda_path, orient="records", lines=True, force_ascii=False)

    summary = {
        "go_emotions_rows": int(len(go_df)),
        "go_emotions_label_counts": go_df["coarse_label"].value_counts().to_dict(),
        "swda_rows": int(len(swda_df)),
        "swda_label_counts": swda_df["coarse_label"].value_counts().to_dict(),
        "go_emotions_path": str(go_path),
        "swda_path": str(swda_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def run_train_setfit(args: argparse.Namespace) -> int:
    """Train and save the SetFit intent model."""
    model_dir = train_setfit_intent_model(
        output_dir=args.output_dir,
        samples_per_label=args.samples_per_label,
        seed=args.seed,
        unknown_policy=args.unknown_policy,
        max_words=args.max_words,
        base_model=args.base_model,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        num_iterations=args.num_iterations,
    )
    print(json.dumps({"saved_model_dir": str(model_dir)}, ensure_ascii=False, indent=2))
    return 0


def run_infer(args: argparse.Namespace) -> int:
    """Run a single async inference request from the CLI."""
    pipeline_instance = AsyncDualInferencePipeline(
        emotion_model_path=args.emotion_model,
        intent_model_path=args.intent_model,
        embedding_model_name=args.embedding_model,
        threshold=args.threshold,
        device=args.device,
    )
    result = asyncio.run(pipeline_instance.analyze_and_route_chat(args.text))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    if args.command == "prepare-data":
        return run_prepare_data(args)
    if args.command == "train-setfit":
        return run_train_setfit(args)
    if args.command == "infer":
        return run_infer(args)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
