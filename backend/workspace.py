import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import COOKIE_NAME, AuthenticationError, AuthService
from backend.config import Config
from backend.database import Database
from backend.models import (
    AgentDefinition,
    AgentRun,
    Application,
    ApplicationEvent,
    Artifact,
    AuditEvent,
    AutomationEvent,
    AutomationRun,
    CaptureEvent,
    CommunicationEvent,
    ConsentGrant,
    Conversation,
    ConversationMessage,
    DeletionRequest,
    EvidenceItem,
    ResumeVariant,
    User,
    new_id,
    utc_now,
)
from backend.modules.applications import add_application_event, get_application_timeline
from backend.storage import EncryptedFileStore
from backend.workspace_schemas import (
    ApplicationResponse,
    ApplicationUpdate,
    CaptureRequest,
    DeletionReceiptResponse,
)

ALLOWED_UPLOADS = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


def application_response(item: Application) -> ApplicationResponse:
    return ApplicationResponse.model_validate(item, from_attributes=True)


def deletion_response(item: DeletionRequest) -> DeletionReceiptResponse:
    categories = json.loads(item.categories_removed or "[]")
    return DeletionReceiptResponse(
        id=item.id,
        status=item.status,
        requested_at=item.requested_at,
        completed_at=item.completed_at,
        backup_expires_at=item.backup_expires_at,
        categories_removed=categories,
        artifacts_removed=item.artifacts_removed,
    )


