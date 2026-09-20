import asyncio
import json
import time
from collections.abc import AsyncIterator

from sqlalchemy import func, select

from backend.config import Config
from backend.database import Database
from backend.integrations.llm import LLMProvider, LLMRequest
from backend.models import (
    AgentDefinition,
    AutomationEvent,
    AutomationRun,
    AutomationTask,
    Conversation,
    ConversationMessage,
    User,
    utc_now,
)
from backend.modules.automation.planner import WorkflowPlanner
from backend.modules.automation.schemas import RunCreate, TaskInput
from backend.modules.automation.tools import ToolContext, ToolRegistry
from backend.modules.matching import JobRanker

DEFAULT_AGENT_INSTRUCTIONS = """
You are the Career Workspace assistant. Help the user understand and progress their
job search using only supplied records and tool results. Separate facts from advice.
Do not invent experience, company information, contacts, outcomes, or communication.
Draft external messages, but do not claim they were sent. Keep the answer direct.
""".strip()


class InvalidWorkflow(ValueError):
    pass


class AutomationService:
    def __init__(
        self,
        config: Config,
        database: Database,
        provider: LLMProvider,
        registry: ToolRegistry | None = None,
        ranker: JobRanker | None = None,
    ):
        self.config = config
        self.database = database
        self.provider = provider
        self.registry = registry or ToolRegistry(ranker=ranker)
        self.planner = WorkflowPlanner(config, provider)
        self.queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.worker_task and not self.worker_task.done():
            return
        self.worker_task = asyncio.create_task(self._worker(), name="automation-worker")
        with self.database.session_factory() as db:
            queued = list(
                db.scalars(select(AutomationRun.id).where(AutomationRun.status == "queued"))
            )
        for run_id in queued:
            self.queue.put_nowait(run_id)

    async def stop(self) -> None:
        if not self.worker_task:
            return
        await self.queue.put(None)
        await self.worker_task
        self.worker_task = None

    async def enqueue(self, run_id: str) -> None:
        await self.queue.put(run_id)

    def create_run(self, user: User, payload: RunCreate) -> AutomationRun:
        with self.database.session_factory() as db:
            agent = None
            if payload.agent_id:
                agent = db.scalar(
                    select(AgentDefinition).where(
                        AgentDefinition.id == payload.agent_id,
                        AgentDefinition.user_id == user.id,
                        AgentDefinition.enabled.is_(True),
                    )
                )
                if agent is None:
                    raise InvalidWorkflow("The selected agent was not found.")

            conversation = None
            if payload.conversation_id:
                conversation = db.scalar(
                    select(Conversation).where(
                        Conversation.id == payload.conversation_id,
                        Conversation.user_id == user.id,
                    )
                )
                if conversation is None:
                    raise InvalidWorkflow("The conversation was not found.")

            tasks = self._normalize_tasks(payload.tasks, payload.mode)
            self._validate_tasks(tasks)
            run = AutomationRun(
                user_id=user.id,
                conversation_id=conversation.id if conversation else None,
                agent_definition_id=agent.id if agent else None,
                prompt=payload.prompt.strip(),
                mode=payload.mode,
                context=payload.context,
            )
            db.add(run)
            db.flush()
            for position, task in enumerate(tasks):
                db.add(self._task_model(run.id, position, task))
            if conversation:
                db.add(
                    ConversationMessage(
                        user_id=user.id,
                        conversation_id=conversation.id,
                        run_id=run.id,
                        role="user",
                        content=run.prompt,
                    )
                )
                conversation.updated_at = utc_now()
            self._add_event(db, run, "run_queued", "Automation queued")
            db.commit()
            db.refresh(run)
            return run

    @staticmethod
    def _normalize_tasks(tasks: list[TaskInput], mode: str) -> list[TaskInput]:
        normalized = [task.model_copy(deep=True) for task in tasks]
        if mode == "sequential":
            for index, task in enumerate(normalized):
                task.depends_on = [normalized[index - 1].key] if index else []
        elif mode == "parallel":
            for task in normalized:
                task.depends_on = []
        return normalized

    @staticmethod
    def _validate_tasks(tasks: list[TaskInput]) -> None:
        keys = [task.key for task in tasks]
        if len(keys) != len(set(keys)):
            raise InvalidWorkflow("Task keys must be unique.")
        key_set = set(keys)
        for task in tasks:
            if task.key in task.depends_on:
                raise InvalidWorkflow(f"Task {task.key} cannot depend on itself.")
            missing = set(task.depends_on) - key_set
            if missing:
                raise InvalidWorkflow(
                    f"Task {task.key} has unknown dependencies: {', '.join(sorted(missing))}."
                )

    @staticmethod
    def _task_model(run_id: str, position: int, task: TaskInput) -> AutomationTask:
        return AutomationTask(
            run_id=run_id,
            task_key=task.key,
            name=task.name,
            kind=task.kind,
            tool_name=task.tool_name,
            instructions=task.instructions,
            input=task.input,
            depends_on=task.depends_on,
            position=position,
        )

    @staticmethod
    def _add_event(
        db,
        run: AutomationRun,
        event_type: str,
        message: str,
        data: dict | None = None,
    ) -> None:
        current = db.scalar(
            select(func.max(AutomationEvent.sequence)).where(AutomationEvent.run_id == run.id)
        )
        db.add(
            AutomationEvent(
                user_id=run.user_id,
                run_id=run.id,
                sequence=(current or 0) + 1,
                event_type=event_type,
                message=message,
                data=data,
            )
        )

    def _conversation_text(self, db, run: AutomationRun) -> str:
        if not run.conversation_id:
            return ""
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == run.conversation_id,
                Conversation.user_id == run.user_id,
            )
        )
        if conversation is None:
            return ""
        messages = list(
            db.scalars(
                select(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id == conversation.id,
                    ConversationMessage.created_at >= conversation.context_started_at,
                )
                .order_by(ConversationMessage.created_at.desc())
                .limit(20)
            )
        )
        messages.reverse()
        return "\n".join(f"{message.role}: {message.content}" for message in messages)

    async def _worker(self) -> None:
        while True:
            run_id = await self.queue.get()
            if run_id is None:
                self.queue.task_done()
                return
            try:
                await self._execute_run(run_id)
            except Exception as error:
                self._fail_run(run_id, error)
            finally:
                self.queue.task_done()

    async def _execute_run(self, run_id: str) -> None:
        started = time.perf_counter()
        with self.database.session_factory() as db:
            run = db.get(AutomationRun, run_id)
            if run is None or run.status != "queued":
                return
            run.status = "running"
            run.started_at = utc_now()
            run.error = None
            agent = (
                db.get(AgentDefinition, run.agent_definition_id)
                if run.agent_definition_id
                else None
            )
            agent_instructions = agent.instructions if agent else DEFAULT_AGENT_INSTRUCTIONS
            agent_model = agent.model if agent and agent.model else self.config.model
            allowed_tools = set(agent.allowed_tools) if agent else None
            conversation = self._conversation_text(db, run)
            self._add_event(db, run, "run_started", "Automation started")
            db.commit()
            user_id = run.user_id
            prompt = run.prompt
            run_context = run.context

        with self.database.session_factory() as db:
            tasks = list(
                db.scalars(
                    select(AutomationTask)
                    .where(AutomationTask.run_id == run_id)
                    .order_by(AutomationTask.position)
                )
            )
        if not tasks:
            catalog = self.registry.catalog()
            if allowed_tools is not None:
                catalog = [tool for tool in catalog if tool["name"] in allowed_tools]
            planned = await self.planner.plan(
                user_id=user_id,
                prompt=prompt,
                context=run_context,
                conversation=conversation,
                tools=catalog,
                agent_instructions=agent_instructions,
                model=agent_model,
            )
            planned = self._normalize_tasks(planned, "graph")
            self._validate_tasks(planned)
            with self.database.session_factory() as db:
                run = db.get(AutomationRun, run_id)
                for position, task in enumerate(planned):
                    db.add(self._task_model(run_id, position, task))
                self._add_event(
                    db,
                    run,
                    "workflow_planned",
                    f"Created {len(planned)} workflow tasks",
                )
                db.commit()

        with self.database.session_factory() as db:
            finished_tasks = list(
                db.scalars(
                    select(AutomationTask).where(
                        AutomationTask.run_id == run_id,
                        AutomationTask.status == "completed",
                    )
                )
            )
        results: dict[str, dict] = {task.task_key: task.result or {} for task in finished_tasks}
        completed: set[str] = set(results)
        while True:
            with self.database.session_factory() as db:
                run = db.get(AutomationRun, run_id)
                tasks = list(
                    db.scalars(
                        select(AutomationTask)
                        .where(AutomationTask.run_id == run_id)
                        .order_by(AutomationTask.position)
                    )
                )
                if run.cancel_requested:
                    run.status = "cancelled"
                    run.completed_at = utc_now()
                    self._add_event(db, run, "run_cancelled", "Automation cancelled")
                    db.commit()
                    return
                pending = [task for task in tasks if task.status == "pending"]
                if not pending:
                    break
                ready = [task for task in pending if set(task.depends_on) <= completed]
                if not ready:
                    raise InvalidWorkflow("The workflow contains a dependency cycle.")
                ready_payloads = [
                    {
                        "id": task.id,
                        "key": task.task_key,
                        "name": task.name,
                        "kind": task.kind,
                        "tool_name": task.tool_name,
                        "instructions": task.instructions,
                        "input": task.input,
                        "depends_on": task.depends_on,
                    }
                    for task in ready
                ]
                for task in ready:
                    task.status = "running"
                    task.started_at = utc_now()
                    self._add_event(
                        db,
                        run,
                        "task_started",
                        f"Started {task.name}",
                        {"task_key": task.task_key},
                    )
                db.commit()

            batch = await asyncio.gather(
                *[
                    self._execute_task(
                        user_id=user_id,
                        prompt=prompt,
                        run_context=run_context,
                        conversation=conversation,
                        agent_instructions=agent_instructions,
                        model=agent_model,
                        allowed_tools=allowed_tools,
                        task=task,
                        prior_results=results,
                    )
                    for task in ready_payloads
                ],
                return_exceptions=True,
            )

            waiting_for_approval = False
            with self.database.session_factory() as db:
                run = db.get(AutomationRun, run_id)
                for task_data, outcome in zip(ready_payloads, batch, strict=True):
                    task = db.get(AutomationTask, task_data["id"])
                    if isinstance(outcome, Exception):
                        task.status = "failed"
                        task.error = str(outcome)[:2_000]
                        task.completed_at = utc_now()
                        self._add_event(
                            db,
                            run,
                            "task_failed",
                            f"Failed {task.name}",
                            {"task_key": task.task_key},
                        )
                        db.commit()
                        raise outcome
                    if outcome.get("approval_required"):
                        task.status = "waiting_approval"
                        task.result = outcome
                        waiting_for_approval = True
                        self._add_event(
                            db,
                            run,
                            "approval_required",
                            outcome.get("message", "Approval is required"),
                            {"task_key": task.task_key, "tool": task.tool_name},
                        )
                        continue
                    task.status = "completed"
                    task.result = outcome
                    task.completed_at = utc_now()
                    results[task.task_key] = outcome
                    completed.add(task.task_key)
                    self._add_event(
                        db,
                        run,
                        "task_completed",
                        f"Completed {task.name}",
                        {"task_key": task.task_key},
                    )
                if waiting_for_approval:
                    run.status = "waiting_approval"
                    db.commit()
                    return
                db.commit()

        result_text = self._final_result(results)
        with self.database.session_factory() as db:
            run = db.get(AutomationRun, run_id)
            run.status = "completed"
            run.result = result_text
            run.completed_at = utc_now()
            run.elapsed_ms = round((time.perf_counter() - started) * 1000)
            self._add_event(db, run, "run_completed", "Automation completed")
            if run.conversation_id:
                db.add(
                    ConversationMessage(
                        user_id=run.user_id,
                        conversation_id=run.conversation_id,
                        run_id=run.id,
                        role="assistant",
                        content=result_text,
                    )
                )
                conversation_row = db.get(Conversation, run.conversation_id)
                if conversation_row:
                    conversation_row.updated_at = utc_now()
            db.commit()

    async def _execute_task(
        self,
        *,
        user_id: str,
        prompt: str,
        run_context: dict,
        conversation: str,
        agent_instructions: str,
        model: str,
        allowed_tools: set[str] | None,
        task: dict,
        prior_results: dict[str, dict],
    ) -> dict:
        if task["kind"] == "tool":
            tool_name = task["tool_name"]
            if not tool_name:
                raise InvalidWorkflow(f"Tool task {task['key']} has no tool name.")
            if allowed_tools is not None and tool_name not in allowed_tools:
                raise InvalidWorkflow(f"Agent is not allowed to use {tool_name}.")
            return await self.registry.execute(
                ToolContext(
                    user_id=user_id,
                    run_context=run_context,
                    session_factory=self.database.session_factory,
                ),
                tool_name,
                task["input"],
            )

        dependencies = {
            key: prior_results[key] for key in task["depends_on"] if key in prior_results
        }
        task_input = "\n\n".join(
            [
                f"User request:\n{prompt}",
                f"Task:\n{task['instructions'] or task['name']}",
                f"Workspace context:\n{json.dumps(run_context, default=str)[:8_000]}",
                f"Dependency results:\n{json.dumps(dependencies, default=str)[:20_000]}",
                f"Recent conversation:\n{conversation or 'No earlier messages.'}",
            ]
        )
        text = await self.provider.complete(
            LLMRequest(
                input=task_input,
                instructions=agent_instructions,
                model=model,
                max_output_tokens=self.config.max_output_tokens,
                user_id=user_id,
                metadata={"component": "automation_task", "task": task["key"][:64]},
            )
        )
        return {"text": text}

    @staticmethod
    def _final_result(results: dict[str, dict]) -> str:
        if not results:
            return "The workflow completed without a result."
        last = list(results.values())[-1]
        if isinstance(last, dict) and isinstance(last.get("text"), str):
            return last["text"]
        if len(results) == 1:
            return json.dumps(last, indent=2, default=str)
        return json.dumps(results, indent=2, default=str)

    def _fail_run(self, run_id: str, error: Exception) -> None:
        with self.database.session_factory() as db:
            run = db.get(AutomationRun, run_id)
            if run is None:
                return
            run.status = "failed"
            run.error = str(error)[:2_000]
            run.completed_at = utc_now()
            self._add_event(db, run, "run_failed", "Automation failed")
            if run.conversation_id:
                db.add(
                    ConversationMessage(
                        user_id=run.user_id,
                        conversation_id=run.conversation_id,
                        run_id=run.id,
                        role="assistant",
                        content="I could not complete that workflow. " + run.error,
                    )
                )
            db.commit()

    async def event_stream(
        self, run_id: str, user_id: str, after_sequence: int = 0
    ) -> AsyncIterator[dict]:
        sequence = after_sequence
        while True:
            with self.database.session_factory() as db:
                run = db.scalar(
                    select(AutomationRun).where(
                        AutomationRun.id == run_id,
                        AutomationRun.user_id == user_id,
                    )
                )
                if run is None:
                    raise InvalidWorkflow("Automation run was not found.")
                events = list(
                    db.scalars(
                        select(AutomationEvent)
                        .where(
                            AutomationEvent.run_id == run.id,
                            AutomationEvent.sequence > sequence,
                        )
                        .order_by(AutomationEvent.sequence)
                    )
                )
                terminal = run.status in {"completed", "failed", "cancelled", "waiting_approval"}
            for event in events:
                sequence = event.sequence
                yield {
                    "sequence": event.sequence,
                    "type": event.event_type,
                    "message": event.message,
                    "data": event.data,
                    "created_at": event.created_at.isoformat(),
                }
            if terminal:
                return
            await asyncio.sleep(0.35)
