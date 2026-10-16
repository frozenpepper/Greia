# Session 04: fresh-install EXECUTE failure — diagnosis handover

**Date:** 2026-09-24
**Repo HEAD:** `0acc0f05` (clean tree, in sync with `origin/main`)
**Status: Session 04 OPEN, BLOCKED on the fresh-install leg.** All later legs
(firstboot → update → recovery → nonboot → persist-refusal) are implemented,
tested source-side, and have manufactured candidates waiting. Nothing past
fresh install has run in QEMU yet.
**A companion agent with only GitHub access has everything needed here plus
`docs/testing/session04-evidence/` (serial log, measurements, driver).**

> **HEAD contains two TEMPORARY diagnostic commits that MUST be reverted
> before Session 04 closure:** `3f101b1c` (marker-gated service step emits)
> and `0acc0f05` (marker-gated faulthandler). They are production-inert
> without the `/run/greia-x8-debug` marker (only the test runner creates
> it), but they are scaffolding, not product.

## 1. What Session 03 delivered (immutable base)

- Source: `6c58601e`; release `greia-0.13.0-phase0-dev`; full `make verify`
  3618 tests OK.
- Bundle `acer-aspire-one-i386-ab.greiaupdate` (540,126,645 bytes):
  `6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67`
- Payload: compressed 383,881,888; uncompressed **1110081536** (this is the
  number that proves the Session-03 flex_bg/geometry repair — old broken
  value was 1610612736); minimum 1111130112;
  `c9b58aee72e058c288204e1bb1136859a8d8d8807f21a66178789982a4b3f543`.
- Hardware support: `f228a314383bec838aed06fc808bd564dc85c96ac70537a3163918313842c24e`,
  58 packages, whole-pool-installed 710,070,272 (a **ceiling**, not a
  machine footprint), 37 dependency closures.
- These artifacts live only on the build host under
  `tmp/session03-linux-release-6c58601e…/out/…` (NOT in git). Do not modify
  them. Their SHAs are in `session04-evidence/measurements.json`.

## 2. Session 04 mission (not yet started, in QEMU terms)

Real product lifecycle on disposable regular-file images, via the existing
`tools.x8_qemu.product.ProductHarness` (extended, not replaced):

```text
real S03 bundle -> fresh A/B install -> SYSTEM_A first healthy boot accepted
-> healthy update staged to SYSTEM_B -> B one-shot boot -> B health commit
-> deliberately unhealthy candidate -> automatic recovery to accepted release
-> deliberately non-booting candidate -> reset/power-cycle leaves accepted
-> PERSIST-incompatible candidate refused before activation/mutation
```

New harness legs already committed (with 18 focused tests in
`tests/test_x8_qemu/test_session04_legs.py`): `run_first_boot_product`,
`run_userspace_failure_product`, `run_nonboot_failure_product`,
`run_persist_refusal_product`, `build_nonbooting_candidate_bundle`, plus the
`update-stage-expect-refused` control phase. Test candidates already built
and verified (SHAs in measurements.json):
`s04-b` (persist 1/1/1), `s04-persist99` (99/99/99),
`s04-broken` (health-issuer removed), `s04-nonboot` (kernels removed).

## 3. How to reproduce the failure

Driver (committed copy): `docs/testing/session04-evidence/s04driver.py`.
One leg per invocation, as root (loop/mount), with bytecode suppression:

```bash
sudo env PYTHONDONTWRITEBYTECODE=1 S04_HEAD=<sha> S04_QEMU_TIMEOUT=3600 \
  python3 /tmp/s04driver.py install
```

- `S04_HEAD` selects the session dir (candidates live alongside it).
- Installer is auto-selected: `<HEAD>/installer/…img` if present, else the
  newest `/tmp/greia-session04-*/installer/…img`.
- LifecycleConfig: `output_dir=<session>/s04legs`, `memory_mib=2048`
  (4096 in one attempt), `cpus=2`, timeout configurable (60–3600).
- After each attempt the driver dir was preserved as
  `s04legs-attempt<N>-*` for forensics; after diagnosis these bulky
  per-attempt dirs (~29 GB total) were deleted during 2026-09-24 disk
  cleanup — everything needed from them (attempt-11 serial, measurements)
  is committed under `docs/testing/session04-evidence/`. The four test
  candidates and the instrumented installer image in `/tmp` were kept
  (needed to continue; rebuildable via the commands above).
