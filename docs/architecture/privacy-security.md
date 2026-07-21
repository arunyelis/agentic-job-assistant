# Privacy and security baseline

This document describes the intended baseline. Public claims must match tested behavior and completed infrastructure.

## Data classes

| Class | Examples | Default handling |
| --- | --- | --- |
| Account | User id, email, preferences | Encrypted transport and database storage |
| Career evidence | Resume text, projects, achievements | Restricted access, encrypted storage |
| Application | Company, role, URL, status, timestamps | User-owned database records |
| Sensitive artifact | Resume file, screenshot, email content | Application-level encryption before storage |
| Credential | OAuth refresh token, provider API key | Separate envelope encryption and never logged |
| Operational metadata | Event type, duration, byte count | Redacted structured logs |

## Required controls

- TLS in hosted environments
- secure, HttpOnly, SameSite session cookies
- short session lifetime and revocation support
- per-record ownership checks
- encryption at rest and in transit
- separate encryption for sensitive artifact bytes and credentials
- upload type and size validation
- idempotency for capture writes
- rate limiting for public endpoints
- security headers and a restrictive content security policy
- dependency, secret, and static checks in continuous integration
- metadata-only application logs
- audit events for access, consent, export, and deletion

## Permission model

The browser extension requests an origin only when the user enables capture for that site. Screenshots are disabled by default. A detected record remains in extension storage until the user confirms or dismisses it.

Gmail and other account integrations are out of scope for the first release. Each future connector requires a separate consent record, narrow scopes, token revocation, and a documented retention policy.

## Export

The user can export structured account, application, consent, and audit information in a readable JSON archive. Raw artifacts are listed and can be included in a later archive format after encrypted export is designed.

## Deletion

Account deletion is an authenticated workflow. It removes user-owned application data, artifacts, consent, credentials, and derived records. A minimal tombstone and deletion receipt may remain without personal content so completion can be demonstrated.

The receipt records:

- request identifier
- request time
- completion time
- categories removed
- artifact count removed
- backup expiry date
- completion status

The product must not promise immediate removal from every backup. The default development policy reports a 30-day backup expiry target until hosted backup behavior is selected and verified.

## Logging

Logs must not contain resume text, chat messages, email bodies, screenshots, access tokens, API keys, or raw page excerpts. Tests should assert that sensitive values are absent from log records.

## Public launch gates

- threat model reviewed
- managed authentication enabled
- production secrets stored in a managed secret service
- encryption keys stored in a managed key service
- backup and restore behavior tested
- deletion behavior tested against every data store
- vulnerability and dependency scans clean
- privacy notice reflects actual providers and retention
- Gmail or similar restricted integrations separately verified before release
