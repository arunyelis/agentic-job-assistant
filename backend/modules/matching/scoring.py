"""Composition and gating. Every weight and cut-off here belongs to code, not the model.

Two rules this module exists to enforce, both learned by measuring rather than
by reading the documentation:

1. Never gate on `confidence`. It reports how peaked a distribution is, not whether
   an answer is safe to act on. A Score split across two adjacent *passing* levels
   and a Choice split between two *acceptable* options both look uncertain and are
   not. Gate on the probability mass of the outcome the code branches on.
2. Never gate on an absolute score. Thresholds calibrated on hand-written examples
   do not survive contact with real postings: real job descriptions carry far more
   requirements, which pushes coverage down and overclaim up for every candidate.
   Rank within the corpus and take a percentile.
"""

from dataclasses import dataclass, field

from backend.integrations.judgment import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from backend.modules.matching.questions import PASSING_LEVEL

WEIGHTS = {"coverage": 0.35, "domain": 0.25, "seniority": 0.20, "ai_alignment": 0.20}
SENIORITY_VALUE = {"matched": 1.0, "over_leveled": 0.75, "under_leveled": 0.25}

BLOCKER_PROBABILITY = 0.70
VETO_MULTIPLIER = 0.15
UNDER_LEVELED_LIMIT = 0.35
BOUNDARY_RISK_LIMIT = 0.50
DEFAULT_SHORTLIST_PERCENTILE = 10

# Identical calls vary by about 0.02 on a 0..1 scale, so any absolute comparison
# needs more margin than that. Ranking is unaffected: two independent runs over 80
# real postings agreed at Spearman 0.984 with the top ten identical.
SAMPLING_SPREAD = 0.03

Verdict = str
TAILOR = "tailor"
REVIEW = "review"
HONEST_GAP = "honest_gap"
SKIP = "skip"


@dataclass(frozen=True)
class JobScore:
    job_id: str
    fit: float
    dimensions: dict[str, float]
    role_type: str
    blocked: bool
    boundary_risk: float
    overclaim: float
    tailoring_upside: float
    under_leveled: float
    location_ok: float
    degraded: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


def _score(answers: dict[str, Answer], key: str) -> ScoreAnswer:
    answer = answers.get(key)
    if not isinstance(answer, ScoreAnswer):
        raise ValueError(f"Expected a Score answer for {key!r}")
    return answer


def _choice(answers: dict[str, Answer], key: str) -> ChoiceAnswer:
    answer = answers.get(key)
    if not isinstance(answer, ChoiceAnswer):
        raise ValueError(f"Expected a Choice answer for {key!r}")
    return answer


def _noul(answers: dict[str, Answer], key: str) -> NoulAnswer:
    answer = answers.get(key)
    if not isinstance(answer, NoulAnswer):
        raise ValueError(f"Expected a Noul answer for {key!r}")
    return answer


def build_score(job_id: str, answers: dict[str, Answer]) -> JobScore:
    graded = {key: _score(answers, key) for key in ("coverage", "domain", "ai_alignment")}
    seniority = _choice(answers, "seniority")

    dimensions = {key: answer.normalized for key, answer in graded.items()}
    dimensions["seniority"] = SENIORITY_VALUE.get(seniority.choice, 0.25)

    fit = sum(WEIGHTS[key] * value for key, value in dimensions.items())
    blocker = _noul(answers, "hard_blocker").probability
    blocked = blocker > BLOCKER_PROBABILITY
    if blocked:
        fit *= VETO_MULTIPLIER

    return JobScore(
        job_id=job_id,
        fit=fit,
        dimensions=dimensions,
        role_type=_choice(answers, "role_type").choice,
        blocked=blocked,
        boundary_risk=max(a.boundary_risk(PASSING_LEVEL) for a in graded.values()),
        overclaim=_noul(answers, "overclaim_risk").probability,
        tailoring_upside=_score(answers, "tailoring_upside").normalized,
        under_leveled=seniority.probability_of("under_leveled"),
        location_ok=_noul(answers, "location_ok").probability,
    )


def shortlist_cutoff(scores: list[JobScore], percentile: int = DEFAULT_SHORTLIST_PERCENTILE) -> float:
    """The fit value that separates the top `percentile` of this corpus.

    A percentile rather than a constant, because the absolute scale moves with the
    corpus: dense enterprise postings score lower across the board than short ones,
    for the same candidate.
    """
    if not scores:
        return 0.0
    ranked = sorted((s.fit for s in scores), reverse=True)
    index = max(0, min(len(ranked) - 1, round(len(ranked) * percentile / 100) - 1))
    return ranked[index]


def decide(score: JobScore, cutoff: float) -> Verdict:
    """What the pipeline should spend on this posting next.

    `boundary_risk` is deliberately not a gate here. It measures distance from a
    fixed rubric level, and on real postings every candidate straddles that level
    on coverage, so gating on it sends the entire corpus to review. It is carried
    on the score for display, where "this dimension is genuinely split" is useful
    to a reader, and the gate uses position instead: review a posting only when
    sampling noise could move it across the shortlist line, because that is the
    only case where a human looking changes the outcome.
    """
    if score.blocked or score.fit + SAMPLING_SPREAD < cutoff:
        return SKIP
    if score.overclaim > 0.80:
        return HONEST_GAP
    if score.under_leveled > UNDER_LEVELED_LIMIT:
        return REVIEW
    if abs(score.fit - cutoff) <= SAMPLING_SPREAD:
        return REVIEW
    return TAILOR


def rank(
    scores: list[JobScore], percentile: int = DEFAULT_SHORTLIST_PERCENTILE
) -> list[tuple[JobScore, Verdict]]:
    cutoff = shortlist_cutoff(scores, percentile)
    ordered = sorted(scores, key=lambda s: -s.fit)
    return [(score, decide(score, cutoff)) for score in ordered]


def fallback_score(job_id: str, title: str, text: str, keywords: list[str]) -> JobScore:
    """Ranking when the judgment service is unavailable.

    Keyword overlap, not understanding. It keeps the product usable and is marked
    `degraded` so the interface can say so rather than implying a real judgment.
    """
    haystack = f"{title}\n{text}".lower()
    hits = [k for k in keywords if k.lower() in haystack]
    overlap = len(hits) / len(keywords) if keywords else 0.0
    return JobScore(
        job_id=job_id,
        fit=overlap,
        dimensions={"keyword_overlap": overlap},
        role_type="unknown",
        blocked=False,
        boundary_risk=1.0,
        overclaim=0.0,
        tailoring_upside=0.0,
        under_leveled=0.0,
        location_ok=0.0,
        degraded=True,
        notes=(f"keyword ranking only: matched {len(hits)} of {len(keywords)}",),
    )
