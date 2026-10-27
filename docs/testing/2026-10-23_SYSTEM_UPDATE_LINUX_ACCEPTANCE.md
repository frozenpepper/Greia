# System-update Linux build, install and Parent acceptance

> **2026-10-27 UPDATE — DETAILED REFERENCE, NOT THE CURRENT TOP-LEVEL EXECUTION GATE.** For owner-authorized current-source A/B repair and consolidated Linux/QEMU acceptance, use [Greia update release acceptance](GREIA_UPDATE_RELEASE_ACCEPTANCE.md). This older document retains useful low-level build, boot, rollback and fault-case details, but its pinned SHAs, historical "current" retry links and required stop/rebuild stages do not override the single live guide. Do not reuse old-source bundles as proof of current behavior.

Date: 2026-10-23. Status: **UNPROVEN runtime work order**, under Session 04 of
`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`.
Implementation source freeze: `4eaad25471fe47b72e900ea2f34777f41be5542b` (770 affected tests
OK, 2 skipped, after commit). Later documentation-only commits preserve that
source boundary. The full repository gate remains NOT GREEN as detailed in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`.
The owner requested this committed handoff for another agent on another machine.
Do not run image composition, mounts, QEMU or installation on the Mac.

The aim is a reliable family update path: download, prepare the inactive slot,
explicit restart at the profile picker, healthy acceptance or rollback, and
surviving child data. No release signing, anti-tampering system, penetration
exercise or new deployment framework belongs in this acceptance.

**Scope update (2026-10-24):** This work order still owns blank-disk BIOS
installation, A/B slot, PERSIST, v3 bundle health and rollback acceptance.
Typed `.greia_update` Python/Activity/combined application packages and their
single-root/bootstrap requirements are a separate acceptance in
`2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`. The source SHA and older mobile or
HTML pins in the historical command example below are not the current
package implementation boundary; use the exact final committed `main` SHA and
matching Parent pins recorded in current `HANDOVER.md`. Do not execute against
the earlier pinned SHA and report package acceptance.

## Current execution route after the Linux report (2026-10-25)

For the initial clean-source A/B smoke only, use the short, current route in
[`2026-10-25_AB_SMOKE_RETRY.md`](2026-10-25_AB_SMOKE_RETRY.md). It rebuilds
both experimental bundles and a clean matching installer from one committed
`main` SHA, then runs install → first boot → healthy A-to-B with the existing
`ProductHarness`. Its role-aware hash interpretation supersedes the older
active-slot raw-hash stop wording in this document for a slot booted during
observation. This does not waive wrong-slot, release-identity, health, PERSIST,
or unbooted-inactive-slot checks.

This document remains the authority for later A/B rollback, reverse-update,
Parent and full-system fault legs; the 2026-10-24 work order owns package
acceptance and its later fault recipes. Sections below are historical context
where they conflict with the short retry route; do not use their prior pinned
source, old bundles, patched installer, or old active-slot raw-hash predicate
as execution authority. The older v3 online-only statements about uploads and
data-only/delta packages apply only to that v3 route, not ADR 0038 `.greia_update`
application packages. Ordinary owner-release commands below remain the
release procedure and are not a workaround for experimental fixture gates.

## 1. Machine and source

Read `SETUP.md`, `AGENTS.md`, `HANDOVER.md`, the lifecycle plan and the OS-work
skill. Use an x86_64 Debian/Ubuntu Linux build host with the documented Greia
build prerequisites, root/sudo and disposable disk space. Use current `main`;
preserve unrelated work. Record exact Greia SHA, HTML pin, mobile SHA, host/tool
versions and every artifact SHA/byte count. Do not use GitHub Actions.

Run in Bash from the repository root; choose an absolute evidence path outside
the checkout with ample free space, then keep it for the whole run:

```bash
set -euo pipefail
git pull --ff-only
git status --short
export SOURCE_HEAD="$(git rev-parse HEAD)"
export UPDATE_EVIDENCE="/var/tmp/greia-update-$SOURCE_HEAD"
export GREIA_RELEASE_VERSION="$(cat VERSION)"
mkdir -p "$UPDATE_EVIDENCE"
git rev-parse HEAD > "$UPDATE_EVIDENCE/source-head.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
make verify 2>&1 | tee "$UPDATE_EVIDENCE/make-verify.log"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/run_tests.py \
  test_ab_install_composition test_fresh_ab_install test_installer_persist \
  test_fstab_single_owner test_update_product_composition \
  test_update_product_negatives test_update_seam_composition \
  test_update_privileged_bridge test_parent_update_delivery \
  test_x8_qemu.test_session04_legs -v \
  2>&1 | tee "$UPDATE_EVIDENCE/focused-tests.log"
