# Working agreement

Career Workspace. Read this before changing anything.

## Two repositories

| | |
|---|---|
| `arunyelis/agentic-job-assistant` | **public** — code, architecture, decision records, design system |
| `arunyelis/career-workspace-product` | **private** — product bible, UX spec, backlog, research journal |

`docs/product/` and `docs/backlog/` are gitignored here. Product strategy never lands
in this repo. If a task needs a bible or UX-spec section, it gets quoted into the
task, not committed.

`v1-chatbot` is a frozen branch holding the superseded v1 implementation. Do not
build on it.

## Branch and PR flow

Every change goes on a branch and lands through a pull request. No direct commits to
`main`. Branch names describe the change, not the ticket.

Before opening a PR:

```bash
uv run ruff check backend tests
uv run pytest
npm test --prefix frontend && npm run build --prefix frontend
npm run typecheck --prefix extension && npm test --prefix extension
```

## Direction before work

State the direction before writing code, and keep it visible in the PR body:

1. **What** changes, in one sentence.
2. **Why**, tied to a real observation rather than a hunch.
3. **How it will be checked** — the test, the measurement, or the run that proves it.
4. **What is assumed**, if anything is unresolved. Name it rather than picking a
   value quietly.

A decision that would be expensive to reverse gets a record in `docs/decisions/`. A
question that cannot be settled with the evidence on hand gets a record with status
`deferred` stating what evidence would settle it. Do not guess and move on.

## Rules paid for in failures

Each of these cost a run against a live paid endpoint before it was understood.

**Never gate on `confidence`.** It measures how peaked a distribution is, not whether
an answer is safe to act on. A Score split across two adjacent *passing* levels and a
Choice split between two *acceptable* options both read as uncertain and are not.
Gate on the probability of the outcome the code branches on:
`ChoiceAnswer.probability_of()`, `ScoreAnswer.mass_at_or_above()`.

**Never gate on an absolute score.** A cut-off tuned on hand-written examples
described the examples: `fit >= 0.60` passed 0 of 80 real postings. Rank within the
corpus and take a percentile.

**Never apply a fixed standard to a relative corpus.** `boundary_risk` measures
distance from a fixed rubric level; on real postings every candidate straddles it, so
gating on it sent all 80 to review. It is reported, never gated.

**Arithmetic, counting, and date comparison stay in code.** The judgment model reads
dates as text and does not count reliably. It answered a 30-day-window question wrong
at 0.89 — wrong *and* confident, so no threshold catches it.

**Batch every question about one state into one request.** They run in parallel
server-side. Measured 9.9x faster and 6.2x cheaper than one call per question, with
identical answers.

**Keep state small.** Accuracy falls as unrelated context grows.

## Currently deferred

`docs/decisions/0007-ranking-calibration-deferred.md` — seven ranking parameters are
placeholders. `Calibration.is_calibrated` is false and every `jobs.rank` response
carries `calibrated: false` with the assumed parameters listed. The ordering is
measured and reliable; the cut-offs are not. Do not present a verdict as settled
while that flag is false, and do not guess new values. Revisit when roughly 200+
ranked postings have recorded outcomes.

## Never commit

`.env`, API keys, resumes, or real application data. `.env.example` carries the
variable names only.
