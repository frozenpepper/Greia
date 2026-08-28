# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Current evidence

The Encyclopedia source gate remains GREEN on:

```text
d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

That source evidence proved 378/378 canonical voice-request rows, 53/53 focused Encyclopedia tests, 1431/1431 full repository tests, 35/35 Activity validations, and a clean worktree.

Two successive terminal-only Simulator smoke attempts then exposed **headless harness defects, not proven Encyclopedia runtime defects**:

1. the first headless helper republished the built-in Encyclopedia as developer-unsigned, correctly hitting Greia's duplicate-identity guard;
2. after that was fixed, the helper correctly reached the real child Shell and profile picker, but it navigated the post-profile screen as though it were the raw `ActivityRegistry` tuple.

The second assumption was wrong. The production Greia child Shell is **Collection-first**:

```text
profile picker
→ Collection Home (Create / Play / Learn / Explore / ...)
→ optional adaptive sub-Collection
→ Activity cards
→ Activity launch
```

The failed smoke evidence is:

```text
tmp/encyclopedia-v01-acceptance/20260828_061732-headless-smoke/
```

It proved:

```text
focused Simulator tests             PASS (44 tests in that checkout)
built-in detection                   PASS
remote bridge                        PASS
first real Shell frame               PASS (mode=profiles, 1024x600)
duplicate-ID collision               GONE
Activity launch                      NOT PROVEN
```

The route defect has now been repaired on GitHub `main`:

- `tools/headless_greia_simulator.py` no longer computes a raw launcher index;
- it derives a typed `ShellLaunchRoute` from the same profile-visible `ActivityCatalogue` projection used by the child Shell;
- the route includes Collection Home index, optional adaptive sub-Collection index, and final Activity-card index;
- built-in, developer and Parent-installed Activity sources are included in the route projection;
- the selected Simulator profile's visibility policy, approximate age and challenge preference are applied before route selection;
- semantic navigation now waits for a fresh real Shell frame after each hierarchy transition/key step;
- focused tests cover both direct Collection → Activity and Collection → adaptive sub-Collection → Activity paths.

One additional repository-state issue must be handled safely before retest: the previous owner-machine report started at local SHA

```text
7417e20729fd1c0562491e26f9fe564deccac058
```

and that SHA is **not present in GitHub's repository history**. Therefore do not assume the owner checkout can fast-forward to current `origin/main`. Preserve any local-only commits before running anything.

Truthful state entering this task:

```text
SOURCE-VERIFIED / LOCAL-BRANCH-RECONCILIATION-CHECK-PENDING
HEADLESS-SHELL-ROUTE-RETEST-PENDING
NARRATION ACCEPTANCE PENDING
```

This task generates **ZERO voice files**.
Do **not** rerun the Encyclopedia source gate.
Do **not** attempt the full 43-page traversal yet.
Do **not** make subjective pre-reader/visual claims from a terminal-only context.

---

## Step 1 — inspect branch ancestry before changing the checkout

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
```

Required before any update:

```text
branch = main
worktree = clean
```

If the worktree is dirty, STOP and report the paths. Do not reset, clean, stash, checkout, or discard anything.

Now classify the local branch **without modifying it**:

```bash
LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"

printf 'LOCAL_HEAD=%s\n' "$LOCAL_HEAD"
printf 'REMOTE_HEAD=%s\n' "$REMOTE_HEAD"
git rev-list --left-right --count HEAD...origin/main

git log --oneline --decorate --graph --max-count=30 HEAD origin/main
```

Then use these exact ancestry checks:

```bash
if [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
  printf '%s\n' 'BRANCH_RELATION=equal'
elif git merge-base --is-ancestor HEAD origin/main; then
  printf '%s\n' 'BRANCH_RELATION=local-behind-fast-forward-safe'
elif git merge-base --is-ancestor origin/main HEAD; then
  printf '%s\n' 'BRANCH_RELATION=local-ahead-unpublished'
else
  printf '%s\n' 'BRANCH_RELATION=diverged'
fi
```

### If `BRANCH_RELATION=equal`

Continue to Step 2.

### If `BRANCH_RELATION=local-behind-fast-forward-safe`

Fast-forward only:

```bash
git merge --ff-only origin/main
git rev-parse HEAD
git status --short
```

Then continue to Step 2.

### If `BRANCH_RELATION=local-ahead-unpublished` or `BRANCH_RELATION=diverged`

**STOP. Do not merge, rebase, reset, cherry-pick, push or pull.**

Return enough evidence for owner review:

```bash
git log --oneline --decorate --graph --max-count=40 --all
git log --oneline origin/main..HEAD
git diff --name-status origin/main...HEAD
git diff --stat origin/main...HEAD
```

Also return the commit message and changed paths for every local-only commit:

```bash
git log --format='%H %s' origin/main..HEAD
```

Do not proceed to Simulator tests until those unpublished commits are reconciled deliberately.

After a safe equality/fast-forward, record the exact resulting HEAD as `STARTING_SHA`.

---

## Step 2 — run the focused Simulator tooling tests once

`tests/` is intentionally not a Python package. Run from inside that directory:

```bash
cd tests
PYTHONPATH=..:../src python3 -m unittest \
  test_headless_greia_simulator.py \
  test_greia_simulator.py \
  -v
TEST_RC=$?
cd ..
```

Required:

```text
TEST_RC=0
```

The headless test module must now include explicit Collection-first route coverage.

