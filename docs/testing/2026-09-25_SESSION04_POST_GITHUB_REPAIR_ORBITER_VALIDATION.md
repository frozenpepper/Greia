# Session 04 — post-GitHub repair Orbiter validation

**Required repair ancestor:** `cfe5b29d611fd6fae145105d4e14d2d7dc180791`

This file begins where the GitHub-side repair ends. Do not redesign the source
before running these checks unless a focused test proves a defect.

## 1. Synchronize and protect inputs

```bash
cd /home/orb/Works/Greia
git fetch origin
git pull --ff-only
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor cfe5b29d611fd6fae145105d4e14d2d7dc180791 HEAD
git status --short
df -h /
```

Require HEAD == origin/main, a clean tracked tree, and `cfe5b29d611fd6fae145105d4e14d2d7dc180791` to be an ancestor of HEAD. Do not pin to an older docs-only HEAD if origin/main has legitimately advanced.

Immutable S03 bundle:

```bash
S03_SHA=6c58601eaad32ad2bba30acb24e33333b9c4bbf3
VERSION=0.13.0-phase0-dev
S03="$PWD/tmp/session03-linux-release-${S03_SHA}/out/greia-${VERSION}"
BUNDLE="$S03/updates/acer-aspire-one-i386-ab.greiaupdate"
test -f "$BUNDLE"
sha256sum "$BUNDLE"
```

Required bundle SHA:

`6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67`

Do not modify the S03 release or the existing four Session-04 candidates.

## 2. Focused source validation

Run:

```bash
python3 -m unittest tests.test_installer_unit_contract
python3 -m unittest tests.test_install_transaction_service
python3 -m unittest tests.test_installer_seam_composition
python3 -m unittest tests.test_x8_qemu.test_session04_legs
```

Also rerun the existing product-install/ProductHarness focused suite used by
the previous Session-04 work. If its invocation is not in shell history, locate
it without changing source:

```bash
grep -R -l "ProductHarness" tests/test_x8_qemu tests | sort
```

Run the relevant unittest module(s). Ordinary bounded source/test defects may
be fixed autonomously, committed and pushed; do not stop for trivial repairs.

The tests must prove:

- shipped unit executes `greia_installer.transaction_service_entrypoint`;
- entrypoint imports canonical `transaction_service.main`;
- `transaction_service.py` is library-only;
- live composition returns the canonical `InstallTransactionService` class;
- exact capabilities are `CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID`;
- `NoNewPrivileges=yes` and `ProtectSystem=strict` remain.

## 3. Build a new installer from the unchanged S03 bundle

Use a new SHA-specific directory:

```bash
HEAD="$(git rev-parse HEAD)"
RUN="/tmp/greia-session04-${HEAD}"
INSTALLER_OUT="$RUN/installer"
mkdir -p "$INSTALLER_OUT"

sudo env PYTHONDONTWRITEBYTECODE=1 \
  build/build-legacy-x86-sd-installer.sh \
  acer-aspire-one-i386-ab \
  "$INSTALLER_OUT" \
  --release-bundle "$BUNDLE"
```

Do not rebuild Session 03.

## 4. Inspect the built installer before QEMU

Require the report/artifact to prove:

- profile `acer-aspire-one-i386-ab`;
- embedded bundle SHA equals the immutable S03 bundle SHA;
- 58 support packages;
- support installed ceiling 710070272;
- shipped unit ExecStart is
  `/usr/bin/python3 -m greia_installer.transaction_service_entrypoint`;
- capability bounding and ambient sets contain exactly the four named caps;
- `NoNewPrivileges=yes`;
- `ProtectSystem=strict`;
- the new entrypoint exists;
- no source `.pyc`/root-owned bytecode contamination.

Extract the live SquashFS read-only if needed, using the existing Session-04
inspection procedure. Do not alter the image while inspecting.

## 5. Prepare a new Session-04 run root

The verified candidate bundles currently live in the protected earlier run:

`/tmp/greia-session04-45c3d283717372cebd2636db860fc162f752f1ee/candidates/`

Copy, do not move, them into the new run:

```bash
mkdir -p "$RUN/candidates" "$RUN/results"
cp -a /tmp/greia-session04-45c3d283717372cebd2636db860fc162f752f1ee/candidates/. "$RUN/candidates/"
cp docs/testing/session04-evidence/s04driver.py /tmp/s04driver.py
```

Verify the four candidate SHAs against the recorded Session-04 report before
using them.

## 6. Diagnostic fresh-install confirmation

Temporary Session-04 diagnostics intentionally still exist in this build.
Run one install leg first:

```bash
sudo env \
  PYTHONDONTWRITEBYTECODE=1 \
  S04_HEAD="$HEAD" \
  SESSION04="$RUN" \
  S04_QEMU_TIMEOUT=3600 \
  python3 /tmp/s04driver.py install
```

Require:

- PREPARE -> PREPARED;
- only one canonical service implementation/module identity is observed;
- apt privilege drop no longer reports setuid/setgid/setgroups EPERM;
- hardware-support install completes;
- finalization receipt/markers are written;
- PERSIST initializes;
- GRUB A/B config exists, default A;
- FIRST_INSTALL_PENDING exists;
- EXECUTE returns INSTALLED, not an empty response.

If the service emits `faulthandler armed` twice in a way that still indicates
two module-global diagnostic states, stop only long enough to diagnose that
regression; do not proceed to lifecycle legs with unresolved split identity.

## 7. Remove temporary diagnostics after the confirming install

Once the diagnostic fresh install is green, remove the temporary Session-04
instrumentation from `transaction_service.py`, the temporary control-runner
termination/sampler additions, and tests that exist only to test `_S04_DIAG_*`.

Do NOT remove the permanent repairs:

- `transaction_service_entrypoint.py`;
- library-only `transaction_service.py` execution topology;
- exact four-capability unit contract;
- permanent canonical-entrypoint/class-identity/refusal regressions.

Commit/push the cleanup, then rebuild the installer again from the same S03
bundle and inspect it. The clean build must contain no Session-04 diagnostics.

## 8. Clean fresh-install acceptance

Run the install leg again against the clean rebuilt installer. It must reproduce
the full green fresh-install result. The diagnostic build alone is not final
acceptance.

## 9. Continue the complete lifecycle without stopping between green legs

Using the clean fresh-install output and existing driver:

```text
firstboot
seed
update
check-persist:update
unhealthy
check-persist:unhealthy
nonboot
check-persist:nonboot
persist
check-persist:persist
```

Run each as one driver invocation with the same `S04_HEAD`, `SESSION04` and
`S04_QEMU_TIMEOUT=3600` environment (the nonboot helper owns its shorter
candidate-attempt timeout).

Required final evidence:

- A first healthy acceptance;
- healthy A -> B stage and B commit;
- active slot isolation;
- actual selected support packages/dependency closure/installed-size bound;
- userspace-broken candidate recovers to accepted B;
- nonboot candidate plus reset returns to B;
- persist99 candidate is refused before inactive-slot mutation;
- PERSIST semantic continuity across all legs.

## 10. Final validation and closure

After all legs are green:

```bash
make verify
git diff --check
git status --short
```

Require no owned leftover mounts/loops, no root-owned source bytecode, no
temporary diagnostics, and a clean tracked tree. Update the active lifecycle
plan, root-cause report and HANDOVER with exact final evidence, commit/push,
mark Session 04 CLOSED and Session 05 OPEN.

Do not stop for ordinary implementation defects. Stop for owner input only if
new evidence requires a security/product change broader than the already
authorized exact four-capability contract or changes storage/rollback/PERSIST
policy.
