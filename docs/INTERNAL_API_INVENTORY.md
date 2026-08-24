# Internal API inventory (`/v-apiserver`)

Every internal endpoint this repo has found or tested, one row each. Read
`API_SURFACES.md` first for the login contract and the response envelope.
`API_ENDPOINTS.md` says where the web app surfaces each endpoint and which
test covers it. This file holds the request and response shapes and the
date each contract was last confirmed on QA.

Last verified: **2026-08-24** (QA, `tests/internal_api` run: 38 passed,
1 skipped for missing SSO credentials).

## How to read the table

- Paths are relative to `<host>/v-apiserver`. Every call sends
  `Cookie: JSESSIONID=<token>` except login.
- "Response" is the envelope's `result` unless the row says otherwise.
  The status numbers are the envelope `status` seen on QA. `code` is 200
  on success and the API error code on failure.
- "Verified on QA" is the date the request and answer in that row were
  last confirmed against `qa.example.invalid`. "staging capture
  2026-05-15" means the row comes from the Chrome network capture behind
  `API_ENDPOINTS.md` and nothing here has called it since. "spec only,
  untested" means the path is in `schemas/openapi_spec_qa.json` (893
  paths) and nothing here has called it.
- "Used by" names the `api_clients/` module, the `tests/internal_api/`
  file, or "WebApp QA fixture" (Soterix-WebApp-QA, `tests/shared/api/`).
- Every path in this file is present in the QA spec snapshot. The spec
  is still stale on request shapes (see the login row).

## Contracts the UI suite depends on

Since 2026-08-24 the UI suite builds its test data through this API. Its
fixtures `api` (login and site list), `api_camera_group` (locations), and
`api_bookmark` (bookmarks) send the requests in the rows marked "WebApp QA
fixture". `test_auth_apis.py`, `test_location_apis.py`, and
`test_bookmark_apis.py` pin those rows. A change in one of those answers
breaks UI test setup in the other repo. Tell the WebApp QA maintainer
before you change a pinned assertion.

