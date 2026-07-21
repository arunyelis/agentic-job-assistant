from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Config
from backend.models import User


class FakeBrowser:
    async def close(self):
        pass


class FakeAssistant:
    def __init__(self):
        self.browser = FakeBrowser()

    def set_resume(self, _session_id, _file_name, _text):
        pass

    def reset(self, _session_id):
        pass


class MemoryLogger:
    def __init__(self):
        self.records = []

    async def write(self, event, **fields):
        self.records.append({"event": event, **fields})


def make_config(tmp_path: Path) -> Config:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "test.md").write_text(
        "---\nname: test\ndescription: Test skill\n---\nTest instructions.",
        encoding="utf-8",
    )
    return Config(
        root_dir=tmp_path,
        skills_dir=skills_dir,
        artifacts_dir=tmp_path / "notes",
        log_file=tmp_path / "logs" / "agent.jsonl",
        frontend_dir=tmp_path / "dist",
        api_key="test-key",
        model="gpt-5.6-luna",
        max_output_tokens=1200,
        port=3000,
        browser_enabled=False,
        database_url=f"sqlite:///{tmp_path / 'workspace.db'}",
        storage_dir=tmp_path / "encrypted-artifacts",
        auth_secret="test-auth-secret",
        data_encryption_key="test-encryption-key",
        rate_limit_per_minute=1_000,
    )


def capture_payload(key: str = "capture-12345") -> dict:
    return {
        "idempotency_key": key,
        "captured_at": datetime.now(UTC).isoformat(),
        "source_url": "https://boards.example.com/jobs/123",
        "source_type": "extension",
        "company": "Northstar Labs",
        "role": "AI Platform Engineer",
        "status": "applied",
        "extraction_confidence": 0.94,
    }


def start_local_session(client: TestClient) -> None:
    response = client.post("/api/v1/auth/local-session")
    assert response.status_code == 200


def test_capture_requires_authentication(tmp_path):
    app = create_app(make_config(tmp_path), FakeAssistant(), MemoryLogger())
    with TestClient(app) as client:
        response = client.post("/api/v1/applications/capture", json=capture_payload())

    assert response.status_code == 401


def test_extension_bearer_session_can_capture(tmp_path):
    app = create_app(make_config(tmp_path), FakeAssistant(), MemoryLogger())
    with TestClient(app) as client:
        session = client.post("/api/v1/auth/local-session")
        token = session.json()["token"]
        client.cookies.clear()
        response = client.post(
            "/api/v1/applications/capture",
            json=capture_payload("extension-capture-123"),
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    assert response.json()["source_type"] == "extension"


def test_confirmed_capture_is_persistent_and_idempotent(tmp_path):
    app = create_app(make_config(tmp_path), FakeAssistant(), MemoryLogger())
    with TestClient(app) as client:
        start_local_session(client)
        first = client.post("/api/v1/applications/capture", json=capture_payload())
        second = client.post("/api/v1/applications/capture", json=capture_payload())
        timeline = client.get("/api/v1/applications")
        today = client.get("/api/v1/today")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(timeline.json()) == 1
    assert timeline.json()[0]["company"] == "Northstar Labs"
    assert today.json()["total"] == 1
    assert today.json()["counts"] == {"applied": 1}


def test_application_ownership_is_enforced(tmp_path):
    config = make_config(tmp_path)
    app = create_app(config, FakeAssistant(), MemoryLogger())
    with TestClient(app) as client:
        start_local_session(client)
        created = client.post("/api/v1/applications/capture", json=capture_payload())

        with app.state.database.session_factory() as db:
            other_user = User(email="other@example.test", display_name="Other user")
            db.add(other_user)
            db.commit()
            other_token = app.state.auth.issue(other_user.id)

        client.cookies.set("career_workspace_session", other_token)
        response = client.get(f"/api/v1/applications/{created.json()['id']}")

    assert response.status_code == 404


def test_encrypted_artifact_export_and_deletion_receipt(tmp_path):
    config = make_config(tmp_path)
    app = create_app(config, FakeAssistant(), MemoryLogger())
    secret_content = b"private screenshot bytes"

    with TestClient(app) as client:
        start_local_session(client)
        artifact = client.post(
            "/api/v1/artifacts",
            data={"kind": "screenshot"},
            files={"file": ("application.png", secret_content, "image/png")},
        )
        payload = capture_payload()
        payload["screenshot_artifact_id"] = artifact.json()["id"]
        client.post("/api/v1/applications/capture", json=payload)
        exported = client.get("/api/v1/account/export")
        deleted = client.post("/api/v1/account/deletion")
        receipt = client.get(f"/api/v1/account/deletion/{deleted.json()['id']}")
        timeline_after_deletion = client.get("/api/v1/applications")

    encrypted_files = list((config.storage_dir or tmp_path).rglob("*.bin"))
    assert artifact.status_code == 201
    assert exported.status_code == 200
    assert exported.json()["artifacts"][0]["fileName"] == "application.png"
    assert secret_content not in exported.content
    assert deleted.status_code == 202
    assert receipt.json()["status"] == "completed"
    assert receipt.json()["artifacts_removed"] == 1
    assert encrypted_files == []
    assert timeline_after_deletion.status_code == 401
