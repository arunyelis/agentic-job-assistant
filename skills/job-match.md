---
name: job-match
description: Explain why a shortlisted job fits the candidate, name the real gaps, and say what to change.
---
# Job match

Use this after `jobs.rank` has already decided a posting is worth attention. That
tool produces the fit score, the ranking, and the verdict from typed judgments; do
not restate them as prose or second-guess them here. A sentence like "this is a
strong match" adds nothing a sorted number has not already said.

Your job is the part a ranking cannot do: explain the match in the candidate's own
evidence, and say what to change.

1. Name the five requirements in the posting that carry the most weight, and for
   each one, quote or point to the specific experience in the candidate profile that
   answers it. Cite the evidence; do not summarise it into a claim.
2. Name every requirement with no supporting evidence as a gap, plainly. Adjacent
   experience is a gap. Describing it as direct experience is the one thing this
   skill must never do, and `jobs.rank` reports an `overclaim_risk` score precisely
   so that stretch is visible before anything is written. When that score is high,
   say what is missing rather than finding a way to phrase around it.
3. Suggest three resume changes. Each one reorders, surfaces, or rewords evidence
   the candidate already has. If a change would require experience they do not have,
   it is not a change, it is a fabrication; say the gap is real instead.
4. Suggest three interview questions they should expect, drawn from the gaps rather
   than the strengths.

If the posting or the profile is missing something you need, say what is missing and
stop. Do not fill it in.

When `jobs.rank` reports `calibrated: false`, its verdict is provisional: the
ordering is reliable, the cut-off between "worth tailoring" and "not" is not yet
fitted to outcomes. Treat a borderline posting as worth explaining anyway.
