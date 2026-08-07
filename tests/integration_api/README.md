# Integration API tests (scaffold)

Target: the third-party surface at `/v-integration-api` - read-only GET
endpoints authenticated by a static `x-vsaas-key` header. The Swagger UI is
the source of truth for the endpoint list (it grows over time):
<https://qa.example.invalid/v-integration-api/swagger-ui/index.html>

Status: **not built yet.** Blocked on an API key being issued - store it as
`VSAAS_INTEGRATION_KEY` in `.env` when it arrives.

Notes for whoever builds this out:

- No session, no login, no expiry: a client here is a `requests.Session` with
  one header. Don't reuse `api_clients/auth_helper.py` - it's for the internal
  `/v-apiserver` surface.
- The surface exists on QA only (stage/prod 404 as of 2026-08-05) - gate tests
  accordingly.
- All endpoints are read-only, so these tests are safe against any environment
  that exposes the surface.
