import json
from collections.abc import Iterator

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import COOKIE_NAME, AuthenticationError, AuthService
from backend.database import Database
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
from backend.modules.automation.schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    ConversationCreate,
    ConversationResponse,
    EventResponse,
    MessageResponse,
    RunApproval,
    RunCreate,
    RunResponse,
    TaskResponse,
    ToolResponse,
)
from backend.modules.automation.service import AutomationService, InvalidWorkflow


def create_automation_router(
    database: Database,
    auth: AuthService,
    service: AutomationService,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["automation"])

    def session() -> Iterator[Session]:
        with database.session_factory() as value:
            yield value

    def current_user(
        db: Session = Depends(session),
        token: str | None = Cookie(default=None, alias=COOKIE_NAME),
        authorization: str | None = Header(default=None),
    ) -> User:
        bearer = None
        if authorization and authorization.lower().startswith("bearer "):
            bearer = authorization[7:].strip()
        try:
            return auth.user_from_token(db, bearer or token)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    def owned_run(db: Session, user_id: str, run_id: str) -> AutomationRun:
        run = db.scalar(
            select(AutomationRun).where(
                AutomationRun.id == run_id,
                AutomationRun.user_id == user_id,
            )
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Automation run was not found.")
        return run

    def run_response(db: Session, run: AutomationRun) -> RunResponse:
        tasks = list(
            db.scalars(
                select(AutomationTask)
                .where(AutomationTask.run_id == run.id)
                .order_by(AutomationTask.position)
            )
        )
        events = list(
            db.scalars(
                select(AutomationEvent)
                .where(AutomationEvent.run_id == run.id)
                .order_by(AutomationEvent.sequence)
            )
        )
        return RunResponse(
            **{
                column: getattr(run, column)
                for column in RunResponse.model_fields
                if column not in {"tasks", "events"}
            },
            tasks=[TaskResponse.model_validate(task) for task in tasks],
            events=[EventResponse.model_validate(event) for event in events],
        )

    @router.get("/automation/tools", response_model=list[ToolResponse])
    def list_tools(_: User = Depends(current_user)) -> list[ToolResponse]:
        return [ToolResponse.model_validate(item) for item in service.registry.catalog()]

    @router.post("/automation/runs", response_model=RunResponse, status_code=202)
    async def create_run(
        payload: RunCreate,
        user: User = Depends(current_user),
    ) -> RunResponse:
        try:
            run = service.create_run(user, payload)
        except InvalidWorkflow as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        await service.enqueue(run.id)
        with database.session_factory() as db:
            return run_response(db, owned_run(db, user.id, run.id))

    @router.get("/automation/runs", response_model=list[RunResponse])
    def list_runs(
        limit: int = Query(default=20, ge=1, le=100),
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[RunResponse]:
        runs = list(
            db.scalars(
                select(AutomationRun)
                .where(AutomationRun.user_id == user.id)
                .order_by(AutomationRun.created_at.desc())
                .limit(limit)
            )
        )
        return [run_response(db, run) for run in runs]

    @router.get("/automation/runs/{run_id}", response_model=RunResponse)
    def get_run(
        run_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> RunResponse:
        return run_response(db, owned_run(db, user.id, run_id))

    @router.post("/automation/runs/{run_id}/cancel", response_model=RunResponse)
    def cancel_run(
        run_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> RunResponse:
        run = owned_run(db, user.id, run_id)
        if run.status not in {"queued", "running", "waiting_approval"}:
            raise HTTPException(status_code=409, detail="This run can no longer be cancelled.")
        run.cancel_requested = True
        if run.status == "waiting_approval":
            run.status = "cancelled"
            run.completed_at = utc_now()
        db.commit()
        return run_response(db, run)

    @router.post("/automation/runs/{run_id}/approve", response_model=RunResponse)
    async def approve_run(
        run_id: str,
        payload: RunApproval,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> RunResponse:
        run = owned_run(db, user.id, run_id)
        if run.status != "waiting_approval":
            raise HTTPException(status_code=409, detail="This run is not waiting for approval.")
        catalog = {item["name"] for item in service.registry.catalog()}
        unknown = set(payload.tools) - catalog
        if unknown:
            raise HTTPException(status_code=400, detail="One or more tools are unknown.")
        context = dict(run.context or {})
        context["confirmed_tools"] = sorted(
            set(context.get("confirmed_tools", [])) | set(payload.tools)
        )
        run.context = context
        run.status = "queued"
        for task in db.scalars(
            select(AutomationTask).where(
                AutomationTask.run_id == run.id,
                AutomationTask.status == "waiting_approval",
            )
        ):
            task.status = "pending"
            task.result = None
        db.commit()
        await service.enqueue(run.id)
        return run_response(db, run)

    @router.get("/automation/runs/{run_id}/events")
    async def stream_events(
        run_id: str,
        request: Request,
        after: int = Query(default=0, ge=0),
        user: User = Depends(current_user),
    ) -> StreamingResponse:
        async def events():
            try:
                async for event in service.event_stream(run_id, user.id, after):
                    if await request.is_disconnected():
                        return
                    yield f"event: run\ndata: {json.dumps(event)}\n\n"
            except InvalidWorkflow as error:
                yield f"event: error\ndata: {json.dumps({'message': str(error)})}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/automation/agents", response_model=list[AgentResponse])
    def list_agents(
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[AgentResponse]:
        agents = list(
            db.scalars(
                select(AgentDefinition)
                .where(AgentDefinition.user_id == user.id)
                .order_by(AgentDefinition.updated_at.desc())
            )
        )
        return [AgentResponse.model_validate(agent) for agent in agents]

    @router.post("/automation/agents", response_model=AgentResponse, status_code=201)
    def create_agent(
        payload: AgentCreate,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> AgentResponse:
        known_tools = {item["name"] for item in service.registry.catalog()}
        if set(payload.allowed_tools) - known_tools:
            raise HTTPException(status_code=400, detail="One or more tools are unknown.")
        agent = AgentDefinition(user_id=user.id, **payload.model_dump())
        db.add(agent)
        db.commit()
        return AgentResponse.model_validate(agent)

    @router.patch("/automation/agents/{agent_id}", response_model=AgentResponse)
    def update_agent(
        agent_id: str,
        payload: AgentUpdate,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> AgentResponse:
        agent = db.scalar(
            select(AgentDefinition).where(
                AgentDefinition.id == agent_id,
                AgentDefinition.user_id == user.id,
            )
        )
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent was not found.")
        values = payload.model_dump(exclude_unset=True)
        if "allowed_tools" in values:
            known_tools = {item["name"] for item in service.registry.catalog()}
            if set(values["allowed_tools"]) - known_tools:
                raise HTTPException(status_code=400, detail="One or more tools are unknown.")
        for field, value in values.items():
            setattr(agent, field, value)
        db.commit()
        return AgentResponse.model_validate(agent)

    @router.get("/assistant/conversations", response_model=list[ConversationResponse])
    def list_conversations(
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[ConversationResponse]:
        conversations = list(
            db.scalars(
                select(Conversation)
                .where(Conversation.user_id == user.id)
                .order_by(Conversation.updated_at.desc())
            )
        )
        return [ConversationResponse.model_validate(item) for item in conversations]

    @router.post(
        "/assistant/conversations",
        response_model=ConversationResponse,
        status_code=201,
    )
    def create_conversation(
        payload: ConversationCreate,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> ConversationResponse:
        conversation = Conversation(user_id=user.id, title=payload.title.strip())
        db.add(conversation)
        db.commit()
        return ConversationResponse.model_validate(conversation)

    @router.get(
        "/assistant/conversations/{conversation_id}/messages",
        response_model=list[MessageResponse],
    )
    def list_messages(
        conversation_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[MessageResponse]:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation was not found.")
        messages = list(
            db.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at)
            )
        )
        return [MessageResponse.model_validate(message) for message in messages]

    @router.post(
        "/assistant/conversations/{conversation_id}/clear",
        response_model=ConversationResponse,
    )
    def clear_conversation_context(
        conversation_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> ConversationResponse:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation was not found.")
        now = utc_now()
        conversation.context_started_at = now
        conversation.updated_at = now
        db.add(
            ConversationMessage(
                user_id=user.id,
                conversation_id=conversation.id,
                role="system",
                content="Context cleared. Earlier messages remain in history.",
            )
        )
        db.commit()
        return ConversationResponse.model_validate(conversation)

    return router
