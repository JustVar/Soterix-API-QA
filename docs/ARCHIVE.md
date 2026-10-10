# What left this repo

On 2026-09-29 the framework was cut down to one QA server, one account
pair and CI on GitHub's machines. The files that described the old setup
left `main`. They are not lost. The branch `archive/pre-pivot` holds the
last commit before the cut. Do not delete that branch.

The archived files describe machines, tenants and accounts that no longer
exist. Restore one only to read it or to adapt it.

The one restore command, from the repo root:

```
git checkout archive/pre-pivot -- <path>
```

## What left, by area

| Area | Files under the tag | Why it left |
|---|---|---|
| The second tenant and the box layer | `config/env/qa.py` (the `boxes` dict, `get_box_config`), `config/base_config.py` (`BOX`, `get_active_box`, `APP_TYPE`), the `BOX` branch of `login_data` in `tests/internal_api/conftest.py`, the per-box keys in `.env.template` | One server, one account pair. The account is `QA_USER` and `QA_PASSWORD`. |
| Other environments | `config/env/stage.py`, `config/env/prod.py`, `config/env/qa_pat.py`, `config/env/stage_pat.py`, `config/env/prod_pat.py` | Those servers are not targets. A second server is a copy of `config/env/qa.py`. |
| The self-hosted CI runner | `.github/workflows/collect-gate.yml` (the `runs-on` expression, the `hosted` input, the weekly schedule, the deploy-key steps, the 4-interpreter shim matrix) | The runner host is off. CI runs on `ubuntu-latest` with no secret. |
| The private package install | the `git+https` line in `requirements.txt` | The package is a wheel under `vendor/`. No second repository grant. |
| The two-remote merge process | `docs/MERGE_RUNBOOK.md`, the "Contributing Across the Two Remotes" section of `README.md` | One rule remains, in `docs/CONVENTIONS.md`: branch, pull request, never force-push `main`. |
| Run history | `history/2026-08.jsonl` | Per-run history is not carried forward. An armed run still writes a local ledger under `history/`, which is gitignored. |
| Camera notes from a dead host | `docs/API_TESTING_NOTES.md` | Its site and camera inventory was captured on a host that no longer resolves. `tools/discover_cameras.py` prints the live topology. |
| A login probe | `tools/probe_login.py` | The question it explored is answered in `docs/API_SURFACES.md` and pinned by `tests/internal_api/test_auth_apis.py`. |
| Guessed QA Touch mappings | 13 rows with `auto_matched: true` in `config/qatouch_case_mapping.json` | They mapped API tests to UI cases. Only rows a person reviewed stay. |
| The production spec snapshot | `schemas/openapi_spec_prod.json` | Nothing read it, and no `config/env/` file can regenerate it. `schemas/openapi_spec_qa.json` stays. |
| A Bruno guide | `docs/BRUNO_GUIDE.md` | Its bootstrap signed in through the captcha-gated login with a plain password and a fixed enterprise id. Bruno is not part of the automation. |

## What stayed and why

- The run archive under `reports/runs/`, because it is what makes a run
  readable on the machine that ran it.
- The collect floor (`config/collect_floor.json`), because it is the only
  check that notices a suite shrinking.
- `KNOWN_LIMITATIONS` in `tests/internal_api/data/endpoints.py`, with every
  reason marked with the server and the month it was measured on, because
  a skip with a stated reason beats a deleted endpoint.
- The QA Touch upload path, off by default, because a team on QA Touch
  can turn it on with 3 keys in `.env`.
