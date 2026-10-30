# Greia Launcher Interaction and Activity Catalogue

**Status:** active design contract; Collection-first Home implemented, bounded-primary-vocabulary correction pending simulator acceptance, adaptive discovery not yet implemented  
**Date:** 2026-08-21  
**Applies to:** child launcher, shared lightweight UI primitives, Activity manifests/packages, Parent Activity installation, child Activity discovery  
**Related:** ADR-0018 lightweight UI foundation; Greia visual style guide; Activity ecosystem architecture; `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`.

## Purpose

The launcher should feel alive, polished and child-friendly without becoming graphically heavy or architecturally special. Effects must come from a small set of reusable, bounded primitives that Activities and other platform screens can reuse later.

This document defines the interaction layer, Activity catalogue/navigation metadata, package-owned icon contract, Collection-first hierarchy, future adaptive grouping and Parent-installed Activity boundary.

The child-facing product authority is `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`. This document explains how those requirements fit the launcher architecture and current source.

## Design principles

1. **Semantic UI first.** Selection, scrolling, Collections, launch state and adaptive depth are renderer-independent concepts.
2. **Cheap presentation.** Shadows and motion use bounded surfaces and sampled transforms rather than a retained scene graph/compositor.
3. **Visible-only work.** The launcher renders only the current visible window.
4. **Input parity.** Pointer, keyboard and future controller/touch paths act on the same semantic navigation state.
5. **Feedback precedes latency.** Activation creates visible response before startup work can block perception.
6. **Presentation never owns authority.** Animation, ranking/filtering or artwork cannot grant package trust, permissions, storage access, focus authority or lifecycle state.
7. **Package identity is separate from presentation.** Collection membership, future discovery hints and icons are presentation metadata; launch identity remains Activity ID + validated registration.
8. **Educational metadata is not navigation metadata.** Learning/skill taxonomy does not automatically become launcher chrome or hierarchy.
9. **Portable Activities are self-presenting.** An Activity may ship its own icon without modifying the base OS asset set.
10. **Every Activity stays identifiable without recognizing art.** Readable Activity names remain reserved in the tile contract.
11. **Collection depth remains visible.** Once inside a Collection/sub-Collection, identity and local Back remain clear.
12. **Home is Collection-first.** Normal child Home is not an `All` Activity wall with filter tabs.
13. **Primary Home vocabulary is platform-owned.** Package metadata can place Activities into known primary destinations but cannot manufacture arbitrary root destinations.
14. **Unknown metadata fails open without proliferating Home.** Otherwise-orphaned valid Activities use one bounded platform Browse/More recovery Collection.
15. **Depth is adaptive and bounded.** Small Collections show Activities directly; large Collections may gain exactly one semantic sub-Collection layer only when it materially helps.
16. **Audience metadata informs discovery without becoming package authority.** Age/development and difficulty are independent; Parent explicit policy wins.
17. **Live package discovery rebuilds authority before publication.** A new tile is not launchable until runtime/permission/history/supervisor services match the same validated registry set.

## Shared primitive layers

### `greia_platform.ui_motion`

Renderer-neutral visual state and transform samples:

- `InteractionVisualState`: hovered, selected, pressed, launching;
- `MotionSample`: scale, x/y offset, shadow lift;
- `HoverMotion`;
- `LaunchMotion`.

These classes contain no Pygame objects, file access, input polling or lifecycle calls. The launch flourish is short and bounded (currently approximately 420 ms), resolving exactly to neutral at handoff.

### `greia_platform.ui_scroll`

`ScrollModel` describes a bounded visible window over a Collection. Selection is authoritative; scrolling exists to keep selection visible. This suits young-child keyboard/controller navigation better than unbounded desktop-style pixel scrolling.

### `greia_platform.pygame_effects`

Pygame-only helpers provide shallow shadows, raised panels, transformed rectangles and cacheable decorated icons. Caches remain bounded; expensive blur pipelines, per-frame full-screen effects and unbounded transformed-surface caches are out of scope for the reference hardware floor.

### `greia_platform.activity_assets`

Package-owned presentation asset validation is platform-owned so installer and launcher share containment/decode bounds. Broken or unreasonable package icon references are rejected before activation instead of failing only while drawing.

## Launcher composition

`LauncherApplication` remains the lifecycle/security core. `GreiaLauncherPresentation` owns richer child-facing presentation/navigation while reusing authoritative profile/session/permission/runtime/supervisor paths. `GreiaChildShell` composes accepted shared visual mixins and the Collection-first Home presentation without taking lifecycle authority away from the base launcher.

