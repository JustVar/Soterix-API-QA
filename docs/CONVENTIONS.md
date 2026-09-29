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
  Tests resolve ids by name at run time. A number in a test is a bug. A
  blank `test_site_name` or `test_camera_name` means the run picks the
  first site by name with a camera and the first camera by name on it
  (`api_clients/data_choice.py`), and prints the choice. A name that is
  set is checked, never replaced.

## Testing

- Browser-free by design: no Playwright dependency, ever.
- GET-only for the endpoint sweep. Mutating endpoints get deliberate
  tests with controlled data, and every name a test creates starts with
  `AutoTest ` and is removed at teardown.
- A skip is not a pass. The skip sources are the rows of the table below.
  Nothing else adds one. A refused discovery call (a non-200) fails,
  never skips: a revoked session or a dead site must not look like a
  data gap.
- Every `KNOWN_LIMITATIONS` row (`tests/internal_api/data/endpoints.py`)
  names the server and the month it was measured on (`_MEASURED` in that
  file). Re-measure it before you keep it on a new server.
- Removing tests lowers the collect floor. Run
  `python tools/collect_floor.py --update` in the same commit and say why
  in the message.

### Skip sources

| Skip | Where |
|---|---|
| `VSAAS_INTEGRATION_KEY` empty: the whole integration suite | `tests/integration_api/conftest.py`, `integration_key` |
| `integration_api_base_url` is `None` in `config/env/`: the integration suite and the key lifecycle test | `integration_base_url`, and `key_admin` in `tests/internal_api/test_api_integration_key_apis.py` |
| the key sees no site, or no site with a channel (an empty 200) | `integration_ids` |
| `allow_write` or `allow_delete` False in `config/env/`: every test that writes | `tests/internal_api/conftest.py`, `data_write_gate`, and `key_admin` |
| a `test_site_name` or `test_camera_name` that does not resolve, or no site with a camera while both are blank | `data_site`, `data_channel_id` |
| the account sees no site | `discovered_site` |
| a row in `KNOWN_LIMITATIONS`, or a path placeholder with no value (`{channelid}` on a site without a channel) | `tests/internal_api/test_get_endpoints_sweep.py` |
| no channel, or no recorded clip (an empty 200) on the sweep's channel | `recorded_clip_window` |
| `SSO_TEST_USERNAME` empty | `tests/internal_api/test_auth_apis.py`, `test_sso_login_accepts_valid_credentials` |
| `MEDIA_SHARE_TEST_EMAIL` empty | `tests/internal_api/test_media_e2e.py`, `test_media_share` |

A missing `QA_USER` or `QA_PASSWORD` is an error, not a skip: the
internal suite stops at login.

## Git

- Work on a branch. Open a pull request. Never force-push `main`.
- The collect gate (`.github/workflows/collect-gate.yml`) must be green
  before a merge. It runs the same commands `README.md` lists.
- Commit messages say what the change does. Nothing else goes in them.
