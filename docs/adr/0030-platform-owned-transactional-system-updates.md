# ADR 0030 — Platform-Owned Transactional System Updates

**Status:** ACCEPTED architecture; implementation incremental/evidence-gated  
**Date:** 2026-08-19  
**Scope:** Greia OS/runtime updates, delivery, authenticity, activation, rollback, Parent control and offline update paths  
**Extends:** ADR 0012; active-plan R13B

## 1. Decision

Greia system/runtime updates are a **platform-owned appliance service**. The Greia Parents client may discover, upload, authorize and observe an update, but it MUST NOT execute package-manager commands, write boot/system partitions, select boot slots, or implement rollback itself.

The stable product model is:

```text
Internet / Parents upload / USB-SD
              |
              v
       Greia update bundle
              |
       verify authenticity
       verify compatibility
       power/space preflight
              |
              v
   privileged SystemUpdateService
              |
              v
       inactive system slot
              |
        pending reboot
              |
      boot health check
        /          \
   confirm        rollback
```

Delivery source and activation mechanism are deliberately separate. All delivery paths feed the same verified bundle/service contract.

## 2. A/B system direction

The target release layout is logically:

```text
boot-selection metadata
system slot A
system slot B
persistent Greia data
```

Routine updates write only the **inactive** system slot. The active known-good system is not modified in place. After complete verification/staging, Greia arms exactly one pending boot into the candidate slot. The candidate must confirm platform health before it becomes the new known-good slot. Failure or missing confirmation rolls back to the previous slot.

A machine/backend may implement these semantics differently below a typed slot backend, but it may not weaken the observable guarantees.

The existing `bios-single-ext4` profiles are **not** retroactively claimed to be A/B capable. Until a profile has a proven slot layout/backend, system-update activation MUST report unavailable rather than falling back to in-place `apt`, file copy, `dd` to the active root, or other destructive shortcuts.

## 3. Persistent child data is outside routine system slots

Profiles, Activity saves/creations, progression/rewards/awards, Parent credentials, device configuration and other logical Greia state must survive system-slot replacement.

Rollback is only real if shared-data migrations are rollback-safe. An unconfirmed candidate OS MUST NOT irreversibly migrate shared state beyond what the previous known-good OS can recover/read. Migration strategies may include backward-compatible schemas or transactional migration snapshots, but irreversible mutation before boot confirmation is forbidden.

## 4. Update bundle

The portable system update artifact uses the suffix:

```text
.greiaupdate
```

The format is intentionally transport-neutral. A bundle contains, at minimum:

```text
manifest.json
manifest.sig
payload.bin
```

The manifest identifies the release, target platform family/architecture/profile compatibility, payload size/hash and signer. The signature authenticates the canonical manifest. The payload hash binds the payload bytes to that signed manifest.

Production update bundles MUST be signed by a trusted Greia release key. HTTPS alone is not release authenticity. Unsigned production activation is forbidden.

Exact schema/limits are source-owned by `src/greia_platform/system_updates.py` and its tests. Documentation examples are not a second parser definition.

## 5. Whole-system payloads first

The initial supported release strategy is a complete system-slot payload, not package-by-package mutation and not binary delta patching.

Reasons:

- the tested release image is the image installed;
- interrupted package scripts cannot leave a half-upgraded active root;
- rollback remains understandable;
- cross-architecture/profile compatibility can be checked before writing;
- later delta transport can be added without changing Parent/API semantics.

Routine updates SHOULD NOT rewrite the partition table or bootloader itself. Bootloader/layout migrations require a separately reviewed recovery-capable path.

## 6. Delivery sources

Greia supports one update service with interchangeable sources:

1. **Network source** — Greia itself downloads an advertised release after Parent authorization/policy permits it.
2. **Parents upload** — a Parent client uploads a `.greiaupdate` file to Greia.
3. **USB/SD source** — Greia discovers a bundle on removable media and offers it through a Parent-authorized flow.

The Parents app does not need to remain connected during staging/activation. For normal online updates, Greia should download directly rather than relaying a large release through the phone/browser.

