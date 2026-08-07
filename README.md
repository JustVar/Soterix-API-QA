# Soterix API - QA

API test automation for the Soterix VSaaS platform. This repo covers **both**
API surfaces - the internal `/v-apiserver` API (everything the web app does)
and the third-party `/v-integration-api` (key-auth, read-only).
Full contracts, environments, and known-good test data: **`docs/API_SURFACES.md`**.

UI automation and manual test cases live in the sibling repo
**Soterix-WebApp-QA**. The two suites share nothing at run time - this repo is
deliberately **browser-free**: no Playwright, no captcha, no UI login. A full
run installs in seconds and launches no browser.

## Quickstart

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.template .env      # then fill in credentials
venv\Scripts\pytest tests\ -q
```

If login fails, **read the error** - it says which of the three things is wrong:

| Error | Meaning | Fix |
|---|---|---|
| "No account ... exists on ..." | credential belongs to a different environment | check `QA_USER` / `ENV` |
| "... exists but the password was rejected" | stored password is stale | refresh it in `.env` |
| "Could not reach the API at ..." | wrong host / no network | check `config/env/`, VPN |

## Layout

```
api_clients/        HTTP clients (auth, cameras, dashboard, search, users, discovery)
config/             env configs (qa/stage/prod) + QA Touch case mapping
docs/               API_SURFACES.md (start here), endpoint catalog, testing notes
plugins/            QA Touch result reporter (dormant unless --qatouch-upload)
schemas/            OpenAPI snapshots + response schemas used for validation
tests/smoke/        internal-API smoke suite
tests/integration_api/  scaffold for the /v-integration-api surface (pending key)
tests/plugins/      unit tests for the reporter plugin
tools/              discovery + QA Touch client utilities
```

## Environments

Select with `ENV=qa|stage|prod` (default `qa`). Hosts are defined in
`config/env/*.py`; credentials come from `.env` (see `.env.template` - the
variable ordering comment there matters).

## QA Touch reporting (opt-in)

Results upload only when explicitly armed:

```powershell
pytest --qatouch-upload --qatouch-run <RUN_KEY> tests\
```

Case mappings live in `config/qatouch_case_mapping.json` - **never** in test
files.
