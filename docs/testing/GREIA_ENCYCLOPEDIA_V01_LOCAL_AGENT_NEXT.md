# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

This is the single rolling instruction for the **next** owner-machine task.

## Current proven state

The previous source-gate run stopped at `focused-tests` only because the gate built invalid unittest module names for this repository layout.

Already proven and committed/pushed:

- `cdb7b8d` — voice-ledger synchronization idempotency + strict row parsing regression coverage.
- `d62d63f` — canonical complete v0.1 voice-request ledger.
- `encyclopedia/VOICE_RECORDING_REQUESTS.md` is clean, canonical and contains exactly **378 rows**.
- `voice-sync` PASS.
- `voice-sync-check` PASS.
- `voice-row-count.json`: 378 rows, all currently `REQUESTED`.
- The focused Encyclopedia tests themselves pass when invoked from a valid unittest discovery/import context.
- The failed gate left the worktree clean.
- This task generates **ZERO voice files** and does **not** run the Simulator unless the source gate itself fully passes and you have returned the result first.

Previous evidence directory:

```text
tmp/encyclopedia-v01-acceptance/20260828_034742/
```

## Root cause to fix

`tools/encyclopedia_v01_source_gate.py` currently builds the focused command using dotted names such as:

```text
tests.test_activity_enciclopedia
```

but `tests/` is not a Python package (`tests/__init__.py` does not exist).

Do **not** add `tests/__init__.py` merely to satisfy the gate.
Do **not** change the test modules themselves.

Python `unittest` accepts test **file paths** from the repository root, so the gate should translate its stable dotted identifiers to paths such as:

```text
tests/test_activity_enciclopedia.py
```

---

## Step 1 — refresh and inspect

From the existing Greia checkout:

```bash
git branch --show-current
git status --short
git fetch origin
git pull --ff-only origin main
```

Required:

```text
branch = main
worktree = clean
```

If unrelated source is dirty, STOP and report it.

---

## Step 2 — fix only the gate command builder

Edit:

```text
tools/encyclopedia_v01_source_gate.py
```

Keep `FOCUSED_TESTS` and `POST_AUDIO_TESTS` as their existing stable dotted identifiers if desired, but `_focused_command()` must build valid file-path arguments for this repository layout.

A clean implementation is semantically equivalent to:

```python
def _focused_command(tests: Sequence[str]) -> tuple[str, ...]:
    paths = tuple(test.replace(".", "/") + ".py" for test in tests)
    return (sys.executable, "-m", "unittest", *paths, "-v")
```

This should turn:

```text
tests.test_encyclopedia_authoring_tools
```

into:

```text
tests/test_encyclopedia_authoring_tools.py
```

Do not add shell wrapping, `cd tests`, package markers or repository-global `PYTHONPATH` changes unless the path-based invocation demonstrably cannot work.

---

## Step 3 — add a regression test for the command builder

Edit:

```text
tests/test_encyclopedia_v01_source_gate.py
```

Import `_focused_command` from the loaded gate module and add a focused test proving that:

```python
command = _focused_command((
    "tests.test_encyclopedia_authoring_tools",
    "tests.test_activity_enciclopedia",
))
```

contains exactly these test targets:

```text
tests/test_encyclopedia_authoring_tools.py
tests/test_activity_enciclopedia.py
```

and does **not** contain:

```text
tests.test_encyclopedia_authoring_tools
tests.test_activity_enciclopedia
```

Also verify the command still begins with the current Python executable + `-m unittest` and ends with `-v`.

Do not weaken any existing source-gate tests.

---

## Step 4 — run only the repair test first

From the repository root run:

```bash
python3 -m unittest tests/test_encyclopedia_v01_source_gate.py -v
```

If it fails: STOP and return the failure. Do not continue.

Then prove the exact gate-built focused command works without running the whole gate:

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path
import subprocess
import sys

path = Path("tools/encyclopedia_v01_source_gate.py")
spec = importlib.util.spec_from_file_location("encyclopedia_source_gate_probe", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

command = module._focused_command(module.FOCUSED_TESTS)
print("COMMAND:", " ".join(command))
completed = subprocess.run(command, cwd=Path.cwd())
print("RETURN_CODE:", completed.returncode)
raise SystemExit(completed.returncode)
PY
```

Required:

```text
RETURN_CODE: 0
```

If it fails: STOP. Do not patch test content to force green.

---

## Step 5 — commit and push the gate fix

Stage only:

```text
tools/encyclopedia_v01_source_gate.py
tests/test_encyclopedia_v01_source_gate.py
```

Commit with a message such as:

```text
Encyclopedia: fix source-gate unittest invocation
```

Push to `origin/main`.

Record the commit SHA.

Confirm afterward:

```bash
git status --short
git rev-parse HEAD
```

Worktree must be clean.

---

## Step 6 — rerun the Encyclopedia source gate exactly ONCE

Run:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

Do not rerun on failure.
Do not repair during the gate.
Do not generate voices.
Do not start the Simulator manually.

### If it fails

STOP immediately and return:

- exact starting SHA;
- failing step + exit code;
- `FIRST_FAILURE.txt`;
- failed-step log;
- `git-status-before.txt`;
- `git-status-at-failure.txt`;
- `voice-row-count.json` if it exists;
- exact evidence-directory path;
- final `git status --short`.

Do not make another fix until the primary agent reviews that first failure.

### If it passes

Return:

- exact starting/current SHA;
- `source-gate-summary.json`;
- `voice-row-count.json`;
- `focused-tests.txt`;
- `make-verify.txt`;
- `voice-assets-check-before.txt`;
- integration/post-audio logs if they exist;
- `git-diff-check.txt`;
- `git-status-after.txt`;
- exact evidence-directory path;
- final `git status --short`.

A PASS means only:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Do **not** start the full Simulator traversal in this task. Stop and return the evidence first.