- QEMU (product-mode, disposable images only):
  `qemu-system-i386 -name greia-product-install-execute -machine
  pc,accel=kvm:tcg -cpu qemu32 -m 2048 -smp 2` with the installer clone
  (snapshot=on), a blank 7 GiB target
  (`serial=GREIA-PROD-TARGET-1`), and a 64 MiB control disk; `-display
  none -monitor none -serial file:…/product-install-execute-serial.log
  -nic none -boot order=c,strict=on -no-reboot`.
- Instrumented installer currently in use (faulthandler + step emits):
  `c413a953ec3e76872bb3d18305e08ec9d1a136ed3a99133812d64648403c449e`
  (report re-verified: profile `acer-aspire-one-i386-ab`, embedded bundle
  SHA == S03 SHA).

## 4. The failure signature (stable across attempts 5–11)

Guest serial (full text in
`session04-evidence/attempt11-install-execute-serial.log`, 4619 bytes):

```text
x8-control: phase install-execute starting
x8-control: socket /run/greia-os/install-transaction.sock present
x8-control: install install-execute: prepare starting
... service Started ...
x8-control: install install-execute: prepared ok
x8-control: install-execute: execute starting
s04-svc: faulthandler armed
s04-svc: inspected
s04-svc: support-bound
s04-svc: capacity-planned
s04-svc: partitioned
s04-svc: identities-bound
s04-svc: streamed
s04-svc: finalize-fstab
s04-svc: finalize-completeness
x8-control: install failed: TransactionClientError:
    transaction response is outside Greia bounds
    File "<stdin>", line 49, in <module>
    File ".../transaction_client.py", line 241, in execute
    File ".../transaction_client.py", line 187, in _round_trip
```

`_round_trip` raises "outside bounds" when the response is **empty**
(`b""`) or over 16 KiB (`MAX_MESSAGE_BYTES`,
`src/greia_platform/privileged_channel.py:34`). The INSTALLED response is
a few hundred bytes, so an empty read means **the server closed the
connection without sending anything**. A hung server would instead trip
the client's 1800 s transport timeout ("unreachable" — a *different*
error seen only in attempts 1–3). Conclusion: **the transaction service
is done (dead/escaped), not hung**, shortly after the completeness step,
before any GRUB/persist/journal work (P1 boot-control empty, P4
uninitialized in every post-mortem).

Slot-A forensics (host RO mounts of the target, attempts 5–11): MBR with
p1/p2/p3/p4; ~1 GB streamed rootfs; fstab specialized (all but attempt 6);
**0 firmware, 0 microcode in dpkg**; no receipt/finalized markers; apt
`lists/` shows lock+partial+auxfiles fresh-dated but EMPTY (no fetched
Packages); **no `run/greia-hardware-support.list` source file**; no
history/dpkg log changes. Nanosecond timeline (attempt 10, guest CEST):
fstab .188 → mountpoint dir .304 → apt files .464–.476 → `run/` mtime
.524. dpkg status is byte-identical to the baked payload (314,082 bytes).

## 5. Attempt log (condensed)

| # | Setup | Outcome |
|---|-------|---------|
| 1–2 | baseline | Hung execute; root cause was the runner missing `execute_transport` (10 s default killed every real install client-side). Fixed in `35cc6360`. |
| 3–4 | traced | Same + pre-existing Session-03 support-classes bug (whole-pool classes vs machine selection). In-guest probe proved it: `support class 'alsa-topology-conf' is in neither firmware nor microcode`. Fixed in `1ecba9de` (+ partial-selection regression tests). |
| 5 | fixed installer | Partition + stream + fstab, then empty response. First “post-fix” signature. |
| 6 | same | Same but NO fstab (death-point variance noted). |
| 7 | mem=4096 | Identical signature (fstab present). Rules out simple RAM-size OOM. |
| 8–9 | sampler + svc emits | Death localized between `finalize-completeness` and `hw-installed` emits. |
| 10 | host-correlated watch | Death inside a ~5 min window; apt lock created, nothing fetched. |
| 11 | faulthandler armed | No crash dump. Same signature. |

Repairs landed along the way (all in `git log`): `--release-bundle`
plumbing (`e5ba3d73`), APT list restore (`3bd8e303`), USB sizing +
bytecode suppression (`6c13abea`), harness legs (`45c3d283`), runner
hardening — socket poll, serial tracing, journal-follow, execute timeout —
(`6d9269e9`, `f099f5a5`, `35cc6360`, `2b2fc91b`), sampler upgrades
(`92688522`, `bbcd7feb`, `6ca183bd`), sampler detach, control-unit
`TimeoutStartSec=0` (test-pinned).

