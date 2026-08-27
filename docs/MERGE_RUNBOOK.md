# Merge runbook

How work moves between this repo's two GitHub remotes without losing
anything. Follow it for every merge. The sibling WebApp repo once lost ~100
files in a merge that showed only 3 conflicts. For every file that only one
side had changed, git took that side's version without asking. The checks
below exist so that cannot happen again.

## The two remotes

| Remote | URL | Role |
|---|---|---|
| `origin` | JustVar/Soterix-API-QA | Fetch + push. Carries a SECOND push URL for Soterix-Systems, so a plain `git push` updates both orgs. |
| `company` | Soterix-Systems/Soterix-API-QA | Fetch-only by convention. The QA team clones and PRs here. |

Neither repo can enable branch protection on the current GitHub plan, so
nothing technical stops a force-push from erasing someone's merged work.
The rules below are the protection.

**Rule zero: nobody force-pushes `main`, ever.** If a rewrite is truly
unavoidable, coordinate first, run `git fetch company`, and use
`--force-with-lease` only. Never use bare `--force`.

## Contributors (integration suite build-out)

1. Clone from `Soterix-Systems/Soterix-API-QA`.
2. **Before writing any code**, check the clone is on the real history:

   ```bash
   git rev-list --max-parents=0 HEAD
   # must print exactly: 92aadd1a9458f3d7fed0efb80f05f046d1142b2f
   ```

   Any other value means the clone predates the 2026-08-07 history cleanup
   and shares no ancestor with main. Merges from it fail with "refusing to
   merge unrelated histories". Recovery that keeps your work (substitute
   YOUR root sha from the command above):

   ```bash
   git fetch https://github.com/Soterix-Systems/Soterix-API-QA.git main
   git rebase --onto FETCH_HEAD <your-root-sha> <your-branch>
   ```

   If the rebase gets ugly: `git format-patch <your-root-sha>..HEAD
   --stdout > work.patch`, fresh clone, `git am -3 work.patch`.
3. Work on a feature branch (for example `integration-api-tests`), push it
   to Soterix-Systems, open a PR against `main` there. Do not push to
   `main` directly. The PR anchors review and this checklist.
4. Before requesting review, run your suite and a whole-tree collection:

   ```bash
   pytest tests/integration_api
   pytest --collect-only -q     # proves you broke no other suite's imports
   ```

## Owner (bringing team merges home)

A plain `git push` pushes to BOTH orgs. If the team merged anything into
company/main first, the push half-succeeds: JustVar advances,
Soterix-Systems rejects, and the remotes diverge. Worse, `git status` still
says "up to date", because only the JustVar URL is fetched. So:

**Before every push:**

```bash
git fetch company
git log --oneline main..company/main   # push ONLY if this prints nothing
```

**If it prints commits, integrate them first (Git Bash, clean tree):**

```bash
PRE=$(git rev-parse HEAD)
git ls-files | sort -u > /tmp/files_pre.txt

git merge --no-ff --no-commit company/main

# 1. Nothing disappeared that should not have:
git ls-files | sort -u > /tmp/files_post.txt
comm -23 /tmp/files_pre.txt /tmp/files_post.txt        # expected removals only

# 2. Files where deletions dwarf additions (the silent-revert signature):
git diff --numstat $PRE | awk '$2 > 2*$1 && $2 > 20'   # review every line it prints

# 3. Files only the company side changed (git merges these without asking):
comm -23 <(git diff --name-only $(git merge-base $PRE company/main) company/main | sort) \
         <(git diff --name-only $(git merge-base $PRE company/main) $PRE | sort)
# eyeball each one's diff before committing

git commit          # then validate before pushing:
pytest --collect-only -q
pytest --setup-plan -q          # catches deleted/renamed fixtures, no live calls
pytest tests/plugins                   # offline unit tests
git push                               # now fast-forwards both orgs
```

If a push already half-succeeded (rejection message named the
Soterix-Systems URL): do the integrate steps above, then push again.
Nothing is lost. The rejection is the safety working.

## After any merge lands

Run each suite once from a clean venv before calling it done. A warm venv
once hid a requirements gap in the sibling repo's merge.