```

A test failure is a failure, not installed evidence. Preserve the first real
error; fix its owner, commit on `main`, and restart the affected acceptance with
the new SHA. Do not weaken compatibility, health or data-survival predicates.

## 2. Build a real baseline and installer

Use the existing owner tool, not a hand-built payload or copied old bundle:

```bash
sudo -E python3 tools/greia_release.py doctor --output "$UPDATE_EVIDENCE"
sudo -E python3 tools/greia_release.py build \
  --version "$GREIA_RELEASE_VERSION" --output "$UPDATE_EVIDENCE/releases" \
  2>&1 | tee "$UPDATE_EVIDENCE/release-build.log"
export UPDATE_RELEASE="$UPDATE_EVIDENCE/releases/greia-$GREIA_RELEASE_VERSION"
export UPDATE_BASE_BUNDLE="$UPDATE_RELEASE/updates/acer-aspire-one-i386-ab.greiaupdate"
python3 tools/greia_release.py inspect "$UPDATE_RELEASE/release-report.json"
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE"
sudo -E build/build-installer-image.sh acer-aspire-one-i386-ab \
  "$UPDATE_EVIDENCE/installer" --release-bundle "$UPDATE_BASE_BUNDLE" \
  2>&1 | tee "$UPDATE_EVIDENCE/installer-build.log"
export UPDATE_INSTALLER="$UPDATE_EVIDENCE/installer/greia-os-installer-acer-aspire-one-i386-ab.img"
sha256sum "$UPDATE_BASE_BUNDLE" "$UPDATE_INSTALLER" > "$UPDATE_EVIDENCE/artifacts.sha256"
```

Keep failed build scratch trees and package caches. Check the real finalized
slot footprint against the profile's 1536 MiB slots; current four-language
content must fit with finalizer reserves. Do not raise capacities to hide a
failure. The current release matrix is Acer A/B only. A successful build is
not a universal Setup image, UEFI or Raspberry Pi certification.

For a second distinct healthy release, use another real composed v3 bundle
built from these source fixes with a different release ID/version. If none
exists, create a disposable **main checkout copy** under the evidence root,
change only `VERSION` to an acceptance-only newer version, record its patch,
and run the same owner build there. Do not publish that fixture as an owner
release. Do not relabel an old incompatible payload. Set
`UPDATE_NEXT_BUNDLE` to that actual bundle before the next section.

## 3. Execute the existing product harness

Use `tools.x8_qemu.product.ProductHarness` without fake callbacks. Its control
seam masks the graphical installer on the disposable clone, drives the real
shipped installer transaction over its socket, then verifies the target image
through production disk parsers. This is automated installer/service proof,
not rendered graphical installer evidence and not a replacement updater. Do
not run the historical generic runner and call it product proof. Never supply
a `/dev/...` path.

```bash
: "${UPDATE_NEXT_BUNDLE:?set the real second release bundle path}"
export UPDATE_NEXT_BUNDLE
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. python3 - <<'PYCODE'
import json, os, zipfile
from pathlib import Path
from tools.x8_qemu.lifecycle import LifecycleConfig
from tools.x8_qemu.product import ProductHarness
root = Path(os.environ["UPDATE_EVIDENCE"]) / "vm"
def harness(name, **kwargs):
    return ProductHarness(LifecycleConfig(output_dir=root / name,
        timeout_seconds=1200, memory_mib=1024, cpus=1, keep_image=True), **kwargs)
