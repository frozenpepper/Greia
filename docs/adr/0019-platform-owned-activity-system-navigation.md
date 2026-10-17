# ADR 0019 — Platform-Owned Activity System Navigation

**Status:** ACCEPTED  
**Date:** 2026-08-15  
**Scope:** child-facing Activity presentation, input routing, lifecycle return, Python/Web/future runtimes, and R7 display/session architecture

## Context

Greia is intended for young children who should not need to relearn how to escape every Activity. Activity publishers also cannot be trusted to preserve a mandatory navigation control if the control is drawn or handled inside Activity code.

A Python helper that asks an Activity to draw a Home button can be ignored, moved or covered. A Web implementation that injects a DOM button can be restyled, obscured or intercepted by page code. Neither meets the requirement that the child always has a stable Greia-owned route back to the Shell.

The existing platform already owns Activity lifecycle and can request graceful stop followed by forced termination. R7 is separately defining the display/session ownership layer. These boundaries provide the correct place to make navigation a platform property rather than a runtime convention.

## Decision

### 1. Home is mandatory platform chrome

While any child-facing Activity is visible, Greia owns and presents a canonical Home control in one stable location.

Home is outside Activity rendering and input authority. Activity code cannot:

- hide it;
- move or resize it;
- restyle or replace it;
- cover it;
- intercept its input;
- disable it;
- veto the resulting return to Greia.

Home requests the platform's normal graceful Activity stop. If the Activity does not terminate within the existing bounded lifecycle deadline, Greia's forced-return path remains authoritative.

### 2. Greia Back is optional and platform-defined

Greia may show Back beside Home when the Shell has a distinct previous Greia navigation context.

Back means **return to the Greia launch origin after ending the Activity**. It is not:

- browser history;
- a Web runtime navigation primitive;
- an Activity-defined internal-back callback;
- permission for an Activity to manipulate Shell navigation.

If no distinct Greia origin exists, Back is absent while the complete protected chrome footprint remains reserved.

### 3. The protected region is renderer-neutral product geometry

`src/greia_platform/system_chrome.py` owns the current renderer-neutral geometry and action vocabulary.

The protected region is fixed by Greia. Activity content may draw behind it, but essential Activity controls should avoid it and Activity input cannot claim it.

The visual glyph can remain small while the pointer/touch hit target remains child-sized.

### 4. System chrome sits above runtime surfaces

The architecture is:

```text
Greia display/session authority
├── trusted system chrome + protected input
└── one Activity surface
    ├── Python/Pygame
    ├── Web/HTML
    └── future runtime
```

Activities do not implement the system controls. Runtime adapters therefore do not need separate Home implementations.

### 5. Display/session backends must support trusted chrome

A production display/session design is acceptable only if Greia can render system chrome above the Activity and receive protected-region input before the Activity.

Consequently, raw serial DRM/KMS ownership in which the Activity becomes the uncontested framebuffer/input owner cannot by itself satisfy production R7 closure.

A tiny persistent Greia-owned compositor/session broker is acceptable if measurements show it is the smallest reliable mechanism for:

- trusted Home/Back chrome;
- protected input routing;
- surface ownership and transitions;
- crash recovery;
- future Web surface integration;

This does not authorize a desktop compositor, arbitrary windows, a taskbar, desktop chrome or general-purpose window management.

### 6. Failure is fail-closed

Once the production system-chrome path is selected, inability to prepare/show/preserve mandatory Home is a platform failure. Greia must not silently launch an Activity without the invariant.

The current provisional Xorg/xinit path remains operational during R7 but is not certified against ADR 0019 until a trusted chrome host is implemented and executed.

### 7. First-party Activities receive no exemption

Writing, Painting and every other Greia-built Activity use the same system navigation boundary as third-party Activities.

### 8. Launch phase (amendment 2026-10-17)

An Activity's window is visible from the launch card on (ADR 0037 §6a), so Home is present from the launch, not only from READY. The Shell draws the chrome backend's Home *picture* at the protected location on its launch screen (so the launch card carries it), the trusted chrome is prepared **and shown** as soon as the session exists (`SystemChromeCoordinator.launch_started`), raised again when the Activity window maps and at READY. Home before READY (trusted chrome, a tap on the Shell's launch-screen Home, or the controller guide button) cancels the launch through lifecycle authority: an immediate bounded forced stop (`TrustedChromeActivitySupervisor.cancel_launch`), because the process has presented nothing of its own. After READY, Home remains the graceful stop. A launch whose chrome cannot be shown fails closed. The picture is never an input surface once the trusted chrome is shown.

## Initial source implementation

Renderer-neutral product geometry/actions:

```text
src/greia_platform/system_chrome.py
```

Backend-neutral trusted-chrome lifecycle seam:

```text
src/greia_launcher/system_chrome.py
```

Current shared Pygame renderer contains canonical vector glyph helpers:

```text
src/greia_platform/pygame_ui.py
src/greia_platform/activity_ui.py   # compatibility surface
```

Pure regression source:

```text
tests/test_system_chrome.py
tests/test_activity_ui.py
```

No production system-chrome backend is selected by this ADR. That implementation is an R7 display/session responsibility.

## Consequences

Positive:

- children learn one universal escape affordance;
- malicious/broken Activities cannot remove the route home;
- Python and Web share exactly the same product behavior;
- lifecycle authority remains platform-owned;
- R7 display architecture is evaluated against a concrete child-safety requirement rather than scanout alone.

Costs:

- the selected display/session backend must support a tiny trusted overlay and protected input region;
- truly exclusive direct framebuffer ownership by arbitrary Activity processes becomes unsuitable for production unless another trusted layer can preserve chrome;
- a small permanent corner region is unavailable for essential Activity controls.

## Non-goals

ADR 0019 does not:

- create a desktop/window manager;
- define Activity-internal Back behavior;
- make browser history child-facing;
- require Activity authors to draw system controls;
- allow Activities to configure system chrome;
- select the production R7 compositor/backend by itself.
