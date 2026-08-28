# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This file is the single rolling instruction for the **next** owner-machine task. Follow it exactly. Do not continue past the first unexpected failure.

## Current state

- `origin/main` includes `56b87b5` and `bbdc08d`.
- The local working tree intentionally still contains the first synchronized 378-row `encyclopedia/VOICE_RECORDING_REQUESTS.md` produced by the failed gate.
- Diagnostic result already established:
  - `CURRENT_ROWS = 378`
  - `NEXT_ROWS = 378`
  - `ADDED_KEYS = 0`
  - `REMOVED_KEYS = 0`
  - non-idempotency is only an accumulating `---` separator before batch 4.
- Do **not** discard or regenerate the ledger before this task.
- This task generates **ZERO voice files**.

## Goal

1. Fix the synchronizer separator idempotency bug.
2. Tighten the ledger row regex so an empty notes cell is valid but a missing notes column is not silently accepted.
3. Add regression tests for both behaviors.
4. Prove the preserved 378-row ledger is canonical and idempotent.
5. Commit/push the source fixes.
6. Commit/push the canonical 378-row ledger.
7. Run the deterministic Encyclopedia source gate exactly once.

Do not start the Simulator in this task.

---

## Step 1 — refresh safely

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
```

Required branch: `main`.

The dirty `encyclopedia/VOICE_RECORDING_REQUESTS.md` is expected and must be preserved.

Do not reset/clean/checkout it.

If unrelated source is dirty, STOP and report it.

---

## Step 2 — fix `sync_voice_requests.py`

In `encyclopedia/sync_voice_requests.py`, change `_manual_prefix()` so the preserved manual prefix stops **before the separator introducing batch 4**, rather than before only the `## 4` heading.

The function must become semantically equivalent to:

```python
def _manual_prefix(existing_text: str) -> str:
    """Keep instructions, vocabulary and the manually-owned E0 navigation batch."""
    marker = "\n---\n\n## 4. Requested batch "
    index = existing_text.find(marker)
    if index < 0:
        raise ValueError("cannot find first factual-batch boundary in voice ledger")
    return existing_text[:index].rstrip()
```

Do not change topic order, cue IDs, wording, filenames, paths, status ownership, or the 378-row invariant.

---

## Step 3 — tighten `voice_ledger.py`

The current parser fix correctly surfaced empty notes rows, but it is more permissive than necessary because it can accept the notes column being absent entirely.

Keep the table grammar strict. The final part of `ROW_RE` should require the notes column while allowing it to be empty, semantically equivalent to:

```python
ROW_RE = re.compile(
    r"^\| (?P<status>[^|]+?) \| `(?P<cue>[^`]+)` \| (?P<kind>[^|]+?) \| "
    r"(?P<speaker>[^|]+?) \| `(?P<voice>[^`]+)` \| (?P<locale>it|en) \| "
    r"(?P<text>.*?) \| `(?P<filename>[^`]+)` \| `(?P<path>[^`]+)` \| "
    r"(?P<notes>.*?)\|$"
)
```

`parse_ledger_rows()` already strips the parsed notes value; leave that behavior unchanged.

---

## Step 4 — add regression tests

Add focused tests to `tests/test_encyclopedia_authoring_tools.py` (or a new narrowly named provider-free test module if cleaner) proving all of the following:

### A. Render idempotency

```python
current = LEDGER.read_text(encoding="utf-8")
once = render_ledger(current)
twice = render_ledger(once)
self.assertEqual(twice, once)
```

### B. Empty notes cell parses

A normal ledger row ending with an empty notes cell (`... | |`) must parse and produce `notes == ""`.

### C. Missing notes column does not parse as a valid data row

Construct a malformed otherwise-row-like line that ends immediately after the backticked path (no ` | |` notes column). Confirm it is not returned as a parsed row.

Do not weaken duplicate-row rejection or any locked-status invariant.

---

## Step 5 — run only the focused repair tests

Run:

```bash
python3 -m unittest \
  tests.test_encyclopedia_authoring_tools \
  tests.test_encyclopedia_voice_batch_state \
  tests.test_encyclopedia_v01_source_gate \
  -v
```

If any test fails: STOP. Do not rerun. Return the failure.

---

## Step 6 — prove the preserved dirty ledger is now canonical

Do **not** run the mutating synchronizer yet.

Run:

```bash
python3 encyclopedia/sync_voice_requests.py --check
```

Expected:

```text
voice request ledger already synchronized
```

Then run:

```bash
python3 - <<'PY'
from pathlib import Path
from encyclopedia.sync_voice_requests import render_ledger
from encyclopedia.voice_ledger import parse_ledger_rows

path = Path("encyclopedia/VOICE_RECORDING_REQUESTS.md")
current = path.read_text(encoding="utf-8")
once = render_ledger(current)
twice = render_ledger(once)
rows = parse_ledger_rows(current)

print("ROWS       =", len(rows))
print("CHECK_EQ   =", current == once)
print("IDEMPOTENT =", once == twice)

assert len(rows) == 378
assert current == once
assert once == twice
PY
```

Required:

```text
ROWS       = 378
CHECK_EQ   = True
IDEMPOTENT = True
```

If not: STOP. Do not modify the ledger further.

---

## Step 7 — commit and push the source fixes

Stage only the source/test files changed in Steps 2–4. Do **not** stage the ledger in this commit.

Commit with a clear message such as:

```text
Encyclopedia: make voice ledger synchronization idempotent
```

Push to `origin/main`.

Record the commit SHA.

---

## Step 8 — validate and commit the canonical 378-row ledger

Before committing, run:

```bash
git diff --check -- encyclopedia/VOICE_RECORDING_REQUESTS.md
python3 encyclopedia/sync_voice_requests.py --check
python3 - <<'PY'
from pathlib import Path
from encyclopedia.voice_ledger import parse_ledger_rows
p = Path("encyclopedia/VOICE_RECORDING_REQUESTS.md")
rows = parse_ledger_rows(p.read_text(encoding="utf-8"))
assert len(rows) == 378
print("rows=378")
print("unique_keys=378" if len(set(rows)) == 378 else "duplicate_keys")
assert len(set(rows)) == 378
PY
```

If all pass, stage **only**:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Commit with a clear message such as:

```text
Encyclopedia: synchronize complete v0.1 voice request ledger
```

Push to `origin/main`.

This commits metadata/request rows only. It does not generate or accept narration.

---

## Step 9 — run the source gate exactly once

First confirm:

```bash
git status --short
git rev-parse HEAD
```

The worktree should be clean except legitimate ignored local staging/evidence state.

Then run exactly once:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

Do not rerun on failure.
Do not repair during the gate.
Do not generate voices.
Do not start the Simulator.

### On failure

STOP and return:

- exact starting SHA;
- failing step and exit code;
- terminal failure output;
- `FIRST_FAILURE.txt`;
- failed-step log;
- `git-status-before.txt`;
- `git-status-at-failure.txt`;
- exact evidence directory path;
- final `git status --short`.

### On PASS

Return:

- exact starting SHA;
- exact final SHA/current `git rev-parse HEAD`;
- `source-gate-summary.json`;
- `voice-row-count.json`;
- `focused-tests.txt`;
- `make-verify.txt`;
- voice-assets check/integration logs if present;
- `git-diff-check.txt`;
- `git-status-after.txt`;
- exact evidence directory path;
- final `git status --short`.

Do not call the Encyclopedia Simulator-accepted. A green source gate means only:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Stop there and return the evidence to the owner/primary agent.
