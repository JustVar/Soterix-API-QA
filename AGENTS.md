# Soterix-API-QA - guidance for AI coding tools

If you use an AI tool to write, test, or update anything in this repo, point
it here first.

Read before making changes:

1. `docs/API_SURFACES.md` - both API surfaces, the auth contracts, and the
   test-data rules. The server lives in `config/env/qa.py`.
2. `docs/writing/ste.md` - the writing rules for all prose: docs, comments,
   docstrings, error messages, commit messages. Use strict mode for error
   messages and log lines, flavored mode for docs. `docs/STYLE.md` is the
   short human summary. Never apply the rules to code, identifiers, or any
   name the reader must match against a screen.

Hard rules:

- This repo is browser-free. Never add playwright or any browser dependency.
  API login is plain HTTP. If login fails, read the error. It names the fix.
- Commit messages state what the change does and why. Nothing else goes in
  them: no signatures, no boilerplate, no trailer lines.
- Plain ASCII in prose: no em dashes, no curly quotes, no emoji.
- QA Touch case mappings go in `config/qatouch_case_mapping.json`, never in
  test files.
- UI automation belongs in the sibling repo Soterix-WebApp-QA. Do not add
  it here.
- The two test suites stay isolated. Internal-suite fixtures live in
  `tests/internal_api/conftest.py`. Integration-suite fixtures live in
  `tests/integration_api/conftest.py`. The root `conftest.py` stays
  minimal. `api_clients/` (BaseAPIClient included) is internal-suite
  plumbing: never reuse or edit it for the integration suite.
- Work on a branch and open a pull request. Never force-push main.
- Nothing names a server, a site or a camera outside `config/env/`.
- Never commit `.env` or any credential.
- Before you edit a file you did not create, read it fully and keep its
  intent. Propose a large rewrite instead of applying it.
