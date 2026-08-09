---
name: greia-activity-authoring
description: Canonical agent skill for designing, implementing, validating, optimizing, and remotely testing Greia Activities against the current Greia SDK and platform contracts.
---

# Greia Activity Authoring Skill

**Audience:** coding agents and human developers creating or modifying Greia Activities  
**Status:** living canonical authoring skill; keep synchronized with the implemented SDK  
**Last reviewed:** 2026-08-09  

---

## 1. When to use this skill

Use this skill whenever the task is to:

- create a new Greia Activity;
- modify an existing Activity;
- port an educational game/tool into Greia;
- design Activity manifest metadata;
- use Greia storage/events/profile/theme/assets APIs;
- optimize an Activity for Greia hardware;
- validate/package/deploy an Activity;
- remotely test an Activity on a Greia developer machine.

For OS/platform/installer work, use `docs/agents/GREIA_AGENT_OPERATIONS.md` instead.

---

## 2. Mandatory source-of-truth read set

Before authoring an Activity, inspect the current versions of:

```text
AGENTS.md
skills/greia-activity-authoring/SKILL.md
src/greia_platform/activities.py
src/greia_platform/activity_api.py
src/greia_platform/storage_client.py
src/greia_platform/event_client.py
runtime/child-runtime.toml
runtime/theme-defaults.toml
assets/catalog/core_icons_v1.toml
```

When educational events/progression are involved also inspect:

```text
runtime/progression-policy.toml
```

Do not assume this skill is newer than the implementation. If those files changed incompatibly, update this skill in the same tranche.

---

## 3. Product canon

A Greia Activity is not a free-standing Linux program and not a desktop application.

It is one supervised child-facing Activity inside the Greia platform.

### Non-negotiable principles

- **Activity is runtime-neutral.** Python/Pygame is the current implemented runtime, not the platform identity.
- **Linux details are not Activity APIs.** Do not depend on X11, DRM, device files, systemd, shell commands, distro paths or CPU architecture.
- **Greia owns identity, lifecycle, storage, sessions, permissions and global progression.**
- **Offline-first.** Core play/use and saves must work without Internet access.
- **Child-first.** The experience should feel like part of Greia, not like a desktop application embedded inside it.
- **Low-resource hardware is first-class.** Optimize for the extreme C0/reference floor rather than assuming a modern PC.
- **Portable state.** Save data must survive moves between i386, amd64 and ARM64 where the Activity is supported.
- **No private dependency environment.** Activities use the curated Greia runtime.

---

## 4. Child UX canon

Default Activity design should favor young children and the appliance model.

### Prefer

- direct manipulation;
- large obvious targets;
- visual/audio feedback;
- consistent symbols and semantic Greia icons;
- minimal required reading for core navigation;
- repetition, discoverability and immediate feedback;
- forgiving input;
- obvious safe return/finish behavior;
- layouts that work at **1024×600** without scrolling a desktop-like viewport;
- language-neutral navigation where text is not educationally necessary;
- localized text when text is purposeful.

### Avoid

- menu bars, window chrome, file pickers or desktop metaphors;
- tiny controls designed for a precise mouse;
- keyboard shortcuts as the only path for a child;
- modal error text requiring adult interpretation;
- assumptions that every child can read;
- dense settings screens;
- unbounded flashing/particle effects;
- hidden exits that can trap the child in an Activity.

Text is allowed and often educationally useful; the rule is not “no text”. The rule is that ordinary child navigation should not depend on reading unnecessarily.

---

## 5. Package shape

Current development packages are directories discovered by an `activity.toml` file.

Typical shape:

```text
my-activity/
├── activity.toml
├── main.py
└── assets/
    ├── ...
```

Do not include:

- `.git`, `.hg`, `.svn`;
- `node_modules`, vendored dependency trees;
- virtual environments;
- `requirements.txt`;
- `pyproject.toml`;
- `setup.py`/`setup.cfg`;
- wheels, eggs, shared libraries or executable installers;
- shell scripts/executable files;
- caches/compiled bytecode;
- symlinks.

The authoritative forbidden paths/files/suffixes and maximum Activity bytes live in:

```text
runtime/child-runtime.toml
```

At the time of this review the maximum validated Activity package size is **50 MiB**. Treat that as a ceiling, not a target. Prefer far smaller packages.

---

## 6. Canonical Activity identity

Activity IDs are durable identity. Titles are presentation.

Current canonical IDs are lower-case reverse-DNS-style identifiers with at least three components, for example:

