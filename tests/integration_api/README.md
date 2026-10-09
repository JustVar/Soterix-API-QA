# Integration API tests

Target: the third-party surface at `/v-integration-api`, with GET endpoints
authenticated by a static `x-vsaas-key` header. The Swagger UI is the source
of truth for the endpoint list (it grows over time):
`<integration_api_base_url>/swagger-ui/index.html`, with
`integration_api_base_url` from `config/env/qa.py`.

Status: **built** (17 tests). The suite skips all 17 while
`VSAAS_INTEGRATION_KEY` is empty, so 17 skips mean the key is missing, not
that the surface passed.

- `test_endpoint_sweep.py`: every documented endpoint, one row each in
  `data/endpoints.py`, checked against its observed response contract
  (data list, portal pointer, or stream session). New endpoint in the
  swagger = one new catalogue row.
- `test_auth.py`: the auth boundary (no key, bogus key, empty key all
  answer 401 with the stable status-9581 error body).
- The key create/disable/enable/delete lifecycle lives in
  `tests/internal_api/test_api_integration_key_apis.py`, because key
  management is an internal-API feature. Only key USE belongs here.

The suite authenticates with the QA tenant key named
**"QA Automation - DO NOT DELETE"** (Admin > Integrations > API
Integration). Store its value as `VSAAS_INTEGRATION_KEY` in `.env`. The
suite skips cleanly on machines without it.

## Where everything goes

The whole build-out lives in this directory. That is what keeps the two
suites in this repo from breaking each other:

- Fixtures: `tests/integration_api/conftest.py` (already started). Never add
  fixtures to the root `conftest.py`.
- Client code: `tests/integration_api/client.py` (create it when needed). A
  client here is a `requests.Session` with one header. The
  `integration_session` fixture may be all you ever need.
- Tests: `tests/integration_api/test_*.py`. Mark them
  `@pytest.mark.integration` (registered in `pytest.ini`).
- Config: the base URL is `integration_api_base_url` in
  `config/env/qa.py`. The key comes from `VSAAS_INTEGRATION_KEY` in `.env`
  (slot exists in `.env.template`).

With that layout, building this suite touches zero shared files, and the
internal suite's plumbing cannot break your runs.

## What NOT to reuse

- `api_clients/auth_helper.py`: internal `/v-apiserver` login (session
  cookie, expiry). This surface has no session and no login.
- `api_clients/base_api_client.py`: also internal-only, two ways. It
  force-appends `/v-apiserver` to any base URL. Its headers speak only
  JSESSIONID-cookie or Bearer (a hex key passed as `token` would be sent as
  a session cookie). Do not subclass it and do not edit it to fit.
  Every internal test depends on its current behavior.

## Conventions

- Missing key or absent surface means **skip, not fail**. The fixtures in
  `conftest.py` already do this. Keep that behavior so whole-tree runs stay
  green on machines without the key. Treat an empty env var as unset.
- Do not invent a new `ENV` value for this surface (it breaks the shared
  config for everyone). Gate on `env_config.get("integration_api_base_url")`
  instead. It is `None` on a server that does not deploy the surface.
- Run only this suite while building:
  `pytest tests/integration_api --html=reports/integration.html --self-contained-html`.
  A bare `pytest` also runs the internal suite, which needs credentials you
  do not have and sends live traffic to the shared QA tenant.
- The root `conftest.py` defines `env_config` and `base_url` for every
  suite. Those two names are taken, so name your fixtures distinctly.
- QA Touch mapping is optional and lives in
  `config/qatouch_case_mapping.json` (hand-edited, never markers in test
  files). Add entries only when you want results uploaded.

## Surface notes

- Not every server deploys the surface. The `integration_base_url`
  fixture skips the suite when `integration_api_base_url` is `None`.
- Endpoints are read-only GETs today, so tests are safe against any
  server that exposes the surface. That claim has an expiry date: the
  platform plans endpoints where a partner writes badge events into the
  platform. Re-check before assuming a new endpoint is safe to hit.
- Merging your work back: branch, pull request, never force-push `main`
  (`docs/CONVENTIONS.md`).
