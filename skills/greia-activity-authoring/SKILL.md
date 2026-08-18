---
name: greia-activity-authoring
description: Canonical agent guide for designing, implementing, packaging, validating and testing Greia Activities against current platform contracts.
---

# Greia Activity Authoring Skill

**Status:** living derived authoring guide  
**Reviewed:** 2026-08-18

This file is practical guidance. Exact implemented APIs/schemas are owned by source/runtime declarations; accepted ADRs own architecture; product docs own child-facing requirements. When this guide disagrees with current source, inspect the authority map and resolve the discrepancy rather than coding to stale prose.

## 1. Mandatory context before Activity work

Read, as relevant:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/architecture/GREIA_ACTIVITY_ECOSYSTEM.md
docs/adr/0012-platform-architecture-constitution.md
docs/adr/0017-platform-owned-sessions-events-progression-and-reward-ledger.md
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/adr/0023-open-activity-ecosystem-distribution-and-official-catalogue.md
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/adr/0027-activity-coordinate-spaces-canvas-and-world-camera.md
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
runtime/child-runtime.toml
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/responsive_layout.py
src/greia_platform/activity_viewport.py
src/greia_platform/localization.py
src/greia_platform/language_presentation.py
```

For Pygame Activities also inspect:

```text
src/greia_platform/pygame_ui.py
src/greia_platform/pygame_canvas.py
src/greia_platform/activity_ui.py
```

For packaging/install work also read:

```text
src/greia_platform/activity_packages.py
src/greia_platform/activity_assets.py
src/greia_platform/trust.py
```

Do not treat chat history as a substitute for these contracts.

## 2. Core Activity invariants

An Activity is content running under Greia, not a miniature desktop application and not a privileged platform service.

An Activity must not:

- own login/profile selection;
- implement its own parent/admin authentication;
- bypass Greia storage/progress/history/event services;
- implement system Home/Back as ordinary Activity widgets;
- manage the host package manager;
- depend on arbitrary host filesystem paths;
- assume direct ownership of Linux input devices or display-session authority;
- assume one physical screen resolution as its semantic coordinate system;
- maintain per-resolution coordinate tables/device-specific layouts when shared viewport/layout primitives can express the behavior;
- place essential Activity controls in the platform-owned Home/Back protected region;
- publish lifecycle READY merely because a renderer initialized before a usable child-facing frame was actually presented;
- treat translated display text as identifiers/authority;
- hard-code user-facing prose/audio into game logic when it can be represented by localization keys/cues;
- claim `languages = ["*"]` merely because hard-coded English happens to run everywhere;
- bake launcher language flags into its own icon asset;
- ship executable native files merely because they work on a developer machine;
- grant itself capabilities/permissions through UI state;
- create an unbounded cache/widget/list merely because current sample data is small.

The platform owns lifecycle, profile/session state, package trust, permissions, system chrome, durable progress/history, physical display/input boundaries, the normal child UI-locale authority chain, launcher language presentation and the platform-owned pre-launch language chooser.

## 3. Package layout

A source Activity is a self-contained directory with `activity.toml` at its root. Keep the package small and explicit.

Example:

```text
activities/my_activity/
├── activity.toml
├── main.py
├── locales/
│   ├── en.json
│   └── it.json
├── assets/
│   └── icon.png
└── ...
```

`locales/` is optional when the Activity is genuinely language-neutral. A single-language Activity should still be structured so adding another language is primarily data/assets work rather than a gameplay rewrite.

Do not add generated caches, virtual environments, arbitrary shell installers, package-manager state or hidden metadata directories.

The current registry rejects symlinks, forbidden names/suffixes, executable package files and packages above the configured runtime size limit.

## 4. Current `activity.toml` shape and migration warning

The exact parser lives in `src/greia_platform/activities.py`; this is an authoring example, not a second schema definition.

```toml
[activity]
id = "org.example.my-activity"
legacy_ids = []
title_key = "activity.my_activity.title"
version = "0.1.0"
icon = "package:assets/icon.png"
languages = ["*"]

[presentation]
categories = ["play", "learn"]

[education]
categories = ["problem_solving", "geometry"]
difficulty = 1
skills = [
  { id = "math.geometry.shape_recognition", weight = 2 },
]
events = [
  { id = "round.completed", kind = "completion" },
]

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = ["display", "pointer"]
optional_capabilities = ["touch"]

