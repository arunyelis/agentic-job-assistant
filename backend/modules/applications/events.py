from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Application, ApplicationEvent, CommunicationEvent


def add_application_event(
    db: Session,
    *,
    user_id: str,
    application_id: str,
    event_type: str,
    title: str,
    details: dict | None = None,
    occurred_at: datetime | None = None,
) -> ApplicationEvent:
    event = ApplicationEvent(
        user_id=user_id,
        application_id=application_id,
        event_type=event_type,
        title=title,
        details=details,
    )
    if occurred_at is not None:
        event.occurred_at = occurred_at
    db.add(event)
    return event


def get_application_timeline(db: Session, *, user_id: str, application_id: str) -> list[dict]:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    if application is None:
        return []
    events = [
        {
            "id": event.id,
            "type": event.event_type,
            "title": event.title,
            "details": event.details,
            "occurred_at": event.occurred_at,
        }
        for event in db.scalars(
            select(ApplicationEvent).where(
                ApplicationEvent.application_id == application_id,
                ApplicationEvent.user_id == user_id,
            )
        )
    ]
    if not any(event["type"] == "application_captured" for event in events):
        events.append(
            {
                "id": f"{application.id}:captured",
                "type": "application_captured",
                "title": "Application captured",
                "details": {
                    "source": application.source_type,
                    "status": application.status,
                },
                "occurred_at": application.captured_at,
            }
        )
    events.extend(
        {
            "id": event.id,
            "type": f"communication_{event.event_type}",
            "title": event.event_type.replace("_", " ").title(),
            "details": {"channel": event.channel},
            "occurred_at": event.occurred_at,
        }
        for event in db.scalars(
            select(CommunicationEvent).where(
                CommunicationEvent.application_id == application_id,
                CommunicationEvent.user_id == user_id,
            )
        )
    )
    return sorted(events, key=lambda event: event["occurred_at"], reverse=True)
