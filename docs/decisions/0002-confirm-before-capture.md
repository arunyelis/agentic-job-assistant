# 0002: Confirm before application capture

- Date: 2026-08-31
- Status: accepted

## Context

Automatic background recording would reduce friction but could capture unrelated browsing, create inaccurate records, and weaken user trust.

## Decision

The extension may detect and prepare a proposed application record. It stores the record in the account only after the user reviews and confirms it. Screenshots remain optional and disabled by default.

## Consequences

- The extension needs an editable confirmation interface.
- Pending proposals can remain device-local for a short period.
- Confirmation rate and correction rate become important product measures.
- Full automatic capture requires a new product and privacy decision.
