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

Use this skill whenever the task is to:

- create a new Greia Activity;
- modify or review an existing Activity;
- port an educational game/tool into Greia;
- design `activity.toml` metadata;
- use Greia lifecycle/storage/event/profile/theme/asset APIs;
- optimize rendering/input/audio for Greia hardware;
- validate an Activity package;
- deploy/test an Activity on a developer Greia machine.

For OS/platform/installer work, use:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Read `docs/DOCUMENTATION.md` for documentation precedence.

This skill summarizes implemented contracts but does not outrank their source owners.

---

## 2. Implemented now versus future architecture

Do not confuse conceptual architecture examples with the current Activity SDK.

| Area | Current status for Activity authors |
|---|---|
| Activity package during development | directory containing `activity.toml` |
| manifest syntax | TOML, parsed by `src/greia_platform/activities.py` |
| implemented runtime | Python/Pygame |
| runtime API version | read `runtime/child-runtime.toml`; currently `0.1` |
| lifecycle | implemented READY/STOP channel through `activity_api` |
| durable storage | implemented Greia broker client |
| events/progression facts | implemented Greia event client/broker |
| shared icons | implemented semantic core icon catalogue |
| theme read API | implemented |
| general shared Activity widget toolkit | **not implemented yet** |
| Web Activity runtime/JS SDK | architectural/planned, not current authoring target |
| `.greiaactivity` archive installation format | future implementation phase |
| `.greiabackup` author-facing format | future implementation phase |
| measured C0/C1/C2/C3 compatibility thresholds | not finalized; design against current reference floor |

If architecture documentation shows YAML manifests, `Greia.storage.*` JavaScript, WebGL capability examples, archive layouts or future package signatures, treat them as **semantic direction**, not current copy-paste code.

---

## 3. Mandatory source-of-truth read set

Before authoring or materially changing an Activity, inspect the current versions of:

```text
AGENTS.md
docs/DOCUMENTATION.md
skills/greia-activity-authoring/SKILL.md
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/storage_client.py
src/greia_platform/event_client.py
src/greia_platform/event_protocol.py
runtime/child-runtime.toml
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
```

When progression/reward behavior matters also inspect:

```text
runtime/progression-policy.toml
```

Useful real built-in references include:

```text
activities/shape_garden/activity.toml
activities/shape_garden/main.py
```

Reference Activities are examples, not immutable style law. Prefer the current SDK/validator over copying an old implementation quirk.

---

## 4. Product canon

A Greia Activity is one supervised child-facing experience inside the Greia platform. It is **not** a free-standing desktop/Linux program.

Non-negotiable principles:

- **Activity is runtime-neutral.** Python/Pygame is the current runtime implementation, not the product identity.
- **Linux internals are not Activity APIs.** Do not depend on X11, DRM, `/dev/*`, systemd, shell commands, distro paths or CPU architecture.
- **Greia owns identity, session lifetime, durable namespace, effective authority and global progression.**
- **Offline-first.** Core play/use and saves must work without Internet access.
- **Child-first.** The Activity should feel native to Greia, not like a desktop app launched inside it.
- **Low-resource hardware is first-class.** Performance is correctness.
- **Portable state.** Durable state must be architecture-neutral.
- **Curated runtime only.** No per-Activity package manager/venv/private dependency environment.

---

## 5. Child UX canon

Design first for young children and 1024×600.

Prefer:

- direct manipulation;
- large forgiving hit targets;
- immediate visual/audio feedback;
- semantic Greia icons for shared concepts;
- minimal required reading for ordinary navigation;
- obvious safe return/finish affordances;
- consistent placement and interaction patterns;
- localized text when text is educationally purposeful;
- pointer/touch geometry that can share the same targets;
- graceful keyboard alternatives where useful.

Avoid:

- menu bars, window chrome and desktop metaphors;
- tiny controls requiring precision;
- file pickers or Linux-path concepts;
- keyboard shortcuts as the only child path;
- dense adult settings UI;
- modal traceback/error walls;
- navigation that assumes reading ability unnecessarily;
- hidden exits or states that trap the child;
- unbounded flashing/particles/noise.

Text is not forbidden. Unnecessary reading dependency is.

---

## 6. Package contract

Current development packages are directories containing `activity.toml`.

Typical Python shape:

```text
my_activity/
├── activity.toml
├── main.py
└── assets/
    └── ... Activity-specific runtime assets only
```

The authoritative package validation policy is:

```text
runtime/child-runtime.toml
src/greia_platform/activities.py
```

At this review the hard validated package ceiling is **50 MiB** (`52428800` bytes). It is a ceiling, not a target.

