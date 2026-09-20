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
    database_url: str = ""
    storage_dir: Path | None = None
    auth_mode: str = "local"
    auth_secret: str = "local-development-secret-change-me"
    environment: str = "development"
    data_encryption_key: str = "local-development-encryption-key"
    max_upload_bytes: int = 10 * 1024 * 1024
    backup_retention_days: int = 30
    rate_limit_per_minute: int = 120
    cors_origins: tuple[str, ...] = ()
    openai_base_url: str | None = None
    typesafe_api_key: str = ""
    typesafe_model: str = "jev-latest"
    typesafe_base_url: str | None = None
    typesafe_concurrency: int = 16
    shortlist_percentile: int = 10


def load_config() -> Config:
    load_dotenv(ROOT_DIR / ".env")
    environment = os.getenv("APP_ENV", "development").strip().lower()
    auth_secret = os.getenv("AUTH_SECRET", "local-development-secret-change-me").strip()
    encryption_key = os.getenv("DATA_ENCRYPTION_KEY", "local-development-encryption-key").strip()
    cors_origins = tuple(
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
    )
    if environment == "production" and (
        auth_secret == "local-development-secret-change-me"
        or encryption_key == "local-development-encryption-key"
    ):
        raise RuntimeError("Production requires AUTH_SECRET and DATA_ENCRYPTION_KEY.")

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
        database_url=os.getenv("DATABASE_URL", "").strip(),
        storage_dir=ROOT_DIR / "data" / "artifacts",
        auth_mode=os.getenv("AUTH_MODE", "local").strip().lower(),
        auth_secret=auth_secret,
        environment=environment,
        data_encryption_key=encryption_key,
        max_upload_bytes=max(
            1024,
            int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
        ),
        backup_retention_days=max(
            1,
            int(os.getenv("BACKUP_RETENTION_DAYS", "30")),
        ),
        rate_limit_per_minute=max(
            10,
            int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
        ),
        cors_origins=cors_origins,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        typesafe_api_key=os.getenv("TYPESAFE_API_KEY", "").strip(),
        typesafe_model=os.getenv("TYPESAFE_MODEL", "jev-latest").strip(),
        typesafe_base_url=os.getenv("TYPESAFE_BASE_URL", "").strip() or None,
        typesafe_concurrency=max(1, int(os.getenv("TYPESAFE_CONCURRENCY", "16"))),
        shortlist_percentile=min(100, max(1, int(os.getenv("SHORTLIST_PERCENTILE", "10")))),
    )
