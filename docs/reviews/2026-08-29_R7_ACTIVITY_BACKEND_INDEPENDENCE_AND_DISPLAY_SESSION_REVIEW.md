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

A second invariant is equally important: **backend independence must not create an abstraction tax. Performance is a correctness property on the Acer floor.** Greia must preserve the optimization capabilities already established by `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` and `skills/greia-activity-authoring/ENGINEERING.md`.

The design principle is:

```text
portable semantics
+ backend-neutral Activity source
+ backend-specific fast paths below the boundary
```

not:

```text
one slow generic implementation shared by every backend
```

## 2. Boundary: what belongs where

### Activity / runtime-neutral layer

Allowed:

- `pygame.Surface`, draw/blit/font/mixer primitives;
- `pygame.display.set_mode`, resize and flip/update as an SDL client operation;
- ordinary local keyboard/mouse/touch events appropriate to the Activity;
- Greia semantic input APIs and interaction profiles;
- Greia-provided viewport/safe-region/session context;
- Greia lifecycle, storage, event, locale and permission APIs;
- the existing Greia performance patterns: precomposed opaque backdrops, converted surfaces, bounded caches, dirty-region rendering, cached transforms, invalidation-driven redraw and adaptive pacing.

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
- display/input settings adapters;
- backend-private performance choices and acceleration that do not change the Activity contract.

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
  |-- existing Activity-side caches / dirty rendering / prepared resources
  v
Activity runtime adapter + supervisor
  |-- injects backend-private client transport
  |-- injects only approved capabilities
  |-- owns lifecycle process boundary
  |-- does not proxy normal pixels or high-rate pointer/text input
  v
DisplaySessionCoordinator + trusted input/chrome coordinators
  |
  +-- selected DisplaySessionBackend
  |     +-- Xorg compatibility
  |     +-- Wayland candidate
  |     +-- backend-private measured fast paths
  |
  +-- trusted Home/Back host
  +-- controller/input broker
  v
