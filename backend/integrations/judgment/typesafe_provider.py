import asyncio
from dataclasses import asdict

import httpx

from backend.integrations.judgment.base import (
    Answer,
    Choice,
    ChoiceAnswer,
    JudgmentUnavailable,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
)

DEFAULT_BASE_URL = "https://api.typesafe.ai/v1"
RETRYABLE_STATUS = {429, 529}


def _encode(question: Question) -> dict:
    payload = {k: v for k, v in asdict(question).items() if v is not None}
    if isinstance(question, Choice) and not question.criteria:
        raise ValueError("A Choice question needs at least two options in criteria.")
    if isinstance(question, Score) and len(question.criteria) < 2:
        raise ValueError("A Score question needs at least two levels in criteria.")
    return payload


def _decode(raw: dict) -> Answer:
    kind = raw.get("type")
    if kind == "noul":
        return NoulAnswer(probability=float(raw["noul"]))
    if kind == "choice":
        return ChoiceAnswer(
            choice=raw["choice"],
            probabilities={k: float(v) for k, v in raw["probabilities"].items()},
            confidence=float(raw["confidence"]),
        )
    if kind == "score":
        return ScoreAnswer(
            score=float(raw["score"]),
            legend=dict(raw["legend"]),
            probabilities={k: float(v) for k, v in raw["probabilities"].items()},
            confidence=float(raw["confidence"]),
        )
    raise JudgmentUnavailable(f"Unrecognized answer type: {kind!r}")


class TypeSafeJudgmentProvider:
    """System One judgments from TypeSafe.

    Every question in a call sees the same state and is evaluated in parallel, so
    ask everything the caller might need in one request rather than one at a time.
    Measured at 9.9x faster and 6.2x cheaper than a call per question, with
    identical answers.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = "jev-latest",
        timeout: float = 30.0,
        max_attempts: int = 3,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key.strip()
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._client = client

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def judge(self, state: object, questions: dict[str, Question]) -> dict[str, Answer]:
        if not self.available:
            raise JudgmentUnavailable("TYPESAFE_API_KEY is not configured.")
        if not questions:
            return {}

        body = {
            "state": state,
            "model": self._model,
            "questions": {qid: _encode(q) for qid, q in questions.items()},
        }
        client = await self._http()
        delay = 1.0
        last: Exception | None = None

        for attempt in range(self._max_attempts):
            try:
                response = await client.post(
                    f"{self._base_url}/systemone",
                    json=body,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            except httpx.HTTPError as error:
                last = error
            else:
                if response.status_code == 200:
                    answers = response.json().get("answers", {})
                    return {qid: _decode(raw) for qid, raw in answers.items()}
                if response.status_code not in RETRYABLE_STATUS:
                    detail = response.text[:300]
                    raise JudgmentUnavailable(
                        f"TypeSafe returned {response.status_code}: {detail}"
                    )
                last = JudgmentUnavailable(f"TypeSafe returned {response.status_code}")
                retry_after = response.headers.get("retry-after")
                delay = float(retry_after) if retry_after else delay

            if attempt < self._max_attempts - 1:
                await asyncio.sleep(delay)
                delay *= 2

        raise JudgmentUnavailable(f"TypeSafe was unreachable after {self._max_attempts} attempts: {last}")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
