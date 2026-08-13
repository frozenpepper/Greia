---
name: greia-activity-authoring
description: Canonical agent guide for designing, implementing, validating and testing Greia Activities against current platform contracts.
---

# Greia Activity Authoring Skill

**Status:** living derived authoring guide  
**Reviewed:** 2026-08-13

This file is practical guidance. Exact implemented APIs/schemas are owned by source/runtime declarations; accepted ADRs own architecture; product docs own child-facing requirements.

## 1. Mandatory read set

Before materially changing an Activity read:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/adr/0018-lightweight-ui-foundation.md
skills/greia-activity-authoring/SKILL.md
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/ui_core.py
src/greia_platform/activity_ui.py
src/greia_platform/storage_client.py
src/greia_platform/event_client.py
src/greia_platform/event_protocol.py
runtime/child-runtime.toml
runtime/storage-policy.toml
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
```

For progression/rewards also inspect `runtime/progression-policy.toml`. For exact current execution/hardware state read `HANDOVER.md`.

## 2. Product canon

A Greia Activity is a supervised child-facing experience, not a Linux desktop program.

- **Activity is the stable abstraction.** Python/Pygame is one runtime.
- **Linux internals are not Activity APIs.** No X11/DRM/systemd/device-file/shell/distro-path dependency.
- **Greia owns lifecycle, durable namespace, sessions, permissions and global progression.**
- **Offline-first.** Core use and saving work without network.
- **Portable state only.** Do not persist host paths, native object graphs or architecture-specific state.
- **Curated runtime only.** No per-Activity venv/package manager/private dependency environment.
- **Low-resource hardware is first-class.** Performance is correctness.

Design at **1024×600 first** with large forgiving targets, direct manipulation, immediate feedback, minimal unnecessary reading and an obvious safe return path. Avoid desktop chrome, tiny controls, file dialogs, dense settings panes and traceback/error walls.

## 3. Current package/runtime contract

Current package shape:

```text
my_activity/
├── activity.toml
├── main.py
└── assets/        # only Activity-specific runtime assets when necessary
```

`runtime/child-runtime.toml` and `src/greia_platform/activities.py` are authoritative. Current hard package ceiling is 50 MiB; it is a ceiling, not a target.

Do not ship dependency trees, venvs, package-manager files, bytecode caches, symlinks, native installers/binaries or unnecessary source/master artwork.

Activity ID is durable identity; title is presentation. Do not casually rename IDs.

Current implemented runtime is Python/Pygame API 0.1. Web/runtime archive formats remain future-facing until source says otherwise.

### Python module limitation

The installed adapter currently launches the manifest entrypoint as a direct file. Package-relative imports such as `from .model import Model` are therefore not yet a supported installed pattern. Do not work around this with `sys.path` mutation/dynamic imports. Small Activities may keep several clean classes in `main.py`; genuinely reusable cross-Activity primitives belong in reviewed `greia_platform` modules.

## 4. Capabilities, permissions and lifecycle

Use only vocabulary declared by `runtime/child-runtime.toml`; do not invent strings. Require only what is essential and use optional capabilities for progressive enhancement.

A manifest permission request is not authority. Ordinary Activities do not gain privileged filesystem/system access.

Lifecycle helpers live in `greia_platform.activity_api`. Call READY only after the child has a usable surface and essential state/assets are ready. Long-running loops must honor Greia STOP requests; Greia retains forced-termination authority.

Unexpected failures should terminate into Supervisor recovery rather than exposing Linux/Python internals or spinning forever.

## 5. Storage, profiles and events

Use Greia Storage through `get_storage()`; never invent durable filesystem locations. Durable namespace is platform-owned and profile/activity scoped.

Portable values should be JSON-compatible logical state, UTF-8 text and explicit media formats such as PNG where appropriate. Do not persist Pygame surfaces, pickle/native graphs, host absolute paths or open resource identifiers.

Creation tools:

- use atomic/debounced writes;
- save on meaningful transitions;
- keep current in-memory work where practical after save failure;
- never silently evict older child creations to manufacture space;
- use visual logical galleries, not filesystem browsing.

Read the active profile via the SDK rather than walking profile directories.

Activities report declared facts/events; Greia owns global reward/progression economics. Event protocol limits and score direction are source/manifest-owned.

## 6. Shared assets, theme and UI

Use semantic core icons through `get_icon_path()` and the canonical asset catalogue; do not hard-code `/opt/greia-os/assets/...` paths.

Use `get_theme()` for the current resolved palette. Ordinary Activities must not request customization-management authority merely to obtain colors.

### Renderer-neutral UI semantics

ADR 0018 and `src/greia_platform/ui_core.py` define the common semantic layer:

```text
Screen
Overlay
Control
Collection
PagedGrid
InvalidationTracker
BoundedCache
```

A child-facing “folder” is a semantic `Collection`, never a Linux filesystem directory. Activities do not create a desktop/window-manager model.

### Current Pygame helpers

`src/greia_platform/activity_ui.py` is the current lightweight Pygame helper layer. It provides 1024×600-first child metrics, large toolbar geometry, bounded icon scaling/cache and a few direct-draw symbols/buttons used by real first-party Activities.

This is **not** a universal retained widget toolkit. Do not add a DOM/CSS clone, scene graph, giant widget hierarchy or animation framework speculatively. Extract the smallest stable primitive after real duplication appears in multiple consumers.

## 7. OOP and architecture quality

Follow `docs/engineering/ENGINEERING_FOUNDATIONS.md`.

- model stable domain concepts with cohesive classes/dataclasses;
- use narrow interfaces/abstract bases at genuine variation points;
- prefer polymorphic implementations to growing backend/type conditional trees;
- prefer composition over inheritance unless substitutability is real;
- make ownership/cleanup explicit;
- keep dependencies flowing through Greia platform contracts rather than hidden globals;
- do not build a second profile/storage/progression/package/backup platform inside an Activity;
- public extension points and non-obvious invariants require useful docstrings/comments.

Strong OOP does not mean maximizing class count. Abstractions must own a real invariant, remove repeated behavior or provide a genuine extension seam.

## 8. Performance canon

Reference assumptions include old Atom-class hardware, roughly 768 MiB RAM and 1024×600 until measured evidence supersedes them.

Avoid per-frame:

- disk/file scans or durable writes;
- image decoding/scaling;
- font construction;
- network operations;
- large temporary object graphs;
- unbounded particles/history/cache growth.

Prefer load/convert once, bounded caches, visible-page rendering, elapsed-time animation and debounced persistence. Static UI should redraw on change where practical. Stable 30-FPS-class pacing is a reasonable default for ordinary 2D Activity animation, not a universal requirement.

Every cache/history/queue needs an explicit bound or demonstrable natural bound.

## 9. Input/audio/error rules

Pointer and touch should share large target geometry where practical; never assume tap-to-click. Keyboard alternatives are welcome but must not hide the only path unless keyboard is inherently required (for example Writing).

Audio should enhance, not gate, interaction; preload/bound short sounds and degrade gracefully when optional audio is unavailable.

Children must never see tracebacks, terminals or Linux diagnostics. Development diagnosis belongs in logs/screenshot tooling.

## 10. Validation and evidence

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py path/to/activity
```