def save(name, result):
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    assert result.get("ok") is True, result
base = Path(os.environ["UPDATE_BASE_BUNDLE"])
next_bundle = Path(os.environ["UPDATE_NEXT_BUNDLE"])
with zipfile.ZipFile(next_bundle) as archive:
    next_id = json.loads(archive.read("manifest.json"))["release_id"]
with zipfile.ZipFile(base) as archive:
    base_id = json.loads(archive.read("manifest.json"))["release_id"]
assert next_id != base_id, (base_id, next_id)
save("install", harness("install", official_image=Path(os.environ["UPDATE_INSTALLER"]),
    release_bundle=base).run_product())
installed = root / "install/product/disposable-target.img"
save("first-boot", harness("first-boot", release_bundle=base).run_first_boot_product(
    installed_image=installed, expected_release_id=base_id))
accepted_a = root / "first-boot/product/firstboot-clone.img"
save("healthy-update", harness("healthy-update").run_boot_health_product(
    installed_image=accepted_a, release_bundle=next_bundle,
    expected_release_id_b=next_id))
PYCODE
```

Check the on-disk record, grubenv and journal, not only acknowledgments:

- Fresh install writes A, initializes B without cloning A, and initializes the
  canonical PERSIST schema. First healthy A boot clears first-install pending.
- PERSIST is mounted by its verified UUID at `/run/greia-persist`; `/boot` is
  the verified shared boot-control filesystem. Mounts precede first-boot,
  boot observer/health, Parent and iwd as required.
- `/etc/greia-os/layout` is a directory bind to PERSIST's layout-authority
  namespace. Atomic replacement of `installed-layout.json` succeeds and a
  fresh read through either slot sees the new record; no file bind remains.
- The one transaction journal is `/run/greia-persist/greia/boot-journal`.
  First-install and update health use that same authority.
- The schema marker is `/run/greia-persist/greia/persist-schema.json`.
  A slot-local fabricated marker must not make readiness true.
- Update B is finalized through the **exact shipped systemd updater unit**,
  including real offline APT hardware-support application. Capture unit
  properties, journal, task peak and memory peak. A mock runner does not prove
  its capability set/TasksMax can finish.
- Accepted A remains unchanged by staging B; after healthy B boot, grubenv,
  journal, mounted root and layout record agree on B and its release ID.

Then run the existing `run_userspace_failure_product`,
`run_nonboot_failure_product`, `run_persist_refusal_product` and
`run_recovery_d31_reverse_product` legs on separate clones of
`vm/healthy-update/product/installed-clone.img`. Use the existing
`build_unhealthy_candidate_bundle` and `build_nonbooting_candidate_bundle`
helpers for disposable bad candidates, retaining actual base hardware-support
bytes. Give every fixture a distinct release ID. Create the schema-refusal
fixture through the existing v3 builder with a read range excluding schema 1.
Keep its payload structurally valid. These helpers and their exact keyword
contracts live in `tools/x8_qemu/product.py`; do not invent a second engine.

Required outcomes: unhealthy userspace times out and recovers to accepted B;
missing-kernel candidate cannot become default and reset returns to B;
incompatible schema is refused before slot mutation; recovery preserves the
accepted slot; a subsequent healthy update targets A and commits. Repeat a
normal A→B→A cycle. Record active/inactive hashes and recovery reasons.

Seed disposable child profiles, creations, settings, pairing credentials and
Wi-Fi state before the update. Verify identical logical values after success,
rollback and reverse update. Interrupt once during receive and once during
inactive-slot write: restart must reconcile without accepting incomplete bytes
or modifying the active slot. Retain negative evidence.

## 4. Parent product path on the installed guest/device

Use the committed HTML pin and the matching mobile shared-core pin. Run the
HTML `npm test` and Mobile `npm run verify`; preserve complete logs and distinguish
known baseline failures from new regressions. Pair normally using the existing
HTTPS procedure; do not place credentials in evidence or Git.

Use an operator-selected reachable HTTPS fixture index with the real candidate
bundle. Configure only Greia's image/service-owned
`GREIA_SYSTEM_UPDATE_INDEX_URL` and `GREIA_SYSTEM_UPDATE_CHANNEL=dev`; the
Parent submits no URL. The production URL stays the existing FrozenPepper
index until actual release publication. Test both HTML and Mobile:

1. Check updates; show installed identity and only exact profile/family/arch/
   board-compatible candidates. Board-neutral `null` is valid, malformed board
   data is not. Known current/older releases must not masquerade as a new update.
2. Prepare by returned release ID. Check progress, then close the browser/app.
   Reconnect: the same durable job continues. Restart Parent during download and
   after staging; reconcile without duplicate active-slot work.
3. Keep calling GET `/api/v1/system/update` and another ordinary Parent route
   while staging runs. Reads remain responsive; they must not wait for the
   serialized root socket. Double taps/uploads cannot replace a busy candidate.
4. At ready-to-restart, keep a child profile active: explicit restart is refused.
   Return to the real profile picker and confirm restart. Missing, unreadable or
   malformed profile state is not idle proof. Race profile selection against
   restart: exactly one wins, and no child is interrupted after activation.
5. Drop the restart response, refuse the systemd handoff once, and restart the
   Parent process around handoff. Show a recoverable result and permit an
   explicit retry when safe; never reboot automatically merely on reconnect.
6. After reboot/reconnect, show **updated** or **rolled back** from the actual
   journal. Check all four Parent locales and preserved child data.
7. Check manual upload's current limit explicitly: it receives the file but
   cannot complete offline preparation without catalog selection. Record this
   as DEFERRED product scope, not a successful offline update.
8. On `legacy-x86-i686` / RC single-root, show activation unavailable and a clear
   need for an A/B reinstall; no pretend in-place migration. Bad/missing PERSIST,
   wrong profile/board, truncated bundle, low storage and disconnected network
   produce understandable failures and preserve the usable installed system.

## 5. Owner pipeline and publication

This section is for actual owner release artifacts only. The experimental
acceptance-fixture report is rejected by `build_update_index.py` and must not
be passed here. For owner releases, the pipeline stays small: owner release build → inspect → generate a static
index → upload immutable artifacts → replace index last. Build EN/IT/ES/FR notes:

```bash
python3 tools/build_update_index.py --release "$UPDATE_RELEASE" \
  --base-url "https://www.frozenpepper.it/greia/updates/$GREIA_RELEASE_VERSION" \
  --channel dev --index "$UPDATE_EVIDENCE/greia-updates.json" \
  --notes-en "$UPDATE_EVIDENCE/notes-en.txt" \
  --notes-it "$UPDATE_EVIDENCE/notes-it.txt" \
  --notes-es "$UPDATE_EVIDENCE/notes-es.txt" \
  --notes-fr "$UPDATE_EVIDENCE/notes-fr.txt"
