# 0006 — A typed judgment provider beside the language model gateway

Date: 2026-09-19
Status: accepted

## Context

Every model-backed decision reached the product through `LLMProvider.complete()`,
which returns `str`. The job-match skill asked for "strong match, partial match, or
weak match" as prose. Prose cannot be sorted, thresholded, or compared across a
corpus, so ranking a list of postings was not expressible: the ceiling was the
interface, not the model.

A second constraint shaped the design. The product cannot scrape LinkedIn or similar
sites from its own servers, and must not drive a user's logged-in session to do it
either. Volume therefore has to come from sources that invite machine reading — ATS
job-board APIs, `schema.org/JobPosting` markup, public feeds — which produces
hundreds of candidate postings per search. Sending every one to a generative model is
too slow and too expensive to be the first stage.

## Decision

Add `JudgmentProvider` alongside `LLMProvider`. It returns typed answers — Noul,
Choice, Score — with probability distributions, implemented against TypeSafe's
System One endpoint. `OpenAIResponsesProvider` keeps everything generative.

`JobRanker` sends one request per posting with every question in it, ranks the
corpus, and marks which postings earn a generative tailoring pass.

## Measurements behind this

80 real postings from four public ATS boards, two independent runs plus a
determinism probe, 250 calls total:

- 0 failures, 0 retries, latency p50 0.38s / p95 0.52s
- 80 postings, 720 judgments, 1.6s wall, $0.000113 per posting
- run-to-run Spearman 0.984, top-10 overlap 10/10
- batching all questions into one call per posting: 9.9x faster, 6.2x cheaper than a
  call per question, with identical answers

## Consequences

**Thresholds are relative, never absolute.** A gate calibrated on hand-written job
descriptions (`fit >= 0.60`) passed 0 of 80 real postings, because real postings
carry far more requirements and push every candidate's coverage down. The shortlist
is a percentile of the scored corpus. `shortlist_cutoff()` and `decide()` own this.

**Confidence is never a gate.** It reports how peaked a distribution is, not whether
an answer is safe to act on. A Score split across two adjacent *passing* levels and a
Choice split between two *acceptable* options both look uncertain and are not.
`ChoiceAnswer.probability_of()` and `ScoreAnswer.mass_at_or_above()` exist so callers
read the outcome they branch on. `boundary_risk` is reported for display only; gating
on it sent the entire corpus to review.

**Arithmetic stays in code.** The model reads dates as text and does not count
reliably. Salary bands, posting age, deadline windows, and requirement counts are
computed, never asked.

**The service is not load-bearing.** TypeSafe is young and its own documentation says
rate limits can change without notice. When the provider is unreachable or
unconfigured, `JobRanker` degrades the whole batch to keyword overlap and marks the
result `degraded` so the interface can say so. Partial degradation is deliberately not
supported: mixing judged and keyword scores would put two scales in one ranking.

**State stays small.** Accuracy falls as unrelated context grows, so posting text is
truncated and only the candidate profile and the one posting travel in each request.
