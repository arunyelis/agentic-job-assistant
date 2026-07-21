from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RunMode = Literal["auto", "sequential", "parallel", "graph"]
TaskKind = Literal["tool", "llm", "agent"]


class TaskInput(BaseModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    kind: TaskKind = "llm"
    tool_name: str | None = Field(default=None, max_length=120)
    instructions: str = Field(default="", max_length=8_000)
    input: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("depends_on")
    @classmethod
    def unique_dependencies(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class RunCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=12_000)
    mode: RunMode = "auto"
    agent_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)
    context: dict = Field(default_factory=dict)
    tasks: list[TaskInput] = Field(default_factory=list, max_length=12)


class RunApproval(BaseModel):
    tools: list[str] = Field(min_length=1, max_length=12)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_key: str
    name: str
    kind: str
    tool_name: str | None
    instructions: str
    input: dict
    depends_on: list[str]
    position: int
    status: str
    result: dict | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    event_type: str
    message: str
    data: dict | None
    created_at: datetime


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str | None
    agent_definition_id: str | None
    prompt: str
    mode: str
    status: str
    context: dict
    result: str | None
    error: str | None
    cancel_requested: bool
    elapsed_ms: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    tasks: list[TaskResponse] = Field(default_factory=list)
    events: list[EventResponse] = Field(default_factory=list)


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(min_length=10, max_length=12_000)
    model: str | None = Field(default=None, max_length=120)
    allowed_tools: list[str] = Field(default_factory=list, max_length=24)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    instructions: str | None = Field(default=None, min_length=10, max_length=12_000)
    model: str | None = Field(default=None, max_length=120)
    allowed_tools: list[str] | None = Field(default=None, max_length=24)
    enabled: bool | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    instructions: str
    model: str | None
    allowed_tools: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict
    side_effect: Literal["none", "workspace", "external"]
    requires_confirmation: bool


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=160)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    context_started_at: datetime
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    run_id: str | None
    role: str
    content: str
    created_at: datetime
