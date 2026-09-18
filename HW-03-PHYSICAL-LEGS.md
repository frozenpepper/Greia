# HW-03 physical legs — exact status and owner runbook (2026-09-18)

Repair tranche (Session 02, R2 `repair` phase) is **source-complete and
Orbiter-proven at the payload level**. Everything below the hardware line is
RED/UNPROVEN. No worker lane can cross that line — every remaining execution
needs owner-operated hardware. This file is the precise handoff.

## 1. Proven (do not re-prove)

- Source tranche Repairs A–J + T12/T14/T16/T17 + HW-05 integrated, reviewer
  PASS each. Phase gate GATE-04 verdict: source consistent.
- HW-01A (Orbiter §16.1–16.5) GREEN at SHA
  `4c5719959b049a4c4301a974d4a181fd1c8e9448`:
  - real `acer-aspire-one-i386-ab` target root composed (`compose_root --role
    target`), 354 packages, clone-neutral (empty `/etc/machine-id`, no dbus
    machine-id, no random-seed, no SSH host keys);
  - payload `payload.ext4.zst`: 383798895 B compressed
    (sha256 `f5663dcd…5a1dde53a09`), 1111490560 B uncompressed (1060 MiB,
    shrink no-op);
  - bundle `greia-0.13.0-acer-aspire-one-i386-ab.greiaupdate`
    (sha256 `2a1e86af…b054fa53d3a`, 383799429 B, schema 3,
    `hardware_support: null`);
  - headroom through both production owners:
    max(1111490560, 1112539136) + 0 + 67108864 + 16777216 = **1196425216 ≤
    1610612736** (headroom 414187520 B ≈ 395 MiB). GREEN;
  - non-mount verifier GREEN (`e2fsck -n`, read-only debugfs, 13 paths).
- Artifacts live on Orbiter (`orb@192.168.68.113`, key-only ssh):
  `/home/orb/hw01a/target-root/`, `/home/orb/hw01a/out/payload.ext4.zst`,
  `/home/orb/hw01a/out/greia-0.13.0-acer-aspire-one-i386-ab.greiaupdate`,
  `/home/orb/hw01a/out/vmlinuz-generic` (sha256 `83bb754f…54ec9a3`),
  `/home/orb/hw01a/out/initrd-generic` (sha256 `176c3499…c2300f4aef`),
  logs `/home/orb/hw01a/logs/` (copied to T-BAG HW-01A attempt scratch).
- Current workstation `main` HEAD is `4c571995` (same SHA — the SHA-bound set
  is intact). Working tree carries the HW-05 comment-only delta uncommitted
  (`signed release` → `unsigned-v3` wording, `boot_transaction.py` +
  `slot_writer.py`, 7 insertions / 7 deletions, zero mechanism change).

## 2. RED / UNPROVEN (needs the three executions below)

- §16.6 installer disk assembly: HW-01B STOPPED on Orbiter (brief-authorized;
  `build/build-image.sh:108` `losetup --find --show --partscan` + parted /
  mkfs / mount / grub-install sequence is prohibited on the Orbiter lane).
  HW-03A STOPPED on this Mac (no `losetup`/`parted`/`mkfs.ext4`/
  `grub-install`, uid 501). No installer identity exists anywhere.
- §17 exact-service staging: HW-02 NOT-EXECUTABLE in every authorized lane;
  HW-03B NOT-EXECUTABLE (no QEMU/disposable Linux lane; harness pinned to
  `legacy-x86-i686`, Acer gap recorded). No staging verdict, no service logs.
- §18 Acer acceptance (all seven predicate groups): entirely unexecuted.
- Repair DoD §23 physical predicates: UNPROVEN. **Session 03 must not begin.**

## 3. Owner execution 1 — installer build (HW-03A re-attempt)

Host: disposable Debian/Ubuntu x86_64, root, with `parted`,
`losetup --partscan`, `mkfs.ext4`, `mount`, `grub-install`. (Orbiter excluded;
this Mac excluded.)

