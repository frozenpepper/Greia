# Greia OS — Boot + Installation/Update Lifecycle Takeover Plan

**Status:** Draft replacement execution authority for discussion / owner ratification  
**Date:** 2026-09-08  
**Repository reviewed:** `frozenpepper/Greia`  
**Current reviewed `main`:** `225102f022147261cee209529ff442ca7a3070c5`  
**R2 work-folder reviewed:** uploaded `R2.zip`  
**Supersedes for future execution:** the current R2 boot/install execution sequence from the present legacy-BIOS proof boundary onward; earlier accepted implementation is retained unless this plan explicitly reopens it.  
**Does not supersede:** the core architectural intent of D23–D50 unless an explicit additive amendment below says so.

---

## 1. Executive decision

Greia should **not** restart the installation/update architecture and should **not** continue directly into UEFI, Pi, Universal Setup composition, or destructive hardware migration yet.

The architecture is directionally strong. The immediate problem is that several release-blocking defects were allowed to pass as “planner-owned follow-up” debt without being converted into dependency-bound tasks. That has left the legacy BIOS tranche source-rich but not executable as one real production lifecycle.

The next milestone is therefore:

> **Prove one complete legacy-BIOS installation → first boot → health acceptance → update → candidate boot → health acceptance → deliberately failed update → bounded recovery/rollback cycle on disposable media, through production composition, under Greia’s RAM/storage constraints, with PERSIST compatibility and reboot-surviving evidence.**

Only after that milestone is green should the same lifecycle semantics be propagated into UEFI and Pi adapters.

This is a **re-gating and completion pass, not a redesign**.

---

## 2. What changed since the external review baseline

The new external analysis reviewed through `632c22c3`.

Current `main` is `225102f022147261cee209529ff442ca7a3070c5`. The two later commits are launcher/profile-selection deferral work:

- `b9fbe378485eb93f0dc0acefda537577bafac70c` — `perf(launcher): defer profile-selection filesystem writes (#190)`
- `225102f022147261cee209529ff442ca7a3070c5` — `perf(launcher): complete profile-selection deferral (#191)`

Those commits are useful boot-path work, but they do **not** change the lifecycle files implicated by the external review. The installation/update findings remain current at the reviewed `main`.

Current repository evidence also records physical motion-during-intro acceptance. Preserve that as a narrow boot-UX proof: it shows the intro/input path no longer restarts or bursts input after intro. It does **not** prove installation, A/B update, production health wiring, or rollback.

---

## 3. What R2 has actually completed, and what remains

### 3.1 Preserve implemented work

The following architecture/substrate work should be retained and built upon:

- signed `.greiaupdate` v2 release authority;
- release sequence / anti-rollback model;
- persistent-state contract and namespace concepts;
- shared `SlotWriter` / `SlotFinalizer` direction;
- A/B boot transaction/journal abstractions;
- typed installer target identity and target-policy direction;
- narrow installer/update privileged protocol work;
- trusted boot-health source protocol and launcher seam;
- common destructive loop/disposable substrate;
- legacy BIOS A/B layout implementation;
- GRUB A/B semantic backend;
- legacy fresh-install and sequenced update source implementations;
- source-scope QEMU harness foundations;
- boot work already integrated for build-time immutable Activity validation, launcher-preparation reduction, first-frame readiness, intro/input continuity, and the latest profile-selection write deferral.

Do not duplicate these with new managers, image formats, writers, finalizers, installers, or boot transaction frameworks.

### 3.2 Current R2 frontier

R2 shows the following material state:

- **Phase 7/common lifecycle:** integrated at source level; `L7-ACER` remains active/non-final.
- **Phase 8A/common destructive substrate:** integrated/accepted at source and disposable-test scope.
- **Phase 8B/legacy BIOS:** layout, GRUB, fresh install, update, and QEMU harness are integrated at source scope.
- **`X8-QEMU-RUN`: planned, not executed.**
- **`X8-ACER-PREFLIGHT`: planned, not executed.**
- **Phase 8C / boot-11 UEFI tasks (`U8-*`): planned only.**
- **Phase 8D / boot-12 Pi tasks (`PI8-*`): planned only.**
- **Phase 8E / boot-13 Universal Setup tasks (`M8-*`): planned only and blocked on Pi proof.**
- **Phase 8F / boot-14 delivery/Parent tasks (`D8-*`): planned only.**
- **Phase 8G / boot-15 destructive acceptance tasks (`G8-*`): planned only.**
- **Phase 9 / boot-16 HOST_FAST tasks (`H9-*`): planned only.**
- **Phase 10 / boot-17 residual optimization tasks (`R10-*`): planned only.**
- **Phase 11 / boot-18 final guards/acceptance tasks (`F11-*`): planned only.**

The planner reports for phases 13–18 being “ready” must not be interpreted as those product phases being implemented or accepted.

### 3.3 Boot-performance task churn

R2 contains many superseded/planned/needs-analysis proof tasks from the physical boot-debug sequence. Do not blindly replay that historical task list. The current repository and HANDOVER contain newer physical evidence and later launcher commits.

Create one takeover-ledger task that maps each remaining boot proof predicate to current `main` evidence. Supersede stale task IDs when newer evidence already proves the same predicate. Preserve the 7-second intro exactly.

---

## 4. Review of the new external analysis

### 4.1 Legacy MBR PARTUUID model — **VALID, release-blocking**

Current legacy layout code creates an `msdos` partition table but mints UUID4-shaped partition identities. Current GRUB validation requires canonical UUID-shaped PARTUUIDs.

That is not the identity shape Linux exposes for DOS/MBR partitions. Linux derives an MBR partition UUID from the disk signature plus partition number (for example `1234abcd-02`). The current abstraction therefore conflates GPT-style GUID partition identity with MBR partition identity.

This finding should reopen the legacy identity/GRUB acceptance boundary.

### 4.2 `search --part-uuid` in generated GRUB — **VALID concern; executable proof required**

The current generator emits `search --part-uuid`. GNU GRUB’s documented `search` modes are file, filesystem label, and filesystem UUID. Text validation of Greia’s generated config is not evidence that the shipped GRUB binary executes this command.

Recommended architecture:

