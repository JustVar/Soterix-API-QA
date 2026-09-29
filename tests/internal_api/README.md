# Internal API tests (/v-apiserver)

## Overview

This folder holds the internal-API suite: smoke-depth tests (marked
`@pytest.mark.smoke`) of the endpoints the web app uses, a GET sweep over
every read-only endpoint in `data/endpoints.py`, 2 end-to-end flows (clip
export, media), and offline unit tests of the HTTP exchange log, the
session cache and the site and camera choice. `pytest --collect-only
tests/internal_api` prints the count. Suite fixtures live in `conftest.py`
in this folder.

`test_api_integration_key_apis.py` walks the API Integration key lifecycle
(create, disable, enable, delete) with a throwaway key and verifies each
state change against the third-party `/v-integration-api` surface. It
writes, so the env `allow_write` and `allow_delete` flags gate it.

`test_location_apis.py` and `test_bookmark_apis.py` are contract tests: the
UI suite (Soterix-WebApp-QA) seeds its test data through those endpoints,
so a change in their answers breaks UI setup there. They write throwaway
`AutoTest ` data and remove it at teardown. See `docs/API_SURFACES.md`,
"Contracts the UI suite depends on".

Directories in this repo name the API surface. Markers name the test depth.
Deeper internal-API tests (regression, security) belong here too, under
their own markers, not in a new top-level directory.

## How to run

From the repository root, with `QA_USER` and `QA_PASSWORD` in `.env`:

```powershell
venv\Scripts\python.exe -m pytest tests\internal_api
```

The server is `api_base_url` in `config/env/qa.py`. There is no host
variable in `.env`.

## Fixtures

- `login_data` - `QA_USER` and `QA_PASSWORD` from `.env`
- `api_base_url` - the API host from the active env file
- `api_auth_token` / `api_auth_helper` - the session cookie, signed in
  once per run and cached in `.session_cache` for the same server and
  account
- `user_api`, `dashboard_api`, `camera_api`, `search_api`, `location_api`,
  `bookmark_api` - API client wrappers
- `discovered_site`, `discovered_site_id`, `discovered_enterprise_id`,
  `test_site_id`, `test_channel_ids` - discovery fixtures that pick valid
  site and channel ids for read-only tests. `TEST_SITE_ID` in `.env` pins
  the site.
- `data_site`, `data_site_id`, `data_channel_id` - the site and camera that
  `test_site_name` and `test_camera_name` in `config/env/` name, resolved
  by name. Tests that write data use these, never `TEST_SITE_ID`. A blank
  name means the first site by name with a camera, and the first camera
  by name on it (`api_clients/data_choice.py`, pinned offline by
  `test_data_choice.py`). The run prints the site and the camera it used.
- `data_write_gate` - skips a writing test unless the env allows both
  writes and deletes (`allow_write`, `allow_delete` in `config/env/`)
- `authed_session`, `discovery_context`, `recorded_clip_window` - the raw
  session and the real ids the sweep and the e2e flows use

## Endpoints covered (examples)

- `/REST/central/user/login` and `/REST/central/user/session` (login contract, session)
- `/REST/central/role/{enterpriseId}` (roles)
- `/REST/dashboard/site/{siteId}/status` (site status)
- `/REST/site/{siteId}/location/tree` (camera groups = locations)
- `/REST/site/config/{siteId}/location` and `/REST/site/{siteId}/deletelocation/{id}` (camera group create and delete)
- `/REST/clipbookmark` (bookmark create, list, soft delete)
- `/REST/site/{siteId}/channel/{channelId}/snap` (camera snapshot)
- `/REST/dashboard/sharedwidgets/{customerId}/data` (widgets)
- `/REST/site/search` (search)

The full list with request and response shapes is
`docs/INTERNAL_API_INVENTORY.md`.

## The sweep's skip list

`data/endpoints.py` holds `KNOWN_LIMITATIONS`, a dict of endpoint name to
reason. The sweep skips those endpoints with that reason. Every reason
names the server and the month it was measured on (`_MEASURED` in that
file). On a new server, delete a row, run the sweep, and keep the row
only if the endpoint still fails for the stated reason. A skip is not a
pass.
