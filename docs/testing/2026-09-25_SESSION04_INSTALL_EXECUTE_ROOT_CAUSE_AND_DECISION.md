# Session 04: install EXECUTE root cause and sandbox decision report

**Date:** 2026-09-25
**Repository:** `/home/orb/Works/Greia`
**Branch:** `main`
**Evidence-producing working HEAD:** `e8180956c7f27d7b712fdfec16d3ba56d3a91a43`
**Status:** **Session 04 OPEN — source repairs are now landed on `main`, but fresh-install/QEMU validation has not yet been rerun and no lifecycle closure is claimed.**

## 1. Executive conclusion

The install failure is no longer an unexplained QEMU disappearance.

The final diagnostic run captured the guest service journal and proved this exact failure:

```text
TargetHardwareSupportInstaller.install()
  -> chroot <slot> apt-get update
  -> apt attempts setgroups/setegid/seteuid
  -> setgroups(65534): Operation not permitted
  -> setegid(65534): Operation not permitted
  -> seteuid(42): Operation not permitted
  -> FreshAbInstallError
  -> TransactionServiceError
  -> greia-install-transaction.service exits status=1
```

The shipped `greia-install-transaction.service` runs with `NoNewPrivileges=yes` and only:

```text
CAP_SYS_ADMIN
CAP_SYS_CHROOT
```

That capability contract is insufficient for apt's normal privilege-drop path. The service raises a normal Python refusal, but the client receives an empty response and reports the bounds error. The final systemd status is:

```text
Result=exit-code
ExecMainCode=1
ExecMainStatus=1
ActiveState=failed
```

This is a product sandbox/capability decision, not corruption, RAM exhaustion, guest reboot, systemd-oomd, a client timeout, or a proven external SIGKILL.

No security repair has been applied. Session 04 remains open pending the decision in section 10.

## 2. Immutable inputs

The Session 03 release remains the only fresh-install input:

```text
source: 6c58601eaad32ad2bba30acb24e33333b9c4bbf3
release: greia-0.13.0-phase0-dev
bundle: acer-aspire-one-i386-ab.greiaupdate
bundle bytes: 540126645
bundle SHA-256: 6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67
payload compressed: 383881888
payload uncompressed: 1110081536
payload minimum slot: 1111130112
payload SHA-256: c9b58aee72e058c288204e1bb1136859a8d8d8807f21a66178789982a4b3f543
support packages: 58
support installed ceiling: 710070272
```

The four Session 04 candidates remain protected under:

```text
/tmp/greia-session04-45c3d283717372cebd2636db860fc162f752f1ee/candidates/
```

The Session 03 release directory remains protected under:

```text
/home/orb/Works/Greia/tmp/session03-linux-release-6c58601eaad32ad2bba30acb24e33333b9c4bbf3/
```

Neither was modified by this diagnosis.

## 3. Failure history

| Attempts | Evidence | Result |
|---|---|---|
| 1–2 | Client used the old short execute transport | False timeout diagnosis; fixed by using `EXECUTE_TIMEOUT_SECONDS` |
| 3–4 | Support-class mismatch | Fixed by narrowing classes to the machine-selected packages |
| 5 | Partitioning, streaming, fstab, completeness succeeded | Empty response after the old failure window |
| 6 | Same failure with fstab variance | Death point varied slightly but stayed in the same install region |
| 7 | 4096 MiB guest | Same failure; simple guest RAM shortage ruled out |
| 8–9 | Sampler and service stage markers | Service still active with low task count; last stage was `finalize-completeness` |
| 10 | Correlated host watch | APT lock/list state appeared, but no useful package result |
| 11 | Faulthandler marker | No dump, but the open file handle had not been retained; evidence was not conclusive |
| 12 | Corrected faulthandler plus socket-boundary diagnostics | Same last stage; no Python exception, encoding, or sendall diagnostic appeared; external death was suspected |
| 13 | Final control-runner status/journal capture | Root cause proved: apt privilege-drop syscalls fail with EPERM and the service exits 1 |