Do not ship forbidden/private runtime material such as:

- `.git`, `.hg`, `.svn`;
- `node_modules`, `vendor`, `vendored`;
- virtual environments;
- `requirements.txt`, `pyproject.toml`, setup files;
- wheels/eggs/shared libraries/native installers;
- executable shell scripts/binaries;
- cached bytecode;
- symlinks;
- runtime source assets that are not needed by the child package.

Do not weaken validation merely to get an Activity accepted.

---

## 7. Stable Activity identity

The Activity ID is durable platform identity; the title is presentation.

Current canonical IDs are lower-case reverse-DNS-style identifiers with at least three components, for example:

```text
org.greia.shape-garden
org.example.maze-garden
```

Do not casually rename a released/durable Activity ID.

`legacy_ids` are trusted built-in migration aliases. Ordinary developer/unsigned packages cannot use legacy aliases to impersonate built-ins.

Package version and storage schema version are separate.

---

## 8. Current `activity.toml` pattern

`src/greia_platform/activities.py` is authoritative.

A current Python manifest can follow this pattern:

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

Before using the example, re-check the parser/runtime file. Do not freeze prose examples into a competing schema.

### Event kinds currently accepted

```text
completion
creation
milestone
score
```

A score event requires:

```text
higher_better
```

or:

```text
lower_better
```

Non-score events must not declare `score_order`.

Activities declare/report facts. They do not author arbitrary global reward amounts.

---

## 9. Capabilities, permission requests and effective grants

These are different concepts.

### Capability vocabulary

Current allowed capability strings are owned by:

```text
runtime/child-runtime.toml
```

At this review:

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

Do not invent capability names.

Use **required** only if the Activity genuinely cannot function without it. Use **optional** for progressive enhancement.

### Permission request vocabulary

Current permission request strings are also owned by `child-runtime.toml`. At this review:

```text
customization.manage
profile.manage_own
removable_media.read
```

A manifest request is **not authority**.

### Environment is not the security boundary

`GREIA_ACTIVITY_CAPABILITIES` and the SDK `_require_capability()` check are Activity-side usability checks only. Activity code can mutate its own environment; therefore environment strings cannot mint privilege.

Effective authority is enforced outside the Activity process by trusted Greia supervision/broker/sandbox policy.

Ordinary remotely deployed `DEVELOPER_UNSIGNED` Activities are deliberately not a path to privileged system permissions.

If an Activity appears to need privileged authority, first ask whether that operation belongs in a typed Greia platform service rather than in the Activity.

---

## 10. Python runtime/import policy

Greia uses one curated shared Python runtime.

Inspect the current `[python]` allow/forbid declarations in:

```text
runtime/child-runtime.toml
```

Current curated roots include selected standard-library modules plus `pygame`, `PIL` and `greia_platform`.

Do not build Activity logic around forbidden/general host-authority modules such as arbitrary process execution, raw sockets, ctypes/native loading, package installation or host filesystem discovery.

If a reusable platform function is missing, extend a typed Greia service/SDK boundary rather than smuggling Linux authority into the Activity.

---

## 11. Lifecycle: READY and STOP

Use:

```python
from greia_platform.activity_api import (
    activity_stop_requested,
    mark_activity_ready,
)
```

### READY

Call:

```python
mark_activity_ready()
```

only after the Activity has created its usable child-facing surface and essential startup assets/state are ready.

Do not call READY at import time just to satisfy the supervisor.

### STOP

Long-running loops should cooperate with graceful return:

```python
while running and not activity_stop_requested():
    ...
```

Greia retains forced-termination authority. Activity cooperation improves graceful exit; it is not the lifecycle security boundary.

### Minimal Pygame loop shape

The real built-in `shape_garden` demonstrates the current fullscreen/30-FPS/lifecycle pattern. A generic shape is:

```python
import pygame
from greia_platform.activity_api import activity_stop_requested, mark_activity_ready


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()

    # Load/convert essential assets and initialize child-visible state here.
    mark_activity_ready()

    running = True
    while running and not activity_stop_requested():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # update bounded state
        # render
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0
```

Adapt child exit/input behavior to Greia UX; do not blindly copy desktop `QUIT` assumptions as the only exit path.

---

## 12. Durable storage

Use the Greia brokered storage client:

```python
from greia_platform.activity_api import get_storage

storage = get_storage()
```

### JSON-compatible key/value state

```python
level = storage.kv_get("current_level", 1)
storage.kv_set("current_level", 2)
removed = storage.kv_delete("obsolete")
keys = storage.kv_list()
```

