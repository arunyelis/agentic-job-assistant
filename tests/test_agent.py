from backend.agent import JobAssistant
from backend.browser import READ_ONLY_BROWSER_TOOLS, PlaywrightBrowser
from backend.config import Config
from backend.skills import Skill


def test_coordinator_has_skill_tool_specialist_tool_and_save_tool(tmp_path):
    config = Config(
        root_dir=tmp_path,
        skills_dir=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        log_file=tmp_path / "logs" / "agent.jsonl",
        frontend_dir=tmp_path / "dist",
        api_key="test-key",
        model="gpt-5.6-luna",
        max_output_tokens=1200,
        port=3000,
        browser_enabled=False,
    )
    skills = {
        "job-match": Skill("job-match", "Match jobs", "Be truthful.", "match.md"),
    }
    assistant = JobAssistant(config, skills, PlaywrightBrowser(tmp_path, False))

    coordinator = assistant._create_coordinator(lambda _: None, [])

    assert [tool.name for tool in coordinator.tools] == [
        "load_skill",
        "spawn_specialist_agent",
        "save_application_note",
    ]
    assert coordinator.model_settings.max_tokens == 1200


def test_browser_tools_are_read_only():
    assert READ_ONLY_BROWSER_TOOLS == [
        "browser_navigate",
        "browser_snapshot",
        "browser_wait_for",
        "browser_tabs",
        "browser_close",
    ]
