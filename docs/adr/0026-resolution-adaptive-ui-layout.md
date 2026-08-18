# ADR 0026 — Resolution-Adaptive UI Layout

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Scope:** all Greia-owned graphical surfaces and shared UI/layout foundations

## Context

Greia has an extreme 1024×600 legacy reference device, but it also targets different x86 machines and first-class ARM hardware. Existing UI code already derives some sizes from the current surface, yet several surfaces still contain fixed reserves, minimum pixel sizes or breakpoint-style assumptions that can accidentally turn one tested panel into the de facto coordinate system.

Handling a resize event is not sufficient. A UI is responsive only when its semantic regions, collections, controls, text, focus geometry and protected system chrome remain usable across the usable display modes Greia exposes.

More importantly, responsiveness must **not become work that every designer or Activity author repeats**. Requiring each surface to maintain separate coordinate sets, breakpoint branches, or hand-tuned positions for 640×480, 1024×600, 1080p, 4K, portrait, and future screens would merely distribute the fixed-resolution problem across the codebase.

Greia also cannot solve this by adopting a heavyweight desktop widget framework or general constraint solver: ADR 0018's low-resource and appliance constraints still apply.

Product requirements are defined in:

```text
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
```

## Decision

### 1. The live usable viewport is layout authority

Greia UI geometry is derived from the current usable viewport and relevant platform-protected regions. Hardware model names and build profiles are not UI-layout selectors.

`1024×600` is an acceptance point, not a logical canvas.

### 2. One semantic layout is authored once

**This is a mandatory platform contract.**

A designer or UI/Activity author defines the semantic composition once: for example header, content collection, optional explanatory region, footer/actions; a collection's minimum useful item size; whether it scrolls/pages; alignment intent; relative importance; readable typography bounds; and artwork fit behavior.

The platform layout layer then derives:

- actual rectangles;
- margins and gaps within bounded design tokens;
- row/column counts;
- wrapping/reflow;
- paging/scroll windows;
- bounded local scale;
- visible and hit-test geometry;
- protected system-chrome/content separation;
- resize recomputation.

Authors **must not** be expected to provide or maintain:

- one coordinate set per resolution;
- per-resolution item positions;
- device/model-specific layouts;
- long breakpoint tables such as `if width >= 1920`, `elif width >= 1024`, etc.;
- a second hand-built portrait layout merely to preserve containment;
- separate pointer hit geometry from the layout that drew the control.

A small semantic mode change is allowed when the *kind of interaction* genuinely changes (for example a collection changing from simultaneously visible items to scrolling), but the threshold and positions should be computed by shared layout policy from available space, not authored as a list of target resolutions.

### 3. Reflow precedes shrink

Responsive surfaces adapt structure automatically: columns, rows, collection window, wrapping, panel placement and scrolling/pagination. Local decorative dimensions may scale within bounds, but Greia must not implement responsiveness by uniformly shrinking or stretching a fixed-resolution composition.

### 4. Shared renderer-neutral layout authority

Reusable responsive calculations belong above renderer-specific drawing code.

The initial implementation owner is:

```text
src/greia_platform/responsive_layout.py
```

It provides small renderer-neutral viewport/rectangle/grid primitives and is expected to grow only with **real reusable layout needs**. The architectural direction is a small automatic layout engine/policy layer, not a collection of per-screen breakpoint helpers.

Launcher, installer, profile UI, system chrome and first-party Activities should consume shared layout policies where doing so removes manual item positioning, fixed-resolution assumptions or duplicated sizing logic.

Renderer-specific code remains responsible for drawing the returned geometry; it should not recalculate a parallel layout independently.

This layer deliberately does not implement a DOM, CSS engine, retained widget tree or general constraint solver.

### 5. Design tokens express intent, not target pixels

Designers may specify bounded semantic values such as:

- compact / normal / spacious gap intent;
- minimum readable control or tile size;
- preferred/max content width;
- typography role and minimum/maximum readable size;
- alignment and ordering;
- contain/crop artwork behavior;
- scroll/page permission.

Those are inputs to shared layout policy. They are not instructions like "x=412 at 1024×600 and x=780 at 1920×1080".

### 6. Containment is a hard invariant

For a display mode exposed as usable, required controls and their hit regions must remain inside the usable viewport or inside an explicitly scrollable/paged region with a reachable navigation path.

When content becomes too constrained, geometry must fail contained and visibly rather than placing destructive/essential controls outside the viewport.

### 7. System chrome participates in responsive layout

ADR 0019 Home/Back chrome remains platform-owned and outside Activity authority. Its protected region must be computed for the live viewport and reserved from Activity content geometry. Activities must not assume unrestricted access to the physical framebuffer dimensions.

### 8. Runtime size changes invalidate dependent state

A display-mode/window-size change must recompute geometry and invalidate or correctly key size-dependent caches. Stale hit targets or scaled surfaces cannot remain authoritative after a resize.

Repeated resize/mode transitions must remain bounded and leak-free.

### 9. Automated acceptance is property-oriented

Tests must cover a representative matrix plus generated nearby/arbitrary viewport dimensions. Exact-resolution snapshot tests alone are insufficient.

Important invariants include:

- positive/contained geometry;
- no essential off-screen control;
- valid collection capacity and navigation;
- hit geometry matching visible geometry;
- preserved asset aspect ratio;
- bounded scaling/growth;
- valid focus order after reflow;
- the same semantic layout specification working across all tested viewport classes without resolution-specific author branches.

### 10. Physical readability remains separate evidence

Pure geometry tests cannot certify actual readability or performance. The 1024×600 Acer floor remains mandatory physical acceptance, while other resolutions can be exercised in owner-controlled windowed/VM/hardware environments as appropriate.

## Consequences

Positive:

- designers and Activity authors create one layout instead of many resolution variants;
- one panel does not become an accidental platform contract;
- x86/ARM and future displays share the same layout architecture;
- odd aspect ratios expose defects in the platform layout layer rather than creating authoring burden;
- reusable geometry removes duplicated breakpoint and hit-position logic;
- automated tests can explore many sizes cheaply.

Costs:

- existing launcher/installer/Activity surfaces with local fixed geometry need incremental migration toward shared automatic layout policies;
- the shared layout layer must be thoughtfully expanded when real UI patterns recur;
- screenshots at one reference resolution are no longer sufficient UI evidence;
- layout and hit-target tests need to be maintained alongside visual work.

## Non-goals

This ADR does not:

- guarantee that every physically possible 1×1 or otherwise unusable display mode is a valid product mode;
- require Greia to advertise every mode a monitor reports;
- authorize a heavyweight UI toolkit or desktop framework;
- create CSS-like per-breakpoint authoring;
- choose the R7 graphics/session backend;
- remove the 1024×600 low-resource reference requirement;
- make portrait orientation a required hardware product mode merely because portrait dimensions are used as an engineering stress probe.