Committed serial evidence:

```text
docs/testing/session04-evidence/attempt12-install-execute-serial.log
docs/testing/session04-evidence/attempt13-install-execute-serial.log
```

## 4. Temporary diagnostics added and tested

The following changes are temporary Session-04 scaffolding only. They must be removed before closure.

### 4.1 Faulthandler lifetime

`src/greia_installer/transaction_service.py` now retains a module-owned serial handle:

```text
_S04_DIAG_SERIAL_HANDLE
```

The handle is assigned immediately after opening `/dev/ttyS0` and remains alive for the service process lifetime. The faulthandler interval is reduced from 1500 seconds to 120 seconds. Arming is idempotent while the marker is active.

This fixes the invalid lifetime assumption in the earlier attempt-11 evidence. It does not prove SIGKILL causes; faulthandler cannot report SIGKILL.

### 4.2 Socket service boundary markers

Marker-gated serial markers now surround:

```text
handle_request entered
handle_request normal response ready
expected exception caught
error response encode starting
error response encoded
sendall starting
sendall completed
UNEXPECTED BASEEXCEPTION ESCAPE
error response encode failed
sendall failed
```

`BaseException` is logged and re-raised where diagnostics catch it. No production error is swallowed or converted to success.

### 4.3 Focused tests

`tests/test_install_transaction_service.py` now covers:

```text
module-owned faulthandler handle and idempotent arming
normal response with marker absent
ordinary TransactionServiceError refusal
InstallTransactionError refusal
PrivilegedChannelError refusal
Unicode/newline/long refusal reason
forced BaseException escape
forced error-response encoding failure
forced sendall failure
```

Executed result:

```text
45 tests passed
```

The Session-04 QEMU harness tests also passed:

```text
20 tests passed
```

The product-install harness suite passed:

```text
38 tests passed
```

### 4.4 Control-runner termination capture

The temporary QEMU control runner now prints bounded final service state after a failed install request:

```text
systemctl show
journalctl -u greia-install-transaction.service
process listing
```

This is test-only harness observation. It is not a product service change and must be removed with the rest of the temporary diagnostics.

## 5. Built-installer verification

The rebuilt diagnostic installer was built through the canonical legacy front door:

```text
build/build-legacy-x86-sd-installer.sh
```

Artifact:

```text
/tmp/greia-session04-e8180956c7f27d7b712fdfec16d3ba56d3a91a43/installer/greia-os-installer-acer-aspire-one-i386-ab.img
```

Verified facts:

```text
profile: acer-aspire-one-i386-ab
image SHA-256: 221759e185ed5b567f912b7c9eea86f4cf067af49437f3c349f35a53b21758e4
embedded bundle SHA-256: 6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67
support packages: 58
support installed bytes: 710070272
live security support: no-alerts
```

The image's live SquashFS was extracted read-only and inspected. The built `transaction_service.py` contains the module-owned handle, 120-second interval, and boundary labels. No `.pyc` file was present in the built Greia tree.

## 6. Final QEMU evidence

The final run used the production-mode QEMU path and the rebuilt diagnostic image. The target was a disposable regular file. The service reached:

```text
inspected
support-bound
capacity-planned
partitioned
identities-bound
streamed
finalize-fstab
finalize-completeness
```

The sampler immediately before failure reported:

```text
ActiveState=active
SubState=running
TasksCurrent=2
TasksMax=8
MemAvailable≈1.74 GiB
Committed_AS≈80 MiB
```

The final journal then reported:

```text
hardware_support_install.py:61
  self.runner.run([... apt-get update ...])

E: setgroups 65534 failed - setgroups (1: Operation not permitted)
E: setegid 65534 failed - setegid (1: Operation not permitted)
E: seteuid 42 failed - seteuid (1: Operation not permitted)
E: setgroups 0 failed - setgroups (1: Operation not permitted)

greia-install-transaction.service:
Main process exited, code=exited, status=1/FAILURE
Failed with result 'exit-code'
```