Current presentation owners include:

```text
src/greia_launcher/catalogue_view.py
src/greia_launcher/presentation.py
src/greia_launcher/collection_home_presentation.py
src/greia_launcher/shared_ui_presentation.py
src/greia_launcher/profile_chrome_presentation.py
src/greia_launcher/feedback_presentation.py
src/greia_launcher/navigation_chrome_presentation.py
src/greia_launcher/child_shell.py
```

### Activity tile anatomy

An Activity tile has two explicit visual regions:

1. **Artwork/icon region**: contain-fitted in a square frame preserving original aspect ratio with **10–12% safe padding** around artwork, topped with soft launcher shadow treatment.
2. **Reserved readable name band**: supports **two-line centered presentation** (max 2 visible lines, word-aware wrapping with safe Unicode grapheme cluster fallback). A defensive display cap of **48 grapheme clusters** is enforced before card ellipsis (`…`).

### Hover, focus, and full-title disclosure

Hovered/selected Activities and Collections use a small lift/scale and stronger emphasis.

Additionally, hovering with a pointer or selecting via keyboard discloses the **full uncapped localized title** in a small, Greia-native floating callout pill. The disclosure pill is bounded to the visible screen area and strictly avoids overlapping the top-left Home/Profile control region. Static tile surface caches remain separate and are never poisoned by dynamic disclosure state.

### Activity launch sequence

1. child activates selected Activity;
2. launcher immediately marks it launching;
3. short bounded flourish runs;
4. full-screen starting overlay takes over;
5. authoritative launch/sandbox/runtime path runs;
6. display/focus handoff follows lifecycle contract;
7. exit/failure returns to the originating Collection/sub-Collection and nearest valid selection.

No launch animation may hide a validation failure indefinitely.

### Live package install while launcher is running

When the registry discovery token changes:

1. validate the complete built-in/developer/Parent source set;
2. keep current catalogue as last-known-good;
3. rebuild runtime manager, permission broker, storage/history/progression composition and `ActivitySupervisor` against the same validated set;
4. publish the new catalogue only after composition succeeds;
5. on failure keep the old catalogue/runtime pair authoritative and show bounded error feedback.

This prevents a visible Activity from being backed by stale launch authority.

# Activity catalogue

The Activity registry remains package truth. `ActivityCatalogue` is only a navigation projection.

It is the correct layer for:

- primary Collection membership;
- bounded Browse/More recoverability;
- future semantic discovery/grouping hints;
- future per-child effective visibility;
- future ranking/recommendation;
- future adaptive direct-vs-sub-Collection depth.

None of these operations duplicates or mutates registration/package state.

## Launcher navigation categories

New/updated manifests declare child-facing primary membership explicitly:

```toml
[presentation]
categories = ["create", "learn"]
```

This is separate from educational taxonomy:

```toml
[education]
categories = ["creativity", "geometry", "fine_motor"]
```

The current platform-owned primary child vocabulary is:

```text
create
play
learn
explore
my_greia
```

The manifest parser remains tolerant of other bounded lower-case identifiers for compatibility/migration and currently allows at most four presentation categories, but **parser acceptance is not Home authority**. `ActivityCatalogue` recognizes the platform primary vocabulary for normal child navigation. Arbitrary package values do not become Collections or root portals.

For an older API 0.1 package with no `[presentation]` table, compatibility may inspect `education.categories`; only values matching recognized primary IDs can become primary destinations. Otherwise the Activity remains recoverable through Browse/More.

Current rules:

- recognized primary Collections have stable order: Create, Play, Learn, Explore, My Greia;
- each has stable semantic Greia icon/art identity;
- one Activity may appear in several recognized primary Collections;
- duplicate presentation never duplicates package/progress/permissions/storage;
- arbitrary category values do not proliferate Home;
- a valid Activity with no recognized primary destination must not be silently lost;
- platform-owned `browse` provides the bounded recovery destination (`Altro` / `More`) only when needed;
- `browse` is recovery policy, not package-owned taxonomy;
- `All` remains internal/admin/fallback catalogue projection, not normal child Home.

The Clinic correction illustrates the taxonomy split:

```toml
[presentation]
categories = ["play", "learn"]

[education]
categories = ["empathy", "caregiving", "hygiene_and_health"]
```

Caregiving remains educational meaning without creating a permanent `Care` Home portal.

