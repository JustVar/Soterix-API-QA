# API Surfaces, Auth Contracts, and Test Data

Last verified: **2026-08-27** (section 2), **2026-08-24** (section 1)

There are **two separate APIs** behind the same hostname. They have different
base paths and different authentication, and not every server deploys the
second one. Confusing them is the most likely source of wasted debugging
time, so this doc is the single reference for both.

| | Internal API | Integration API |
|---|---|---|
| Base path | `/v-apiserver` | `/v-integration-api` |
| Auth | `JSESSIONID` session cookie | `x-vsaas-key` header (static API key) |
| Scope | Everything the web app does | Read-only subset for 3rd parties |
| Methods | GET / POST / PUT / DELETE | GET only |
| Documented? | Vendor swagger is stale. Shapes come from testing: `INTERNAL_API_INVENTORY.md` | Swagger UI published |
| Available | every server | not every server: `integration_api_base_url` in `config/env/` is `None` where it is missing |

---

## 1. Internal API (`/v-apiserver`)

This is what the suite in `tests/internal_api/` targets, and what the SPA itself uses.

### Login - the only path that works from an API client

```
POST {host}/v-apiserver/REST/central/user/login
Content-Type: application/json

{
  "accountid": "user@soterixsystems.com",   <- the EMAIL goes here
  "username":  "Example Label",                   <- hardcoded literal, not the user
  "password":  "<SHA512 hex digest of the plaintext password>"
}
```

Success returns HTTP `200` with envelope `status` 2002 and the token at
`result[0].JSESSIONID`. Send it on every subsequent call as
`Cookie: JSESSIONID=<token>`. No reCAPTCHA is involved on this path.

Implemented in `AuthHelper._api_login()`
(`api_clients/auth_helper.py`). **No browser is required.**
`tests/internal_api/test_auth_apis.py::test_login_contract_returns_a_session`
pins this contract (verified 2026-08-24).

### Things that do NOT work - and why

- **`/REST/central/user/auth/login` requires a `captcha` query parameter.** Only a
  browser can produce a reCAPTCHA token, so this endpoint is unusable from an API
  client. The suite used to call it, fail, and silently fall back to driving a
  headed Chromium. That fallback no longer exists in this repo. No code reads an
  `ALLOW_UI_LOGIN_FALLBACK` variable. A login failure raises with a message that
  names the fix (table below).
- **Plaintext passwords are always rejected.** The password must be SHA512-hashed.
- **`/REST/sso/login`** returns "Missing one or more mandatory request
  parameter(s)" for every shape tried. Its required parameters are unknown.

The `accountid` / `"Example Label"` / SHA512 contract was read from the web app's own
JS bundle (chunk `6031-*.js`), the same build on every server seen so far.
If login ever breaks with correct credentials, re-check that chunk first.

### Reading login failures

The server distinguishes these, and each needs a different fix:

| Response | Meaning | Fix |
|---|---|---|
| `404` "There is no user with the userid!" | Account does not exist on this host | Check `QA_USER` in `.env` and `base_url` in `config/env/qa.py` |
| `400` "Invalid username and/or password!" | Account exists, password rejected | Stored password is stale |
| Connection error / DNS failure | Host is wrong or unreachable | Check `base_url` in `config/env/qa.py`, VPN |

`AuthHelper` raises these as distinct messages - trust them.

### The response envelope

Every internal call answers the same JSON envelope:

```
{"status": 2000, "code": 200, "description": "OK",
 "message": "Successfully Retrieved!", "uri": "/v-apiserver/REST/site",
 "result": [...]}
```

Trust `code`, `result`, and a follow-up read. Do not trust `message`. The
text comes from a fixed set and often does not match what happened. Two
examples from QA (2026-08-24):

- `POST /REST/site/{site}/getuserviewlayouts` with body `{}` answered
  status 2006 "Successfully deleted!" with `result [{"mode": ...}]` and
  deleted nothing (checked in the UI). With `{"mode": "live"}` it answered
  status 3139 "Required http POST request payload is not found!".
- `DELETE /REST/clipbookmark/{id}` answers 2006 "Successfully deleted!"
  while the row stays in the site list. It is a soft delete: `deletedAt`
  is -1 while the bookmark is live and a timestamp after the delete.

On success `code` is 200 and `status` is the API status. On an error the
2 fields swap roles: `code` carries the API error code, `status` carries
the HTTP status, and a `returnValue` names the error. A repeated
`deletelocation` answers:

