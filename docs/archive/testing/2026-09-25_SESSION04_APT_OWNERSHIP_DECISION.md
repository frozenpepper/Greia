# Session 04: apt ownership capability decision report

**Date:** 2026-09-25
**Repository HEAD:** `7eb2be23e27a67a28d5c42bace65eb0be0c92bd8`
**Status:** Session 04 OPEN. Follow-up review found that the recorded `CAP_CHOWN` conclusion was premature: APT reports the observed `chown` failure as a warning and continues. No fifth capability is authorized. The next blocker is to capture the actual fatal package-command tail.

## 1. Decision status after follow-up review

The post-GitHub Orbiter validation reached a real non-zero package-command failure after the authorized four-capability repair:

```text
W: chown to _apt:root of directory /var/cache/apt/archives/partial failed
SetupAPTPartialDirectory (1: Operation not permitted)
```

The exact service unit currently authorizes:

```text
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID
AmbientCapabilities=CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID
NoNewPrivileges=yes
ProtectSystem=strict
```

The first report interpreted that warning as the cause of the non-zero `apt-get` exit. Follow-up review of Debian APT source shows that this inference is not proven: `SetupAPTPartialDirectory()` emits `WarningE` on failed `chown()` and continues. Greia's production runner then compounded the ambiguity by keeping only the first 256 stderr characters, which preserved the early warning and discarded any later fatal apt/dpkg/postinst reason.

Therefore **no `CAP_CHOWN` decision should be made yet**. The current exact four-capability contract remains authoritative until a rerun exposes the actual fatal tail.

## 2. Validation state before the decision

The required post-GitHub procedure was executed through its focused source and
Orbiter stages.

The repair ancestor was present:

```text
06341ad49cc6b7ff9ed5bda4ad8919051bceb9d4
```

`HEAD` and `origin/main` were synchronized at `46a654fd` before the new repair
tranche. The immutable S03 bundle was verified:

```text
6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67
```

Focused source results:

```text
test_installer_unit_contract       23 PASS
test_install_transaction_service   46 PASS
test_installer_seam_composition   13 PASS
test_x8_qemu.test_session04_legs   20 PASS
test_x8_qemu.test_product_install  38 PASS
hardware_support_install            3 PASS
installer_pool_mount_cleanup        6 PASS
installer_engine                   18 PASS
```

The combined affected final run was 65 PASS across the ProductHarness,
hardware-support, cleanup, and engine suites.

## 3. Repair history proven on Orbiter

The GitHub repair fixed the previous capability and module-identity failures:

1. `transaction_service_entrypoint` became the shipped executable wrapper.
2. `transaction_service.py` became library-only.
3. `CAP_SETUID` and `CAP_SETGID` were added for apt's privilege drop.
4. `NoNewPrivileges=yes` and `ProtectSystem=strict` remained enabled.

The first rebuilt diagnostic image proved the service and artifact contract,
then exposed a target-chroot defect:

```text
E: Can not write log (Is /dev/pts mounted?)
posix_openpt (2: No such file or directory)
```

The shared `mount_chroot_filesystems` helper was added to mount `dev`, `proc`,
`sys`, and `run` into the mounted target before the offline apt operation. The
legacy engine now reuses the same helper, so there is one implementation.

The next diagnostic run reached apt package configuration, then cleanup failed:

```text
umount: /run/greia-slots/slot-a-<pid>: target is busy
```

The installer cleanup wrapper was extended from one best-effort `umount` to a
bounded normal-then-lazy detach policy, with regression coverage. The legacy
engine already used the same policy.

The latest diagnostic run is the first run after both repairs:

```text
PREPARE: PREPARED
EXECUTE: reached package configuration
Failure: chown _apt:root on /var/cache/apt/archives/partial
```

Committed evidence:

```text
docs/testing/session04-evidence/post-repair-04-cap-chown-refusal.log
```

The response payload was a bounded `ERROR` refusal, not an empty response and
not an unexplained process death. The test-only control trace exposed the
underlying apt reason that the ordinary client intentionally hides behind its
wrong-op guard.

## 4. Why `CAP_CHOWN` is not yet justified

`CAP_SETUID` and `CAP_SETGID` allow apt to transition from root to its `_apt`
sandbox user. They do not allow the root-owned installer service to change
ownership of the apt partial-cache directory to `_apt:root`.

The failing operation is an ownership change, not a process credential change:

```text
chown(_apt, root, /var/cache/apt/archives/partial)
```

APT does attempt `chown()` under the current sandbox, but its own acquisition setup treats that failure as a warning. The observed warning is therefore evidence that `CAP_CHOWN` is absent, **not evidence that the missing capability caused the command's non-zero exit**. A later stderr line may carry the real fatal reason.

The current service deliberately grants only the capabilities already proven necessary. Adding another capability remains a deliberate security decision and is deferred until executable evidence identifies an operation that is actually fatal.

## 5. Deferred option — add CAP_CHOWN only if the fatal tail proves it

### Change

Add `CAP_CHOWN` to both the capability bounding set and ambient capability set:

```text
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID CAP_CHOWN
AmbientCapabilities=CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID CAP_CHOWN
```

Keep unchanged:

```text
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
RestrictAddressFamilies=AF_UNIX
SystemCallArchitectures=native
LimitCORE=0
TasksMax=8
ReadWritePaths=...
```

