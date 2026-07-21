from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Application, utc_now
from backend.modules.applications import (
    add_application_event,
    get_application_timeline,
)

SideEffect = Literal["none", "workspace", "external"]


@dataclass(frozen=True)
class ToolContext:
    user_id: str
    run_context: dict
    session_factory: sessionmaker[Session]


class AutomationTool(Protocol):
    name: str
    description: str
    input_model: type[BaseModel]
    side_effect: SideEffect
    requires_confirmation: bool

    async def execute(self, context: ToolContext, payload: BaseModel) -> dict: ...


class SearchApplicationsInput(BaseModel):
    search: str = Field(default="", max_length=120)
    status: str | None = Field(default=None, max_length=40)
    limit: int = Field(default=25, ge=1, le=100)


class SearchApplicationsTool:
    name = "applications.search"
    description = "Find the user's applications by company, role, or stage."
    input_model = SearchApplicationsInput
    side_effect: SideEffect = "none"
    requires_confirmation = False

    async def execute(self, context: ToolContext, payload: SearchApplicationsInput) -> dict:
        with context.session_factory() as db:
            statement = select(Application).where(Application.user_id == context.user_id)
            if payload.search.strip():
                term = f"%{payload.search.strip()}%"
                statement = statement.where(
                    or_(Application.company.ilike(term), Application.role.ilike(term))
                )
            if payload.status:
                statement = statement.where(Application.status == payload.status)
            items = list(
                db.scalars(statement.order_by(Application.updated_at.desc()).limit(payload.limit))
            )
        return {
            "count": len(items),
            "applications": [
                {
                    "id": item.id,
                    "company": item.company,
                    "role": item.role,
                    "status": item.status,
                    "captured_at": item.captured_at.isoformat(),
                    "next_action_at": (
                        item.next_action_at.isoformat() if item.next_action_at else None
                    ),
                    "needs_review": item.needs_review,
                }
                for item in items
            ],
        }


class PipelineSummaryInput(BaseModel):
    include_attention: bool = True


class PipelineSummaryTool:
    name = "applications.pipeline_summary"
    description = "Count applications by stage and identify records needing review."
    input_model = PipelineSummaryInput
    side_effect: SideEffect = "none"
    requires_confirmation = False

    async def execute(self, context: ToolContext, payload: PipelineSummaryInput) -> dict:
        with context.session_factory() as db:
            counts = dict(
                db.execute(
                    select(Application.status, func.count(Application.id))
                    .where(Application.user_id == context.user_id)
                    .group_by(Application.status)
                ).all()
            )
            review = 0
            if payload.include_attention:
                review = (
                    db.scalar(
                        select(func.count(Application.id)).where(
                            Application.user_id == context.user_id,
                            Application.needs_review.is_(True),
                        )
                    )
                    or 0
                )
        return {"total": sum(counts.values()), "stages": counts, "needs_review": review}


class FilterApplicationsInput(BaseModel):
    search: str = Field(default="", max_length=120)
    status: Literal[
        "all",
        "captured",
        "applied",
        "assessment",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
    ] = "all"


class FilterApplicationsTool:
    name = "workspace.filter_applications"
    description = (
        "Open the Applications workspace with a company, role, or stage filter. "
        "This changes only the user's current view and does not edit application data."
    )
    input_model = FilterApplicationsInput
    side_effect: SideEffect = "none"
    requires_confirmation = False

    async def execute(self, context: ToolContext, payload: FilterApplicationsInput) -> dict:
        return {
            "ui_action": {
                "type": "filter_applications",
                "search": payload.search.strip(),
                "status": payload.status,
            },
            "message": "The application view is ready.",
        }


class ApplicationTimelineInput(BaseModel):
    application_id: str = Field(min_length=36, max_length=36)


class ApplicationTimelineTool:
    name = "applications.timeline"
    description = "Read the ordered event timeline for one application owned by the user."
    input_model = ApplicationTimelineInput
    side_effect: SideEffect = "none"
    requires_confirmation = False

    async def execute(self, context: ToolContext, payload: ApplicationTimelineInput) -> dict:
        with context.session_factory() as db:
            application = db.scalar(
                select(Application).where(
                    Application.id == payload.application_id,
                    Application.user_id == context.user_id,
                )
            )
            if application is None:
                raise ValueError("Application was not found.")
            events = get_application_timeline(
                db,
                user_id=context.user_id,
                application_id=application.id,
            )
        return {
            "application": {
                "id": application.id,
                "company": application.company,
                "role": application.role,
                "status": application.status,
            },
            "events": [
                {
                    "type": event["type"],
                    "title": event["title"],
                    "details": event["details"],
                    "occurred_at": event["occurred_at"].isoformat(),
                }
                for event in events
            ],
        }


class UpdateApplicationStatusInput(BaseModel):
    application_id: str = Field(min_length=36, max_length=36)
    status: Literal[
        "captured",
        "applied",
        "assessment",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
    ]


class UpdateApplicationStatusTool:
    name = "applications.update_status"
    description = "Move an application to a different pipeline stage."
    input_model = UpdateApplicationStatusInput
    side_effect: SideEffect = "workspace"
    requires_confirmation = True

    async def execute(self, context: ToolContext, payload: UpdateApplicationStatusInput) -> dict:
        confirmed = set(context.run_context.get("confirmed_tools", []))
        if self.name not in confirmed:
            return {
                "approval_required": True,
                "tool": self.name,
                "proposed_input": payload.model_dump(),
                "message": "Confirm the stage change before it is applied.",
            }

        with context.session_factory() as db:
            application = db.scalar(
                select(Application).where(
                    Application.id == payload.application_id,
                    Application.user_id == context.user_id,
                )
            )
            if application is None:
                raise ValueError("Application was not found.")
            previous = application.status
            application.status = payload.status
            application.updated_at = utc_now()
            add_application_event(
                db,
                user_id=context.user_id,
                application_id=application.id,
                event_type="stage_changed",
                title=f"Moved from {previous} to {payload.status}",
                details={"from": previous, "to": payload.status, "source": "automation"},
            )
            db.commit()
        return {
            "application_id": payload.application_id,
            "previous_status": previous,
            "status": payload.status,
        }


class ToolRegistry:
    def __init__(self, tools: list[AutomationTool] | None = None):
        default_tools: list[AutomationTool] = [
            SearchApplicationsTool(),
            PipelineSummaryTool(),
            FilterApplicationsTool(),
            ApplicationTimelineTool(),
            UpdateApplicationStatusTool(),
        ]
        self._tools = {tool.name: tool for tool in (tools or default_tools)}

    def catalog(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_model.model_json_schema(),
                "side_effect": tool.side_effect,
                "requires_confirmation": tool.requires_confirmation,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, context: ToolContext, name: str, payload: dict) -> dict:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        parsed = tool.input_model.model_validate(payload)
        return await tool.execute(context, parsed)

    def has(self, name: str) -> bool:
        return name in self._tools