Linux graphics/input stack
```

`DisplayTransport` is launcher-internal. X11/Wayland environment values may be injected into the child process because SDL needs them, but they are plumbing, not Activity API. Activity source must not read or branch on them.

## 5. Performance preservation contract

R7 must preserve the performance model already measured on the reference Acer. The existing manual records the important cost shape: opaque full-screen copies are cheap, large per-pixel-alpha blends are expensive, `smoothscale`/decode in hot paths are unacceptable, and idle wake cadence materially consumes the single Atom core. Backend work must be designed around those facts rather than assuming desktop-class headroom.

### 5.1 No pixel-proxy abstraction

The platform abstraction must not turn Activity presentation into a Greia IPC framebuffer protocol or copy every rendered frame through Python merely to make backends look uniform.

The Activity should continue rendering through SDL/Pygame directly to the backend-provided client surface. `DisplaySessionBackend` supplies/owns session transport and authority; it does not become the renderer.

This preserves:

- Pygame/SDL surface conversion and optimized blit paths;
- Activity precomposed opaque backdrops;
- dirty-region and invalidation-driven rendering;
- cached scale/flip/decoded assets;
- local high-rate drawing such as Painting strokes;
- backend/SDL acceleration or transport improvements where the selected stack supports them.

### 5.2 No high-rate input IPC by default

Do not route every mouse motion, text event or drawing sample through a Python broker solely for architectural symmetry.

Protected system actions and physical-controller ownership are trusted-platform responsibilities. Ordinary high-rate Activity input may remain on the direct SDL event path when the selected backend can guarantee that reserved Greia input is consumed first.

If a backend requires a bridge, it must be measured on the Acer floor before adoption and must not silently degrade Painting, pointer games or text entry.

### 5.3 Trusted chrome must be tiny and cheap

Moving Home/Back out of Activities must not replace one cheap local draw with a continuously composited full-screen alpha layer.

The trusted chrome implementation should, where the backend permits:

- redraw only on state/invalidation, not every idle tick;
- pre-render/cache stable chrome pixels;
- keep alpha/composited area to the small protected footprint;
- avoid full-screen translucent surfaces for ordinary Activity presentation;
- avoid polling work while idle when event-driven wakeup is available;
- keep resource ownership bounded;
- measure any compositor/session host rather than assuming its cost is negligible.

A backend that can enforce trusted chrome only by imposing a large permanent frame/composition cost is not automatically acceptable.

### 5.4 Backend specialization is allowed and expected

The backend interface standardizes semantics and lifecycle, not implementation mechanics.

`LegacyXDisplaySessionBackend`, a future Wayland backend and any measured KMS path may use different backend-private mechanisms for presentation, focus, buffers, input interception or synchronization. SDL/backend facilities such as shared-memory or hardware-assisted paths may be used internally when available and measured.

Do not expose those mechanisms to Activities, but do not prohibit them below the boundary.

### 5.5 Preserve optimization opportunities, not identical internals

The acceptance requirement is that the same Activity code can retain the same optimization strategy on every production backend:

```text
prepare/decode once
convert once
precompose static scene
cache bounded reusable transforms
redraw only invalidated regions
present through SDL
sleep/pace when idle
```

The backend may implement the final presentation differently. It must not force the Activity to abandon those optimizations.

### 5.6 Performance baselines precede migration

Before changing a representative Activity or backend path, capture a baseline for the exact user interaction being touched. For R7 this includes at least:

- Writing steady typing/editing;
- Painting sustained pointer drawing;
- one static/turn-based dirty-render Activity;
- one continuously animated game;
- Shell -> Activity launch and Activity -> Shell return;
- trusted Home activation;
- idle Activity with no visible changes.

Record frame/update cost, process CPU, RSS/PSS sanity, input responsiveness and relevant redraw/invalidation counts where practical.

After the migration, repeat the same workload on the same hardware and source state. A backend/security refactor that materially degrades an accepted hot path is not complete merely because functional tests pass.

### 5.7 Existing performance targets remain in force

R7 does not relax the current Activity engineering targets:

```text
smooth gameplay target: ~30 fps on Atom-class floor
added input latency:     <= 50 ms
static/paused idle CPU:  near zero where architecture permits
```

Physical claims require named hardware and exact SHA. Backend selection must consider user-visible performance alongside authority, reliability, memory, disk and compatibility.

## 6. Implementation sequence

### R7.1 — freeze the Activity/backend and performance invariants

1. Add/enforce the backend-independence invariant in contributor guidance/validation.
2. Add a repository validator for backend-specific Activity dependencies.
3. Scan every first-party Activity and classify backend/trusted-chrome/raw-input findings before changing behavior.
4. Explicitly allow ordinary Pygame/SDL APIs; do not create false positives for `pygame.display` or normal event handling.
5. Record the representative physical performance baselines required by §5.6 before changing those hot paths.

**Exit:** new Activity code cannot deepen backend coupling, and the migration has explicit before-state performance evidence rather than relying on memory.

### R7.2 — harden the existing display-session seam without adding render copies

1. Keep `DisplaySessionCoordinator` as the state-machine owner.
2. Review `DisplaySessionBackend` against the real needs: prepare, present, restore, trusted overlay coordination, focus/session recovery and backend-private launch transport.
3. Move any generic-launcher X11 behavior behind `LegacyXDisplaySessionBackend` or another narrowly X-specific collaborator.
4. Compose the backend in `greia_launcher.composition`; do not scatter backend conditionals.
5. Keep `DisplayTransport` private to trusted launcher/supervisor code.
6. Reject designs that proxy normal Activity frames through Python or insert unnecessary full-frame copies.

**Exit:** replacing the backend implementation requires no Activity source/API changes and the seam itself does not impose a measurable hot-path rendering tax.

### R7.3 — move trusted chrome out of Activities

1. Implement a real `SystemChromeBackend` for the current Xorg compatibility session first, using the already-existing `SystemChromeCoordinator` seam.
2. Integrate its lifecycle with the display-session lease and Activity supervisor.
3. Ensure Home/Back input is consumed before Activity input and invokes Greia stop/forced-return authority.
4. Change viewport/canvas helpers to receive trusted reserved-region geometry rather than instantiate chrome authority.
5. Remove Activity-side `draw_system_chrome_overlay()` and `is_home_clicked()` usage.
6. Make the chrome path invalidation/event driven and bounded as specified in §5.3.
7. Fail closed: do not present an Activity if mandatory Home cannot be preserved.

**Exit:** a deliberately non-cooperative test Activity cannot hide, cover, intercept or disable real Home, and the trusted chrome path does not create a persistent full-screen composition/redraw penalty.

### R7.4 — input ownership completion

1. Preserve `input_core.py` as runtime-neutral semantic vocabulary.
2. Keep physical controller ownership in the trusted platform; ordinary Activities do not open raw joystick/device nodes.
3. Consume Guide/system input before Activity delivery.
4. Provide semantic controller actions and virtual pointer according to the manifest interaction profile.
5. Preserve direct local Pygame text/pointer paths where safe and performance-sensitive rather than forcing high-rate IPC without evidence.

**Exit:** keyboard/pointer/touch/controller coexist, controller reconnect works, protected input remains outside Activity authority, and high-rate pointer/text workloads remain within accepted latency/performance behavior.

### R7.5 — migrate first-party Activities by pattern

**Wave 1 — canonical/mandatory:** Writing, Painting.  
Remove cooperative Home/chrome ownership; preserve existing caches/render cadence; prove save/recovery and typing/drawing performance survive.

**Wave 2 — shared reference-canvas exemplars:** Labyrinth, Dragon Flight, Shape Garden.  
Use these to prove the central canvas/viewport migration without discarding Activity-side scene/preparation optimizations.

**Wave 3 — capability-rich exemplar:** Voice Stories.  
Prove microphone/platform service behavior is unaffected by graphics/session migration.

**Wave 4 — repository-wide mechanical migration:** remaining first-party Activities, grouped by shared helper usage rather than one-off rewrites.

Do not combine this with unrelated visual/gameplay rewrites. Do not "simplify" an Activity by removing an accepted optimization merely to make backend migration easier.

### R7.6 — Wayland implementation behind the same contract

Only after Legacy X passes the completed contract:

1. implement `WaylandDisplaySessionBackend` and only the minimum trusted compositor/session host actually required by ADR 0019;
2. run the exact same functional/security contract tests;
3. require zero Activity code changes;
4. repeat the representative Activity performance workloads from the Legacy X baseline;
5. benchmark against Xorg on the real Acer and Pi reference hardware.

Direct KMSDRM remains an optional measured experiment, not an architectural prerequisite. If it cannot preserve trusted chrome/input without recreating compositor responsibilities, do not promote it.

### R7.7 — evidence-based backend selection

Measure at minimum:

- installed dependency closure / disk delta;
- idle and active PSS/RSS;
- process/FD count;
- Shell startup and Activity launch/return latency;
- frame pacing and idle CPU;
- pointer/controller latency;
- Painting sustained-input responsiveness;
- Writing text-input responsiveness;
- dirty-render/static Activity steady-state cost;
- animated Activity frame cost;
- trusted-chrome steady and activation cost;
- 100 launch/return cycles;
- deliberate Activity crash/hang recovery;
- controller disconnect/reconnect;
- protected Home under hostile/non-cooperative Activity behavior;
- 768 MiB memory-pressure behavior on the Acer floor.

Prefer one backend everywhere if physical evidence supports it. If hardware genuinely requires different implementations, profile selection is acceptable because the public Greia contract remains one architecture.

Performance is a gate, not a decorative benchmark. A backend that is architecturally elegant but materially worsens accepted child-visible performance on the reference floor does not win automatically.

## 7. Validator rules

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

The validator must **not** reject legitimate performance-oriented Pygame/SDL code such as surface conversion, bounded caches, `pygame.display`, dirty rects, direct local pointer/text events or cached transforms merely because those are close to the renderer.

## 8. Contract, negative and performance tests

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

Performance-sensitive equivalence also requires:

- no accidental per-frame decode/scale/font/config/device work introduced by the migration;
- no new unbounded caches;
- no continuous Activity redraw caused solely by trusted chrome;
- no mandatory full-frame Python copy/proxy path;
- no mandatory high-rate pointer/text IPC path without physical evidence;
- representative pre/post physical measurements from §5.6;
- pixel/behavior equivalence for cache/dirty-region fast paths where applicable.

Use a deterministic fake backend for state-machine unit tests, then execute the same contract against Legacy X and later Wayland. Simulator evidence does not replace physical backend evidence.

## 9. Files expected to change during implementation

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

## 10. Activity migration rule of thumb

For each Activity ask five questions:

1. Does it render only through runtime-neutral APIs? If yes, keep the rendering.
2. Which existing performance optimizations does it rely on, and will the migration preserve them unchanged?
3. Does it draw/hit-test Greia Home/Back? Remove that responsibility.
4. Does it need essential controls near a reserved region? Consume the trusted viewport/safe-area context.
5. Does it own physical input/controller/backend state? Move that ownership to Greia and expose only semantic/runtime-neutral behavior.

The intended result is deliberately boring: gameplay code and its optimization strategy should scarcely notice whether Greia is running on Xorg or Wayland.

## 11. R7 completion interpretation

R7 is no longer interpreted as "remove Xorg" or "make Activities use direct KMS".

R7 means:

- one stable Greia display/session/input authority contract;
- backend-independent Activities;
- no generic abstraction tax that discards accepted low-resource optimization strategies;
- trusted Home/Back and reserved input genuinely above Activity authority;
- physical input owned/brokered by Greia;
- at least one production backend proven on each claimed reference platform;
- backend selection made from measured compatibility, authority, resource and performance evidence.

Xorg can remain an implementation if it wins the evidence. Wayland can replace it globally or on selected profiles without changing the Activity model. Different backends may use different optimized internals. That is the purpose of the abstraction boundary.