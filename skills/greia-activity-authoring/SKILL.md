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
docs/adr/0012-platform-constitution.md
docs/adr/0017-platform-owned-activity-events-progress-and-history.md
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/adr/0023-open-activity-ecosystem-distribution-and-official-catalogue.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
runtime/child-runtime.toml
src/greia_platform/activities.py
src/greia_platform/activity_api.py
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
- ship executable native files merely because they work on a developer machine;
- turn display text or translated labels into identifiers/authority;
- grant itself capabilities/permissions through UI state;
- create an unbounded cache/widget/list merely because the current sample data is small.

The platform owns lifecycle, profile/session state, package trust, permissions, system chrome, durable progress/history, and the physical display/input boundary.

## 3. Package layout

A source Activity is a self-contained directory with `activity.toml` at its root. Keep the package small and explicit.

Example:

```text
activities/my_activity/
├── activity.toml
├── main.py
├── assets/
│   └── icon.png
└── ...
```

Do not add generated caches, virtual environments, arbitrary shell installers, package-manager state or hidden metadata directories.

The current registry rejects symlinks, forbidden names/suffixes, executable package files and packages above the configured runtime size limit.

## 4. Current `activity.toml` shape

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

## 5. Launcher navigation categories are NOT education categories

This distinction is important after the 2026-08-18 launcher work.

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

The parser deliberately does not freeze that list forever, but category IDs are bounded platform-style identifiers and one package may currently declare at most four.

An Activity may appear in more than one launcher category without duplicating installation, permissions, progress or saves.

### Educational taxonomy

Keep learning/progression metadata under:

```toml
[education]
categories = ["creativity", "fine_motor", "geometry"]
```

These values may be numerous/specific because they are semantic learning tags. **Do not add `fine_motor`, `problem_solving`, etc. to `[presentation]` merely to surface educational metadata as launcher tabs.**

Older API-0.1 packages with no `[presentation]` table currently fall back to `education.categories` for compatibility. New/updated packages should not rely on that fallback.

## 6. Activity icons

### Platform catalogue icon

A built-in Activity may reference a shared semantic icon ID:

```toml
[activity]
icon = "palette"
```

The ID must exist in the platform asset catalogue.

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

Parent package installation validates this reference **before activation**. Do not attempt to reference `/home/...`, `/usr/share/...`, URLs, removable media or another Activity's assets.

Recommended visual authoring:

- square source canvas;
- transparent background where appropriate;
- clear silhouette at launcher scale;
- important detail away from the outer 8–10%;
- no required text inside the icon;
- expect the launcher to add its own subtle shadow/depth treatment.

## 7. Input and interaction

Use an `input.profile` that reflects the interaction model rather than the developer's current mouse/keyboard.

Examples:

- `pointer` for primarily pointer/touch manipulation;
- `text` for typing-oriented Activities;
- `hybrid` where multiple semantic inputs are meaningful.

Consult ADR 0020 and `ACTIVITY_INPUT_STANDARDS.md` for current profiles/actions/controller semantics.

Do not read `/dev/input` directly or make raw SDL/Pygame controller ownership a package authority contract. Input-device authority belongs to the platform.

Activities should remain operable without relying only on hover. Hover is enhancement, not the only indication of selection/action.

## 8. UI architecture for Activities

ADR 0018 requires a lightweight semantic UI foundation, not a desktop widget framework.

Current relevant shared layers include:

```text
src/greia_platform/ui_core.py
src/greia_platform/ui_motion.py
src/greia_platform/ui_scroll.py
src/greia_platform/pygame_ui.py
src/greia_platform/activity_ui.py
```

Pygame rendering helpers now also include:

```text
src/greia_platform/pygame_effects.py
```

### Use shared semantics, not launcher internals

`greia_launcher.presentation` is platform Shell/launcher composition. An Activity must not import launcher modules merely to copy a shadow or animation.

If an effect becomes broadly useful to Activities, promote the concrete reusable primitive into the shared platform layer with bounded behavior and tests. The 2026-08-18 launcher work intentionally moved generic motion/scroll/depth primitives into `greia_platform` for this reason.

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