## 6. Ruled OUT (with killing evidence)

- **10 s client timeout** — fixed; later attempts use `EXECUTE_TIMEOUT_SECONDS` (1800 s).
- **Support-classes mismatch** — found, fixed, installer rebuilt; install now passes binding (partitioning + streaming prove it).
- **Whole-pool capacity refusal** — would refuse fast with a message, and streaming proves capacity passed.
- **OOM by footprint** — sampler showed 1.7 GB free, Committed_AS 53–72 MB stable, TasksCurrent 1–2; death identical at 4096 MB. (Caveat: sampler dies ~90 s in; see §8.)
- **TasksMax=8 pressure** — observed 1–2/8 before death; the limit throttles forks (EAGAIN → handled error), it does not SIGKILL.
- **Timeouts generally** — every install-path subprocess has a finite timeout (partition 300 s, hw 600 s, unmount 120 s) and all timeout errors convert to handled ERROR responses, not empty ones.
- **Guest reboot** — single “starting” + single login prompt in every serial.
- **Host disk-full as cause** — writes (1.2 GB target, serial, snapshots, clone copy) demonstrably succeeded throughout the failing runs; the disk filled with session debris *afterward* (cleaned ~15 GB; 12 GB free at handover).
- **Corrupt bundle/pool/payload** — host-side full service-stack reproduction (`PREPARE_PLAN` + `EXECUTE` through the real `handle_request` against a loop device) completes in ~66 s with the exact S03 artifacts.
- **systemd-oomd** — binary absent from the installer image.
- **strace/gdb in guest** — both absent from the image (checked).

## 7. Open hypotheses (ranked)

1. **Async SIGKILL from an unidentified in-guest agent.** Everything
   handled converts to ERROR responses (`execute_ab_install` catches
   broad `Exception`; `handle_connection` catches the trio). Only death
   (or a BaseException) yields an empty response. No agent identified;
   OOM/cgroup/systemd-kill all contradicted or unproven.
2. **Faulthandler silence is unreliable.** The `open("/dev/ttyS0")`
   handle is a local in `_s04_diag_faulthandler` with no saved reference;
   if GC closes the fd, crash/hang dumps fail silently. **Fix the fd
   lifetime before trusting “no dump”.**
3. **ERROR-response encoding crash.** `encode_response` raising inside
   `handle_connection`'s except-handler (e.g., on hostile tool bytes in
   the reason) escapes the trio-catch, kills `serve_forever`, and yields
   exactly this empty response. Unproven but architecturally live.
4. **BaseException escape** (SystemExit/KeyboardInterrupt/GeneratorExit).
   Grep found none in the path, but no systematic audit was done
   (generators verified absent in installer/platform finalize files).
5. **D-state wedge + client confusion.** Weak: a wedged server never
   closes, so the client should time out (“unreachable”), not read EOF.
6. **Forensic staleness.** The guest idles WITH slot A mounted; host RO
   reads may lag guest dirty buffers (mitigated by 30 s+ idle writeback
   and ext4 journal replay on RO mount, but never zero).
7. **Clock skew.** APIC-vs-PM-Timer 97-vs-100 ms note; guest CEST vs host
   UTC confused early timelines. Forensic nuisance, not a cause.

## 8. What the next agent should do (in order)

1. **Fix the faulthandler fd lifetime** (save a global reference in
   `transaction_service.py`), rebuild the installer, rerun install. A
   segfault/SIGABRT will then *prove itself* with a traceback; continued
   silence points at SIGKILL.
2. **Sandboxed host repro**: run the working host-side service-stack
   reproduction (`/tmp` scripts are gone with cleanup — rebuild from
   §3 pattern) under `systemd-run` with the unit's exact directives
   (`TasksMax=8`, `ProtectSystem=strict`, `PrivateTmp`,
   `NoNewPrivileges`, `CapabilityBoundingSet`, `RestrictAddressFamilies`,
   …). If it dies there, the sandbox is guilty — bisect directives.
3. If sandbox is innocent: **ExecStart wrapper with strace** (temporary
   installer rebuild) for signal-level truth; audit BaseException paths
   and `encode_response` failure modes in parallel.
4. Keep one leg per driver run, 3600 s budget for real legs (outcome is
   currently fast, but a healthy install needs ~10–20 min); poll serial
   size/mtime from the host for arrival timelines.
