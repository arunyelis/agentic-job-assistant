# Career Workspace vision

## Product statement

Career Workspace is a user-controlled place to capture a job search, organize career evidence, and decide what to do next. It should help people make stronger applications while removing the work of tracking them.

It is not a bulk application bot. The system assists, records, and prepares. The user reviews consequential actions.

## Initial audience

The first serious users are high-volume technology job seekers who apply across many company sites and applicant tracking systems. They commonly maintain several resume versions, lose track of submitted material, and receive status updates in a separate email inbox.

Students and experienced professionals remain important. Their onboarding and guidance can differ after the capture workflow is reliable.

## Problems to solve

1. Application activity is spread across job boards, company sites, email, documents, and personal spreadsheets.
2. Manual tracking takes enough effort that people stop doing it.
3. A user often cannot reproduce the resume and answers submitted to a specific employer.
4. Resume customization is disconnected from the evidence that supports each claim.
5. Existing tools frequently optimize application volume instead of useful decisions and truthful positioning.
6. Career data is sensitive, but users rarely receive a clear record of where it is stored or how it is deleted.

## Product principles

- **Capture before administration.** Observe a user-approved event and prepare a record before asking the user to type CRM data.
- **Confirm before storing.** Detected applications remain proposals until the user confirms them.
- **Evidence before generation.** Generated claims must trace to user-provided evidence.
- **Actions before dashboards.** The first screen explains what changed and what deserves attention today.
- **Progressive permission.** Ask for a browser, email, or file permission only when the related feature is used.
- **Visible data flow.** Show what was collected, why it was collected, and where it is stored.
- **Human control.** Do not automatically submit applications or send messages in the initial product.
- **Plain engineering.** Prefer understandable modules and established libraries over unnecessary abstractions.

## Non-goals for the first release

- Automatic application submission
- Background collection of all browser activity
- LinkedIn application-history scraping
- Gmail OAuth access
- Community benchmarking
- Recruiter or employer workflows
- A marketplace for skills or templates
- Multiple backend services

## Product model

Career Workspace will grow around five connected areas:

1. **Career evidence:** experience, projects, skills, achievements, preferences, and source documents.
2. **Application capture:** confirmed records from the browser extension or a manual entry.
3. **Application intelligence:** role fit, evidence gaps, resume positioning, and follow-up guidance.
4. **Career timeline:** applications, communication, interviews, outcomes, and submitted snapshots.
5. **Privacy control:** connected sources, consent history, export, retention, and deletion receipts.

## Success signals

The first release succeeds when a user can capture applications during a normal search without maintaining a separate spreadsheet, find the submitted context later, and trust that the product did not record unrelated browsing.

Initial measures:

- percentage of detected applications that users confirm
- time from detection to confirmation
- correction rate for extracted company and role
- duplicate capture rate
- weekly return rate to the Today view
- percentage of users who can identify the resume used for an application
- deletion and export completion rate
