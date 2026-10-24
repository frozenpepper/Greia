# System-update implementation evidence reconciliation

Date: 2026-10-24. Status: **SOURCE + LOCAL TESTS ONLY; Session 04 remains OPEN**.
This record reconciles the Oct 23 source integration with the logs available
for the current host. It does not certify an image, Linux guest, VM, or device.

## Revisions and provenance

- Implementation source freeze: `4eaad25471fe47b72e900ea2f34777f41be5542b`. The implementation was
  prepared on base `2fd29dffa75edc3ce5edd16431a86e6722a68830`; earlier
  working-tree runs retain that boundary. The post-commit run against the
  exact implementation commit executed 770 tests in 15.941s, **OK (2 skipped)**,
  `/tmp/greia-update-completion/focused-4eaad2547.log` (SHA recorded in log).
  Later documentation-only commits do not create new image/device evidence.
- HTML Parent App pin: `e0116787bb324ca4685ad832cbc8d4d9e5b3461d` (pushed).
- Mobile Parent App: `06441e56e5e38d6e4a70f6e435d9d4ea7f339273` (local commit;
  its checkout has no configured remote).
- No release bundle, installer image, index, or hosted Actions artifact was
  published or built for this evidence run.

## Implemented source scope

The existing v3 inactive-slot lifecycle is extended with actual PERSIST and
shared `/boot` ownership for first install, schema/layout records, and the
single first-install/update journal. `/etc/greia-os/layout` is a directory bind
to the PERSIST layout authority. Boot-health issuance, commit, and deadline
recovery use the shared journal. Parent has one durable background check,
download, verify, and prepare job through the existing inbox and typed root
socket; status reads use cached snapshots while root performs long staging.
Root owns final compatibility and activation decisions, including an explicit
profile-picker/no-active-child restart fence. The index builder and Parent UI
retain the existing static-index/full-bundle pipeline.

Source keeps activation unavailable on single-root legacy/RC installations.
Full compressed v3 bundles remain the only implemented transfer. Manual upload
can receive a bundle, but staging requires an online catalog selection and
re-resolution. Neither offline manual staging nor a Python-only delta is
implemented or measured. No signing, anti-tamper, or penetration-test framework
was added.

## Executed local checks

The initial integrated source run predates the BIOS installer correction: 37
affected modules, 743 tests, **OK, 2 skipped**,
`/tmp/greia-update-completion/focused-integrated-final.log`; its module list is
`/tmp/greia-update-completion/focused-modules.txt`. Separate pre-fix runs were
33 boot-health issuer tests, 32 recovery tests, and 76 product/GRUB review
tests. Logs are `boot-health-issuer.log`, `recovery.log`, and
`product-grub-review-fix.log` under `/tmp/greia-update-completion/`.

After the BIOS adapter fix settled, a focused 8-suite slice passed 116 tests
covering fresh A/B install, EFI/BIOS adapter, identity sequencing, installed
release identity, A/B composition, install RSS, streaming memory, and installer
seam composition. The combined frozen 38-module gate then passed **770 tests,
2 skipped** in 17.896 seconds at
`/tmp/greia-update-completion/focused-final-frozen.log`; an independent fresh
process passed the same 770 tests, 2 skipped, in 65.192 seconds at
`/tmp/greia-update-completion/focused-final-bios-rerun.log`. The 116-test log
is `/tmp/greia-update-completion/bios-boot-combined-focused.log`. An earlier
combined attempt during source edits reported one seam assertion failure;
after the assertion was corrected to inspect the actual `shell=False` runner
and adapter argv delegation, both clean 770-test reruns passed. Keep the failed
attempt in the ledger; it did not reproduce on the settled source.

The fresh-install BIOS seam is
`FreshAbInstallSeams.bios_bootloader_installer(target, boot_directory)`, bound
in `src/greia_installer/device_seams.py` through the existing disk-identity
revalidation and argument-array GRUB runner. These remain **source/fake-runner
tests**, not proof that BIOS GRUB boots a generated image or installed guest.