5. Rebuild the installer **only** when shipped code changes (harness/
   runner changes inject at leg start, no rebuild needed).
6. Before closure: **revert `3f101b1c` + `0acc0f05`**, run full
   `make verify`, continue the lifecycle (firstboot → seed → update →
   B-commit → broken → recovery → nonboot → reset → persist99 refusal),
   update `HANDOVER.md` + the lifecycle plan, commit, push.

## 9. Warnings / traps

- **Do not touch** other sessions' `/tmp` dirs (`greia-exp`, `greia-p5-*`,
  `session03-*`), host apt caches (never clear), or attempt evidence
  beyond what is recorded here. Disk is at 98% (12 GB free) — check
  `df` before each run; one attempt peaks near ~9 GB.
- Leftover loop devices with deleted backing files exist from harness
  timeout-kills; detach individually (`losetup -d /dev/loopN`), never
  `losetup -D`; never `umount -R`.
- The sampler dying ~90 s in is itself unexplained; detached-setsid did
  not save it. Treat sampler absence as data, not as failure.
- `dmesg` in-guest is blind (`CAP_SYSLOG` denial line in serial), so no
  kernel-side evidence exists for any attempt.
- `control_runner_text()` + `control_unit_text()` are generated into
  clones at leg start from the *working tree* — always re-verify what
  the guest actually runs; stale-clone confusion already cost hours once
  (a debug image booted a stale runner and sat silent at a login prompt).
- `update-stage-expect-refused`, the Session-04 legs, and the nonboot
  builder are committed and source-tested; only the QEMU legs await the
  install fix.

## 10. Key code references (at HEAD `0acc0f05`)

- Install flow: `src/greia_installer/fresh_ab_install.py:513`
  (`execute_fresh_ab_install`); support binding
  (`_support_set_from_seams`, `:1068`); TEMPORARY emits throughout.
- Seams/selection: `src/greia_installer/device_seams.py:370`
  (`selected_installed_bytes`), `:538` (classes wiring).
- Finalizer: `src/greia_platform/slot_writer.py` (`SlotFinalizer.finalize`,
  TEMPORARY emits `finalize-fstab/completeness/hw-installed/artifacts/
  receipt/health`).
- Service: `src/greia_installer/transaction_service.py:871` (trio catch);
  TEMPORARY `_s04_diag_faulthandler`.
- Client bounds check:
  `src/greia_installer/transaction_client.py:187`; execute transport
  (`EXECUTE_TIMEOUT_SECONDS`, 1800 s).
- Sockets: `src/greia_platform/update_privileged.py:176` (CONFIRMED
  mapping); bundle cap `privileged_channel.py:34` (16 KiB).
- GRUB one-shot consume: `src/greia_platform/grub_ab.py:318`.
- Microcode policy: `src/greia_platform/hardware_enablement.py:369`
  (any GenuineIntel → `intel-microcode`; pool offers both microcodes).
- Harness: `tools/x8_qemu/product.py` (`ProductHarness`,
  `control_runner_text/unit_text`, sampler); unit file:
  `build/installer-overlay/etc/systemd/system/
  greia-install-transaction.service`.
- Tests: `tests/test_x8_qemu/test_session04_legs.py` (20 tests),
  `tests/test_installer_seam_composition.py`
  (`PartialSelectionSupportClassTests`).

## 11. Follow-up evidence and current decision state (2026-09-25)

The faulthandler file-handle lifetime was corrected, the repeating interval was
reduced to 120 seconds, and marker-gated socket-boundary diagnostics were added
temporarily. The focused transaction-service suite passed 45 tests and the
Session-04 harness suite passed 20 tests.

The final instrumented QEMU install run captured the missing service journal.
The service did not disappear for an unexplained reason: apt inside the mounted
slot failed at `hardware_support_install.py:61` while attempting its normal
privilege drop:

```text
setgroups(65534): Operation not permitted
setegid(65534): Operation not permitted
seteuid(42): Operation not permitted
```

The service then exited with `Result=exit-code` and `ExecMainStatus=1`. The
client's empty response is a consequence of the failed service request, not
evidence of a proven external SIGKILL. The exact call graph, host sandbox
bisect, cleanup state, and the required security decision are recorded in
`docs/archive/testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md`.

Session 04 remains OPEN. No capability, `NoNewPrivileges`, or apt sandbox
repair has been selected or applied. The temporary diagnostics and the final
journal evidence remain in the working tree for the next authorized step.
