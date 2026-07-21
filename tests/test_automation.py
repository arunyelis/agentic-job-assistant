import asyncio
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Config
from backend.integrations.llm import LLMRequest


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
    async def write(self, _event, **_fields):
        pass


class FakeProvider:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> str:
        self.calls.append(request)
        if request.metadata.get("component") == "workflow_planner":
            return json.dumps(
                {
                    "tasks": [
                        {
                            "key": "pipeline",
                            "name": "Read pipeline",
                            "kind": "tool",
                            "tool_name": "applications.pipeline_summary",
                            "input": {},
                            "depends_on": [],
                        },
                        {
                            "key": "answer",
                            "name": "Explain pipeline",
                            "kind": "agent",
                            "instructions": "Explain the pipeline and suggest one action.",
                            "input": {},
                            "depends_on": ["pipeline"],
                        },
                    ]
                }
            )
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.04)
        self.active -= 1
        return f"Completed {request.metadata.get('task', 'task')}"


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


def wait_for_run(client: TestClient, run_id: str, terminal: set[str] | None = None) -> dict:
    expected = terminal or {"completed", "failed", "waiting_approval", "cancelled"}
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/automation/runs/{run_id}")
        assert response.status_code == 200
        run = response.json()
        if run["status"] in expected:
            return run
        time.sleep(0.02)
    raise AssertionError("Automation run did not finish in time.")


def task(key: str) -> dict:
    return {
        "key": key,
        "name": key.title(),
        "kind": "llm",
        "instructions": f"Complete {key}.",
        "input": {},
        "depends_on": [],
    }


def test_sequential_and_parallel_modes_use_the_same_async_endpoint(tmp_path):
    provider = FakeProvider()
    app = create_app(
        make_config(tmp_path),
        FakeAssistant(),
        MemoryLogger(),
        llm_provider=provider,
    )
    with TestClient(app) as client:
        client.post("/api/v1/auth/local-session")
        sequential = client.post(
            "/api/v1/automation/runs",
            json={"prompt": "Run in order", "mode": "sequential", "tasks": [task("a"), task("b")]},
        )
        sequential_run = wait_for_run(client, sequential.json()["id"])
        stream = client.get(f"/api/v1/automation/runs/{sequential_run['id']}/events")
        assert provider.max_active == 1
        assert sequential_run["status"] == "completed"
        assert sequential_run["tasks"][1]["depends_on"] == ["a"]
        assert "event: run" in stream.text
        assert "run_completed" in stream.text

        provider.max_active = 0
        parallel = client.post(
            "/api/v1/automation/runs",
            json={"prompt": "Run together", "mode": "parallel", "tasks": [task("c"), task("d")]},
        )
        parallel_run = wait_for_run(client, parallel.json()["id"])

    assert parallel_run["status"] == "completed"
    assert provider.max_active == 2
    assert all(item["depends_on"] == [] for item in parallel_run["tasks"])