Values must be portable JSON (`allow_nan=False`). Do not use pickle/native object graphs as official durable state.

### Private files

```python
storage.file_write_atomic("drawing.png", png_bytes)
data = storage.file_read("drawing.png")
files = storage.file_list()
removed = storage.file_delete("drawing.png")
```

Use logical relative names, never host absolute paths.

### Information/checkpoint

```python
info = storage.info()
checkpoint_token = storage.checkpoint()
```

The client transport accepts large bounded payloads, but that is not permission to waste memory/storage. Inspect service quota/info and design compact state.

Do not bypass Greia storage with an arbitrary persistent filesystem location; that breaks quota/migration/backup semantics.

---

## 13. Events, scores and progression

Use:

```python
from greia_platform.activity_api import emit_activity_event
```

Completion example:

```python
receipt = emit_activity_event(
    "maze.completed",
    idempotency_key=f"maze:{maze_id}:complete",
    payload={"maze_id": maze_id},
)
```

Score example:

```python
receipt = emit_activity_event(
    "maze.time",
    idempotency_key=f"maze:{maze_id}:time:{attempt_id}",
    score=elapsed_seconds,
)
```

Rules:

- event ID must be declared in the manifest;
- use a stable idempotency key for one logical fact;
- payload must be portable JSON-compatible data;
- keep payloads small and semantic, not state dumps;
- the event protocol has a hard **64 KiB encoded message ceiling** at this review;
- score direction comes from the manifest event definition;
- Greia owns reward/progression policy;
- never write directly into platform history/progression databases.

The returned receipt may report duplicate status and platform-computed reward deltas. Treat those as the broker's result for the submitted fact; do not attempt to modify global reward authority locally.

---

## 14. Profile API

Read the active profile's bounded presentation data via:

```python
from greia_platform.activity_api import get_active_profile

profile = get_active_profile()
```

Current result contains fields such as:

```text
profile_id
display_name
avatar_id
```

Do not search profile directories or infer sibling users from the host filesystem.

Profile-changing helpers require explicit capability/permission context and are normally system/trusted workflows, not ordinary game logic.

---

## 15. Shared visual assets

The canonical semantic icon catalogue is:

```text
assets/catalog/core_icons_v1.toml
```

Resolve an icon via:

```python
from greia_platform.activity_api import get_icon_path

icon_path = get_icon_path("unicorn", 128)
```

Do not hard-code `/opt/greia-os/assets/...` paths.

The SDK chooses the available 64/128/256 asset tier based on the requested size. Inspect the catalogue for exact IDs; do not invent filenames.

Current examples include concepts such as:

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

Use platform-shared assets for platform-wide semantics. Bundle Activity-specific artwork only when it genuinely belongs to that Activity.

---

## 16. Theme integration

Use:

```python
from greia_platform.activity_api import get_theme

theme = get_theme()
```

The current `ResolvedTheme` exposes:

```text
preferences
background       # RGB tuple
panel            # RGB tuple
accent           # RGB tuple
text             # RGB tuple
accent_text      # RGB tuple chosen for contrast
wallpaper_path   # managed Path or None
```

Use those colors where platform visual continuity is appropriate.

Do not duplicate the platform palette constants privately when you actually want the child's Greia theme.

`runtime/theme-defaults.toml` owns the canonical palette/default IDs.

An Activity is still allowed to have a deliberate game/art visual identity; theme integration should strengthen coherence, not erase necessary contrast/gameplay semantics.

---

## 17. Shared UI/graphics library status

At this review Greia has shared semantic assets/theme services, but **no accepted general-purpose Activity widget/layout/animation toolkit**.

Do not fabricate imports such as `greia_ui.Button` because an architecture description sounds like one should exist.

When multiple Activities repeatedly need the same optimized child control/layout/font-cache/transition/audio-cue primitives, propose a reviewed shared SDK library. Once accepted, update this skill and prefer the shared implementation over private clones.

Until then, keep Activity-local UI infrastructure small, reusable within the Activity, and compatible with the performance rules below.

---

## 18. Runtime asset discipline

For Activity-specific assets:

- ship only runtime-needed derivatives;
- size images near their real display use rather than shipping giant masters;
- avoid duplicate copies of Greia core icons;
- preload/decode bounded essential assets during startup;
- call `convert()`/`convert_alpha()` after display creation where appropriate;
- cache scaled variants used repeatedly;
- cache fonts and rendered static text;
- preserve aspect ratio unless distortion is intentional;
- avoid thousands of tiny files when a bounded simpler representation works;
- keep master/source artwork outside the runtime package when not needed by the child.

---

## 19. Performance canon

Performance is part of correctness.