```text
org.greia.shape-garden
org.example.number-train
```

Do not casually rename an Activity ID after release or after durable saves depend on it.

Legacy aliases are reserved for trusted built-in migration and are not available to ordinary developer packages.

Versions and save-schema versions are separate concepts.

---

## 7. Current manifest contract

`src/greia_platform/activities.py` is authoritative for parsing and validation.

A current Python Activity manifest follows this semantic shape:

```toml
[activity]
id = "org.example.maze-garden"
legacy_ids = []
title_key = "activity.maze-garden.title"
version = "0.1.0"
icon = "puzzle_pieces"
languages = ["en", "it"]

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

[education]
categories = ["logic", "spatial"]
difficulty = 3

[[education.skills]]
id = "spatial-reasoning"
weight = 5

[[education.events]]
id = "maze.completed"
kind = "completion"

[[education.events]]
id = "maze.time"
kind = "score"
score_order = "lower_better"
```

Do not copy this blindly if the parser/schema has changed. Re-check `activities.py` and `child-runtime.toml` first.

### Current event kinds

The implemented manifest accepts:

```text
completion
creation
milestone
score
```

A `score` event must declare exactly one score order:

```text
higher_better
lower_better
```

Non-score events must not declare `score_order`.

Activities report facts; they do not declare arbitrary global reward amounts.

---

## 8. Capabilities versus permissions

These are deliberately separate.

### Capabilities

Capabilities describe runtime/hardware functions an Activity needs or can optionally enhance itself with.

Current allowed vocabulary is defined only by:

```text
runtime/child-runtime.toml
```

At this review it includes concepts such as:

```text
display
pointer
keyboard
touch
audio.basic
network
removable_media
power.controlled_shutdown
```

Do not invent a capability string.

Use required capabilities only when the Activity genuinely cannot function without them. Use optional capabilities for progressive enhancement.

### Permissions

Permissions request privileged platform operations. A request is **not a grant**.

Current allowed permission vocabulary is also defined by `runtime/child-runtime.toml` and includes narrow operations such as profile/customization/removable-media management.

Ordinary remotely deployed `DEVELOPER_UNSIGNED` Activities are intentionally refused if they request privileged permissions.

Do not design a normal Activity around privileged permission access unless the product requirement explicitly makes it a trusted system Activity.

---

## 9. Python runtime rules

Greia Phase 0 uses one curated shared Python runtime.

Before importing a module, inspect the current `[python]` allow/forbid lists in:

```text
runtime/child-runtime.toml
```

The intended authoring model includes standard-library modules selected by Greia plus platform-curated packages such as Pygame/Pillow and `greia_platform`.

Activities must not depend directly on modules that provide arbitrary OS/process/network authority when the runtime forbids them. In particular, do not design around direct shell/process execution, private package installation, ctypes/native code loading, arbitrary sockets or host filesystem discovery.

If an Activity needs a new platform function, add or extend a typed Greia platform/SDK service rather than smuggling Linux authority into the Activity.

---

## 10. Lifecycle API

Import lifecycle helpers from:

```python
from greia_platform.activity_api import (
    activity_stop_requested,
    mark_activity_ready,
)
```

### Ready

Call:

```python
mark_activity_ready()
```

only after the Activity has created a usable child-facing surface and completed essential startup.

Do not mark READY at module import merely to satisfy a watchdog.

### Stop

Long-running loops should check:

```python
if activity_stop_requested():
    running = False
```

and leave cleanly when practical.

Greia still owns forced termination. Activity cooperation improves graceful return but is not authoritative lifecycle control.

---

## 11. Durable storage

Use the runtime-neutral Greia storage client:

```python
from greia_platform.activity_api import get_storage

storage = get_storage()
```

### JSON-compatible KV state

```python
level = storage.kv_get("current_level", 1)
storage.kv_set("current_level", 2)
storage.kv_delete("old_key")
keys = storage.kv_list()
```

Values must be portable JSON. Do not use pickle/native Python object serialization as official durable state.

### Private files

```python
storage.file_write_atomic("drawing.png", png_bytes)
data = storage.file_read("drawing.png")
files = storage.file_list()
storage.file_delete("drawing.png")
```

Use logical relative names, not host absolute paths.

### Checkpoints/info

```python
checkpoint_token = storage.checkpoint()
info = storage.info()
```

Do not bypass Greia storage by inventing another persistent path. Greia needs to preserve quotas, migration and backup semantics.

---

## 12. Events and progression

Use:

```python
from greia_platform.activity_api import emit_activity_event
```

