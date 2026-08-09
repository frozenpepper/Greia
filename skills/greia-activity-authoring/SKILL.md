---
name: greia-activity-authoring
description: Canonical agent skill for designing, implementing, validating, optimizing, and remotely testing Greia Activities against the current Greia SDK and platform contracts.
---

# Greia Activity Authoring Skill

**Audience:** coding agents and human developers creating or modifying Greia Activities  
**Status:** living derived authoring contract  
**Last reviewed:** 2026-08-10

---

## 1. Use this skill for Activity work

Use this skill whenever work creates, changes, reviews, ports, validates, optimizes, deploys or tests a Greia Activity.

For repository/build/test-hardware operation use:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

For documentation authority and conflict resolution use:

```text
docs/DOCUMENTATION.md
```

This skill is intentionally practical. It summarizes current implementation but does **not** outrank source/runtime declarations.

---

## 2. Implemented now versus future architecture

Do not turn conceptual architecture examples into current APIs.

| Area | Current Activity-authoring status |
|---|---|
| development package | directory containing `activity.toml` |
| manifest syntax | TOML |
| implemented runtime | Python/Pygame |
| runtime API | `runtime/child-runtime.toml`; currently `0.1` |
| lifecycle READY/STOP | implemented |
| durable storage | implemented brokered Greia Storage |
| events/progression facts | implemented brokered Greia events |
| semantic shared icons | implemented |
| canonical theme read | implemented |
| profile-personalized theme read for ordinary Activities | **not implemented yet** |
| shared Activity UI | minimal primitives in `src/greia_platform/activity_ui.py` |
| general widget/layout/scene toolkit | **not implemented** |
| Web Activity runtime/JS SDK | future |
| `.greiaactivity` archive | future |
| `.greiabackup` author-facing format | future |
| measured C0/C1/C2/C3 thresholds | not finalized |

YAML manifests, Web SDK snippets, package archives and future capability examples in architecture documents are semantic direction unless current source says otherwise.

---

## 3. Mandatory source-of-truth read set

Before materially changing an Activity inspect current versions of:

```text
AGENTS.md
docs/DOCUMENTATION.md
skills/greia-activity-authoring/SKILL.md
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/activity_ui.py
src/greia_platform/storage_client.py
src/greia_platform/event_client.py
src/greia_platform/event_protocol.py
runtime/child-runtime.toml
runtime/storage-policy.toml
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
```

When progression/rewards matter also inspect:

```text
runtime/progression-policy.toml
```

Useful current built-in references:

```text
activities/shape_garden/
activities/writing/
activities/painting/
```

Reference Activities are examples, not schema authority.

---

## 4. Product canon

A Greia Activity is a supervised child-facing experience inside Greia, not a Linux desktop program.

Non-negotiable principles:

- **Activity is the stable abstraction.** Python is a runtime, not the product identity.
- **Linux internals are not Activity APIs.** No X11/DRM/systemd/device-file/shell/distro-path dependency.
- **Greia owns lifecycle, durable namespace, effective authority, sessions and global progression.**
- **Offline-first.** Core use and saving must work with no network.
- **Child-first.** The experience should look and behave like Greia, not an embedded desktop app.
- **Low-resource hardware is first-class.** Performance is correctness.
- **Portable state only.** Durable data must survive architecture changes.
- **Curated runtime only.** No per-Activity package manager, venv or private dependency environment.

---

## 5. Child UX canon

Design at **1024×600 first** for young children.

Prefer:

- large forgiving targets;
- direct manipulation;
- immediate visual feedback;
- semantic icons for shared concepts;
- generous spacing;
- minimal required reading for navigation;
- obvious safe return behavior;
- consistent placement;
- localized purposeful text;
- pointer/touch geometry that can share targets;
- keyboard alternatives where useful.

Avoid:

- menu bars/window chrome;
- tiny precision controls;
- filesystem/path concepts;
- desktop file dialogs;
- dense settings panes;
- modal traceback/error walls;
- hidden exits;
- uncontrolled flashing/particles;
- reading as an unnecessary navigation prerequisite.