## Auth and session

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/central/user/login` | Sign in, open a session | JSON `{"accountid": <email>, "username": "Example Label", "password": <sha512 hex>}` | HTTP 200, status 2002, `result[0].JSESSIONID`. 404 "There is no user with the userid!" for an unknown account. 400 "Invalid username and/or password!" for a wrong password. | 2026-08-24 | `auth_helper.py`, `test_auth_apis.py`, WebApp QA fixture `api` | No captcha on this path. The spec lists the 3 fields as query parameters. The JSON body is what works. |
| `GET /REST/central/user/session` | The current session | none | 200, status 2000, `result[0]` = `{streamer, JSESSIONID, userId}` | 2026-08-24 | `auth_helper.py` (cache check), `user_api.py`, `site_helper.py`, `test_user_apis.py`, `test_auth_apis.py` | |
| `POST /REST/central/user/auth/login` | Browser login with reCAPTCHA | needs a `captcha` query parameter | Rejects an API client. No token in the body. | 2026-08-24 (rejection only) | `test_auth_apis.py` | Unusable from an API client. Do not route login through it. |
| `POST /REST/sso/login` | SSO login | unknown | "Missing one or more mandatory request parameter(s)" for every shape tried | unverified | `test_auth_apis.py` (skips without `SSO_TEST_USERNAME`) | Parameter contract unknown. |
| `GET /REST/central/user/auth/logout` | End the session | none | | spec only, untested | none | Never call it on the shared session. It ends every test using that token. |
| `POST /REST/site/{siteId}/auth/logout` | End the site session | | | spec only, untested | none | Same warning. |
| `GET /REST/central/userprofile/roles` | Roles of the current user | none | 200, result list | 2026-08-24 | `user_api.py`, `test_user_apis.py` | |
| `GET /REST/central/role/{enterpriseId}` | Roles of an enterprise | none | 200, result `[{profileId, profileName, priority, ...}]` | 2026-08-24 | `test_user_apis.py`, `test_admin_users_apis.py` | |

## Sites, users, edge

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `GET /REST/site` | Sites the account can see | none | 200, status 2000, result `[{siteId, name, enterpriseId, address, ...}]` | 2026-08-24 | `discovery_helper.py`, `test_location_apis.py`, WebApp QA fixture `api` | On QA the account sees 8 sites. 16 is "Newtown Action Area" (the UI suite's site). 17 is "Example Corporate Office". |
| `GET /REST/site/user/{email}` | Sites assigned to a user | none | 200, result with the same site shape | 2026-08-24 | `site_discovery.py` (fixtures `discovered_site`, `data_site`), `site_helper.py`, `test_admin_users_apis.py` | |
| `GET /REST/site/{siteId}` | One site | none | 200, result `[{... enterpriseId}]` | unverified | `search_api.py` (inside a try/except, to read `enterpriseId`) | A failure there is silent. |
| `GET /REST/site/{siteId}/getsitedetails` | Site detail | none | 200, result present | 2026-08-24 | `test_admin_sites_apis.py` | |
| `POST /REST/enterprise/sitedetails` | Site roster of an enterprise | JSON `{"enterpriseId": n}` | 200, result list or dict | 2026-08-24 | `test_admin_sites_apis.py` | Payload inferred from capture. |
| `GET /REST/central/user/enterprise/{enterpriseId}` | Users of an enterprise | none | 200, result `[user]` with `userId` and `email` | 2026-08-24 | `test_admin_users_apis.py` | |
| `GET /REST/central/user/enterprise/{enterpriseId}/profile/{profileId}` | Users with one profile | none | 200, result present | 2026-08-24 | `test_admin_users_apis.py` | `profileId` comes from `/REST/central/role/{enterpriseId}`. |
| `GET /REST/edge/version/latest` | Latest published edge build | none | 200, result not null | 2026-08-24 | `test_admin_sites_apis.py` | |
| `GET /REST/edge/version/site/{siteId}/current` | Running edge build of a site | none | 200 | 2026-08-24 | `test_admin_sites_apis.py` | |
| `GET /REST/edge/version/site/{siteId}/previous` | Previous edge build of a site | none | 200 | 2026-08-24 | `test_admin_sites_apis.py` | |
| `DELETE /REST/site/{siteId}` | Delete a site | | | unverified (inferred from the old swagger) | none | Never call it on the shared tenant. |
| `POST /REST/central/user/update` | Edit a user | | | staging capture 2026-05-15 (not triggered) | none | |
| `PUT /REST/central/user/password/reset` | Forgot-password flow | | | staging capture 2026-05-15 (not triggered) | none | The catalog lists it as POST. The spec has PUT. |
| `PUT /REST/central/user/password/update` | Change password | | | staging capture 2026-05-15 (not triggered) | none | |

## Cameras

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `GET /REST/site/{siteId}/channel` | Cameras of a site (flat list) | none | 200, result `[VChannel {id, name, model, snapUrl, ...}]` | 2026-08-24 | `camera_api.py` (`get_camera_tree`), `discovery_helper.py`, `test_camera_apis.py`, `test_platform_apis.py` | `snapUrl` marks a snapshot-capable camera. The client method name says tree. It is the flat list. |
| `GET /REST/site/{siteId}/channel/{channelId}/snap` | Snapshot as JSON bytes | none | 200, status 2000, result `[{"content": [signed bytes]}]`. `content[0:2] == [-1, -40]` is the JPEG signature. | 2026-08-24 | `test_camera_apis.py`, `test_platform_apis.py` | |
| `GET /REST/site/{siteId}/channel/{channelId}/camera/snap` | Snapshot from the camera | none | | unverified | `camera_api.py` (`get_camera_snapshot`, no test calls it) | |

## Camera groups (locations)

A camera group in Admin > Sites is a location in the API. The UI reads
`location/tree` (and `getalllocations`) for its Groups dropdown.

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `GET /REST/site/{siteId}/location/tree` | Camera groups with their cameras | none | 200, status 2000, result `[{"location": {id, name}, "channel": [VChannel, ...]}]` | 2026-08-24 | `location_api.py`, `test_location_apis.py`, `test_platform_apis.py`, WebApp QA fixture `api_camera_group` | "All Cameras" (id 1) holds every camera on the site. A camera can sit in several locations. |
| `POST /REST/site/config/{siteId}/location` | Create a camera group | JSON `{"name": "...", "siteId": 16, "channelList": [97]}` | 200, status 2007 "Successfully Applied!", result echoes the request without an id | 2026-08-24 | `location_api.py`, `test_location_apis.py`, WebApp QA fixture `api_camera_group` | The id only comes from a `location/tree` read. The spec schema (`UpdateLocationRequest`) also has `id`. |
| `GET /REST/site/{siteId}/deletelocation/{locationId}` | Delete a camera group | none | 200, status 2000, result `[true]`. Repeat: HTTP 400, `code` 1006, `status` 400, `returnValue` "DB_NOT_FOUND", "Database: no record found!" | 2026-08-24 | `location_api.py`, `test_location_apis.py`, WebApp QA fixture `api_camera_group` | A GET that writes. The camera keeps its other locations. |
| `GET /REST/site/{siteId}/getalllocations` | Locations without cameras | none | | unverified (seen in the Admin > Sites page trace 2026-08-24, not called from this repo) | none | |
| `POST /REST/site/config/{siteId}/update/location` | Edit a camera group | | | spec only, untested | none | |
| `POST /REST/site/{siteId}/addlocation` | Older create path | | | spec only, untested | none | |

## Groups (legacy, not shown in the UI)

These answer, but nothing made through them appears in the Admin UI
(checked 2026-08-24). Do not use them to seed UI tests.

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/site/{siteId}/addgroup` | Create a group | JSON `{"name": "..."}` | 200, result `[{"id": 2, "name": "..."}]`, message "Successfully Retrieved!" | 2026-08-24 (WebApp QA pilot) | none | The message text is wrong. |
| `POST /REST/site/{siteId}/updategrouploctions` | Attach cameras to a group | JSON `{"channelIds": [97], "secondaryId": 2}` | 200, result `[true]` | 2026-08-24 (WebApp QA pilot) | none | The path spelling is the vendor's. |
| `GET /REST/site/{siteId}/getchannelsbygroup/{groupId}` | Cameras of a group | none | 200, result `[]` even with a camera attached | 2026-08-24 (WebApp QA pilot) | none | |
| `GET /REST/site/{siteId}/deletegroup/{groupId}` | Delete a group | none | 200, result `[true]` | 2026-08-24 (WebApp QA pilot) | none | |
| `GET /REST/site/{siteId}/grouptree` | Group tree | none | 200, status 2000 | 2026-08-24 (WebApp QA pilot) | none | |
| `GET /REST/site/{siteId}/getAllGroups` | All groups | | | spec only, untested | none | |
| `GET /REST/site/{siteId}/group/tree` | Group tree (other spelling) | | | spec only, untested | none | |

