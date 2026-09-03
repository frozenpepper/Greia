# Greia Responsive UI and Display Layout Requirements

**Status:** accepted product requirement  
**Date:** 2026-08-18  
**Scope:** every Greia-owned graphical surface: boot/install UI after graphics handoff, profile picker, launcher/Shell, system chrome, Parent UI where rendered locally, first-party Activities, settings, overlays and recovery surfaces

## 1. Product requirement

Greia must not be designed for one fixed pixel resolution.

Every Greia-owned UI must adapt to the **actual current usable viewport** reported by the display/session layer. `1024×600` remains an important low-resource/reference acceptance point, but it is not a coordinate system, a fixed canvas, or permission to hard-code layout around one Acer panel.

The same UI architecture must remain usable across different resolutions, aspect ratios and pixel densities without requiring model-specific forks.

This requirement applies equally to x86 and ARM hardware.

## 2. Core invariant

For every display mode that Greia exposes as usable:

- essential controls remain fully reachable;
- essential text remains readable and is not geometrically squashed;
- no required control is permanently clipped beyond an edge;
- no required interaction depends on coordinates that only make sense at one resolution;
- collections reflow, paginate or scroll when space changes;
- overlays/sheets stay inside the usable viewport and remain dismissible;
- protected Greia Home/Back system chrome remains visible, reachable and outside Activity authority;
- pointer/touch hit targets remain aligned with what is visibly drawn;
- keyboard/controller focus order remains valid after reflow;
- resize/mode changes invalidate geometry and renderer caches that depend on size;
- aspect-ratio changes do not stretch icons, artwork or text non-uniformly;
- child-facing layouts preserve clear hierarchy rather than merely shrinking every element by one global scale factor.

A layout that looks good at 1024×600 but clips at 800×600, wastes most of a 1920×1080 screen, or breaks when the aspect ratio changes is a defect.

## 3. Single-layout authoring contract

**Designers and coders define one semantic layout. They do not maintain multiple resolution-specific layouts.**

An author should express intent such as:

- this is a header, content collection, footer or overlay;
- these controls are ordered together;
- this collection may scroll/page;
- this tile/control has a minimum useful size and a bounded preferred size;
- this text uses a semantic typography role with readable bounds;
- this artwork should contain/crop while preserving aspect ratio;
- this action is primary/secondary and must remain reachable.

The Greia platform layout system is responsible for converting that single semantic definition into actual geometry for the current viewport, including:

- positions and rectangles;
- row/column counts;
- wrapping/reflow;
- margins and gaps from shared design tokens;
- bounded scaling;
- scroll/page windows;
- protected system-chrome reservation;
- visible and hit-test geometry;
- recomputation after resolution/window changes.

Authors must **not** be required to write or maintain:

- `640×480` positions;
- `1024×600` positions;
- `1920×1080` positions;
- 4K positions;
- separate Acer/Pi/desktop coordinate tables;
- long width/height breakpoint chains;
- duplicated pointer hit rectangles that are separate from the layout used to draw controls.

A surface may declare semantic constraints and bounded design preferences. It may not make responsiveness the responsibility of every individual Activity or screen implementation.

If a recurring layout pattern needs special handling, improve the shared layout primitive/policy so all consumers benefit rather than adding another resolution-specific branch in one screen.

## 4. Responsive strategy

Greia uses cheap deterministic responsive geometry, consistent with ADR 0018 and ADR 0026.

Preferred platform behaviors:

1. derive dimensions from the live viewport;
2. use semantic regions (header/system chrome/content/footer) rather than absolute screen coordinates;
3. choose column/row counts automatically from available content space and minimum usable item dimensions rather than target-resolution checks;
4. reflow before shrinking;
5. reduce spacing/decorative scale before reducing readable text or hit targets;
6. switch automatically to fewer columns/rows and bounded scrolling/pagination when necessary;
7. cap growth on large displays so controls do not become absurdly large;
8. center or distribute bounded content regions when extra space exists;
9. preserve artwork aspect ratio with contain/crop policies appropriate to the asset rather than arbitrary x/y stretching;
10. keep layout calculations renderer-neutral where practical and renderer-specific drawing below them.

Do not introduce a general constraint solver, DOM/CSS clone or desktop widget framework merely to satisfy responsiveness.

## 5. No device-specific UI geometry

Hardware profiles may select supported display modes and hardware adapters. They must not select separate launcher/installer layouts such as `acer_layout`, `pi_layout`, `1080p_layout`, or model-name coordinate tables.

Responsive behavior is driven by viewport/capability facts, not hardware identity.

A narrow exception is allowed only when a physical form factor creates a genuine product capability difference that cannot be represented by viewport/input/capability data; such an exception requires explicit architecture review.

## 6. Small-screen degradation rules

When available space becomes constrained, the automatic layout system should degrade in this order:

1. reduce decorative whitespace and nonessential ornament;
2. reduce the number of simultaneously visible columns/rows;
3. use scrolling/pagination for collections;
4. wrap or shorten secondary explanatory copy where product semantics permit;
5. reduce bounded decorative icon/art size;
6. reduce text size only within documented readability limits.

Never solve a small screen by:

- clipping the only Back/Continue/Home action;
- overlapping hit targets;
- making text unreadably small;
- horizontally squashing text or icons;
- hiding essential state with no navigation path;
- requiring a mouse to reach content that keyboard/controller navigation cannot reach.

If a physically implausible mode is below Greia's minimum usable UI envelope, the display service should not advertise that mode as a normal usable choice. The UI must still fail visibly and safely rather than drawing destructive controls off-screen.