Text is not forbidden. Unnecessary reading dependency is.

### Creative-tool reference

`Writing` and `Painting` establish an important product pattern:

```text
large useful surface
+ a few large controls
+ automatic durable saving
+ visual gallery
- desktop application chrome
```

Do not turn a child creation tool into mini Word, mini Photoshop or a filesystem manager.

---

## 6. Package contract

Current package shape:

```text
my_activity/
├── activity.toml
├── main.py
└── assets/        # only Activity-specific runtime assets when needed
```

Authoritative validation:

```text
runtime/child-runtime.toml
src/greia_platform/activities.py
```

Current hard Activity package ceiling is **50 MiB**. It is a ceiling, not a target.

Do not ship:

- `.git`, `.hg`, `.svn`;
- `node_modules`, `vendor`, vendored dependency trees;
- venvs;
- `requirements.txt`, `pyproject.toml`, setup files;
- wheels/eggs/shared libraries/native installers;
- executable scripts/binaries;
- bytecode caches;
- symlinks;
- source/master artwork unnecessary at runtime.

Never weaken validation merely to make a package pass.

---

## 7. Stable Activity identity

Activity ID is durable identity; title is presentation.

Current examples:

```text
org.greia.shape-garden
org.greia.writing
org.greia.painting
org.example.maze-garden
```

Do not casually rename a durable Activity ID.

`legacy_ids` are trusted built-in migration aliases. An unsigned package cannot acquire built-in identity merely by claiming an alias or reserved ID.

Package version and storage-schema version are distinct.

---

## 8. Current `activity.toml` pattern

Current shape:

```toml
[activity]
id = "org.example.maze-garden"
legacy_ids = []
title_key = "activity.maze_garden.title"
version = "0.1.0"
icon = "puzzle_pieces"
languages = ["en", "it"]

[education]
categories = ["logic", "spatial"]
difficulty = 3
skills = [
  { id = "spatial.reasoning", weight = 5 },
]
events = [
  { id = "maze.completed", kind = "completion" },
  { id = "maze.time", kind = "score", score_order = "lower_better" },
]

[runtime]
type = "python"
api_version = "0.1"
entrypoint = "main.py"

[requirements]
required_capabilities = ["display", "pointer"]
optional_capabilities = ["keyboard", "audio.basic", "touch"]

[permissions]
requested = []

[storage]
schema_version = 1
```

Re-check the parser before copying this example.

Current event kinds:

```text
completion
creation
milestone
score
```

Score events require exactly one direction:

```text
higher_better
lower_better
```

Activities report facts. They do not author arbitrary global reward values.

---

## 9. Capabilities, permissions and grants

These are different concepts.

Current capability vocabulary comes only from `runtime/child-runtime.toml` and currently includes:

```text
audio.basic
display
keyboard
network
pointer
power.controlled_shutdown
removable_media
touch
```

Current permission-request vocabulary:

```text
customization.manage
profile.manage_own
removable_media.read
```

Rules:

- require a capability only if the Activity cannot function without it;
- use optional capabilities for progressive enhancement;
- do not invent strings;
- a manifest permission request is not a grant;
- Activity environment strings are not authority;
- effective authority is enforced outside the Activity process.

An Activity that only wants Greia colors must **not** request `customization.manage`.

---

## 10. Python runtime/import policy

Greia uses one curated Python environment.

Inspect `[python]` in `runtime/child-runtime.toml` before importing modules. Current curated roots include selected standard-library modules plus `pygame`, `PIL` and `greia_platform`.

Do not design around process execution, raw sockets, ctypes/native loading, package installation or host filesystem discovery.

If a reusable platform function is missing, extend a typed Greia service/SDK boundary instead of smuggling Linux authority into the Activity.

### Current multi-file limitation

