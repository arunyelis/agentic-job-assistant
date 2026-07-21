# ADR 0005: Keep one server-side language model gateway

Date: 2026-08-31

Status: accepted

## Decision

Web, extension, voice, and future clients call the authenticated Career Workspace automation API. They do not call OpenAI directly. Backend modules use a provider-neutral language model interface with an OpenAI Responses adapter.

The adapter disables provider-side storage for normal requests. Career Workspace persists only the conversation and run information required by the product under the user's account controls.

## Reasons

- API keys never reach browser clients.
- Cost limits, model selection, audit data, and redaction are enforced consistently.
- The provider can change without rewriting product modules.
- The same endpoint supports manual prompts, explicit workflows, and model-planned work.

## Consequences

- Public deployment needs managed authentication and encrypted user or service credentials.
- The API must not use unrestricted wildcard CORS with credentialed requests.
- Provider retention settings must be reviewed against the privacy policy before use.