Integrated provider-free gate:

```bash
make verify
```

Meaningful pure tests include state transitions, procedural logic, text buffers, save/index ordering, rollback, bounded history/cache behavior, layout/paging geometry and score/event logic.

Do not replace visual judgment with brittle pixel-exact tests. Local/windowed execution does not prove installed sandbox/storage/display/session or low-end hardware behavior. Use the applicable `docs/testing/*` protocol for VM/physical evidence.

Do not claim commands passed unless they actually executed against the stated checkout.

## 11. Definition of done

Before claiming an Activity source-ready, verify at least:

- stable ID and manifest validation;
- deliberate package/storage schema versions;
- minimal required/optional capabilities and permissions;
- curated imports only;
- READY/STOP correctness;
- Greia Storage only for durable state;
- no silent creation eviction/deletion;
- events only where meaningful and declared;
- semantic assets/theme/shared UI used appropriately;
- 1024×600 usability and child-sized controls;
- bounded hot-loop/history/cache behavior;
- no per-frame durable writes;
- child-safe failure behavior;
- useful provider-free tests;
- standalone validation actually executed;
- `make verify` actually executed before integration-PASS claims;
- required installed/physical evidence completed and accurately scoped.

Writing (`org.greia.writing`) and Painting (`org.greia.painting`) are current first-party creative references, but their exact acceptance state belongs in `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` and `HANDOVER.md`.

## 12. Maintaining this skill

Update this file in the same tranche when Activity-facing manifest/runtime/lifecycle/storage/event/trust/theme/assets/UI/performance/deployment contracts materially change. If implementation makes this guide materially wrong, the tranche is not fully documented.