### Advantages

- Directly matches the operation apt is attempting.
- Preserves apt's normal `_apt` privilege-drop design.
- Preserves `NoNewPrivileges` and the strict filesystem posture.
- Does not grant network, mount-policy, ptrace, or raw device authority beyond
  the existing install boundary.
- Keeps the offline local-pool package path standard and auditable.
- Is the smallest capability delta that addresses the observed failure.

### Costs and risks

- The service gains the ability to change file ownership anywhere its existing
  `CAP_SYS_ADMIN` mount boundary can reach.
- This is broader than the already authorized exact four-capability contract.
- The unit contract tests and documentation must be updated from "exact four"
  to the newly accepted exact five.
- A fresh QEMU install is still required after the change; source tests cannot
  prove apt behavior inside the guest.

### Required proof after authorization

1. Update the unit and capability contract tests.
2. Update the unit documentation and capability rationale.
3. Rebuild the diagnostic installer from the unchanged S03 bundle.
4. Inspect the built unit and live root.
5. Run one fresh install and require `EXECUTE INSTALLED`.
6. Verify no `CAP_CHOWN`-related cleanup or ownership error remains.
7. Only then remove temporary diagnostics and run clean acceptance.

## 6. Deferred option — change apt ownership behavior only if required

### Change

Keep the capability set at four and make the offline apt operation avoid
requiring a root-to-`_apt` ownership transition in the mounted target.

Possible implementation directions to investigate, none yet accepted:

- configure apt's sandbox user and group explicitly;
- pre-create the apt partial directory with the exact final ownership before
  invoking apt;
- use a bounded apt/dpkg option that disables the ownership setup path;
- run the specific apt operation as root and explicitly accept the reduced
  privilege separation.

These are not equivalent. The first three may preserve the capability set but
must be proven not to weaken the offline verification, cleanup, or package
integrity boundaries. Running apt as root changes the privilege model of the
package operation and needs a separate security rationale.

### Advantages

- Preserves the exact four-capability unit contract.
- No new ambient or bounding capability is exposed to the service.
- Potentially keeps the service's capability surface unchanged.

### Costs and risks

- No option has been proven against the real target payload and apt version.
- Pre-created ownership may be fragile across payload layouts and may conceal
  a real integrity requirement.
- Running apt as root may remove an intentional privilege boundary.
- apt/dpkg options can be version-sensitive and are not automatically
  self-documenting Greia policy.
- It may still require a real QEMU run to prove that later cleanup and package
  configuration complete.

### Required proof before acceptance

1. Select one exact ownership/privilege policy.
2. Add a focused test that fails without the policy and passes with it.
3. Document why the policy is safe for an offline verified pool.
4. Rebuild and run one fresh install.
5. Verify package records, receipts, selected dependency closure, and cleanup.
6. Keep the four-capability unit unchanged.

## 7. Options explicitly not recommended

### Remove NoNewPrivileges

This is broader than the demonstrated operation and weakens the accepted
service posture. It should not be selected merely to make apt proceed.

### Run the whole service unprivileged or relax the whole sandbox

This would change unrelated platform protections and is not justified by the
current evidence.

### Chown from a separate unrestricted helper

This would create a second privileged path around the bounded service and
violate the fail-closed ownership model.

## 8. Current repository state

Committed repair tranche:

```text
7eb2be23 fix(installer): mount chroot filesystems for apt
```

The tranche contains:

- shared target chroot filesystem mounts;
- normal-then-lazy bind cleanup;
- focused regression coverage;
- the bounded test-only execute-response trace;
- the post-repair refusal evidence;
- HANDOVER and lifecycle-plan updates.

The current installer artifacts and disposable QEMU scratch are not acceptance
artifacts. The latest diagnostic image was built from the unchanged S03 bundle
and the current source. The blocked QEMU was stopped; no Session-04 mounts or
loops remain. Approximately 75 GB was free at cleanup.

Temporary Session-04 diagnostics remain because fresh install is not green.
They must be removed after the authorized repair and a confirming install, as
required by the post-GitHub validation procedure.

## 9. Acceptance criteria after the decision

Regardless of the option selected:

```text
fresh install: PASS with EXECUTE INSTALLED
no apt chown/setuid/setgid EPERM
no target slot left busy
finalization receipt written
PERSIST initialized
GRUB A/B default A
FIRST_INSTALL_PENDING present
no temporary diagnostics in clean rebuild
full lifecycle legs green
make verify PASS
no owned mounts/loops/bytecode
Session 04 CLOSED only after all legs
```

## 10. Revised decision record

No fifth capability is authorized. Follow-up source review proved the evidence boundary was insufficient: the package runner retained only the stderr prefix while APT's observed chown failure is warning-level. GitHub source repair now preserves both bounded stderr head and fatal tail, and the chroot/update cleanup was also corrected from lazy best-effort detach to shared recursive fail-closed cleanup.

Required next action: validate current `main` on Orbiter, rebuild the diagnostic installer from the unchanged S03 bundle, and rerun **fresh install only**. Use the new refusal reason to identify the actual fatal tail. Only if that tail proves a capability/ownership failure should the capability contract be reconsidered.

GitHub repair head at the time of this revision: `ec7cbe29fe13a7a25861ac893080dedd53494179`.
