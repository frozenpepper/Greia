# Greia Art & Graphics System

**Status:** stable visual-system architecture and documentation index  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Last architecture review:** 2026-08-20

This is the **main entry point** for humans and agents working on Greia artwork, UI graphics, characters, environments, visual assets, animation, runtime visual consumption, or Activity reuse.

It is intentionally not the progress diary. Use this document to understand the system and find the authority for each detail.

---

# 1. Documentation map

Read this file first for visual work, then follow the narrower authority that owns the detail you need.

## Stable visual architecture / index

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

This file owns:

- the system-wide visual architecture;
- the asset-first production model;
- source-library organization;
- semantic runtime asset architecture;
- build-time rendition model;
- renderer/cache boundaries;
- Shell and Activity consumption direction;
- the documentation map.

## Current sequencing and history

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Owns:

- current phase;
- current checkpoint;
- milestone completion state;
- exact next action;
- append-only progress history.

## Fast cross-session resume

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Owns:

- current accepted direction;
- current implementation/evidence state;
- next exact visual task;
- current testing rule;
- rejected/stale directions.

## Project-wide continuation state

```text
HANDOVER.md
```

## Visual language and art requirements

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
```

## Character architecture

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
```

## Practical production/integration workflow

```text
skills/greia-visual-authoring/SKILL.md
```

## Source-tree inventory

```text
assets/visual/README.md
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

## Current simulator protocols

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
docs/testing/2026-08-20_V5_ACTIVITY_SHARED_VISUAL_SIMULATOR.md
```

`AGENTS.md` is the repository-wide authority that makes this guide mandatory for visual work.

---

# 2. Product constraints the visual system must respect

Greia is a child-first educational/game Linux appliance, not a desktop theme project.

Visual architecture must remain compatible with:

- no visible Linux shell in the normal child path;
- Greia Shell as the graphical OS surface;
- protected platform Home/Back behavior;
- offline-first use;
- ARM and x86 support;
- low-resource hardware;
- historical 800×600 / 1024×600 constraints and current simulator viewport matrix;
- static completeness when animation is absent;
- Activities that may be Python/Pygame today and Web/HTML in parallel/future paths;
- no dependency on professional per-asset animation labor;
- no runtime requirement for heavy SVG/3D/vector engines on low-end targets.

Visual richness is welcome. Runtime unpredictability is not.

---

# 3. Core production model

The accepted Greia pipeline is:

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → explicit semantic runtime consumption → Shell/Activity reuse**

This order matters.

## 3.1 Asset-first means asset-first

Before composing a finished scene, create reusable pieces worth keeping individually.

Examples:

```text
tree
bush
rock cluster
fallen log
ground edge
cloud
fog strip
sunlight shaft
window
workbench
shelf
bookcase
rug
lamp
panel frame
button frame
soft shadow
badge
```

A scene is not allowed to hide weak source assets.

## 3.2 Simplification is not cheap art

Constraint-native Greia art may use simplified silhouettes, anatomy and motion. That does **not** mean:

- raw circles as final trees;
- tutorial rectangles as buildings;
- generic flat web-app cards;
- crude full-screen mockups presented as design direction.

The quality target is a polished storybook / felt-board / toy-diorama world with controlled texture, warm local light, soft depth, clean silhouettes and strong low-resolution readability.

---

# 4. Visual language

The narrow palette/type/style details live in `GREIA_VISUAL_STYLE_GUIDE.md` and `runtime/theme-defaults.toml`.

System-level direction:

- warm, friendly, tactile;
- rounded but not generic SaaS UI;
- local highlights and shallow physical depth;
- clear silhouettes;
- soft contact/cast shadows;
- restrained gradients;
- decoration that supports rather than competes with play;
- readable at low resolution;
- child-facing state must never rely on color alone.

Greia's shared theme palette includes warm cream, sky, mint, lavender, peach, rose, sand and aqua backgrounds plus sunshine/coral/leaf/ocean/grape/raspberry/orange/turquoise accents.

Text defaults to the accepted theme typography (currently Nunito Sans in the style authority).

---

# 5. Character system

Core cast:

```text
Lilli — unicorn Puff
Nino  — owl Bean
Tito  — fox Puff
Momo  — friendly monster Puff
```

The character system deliberately avoids detailed anatomical rigs as the default production model.

## 5.1 Character grammar

Identity comes from:

- silhouette;
- color grouping;
- face;
- ears/horns/tufts;
- tails/wings/accessories;
- sound/behavior;
- a small number of authored expression states.

## 5.2 Shared expression states

Current shared vocabulary:

```text
neutral
blink
happy
surprised
sleepy
```

