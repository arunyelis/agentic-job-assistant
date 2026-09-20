from dataclasses import dataclass, field
from typing import Literal, Protocol


class JudgmentUnavailable(RuntimeError):
    """The judgment service could not answer. Callers must degrade, not fail."""


@dataclass(frozen=True)
class Noul:
    """A yes/no judgment. The answer is the probability that the answer is yes."""

    instructions: str
    criteria: dict[str, str] | None = None
    type: Literal["noul"] = "noul"


@dataclass(frozen=True)
class Choice:
    """One option from a defined set, with a probability for every option."""

    instructions: str
    criteria: dict[str, str | None] = field(default_factory=dict)
    type: Literal["choice"] = "choice"


@dataclass(frozen=True)
class Score:
    """A position along ordered levels, each describing a concrete situation."""

    instructions: str
    criteria: list[str] = field(default_factory=list)
    type: Literal["score"] = "score"


Question = Noul | Choice | Score


@dataclass(frozen=True)
class NoulAnswer:
    probability: float

    @property
    def yes(self) -> bool:
        return self.probability > 0.5


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    probabilities: dict[str, float]
    confidence: float

    def probability_of(self, option: str) -> float:
        """Read one option directly.

        Prefer this over `confidence` when gating. Confidence measures how peaked
        the distribution is, not whether the answer is safe to act on: a split
        between two acceptable options looks uncertain and is not.
        """
        return self.probabilities.get(option, 0.0)


@dataclass(frozen=True)
class ScoreAnswer:
    score: float
    legend: dict[str, str]
    probabilities: dict[str, float]
    confidence: float

    @property
    def normalized(self) -> float:
        """The score on a 0..1 scale, independent of how many levels were defined."""
        levels = len(self.legend)
        return self.score / (levels - 1) if levels > 1 else 0.0

    def mass_at_or_above(self, level: int) -> float:
        return sum(p for lvl, p in self.probabilities.items() if int(lvl) >= level)

    def boundary_risk(self, passing_level: int) -> float:
        """How close this sits to a pass/fail line: 0 decisive, 1 on the fence.

        Two adjacent *passing* levels splitting the mass is a confident answer
        that `confidence` reports as an uncertain one. This measures the thing
        that actually matters, which is the mass on each side of the cut.
        """
        return 1.0 - 2.0 * abs(self.mass_at_or_above(passing_level) - 0.5)


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer


class JudgmentProvider(Protocol):
    """Returns typed judgments over a state.

    The counterpart to `LLMProvider`. That one generates text; this one decides,
    and returns values code can sort, threshold, and branch on without parsing.
    """

    @property
    def available(self) -> bool: ...

    async def judge(
        self, state: object, questions: dict[str, Question]
    ) -> dict[str, Answer]: ...
