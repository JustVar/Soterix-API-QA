# Soterix API - QA

## What this repo does

This repo tests the APIs of the Soterix VSaaS platform with HTTP requests.
It uses no browser. A test sends a request, then checks the status, the
shape and the content of the answer.

## How it works

1. The tests are Python. pytest runs them, and the `requests` library sends
   the calls. A full run installs in seconds.
2. The platform has 2 API surfaces, and each one has its own suite, its own
   login and its own credentials in `.env`. One suite can break and the
   other still runs.
3. The internal suite signs in one time for each run and keeps the session
   cookie. The clients in `api_clients/` hold the endpoints, so a change in
   the API is corrected in 1 place.
4. Each run keeps its evidence and its report page the same way as the
   WebApp repo. The shared package `soterix-qa-shared` supplies that code.
5. The upload of results to QA Touch is optional and off by default.

## The 2 suites

| Suite | Surface | Auth | Credentials |
|---|---|---|---|
| `tests/internal_api/` | internal `/v-apiserver` (everything the web app does) | session cookie | `QA_USER` / `QA_PASSWORD` |
| `tests/integration_api/` | third-party `/v-integration-api` (partner API) | static `x-vsaas-key` header | `VSAAS_INTEGRATION_KEY` |

One naming trap, worth stating once: **"Integration API" names the partner
product surface** (`/v-integration-api`), not the test level. End-to-end
tests of internal endpoints are internal-suite work and live in
`tests/internal_api/`, whatever their depth. When someone says "integration
tests", ask which of the two they mean.

Full contracts, environments, and known-good test data: **`docs/API_SURFACES.md`**.
Every internal endpoint found or tested, with request and response shapes:
**`docs/INTERNAL_API_INVENTORY.md`**.
To build out the integration suite, start at **`tests/integration_api/README.md`**.
It says where code goes and what not to reuse.

UI automation and manual test cases live in the sibling repo
**Soterix-WebApp-QA**. The two repos share nothing at run time. This repo is
deliberately **browser-free**: no Playwright, no captcha, no UI login. A full
run installs in seconds and launches no browser.

## Quickstart

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.template .env      # then fill in credentials
```

That is the whole setup. `requirements.txt` pulls in the shared QA pipeline
(`soterix-qa-shared`) for you, over HTTPS, using the same GitHub login your
`git clone` used. You need read access to that repo, which is granted
separately from this one: if pip reports a 404, ask for it rather than
hunting for a token. `plugins/` and `tools/` here are thin shims over that
package, so nothing collects without it.

**Only if you need to change the shared package**, clone it beside this repo
and install it editable. That overrides the pinned copy until you reinstall:

```powershell
cd ..
git clone https://github.com/Soterix-Systems/SOTERIX-QA-SHARED.git soterix-qa-shared
cd Soterix-API-QA
venv\Scripts\pip install -e ..\soterix-qa-shared
```

Most people never need this.

Run the suite you are working on, not the whole tree. The two suites need
different credentials, and a bare `pytest` errors on whichever one you lack:

```powershell
# Internal /v-apiserver suite (needs QA_USER/QA_PASSWORD)
venv\Scripts\pytest tests\internal_api --html=reports/internal.html --self-contained-html

# Third-party /v-integration-api suite (needs VSAAS_INTEGRATION_KEY, skips without it)
venv\Scripts\pytest tests\integration_api --html=reports/integration.html --self-contained-html

