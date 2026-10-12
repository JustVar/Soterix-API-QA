# Soterix API - QA

## About this repo

API test automation for the VSaaS platform behind NexaiQ-Core, the web app of
Soterix Systems, an AI video-surveillance SaaS company. Built by Justin
Varughese, System Platform QA/QC Manager.

- 52 functional tests of the internal API, a sweep of 101 read endpoints
  (67 checked for a 200 answer and valid JSON, 34 skipped with the
  measured reason) and 17 tests of the partner API.
- 83 internal endpoints documented from the live system, each with the date
  it was last confirmed. These are the endpoints the clients and the
  functional tests use, with their request and response shapes; the
  sweep's list is separate
  ([docs/INTERNAL_API_INVENTORY.md](docs/INTERNAL_API_INVENTORY.md)).
- Where to start:
  - The login triage ([api_clients/auth_helper.py](api_clients/auth_helper.py)),
    which tells an unknown account, a stale password and an unreachable server
    apart and names the fix.
  - The skip list ([tests/internal_api/data/endpoints.py](tests/internal_api/data/endpoints.py)),
    where every endpoint the sweep skips says where and when the failure was
    measured.
  - The HTTP exchange log
    ([api_clients/base_api_client.py](api_clients/base_api_client.py)), which
    attaches the masked requests and answers to every failed test.
- Built with AI coding agents (Claude Code, OpenAI Codex, Microsoft 365
  Copilot) under the rules in [AGENTS.md](AGENTS.md).
- To see it run: follow the first 4 setup commands below, then run
  `venv\Scripts\python.exe -m pytest tests/plugins tests/internal_api/test_data_choice.py tests/internal_api/test_http_exchange_log.py tests/internal_api/test_auth_cache.py tests/internal_api/test_login_label.py`
  (`venv/bin/python` on Mac or Linux). These 47 tests need no server.
