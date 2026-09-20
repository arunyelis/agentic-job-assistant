"""Every tunable in the ranker, in one place, with its provenance recorded.

The parameters below fall into two groups, and the difference matters more than
any individual value.

**Measured** — derived from observed behaviour of the judgment service:

- `sampling_spread`: identical calls to the same posting varied by 0.020 to 0.027
  on a 0..1 scale over a five-call probe. 0.03 is that, rounded up.

**Assumed** — chosen without evidence, because nothing in the system yet records
whether a ranking decision was right. Every one of these is a placeholder:

- `weights`: which dimensions matter, and how much, is a statement about one
  candidate's priorities. It is not a property of the model or the corpus.
- `seniority_value`: how much being over-levelled should cost relative to being
  under-levelled.
- `blocker_probability`, `veto_multiplier`: when a stated hard requirement is
  unmet enough to veto, and how hard.
- `under_leveled_limit`, `overclaim_limit`: where a posting stops being worth
  tailoring and starts being worth a second look.
- `shortlist_percentile`: how much of the corpus earns a generative pass. This is
  a budget decision as much as a quality one.

Resolving the assumed group needs outcome data the product does not collect yet:
postings ranked, what the candidate did, and what came back. Until then
`is_calibrated` stays false and callers are expected to surface that rather than
present these numbers as findings. See
`docs/decisions/0007-ranking-calibration-deferred.md`.
"""

from dataclasses import dataclass, field
from typing import Literal

Provenance = Literal["measured", "assumed"]

PROVENANCE: dict[str, Provenance] = {
    "sampling_spread": "measured",
    "weights": "assumed",
    "seniority_value": "assumed",
    "blocker_probability": "assumed",
    "veto_multiplier": "assumed",
    "under_leveled_limit": "assumed",
    "overclaim_limit": "assumed",
    "shortlist_percentile": "assumed",
}


@dataclass(frozen=True)
class Calibration:
    name: str = "uncalibrated-default"
    is_calibrated: bool = False

    weights: dict[str, float] = field(
        default_factory=lambda: {
            "coverage": 0.35,
            "domain": 0.25,
            "seniority": 0.20,
            "ai_alignment": 0.20,
        }
    )
    seniority_value: dict[str, float] = field(
        default_factory=lambda: {"matched": 1.0, "over_leveled": 0.75, "under_leveled": 0.25}
    )
    blocker_probability: float = 0.70
    veto_multiplier: float = 0.15
    under_leveled_limit: float = 0.35
    overclaim_limit: float = 0.80
    shortlist_percentile: int = 10
    sampling_spread: float = 0.03

    def __post_init__(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Dimension weights must sum to 1.0, got {total}")
        if not 1 <= self.shortlist_percentile <= 100:
            raise ValueError("shortlist_percentile must be between 1 and 100")

    @property
    def assumed_parameters(self) -> tuple[str, ...]:
        """Which parameters are still placeholders, for logs and the interface."""
        if self.is_calibrated:
            return ()
        return tuple(name for name, source in PROVENANCE.items() if source == "assumed")


UNCALIBRATED_DEFAULT = Calibration()
