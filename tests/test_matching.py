import httpx
import pytest

from backend.integrations.judgment import (
    Choice,
    ChoiceAnswer,
    JudgmentUnavailable,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    TypeSafeJudgmentProvider,
)
from backend.modules.matching import (
    UNCALIBRATED_DEFAULT,
    Calibration,
    JobRanker,
    Posting,
    build_score,
    decide,
    rank,
    shortlist_cutoff,
)
from backend.modules.matching.scoring import HONEST_GAP, REVIEW, SKIP, TAILOR

PROFILE = {"skills": {"ai": ["RAG", "LLM integration"], "engineering": ["React", "TypeScript"]}}


def graded(level_probabilities, legend_size=4):
    legend = {str(i): f"level {i}" for i in range(legend_size)}
    score = sum(int(k) * v for k, v in level_probabilities.items())
    top = max(level_probabilities.values())
    return ScoreAnswer(
        score=score,
        legend=legend,
        probabilities=level_probabilities,
        confidence=top,
    )


def answers(**overrides):
    base = {
        "coverage": graded({"0": 0.0, "1": 0.0, "2": 0.55, "3": 0.45}),
        "domain": graded({"0": 0.0, "1": 0.0, "2": 0.1, "3": 0.9}),
        "ai_alignment": graded({"0": 0.0, "1": 0.0, "2": 0.05, "3": 0.95}),
        "seniority": ChoiceAnswer(
            choice="matched",
            probabilities={"under_leveled": 0.05, "matched": 0.55, "over_leveled": 0.40},
            confidence=0.42,
        ),
        "role_type": ChoiceAnswer(
            choice="engineering",
            probabilities={"engineering": 0.9, "design": 0.1},
            confidence=0.9,
        ),
        "hard_blocker": NoulAnswer(probability=0.05),
        "overclaim_risk": NoulAnswer(probability=0.3),
        "tailoring_upside": graded({"0": 0.0, "1": 0.0, "2": 0.2, "3": 0.8}),
        "location_ok": NoulAnswer(probability=0.95),
    }
    base.update(overrides)
    return base


def test_score_normalizes_across_level_counts():
    three = ScoreAnswer(2.0, {"0": "a", "1": "b", "2": "c"}, {"2": 1.0}, 1.0)
    four = ScoreAnswer(3.0, {"0": "a", "1": "b", "2": "c", "3": "d"}, {"3": 1.0}, 1.0)
    assert three.normalized == pytest.approx(1.0)
    assert four.normalized == pytest.approx(1.0)


def test_adjacent_passing_levels_are_decisive_not_uncertain():
    """The trap: low confidence across two *passing* levels is not uncertainty."""
    answer = graded({"0": 0.0, "1": 0.0, "2": 0.55, "3": 0.45})
    assert answer.confidence < 0.6
    assert answer.boundary_risk(2) == pytest.approx(0.0, abs=1e-6)


def test_split_across_the_pass_mark_is_genuinely_uncertain():
    answer = graded({"0": 0.0, "1": 0.5, "2": 0.5, "3": 0.0})
    assert answer.boundary_risk(2) == pytest.approx(1.0, abs=1e-6)


def test_a_strong_match_with_low_confidence_still_gets_tailored():
    score = build_score("a", answers())
    assert score.boundary_risk == pytest.approx(0.0, abs=1e-6)
    assert decide(score, cutoff=score.fit - 0.2) == TAILOR


def test_a_posting_sitting_on_the_shortlist_line_goes_to_review():
    """Sampling noise could move it either side, so a human looking changes the outcome."""
    score = build_score("a", answers())
    assert decide(score, cutoff=score.fit) == REVIEW


def test_boundary_risk_is_reported_but_never_gates():
    """Real postings straddle the rubric pass mark on coverage; that must not mean review."""
    straddling = graded({"0": 0.0, "1": 0.5, "2": 0.5, "3": 0.0})
    score = build_score("a", answers(coverage=straddling))
    assert score.boundary_risk == pytest.approx(1.0, abs=1e-6)
    assert decide(score, cutoff=score.fit - 0.2) == TAILOR