- The case study that covers all three repos:
  [qa-automation-case-study](https://github.com/JustVar/qa-automation-case-study).
  Its [Terms](https://github.com/JustVar/qa-automation-case-study#terms)
  section explains the words these READMEs use.
- The two sibling repos:
  [Soterix-WebApp-QA](https://github.com/JustVar/Soterix-WebApp-QA) and
  [SOTERIX-QA-SHARED](https://github.com/JustVar/SOTERIX-QA-SHARED).
- Running it today: Soterix has since closed and its QA server is gone, so
  the API tests have nothing to run against. The offline tests above still
  run on any machine. CI ran on the company's copies of these repos and is
  switched off here.

## What this repo does

This repo tests the APIs of the Soterix VSaaS platform with HTTP requests
against one QA server. It uses no browser. A test sends a request, then
checks the status, the shape and the content of the answer.

## How it works

1. The tests are Python. pytest runs them, and the `requests` library sends
   the calls.
2. The platform has 2 API surfaces. Each one has its own suite, its own
   login and its own credential in `.env`. One suite can break and the
   other still runs.
3. The internal suite signs in one time for each run and keeps the session
   cookie. The clients in `api_clients/` hold the endpoints, so a change in
   the API is corrected in 1 place.
4. Each run writes its evidence and its report page under `reports/runs/`
   on the machine that ran it. The shared package `soterix-qa-shared`
   supplies that code. It installs from the wheel under `vendor/`.
5. The upload of results to QA Touch is optional and off by default.

## The 2 suites

| Suite | Surface | Auth | Credential in `.env` |
|---|---|---|---|
| `tests/internal_api/` | internal `/v-apiserver` (everything the web app does) | session cookie | `QA_USER` / `QA_PASSWORD` |
| `tests/integration_api/` | third-party `/v-integration-api` (partner API) | static `x-vsaas-key` header | `VSAAS_INTEGRATION_KEY` |

"Integration API" names the partner product surface (`/v-integration-api`),
not the test level. End-to-end tests of internal endpoints are internal-suite
work and live in `tests/internal_api/`. When someone says "integration
tests", ask which of the two they mean.

The auth contracts and the test-data rules: `docs/API_SURFACES.md`.
Every internal endpoint found or tested, with request and response shapes:
`docs/INTERNAL_API_INVENTORY.md`.
To extend the integration suite, start at `tests/integration_api/README.md`.

UI automation lives in the sibling repo Soterix-WebApp-QA. The two repos
share nothing at run time. This repo stays browser-free: no Playwright, no
captcha, no UI login.

## Setup

Python 3.14. 5 commands. They are for Windows PowerShell. On Mac or Linux,
clone to any path, use `venv/bin/python` wherever a command says
`venv\Scripts\python.exe`, and use `cp` instead of `copy`.

```powershell
git clone https://github.com/JustVar/Soterix-API-QA.git C:\qa\api-qa
cd C:\qa\api-qa
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.template .env
```

`pip install` takes about 1 minute and asks for no credential. The shared
package comes from `vendor/`, so no other repository access is needed.

Then fill 3 lines in `.env`:

```
QA_USER=               the account the tests sign in as
QA_PASSWORD=
LOGIN_USERNAME_LABEL=  the fixed label the web app sends with every login
```

Leave every other line as it is.

The server and the test data live in one file, `config/env/qa.py`:
`base_url`, `api_base_url`, `integration_api_base_url`, `test_site_name`
and `test_camera_name`. The server in that file is a placeholder
(`qa.example.invalid`): set the keys to the server you test. The file's header lists them. `test_site_name` and
`test_camera_name` may stay blank: the run then uses the first site by
name that has a camera, and the first camera by name on it, and prints
the choice. A name that is set is checked, never replaced. To see the
sites and the cameras the account can see, run
`venv\Scripts\python.exe tools\discover_cameras.py`.

## The first run

One test. It signs in, then reads the camera tree of the test site:

```powershell
venv\Scripts\python.exe -m pytest tests\internal_api\test_camera_apis.py::test_get_camera_tree
```

The last line prints `1 passed`. The run's page is
`reports\runs\<run>\run.html`, and `reports\runs\index.html` lists every
run on this machine. Open the run page. A failed test shows its error and
the HTTP exchanges that led to it. A skipped test shows its reason.
"skipped" is not "passed".

If login fails, read the error. It says which of 3 things is wrong. A
blank `LOGIN_USERNAME_LABEL` stops the run before the request with a
message that names it.

| Error | Meaning | Fix |
|---|---|---|
| "No account ... exists on ..." | the account is not on this server | check `QA_USER` in `.env` and `base_url` in `config/env/qa.py` |
| "... exists but the password was rejected" | the stored password is stale | refresh it in `.env` |
| "Could not reach the API at ..." | wrong host or no network | check `base_url`, the VPN |

Then the suites:

```powershell
# Internal /v-apiserver suite (needs QA_USER/QA_PASSWORD)
venv\Scripts\python.exe -m pytest tests\internal_api

# Third-party /v-integration-api suite (needs VSAAS_INTEGRATION_KEY)
venv\Scripts\python.exe -m pytest tests\integration_api

# Offline checks (no credentials)
venv\Scripts\python.exe -m pytest tests\plugins
```

Run the suite you work on, not the whole tree. A bare `pytest` runs both
suites and errors on the credential you lack. The integration suite skips
all 17 tests while `VSAAS_INTEGRATION_KEY` is empty: 17 skips there mean
the key is missing, not that the surface passed.

The endpoint sweep in `tests/internal_api/test_get_endpoints_sweep.py` skips
the endpoints listed in `tests/internal_api/data/endpoints.py`
(`KNOWN_LIMITATIONS`). Every reason there says it was measured on the
company's QA server and in which month (`_MEASURED` in that file). On a
new server, delete a row, run the sweep, and keep the row only if the
endpoint still fails for the stated reason.

## TLS

The clients do not verify the server certificate unless `SSL_VERIFY=true`
is in `.env`. The QA server's certificate has not been proven from a
clean machine. Set it to true on a server with a certificate a public CA
signed, and a failed handshake then reads as "Could not reach the API".

## Before you push: the collect gate

The workflow `.github/workflows/collect-gate.yml` runs these checks on
GitHub's machines with no secret. It is switched off on this copy, so run
the same commands by hand. They prove the wiring, not the surface:

1. `pytest --collect-only` and `pytest --setup-plan`: every import and
   fixture resolves. No test runs.
2. `python tools/collect_floor.py`: the collected count per suite did not
   drop below `config/collect_floor.json`. If you removed tests on
   purpose, run `python tools/collect_floor.py --update` and say why in
   the commit message.
3. `pytest tests/plugins`, then the 4 offline files of the internal suite
   (the command under "About this repo"): the shim guards, the
   shared-package pin, and the client code with its HTTP calls stubbed.
4. `pytest tests/integration_api`: self-skipping without the key.
5. `python -m ruff check .`

Run the same commands with `venv\Scripts\python.exe -m` before you push.
Work on a branch and open a pull request. Never force-push `main`.

## Layout

```
.github/workflows/  collect-gate CI (imports, fixture wiring, floor, lint)
api_clients/        internal-suite HTTP clients (auth, cameras, locations, bookmarks, dashboard, search, users), the TLS rule (tls.py), the site and camera choice (data_choice.py)
config/             config/env/qa.py (the server), the collect floor, the QA Touch case mapping
docs/               API_SURFACES.md (start here), INTERNAL_API_INVENTORY.md, endpoint catalog, ARCHIVE.md
plugins/            shims over the shared package: run archive, QA Touch reporter
schemas/            OpenAPI snapshot of the QA server: a reference for paths and request bodies (docs/API_SURFACES.md says why it cannot check a response)
tests/internal_api/     internal-API suite (fixtures in its conftest.py)
tests/integration_api/  integration-API suite (key auth, endpoint sweep)
tests/plugins/      offline pins: shim guards, shared-package pin
tools/              discover_cameras.py, download_openapi_spec.py, api_usage.py, collect_floor.py
vendor/             the shared package wheel that requirements.txt installs
```

Each suite keeps its fixtures in its own `conftest.py`. The root
`conftest.py` carries only what every suite shares (`env_config`,
`base_url`). `api_clients/` belongs to the internal suite alone. That is
what lets either suite break without taking the other down.

A second server is a copy of `config/env/qa.py` under
`config/env/<name>.py`, selected with `ENV=<name>` in `.env`. Do not add
config keys anywhere else.

## QA Touch upload (opt-in)

Results upload only when a run is armed:

```powershell
venv\Scripts\python.exe -m pytest --qatouch-upload --qatouch-run <RUN_KEY> tests\
```

It needs `QATOUCH_API_KEY`, `QATOUCH_DOMAIN` and `QATOUCH_PROJECT_ID` in
`.env`. Case mappings live in `config/qatouch_case_mapping.json`, hand
edited, never in test files. Only rows marked `reviewed: true` upload.

## Where the results are

Failure detail is in the run page, `reports/runs/<run>/run.html`, with the
HTTP exchanges each failed test made. `reports/runs/index.html` lists every
run on this machine. Defects go to Jira, filed by a person.

What left this repo and how to get it back: `docs/ARCHIVE.md`.
