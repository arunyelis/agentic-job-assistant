import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from agents import set_tracing_disabled
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from backend.agent import JobAssistant, MissingApiKeyError, MissingResumeError
from backend.auth import AuthService
from backend.browser import PlaywrightBrowser
from backend.config import Config, load_config
from backend.database import Database
from backend.integrations.llm import LLMProvider, OpenAIResponsesProvider
from backend.logger import JsonLogger
from backend.modules.automation import AutomationService, create_automation_router
from backend.resume import MAX_RESUME_BYTES, ResumeError, extract_resume
from backend.security import SecurityMiddleware
from backend.skills import load_skills
from backend.storage import EncryptedFileStore
from backend.workspace import create_workspace_router


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=100)
    message: str = Field(min_length=1, max_length=8_000)


class ResetRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=100)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(
    config: Config | None = None,
    assistant: JobAssistant | None = None,
    logger: JsonLogger | None = None,
    database: Database | None = None,
    storage: EncryptedFileStore | None = None,
    llm_provider: LLMProvider | None = None,
    automation_service: AutomationService | None = None,
) -> FastAPI:
    set_tracing_disabled(True)
    config = config or load_config()
    skills = load_skills(config.skills_dir)
    browser = PlaywrightBrowser(config.root_dir, config.browser_enabled)
    assistant = assistant or JobAssistant(config, skills, browser)
    logger = logger or JsonLogger(config.log_file)
    database = database or Database(config.database_url, config.root_dir)
    storage = storage or EncryptedFileStore(
        config.storage_dir or config.root_dir / "data" / "artifacts",
        config.data_encryption_key,
    )
    auth = AuthService(config.auth_secret, config.auth_mode)
    llm_provider = llm_provider or OpenAIResponsesProvider(
        config.api_key,
        config.openai_base_url,
    )
    automation_service = automation_service or AutomationService(
        config,
        database,
        llm_provider,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.create_tables()
        await automation_service.start()
        await logger.write(
            "server_started",
            model=config.model,
            browser_enabled=config.browser_enabled,
            skill_count=len(skills),
        )
        yield
        await automation_service.stop()
        await assistant.browser.close()
        database.close()

    app = FastAPI(title="Agentic Job Assistant", version="1.0.0", lifespan=lifespan)
    app.state.config = config
    app.state.assistant = assistant
    app.state.logger = logger
    app.state.database = database
    app.state.auth = auth
    app.state.storage = storage
    app.state.automation = automation_service
    app.add_middleware(
        SecurityMiddleware,
        requests_per_minute=config.rate_limit_per_minute,
    )
    if config.environment != "production" or config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_origin_regex=(
                r"chrome-extension://[a-p]{32}" if config.environment != "production" else None
            ),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.include_router(create_workspace_router(config, database, auth, storage))
    app.include_router(create_automation_router(database, auth, automation_service))

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "model": config.model,
            "apiKeyConfigured": bool(config.api_key),
            "browserEnabled": config.browser_enabled,
            "skills": list(skills),
        }

    @app.post("/api/resume")
    async def upload_resume(
        session_id: str = Form(min_length=8, max_length=100),
        resume: UploadFile = File(...),
    ) -> dict:
        started = time.perf_counter()
        file_name = Path(resume.filename or "resume").name
        data = await resume.read(MAX_RESUME_BYTES + 1)
        try:
            text = extract_resume(file_name, data)
        except ResumeError as error:
            await logger.write(
                "resume_rejected",
                session=session_id[:12],
                file_extension=Path(file_name).suffix.lower(),
                byte_count=len(data),
            )
            raise HTTPException(status_code=400, detail=str(error)) from error

        assistant.set_resume(session_id, file_name, text)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        await logger.write(
            "resume_uploaded",
            session=session_id[:12],
            file_extension=Path(file_name).suffix.lower(),
            byte_count=len(data),
            character_count=len(text),
            elapsed_ms=elapsed_ms,
        )
        return {"fileName": file_name, "characterCount": len(text), "elapsedMs": elapsed_ms}

    @app.post("/api/chat")
    async def chat(payload: ChatRequest) -> JSONResponse:
        started = time.perf_counter()
        try:
            result = await assistant.chat(payload.session_id, payload.message.strip())
        except (MissingApiKeyError, MissingResumeError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            await logger.write(
                "chat_failed",
                session=payload.session_id[:12],
                message_chars=len(payload.message),
                error_type=type(error).__name__,
            )
            raise HTTPException(
                status_code=500, detail="The agent could not complete the request."
            ) from error

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        await logger.write(
            "chat_completed",
            session=payload.session_id[:12],
            message_chars=len(payload.message),
            response_chars=len(result["answer"]),
            activity_count=len(result["events"]),
            elapsed_ms=elapsed_ms,
            streamed=False,
        )
        return JSONResponse({**result, "elapsedMs": elapsed_ms})

    @app.post("/api/chat/stream")
    async def stream_chat(payload: ChatRequest, request: Request) -> StreamingResponse:
        started = time.perf_counter()

        async def event_stream():
            answer = ""
            activity_count = 0
            try:
                async for item in assistant.stream(payload.session_id, payload.message.strip()):
                    if await request.is_disconnected():
                        await logger.write(
                            "chat_disconnected",
                            session=payload.session_id[:12],
                            message_chars=len(payload.message),
                        )
                        return

                    if item["event"] == "activity":
                        activity_count += 1
                    if item["event"] == "complete":
                        answer = item["data"]["answer"]
                        elapsed_ms = round((time.perf_counter() - started) * 1000)
                        await logger.write(
                            "chat_completed",
                            session=payload.session_id[:12],
                            message_chars=len(payload.message),
                            response_chars=len(answer),
                            activity_count=activity_count,
                            elapsed_ms=elapsed_ms,
                            streamed=True,
                        )
                        yield sse("done", {"answer": answer, "elapsedMs": elapsed_ms})
                    else:
                        yield sse(item["event"], item["data"])
            except (MissingApiKeyError, MissingResumeError) as error:
                yield sse("error", {"message": str(error)})
            except Exception as error:
                await logger.write(
                    "chat_failed",
                    session=payload.session_id[:12],
                    message_chars=len(payload.message),
                    error_type=type(error).__name__,
                    streamed=True,
                )
                yield sse("error", {"message": "The agent could not complete the request."})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/api/reset")
    async def reset(payload: ResetRequest) -> dict:
        assistant.reset(payload.session_id)
        await logger.write("session_reset", session=payload.session_id[:12])
        return {"ok": True}

    assets_dir = config.frontend_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        index_file = config.frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(
            {"message": "Frontend is not built. Run npm install and npm run build in frontend."},
            status_code=503,
        )

    return app


app = create_app()
