import json
import re

from backend.config import Config
from backend.integrations.llm import LLMProvider, LLMRequest
from backend.modules.automation.schemas import TaskInput


def parse_json_object(value: str) -> dict:
    clean = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", clean, flags=re.DOTALL)
    if fenced:
        clean = fenced.group(1)
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("The workflow plan must be an object.")
    return parsed


class WorkflowPlanner:
    def __init__(self, config: Config, provider: LLMProvider):
        self.config = config
        self.provider = provider

    async def plan(
        self,
        *,
        user_id: str,
        prompt: str,
        context: dict,
        conversation: str,
        tools: list[dict],
        agent_instructions: str,
        model: str,
    ) -> list[TaskInput]:
        tool_text = json.dumps(tools, separators=(",", ":"))
        planner_instructions = """
You plan a small career-workspace workflow. Return one JSON object and no markdown.
The object must contain a tasks array. Each task has key, name, kind, tool_name,
instructions, input, and depends_on. kind is tool, llm, or agent. Use independent
tasks with no dependencies when they can run concurrently. Add dependencies only
when a task requires earlier output. End tool-heavy workflows with one llm synthesis
task that depends on the relevant tool tasks. Use at most six tasks. Never invent a
tool name. Never schedule a side-effecting tool unless the user explicitly asked for
that exact workspace change. External communication is draft-only.
""".strip()
        planner_input = "\n\n".join(
            [
                f"User request:\n{prompt}",
                f"Current workspace context:\n{json.dumps(context, default=str)[:8_000]}",
                f"Recent conversation:\n{conversation or 'No earlier messages.'}",
                f"Available tools:\n{tool_text}",
                f"Selected agent instructions:\n{agent_instructions}",
            ]
        )
        raw = await self.provider.complete(
            LLMRequest(
                input=planner_input,
                instructions=planner_instructions,
                model=model,
                max_output_tokens=min(900, self.config.max_output_tokens),
                user_id=user_id,
                metadata={"component": "workflow_planner"},
            )
        )
        data = parse_json_object(raw)
        tasks = [TaskInput.model_validate(item) for item in data.get("tasks", [])]
        if not tasks:
            raise ValueError("The model did not create any workflow tasks.")
        return tasks[:6]