The validator currently tolerates package-relative imports, but the installed Python adapter launches `runtime.entrypoint` as a **direct file**. Therefore an entrypoint that relies on package-relative imports such as:

```python
from .model import Model
```

is not yet a supported installed authoring pattern.

Do not work around this with `sys.path` mutation, dynamic imports or `importlib`.

Until module-launch semantics are deliberately implemented and regression-tested:

- keep small Activity-local classes in `main.py`; or
- move genuinely reusable cross-Activity primitives into a reviewed `greia_platform` SDK module.

This is known platform debt, not desired long-term architecture.

---

## 11. Lifecycle READY and STOP

Use:

```python
from greia_platform.activity_api import (
    activity_stop_requested,
    mark_activity_ready,
)
```

Call READY only after the child has a usable surface and essential state/assets are ready.

Long-running loops should cooperate with graceful stop:

```python
while running and not activity_stop_requested():
    ...
```

Greia retains forced-termination authority.

Typical Pygame structure:

```python
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# load essential state/assets
mark_activity_ready()

while running and not activity_stop_requested():
    for event in pygame.event.get():
        ...
    ...
    pygame.display.flip()
    clock.tick(30)
```

Do not make `pygame.QUIT` the child’s only exit path.

---

## 12. Durable storage

Use:

```python
from greia_platform.activity_api import get_storage
storage = get_storage()
```

KV:

```python
value = storage.kv_get("key", default)
storage.kv_set("key", value)
storage.kv_delete("key")
storage.kv_list()
```

Private files:

```python
storage.file_write_atomic("drawing.png", png_bytes)
data = storage.file_read("drawing.png")
storage.file_list()
storage.file_delete("drawing.png")
```

Checkpoint/info:

```python
storage.info()
storage.checkpoint()
```

Values must be portable JSON. Private filenames are logical relative names. Never persist host absolute paths or bypass Greia Storage.

Current Phase-0 policy is approximately:

```text
32 MiB namespace quota
2 MiB KV area
256 KiB one KV value
16 MiB one private file
512 private files
```

`runtime/storage-policy.toml` is authoritative.

### Creation-data rule

A creation tool may refuse a new creation when bounded library/quota limits are reached, but it must **never silently evict an older child creation** to manufacture space.

On save failure, keep current in-memory work intact where practical and expose a child-safe failure state. Do not disguise failure as success.

---

## 13. Events, scores and progression

Use:

```python
from greia_platform.activity_api import emit_activity_event
```

Example:

```python
emit_activity_event(
    "maze.completed",
    idempotency_key=f"maze:{maze_id}:complete",
    payload={"maze_id": maze_id},
)
```

Rules:

- event ID must be declared in the manifest;
- one logical fact gets a stable idempotency key;
- payload is small portable JSON-compatible data;
- event protocol currently has a hard **64 KiB encoded message ceiling**;
- score direction comes from manifest definition;
- Greia owns reward/progression economics;
- never write platform history/progression databases directly.

Not every creative tool needs to emit a progression event merely because it saves work. Do not turn ordinary child creation into gamification by default.

---

## 14. Profile API

Read bounded active-profile presentation information via:

```python
from greia_platform.activity_api import get_active_profile
profile = get_active_profile()
```

Current data includes profile ID, display name and avatar ID.

Do not search profile directories or enumerate sibling children from the filesystem.

Profile mutation is privileged and should normally remain a system workflow.

---

## 15. Shared semantic assets

Canonical icon catalogue:

```text
assets/catalog/core_icons_v1.toml
```

Use:

```python
from greia_platform.activity_api import get_icon_path
icon_path = get_icon_path("unicorn", 128)
```

Do not hard-code `/opt/greia-os/assets/...` paths.

Current semantic IDs include concepts such as:

```text
book
robot
unicorn
globe
backpack
palette
abc_board
music_star
potions
treasure_chest
coins
star_trophy
map
magnifier
puzzle_pieces
car
garden
owl
dinosaur
rainbow
heart
yellow_star
check
close_button
```

