# Greia Launcher Interaction and Activity Catalogue

**Status:** active design contract  
**Date:** 2026-08-18  
**Applies to:** child launcher, shared lightweight UI primitives, Activity manifests/packages, Parent Activity installation  
**Related:** ADR-0018 lightweight UI foundation; Greia visual style guide; Activity ecosystem architecture.

## Purpose

The launcher should feel alive, polished and child-friendly without becoming graphically heavy or architecturally special. Effects must therefore come from a small set of reusable, bounded primitives that Activities and other platform screens can use later.

This document defines that interaction layer, Activity catalogue/navigation metadata, package-owned icon contract and Parent-installed Activity boundary.

## Design principles

1. **Semantic UI first.** Selection, scrolling, categories and launch state are renderer-independent concepts.
2. **Cheap presentation.** Shadows and motion use bounded surfaces and sampled transforms rather than a retained scene graph or compositor.
3. **Visible-only work.** The launcher renders only the current scroll window.
4. **Input parity.** Pointer, keyboard and future controller/touch paths act on the same selection/navigation state.
5. **Feedback precedes latency.** A click/activation must create visible response before startup work can block perception.
6. **Presentation never owns authority.** Animation cannot grant package trust, permissions, storage access, focus authority or lifecycle state.
7. **Package identity is separate from presentation.** Launcher categories and icons are manifest metadata; launch identity remains the Activity ID and validated package registration.
8. **Educational metadata is not navigation metadata.** A skill/progression tag such as `fine_motor` must not automatically become permanent launcher chrome for newly authored packages.
9. **Portable Activities are self-presenting.** An Activity may ship its own icon without adding an asset to the base OS.
10. **Every Activity remains identifiable without recognizing artwork.** The launcher always reserves readable space for the Activity name; icons complement names rather than replacing them.
11. **Category depth remains visible.** Once a child enters a category, the category identity stays pinned at the top together with a local Back-to-All control.
12. **Live package discovery must rebuild authority before UI publication.** A newly installed tile is not launchable until runtime/permission/history/supervisor services have been rebuilt from the same validated registry set.

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

### `greia_platform.activity_assets`

Package-owned presentation asset validation is platform-owned rather than launcher-owned. The installer and launcher therefore use the same containment and decode-bound rules for Activity icons. A package with a broken `package:` icon path or unreasonable image dimensions is rejected before activation instead of being accepted and failing only when drawn.

## Launcher composition

`LauncherApplication` remains the lifecycle/security core. `GreiaLauncherPresentation` specializes child-facing presentation and navigation while reusing the authoritative profile/session/permission/runtime/supervisor paths.

The installed X session launches `greia_launcher.presentation`.

### Activity tile anatomy

An Activity tile is not just an icon in a box. It has two explicit visual regions:

1. an artwork region for the Activity icon;
2. a reserved name band at the bottom.

The name band is part of the tile contract. It must remain readable even when an Activity ships unfamiliar artwork. Text fitting reduces font size and, only as a final fallback, shortens with an ellipsis; glyphs must not be geometrically squashed to fit.

The icon remains visually dominant, but layout must leave enough vertical space that the name never appears accidentally clipped or absent.

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

### Live package install while launcher is running

The launcher periodically observes the registry discovery token. When Parent installation changes the active package tree:

1. the registry validates the complete combined built-in/developer/Parent source set;
2. the launcher holds the existing catalogue as last-known-good state;
3. runtime manager, permission broker, storage/history/progression composition and `ActivitySupervisor` are rebuilt against the newly validated Activity set;
4. only after that succeeds is the new catalogue published to the child UI;
5. if validation/composition fails, the current catalogue/runtime pair remains authoritative and the launcher shows its error indicator.

This prevents a visually present Activity from being backed by stale launch authority.

## Activity catalogue

The Activity registry remains the source of package truth. `ActivityCatalogue` is only a projection for navigation.

### Launcher navigation categories

New/updated manifests should declare child-facing navigation categories explicitly:

```toml
[presentation]
categories = ["create", "learn"]
```

These are deliberately separate from the educational taxonomy:

```toml
[education]
categories = ["creativity", "geometry", "fine_motor"]
```

`education.categories` continues to describe learning/skill context. It must not be overloaded merely to obtain a launcher tab.

Current recommended high-level launcher vocabulary is:

- `create`
- `play`
- `learn`
- `explore`
- `my_greia`

The parser does not freeze this list as a permanent allowlist, but launcher category IDs must be bounded, lower-case platform-style identifiers and a package may declare at most four. A later localized category vocabulary may become platform-owned data without changing Activity identity.

For compatibility, an older API 0.1 package with no `[presentation]` table temporarily falls back to its `education.categories`. This is compatibility behavior, not the recommended authoring pattern.

Current built-ins intentionally demonstrate a compact information architecture:

- Painting → `create`
- Shape Garden → `create`, `learn`
- Writing → `create`, `learn`
- Workshop Settings → `my_greia`

Rules:

- `All` is always available and is the category landing/root view;
- known high-level categories have a stable child-facing ordering (`Create`, `Play`, `Learn`, `Explore`, `My Greia`);
- each category has a stable semantic Greia icon as well as a title;
- one Activity may appear in multiple categories;
- duplicate appearance never duplicates installation, progress or permissions;
- an Activity with no usable category still appears under `All`;
- category selection is presentation state only.

### Category hierarchy and local Back

The top-level `All` view presents the available categories as icon-led category controls. Once a child enters a category, the top row changes from the category chooser to a persistent category header:

```text
[ Back ]   [ Category icon ]  Category name
```

The header stays fixed while Activity content scrolls. This gives the child a continuous visual answer to “where am I?” and avoids requiring them to infer category state from a highlighted tab among many choices.