## Bookmarks

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/clipbookmark` | Create a bookmark | Query `timestamp` (ms), `siteId`, `cameraId`, `retentionDays`, `comment`. Multipart part `snap` holding an image file (required). | 200, status 2005 "Successfully created!", result `[VClipBookmark]` = `{bookmarkId, timestamp, createdTime, userId, siteId, cameraId, snap, retentionDays, comment, deletedAt: -1, offset, limit}` | 2026-08-24 | `bookmark_api.py`, `test_bookmark_apis.py`, WebApp QA fixture `api_bookmark` | A 1x1 PNG is enough for `snap`. |
| `GET /REST/clipbookmark/{siteId}` | Bookmarks of a site | none | 200, status 2000, result `[VClipBookmark]`, soft-deleted rows included | 2026-08-24 | `bookmark_api.py`, `test_bookmark_apis.py`, WebApp QA fixture `api_bookmark` | A live row holds `deletedAt` -1. |
| `DELETE /REST/clipbookmark/{bookmarkId}` | Soft-delete a bookmark | none | 200, status 2006 "Successfully deleted!", result `[]`. The row stays listed with `deletedAt` set to a timestamp. A repeat answers 200, 2006 again. | 2026-08-24 | `bookmark_api.py`, `test_bookmark_apis.py`, WebApp QA fixture `api_bookmark` | No hard delete found. Rows expire with `retentionDays`. "Gone" means `deletedAt > 0`, not absence from the list. |
| `POST /REST/clipbookmark/update` | Edit a bookmark | | | spec only, untested | none | |
| `POST /REST/clipbookmark/search` | Search bookmarks | | | spec only, untested | none | |
| `POST /REST/clipbookmark/count` | Count bookmarks | | | spec only, untested | none | |

## View layouts

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/site/{siteId}/getuserviewlayouts` | Read the user's saved view layouts | Spec schema `UserViewLayouts` (`mode` integer, `username`, `liveViewLayouts`, ...). `{}` answered status 2006 "Successfully deleted!" with result `[{"mode": ...}]` and deleted nothing. `{"mode": "live"}` answered status 3139 "Required http POST request payload is not found!". | see Request | 2026-08-24 (WebApp QA) | none | The `message` is wrong on both answers. The working payload is unknown. There is no safe oracle for "deleted nothing", so no test pins it. |
| `POST /REST/site/{siteId}/saveuserviewlayouts` | Save view layouts | | | spec only, untested | none | |

