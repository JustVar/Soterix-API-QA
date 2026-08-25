# API Testing Notes - Camera Discovery (QA)

> Auth and environment details moved to **`docs/API_SURFACES.md`**, which covers
> both the internal (`/v-apiserver`) and integration (`/v-integration-api`) APIs.
> This file covers camera/channel discovery and the HTTP exchange block in
> failure reports (last section).

## QA Environment Configuration

| Setting | Value |
|---------|-------|
| Base URL | https://qa.example.invalid |
| API Path | /v-apiserver |
| Test data site | "Newtown Action Area" = siteId 16, camera "main gate" = channel 97. Resolved by name from `test_site_name` in `config/env/qa.py`. |
| `TEST_SITE_ID` | Optional pin for read-only tests only. 17 is "Example Corporate Office", not the test data site. |

Updated 2026-08-24. The old host `qa.example.invalid` **no longer
resolves in DNS**, and site `110` returns 400 for the current account. The
account's sites on 2026-08-24 were `16, 17, 97, 105, 109, 111, 125, 153`.
The camera inventory below was captured against site 110 on the previous
host and is retained only as a historical reference; use
`tools/discover_cameras.py` for the live topology (it still defaults to
site 17 when `TEST_SITE_ID` is unset).

## Authentication

- JSESSIONID cookie-based auth (not JWT)
- Obtained over HTTP with **no browser**: `POST /REST/central/user/login` with a
  SHA512-hashed password - see `docs/API_SURFACES.md` for the exact payload
- Session cached in `.session_cache` (8 hour TTL)

> **Correction (2026-08-05).** This file previously stated that "API login
> returns 400 for the QA account (expected)" and that the suite "falls back to UI
> login via Playwright". That was a bug being recorded as intended behaviour. The
> 400 was caused by calling the captcha-gated `/REST/central/user/auth/login`
> with a plaintext password. No UI fallback exists in this repo (no code reads
> an `ALLOW_UI_LOGIN_FALLBACK` variable). API runs launch no browser at all.

## Camera API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /REST/site/{site_id}/channel | GET | List all cameras/channels |
| /REST/site/{site_id}/channel/{channel_id}/snap | GET | Get camera snapshot |

### Snapshot Response Format

```json
{
  "status": 2000,
  "code": 200,
  "result": [
    {
      "content": [-1, -40, -1, -32, ...]
    }
  ]
}
```

- First two bytes `[-1, -40]` = `0xFF 0xD8` = JPEG signature

## Channel ID Assignment

Channel IDs appear to be assigned sequentially based on the order cameras are authenticated/added to the site.

## Camera Inventory (Site 110 - QA Lab)

| Channel | Name | Brand |
|---------|------|-------|
| 1 | Axis_3 | Axis |
| 2-4 | Avigilon-Multi_1.1-1.3 | Avigilon |
| 5 | Avigilon-Thermal | Avigilon |
| 6-8 | Hanwha_5, _6, _Encoder_27 | Hanwha |
| 9 | Advidia (Internal Audio) | ONVIF |
| 10 | Axis_4 | Axis |
| 11 | IPRO-Internal Mic | i-Pro |
| 12-15 | Hanwha_3, _2, _PTZ, _Fisheye | Hanwha |
| 16 | Vivotek_1 | ONVIF |
| 17-22 | Hanwha_7, _Multi_1.1-1.4, _8 | Hanwha |
| 23-24 | Axis_1, _2 | Axis |
| 25 | Avigilon Video Intercom | Avigilon |

## Discovery & Dynamic Environments

The test suite supports dynamic camera/site topologies via a `DiscoveryHelper`.
It attempts to discover sites and channels at session startup and prefers channels
that expose a `snapUrl` (snapshot-capable). Discovery is cached for the test
session to avoid repeated API calls.

CLI tool: `tools/discover_cameras.py` can be used to inspect a site's cameras and
their snapshot capability.

Usage:

```powershell
python tools/discover_cameras.py --env qa
python tools/discover_cameras.py --env staging --site 120
```

Tests adapt automatically when cameras are added/removed; the `test_channel_ids`
fixture picks snapshot-capable channels first, then falls back to any channel
ids discovered for the site.

## HTTP exchanges in failure reports

When an internal-suite test fails, the HTML report and the terminal output
show the HTTP calls that led to the failure, not only the assertion.

- `BaseAPIClient` (`api_clients/base_api_client.py`) keeps the last 20
  exchanges per client: method, URL, status, elapsed ms, request body, and
  the first 500 chars of the response body.
- `tests/internal_api/conftest.py` clears that log at the start of each
  test. If the test fails in its call phase, the hook adds an
  "HTTP exchanges" block to the test's row in the pytest-html report and an
  "HTTP exchanges" section to the terminal failure output.
- A passing test carries no block. Calls made with `requests` directly
  (for example in `test_auth_apis.py`) are not logged.

Example block:

```
1. POST https://qa.example.invalid/v-apiserver/REST/central/user/login -> 200 (412 ms)
   request: {"accountid": "qa@example.com", "username": "Example Label", "password": "***"}
   response: {"status": 2002, "code": 200, "result": [{"JSESSIONID": "***"}]}
2. GET https://qa.example.invalid/v-apiserver/REST/central/user/session -> 200 (95 ms)
   response: {"status": 2000, "code": 200, "result": [{"userId": "qa@example.com", ...
```

Masked before storage, in both request and response text: values of keys
that contain password, passwd, pwd, token, secret, jsessionid, authorization,
cookie, api key, or vsaas-key. `JSESSIONID=...` in a URL or cookie string.
Any bare SHA512 hex digest (the form the login password travels in). Bodies
longer than 500 chars are cut and end with `... [N chars total]`. Image and
binary responses show only the content type and byte count.

The log is in memory only. It never reaches `logs/api_requests.log`.
