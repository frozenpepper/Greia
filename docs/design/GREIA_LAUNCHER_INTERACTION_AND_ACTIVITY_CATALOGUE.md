# Greia Launcher Interaction and Activity Catalogue

**Status:** active design contract; collection-first/adaptive-discovery migration accepted but not fully implemented  
**Date:** 2026-08-20  
**Applies to:** child launcher, shared lightweight UI primitives, Activity manifests/packages, Parent Activity installation, child Activity discovery  
**Related:** ADR-0018 lightweight UI foundation; Greia visual style guide; Activity ecosystem architecture; `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`.

## Purpose

The launcher should feel alive, polished and child-friendly without becoming graphically heavy or architecturally special. Effects must therefore come from a small set of reusable, bounded primitives that Activities and other platform screens can use later.

This document defines that interaction layer, Activity catalogue/navigation metadata, package-owned icon contract, adaptive Collection hierarchy and Parent-installed Activity boundary.

The child-facing product requirements for collection-first discovery, adaptive depth, age/developmental suitability, difficulty and Parent per-child visibility live in `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`. This design document explains how those requirements fit the launcher architecture.

## Design principles

1. **Semantic UI first.** Selection, scrolling, Collections, launch state and adaptive depth are renderer-independent concepts.
2. **Cheap presentation.** Shadows and motion use bounded surfaces and sampled transforms rather than a retained scene graph or compositor.
3. **Visible-only work.** The launcher renders only the current scroll window.
4. **Input parity.** Pointer, keyboard and future controller/touch paths act on the same selection/navigation state.
5. **Feedback precedes latency.** A click/activation must create visible response before startup work can block perception.
6. **Presentation never owns authority.** Animation, ranking or filtering cannot grant package trust, permissions, storage access, focus authority or lifecycle state.
7. **Package identity is separate from presentation.** Launcher categories, discovery hints and icons are presentation metadata; launch identity remains the Activity ID and validated package registration.
8. **Educational metadata is not navigation metadata.** A skill/progression tag such as `fine_motor` must not automatically become permanent launcher chrome or another navigation level.
9. **Portable Activities are self-presenting.** An Activity may ship its own icon without adding an asset to the base OS.
10. **Every Activity remains identifiable without recognizing artwork.** The launcher always reserves readable space for the Activity name; icons complement names rather than replacing them.
11. **Collection depth remains visible.** Once a child enters a Collection or optional sub-Collection, its identity stays visible together with a local Back control.
12. **Home is Collection-first, not a giant Activity wall.** Primary child Collections are destinations rather than filter tabs over an `All` grid.
13. **Depth is adaptive and bounded.** Small Collections show Activities directly; larger Collections may introduce exactly one semantic sub-Collection layer when it materially simplifies discovery.
14. **Audience metadata informs discovery without becoming package authority.** Age/development and difficulty are separate facts; Parent explicit visibility policy wins over automatic recommendation.
15. **Live package discovery must rebuild authority before UI publication.** A newly installed tile is not launchable until runtime/permission/history/supervisor services have been rebuilt from the same validated registry set.

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

### Collection-card anatomy

Primary Collections should be stronger visual objects than filter controls. A Collection card/object may use a Greia-owned physical metaphor such as an art case, toy box, book, explorer bag, shelf or personal chest, provided the metaphor remains semantic and does not expose filesystem behavior.

A Collection presentation should include:

- a stable semantic icon/art identity;
- a localized title where text is useful;
- a large child-sized hit/focus target;
- clear selected/hovered/pressed state;
- optional bounded ambient character/art treatment where it does not obscure the choice or add unbounded animation cost.

The Collection object is presentation over Greia's semantic `Collection`, not a host directory.

### Hover and selection

A hovered or selected Activity or Collection tile:

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
7. on exit/failure, control returns to the same Collection/sub-Collection and nearest valid selection.

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

That projection is the correct architectural layer for:

- high-level Collection membership;
- optional future semantic discovery/grouping hints;
- per-child effective visibility projection;
- ranking/recommendation presentation;
- adaptive direct-vs-sub-Collection depth.

None of those presentation operations duplicate or mutate the underlying Activity registration.

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

