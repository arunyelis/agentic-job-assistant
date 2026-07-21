from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Literal

from agents import Agent, ModelSettings, Runner, function_tool

from backend.artifacts import save_artifact
from backend.browser import PlaywrightBrowser
from backend.config import Config
from backend.skills import Skill, skill_catalog


Activity = dict[str, str]
ActivityCallback = Callable[[Activity], None]

SPECIALISTS = {
    "job_researcher": {
        "name": "Job Researcher",
        "skill": "job-match",
        "instructions": (
            "Find concrete evidence, separate facts from assumptions, and return a compact "
            "fit assessment."
        ),
    },
    "application_writer": {
        "name": "Application Writer",
        "skill": "application-writing",
        "instructions": (
            "Write natural application material using only facts supplied by the user."
        ),
    },
    "follow_up_coach": {
        "name": "Follow-up Coach",
        "skill": "follow-up",
        "instructions": (
            "Draft a short follow-up and explain sensible timing. Never send it."
        ),
    },
}


class MissingApiKeyError(RuntimeError):
    pass


class MissingResumeError(ValueError):
    pass


@dataclass
class SessionState:
    resume_text: str = ""
    resume_name: str = ""
    history: list[dict[str, str]] = field(default_factory=list)


class JobAssistant:
    def __init__(
        self,
        config: Config,
        skills: dict[str, Skill],
        browser: PlaywrightBrowser,
    ):
        self.config = config
        self.skills = skills
        self.browser = browser
        self.sessions: dict[str, SessionState] = {}

    def set_resume(self, session_id: str, file_name: str, resume_text: str) -> None:
        session = self.sessions.setdefault(session_id, SessionState())
        session.resume_name = file_name
        session.resume_text = resume_text

    def reset(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def _session(self, session_id: str) -> SessionState:
        session = self.sessions.get(session_id)
        if not session or not session.resume_text:
            raise MissingResumeError("Upload a resume before starting the chat.")
        return session

    def _check_api_key(self) -> None:
        if not self.config.api_key:
            raise MissingApiKeyError("OPENAI_API_KEY is not set. Add it to your .env file.")

    @staticmethod
    def _history_text(history: list[dict[str, str]]) -> str:
        if not history:
            return "No earlier messages."
        return "\n\n".join(f"{item['role']}: {item['content']}" for item in history)

    @staticmethod
    def _has_url(text: str) -> bool:
        return "http://" in text.lower() or "https://" in text.lower()

    def _remember(self, session: SessionState, message: str, answer: str) -> None:
        session.history = [
            *session.history,
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ][-8:]

    async def _prepare(
        self,
        session_id: str,
        message: str,
        record: ActivityCallback,
    ) -> tuple[SessionState, Agent, list]:
        self._check_api_key()
        session = self._session(session_id)
        browser_servers = []
        browser_context = f"{self._history_text(session.history)}\n{message}"

        if self.config.browser_enabled and self._has_url(browser_context):
            try:
                browser = await self.browser.connect()
                if browser:
                    browser_servers.append(browser)
                    record({"type": "tool", "label": "Connected read-only Playwright MCP"})
            except Exception as error:
                record({"type": "warning", "label": f"Browser unavailable: {error}"})

        coordinator = self._create_coordinator(record, browser_servers)
        return session, coordinator, browser_servers

    def _input(self, session: SessionState, message: str) -> str:
        return "\n".join(
            [
                "Candidate resume:",
                session.resume_text,
                "",
                "Recent conversation:",
                self._history_text(session.history),
                "",
                f"User: {message}",
            ]
        )

    def _create_coordinator(self, record: ActivityCallback, browser_servers: list) -> Agent:
        @function_tool
        async def load_skill(name: str) -> str:
            """Load the full instructions for one skill.

            Args:
                name: Exact skill name from the available skills list.
            """
            skill = self.skills.get(name)
            if not skill:
                return f"Unknown skill: {name}"
            record({"type": "skill", "label": f"Loaded {name} skill"})
            return skill.instructions

        @function_tool
        async def spawn_specialist_agent(
            role: Literal["job_researcher", "application_writer", "follow_up_coach"],
            task: str,
            context: str = "",
        ) -> str:
            """Create one specialist only when separate focused work improves the answer.

            Args:
                role: The specialist best suited to the delegated work.
                task: A focused task for the specialist.
                context: Relevant resume, job, or conversation context.
            """
            specialist_config = SPECIALISTS[role]
            skill = self.skills.get(specialist_config["skill"])
            record({"type": "agent", "label": f"Spawned {role.replace('_', ' ')}"})

            specialist = Agent(
                name=specialist_config["name"],
                model=self.config.model,
                model_settings=ModelSettings(
                    max_tokens=min(self.config.max_output_tokens, 800),
                    reasoning={"effort": "low"},
                    verbosity="low",
                ),
                instructions="\n".join(
                    [
                        specialist_config["instructions"],
                        "You are a child agent. Complete only the delegated task.",
                        "Never invent candidate experience, company facts, contacts, or outcomes.",
                        "",
                        "Skill instructions:",
                        skill.instructions if skill else "No matching skill was found.",
                    ]
                ),
            )
            result = await Runner.run(
                specialist,
                f"Delegated task:\n{task[:2_000]}\n\nContext:\n{context[:14_000]}",
                max_turns=2,
            )
            return str(result.final_output or "The specialist returned no result.")

        @function_tool
        async def save_application_note(name: str, content: str) -> str:
            """Save material locally only when the user explicitly asks for a file.

            Args:
                name: Short file name without a path.
                content: Markdown content to save.
            """
            file_name, _ = save_artifact(
                self.config.artifacts_dir,
                name[:100],
                content[:30_000],
            )
            record({"type": "tool", "label": f"Saved {file_name}"})
            return f"Saved locally as artifacts/{file_name}"

        return Agent(
            name="Job Application Coordinator",
            model=self.config.model,
            model_settings=ModelSettings(
                max_tokens=self.config.max_output_tokens,
                reasoning={"effort": "low", "summary": "concise"},
                verbosity="low",
            ),
            instructions="\n".join(
                [
                    "You are a practical job application assistant.",
                    "Help assess roles, tailor truthful material, prepare for interviews, and draft follow-ups.",
                    "Load the most relevant skill before specialized work.",
                    "Spawn one specialist when a separate research or writing pass materially improves the answer.",
                    "Do not spawn a specialist for greetings, minor edits, or simple questions.",
                    "Use Playwright MCP to read a public job URL before assessing it when browser tools are available.",
                    "Browser access is read-only. Never log in, fill a form, upload, click apply or submit, or send email.",
                    "Never claim an external action happened and never invent experience, facts, metrics, or contacts.",
                    "Save a file only when the user explicitly asks to save or export it.",
                    "Keep answers direct, natural, and useful.",
                    "",
                    "Available skills:",
                    skill_catalog(self.skills),
                ]
            ),
            tools=[load_skill, spawn_specialist_agent, save_application_note],
            mcp_servers=browser_servers,
            mcp_config={"include_server_in_tool_names": True},
        )

    async def chat(self, session_id: str, message: str) -> dict:
        events: list[Activity] = []
        session, coordinator, browser_servers = await self._prepare(
            session_id, message, events.append
        )
        try:
            result = await Runner.run(
                coordinator,
                self._input(session, message),
                max_turns=8,
            )
        finally:
            for server in browser_servers:
                await self.browser.close(server)
        answer = str(result.final_output or "I could not produce a response.")
        self._remember(session, message, answer)
        return {"answer": answer, "events": events}

    async def stream(self, session_id: str, message: str) -> AsyncIterator[dict]:
        pending: deque[Activity] = deque()
        session, coordinator, browser_servers = await self._prepare(
            session_id, message, pending.append
        )
        result = Runner.run_streamed(
            coordinator,
            self._input(session, message),
            max_turns=8,
        )

        try:
            async for event in result.stream_events():
                while pending:
                    yield {"event": "activity", "data": pending.popleft()}

                if event.type == "raw_response_event":
                    event_type = getattr(event.data, "type", "")
                    if event_type == "response.output_text.delta":
                        yield {"event": "token", "data": {"text": event.data.delta}}
                    elif event_type == "response.reasoning_summary_text.delta":
                        yield {
                            "event": "reasoning",
                            "data": {
                                "text": event.data.delta,
                                "itemId": event.data.item_id,
                                "summaryIndex": event.data.summary_index,
                            },
                        }

                if event.type == "run_item_stream_event" and event.name == "tool_called":
                    raw_item = getattr(event.item, "raw_item", None)
                    tool_name = getattr(raw_item, "name", "")
                    if "browser_" in tool_name:
                        yield {
                            "event": "activity",
                            "data": {
                                "type": "tool",
                                "label": f"Used {tool_name.split('browser_', 1)[-1].replace('_', ' ')}",
                            },
                        }

            while pending:
                yield {"event": "activity", "data": pending.popleft()}
            answer = str(result.final_output or "I could not produce a response.")
        finally:
            for server in browser_servers:
                await self.browser.close(server)

        self._remember(session, message, answer)
        yield {"event": "complete", "data": {"answer": answer}}