# Reporter plugin unit tests (offline, no credentials)
venv\Scripts\pytest tests\plugins
```

Before pushing, prove you broke no other suite's wiring. These checks need
no credentials, and CI runs the same ones via
`.github/workflows/collect-gate.yml`:

```powershell
venv\Scripts\pytest --collect-only
venv\Scripts\pytest --setup-plan
```

If internal-suite login fails, **read the error**. It says which of the
three things is wrong:

| Error | Meaning | Fix |
|---|---|---|
| "No account ... exists on ..." | credential belongs to a different environment | check `QA_USER` / `ENV` |
| "... exists but the password was rejected" | stored password is stale | refresh it in `.env` |
| "Could not reach the API at ..." | wrong host / no network | check `config/env/`, VPN |

## Layout

```
.github/workflows/  collect-gate CI: imports + fixture wiring on every push/PR
api_clients/        internal-suite HTTP clients (auth, cameras, locations, bookmarks, dashboard, search, users)
config/             env configs (qa/stage/prod) + QA Touch case mapping
docs/               API_SURFACES.md (start here), INTERNAL_API_INVENTORY.md, endpoint catalog, MERGE_RUNBOOK.md
plugins/            QA Touch result reporter (dormant unless --qatouch-upload)
schemas/            OpenAPI snapshots + response schemas used for validation
tests/internal_api/     internal-API suite (fixtures in its conftest.py)
tests/integration_api/  integration-API suite (17 tests; key auth, endpoint sweep)
tests/plugins/      unit tests for the reporter plugin
tools/              discovery + QA Touch client utilities
```

The isolation rules: each suite keeps its fixtures in its own `conftest.py`.
The root `conftest.py` carries only what every suite shares (`env_config`,
`base_url`). `api_clients/` (`BaseAPIClient` included) belongs to the
internal suite alone. That is what lets either suite break without taking
the other down.

## Environments

Select with `ENV=qa|stage|prod` (default `qa`). Hosts are defined in
`config/env/*.py`. Credentials come from `.env`, copied from `.env.template`. The integration surface
exists on QA only: its base URL is the `integration_api_base_url` key, which
is `None` on stage/prod so integration tests skip there. Do not invent new
`ENV` values. Add config keys instead.

## Contributing Across the Two Remotes

This repo lives in two GitHub orgs (JustVar + Soterix-Systems). All merges
follow **`docs/MERGE_RUNBOOK.md`**. The two rules everyone must know:

1. **On a fresh clone**, run `git rev-list --max-parents=0 HEAD` first. It must
   print `92aadd1a9458f3d7fed0efb80f05f046d1142b2f`. Anything else means the
   clone is on dead pre-cleanup history, and the runbook has the recovery.
2. **Nobody force-pushes `main`.** Branch protection is unavailable on the
   current GitHub plan, so this rule is the protection.

Team changes go through a feature branch and a PR on Soterix-Systems.

## QA Touch Reporting (Opt-in)

Results upload only when explicitly armed:

```powershell
pytest --qatouch-upload --qatouch-run <RUN_KEY> tests\
```

Case mappings live in `config/qatouch_case_mapping.json` (hand-edited),
**never** in test files.

## After a Run

One question, one place. Statuses of record live in the QA Touch run when
the run was armed. Failure detail lives in the per-suite HTML report
(`reports/internal.html` / `reports/integration.html`) plus the HTTP
exchange log each failed test prints. Long-term history lives in
`history/*.jsonl`, committed. Defects live in Jira, filed by a person.

A manual or debug run uploads nothing and ledgers nothing: run it, read
the report, iterate, done. Arm a run only when it is an official check.

The team-wide viewing plan (nginx on spartan1 serving run evidence, the
self-hosted runner beside it, retention) is decided and documented once,
in the WebApp repo: `Soterix-WebApp-QA/docs/RUN_WORKFLOWS.md`. This repo's
runs are browser-free, so its evidence is smaller, but it follows the same
model.

### If spartan1 is down

The merge gate runs on spartan1, which costs no Actions minutes. If the box
is off, a push has no runner, so the gate waits instead of failing. That
looks like a hang and is not one.

Send it back to GitHub's machines either way:

- Set the repository variable `CI_RUNNER` to `hosted`. It applies to every
  event, a push included, and it stays set until somebody removes it.
- Or start the workflow by hand from the Actions tab with `hosted` ticked. A
  dispatch input is null on an automatic event, so this one covers a single
  run.

Remove the variable when the box is back, or every run bills minutes again:

```bash
gh variable delete CI_RUNNER -R Soterix-Systems/Soterix-API-QA
```
