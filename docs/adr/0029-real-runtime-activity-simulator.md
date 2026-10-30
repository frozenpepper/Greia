# ADR 0029 — Real-Runtime Greia Activity Simulator

**Status:** ACCEPTED  
**Date:** 2026-08-19  
**Hardened after adversarial review:** 2026-08-19  
**Scope:** Activity developer tooling, synthetic-device testing, Greia Shell development composition, Python/Web runtime integration, responsive UI acceptance and developer evidence classification

## Context

Greia needs a practical way for Activity authors to test work without installing a full Greia image, booting a VM, or owning every reference device. The need is especially strong for viewport/resolution testing, child visual settings, semantic hardware-capability compatibility, launcher/package/lifecycle integration and rapid Activity loading.

A VM reproduces many Linux details irrelevant to Activity iteration. A mock Greia-themed preview has the opposite failure: it can drift from the actual launcher, manifest parser, permissions, profile state, runtime adapters and responsive layout. ADR 0027 already requires preview tooling to use the same transform/layout implementation as runtime rather than a fake preview algorithm. The same principle applies to the complete Activity environment.

The first implementation was deliberately reviewed adversarially in `2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md` (archived; see git history). That review exposed composition duplication, a shadowable Python bootstrap, unsafe Shell restart semantics, unsafe source-folder staging, Activity-visible simulator identity and weaker-than-required evidence/portability boundaries. The hardened decision below makes the non-drift goal mechanical rather than aspirational.

## Decision

### 1. Greia provides a real-runtime Activity Simulator

The **Greia Activity Simulator** is developer tooling that runs the real Greia child platform against a synthetic device. It is not a virtual machine, a second launcher, a fake validator, a simulator-specific storage/progression/permission system, or hardware/production-sandbox evidence.

> **Everything above an existing platform/runtime/hardware seam stays real. Only facts that genuinely come from the missing physical Greia machine may be synthetic.**

Conceptually:

```text
Simulator control plane
  ├── synthetic viewport
  ├── synthetic HAL capability facts
  └── isolated workspace roots
          ↓
REAL GREIA PLATFORM COMPOSITION
  ├── child Shell / launcher
  ├── ActivityRegistry + package trust
  ├── PermissionBroker
  ├── ProfileStore / customization
  ├── RuntimeManager / ActivitySupervisor
  ├── Storage / history / events
  └── responsive/canvas/system-safe geometry
          ↓
  injected Python adapter / future canonical Web adapter
```

### 2. Production composition is the only service graph

The simulator must not reconstruct launcher services. `build_launcher_runtime_services()` is the single owner of device-capability, permission, runtime-manager, storage and history composition. `GreiaChildShell` owns the single runtime-service/supervisor rebuild and publication sequence.

Synthetic compositions may inject only typed variation points exposed by those owners, currently:

```text
GreiaHAL
runtime adapter set/factory
child-Shell display/window request hooks
display-session coordinator/backend where genuinely applicable
```

The simulator must not own another `PermissionBroker`, storage/history service graph or supervisor specialization. A subclass/inheritance check alone is not sufficient non-drift evidence; tests must prove that simulator composition consumes the canonical owner.

When a simulator feature reveals a missing production seam, improve the shared Greia abstraction rather than copying the production method into `greia_simulator`.

### 3. The child-facing simulator window is the real Greia Shell

The desktop control plane may use an ordinary developer UI. It is not the child experience. The simulated device runs the actual profile-aware `GreiaChildShell`, including profile selection, launcher categories, package icons, My Greia state, motion, launch supervision and normal display-size cache invalidation.

The simulator may select an exact initial/resized desktop surface through the shared Shell display-policy hooks. It must not replace `_draw()`, manually clear private launcher caches, or maintain a second resize algorithm.

### 4. Simulator state is isolated, checkout-bound and single-writer

Simulator profiles, saves, packages, developer Activities and media live outside the source checkout. The source checkout supplies real built-in Activities/assets/runtime policy through development `GREIA_OS_ROOT`.

Each workspace records a schema version and the checkout path that owns it. Reusing state with another checkout is rejected unless the developer explicitly requests a rebind. A workspace has one active writer lease so two simulator control planes cannot race the same profile/session/developer-Activity state.

### 5. Device simulation uses canonical typed Greia HAL facts

Resolution and hardware/service availability are represented through `GreiaHAL` / `DeviceCapabilityService`. A missing capability therefore reaches the real compatibility/permission path rather than becoming an Activity-side test.

