# Greia Encyclopedia v0.1 — 43-PAGE MECHANICAL TRAVERSAL — LOCAL AGENT TASK

This is the authoritative owner-machine task for the **single 43-page mechanical traversal run**.

Do not substitute the consolidated acceptance runbook for this task.

## Scope of this task

Run only the mechanical Simulator traversal of the already source-verified Greia Encyclopedia v0.1.

Accepted prior evidence:

```text
source gate: PASS
source evidence: tmp/encyclopedia-v01-acceptance/20260828_044052/

headless lifecycle smoke: PASS
smoke evidence: tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
real route: home[2]=learn -> activity[4]=org.greia.enciclopedia
```

The mechanical driver is:

```text
tools/encyclopedia_v01_headless_traversal.py
```

Focused contract test:

```text
tests/test_encyclopedia_v01_headless_traversal.py
```

This run must generate **ZERO voice files**.

Do NOT:

- rerun the Encyclopedia source gate;
- run `sync_voice_requests.py` as an acceptance step;
- generate narration;
- integrate or modify voice assets;
- run the broad consolidated acceptance runbook;
- repair source during the evidence run;
- rerun a failed traversal;
- claim signature interactions are visually accepted merely because a frame changed;
- claim pointer/keyboard parity, pre-reader UX, responsive-layout acceptance, or narration acceptance.

The purpose of this run is mechanical evidence only:

```text
real Shell -> Encyclopedia
all 6 sections reached
all 36 factual entries reached
one bounded semantic ACTIVATE delivered per entry
before/after PNG pair captured per entry
internal semantic Back works
all sections return to Encyclopedia home
protected Greia Home returns to Shell
```

---

## Step 1 — update safely

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"
printf 'LOCAL_HEAD=%s\nREMOTE_HEAD=%s\n' "$LOCAL_HEAD" "$REMOTE_HEAD"
git rev-list --left-right --count HEAD...origin/main
```

Required before changing anything:

```text
branch = main
worktree = clean
```

If the worktree is dirty, STOP. Do not reset, clean, stash, checkout, or discard anything.

If `LOCAL_HEAD == REMOTE_HEAD`, continue.

If local HEAD is an ancestor of `origin/main`, fast-forward only:

```bash
git merge --ff-only origin/main
```

If local is ahead of `origin/main` or histories diverged, STOP without modifying history and return:

```bash
git log --oneline --decorate --graph --max-count=40 --all
git log --oneline origin/main..HEAD
git diff --name-status origin/main...HEAD
```

Do not merge, rebase, reset, cherry-pick or push to resolve divergence inside this task.

After equality/fast-forward:

```bash
git rev-parse HEAD
git status --short
```

Record exact HEAD as `STARTING_SHA`.

Verify that this exact dedicated task exists locally after the update:

```bash
test -f docs/testing/GREIA_ENCYCLOPEDIA_V01_MECHANICAL_TRAVERSAL_LOCAL_AGENT.md
```

If it does not exist, STOP: the checkout is not on the required task revision.

---

## Step 2 — focused tooling tests, exactly once

`tests/` is intentionally not a Python package:

```bash
cd tests
PYTHONPATH=..:../src python3 -m unittest \
  test_encyclopedia_v01_headless_traversal.py \
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

If tests fail, STOP. Do not fix and do not rerun. Return the first failure.

---

## Step 3 — create one fresh evidence directory

Run in Bash:

```bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}-mechanical-traversal"
WORKSPACE="$HOME/.greia-simulator-encyclopedia-v01-traversal-${RUN_ID}"
mkdir -p "$EVIDENCE"
printf '%s\n' "$EVIDENCE" > ./tmp/encyclopedia-v01-acceptance/.latest-run

git rev-parse HEAD > "$EVIDENCE/starting-sha.txt"
git status --short > "$EVIDENCE/git-status-before.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_044052/" > "$EVIDENCE/source-gate-evidence.txt"
printf '%s\n' "tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/" > "$EVIDENCE/lifecycle-smoke-evidence.txt"
```

Simulator mutable state stays outside the checkout in `$WORKSPACE`.

---

## Step 4 — run exactly one 43-page mechanical traversal

Run exactly once:

