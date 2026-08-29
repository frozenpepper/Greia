# R7 Activity Backend Independence and Display/Session Review

**Status:** accepted implementation review / subordinate R7 execution specification  
**Date:** 2026-08-29  
**Authority:** subordinate to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`, ADR 0019 and ADR 0020. This is **not** a competing implementation plan.

## 1. Decision

Greia Activities must be display-backend independent immediately.

An Activity may use runtime-neutral drawing and event APIs such as Pygame/SDL. It must not know, select, probe, configure or depend on X11, Wayland, DRM/KMS, evdev/libinput, host display sockets, physical input devices or backend-specific environment variables.

Greia does **not** need a new drawing API. SDL/Pygame remains the renderer abstraction. Greia owns the higher-level display/session/input authority around the Activity surface.

The existing `src/greia_launcher/display_session.py` is the seed of the correct boundary. `DisplaySessionCoordinator` owns the shell <-> Activity surface state machine and `DisplaySessionBackend` is the polymorphic implementation seam. `LegacyXDisplaySessionBackend` is the current compatibility implementation. R7 should complete and harden this seam rather than invent a parallel display HAL.

Backend classes are protocol/capability implementations, not hardware classes:

```text
DisplaySessionCoordinator
        |
        +-- LegacyXDisplaySessionBackend
        +-- WaylandDisplaySessionBackend       # R7 candidate implementation
        +-- DirectKmsDisplaySessionBackend      # only if evidence gives it a real use