Example completion:

```python
emit_activity_event(
    "maze.completed",
    idempotency_key=f"maze:{maze_id}:complete",
    payload={"maze_id": maze_id},
)
```

Example score:

```python
emit_activity_event(
    "maze.time",
    idempotency_key=f"maze:{maze_id}:time:{attempt_id}",
    score=elapsed_seconds,
)
```

Rules:

- event ID must be declared in the manifest;
- use a stable idempotency key for one logical fact;
- payload must remain portable/JSON-compatible;
- Activity code reports facts/scores only;
- Greia owns reward economics and global progression;
- never write directly into platform history/progression databases.

---

## 13. Profile API

Read current profile presentation data through:

```python
from greia_platform.activity_api import get_active_profile

profile = get_active_profile()
```

This exposes bounded presentation identity such as profile ID, display name and avatar ID.

Do not search profile directories or infer sibling users from the filesystem.

Profile-changing APIs require explicit platform permission and are normally reserved for trusted system Activities.

---

## 14. Shared graphics and visual canon

### 14.1 Use semantic Greia assets

The current canonical shared icon library is:

```text
assets/catalog/core_icons_v1.toml
```

Resolve icons through the SDK:

```python
from greia_platform.activity_api import get_icon_path

path = get_icon_path("unicorn", 128)
```

Do not hard-code `/opt/greia-os/assets/...` paths.

The catalogue currently provides semantic IDs including examples such as:

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

Always inspect the catalogue for the current exact list rather than inventing filenames.

### 14.2 Theme integration

Get the child's resolved Greia theme with:

```python
from greia_platform.activity_api import get_theme

theme = get_theme()
```

Use theme colors where they fit the Activity rather than duplicating platform palette constants.

`runtime/theme-defaults.toml` defines the canonical platform palette and defaults.

### 14.3 Current limitation: no general Greia widget toolkit yet

At this review Greia has shared semantic assets and theme services, but there is **not yet a canonical general-purpose Activity widget/layout/animation library**.

Do not pretend one exists.

When multiple Activities begin duplicating the same performant child controls, layout primitives, transitions, audio cues or animation infrastructure, propose a reviewed shared library under the Greia platform/SDK rather than copy-pasting slightly different implementations forever.

When such a shared graphics/UI library is accepted, this skill must be updated immediately and Activity authors should prefer it over private clones.

---

## 15. Asset authoring rules

Use shared semantic assets when the concept is platform-wide. Bundle Activity-specific artwork only when it genuinely belongs to that Activity.

For Activity-owned artwork:

- keep dimensions proportional to actual screen use;
- avoid shipping giant source-resolution images when only small sprites are rendered;
- prefer formats Pygame/Pillow can decode efficiently in the curated runtime;
- preload resources during bounded startup rather than repeatedly opening files during frames;
- cache scaled variants used repeatedly;
- preserve aspect ratio unless distortion is intentional;
- avoid thousands of tiny files when a simpler bounded representation works;
- do not ship duplicate copies of existing Greia shared icons.

Source/master artwork that is not needed at runtime should stay outside the Activity package when possible.

---

## 16. Performance canon

Performance is part of correctness on Greia.

The extreme reference class includes an old Atom-class netbook with roughly 768 MiB RAM and a 1024×600 screen until exact inventory supersedes the estimate.

### Required engineering attitude

- profile rather than assume;
- keep startup bounded;
- keep memory bounded;
- keep frame work bounded;
- avoid hidden background work;
- prefer simple 2D techniques that remain pleasant on weak hardware;
- implement richer effects as optional progressive enhancement when needed.

### Pygame hot-loop rules

**Do not perform these every frame unless proven trivial and necessary:**

- disk reads;
- image decode/load;
- font construction;
- large image scaling;
- expensive text layout for unchanged strings;
- constructing large lists/dicts of temporary objects;
- scanning directories;
- storage broker writes;
- network operations;
- uncontrolled particle/object spawning.

Prefer:

- load/decode once;
- `convert()`/`convert_alpha()` surfaces after display initialization where appropriate;
- cache fonts;
- cache rendered static text;
- cache scaled sprites/backgrounds per required size;
- update only changed state;
- use `pygame.time.Clock()` or equivalent bounded pacing;
- cap particle/entity counts;
- reuse objects/surfaces where simple and clear;
- perform durable writes on meaningful state transitions, not every frame;
- keep animations based on elapsed time rather than frame count.

### Frame-rate guidance

