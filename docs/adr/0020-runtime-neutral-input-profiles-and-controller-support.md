# ADR 0020 — Runtime-Neutral Input Profiles and Controller Support

**Status:** ACCEPTED  
**Date:** 2026-08-15  
**Scope:** Greia input HAL, Shell, Activity manifests, Python/Pygame input adapters, future Web input bridge, and R7 trusted input/session architecture

## Context

Greia requires joystick/controller support from Phase 0. Adding controller support independently inside each Activity would create inconsistent button layouts, repeated dead-zone/cursor logic, controller-brand assumptions, and a difficult future Web migration.

At the same time, forcing every Activity into one universal control layout would be wrong: painting is spatial/pointer-oriented, writing requires real text input, a maze wants directional movement, and richer games may need analog controls.

ADR 0019 also establishes a higher-trust Greia-owned Home/Back layer that Activity code cannot intercept. Physical controller ownership therefore cannot be designed separately from system input authority.

## Decision

### 1. Controller is a first-class HAL capability

The input HAL reports controller availability independently of keyboard, pointer and touch availability.

`controller` means a usable controller source is available on the device. It is hardware/service capability, not an Activity interaction model and not a permission to access raw host input devices.

### 2. Activities declare interaction intent

The Activity manifest supports:

```toml
[input]
profile = "pointer"
```

The accepted vocabulary is deliberately small:

```text
navigation
pointer
directional
game
text
hybrid
```

The profile is platform-validated before launch and is exposed to the runtime as descriptive context.

Existing API 0.1 packages without the table retain temporary `hybrid` compatibility. New and materially updated Activities should declare the profile explicitly.

### 3. Greia owns the learned standard mappings

Renderer-neutral mapping semantics live above Pygame, SDL, Web Gamepad APIs and Linux device paths.

The baseline includes:

- navigation: arrows / D-pad or left stick; Space/Enter / south face activate;
- directional/simple game: arrows + Space; D-pad/left stick + south face;
- pointer: normal mouse/touch plus controller left-stick virtual pointer and south-face primary action;
- game: the simple baseline plus additional semantic actions when genuinely needed;
- text: preserve real keyboard text semantics rather than stealing Space/Enter/arrows for game mapping.

Activities may extend appropriate semantic behavior, but they must not build ordinary controls around consumer-brand labels or raw button numbers.

### 4. Controller vocabulary is positional and semantic

The platform normalizes controller controls as roles/positions such as `FACE_SOUTH`, `FACE_EAST`, D-pad, sticks, shoulders and triggers.

A backend may consume an API whose constants use Xbox-style A/B/X/Y names, but those labels terminate at the backend boundary.

### 5. Pointer emulation is semantic, not OS-global

For pointer-profile Activities, Greia may drive a virtual pointer from a controller stick.

This pointer is part of the Greia input/session semantics. Controller support must not be implemented by globally creating a fake Linux mouse simply to satisfy an Activity.

Dead zones, response curves, pointer speed and bounds are centralized platform policy.

### 6. Devices coexist

Keyboard, pointer, touch and controller are not exclusive modes. Greia accepts whichever appropriate input source the child uses without requiring a manual input-mode switch.

Disconnecting a controller must not disable keyboard or pointer operation.

### 7. System input remains above Activity input

The controller Guide/system control, where reliably available, is reserved to the Greia platform and is never mapped into ordinary Activity semantic actions.

Its ultimate Home behavior belongs to the ADR 0019 trusted system-navigation layer. This ADR deliberately does not freeze an untested fallback controller chord; such a chord requires accidental-activation evidence first.

### 8. Production physical-device ownership belongs to Greia

Ordinary Activities do not receive raw `/dev/input`, joystick device, seat or equivalent host authority merely because controllers are supported.

The production display/input/session backend owns physical input and first consumes protected Greia system actions. Activity-facing input then crosses a runtime-neutral broker/bridge appropriate to the selected interaction profile.

Current trusted Shell/backend prototypes may open bounded SDL/Pygame controller objects while R7 is open. That implementation detail does not become an Activity API or authorize direct device binding into the sandbox.

### 9. Python and Web share semantics

Python/Pygame and future Web/HTML Activities use the same interaction profiles and semantic actions.

The Web runtime must not require each page to implement controller-brand Gamepad API mappings for standard Greia behavior. System Home/Back stays outside the DOM and browser history remains unrelated to Greia Back.

### 10. Keep the implementation small

This decision does not create a generic game engine or a universal input scripting framework.

The source should consist of:

- typed input/HAL capability facts;
- a small runtime-neutral interaction/mapping core;
- renderer/runtime adapters;
- bounded device ownership at trusted platform seams;
- focused tests.

Additional abstractions require real consumers.

## Initial implementation

Renderer-neutral input semantics:

```text
src/greia_platform/input_core.py
```

Current Pygame translation/trusted-controller helper:

```text
src/greia_platform/pygame_input.py
```

Capability ownership:

```text
src/greia_platform/hal.py
src/greia_platform/device_capabilities.py
src/greia_platform/hal_legacy_x.py
runtime/child-runtime.toml
```

Manifest/SDK launch context:

```text
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_launcher/supervisor.py
```

Exact current execution/evidence status belongs in `HANDOVER.md`.

## R7 consequences

R7 cannot close merely by demonstrating display scanout and keyboard/pointer operation.

The selected production session/input architecture must also demonstrate:

- controller discovery/ownership without granting raw Activity input authority;
- trusted system-input interception before Activity delivery;
- standard keyboard/controller navigation;
- directional/game mapping;
- pointer-profile virtual-pointer behavior;
- disconnect/reconnect recovery;
- bounded resource ownership;
- acceptable input latency/dead-zone behavior on reference hardware;
- a transport/bridge model reusable by Web.

This strengthens, rather than replaces, the ADR 0019 system-chrome requirement.

## Consequences

Positive:

- children learn stable controls across Activities;
- controller support is available without per-Activity hardware code;
- pointer Activities can remain pointer-oriented;
- simple games receive a predictable arrows/Space and controller baseline;
- Python and Web do not fork the input product model;
- dead-zone and controller-cursor tuning can improve centrally;
- system input remains enforceable above Activity code.

Costs:

- R7 must implement a real trusted physical-input path rather than exposing raw controller devices to child processes;
- current Python Activities need incremental adoption of semantic input helpers/bridges;
- physical controller evidence becomes part of Phase-0 certification.

## Rejected alternatives

### Per-Activity joystick handling

Rejected because it duplicates mappings/dead zones/device lifecycle and makes controls inconsistent.

### Controller-as-global-Linux-mouse

Rejected as the platform model because it leaks implementation details, creates surprising behavior outside spatial Activities and complicates protected system input.

### Brand-specific Activity mappings

Rejected because A/B/X/Y labeling and layout conventions differ across controller families.

### Controller-only input mode

Rejected because children should be able to switch naturally between available devices.

### Raw `/dev/input` access for ordinary Activities

Rejected because it bypasses Greia's protected system-input and runtime-neutral authority boundaries.