## 7. Parent API boundary

The Parent API exposes semantic update operations/status, for example:

```text
read update status
check availability
queue/upload bundle
prepare verified candidate
request restart when ready
```

Exact routes/states are protocol-source-owned.

The Parent HTTP service remains unprivileged. Receiving a bundle is not system authority. Privileged slot writes, boot selection, reboot and boot confirmation belong to the dedicated system update service/backend.

No API may expose arbitrary `apt`, `dpkg`, `mount`, `dd`, GRUB commands, shell commands or arbitrary filesystem destinations.

## 8. State model

The implementation should distinguish at least these semantic phases even if exact enum names differ:

```text
UP_TO_DATE
AVAILABLE
RECEIVING
VERIFYING
VERIFIED
STAGING
READY_TO_RESTART
PENDING_BOOT_CONFIRMATION
UPDATED
ROLLED_BACK
FAILED
UNAVAILABLE
```

Errors must be bounded parent-readable classifications; detailed diagnostics may remain in privileged logs.

## 9. Safety preflight

Before activation, Greia must verify:

- signature/key trust;
- bundle schema and bounded archive structure;
- payload hash and declared size;
- target platform family/architecture/profile compatibility;
- no prohibited downgrade unless an explicit recovery policy authorizes it;
- sufficient inactive-slot capacity/free working space;
- suitable power condition where the hardware can report it;
- candidate slot is not the currently active slot;
- boot backend supports atomic/pending selection and rollback semantics.

Any failed trust/safety check fails closed.

## 10. Boot confirmation

A candidate is not accepted merely because the kernel started. The selected backend must have a bounded boot-attempt/health-confirmation mechanism. Confirmation should require the minimum Greia platform health necessary to know that the child appliance can recover into a usable Shell/service state.

Missing confirmation causes rollback; it must not create an infinite candidate-boot loop.

## 11. Cryptographic implementation boundary

Greia will not implement custom cryptographic primitives. Release signing/verification uses a reviewed library/tooling backend. The initial source contract uses Ed25519 manifest signatures with trusted public keys; production image composition must deliberately include and measure the verifier dependency before enabling update activation.

Private release signing keys never ship in Greia images or the Git repository.

## 12. RAUC evaluation

RAUC remains a strong candidate implementation below this ADR because its signed bundles, slot model and bootloader integration align closely with these semantics. It is **not selected merely by this ADR**. Before choosing it, Greia must measure package/disk/RAM/process/boot integration cost on the C0/Acer floor and verify GRUB plus Raspberry Pi backend fit.

A custom backend, if chosen, must meet the same transaction/rollback/authenticity contracts and must stay narrow rather than becoming a second package manager.

## 13. Initial implementation slice

The first source slice may safely implement before A/B migration:

- signed `.greiaupdate` build/inspect/verification primitives;
- an immutable verified-update inbox/store;
- typed update status and backend protocol;
- an explicitly unavailable backend for current single-root layouts;
- Parent API capability/status/upload plumbing;
- developer tooling to generate keys, build bundles and push them;
- focused provider-free tests.

It MUST NOT claim that current `bios-single-ext4` machines can activate updates.

## 14. Rejected alternatives

Rejected:

- Parent web app executing `apt upgrade` or shell commands;
- in-place mutation of the active root as the normal update model;
- trusting SHA-256 without publisher authentication;
- trusting HTTPS as the sole authenticity boundary;
- one update mechanism for Internet and a different installer for USB/Parents upload;
- automatically rebooting a child in the middle of an Activity;
- irreversible shared-data migration before candidate confirmation;
- pretending a single-root current profile has rollback because an old installer image exists.

## 15. Product rule

The parent-facing experience should remain approximately:

```text
Update available -> Update Greia -> Update ready -> Restart & Update
```

If the candidate fails:

```text
Greia restored the previous version. Child data was preserved.
```

Linux/package/slot/bootloader mechanics remain hidden from ordinary parent and child workflows.