def test_hard_blocker_vetoes_rather_than_being_weighted():
    clean = build_score("a", answers())
    blocked = build_score("a", answers(hard_blocker=NoulAnswer(probability=0.95)))
    assert blocked.blocked
    assert blocked.fit < clean.fit * 0.2
    assert decide(blocked, cutoff=0.0) == SKIP


def test_under_leveled_probability_gates_not_choice_confidence():
    under = build_score(
        "a",
        answers(
            seniority=ChoiceAnswer(
                choice="matched",
                probabilities={"under_leveled": 0.45, "matched": 0.50, "over_leveled": 0.05},
                confidence=0.5,
            )
        ),
    )
    assert decide(under, cutoff=0.0) == REVIEW


def test_overclaim_is_flagged_rather_than_silently_tailored():
    risky = build_score("a", answers(overclaim_risk=NoulAnswer(probability=0.9)))
    assert decide(risky, cutoff=0.0) == HONEST_GAP


def test_cutoff_follows_the_corpus_not_a_constant():
    low = [build_score(str(i), answers()) for i in range(10)]
    assert shortlist_cutoff(low, percentile=10) == pytest.approx(max(s.fit for s in low))
    assert shortlist_cutoff([], percentile=10) == 0.0


def test_percentile_keeps_a_shortlist_even_when_all_scores_are_low():
    """The synthetic-threshold failure: dense real postings score low across the board."""
    weak = graded({"0": 0.1, "1": 0.6, "2": 0.3, "3": 0.0})
    scores = [
        build_score(str(i), answers(coverage=weak, domain=weak, ai_alignment=weak))
        for i in range(20)
    ]
    assert all(s.fit < 0.6 for s in scores)
    ordered = rank(scores, percentile=10)
    assert any(verdict != SKIP for _, verdict in ordered)


class StubProvider:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    async def judge(self, state, questions):
        self.calls += 1
        if self.error:
            raise self.error
        return answers()


POSTINGS = [
    Posting(id="1", title="AI Engineer", text="Build RAG systems with React and TypeScript."),
    Posting(id="2", title="Payroll Manager", text="Run payroll for the APAC region."),
]


async def test_ranker_sends_one_request_per_posting():
    provider = StubProvider()
    result = await JobRanker(provider).rank(PROFILE, POSTINGS)
    assert provider.calls == len(POSTINGS)
    assert not result.degraded
    assert len(result.ranked) == len(POSTINGS)


async def test_ranker_degrades_instead_of_failing():
    provider = StubProvider(error=JudgmentUnavailable("service down"))
    result = await JobRanker(provider).rank(PROFILE, POSTINGS)
    assert result.degraded
    assert "service down" in result.reason
    assert [item.posting.id for item in result.ranked]
    assert all(item.score.degraded for item in result.ranked)


async def test_degraded_ranking_still_orders_by_keyword_overlap():
    result = await JobRanker(StubProvider(error=JudgmentUnavailable("down"))).rank(
        PROFILE, POSTINGS
    )
    assert result.ranked[0].posting.id == "1"


async def test_missing_key_degrades_without_a_network_call():
    result = await JobRanker(TypeSafeJudgmentProvider(api_key="")).rank(PROFILE, POSTINGS)
    assert result.degraded
    assert "not configured" in result.reason


async def test_empty_corpus_is_not_an_error():
    result = await JobRanker(StubProvider()).rank(PROFILE, [])
    assert result.ranked == []
    assert not result.degraded


def _provider(handler):
    transport = httpx.MockTransport(handler)
    return TypeSafeJudgmentProvider(
        api_key="test-key",
        client=httpx.AsyncClient(transport=transport),
    )