## Collection-first Home

Collection-first Home is implemented and accepted at Activity Simulator scope through `CollectionFirstHomeMixin` and `ui.portal.frame/default`.

Normal child flow:

```text
profile
  → Greia Home
    → primary Collection
      → Activity
```

The previous `All + filter row` remains historical/compatibility presentation, not the normal Home information architecture.

Current accepted simulator evidence covers:

- Collection portals instead of the All-Activity wall;
- keyboard/pointer Home navigation;
- Collection entry/local Back/root Back;
- Activity launch + return to originating Collection;
- multi-membership projection;
- corrupt-portal fail-soft rendering without reverting the IA;
- six responsive target rows;
- simulator frame sanity.

The first accepted run exposed an extra top-level `Care` portal because arbitrary package categories were still projected as Collections. The bounded-primary-vocabulary source correction is now implemented and awaits its dedicated simulator gate:

```text
2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md (archived; see git history)
```

Until that gate passes, do not claim simulator acceptance for the primary-vocabulary/More correction itself.

## Collection hierarchy and local Back

A direct small Collection:

```text
[ Back ]   [ Collection identity ]

[ Activity ] [ Activity ] [ Activity ]
```

Future large coherent Collection:

```text
[ Back ]   [ Collection identity ]

[ Drawing ] [ Writing ] [ Music ] [ Building ]
```

Then one optional level:

```text
[ Back ]   [ Sub-Collection identity ]

[ Activity ] [ Activity ] [ Activity ]
```

The launcher-local Back control is not ADR-0019 protected Activity system chrome. It moves one launcher discovery level toward Home and never substitutes for Greia's protected Activity Home/Back authority.

## Adaptive depth policy — accepted target, not yet source-complete

Initial target:

- 1–10 **effective visible** Activities in a primary Collection → show Activities directly;
- >10 → evaluate whether one semantic sub-Collection layer materially improves discovery;
- never force subdivision merely because count crossed a threshold;
- if no coherent partition exists, retain direct bounded scrolling/paging;
- never exceed `Home → primary Collection → optional sub-Collection → Activity`.

A useful subdivision normally yields roughly 2–5 recognizable groups and avoids a dominant meaningless Other bucket.

Stability/hysteresis target:

- evaluate subdivision above 10;
- once a useful subdivided view is adopted, do not collapse after a one/two-item fluctuation;
- initial collapse target around 8 effective visible Activities.

Exact constants/persistence remain platform policy and may evolve from child testing.

## Effective per-child catalogue — future policy seam

Future adaptive depth must use the effective visible set, conceptually:

```text
validated Activity registry
    ↓
Parent per-child visibility / explicit Activity overrides
    ↓
profile audience/challenge discovery policy
    ↓
effective visible Activity set
    ↓
Collection projection + adaptive depth
```

Filtering/ranking never changes package trust, registration or launch authority.

## Future semantic discovery hints

Current parser supports primary `[presentation].categories` only. Future bounded grouping hints are conceptually:

```toml
[presentation]
categories = ["create", "learn"]
discovery_tags = ["drawing", "shapes"]
```

They help platform policy form useful optional sub-Collections when the effective catalogue is large enough. They do not command folder creation and do not define filesystem paths.

As of 2026-08-21, `discovery_tags` is a design target and is **not currently parsed**.

## Age/development and difficulty

Current source parses:

```toml
[education]
difficulty = 1
```

with difficulty 1–10. It represents challenge, **not age**.

Accepted future developmental suitability remains independent, conceptually:

```toml
[education]
difficulty = 3
recommended_age_min = 5
recommended_age_max = 8
```

Adaptive challenge may later declare a range, conceptually:

```toml
[education]
difficulty = 3
difficulty_min = 1
difficulty_max = 7
adaptive_difficulty = true
```

These age/adaptive-difficulty fields are not yet parsed. Missing future age metadata fails open for ordinary discovery; explicit Parent hide remains authoritative.

## Parent and child discovery policy — future

Parent management may later expose policies equivalent to:

```text
Show everything
Hide Activities probably too simple
Show recommended range only
Custom
```

plus per-Activity always-show/always-hide overrides. Exact date of birth is not required; coarse age/development stage is sufficient for discovery. Child-facing recommendation must not shame or grade the child.

## Activity scrolling

A direct Activity Collection uses a bounded visible window. Current launcher supports semantic arrow/controller selection, bounded paging/scrolling, mouse-wheel semantic movement and explicit controls when more content exists. Only visible items are rendered.

