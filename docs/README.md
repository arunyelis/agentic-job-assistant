# Engineering documentation

This directory holds the engineering record for Career Workspace: how the system is
built, why the expensive decisions were made, and the visual language the interface
implements.

## Contents

- [System architecture](architecture/system.md) — backend modules, data flow, trust boundaries
- [Privacy and security baseline](architecture/privacy-security.md) — data classes and the intended guarantees
- [Design system](design-system.md) — tokens, surfaces, and interface primitives
- [Decision records](decisions/README.md) — dated records for decisions that would be expensive to reverse
- [Archive](archive/) — superseded documents kept for reference

## Product documentation

Product strategy, the UX specification, the development backlog, and the research
journal are maintained in a separate private repository and are not part of this
codebase. Contributors working on a task will be given the relevant section.

## Working agreement

- Update the architecture documents when data flow, trust boundaries, or infrastructure change.
- Update `design-system.md` before introducing a new visual token or primitive.
- Add a dated record under `decisions/` for a decision that would be expensive to reverse.
- Documents explain decisions in plain language. They are not marketing material and
  must not claim a feature or safeguard exists before it is implemented.