A **stable 30 FPS** on low-end C0 hardware is a sensible default authoring target for most child Activities. Do not spend CPU/GPU chasing 60 FPS when the interaction does not benefit.

This is current authoring guidance, not yet a constitutional release threshold. Measure on target hardware and record real results.

### Startup guidance

Create the display, essential assets and first usable interaction promptly; then call `mark_activity_ready()`.

Large optional content may be prepared lazily after the child can interact, provided this does not create input stalls or nondeterministic loading failures.

---

## 17. Resolution/layout performance

The extreme reference display is 1024×600.

Design at that size first.

Recommended patterns:

- derive layout from current surface dimensions;
- establish a small number of resolution/layout breakpoints only if genuinely needed;
- use integer/rational scaling where suitable for crisp pixel art;
- cache resolution-dependent surfaces and rebuild only after a resolution change;
- keep child targets comfortably large;
- reserve safe margins rather than packing the whole screen.

Do not build a 1920×1080 scene and downscale the entire framebuffer every frame on the netbook.

---

## 18. Input design

Only require capabilities the Activity actually needs.

Prefer one interaction model that gracefully supports several devices when practical:

- pointer/touch targets share geometry;
- keyboard can provide an alternative, not a secret mandatory path;
- no assumption that tap-to-click is enabled;
- ignore accidental repeated input where appropriate;
- make destructive/irreversible child actions difficult to trigger accidentally.

Do not open `/dev/input` or depend on X11 input APIs. Greia supplies the Activity-visible input environment through the runtime/display/session architecture.

---

## 19. Audio design

Audio should enhance rather than block play.

- preload short common sounds where feasible;
- avoid decoding the same effect repeatedly;
- bound simultaneous channels/effects;
- keep functionality usable if audio is unavailable when `audio.basic` is optional;
- do not use audio as the only communication channel for an essential state;
- respect eventual platform/parent audio policy rather than implementing a private system-volume control.

---

## 20. Error and recovery behavior

An Activity should fail cleanly rather than reveal Linux internals.

- catch expected content/data errors at an Activity boundary and present child-safe recovery when practical;
- do not show Python tracebacks to children;
- do not invoke a shell/terminal for debugging;
- allow unexpected crashes to terminate so Greia Supervisor can record/recover them;
- do not catch `BaseException` and spin forever trying to hide fatal failures;
- honor stop requests in the main loop;
- keep durable writes atomic through Greia storage.

During development, inspect failures through remote logs rather than adding Linux-facing debug UI to the child experience.

---

## 21. Architecture-neutral state and randomness

Save only what is required to reconstruct logical Activity state.

Good durable examples:

```text
level number
puzzle seed
child-created drawing bytes
settings flags
score/history facts local to the Activity
```

Avoid persisting:

```text
raw pygame Surface objects
memory addresses
absolute paths
pickle blobs
open file/socket descriptors
machine IDs
CPU/GPU-specific objects
```

If deterministic replay matters, save explicit seeds/versioned generation parameters rather than enormous derived state.

---

## 22. Do not create a second platform inside the Activity

An Activity must not independently implement replacements for:

- child profiles;
- global reward ledger;
- global progression;
- package installation/update;
- backups;
- OS settings;
- hardware configuration;
- generic networking authority;
- filesystem browser;
- shell/terminal;
- app store/launcher.

If a reusable concern belongs above one Activity, propose it at the Greia platform/SDK layer.

---

## 23. Validation during development

Validate one Activity explicitly:

```bash
PYTHONPATH=src python3 tools/validate_activity.py path/to/activity
```

Run the project validation/gate before declaring repository work complete:

```bash
make verify
```

The project gate validates every bundled Activity under `activities/*` that contains `activity.toml`.

Remove `__pycache__`/compiled bytecode before packaging; the validator intentionally rejects prohibited artifacts.

Do not weaken validation rules merely to make an Activity pass. Fix the Activity or make a deliberate reviewed platform change.

---

## 24. Local/windowed development

Where current launcher/Activity tooling permits windowed/source development, use it for rapid iteration, but do not treat it as proof of installed sandbox, storage-broker, lifecycle, display-backend or hardware behavior.

An Activity that works on a modern Mac/PC may still be unacceptable on the reference netbook due to:

- memory;
- load/decode time;
- Pygame/SDL behavior;
- 1024×600 layout;
- sandbox/import restrictions;
- missing optional capabilities;
- graphics/input backend behavior.

---

## 25. Remote deployment/test loop

