# QA program register

The running record of what is decided, done, and open across the QA
automation program. It lives here because this repo is pushed to both
GitHub orgs, so the record survives a machine loss.

Scope: the two QA test repos, the shared package `soterix-qa-core`, QA
Touch, Jira, and CI. Detail lives in the linked documents; this file is the
index and the decision log, and it is the place to look before asking
"what happened to that thing we talked about".

Last updated: 2026-08-28.

---

## 1. Decisions (settled; change them deliberately, not by drift)

| # | Decision | Why it was made | Date |
|---|---|---|---|
| D1 | Two repos split by API surface: `Soterix-WebApp-QA` (UI) and `Soterix-API-QA` (API, browser-free) | The suites share nothing at run time; the API suite must install in seconds with no browser | 2026-08-07 |
| D2 | Directories name the API surface, markers name the test depth (`tests/internal_api`, `tests/integration_api`) | "smoke" described depth and read as identity, hiding the real split | 2026-08-27 |
| D3 | "Integration API" means the partner product surface `/v-integration-api`, never the test level | The two meanings collided and cost a full investigation | 2026-08-27 |
| D4 | QA Touch is per product. Core cases are authored once in NexaiQ-Core (JlW1) and executed per product as separate runs; each product project holds only its own cases | Every product uses core functionality; duplicating core cases into six projects is a maintenance trap | 2026-08-28 |
| D5 | Own the test-data contract: a versioned seeding module in the shared package, guarded by contract tests, with per-product layers on top | The UI suite already seeds through the internal API; that is a real cross-suite contract | 2026-08-28 |
| D6 | CI runs on the US and India lab boxes (self-hosted runners), not hosted runners | Lab boxes reach the tenant and avoid the datacenter-IP reCAPTCHA problem entirely for QA | 2026-08-28 |
| D7 | A shared installable package (`soterix-qa-core`) is the anti-duplication strategy; new product repos consume it rather than copying it | The QA Touch pipeline had already diverged between two repos; six products would multiply it | 2026-08-27 |
| D8 | New repo only when a product's stack genuinely diverges (Mobile/Appium, C2C hardware, Neurosen offline). Otherwise a suite in an existing repo | Repo proliferation costs more than it saves; the Aug 2026 split is the priced precedent | 2026-08-28 |
| D9 | Finish the NexaiQ-Core foundations first as the template, then clone the proven pattern per product | Core is the proving ground; per-product is a multi-quarter program | 2026-08-28 |
| D10 | **QA Ops Hub is not part of the solution.** It was a proof of concept and recent research found it unnecessary | Removes a service, a database and a second Jira field mapping from the design | 2026-08-28 |
| D11 | QA Touch case-to-test mapping stays in config JSON, never in test files | The whole team runs the scripts; QA Touch reporting is one person's workflow. This decision is also what makes a tool migration possible at all | earlier |
| D12 | Plugin registration is unconditional and fails legibly; conditional registration was tested and rejected | Conditional registration turns an armed upload into a silent no-op | 2026-08-28 |

### What D10 changes

- The bug-review queue and the verification-review queue stay **CLI + JSON
  in the UI repo**. They were slated to move into the Hub; they no longer
  are. No replacement service is planned.
- The reporting dashboard has **no serving host**. Reports are local files
  (`reports/runs/`, `run.html`, `health.html`) plus optional email. Decide
  later whether anything hosts them; nothing depends on it today.
