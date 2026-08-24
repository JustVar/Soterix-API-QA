# Soterix VSaaS - API Endpoint Catalog

Living catalog of every REST endpoint the NexaiQ-Core SPA exercises, with smoke-test coverage status. Source of truth: live network capture on `staging.example.invalid`. Vendor swagger is currently stale (per 2026-05-15 audit) - trust this doc over swagger until a refreshed spec is delivered.

This file says where each call surfaces and whether a test covers it. Request
and response shapes, and the date each was verified on QA, live in
[INTERNAL_API_INVENTORY.md](./INTERNAL_API_INVENTORY.md).

Last updated: **2026-08-24** (coverage flags and the auth rows; the capture is still from 2026-05-15)
Capture method: **live network capture in Chrome DevTools, signed in as a QA account**

## Base path

All endpoints below are relative to `<host>/v-apiserver`. Example: `/REST/central/user/session` is fetched from `https://staging.example.invalid/v-apiserver/REST/central/user/session`.

Per-environment host:

| Env | Host |
|---|---|
| prod | `https://app.example.invalid` |
| staging | `https://staging.example.invalid` |
| qa | `https://qa.example.invalid` |

Auth: JSESSIONID cookie (not JWT). See `api_clients/auth_helper.py`.

## Status legend

- **covered** - has a dedicated test in `tests/internal_api/`
- **in-progress** - Tier 1 stub written, assertions need fleshing out
- **uncovered** - observed live, no test
- **untriggered** - likely exists (write path, lazy panel) but not yet captured

---

## Auth / Session

| Status | Method | Path | Notes |
|---|---|---|---|
| covered | POST | `/REST/central/user/login` | The login the web client uses (JSON body, SHA512 password, no captcha). Used by `auth_helper.py`. `test_auth_apis.py::test_login_contract_returns_a_session` |
| covered | POST | `/REST/central/user/auth/login` | Captcha-gated browser login. Unusable from an API client. `test_auth_apis.py` pins the rejection. |
| uncovered | POST | `/REST/sso/login` | Parameters unknown. `test_auth_apis.py` skips without `SSO_TEST_USERNAME`. Not used by `auth_helper.py`. |
| untriggered | POST | `/REST/site/{siteId}/auth/logout` | Inferred from prior swagger; not yet exercised on staging. |
| covered | GET | `/REST/central/user/session` | `test_user_apis.py::test_get_user_session` |
| covered | GET | `/REST/central/userprofile/roles` | `test_user_apis.py::test_get_user_roles` |
| covered | GET | `/REST/central/role/{enterpriseId}` | `test_user_apis.py::test_get_roles_by_enterprise` |

## User management (Admin -> Users)

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | GET | `/REST/site/user/{email}` | Views, Media, Admin. `test_admin_users_apis.py` |
| covered | GET | `/REST/central/user/enterprise/{enterpriseId}` | Admin -> Users tab. `test_admin_users_apis.py` |
| covered | GET | `/REST/central/user/enterprise/{enterpriseId}/profile/{profileId}` | Admin dashboard summary. `test_admin_users_apis.py` |
| untriggered | POST | `/REST/central/user/update` | User edit (not triggered) |
| untriggered | PUT | `/REST/central/user/password/reset` | Forgot-password flow (the QA spec has PUT, not POST) |
| untriggered | PUT | `/REST/central/user/password/update` | Change-password modal |

