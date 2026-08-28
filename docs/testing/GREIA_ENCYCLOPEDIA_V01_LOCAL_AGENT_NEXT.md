# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Current accepted evidence

Source gate remains GREEN:

```text
runtime/source SHA: d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
evidence: tmp/encyclopedia-v01-acceptance/20260828_044052/
```

The corrected headless lifecycle smoke is also GREEN:

```text
owner-machine SHA: 621c1950133151b9c89c14ec74e4628e4c665147
evidence: tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
route: home[2]=learn -> activity[4]=org.greia.enciclopedia
focused Simulator tests: 45/45 PASS
real Shell -> Encyclopedia: PASS
first Activity frame: PASS
12 s survival: PASS
bounded semantic interaction: PASS
protected Home -> Shell: PASS
worktree: clean
```

This proves the real Shell/Activity lifecycle lane. It does **not** prove all 43 pages or subjective visual/pre-reader quality.

A dedicated mechanical traversal driver now exists:

```text
tools/encyclopedia_v01_headless_traversal.py
tests/test_encyclopedia_v01_headless_traversal.py
```

It launches the real built-in Encyclopedia through the real child Shell, visits all six section pages and all 36 factual entries using only semantic keyboard navigation, sends one bounded primary ACTIVATE interaction per entry, captures before/after PNG evidence, uses the Encyclopedia's own semantic Back path, and finally returns through protected Greia Home.

It deliberately does **not** claim that an interaction is visually correct merely because a frame changed. Signature-interaction correctness, pointer parity and pre-reader quality remain a separate visual review of the captured frames.

Truthful state entering this task:

```text
SOURCE-VERIFIED
HEADLESS-LIFECYCLE-SMOKE-PASS
43-PAGE-MECHANICAL-TRAVERSAL-PENDING
VISUAL/PRE-READER REVIEW PENDING
NARRATION ACCEPTANCE PENDING
```

This task generates **ZERO voice files**.
Do **not** rerun the Encyclopedia source gate.
Do **not** make runtime/source repairs during the evidence run.
Do **not** rerun a failed traversal.

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

If dirty, STOP and report the paths. Do not reset/clean/stash/discard.

If `LOCAL_HEAD == REMOTE_HEAD`, continue.

If local HEAD is an ancestor of `origin/main`, fast-forward only:

```bash
git merge --ff-only origin/main
```

If local is ahead or histories diverged, STOP. Do not merge/rebase/reset/cherry-pick/push. Return:

```bash
git log --oneline --decorate --graph --max-count=40 --all
git log --oneline origin/main..HEAD
git diff --name-status origin/main...HEAD
```

After equality/fast-forward:

```bash
git rev-parse HEAD
git status --short
```

Record exact HEAD as `STARTING_SHA`.

---

## Step 2 — focused tooling tests, once

`tests/` is intentionally not a package:

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

If this fails: STOP, do not fix and do not rerun. Return the first failure.

---

## Step 3 — create one fresh traversal evidence run

Use Bash:

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

Simulator mutable state remains outside the checkout in `$WORKSPACE`.

---

## Step 4 — run exactly one 43-page mechanical traversal

Run once:

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

Expected PASS contract:

```text
real Shell route resolves to org.greia.enciclopedia
real Shell first frame arrives
real Encyclopedia home frame arrives
6 / 6 section pages captured
36 / 36 factual entries reached
36 / 36 bounded semantic ACTIVATE interactions delivered
before + after PNG captured for every factual entry
internal semantic ESCAPE/Back returns from every entry
section -> Encyclopedia home returns work
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

The driver records `changed_pixel_fraction` for each before/after pair. That metric only proves the frame changed; it is **not** permission to claim the planned signature interaction is visually correct.

### Hard stop

If `TRAVERSAL_RC != 0`, STOP. Do not edit source and do not rerun. Preserve:

```text
FIRST_FAILURE.txt
traversal-summary.json
mechanical-traversal.txt
enciclopedia-child.log
all screenshots produced before failure
```

---

## Step 5 — inspect the libpng warning honestly

The previous green smoke emitted:

```text
libpng error: bad adaptive filter value
```

Do not assume this came from screenshot encoding. The smoke PNGs were valid, so this may instead be a failed PNG asset decode with a fail-soft visual fallback.

The traversal summary automatically collects `libpng` / warning lines from the child log under `child_warnings`.

Report those lines exactly. Do not repair them in this run.

---

## Step 6 — final clean state

Regardless of traversal PASS/FAIL:

```bash
git diff --check > "$EVIDENCE/git-diff-check.txt" 2>&1
DIFF_RC=$?
git status --short > "$EVIDENCE/git-status-after.txt"
```

Source worktree must remain clean. `tmp/` is gitignored.

Create one evidence archive for owner/primary-agent visual review; this is evidence only, not a project package:

```bash
python3 - <<'PY'
from pathlib import Path
import shutil
p = Path("$(cat ./tmp/encyclopedia-v01-acceptance/.latest-run)")
shutil.make_archive(str(p), "zip", root_dir=p)
print(str(p) + ".zip")
PY
```

If the shell does not expand the command substitution inside that quoted Python block on your environment, instead resolve `EVIDENCE` first and use Python with that exact path. Do not modify source to create the archive.

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

- the complete PASS summary or failure tail from `mechanical-traversal.txt`;
- `traversal-summary.json`;
- `FIRST_FAILURE.txt` if present;
- the complete short `enciclopedia-child.log`, or relevant warning/error tail if it becomes large;
- count of PNG files and total evidence size;
- final `git status --short`.

Do **not** claim from this task:

```text
signature interactions visually accepted
pointer/keyboard parity accepted
pre-reader UX accepted
responsive-layout matrix accepted
narration accepted
```

If the mechanical traversal is green, the next task is **visual review of these captured frames plus the remaining pointer/pre-reader/responsive acceptance**, not another source-gate run.
