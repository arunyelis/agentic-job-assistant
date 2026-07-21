# Agentic Job Assistant

A small local chatbot that shows practical agent engineering without a large architecture:

- FastAPI backend written entirely in Python;
- React UI written in plain JavaScript;
- OpenAI Agents SDK coordinator with streamed responses;
- Markdown skills loaded only when useful;
- specialist agents created on demand for job research, application writing, and follow-up coaching;
- local tools for user-requested Markdown notes;
- read-only Playwright MCP access to public job pages;
- resume upload for PDF, DOCX, TXT, and Markdown files;
- response timing, activity updates, concise reasoning summaries, and privacy-safe JSONL logs.

The app does not log in, fill forms, upload to job sites, submit applications, or send email. The user reviews the result and takes the final action.

## Quick start

Requirements: Python 3.11+, Node.js 20+, [uv](https://docs.astral.sh/uv/), and an OpenAI API key.

```bash
git clone https://github.com/arunyelis/agentic-job-assistant.git
cd agentic-job-assistant
cp .env.example .env
```

Add the API key to `.env`:

```env
OPENAI_API_KEY=your_key_here
```

Install and build:

```bash
uv sync --dev
npm install --prefix frontend
npm run setup:browser --prefix frontend
npm run build --prefix frontend
```

Start the local app:

```bash
uv run python -m backend
```

Open [http://localhost:3000](http://localhost:3000). Upload a resume before sending the first message.

## Try these prompts

```text
Analyze this job against my resume: https://company.example/jobs/123
```

```text
Write a short cover letter for this role using only evidence from my resume.
```

```text
Draft a follow-up for an application I submitted seven days ago.
```

## How it works

1. The backend extracts resume text in memory and associates it with the local chat session.
2. The coordinator receives the resume, recent messages, and the new request.
3. It can load a relevant Markdown skill, call a local save tool, or create one focused child agent.
4. If the conversation contains a public URL, the backend connects to Playwright MCP. Its allowlist contains only navigation, snapshots, tabs, waits, and close.
5. Tokens, tool activity, optional concise reasoning summaries, and final timing stream to the React UI over server-sent events.

Specialists are not created for greetings, small edits, or simple questions. They have no tools, so they cannot recursively create more agents.

## Project layout

```text
backend/app.py       FastAPI routes, streaming, upload, and timing
backend/agent.py     coordinator, tools, and specialist creation
backend/browser.py   read-only Playwright MCP lifecycle and allowlist
backend/resume.py    in-memory PDF, DOCX, TXT, and Markdown extraction
backend/logger.py    metadata-only local JSONL logging
backend/skills.py    Markdown skill loader
frontend/src/        React UI in JavaScript
skills/              job matching, writing, and follow-up playbooks
tests/               Python and frontend unit tests
artifacts/           notes saved only when the user asks
logs/                ignored local run metadata
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Required for LLM calls |
| `OPENAI_MODEL` | `gpt-5.6-luna` | Coordinator and specialist model |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1200` | Coordinator output cap; specialists are capped at 800 |
| `PORT` | `3000` | Documented local port |
| `ENABLE_PLAYWRIGHT_MCP` | `true` | Enables public job-page reading |

The defaults use low reasoning effort, low verbosity, and a conservative output limit to control spend. If the account cannot access the configured model, change `OPENAI_MODEL` in `.env`.

## Privacy and logs

Resume text is sent to the configured OpenAI model, kept in local process memory for the current chat, and cleared by **New chat** or a server restart. It is not written to local disk. SDK tracing is disabled. `logs/agent.jsonl` stores only operational metadata such as timestamps, character counts, event types, and elapsed time. Chat text and resume text are not logged.

## Development

Run the API with reload:

```bash
uv run uvicorn backend.app:app --host 127.0.0.1 --port 3000 --reload
```

In another terminal, run Vite:

```bash
npm run dev --prefix frontend
```

Vite opens the React app on `http://localhost:5173` and proxies `/api` to port 3000.

## Tests

```bash
uv run pytest
npm test --prefix frontend
npm run build --prefix frontend
```

The tests cover skill parsing, safe artifact names, resume extraction, API uploads and streaming, coordinator tools, the MCP allowlist, and SSE parsing.

Built against the official [OpenAI Agents SDK for Python](https://openai.github.io/openai-agents-python/) and [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp).
