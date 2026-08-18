# Greia Launcher Interaction and Activity Catalogue

**Status:** active design contract  
**Date:** 2026-08-18  
**Applies to:** child launcher, shared lightweight UI primitives, Activity manifests/packages, Parent Activity installation  
**Related:** ADR-0018 lightweight UI foundation; Greia visual style guide; Activity ecosystem architecture.

## Purpose

The launcher should feel alive, polished and child-friendly without becoming graphically heavy or architecturally special. Effects must therefore come from a small set of reusable, bounded primitives that Activities and other platform screens can use later.

This document defines that interaction layer and the Activity catalogue model.

## Design principles

1. **Semantic UI first.** Selection, scrolling, categories and launch state are renderer-independent concepts.
2. **Cheap presentation.** Shadows and motion use bounded surfaces and sampled transforms rather than a retained scene graph or compositor.
3. **Visible-only work.** The launcher renders only the current scroll window.
4. **Input parity.** Pointer, keyboard and future controller/touch paths act on the same selection/navigation state.
5. **Feedback precedes latency.** A click/activation must create visible response before startup work can block perception.
6. **Presentation never owns authority.** Animation cannot grant package trust, permissions, storage access, focus authority or lifecycle state.
7. **Package identity is separate from presentation.** Categories and icons are manifest metadata; launch identity remains the Activity ID and validated package registration.
8. **Portable Activities are self-presenting.** An Activity may ship its own icon without adding an asset to the base OS.

## Shared primitive layers

### `greia_platform.ui_motion`

Defines renderer-neutral visual state and transform samples:

- `InteractionVisualState`
  - hovered
  - selected
  - pressed
  - launching
- `MotionSample`
  - scale
  - x/y offset
  - shadow lift
- `HoverMotion`
- `LaunchMotion`

These classes contain no Pygame objects, file access, input polling or lifecycle calls.

The launch flourish is intentionally short and bounded. Current defaults are approximately 420 ms with a small horizontal squiggle, upward bounce and mild scale. At the end it resolves exactly to the neutral transform so the handoff does not jump.

### `greia_platform.ui_scroll`

`ScrollModel` describes a bounded visible window over a collection. Selection is authoritative; scrolling exists to keep the selected item visible.

This is more appropriate for young children and keyboard/controller input than an unbounded desktop-style pixel scroller. Pointer-wheel input advances by semantic rows.

### `greia_platform.pygame_effects`

Pygame-only presentation helpers provide:

- shallow rounded card shadows;
- raised panels;
- transformed card rectangles;
- shadowed transparent icons;
- cacheable shadow/icon surfaces.

All caches used by the launcher are bounded. Expensive blur filters, per-frame full-screen alpha effects and unbounded transformed-surface caches are out of scope for the reference hardware floor.

## Launcher composition

`LauncherApplication` remains the lifecycle/security core. `GreiaLauncherPresentation` specializes child-facing presentation and navigation while reusing the authoritative profile/session/permission/runtime/supervisor paths.

The installed X session launches `greia_launcher.presentation`.

### Hover and selection

A hovered or selected Activity tile:

- lifts a few pixels;
- scales by only a few percent;
- strengthens its outline;
- keeps a shallow drop shadow.

The effect should be noticeable but not twitchy. Selection must still be obvious when no pointer exists.

### Activity launch sequence

1. user activates the selected Activity;
2. launcher immediately marks the tile as launching;
3. tile performs a short squiggle/bounce flourish;
4. the existing full-screen starting overlay takes over;
5. the authoritative Activity launch/sandbox/runtime path runs;
6. display/focus handoff follows the platform lifecycle contract;
7. on exit/failure, control returns to the same category and nearest valid selection.

No launch animation may hide a validation failure indefinitely or continue as an unbounded loop.

## Activity catalogue

The Activity registry remains the source of package truth. `ActivityCatalogue` is only a projection for navigation.

### Categories

