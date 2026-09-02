# Engineering conventions

The full house conventions live with the UI repo
(Soterix-WebApp-QA, docs/CONVENTIONS.md); this file holds the ones this
repo enforces directly.

## Code notes

- **No ticket keys in code.** Jira numbers change and go stale; code
  outlives them. Comments, docstrings, and messages describe the
  BEHAVIOR; ticket references belong in docs (a README or register),
  which map behavior to the current ticket.
- **Comments follow the code's writing principles**: concise, direct,
  nothing twice. Keep the why and the measured fact with its probe
  date; drop migration/port history and anything the code already says.

## Testing

- Browser-free by design: no Playwright dependency, ever.
- GET-only for the endpoint sweep; mutating endpoints get deliberate
  tests with controlled data.
