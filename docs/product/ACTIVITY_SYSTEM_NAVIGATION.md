# Greia Activity System Navigation

**Status:** ACCEPTED product requirement  
**Date:** 2026-08-15  
**Applies to:** every child-facing Activity runtime, including first-party Activities

## Purpose

Young children need one stable escape route from every Activity. Greia therefore provides a tiny, consistent system-navigation area that belongs to the platform rather than to Activity code.

The child should be able to learn one physical rule and reuse it everywhere:

> The Greia Home control always takes me back to Greia.

This is a safety, accessibility, learnability and platform-consistency requirement.

## Mandatory Home control

Every running child-facing Activity must have a Greia-owned **Home** control that:

- is always present while the Activity is visible;
- uses the same Greia graphic and placement across runtimes and Activities;
- has a child-sized hit target even though the visible glyph is small and unobtrusive;
- requests graceful Activity shutdown through the platform lifecycle;
- cannot be hidden, moved, recolored, resized, covered, disabled or replaced by Activity code;
- cannot have its input intercepted or vetoed by Activity code;
- still returns to Greia when an Activity hangs or refuses graceful shutdown, using the platform's bounded forced-return path.

Home ends the current Activity and returns to the Greia Shell surface it was launched from: the Collection page (e.g. a theme folder such as the Sea folder) when it was launched from one, otherwise the child's Home surface. (Owner decision 2026-10-17: keep the launch Collection, so a child can pick a related Activity straight away.)

An Activity may provide its own in-content exit or navigation controls, but those never replace the Greia Home control.

## Optional Greia Back control

Greia may show a **Back** control beside Home when the Shell has a meaningful previous Greia navigation context.

Back:

- is platform-owned under the same protection rules as Home;
- ends the Activity and returns to the Greia screen/Collection from which it was launched;
- is absent when no distinct previous Greia context exists;
- is not browser history for Web Activities;
- is not an Activity-defined internal-back operation;
- cannot be enabled merely because an Activity requests it.

Activities remain free to implement their own internal navigation within their content area.

## Protected region

Greia reserves a small fixed corner region for system navigation. The complete Home+Back footprint remains reserved even when Back is hidden, so Activity layout does not jump when Greia navigation context changes.

The current renderer-neutral geometry is owned by:

```text
src/greia_platform/system_chrome.py
```

At the 1024×600 reference size, the visible symbol is deliberately smaller than its approximately child-sized 60 px hit target. Exact scaling is source-owned and bounded.

Activity authors should avoid placing essential content in the protected region. They do not receive authority over the region.

## Controller system input

ADR 0020 defines standard Activity input/controller semantics. System navigation remains a higher-trust layer.

Where a supported controller reliably exposes a dedicated **Guide/system** control, Greia reserves that control for platform use; it is never delivered as an ordinary Activity action. The intended role is a hardware route to the same Greia Home semantics, subject to backend/hardware acceptance.

A fallback multi-button Home chord may be selected later for controllers without a reliable Guide control, but no chord is frozen until child testing demonstrates that accidental activation is acceptably rare. Activities must not claim potential system chords for essential gameplay.

## Runtime neutrality

The system navigation layer sits above Activity runtimes:

```text
Greia display/session/input owner
├── trusted Greia system chrome + protected pointer/touch/controller input
└── Activity surface
    ├── Python/Pygame
    ├── Web/HTML
    └── future runtimes
```

Python and Web Activities do not draw the Greia Home/Back controls themselves. A future Web bridge therefore does not inject a removable DOM button and JavaScript does not receive protected-region or reserved-controller system input.

## Display/input acceptance requirement

A production display/session/input backend is conformant only if it can preserve trusted Greia system chrome above the Activity surface and route protected system input to Greia before Activity input dispatch.

A backend that gives an Activity exclusive uncontested framebuffer/input ownership with no trusted overlay/system-input path is not sufficient for production, even if raw scanout itself works.

This requirement is part of R7 display/session architecture selection and is one reason a minimal Greia-owned compositor/session broker may be justified. It does **not** authorize a desktop environment or general-purpose window manager.

## Failure behavior

If Greia cannot provide or preserve mandatory Home chrome for a production Activity session, the platform must fail closed rather than silently launch an Activity without the escape affordance.

The current provisional Xorg path is not certified against this invariant until a trusted system-chrome/input host is implemented and executed. Source contracts alone are not runtime evidence.

## Acceptance criteria

For each supported runtime/backend combination, verify that:

1. Home is visible at the canonical location over arbitrary Activity content.
2. The Activity cannot cover or restyle Home.
3. Pointer/touch inside Home is consumed by Greia and not delivered to the Activity.
4. A reserved controller Guide/system input, when supported by the hardware/backend, is consumed by Greia and not delivered to Activity content.
5. Home requests graceful stop and returns to the Shell surface it was launched from (Collection or Home).
6. An uncooperative/frozen Activity is forcibly returned after the platform deadline.
7. Back appears only when Greia has a distinct launch origin and returns there.
8. Web content cannot intercept the system controls or turn Back into browser history.
9. Python content cannot intercept the system controls through Pygame input.
10. First-party Activities receive no exemption.
11. The controls remain usable at 1024×600 and on the Acer resource floor.
