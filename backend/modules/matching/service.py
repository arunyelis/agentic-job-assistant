import asyncio
from dataclasses import dataclass

from backend.integrations.judgment import JudgmentProvider, JudgmentUnavailable
from backend.modules.matching.questions import MATCH_QUESTIONS
from backend.modules.matching.scoring import (
    DEFAULT_SHORTLIST_PERCENTILE,
    JobScore,
    Verdict,
    build_score,
    fallback_score,
    rank,
)

DEFAULT_CONCURRENCY = 16
MAX_JOB_TEXT_CHARS = 4000


@dataclass(frozen=True)
class Posting:
    id: str
    title: str
    text: str
    location: str = ""
    company: str = ""
    url: str = ""


@dataclass(frozen=True)
class RankedPosting:
    posting: Posting
    score: JobScore
    verdict: Verdict


@dataclass(frozen=True)
class RankingResult:
    ranked: list[RankedPosting]
    degraded: bool
    reason: str = ""

    @property
    def shortlist(self) -> list[RankedPosting]:
        return [item for item in self.ranked if item.verdict == "tailor"]


class JobRanker:
    """Ranks postings against one candidate profile.

    One request per posting, many in flight at once. Every question for a posting
    travels in that single request because they share its state and run in parallel
    server-side; splitting them would cost roughly ten times the latency for the
    same answers.
    """

    def __init__(
        self,
        provider: JudgmentProvider | None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ):
        self._provider = provider
        self._semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _judge(self, profile: dict, posting: Posting) -> JobScore:
        state = {
            "candidate": profile,
            "job": {
                "title": posting.title,
                "location": posting.location,
                "text": posting.text[:MAX_JOB_TEXT_CHARS],
            },
        }
        async with self._semaphore:
            answers = await self._provider.judge(state, MATCH_QUESTIONS)
        return build_score(posting.id, answers)

    async def rank(
        self,
        profile: dict,
        postings: list[Posting],
        percentile: int = DEFAULT_SHORTLIST_PERCENTILE,
    ) -> RankingResult:
        if not postings:
            return RankingResult(ranked=[], degraded=False)

        if self._provider is None or not self._provider.available:
            return self._degraded(profile, postings, percentile, "judgment service not configured")

        results = await asyncio.gather(
            *(self._judge(profile, posting) for posting in postings),
            return_exceptions=True,
        )
        failures = [r for r in results if isinstance(r, BaseException)]
        if failures:
            # Mixing real scores with keyword scores would put two different scales
            # in one ranking, so the whole batch degrades together or not at all.
            return self._degraded(
                profile, postings, percentile,
                f"{len(failures)} of {len(postings)} judgments failed: {failures[0]}",
            )

        by_id = {posting.id: posting for posting in postings}
        ordered = rank([r for r in results if isinstance(r, JobScore)], percentile)
        return RankingResult(
            ranked=[RankedPosting(by_id[s.job_id], s, v) for s, v in ordered],
            degraded=False,
        )

    def _degraded(
        self, profile: dict, postings: list[Posting], percentile: int, reason: str
    ) -> RankingResult:
        keywords = _profile_keywords(profile)
        scores = [
            fallback_score(posting.id, posting.title, posting.text, keywords)
            for posting in postings
        ]
        by_id = {posting.id: posting for posting in postings}
        ordered = rank(scores, percentile)
        return RankingResult(
            ranked=[RankedPosting(by_id[s.job_id], s, v) for s, v in ordered],
            degraded=True,
            reason=reason,
        )


def _profile_keywords(profile: dict) -> list[str]:
    skills = profile.get("skills", {})
    terms: list[str] = []
    if isinstance(skills, dict):
        for values in skills.values():
            terms.extend(str(v) for v in values)
    elif isinstance(skills, list):
        terms.extend(str(v) for v in skills)
    seen: dict[str, None] = {}
    for term in terms:
        cleaned = term.strip()
        if len(cleaned) > 2:
            seen.setdefault(cleaned.lower(), None)
    return list(seen)


async def check_judgment_service(provider: JudgmentProvider | None) -> dict:
    """A cheap liveness probe, for the doctor endpoint and startup logging."""
    if provider is None or not provider.available:
        return {"configured": False, "reachable": False, "detail": "no API key"}
    from backend.integrations.judgment import Noul

    try:
        await provider.judge("ping", {"alive": Noul(instructions="Is this text in English?")})
    except JudgmentUnavailable as error:
        return {"configured": True, "reachable": False, "detail": str(error)[:200]}
    return {"configured": True, "reachable": True, "detail": ""}