- treat **GRUB’s filesystem locator** and **Linux’s kernel root locator** as separate semantic facts;
- resolve the slot in GRUB by filesystem UUID (`search --fs-uuid`) unless the exact shipped GRUB binary proves another supported primitive;
- keep `root=PARTUUID=...` for the Linux/initramfs root locator if that remains the desired kernel contract;
- bind both to the same semantic slot in Greia’s layout authority and validator, without requiring their strings to be identical.

This is cleaner than inventing a fake UUID format to satisfy one validator.

### 4.3 Fresh install buffers the whole payload in RAM — **VALID, release-blocking, and already a plan violation**

The current `open_bundle_payload_stream` path reads `payload.bin` fully from the ZIP and wraps it in `BytesIO` before the shared writer streams it.

This is especially important because the governing plan already says in **D33**:

> payload staging is streamed; the same streaming primitive is used from Setup media during fresh installation; working memory is bounded and measured on C0.

The R2 X8-INSTALL reviewer already identified this exact problem but classified it as non-blocking planner debt. That classification was too weak: it contradicts a frozen decision and the 768 MiB floor.

### 4.4 QEMU harness cannot execute its own promised lifecycle — **VALID, release-blocking**

R2’s own X8-QEMU-HARNESS reviewer explicitly recorded that:

- `run()` refuses a pre-existing image;
- no image-assembly path creates that image;
- the production loop does not perform the inter-boot stage/arm/health/commit/reconcile transitions;
- PERSIST markers and resource reports are not actually populated by the production run path.

Yet `X8-QEMU-RUN` is a verification task with **Allowed source changes: NONE**.

That creates an orchestration contradiction: the known defects cannot be repaired by the task that is supposed to close them.

The harness task must be reopened or superseded by a correction task before the run task.

### 4.5 Production composition is missing — **VALID, release-blocking**

The pieces exist, but the shipped path is not assembled end to end:

- the installer service can accept an A/B executor, but the production builder does not provide the complete production executor/mount/staging composition;
- the privileged updater entry point still fails closed because its destructive backend is not wired;
- R2 source reviews explicitly defer live listener/peer binding, production observer, credential transport, actual slot-filesystem/mount composition, and launcher/on-device call-site wiring to downstream work.

Those are not optional release polish. They are the path that turns source components into the product.

A release-capable A/B profile must fail closed if this composition is absent. It must never silently fall back to the legacy single-root install path.

### 4.6 Reboot-surviving diagnostics — **VALID and should move earlier**

Current journald is explicitly volatile (`Storage=volatile`), and `/run` marker state does not survive reboot.

The governing architecture already allows explicitly classified bounded persistent logs/evidence under D30, but no product-level previous-boot record currently closes the debugging/recovery gap.

Implement a very small PERSIST boot/lifecycle record rather than making all journald persistent.

### 4.7 Documentation conflicts — **VALID**

Current operational docs disagree on at least:

- progress bar vs spinner/current intro behavior;
- persistent diagnostics vs `Storage=volatile`;
- one normal GRUB entry vs the A/B backend’s two semantic entries.

The active large lifecycle/boot authority also lives in the R2 work folder rather than as one canonical repository plan. That creates drift risk for both humans and future agents.

### 4.8 “Measure usable boot, not only visible boot” — **ACCEPT, add as a KPI**

Keep the existing primary pre-intro KPI, but add:

- `T_first_frame`: power-on → first intro frame;
- `T_interactive_ready`: power-on → usable profile picker / child home interaction;
- `T_intro_to_interactive_delta`: intro end → interactive readiness.

The 7-second intro remains intentional. A deferral is not an optimization if it simply moves a pause behind the animation.

### 4.9 Failure UX — **ACCEPT, release requirement but not a reason to redesign lifecycle core**

Define bounded launcher retries and a stable Greia recovery surface with parent-facing instructions. Endless X-session restart, a frozen splash, or a black screen are not terminal product states.

### 4.10 Rollback trigger — **ACCEPT; current semantics need an explicit recovery mechanism**

One-shot boot selection preserves the previous default for the next boot, but it does not itself cause a hung candidate to reboot.

Greia must explicitly distinguish:

- userspace/launcher failure where the OS can still trigger a controlled reboot;
- kernel panic where an automatic panic reboot can be configured/proven;
- total hardware/kernel hang where automatic recovery requires a reliable hardware watchdog; otherwise recovery occurs at the next manual power cycle.

Do not claim “automatic rollback from every hang” on hardware that cannot physically guarantee the reset.

### 4.11 Shared child data compatibility — **ACCEPT, but this is enforcement of existing D31 rather than a new architecture**

D31 already requires pending releases either to remain readable by the accepted release or to write transactionally/versioned so pending changes can be abandoned on rollback.

What is missing is strong acceptance evidence. The legacy disposable cycle must include a candidate that writes real representative settings/save/progression state and then fails. The previous release must read the resulting PERSIST state correctly.

### 4.12 Whole-machine budget — **ACCEPT; move a first resource gate earlier**

The old plan puts full resource budgeting in 8G.9. That is too late to discover that the foundational lifecycle cannot fit the C0 machine.

Add a legacy disposable/C0-class budget gate before adapter proliferation. Keep the later 8G.9 cross-platform final budget as well.

### 4.13 Per-adapter proof — **KEEP; already philosophically correct**

The original 8B/8C/8D split is right. BIOS, UEFI, Pi400 and Pi500 may share transaction semantics, but must not share unproven firmware/identity assumptions.

---

## 5. Process correction: evidence grades and debt ownership

This is the most important orchestration improvement beyond the source fixes.

R2 currently allows a task to PASS at “source scope” while listing a release blocker under “planner-owned follow-up.” That is acceptable only if the follow-up immediately becomes an explicit dependency-bound task. That did not consistently happen.

From this plan onward, record **two orthogonal states**:

### 5.1 Task integration state

- `PLANNED`
- `INTEGRATED`
- `SUPERSEDED`
- `BLOCKED`

### 5.2 Evidence grade

- **S — Source:** implementation + static/unit/contract tests.
- **V — Virtual/Disposable:** actual disposable disk / firmware / reboot lifecycle executed.
- **H — Hardware:** exact reference hardware path executed.
- **R — Release:** all required adapters, resource budgets, recovery, data compatibility, docs and source guards green.

