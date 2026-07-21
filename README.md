# Career Workspace

Career Workspace is a private place to capture job applications, organize the search, and use an agentic assistant against a real resume. The first product slice focuses on confirmed application capture instead of automatic submission.

The repository contains:

- a Python and FastAPI modular backend
- persistent application records through SQLAlchemy and PostgreSQL or SQLite
- encrypted local artifact storage
- a React and TypeScript web workspace
- Tailwind CSS 4 and accessible shadcn-style interface primitives
- a React and TypeScript Chrome extension using Manifest V3
- a durable asynchronous workflow coordinator with typed tools, task graphs, and custom agents
- an OpenAI Agents SDK resume assistant with skills, streaming, and focused specialists
- versioned product, design, architecture, privacy, and decision documentation

The browser extension does not submit applications. It detects or reads the current page, prepares a proposal, and stores it only after the user confirms the company and role. LinkedIn automatic capture is disabled.

## Local setup

Requirements:

- Python 3.11 or newer
- Node.js 20 or newer
- [uv](https://docs.astral.sh/uv/)
- an OpenAI API key for assistant features

Create the local configuration:

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY`, `AUTH_SECRET`, and `DATA_ENCRYPTION_KEY` in `.env`. Use separate long random values for the two secrets.

Install and build:

```bash
uv sync --dev
npm install --prefix frontend
npm install --prefix extension
npm run build --prefix frontend
npm run build --prefix extension
```

Start the product:

```bash
uv run alembic upgrade head
uv run python -m backend
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

SQLite is used when `DATABASE_URL` is empty or points to the local database. The account boundary is a signed development session. Production refuses the default secrets and requires a managed authentication adapter before public use.

## Chrome extension

Build the extension, then load `extension/dist` as an unpacked extension from `chrome://extensions`.

1. Keep Career Workspace running at `http://127.0.0.1:3000`.
2. Open a public application or career page.
3. Open the extension and choose **Enable this site**.
4. Complete the application normally or choose **Capture current page**.
5. Review the company, role, and optional screenshot setting.
6. Choose **Save application**.

The permission is requested for the current origin. The optional permission list does not grant access until the user approves a site.

## Docker with PostgreSQL

After creating `.env`, run:

```bash
docker compose up --build
```

The app is available at [http://127.0.0.1:3000](http://127.0.0.1:3000). PostgreSQL and encrypted artifacts use named Docker volumes.

## Application API

The initial authenticated interface is:

```text
POST   /api/v1/applications/capture
GET    /api/v1/applications
GET    /api/v1/applications/{id}
GET    /api/v1/applications/{id}/timeline
PATCH  /api/v1/applications/{id}
POST   /api/v1/artifacts
GET    /api/v1/account/export
POST   /api/v1/account/deletion
GET    /api/v1/account/deletion/{request_id}
```

Capture writes use a user-scoped idempotency key. Low-confidence records enter the Capture Inbox. Uploaded artifact bytes are encrypted before being written to the local storage adapter.

## Automation API

Every model-backed product workflow can use the same authenticated interface:

```text
GET    /api/v1/automation/tools
POST   /api/v1/automation/runs
GET    /api/v1/automation/runs
GET    /api/v1/automation/runs/{id}
GET    /api/v1/automation/runs/{id}/events
POST   /api/v1/automation/runs/{id}/approve
POST   /api/v1/automation/runs/{id}/cancel
GET    /api/v1/automation/agents
POST   /api/v1/automation/agents
PATCH  /api/v1/automation/agents/{id}
GET    /api/v1/assistant/conversations
POST   /api/v1/assistant/conversations
GET    /api/v1/assistant/conversations/{id}/messages
POST   /api/v1/assistant/conversations/{id}/clear
```

`POST /api/v1/automation/runs` returns `202 Accepted`. A request can use `auto`, `sequential`, `parallel`, or `graph` mode. Auto mode asks the model for a bounded plan. Explicit modes accept typed tasks and dependency keys. Ready independent tasks run concurrently. Workspace changes pause for approval when the registered tool requires it.

The default model is `gpt-5.6-luna` with a 1,200 output-token limit to keep local usage economical. Change these limits in `.env`. OpenAI credentials remain in the backend, normal provider requests use `store=false`, and clients receive only the Career Workspace API. Browser clients from another approved origin must be listed in `CORS_ORIGINS`. Non-browser clients can use the same short-lived bearer token used by the local extension.

## Assistant

The floating workspace assistant is available on every screen and stores its conversation history in the local account database. It supports New Chat, `/new`, `/clear`, browser-supported voice dictation, custom agents, and safe workspace navigation. It can draft external communication, but it does not send it.

Upload a PDF, DOCX, TXT, or Markdown resume before using resume-specific work on the full Assistant page. Resume text stays in process memory for that chat and is not written to operational logs.

The coordinator can:

- load job-match, application-writing, and follow-up skills
- use read-only Playwright MCP for public job pages
- create one focused researcher, writer, or follow-up specialist when it improves the response
- stream response tokens, activity, timing, and concise work summaries

It cannot log in, submit forms, send email, or claim that an external action happened.

## Documentation

- [Product vision](docs/product/vision.md)
- [Founder research journal](docs/product/research-journal.md)
- [Roadmap](docs/product/roadmap.md)
- [Design system](docs/product/design-system.md)
- [System architecture](docs/architecture/system.md)
- [Privacy and security baseline](docs/architecture/privacy-security.md)
- [Decision records](docs/decisions/README.md)

These documents are the source of truth across future development sessions. Meaningful product or architecture changes should update the related document or add a decision record.

## Tests and checks

```bash
uv run ruff check backend tests
uv run pytest
npm test --prefix frontend
npm run build --prefix frontend
npm run typecheck --prefix extension
npm test --prefix extension
npm run build --prefix extension
```

The tests cover API ownership, confirmed and idempotent capture, encrypted artifacts, export, deletion receipts, asynchronous sequential and parallel tasks, graph planning, approval resume, conversation context, custom-agent tool boundaries, workspace actions, agent streaming, resume parsing, extension extraction, confirmation detection, and the LinkedIn automatic-capture boundary.