`education.categories` continues to describe learning/skill context. It must not be overloaded merely to obtain launcher navigation.

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

- known high-level categories have a stable child-facing ordering (`Create`, `Play`, `Learn`, `Explore`, `My Greia`);
- each primary Collection has a stable semantic Greia icon/art identity as well as a title;
- one Activity may appear in multiple Collections;
- duplicate appearance never duplicates installation, progress or permissions;
- an Activity with no usable high-level category must remain recoverably discoverable through fallback/browse policy and must never be silently lost;
- Collection selection is presentation state only.

### Collection-first Home

The accepted target Home presentation shows the available **primary Collections**, not every Activity plus filter controls.

Conceptually:

```text
Greia Home

[ Create ]   [ Play ]
[ Learn  ]   [ Explore ]
[ My Greia ]
```

The actual renderer uses Greia semantic assets rather than literal emoji.

`All` may continue to exist internally because it is useful for catalogue fallback, tests, Parent/admin inventory and future search/browse. It is no longer the preferred child root concept.

This is a deliberate change from the current source presentation, which still initializes the launcher in `ALL_ACTIVITIES_ID` and presents category controls over the Activity catalogue. The source must be migrated before this target behavior can be called implemented.

### Collection hierarchy and local Back

Once a child enters a primary Collection, the Collection identity stays pinned/visible while its content scrolls.

A direct small Collection is conceptually:

```text
[ Back ]   [ Collection icon ]  Create

[ Activity ] [ Activity ] [ Activity ]
[ Activity ]
```

A large Collection may become:

```text
[ Back ]   [ Collection icon ]  Create

[ Drawing ] [ Writing ] [ Music ] [ Building ]
```

and then:

```text
[ Back ]   [ Sub-Collection icon ]  Drawing

[ Activity ] [ Activity ] [ Activity ]
```

The Back control here is **launcher-local navigation**, not ADR-0019 Activity system chrome. It moves one launcher Collection level toward Home. It does not stop a running Activity and must not be confused with Greia-owned Home/Back shown above Activity content.

Keyboard/controller/touch semantics must match the visible hierarchy. `Esc`/Backspace or the mapped Back action moves up one launcher Collection level; root behavior retains the appropriate profile/logout semantics.

### Adaptive depth policy

Adaptive depth is a platform projection decision, not package-defined folder structure.

Initial accepted policy from `CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`:

- 1–10 **effective visible** Activities in a primary Collection → show Activities directly;
- more than 10 effective visible Activities → evaluate whether one semantic sub-Collection layer materially improves discovery;
- do not create bad sub-Collections simply because the count crossed a threshold;
- if no coherent partition exists, retain direct bounded scrolling/paging;
- never exceed `Home → primary Collection → optional sub-Collection → Activity`.

A useful subdivision normally yields approximately 2–5 recognizable groups and avoids a dominant meaningless `Other` bucket.

The launcher should use stability/hysteresis so one install/remove does not continually change the child's navigation. The initial design target is to evaluate subdivision above 10 and avoid collapsing an adopted useful subdivision until the effective count falls to roughly 8 or lower. Exact constants/persistence are platform policy and may be tuned through child testing.

### Effective per-child catalogue

The count used for adaptive depth is not the raw number of installed packages.

Conceptually:

```text
validated Activity registry
    ↓
Parent per-child visibility / explicit Activity overrides
    ↓
profile audience/challenge discovery policy
    ↓
current child discovery view where applicable
    ↓
effective visible Activity set
    ↓
Collection projection and adaptive depth
```

This prevents a device with 20 installed Activities but only 6 visible to one child from receiving an unnecessary extra navigation level.

Filtering/ranking never changes package trust, registration or launch authority.

### Future semantic discovery hints

The current parser supports only high-level `[presentation].categories`.

A future manifest migration may add bounded presentation hints conceptually equivalent to:

```toml
[presentation]
categories = ["create", "learn"]
discovery_tags = ["drawing", "shapes"]
```

These hints allow `ActivityCatalogue`/platform policy to form useful optional sub-Collections when the effective catalogue is large enough. They do not directly command Greia to make a folder and do not define a filesystem path.