The client still observed:

```text
TransactionClientError: transaction response is outside Greia bounds
```

This is because the failure occurs in the synchronous service path before a valid framed response reaches the client. The final service status is authoritative over the earlier empty-response interpretation.

## 7. Why the earlier diagnosis was incomplete

The earlier report correctly identified the last visible install stage but did not have the final service journal. Several hypotheses are now ruled down or corrected:

- The faulthandler handle lifetime was not proven in attempt 11; that is now fixed.
- The service is not proven externally SIGKILLed. The final run shows an ordinary Python exception and systemd exit status 1.
- The client timeout is not the cause; the final journal is available after the response failure.
- Simple RAM shortage remains ruled out by the 2 GiB and 4 GiB attempts and the sampler.
- `systemd-oomd` remains absent from the image.
- The support pool and bundle are not corrupted; the host-side unsandboxed full service stack completed with the exact S03 bundle and support pool.
- The host sandbox's separate e2fsck SIGSEGV does not explain the QEMU failure: it occurs earlier, during host-side fresh-target setup, and is not the guest journal's failure.

## 8. Exact call graph at the failure

The production call graph is:

```text
transaction_service.handle_connection()
  -> transaction_service.InstallTransactionService.handle_request()
    -> execute_ab_install()
      -> fresh_ab_install.execute_fresh_ab_install()
        -> SlotFinalizer.finalize()
          -> filesystem.check_completeness()
          -> package_installer.install(firmware, microcode)
            -> InstallerPoolBindCleanupPackageInstaller.install()
              -> SharedSlotPackageInstaller.install()
                -> InstallerSlotPackageInstaller.install()
                  -> TargetHardwareSupportInstaller.install()
                    -> SubprocessHardwareSupportRunner.run()
                      -> chroot <slot> apt-get update
```

The failure is in the final hardware-support package step, after completeness and before the `hw-installed` stage marker.

## 9. Host sandbox reproduction and bisect

A host-side reproduction using the built live root, exact S03 bundle, exact support pool, production seams, and a disposable loop target produced:

```text
unsandboxed: PREPARE PREPARED; EXECUTE INSTALLED
full restrictions: e2fsck SIGSEGV during fresh-target setup
```

The host sandbox issue was bisected only far enough to establish that it is not the QEMU root cause:

```text
full restrictions                                      FAIL at e2fsck
remove SystemCallArchitectures                         FAIL at e2fsck
remove ProtectSystem=strict                            PASS
remove NoNewPrivileges=yes, keep ProtectSystem=strict  PASS
```

A standalone e2fsck probe under the same full restriction pair passed on both a finalized filesystem and a fresh regular-file ext4 image. Therefore the host-only e2fsck result is treated as a disposable loop/host reproduction interaction, not as authority to weaken the shipped guest service sandbox.

The QEMU guest evidence is stronger for the product path: it reaches the same finalizer boundary and then records the apt privilege-drop EPERM directly.

## 10. Security decision required

The accepted unit currently declares:

```text
NoNewPrivileges=yes
ProtectSystem=strict
CapabilityBoundingSet=CAP_SYS_ADMIN CAP_SYS_CHROOT
AmbientCapabilities=CAP_SYS_ADMIN CAP_SYS_CHROOT
```

The required repair choices are:

### Option A — add only CAP_SETUID and CAP_SETGID

Add those two capabilities to the service capability bounding and ambient sets while retaining `NoNewPrivileges`, `ProtectSystem`, filesystem restrictions, address-family restrictions, and task limits.

Advantages:

```text
apt keeps its normal _apt/nobody privilege drop
No broad sandbox weakening
Capability intent remains narrow and explicit
The missing operation is directly repaired
```