[permissions]
requested = []

[storage]
schema_version = 1
```

### 4.1 Activity identity

Use a stable lower-case reverse-DNS Activity ID. Do not encode display language, machine model, install path or current version into the canonical ID.

`legacy_ids` exists for built-in migration compatibility and is not a general third-party alias mechanism. External/Parent-trusted packages cannot claim built-in legacy aliases.

### 4.2 Runtime/API version

Use only runtime types/API versions actually accepted by the current runtime catalogue. Do not write a future Web runtime into a package and call it supported because the architecture allows one later.

The entrypoint must be a safe relative file path inside the package.

### 4.3 Capabilities versus permissions

Capabilities describe required/optional platform facilities. Permissions request bounded authority mediated by the platform. Use the exact vocabularies from `runtime/child-runtime.toml`; do not invent strings locally.

Unknown, duplicated or overlapping required/optional capability declarations are validation errors.

### 4.4 Localization metadata is in architectural migration

ADR 0028 selects a more precise future contract than the current broad `activity.languages` field. Conceptually it distinguishes:

```text
catalogue/title locales
Activity UI locales
Activity UI language-selection policy
content/learning locales
content-language-selection policy
true language-neutrality
```

Do **not** silently invent unsupported manifest tables and assume the current parser consumes them. Inspect the exact current schema. If implementing the localization contract, update parser/runtime/tests/docs together.

Even before the manifest migration is complete, write Activity code so user-facing strings/audio are isolated behind semantic resource keys and so a second language can be added without rewriting gameplay.

## 5. Launcher navigation categories are NOT education categories

### Child-facing launcher navigation

Use:

```toml
[presentation]
categories = ["create", "learn"]
```

Current recommended high-level vocabulary:

```text
create
play
learn
explore
my_greia
```

An Activity may appear in more than one launcher category without duplicating installation, permissions, progress or saves.

### Educational taxonomy

Keep learning/progression metadata under:

```toml
[education]
categories = ["creativity", "fine_motor", "geometry"]
```

These values may be numerous/specific because they are semantic learning tags. Do not add `fine_motor`, `problem_solving`, etc. to `[presentation]` merely to surface educational metadata as launcher tabs.

Older API-0.1 packages with no `[presentation]` table currently fall back to `education.categories` for compatibility. New/updated packages should not rely on that fallback.

## 6. Activity icons and dynamic language presentation

### Platform catalogue icon

A built-in Activity may reference a shared semantic icon ID:

```toml
[activity]
icon = "palette"
```

### Package-owned icon

Portable Activities may carry their own visual identity:

```toml
[activity]
icon = "package:assets/icon.png"
```

Current package-owned icon rules are owned by `src/greia_platform/activity_assets.py`:

- PNG or WebP;
- relative path only;
- no `.`/`..` traversal;
- bounded depth/length;
- must resolve to a regular file strictly inside the validated package root.

Recommended visual authoring:

- square source canvas;
- transparent background where appropriate;
- clear silhouette at launcher scale;
- important detail away from the outer 8–10%;
- no required text inside the icon;
- expect launcher shadow/depth treatment.

### Do not bake language into the Activity icon

Greia owns the dynamic language emblem. For language-specific Activities, the launcher composites the flag corresponding to the **actual resolved launch language**.

Examples selected by product policy:

```text
English    → British flag
Spanish    → Spain flag
Italian    → Italy flag
French     → France flag
```

A multilingual Activity may show a different flag when the child profile language changes. An English-only Activity on an Italian system shows the British flag. A language-neutral Activity does not need a language flag.

Do not use `EN`/`IT` initials as the primary child-facing language signal; many Greia users cannot read.

## 7. Input and interaction

Use an `input.profile` that reflects the interaction model rather than the developer's current mouse/keyboard.

Examples:

- `pointer` for primarily pointer/touch manipulation;
- `text` for typing-oriented Activities;
- `hybrid` where multiple semantic inputs are meaningful.

Consult ADR 0020 and `ACTIVITY_INPUT_STANDARDS.md` for current profiles/actions/controller semantics.

Do not read `/dev/input` directly or make raw SDL/Pygame controller ownership a package authority contract. Input-device authority belongs to the platform.

Activities should remain operable without relying only on hover. Hover is enhancement, not the only indication of selection/action.

For pointer/touch content authored in reference/world coordinates, use the **same Greia transform object for rendering and physical→logical input mapping**. Do not independently rescale hit testing.

## 8. UI architecture and automatic resolution adaptation

ADR 0018 requires a lightweight semantic UI foundation. ADR 0026 additionally requires platform-owned automatic resolution adaptation.

**Designers/programmers author one semantic layout. They do not maintain separate screen-resolution layouts.**

Current shared layers include:

```text
src/greia_platform/ui_core.py
src/greia_platform/ui_motion.py
src/greia_platform/ui_scroll.py
src/greia_platform/responsive_layout.py
src/greia_platform/activity_viewport.py
src/greia_platform/pygame_ui.py
src/greia_platform/pygame_canvas.py
src/greia_platform/activity_ui.py
src/greia_platform/pygame_effects.py
```

### Use shared semantics, not launcher internals

`greia_launcher.presentation` is platform Shell/launcher composition. An Activity must not import launcher modules merely to copy a shadow, animation or layout algorithm.

If an effect/layout pattern becomes broadly useful to Activities, promote the concrete reusable primitive into the shared platform layer with bounded behavior and tests.

### Pygame Activity controls must use Activity-safe geometry

`ChildUiMetrics.toolbar_button()` is a full-surface helper retained for non-Activity Greia surfaces. Inside an Activity, essential controls/content must instead be derived from the platform-protected safe region:

```python
metrics = ChildUiMetrics.for_size(*screen.get_size())