```
HTTP 400 {"returnValue": "DB_NOT_FOUND", "code": 1006, "status": 400,
          "description": "Bad Request", "message": "Database: no record found!"}
```

Status values seen on QA (2026-08-24):

| Value | Field | HTTP | Seen on | Meaning |
|---|---|---|---|---|
| 2000 | `status` | 200 | most GETs, `deletelocation` | retrieved |
| 2002 | `status` | 200 | `central/user/login` | login ok |
| 2005 | `status` | 200 | `POST /REST/clipbookmark` | created |
| 2006 | `status` | 200 | `DELETE /REST/clipbookmark/{id}`, `getuserviewlayouts` with `{}` | deleted, also used as a generic ok |
| 2007 | `status` | 200 | `POST /REST/site/config/{site}/location` | applied |
| 3139 | `status` | not recorded | `getuserviewlayouts`, `site/search` with a body the server cannot read | payload missing |
| 1006 | `code` | 400 | repeated `deletelocation` | "Database: no record found!" |

`test_location_apis.py::test_delete_location_removes_it_and_a_second_delete_answers_1006`
pins the 1006 shape.

### Contracts the UI suite depends on

Since 2026-08-24 the UI suite (Soterix-WebApp-QA, `tests/shared/api/`)
builds its test data through this API instead of the browser. Its fixtures
send these requests:

| UI fixture | Endpoints | Pinned by |
|---|---|---|
| `api` (login, site check) | `POST /REST/central/user/login`, `GET /REST/site` | `test_auth_apis.py::test_login_contract_returns_a_session`, `test_location_apis.py::test_site_list_names_the_data_site` |
| `api_camera_group` (camera groups are locations) | `POST /REST/site/config/{site}/location`, `GET /REST/site/{site}/location/tree`, `GET /REST/site/{site}/deletelocation/{id}` | `test_location_apis.py` |
| `api_bookmark` | `POST /REST/clipbookmark`, `GET /REST/clipbookmark/{site}`, `DELETE /REST/clipbookmark/{id}` | `test_bookmark_apis.py` |

A change in any of these answers breaks UI test setup in the other repo.
When a pinned test fails, tell the WebApp QA maintainer before you change
the assertion. Request and response shapes: `INTERNAL_API_INVENTORY.md`.

---

## 2. Integration API (`/v-integration-api`)

Swagger UI: `<integration_api_base_url>/swagger-ui/index.html`, with
`integration_api_base_url` from `config/env/qa.py`.
Machine-readable spec: `/v-integration-api/v3/api-docs`

This surface is published for **third-party integrators**. It is a deliberately
read-only subset - it is *not* a substitute for the internal API, and most
of what QA tests has no equivalent here.

### Auth

A single static API key in a header. No login, no session, no expiry handling:

```
x-vsaas-key: <key>
```

Missing, wrong, empty, or disabled key returns `401` with `status: 9581`,
`"Invalid API Key in request headers."` (verified live 2026-08-27).

The key goes in `.env` as `VSAAS_INTEGRATION_KEY`. Never commit it. The QA
tenant carries a durable key named **"QA Automation - DO NOT DELETE"** for
the test suite. Keys are managed in the product under Admin > Integrations >
API Integration, backed by internal endpoints (session auth, enterprise
admin):

```
GET    /v-apiserver/REST/api/integration/key/{enterpriseId}      list
POST   /v-apiserver/REST/api/integration/key/generate            create
       body: {enterpriseId, name, host[], description[]}
PUT    /v-apiserver/REST/api/integration/key/{key}               update
GET    /v-apiserver/REST/api/integration/key/{key}/status/{0|1}  disable/enable
DELETE /v-apiserver/REST/api/integration/key/{key}               delete
```

Disable and delete take effect on the surface (401) within seconds. The
lifecycle test in `tests/internal_api/test_api_integration_key_apis.py`
verifies the whole cycle. Note: a key's `host[]` allowlist did NOT restrict
callers in live checks (a key listing only the QA host worked from an
outside IP) - treat `host` as documentation, and ask the platform team what
it is meant to enforce.

### Endpoints

Snapshot verified live on 2026-08-27. **The Swagger UI above is the source
of truth** - new endpoints are being added over time, so don't treat this
list as complete.

**Sites**
- `/REST/site`
- `/REST/site/{siteid}`

**Cameras**
- `/REST/site/channel`
- `/REST/site/channel/{siteid}`
- `/REST/site/channel/{siteid}/{channelid}`
- `/REST/site/channel/{siteid}/{channelid}/image/parameter`
- `/REST/site/channel/{siteid}/{channelid}/streaming/parameter`
- `/REST/site/channel/{siteid}/{channelid}/streaming/parameter/capability`