```

Preserve the existing `parents_app` block/other channel by starting from the
current index using shared `site-ftp`. Its skill owns exact upload/download
commands and publication approval. Preview the actual files, upload bundle
first, verify public size/hash/download, then atomically replace the index.
Never publish acceptance-only fixtures. Do not enable hosted Actions or invent
a signing-key ceremony. A future local/self-hosted scheduler can invoke these
same commands after owner-selected release acceptance.

Current transport is the full compressed v3 slot bundle. Measure its actual
bytes, peak RAM, scratch storage, preparation time and idle-service cost on
this build. For a representative Python-only change, report those numbers
beside the changed-file bytes. No delta or data-only package route is accepted
here; choose a smaller transport only after measurement and a separate bounded
design that retains the same inactive-slot writer, health and rollback owners.

## 6. Return evidence and next state

Return a Markdown result containing source/client SHAs; host; commands and exit
codes; artifact hashes/sizes; logs/screenshots; exact mounted UUIDs and fstab;
first-install/update/rollback journals; accepted/default/root identities; child
data checks; service task/RAM peaks; transfer measurements; and every failure.
Update HANDOVER and append the lifecycle ledger honestly. Keep Session 04 OPEN
until its real product criteria pass. VM proof does not certify Acer hardware.

Physical installation is a separate final pass on a named, owner-approved
**disposable** target through the existing graphical installer and media writer.
This handoff supplies no physical disk identity and authorizes no guessed disk
wipe. Ask for the target only when that physical pass is actually ready.

## 7. Evidence snapshot correction and BIOS boot gate (2026-10-24)

This addendum is append-only and does not replace the Oct 23 work-order
criteria. At the evidence snapshot, the work-order file is untracked and Greia
source changes are uncommitted. Checkout `HEAD`
`2fd29dffa75edc3ce5edd16431a86e6722a68830` is only the base revision; it does
not identify the current implementation. Do not start the external run from
that SHA or from a partial copied worktree. First commit the complete intended
source and handoff on the canonical branch, then record the exact resulting
source SHA and rerun the required local checks against that commit.

The available integrated source run (37 modules, 743 tests, 2 skips), 33 boot
health issuer tests, 32 recovery tests, and 76 product/GRUB tests all predate a
pending BIOS installer fix. Keep those results explicitly **pre-fix**. The
full-suite evidence is not green: the initial run reported 5,876 tests with 17
failures, 28 errors, and 8 skips; later runs aborted with signal 6 during
`typography.clear` in the Activity tempo test. Detailed output and baseline
comparisons are in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md` and
`/tmp/greia-update-completion/`. No Linux build, QEMU guest, installation,
authenticated Parent browser/device, or physical device run has been completed.