gallery = metrics.activity_toolbar_button(0, side="left")
new = metrics.activity_toolbar_button(0, side="right")
content = metrics.activity_content_rect()
```

Use `activity_safe_rect()` when an Activity-owned secondary region (for example a Painting palette) must be anchored to the usable Activity area.

Do not compensate for Home/Back with a guessed top-left inset, and do not draw an Activity-owned Close/Home/Back control to reclaim that area. The shared helper and the system-chrome backend derive geometry from the same protected-region contract.

### Effects should be subtle and bounded

Good examples:

- small hover/focus lift;
- shallow drop shadow;
- bounded press feedback;
- short deterministic transition;
- semantic selection-aware scrolling.

Avoid:

- full-screen blur/compositing pipelines;
- unbounded retained animation objects;
- hundreds of offscreen widgets/surfaces;
- disk/network/package scans every frame;
- animation that delays input or hides an error indefinitely;
- mechanics that require a high refresh rate to remain usable.

The legacy 1024×600/i686 floor remains a real engineering constraint.

## 9. Activity viewport, reference canvas and world authoring

ADR 0027 defines the spatial contract. The author chooses content semantics, not target resolutions.

### 9.1 Default design reference

For canvas-style visual authoring, the default logical reference is:

```text
1024 × 600 logical units
```

This is aligned with the reference netbook so designers have a concrete child-tested starting composition. It is not permission to assume the physical surface is 1024×600.

### 9.2 Choose one or compose several spatial models

```text
fluid
reference_canvas
world_camera
hybrid
```

Typical choices:

- math/question grid → `fluid`;
- text editor/gallery → `fluid`;
- fixed puzzle/board → `reference_canvas` + `contain`;
- decorative full-bleed scene → `reference_canvas` + `cover`;
- side-scroller/top-down game → `world_camera` + `expand`;
- painting/physics sandbox/game HUD → `hybrid`.

Read `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` for the full decision guide.

### 9.3 Reference canvas

`contain` keeps the whole reference composition visible and may letterbox.

`cover` fills the target but may crop outer expendable content.

Never non-uniformly stretch the design to another aspect ratio.

For simple Pygame fixed scenes, `PygameReferenceCanvas` lets the author draw once on the logical surface and maps presentation/input automatically.

For flat procedural scenes, prefer its normal presentation scaler unless smooth whole-frame resampling has a measured visual benefit. The low-resource target matters; do not spend CPU on smoothscale merely because it looks like a quality toggle.

### 9.4 World camera

World/game state uses stable logical coordinates independent of physical display pixels.

`expand` normally preserves the reference camera scale while revealing additional world on the excess aspect-ratio axis. A wider screen can show more horizontal world; a taller screen can show more vertical world.

Changing resolution must not rewrite physics, collisions, level coordinates or saved world state.

Use `visible_logical_rect` for culling. Do not render an entire unbounded world because it exists.

### 9.5 Fluid layout

For semantic UI/grids/collections, declare usable size constraints and let `responsive_layout` select rows/columns/visible capacity. Do not author breakpoint tables like `if width >= 1920` / `elif width >= 1024` to manually move items.

### 9.6 Hybrid layers

Rich Activities commonly combine:

```text
world/background       world_camera
HUD/tools              fluid safe UI
fixed board/document   reference/logical canvas
modal sheet            fluid overlay
Home/Back              platform-owned chrome
```

### 9.7 System chrome / safe UI

Greia Home/Back regions are platform-protected. Essential Activity controls belong in platform-derived safe UI geometry. Background/world art may visually extend under chrome where appropriate, but Activity pointer authority does not.

Do not hard-code a pixel inset for system chrome.

For fluid Pygame Activities use `ChildUiMetrics.activity_toolbar_button()`, `activity_content_rect()` and, where needed, `activity_safe_rect()`. For reference/world Activities use `activity_viewport_for_surface()` / the mapper's logical safe-region support and reject Activity input inside protected physical chrome before mapping it into gameplay.

Rendering and hit testing must therefore share both boundaries: the same logical↔physical transform for content, and the same Greia-owned protected-region authority for system navigation.

### 9.8 Durable state is resolution-neutral

Do not save physical UI coordinates as portable content state.

Good: world position, semantic item ID, painting document dimensions/content, text, camera world position if meaningful.

Bad: button x/y because the current screen was 1366 pixels wide, current wrap points, physical pointer position as game state.

## 10. Localization and language authoring

ADR 0028 is mandatory for new language-aware Activity work.

### 10.1 Many Activities may ship in one language — that is acceptable

Do not reject or artificially block an English-only Activity on an Italian system. The platform resolves it to English and visually signals that fact with the British flag.

The important requirement is honesty and structure: declare actual support and keep the Activity easy to translate later.

### 10.2 Separate catalogue/title language from in-Activity UI language

An English-only Activity may still ship an Italian launcher title.

Example:

```text
launcher/profile locale:  it-IT
launcher title:           Italian translation
Activity UI:              English only
launcher flag:            British flag
```

`activity.title_key` is a semantic key, not final prose. Localized launcher names should come from package/platform localization data once the manifest/runtime integration is complete.

### 10.3 Separate UI language from content/learning language

Do not use one ambiguous `language` variable for everything.

Example Writing Activity:

```text
Greia UI:           Italian
Writing UI:         Italian or language-neutral icons
content language:   English
spell/audio rules:  English
```

A language-learning Activity may likewise give Italian instructions while lesson words/audio are English.

Conceptually keep:

```text
ui_locale
content_locale
```

separate in code/state.

### 10.4 Ordinary UI language follows the child profile

Normal resolution is:

```text
device default locale
→ optional child-profile override
→ Activity supported UI locale/fallback
```

Do not invent a settings page where the parent configures a UI language for every Activity.

### 10.5 Opt-in pre-launch language selection

An Activity may explicitly declare that UI language or content language is selectable at launch.

Greia owns the chooser. It should use large flags and optional spoken language names, not a text-heavy list. The Activity receives the selected locale as launch context.

Do not build another private language chooser inside every Activity merely to choose runtime locale.

### 10.6 Localization bundle structure

ADR 0028 selects cross-runtime JSON bundles under `locales/`.

Example:

```json
{
  "schema_version": 1,
  "locale": "it",
  "direction": "ltr",
  "strings": {
    "activity.title": "Scriviamo!",
    "feedback.correct": "Bravissima!"
  },
  "audio": {
    "feedback.correct": {
      "path": "locales/it/audio/correct.ogg",
      "caption_key": "feedback.correct"
    }
  }
}
```

Current runtime-neutral primitives live in `greia_platform.localization`.

### 10.7 Always isolate user-facing strings from gameplay logic

Even if only English ships today, prefer:

```text
feedback.correct
instruction.choose
activity.title
```

over hard-coded prose spread through game state/control flow.

Do not concatenate translated fragments into English sentence order.

Bad:

```text
translated("you_have") + count + translated("apples")
```

Prefer a complete semantic message with named variables.

### 10.8 Localize spoken instructions through semantic cue IDs

Use cues such as:

```text
instruction.choose
feedback.correct
character.professor.welcome
```

rather than hard-coded locale-specific filenames in gameplay logic.

Localized audio is part of the package data. Initial portable localized-audio support is OGG/WAV. Do not depend on arbitrary codecs available on a developer laptop.

### 10.9 Language-neutral is a real semantic claim

A shape-matching game with icons/sounds that require no linguistic interpretation may be language-neutral.

An Activity with hard-coded English words is not language-neutral just because it technically launches everywhere.

### 10.10 Localization must not create language-specific layouts

Translations vary in length. Let ADR 0026 responsive layout absorb the difference through wrapping/reflow/bounded sizing.

Do not create an Italian coordinate table and an English coordinate table.

For canvas/world games, put translated HUD/instructions in fluid/safe UI layers where practical. If localized text belongs inside a fixed logical scene, give it logical bounds that shared text-fitting/wrapping can use.

## 11. Scrolling collections

Use renderer-neutral collection/scroll semantics where possible. `ScrollModel` keeps a selected item inside a bounded visible window and advances by semantic items/rows rather than requiring desktop-style free-pixel scrolling.

General rule:

- selection state is semantic authority;
- renderer shows only the current bounded window;
- keyboard/controller movement and pointer/touch scrolling update the same model;
- a large content set must not cause an equally large retained widget/surface set.

The launcher's exact row count is not an Activity requirement; the bounded principle is.

## 12. System navigation and lifecycle readiness

Universal Home/Back behavior is platform-owned system chrome under ADR 0019.

Do not draw fake Home/Back/Close buttons inside an Activity and treat them as equivalent security/lifecycle controls. Use the supported platform contract and leave protected chrome geometry/authority to the launcher/system layer.

### READY means first usable frame is actually presentable

For Pygame Activities, do not call `mark_activity_ready()` immediately after initialization. Render and present the first usable child-facing frame first, then publish READY once:

```python
ready_published = False
while running and not activity_stop_requested():
    ...
    draw_frame()
    pygame.display.flip()
    if not ready_published:
        mark_activity_ready()
        ready_published = True
