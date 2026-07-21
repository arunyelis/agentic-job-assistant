import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent


def read_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    root_dir: Path
    skills_dir: Path
    artifacts_dir: Path
    log_file: Path
    frontend_dir: Path
    api_key: str
    model: str
    max_output_tokens: int
    port: int
    browser_enabled: bool


def load_config() -> Config:
    load_dotenv(ROOT_DIR / ".env")
    return Config(
        root_dir=ROOT_DIR,
        skills_dir=ROOT_DIR / "skills",
        artifacts_dir=ROOT_DIR / "artifacts",
        log_file=ROOT_DIR / "logs" / "agent.jsonl",
        frontend_dir=ROOT_DIR / "frontend" / "dist",
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip(),
        max_output_tokens=max(200, int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "1200"))),
        port=int(os.getenv("PORT", "3000")),
        browser_enabled=read_bool(os.getenv("ENABLE_PLAYWRIGHT_MCP"), True),
    )