def create_workspace_router(
    config: Config,
    database: Database,
    auth: AuthService,
    storage: EncryptedFileStore,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def session() -> Session:
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

    def audit(
        db: Session,
        user_id: str,
        event_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        db.add(
            AuditEvent(
                user_id=user_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(details, separators=(",", ":")) if details else None,
            )
        )

    @router.post("/auth/local-session")
    def local_session(response: Response, db: Session = Depends(session)) -> dict:
        if config.auth_mode != "local":
            raise HTTPException(status_code=404, detail="Local sessions are disabled.")
        user = auth.local_user(db)
        token = auth.issue(user.id)
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            secure=config.environment == "production",
            samesite="strict",
            max_age=auth.ttl_seconds,
            path="/",
        )
        return {
            "user": {
                "id": user.id,
                "displayName": user.display_name,
                "accountMode": "local",
            },
            "token": token,
            "expiresIn": auth.ttl_seconds,
        }

    @router.delete("/auth/session")
    def sign_out(response: Response) -> dict:
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"ok": True}

    @router.post(
        "/applications/capture",
        response_model=ApplicationResponse,
        status_code=201,
    )
    def capture_application(
        payload: CaptureRequest,
        response: Response,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> ApplicationResponse:
        existing = db.scalar(
            select(Application).where(
                Application.user_id == user.id,
                Application.idempotency_key == payload.idempotency_key,
            )
        )
        if existing:
            response.status_code = 200
            return application_response(existing)

        if payload.screenshot_artifact_id:
            screenshot = db.scalar(
                select(Artifact).where(
                    Artifact.id == payload.screenshot_artifact_id,
                    Artifact.user_id == user.id,
                )
            )
            if screenshot is None:
                raise HTTPException(status_code=400, detail="Screenshot artifact was not found.")

        item = Application(
            user_id=user.id,
            idempotency_key=payload.idempotency_key,
            source_url=payload.source_url,
            source_type=payload.source_type,
            company=payload.company.strip(),
            role=payload.role.strip(),
            status=payload.status,
            captured_at=payload.captured_at,
            extraction_confidence=payload.extraction_confidence,
            selected_resume_id=payload.selected_resume_id,
            screenshot_artifact_id=payload.screenshot_artifact_id,
            page_excerpt=payload.page_excerpt,
            needs_review=payload.extraction_confidence < 0.72,
        )
        db.add(item)
        db.flush()
        db.add(
            CaptureEvent(
                user_id=user.id,
                application_id=item.id,
                event_type="confirmed",
                detection_confidence=payload.extraction_confidence,
            )
        )
        add_application_event(
            db,
            user_id=user.id,
            application_id=item.id,
            event_type="application_captured",
            title="Application captured",
            details={"source": payload.source_type, "status": payload.status},
            occurred_at=payload.captured_at,
        )
        audit(db, user.id, "application_captured", "application", item.id)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicate = db.scalar(
                select(Application).where(
                    Application.user_id == user.id,
                    Application.idempotency_key == payload.idempotency_key,
                )
            )
            if duplicate is None:
                raise
            response.status_code = 200
            return application_response(duplicate)
        return application_response(item)

    @router.get("/applications", response_model=list[ApplicationResponse])
    def list_applications(
        search: str = Query(default="", max_length=120),
        status: str | None = Query(default=None, max_length=40),
        needs_review: bool | None = None,
        limit: int = Query(default=100, ge=1, le=200),
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[ApplicationResponse]:
        statement = select(Application).where(Application.user_id == user.id)
        if search.strip():
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(Application.company.ilike(term), Application.role.ilike(term))
            )
        if status:
            statement = statement.where(Application.status == status)
        if needs_review is not None:
            statement = statement.where(Application.needs_review == needs_review)
        statement = statement.order_by(Application.captured_at.desc()).limit(limit)
        return [application_response(item) for item in db.scalars(statement)]

    @router.get("/applications/{application_id}", response_model=ApplicationResponse)
    def get_application(
        application_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> ApplicationResponse:
        item = db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Application was not found.")
        return application_response(item)

    @router.patch("/applications/{application_id}", response_model=ApplicationResponse)
    def update_application(
        application_id: str,
        payload: ApplicationUpdate,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> ApplicationResponse:
        item = db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Application was not found.")
        values = payload.model_dump(exclude_unset=True)
        previous_status = item.status
        for field, value in values.items():
            setattr(item, field, value.strip() if isinstance(value, str) else value)
        if "status" in values and item.status != previous_status:
            add_application_event(
                db,
                user_id=user.id,
                application_id=item.id,
                event_type="stage_changed",
                title=f"Moved from {previous_status} to {item.status}",
                details={
                    "from": previous_status,
                    "to": item.status,
                    "source": "workspace",
                },
            )
        elif values:
            add_application_event(
                db,
                user_id=user.id,
                application_id=item.id,
                event_type="application_updated",
                title="Application details updated",
                details={"fields": sorted(values)},
            )
        audit(db, user.id, "application_updated", "application", item.id)
        db.commit()
        return application_response(item)

    @router.get("/applications/{application_id}/timeline")
    def application_timeline(
        application_id: str,
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> list[dict]:
        application = db.scalar(
            select(Application).where(
                Application.id == application_id,
                Application.user_id == user.id,
            )
        )
        if application is None:
            raise HTTPException(status_code=404, detail="Application was not found.")
        return get_application_timeline(db, user_id=user.id, application_id=application.id)

    @router.get("/today")
    def today(
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> dict:
        counts = dict(
            db.execute(
                select(Application.status, func.count(Application.id))
                .where(Application.user_id == user.id)
                .group_by(Application.status)
            ).all()
        )
        review_count = db.scalar(
            select(func.count(Application.id)).where(
                Application.user_id == user.id,
                Application.needs_review.is_(True),
            )
        )
        recent = list(
            db.scalars(
                select(Application)
                .where(Application.user_id == user.id)
                .order_by(Application.captured_at.desc())
                .limit(5)
            )
        )
        return {
            "total": sum(counts.values()),
            "counts": counts,
            "needsReview": review_count or 0,
            "recent": [application_response(item).model_dump(mode="json") for item in recent],
        }

    @router.post("/artifacts", status_code=201)
    async def upload_artifact(
        kind: str = Form(default="attachment", max_length=40),
        file: UploadFile = File(...),
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> dict:
        content_type = (file.content_type or "application/octet-stream").lower()
        if content_type not in ALLOWED_UPLOADS:
            raise HTTPException(status_code=400, detail="This file type is not supported.")
        data = await file.read(config.max_upload_bytes + 1)
        if len(data) > config.max_upload_bytes:
            raise HTTPException(status_code=413, detail="The file exceeds the upload limit.")
        if not data:
            raise HTTPException(status_code=400, detail="The file is empty.")
        artifact_id = new_id()
        file_name = Path(file.filename or "artifact").name[:255]
        storage_key = storage.put(user.id, artifact_id, data)
        item = Artifact(
            id=artifact_id,
            user_id=user.id,
            kind=kind,
            file_name=file_name,
            content_type=content_type,
            byte_count=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            storage_key=storage_key,
        )
        db.add(item)
        audit(db, user.id, "artifact_uploaded", "artifact", item.id, {"kind": kind})
        db.commit()
        return {
            "id": item.id,
            "kind": item.kind,
            "fileName": item.file_name,
            "contentType": item.content_type,
            "byteCount": item.byte_count,
            "createdAt": item.created_at,
        }

    @router.get("/account/export")
    def export_account(
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> JSONResponse:
        applications = list(
            db.scalars(
                select(Application)
                .where(Application.user_id == user.id)
                .order_by(Application.captured_at)
            )
        )
        artifacts = list(db.scalars(select(Artifact).where(Artifact.user_id == user.id)))
        consents = list(db.scalars(select(ConsentGrant).where(ConsentGrant.user_id == user.id)))
        audit(db, user.id, "account_exported", "user", user.id)
        db.commit()
        return JSONResponse(
            {
                "exportedAt": datetime.now(UTC).isoformat(),
                "account": {"id": user.id, "displayName": user.display_name},
                "applications": [
                    application_response(item).model_dump(mode="json") for item in applications
                ],
                "artifacts": [
                    {
                        "id": item.id,
                        "kind": item.kind,
                        "fileName": item.file_name,
                        "contentType": item.content_type,
                        "byteCount": item.byte_count,
                        "sha256": item.sha256,
                        "createdAt": item.created_at.isoformat(),
                    }
                    for item in artifacts
                ],
                "consents": [
                    {
                        "id": item.id,
                        "capability": item.capability,
                        "scope": item.scope,
                        "granted": item.granted,
                        "createdAt": item.created_at.isoformat(),
                        "revokedAt": item.revoked_at.isoformat() if item.revoked_at else None,
                    }
                    for item in consents
                ],
            },
            headers={"Content-Disposition": "attachment; filename=career-workspace-export.json"},
        )

    @router.post(
        "/account/deletion",
        response_model=DeletionReceiptResponse,
        status_code=202,
    )
    def delete_account(
        db: Session = Depends(session),
        user: User = Depends(current_user),
    ) -> DeletionReceiptResponse:
        request = DeletionRequest(user_id=user.id, status="processing")
        db.add(request)
        db.flush()
        artifacts = list(db.scalars(select(Artifact).where(Artifact.user_id == user.id)))
        for artifact in artifacts:
            storage.delete(artifact.storage_key)

        categories = [
            "applications",
            "application events",
            "capture events",
            "artifacts",
            "career evidence",
            "resume variants",
            "communication events",
            "agent runs",
            "automation runs",
            "custom agents",
            "assistant conversations",
            "consent grants",
            "audit events",
        ]
        for model in (
            ConversationMessage,
            AutomationEvent,
            AutomationRun,
            Conversation,
            AgentDefinition,
            ApplicationEvent,
            CaptureEvent,
            CommunicationEvent,
            Application,
            EvidenceItem,
            ResumeVariant,
            AgentRun,
            ConsentGrant,
            AuditEvent,
            Artifact,
        ):
            db.execute(delete(model).where(model.user_id == user.id))

        now = utc_now()
        request.status = "completed"
        request.completed_at = now
        request.backup_expires_at = now + timedelta(days=config.backup_retention_days)
        request.categories_removed = json.dumps(categories)
        request.artifacts_removed = len(artifacts)
        user.email = None
        user.display_name = None
        user.status = "deleted"
        db.commit()
        return deletion_response(request)

    @router.get(
        "/account/deletion/{request_id}",
        response_model=DeletionReceiptResponse,
    )
    def deletion_receipt(
        request_id: str,
        db: Session = Depends(session),
        token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ) -> DeletionReceiptResponse:
        try:
            user = auth.user_from_token(db, token, allow_deleted=True)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        request = db.scalar(
            select(DeletionRequest).where(
                DeletionRequest.id == request_id,
                DeletionRequest.user_id == user.id,
            )
        )
        if request is None:
            raise HTTPException(status_code=404, detail="Deletion receipt was not found.")
        return deletion_response(request)

    return router
