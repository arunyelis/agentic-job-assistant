# Product roadmap

The roadmap is ordered by product learning. A later release should not begin because its technology is interesting. It should begin when the earlier release is reliable enough to support it.

## Release 1: Capture and organize

- Cloud-account shaped application records
- Confirmed browser capture
- Manual capture fallback
- Today view and searchable timeline
- Synchronized pipeline and table views
- Application detail timeline
- User-configurable table columns and saved filters
- Persistent contextual assistant available from every screen
- Capture review inbox
- Optional screenshot artifacts
- Data export and deletion receipt
- Privacy-safe operational logging

### Exit criteria

- Common applicant tracking pages can be captured or entered manually.
- No record is stored before confirmation.
- Duplicate submissions are handled idempotently.
- Application data survives a restart.
- A user cannot access another user’s records.
- Export and deletion complete successfully.

## Release 2: Career evidence and resumes

- Canonical career evidence profile with source references
- Role-family positioning profiles
- Resume templates and document generation
- Job-specific change layer with highlighted differences
- Exact submitted resume snapshot per application
- Unsupported-claim warnings

## Release 3: Communication and interviews

- User-controlled email forwarding or selected-message ingestion
- Recruiter, assessment, interview, rejection, and offer classification
- Follow-up reminders
- Evidence-backed interview preparation and stories
- Gmail OAuth only after verification and security requirements are met

## Release 4: Assisted completion and community

- Approval-based form filling
- No automatic submission without a separate product and risk decision
- Opt-in, aggregated community insights
- Mentoring, coaching, and job-club workflows

## Open questions

- Which applicant tracking systems account for most early-user applications?
- What accuracy threshold should require manual review?
- How long should raw page excerpts and screenshots be retained?
- Which managed identity provider best fits a public beta?
- Should users bring their own model key or buy a metered usage allowance?
- What evidence should count as verified rather than user-asserted?

## Automation platform foundation

- One asynchronous run endpoint for the web app, extension, and future clients
- Explicit sequential, parallel, and dependency-graph execution modes
- Model-planned workflows when the user does not supply a task plan
- Typed tools with side-effect classification and approval requirements
- Reusable custom agents with tool allowlists
- Persistent conversations, context reset, and structured run history
- Replaceable queue and language model adapters
