# R4 closure patch — local validation

**Validation result:** PASS at source/test HEAD `44927e37dcb150d9fb6cbad7226a52c35c41bf91` — 3589 tests OK, 4 skipped; `make verify` exit 0. This file is retained as the reproducible validation procedure/evidence, not as pending routing. Session 03 is now open.

**Purpose:** validate the small post-R4 closure patch that makes hardware-support
bundle production fail closed, tightens archive-inspection arguments, updates
fixtures to use real valid support archives, and retires stale release/hardware
routing.

This validation is **source/test execution only**. Do not build an installer,
compose a Greia root, create release images, run debootstrap, invoke
`greia_release.py build`, run QEMU, mount/loop images, repartition storage,
flash media, boot the Acer, use Orbiter, run Docker, or perform any other
installer/image/hardware build operation on the owner's system.

## 1. Preconditions

From the Greia repository:

```bash
git pull --ff-only
git status --short
git rev-parse HEAD
git log --oneline -12
```

Requirements:

- working tree must be clean before testing;
- HEAD must contain the current closure-repair commits, including
  `865f8ae73fd0476dda6e1c7018bd96c0d7c9cf9a`, or a later descendant on
  `main`;
- do not edit source or tests during this validation run;
- use the repository's existing Python environment/dependencies.

If the tree is dirty before you start, STOP and report the paths. Do not reset,
stash, delete, or overwrite someone else's work.

## 2. Syntax/import smoke

Run:

```bash
PYTHONPATH=src python3 -m py_compile \
  src/greia_platform/system_updates.py \
  src/greia_installer/hardware_support_archive.py \
  tests/test_hardware_support_archive_verdicts.py \
  tests/test_update_v3_bundle.py \
  tests/test_system_updates.py \
  tests/test_system_update_service.py
```

Expected: exit 0, no traceback.

## 3. Focused regression suites

Run each command separately and record the exact result.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_hardware_support_archive_verdicts.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_update_v3_bundle.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_updates.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_update_service.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_support_outer_bound.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_candidate_support.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_release_cli_finalized_capacity.py' -v

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_greia_update_tool.py' -v

# High-fanout stale-fixture regressions found by the first validation attempt.
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_ab_install_composition.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_fresh_ab_install.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_persistent_layout.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_installed_release_identity.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_release_v2.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_update_streaming.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_install_streaming_memory.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_installer_identity_sequencing.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_t3_update_production.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_update_activation_contract.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_update_product_negatives.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_x8_sequenced_update.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_runner.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_product_recovery_d31_reverse.py' -v

# Second-validation regressions: malformed-runtime boundary, real missing
# device ordering, and x8 source-scope lifecycle harness.
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_candidate_support_streaming.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_bootchain.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_devproof.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_devrun3.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_lifecycle.py' -v
```

The important new predicates are:

1. a malformed supplied `hardware-support.tar.zst` is rejected by
   `build_update_bundle()` **before** a `.greiaupdate` output is published;
2. malformed parser-parity fixtures no longer require the production bundle
   builder to package invalid support;
3. valid support-carrying v3 bundles still round-trip;
4. `inspect_archive_file()` rejects expected SHA without expected size, and
   expected size without expected SHA;
5. supplying both expected facts still succeeds for a valid archive;
6. existing candidate-support single-pass/outer-bound/PERSIST behavior remains
   green.

Do not weaken an assertion to obtain PASS.


### Safety boundary for x8 source-scope tests

The named x8 tests above are permitted only as ordinary `unittest` source-scope
fixtures executed by the existing test suite. They must not invoke a real QEMU
run, product installer build, debootstrap/root composition, mount/loop device,
or media write. If any named test attempts such an operation on this host,
STOP that test and report it rather than granting privileges or changing the
host. Tiny disposable files created under Python temporary directories by unit
test fixtures are ordinary test state, not authorization to build Greia media.

## 4. Source-diff hygiene

Run:

```bash
git diff --check 67c7c445f4be6b7173070ddf1cdace4e434b04bd..HEAD
git status --short
```

Expected:

- `git diff --check`: exit 0;
- working tree still clean.

## 5. Full repository verification

Run with enough wall-clock allowance for the current suite (the previous
successful-to-completion runs took roughly 14–16 minutes). Capture the **entire**
output so a late error identity is never lost:

```bash
set -o pipefail
make verify 2>&1 | tee /tmp/greia-r4-closure-make-verify.log
```

Use a command timeout of at least 1200 seconds if the local agent/runtime imposes
one. A timeout is not a test failure; rerun with a sufficient timeout rather than
changing source.

Do not shorten this to a subset if the command is runnable locally. `make verify`
for this repository runs tests/validation/shell syntax/source-footprint checks;
it does **not** authorize building an installer or release image. If the local
Makefile changes so that `make verify` would invoke installer/image/root
composition work, STOP before running it and report that change.

If it passes, record:

- exact HEAD;
- total tests;
- skips;
- wall-clock duration if printed.

If it fails:

1. do **not** edit anything;
2. record the first failing test and complete traceback/error;
3. record whether focused suites above were green;
4. run the single failing test once in isolation only when its test path is
   obvious from the output;
5. report whether the isolated failure reproduces;
6. include `git status --short`;
7. stop.

Do not classify a failure as "pre-existing" merely because an older handover
said so. This validation is evidence for the current HEAD.

## 6. Documentation-routing sanity

Confirm manually by reading the files only; no browser/hardware action:

```bash
grep -n "HISTORICAL — DO NOT EXECUTE" HW-03-PHYSICAL-LEGS.md
grep -n "RELEASE_BUILD_FILESYSTEM_BYTES" docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
grep -n "1073741824\|1074790400" docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md || true
```

Expected:

- HW-03 has the retirement banner at the top;
- the release workflow uses release-specific placeholders;
- the old Acer payload flags `--filesystem-bytes 1073741824` and
  `--minimum-slot-bytes 1074790400` are absent from the active release
  workflow. A legitimate mention of a separate 1 GiB profile slot bound is
  not a failure.

## 7. Evidence to return

Return exactly this information:

```text
R4 CLOSURE VALIDATION

HEAD:
<full sha>

TREE CLEAN BEFORE:
yes/no

PY_COMPILE:
PASS/FAIL

FOCUSED:
test_hardware_support_archive_verdicts: <result>
test_update_v3_bundle: <result>
test_system_updates: <result>
test_system_update_service: <result>
test_support_outer_bound: <result>
test_candidate_support: <result>
test_release_cli_finalized_capacity: <result>
test_greia_update_tool: <result>
high-fanout stale-fixture regression set: <result>
second-validation regression set: <result>
test_lifecycle: <result>

DIFF_CHECK:
PASS/FAIL

MAKE_VERIFY:
PASS/FAIL
<test count / skips or first failure>

DOC_ROUTING:
PASS/FAIL

TREE CLEAN AFTER:
yes/no

FAILURE DETAILS:
<only if any>
```

No installer/image build and no physical acceptance are part of this validation.