A source-integrated task can legitimately be `INTEGRATED / S`. It must not be described as “accepted lifecycle” when the gate requires V or H evidence.

### 5.3 No orphan release blockers

Any reviewer observation that conflicts with a frozen decision, a phase gate, supported-hardware floor, destructive safety rule, or production-composition requirement is **blocking debt**.

Before that review may close, the orchestrator must do one of:

1. fix it in the current task; or
2. create a named successor task with an explicit dependency before the affected gate; or
3. escalate to owner because the governing decision must change.

“Planner-owned follow-up” with no task ID is not an acceptable terminal state for blocking debt.

---

# 6. Replacement execution plan

## TAKEOVER-0 — Canonicalize authority and reconcile the ledger

**Goal:** make the new plan the single current execution authority without losing prior work.

### Work

1. Commit this takeover plan into the Greia repository under one canonical path, e.g.:
   - `docs/plans/GREIA_BOOT_INSTALL_LIFECYCLE_TAKEOVER_2026-09-08.md`
2. Add a compact current-status table with:
   - current `main` SHA;
   - original R2 task ID;
   - integration state;
   - evidence grade S/V/H/R;
   - whether reopened by this plan;
   - replacement task if superseded.
3. Preserve D23–D50. Add only explicit additive decisions needed by this plan.
4. Reconcile the old boot-performance task churn against current `main` and current HANDOVER evidence. Do not rerun stale superseded hardware tests merely because R2 still says `planned`.
5. Mark the old external/work-folder plan as historical once the canonical plan is committed.
6. Put a prominent pointer from HANDOVER to the canonical plan and current evidence index.

### Gate T0

- one canonical plan is in Git;
- every known release blocker below has an owner task;
- current R2 work is neither discarded nor falsely marked complete.

---

## TAKEOVER-1 — Repair legacy partition identity and GRUB root resolution

**Reopens/supersedes evidence from:** `X8-LAYOUT`, `X8-GRUB`.

### T1.1 — Make partition identity layout-specific and observed

Do not represent every partition ID as a canonical UUID.

Introduce a narrow typed representation/validator, for example:

```text
PartitionIdentity
  scheme = GPT_GUID | MBR_PARTUUID
  partuuid = normalized opaque/typed value
  filesystem_uuid = canonical filesystem UUID
```

For legacy MBR:

1. create the DOS partition table;
2. ensure/obtain the disk signature through a controlled supported tool path;
3. partition;
4. settle udev;
5. probe the actual resulting partitions;
6. bind layout authority to the **observed** MBR PARTUUIDs and observed/role-owned filesystem UUIDs;
7. verify topology before any boot configuration is committed.

Never mint an independent UUID4 and label it an MBR PARTUUID.

GPT and Pi adapters later implement their own parsers/observation rules behind the same semantic interface.

### T1.2 — Separate GRUB file lookup from Linux root lookup

Recommended default:

- GRUB locates each slot filesystem using its filesystem UUID via a documented `search --fs-uuid` primitive;
- Linux/initramfs receives the slot’s observed `root=PARTUUID=...` if that remains the chosen kernel ABI;
- Greia validates that both identifiers belong to the same semantic slot in the installed layout record.

If the exact shipped GRUB package demonstrably supports a different partition-UUID search primitive, it may be used only after an executable test pins that fact. Do not let Greia’s own parser certify a GRUB command that has never been executed.

### T1.3 — Disposable real-partition proof

On a genuinely partitioned raw image/loop device:

- create MBR layout;
- probe actual disk signature/PARTUUIDs;
- persist record;
- reload record after teardown/remount;
- prove A/B/PERSIST identity resolution;
- prove wrong disk signature, swapped partitions and cloned filesystem UUIDs fail closed;
- install the exact GRUB artifact and execute its config in QEMU/SeaBIOS in the later lifecycle gate.

### Gate T1

- no fabricated UUID4 MBR PARTUUIDs;
- record matches real block topology;
- GRUB locator uses a proven primitive;
- kernel root locator is independently correct;
- source tests + disposable partition probe green.

---

## TAKEOVER-2 — Restore true streaming and prove the C0 memory bound

**Reopens:** `X8-INSTALL` memory acceptance.  
**Enforces existing decision:** D33.

### T2.1 — Fix ZIP member ownership

Replace whole-member `ZipFile.read(...) -> BytesIO(...)` with a context-managed live ZIP member stream whose archive lifetime spans the writer consumption.

Requirements:

- no full uncompressed `payload.bin` allocation;
- no second extracted payload copy on disk;
- manifest-declared uncompressed size is bounded before write;
- stream errors propagate as transaction failure;
- archive/member handles close deterministically on success/failure;
- hash/readback semantics remain owned by the shared `SlotWriter`.

### T2.2 — Measure the whole install/update path

Measure peak memory across:

- bundle verification;
- decompression;
- slot write;
- readback verification;
- filesystem role binding/expansion;
- finalization;
- initramfs/boot artifact generation;
- PERSIST initialization;
- boot configuration.

Do not report only the writer chunk size.

### T2.3 — 768 MiB gate

Run a representative/max-size signed release through the disposable install and update path with a **768 MiB machine/guest limit**.

Acceptance:

- no OOM;
- no swap-thrash dependency;
- peak RSS/anonymous memory recorded;
- peak memory does not scale approximately 1:1 with uncompressed payload size;
- a payload large enough to expose accidental whole-buffering is used as a positive control.

### Gate T2

D33 is true in the real fresh-install path, not only in `SlotWriter` internals.

---

## TAKEOVER-3 — Wire one production lifecycle composition

**Reopens/completes:** `A8-INSTALL-SVC`, `A8-UPDATE-SVC`, `X8-INSTALL`, `X8-UPDATE`, L7 health/protocol production seams.

This is the most important source-completion tranche.

### T3.1 — Production A/B install executor

The shipped installer service builder must construct the release-capable A/B executor for an A/B profile using only device-owned/profile-owned configuration:

- trusted signer/key directory;
- release bundle source resolved by Setup authority;
- typed layout adapter;
- production semantic slot-filesystem/mount implementation;
- shared `SlotWriter`;
- shared `SlotFinalizer`;
- PERSIST authority;
- boot backend;
- journal;
- hardware inventory/support finalization.

