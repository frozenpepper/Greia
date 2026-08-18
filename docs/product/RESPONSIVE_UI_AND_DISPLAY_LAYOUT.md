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

## 3. Responsive strategy

Greia uses cheap deterministic responsive geometry, consistent with ADR 0018.

Preferred techniques:

1. derive dimensions from the live viewport;
2. use semantic regions (header/system chrome/content/footer) rather than absolute screen coordinates;
3. choose column/row counts from available content space and minimum usable item dimensions rather than device-name checks;
4. reflow before shrinking;
5. reduce spacing/decorative scale before reducing readable text or hit targets;
6. switch to fewer columns/rows and use bounded scrolling/pagination when necessary;
7. cap growth on large displays so controls do not become absurdly large;
8. center or distribute bounded content regions when extra space exists;
9. preserve artwork aspect ratio with contain/crop policies appropriate to the asset rather than arbitrary x/y stretching;
10. keep all calculations renderer-neutral where practical and renderer-specific drawing below them.

Do not introduce a general constraint solver, DOM/CSS clone or desktop widget framework merely to satisfy responsiveness.

## 4. No device-specific UI geometry

Hardware profiles may select supported display modes and hardware adapters. They must not select separate launcher/installer layouts such as `acer_layout`, `pi_layout`, `1080p_layout`, or model-name coordinate tables.

Responsive behavior is driven by viewport/capability facts, not hardware identity.

A narrow exception is allowed only when a physical form factor creates a genuine product capability difference that cannot be represented by viewport/input/capability data; such an exception requires explicit architecture review.

## 5. Small-screen degradation rules

When available space becomes constrained, the order of degradation is:

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

## 6. Large-screen behavior

Large/high-resolution displays must not simply scale the Acer UI until tiles and text become enormous.

Use bounded maximum sizes, sensible content widths, additional columns only when useful, and preserved visual hierarchy. Extra space may increase breathing room or visible collection capacity, but must not alter semantics.

## 7. Orientation and unusual aspect ratios

Greia's current reference hardware is landscape, but layout code must not assume a particular aspect ratio.

Portrait and unusually wide/tall test viewports are required engineering probes because they expose hidden fixed-coordinate assumptions. A product profile may later choose not to advertise an orientation on specific hardware, but shared UI code remains viewport-driven.

## 8. Resolution changes at runtime

When the display mode or window size changes, Greia-owned surfaces must recompute dependent geometry on the next render/update boundary.

Size-dependent caches (scaled icons, shadows, fonts where size changes, pre-rendered surfaces) must be invalidated or keyed by size. Stale hit rectangles must not survive a layout change.

The operation must not leak surfaces, fonts, file descriptors, threads or unbounded cache entries through repeated resize cycles.

## 9. First-party Activity rule

First-party Activities are part of Greia and must obey the same requirement.

Activities must use the current Activity surface size and protected system-chrome/content geometry supplied by Greia. They must not assume `1024×600`, desktop window chrome, or unrestricted access to the full physical framebuffer.

Activity-specific gameplay may choose a logical coordinate space internally, but it must map that logical space to the actual Activity viewport with preserved aspect ratio and correct input-coordinate mapping.

## 10. Parent HTML client

The Greia Parents HTML client must be responsive independently of the Greia device screen. It must remain usable on common phone, tablet and desktop browser widths and must not rely on the Greia display resolution.

Parent-client responsiveness does not authorize heavyweight web dependencies or cloud runtime assets.

## 11. Acceptance model

Responsiveness is both a **property** and a **representative-resolution matrix**.

Automated geometry tests should exercise many generated viewport dimensions and assert invariants such as containment, non-overlap where required, valid focus targets and positive dimensions.

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

## 12. Required surfaces for acceptance

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

## 13. Evidence boundary

A screenshot at one resolution is not proof of responsiveness.

A source unit test is not proof of physical readability.

A physical Acer PASS is not proof of arbitrary-resolution behavior.

Closure requires the combination of viewport-driven source architecture, automated multi-size invariants, representative rendered interaction checks, and physical acceptance at the low-resource reference floor.