Once an explicit Greia developer image is installed, use the repository helper rather than touching the netbook for routine testing.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Typical loop:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py deploy path/to/activity
python3 tools/greia_remote.py screenshot out/activity-before.png
# navigate/operate using key, mousemove, click, type
python3 tools/greia_remote.py screenshot out/activity-after.png
python3 tools/greia_remote.py logs --service launcher --lines 500
```

For an ordinary Activity, never use `--replace-system` merely because deployment by normal trust fails. Fix the manifest/permissions/package instead.

---

## 26. Performance acceptance loop

For nontrivial Activities, especially animations/games:

1. validate the package;
2. test basic logic provider-free where practical;
3. run/window the Activity in development;
4. deploy to the Greia developer target;
5. test at 1024×600;
6. capture startup/first usable screen;
7. exercise the busiest realistic scene;
8. observe responsiveness/frame pacing;
9. collect process/RSS/CPU evidence when tooling allows;
10. check logs for stalls/errors;
11. repeat after optimization;
12. preserve before/after evidence rather than relying on subjective impressions.

If a visual effect is expensive on the netbook, simplify it or make it progressive enhancement. Do not redefine the reference hardware away.

---

## 27. Code-quality canon

Prefer clean, readable object boundaries over procedural sprawl, especially for reusable game/activity systems.

Useful separations often include:

```text
Activity/Application
Scene/State
Model/domain state
Renderer/view
Input mapping
Asset cache
Audio controller
Greia service adapter
```

Do not force classes where a simple pure function is clearer. Use polymorphism when there are genuinely multiple interchangeable behaviors (scenes, activities, tools, challenge types, rendering strategies), not as decoration.

Keep simulation/domain logic decoupled from rendering where that improves testing and reuse.

Avoid global mutable state except narrow immutable/cached shared resources.

---

## 28. Testing expectations for Activity code

Add provider-free tests for logic that can fail without a display:

- procedural generation;
- scoring/local progression facts;
- collision/math;
- state transitions;
- save-state encode/decode;
- content rules;
- bounded random generation;
- layout calculations when practical.

Do not build brittle screenshot-pixel tests for every visual detail. Use visual acceptance screenshots for layout/appearance and deterministic unit tests for logic/contracts.

Never replace semantic LLM/game/content judgment with naive regex/word-count checks when the requirement is actually qualitative.

---

## 29. Definition of done for a new Activity

A new Activity is not done merely because `main.py` starts.

Before claiming source-ready, confirm:

- stable canonical Activity ID chosen;
- manifest validates;
- required vs optional capabilities are minimal and accurate;
- no unnecessary privileged permissions;
- curated-runtime imports only;
- no private dependency files/environment;
- uses Greia storage rather than arbitrary durable paths;
- declares/emits normalized events where progression facts exist;
- shared Greia assets/theme used where appropriate;
- Activity-specific assets are optimized;
- 1024×600 layout is usable;
- child navigation does not unnecessarily require reading;
- startup marks READY at the correct point;
- main loop honors stop request;
- per-frame work is bounded/cached;
- persistent writes are not performed every frame;
- errors do not expose Linux/Python internals to the child;
- provider-free tests added for meaningful logic;
- `validate_activity.py` passes;
- repository `make verify` passes when the work is integrated;
- real developer-hardware acceptance is performed when required;
- no source test is misrepresented as physical-hardware proof.

---

## 30. Definition of done for an Activity modification

For an existing Activity:

- preserve canonical ID unless there is an explicit migration decision;
- decide whether package version changes;
- decide whether save-schema version changes;
- preserve existing save semantics or provide a reviewed migration path when platform support exists;
- do not silently remove educational events/skills or change score direction;
- compare resource/performance behavior for significant visual/content changes;
- test the modified path plus startup/exit/storage basics;
- redeploy remotely and verify with screenshots/logs where hardware evidence is relevant.

---

## 31. Maintaining this skill

This file is a living project artifact, not generic advice.

Update it in the same tranche whenever any of these change:

- Activity manifest schema;
- runtime API version;
- allowed capabilities or permissions;
- Python import/runtime policy;
- lifecycle API;
- storage API;
- event/progression API;
- package validation rules/size limit;
- Activity trust model;
- shared asset catalogue or resolution API;
- theme API/palette policy;
- accepted shared graphics/UI/audio library;
- developer deployment workflow;
- performance/reference-hardware requirements;
- packaging/install format;
- Web-runtime Activity SDK when it becomes implemented.

If a source change makes this skill wrong, the source change is not completely documented until this file is corrected.