## 9. Scrolling collections

Use renderer-neutral collection/scroll semantics where possible. `ScrollModel` keeps a selected item inside a bounded visible window and advances by semantic items/rows rather than requiring desktop-style free-pixel scrolling.

General rule:

- selection state is semantic authority;
- renderer shows only the current bounded window;
- keyboard/controller movement and pointer/touch scrolling update the same model;
- a large content set must not cause an equally large retained widget/surface set.

The launcher itself currently demonstrates a two-row bounded Activity window. That exact launcher layout is not an Activity requirement; the bounded principle is.

## 10. System navigation

Universal Home/Back behavior is platform-owned system chrome under ADR 0019.

Do not draw fake Home/Back buttons inside an Activity and treat them as equivalent security/lifecycle controls. Use the supported platform contract and leave protected chrome geometry/authority to the launcher/system layer.

## 11. Storage, events, progress, awards

Use Greia's typed storage/event APIs. Do not write to arbitrary host paths or maintain a second authoritative progress database inside the package.

Activity events should express semantic facts such as completion/creation/score/milestone. Platform progression/history owns durable interpretation.

Awards/badges/celebrations are platform-owned architecture under ADR 0025. An Activity should emit the supported semantic evidence; it must not mint authoritative awards itself merely by displaying a badge image.

## 12. Packaging as `.greiaactivity`

The first implemented package-install seam uses a bounded ZIP archive commonly named with the `.greiaactivity` suffix.

The normal Activity root is the archive root:

```text
my-activity.greiaactivity
├── activity.toml
├── main.py
└── assets/
    └── icon.png
```

**Do not add a wrapper directory** such as `my-activity/activity.toml` inside the archive.

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

## 13. Parent installation

The Parent API now protocol-defines:

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

## 14. Runtime discovery after install

The launcher can detect the Parent active package source while already running. The safe sequence is:

1. registry discovery/validation of the combined source set;
2. rebuild runtime/permission/storage/history/progression/supervisor authority against that exact validated set;
3. publish the new child-facing catalogue only after authority rebuild succeeds;
4. retain the previous known-good catalogue/runtime pair on failure.

Activity authors should therefore not require a reboot/restart merely to make an otherwise valid new install discoverable, but they must also not assume package presence implies launch authority before registry/runtime composition succeeds.

## 15. Validation and tests

Before considering Activity source ready, run the repository's canonical validation/test paths on an owner-controlled checkout. Relevant focused tests commonly include Activity contract/runtime/input/UI tests, but the active plan/handover owns the exact current verification step.

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
- successful install appears through the ordinary registry and launches through normal authority;
- input/profile behavior works on the intended hardware floor;
- Home/Back/system chrome behavior remains platform-owned;
- caches/lists/effects remain bounded.

**Never claim PASS because a test file exists.** Record only commands actually executed and their real output/evidence.

## 16. Quality checklist for child-facing Activities

A good Greia Activity should generally be:

- understandable with little or no reading for its target age where product scope requires it;
- visually clear at 1024×600;
- immediately responsive to input;
- forgiving of mistakes;
- replayable rather than a one-shot worksheet;
- explicit about feedback without becoming overstimulating;
- usable across the declared input profile;
- free of child-visible desktop/shell/package-manager artifacts;
- able to crash/exit without taking the launcher/session down;
- semantically integrated with platform storage/events/progress instead of inventing private equivalents;
- visually compatible with Greia without requiring every package to reuse a generic system icon.

## 17. When changing the Activity contract

If author-facing Activity behavior changes, update in the same tranche:

- exact source/runtime owner;
- focused tests;
- this skill;
- relevant design/product/architecture documents;
- `docs/DOCUMENTATION.md` if authority ownership changes;
- active plan progress and `HANDOVER.md` for substantive implementation/evidence changes.

If the change is architectural rather than merely implementation detail, resolve it through the applicable ADR instead of silently extending the manifest/API.