**Events**
- `/REST/event`
- `/REST/event/snap/{siteid}/{snapid}`

**Streaming**
- `/REST/stream`
- `/REST/stream/session`
- `/REST/stream/{siteid}/startlive/{channelid}`
- `/REST/stream/{siteid}/startarchive/{channelid}/{starttimestamp}`

Response contracts that a naive "assert 200" gets wrong (all verified live,
the sweep in `tests/integration_api/` encodes them per endpoint):

- `/REST/event` and `/REST/stream` answer 200 with **no data**: a portal
  pointer message plus a `streamingServerUrl`. They are navigation hints,
  not data endpoints.
- A bad or missing sub-resource id answers **400** ("Runtime exception
  occurred!" or "check your request parameters"), not 404.
- `startlive`/`startarchive` answer 200 "Successfully created!" and return
  a real WebRTC `streamurl`. They **create a server-side streaming
  session**, so the surface is not strictly read-only in effect. The TTL of
  a session whose stream URL is never connected is unknown. Ask the
  platform team and record the answer here.

### Why this matters for test design

Because it is key-authenticated and read-only, this surface is the cheapest thing
in the whole system to test: no login flow, no session expiry, no captcha, no
browser, and safe to run against any environment that exposes it. It is a good
first target for the API test repo.

The catch is coverage - it exposes only a small slice of the platform so far
(more is promised as the swagger site gets updated). Everything else still requires the internal
API and its session login, and remains **undocumented**: the endpoint list has to
be discovered by capturing what the app does. `docs/API_ENDPOINTS.md` is that
running catalog (where each call surfaces, coverage status).
`docs/INTERNAL_API_INVENTORY.md` holds the request and response shapes and
the date each was verified.

---

## 3. The server and the test data

One file names the server: `config/env/qa.py`. Its keys:

| Key | What it is |
|---|---|
| `base_url` | the site root |
| `api_base_url` | `base_url` + `/v-apiserver` |
| `integration_api_base_url` | `base_url` + `/v-integration-api`, or `None` on a server without the surface |
| `allow_write`, `allow_delete` | both must be `True` for tests that create data to run |
| `test_site_name`, `test_camera_name` | a site and a camera the account can see, resolved by name. Optional: blank means the first site by name with a camera, and the first camera by name on it |

The account is `QA_USER` and `QA_PASSWORD` in `.env`. `ENV=<name>` selects
`config/env/<name>.py`. A second server is a copy of `qa.py`.

### Test data

Sites and channels differ per account, so the suite discovers them at run time.

**Read-only tests** use the discovery fixtures (`test_site_id`,
`test_channel_ids`) rather than hardcoded ids. Set `TEST_SITE_ID` in `.env`
only to pin a specific site your account can reach. A site id your account
cannot reach returns 400. `TEST_CHANNEL_ID` pins the channel of the sweep
and the e2e flows the same way.

**Tests that write data** (locations, bookmarks) use the fixtures
`data_site_id` and `data_channel_id`. They resolve the site by NAME from
`test_site_name` and `test_camera_name` in `config/env/`, never from
`TEST_SITE_ID`. Name the site, not a number: two sites with similar names
once carried the wrong id in both repos. If you set `TEST_SITE_ID`, write
the site name next to it in `.env`. When a name does not resolve, the skip
message lists the names the account sees.

Both names may stay blank. The run then picks the first site by name that
the account can see, with status `REGISTERED` and at least 1 camera in its
location tree, and the first camera by name on it. Sorted by name, never
by the server's order, because that order changes when a camera is added.
A channel whose `isChannelDeleted` is set is not a camera. A name that is
set is checked, never replaced. The rule is `api_clients/data_choice.py`,
pinned offline by `tests/internal_api/test_data_choice.py`, and the run
prints the site and the camera it used (`[DATA SITE]`, `[DATA CAMERA]`).

Writes are gated by `allow_write` and `allow_delete` in `config/env/`
(fixture `data_write_gate`). Every name a test creates starts with
`AutoTest ` and the test removes it at teardown.

---

## Open items

- ~~Obtain and store the integration API key~~ done 2026-08-27: the QA
  tenant key "QA Automation - DO NOT DELETE" backs `VSAAS_INTEGRATION_KEY`.
- `/REST/sso/login` parameter contract is still unknown.
- `POST /REST/site/{site}/getuserviewlayouts` working payload is unknown
  (`{}` and `{"mode": "live"}` both answer the wrong message).