Source footprint check PASSed (`shell-footprint.log`, 460.9 MiB tracked source
footprint). Project validation still exits with the ARM64 target-builder error;
the same error is reproduced on the clean baseline in `baseline-validate.log`.
The isolated MBR observer suite has the same one message-expectation failure on
the current tree and clean baseline (`mbr-current.log`, `mbr-baseline.log`).
The clean-baseline focused comparisons record nine pre-existing issue
identities across activity state, ARM64 composition, unavailable macOS `lsblk`,
Parent image assertions, and MBR wording. Their outputs are the
`baseline-test_*.log` files in `/tmp/greia-update-completion/`.

`make verify` has **no completed frozen-source result in this snapshot**. The
frozen-source run `/tmp/greia-update-completion/make-verify-frozen-bios.log`
was still running and had no final unittest summary when checked. The first
full run executed 5,876 tests and reported 17 failures, 28 errors, and 8 skips
(`/tmp/greia-update-completion/make-verify.log`); that run overlapped source
work in progress. Later integrated and final runs both terminated with native
`Abort trap: 6` during test execution. The final faulthandler identifies
`src/greia_platform/typography.py:274` (`clear`) called by
`tests/test_activity_tempo_di_greia.py:555`;
`make-verify-integrated.log` and `make-verify-final.log` preserve both traces.
The integrated trace also printed three failures before aborting, so it has no
complete-suite summary. Do not translate these logs into a full-suite pass.

Mobile `npm run verify` completed `tsc --noEmit` and its 30 tests (30/30), then
the shared-core suite reported 83/89 with six failures
(`/tmp/greia-mobile-npm-verify-e011678-final.log`). Clean HTML baseline
`5518a9e` reported 76/82 with the same six failures
(`/tmp/greia-html-baseline-5518a9e-npm-test.log`). The focused HTML update
tests were reported 13/13 PASS; no reliable current full HTML package-suite log
is cited here. These results do not replace authenticated browser acceptance.

## Acceptance still owed

No Linux build host, image composition, QEMU VM, installed guest, physical
device, authenticated Parent browser, or mobile device was run. The external
work order in `docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md` owns
that work. Its first blank-disk BIOS install must prove that the installed
target actually boots through BIOS GRUB into Greia; a successful installer
return, generated config, or unit test alone is insufficient. Capture the
booted guest and on-disk GRUB/MBR state after the source and handoff are
committed and the external Linux run starts.

After that gate, still run the exact shipped updater systemd unit, healthy
A→B→A updates, interrupted receive/staging, bad userspace/kernel rollback,
PERSIST refusal, child-data survival, restart lost-response/refusal recovery,
Parent HTML/Mobile on the installed guest, and the manual-upload and
single-root negative cases in the work order. Keep each source, build, VM, and
device result labeled at its actual evidence tier. Session 04 remains OPEN.

## 2026-10-24 — Frozen-worktree full gate completed

This addendum supersedes the earlier note that the frozen full gate was still
running. `/tmp/greia-update-completion/make-verify-frozen-bios.log` completed
**5,890 tests in 302.538 seconds: FAILED, 7 failures, 3 errors, 8 skipped**.
The full gate is NOT GREEN. Nine outcomes match separately reproduced clean-
baseline issues: three Foresta Parole content assertions, two Parent Wi-Fi
assertions, one MBR diagnostic expectation, one ARM64 profile resolution error,
and two installer-state errors caused by unavailable host `lsblk` behavior.

The remaining failure is
`test_launcher_long_session_memory.ShellLaunchCycleMemoryTests.test_repeated_launches_do_not_grow_shell_memory`:
retained surfaces measured 675,948 bytes after 24 launches against a 524,288
byte limit. The two-test memory module passed in isolation on both baseline
(`memory-baseline.log`, 8.333 s) and current (`memory-current.log`, 7.296 s)
trees. Therefore the full-suite-only failure is unresolved/order-dependent;
these standalone passes do not prove it is a baseline failure. Keep it as an
unresolved full-suite regression candidate. The focused 38-module gate remains
PASS at 770 tests, 2 skipped; it does not replace the red full gate or Linux
BIOS boot acceptance.