Inspect the actual catalogue for the exact current set.

---

## 16. Theme API and least privilege

Use:

```python
from greia_platform.activity_api import get_theme
theme = get_theme()
```

Current `ResolvedTheme` exposes:

```text
preferences
background
panel
accent
text
accent_text
wallpaper_path
```

### Ordinary Activities

An ordinary unprivileged Activity currently receives Greia’s **canonical default resolved palette**. It does not receive the child’s raw customization directory or wallpaper merely to obtain colors.

This means ordinary Activities can look coherently Greia-native without requesting `customization.manage`.

### Trusted customization context

An Activity already granted profile customization authority receives the actual resolved customization state through the existing managed path.

### Current limitation

A safe read-only personalized theme snapshot for ordinary Activities is **not implemented yet**. Do not claim that ordinary Activities automatically inherit each child’s chosen wallpaper/colors.

If that feature is added later, prefer a bounded read-only theme snapshot over exposing raw customization files to all Activities.

---

## 17. Shared Activity UI primitives

The first deliberately small shared UI layer is:

```text
src/greia_platform/activity_ui.py
```

Current primitives include:

- `ChildUiMetrics` — 1024×600-first proportional metrics;
- large toolbar-button geometry;
- cached semantic-icon loading/scaling;
- rounded icon-button rendering;
- small shared symbols currently justified by real consumers;
- bounded RGB `mix()`.

Initial real consumers:

```text
activities/writing
activities/painting
```

This is **not** a general widget toolkit. There is no accepted retained widget tree, layout DSL, scene system or animation framework.

Extraction rule:

1. identify real duplication in two or more Activities;
2. extract the smallest stable primitive;
3. keep cost bounded on C0 hardware;
4. add provider-free tests where meaningful;
5. update this skill.

Do not invent abstractions before real Activities need them.

---

## 18. Runtime asset discipline

For Activity-owned assets:

- ship runtime derivatives, not giant masters;
- size near actual display use;
- do not duplicate Greia core icons;
- preload/decode bounded essential assets;
- `convert()`/`convert_alpha()` after display initialization where appropriate;
- cache scaled variants;
- cache fonts and unchanged rendered text;
- preserve aspect ratio unless distortion is intentional;
- avoid thousands of tiny files.

---

## 19. Performance canon

The extreme reference assumptions remain roughly:

```text
old Atom-class CPU
~768 MiB RAM
1024×600
small internal storage
```

until physical inventory/certification supersedes them.

Do not perform expensive or variable work every frame without measurement.

Avoid per-frame:

- disk reads;
- image decoding;
- font construction;
- large scaling;
- storage writes;
- directory scans;
- network operations;
- large temporary object graphs;
- unbounded particles/entities/history.

Prefer:

- load/convert once;
- cache fonts/images/scales/static text;
- update changed state only;
- bounded object/history counts;
- elapsed-time animation;
- 30-FPS-class pacing where suitable;
- durable writes on meaningful/debounced state transitions.

### Current creative-tool examples

Writing:

- large font objects are created once;
- visual line layout is rebuilt only when text changes;
- durable writes are debounced rather than per keypress;
- undo history is bounded.

Painting:

- pointer strokes render directly into one bounded canvas surface;
- recent undo stores bounded strokes, not unlimited full-screen snapshots;
- old undo strokes fold into a base canvas;
- PNG encoding happens only on save/transition, not each event/frame;
- gallery thumbnails are cached.

### Frame-rate guidance

Stable **30 FPS** is a sensible default for most 2D Greia Activities. It remains authoring guidance until measured release thresholds exist.

---

## 20. Resolution/layout rules

Design at 1024×600 first.

Use `ChildUiMetrics` for shared large-toolbar geometry where appropriate.

Good patterns:

- derive geometry from actual surface dimensions;
- maintain safe margins;
- keep hit targets large;
- cache resolution-dependent surfaces;
- use only meaningful breakpoints;
- never build a huge internal 1080p framebuffer and downscale it every frame on C0.

