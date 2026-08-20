# Soterix API - QA

API test automation for the Soterix VSaaS platform. This repo carries **two
isolated suites**, one per API surface:

| Suite | Surface | Auth | Credentials |
|---|---|---|---|
| `tests/internal_api/` | internal `/v-apiserver` (everything the web app does) | session cookie | `QA_USER` / `QA_PASSWORD` |
| `tests/integration_api/` | third-party `/v-integration-api` (partner API) | static `x-vsaas-key` header | `VSAAS_INTEGRATION_KEY` |

Full contracts, environments, and known-good test data: **`docs/API_SURFACES.md`**.
Building out the integration suite? Start at **`tests/integration_api/README.md`** -
it says where code goes and what not to reuse.

UI automation and manual test cases live in the sibling repo
**Soterix-WebApp-QA**. The two repos share nothing at run time - this repo is
deliberately **browser-free**: no Playwright, no captcha, no UI login. A full
run installs in seconds and launches no browser.

## Quickstart

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.template .env      # then fill in credentials
```

Run the suite you are working on, not the whole tree - the two suites need
different credentials, so a bare `pytest` errors on whichever one you lack:

```powershell
# Internal /v-apiserver suite (needs QA_USER/QA_PASSWORD)
venv\Scripts\pytest tests\internal_api --html=reports/internal.html --self-contained-html

# Third-party /v-integration-api suite (needs VSAAS_INTEGRATION_KEY; skips without it)
venv\Scripts\pytest tests\integration_api --html=reports/integration.html --self-contained-html

# Reporter plugin unit tests (offline, no credentials)
venv\Scripts\pytest tests\plugins
```

Before pushing, prove you broke no other suite's wiring (no credentials
needed; CI runs the same checks via `.github/workflows/collect-gate.yml`):

```powershell
venv\Scripts\pytest tests\ --collect-only -q
venv\Scripts\pytest tests\ --setup-plan -q
```

If internal-suite login fails, **read the error** - it says which of the
three things is wrong:

| Error | Meaning | Fix |
|---|---|---|
| "No account ... exists on ..." | credential belongs to a different environment | check `QA_USER` / `ENV` |
| "... exists but the password was rejected" | stored password is stale | refresh it in `.env` |
| "Could not reach the API at ..." | wrong host / no network | check `config/env/`, VPN |

## Layout

```
.github/workflows/  collect-gate CI: imports + fixture wiring on every push/PR
api_clients/        internal-suite HTTP clients (auth, cameras, dashboard, search, users)
config/             env configs (qa/stage/prod) + QA Touch case mapping
docs/               API_SURFACES.md (start here), endpoint catalog, MERGE_RUNBOOK.md
plugins/            QA Touch result reporter (dormant unless --qatouch-upload)
qa/                 doc_registry.yaml (test-to-doc mapping)
schemas/            OpenAPI snapshots + response schemas used for validation
tests/internal_api/        internal-API suite (fixtures in its conftest.py)
tests/integration_api/  integration-API suite (fixtures in its conftest.py; pending key)
tests/plugins/      unit tests for the reporter plugin
tools/              discovery + QA Touch client utilities
```

The isolation rules, in one breath: each suite keeps its fixtures in its own
`conftest.py`; the root `conftest.py` carries only what every suite shares
(`env_config`, `base_url`); `api_clients/` - `BaseAPIClient` included -
belongs to the internal suite alone. That is what lets either suite break
without taking the other down.

## Environments

Select with `ENV=qa|stage|prod` (default `qa`). Hosts are defined in
`config/env/*.py`; credentials come from `.env` (see `.env.template` - the
variable ordering comment there matters). The integration surface exists on
QA only: its base URL is the `integration_api_base_url` key, which is `None`
on stage/prod so integration tests skip there. Do not invent new `ENV`
values - add config keys instead.

## Contributing across the two remotes

This repo lives in two GitHub orgs (JustVar + Soterix-Systems). All merges
follow **`docs/MERGE_RUNBOOK.md`**. The two rules everyone must know:

1. **Fresh clone?** Run `git rev-list --max-parents=0 HEAD` first - it must
   print `92aadd1a9458f3d7fed0efb80f05f046d1142b2f`. Anything else means the
   clone is on dead pre-cleanup history; the runbook has the recovery.
2. **Nobody force-pushes `main`.** Branch protection is unavailable on the
   current GitHub plan, so this rule is the protection.

Team changes go through a feature branch and a PR on Soterix-Systems.

## QA Touch reporting (opt-in)

Results upload only when explicitly armed:

```powershell
pytest --qatouch-upload --qatouch-run <RUN_KEY> tests\
```

Case mappings live in `config/qatouch_case_mapping.json` (hand-edited) -
**never** in test files.
