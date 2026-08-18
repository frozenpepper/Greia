# ADR 0026 — Resolution-Adaptive UI Layout

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Scope:** all Greia-owned graphical surfaces and shared UI/layout foundations

## Context

Greia has an extreme 1024×600 legacy reference device, but it also targets different x86 machines and first-class ARM hardware. Existing UI code already derives some sizes from the current surface, yet several surfaces still contain fixed reserves, minimum pixel sizes or breakpoint-style assumptions that can accidentally turn one tested panel into the de facto coordinate system.

Handling a resize event is not sufficient. A UI is responsive only when its semantic regions, collections, controls, text, focus geometry and protected system chrome remain usable across the usable display modes Greia exposes.

Greia also cannot solve this by adopting a heavyweight desktop widget framework or general constraint solver: ADR 0018's low-resource and appliance constraints still apply.

Product requirements are defined in:

```text
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
```

## Decision

### 1. The live usable viewport is layout authority

Greia UI geometry is derived from the current usable viewport and relevant platform-protected regions. Hardware model names and build profiles are not UI-layout selectors.

`1024×600` is an acceptance point, not a logical canvas.

### 2. Reflow precedes shrink

Responsive surfaces must first adapt structure: columns, rows, collection window, wrapping, panel placement and scrolling/pagination. Local decorative dimensions may scale within bounds, but Greia must not implement responsiveness by uniformly shrinking or stretching a fixed-resolution composition.

### 3. Shared renderer-neutral geometry

Reusable responsive calculations belong above renderer-specific drawing code.

The initial implementation owner is:

```text
src/greia_platform/responsive_layout.py
```

It provides small renderer-neutral viewport/rectangle/grid primitives. It deliberately does not implement a DOM, CSS engine, retained widget tree or generic constraint solver.

Launcher, installer and first-party Activity migrations should consume shared geometry where doing so removes fixed-resolution assumptions or duplicated sizing logic.

### 4. Containment is a hard invariant

For a display mode exposed as usable, required controls and their hit regions must remain inside the usable viewport or inside an explicitly scrollable/paged region with a reachable navigation path.

When content becomes too constrained, geometry must fail contained and visibly rather than placing destructive/essential controls outside the viewport.

### 5. System chrome participates in responsive layout

ADR 0019 Home/Back chrome remains platform-owned and outside Activity authority. Its protected region must be computed for the live viewport and reserved from Activity content geometry. Activities must not assume unrestricted access to the physical framebuffer dimensions.

### 6. Runtime size changes invalidate dependent state

A display-mode/window-size change must recompute geometry and invalidate or correctly key size-dependent caches. Stale hit targets or scaled surfaces cannot remain authoritative after a resize.

Repeated resize/mode transitions must remain bounded and leak-free.

### 7. Automated acceptance is property-oriented

Tests must cover a representative matrix plus generated nearby/arbitrary viewport dimensions. Exact-resolution snapshot tests alone are insufficient.

Important invariants include:

- positive/contained geometry;
- no essential off-screen control;
- valid collection capacity and navigation;
- hit geometry matching visible geometry;
- preserved asset aspect ratio;
- bounded scaling/growth;
- valid focus order after reflow.

### 8. Physical readability remains separate evidence

Pure geometry tests cannot certify actual readability or performance. The 1024×600 Acer floor remains mandatory physical acceptance, while other resolutions can be exercised in owner-controlled windowed/VM/hardware environments as appropriate.

## Consequences

Positive:

- one panel does not become an accidental platform contract;
- x86/ARM and future displays share the same layout architecture;
- odd aspect ratios expose defects earlier;
- reusable geometry reduces duplicated breakpoint logic;
- automated tests can explore many sizes cheaply.

Costs:

- existing launcher/installer/Activity surfaces with local fixed geometry need incremental migration;
- screenshots at one reference resolution are no longer sufficient UI evidence;
- layout and hit-target tests need to be maintained alongside visual work.

## Non-goals

This ADR does not:

- guarantee that every physically possible 1×1 or otherwise unusable display mode is a valid product mode;
- require Greia to advertise every mode a monitor reports;
- authorize a heavyweight UI toolkit or desktop framework;
- choose the R7 graphics/session backend;
- remove the 1024×600 low-resource reference requirement;
- make portrait orientation a required hardware product mode merely because portrait dimensions are used as an engineering stress probe.