## Sites & devices (Admin -> Sites)

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | GET | `/REST/site` | Site list. `test_location_apis.py::test_site_list_names_the_data_site` |
| covered | GET | `/REST/site/{siteId}/location/tree` | Admin -> Sites Groups dropdown (a camera group is a location). `test_platform_apis.py`, `test_location_apis.py` |
| covered | POST | `/REST/site/config/{siteId}/location` | Admin -> Sites, create camera group. `test_location_apis.py`. The UI suite seeds groups through it. |
| covered | GET | `/REST/site/{siteId}/deletelocation/{locationId}` | Admin -> Sites, delete camera group. `test_location_apis.py` |
| uncovered | GET | `/REST/site/{siteId}/getalllocations` | Admin -> Sites (seen in the page trace 2026-08-24) |
| covered | GET | `/REST/site/{siteId}/channel` | `test_camera_apis.py` |
| covered | GET | `/REST/site/{siteId}/channel/{channelId}/snap` | `test_camera_apis.py` |
| covered | POST | `/REST/enterprise/sitedetails` | Admin -> Sites tab. `test_admin_sites_apis.py` |
| covered | GET | `/REST/site/{siteId}/getsitedetails` | Admin dashboard + Sites. `test_admin_sites_apis.py` |
| covered | GET | `/REST/edge/version/latest` | Admin -> Sites. `test_admin_sites_apis.py` |
| covered | GET | `/REST/edge/version/site/{siteId}/current` | Admin -> Sites. `test_admin_sites_apis.py` |
| covered | GET | `/REST/edge/version/site/{siteId}/previous` | Admin -> Sites. `test_admin_sites_apis.py` |
| untriggered | DELETE | `/REST/site/{siteId}` | Site delete (not triggered) |

The legacy group endpoints (`addgroup`, `updategrouploctions`,
`getchannelsbygroup`, `deletegroup`, `grouptree`) answer but the Admin UI
never shows what they make. Shapes in the inventory.

## Rules & analytics (Admin -> Rules)

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | POST | `/REST/rule/enterprise/{enterpriseId}/search` | Admin -> Rules + dashboard. `test_admin_rules_apis.py` |
| covered | GET | `/REST/analyticschedule/{enterpriseId}/type/{type}` | Admin -> Rules. `test_admin_rules_apis.py` |
| covered | GET | `/REST/webhook/{enterpriseId}` | Admin -> Rules -> Webhooks. `test_admin_rules_apis.py` |
| covered | GET | `/REST/site/analytics/enterprise/{enterpriseId}/licensed` | Views, Search, Rules. `test_admin_rules_apis.py` |
| untriggered | POST | `/REST/rule/enterprise/{enterpriseId}/...` (CRUD) | Rule wizard (not triggered) |
| untriggered | POST | `/REST/webhook` / `/webhook/update` | Webhook CRUD |

