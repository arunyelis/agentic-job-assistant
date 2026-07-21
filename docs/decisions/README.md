# Architecture decision records

Create a numbered record when a decision changes a trust boundary, core data model, deployment shape, or product interaction that would be expensive to reverse.

Each record contains the date, status, context, decision, consequences, and follow-up conditions. Do not delete superseded records. Add a new record that links to the earlier one.

- [0001: Use a cloud account as the source of truth](0001-cloud-account.md)
- [0002: Confirm captures before storage](0002-confirm-before-capture.md)
- [0003: Use a modular Python backend](0003-modular-python-backend.md)
- [0004: Use durable asynchronous task graphs](0004-durable-asynchronous-task-graphs.md)
- [0005: Keep one server-side language model gateway](0005-server-side-language-model-gateway.md)
