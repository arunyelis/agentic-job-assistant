# 0001: Cloud account is the source of truth

- Date: 2026-08-31
- Status: accepted

## Context

Background email processing, multiple devices, durable timelines, and future community features are difficult when application data exists on only one device.

## Decision

Use a cloud-account model as the product source of truth. Local development will exercise the same ownership boundaries with a local authentication adapter and database.

## Consequences

- The product carries a meaningful security and deletion responsibility.
- Every stored record needs an authenticated owner.
- Users must be shown when content is sent to an external model or service.
- A fully local mode could be explored later, but it is not the primary architecture.