async def test_provider_decodes_all_three_answer_types():
    def handler(request):
        return httpx.Response(200, json={
            "model": "jev-1.13.0",
            "answers": {
                "n": {"type": "noul", "noul": 0.92},
                "c": {"type": "choice", "choice": "x",
                      "probabilities": {"x": 0.8, "y": 0.2}, "confidence": 0.7},
                "s": {"type": "score", "score": 1.6,
                      "legend": {"0": "a", "1": "b", "2": "c"},
                      "probabilities": {"0": 0.05, "1": 0.3, "2": 0.65},
                      "confidence": 0.78},
            },
            "usage": {"input_tokens": 10, "output_tokens": 0},
        })

    got = await _provider(handler).judge("hi", {
        "n": Noul(instructions="q"),
        "c": Choice(instructions="q", criteria={"x": None, "y": None}),
        "s": Score(instructions="q", criteria=["a", "b", "c"]),
    })
    assert isinstance(got["n"], NoulAnswer) and got["n"].yes
    assert isinstance(got["c"], ChoiceAnswer) and got["c"].probability_of("x") == 0.8
    assert isinstance(got["s"], ScoreAnswer) and got["s"].normalized == pytest.approx(0.8)


async def test_provider_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={})
        return httpx.Response(200, json={
            "answers": {"n": {"type": "noul", "noul": 0.5}},
            "usage": {"input_tokens": 1, "output_tokens": 0},
        })

    got = await _provider(handler).judge("hi", {"n": Noul(instructions="q")})
    assert calls["n"] == 2
    assert got["n"].probability == 0.5


async def test_provider_does_not_retry_a_bad_request():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(422, json={"detail": "bad question"})

    with pytest.raises(JudgmentUnavailable, match="422"):
        await _provider(handler).judge("hi", {"n": Noul(instructions="q")})
    assert calls["n"] == 1


def test_malformed_questions_are_rejected_before_the_network():
    with pytest.raises(ValueError):
        from backend.integrations.judgment.typesafe_provider import _encode
        _encode(Score(instructions="q", criteria=["only one"]))


# --- calibration: the parameters are assumptions until outcomes say otherwise ---


def test_default_calibration_reports_itself_as_unfitted():
    assert not UNCALIBRATED_DEFAULT.is_calibrated
    assumed = UNCALIBRATED_DEFAULT.assumed_parameters
    assert "weights" in assumed
    assert "shortlist_percentile" in assumed
    assert "sampling_spread" not in assumed, "sampling spread was measured, not assumed"


def test_a_fitted_calibration_reports_no_assumptions():
    fitted = Calibration(name="from-outcomes-2026-Q4", is_calibrated=True)
    assert fitted.assumed_parameters == ()


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        Calibration(weights={"coverage": 0.9, "domain": 0.9, "seniority": 0.1, "ai_alignment": 0.1})


def test_percentile_is_bounded():
    with pytest.raises(ValueError, match="between 1 and 100"):
        Calibration(shortlist_percentile=0)


def test_changing_weights_changes_fit_without_touching_the_model():
    """Re-weighting is a code change, not a re-run. No judgment is re-requested."""
    ai_heavy = Calibration(
        weights={"coverage": 0.1, "domain": 0.1, "seniority": 0.1, "ai_alignment": 0.7}
    )
    baseline = build_score("a", answers())
    weighted = build_score("a", answers(), ai_heavy)
    assert weighted.fit != baseline.fit
    assert weighted.dimensions["ai_alignment"] == baseline.dimensions["ai_alignment"]


def test_calibration_controls_the_veto_threshold():
    lenient = Calibration(blocker_probability=0.99)
    marginal = answers(hard_blocker=NoulAnswer(probability=0.8))
    assert build_score("a", marginal).blocked
    assert not build_score("a", marginal, lenient).blocked


async def test_ranking_result_carries_the_calibration_state_forward():
    result = await JobRanker(StubProvider()).rank(PROFILE, POSTINGS)
    assert not result.calibrated
    assert "weights" in result.calibration.assumed_parameters


async def test_degraded_results_also_report_calibration_state():
    result = await JobRanker(StubProvider(error=JudgmentUnavailable("down"))).rank(
        PROFILE, POSTINGS
    )
    assert result.degraded and not result.calibrated
