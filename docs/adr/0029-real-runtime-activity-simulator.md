# ADR 0029 — Real-Runtime Greia Activity Simulator

**Status:** ACCEPTED  
**Date:** 2026-08-19  
**Scope:** Activity developer tooling, synthetic-device testing, Greia Shell development composition, Python/Web runtime integration, responsive UI acceptance and developer evidence classification

## Context

Greia needs a practical way for Activity authors to test work without installing a full Greia image, booting a VM, or owning every reference device. The need is especially strong for viewport/resolution testing, child visual settings, semantic hardware-capability compatibility, launcher/package/lifecycle integration and rapid Activity loading.

A VM reproduces many Linux details irrelevant to Activity iteration. A mock Greia-themed preview has the opposite failure: it can drift from the actual launcher, manifest parser, permissions, profile state, runtime adapters and responsive layout. ADR 0027 already requires preview tooling to use the same transform/layout implementation as runtime rather than a fake preview algorithm. The same principle applies to the complete Activity environment.

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
REAL GREIA PLATFORM
  ├── child Shell / launcher
  ├── ActivityRegistry + package trust
  ├── PermissionBroker
  ├── ProfileStore / customization
  ├── RuntimeManager / ActivitySupervisor
  ├── Storage / history / events
  └── responsive/canvas/system-safe geometry
          ↓
  Python adapter / future Web adapter
```

### 2. Simulator-specific code lives below existing seams

The simulator may implement genuine variation points: synthetic `GreiaHAL`, simulator runtime launch wrapping required to map current renderer fullscreen requests onto a desktop test viewport, isolated filesystem roots supplied through existing configuration seams, and a developer desktop control plane.

It must not fork or duplicate manifest parsing, package trust, launcher catalogue/categories/icons, PermissionBroker decisions, profile storage, Activity storage, history/session/event/progression semantics, lifecycle/watchdog, responsive/canvas transforms, input-profile vocabulary or future Web Activity APIs.

When a missing simulator feature reveals that production Greia lacks a clean seam, improve the shared Greia abstraction instead of embedding a second policy implementation in the simulator.

### 3. The child-facing simulator window is the real Greia Shell

The simulator control plane may use an ordinary developer desktop UI. That UI is not the Greia child experience. The simulated device runs the actual profile-aware Greia child-shell/launcher composition, so profile selection, categories, package icons, My Greia settings, motion and launch supervision remain production source.

### 4. Simulator state is isolated

Simulator profiles, saves, packages, developer Activities and media live outside the source checkout in an isolated workspace. The source checkout supplies real built-in Activities/assets/runtime policy through development `GREIA_OS_ROOT`.

### 5. Device simulation uses typed Greia HAL facts

Resolution and hardware availability are represented through the existing `GreiaHAL` / `DeviceCapabilityService` path. A missing capability therefore reaches the real compatibility/permission path rather than merely changing a simulator checkbox.

Initial vocabulary is the implemented Greia vocabulary: `display`, `keyboard`, `pointer`, `touch`, `controller`, `audio.basic`, `network`, `removable_media`, `power.controlled_shutdown`.

Named presets are convenience bundles only; hardware model names never become layout or permission authority.

### 6. Resolution simulation exercises real layout/canvas contracts

The selected viewport is the synthetic physical Activity surface. Real responsive layout, Activity viewport, reference/world transforms, system-safe geometry and semantic interface-size composition consume it. The simulator must not contain a parallel responsive algorithm or per-Activity/per-resolution coordinates.

Initial presets include 1024×600, 1280×720, 1280×800, 1366×768 and 1920×1080 plus bounded custom dimensions.

### 7. Current Python display interception is a simulator compatibility adapter

While R7 is open, current Pygame Activities still commonly call `pygame.display.set_mode(... FULLSCREEN)` directly. For the simulator only, the Python runtime adapter may start a validated Activity through a small bootstrap that maps that renderer call to the synthetic viewport and removes fullscreen ownership.

This is below the runtime-adapter seam, changes no production runtime behavior and must remain narrow. It must not monkeypatch Greia storage, permissions, lifecycle, profile APIs, layout, input semantics or package validation. As the shared display/session abstraction matures, the simulator should consume it and retire compatibility interception that is no longer needed.

### 8. Load Activity Folder uses real developer trust and registry authority

The simulator stages a mutable source folder into an isolated developer root, validates it through the real `ActivityRegistry` together with built-in identity authority, and uses `DEVELOPER_UNSIGNED` trust. The staging helper may omit VCS/bytecode cache residue but may not weaken semantic package/runtime validation or upgrade trust. Normal launcher rescan/discovery remains authoritative.

### 9. Install Activity Package exercises the canonical transaction

Package testing calls `ActivityPackageService`; there is no simulator-only unzip/install path. This keeps fast source loading distinct from real archive validation/immutable-store/receipt/activation testing. Simulator install PASS does not close R10.

### 10. Child settings use real profile/customization state

The control plane may preselect `compact` / `normal` / `large` using the real `UiPreferencesStore`. Other visual choices should preferably be exercised through the actual My Greia Activity. Future language/settings controls may appear only when they can write through the same authoritative platform store/service; shadow simulator settings are forbidden.

### 11. Web/HTML support must come from canonical R9 Web runtime

Web/HTML is part of the intended simulator contract, but the simulator must not invent a host-browser or simulator-only webview path. Current source composition has Python only. Until R9 provides the canonical `WebRuntimeAdapter`/SDK bridge, Web runtime unavailability remains real. Once implemented, the simulator adds the same adapter to `RuntimeManager` and supplies only synthetic device/session backends.

### 12. Mac-first, core-platform-neutral

The initial desktop control plane may target macOS first, but core simulator semantics use portable Python/platform contracts. Windows/Linux should primarily be packaging/control-plane ports, not rewrites.

### 13. Evidence classification is strict

Simulator evidence may prove real registry validation, synthetic capability policy, responsive behavior at selected viewports, profile visual context, desktop-composition lifecycle/storage/history/events and current local package-transaction behavior.

It cannot prove Bubblewrap/kernel isolation, production filesystem containment, Xorg/DRM/KMS/compositor behavior, physical controller/input ownership or latency, trusted system-chrome non-coverability, real audio/network/media hardware, boot/installer/initramfs behavior, Acer/Pi performance, or R7/R8/R9/R10/R14 closure.

### 14. Alignment regressions are mandatory

Tests must lock the synthetic HAL vocabulary, runtime-adapter use, simulator-only display wrapping, state isolation and environment wiring. Documentation and Activity/agent manuals must remain synchronized with source behavior.

## Initial implementation owners

```text
src/greia_simulator/device.py
src/greia_simulator/workspace.py
src/greia_simulator/runtime.py
src/greia_simulator/python_activity.py
src/greia_simulator/child_shell.py
src/greia_simulator/app.py
tools/greia_simulator.py
tests/test_greia_simulator.py
```

The real services intentionally remain owned by existing `greia_platform` / `greia_launcher` modules.

## Consequences

The simulator makes multi-resolution/profile/capability Activity development cheap while becoming stronger automatically as shared Greia services improve. The cost is that desktop SDL behavior is still not production backend/hardware evidence and the current Python fullscreen adapter remains temporary compatibility debt.

## Non-goals

This ADR does not close/select R7, implement R9 Web, make a desktop toolkit part of Greia OS, replace VM/image/physical testing, certify production sandboxing, create a VM/emulator, authorize parallel platform services, or permit per-resolution Activity authoring.
