# Bruno - API Exploration Guide for QA

This guide explains what Bruno is, why we use it alongside the pytest suite, and how to drive the Soterix VSaaS REST API with it.

## Summary

- **pytest runs the automated API tests.** No external tool needed at test runtime.
- **Bruno is for humans** - interactive poking, response inspection, sharing endpoint collections, prototyping a request before promoting it into a pytest test.
- Bruno collections live as **plain files in the repo** (no cloud account, no sync drift). Anyone can clone the repo and open the collection.

## Why Bruno instead of Postman or Insomnia?

| Concern | Bruno | Postman | Insomnia |
|---|---|---|---|
| Collections stored as files | yes: `.bru` files in git | no: Cloud sync (free tier limited) | partial: Partial |
| Works fully offline | yes: | no: requires sign-in | partial: |
| Per-env vars in repo | yes: | partial: in cloud | partial: |
| Free for teams | yes: open source | no: paid tiers above 3 users | no: paid tiers |
| Code-review friendly | yes: diff plain text | no: binary export | no: |

If your team is already deep into Postman, Postman is fine - the workflow below maps 1:1. We just don't want a cloud login to be a prerequisite for running a smoke test interactively.

## Install

- **Desktop app:** download from <https://www.usebruno.com/downloads>.
- **CLI (optional, for CI):** `npm install -g @usebruno/cli` - run a Bruno collection from the command line, useful for ad-hoc smoke runs outside pytest.

## Where the collection lives

```
tests/bruno/
├── bruno.json              # collection manifest
├── environments/
│   └── qa.bru              # base_url from config/env/qa.py
├── Auth/
│   ├── Login.bru
│   └── Get Session.bru
├── Sites/
│   ├── Get Site Details.bru
│   ├── Enterprise Site Details.bru
│   └── Edge Version Latest.bru
├── Rules/
│   └── Rule Search.bru
├── Events/
│   └── Site Search Event.bru
└── Licenses/
    ├── Available.bru
    ├── Assigned.bru
    └── Overview.bru
```

The collection is **not yet committed** - see "Bootstrapping the collection" below.

## Bootstrapping the collection (one-time, ~15 minutes)

1. Open Bruno -> **Create Collection** -> choose `tests/bruno/` inside this repo.
2. **Add an environment** named `qa`:
   - `baseUrl` = the `api_base_url` value in `config/env/qa.py`
   - `enterpriseId` = `1`
   - `username` = your QA account email
3. A second server is a second environment with its own `baseUrl`.
4. Add a **Pre-request script** at the collection level that logs in and stores `JSESSIONID`:

   ```js
   // tests/bruno/scripts/login.js (pseudo - adapt to Bruno scripting syntax)
   const res = await bru.fetch({
     url: `${bru.env.baseUrl}/REST/central/user/auth/login`,
     method: "POST",
     body: { username: bru.env.username, password: bru.getEnvVar("password") }
   });
   const cookie = res.headers["set-cookie"]?.match(/JSESSIONID=([^;]+)/)?.[1];
   bru.setEnvVar("JSESSIONID", cookie);
   ```

5. Add **collection-level headers**: `Cookie: JSESSIONID={{JSESSIONID}}` and `Accept: application/json`.
6. Save & commit the collection (commit `.bru` files. Do NOT commit a passwords file. Use Bruno's secret env vars or a local `.env.local`).

## Day-to-day workflow

### Exploring a new endpoint before writing a test

1. **Capture the request from the SPA** - open Chrome DevTools, navigate to the feature, copy the request as a fetch from the Network panel.
2. **Paste into Bruno** -> New Request -> Paste as cURL/fetch.
3. **Replace hardcoded values** with `{{baseUrl}}`, `{{enterpriseId}}`, `{{siteId}}` etc.
4. **Send** - confirm 200 + sane response shape.
5. **Save under the appropriate folder** (Auth, Sites, Rules...) so others can re-use it.
6. **Promote to a smoke test** - copy the path, method, and payload shape into a new `test_<area>_apis.py` in `tests/internal_api/`. See `docs/API_ENDPOINTS.md` for the master endpoint catalog.

### Debugging a failing smoke test

1. Find the failing endpoint in `docs/API_ENDPOINTS.md`.
2. Open the matching Bruno request, hit Send.
3. If Bruno succeeds but pytest fails -> check the headers, body and content-type the client in `api_clients/` sends.
4. If Bruno also fails -> server-side problem. Capture the response and file it in Jira.

### Sharing a repro with the platform team

1. Reproduce the failing call in Bruno.
2. Export the single request: right-click -> **Export as cURL**.
3. Paste into the bug ticket. Anyone with credentials can reproduce.

## Important rules

1. **Never commit credentials.** Use Bruno's secret env vars or a gitignored `.env.local`. The `.bru` files in `environments/` should only contain non-secret host URLs and enterprise IDs.
2. **Do not run destructive requests against a server you do not own.** Bruno has no guardrails. The pytest suite has `allow_write` and `allow_delete` in `config/env/`. Bruno has neither.
3. **Keep the collection aligned with `docs/API_ENDPOINTS.md`.** When you add a Bruno request, add or update the corresponding row in the endpoint catalog so the two stay in sync.
4. **Bruno is exploratory, the pytest suite is authoritative.** A green Bruno request does not count as test coverage - only a smoke test in `tests/internal_api/` does.

## What about running Bruno in CI?

We don't, currently. CI runs the pytest collect-gate. Bruno's CLI (`bru run`) could shadow-run the collection in CI as a smoke-of-the-smoke, but that's redundant - if the pytest suite passes, Bruno would too. Skip unless we hit a specific need.

## Alternatives if Bruno isn't for you

- **Hoppscotch** (web app) - fast, no install, no auth required, but no checked-in collection.
- **Thunder Client** (VS Code extension) - collections are JSON files, lives in `.vscode/`.
- **HTTPie / curl** - no UI, no collection management, but fine for one-off pokes from a terminal.
- **Postman** - works, but cloud sign-in is friction for new teammates.

## Related docs

- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - master catalog of every observed endpoint + smoke coverage status
- [API_SURFACES.md](./API_SURFACES.md) - the auth contracts and the test-data rules
- `api_clients/base_api_client.py` - the requests-based client the internal-API tests extend