- The Jira multi-project problem shrinks to **one** implementation (the UI
  repo's `smart_jira_bug_creator` + `config/jira_field_mapping.py`). The
  Hub's copy-pasted custom-field IDs are no longer a concern.
- The Hub's database pointing at the retired NUC is moot.

---

## 2. Shipped

- **Integration-API suite**: 14-endpoint catalogue sweep plus auth-boundary
  tests, and the API key lifecycle test (create, disable, enable, delete)
  against the internal key endpoints. Live-verified. `docs/API_SURFACES.md`.
- **Suite isolation**: per-suite conftests, package inits, per-suite HTML
  reports, `integration_api_base_url` config slots, root-wide collect gate.
- **`tests/smoke` renamed to `tests/internal_api`** with all QA Touch
  mapping keys and doc-registry paths moved (verified: zero unmatched).
- **QA Touch step cases**: `create_test_case_with_steps` (the plain endpoint
  silently creates Exploratory Session cases that never list). Five API
  Integration cases created and mapped.
- **The durable QA key** "QA Automation - DO NOT DELETE" with per-host
  descriptions, wired to `VSAAS_INTEGRATION_KEY`.
- **`soterix-qa-core`**: scaffold, the unified QA Touch client (UI superset
  plus the API's step-case method), 25 offline tests, ruff config, py.typed,
  version accessor, and `STATUS.md` — the extraction plan, corrected across
  three adversarial audit rounds.
- **`docs/MERGE_RUNBOOK.md`**, the dual-remote push gate, and the
  post-merge shrinkage checks.

---

## 3. Open work

### 3a. The seams (from the resilience audit, 2026-08-28)

Ranked by value per hour. Effort S unless noted.

| # | Seam | Where | Status |
|---|---|---|---|
| S1 | Push `soterix-qa-core` to GitHub (dual-remote shape) | core repo | open — same as STATUS.md step 0 |
| S2 | Back up test cases: parameterize the snapshot tool's project key, track the snapshot in git | UI repo `tools/qatouch_analytics.py`, `.gitignore` | open — highest value |
| S3 | Make the rename guard class-aware (AST, not regex) | UI repo `tools/qatouch_mapping.py` | open — land before the migration |
| S4 | Normalize parametrization on both sides of the mapping lookup | UI repo mapping + the reporter | open — split across the migration |
| S5 | Re-key the reporter from case key to node id, behind a result-sink interface (M) | core repo, during step 1 | open — cheap now, ~3x later |
| S6 | Preflight probes the API base URL; first login failure aborts the session (M) | UI repo `tools/pre_run_check.py`, `conftest.py` | open |
| S7 | Case-text drift detection between docstrings and QA Touch (M) | UI repo `tools/qatouch_cases_from_tests.py` | open |

### 3b. The package extraction

`soterix-qa-core/STATUS.md` is the plan of record: nine prototype-proven
rules, the compatibility contract, and steps 0 through 7. Step 2 is
deliberately split — only the stdlib leaves move now; the archive, report,
health and email stack stays in the UI repo until a second consumer needs
it and gets its own design pass.

### 3c. In review

- **PR #2** (Soterix-API-QA): the port of PR #1's work into
  `tests/internal_api` — catalogue sweep and two e2e flows on the shared
  fixtures, credentials removed, writes gated. Awaiting review.
- **PR #1**: superseded by #2. Drop the `new_API_flow/` tree once #2 lands.

### 3d. Product findings, with the team (not yet filed as Jira issues)

1. NC-20224 (channel status/snap) and NC-20225 (channel groups) are marked
   Complete but every documented path returns 404 on QA.
2. An API key's `host[]` allowlist is not enforced — a key listing only the
   QA host authenticated from an external IP.
3. `startlive`/`startarchive` create server-side streaming sessions with no
   stop endpoint and an unknown TTL.

### 3e. Hygiene and risk

| Item | Note |
|---|---|
| Azure client secret | Expired 2026-07-22; the report mailer is non-functional until rotated |
| Videonetics named account in `config/env/qa.py` | A person's account used as a shared test box; replace with a service account (long lead time, start early) |
| Within-repo case-key duplicates | UI 42 keys / 76 redundant claims; API 5 / 19. The same-run overwrite hazard. Baseline recorded so a checker can land non-blocking |
| `WEnvKQ` cross-repo collision | Dormant: results are written per run, and the UI row is unreviewed. Hygiene, not a blocker |
| Case content coverage | Only ~15% of tests carry real docstring steps; 63% of QA Touch steps are filler. "The repo is the source of truth" is aspirational until S7 plus human writing |
| Operational schedule | Who runs the vendor contract check, rotates secrets, reviews team commits. 95% of framework commits are one person |

### 3f. Future product foundations (each needs its own design pass)

Mobile (Appium, Android + iOS), C2C (camera hardware and firmware; ties to
the Triple Helix roadmap item), Neurosen (offline-first, with an
initial-install online check to be confirmed). Reusable today: the client
(fully project-parameterized), the archive and report stack (no Playwright
imports), the product table (already carries all six product keys), and the
C2C hardware pattern that already works.

---

## 4. Where the detail lives

| Document | What it holds |
|---|---|
| `soterix-qa-core/STATUS.md` | The extraction plan: rules, compatibility contract, ordered steps |
| `docs/API_SURFACES.md` | Both API surfaces, auth contracts, response traps, key management |
| `docs/INTERNAL_API_INVENTORY.md` | Every internal endpoint with request and response shapes |
| `docs/MERGE_RUNBOOK.md` | Dual-remote merges, the pre-push gate, shrinkage checks |
| `tests/integration_api/README.md` | The integration suite's build-out contract |
| UI repo `docs/CONVENTIONS.md`, `FAILURE_TRIAGE.md`, `QA_THINGS_TO_KNOW.md` | Test authoring, triage, tenant traps |
| `dashboards/.../QA_ROADMAP.md` | The roadmap rows this register summarizes |
