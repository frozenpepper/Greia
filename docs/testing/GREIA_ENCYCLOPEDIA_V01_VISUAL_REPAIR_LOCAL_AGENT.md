# Greia Encyclopedia v0.1 — VISUAL REPAIR + EVIDENCE RECAPTURE — LOCAL AGENT TASK

This is the authoritative owner-machine task for the post-visual-review repair tranche.

Do not substitute the consolidated acceptance runbook.
Do not regenerate narration.
Do not make unrelated visual/design changes.

## Accepted prior evidence

Source gate:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Lifecycle smoke:

```text
tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
```

Mechanical traversal under review:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal/
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip
```

Primary visual review:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_VISUAL_EVIDENCE_REVIEW.md
```

That review established:

```text
43-page reachability/back                 PASS
coherent first-interaction visual pairs   34 / 36
space.sun pair                            INVALID capture race
space.neptune pair                        INVALID capture race
history.pyramids intro caption            OVERFLOW defect
Body section Teeth target                 LOW-CONTRAST defect
```

The primary agent has already landed the two runtime visual repairs:

- `activities/enciclopedia_greia/pages/pyramids.py`: preserve approved wording and fit/wrap long caption text inside the existing panel;
- `activities/enciclopedia_greia/pages/body.py`: increase Teeth target glyph contrast without changing navigation or factual content.

Your coding task is **only** the traversal capture-settle repair plus its regression test. Then verify the complete repaired state once.

---

## 1. Update safely

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

If dirty: STOP. Do not reset/clean/stash/discard.

If equal, continue.
If local is behind and is an ancestor of `origin/main`, fast-forward only:

```bash
git merge --ff-only origin/main
```

If local is ahead or diverged: STOP and return the local-only history/diff. Do not merge/rebase/reset/cherry-pick/push to resolve it inside this task.

Record the resulting HEAD as `STARTING_SHA`.

Confirm these files exist:

```bash
test -f docs/reviews/2026-08-28_ENCYCLOPEDIA_V01_VISUAL_EVIDENCE_REVIEW.md
test -f tools/encyclopedia_v01_headless_traversal.py
test -f tests/test_encyclopedia_v01_headless_traversal.py
```

---

## 2. Implement only the traversal transition-settle fix

Problem to solve:

The old traversal helper considered the first later global Activity frame sufficient proof that a posted semantic key had taken effect. On animated `space`, that allowed `space.sun-before.png` and `space.neptune-before.png` to capture the old section page before RETURN was consumed.

Do **not** add page-specific IDs, source inspection, hidden runtime hooks, click coordinates, or Sun/Neptune special cases.

Implement a general bounded frame-settle contract in:

```text
tools/encyclopedia_v01_headless_traversal.py
```

Required shape:

1. Extend the internal semantic-key helper so the caller can require more than one post-key Activity frame. A name such as `min_frame_advance` or equivalent is fine.
2. Default ordinary focus/input movement to the current one-frame behavior.
3. For semantic operations that change Encyclopedia pages, require at least **3** post-key Activity frames before continuing:
   - Encyclopedia Home -> section `RETURN`;
   - section -> factual entry `RETURN`;
   - factual entry -> section `ESCAPE`;
   - section -> Encyclopedia Home `ESCAPE`.
4. Keep the factual entry's primary ACTIVATE interaction bounded as before; do not change the interaction semantics just to create larger screenshot deltas.
5. Do not add arbitrary multi-second sleeps. The contract must remain frame-bounded and low-cost.

The wait predicate should still require:

```text
mode == activity
```

and a frame count satisfying the requested minimum advance relative to the pre-key count.

### Regression test

Update:

```text
tests/test_encyclopedia_v01_headless_traversal.py
```

Add a behavioral test proving the multi-frame key contract. At minimum:

- start from a mocked current Activity state with known `frame_count`;
- request a minimum advance of 3;
- prove the wait predicate rejects +1 and +2;
- prove it accepts +3;
- prove the bridge receives the requested key;
- keep existing navigation/36-page contract tests intact.

Also add a contract assertion that page-changing RETURN/ESCAPE call sites use the multi-frame settle path rather than silently reverting to the one-frame default. Do not create page-specific assertions for Sun or Neptune.

---

## 3. Focused tests — exactly once

After implementing the harness/test change, run exactly once:

```bash
cd tests
PYTHONPATH=../src:.. python3 -m unittest \
  test_encyclopedia_v01_headless_traversal.py \
  test_headless_greia_simulator.py \
  test_greia_simulator.py \
  test_activity_enciclopedia.py \
  -v
FOCUSED_RC=$?
cd ..
```