## Dashboards and widgets

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `GET /REST/dashboard/site/{siteId}/status` | Site status | none | 200, result `{siteId, enterpriseid, ...}` | 2026-08-24 | `dashboard_api.py`, `enterprise_helper.py`, `test_dashboard_apis.py`, `test_platform_apis.py` | The key is lowercase `enterpriseid` here and `enterpriseId` elsewhere. |
| `GET /REST/dashboard/sharedwidgets/{enterpriseId}/data` | Shared widgets | none | 200, result dict or list | 2026-08-24 | `dashboard_api.py`, `test_dashboard_apis.py` (calls it with id 1), `test_platform_apis.py` | |
| `GET /REST/dashboard/widget/mywidgets/data` | My widgets | | | staging capture 2026-05-15 | none | |
| `GET /REST/dashboard/getmydashboards/data` | My dashboards | | | staging capture 2026-05-15 | none | |
| `GET /REST/dashboard/shareddashboards/{enterpriseId}/data` | Shared dashboards | | | staging capture 2026-05-15 | none | |
| `GET /REST/dashboard/thumbnail/{dashboardId}` | Dashboard thumbnail | | | staging capture 2026-05-15 | none | |
| `GET /REST/dashboard/widget/thumbnail/{widgetId}` | Widget thumbnail | | | staging capture 2026-05-15 | none | |
| `PUT /REST/dashboard/widget/update/{widgetId}` | Edit a widget | | | staging capture 2026-05-15 (not triggered) | none | |