After the BIOS installer fix is committed and its final focused test result is
recorded, add this explicit first product predicate to the Linux run: from a
blank disposable VM disk, install in BIOS (not UEFI) mode, detach the installer
media, and boot the installed target through BIOS GRUB into Greia. Preserve the
BIOS firmware configuration, boot capture/serial evidence, install result,
partition table, installed MBR/GRUB state, and `grubenv` default-slot/journal
result. A successful installer return, a present `grub.cfg`, fake runner, or
source test does not prove that GRUB boots. The BIOS leg is separate from EFI
acceptance and is required before proceeding to healthy A/B update legs.

Source/client references for this snapshot are HTML pin
`e0116787bb324ca4685ad832cbc8d4d9e5b3461d` (pushed) and Mobile commit
`06441e56e5e38d6e4a70f6e435d9d4ea7f339273` (local; no remote). Update those
references only from the actual committed client pins used by the external
runner. Session 04 stays OPEN until the Linux product predicates and their
evidence are complete.

## 8. Final local source-test snapshot (2026-10-24)

Append-only correction to §7: after the BIOS adapter fix settled, eight
focused suites passed 116 tests. The frozen 38-module source gate passed
**770 tests, 2 skipped** (`/tmp/greia-update-completion/focused-final-frozen.log`);
an independent fresh-process rerun passed the same count
(`/tmp/greia-update-completion/focused-final-bios-rerun.log`). The combined
116-test run is at `/tmp/greia-update-completion/bios-boot-combined-focused.log`.
An earlier combined attempt during source edits had one seam assertion failure;
the production runner/adapter assertion was corrected and the failure did not
recur in either final run. Preserve that earlier log; it is not a Linux boot
result.

