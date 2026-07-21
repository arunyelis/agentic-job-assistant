from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Config


class FakeBrowser:
    async def close(self):
        pass


class FakeAssistant:
    def __init__(self):
        self.browser = FakeBrowser()
        self.resumes = {}

    def set_resume(self, session_id, file_name, text):
        self.resumes[session_id] = (file_name, text)

    def reset(self, session_id):
        self.resumes.pop(session_id, None)

    async def chat(self, session_id, message):
        return {"answer": f"Reply to {message}", "events": []}

    async def stream(self, session_id, message):
        yield {"event": "activity", "data": {"type": "skill", "label": "Loaded test"}}
        yield {"event": "token", "data": {"text": "Streamed reply"}}
        yield {"event": "complete", "data": {"answer": "Streamed reply"}}


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
        artifacts_dir=tmp_path / "artifacts",
        log_file=tmp_path / "logs" / "agent.jsonl",
        frontend_dir=tmp_path / "dist",
        api_key="test-key",
        model="gpt-5.6-luna",
        max_output_tokens=1200,
        port=3000,
        browser_enabled=True,
    )


def test_health_and_resume_upload(tmp_path):
    assistant = FakeAssistant()
    app = create_app(make_config(tmp_path), assistant, MemoryLogger())

    with TestClient(app) as client:
        health = client.get("/api/health")
        upload = client.post(
            "/api/resume",
            data={"session_id": "session-123"},
            files={
                "resume": (
                    "resume.txt",
                    b"Alex Morgan, AI Engineer. Built Python services and tested LLM applications.",
                    "text/plain",
                )
            },
        )

    assert health.status_code == 200
    assert health.json()["skills"] == ["test"]
    assert upload.status_code == 200
    assert assistant.resumes["session-123"][0] == "resume.txt"


def test_stream_route_forwards_events_and_logs_metadata(tmp_path):
    logger = MemoryLogger()
    app = create_app(make_config(tmp_path), FakeAssistant(), logger)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={"session_id": "session-123", "message": "Help with this role"},
        )

    assert response.status_code == 200
    assert "event: activity" in response.text
    assert "event: token" in response.text
    assert "event: done" in response.text
    completed = next(item for item in logger.records if item["event"] == "chat_completed")
    assert completed["streamed"] is True
    assert "message" not in completed
    assert "answer" not in completed
