# Session 03 owner release CLI — local source validation

**Scope:** source/static/unit/integration validation only for the Session 03
owner release CLI implementation.

**ABSOLUTE HOST BOUNDARY:** do **not** build Greia artifacts on this machine.
Do not run `greia_release.py build` or `build-profile`; do not compose a
Greia root; do not run debootstrap/chroot composition; do not build an
installer, release image or payload; do not run real QEMU; do not mount or
create loop devices; do not write media; do not use Docker or Orbiter. The
commands below exercise only Python fake-runner/source contracts, shell syntax,
static repository validation and the existing source-level test suite.

## 1. Preconditions

```bash
git pull --ff-only
git status --short
git rev-parse HEAD
git log --oneline -15
```

Required:

- working tree clean;
- HEAD is current `main` and contains the Session 03 implementation;
- do not edit source/tests during this validation;
- do not run any command not listed below as an attempted workaround.

If the tree is dirty, STOP and report the paths. Do not stash/reset/delete
someone else's work.

## 2. Syntax only

```bash
PYTHONPATH=src:tools python3 -m py_compile \
  tools/greia_release.py \
  tools/build_release.py \
  tests/test_greia_release.py \
  tests/test_build_release.py

bash -n \
  build/lib/compose.sh \
  build/compose-release-profile.sh \
  build/populate-hardware-support-pool.sh
```

Expected: exit 0. These commands do not compose/build anything.

## 3. Focused source tests

Run separately and capture exact counts:

```bash
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_greia_release.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_build_release.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_build_profiles.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_release_cli_finalized_capacity.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_payload_receipt_binding.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_greia_update_tool.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_system_overlay_contract.py' -v
PYTHONPATH=src:tools python3 -m unittest discover -s tests -p 'test_hardware_support_archive_verdicts.py' -v
```

The new Session 03 tests must prove, without executing a real build:

- final release directory schema is stable;
- `doctor` checks Linux/x86_64/root/tools/profile support/workspace and fails
  closed;
- normal build orchestration uses the bounded
  `build/compose-release-profile.sh` adapter;
- target/live composition and hardware-support population remain shell-owned;
- the Python CLI calls existing payload/support/bundle producers rather than
  duplicating their logic;
- payload minimum is derived from the actual shrunk ext4 artifact when omitted;
- bundle construction consumes the producer receipt and profile file, with no
  manual uncompressed/minimum-size archaeology;
- failed builds never publish the final release directory and preserve scratch;
- successful fake-runner builds atomically publish one Acer update bundle,
  intermediates and a portable `release-report.json`;
- the report contains no stale `.greia-work` paths;
- media accounting matches the actual published directories;
- `write-media` retains the existing interactive exact-device confirmation;
- direct `compose.sh` and the Session 03 release composition adapter own
  bounded mount teardown.

Do not weaken assertions to obtain PASS.

## 4. Diff and shell hygiene

Use the R4-closeout documentation HEAD as the Session 03 baseline:

```bash
git diff --check 9bc2e74f393b565132266681c624b8405b9a607c..HEAD
make shell-check
git status --short
```

Expected: all clean. `make shell-check` is syntax/static shell checking only.

## 5. Full source verification

The repository's current `make verify` target is source/test validation
(`clean-bytecode test validate shell-check footprint`) and does not build the
installer/root/release artifacts. Confirm that fact from the Makefile before
running it. If the target has changed to invoke build/debootstrap/QEMU/mount
work, STOP and report the change.

Then run with a >=1200 second allowance and capture the entire log:

```bash
set -o pipefail
make verify 2>&1 | tee /tmp/greia-session03-source-verify.log
```

A timeout is not a product failure. If the runtime wrapper times out while tests
are still progressing, rerun with a larger timeout; do not change source.

## 6. Explicitly prohibited commands

Do **not** run any of these during this validation:

```text
sudo python3 tools/greia_release.py build ...
python3 tools/greia_release.py build ...
sudo python3 tools/greia_release.py build-profile ...
python3 tools/greia_release.py build-profile ...
tools/greia_release.py write-media ...
build/compose-release-profile.sh ...
build/lib/compose.sh --profile ... --role ...
build/build-image.sh ...
build/build-installer-image.sh ...
debootstrap ...
qemu-system-*
losetup ...
mount ...
```

Do not run `doctor` as a substitute for these tests; its host checks are
already covered deterministically through the injected source tests.

## 7. Evidence to return

Return:

```text
SESSION 03 SOURCE VALIDATION

HEAD:
<full sha>

TREE CLEAN BEFORE:
yes/no

PY_COMPILE:
PASS/FAIL

BASH_N:
PASS/FAIL

FOCUSED:
test_greia_release: <result>
test_build_release: <result>
test_build_profiles: <result>
test_release_cli_finalized_capacity: <result>
test_payload_receipt_binding: <result>
test_greia_update_tool: <result>
test_system_overlay_contract: <result>
test_hardware_support_archive_verdicts: <result>

DIFF_CHECK:
PASS/FAIL

SHELL_CHECK:
PASS/FAIL

MAKE_VERIFY:
PASS/FAIL
<test count / skipped / first failure>

TREE CLEAN AFTER:
yes/no

PROHIBITED BUILD COMMANDS RUN:
no

FAILURE DETAILS:
<only if any>
```

This validation can establish **Session 03 source correctness only**. A real
one-command Acer release build must later run on the appropriate supported
x86_64 Linux build host; it is not authorized on the owner's local machine by
this document.