```bash
git rev-parse HEAD   # must be 4c5719959b049a4c4301a974d4a181fd1c8e9448; record it
# reuse — do NOT rebuild — the HW-01A bundle:
#   greia-0.13.0-acer-aspire-one-i386-ab.greiaupdate (sha256 2a1e86af…b054fa53d3a)
sudo -n bash build/build-installer-image.sh  # profile acer-aspire-one-i386-ab
```

Record: artifact path, byte size, sha256, release/profile identity.
Constraints: no Greia install to the build host's own disks, no repartition
of host storage, no Docker, no credentials in artifacts/logs/commits.
If any step needs something the host lacks: STOP, name the exact missing
capability + attempted host + next alternative. Do not resize slots or shrink
reserves to force green. Acer install/boot predicates stay RED after this leg
by design.

## 4. Owner execution 2 — exact-service staging (HW-03B re-attempt)

Host: Linux x86_64, root, `qemu-system-x86_64` + SeaBIOS, `losetup`, `mount`,
`partprobe`, `udevadm`, `mkfs.ext4` (per `tools/x8_qemu/runner.py`
`require_host`). Run the harness **unmodified** (profile stays
`legacy-x86-i686`; do NOT adapt it to Acer, do NOT add Docker).

Stage the §3 bundle through the exact shipped `greia-system-update.service`
sandbox (`CAP_SYS_ADMIN CAP_SYS_CHROOT`, exact production update composition)
against a real disposable inactive block/filesystem target: real zstd stream,
candidate support extraction (bundle declares `hardware_support: null`, so
the absent path must perform no extraction), chroot offline package path,
real finalizer. Capture service logs around staging.

Verdict needs: staging succeeds; active slot untouched; support provenance =
candidate archive; final fstab carries the destination UUID; clone-neutral
state correct; completeness + health pass; inbox removed only after success.
Record the `legacy-x86-i686` vs `acer-aspire-one-i386-ab` gap explicitly.
If no capable host: second explicit NOT-EXECUTABLE (same A0 contract).

## 5. Owner execution 3 — Acer acceptance (HW-03 §18)

Reference Acer Aspire One, from the recorded HEAD with the §3 installer +
bundle. Fresh install; verify 1536 MiB SYSTEM_A/SYSTEM_B, PERSIST present, A
populated, B empty/unaccepted, normal Greia boot. A-slot specialization:
fstab root UUID = SYSTEM_A, tmpfs policy present, machine-id generated (not
build-host copied), no build-host SSH identity. Stage the real v3 candidate
through the installed service (never an ad-hoc SlotWriter shell): targets B,
A untouched, UUID becomes B's role UUID, canonical fstab for B, candidate
support from the candidate archive, chroot offline path, completeness pass,
inbox removed only after success. Arm B one-shot, reboot, verify B boots,
health reached, B accepted, default advances. Bad-candidate smoke: accepted
slot survives, default returns, PERSIST child/Parent data intact.

Do NOT manually patch the installed disk. Stop-and-report on the first
failing boundary or §19 condition. Allowed source changes: NONE.

## 6. Evidence return (§24 block)

Bound to ONE SHA: final SHA, files changed, focused + `make verify` results,
ORBITER block (§1 byte counts/reserve/headroom/verifier outputs — already
held in T-BAG HW-01A scratch), installer block (§3 path/bytes/sha256),
ACER block (§5 partitions, UUID/fstab, staging/boot/health/recovery/PERSIST,
service logs). Hand the block to the run: HW-04 writes the §24 table into
HANDOVER + `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`,
then PHASE-GATE-01 re-audits narrowly.

## 7. Run state (T-BAG R2 `repair`)

Integrated with reviewer PASS: T01–T18 source tranche, HW-01A (GREEN),
HW-01B (STOP), HW-05, HW-03A (STOP), HW-03B (NOT-EXECUTABLE), both triages
RESUME. Recorded BLOCKED: HW-02 (NOT-EXECUTABLE, proof carried by HW-03),
HW-03 (awaits the three executions above). Queued: HW-04 (needs §6 block).
Gate GATE-04 BLOCKED. Runtime pinned: analyst + grunt =
`opencode / opencode-go/muse-spark-1.3-contributor`.
Worker model note: parallel launches collide on the shared 6.9 GB
`~/.local/share/opencode/opencode.db` (`unable to open database file`) —
the parent serializes launches until that contention clears.
