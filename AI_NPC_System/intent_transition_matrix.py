"""Intent transition policy for CREDO latency-cover responses.

The user's dialog act should not be copied blindly into the FastTrack response.
This matrix maps a detected user intent to a likely response intent so the cover
sounds like a conversational move, not an echo of the classifier label.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping


INTENTS = ("QUESTION", "INFORM", "ACKNOWLEDGE", "DIRECTIVE", "EXPRESSIVE", "REJECT", "UNKNOWN")


TRANSITION_MATRIX: dict[str, dict[str, float]] = {
    "QUESTION": {
        "ACKNOWLEDGE": 0.34,
        "INFORM": 0.30,
        "EXPRESSIVE": 0.18,
        "QUESTION": 0.08,
        "DIRECTIVE": 0.05,
        "REJECT": 0.05,
    },
    "INFORM": {
        "ACKNOWLEDGE": 0.36,
        "QUESTION": 0.24,
        "EXPRESSIVE": 0.18,
        "INFORM": 0.12,
        "DIRECTIVE": 0.06,
        "REJECT": 0.04,
    },
    "ACKNOWLEDGE": {
        "INFORM": 0.34,
        "EXPRESSIVE": 0.24,
        "QUESTION": 0.18,
        "ACKNOWLEDGE": 0.10,
        "DIRECTIVE": 0.08,
        "REJECT": 0.06,
    },
    "DIRECTIVE": {
        "ACKNOWLEDGE": 0.42,
        "INFORM": 0.24,
        "EXPRESSIVE": 0.14,
        "QUESTION": 0.10,
        "DIRECTIVE": 0.06,
        "REJECT": 0.04,
    },
    "EXPRESSIVE": {
        "EXPRESSIVE": 0.30,
        "ACKNOWLEDGE": 0.26,
        "QUESTION": 0.18,
        "INFORM": 0.16,
        "DIRECTIVE": 0.06,
        "REJECT": 0.04,
    },
    "REJECT": {
        "ACKNOWLEDGE": 0.32,
        "INFORM": 0.22,
        "QUESTION": 0.18,
        "EXPRESSIVE": 0.16,
        "REJECT": 0.08,
        "DIRECTIVE": 0.04,
    },
    "UNKNOWN": {
        "ACKNOWLEDGE": 0.30,
        "QUESTION": 0.22,
        "INFORM": 0.22,
        "EXPRESSIVE": 0.18,
        "DIRECTIVE": 0.04,
        "REJECT": 0.04,
    },
}


EMOTION_BIAS: dict[str, dict[str, float]] = {
    "positive": {"EXPRESSIVE": 1.25, "ACKNOWLEDGE": 1.10},
    "negative": {"ACKNOWLEDGE": 1.20, "QUESTION": 1.10, "REJECT": 0.75},
    "ambiguous": {"QUESTION": 1.25, "ACKNOWLEDGE": 1.10},
    "neutral": {"INFORM": 1.10, "ACKNOWLEDGE": 1.10},
}


@dataclass(frozen=True)
class IntentTransition:
    """Selected response intent and the normalized transition distribution."""

    user_intent: str
    response_intent: str
    distribution: dict[str, float]


class IntentTransitionPlanner:
    """Sample response intent from a user-intent transition matrix."""

    def __init__(self, matrix: Mapping[str, Mapping[str, float]] | None = None) -> None:
        self.matrix = {key: dict(value) for key, value in (matrix or TRANSITION_MATRIX).items()}

    def choose(
        self,
        user_intent: str,
        *,
        emotion: str = "neutral",
        rng: random.Random | None = None,
    ) -> IntentTransition:
        """Choose a response intent after applying a light emotion bias."""
        rng = rng or random
        user_intent = self._normalize_intent(user_intent)
        weights = dict(self.matrix.get(user_intent) or self.matrix["UNKNOWN"])

        for intent, multiplier in EMOTION_BIAS.get(emotion.lower(), {}).items():
            if intent in weights:
                weights[intent] *= multiplier

        total = sum(max(value, 0.0) for value in weights.values()) or 1.0
        distribution = {intent: max(value, 0.0) / total for intent, value in weights.items()}

        cursor = rng.random()
        cumulative = 0.0
        for intent, probability in distribution.items():
            cumulative += probability
            if cursor <= cumulative:
                return IntentTransition(user_intent, intent, distribution)
        fallback = next(reversed(distribution))
        return IntentTransition(user_intent, fallback, distribution)

    def _normalize_intent(self, intent: str) -> str:
        intent = str(intent or "UNKNOWN").upper()
        return intent if intent in INTENTS else "UNKNOWN"