A release-capable profile with missing composition is a hard failure **before destructive work**.

It must never silently route to the old single-root engine.

Legacy/single-root recovery profiles remain explicit and update-activation-disabled.

### T3.2 — Production update backend

Wire the privileged update service through the same:

- signed release inspection;
- layout authority;
- inactive-slot resolution;
- writer/finalizer;
- boot transaction backend;
- journal;
- health acceptance.

The production update entry point must no longer exist only as an “unwired backend” fail-closed stub for release-capable A/B profiles.

### T3.3 — Production health composition

Complete the on-device chain:

```text
actual boot observation
  -> boot/release/slot identity
  -> one-use credential
  -> OS-attested narrow health endpoint
  -> trusted launcher path
  -> FIRST_FRAME_VISIBLE
  -> full 7-second intro
  -> INTERACTIVE_READY
  -> confirm + finalize healthy transaction
  -> only then enable untrusted Activity launch
```

Requirements:

- peer identity is kernel/OS-attested at the socket boundary, not merely caller-supplied text;
- production `ActualBootObserver` resolves real booted slot/release/root identity;
- credential transport is the production systemd credential/service path;
- launcher calls the production health seam at the real lifecycle transition;
- first-frame systemd readiness remains separate from update health;
- first install uses the same health predicate without pretending it has rollback.

### T3.4 — Composition proof

A source/integration test must instantiate the **shipped profile composition**, not isolated fakes, and prove:

```text
profile
 -> installer socket/service
 -> signed release
 -> A/B/PERSIST layout
 -> finalized SYSTEM_A
 -> boot backend
 -> FIRST_INSTALL_PENDING
 -> observed boot
 -> trusted health
 -> accepted A
```

And for update:

```text
accepted A
 -> signed B
 -> inactive write/finalize
 -> one-shot arm
 -> observed B
 -> trusted health
 -> persistent default B
 -> accepted record B
```

### Gate T3

There is one reachable production call graph from shipped service/profile to lifecycle completion. No essential step exists only behind a test injection seam.

---

## TAKEOVER-4 — Specify and implement bounded failed-candidate recovery

**Adds explicit mechanism to existing one-shot rollback semantics.**

### T4.1 — Common recovery contract

The boot transaction owns a candidate health deadline. A candidate that reaches the OS but fails to become healthy within the bounded deadline must trigger a controlled reboot while the previous accepted slot remains the persistent default.

Implement this as a narrow lifecycle capability, preferably through systemd and existing boot transaction state—not a generic daemon/manager.

### T4.2 — Failure classes

Prove and document separately:

1. launcher exits/crashes;
2. userspace reaches emergency/failure state before health;
3. health service fails;
4. kernel panic;
5. hard kernel/hardware hang.

Recommended product claim:

- cases 1–4 recover automatically where the platform can still execute a controlled/panic reboot;
- case 5 uses a hardware watchdog only on platforms where one is present and proven;
- otherwise the previous accepted slot is guaranteed to return on the **next physical power cycle**, but that is manual recovery and must be described honestly.

### T4.3 — Owner decision

Owner must decide whether Greia release support requires **fully unattended recovery from a total hard hang on every supported device**.

Recommended default: **No.** Require automatic recovery from recoverable userspace/panic failures; require safe previous-default recovery on next power cycle for an unrecoverable hard hang when the hardware lacks a proven watchdog. Requiring unattended recovery from every hang would become a hardware-support-floor requirement.

### Gate T4

Rollback is not merely “the old default still exists.” The plan identifies what causes the next boot, what is automatic, and what requires a parent power cycle.

---

## TAKEOVER-5 — Add bounded reboot-surviving lifecycle evidence

### T5.1 — Keep journald volatile by default

Do not make the whole journal persistent merely to debug boot.

### T5.2 — Add a tiny PERSIST boot/lifecycle record

Store a bounded current/previous boot summary under the persistent system namespace. Minimum facts:

- boot ID;
- monotonic/start timestamp where meaningful;
- semantic slot;
- release ID/sequence;
- transaction ID/type;
- last reached boot milestone;
- launcher exit/result;
- health confirm/finalize result;
- boot backend observed default/one-shot state;
- rollback/recovery reason;
- install/update transaction terminal state.

Recommended initial hard cap: **64 KiB total** for the structured boot-history ring, subject to measurement and source-level enforcement. This is not a log stream.

### T5.3 — Write budget

Persist only coarse lifecycle boundaries. Do **not** synchronously write animation frames, input events, or verbose journal messages.

A candidate implementation may rotate `current -> previous` at boot and update only a few critical milestones/terminal events.

### Gate T5

After a failed candidate and reboot, the next accepted system can explain which slot/release attempted to boot, the last durable milestone, and why recovery occurred without relying on volatile `/run` or the previous boot’s journal.

---

## TAKEOVER-6 — Rebuild the QEMU harness into a real lifecycle harness

**Supersedes the current `X8-QEMU-HARNESS` source-only closure and unblocks a new run task.**

The existing `X8-QEMU-RUN` brief cannot close this because it forbids source changes while the current runner is known to be incomplete.

### T6.1 — Harness owns disposable image assembly

The harness must:

- create its own raw disposable disk outside the source tree;
- apply the real `legacy-bios-ab-v1` layout;
- invoke the production-composed install path, not manually fabricate final state;
- install real GRUB/SeaBIOS-bootable artifacts;
- retain evidence only in the designated output directory;
- tear down loop/mount state safely.

### T6.2 — Lifecycle sequence

Execute at minimum:

1. **Fresh install release A**
   - signed release A;
   - create A/B/PERSIST;
   - A finalized, B inactive;
   - `FIRST_INSTALL_PENDING`.
2. **Boot A**
   - actual SeaBIOS/GRUB boot;
   - actual Greia boot/launcher health path if virtual graphics path supports it;
   - A becomes accepted/default.
3. **Stage release B**
   - inactive B only;
   - finalize B;
   - arm one-shot B;
   - persistent default remains A.
4. **Boot B**
   - one-shot consumed;
   - observe B;
   - trusted health;
   - commit B as persistent default/accepted.
5. **Stage deliberately broken release C/A-role candidate**
   - candidate is validly signed/processable but intentionally fails at a controlled post-boot condition;
   - arm candidate one-shot;
   - persistent default remains B.