Every manifest already supports:

```toml
categories = ["creative", "drawing"]
```

Rules:

- `All` is always available and appears first;
- one Activity may appear in multiple categories;
- duplicate appearance never duplicates installation, progress or permissions;
- category IDs are normalized for matching but remain semantic metadata;
- category display vocabulary/localization should ultimately be platform-owned;
- an Activity with no category still appears under `All`.

The current launcher shows category pills/tabs near the top of the Activity screen. `Tab` cycles categories; pointer activation chooses one. Future controller/touch bindings must map to the same category state.

### Scrolling

The launcher currently presents two visible Activity rows. Column count adapts to available width. The collection becomes scrollable when it exceeds visible capacity.

Supported navigation:

- arrows move the semantic selection;
- moving beyond the visible window scrolls just enough to keep selection visible;
- mouse wheel advances by rows;
- explicit up/down controls appear only when there is more content;
- switching category resets selection and scroll window predictably.

This must remain bounded regardless of the number of installed Activities.

## Activity icons

### Built-in catalogue icon

Existing Activities remain valid:

```toml
icon = "paint"
```

The ID resolves through Greia's platform asset catalogue.

### Package-owned icon

A portable Activity may ship its own icon:

```toml
icon = "package:assets/icon.png"
```

Current allowed formats are PNG and WebP.

The resolver requires:

- a relative path;
- no `.`/`..` traversal;
- bounded length and depth;
- resolution strictly inside the validated Activity package root;
- a regular existing file.

The launcher decorates the resulting icon with the same shallow shadow used for built-ins, so package-provided artwork still belongs visually to Greia without being redrawn by the OS.

Recommended authoring target:

- square source image;
- transparent background where appropriate;
- clear silhouette at small sizes;
- important details kept away from outer 8–10% of the canvas;
- no text required to identify the Activity.

## Parent-installed Activities

Parent-installed packages are deliberately a separate source:

- trust: `PARENT_TRUSTED_UNSIGNED`;
- source ID: `greia-parent-package-service`;
- active root: `/var/lib/greia-os/activity-packages/active` by default.

The launcher composes this source with built-ins and any explicit developer source through the normal `ActivityRegistry`. It then rebuilds the same runtime/permission/history/supervisor services from the combined validated Activity set.

Presentation must never scan arbitrary Parent-upload directories directly.

## `.greiaactivity` packaging convention

The first implemented new-install package format is a bounded ZIP archive named with the `.greiaactivity` suffix. The normal Activity package root is the archive root:

```text
my-activity.greiaactivity
├── activity.toml
├── src/...
└── assets/
    └── icon.png
```

Do **not** add another arbitrary top-level wrapper directory.

Installation is performed by the platform package service, not by copying this directory from the Parent UI.

## Parent install availability

The existence of the endpoint does not imply release availability.

`activities.install` remains capability-gated. Because the current Parent transport is provisional HTTP, ordinary/release systems keep executable package installation disabled. Explicit developer/owner-enabled systems can exercise the complete new-install path for development and acceptance.

A production enablement decision requires the secure Parent transport/pairing work plus the remaining R10 update/signature/revocation/rollback policies.

## Performance constraints

The launcher must remain comfortable on the legacy 1024×600/i686 reference floor:

- 30 Hz is an acceptable UI target for these subtle effects;
- motion calculations allocate no retained animation objects per frame;
- icon/font/shadow caches are bounded;
- only visible tiles are rendered;
- effects must degrade gracefully rather than delay input or Activity launch;
- no effect may trigger network, disk scan or package discovery every frame.

## Future extensions

The primitives are intentionally reusable for:

- profile cards;
- badge/reward popups;
- Parent-approved system dialogs;
- Activity SDK controls where appropriate;
- category transitions;
- subtle focus/selection effects in installer and setup screens.

Future additions should be concrete primitives justified by multiple callers. Do not grow this into a generic UI framework merely because another effect is desirable.
