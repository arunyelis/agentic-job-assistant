# Product research journal

Research entries preserve the original observation and separate it from later interpretation.

## 2026-08-31: Founder job-search experience

### Observation

The founder applied to roughly 7,000 roles across LinkedIn, company career sites, and applicant tracking systems. LinkedIn retained part of the history. A personal spreadsheet captured about 100 additional applications, but manual upkeep became too time consuming. Large employers such as Amazon, Google, and Meta also use separate application experiences.

Resume customization, submitted file tracking, and follow-up tracking were similarly fragmented. Recruiter and stage-change emails arrived in Gmail, separate from the application record.

### Product interpretation

The core pain is fragmentation and administrative effort, not the absence of another job board or resume editor. A useful product should capture a small, user-approved application event close to the moment it happens and then connect later evidence and communication to it.

### Constraints raised

- Users should not need to reconstruct thousands of records manually.
- Browser capture needs screenshot, text, and voice fallbacks for difficult sites.
- Email signals could reduce manual status updates, but access must be narrow and explicit.
- Career data needs strong encryption, authorization, masking, and deletion controls.
- The product should be useful before it is monetized. Early charges should be limited to transparent AI or hosting costs where practical.
- Frontend, backend, extension, operations, and infrastructure should progress through separate, reviewable stages.

## 2026-08-31: Product direction decisions

- Use a cloud account as the primary source of truth.
- Serve high-volume technology job seekers first.
- Prove application capture and organization before resume intelligence or email integration.
- Detect likely application events and ask for one-tap confirmation before storing them.
- Keep screenshots disabled by default.

## 2026-09-01: Workspace and automation feedback

### Observation

A capture list alone does not explain the state of a job search. Users need a pipeline they can move through, a dense table for scanning, and a detailed history for each application. The assistant also loses value when it is isolated on one page or requires the user to translate a request into several dashboard actions.

### Product interpretation

Applications are one record shown through several synchronized perspectives. Pipeline, table, detail timeline, Today, and assistant results must share the same data and URL-addressable filters. The assistant should remain present on every screen, preserve conversation history, accept text or browser-supported voice dictation, and turn safe requests into visible workspace navigation. Consequential data changes still require confirmation.

### Engineering interpretation

- Keep the backend as an extraction-ready modular monolith.
- Provide one authenticated asynchronous automation API for the web app, extension, and future clients.
- Support explicit sequential, parallel, and dependency-graph task execution.
- Allow bounded model planning and reusable custom agents with tool allowlists.
- Represent tool inputs with typed schemas and classify side effects.
- Store runs, tasks, events, conversations, and context resets as durable product records.
- Keep provider credentials on the server and provider retention disabled for normal model requests.

### Design direction

The visual system should feel more continuous than a collection of cards. Use tonal regions, layered overlays, generous spacing, and contextual boundaries that appear where they help comprehension. Keep strong contrast, visible focus, and familiar controls. The goal is a calm, distinctive work surface, not decorative glass.