The canonical capability vocabulary comes from `RuntimeCatalogue.allowed_capabilities`. `greia_simulator.device` owns only the mapping between currently representable semantic capabilities and synthetic HAL fields. If Greia adds a canonical capability that the simulator HAL cannot represent, simulator startup/tests must fail until that mapping is deliberately added.

Viewport presets are **geometry conveniences only**. Their labels must not imply Acer hardware, tablet/touch hardware, CPU/RAM/GPU/storage limits or architecture emulation. Initial geometry presets are 1024×600, 1280×720, 1280×800, 1366×768 and 1920×1080 plus bounded custom dimensions.

### 6. Resolution simulation exercises real layout/canvas contracts

The selected viewport is the synthetic physical child/Activity surface. Real responsive layout, Activity viewport, reference/world transforms, system-safe geometry and semantic interface-size composition consume it. The simulator must not contain per-Activity/per-resolution coordinate tables or a parallel responsive algorithm.

Current Pygame Shell sizing goes through the shared launcher window-policy seam. Current Pygame Activity sizing still needs the temporary runtime compatibility adapter described below until the R7 display/surface architecture removes direct Activity display ownership.

### 7. Current Python display interception is narrow, trusted and temporary

While R7 is open, current Pygame Activities still commonly call `pygame.display.set_mode(... FULLSCREEN)` directly. The simulator therefore wraps the **canonical Python runtime command** with one Greia-owned bootstrap that maps only `pygame.display.set_mode()` to the selected synthetic viewport and removes fullscreen ownership.

The bootstrap is executed by absolute trusted file path. It is not resolved through `python -m`, Activity cwd or an Activity-controlled package name. Before Activity code runs it restores only the trusted Greia `src/` root needed by the curated runtime and keeps that path ahead of Activity content.

The bootstrap does not patch Greia storage, permissions, lifecycle, profiles, input semantics, layout or package validation. It must not grow into a simulator-specific SDL framework. The long-term owner remains the shared R7 Activity display/surface abstraction, at which point this compatibility layer should disappear.

### 8. Simulator identity is not an Activity API

Ordinary Activity launch context contains the same Greia-facing concepts as normal development/production launch context. `GREIA_SIMULATOR`, a simulator viewport flag, simulator preset names or other simulator-only layout switches are forbidden Activity APIs.

Synthetic viewport is passed as trusted runtime-adapter/bootstrap plumbing, not an Activity environment variable. The bootstrap defensively removes stale `GREIA_SIMULATOR*` variables before executing Activity code. First-party source lint remains useful, but runtime non-exposure is the real boundary.

### 9. Load Activity Folder is bounded and transactional

Fast developer loading may omit ordinary VCS/cache residue, but the managed copy must remain semantically equivalent to the accepted source.

Before copying, the simulator performs a finite lstat-based safety snapshot bounded by a fixed 512 MiB safety ceiling (the canonical `RuntimeCatalogue.maximum_activity_bytes` is a 64 MiB warn-only guideline since the 2026-10-21 owner decision). Symlinks, special files, executable package files and canonical forbidden content are rejected rather than dereferenced or transformed. Source and simulator-managed state may not contain one another.

The bounded staged copy is then validated through the real `ActivityRegistry` together with built-in identity authority under `DEVELOPER_UNSIGNED` trust. Publication into `developer-activities/<activity-id>` is transactional: an existing last-known-good copy is retained until the replacement has passed final normal registry discovery, and is restored if final publication/validation fails.

Normal launcher rescan remains authoritative.

### 10. Install Activity Package exercises only the canonical transaction

Package testing calls `ActivityPackageService`; there is no simulator extractor or install fallback. Package-service import is lazy so platforms that cannot currently provide the canonical package lock backend can still use non-package simulator functionality. On such hosts package-install testing is reported unavailable rather than reimplemented.

A simulator install PASS does not close R10.

### 11. Stop / Restart must retire the real Activity first

The control plane may not kill the Shell and assume an Activity dies with it. Python Activities run in their own process session by design.

A simulator Shell Stop/Restart request therefore unwinds the Shell and, if an Activity is active, uses the real `ActivitySupervisor` path: request graceful STOP, poll to a bounded deadline, then escalate through `force_stop(... SYSTEM_SHUTDOWN)` if necessary. Only after the Shell has had a bounded opportunity to complete lifecycle/broker/control/history cleanup may the control plane hard-kill the Shell as a last-resort host-process fallback.

### 12. Child settings use real named profile state