As of 2026-08-20, `discovery_tags` is a design target and **not a currently accepted parser field**.

### Age/development and difficulty metadata

Current source already exposes `ActivityManifest.difficulty`, parsed from:

```toml
[education]
difficulty = 1
```

and validated from 1 through 10.

Difficulty represents baseline challenge, **not age**.

The accepted target audience model adds optional developmental suitability independently, conceptually:

```toml
[education]
difficulty = 3
recommended_age_min = 5
recommended_age_max = 8
```

Open-ended tools may omit an upper bound.

Activities that genuinely scale challenge may eventually declare a supported range and adaptive behavior, conceptually:

```toml
[education]
difficulty = 3
difficulty_min = 1
difficulty_max = 7
adaptive_difficulty = true
```

These additional age/adaptive-difficulty fields are **not yet parsed by current source**. Exact names/bounds become source-owned when implementation lands.

Age/developmental suitability and difficulty must remain separate dimensions because an Activity can be age-appropriate but easy/hard, or difficult within a younger developmental target while still being too elementary in subject matter for an older child.

Missing age metadata must fail open for ordinary discovery: unknown does not mean unsuitable. Explicit Parent hide remains authoritative.

### Parent and child discovery policy

Parent management may eventually expose per-child policies such as:

```text
Show everything
Hide Activities probably too simple
Show recommended range only
Custom
```

with per-Activity `always show` / `always hide` overrides.

A child-facing discovery view may optionally offer icon-led equivalents of `For me`, `Easier`, `Harder` and `All`, but recommendation must not shame or grade the child.

The child profile does not need an exact date of birth. A coarse/approximate age or developmental stage and challenge preference are sufficient for this discovery purpose.

The current `ChildProfile` source does not yet contain these audience/challenge fields; this remains implementation work.

### Activity scrolling

A direct Activity Collection presents a bounded visible window. Column/row capacity adapts to available geometry and the collection becomes scrollable/paged when it exceeds visible capacity.

Supported navigation:

- arrows/controller direction move the semantic selection;
- moving beyond the visible window scrolls just enough to keep selection visible;
- mouse wheel advances by semantic rows;
- explicit up/down controls appear only when there is more content;
- switching Collection resets or restores selection/scroll state predictably.

Only the visible window is rendered. Installed Activity count therefore does not create an unbounded tile/widget set.

The current implementation uses two visible Activity rows and a width-derived column count; responsive-layout migration may evolve exact geometry while preserving bounded visible-only rendering.

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
- only visible Activity/Collection tiles are rendered;
- Collection header/Activity labels use cached font/icon paths and no per-frame disk discovery;
- adaptive projection is recomputed only on meaningful catalogue/profile/policy changes, not every frame;
- effects must degrade gracefully rather than delay input or Activity launch;
- no effect may trigger network, disk scan or package discovery every frame.

## Implementation migration status

As of 2026-08-20, source already provides useful foundations:

- semantic `Collection` in `greia_platform.ui_core`;
- `ActivityCatalogue` as a presentation projection;
- high-level launcher categories;
- one Activity in multiple categories;
- bounded scrolling;
- `education.difficulty` 1–10;
- Collection-first Home (`ui.portal.frame` / `CollectionFirstHomeMixin`) replacing normal `All` landing, accepted via Activity Simulator (`docs/testing/2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md`);
- Parent direction for later per-child Activity availability.

Source still needs migration for the remainder of the target:

- optional adaptive sub-Collections and hysteresis;
- future discovery-group metadata;
- age/developmental suitability fields;
- adaptive difficulty range metadata;
- profile audience/challenge preference;
- Parent visibility policy/API/UI;
- per-child effective-catalogue projection.

Do not describe those target items as implemented until source/tests/Parent client are updated and verified.

## Future extensions

The primitives are intentionally reusable for:

- profile cards;
- badge/reward popups;
- Parent-approved system dialogs;
- Activity SDK controls where appropriate;
- Collection transitions;
- subtle focus/selection effects in installer and setup screens;
- bounded recent/favorite/Continue shortcuts that obey the effective per-child catalogue.

Future additions should be concrete primitives justified by multiple callers. Do not grow this into a generic UI framework merely because another effect is desirable.