`blink` must visibly close the eyes.

## 5.3 Shared motion vocabulary

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

Motion favors whole-body translate/tilt/squash/stretch/wobble plus authored static face states.

Do not make shoulders/elbows/knees/realistic gait prerequisites for normal Greia character animation.

---

# 6. Environment architecture

Scenes are assembled from reusable depth layers.

Recommended conceptual stack:

```text
0  sky / room base
10 far background
20 mid background
30 playfield / ground
40 interactive props
50 foreground framing
60 atmosphere / fog
70 light / shadow / FX
80 characters
90 Activity-local UI
100 protected Greia platform UI/chrome where applicable
```

Exact z values are composition-specific; the separation principle is stable.

## 6.1 Parallax

Use small, readable depth differences rather than dramatic camera tricks.

Typical intent:

```text
sky                  0.00
far landscape        0.05–0.10
mid background       0.10–0.20
playfield props      0.25–0.35
foreground framing   0.40–0.55
```

Parallax is optional enrichment. Static layout must remain coherent.

## 6.2 Ambient motion

Good candidates:

- slow cloud drift;
- tiny foliage/reed sway;
- low-count fireflies/dust;
- gentle water shimmer/ripples;
- fog drift;
- slow light breathing;
- tiny prop idles.

Motion must be bounded and cheap.

---

# 7. Lighting and shadow are reusable assets

Do not bake every depth cue uniquely into every scene.

Reusable families include:

```text
soft contact shadow
cast-shadow decal
highlight sheen
window-light shaft
sunlight shaft
fog/haze strip
window glow
reflection glow
reward glow
subtle vignette/framing shadow
```

Light/shadow overlays should remain independently removable where reuse benefits.

---

# 8. Current reusable source library

Broad environment/UI coverage exists already.

```text
assets/visual/environments/forest_meadow/v0.2/
assets/visual/ui/v0.1/
assets/visual/environments/workshop/v0.1/
assets/visual/environments/clinic/v0.1/
assets/visual/environments/reading_classroom/v0.1/
assets/visual/environments/fantasy_village_night/v0.1/
assets/visual/environments/water_pond/v0.1/
```

The current active plan forbids creating another environment family merely to keep producing assets. New packs require a concrete reuse gap.

## 8.1 Pack metadata

Each reusable pack should expose explicit metadata such as:

- pack/catalog ID;
- version;
- status;
- provenance;
- asset semantic ID;
- file path;
- family/role;
- alpha behavior;
- optional parallax/ambient hints;
- shared dependencies/reuse notes;
- runtime-consumed state where relevant.

Pack metadata is a design/review inventory. It is **not** permission for runtime directory discovery.

---

# 9. Shared UI system

Current shared UI source family lives under:

```text
assets/visual/ui/v0.1/
```

Families include:

```text
panel / sheet frame
activity card frame
primary button
button states
icon button
pill/tab
badge
progress track/fill
speech/help bubble
focus ring
avatar frame
soft shadow
highlight sheen
loading/error/empty illustration
portal/category framing
```

## 9.1 State language

A state must combine multiple cues where needed:

- outline/frame thickness;
- shape;
- badge/icon;
- lift/depression;
- local depth;
- short motion;
- text when appropriate.

## 9.2 Motion vocabulary

```text
hover/focus  → tiny lift + depth change
press        → small depress/squash
selected     → stronger frame + depth
launch       → short bounce/squiggle/pop
reward       → pop + restrained sparkle
gentle error → restrained wobble
```

Protected platform Home/Back controls remain platform-owned and cannot be replaced by Activity artwork.

---

# 10. Semantic asset architecture

Runtime-facing visuals extend Greia's existing explicit asset catalogue.

Core owners:

```text
src/greia_platform/assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
assets/catalog/shared_visuals_v1.toml
```

## 10.1 One semantic namespace

Icons and shared visuals share one explicit semantic namespace.

Examples:

```text
paint
backpack
ui.shadow.soft
ui.panel.base
ui.card.activity
ui.button.primary
```

A shared visual carries:

```text
semantic ID
kind
role
explicit variants
required default variant
explicit resolved asset path
```

IDs are product semantics. Filenames are implementation details.

## 10.2 No runtime discovery

Forbidden runtime behavior:

```text
scan assets/visual recursively
pick files by naming convention
auto-register arbitrary SVGs
search host directories
```

Consumers load explicit catalogues only.

Benefits:

- deterministic content;
- bounded startup work;
- review/provenance clarity;
- duplicate-ID rejection;
- path containment;
- predictable image composition;
- renderer independence at the semantic level.

## 10.3 Catalogue merge contract