The control plane may write `compact` / `normal` / `large` only through the real `UiPreferencesStore` for an explicitly selected simulator child profile. It must not silently mutate profile index zero or maintain a shadow settings store.

Colors, wallpaper and avatar should normally be exercised through the actual My Greia Activity. Future language/settings controls may appear only when they write through the same authoritative platform store/service.

### 13. Desktop simulator code is trusted developer code, not an untrusted-code sandbox

The source-mode desktop simulator intentionally does not claim production Bubblewrap/kernel/filesystem containment. A valid Activity process runs with the developer host user's underlying OS access unless a separate host-sandbox layer is deliberately added.

The control plane and documentation must therefore say prominently:

```text
load/run only Activity code and packages you trust
semantic capability switches test Greia policy/compatibility
semantic capability absence does not physically disable host input/filesystem access
```

A future host sandbox may improve developer safety but cannot be relabeled as production Bubblewrap evidence.

### 14. Web/HTML support must come from canonical R9 Web runtime

Web/HTML remains part of the intended simulator contract, but the simulator must not invent a host-browser/private-webview path. A syntactically valid `runtime.type = "web"` package may be registry-valid before a Web adapter exists; current canonical unavailability is a RuntimeManager/launch concern, not something the simulator should secretly reject earlier.

When R9 provides the canonical Web adapter/SDK bridge, the simulator injects that same adapter into the existing composition and supplies only synthetic device/session backends.

### 15. Mac-first with portable core, not premature multiplatform claims

macOS is the first supported desktop target. Workspace/device/control semantics should remain portable Python. Canonical package installation may remain host-limited until its platform lock implementation is portable; lazy loading prevents that limitation from disabling unrelated simulator use.

Windows/Linux maturity must be earned through execution/packaging tests rather than implied by architecture alone.

### 16. Evidence classification is strict

Simulator evidence may prove real registry/trust behavior, synthetic capability policy, responsive behavior at selected viewports, real profile visual context, desktop-composition lifecycle/storage/history/events and current local package-transaction behavior.

It cannot prove Bubblewrap/kernel isolation, production filesystem containment, physical input suppression, Xorg/DRM/KMS/compositor behavior, trusted system-chrome non-coverability, real audio/network/media hardware, boot/installer/initramfs behavior, Acer/Pi performance, or R7/R8/R9/R10/R14 closure.

### 17. Alignment regressions are mandatory

Focused tests must cover more than inheritance. At minimum they lock:

- canonical composition with injected HAL/runtime adapter;
- no simulator-owned service graph or Shell `_rebuild_runtime_services()`/`_draw()` replacement;
- absolute trusted bootstrap and module-shadow resistance;
- no Activity-visible simulator identity;
- canonical capability vocabulary coverage;
- workspace checkout binding/single writer;
- named-profile UI preference persistence;
- positive developer loading plus identity collision, symlink, oversize, overlap and rollback negatives;
- canonical package-service delegation;
- valid-but-unavailable runtime behavior;
- bounded supervisor shutdown;
- a real local Python Activity lifecycle path covering READY, storage, events/history and STOP when simulator dependencies are installed.

Manual viewport/visual acceptance remains separate from source tests and must not begin by weakening these boundaries.

## Implementation owners

```text
Shared owners strengthened for simulator variation:
  src/greia_launcher/composition.py
  src/greia_launcher/child_shell.py
  src/greia_launcher/presentation.py

Simulator variation/control owners:
  src/greia_simulator/device.py
  src/greia_simulator/workspace.py
  src/greia_simulator/runtime.py
  src/greia_simulator/python_activity.py
  src/greia_simulator/child_shell.py
  src/greia_simulator/app.py
  tools/greia_simulator.py
  tests/test_greia_simulator.py
```

The real services intentionally remain owned by `greia_platform` / `greia_launcher`.

## Consequences

The simulator becomes useful specifically because it is thin: future shared Greia service changes flow through the same composition automatically. Hardening adds some deliberate friction—single-writer state, checkout identity, trusted-code warnings and strict source staging—but removes silent divergence and unsafe developer behavior.

Desktop SDL behavior remains developer evidence, and direct Pygame Activity display interception remains temporary R7 compatibility debt.

## Non-goals

This ADR does not close/select R7, implement R9 Web, make a desktop toolkit part of Greia OS, replace VM/image/physical testing, certify production sandboxing, create a VM/emulator, authorize parallel platform services, emulate Acer/Pi resource performance, or permit per-resolution Activity authoring.