Higher-capability machines may enhance quality without changing Activity identity.

---

## 21. Input design

Require only what is necessary.

- pointer and touch should share target geometry where practical;
- do not assume tap-to-click;
- keyboard alternatives are welcome but should not hide the only path;
- irreversible actions need deliberate child-safe interaction;
- do not open `/dev/input` or call X11 input utilities.

Touch declared as optional is not the same as touch acceptance. Handle actual touch event semantics and test them before claiming support.

Writing naturally requires keyboard input. Painting must remain usable without a keyboard.

---

## 22. Audio design

Audio should enhance rather than gate interaction.

- preload short sounds;
- bound simultaneous channels;
- degrade gracefully when optional audio is absent;
- never make sound the only essential state signal;
- do not implement private system-volume authority.

---

## 23. Error/recovery behavior

An Activity must not reveal Linux internals to children.

- handle expected content/storage failures at a child-safe boundary;
- do not display tracebacks or terminals;
- do not launch a shell for debugging;
- let unexpected crashes terminate so Greia Supervisor can recover;
- do not catch `BaseException` and spin forever;
- honor STOP requests;
- preserve current child work in memory when a durable write fails where practical.

Development diagnosis belongs in logs/screenshot tooling.

---

## 24. Portable state

Good durable state:

```text
UTF-8 text
JSON-compatible logical state
PNG/JPEG child creations where explicitly appropriate
procedural seed/version
small Activity-local preferences
```

Bad durable state:

```text
pygame Surface
pickle/native object graph
absolute host path
memory address
open descriptor/socket
machine ID
GPU/CPU-specific object
```

Persist the logical creation, not the implementation object.

---

## 25. Do not build a second platform inside an Activity

An Activity must not independently replace:

- child profiles;
- global progression/reward ledger;
- package installation/update;
- backup/restore;
- OS settings;
- hardware configuration;
- filesystem browser;
- generic privileged networking;
- shell/terminal;
- launcher/app store.

Reusable platform concerns belong in Greia.

---

## 26. Code-quality canon

Prefer readable, testable boundaries over procedural sprawl.

Useful conceptual separations:

```text
Application
Scene/state
Domain model
Renderer/view
Input mapping
Asset cache
Greia storage/service adapter
```

Use classes/polymorphism where they represent real interchangeable behavior. Do not create inheritance for decoration.

Because the current Python direct-file launch seam limits package-relative modules, a small Activity may temporarily keep several clean classes in one `main.py`. That is preferable to a monolithic function and preferable to unsupported import hacks.

---

## 27. Provider-free tests

Test logic that does not require installed display/session hardware, such as:

- procedural generation;
- state transitions;
- text-buffer behavior;
- save/index ordering;
- quota/library refusal semantics;
- bounded undo/history;
- layout geometry;
- color/math helpers;
- score/fact generation;
- collision/math.

Do not replace qualitative visual judgment with brittle pixel-exact screenshot tests or naive keyword checks.

Visual acceptance belongs in screenshots/real interaction; semantic invariants belong in deterministic tests.

---

## 28. Validation

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py path/to/activity
```

For bundled repository Activities, the validator uses built-in source trust. Arbitrary external directories remain `DEVELOPER_UNSIGNED`; validation is not a trust upgrade.

Integrated gate:

```bash
make verify
```

Do not claim either command passed unless it actually executed against the stated checkout.

Standalone source validation does not prove installed sandbox/storage/display/hardware behavior.

---

## 29. Local/windowed boundary

Local/windowed execution can accelerate iteration but does not prove:

- installed Bubblewrap isolation;
- storage/event broker transport;
- display-session ownership;
- developer-remote control;
- low-memory performance;
- Acer/Pi behavior.

A modern Mac/PC is not acceptance evidence for the low-end reference machine.

---

## 30. Remote developer loop

Once the developer image is actually accepted, read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Typical loop:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py deploy path/to/activity
python3 tools/greia_remote.py screenshot out/before.png
# key / mousemove / click / type
python3 tools/greia_remote.py screenshot out/after.png
python3 tools/greia_remote.py logs --service launcher --lines 500
```

