# ADR 0027 — Activity Coordinate Spaces, Reference Canvas and World Camera

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Scope:** all Activity runtimes, first-party Activities, Activity SDK/UI authoring, platform system-chrome/display/input integration

## Context

Greia Activities are not one visual category. The platform must support, among other things:

- a simple grid-based arithmetic exercise;
- a multiple-choice visual puzzle;
- a drawing/painting canvas;
- a text editor;
- a physics or construction sandbox;
- a fixed-board game;
- a top-down game;
- a side-scrolling platform game with a world much larger than the screen;
- future Web-runtime Activities with equivalent semantics.

The project therefore cannot equate "responsive Activity" with "move some buttons around at different screen widths".

At the same time, authors must not have to design and maintain separate layouts for 640×480, 1024×600, 1366×768, 1080p, 4K, Raspberry Pi displays, or future hardware. The first-generation Acer's 1024×600 panel is a useful design reference, but it must not become a physical-resolution dependency.

Existing first-party code already demonstrates the problem:

- Writing/Painting use a simple global scale derived from 1024×600;
- Shape Garden uses raw physical pixel coordinates;
- launcher/system UI has its own responsive geometry;
- games will need camera/world semantics that neither approach represents.

ADR 0026 establishes platform-owned automatic responsiveness. This ADR defines the Activity-specific spatial model beneath that requirement.

## Decision

### 1. Greia recognizes four Activity spatial models

The renderer-neutral vocabulary is:

```text
fluid
reference_canvas
world_camera
hybrid
```

These are authoring/layout semantics, not hardware profiles and not runtime types.

An Activity may evolve from one model to another without changing its identity or storage semantics.

### 2. Physical pixels are never the authored Activity coordinate contract

The actual Activity surface uses **physical coordinates** supplied by the selected display backend.

Activity content may instead use:

- **semantic layout coordinates** produced by Greia's responsive layout policies;
- **reference-canvas coordinates**, defaulting to a 1024×600 logical design space;
- **world coordinates**, arbitrary units owned by the game/simulation;
- combinations of these in separate layers.

Pointer/touch input is mapped from physical coordinates back through the same transform used for rendering.

Authors do not implement an independent inverse transform by hand.

### 3. 1024×600 is the default reference authoring canvas

The default Activity reference design space is:

```text
1024 × 600 logical units
```

This is intentionally aligned with the low-resource Acer reference because:

- it gives designers a concrete, child-tested composition size;
- pixel values remain intuitive while authoring;
- first-party visual acceptance can occur at 1:1 scale on the hardware floor;
- a design that is readable there generally has adequate information density.

It is nevertheless a **logical canvas**. At another physical resolution Greia computes the mapping automatically.

A specialized Activity may choose another logical reference size when there is a real content reason, but "this monitor is 1080p" is not such a reason.

### 4. Reference-canvas mapping has three uniform policies

#### `contain`

The entire authored reference view is always visible.

Greia scales uniformly and centers it in the available target rectangle. If aspect ratios differ, letterbox/pillarbox space may remain.

Use for:

- fixed visual puzzles;
- board layouts where every authored edge must remain visible;
- legacy/fixed compositions during migration;
- scenes where cropping would hide meaningful content.

Do not stretch x/y independently.

#### `cover`

The target rectangle is completely filled with uniform scale; excess logical edges may be cropped.

Use for:

- decorative/immersive backgrounds;
- scenes with intentionally nonessential outer bleed;
- visual layers that are designed with a safe center region.

Essential controls/content must not rely on regions that `cover` may crop.

#### `expand`

The reference view is preserved at a uniform scale but extra aspect-ratio space reveals **more logical content** instead of showing bars or cropping.

Examples:

- on a wider screen, a side-scroller can reveal more world to the left/right;
- on a taller screen, a top-down world can reveal more vertically;
- a simulation can expose additional environment without changing physics scale.

This is the default world-camera policy.

`expand` is not appropriate for a finite fixed artwork whose outer logical area does not exist; use `contain` or fluid layout instead.

### 5. Fluid model is for semantic UI/content reflow

`fluid` Activities do not primarily place content at fixed canvas coordinates.

They describe semantic regions and constraints, then shared responsive layout policies choose actual geometry.

Use for:

- arithmetic/question grids;
- menus/collections;
- text editors;
- settings-like controls;
- galleries;
- toolbars surrounding a resizable content region.

A grid-based math Activity should say, conceptually:

```text
question/feedback region
answer-grid collection
minimum useful answer-card size
maximum rows/columns as appropriate
scroll/page if necessary
```

It should not contain hand-written layouts for each screen resolution.

### 6. World-camera model is for worlds larger than the viewport

`world_camera` separates world state from display resolution.

World objects exist in logical world coordinates independent of the screen. A camera selects a logical view centered at an arbitrary world position. Greia maps that camera to the physical Activity viewport.

For a side-scroller:

```text
world coordinates         e.g. x = 0..100000, y = 0..1200
reference camera view     e.g. 1024×600 logical units
camera center             follows player according to game policy
fit                        expand (normally)
physical surface           whatever Greia actually provides
```

Changing monitor resolution must not:

- alter character speed;
- alter gravity;
- alter collision coordinates;
- rewrite level data;
- move saved objects in world space;
- require another authored level layout.

It only changes the camera transform/visible world extent according to policy.

### 7. Hybrid is normal, not an exception

Many rich Activities combine layers with different spatial semantics.

Typical side-scroller:

```text
world/background layer     world_camera / expand
HUD/status layer           fluid safe UI
modal pause/help sheet     fluid overlay
platform Home/Back         Greia system chrome, outside Activity authority
```

Typical Painting Activity:

