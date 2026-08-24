# Internal API tests (/v-apiserver)

## Overview
This folder holds the internal-API suite: smoke-depth tests (marked `@pytest.mark.smoke`) that quickly validate core platform functionality across environments. The suite currently collects 39 tests covering auth, user/session, admin, dashboard, camera, camera groups (locations), bookmarks, events, and search endpoints. Suite fixtures live in `conftest.py` in this folder.

`test_location_apis.py` and `test_bookmark_apis.py` are contract tests: the
UI suite (Soterix-WebApp-QA) seeds its test data through those endpoints,
so a change in their answers breaks UI setup there. They write throwaway
`AutoTest ` data and remove it at teardown. See `docs/API_SURFACES.md`,
"Contracts the UI suite depends on".

Directories in this repo name the API surface. Markers name the test depth.
Deeper internal-API tests (regression, security) belong here too, under
their own markers, not in a new top-level directory.

Scope:
- Lightweight smoke checks (status codes, basic response shape)
- Dynamic discovery of site and enterprise IDs via fixtures
- Tests intended to be fast and safe to run against test/QA environments

## Core tests (the original 16, later files follow the same pattern)
1. `test_get_user_session` - GET current user session; validate session response structure via `user_api.validate_session_response()`.
2. `test_get_user_roles` - GET user roles; assert response type (list/dict).
3. `test_get_enterprise_id_dynamic` - Validate dynamic enterprise ID derived from site status (fixture `test_enterprise_id`).
4. `test_get_roles_by_enterprise` - GET roles for dynamically discovered enterprise via `/REST/central/role/{enterpriseId}`; validate code/result and role fields.
5. `test_auto_discover_site_and_enterprise` - Ensure `discovered_site`, `discovered_site_id`, and `discovered_enterprise_id` fixtures return valid values.

6. `test_get_site_status` (platform) - GET `/REST/dashboard/site/{siteId}/status`; validate JSON response and presence of siteId.
7. `test_get_camera_tree` (platform) - GET `/REST/site/{siteId}/location/tree`; validate structure contains locations/devices.
8. `test_get_camera_snap` (platform) - GET `/REST/site/{siteId}/channel/{channelId}/snap`; accept binary image or JSON; validate JPEG/PNG magic bytes for images.
9. `test_get_widgets` (platform) - GET `/REST/dashboard/sharedwidgets/{customerId}/data`; validate result shape.
10. `test_search_person` (platform) - POST `/REST/site/search` with PERSON category payload for last hour; validate results structure.

11. `test_search_person_basic` - Search API helper for PERSON; basic type assertion for response.
12. `test_search_vehicle_basic` - Search API helper for VEHICLE; basic type assertion for response.

13. `test_get_site_status` (dashboard_api wrapper) - via `dashboard_api.get_site_status(test_site_id)` and `dashboard_api.validate_status_response()`.
14. `test_get_shared_widgets` (dashboard_api wrapper) - via `dashboard_api.get_shared_widgets(1)`; validate response shape.

15. `test_get_camera_tree` (camera_api wrapper) - `camera_api.get_camera_tree(test_site_id)` and validate via `camera_api.validate_camera_tree()`.
16. `test_get_camera_snapshot` (camera_api wrapper) - Discover a channel id and call `/REST/site/{siteId}/channel/{channelId}/snap`; validate response includes JPEG signature and expected content array.

## How to run
From repository root:

```bash
# Run the internal-API suite
pytest tests/internal_api/ -v
```

Target a specific environment by setting env variables or using the project's env config, e.g.: `ENV=qa BASE_URL=https://qa.example.invalid pytest tests/internal_api/ -v`.

## API endpoints covered (examples)
- `/REST/central/user/login` and `/REST/central/user/session` (login contract, session)
- `/REST/central/role/{enterpriseId}` (roles)
- `/REST/dashboard/site/{siteId}/status` (site status)
- `/REST/site/{siteId}/location/tree` (camera groups = locations)
- `/REST/site/config/{siteId}/location` and `/REST/site/{siteId}/deletelocation/{id}` (camera group create and delete)
- `/REST/clipbookmark` (bookmark create, list, soft delete)
- `/REST/site/{siteId}/channel/{channelId}/snap` (camera snapshot)
- `/REST/dashboard/sharedwidgets/{customerId}/data` (widgets)
- `/REST/site/search` (search)

The full list with request and response shapes is `docs/INTERNAL_API_INVENTORY.md`.

## Fixtures used
- `api_base_url` - resolved API base URL for the active environment
- `api_auth_token` / `api_auth_helper` - provides auth token or helper for requests
- `user_api`, `dashboard_api`, `camera_api`, `search_api`, `location_api`, `bookmark_api` - API client wrappers used by tests
- `discovered_site`, `discovered_site_id`, `discovered_enterprise_id`, `test_site_id`, `test_channel_ids` - auto-discovery fixtures to pick valid site/channel ids for read-only tests
- `data_site`, `data_site_id`, `data_channel_id` - the site and camera that `test_site_name` / `test_camera_name` in `config/env/` name, resolved by name. Tests that write data use these, never `TEST_SITE_ID`.
- `data_write_gate` - skips a writing test unless the env allows both writes and deletes (`allow_write`, `allow_delete` in `config/env/`)

## Notes & Recommendations
- Some tests accept multiple valid shapes (JSON or binary) - assertions aim to be permissive to reduce false negatives.
- Consider centralizing magic values (e.g., default channel id `1`) into fixtures or config for clarity.