6. **Boot broken candidate**
   - health does not confirm;
   - recovery trigger is exercised.
7. **Recovery boot**
   - previous B boots;
   - B remains accepted/default;
   - candidate transaction is failed/rolled back;
   - PERSIST remains valid.
8. **B → A successful update**
   - complete the reverse-slot path so slot role does not accidentally become release identity.

### T6.3 — Guest/disk observations are authoritative

After each transition record from the actual disk/guest:

- semantic slot/release;
- layout record;
- GRUB environment/default/one-shot state;
- transaction journal;
- persistent boot evidence;
- representative PERSIST state;
- release hashes;
- image SHA;
- boot outcome.

Do not generate a report whose `ok` flag is independent of those assertions.

### T6.4 — Positive controls

At least:

- disabling/defeating candidate health must make the harness detect failure and recovery;
- corrupting GRUB slot binding must make boot/config acceptance fail;
- breaking the expected rollback/default invariant must make the overall run RED;
- a runner that merely reboots the same disk seven times without lifecycle transitions must fail its own contract tests.

### Gate T6

The runner is executable end to end on the supported QEMU host and can fail for the right reasons.

---

## TAKEOVER-7 — Disposable legacy lifecycle acceptance

**Replaces old `X8-QEMU-RUN` with an executable acceptance task.**

### T7.1 — Execute the repaired harness

On a QEMU-capable Linux x86_64 host with real SeaBIOS/GRUB tooling.

### T7.2 — Include shared-data rollback proof

Before booting the deliberately broken candidate, have it perform representative **real Greia persistent-state writes** through normal store APIs, for example:

- a settings change;
- child/profile/progression state;
- an Activity save/creation fixture;
- Parent policy/state fixture where safe.

Then fail the candidate before acceptance.

The previous accepted release must:

- boot;
- parse/read the state;
- preserve semantic values;
- not require destructive repair.

This is the executable proof of D31.

### T7.3 — Interruption matrix, legacy first

Exercise at least:

- inactive base write interruption;
- base readback/finalization interruption;
- boot-artifact staging interruption;
- one-shot arm interruption;
- candidate boot before health;
- `HEALTHY_COMMITTING` before backend commit;
- backend committed but accepted-state record not yet written.

Previous accepted slot must remain/reconcile correctly.

### T7.4 — Resource envelope

Record:

- max RSS / `MemAvailable` across install and update;
- payload decompression memory;
- slot finalization peak;
- update staging workspace;
- raw disk used/free;
- both slot sizes;
- release bundle size;
- PERSIST minimum/headroom;
- diagnostic/history budget.

Run a near-full-storage case that still satisfies the declared minimum and prove the transaction either preflights successfully with reserved headroom or fails **before** destructive/staging work.

### Gate T7 — **Legacy lifecycle V-proof**

All must be green:

- real MBR identities;
- real SeaBIOS/GRUB boot;
- production install composition;
- production update composition;
- health/commit semantics;
- successful A→B and B→A;
- deliberately failed candidate recovery;
- D31 shared-data rollback compatibility;
- 768 MiB memory bound;
- near-full storage preflight;
- reboot-surviving evidence;
- fault reconciliation.

Only after T7 should Greia clone these semantics into additional platform adapters.

---

## TAKEOVER-8 — Legacy hardware preflight, no destructive migration yet

Resume/supersede `X8-ACER-PREFLIGHT` and the useful portion of active `L7-ACER` only after T7.

On the reference Acer, non-destructively verify:

- actual disk geometry/capacity vs corrected layout;
- actual same-session target identity quality;
- GRUB/BIOS tool compatibility;
- no hidden assumption that MBR PARTUUID is a UUID4;
- memory floor with representative verification/dry-run load;
- portable backup captures every PERSISTENT_SHARED class;
- restore of that backup into a disposable corrected A/B image;
- recovery media and exact STOP conditions.

No repartitioning of the valued Acer here.

### Gate T8

Acer is demonstrably eligible for the later exact-image migration, but remains unmodified.

---

# 7. Resume the original downstream plan, with amended gates

Once T7 is green, resume the original platform sequence. Do not discard its decomposition.

## 7.1 UEFI / current boot-11 `U8-*`

Resume:

- `U8-LAYOUT`
- `U8-SECURE`
- `U8-OVMF`
- `U8-PHYSICAL`

Amend acceptance to require:

- GPT PARTUUID parsing/validation is adapter-specific and observed;
- production composition is shared with legacy, not rebuilt;
- actual OVMF install → boot → update → failed-candidate recovery;
- Secure Boot ON/OFF;
- SATA/NVMe variants where supported;
- same PERSIST compatibility and evidence schema;
- exact automatic/manual recovery claims recorded for the platform.

Do not import the legacy MBR identity parser into GPT.

## 7.2 Pi 400 / Pi 500 / current boot-12 `PI8-*`

Resume the existing Pi plan after UEFI source/virtual proof is at its intended gate.

Retain:

- typed board detection;
- built-in microSD target policy;
- USB-first/card-absent setup flow;
- native tryboot/autoboot backend;
- Pi400 and Pi500 separate physical proof;
- no routine EEPROM rewrite.

Add:

- board-specific identity parser/observation;
- the same production lifecycle journal/health/data compatibility contract;
- explicit recovery trigger capability/limitation per board;
- bounded PERSIST previous-boot evidence;
- low-memory/storage proof appropriate to Pi hardware.

## 7.3 Universal Setup / current boot-13 `M8-*`

Resume:

- `M8-COMPOSER`
- `M8-MANIFEST`
- `M8-LOWMEM`
- `M8-BOOT-MATRIX`

Do **not** create a new install/update stack in the composer.

The exact Setup image must use the already-proven production services and same signed release artifact.

Keep the exact-image SHA boot matrix and Acer `toram` prohibition.

Extend `M8-LOWMEM` to measure:

- verification;
- UI;
- dry-run plan;
- full install on disposable C0-class target where available;
- no whole-payload RAM copy.

## 7.4 Delivery + Parent / current boot-14 `D8-*`

Resume the current chain:

`D8-CHANNEL -> D8-FETCH -> D8-API -> D8-HTML -> D8-MOBILE -> D8-PROOF`

