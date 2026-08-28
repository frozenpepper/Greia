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

The first Simulator attempt did **not** prove an Encyclopedia runtime defect. It exposed a headless-Simulator tooling defect: `tools/headless_greia_simulator.py` republished a built-in Activity as developer-unsigned and therefore correctly hit Greia's duplicate-identity guard.

That Simulator tooling has now been repaired on `main`:

- a built-in `--activity-dir` is recognized as built-in and is **not** copied to the developer root;
- its canonical Activity ID is resolved from the manifest;
- the target index is resolved through Greia's real `ActivityRegistry`;
- the headless runner selects the normal child profile, navigates the real Shell Activity catalogue with semantic keys, and launches through the production launcher/supervisor path;
- the runner waits for a real `mode=activity` remote frame;
- after the interaction/survival window it invokes the platform-owned protected Home hitbox and requires a real return to `mode=activities`;
- child stdout/stderr is preserved beside the screenshots instead of sitting in an undrained pipe;
- focused regression tests are in `tests/test_headless_greia_simulator.py`.

Truthful state entering this task:

```text
SOURCE-VERIFIED / SIMULATOR-TOOLING-RETEST-PENDING
NARRATION ACCEPTANCE PENDING
```

This task generates **ZERO voice files**.
Do **not** rerun the Encyclopedia source gate.
Do **not** attempt the full 43-page traversal yet.
Do **not** make subjective pre-reader/visual claims from a terminal-only context.

---

## Step 1 — update safely

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

Required:

```text
branch = main
worktree = clean
```

If unrelated source is dirty or the pull cannot fast-forward, STOP and report it. Do not reset, clean, stash, checkout, or discard anything.

Record the exact HEAD as `STARTING_SHA`.

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

If the tests fail, STOP. Do not repair or rerun. Return the exact first failure.

---

## Step 3 — create evidence for one real built-in Encyclopedia smoke launch

From repository root:

```bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}-headless-smoke"
WORKSPACE="$HOME/.greia-simulator-encyclopedia-v01-headless-${RUN_ID}"
mkdir -p "$EVIDENCE"
printf '%s\n' "$EVIDENCE" > ./tmp/encyclopedia-v01-acceptance/.latest-run

git rev-parse HEAD > "$EVIDENCE/starting-sha.txt"
git status --short > "$EVIDENCE/git-status-before.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_044052/" \
  > "$EVIDENCE/source-gate-evidence.txt"
```

Simulator mutable state stays outside the checkout in `$WORKSPACE`.

---

## Step 4 — run exactly one repaired built-in headless launch

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
real Greia child Shell starts
remote bridge comes up
first Shell frame captured
normal profile selection succeeds
org.greia.enciclopedia is selected through semantic Shell navigation
real Activity frame arrives with mode=activity
RETURN is delivered to the Activity as the bounded meaningful interaction
Activity/Shell survive >=12 seconds
protected Greia Home is invoked through platform chrome
remote bridge returns to mode=activities
runner reports PASS
```

There must be **no** `Activity identity/alias collision`.

Expected evidence files include:

```text
enciclopedia-01-shell-frame.png
enciclopedia-02-activity-first-frame.png
enciclopedia-03-post-interaction.png
enciclopedia-04-returned-shell.png
enciclopedia-child.log
headless-smoke.txt
```

If `SMOKE_RC != 0`, STOP. Do not repair and do not rerun. Return the first failure plus the child log and whatever screenshots were produced.

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

```text
STARTING_SHA=
FOCUSED_SIMULATOR_TESTS=PASS/FAIL
HEADLESS_BUILTIN_DETECTION=PASS/FAIL/not-reached
SHELL_FIRST_FRAME=PASS/FAIL/not-reached
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

If this passes, the next tranche will build/run the **mechanical 43-page traversal and screenshot capture** on the now-proven headless lane. Subjective pre-reader/visual-quality judgment will remain a separate human/vision review of those captured frames.