```bash
python3 tools/encyclopedia_v01_headless_traversal.py \
  --workspace-dir "$WORKSPACE" \
  --evidence-dir "$EVIDENCE" \
  --locale it \
  --viewport 1024x600 \
  2>&1 | tee "$EVIDENCE/mechanical-traversal.txt"
TRAVERSAL_RC=${PIPESTATUS[0]}
```

Do not interrupt a healthy run.

A PASS must establish:

```text
real Shell -> org.greia.enciclopedia
real Encyclopedia home frame captured
6 / 6 section pages captured
36 / 36 factual entries reached
36 / 36 bounded semantic ACTIVATE interactions delivered
36 / 36 before+after PNG pairs captured
internal semantic Back returns from every entry
all six sections return to Encyclopedia home
protected Greia Home returns to real Shell
traversal-summary.json status = PASS
TRAVERSAL_RC = 0
```

Expected screenshot structure includes:

```text
screenshots/00-shell-profile-picker.png
screenshots/00-encyclopedia-home.png
screenshots/sections/01-animals.png
...
screenshots/sections/06-history.png
screenshots/entries/animals.lion-before.png
screenshots/entries/animals.lion-after.png
...
screenshots/entries/history.pyramids-before.png
screenshots/entries/history.pyramids-after.png
screenshots/98-encyclopedia-home-after-traversal.png
screenshots/99-returned-shell.png
```

The driver records `changed_pixel_fraction` for before/after pairs. This is diagnostic only. A nonzero value proves that pixels changed, not that the intended educational/signature interaction is visually correct.

### Hard stop

If `TRAVERSAL_RC != 0`, STOP. Do not edit source and do not rerun.

Preserve all partial evidence, especially:

```text
FIRST_FAILURE.txt
traversal-summary.json
mechanical-traversal.txt
enciclopedia-child.log
all screenshots produced before failure
```

---

## Step 5 — preserve child warnings exactly

The previous lifecycle smoke emitted:

```text
libpng error: bad adaptive filter value
```

Do not assume a cause and do not repair it in this run.

The traversal summary collects relevant child warnings. Return them exactly.

---

## Step 6 — final clean-state evidence

Regardless of PASS/FAIL:

```bash
git diff --check > "$EVIDENCE/git-diff-check.txt" 2>&1
DIFF_RC=$?
git status --short > "$EVIDENCE/git-status-after.txt"
```

The source worktree must remain clean. `tmp/` is gitignored.

Create one **evidence-only ZIP**, not a project ZIP:

```bash
EVIDENCE="$EVIDENCE" python3 - <<'PY'
import os
from pathlib import Path
import shutil

p = Path(os.environ["EVIDENCE"])
archive = shutil.make_archive(str(p), "zip", root_dir=p)
print(archive)
PY
```

---

## Return exactly this report

```text
STARTING_SHA=
FOCUSED_TRAVERSAL_TESTS=PASS/FAIL
MECHANICAL_TRAVERSAL_RC=
SHELL_TO_ENCYCLOPEDIA=PASS/FAIL/not-reached
SECTIONS_CAPTURED=<n>/6
ENTRIES_REACHED=<n>/36
ENTRY_INTERACTIONS_DELIVERED=<n>/36
ENTRY_BEFORE_AFTER_PAIRS=<n>/36
INTERNAL_BACK_RETURNS=<n>/36
ENCYCLOPEDIA_HOME_RETURN=PASS/FAIL/not-reached
PROTECTED_HOME_RETURN_TO_SHELL=PASS/FAIL/not-reached
TRAVERSAL_SUMMARY_STATUS=
CHILD_WARNINGS=<exact warning lines or none>
WORKTREE_AFTER=clean/dirty
FIRST_FAILURE=<none or exact stage/message>
EVIDENCE_DIR=
EVIDENCE_ZIP=
```

Also return:

- complete PASS summary or failure tail from `mechanical-traversal.txt`;
- `traversal-summary.json`;
- `FIRST_FAILURE.txt` if present;
- child log (complete if short, otherwise relevant warning/error tail);
- PNG count and total evidence size;
- final `git status --short`.

## What this task does NOT accept

Even on PASS, do not claim:

```text
signature interactions visually accepted
pointer/keyboard parity accepted
pre-reader UX accepted
responsive-layout matrix accepted
narration accepted
```

A green mechanical traversal only advances the project to visual review of the captured evidence plus the remaining pointer/pre-reader/responsive gates.
