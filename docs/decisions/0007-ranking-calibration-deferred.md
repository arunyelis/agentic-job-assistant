# 0007 — Ranking thresholds stay uncalibrated, deliberately

Date: 2026-09-19
Status: deferred
Relates to: [0006](0006-typed-judgment-provider.md)

## The open question

`JobRanker` produces an ordering and a verdict per posting. The ordering is
measured and stable: two independent runs over 80 real postings agreed at Spearman
0.984 with the top ten identical. The verdicts are not. They depend on eight
parameters — dimension weights, the seniority penalty, the blocker threshold and
its veto multiplier, the under-levelled and overclaim limits, and the shortlist
percentile — and every one of them was chosen without evidence.

Three separate attempts to set these by reasoning all failed the same way, each
caught only by running against real data:

1. A confidence floor of 0.55 sent the second-best match to human review, because a
   Score split across two adjacent *passing* levels reads as low confidence.
2. An absolute cut-off of `fit >= 0.60`, tuned on eight hand-written job
   descriptions, passed **0 of 80** real postings. Real descriptions carry far more
   requirements, so coverage sits lower for every candidate.
3. A `boundary_risk > 0.5` gate sent **all 80** postings to review, because every
   candidate straddles a fixed rubric level on coverage.

The pattern is consistent: a threshold guessed from examples describes the examples.
A fourth guess would cost another measured run and would fail for a fourth reason.

## Decision

Stop guessing. Do not set these values by argument.

Every parameter moves into `Calibration` with its provenance recorded, separating
the one value that was measured (`sampling_spread`, from an observed 0.020–0.027
run-to-run variance) from the seven that are placeholders. `Calibration.is_calibrated`
is false, `RankingResult.calibrated` carries that to every caller, and the
`jobs.rank` tool returns `calibrated: false` with the list of assumed parameters on
every response.

The product therefore ships the ordering, which is earned, while stating plainly
that the cut-offs are not. The interface must not present a verdict as settled while
`calibrated` is false.

## What would resolve this

Outcome data the product does not collect yet. Concretely, for each ranked posting:
the judgment values, the verdict given, whether the candidate applied, and what came
back. A few hundred rows with real outcomes makes the weights and cut-offs fittable
rather than arguable, and the same store turns the judgments into features for a
supervised model.

That capture belongs with application tracking, which already exists in the data
model. It is not built here because wiring an outcome store to fit thresholds nobody
has the data for yet would be the same mistake in a larger form.

## Revisit when

- the workspace has recorded outcomes for roughly 200+ ranked postings, or
- a user reports that the shortlist is consistently the wrong size, which is
  evidence about `shortlist_percentile` specifically and can be acted on alone.

Until then, changing a weight is a one-line code change that needs no new judgments:
the stored answers are unchanged, so re-weighting and re-ranking cost nothing.

## Consequences

Anyone reading a verdict needs to know it rests on assumptions, so the flag is part
of the tool contract rather than a comment. The cost of this honesty is that the
interface has to say "provisional" until there is a reason not to. That is the
correct thing to say.
