# ADR 0030 — Platform-Owned Transactional System Updates

**Status:** ACCEPTED core A/B update architecture; release-authenticity sections superseded by ADR 0036  
**Date:** 2026-08-19; simplified 2026-09-15  
**Scope:** Greia OS/runtime updates, delivery, activation, rollback and Parent control  
**Extends:** ADR 0012  
**Superseded by ADR 0036 where conflicting:** release signing, key trust, anti-tamper, cryptographic anti-rollback and release-file authenticity requirements

## 1. Decision

Greia system/runtime updates are a **platform-owned appliance service**.

The Parent client may choose/upload an update, authorize restart and observe progress. It does not execute package-manager commands, write partitions or implement boot rollback itself.

Stable model:

```text
Parent upload / future Internet download / removable media
                     |
                     v
                .greiaupdate
                     |
          basic structure + compatibility
                     |
                     v
          SystemUpdateService
                     |
             inactive system slot
                     |
               one-shot boot
               /          \
         healthy           failed
           |                 |
         commit           rollback
```

This is a reliability architecture, not a hostile-tamper security architecture.

## 2. A/B system model

Release-capable Greia installations use:

```text
boot-selection state
system slot A
system slot B
PERSIST
```

Routine updates write only the **inactive** system slot.

The active system is never mutated in place by the normal updater.

After staging, Greia boots the candidate once. If Greia reaches the required usable Shell/service health point, the candidate becomes current. If candidate boot or health fails, the previous slot becomes current again.

Existing single-root installations are not pretended to have rollback. They require reinstall/migration into the supported layout.

## 3. Persistent child data

Profiles, Activity saves/creations, progression, Parent configuration and other durable user state live outside routine system slots.

An unconfirmed candidate must not irreversibly transform shared data so that the previous release cannot use it after rollback.

Keep migrations backward-compatible until candidate acceptance or defer irreversible migration until after acceptance.

## 4. `.greiaupdate`

The portable update artifact uses:

```text
.greiaupdate
```

ADR 0036 owns the current simple bundle format.

The bundle contains a small manifest, one complete system-slot image and the bounded hardware-support content required by finalization.

Normal acceptance checks are practical:

```text
bundle is readable
manifest fields are valid
profile/architecture/board are compatible
payload fits the inactive slot
payload is a complete Greia system image
```

No release signing key, signature verification, public-key trust store or cryptographic anti-rollback mechanism is required by Greia's update architecture.

Optional checksums are ordinary corruption/debugging aids only.

## 5. Whole-system payloads

The supported strategy is a complete system-slot payload, not package-by-package mutation of the active root.

Reasons:

- interrupted update cannot half-upgrade the running OS;
- rollback remains simple;
- the same artifact is used by fresh installation and update;
- architecture/profile compatibility can be checked before writing.

Routine updates do not repartition the disk or replace the platform bootloader.

## 6. Delivery sources

All delivery sources feed the same updater:

1. Parent uploads a local `.greiaupdate`;
2. Greia may later download an advertised update itself;
3. removable media may later provide a bundle.

Delivery source does not change staging/rollback behavior.

## 7. Parent API boundary

The Parent API exposes semantic operations such as:

```text
read update status
upload/queue bundle
prepare candidate
request restart
read result
```

The Parent web application does not expose arbitrary `apt`, `dpkg`, `mount`, `dd`, GRUB or shell commands.

This boundary is kept because it makes the product simpler and prevents accidental misuse, not because the owner is treated as an attacker.

## 8. State model

Implementation may use names equivalent to:

```text
UP_TO_DATE
AVAILABLE
RECEIVING
CHECKING
STAGING
READY_TO_RESTART
PENDING_BOOT_CONFIRMATION
UPDATED
ROLLED_BACK
FAILED
UNAVAILABLE
```

Exact enum names remain source-owned.

## 9. Practical preflight

Before writing the inactive slot, check only useful failure conditions:

- bundle is readable and structurally bounded;
- profile/architecture/board compatibility matches;
- inactive slot has enough capacity;
- destination is not the active slot;
- candidate payload passes the fast completeness smoke check;
- boot backend supports one-shot candidate selection/rollback;
- power condition is acceptable where useful/reliably detectable.

Selecting an older compatible Greia version may show a warning and require explicit confirmation. It is not prohibited by an anti-rollback security mechanism.

## 10. Boot confirmation

A candidate is not accepted just because the kernel started.

Confirmation should mean the child appliance reached the minimum usable Greia Shell/service state required for normal recovery.

Missing confirmation must not create an infinite candidate-boot loop.

## 11. Implementation boundary

Use Greia's narrow shared update implementation:

```text
SlotWriter
SlotFinalizer
platform BootBackend
```

Do not grow a second package manager or a parallel updater per platform.

Raspberry Pi and x86 may implement boot selection differently underneath the same candidate/commit/rollback semantics.

## 12. Rejected normal-update approaches

Rejected:

- Parent browser directly running `apt upgrade`;
- in-place mutation of the active system root;
- platform-specific updater copies;
- automatic destructive repartition as an ordinary update;
- irreversible shared-data migration before candidate acceptance;
- treating file tampering/signature verification as a core product requirement.

## 13. Product rule

The parent-facing experience remains approximately:

```text
Choose update -> Preparing -> Ready to Restart -> Restart & Update
```

If candidate boot fails:

```text
Greia restored the previous version. Child data was preserved.
```

Linux/package/slot/bootloader mechanics remain hidden from ordinary parent and child workflows.