## Search and events

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/site/search` | Submit a search job | JSON `{"queryList": [{"query": {siteId, channelList, startTimeStamp, endTimeStamp, category "PERSON" or "VEHICLE", description {...}}}], "isAddedByRule": false}` | 200, result `[{jobId, ...}]` | 2026-08-24 | `search_api.py`, `test_search_api.py`, `test_platform_apis.py`, `test_events_apis.py` | `search_api.py` retries with a raw JSON string body when the server answers "Required http POST request payload is not found". |
| `POST /REST/site/search/event` | Page the events of a search job | JSON `{"jobId": ..., "offset": 0, "limit": 25}` | 200, result `[{eventList: [...]}]`. `{}` must not answer data. | 2026-08-24 | `test_events_apis.py` | Not a filter query. `siteId`, `startTime`, `ruleType` there answer 400 "verify request parameter data type". |
| `GET /REST/das/event/type/{typeId}/limit/{n}` | Recent events of one type (LPR page) | | | staging capture 2026-05-15 | none | |

## Rules and analytics

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `POST /REST/rule/enterprise/{enterpriseId}/search` | Rules of an enterprise | JSON `{}` | 200, result list or dict | 2026-08-24 | `test_admin_rules_apis.py` | |
| `GET /REST/analyticschedule/{enterpriseId}/type/{type}` | Analytic schedules | none (type 1) | 200 | 2026-08-24 | `test_admin_rules_apis.py` | |
| `GET /REST/webhook/{enterpriseId}` | Webhooks of an enterprise | none | 200, result list (empty is valid) | 2026-08-24 | `test_admin_rules_apis.py` | |
| `GET /REST/site/analytics/enterprise/{enterpriseId}/licensed` | Licensed analytic types | none | 200, result present | 2026-08-24 | `test_admin_rules_apis.py` | |
| `POST /REST/webhook` | Create a webhook | | | staging capture 2026-05-15 (not triggered) | none | |
| `POST /REST/rule/enterprise/{enterpriseId}` | Rule CRUD | | | staging capture 2026-05-15 (not triggered) | none | Needs throwaway test data. |

## Maps, media, LPR, licenses, platform

All rows here come from the staging capture of 2026-05-15. Nothing in this
repo has called them.

| Method and path | What it does | Request | Response and status | Verified on QA | Used by | Notes |
|---|---|---|---|---|---|---|
| `GET /REST/staticmap/{siteId}/metadata` | Map metadata | | | staging capture 2026-05-15 | none | Maps and the Admin dashboard. |
| `GET /REST/staticmap/{siteId}/enc/{encId}/thumbnail` | Map thumbnail | | | staging capture 2026-05-15 | none | |
| `GET /REST/media/storage/vault` | Vault storage | | | staging capture 2026-05-15 | none | |
| `POST /REST/media/search/enc` | Media search | | | staging capture 2026-05-15 | none | Clips, folders, vault, and My Media share it. |
| `PUT /REST/media/vault/{mediaid}` | Add to vault | | | staging capture 2026-05-15 (not triggered) | none | |
| `GET /REST/lpr/site/{siteId}/location/tree` | LPR camera tree | | | staging capture 2026-05-15 | none | |
| `GET /REST/lpr/enterprise/{enterpriseId}/widget/data` | LPR widget data | | | staging capture 2026-05-15 | none | |
| `GET /REST/user/license/available/{enterpriseId}/{email}` | Available licenses | | | staging capture 2026-05-15 | none | |
| `GET /REST/user/license/overview/{enterpriseId}` | License overview | | | staging capture 2026-05-15 | none | |
| `GET /REST/user/license/assigned/{enterpriseId}/{email}` | Assigned licenses | | | staging capture 2026-05-15 | none | |
| `GET /REST/enterprise/{enterpriseId}/withlogo` | Enterprise with logo | | | staging capture 2026-05-15 | none | |
| `POST /REST/user/license/feature/assignment` | Assign a license | | | staging capture 2026-05-15 (not triggered) | none | |
| `POST /REST/user/license/feature/update/assignment/{action}` | Unassign or reassign a license | | | staging capture 2026-05-15 (not triggered) | none | |
| `GET /REST/favourite/getallfavourites` | Favourites | | | staging capture 2026-05-15 | none | |
| `GET /REST/platform/deployment` | Deployment info | | | staging capture 2026-05-15 | none | Admin > General. |

## How to update this file

1. When a test lands or a probe confirms a shape, set "Verified on QA" to
   that date and fill in the request and response columns.
2. When you find a new endpoint, add a row. If it came from the spec
   alone, mark it "spec only, untested".
3. Keep `API_ENDPOINTS.md` in step: it holds the coverage status and the
   screen that surfaces the endpoint.
4. Bump "Last verified" at the top after a full `tests/internal_api` run.