The extreme reference assumptions remain roughly:

```text
old Atom-class CPU
~768 MiB RAM
1024×600 display
small internal storage
```

until exact physical inventory/certification supersedes the estimates.

### Hot-loop rule

Do not perform expensive/variable work every frame unless measured and justified.

Avoid per-frame:

- disk reads;
- image decode/load;
- font construction;
- large image scaling;
- rendering unchanged expensive text;
- directory scanning;
- storage broker writes;
- network operations;
- creation of large temporary object graphs;
- unbounded entity/particle spawning.

Prefer:

- load/convert once;
- cache fonts/images/scales/static text;
- update changed state only;
- bounded entity/particle counts;
- elapsed-time animation rather than frame-count assumptions;
- `pygame.time.Clock()` or equivalent pacing;
- meaningful-event durable writes rather than every-frame saves;
- optional richer effects rather than raising the hardware floor.

### Frame-rate guidance

A stable **30 FPS** is a sensible default authoring target for most 2D child Activities on the low-end reference class. It is currently guidance, not a formally measured release threshold.

Do not burn CPU/GPU chasing 60 FPS when interaction quality does not benefit.

### Startup guidance

Get to a usable child-facing screen promptly, then call READY. Large optional content can load lazily only if it does not produce input stalls or nondeterministic failures.

---

## 20. Resolution/layout performance

Design at **1024×600 first**.

Good patterns:

- derive layout from the actual surface size;
- use a small number of meaningful breakpoints only when necessary;
- cache resolution-dependent surfaces and rebuild only on size change;
- use integer/rational scaling for pixel art when suitable;
- keep targets large with safe margins;
- avoid rendering a huge virtual 1080p scene and downscaling the entire framebuffer every frame on the netbook.

Higher-capability machines may enhance quality without creating a separate product identity.

---

## 21. Input design

Require only the capabilities you need.

- pointer and touch should share target geometry where practical;
- keyboard may offer alternatives but should not become a hidden mandatory child path;
- do not assume tap-to-click is enabled;
- debounce/ignore accidental repeated actions where appropriate;
- make irreversible/destructive child actions difficult to trigger accidentally;
- do not open raw input devices or call X11 input utilities.

Greia owns the platform input/session boundary.

---

## 22. Audio design

Audio should enhance rather than gate essential interaction.

- preload short common effects;
- avoid repeatedly decoding the same sound;
- bound simultaneous channels/effects;
- degrade gracefully when `audio.basic` is optional/unavailable;
- do not use audio as the only signal for an essential state;
- do not implement a private system-volume authority.

---

## 23. Error/recovery behavior

An Activity must not reveal Linux internals to children.

- handle expected content/state errors at a child-safe boundary;
- never intentionally show Python tracebacks/terminal output in the child UI;
- do not launch a shell for debugging;
- allow unexpected crashes to terminate so Greia can record/recover them;
- do not catch `BaseException` and spin forever hiding fatal state;
- honor stop requests;
- keep durable writes atomic through Greia storage;
- inspect failures through developer logs/screenshot tooling.

---

## 24. Portable state/randomness

Save logical state, not runtime objects.

Good durable state:

```text
level number
puzzle seed/version
child drawing bytes
Activity-local settings
logical score/progress state
```

Bad durable state:

```text
pygame Surface
pickle blob
absolute host path
memory address
open descriptor/socket
machine ID
GPU/CPU-specific object
```

For reproducible procedural content, persist explicit seeds and versioned generation parameters rather than huge derived snapshots where practical.

---

## 25. Do not build a second platform inside an Activity

An Activity must not independently replace:

- child profiles;
- global reward/progression services;
- package installation/update;
- backup/restore;
- OS settings;
- hardware configuration;
- generic networking authority;
- filesystem browser;
- shell/terminal;
- app store/launcher.

Reusable cross-Activity concerns belong in Greia platform/SDK design.

---

## 26. Code-quality canon

Prefer readable boundaries and testable domain logic over procedural sprawl.

Useful separations often include:

```text
Activity/Application
Scene/State
Domain model
Renderer/View
Input mapping
Asset cache
Audio controller
Greia service adapter
```

Use classes/polymorphism where there are genuinely interchangeable behaviors (scenes, tools, challenge types, rendering strategies). Do not manufacture inheritance for decoration.

Keep domain/simulation logic decoupled from rendering when that improves testing, portability and optimization.

Avoid broad mutable globals; narrow immutable/cached resources are acceptable when clear.

---

## 27. Provider-free tests

Add deterministic tests for logic that does not require the installed display/session stack, for example:

