# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Current accepted evidence

Source gate is GREEN:

```text
runtime/source SHA: d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
evidence: tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Real headless lifecycle smoke is GREEN:

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

The next tool is:

```text
tools/encyclopedia_v01_headless_traversal.py
tests/test_encyclopedia_v01_headless_traversal.py
```

It traverses all six sections and all 36 factual entries through the real Shell-launched Activity using semantic keyboard navigation only. It captures a before/after PNG pair for each factual entry, delivers one bounded primary ACTIVATE interaction, uses the Encyclopedia's own semantic Back path, and finally returns through protected Greia Home.

It does **not** claim visual/signature correctness merely because a frame changed. Those screenshots are evidence for the later visual review.

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
Do **not** repair source during the evidence run.
Do **not** rerun a failed traversal.

---

## 1. Update safely

```bash
git branch --show-current
git status --short
git fetch origin
LOCAL_HEAD="$(git rev-parse HEAD)"
REMOTE_HEAD="$(git rev-parse origin/main)"
printf 'LOCAL_HEAD=%s\nREMOTE_HEAD=%s\n' "$LOCAL_HEAD" "$REMOTE_HEAD"
git rev-list --left-right --count HEAD...origin/main
```

Required:

```text
branch = main
worktree = clean
```

If dirty, STOP. Do not reset/clean/stash/discard.

If equal, continue. If local HEAD is an ancestor of `origin/main`, fast-forward only:

```bash
git merge --ff-only origin/main
```

If local is ahead or histories diverged, STOP without modifying history and return:

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

## 2. Focused tooling tests — once

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

Required: `TEST_RC=0`.

If tests fail, STOP. Do not fix or rerun. Return the first failure.

---

## 3. Create one fresh traversal run

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

## 4. Run exactly one 43-page mechanical traversal

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
real Encyclopedia home frame
6 / 6 sections captured
36 / 36 factual entries reached
36 / 36 bounded semantic ACTIVATE interactions delivered
36 / 36 before+after PNG pairs captured
internal semantic Back returns from every entry
all six sections return to Encyclopedia home
protected Greia Home returns to real Shell
traversal-summary.json status = PASS
TRAVERSAL_RC = 0
```

Expected screenshot structure:

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

`changed_pixel_fraction` is diagnostic only. It proves a frame changed; it does not prove the intended educational/signature behavior is visually correct.

If `TRAVERSAL_RC != 0`, STOP. Do not edit or rerun. Preserve all evidence including `FIRST_FAILURE.txt`, `traversal-summary.json`, child log and partial screenshots.

---

## 5. Preserve the libpng warning honestly

The previous green smoke emitted:

```text
libpng error: bad adaptive filter value
```

Do not assume this came from screenshot encoding. The previous screenshots were valid, so this may instead indicate an asset decode that fell back visually.

The traversal summary records `libpng` / warning lines from the child log under `child_warnings`. Return those lines exactly. Do not fix them in this run.

---

## 6. Final clean state and evidence ZIP

Regardless of PASS/FAIL:

```bash
git diff --check > "$EVIDENCE/git-diff-check.txt" 2>&1
DIFF_RC=$?
git status --short > "$EVIDENCE/git-status-after.txt"
```

Source worktree must remain clean. `tmp/` is gitignored.

Create one evidence-only ZIP so the owner can upload the screenshots for visual review:

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

Do not create a project ZIP and do not modify source.

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
- child log (complete if short, otherwise relevant warnings/errors);
- PNG count and total evidence size;
- final `git status --short`.

Do **not** claim from this task:

```text
signature interactions visually accepted
pointer/keyboard parity accepted
pre-reader UX accepted
responsive-layout matrix accepted
narration accepted
```

If mechanical traversal is green, the next task is visual review of the evidence ZIP plus the remaining pointer/pre-reader/responsive acceptance. Do not rerun the source gate.
