import hashlib

from openai import AsyncOpenAI

from backend.integrations.llm.base import LLMRequest


class OpenAIResponsesProvider:
    """Small Responses API adapter used by every backend module."""

    def __init__(self, api_key: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url) if api_key else None

    async def complete(self, request: LLMRequest) -> str:
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        safety_identifier = hashlib.sha256(request.user_id.encode("utf-8")).hexdigest()[:64]
        response = await self.client.responses.create(
            model=request.model,
            instructions=request.instructions,
            input=request.input,
            max_output_tokens=request.max_output_tokens,
            parallel_tool_calls=True,
            safety_identifier=safety_identifier,
            store=False,
            metadata=request.metadata,
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("The model returned an empty response.")
        return text