If the tests fail, STOP. Do not repair or rerun. Return the exact first failure.

---

## Step 3 — create evidence for one real built-in Encyclopedia smoke launch

From repository root:

```bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}-headless-route-smoke"
WORKSPACE="$HOME/.greia-simulator-encyclopedia-v01-headless-${RUN_ID}"
mkdir -p "$EVIDENCE"
printf '%s\n' "$EVIDENCE" > ./tmp/encyclopedia-v01-acceptance/.latest-run

git rev-parse HEAD > "$EVIDENCE/starting-sha.txt"
git status --short > "$EVIDENCE/git-status-before.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_044052/" \
  > "$EVIDENCE/source-gate-evidence.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_061732-headless-smoke/" \
  > "$EVIDENCE/previous-smoke-evidence.txt"
```

Simulator mutable state stays outside the checkout in `$WORKSPACE`.

---

## Step 4 — run exactly one Collection-first built-in headless launch

Run exactly once:

```bash
python3 tools/headless_greia_simulator.py \
  --activity-dir activities/enciclopedia_greia \
  --workspace-dir "$WORKSPACE" \
  --locale it \
  --viewport 1024x600 \
  --survival-seconds 12 \
  --press-key RETURN \
  --screenshot-prefix "$EVIDENCE/enciclopedia" \
  2>&1 | tee "$EVIDENCE/headless-smoke.txt"
SMOKE_RC=${PIPESTATUS[0]}
```

Run this command in **Bash** so `PIPESTATUS[0]` is the real simulator exit code.

Expected behavior, in order:

```text
built-in Activity detected; skipping developer publication
semantic route is logged as:
  home[...] = <Collection>
  [optional group[...] = <sub-Collection>]
  activity[...] = org.greia.enciclopedia
real Greia child Shell starts
remote bridge comes up
first Shell frame captured in mode=profiles
profile RETURN reaches mode=activities / Collection Home
semantic RIGHT/RETURN steps traverse the logged Collection-first route
real Encyclopedia frame arrives with mode=activity
RETURN is delivered to the Encyclopedia as the bounded interaction
Activity/Shell survive >=12 seconds
protected Greia Home is invoked through platform chrome
remote bridge returns to mode=activities
runner reports PASS
```

There must be **no**:

```text
Activity identity/alias collision
raw "launcher index X/Y" navigation
```

Expected evidence files include:

```text
enciclopedia-01-shell-frame.png
enciclopedia-02-activity-first-frame.png
enciclopedia-03-post-interaction.png
enciclopedia-04-returned-shell.png
enciclopedia-child.log
headless-smoke.txt
```

If `SMOKE_RC != 0`, STOP. Do not repair and do not rerun. Return:

- the exact logged semantic route;
- the exact first navigation stage that stalled, if any;
- the child log;
- every screenshot that was actually produced.

---

## Step 5 — final clean-state evidence

If the smoke run passes:

```bash
git diff --check > "$EVIDENCE/git-diff-check.txt" 2>&1
DIFF_RC=$?
git status --short > "$EVIDENCE/git-status-after.txt"
```

Required:

```text
DIFF_RC=0
source worktree remains clean
```

The project-local `tmp/` evidence is gitignored and does not count as source dirt.

---

## Return exactly this report

If Step 1 stops for unpublished/diverged history, return:

```text
LOCAL_HEAD=
REMOTE_HEAD=
BRANCH_RELATION=local-ahead-unpublished/diverged
LOCAL_ONLY_COMMITS=
LOCAL_ONLY_CHANGED_PATHS=
WORKTREE=clean/dirty
FIRST_FAILURE=branch histories require deliberate reconciliation
```

Otherwise return the smoke report:

```text
STARTING_SHA=
FOCUSED_SIMULATOR_TESTS=PASS/FAIL
HEADLESS_BUILTIN_DETECTION=PASS/FAIL/not-reached
COLLECTION_FIRST_ROUTE_RESOLVED=PASS/FAIL/not-reached
ROUTE=<exact logged route or not-reached>
SHELL_FIRST_FRAME=PASS/FAIL/not-reached
PROFILE_TO_COLLECTION_HOME=PASS/FAIL/not-reached
COLLECTION_ROUTE_NAVIGATION=PASS/FAIL/not-reached
ENCYCLOPEDIA_LAUNCH_VIA_REAL_SHELL=PASS/FAIL/not-reached
ENCYCLOPEDIA_FIRST_ACTIVITY_FRAME=PASS/FAIL/not-reached
SURVIVAL_12S=PASS/FAIL/not-reached
BOUNDED_RETURN_INTERACTION=PASS/FAIL/not-reached
PROTECTED_HOME_RETURN_TO_SHELL=PASS/FAIL/not-reached
HEADLESS_SMOKE_RC=
WORKTREE_AFTER=
FIRST_FAILURE=<none or exact failure>
EVIDENCE_DIR=
```

Also return:

- complete `headless-smoke.txt` failure tail or PASS summary;
- `enciclopedia-child.log` (or relevant tail if large);
- names and sizes of every produced PNG;
- final `git status --short`.

Do not claim the full 43-page Simulator traversal or pre-reader acceptance from this task.

If this passes, the next tranche will build/run the **mechanical 43-page traversal and screenshot capture** on the now-proven headless lane. Subjective pre-reader/visual-quality judgment remains a separate human/vision review of those captured frames.
