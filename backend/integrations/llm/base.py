from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    input: str
    instructions: str
    model: str
    max_output_tokens: int
    user_id: str
    metadata: dict[str, str] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> str: ...
