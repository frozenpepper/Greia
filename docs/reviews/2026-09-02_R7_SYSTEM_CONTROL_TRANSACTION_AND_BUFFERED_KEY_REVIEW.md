# R7 Review — System-control transaction and buffered-key corrections

**Date:** 2026-09-02  
**Status:** source corrected; execution pending  
**Scope:** post-physical R7 system-control/hardware-session delta

## Evidence boundary

The trusted Greia Home regression was physically closed earlier at `57626d3f65a8bf3ae074eee15b00ee32ba3277bd`. The current review does not reopen that result. It examines the platform system-control tranche that landed afterward and therefore had not inherited that physical acceptance automatically.

## Finding 1 — relative media-key updates could lose a concurrent Parent write

`SystemControlSettingsStore` describes its persisted desired state as inter-process safe. Its absolute `update()` path took the shared file lock, but `SystemControlService.handle_action()` first performed an unlocked `store.read()`, computed a relative volume/brightness/mute value, and only then entered the separately locked `store.update()` operation.

That creates a classic stale-read/lost-update window:

1. media-key handler reads volume 70;
2. Parent process commits volume 35;
3. media-key handler enters `update()` using the already-computed 75;
4. the Parent value is overwritten even though both writers individually used the same store.

This is a product contract defect, not a cosmetic race: Parent controls and physical system keys are two legitimate writers to one desired-state authority.

### Correction

Commit:

```text
adec85c4fdf005ac473124dbf973405c37f3ddfa
System controls: make relative key updates transactional
```

`SystemControlSettingsStore` now exposes a small `mutate()` transaction. It acquires the existing shared lock, reads the latest desired state, applies one typed mutation, validates it and atomically persists it. Existing absolute `update()` delegates to the same seam.

`SystemControlService.handle_action()` now expresses volume/brightness/mute changes as mutations of the locked current value. Backend application occurs only after persistence and lock release. No new process, cache, privilege or device authority was introduced.

## Finding 2 — already-buffered Xlib media keys could stall behind `select()`

`LegacyXMediaKeyListener.wait_action()` previously called `select()` on the X connection file descriptor before consulting `XPending()`.

Xlib may already have read more than one KeyPress into its client-side queue. After the first event is returned to Greia, another event can remain buffered in Xlib while the kernel socket is no longer readable. Calling `select()` first can therefore delay the next already-buffered media key until the poll timeout or unrelated X traffic.

This is visible as unreliable rapid volume/brightness presses or auto-repeat on the low-resource appliance.

### Correction

Commit:

```text
e89e2e52d88f31b42c4faf6894bc25893435d362
Legacy X controls: drain buffered media keys before polling
```

The listener now drains recognized pending Xlib events first. It waits on the X socket only when the client queue is empty, then drains again after readiness. High-rate Activity input remains untouched; this is only the tiny Greia-owned media-key listener.

## Regression coverage

Commit:

```text
8610efc7dfb19ef9b82ace7b823a348f728a6f98
Test transactional and buffered system-control input
```

The focused behavioral contracts verify:

- a relative media-key action consumes the latest state supplied by the transaction and does not split its semantics across `read()` and `update()`;
- two X key events already buffered in Xlib are both consumed without an unnecessary `select()` call.

These tests are behavioral collaborator contracts. No source-string/name-presence audit was added.

## Acceptance-procedure correction

The previous `docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md` had become unsafe to execute literally because it hard-coded an obsolete source candidate, historical Activity count and old catalogue geometry.

Commit:

```text
b7a3d0ddc671898286c00dea0ca1aeb6f022723a
R7: make final evidence gate exact-candidate safe
```

The procedure now:

- freezes current `origin/main` dynamically;
- records actual test/Activity counts;
- forbids hard-coded launcher coordinates as authority evidence;
- requires semantic child-Shell launch and physical trusted Home for final hardware proof;
- adds a current system-control physical lane covering normal keys, rapid bursts, Parent-setting + relative-key composition and non-leakage into Activities;
- retains the remaining hostile 10/10, abrupt crash, 20/20 durability, Writing/Painting and performance/log gates.

## Current disposition

No post-correction execution result is claimed in this review. GitHub source commits are not test evidence.

Required next step:

1. freeze exact current `origin/main`;
2. run the focused system-control/R7 source gate and `make verify`;
3. run the real-Shell Simulator smoke;
4. if green, deploy that exact frozen SHA to the reference Acer;
5. execute the current system-control physical lane and remaining R7.2/R7.3 evidence gaps;
6. only then append factual results to the active architecture plan and update `HANDOVER.md`;
7. do not start R7.4 unless the final verdict is genuinely `ACCEPTED`.
