# ADR 0018 — Lightweight Greia UI Foundation

**Status:** ACCEPTED  
**Date:** 2026-08-13  
**Scope:** Greia Shell, installer, parent-native surfaces, first-party Python Activities, and shared UI engineering conventions

## Context

Greia is an appliance-like child operating environment, not a desktop distribution. The project needs a coherent graphical foundation that is easy to extend as an open-source codebase while remaining suitable for the first-generation Acer Aspire One resource floor.

The repository already contains useful UI ideas in several places: Shell page/grid logic, hit targets, theme and asset caches, installer controls, and the first shared `activity_ui` primitives used by Writing and Painting. Allowing each new surface to continue inventing its own layout, cache, navigation and control model would increase duplication, make behavior inconsistent, and make low-resource performance harder to reason about.

Conversely, adopting a desktop-style window manager or a large retained widget framework would add concepts and runtime cost that Greia does not need.

## Decision

### 1. Greia uses a surface model, not a desktop/window model

The primary child-facing abstraction is a **Screen**: one full logical Greia surface occupying the current session.

A Screen may temporarily host one or more **Overlays** for bounded modal interaction such as confirmation, PIN entry, a choice sheet, or a transient explanation.

Greia does not introduce general-purpose draggable/resizable windows, minimize/maximize state, taskbars, arbitrary z-order, desktop icons, or generic window-manager behavior.

The normal conceptual hierarchy is:

```text
Screen
  └── optional Overlay / Sheet
        └── Panel / Card / Collection
              └── Control
```

Mandatory Activity Home/Back system navigation is deliberately **not** an Activity `Overlay` in this hierarchy. It belongs to the higher-trust platform presentation/input layer defined by ADR 0019 and remains outside Activity rendering and input authority.

### 2. Child grouping uses Collections, not filesystem folders

A **Collection** is an ordered group of child-facing object references with stable semantic identity and optional presentation metadata.

A Collection may visually resemble a folder, shelf, box, book, bag, or other age-appropriate object, but it is not a host filesystem directory and must not expose Linux paths.

Collections may group Activities, documents, paintings, settings choices, rewards, or other Greia-owned child objects. Filesystem storage remains behind the relevant platform service.

### 3. Strong OOP is a project architecture requirement

Greia source should be structured around cohesive domain objects with explicit ownership and narrow responsibilities.

At genuine variation points, use typed interfaces/protocols/abstract base classes and polymorphic implementations rather than growing type/backend conditionals throughout callers. Examples include runtime adapters, display/session backends, system-chrome backends, hardware adapters, storage implementations, Screens, Overlays, controls, and renderer-specific UI implementations.

Composition is preferred over inheritance when behavior is assembled rather than specialized. Inheritance is appropriate when substitutability is real and enforced by a narrow base contract.

Do not create abstraction layers merely to increase class count. An abstraction must own a stable concept, remove real duplication, enforce an invariant, or provide a genuine extension seam.

Large god objects, cross-layer manager classes, hidden global state, circular dependencies, and repeated `if backend/type/runtime == ...` dispatch trees are architecture smells and require justification or refactoring.

### 4. Renderer-neutral semantics stay above renderer-specific implementation

Greia's semantic concepts — Screen, Overlay, Collection, navigation, focus/activation, invalidation and resource bounds — are not tied to Pygame.

The current Python implementation may provide efficient Pygame-specific controls/rendering beneath those concepts. A future Web runtime may implement equivalent semantics differently without importing a Python/Pygame widget implementation.

Therefore a first-party Pygame UI helper is not itself the universal Activity contract.

ADR 0019 separately defines renderer-neutral **platform system chrome** above Activity runtime surfaces. An Activity-renderer implementation may share glyph primitives with the platform renderer, but the mandatory Home/Back controls themselves cannot be owned by Activity code.

### 5. Performance and bounded resources are part of UI correctness

The UI foundation must be designed for the extreme low-resource reference class.

Required rules:

- caches are explicitly bounded;
- images and fonts are decoded/constructed once per required variant and reused;
- static text and scaled assets are not regenerated every frame without cause;
- normal controls draw directly to the owning surface unless an off-screen surface has a measured benefit;
- avoid one backing Surface/object graph per small control;
- collections render only the visible page/items;
- histories, animations and transient resource pools have explicit limits;
- layout uses cheap deterministic geometry rather than a general constraint solver;
- ordinary static Shell screens should be able to become event/invalidation driven instead of repainting continuously while idle;
- animation is bounded and purposeful; a 30 Hz presentation target is sufficient for ordinary Shell animation unless a measured workload requires more;
- Activities that need a different frame policy own that decision inside their supervised surface.

Resource usage is an acceptance property, not a later optimization pass.

Mandatory system chrome must likewise remain a tiny bounded presentation/input layer and must not become an excuse for a general retained desktop compositor or independent always-busy rendering framework.

### 6. The initial common vocabulary is intentionally small

The shared base should grow from real use. The initial architecture vocabulary is:

- `Screen`;
- `Overlay`;
- `Control`;
- `Collection`;
- `PagedGrid` / visible-page navigation;
- bounded resource caches;
- render invalidation state;
- renderer-specific metrics/assets/fonts beneath the semantic layer.

Do not add a DOM clone, CSS system, general scene graph, arbitrary retained widget tree, animation framework, signal/slot framework, or desktop window manager without a new evidence-backed architecture decision.

### 7. Public architecture must remain understandable to outside contributors

Greia is intended to become a substantial open-source project. Stable classes, protocols and non-obvious algorithms must have useful docstrings; architectural extension points must be documented; names must express domain meaning; modules should remain cohesive; tests should cover contracts independently of hardware when possible.

A contributor should be able to determine where a new implementation belongs without tracing unrelated subsystems or copying an existing monolith.

## Initial implementation

The first source implementation is owned by:

```text
src/greia_platform/ui_core.py
src/greia_platform/activity_ui.py
```

`ui_core.py` owns renderer-neutral semantic/navigation/resource primitives. `activity_ui.py` remains the current lightweight Pygame implementation used by first-party Python Activities and may consume those common primitives.

Platform-wide Pygame consumers may use `src/greia_platform/pygame_ui.py` as the neutral import surface while existing Activity imports remain compatible.

Mandatory Activity system navigation is owned separately by:

```text
src/greia_platform/system_chrome.py
src/greia_launcher/system_chrome.py
```

under ADR 0019.

Existing Shell/installer UI should migrate incrementally to these primitives when the migration removes real duplication or resource waste. Migration must preserve current product behavior and R7 display/session boundaries; this ADR does not select a compositor or change graphics ownership.

## Consequences

Positive:

- a consistent extension model for future contributors;
- less duplicated paging/cache/navigation logic;
- better testability through polymorphic contracts;
- explicit bounded-resource behavior;
- no desktop/window-manager complexity;
- future renderer/runtime implementations can remain independent beneath common semantics.

Costs:

- some existing procedural UI code will need incremental migration;
- contributors must resist both under-abstracting repeated behavior and over-engineering speculative framework features;
- resource limits and lifecycle contracts need dedicated tests.

## Non-goals

This ADR does not:

- create a desktop environment;
- select the R7 production graphics backend;
- make Pygame the permanent universal renderer;
- expose filesystem folders to children;
- require every tiny draw helper to become a class;
- make mandatory Activity system Home/Back an Activity-owned Overlay or widget;
- authorize speculative framework growth before real consumers exist.