Keep Parent unprivileged and semantic.

No arbitrary URL/path/device/boot arguments.

UI should report rollback in product language and say child data was preserved only when the persistent compatibility proof is actually green.

## 7.5 Cross-platform destructive acceptance / current boot-15 `G8-*`

Resume only after exact Setup image proof.

Keep:

- exact BOM;
- portable backup/restore;
- single reference Acer migration;
- Acer successful update + forced failed candidate;
- modern hardware path;
- Pi400 path;
- Pi500 path;
- cross-backend interruption matrix;
- final resource budgets;
- closeout.

Strengthen the gate so every backend records:

- recovery trigger behavior;
- shared-data rollback compatibility;
- previous-boot evidence;
- first-frame + interactive-ready boot metrics;
- actual maximum RAM/storage workspace.

## 7.6 HOST_FAST / current boot-16 `H9-*`

Keep fully optional and **after** release-capable lifecycle acceptance.

Do not let HOST_FAST become the only recovery path.

## 7.7 Residual boot optimization / current boot-17 `R10-*`

Keep the measurement-first rule.

Add the dual KPI:

- first visible intro frame;
- interactive-ready profile picker/home.

An optimization is accepted only if it does not improve the first metric by hiding an equal/larger delay behind the 7-second intro.

## 7.8 Final guards/acceptance / current boot-18 `F11-*`

Retain the existing final guard sequence and add permanent guards for:

- no whole-payload `ZipFile.read(payload)` path;
- layout-specific partition identity validation;
- release-capable profile cannot select legacy single-root install fallback;
- update privileged service cannot ship unwired on an A/B-enabled profile;
- production health call graph exists;
- QEMU lifecycle report derives success from required state assertions;
- bounded PERSIST boot-history schema/size;
- docs do not claim persistent journald while `Storage=volatile`;
- boot documentation is backend/layout-specific where necessary.

---

# 8. Boot UX and performance lane

The lifecycle correction does not undo the boot work already completed.

## 8.1 Preserve

- the intentional 7-second intro;
- build-time immutable Activity validation;
- first-frame readiness separation;
- intro motion/input fixes;
- launcher preparation reduction;
- profile-selection filesystem write deferral;
- current low-resource philosophy.

## 8.2 Add dual timing evidence

Every reference boot sample should record:

```text
power-on -> first visible intro frame
power-on -> intro complete
power-on -> INTERACTIVE_READY
intro complete -> INTERACTIVE_READY delta
```

Also record launcher/system RSS at first frame and interactive ready.

## 8.3 Stable recovery experience

Before final release, add a bounded terminal launcher failure path:

- a small finite restart policy;
- if still unhealthy, enter a stable Greia-branded recovery surface;
- parent-facing plain-language instructions;
- display whether a system update was rolled back/recovered when known;
- never launch Activities in the failed state;
- never loop X/session restarts forever.

This should consume lifecycle/recovery state; it must not invent a second recovery authority.

---

# 9. Storage/resource policy

Do not wait until final physical acceptance to learn the product does not fit.

Use two resource gates:

### Early legacy gate (T7)

Prove the lifecycle on C0-class RAM and a near-minimum disposable disk.

### Final cross-platform gate (8G/G8)

Freeze actual product minimums from measured:

```text
Setup medium raw/compressed size
SYSTEM_A capacity
SYSTEM_B capacity
PERSIST minimum + reserved child-data headroom
one downloaded release bundle
transaction/finalization workspace
boot-control/ESP/FAT overhead
persistent lifecycle evidence
recovery/backup requirements
```

Preflight must reserve enough space for the transaction before mutating an inactive slot or target disk.

Do not set the public minimum storage size from the old 800/1000/1250 MiB comparison alone.

---

# 10. Documentation cleanup

## Immediate

- commit this plan;
- add one current lifecycle status/evidence ledger;
- make old external R2 plan historical, not competing authority;
- add warnings/pointers in operational docs where currently false statements could mislead execution.

## After corrected legacy semantics settle

Reconcile:

- `docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md`;
- current boot progress/design docs;
- GRUB guidance per backend;
- journald vs persistent boot-evidence behavior;
- installer/update architecture docs;
- Setup media architecture;
- Parent update behavior;
- skills `greia-os-work/SKILL.md` and `BOOT.md` where normative behavior changed.

## HANDOVER policy

Keep HANDOVER as a current checkpoint:

- current SHA;
- current plan link;
- current gate;
- last accepted evidence links;
- current blockers.

Move long historical evidence into dated evidence files rather than endlessly duplicating numbered HANDOVER sections.

---

# 11. Proposed additive architectural decisions

These do not replace D23–D50; they close ambiguities exposed by implementation.

## D51 — Partition identity representation is adapter-specific and observed

`PARTUUID` is not globally “a UUID object.” Each layout adapter owns parsing/normalization. Persistent layout authority records identities observed from the created/probed block topology.

## D52 — Bootloader file lookup and kernel root lookup are separate semantic locators

A bootloader may locate a filesystem by filesystem UUID while the kernel receives a partition identity. Both bind to the same slot; they do not need identical syntax or capability.

## D53 — A frozen streaming decision is a release gate, not an optimization

Whole-payload buffering in fresh install/update is forbidden on release-capable profiles. Memory proof covers the complete transaction.

## D54 — Production composition is part of feature completeness

A service/protocol/backend that exists only behind injected fakes is source substrate, not a finished feature. Release-capable profiles fail closed when production composition is absent; they do not silently fall back.

## D55 — Failed-candidate recovery has an explicit trigger contract

One-shot fallback defines *where* the next boot goes; the lifecycle also defines *what causes* that next boot for recoverable failures. Hard-hang guarantees are limited by proven watchdog capability.

## D56 — Previous-boot lifecycle evidence is a bounded PERSIST namespace

Detailed journal stays volatile unless separately justified. A tiny structured record survives reboot for transaction/recovery diagnosis.

## D57 — Boot performance has visible and usable KPIs

The intentional 7-second intro remains. `T_first_frame` and `T_interactive_ready` are both release metrics; deferral may not merely relocate latency behind the intro.

## D58 — Blocking review debt must have a successor edge