## Events

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | POST | `/REST/site/search` | `test_platform_apis.py`, `test_search_api.py` (person/vehicle payloads) |
| covered | POST | `/REST/site/search/event` | Events page -> Search button (pages a search job's events). `test_events_apis.py` |
| uncovered | GET | `/REST/das/event/type/{typeId}/limit/{n}` | LPR page |

## Bookmarks

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | POST | `/REST/clipbookmark` | Bookmark a clip (multipart `snap` + query parameters). `test_bookmark_apis.py`. The UI suite seeds bookmarks through it. |
| covered | GET | `/REST/clipbookmark/{siteId}` | Bookmarks panel. `test_bookmark_apis.py` |
| covered | DELETE | `/REST/clipbookmark/{bookmarkId}` | Bookmarks panel, delete (soft delete). `test_bookmark_apis.py` |

## View layouts

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | POST | `/REST/site/{siteId}/getuserviewlayouts` | Views page. Working payload unknown, answers a wrong `message` (inventory). |

## Insights / dashboards / widgets

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| covered | GET | `/REST/dashboard/site/{siteId}/status` | `test_platform_apis.py` |
| covered | GET | `/REST/dashboard/sharedwidgets/{customerId}/data` | `test_platform_apis.py` |
| uncovered | GET | `/REST/dashboard/widget/mywidgets/data` | Insights |
| uncovered | GET | `/REST/dashboard/getmydashboards/data` | Insights |
| uncovered | GET | `/REST/dashboard/shareddashboards/{customerId}/data` | Insights |
| uncovered | GET | `/REST/dashboard/thumbnail/{dashboardId}` | Insights |
| uncovered | GET | `/REST/dashboard/widget/thumbnail/{widgetId}` | Insights / LPR |
| untriggered | PUT | `/REST/dashboard/widget/update/{widgetId}` | Widget edit |

## Maps

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | GET | `/REST/staticmap/{siteId}/metadata` | Maps + Admin dashboard |
| uncovered | GET | `/REST/staticmap/{siteId}/enc/{encId}/thumbnail` | Maps + Admin dashboard |
| untriggered | POST / PUT | `/REST/staticmap/{siteId}` and `/addchannel`, `/addchannels`, `/direction` | Map edit |

## Media

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | GET | `/REST/media/storage/vault` | Media |
| uncovered | POST | `/REST/media/search/enc` | Media (clips, folders, vault, My Media all share this) |
| untriggered | PUT | `/REST/media/vault/{mediaid}` | Add to vault |

## LPR

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | GET | `/REST/lpr/site/{siteId}/location/tree` | LPR |
| uncovered | GET | `/REST/lpr/enterprise/{enterpriseId}/widget/data` | LPR |

## Licenses (Admin -> Licenses)

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | GET | `/REST/user/license/available/{enterpriseId}/{email}` | Admin -> Licenses (default tab) |
| uncovered | GET | `/REST/user/license/overview/{enterpriseId}` | Admin -> Licenses |
| uncovered | GET | `/REST/user/license/assigned/{enterpriseId}/{email}` | Admin -> Assigned Licenses sub-tab |
| uncovered | GET | `/REST/enterprise/{enterpriseId}/withlogo` | Admin -> Licenses |
| untriggered | POST | `/REST/user/license/feature/assignment` | License assign action |
| untriggered | POST | `/REST/user/license/feature/update/assignment/{action}` | License unassign/re-assign |

## Platform / misc

| Status | Method | Path | Where surfaced |
|---|---|---|---|
| uncovered | GET | `/REST/favourite/getallfavourites` | Global (LPR + others) |
| uncovered | GET | `/REST/platform/deployment` | Admin -> General |

## Not REST (excluded from API smoke planning)

These features are backed by **Firebase Firestore live channels**, not REST. Test them via UI smoke instead:

- Notifications panel (bell icon, badge count, mute/unmute)
- Chats panel (group messages, real-time delivery)

Endpoint pattern: `firestore.googleapis.com/.../Listen/channel?...`

---

## How to update this doc

1. Drive the SPA through a feature you suspect has uncovered endpoints.
2. Capture network traffic. Three ways:
   - **Quick & local:** open Chrome DevTools -> Network -> filter `v-apiserver` -> click through the feature -> Save as HAR.
   - **Interactive exploration:** use Bruno to poke an endpoint and refine the request shape before promoting it to a smoke test. See [BRUNO_GUIDE.md](./BRUNO_GUIDE.md).
   - **Programmatic:** in the DevTools console, patch `window.fetch` to log every REST call, then click through the feature and read the log.
3. Diff against this catalog. Add new rows under the right section with status `uncovered` and a one-line "Where surfaced" note.
4. When a smoke test lands, flip status to covered and link the test file/function.
5. Bump the "Last updated" date.

## Tooling at a glance

| Tool | What it does | When to use |
|---|---|---|
| **pytest internal-API suite** (`tests/internal_api/`) | The authoritative automated API tests (smoke depth, `@pytest.mark.smoke`) | Always - this is the source of truth for coverage |
| **Bruno** (`tests/bruno/`, not yet in this repo) | Human-friendly request collection, plain-file checked into git | Exploring a new endpoint, debugging a failing smoke test, sharing a repro with the platform team - see [BRUNO_GUIDE.md](./BRUNO_GUIDE.md) |
| **Chrome DevTools network capture** | Capturing what the SPA actually calls | First step in discovering an undocumented endpoint |

pytest is the test runtime. This repo is browser-free. Bruno is for exploration; it is not a CI dependency.

## Why no swagger?

Vendor swagger at `https://app.example.invalid/v-apiserver/v3/api-docs` was audited 2026-05-15 and found stale - at least 14 production endpoints (most of the dashboard, LPR, media, and analytics surfaces) are missing from it, and the documented base URL is wrong. Treat swagger as advisory, not authoritative. This document supersedes it for QA test planning.