```

The supervisor uses READY as a presentation/lifecycle boundary. Advertising it before the first frame can expose a blank/uninitialized transition and makes readiness evidence dishonest.

Keep responding to `activity_stop_requested()` so platform Home/system shutdown can terminate the Activity through the authoritative lifecycle rather than through an Activity-owned fake close control.

## 13. Storage, events, progress and awards

Use Greia's typed storage/event APIs. Do not write to arbitrary host paths or maintain a second authoritative progress database inside the package.

Activity events should express semantic facts such as completion/creation/score/milestone. Platform progression/history owns durable interpretation.

Awards/badges/celebrations are platform-owned architecture under ADR 0025. An Activity should emit supported semantic evidence; it must not mint authoritative awards itself merely by displaying a badge image.

Language and resolution are presentation/context. Do not rewrite semantic score/progress IDs because locale or screen size changes.

## 14. Packaging as `.greiaactivity`

The first implemented package-install seam uses a bounded ZIP archive commonly named with the `.greiaactivity` suffix.

The normal Activity root is the archive root:

```text
my-activity.greiaactivity
├── activity.toml
├── main.py
├── locales/
└── assets/
```

Do not add a wrapper directory such as `my-activity/activity.toml` inside the archive.

The current package service rejects unsafe archive/path/symlink/special-file/compression behavior, stages privately, validates through the ordinary registry, validates package-owned icons, stores a read-only digest-addressed immutable copy and atomically publishes a read-only active tree.

### Important scope boundary

This is currently a **new-install** foundation, not full R10.

Current intentional limitations:

- an existing Activity ID is rejected rather than updated;
- removal is not implemented as a finished Parent package workflow;
- rollback/version-selection policy is not complete;
- signature/revocation/catalogue policy is not complete;
- save migration/compatibility policy for updates is not complete;
- general release install is not enabled while Parent transport is provisional HTTP.

Do not implement your own update/delete mechanism inside an Activity to work around these limitations.

## 15. Parent installation

The Parent API protocol-defines:

```text
POST /api/v1/activities/install
```

but clients must honor capability negotiation:

```text
activities.install
```

Ordinary/release images currently advertise this as false. Explicit developer/owner-enabled machines may advertise it true for development/acceptance of the new-install seam.

The external HTML Parent client is pinned/integrity-checked by the Greia build. It uploads package bytes directly to the typed endpoint. It must never replace a false capability with raw filesystem copy, shell commands, `apt`, SSH or an ad-hoc upload directory.

Parent-installed packages have distinct trust:

```text
PARENT_TRUSTED_UNSIGNED
```

They remain separate from built-ins and developer-unsigned sources even though they use the same registry/runtime/permission/supervisor path after validation.

## 16. Runtime discovery after install

The launcher can detect the Parent active package source while already running. The safe sequence is:

1. registry discovery/validation of the combined source set;
2. rebuild runtime/permission/storage/history/progression/supervisor authority against that exact validated set;
3. publish the new child-facing catalogue only after authority rebuild succeeds;
4. retain the previous known-good catalogue/runtime pair on failure.

Activity authors should not require a reboot/restart merely to make an otherwise valid new install discoverable, but must not assume package presence implies launch authority before runtime composition succeeds.

## 17. Validation and tests

Before considering Activity source ready, run the repository's canonical owner-controlled validation/test paths.

Relevant current focused architecture tests include, as applicable:

```text
tests.test_responsive_layout
tests.test_activity_viewport
tests.test_activity_ui
tests.test_first_party_activity_readiness
tests.test_shape_garden_contract
tests.test_core_activity_system_safe_ui
tests.test_localization
tests.test_language_presentation
tests.test_ui_motion_scroll
tests.test_launcher_presentation
```

For a `.greiaactivity` package, test at least:

- manifest parses/validates;
- canonical ID does not collide;
- entrypoint stays inside package;
- package has no forbidden/symlink/executable artifacts;
- declared capabilities/permissions exist;
- launcher categories are sensible high-level navigation metadata;
- educational categories remain learning metadata;
- package icon exists and is contained;
- archive root contains `activity.toml` directly;
- install rejection leaves no active executable package;
- successful install appears through ordinary registry and launches through normal authority;
- input/profile behavior works on the intended hardware floor;
- Home/Back/system chrome remains platform-owned;
- essential Activity controls/content stay outside protected system-chrome geometry;
- reference/world pointer input uses the same transform as rendering and rejects protected-chrome input;
- READY is published only after the first usable frame is presented;
- responsive/canvas behavior does not require per-resolution source edits;
- language declarations are honest;
- single-language fallback works on a differently configured profile where applicable;
- launcher title localization and dynamic language flag are correct where implemented;
- strings/audio are isolated enough that another locale can be added without gameplay rewrite;
- caches/lists/effects remain bounded.

Never claim PASS because a test file exists. Record only commands actually executed and their real output/evidence.

## 18. Quality checklist for child-facing Activities

A good Greia Activity should generally be:

- understandable with little or no reading for its target age where product scope requires it;
- visually clear at the 1024×600 reference while automatically adapting to other usable viewports;
- immediately responsive to input;
- forgiving of mistakes;
- replayable rather than a one-shot worksheet;
- explicit about feedback without becoming overstimulating;
- usable across the declared input profile;
- free of child-visible desktop/shell/package-manager artifacts;
- able to crash/exit without taking the launcher/session down;
- semantically integrated with platform storage/events/progress instead of inventing private equivalents;
- visually compatible with Greia without requiring every package to reuse a generic system icon;
- honest about its available languages;
- easy to localize later even if only one language ships initially;
- free of per-resolution and per-language coordinate forks;
- free of Activity-owned fake system navigation and early READY publication.

## 19. When changing the Activity contract

If author-facing Activity behavior changes, update in the same tranche:

- exact source/runtime owner;
- focused tests;
- this skill;
- relevant design/product/architecture documents;
- `docs/DOCUMENTATION.md` if authority ownership changes;
- active plan progress and `HANDOVER.md` for substantive implementation/evidence changes.

If the change is architectural rather than merely implementation detail, resolve it through the applicable ADR instead of silently extending manifest/API behavior.