- procedural generation;
- scoring/fact creation;
- collision/math;
- state transitions;
- save encode/decode;
- content rules;
- bounded randomness;
- layout calculations.

Do not replace qualitative visual/content judgment with naive regex/word-count checks.

Do not create brittle pixel-exact screenshots for every visual detail. Use semantic unit tests for logic/contracts and visual/hardware acceptance for appearance.

---

## 28. Validation

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py path/to/activity
```

For a bundled Activity under the repository `activities/` root, the validator uses built-in trust semantics; an arbitrary external path remains `DEVELOPER_UNSIGNED`. Invoking validation is not a trust upgrade.

Run repository verification before claiming integrated source-ready work:

```bash
make verify
```

Remove cached bytecode/forbidden artifacts before validation.

A passing standalone validator does not prove installed sandbox/lifecycle/display/hardware behavior.

---

## 29. Local/windowed development boundary

Use local/windowed/source execution for rapid iteration where supported, but do not treat it as proof of:

- installed Bubblewrap/isolation;
- storage/event broker transport;
- display-session ownership;
- developer-remote behavior;
- low-memory performance;
- Acer/Pi behavior.

An Activity that is smooth on a modern development Mac/PC can still fail Greia requirements because of memory, asset decoding, 1024×600 layout, import restrictions or SDL/backend behavior.

---

## 30. Remote developer test loop

Once an explicit developer image is actually installed/accepted, read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Typical loop:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py deploy path/to/activity
python3 tools/greia_remote.py screenshot out/activity-before.png
# drive the UI with key / mousemove / click / type
python3 tools/greia_remote.py screenshot out/activity-after.png
python3 tools/greia_remote.py logs --service launcher --lines 500
```

For ordinary Activity development, never use `--replace-system` merely because unsigned deployment rejects the package. Fix the Activity/trust request.

Do not claim this remote loop works on hardware until the current handover records real acceptance evidence.

---

## 31. Performance acceptance loop

For a nontrivial game/animation:

1. validate package/imports;
2. run provider-free logic tests;
3. exercise local/windowed behavior;
4. deploy to the developer target when hardware acceptance is available;
5. test at 1024×600;
6. capture startup/first usable screen;
7. exercise the busiest realistic scene;
8. observe frame pacing/responsiveness;
9. collect RSS/CPU evidence when tooling allows;
10. check logs for stalls/errors;
11. optimize measured hotspots;
12. repeat and preserve before/after evidence.

Simplify expensive effects or make them progressive enhancement rather than redefining the reference hardware away.

---

## 32. Definition of done — new Activity

Before claiming a new Activity source-ready:

- stable canonical ID chosen;
- `activity.toml` validates;
- package/runtime version and save schema chosen deliberately;
- required/optional capabilities minimal and accurate;
- no unnecessary privileged permission requests;
- curated-runtime imports only;
- no private dependency environment;
- READY emitted only when usable;
- STOP honored in long-running loop;
- Greia storage used for durable state;
- normalized events declared/emitted where progression facts exist;
- shared icons/theme used where appropriate;
- Activity assets optimized;
- 1024×600 usable;
- child navigation does not unnecessarily require reading;
- frame work and entity counts bounded;
- no per-frame durable writes;
- errors do not expose Linux/Python internals;
- meaningful provider-free logic tests added;
- standalone Activity validation passes;
- integrated `make verify` passes when repository work is ready;
- hardware/VM evidence is performed when required and labelled accurately.

---

## 33. Definition of done — modification

For an existing Activity:

- preserve canonical ID unless an explicit migration decision exists;
- decide whether package version changes;
- decide whether storage schema changes;
- preserve existing saves or use a reviewed migration mechanism when available;
- do not silently remove educational skills/events or reverse score semantics;
- compare performance/resource behavior for significant visual/content changes;
- test changed logic plus startup/exit/storage basics;
- redeploy/capture hardware evidence when the change affects installed behavior.

---

## 34. Maintaining this skill

Update this file in the same tranche whenever any of these change:

- Activity manifest schema;
- runtime API version;
- allowed capabilities/permission requests;
- effective trust behavior relevant to authors;
- Python import/runtime policy;
- lifecycle API;
- storage API;
- event/progression API/protocol limits;
- package validation/size rules;
- shared asset catalogue/resolution API;
- theme API/palette policy;
- accepted shared UI/graphics/audio library;
- developer deployment workflow;
- reference hardware/performance requirements;
- `.greiaactivity` implementation when it becomes real;
- Web runtime/SDK when it becomes real.

If source/runtime changes make this skill materially wrong, the change is incompletely documented until the skill is corrected.
