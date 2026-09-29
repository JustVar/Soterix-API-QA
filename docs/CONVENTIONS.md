# Engineering conventions

The full house conventions live with the UI repo
(Soterix-WebApp-QA, docs/CONVENTIONS.md). This file holds the ones this
repo enforces directly.

## Code notes

- **No ticket keys in code.** Jira numbers change and go stale. Code
  outlives them. Comments, docstrings and messages describe the
  BEHAVIOR. Ticket references belong in docs, which map behavior to the
  current ticket.
- **Comments follow the code's writing principles**: concise, direct,
  nothing twice. Keep the why and the measured fact. Drop migration
  history and anything the code already says.
- **Nothing names a server, a site or a camera outside `config/env/`.**
  Tests resolve ids by name at run time. A number in a test is a bug.

## Testing

- Browser-free by design: no Playwright dependency, ever.
- GET-only for the endpoint sweep. Mutating endpoints get deliberate
  tests with controlled data, and every name a test creates starts with
  `AutoTest ` and is removed at teardown.
- A skip is not a pass. The only skip sources are: a missing credential
  (`QA_USER`, `VSAAS_INTEGRATION_KEY`), the `allow_write` and
  `allow_delete` flags, a site or camera name that does not resolve, and
  a row in `KNOWN_LIMITATIONS` (`tests/internal_api/data/endpoints.py`).
  Every `KNOWN_LIMITATIONS` row was measured on the previous QA server.
  Re-measure it before you keep it on a new one.
- Removing tests lowers the collect floor. Run
  `python tools/collect_floor.py --update` in the same commit and say why
  in the message.

## Git

- Work on a branch. Open a pull request. Never force-push `main`.
- The collect gate (`.github/workflows/collect-gate.yml`) must be green
  before a merge. It runs the same commands `README.md` lists.
- Commit messages say what the change does. Nothing else goes in them.