Costs:

```text
The unit contract changes
The capability policy and tests must be updated
A real QEMU install must prove apt succeeds under the new unit
```

This is the recommended repair if the owner accepts the narrowly expanded capability set.

### Option B — keep the capability set and run apt as root

Configure the offline apt invocation with an explicit root sandbox user, for example `APT::Sandbox::User=root`.

Advantages:

```text
No new capabilities
No removal of NoNewPrivileges
```

Costs:

```text
apt package methods retain more privilege
The installer service executes package operations as root rather than dropping to _apt/nobody
This is a deliberate security tradeoff and must be documented
```

### Option C — remove NoNewPrivileges

Not recommended. It is broader than the demonstrated missing operation and weakens the accepted service posture.

Follow-up review selected **Option A**: retain the existing sandbox and add only `CAP_SETUID` and `CAP_SETGID`. This repair is now landed on `main`; Orbiter must still rebuild the installer and prove the capability set in product-mode QEMU.

## 11. Required next steps after the decision

1. Apply the selected repair in the service unit and its capability contract tests.
2. Rebuild the Session-04 installer from the unchanged S03 bundle.
3. Inspect the built live root and shipped unit artifact.
4. Run one fresh-install QEMU leg and require `EXECUTE INSTALLED`.
5. Continue only after fresh install is green:

```text
first A acceptance
seed
healthy A->B update
B commit
userspace-broken candidate
recovery to B
nonboot candidate
reset/power-cycle
PERSIST-incompatible refusal
```

6. Remove all temporary diagnostics, including:

```text
faulthandler handle and marker
service boundary logging
control-runner termination capture
temporary sandbox/host diagnostics
```

7. Run focused tests, then `make verify`.
8. Update `HANDOVER.md` and the lifecycle plan with exact evidence.
9. Commit and push only after the lifecycle is actually closed.

## 12. Current repository and host state

The diagnostic scaffolding and evidence are committed. Product source repairs are now landed on `main`, but have not yet been executed on Orbiter: the service has a separate canonical entrypoint and the unit has the narrowly expanded four-capability set.

Current owned scratch cleanup completed:

```text
no Session-04 QEMU mount remains
no Session-04 loop remains
no sandbox target remains
no owned sandbox root remains
approximately 84 GB free on /
```

The next action is Linux validation: run the focused source suites, rebuild and inspect the installer, then rerun the fresh-install QEMU leg. Session 04 is not closed.


## 13. Follow-up architecture review and landed source repair

A post-report review found a second production defect in the service execution topology. The shipped unit executed:

```text
python3 -m greia_installer.transaction_service
```

while `composition.build_install_service()` lazily imports
`greia_installer.transaction_service`. Executing the implementation itself
with `-m` can therefore place one copy under `__main__` and a second copy
under the canonical package name. That splits module globals and class identity
inside one process. Attempt 13's duplicate faulthandler arming and the escaped
`greia_installer.transaction_service.TransactionServiceError` despite an
apparently matching handler are consistent with this defect.

The source repair now on `main` is structural rather than a `sys.modules`
alias or broader exception catch:

- new thin executable module
  `greia_installer.transaction_service_entrypoint`;
- shipped unit executes that wrapper;
- `transaction_service.py` is library-only and remains the single canonical
  owner of service classes/exceptions;
- unit-contract tests pin the wrapper and canonical class identity;
- the capability contract is exactly
  `CAP_SYS_ADMIN CAP_SYS_CHROOT CAP_SETUID CAP_SETGID`;
- `NoNewPrivileges=yes` and `ProtectSystem=strict` remain unchanged.

These source changes were made through GitHub and have **not** yet been executed
on Orbiter. The temporary Session-04 diagnostics remain intentionally present
until one diagnostic fresh-install confirms both the canonical service behavior
and successful apt privilege dropping. They must still be removed before final
Session-04 acceptance.
