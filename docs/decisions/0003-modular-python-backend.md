# 0003: Keep a modular Python backend

- Date: 2026-08-31
- Status: accepted

## Context

The existing product is a small FastAPI application. The next release needs persistence, ownership, artifacts, privacy workflows, and agent execution, but not independent scaling of each feature.

## Decision

Keep Python and FastAPI as one deployable modular application. Use PostgreSQL through SQLAlchemy and add clear internal modules. Do not introduce Java or backend microservices at this stage.

## Consequences

- Transactions, authorization, and deletion remain easier to follow.
- Background jobs can initially share the same codebase.
- Service extraction remains possible if measured load creates a real need.