Required:

```text
FOCUSED_RC=0
```

If this fails: STOP. Do not repair and rerun during this evidence attempt. Return the exact first failure.

If green, run:

```bash
git diff --check
```

Then commit/push only your harness/test changes. Suggested message:

```text
Encyclopedia: settle headless page transitions before capture
```

Do not amend/rewrite the primary agent's Pyramids/Body commits.

---

## 4. Run the Encyclopedia source gate exactly once

Runtime Activity source changed after the previous green source gate, so a new source gate is required.

On a clean, pushed `main`, run exactly once:

```bash
python3 tools/encyclopedia_v01_source_gate.py
SOURCE_GATE_RC=$?
```

Required terminal disposition:

```text
SOURCE GATE PASS — Simulator acceptance is still pending.
```

If `SOURCE_GATE_RC != 0`: STOP. Do not fix and rerun. Return the source-gate evidence directory and first failure.

Do not generate voices. The gate's existing accepted-audio logic remains authoritative.

---

## 5. Run one fresh 43-page mechanical traversal exactly once

Only after the source gate is green:

```bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/encyclopedia-v01-acceptance/${RUN_ID}-visual-repair-recapture"
WORKSPACE="$HOME/.greia-simulator-encyclopedia-v01-recapture-${RUN_ID}"
mkdir -p "$EVIDENCE"
printf '%s\n' "$EVIDENCE" > ./tmp/encyclopedia-v01-acceptance/.latest-run

git rev-parse HEAD > "$EVIDENCE/starting-sha.txt"
git status --short > "$EVIDENCE/git-status-before.txt"

python3 tools/encyclopedia_v01_headless_traversal.py \
  --workspace-dir "$WORKSPACE" \
  --evidence-dir "$EVIDENCE" \
  --locale it \
  --viewport 1024x600 \
  2>&1 | tee "$EVIDENCE/mechanical-traversal.txt"
TRAVERSAL_RC=${PIPESTATUS[0]}
```

Use Bash so `PIPESTATUS[0]` is the real traversal exit code.

Required mechanical result:

```text
TRAVERSAL_RC=0
sections 6/6
entries 36/36
internal Back 36/36
protected Home -> Shell PASS
traversal-summary status PASS
```

Do not claim visual acceptance yourself.
Do not infer correctness from changed-pixel values.
Do not repair/re-run if it fails.

Preserve the exact child warning lines, including any recurrence of:

```text
libpng error: bad adaptive filter value
```

---

## 6. Final state + evidence ZIP

Regardless of traversal PASS/FAIL:

```bash
git diff --check > "$EVIDENCE/git-diff-check.txt" 2>&1
DIFF_RC=$?
git status --short > "$EVIDENCE/git-status-after.txt"
```

Source worktree must be clean after a PASS.

Create one evidence-only ZIP:

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

## 7. Return exactly this report

```text
STARTING_SHA=
HARNESS_FIX_COMMIT=
FOCUSED_TESTS=PASS/FAIL
SOURCE_GATE_RC=
SOURCE_GATE_EVIDENCE=
MECHANICAL_TRAVERSAL_RC=
SECTIONS_CAPTURED=<n>/6
ENTRIES_REACHED=<n>/36
ENTRY_BEFORE_AFTER_PAIRS=<n>/36
INTERNAL_BACK_RETURNS=<n>/36
PROTECTED_HOME_RETURN_TO_SHELL=PASS/FAIL/not-reached
TRAVERSAL_SUMMARY_STATUS=
CHILD_WARNINGS=<exact lines or none>
WORKTREE_AFTER=clean/dirty
FIRST_FAILURE=<none or exact stage/message>
EVIDENCE_DIR=
EVIDENCE_ZIP=
```

Also return:

- focused-test final summary;
- source-gate final summary/evidence directory;
- traversal PASS summary or failure tail;
- `traversal-summary.json`;
- child warning/error tail;
- PNG count and ZIP size;
- final `git status --short`.

Do not claim:

```text
visual/signature acceptance
pointer parity
pre-reader final acceptance
responsive acceptance
narration acceptance
```

The primary/vision reviewer will inspect the fresh ZIP, especially:

```text
space.sun-before / after
space.neptune-before / after
history.pyramids-before / after
sections/04-body.png
```

Only after that review will pointer/responsive acceptance proceed.