The frozen-source full `make verify` process had not emitted a final summary
when this correction was recorded. Treat it as unresolved until its terminal
exit and complete log are reported. Do not infer a pass from the focused gate.
These local tests do not prove a built installer boots through BIOS GRUB. The
first Linux product run remains the blank disposable disk BIOS install in §3,
followed by detached-media boot through installed BIOS GRUB into Greia. Source
remains uncommitted and this work order untracked at this snapshot; the
external runner must use the later exact committed source SHA, not base
`2fd29dffa75edc3ce5edd16431a86e6722a68830`.

## 9. Completed frozen-worktree full gate (2026-10-24)

Correction to §8: the frozen-worktree full gate has now finished. Its log is
`/tmp/greia-update-completion/make-verify-frozen-bios.log`: **5,890 tests in
302.538 seconds, FAILED with 7 failures, 3 errors, 8 skipped**. The full gate
is NOT GREEN. Nine outcomes match separately reproduced clean-baseline issues:
Foresta Parole content (3), Parent Wi-Fi assertions (2), MBR diagnostic (1),
ARM64 profile resolution (1), and installer-state/macOS `lsblk` behavior (2).

The extra full-run failure is the launcher long-session memory test, which
measured 675,948 retained-surface bytes after 24 launches against a 524,288
byte bound. Its isolated two-test module passes on both baseline and current
worktrees (`memory-baseline.log`, 8.333 s; `memory-current.log`, 7.296 s).
The failure is therefore unresolved/order-dependent; do not classify it as a
baseline issue. The focused 38-module gate still passes 770 tests with 2
skipped, but does not clear the full gate. Linux install/BIOS boot and device
acceptance remain separate and unrun.

## 10. Experimental A/B VM fixture route (2026-10-24)

Use this route only when the production release build is correctly blocked by
the provisional boot-cover gate and the owner has authorized disposable Linux
VM testing. It was added to make the Acer A/B software-update harness runnable
without changing release eligibility. It does not accept the early framebuffer
cover, waive any profile/payload/slot/PERSIST/installer/boot-health checks, or
authorize release publication or physical/family-device use.

Start from the clean committed source SHA used by the acceptance work order.
Build the baseline fixture and installer with §2 of
`2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`; that section defines these exact
exports: `UPDATE_FIXTURE_VERSION`, `UPDATE_FIXTURE_ID`, `UPDATE_FIXTURE`,
`UPDATE_FIXTURE_REPORT`, `UPDATE_BASE_BUNDLE`, `UPDATE_INSTALLER`, and
`UPDATE_BASE_RELEASE_ID`. The fixture command keeps real profile sizing and
payload-receipt production; its separate `greia-acceptance-fixture-*`
directory/report and release ID are experimental. The update-index builder
rejects the experimental report.

Create two disposable source copies for later and reverse candidates. Change
only `VERSION` in each copy, record each one-line diff, and run the same
fixture command there. Keep the base checkout untouched. For the current
`0.13.0-phase0-dev` source these monotonically newer fixture versions are
`0.13.1-phase0-dev` and `0.13.2-phase0-dev`; if the repository version has
advanced, choose two newer versions and record them before running.