Do not use `--replace-system` merely to bypass normal unsigned validation/trust failures.

Do not claim the loop works on physical hardware until current evidence says so.

---

## 31. Performance acceptance loop

For a nontrivial game or creative tool:

1. validate manifest/import policy;
2. run provider-free logic tests;
3. exercise local/windowed behavior if useful;
4. deploy to accepted developer hardware when available;
5. test at 1024×600;
6. capture startup/first usable frame;
7. exercise the busiest realistic scene/document/canvas interaction;
8. exercise autosave and failure/quota behavior;
9. collect CPU/RSS/process evidence when tooling allows;
10. inspect logs for stalls/errors;
11. optimize measured hotspots;
12. repeat and preserve before/after evidence.

Do not redefine the hardware floor to preserve an expensive effect.

---

## 32. Creative-tool durability checklist

For text/art/music/project tools specifically:

- creation IDs are durable and independent of display labels;
- save data lives only in Greia Storage;
- writes are atomic/debounced;
- leaving/switching forces a meaningful save attempt;
- save failure remains visible and does not destroy in-memory work;
- library pressure never silently evicts older work;
- galleries use logical creation records, not filesystem browsing;
- export is a future typed platform workflow, not a raw child file picker;
- backup inclusion follows Greia logical backup semantics when implemented.

---

## 33. Definition of done — new Activity

Before claiming source-ready:

- stable canonical ID chosen;
- manifest validates;
- package version/storage schema deliberate;
- required/optional capabilities minimal;
- no unnecessary privileged permissions;
- curated imports only;
- READY at correct point;
- STOP honored;
- Greia Storage used;
- no silent creation eviction/deletion;
- events used only where meaningful;
- shared icons/theme/UI primitives used appropriately;
- assets optimized;
- 1024×600 usable by design;
- controls large and child-appropriate;
- hot-loop work bounded;
- no per-frame durable writes;
- errors hide Linux/Python internals;
- meaningful provider-free tests added;
- standalone validator actually passes;
- integrated `make verify` actually passes when claiming integration;
- required VM/physical evidence is completed and accurately scoped.

---

## 34. Definition of done — modification

For an existing Activity:

- preserve canonical ID unless migration is explicit;
- decide package-version impact;
- decide storage-schema impact;
- preserve saves or use reviewed migration;
- do not silently remove educational events/skills;
- compare resource behavior for substantial visual changes;
- test changed logic plus startup/exit/storage basics;
- repeat installed visual/hardware acceptance when affected.

---

## 35. Current Phase-0 creative references

### Writing

```text
id: org.greia.writing
source: activities/writing/
core: large Unicode text, wrapping/caret/navigation, bounded undo, visual gallery, debounced UTF-8 saves
```

### Painting

```text
id: org.greia.painting
source: activities/painting/
core: large raster canvas, fixed color palette, three brush sizes, eraser, bounded stroke undo, PNG saves/gallery
```

These are **source implementations under active validation**, not yet hardware-certified examples. Read:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

for exact product acceptance state.

---

## 36. Maintaining this skill

Update this file in the same tranche whenever any of these change:

- manifest schema;
- runtime API/version;
- capability or permission vocabulary;
- Activity trust semantics relevant to authors;
- Python import/entrypoint/module behavior;
- lifecycle API;
- Storage API/policy semantics;
- event/progression API/protocol limits;
- package validation/size rules;
- shared asset catalogue;
- theme API or personalization semantics;
- shared UI/graphics/audio primitives;
- developer deployment workflow;
- reference-hardware/performance requirements;
- `.greiaactivity` when implemented;
- Web runtime/SDK when implemented.

If implementation makes this skill materially wrong, the implementation tranche is not completely documented until this skill is corrected.
