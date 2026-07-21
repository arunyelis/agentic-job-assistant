# ADR 0004: Use durable asynchronous task graphs

Date: 2026-08-31

Status: accepted

## Decision

All longer automation enters through a durable run record. A run contains typed tasks, dependency keys, status, result, and structured events. Ready tasks may execute concurrently. Dependent tasks execute only after their prerequisites complete.

The local adapter uses an in-process asynchronous queue. The contract allows a distributed queue and independent workers to replace it later.

## Reasons

- HTTP requests return quickly instead of waiting for model or tool work.
- Retries, approval pauses, cancellation, debugging, and evaluation have a durable home.
- Sequential and parallel work use the same model.
- A service can be extracted without changing clients.

## Consequences

- Every tool needs a typed input contract and declared side-effect level.
- External or destructive actions require approval before execution.
- Worker concurrency and retry policy must be measured before horizontal scaling.