# Activity icons

## Built-in catalogue icon

```toml
[activity]
icon = "palette"
```

resolves through Greia's platform asset catalogue.

## Package-owned icon

A portable Activity may use:

```toml
[activity]
icon = "package:assets/icon.png"
```

Current allowed package formats are PNG/WebP. Platform validation requires:

- relative contained path;
- no traversal/absolute escape;
- bounded path length/depth;
- regular existing file inside validated package root;
- bounded file size;
- valid supported image header;
- bounded decode dimensions (currently at most 1024×1024 for launcher package icons).

Recommended source: square, clean silhouette, transparent background where useful, important content away from outer edge, no text dependency because launcher renders the Activity title separately.

# Parent-installed Activities

Parent-installed packages are a separate typed source:

- trust: `PARENT_TRUSTED_UNSIGNED`;
- source ID: `greia-parent-package-service`;
- default active root: `/var/lib/greia-os/activity-packages/active`.

The launcher composes this source through the same `ActivityRegistry`, then rebuilds runtime/permission/history/supervisor composition before publishing changes. Presentation never scans arbitrary upload directories.

## `.greiaactivity` packaging convention

The implemented new-install format is a bounded ZIP with `.greiaactivity` suffix and Activity package root at archive root:

```text
my-activity.greiaactivity
├── activity.toml
├── main.py
└── assets/
    └── icon.png
```

No arbitrary wrapper directory. Installer rejects traversal, unsafe paths, symlinks/special files, encrypted entries, unsafe compression, excessive entry count and excessive expanded size before registry/asset validation.

### Install transaction

Current new-install service uses process-wide serialization, private staging, full registry/asset validation, digest-addressed immutable storage, prepared read-only activation tree, receipt preparation and atomic activation rename as commit point. Existing Activity IDs are deliberately rejected; update/removal/signature/revocation/rollback-selection remain separate policy work.

## Parent install availability

Protocol existence does not imply release availability. `POST /api/v1/activities/install` remains capability-gated; ordinary/release systems keep executable package installation disabled while Parent transport is provisional. Developer/owner-enabled systems can exercise the implemented new-install path for development/acceptance.

# Performance constraints

The launcher must remain comfortable on the legacy 1024×600/i686 reference floor:

- ~30 Hz is acceptable for subtle UI effects;
- no retained per-frame animation-object allocation;
- bounded icon/font/shadow/visual caches;
- only visible Activity/Collection items rendered;
- no per-frame disk/package discovery;
- adaptive projection recomputed only on meaningful catalogue/profile/policy changes;
- visual effects degrade gracefully rather than delay input/launch;
- no network/disk scan triggered by a frame render.

# Implementation migration status

Current source provides:

- semantic `Collection` in `greia_platform.ui_core`;
- `ActivityCatalogue` projection;
- Collection-first Home accepted through Activity Simulator;
- platform-owned primary IDs `create`, `play`, `learn`, `explore`, `my_greia` in source;
- source-implemented Browse/More recoverability for Activities lacking recognized primary membership;
- source-implemented suppression of arbitrary package categories as launcher Collections;
- built-in Clinic corrected to Play + Learn navigation while care/health remains educational taxonomy;
- multi-membership and bounded Activity scrolling;
- `education.difficulty` 1–10;
- Parent direction for future per-child policy.

Current acceptance boundary:

- Collection-first Home with bounded primary vocabulary & Browse recovery: **SIMULATOR VISUAL REVIEW** via `2026-08-21_COLLECTION_FIRST_HOME_SIMULATOR.md` (archived; see git history) and `2026-08-21_COLLECTION_PRIMARY_VOCABULARY_SIMULATOR.md` (archived; see git history).

Still not implemented:

- optional adaptive sub-Collections/hysteresis;
- `presentation.discovery_tags`;
- age/development suitability manifest fields;
- adaptive difficulty range metadata;
- profile audience/challenge preference;
- Parent visibility policy/API/UI;
- per-child effective-catalogue projection.

Do not describe those target items as implemented until source/tests/Parent client are updated and verified.

# Future extensions

The primitives are intentionally reusable for profile cards, reward popups, Parent-approved dialogs, Activity SDK controls, Collection transitions, focus effects and bounded recent/favorite/Continue shortcuts that obey effective per-child visibility.

Future additions should be concrete primitives justified by real callers. Do not grow this into a generic UI framework merely because another effect is desirable.