The Back control here is **launcher-local navigation**, not ADR-0019 Activity system chrome. It returns to the launcher `All`/category landing. It does not stop a running Activity and must not be confused with Greia-owned Home/Back shown above Activity content.

Keyboard semantics match the visual hierarchy:

- `Esc` or `Backspace` inside a category returns to `All`;
- `Esc` from `All` retains the existing profile/logout behavior;
- `Tab` can still cycle categories for keyboard development/testing;
- future controller/touch bindings must act on the same category state.

### Activity scrolling

The launcher presents two visible Activity rows. Column count adapts to available width. The collection becomes scrollable when it exceeds visible capacity.

Supported navigation:

- arrows move the semantic selection;
- moving beyond the visible window scrolls just enough to keep selection visible;
- mouse wheel advances by rows;
- explicit up/down controls appear only when there is more content;
- switching category resets selection and scroll window predictably.

Only the visible window is rendered. Installed Activity count therefore does not create an unbounded tile/widget set.

## Activity icons

### Built-in catalogue icon

Existing Activities remain valid:

```toml
[activity]
icon = "palette"
```

The ID resolves through Greia's platform asset catalogue.

### Package-owned icon

A portable Activity may ship its own icon:

```toml
[activity]
icon = "package:assets/icon.png"
```

Current allowed formats are PNG and WebP.

The platform resolver requires:

- a relative path;
- no `.`/`..` escape;
- bounded path length and depth;
- resolution strictly inside the validated Activity package root;
- a regular existing file;
- a bounded file size;
- a valid supported image header;
- bounded decode dimensions (currently at most 1024×1024 for launcher package icons).

For Parent-installed packages the reference is validated during package installation. The launcher then loads exactly that validated package asset and decorates it with the same shallow shadow used for built-ins.

Recommended authoring target:

- square source image;
- transparent background where appropriate;
- clear silhouette at small sizes;
- important details kept away from outer 8–10% of the canvas;
- no text required inside the artwork, because the launcher always renders the Activity name separately.

## Parent-installed Activities

Parent-installed packages are deliberately a separate source:

- trust: `PARENT_TRUSTED_UNSIGNED`;
- source ID: `greia-parent-package-service`;
- active root: `/var/lib/greia-os/activity-packages/active` by default.

The launcher composes this source with built-ins and any explicit developer source through the normal `ActivityRegistry`. It rebuilds the same runtime/permission/history/supervisor composition before publishing registry changes.

The filesystem boundary is intentional:

- `/var/lib/greia-os` is traversable by the launcher;
- `/var/lib/greia-os/activity-packages/active` is read-only/traversable;
- immutable versions, staging and receipts remain Parent-service-private;
- sensitive Parent credentials remain protected by their own file/directory permissions.

Presentation must never scan arbitrary Parent-upload directories directly.

## `.greiaactivity` packaging convention

The first implemented **new-install** package format is a bounded ZIP archive named with the `.greiaactivity` suffix. The normal Activity package root is the archive root:

```text
my-activity.greiaactivity
├── activity.toml
├── main.py
└── assets/
    └── icon.png
```

Do **not** add another arbitrary top-level wrapper directory.

The installer rejects archive traversal, hidden/absolute/backslash paths, portable duplicate paths, symlinks, special files, encrypted entries, unsafe compression, excessive entry count and excessive expanded size. The extracted tree is then validated through the normal `ActivityRegistry` and platform Activity-asset checks.

### Install transaction

The current new-install service uses:

1. process-wide serialization through a private `0600` lock file under the package state root (plus an in-process lock to avoid redundant local contenders);
2. private staging;
3. full registry/asset validation;
4. digest-addressed read-only immutable version storage;
5. a prepared read-only activation tree;
6. audit receipt preparation;
7. atomic rename of the activation tree into the Parent Activity source as the commit point.

If receipt preparation fails, no executable Activity becomes visible. An interrupted attempt may leave an immutable version or orphan pre-commit receipt, neither of which is launch-authoritative; retries verify the immutable digest before reuse.

The process-wide lock uses `flock` on `.install.lock` in the authoritative package store, rejects a non-regular lock target, and fixes its mode to `0600`. Therefore two `ActivityPackageService` instances/processes sharing the same local Greia package store cannot race receipt and activation state merely because HTTP/process composition changes later. Any future move to a non-local/distributed package store would require a storage-appropriate equivalent rather than assuming local `flock` semantics.

Existing Activity IDs are deliberately rejected. This tranche does **not** pretend that update, removal, rollback-selection, signature/revocation or curated-store policy is complete.

## Parent install availability

The existence of the endpoint does not imply release availability.

`POST /api/v1/activities/install` is protocol-defined, but `activities.install` remains capability-gated. Because the current Parent transport is provisional HTTP, ordinary/release systems keep executable package installation disabled. Explicit developer/owner-enabled systems can exercise the complete new-install path for development and acceptance.

The external HTML Parent client asks the API index before showing the upload form. It sends the package bytes directly rather than base64/JSON wrapping them, applies the same 32 MiB request ceiling for immediate feedback, reports typed rejection messages and refreshes the Activity list after success.

A production enablement decision requires secure Parent transport/pairing plus the remaining R10 update/signature/revocation/rollback policies.

## Performance constraints

The launcher must remain comfortable on the legacy 1024×600/i686 reference floor:

- 30 Hz is an acceptable UI target for these subtle effects;
- motion calculations allocate no retained animation objects per frame;
- icon/font/shadow caches are bounded;
- only visible Activity tiles are rendered;
- category header/Activity labels use existing cached font/icon paths and no per-frame disk discovery;
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