Explicit catalogues may merge only when they resolve under the same assets root.

Important invariants:

- core icon catalogue remains mandatory;
- generated shared visual catalogue may be optional for fallback consumers;
- semantic IDs remain globally unique;
- mismatched roots fail;
- invalid/missing optional shared visual output must not crash otherwise-valid Shell/Activity paths.

---

# 11. Source masters versus runtime renditions

Greia separates high-quality source masters from low-cost runtime files.

Current V5 pipeline:

```text
assets/visual/ui/v0.1/*.svg
        ↓ explicit selection
assets/catalog/shared_visuals_v1_source.toml
        ↓ build host
rsvg-convert / librsvg
        ↓
assets/visual/runtime/v1/.../*.png
        +
assets/catalog/shared_visuals_v1.toml
```

Current build authority:

```text
tools/build_visual_renditions.py
```

Current validator:

```text
tools/validate_visual_renditions.py
```

Entry points:

```text
make visual-assets
make visual-assets-check
```

The builder is transactional: failed generation must not destroy previous good output.

## 11.1 Why SVG is not rendered on low-end target

Benefits of build-time conversion:

- smaller target dependency set;
- bounded startup cost;
- predictable dimensions;
- easier cache accounting;
- easier low-resource profiling;
- no surprise SVG parser/render cost during play.

---

# 12. Pygame renderer adapter

Current adapter:

```text
src/greia_platform/pygame_visual_assets.py
```

`PygameVisualSurfaceCache` realizes shared semantic visuals as renderer-ready Pygame surfaces.

Properties:

- PNG-only runtime paths;
- semantic ID + variant + requested size key;
- lazy Pygame import;
- one-time decode/scale on cache miss;
- existing `ui_core.BoundedCache` reuse;
- default 12-entry LRU;
- bounded requested surface area;
- explicit clear;
- no per-frame filesystem/decode after cache hit.

This is a renderer adapter, not the visual architecture itself.

Future Web/SDL adapters should preserve semantic IDs and variant meaning without requiring consumers to know Pygame internals.

---

# 13. Shell consumption architecture

Current first accepted Shell consumer:

```text
ui.shadow.soft
```

under launcher Activity tiles.

Source seam:

```text
src/greia_launcher/visual_assets.py
src/greia_launcher/main.py
src/greia_launcher/presentation.py
```

The first consumer proves:

```text
semantic catalogue
→ generated PNG
→ bounded Pygame cache
→ real Shell rendering
→ fail-soft primitive fallback
```

It preserves Activity tile hit geometry, responsive grid geometry, label-band geometry, selection/hover behavior and launch lifecycle.

Current fallback remains the primitive/static `draw_soft_shadow` path.

Evidence for this consumer is **SIMULATOR VISUAL REVIEW**, recorded in `LOCAL_AGENT_RESULT.md`.

Do not convert this into blanket approval for all UI source assets or physical low-end performance.

---

# 14. Activity semantic shared-visual architecture

The next V5 architecture step is now source-started.

Current Activity API owner:

```text
src/greia_platform/activity_api.py
```

The semantic contract is:

```python
get_shared_visual(asset_id, variant="default")
get_shared_visual_path(asset_id, variant="default")
```

`get_shared_visual(...)` returns a read-only `SharedVisualReference` containing:

```text
asset_id
kind
role
variant
path   # current Python runtime realization
```

Important meaning:

- the Activity requests a semantic ID and explicit variant;
- the Activity cannot provide or traverse an arbitrary host path;
- the Activity cannot mutate the catalogue;
- core icons remain available even if optional generated visual catalogue loading fails;
- unknown shared visual IDs/variants fail narrowly;
- Activity-private art remains allowed.

The `Path` is the current Python realization, not the permanent cross-renderer API shape. Future Web runtime support should expose the same semantic ID/variant contract through a controlled asset URL/handle rather than host filesystem access.

## 14.1 First Python Activity source consumer

Current source seed:

```text
activities/shape_garden/main.py
```

Shape Garden resolves:

```text
ui.shadow.soft
```

once at Activity startup, scales it once to a bounded reference size, and reuses the resulting surface while drawing shapes. Missing/invalid optional shared visuals keep the Activity playable.

This is currently **SOURCE only until the dated Activity Simulator protocol passes**.

Do not claim Activity semantic integration complete merely because the source exists.

---

# 15. Web Activity direction

Web Activities must eventually use the same semantic IDs and variant names as Python Activities.

Intended concept:

```text
Activity semantic request
→ platform-authorized visual resolver
→ renderer/runtime adapter
→ local controlled URL/handle/surface
```

The Web adapter must not expose arbitrary filesystem paths.

