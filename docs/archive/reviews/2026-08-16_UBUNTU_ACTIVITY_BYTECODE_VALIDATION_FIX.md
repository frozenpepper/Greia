# Greia — Ubuntu Source Gate `f305aed` Activity-Bytecode Validation Fix

**Date:** 2026-08-16  
**Host:** owner-controlled Intel Mac mini / Ubuntu 24.04.4 LTS / x86_64  
**Failed tested commit:** `f305aed838104cd26b8330eea776a78525e88956`  
**Target installer profile:** `legacy-x86-i686`  
**Result before fix:** aggregate source gate FAIL; image build NOT RUN; SD write NOT RUN

## Preserved execution result

The local operator followed the fail-closed rerun runbook and ran:

```bash
bash tools/run_hardware_enablement_source_gate.sh
```

Results:

```text
focused hardware-enablement suite 1: 77 tests PASS
focused hardware-enablement suite 2: 32 tests PASS
full source suite / make verify tests: 530 tests PASS
make verify validate step: FAIL
aggregate gate exit: 2
image build: NOT RUN
SD write: NOT RUN
```

The operator correctly stopped before building physical media.

## Root cause

The `make verify` gate sequence is:

```text
clean-bytecode → test → validate → shell-check → footprint → clean-bytecode
```

`tests/test_core_creation_activities.py` loads the first-party Writing and
Painting Activities directly from the Activity source tree:

```python
WRITING = _load("greia_test_writing_activity", ROOT / "activities" / "writing" / "main.py")
PAINTING = _load("greia_test_painting_activity", ROOT / "activities" / "painting" / "main.py")
```

`importlib.util.spec_from_file_location` + `exec_module` compiles the module
and, unless suppressed, writes a bytecode cache:

```text
activities/writing/__pycache__/main.cpython-312.pyc
activities/painting/__pycache__/main.cpython-312.pyc
```

The subsequent `tools/validate_project.py` → `RuntimeManager.validate_package`
→ `PythonRuntimeAdapter.validate_package` forbids `__pycache__` directories
inside Activity packages (`forbidden_path_names`), producing:

```text
RuntimeValidationError: forbidden Python package directory: __pycache__
```

The Activity tree must remain bytecode-free (AGENTS.md: "Activity validation
intentionally rejects cached bytecode inside Activity folders"). This failure
was only reachable after the earlier Shell-input repairs made `make test`
pass, which is why it was not observed at `5182ba4…` or `8d05fbb…`.

## Fix

In `tests/test_core_creation_activities.py`, set Python's global
no-bytecode flag before the Activity modules are loaded:

```python
sys.dont_write_bytecode = True
```

This keeps the test's module-level import behavior intact while ensuring the
Activity tree is not polluted by bytecode caches that the validate stage
must reject. No production source, build script, or gate was modified.

## Verification

With the fix applied, the full authoritative gate exits `0`:

```text
focused hardware-enablement suite 1: 77 PASS
focused hardware-enablement suite 2: 32 PASS
full source suite / make verify: 530 tests PASS
project validation: PASS (4 Activities)
shell-check: PASS
footprint: PASS
aggregate gate exit: 0
```

## Evidence boundary

The aggregate source gate is now PROVEN at `f305aed…` + this fix on the
owner-controlled Ubuntu host. This does **not** prove a canonical installer
build, VM installation, or diverse physical-machine acceptance. Those
remain later stages per the rerun runbook.