```text
toolbar/palette             fluid safe UI
painting document           logical document canvas fitted into remaining region
platform Home/Back          Greia system chrome
```

Typical construction/physics Activity:

```text
world/simulation            world_camera
parts palette               fluid collection
selected-object handles     world transform
help/confirmation           fluid overlay
```

Authors compose these platform primitives; they do not manually calculate one monolithic set of physical coordinates.

### 8. Platform system chrome creates protected physical regions

ADR 0019 Home/Back remains platform-owned.

An Activity viewport therefore consists of:

- the full physical Activity surface;
- one or more platform-protected physical regions;
- an automatically derived safe UI region for essential Activity controls.

World/background rendering may intentionally pass visually beneath protected chrome when the backend composition model permits it, but Activity input in that region remains unavailable to the Activity.

Essential Activity UI should normally use the safe UI region.

The platform computes it. Authors do not hard-code "leave 150 pixels at the top-left".

### 9. Drawing and input must share one transform object

A transform is authoritative in both directions:

```text
logical/world -> physical     rendering
physical -> logical/world     pointer/touch interaction
```

This prevents a common class of bugs where an object looks correct after scaling but clicks are offset because hit testing still uses physical/reference coordinates from a different calculation.

Controller/keyboard semantic input remains governed by ADR 0020 and need not pass through a pointer-coordinate transform.

### 10. Hit regions belong to logical/semantic objects

For canvas/world content, define hit geometry in the same logical coordinate space as the object.

For fluid controls, visible and hit geometry come from the same shared layout result.

Do not maintain a second manually positioned hitbox table per resolution.

### 11. Artwork scaling preserves aspect ratio by default

Greia must not non-uniformly stretch character art, icons, tiles, sprites or scene art merely to fill a viewport.

Use one of:

- contain;
- cover with explicit crop semantics;
- world-camera transform;
- fluid region plus contain/crop behavior.

Any intentional non-uniform visual deformation is an Activity/art effect, not a resolution adaptation strategy.

### 12. Resolution does not change durable content semantics

Changing viewport size must not rewrite durable Activity state solely to make it fit a screen.

Examples:

- a painting's document dimensions are document metadata, not current monitor dimensions;
- a level's world coordinates remain stable;
- a math question/answer identity is independent of grid columns;
- text contents are independent of current wrap points;
- camera position may persist if useful, but physical pixel offsets must not become portable save data.

Portable saves remain architecture/resolution-neutral.

### 13. Runtime-neutral architecture, renderer-specific adapters

Initial renderer-neutral implementation:

```text
src/greia_platform/activity_viewport.py
src/greia_platform/responsive_layout.py
```

They define coordinate/viewport semantics and pure transform math.

Pygame-specific convenience adapters may live below these contracts in `greia_platform.activity_ui` / `pygame_ui`. A future Web runtime implements equivalent semantics using its own renderer/browser mechanisms without importing Pygame.

### 14. Authors should get convenience, not math homework

The target authoring experience is approximately:

#### Fixed puzzle/reference canvas

```python
canvas = Greia reference canvas 1024×600, contain
# draw at the one authored coordinate system
# Greia presents it at the actual viewport
# pointer positions are received/mapped in canvas coordinates
```

#### Side-scroller

```python
camera = Greia world camera centered on player, reference view 1024×600, expand
# draw/query world objects in world coordinates
# Greia maps them to actual pixels
# pointer world interactions map back through camera if needed
```

#### Grid math Activity

```python
layout = Greia fluid collection with child-sized card constraints
# populate semantic answers
# Greia decides columns/rows/window from available space
```

The exact convenience API can evolve, but requiring each Activity author to reproduce the transform/layout algorithm is contrary to this ADR.

### 15. Preview/testing must use the same platform transforms

Future Activity preview tooling should let a designer author at the 1024×600 reference and switch viewport presets/arbitrary dimensions without changing Activity source.

The preview must invoke the same shared transform/layout implementation used at runtime. A separate fake responsive preview algorithm would create false confidence.

### 16. Performance remains part of the design

Automatic resolution support must not imply rendering every Activity into a giant 4K off-screen surface.

Preferred behavior:

- logical math remains cheap/pure;
- cull world objects outside the logical camera view;
- render only visible collection items;
- cache bounded scaled assets/variants;
- at native 1024×600, avoid unnecessary scale passes;
- choose renderer-specific direct-transform or intermediate-surface strategies based on measured cost;
- no per-frame filesystem reads/font creation/image decode;
- no unbounded transform/surface caches on repeated resize.

A Pygame helper that offers an off-screen reference surface may be useful for simple fixed Activities, but it must not become the only rendering architecture for complex games.

## Consequences

Positive:

- one Activity can run across Greia hardware without per-resolution authoring;
- designers can work against a concrete 1024×600 reference when appropriate;
- simple UI and complex games are both first-class rather than forcing one into the other's model;
- side-scrollers/world games keep stable physics/level coordinates;
- input and rendering stay aligned through one transform;
- future Web runtime can share semantics without sharing Pygame code;
- system chrome/safe areas become an explicit part of Activity layout.

Costs:

- current first-party Activities need migration from ad-hoc physical scaling/coordinates;
- Pygame convenience APIs need careful design so simple authors do not handle transforms manually;
- hybrid Activities must consciously separate world and UI layers;
- visual acceptance must cover multiple aspect ratios as well as the Acer reference.

## Non-goals

This ADR does not:

- force every Activity into a fixed 1024×600 off-screen surface;
- force every Activity into fluid widgets;
- make resolution changes alter gameplay physics/world state;
- authorize Activities to own platform Home/Back;
- define a general scene graph/game engine;
- choose one camera-follow algorithm for games;
- require a desktop-style UI framework;
- make every arbitrary monitor mode a supported Greia product mode.