## 7. Large-screen behavior

Large/high-resolution displays must not simply scale the Acer UI until tiles and text become enormous.

The shared layout system uses bounded maximum sizes, sensible content widths, additional columns only when useful, and preserved visual hierarchy. Extra space may increase breathing room or visible collection capacity, but must not alter semantics.

## 8. Orientation and unusual aspect ratios

Greia's current reference hardware is landscape, but layout code must not assume a particular aspect ratio.

Portrait and unusually wide/tall test viewports are required engineering probes because they expose hidden fixed-coordinate assumptions. A product profile may later choose not to advertise an orientation on specific hardware, but shared UI code remains viewport-driven.

The existence of portrait stress tests does not mean designers must create a second portrait design; the same semantic layout must reflow through the shared platform policy.

## 9. Resolution changes at runtime

When the display mode or window size changes, Greia-owned surfaces must recompute dependent geometry on the next render/update boundary.

Size-dependent caches (scaled icons, shadows, fonts where size changes, pre-rendered surfaces) must be invalidated or keyed by size. Stale hit rectangles must not survive a layout change.

The operation must not leak surfaces, fonts, file descriptors, threads or unbounded cache entries through repeated resize cycles.

## 10. First-party Activity rule

First-party Activities are part of Greia and must obey the same requirement.

Activities must use Greia's shared responsive UI/layout primitives for ordinary interface composition rather than implementing their own per-resolution positioning systems. They consume the current Activity surface/content region and protected system-chrome geometry supplied by Greia.

Activity authors should not need to know the physical display resolution.

Activity-specific gameplay may choose a logical coordinate space internally, but it must map that logical space to the actual Activity viewport with preserved aspect ratio and correct input-coordinate mapping. This exception is for game-world coordinates, not for hand-authoring multiple UI layouts.

## 11. Parent HTML client

The Greia Parents HTML client must be responsive independently of the Greia device screen. It must remain usable on common phone, tablet and desktop browser widths and must not rely on the Greia display resolution.

Its authors likewise maintain one responsive semantic client layout rather than separate hand-positioned phone/tablet/desktop pages. Native browser layout mechanisms may implement that contract because the Parent HTML client is a Web surface; this does not change the lightweight native Greia UI architecture.

Parent-client responsiveness does not authorize heavyweight web dependencies or cloud runtime assets.

## 12. Acceptance model

Responsiveness is both a **property** and a **representative-resolution matrix**.

Automated geometry tests should exercise many generated viewport dimensions and assert invariants such as containment, non-overlap where required, valid focus targets and positive dimensions.

Tests must also verify that one semantic layout specification works across those viewports without per-resolution author branches.

Representative visual/interaction acceptance must include at least:

```text
640×480       constrained 4:3
800×600       common 4:3
1024×600      Greia legacy reference
1024×768      4:3
1280×720      16:9
1366×768      common laptop
1920×1080     full HD
2560×1440     high resolution
3840×2160     4K growth/capping probe
720×1280      portrait stress probe
1280×720 -> 800×600 -> 1920×1080 runtime resize sequence where supported
```

This matrix is not a whitelist. Passing only these exact dimensions does not satisfy the requirement if nearby/random dimensions break.

## 13. Required surfaces for acceptance

At minimum verify:

- installer every page, including Wi-Fi/password entry, confirmation, progress, error and completion;
- profile chooser and optional child-password entry;
- launcher root and each category;
- launcher with enough Activities to force scrolling/pagination;
- Activity-name labels and package-owned icons;
- platform Home/Back chrome;
- settings surfaces;
- Writing and Painting;
- at least one pointer/game-like Activity if present;
- dialogs/overlays and destructive confirmations;
- Greia Parents HTML at narrow phone, tablet and desktop widths.

## 14. Evidence boundary

A screenshot at one resolution is not proof of responsiveness.

A source unit test is not proof of physical readability.

A physical Acer PASS is not proof of arbitrary-resolution behavior.

Closure requires the combination of platform-owned automatic layout architecture, automated multi-size invariants, representative rendered interaction checks, and physical acceptance at the low-resource reference floor.

## 16. Implemented platform seams (2026-09-03 tranche)

The following source seams implement this requirement; normative architecture remains with ADR 0026 and ADR 0035:

- physical display facts via `DisplayMetrics` (raw facts only; unknown size explicit, never invented);
- suitability via `DisplayPolicy.phase0()` envelope comparison (no resolution whitelist; unknown fails open, provably-unsupported blocks destructive install);
- shared interactive minimums via `PhysicalUiPolicy.minimum_pixels` (bounded 8–320 px; floors minimums, never global scaling);
- single trusted-action floor (`TRUSTED_ACTION_MINIMUM_MM = 10.0`, defined once in `src/greia_launcher/system_chrome.py`) shared by navigation and profile chrome;
- pointer setup via `HardwareSettingsStore` (schema v2, tap-OFF) applied through the Legacy-X hardware-session controller; installer pointer preview and the Parent pointer tab share `SPEED_PRESETS` and go only through the `PointerSettingsController.apply_pointer_settings` seam with semantic settings (generic kind labels, never backend ids);
- metrics-vs-scaling rule: density may raise shared touch-target minimums only; it must not rescale layout, typography, or artwork globally.
- tap-default correction: platform policy (AGENTS.md) owns tap-to-click OFF; runtime/source had drifted and this tranche reconciled TOML, store defaults, installer copy, and Parent copy to OFF.