```

Build/hardware profiles may select an implementation. Activities and the common launcher/runtime contracts must remain identical.

## 2. Boundary: what belongs where

### Activity / runtime-neutral layer

Allowed:

- `pygame.Surface`, draw/blit/font/mixer primitives;
- `pygame.display.set_mode`, resize and flip/update as an SDL client operation;
- ordinary local keyboard/mouse/touch events appropriate to the Activity;
- Greia semantic input APIs and interaction profiles;
- Greia-provided viewport/safe-region/session context;
- Greia lifecycle, storage, event, locale and permission APIs.

Forbidden as an Activity dependency:

- Xlib/XCB/X11 APIs;
- `DISPLAY`, `XAUTHORITY`, `xrandr`, `xinput`, `xdotool`;
- Wayland protocol/socket APIs or `WAYLAND_DISPLAY`;
- `SDL_VIDEODRIVER` selection;
- DRM/KMS/GBM APIs or `/dev/dri/*`;
- evdev/libinput or `/dev/input/*`;
- direct physical controller/joystick ownership for ordinary Activities;
- drawing, hit-testing or implementing the real Greia Home/Back controls.

A test harness may set SDL's `dummy` driver in explicitly scoped test infrastructure; that is test composition, not an Activity runtime dependency.

### Trusted Greia display/session layer

Owns:

- backend selection and backend-private environment injection;
- surface/session preparation, presentation, focus and shell recovery;
- trusted Home/Back presentation above the Activity surface;
- protected-region input interception before Activity delivery;
- controller discovery/normalization and reserved Guide/system input;
- crash/hang recovery and surface reclamation;
- backend-specific focus/cursor/session quirks;
- display/input settings adapters.

### HAL versus display-session boundary

Keep the existing distinction:

- `greia_platform.hal` / `hal_legacy_x.py`: hardware capability facts and bounded settings/probe operations;
- `greia_launcher.display_session`: active graphical surface/session ownership and backend transport.

Do not turn `GreiaHAL` into a giant session/window/compositor object.

## 3. Activity audit: recurring patterns

This review inspected representative Activities spanning the two mandatory creation tools, older/simple games, newer modular games and microphone work:

- `activities/writing/main.py`
- `activities/painting/main.py`
- `activities/labirinto_magico/maze_app.py`
- `activities/volo_draghetto/dragon_app.py`
- `activities/shape_garden/main.py`
- `activities/storie_della_mia_voce/voice_app.py`

The sample is sufficient to expose the shared architectural patterns; implementation must still run a repository-wide static scan before migration closure.

### Pattern A — fullscreen Pygame surface creation

Writing and Painting create `(0, 0)` fullscreen SDL/Pygame displays. Newer Activities commonly accept an injected surface and otherwise create a 1024x600/resizable Pygame surface.

**Disposition:** keep. This is SDL-level, backend-neutral behavior. Prefer a small shared Activity runtime/surface bootstrap over time to normalize readiness/resizing/session context, but do not block R7 on replacing every `pygame.display.set_mode()` call.

### Pattern B — Activity-owned trusted chrome

Writing, Painting, Labyrinth, Dragon Flight, Shape Garden and Voice Stories import shared helpers such as `draw_system_chrome_overlay()` and/or `is_home_clicked()`.

This is the principal trust-boundary drift.

The helpers make first-party Activities *cooperate* with ADR 0019, but do not enforce it. An Activity process can omit, cover, imitate or ignore the control. The accepted ADR explicitly says the real Home/Back must sit outside Activity rendering/input authority.

**Disposition:** remove Activity ownership. The production backend/trusted chrome host renders and hit-tests Home/Back. Activities receive only reserved/safe geometry and lifecycle stop state; they never receive the system-navigation action as an event they can veto.

### Pattern C — shared reference canvas derives safe area from chrome itself

`greia_platform.pygame_canvas.activity_viewport_for_surface()` directly instantiates `ActivitySystemChromeLayout`; `PygameReferenceCanvas.present()` defaults to drawing system chrome onto the Activity target.

This centralizes the drift, which is good for migration.

**Disposition:** preserve `PygameReferenceCanvas`, `PygameCanvasMapper`, logical coordinate transforms and safe-layout concepts. Change their input from "construct the platform chrome here" to an `ActivityViewport`/reserved-region context supplied by the trusted session/runtime. Remove trusted chrome rendering from `present()`; an optional Activity-local cursor remains a separate concern.

### Pattern D — direct local pointer/keyboard Pygame events

Activities commonly consume `pygame.event.get()` for movement, text, clicking, drawing and resize.

**Disposition:** do not blindly IPC every mouse motion or keystroke. High-frequency local pointer/text input is valuable on Acer-class hardware. R7 must instead ensure protected system input is consumed at the trusted layer before it reaches the Activity, and controller/physical-device ownership remains brokered. The exact backend mechanism may differ while the Activity-visible behavior remains identical.

### Pattern E — ESC as a convenient Activity exit

Several first-party Activities treat Escape as an exit/cancel.

**Disposition:** allowed as an Activity-local convenience, but never as Greia's only or authoritative escape route. Mandatory Home remains platform-owned and works even if the Activity hangs or ignores events.

### Pattern F — modular newer Activity architecture

Labyrinth, Dragon Flight, Shape Garden and Voice Stories already split lifecycle/models/rendering/services more cleanly than the older mandatory Writing/Painting implementations.

**Disposition:** preserve these module boundaries. Backend migration should be mostly a shared-platform import/context change, not a rewrite of gameplay/renderers. Writing/Painting can receive focused migration first; broader code-quality refactors remain separate work unless required for the trust boundary.

### Pattern G — microphone/platform service consumption

Voice Stories uses Greia Activity APIs to obtain the platform-owned capture route while its graphical lifecycle remains ordinary Pygame.

**Disposition:** this is the model to emulate: Activities request semantic capability/service access; backend/device details terminate at the Greia platform boundary.

## 4. Target runtime composition

```text
Activity code
  |-- Pygame/SDL rendering
  |-- Greia Activity API
  |-- semantic input / viewport context
  v
Activity runtime adapter + supervisor
  |-- injects backend-private client transport
  |-- injects only approved capabilities
  |-- owns lifecycle process boundary
  v
DisplaySessionCoordinator + trusted input/chrome coordinators
  |
  +-- selected DisplaySessionBackend
  |     +-- Xorg compatibility
  |     +-- Wayland candidate
  |
  +-- trusted Home/Back host
  +-- controller/input broker
  v
Linux graphics/input stack
```

`DisplayTransport` is launcher-internal. X11/Wayland environment values may be injected into the child process because SDL needs them, but they are plumbing, not Activity API. Activity source must not read or branch on them.

## 5. Implementation sequence

### R7.1 — freeze the Activity/backend invariant

1. Add the invariant to OS and Activity contributor guidance.
2. Add a repository validator for backend-specific Activity dependencies.
3. Scan every first-party Activity and classify findings before changing behavior.
4. Explicitly allow ordinary Pygame/SDL APIs; do not create false positives for `pygame.display` or normal event handling.

**Exit:** new Activity code cannot intentionally deepen X11/Wayland/KMS/raw-input coupling.

### R7.2 — harden the existing display-session seam

1. Keep `DisplaySessionCoordinator` as the state-machine owner.
2. Review `DisplaySessionBackend` against the real needs: prepare, present, restore, trusted overlay coordination, focus/session recovery and backend-private launch transport.
3. Move any generic-launcher X11 behavior (including focus workarounds) behind `LegacyXDisplaySessionBackend` or another narrowly X-specific collaborator.
4. Compose the backend in `greia_launcher.composition`; do not scatter backend conditionals.
5. Keep `DisplayTransport` private to trusted launcher/supervisor code.

**Exit:** replacing the backend implementation requires no Activity source/API changes.

### R7.3 — move trusted chrome out of Activities

1. Implement a real `SystemChromeBackend` for the current Xorg compatibility session first, using the already-existing `SystemChromeCoordinator` seam.
2. Integrate its lifecycle with the display-session lease and Activity supervisor.
3. Ensure Home/Back input is consumed before Activity input and invokes Greia stop/forced-return authority.
4. Change viewport/canvas helpers to receive trusted reserved-region geometry rather than instantiate chrome authority.
5. Remove Activity-side `draw_system_chrome_overlay()` and `is_home_clicked()` usage.
6. Fail closed: do not present an Activity if mandatory Home cannot be preserved.

**Exit:** a deliberately non-cooperative test Activity cannot hide, cover, intercept or disable real Home.

### R7.4 — input ownership completion

1. Preserve `input_core.py` as runtime-neutral semantic vocabulary.
2. Keep physical controller ownership in the trusted platform; ordinary Activities do not open raw joystick/device nodes.
3. Consume Guide/system input before Activity delivery.
4. Provide semantic controller actions and virtual pointer according to the manifest interaction profile.
5. Preserve direct local Pygame text/pointer paths where safe and performance-sensitive rather than forcing high-rate IPC without evidence.

**Exit:** keyboard/pointer/touch/controller coexist, controller reconnect works, and protected input remains outside Activity authority.

### R7.5 — migrate first-party Activities by pattern

**Wave 1 — canonical/mandatory:** Writing, Painting.  
Remove cooperative Home/chrome ownership and prove save/recovery behavior survives.

**Wave 2 — shared reference-canvas exemplars:** Labyrinth, Dragon Flight, Shape Garden.  
Use these to prove the central canvas/viewport migration and establish the preferred authoring pattern.

**Wave 3 — capability-rich exemplar:** Voice Stories.  
Prove microphone/platform service behavior is unaffected by graphics/session migration.

**Wave 4 — repository-wide mechanical migration:** remaining first-party Activities, grouped by shared helper usage rather than one-off rewrites.

Do not combine this with unrelated visual/gameplay rewrites.

### R7.6 — Wayland implementation behind the same contract

Only after Legacy X passes the completed contract:

1. implement `WaylandDisplaySessionBackend` (and the minimum trusted compositor/session host needed by ADR 0019);
2. run the exact same contract/security tests;
3. require zero Activity code changes;
4. benchmark against Xorg on the real Acer and Pi reference hardware.

Direct KMSDRM remains an optional measured experiment, not an architectural prerequisite. If it cannot preserve trusted chrome/input without recreating compositor responsibilities, do not promote it.

### R7.7 — evidence-based backend selection

Measure at minimum:

- installed dependency closure / disk delta;
- idle and active PSS/RSS;
- process/FD count;
- Shell startup and Activity launch/return latency;
- frame pacing and idle CPU;
- pointer/controller latency;
- 100 launch/return cycles;
- deliberate Activity crash/hang recovery;
- controller disconnect/reconnect;
- protected Home under hostile/non-cooperative Activity behavior;
- 768 MiB memory-pressure behavior on the Acer floor.

Prefer one backend everywhere if physical evidence supports it. If hardware genuinely requires different implementations, profile selection is acceptable because the public Greia contract remains one architecture.

## 6. Validator rules

The Activity source/package validator should reject ordinary Activity source that imports/uses backend authority such as:

```text
Xlib / xcffib / pywayland / evdev / libinput
xrandr / xinput / xdotool
DISPLAY / XAUTHORITY / WAYLAND_DISPLAY / SDL_VIDEODRIVER
/dev/input/* / /dev/dri/*
direct raw controller device ownership
trusted-system-chrome renderer/hit-test helpers after migration
```

Validation must be AST/structured where practical and language/runtime appropriate; do not build a brittle English-keyword game. Test fixtures/tooling get explicit narrow exceptions.

## 7. Contract and negative tests

Every production backend must pass the same behavioral contract. Include at least:

- prepare -> READY -> present -> end -> Shell;
- launch failure before READY -> Shell recovery;
- crash after presentation -> Shell recovery;
- stale lease/callback rejection;
- Activity paints every pixel -> Home remains visible/authoritative;
- Activity never calls chrome helper -> Home still works;
- Activity drains/ignores its event queue -> Home still forces bounded return;
- Activity attempts fake Home -> fake control has no platform authority;
- protected-region pointer/touch is not delivered as Activity action;
- Guide/system controller action is never delivered as ordinary Activity action;
- raw `/dev/input` and display-device authority remain unavailable;
- resize/reference-canvas safe region remains correct;
- text input and high-rate Painting pointer input remain responsive;
- backend switch requires no Activity changes.

Use a deterministic fake backend for state-machine unit tests, then execute the same contract against Legacy X and later Wayland. Simulator evidence does not replace physical backend evidence.

## 8. Files expected to change during implementation

Primary platform owners:

```text
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_launcher/system_chrome.py
src/greia_launcher/composition.py
src/greia_launcher/supervisor.py
src/greia_launcher/main.py
src/greia_platform/pygame_canvas.py
src/greia_platform/activity_ui.py
src/greia_platform/activity_viewport.py
src/greia_platform/input_core.py
src/greia_platform/pygame_input.py
```

Likely new backend files only when real implementations exist:

```text
src/greia_launcher/display_session_wayland.py
# and a narrowly scoped trusted Wayland chrome/input host if required
```

Do not create `AcerBackend`, `PiBackend` or a giant all-purpose `PlatformBackend`.

## 9. Activity migration rule of thumb

For each Activity ask four questions:

1. Does it render only through runtime-neutral APIs? If yes, keep the rendering.
2. Does it draw/hit-test Greia Home/Back? Remove that responsibility.
3. Does it need essential controls near a reserved region? Consume the trusted viewport/safe-area context.
4. Does it own physical input/controller/backend state? Move that ownership to Greia and expose only semantic/runtime-neutral behavior.

The intended result is deliberately boring: gameplay code should scarcely notice whether Greia is running on Xorg or Wayland.

## 10. R7 completion interpretation

R7 is no longer interpreted as "remove Xorg" or "make Activities use direct KMS".

R7 means:

- one stable Greia display/session/input authority contract;
- backend-independent Activities;
- trusted Home/Back and reserved input genuinely above Activity authority;
- physical input owned/brokered by Greia;
- at least one production backend proven on each claimed reference platform;
- backend selection made from measured compatibility/resource evidence.

Xorg can remain an implementation if it wins the evidence. Wayland can replace it globally or on selected profiles without changing the Activity model. That is the purpose of the abstraction boundary.