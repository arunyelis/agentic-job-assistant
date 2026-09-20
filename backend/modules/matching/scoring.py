"""Composition and gating. Every weight and cut-off belongs to code, not the model.

Three rules this module exists to enforce, each learned by measuring rather than
by reasoning, and each after getting it wrong first:

1. Never gate on `confidence`. It reports how peaked a distribution is, not whether
   an answer is safe to act on. A Score split across two adjacent *passing* levels
   and a Choice split between two *acceptable* options both look uncertain and are
   not. Gate on the probability mass of the outcome the code branches on.
2. Never gate on an absolute score. Thresholds calibrated on hand-written examples
   do not survive contact with real postings: real descriptions carry far more
   requirements, which pushes coverage down and overclaim up for every candidate.
   Rank within the corpus and take a percentile.
3. Never apply an absolute standard to a relative corpus, which is rule 2 wearing a
   different hat. `boundary_risk` measures distance from a fixed rubric level; on
   real postings every candidate straddles that level, so gating on it sent the
   whole corpus to review. It is reported, never gated.

The numbers themselves live in `Calibration` and are mostly still assumptions.
"""

from dataclasses import dataclass, field

from backend.integrations.judgment import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from backend.modules.matching.calibration import UNCALIBRATED_DEFAULT, Calibration
from backend.modules.matching.questions import PASSING_LEVEL

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


def build_score(
    job_id: str,
    answers: dict[str, Answer],
    calibration: Calibration = UNCALIBRATED_DEFAULT,
) -> JobScore:
    graded = {key: _score(answers, key) for key in ("coverage", "domain", "ai_alignment")}
    seniority = _choice(answers, "seniority")

    dimensions = {key: answer.normalized for key, answer in graded.items()}
    dimensions["seniority"] = calibration.seniority_value.get(seniority.choice, 0.25)

    fit = sum(calibration.weights[key] * value for key, value in dimensions.items())
    blocked = _noul(answers, "hard_blocker").probability > calibration.blocker_probability
    if blocked:
        fit *= calibration.veto_multiplier

    return JobScore(
        job_id=job_id,
        fit=fit,
        dimensions=dimensions,
        role_type=_choice(answers, "role_type").choice,
        blocked=blocked,
        # Reported for display: "this dimension is genuinely split" is useful to a
        # reader. It is deliberately not a gate; see rule 3 above.
        boundary_risk=max(a.boundary_risk(PASSING_LEVEL) for a in graded.values()),
        overclaim=_noul(answers, "overclaim_risk").probability,
        tailoring_upside=_score(answers, "tailoring_upside").normalized,
        under_leveled=seniority.probability_of("under_leveled"),
        location_ok=_noul(answers, "location_ok").probability,
    )


def shortlist_cutoff(scores: list[JobScore], percentile: int) -> float:
    """The fit value separating the top `percentile` of this corpus.

    A percentile rather than a constant, because the absolute scale moves with the
    corpus: dense enterprise postings score lower across the board than short ones,
    for the same candidate.
    """
    if not scores:
        return 0.0
    ranked = sorted((s.fit for s in scores), reverse=True)
    index = max(0, min(len(ranked) - 1, round(len(ranked) * percentile / 100) - 1))
    return ranked[index]


def decide(
    score: JobScore,
    cutoff: float,
    calibration: Calibration = UNCALIBRATED_DEFAULT,
) -> Verdict:
    """What the pipeline should spend on this posting next.

    Review means "a human looking changes the outcome", which is true in exactly two
    cases: the posting sits close enough to the shortlist line that sampling noise
    could move it either side, or the candidate may be under-levelled for it.
    """
    spread = calibration.sampling_spread
    if score.blocked or score.fit + spread < cutoff:
        return SKIP
    if score.overclaim > calibration.overclaim_limit:
        return HONEST_GAP
    if score.under_leveled > calibration.under_leveled_limit:
        return REVIEW
    if abs(score.fit - cutoff) <= spread:
        return REVIEW
    return TAILOR


def rank(
    scores: list[JobScore],
    calibration: Calibration = UNCALIBRATED_DEFAULT,
    percentile: int | None = None,
) -> list[tuple[JobScore, Verdict]]:
    cut_at = percentile if percentile is not None else calibration.shortlist_percentile
    cutoff = shortlist_cutoff(scores, cut_at)
    ordered = sorted(scores, key=lambda s: -s.fit)
    return [(score, decide(score, cutoff, calibration)) for score in ordered]


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
