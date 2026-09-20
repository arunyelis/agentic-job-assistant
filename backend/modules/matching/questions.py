"""The judgments that decide whether a posting deserves the candidate's attention.

Each one is a single judgment a knowledgeable person makes in a second given the
right context. Anything that is arithmetic, a date comparison, or a lookup stays
in code: the model is unreliable at those and confidently so.
"""

from backend.integrations.judgment import Choice, Noul, Question, Score

# Score level treated as the pass mark when measuring distance from the decision
# boundary. Level 2 of 4 is "most requirements supported" / "adjacent craft".
PASSING_LEVEL = 2

MATCH_QUESTIONS: dict[str, Question] = {
    "coverage": Score(
        instructions=(
            "How many of the requirements stated in `job.text` are directly supported by "
            "`candidate.evidence` and `candidate.skills`? Count only direct evidence, not "
            "adjacent or transferable experience."
        ),
        criteria=[
            "Almost none of the stated requirements have supporting evidence",
            "Some requirements are supported, but most of the important ones are not",
            "Most stated requirements are supported, with one or two gaps",
            "Essentially every stated requirement has direct supporting evidence",
        ],
    ),
    "domain": Score(
        instructions=(
            "How close is the problem space of `job.text` to the work described in "
            "`candidate.evidence`?"
        ),
        criteria=[
            "A different profession entirely",
            "Same broad industry, but different craft and daily work",
            "Adjacent craft with meaningful overlap in daily work",
            "The same kind of work the candidate already does",
        ],
    ),
    "ai_alignment": Score(
        instructions=(
            "How central is applied AI or LLM work to `job.text`, and does "
            "`candidate.evidence` show that specific kind of AI work?"
        ),
        criteria=[
            "The role involves no AI or LLM work",
            "AI is mentioned but peripheral to the role",
            "AI is a real part of the role and the candidate has related evidence",
            "The role centers on the same applied LLM work the candidate has shipped",
        ],
    ),
    "seniority": Choice(
        instructions=(
            "Comparing the experience level required by `job.text` against "
            "`candidate.years_experience` and `candidate.evidence`, how does the candidate "
            "sit relative to this role?"
        ),
        criteria={
            "under_leveled": "The role requires materially more experience or scope than the candidate has",
            "matched": "The candidate's experience and scope line up with the role",
            "over_leveled": "The candidate is more experienced than the role calls for",
        },
    ),
    "role_type": Choice(
        instructions="What kind of role is `job.text`?",
        criteria={
            "design": "Primarily design craft",
            "engineering": "Primarily writing and shipping software",
            "hybrid": "Genuinely both design and engineering",
            "leadership": "Primarily managing people or organizations",
            "other": "Something else entirely",
        },
    ),
    "hard_blocker": Noul(
        instructions=(
            "Does `job.text` state a hard requirement, such as a specific degree, "
            "professional license, certification, or a minimum number of years, that "
            "`candidate` clearly does not meet?"
        ),
        criteria={
            "true": "A stated hard requirement is clearly not met",
            "false": "No stated hard requirement is clearly unmet",
        },
    ),
    "overclaim_risk": Noul(
        instructions=(
            "To present `candidate` as a strong match for `job.text`, would a resume have "
            "to describe adjacent or transferable experience as if it were direct experience?"
        ),
    ),
    "tailoring_upside": Score(
        instructions=(
            "The candidate already has the underlying experience. How much would rewriting "
            "the resume to emphasize the right evidence for `job.text` change how a "
            "recruiter reads this application?"
        ),
        criteria=[
            "No amount of rewriting helps; the underlying experience is not there",
            "Rewriting helps a little, but the core gap remains",
            "The right evidence exists but is buried; rewriting would meaningfully help",
            "The candidate is a strong match already and rewriting mainly sharpens the framing",
        ],
    ),
    "location_ok": Noul(
        instructions=(
            "Is the location or work arrangement in `job.text` compatible with "
            "`candidate.work_authorization`?"
        ),
    ),
}
