from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ApplicationStatus = Literal[
    "captured",
    "applied",
    "assessment",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
]


class CaptureRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    captured_at: datetime
    source_url: str = Field(min_length=1, max_length=2048)
    source_type: Literal["extension", "manual", "import"] = "extension"
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=240)
    status: ApplicationStatus = "applied"
    extraction_confidence: float = Field(default=1.0, ge=0, le=1)
    selected_resume_id: str | None = Field(default=None, max_length=36)
    screenshot_artifact_id: str | None = Field(default=None, max_length=36)
    page_excerpt: str | None = Field(default=None, max_length=5_000)

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        clean = value.strip()
        if not clean.startswith(("http://", "https://")):
            raise ValueError("source_url must use http or https")
        return clean


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=240)
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=8_000)
    needs_review: bool | None = None
    next_action_at: datetime | None = None


class ApplicationResponse(BaseModel):
    id: str
    source_url: str
    source_type: str
    company: str
    role: str
    status: str
    captured_at: datetime
    extraction_confidence: float
    selected_resume_id: str | None
    screenshot_artifact_id: str | None
    notes: str | None
    needs_review: bool
    next_action_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeletionReceiptResponse(BaseModel):
    id: str
    status: str
    requested_at: datetime
    completed_at: datetime | None
    backup_expires_at: datetime | None
    categories_removed: list[str]
    artifacts_removed: int