```bash
SOURCE_CHECKOUT="$(git rev-parse --show-toplevel)"
UPDATE_NEXT_VERSION=0.13.1-phase0-dev
UPDATE_REVERSE_VERSION=0.13.2-phase0-dev
UPDATE_NEXT_SOURCE="$UPDATE_EVIDENCE/fixture-source-next"
UPDATE_REVERSE_SOURCE="$UPDATE_EVIDENCE/fixture-source-reverse"
git clone --shared "$SOURCE_CHECKOUT" "$UPDATE_NEXT_SOURCE"
git clone --shared "$SOURCE_CHECKOUT" "$UPDATE_REVERSE_SOURCE"
printf '%s\n' "$UPDATE_NEXT_VERSION" > "$UPDATE_NEXT_SOURCE/VERSION"
printf '%s\n' "$UPDATE_REVERSE_VERSION" > "$UPDATE_REVERSE_SOURCE/VERSION"
git -C "$UPDATE_NEXT_SOURCE" diff -- VERSION > "$UPDATE_EVIDENCE/next-version.patch"
git -C "$UPDATE_REVERSE_SOURCE" diff -- VERSION > "$UPDATE_EVIDENCE/reverse-version.patch"
test -s "$UPDATE_EVIDENCE/next-version.patch"
test -s "$UPDATE_EVIDENCE/reverse-version.patch"
(cd "$UPDATE_NEXT_SOURCE" && sudo -E unshare --mount --propagation private -- \
  python3 tools/greia_release.py build-acceptance-fixture \
  --version "$UPDATE_NEXT_VERSION" --output "$UPDATE_EVIDENCE/acceptance-fixtures")
(cd "$UPDATE_REVERSE_SOURCE" && sudo -E unshare --mount --propagation private -- \
  python3 tools/greia_release.py build-acceptance-fixture \
  --version "$UPDATE_REVERSE_VERSION" --output "$UPDATE_EVIDENCE/acceptance-fixtures")
UPDATE_NEXT_FIXTURE="$UPDATE_EVIDENCE/acceptance-fixtures/greia-acceptance-fixture-$UPDATE_NEXT_VERSION"
UPDATE_REVERSE_FIXTURE="$UPDATE_EVIDENCE/acceptance-fixtures/greia-acceptance-fixture-$UPDATE_REVERSE_VERSION"
UPDATE_NEXT_BUNDLE="$UPDATE_NEXT_FIXTURE/updates/acer-aspire-one-i386-ab.greiaupdate"
UPDATE_REVERSE_BUNDLE="$UPDATE_REVERSE_FIXTURE/updates/acer-aspire-one-i386-ab.greiaupdate"
UPDATE_NEXT_RELEASE_ID="greia-acceptance-fixture-$UPDATE_NEXT_VERSION"
UPDATE_REVERSE_RELEASE_ID="greia-acceptance-fixture-$UPDATE_REVERSE_VERSION"
export UPDATE_NEXT_VERSION UPDATE_REVERSE_VERSION UPDATE_NEXT_SOURCE UPDATE_REVERSE_SOURCE
export UPDATE_NEXT_FIXTURE UPDATE_REVERSE_FIXTURE UPDATE_NEXT_BUNDLE UPDATE_REVERSE_BUNDLE
export UPDATE_NEXT_RELEASE_ID UPDATE_REVERSE_RELEASE_ID
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE" > "$UPDATE_EVIDENCE/base-bundle-inspect.json"
python3 tools/greia_update.py inspect "$UPDATE_NEXT_BUNDLE" > "$UPDATE_EVIDENCE/next-bundle-inspect.json"
python3 tools/greia_update.py inspect "$UPDATE_REVERSE_BUNDLE" > "$UPDATE_EVIDENCE/reverse-bundle-inspect.json"
sha256sum "$UPDATE_BASE_BUNDLE" "$UPDATE_NEXT_BUNDLE" "$UPDATE_REVERSE_BUNDLE" \
  > "$UPDATE_EVIDENCE/ab-fixture-bundles.sha256"
```

Before running the §3 A/B harness, verify all three manifest release IDs match
the exported fixture IDs and the reports carry
`artifact_class=experimental_acceptance_fixture` plus
`release_eligible=false`. Set `UPDATE_REVERSE_BUNDLE` before the §10 failure
driver. These artifacts are only disposable VM inputs: do not pass their
reports to `build_update_index.py`, publish them, or call their build success
release acceptance. Preserve build roots on failure. Record each VM predicate
as PASS/FAIL/NOT RUN; source tests and fixture construction do not prove a
Linux boot, A/B behavior, or physical acceptance.