A release-blocking reviewer observation cannot terminate as unnamed “planner-owned follow-up.” It must be fixed, explicitly tasked before the gate, or escalated.

---

# 12. Exact high-level dependency graph

```text
T0 Canonical plan + status ledger
 |
 +--> T1 Legacy MBR identity + GRUB locator correction
 |      |
 |      +--> T2 True streaming + 768 MiB proof
 |              |
 |              +--> T3 Production install/update/health composition
 |                      |
 |                      +--> T4 Explicit failed-candidate recovery trigger
 |                      |      |
 |                      |      +--> T5 Reboot-surviving bounded evidence
 |                      |              |
 |                      |              +--> T6 Repair executable QEMU lifecycle harness
 |                      |                      |
 |                      |                      +--> T7 Full disposable legacy lifecycle V-proof
 |                      |                              |
 |                      |                              +--> T8 Acer non-destructive preflight
 |                      |                              |
 |                      |                              +--> U8 modern UEFI
 |                      |                                      |
 |                      |                                      +--> PI8 Pi400/Pi500
 |                      |                                              |
 |                      |                                              +--> M8 Universal Setup image
 |                      |                                                      |
 |                      |                                                      +--> D8 delivery/Parent
 |                      |                                                              |
 |                      |                                                              +--> G8 destructive matrix
 |                      |                                                                      |
 |                      |                                                                      +--> H9 optional HOST_FAST
 |                      |                                                                              |
 |                      |                                                                              +--> R10 optional residual boot work
 |                      |                                                                                      |
 |                      |                                                                                      +--> F11 final guards/release closure
 |
 +--> boot evidence-ledger reconciliation (read-only / no stale reruns)
```

Some source work inside T2/T3/T5 may be implemented in parallel if ownership is disjoint, but the **acceptance gates remain ordered** as shown.

---

# 13. Minimum complete disposable acceptance scenario

No later adapter work should start until this scenario passes:

### Install

- verified signed A release;
- production service path;
- real MBR identities probed;
- streamed write under memory bound;
- SYSTEM_A finalized;
- B inactive;
- PERSIST initialized;
- GRUB installed;
- first boot A;
- actual health acceptance;
- A persistent default.

### Successful update

- verified higher-sequence B;
- stage only inactive slot;
- finalize;
- arm one-shot;
- boot B;
- health;
- crash-reconcilable commit;
- B persistent default/accepted.

### Failed update

- verified higher-sequence deliberately broken candidate;
- make representative PERSIST writes through real APIs;
- one-shot boot candidate;
- fail before health;
- exercise defined recovery trigger;
- boot previous B;
- old release reads PERSIST correctly;
- candidate marked failed/rolled back;
- bounded previous-boot record explains failure.

### Reverse update

- stage a later good release into A;
- boot/health/accept A;
- prove slot role and release identity remain independent.

### Resource/fault envelope

- repeat under 768 MiB limit;
- near-minimum storage case;
- interruption at writer/finalizer/arm/healthy-commit boundaries;
- no accepted-slot corruption;
- no Setup/source-media mutation;
- no silent legacy fallback.

---

# 14. Owner decisions still needed

The plan can begin with the recommended defaults, but two product-level choices should be explicitly ratified.

## Decision A — hard-hang recovery guarantee

**Recommended:** Greia guarantees automatic rollback/reboot for failures where the OS can still trigger a reboot (including configured panic recovery), and guarantees previous-slot recovery on the next physical power cycle for a total hang on hardware without a proven watchdog.

**Alternative:** require fully unattended recovery from total hangs on every supported device. If chosen, reliable watchdog/reset capability becomes part of the supported-hardware floor and must be proven per adapter.

## Decision B — public storage floor

Do **not** choose a number now from old estimates. Measure T7 and final G8 envelopes first, then ratify the minimum supported target size plus reserved child-data headroom.

The architecture should reserve user/PERSIST headroom rather than consuming nearly all storage with A/B roots and update workspace.

---

# 15. What should happen next

The immediate orchestration sequence should be:

1. **TAKEOVER-0** — put this plan/status ledger under repository authority and supersede stale execution edges.
2. **TAKEOVER-1** — correct MBR identity and GRUB locator semantics.
3. **TAKEOVER-2** — fix payload streaming and prove memory behavior.
4. **TAKEOVER-3** — finish the actual shipped install/update/health composition.
5. **TAKEOVER-4/5** — define recovery trigger and durable minimal evidence.
6. **TAKEOVER-6** — repair the QEMU harness that R2 already knew was unwired.
7. **TAKEOVER-7** — run the complete disposable lifecycle, including deliberately failed candidate and PERSIST compatibility.
8. **TAKEOVER-8** — non-destructive Acer preflight.
9. Resume the already planned **U8 → PI8 → M8 → D8 → G8 → H9 → R10 → F11** chain with the amended gates above.

This preserves the strongest part of the existing Greia philosophy:

> **Do work at the lifecycle boundary that owns it, and require executable evidence before copying semantics into another adapter.**

The correction is to make “production composition” and “evidence grade” explicit boundaries too.

---

## 16. External technical references used for the identity/GRUB review

- Linux kernel DOS partition parser (`block/partitions/msdos.c`) — MBR partition metadata UUID is formed from disk signature + partition number.
- GNU GRUB Manual, `search` command — documented search modes are file, filesystem label and filesystem UUID.
- GNU GRUB root-identification documentation — Linux root may be passed using filesystem UUID or PARTUUID depending on configuration/initrd semantics.

These references do not replace executable proof against the exact GRUB/kernel artifacts shipped by Greia.

---

# Appendix T0 — Canonical status ledger (added by T0-PLAN, 2026-09-08)

This appendix is the TAKEOVER-0 compact status ledger. It does not amend
decisions D23–D50 (preserved) or D51–D58 (added by §§11 above). The body above
is the verbatim canonical takeover authority; this appendix only records
where each blocker lives now.

- **Canonical plan path:** `docs/plans/GREIA_BOOT_INSTALL_LIFECYCLE_TAKEOVER_2026-09-08.md`
- **Plan baseline cited by authority:** `225102f022147261cee209529ff442ca7a3070c5`
- **Current primary `main` at ledger time:** `48468c02bf2943021db5178269539eecf1abf8c3`
- **Ledger worktree HEAD (T-BAG checkpoint, no source change):**
  `890fd1773355c5ac6414b7bb6d0f521670a9fe1e`