Do not freeze a Web transport merely by copying the Python `Path` API.

---

# 16. Activity-private art versus shared Greia art

Both are valid.

Use Activity-private assets when the image belongs uniquely to that Activity's gameplay/content.

Use shared Greia semantic visuals when the visual is a platform/shared concept such as:

- common panel/button frame;
- shared shadow;
- system-wide character/prop where appropriate;
- cross-Activity environment piece explicitly promoted for reuse;
- shared FX or decorative family.

Do not force every Activity asset into the global catalogue.

Do not duplicate a shared master privately simply to avoid using the semantic resolver.

---

# 17. Performance rules

Hard direction:

- no target runtime SVG rasterization;
- no per-frame image file loads;
- no per-frame directory scanning;
- no per-frame smoothscale where a bounded cached/prepared surface can be reused;
- no unbounded image/texture caches;
- no giant mandatory atlas as a shortcut;
- no full-screen animation dependency for basic meaning;
- static fallback remains valid;
- expensive conversion happens at build time;
- decode/scale happens once per bounded cache/preparation key;
- cache invalidation happens only on meaningful size/theme/state changes.

Simulator frame-count evidence detects gross regressions but does not prove physical Acer/Pi performance.

---

# 18. Evidence and approval vocabulary

Evidence classes:

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
REJECTED EXPERIMENT
```

Artwork states:

```text
concept
candidate
approved
superseded
rejected
```

When `approved` could be ambiguous, state scope:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Examples:

- an SVG may be candidate source art without runtime consumption;
- a character may be an approved static style anchor without release approval;
- generated PNG presence is not proof of consumer integration;
- simulator acceptance is not physical low-resource acceptance.

---

# 19. Standard source-asset workflow

For new/extended source art:

1. state the real reuse gap;
2. inspect existing packs first;
3. list proposed individual masters;
4. create/revise masters individually;
5. review individual assets on representative grounds;
6. correct weak assets before composition;
7. record metadata/provenance/status;
8. compose independent target references from actual masters;
9. add restrained light/parallax/motion only where it improves depth;
10. record cross-pack reuse;
11. promote only selected assets into explicit runtime-rendition manifests;
12. build runtime renditions;
13. consume through semantic catalogue/resolver/renderer adapter;
14. verify through the appropriate simulator/physical protocol;
15. update plan/resume/guide when contracts change.

---

# 20. Standard runtime-integration workflow

For a shared visual entering a real consumer:

```text
1. source asset is reviewed enough for the intended scope
2. semantic ID + variants are explicit
3. source rendition manifest selects it
4. build host generates PNG rendition
5. generated catalogue is validated
6. consumer requests semantic ID, never scans directories
7. renderer adapter/preparation caches bounded surfaces/resources
8. optional visual has a safe fallback where appropriate
9. simulator validates real consumer behavior
10. physical testing is added only when the claim requires it
11. docs/evidence state is updated
```

---

# 21. Anti-patterns / rejected architecture

Do not reintroduce:

- complex quadruped/puppet rig as default character architecture;
- generated sprite sheets assumed production-ready;
- degrading accepted characters through redraw/overlay drift;
- fake expression overlays;
- a blink state that does not close eyes;
- crude primitive scenes presented as final direction;
- full-screen mockups before source assets exist;
- decorative HTML presentations hiding weak art;
- one-shot concept scene images as source architecture;
- runtime SVG rasterization on low-end targets;
- arbitrary asset-directory discovery;
- a second visual catalogue/cache system;
- per-frame PNG decode/scale;
- unbounded caches;
- simulator-specific branches in production rendering;
- per-resolution hard-coded UI forks;
- broad exception swallowing to hide visual failures;
- endless new environment packs after coverage is already broad;
- duplicating generic assets instead of using shared masters.

---

# 22. Current implementation snapshot

This section is deliberately short. The authoritative live checkpoint remains the active plan and resume file.

As of 2026-08-20:

- V2/V3/V4 source coverage exists through Water/Pond;
- the runtime SVG→PNG build pipeline exists;
- generated UI runtime renditions exist;
- the bounded Pygame visual cache exists;
- `ui.shadow.soft` is accepted as the first Shell consumer at **SIMULATOR VISUAL REVIEW** scope;
- `activity_api.get_shared_visual(...)` / `get_shared_visual_path(...)` now provide the first Python semantic Activity resolver source;
- Shape Garden is the first source Activity consumer and still requires Activity Simulator acceptance before that gate closes;
- the next architectural target is to prove this Activity seam, then design the future Web equivalent around the same semantic IDs/variants.

Resume from:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

not from chat history.