def test_model_can_plan_tools_and_persist_conversation_history(tmp_path):
    provider = FakeProvider()
    app = create_app(
        make_config(tmp_path),
        FakeAssistant(),
        MemoryLogger(),
        llm_provider=provider,
    )
    with TestClient(app) as client:
        client.post("/api/v1/auth/local-session")
        conversation = client.post(
            "/api/v1/assistant/conversations", json={"title": "Pipeline review"}
        ).json()
        response = client.post(
            "/api/v1/automation/runs",
            json={
                "prompt": "What should I focus on?",
                "mode": "auto",
                "conversation_id": conversation["id"],
                "context": {"page": "/applications"},
            },
        )
        run = wait_for_run(client, response.json()["id"])
        messages = client.get(
            f"/api/v1/assistant/conversations/{conversation['id']}/messages"
        ).json()
        cleared = client.post(f"/api/v1/assistant/conversations/{conversation['id']}/clear")

    assert run["status"] == "completed"
    assert [item["task_key"] for item in run["tasks"]] == ["pipeline", "answer"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert cleared.status_code == 200


def test_custom_agent_tool_allowlist_and_approval_resume(tmp_path):
    provider = FakeProvider()
    app = create_app(
        make_config(tmp_path),
        FakeAssistant(),
        MemoryLogger(),
        llm_provider=provider,
    )
    with TestClient(app) as client:
        client.post("/api/v1/auth/local-session")
        application = client.post(
            "/api/v1/applications/capture",
            json={
                "idempotency_key": "automation-capture",
                "captured_at": "2026-08-31T12:00:00Z",
                "source_url": "https://jobs.example.com/1",
                "source_type": "manual",
                "company": "Northstar Labs",
                "role": "AI Engineer",
                "status": "applied",
                "extraction_confidence": 1,
            },
        ).json()
        agent = client.post(
            "/api/v1/automation/agents",
            json={
                "name": "Pipeline operator",
                "description": "Moves confirmed records",
                "instructions": "Manage application stages using only confirmed user requests.",
                "model": "gpt-5.4-mini",
                "allowed_tools": ["applications.update_status"],
            },
        ).json()
        queued = client.post(
            "/api/v1/automation/runs",
            json={
                "prompt": "Move this application to interview",
                "mode": "graph",
                "agent_id": agent["id"],
                "tasks": [
                    {
                        "key": "move",
                        "name": "Move application",
                        "kind": "tool",
                        "tool_name": "applications.update_status",
                        "input": {"application_id": application["id"], "status": "interview"},
                        "depends_on": [],
                    }
                ],
            },
        )
        waiting = wait_for_run(client, queued.json()["id"], {"waiting_approval"})
        approved = client.post(
            f"/api/v1/automation/runs/{waiting['id']}/approve",
            json={"tools": ["applications.update_status"]},
        )
        completed = wait_for_run(client, approved.json()["id"])
        updated = client.get(f"/api/v1/applications/{application['id']}").json()
        timeline = client.get(f"/api/v1/applications/{application['id']}/timeline").json()
        custom_model_run = client.post(
            "/api/v1/automation/runs",
            json={
                "prompt": "Summarize this change",
                "mode": "graph",
                "agent_id": agent["id"],
                "tasks": [task("custom_model")],
            },
        )
        wait_for_run(client, custom_model_run.json()["id"])

    assert waiting["tasks"][0]["status"] == "waiting_approval"
    assert completed["status"] == "completed"
    assert updated["status"] == "interview"
    assert timeline[0]["type"] == "stage_changed"
    assert provider.calls[-1].model == "gpt-5.4-mini"


def test_automation_runs_are_user_scoped(tmp_path):
    provider = FakeProvider()
    app = create_app(
        make_config(tmp_path),
        FakeAssistant(),
        MemoryLogger(),
        llm_provider=provider,
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/auth/local-session")
        run = client.post(
            "/api/v1/automation/runs",
            json={"prompt": "Summarize", "mode": "parallel", "tasks": [task("summary")]},
        ).json()
        original_token = session.json()["token"]
        with app.state.database.session_factory() as db:
            from backend.models import User

            other = User(email="other-automation@example.test")
            db.add(other)
            db.commit()
            other_token = app.state.auth.issue(other.id)
        client.cookies.set("career_workspace_session", other_token)
        hidden = client.get(f"/api/v1/automation/runs/{run['id']}")
        client.cookies.set("career_workspace_session", original_token)
        visible = wait_for_run(client, run["id"])

    assert hidden.status_code == 404
    assert visible["status"] == "completed"


def test_filter_tool_returns_a_safe_workspace_action(tmp_path):
    provider = FakeProvider()
    app = create_app(
        make_config(tmp_path),
        FakeAssistant(),
        MemoryLogger(),
        llm_provider=provider,
    )
    with TestClient(app) as client:
        client.post("/api/v1/auth/local-session")
        response = client.post(
            "/api/v1/automation/runs",
            json={
                "prompt": "Show interview applications at Northstar",
                "mode": "graph",
                "tasks": [
                    {
                        "key": "filter",
                        "name": "Filter applications",
                        "kind": "tool",
                        "tool_name": "workspace.filter_applications",
                        "input": {"search": "Northstar", "status": "interview"},
                        "depends_on": [],
                    }
                ],
            },
        )
        completed = wait_for_run(client, response.json()["id"])

    assert completed["status"] == "completed"
    assert completed["tasks"][0]["result"]["ui_action"] == {
        "type": "filter_applications",
        "search": "Northstar",
        "status": "interview",
    }