- **Baseline drift check:** `225102f0..48468c02` touches only `HANDOVER.md`
  (§42 R2-abandoned note) and one launcher review doc; no
  `src/greia_installer`, `src/greia_platform` lifecycle, `tools/x8_qemu`, or
  `build` lifecycle file changed on the takeover paths. The plan's findings
  remain current.
- **R2 work-folder state** (`TBag/runs/R2/`, uploaded `R2.zip`) is historical
  context only. It is neither deleted nor authoritative; see `HANDOVER.md`
  §43 and the §42 R2-abandoned record.
- **Evidence grades** follow plan §5: `S` source, `V` virtual/disposable,
  `H` hardware, `R` release. `—` means no evidence yet. No row below claims
  `V`/`H`/`R` for lifecycle work that has only source scope.

| Takeover tranche / release blocker | Original R2 task ID(s) | Integration state | Evidence grade | Reopened by this plan | Owner / replacement task |
|---|---|---|---|---|---|
| T0 canonical authority + ledger (Gate T0) | — (new) | INTEGRATED | S | — | T0-PLAN (this tranche) |
| Boot proof-predicate reconciliation (§3.3 churn; 7-s intro preserved) | many R2 boot-debug proof tasks (superseded/planned/needs-analysis) | PLANNED | — | — (read-only triage, no reruns) | T0-LEDGER |
| T1 MBR identity (§4.1; D51) | X8-LAYOUT | INTEGRATED | S | YES | T1-IDENT |
| T1 GRUB locator (§4.2; D52) | X8-GRUB | INTEGRATED | S | YES | T1-GRUB |
| T2 streaming + 768 MiB bound (§4.3; D33/D53) | X8-INSTALL (memory acceptance) | INTEGRATED | S | YES | T2-STREAM |
| T3 production install composition (§4.5; D54) | A8-INSTALL-SVC, X8-INSTALL (production seam) | INTEGRATED | S | YES | T3-INSTALL |
| T3 production update + health composition (§4.5; D54) | A8-UPDATE-SVC, X8-UPDATE, L7 health/protocol seams | INTEGRATED | S | YES | T3-UPDATE |
| T4 explicit recovery trigger (§4.10; D55; owner Decision A default) | — (gap: one-shot exists, trigger undefined) | PLANNED | — | — (new mechanism) | T4-RECOVER |
| T5 bounded PERSIST boot record (§4.6; D56; D30) | — (gap: journald volatile, no previous-boot record) | PLANNED | — | — (new mechanism) | T5-EVID |
| T6 executable QEMU harness (§4.4; supersedes source-only closure) | X8-QEMU-HARNESS (source-only), X8-QEMU-RUN (planned, Allowed-changes NONE contradiction) | INTEGRATED (harness source) / PLANNED (run) | S / — | YES (harness) | T6-HARNESS |
| T7 disposable legacy lifecycle V-proof (Gate T7) | X8-QEMU-RUN (replaced by executable acceptance) | PLANNED | — | — (new acceptance) | T7-LIFE |
| T8 Acer non-destructive preflight (Gate T8) | X8-ACER-PREFLIGHT (planned), L7-ACER (active/non-final) | PLANNED / INTEGRATED (L7-ACER source, non-final) | — / S | partial (preflight resumed after T7) | T8-ACER |
| Phase 7 common lifecycle (preserved substrate) | L7-* lineage | INTEGRATED | S | NO (L7-ACER stays active/non-final) | T8-ACER for lifecycle relevance; T0-LEDGER for boot predicates |
| Phase 8A common destructive substrate (preserved) | 8A tasks | INTEGRATED | S | NO | — (substrate; later G8 matrix reuses it) |
| Phase 8B legacy BIOS substrate (preserved, reopened per-tranche above) | X8-LAYOUT, X8-GRUB, X8-INSTALL, X8-UPDATE, X8-QEMU-HARNESS | INTEGRATED | S | YES (see T1/T2/T3/T6 rows) | T1-IDENT, T1-GRUB, T2-STREAM, T3-INSTALL, T3-UPDATE, T6-HARNESS |
| UEFI adapters (8C / boot-11) | U8-LAYOUT, U8-SECURE, U8-OVMF, U8-PHYSICAL | PLANNED | — | NO (resume after T7) | DOWN-U8 |
| Pi adapters (8D / boot-12) | PI8-* | PLANNED | — | NO (resume after UEFI) | DOWN-PI8 |
| Universal Setup (8E / boot-13) | M8-COMPOSER, M8-MANIFEST, M8-LOWMEM, M8-BOOT-MATRIX | PLANNED | — | NO (blocked on Pi proof) | DOWN-M8D8 (with D8 chain) |
| Delivery + Parent (8F / boot-14) | D8-CHANNEL, D8-FETCH, D8-API, D8-HTML, D8-MOBILE, D8-PROOF | PLANNED | — | NO | DOWN-M8D8 (with M8 chain) |
| Cross-platform destructive acceptance (8G / boot-15) | G8-* | PLANNED | — | NO | DOWN-G8FINAL |
| HOST_FAST (boot-16, optional, after release-capable acceptance) | H9-* | PLANNED | — | NO | DOWN-G8FINAL |
| Residual optimization (boot-17, measurement-first + dual KPI) | R10-* | PLANNED | — | NO | DOWN-G8FINAL |
| Final guards/acceptance (boot-18 + §7.8 permanent guards) | F11-* | PLANNED | — | NO | DOWN-G8FINAL |
| Docs cleanup (§10 immediate; backend-specific reconciliation after semantics settle) | — | PLANNED | — | — | T0-PLAN (immediate ledger/pointer only); backend docs follow T1–T5 |

No live task above is shown green above its real evidence grade: every
`INTEGRATED` lifecycle row is grade `S` (source scope); every `V`/`H`/`R`
gate (T7, T8, downstream adapters) remains `PLANNED` until its executable
proof runs. Stale R2 `planned` boot proofs are not ordered for rerun by this
ledger; T0-LEDGER dispositions each predicate as
PROVEN / STALE-SUPERSEDED / STILL-OPEN with a named owner.
