# Greia Art & Graphics System

**Status:** living visual-system architecture and navigation guide  
**Last reviewed:** 2026-08-20  
**Audience:** humans, coding agents, Activity authors, visual contributors, reviewers  
**Repository:** `frozenpepper/Greia`  
**Current workstream:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current resume file:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

---

# 1. Purpose

This is the **main entry point for Greia's art, graphics, visual-asset, animation, composition and visual-runtime system**.

If you are new to Greia visual work, start here. This document explains:

- the visual-production philosophy;
- how source artwork is organized;
- how characters, environments, props, FX and UI fit together;
- how layered scenes, parallax, light and motion are expected to work;
- how semantic asset IDs, build-time renditions and runtime caches fit together;
- how the Shell and Activities are expected to consume the same shared visual system;
- which files own which details;
- how to review and extend the system without creating a parallel architecture;
- where to resume current implementation work.

This document is intentionally a **synthesis and index**, not a replacement for accepted ADRs, exact source contracts or the active implementation plan.

When there is a conflict:

1. `AGENTS.md` owns repository-wide rules;
2. accepted ADRs own normative platform architecture;
3. exact source/runtime declarations own currently implemented APIs and schemas;
4. this guide owns the integrated explanation and navigation of the visual system;
5. the active visual plan owns sequencing and completion state;
6. pack-local files own candidate art/review/composition details.

---

# 2. The system in one sentence

Greia uses an **asset-first, semantic, composable visual library**:

> **excellent individual source assets → reusable packs → layered composition → subtle light/motion/parallax → explicit build-time runtime renditions → semantic catalogues → bounded renderer caches → shared Shell/Activity consumption**

The system is designed around four realities:

- Greia must look coherent and rich enough to feel like a real child-oriented world;
- the extreme hardware floor is old and resource-constrained;
- Activities must not each invent their own unrelated visual infrastructure;
- graphics architecture must remain renderer/runtime-neutral enough to survive the future move beyond provisional Xorg/Pygame details.

---

# 3. Non-negotiable design principles

## 3.1 Asset first

Do not begin with a crude full-screen mock and attempt to hide weak pieces inside it.

A scene, UI family or visual feature should normally progress as:

```text
individual master
→ individual review
→ reusable family/pack
→ target-size composition
→ restrained motion/light/parallax
→ explicit runtime selection
→ real consumer
→ simulator/physical evidence
```

A weak primitive is not production art merely because several weak primitives are combined.

## 3.2 Reuse before duplication

Generic objects belong in shared packs.

Examples:

```text
tree
bush
rock
log
cloud
shadow
firefly
block
pencil cup
button treatment
card treatment
window-light overlay
```

If a semantically suitable shared master exists, reference it. Do not repaint a nearly identical private copy for every Activity/environment.

## 3.3 Richness comes from composition, not runtime heaviness

Greia can look visually rich while remaining cheap to render.

The preferred model is:

- carefully authored static masters;
- pre-rendered runtime PNGs;
- layered depth;
- local contact/cast shadows;
- subtle highlights;
- restrained overlays;
- small transform-based motion;
- bounded parallax;
- static fallbacks.

Avoid systems that require large skeletal rigs, continuous SVG rasterization, video backgrounds, shader-heavy rendering, huge texture atlases or per-frame file decoding on the low-end target.

## 3.4 Motion supports good art; it does not rescue bad art

Allowed motion includes:

- slow cloud drift;
- tiny foliage/reed sway;
- subtle idle bounce;
- small hover lift;
- short launch bounce/squiggle;
- water shimmer/ripple;
- light-ray breathing;
- fog/dust/firefly drift;
- parallax offsets.

Important meaning must remain understandable in the static state.

## 3.5 One shared visual language

Greia should feel like one world rather than a launcher surrounded by unrelated apps.

Consistency should come from:

- common palette families;
- shared typography;
- common shape/depth language;
- shared characters where appropriate;
- shared asset semantics;
- common UI state vocabulary;
- shared lighting/shadow language;
- platform-owned protected system chrome.

Activities may have expressive identities, but should not reinvent basic navigation/control grammar.

---

# 4. Visual-language authorities

Use this guide as the index, then follow the narrower authority.

| Topic | Primary file |
|---|---|
| overall visual system / architecture / index | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| visual personality, palette, typography, contrast | `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` |
| platform/core artwork inventory and required families | `docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md` |
| constraint-native character construction | `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md` |
| character expression + motion vocabulary | `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md` |
| launcher interaction/catalogue behavior | `docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md` |
| Activity spatial/canvas authoring | `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` |
| practical visual-authoring workflow | `skills/greia-visual-authoring/SKILL.md` |
| current sequencing / milestones / art ledger | `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` |
| current session continuation | `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` |
| current project-wide evidence / continuation | `HANDOVER.md` |
| exact documentation authority model | `docs/DOCUMENTATION.md` |

Relevant platform architecture:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0026-resolution-adaptive-single-authoring-ui.md
docs/adr/0027-activity-coordinate-spaces-reference-canvas-world-camera.md
```

The visual system must remain compatible with the direct/appliance display direction selected by ADR 0014 and must not deepen X11 coupling while R7 remains open.

---

# 5. Source library structure

The reusable visual source library lives under:

```text
assets/visual/
```

The important top-level concepts are:

```text
assets/visual/characters/       character expression/state masters
assets/visual/specimens/        reviewed style anchors / historical experiments
assets/visual/environments/     reusable environment packs
assets/visual/ui/               reusable UI artwork families
assets/visual/library_v0.1.toml character/archetype/expression/motion design inventory
assets/visual/packs_v0.1.toml   pack-level inventory and reuse relationships
assets/visual/README.md         source-tree operational summary
```

Design inventories are **not runtime filesystem-discovery contracts**.

Runtime code must not recursively scan these directories and guess meaning from filenames.

---

# 6. Current source packs

Current broad source coverage is sufficient to stop pack proliferation and focus on runtime integration.

| Pack | Location | Current role |
|---|---|---|
| Forest / Meadow v0.2 | `assets/visual/environments/forest_meadow/v0.2/` | generic outdoor landscape, foliage, props, distant layers, atmosphere |
| Shared UI v0.1 | `assets/visual/ui/v0.1/` | panels, cards, buttons, tabs, badges, progress, bubbles, reward/help/error/loading/empty/focus/shadow families |
| Workshop v0.1 | `assets/visual/environments/workshop/v0.1/` | indoor making/creative furniture and props |
| Clinic / Care v0.1 | `assets/visual/environments/clinic/v0.1/` | warm pretend-care furniture, props and light |
| Reading / Classroom v0.1 | `assets/visual/environments/reading_classroom/v0.1/` | reading/learning furniture, books, boards, seating |
| Fantasy / Village / Night v0.1 | `assets/visual/environments/fantasy_village_night/v0.1/` | village architecture, night layers, moon/window light |
| Water / Pond v0.1 | `assets/visual/environments/water_pond/v0.1/` | water/shoreline/lily/reed/dock/ripple/shimmer families |

Pack-local files normally include some combination of:

```text
catalog.toml
README.md
REVIEW.md
COMPOSITION.md
composition*.toml
reference_1024x600.svg
reference_800x600.svg
```

These record candidate source and review state. They do not independently authorize runtime consumption.

---

# 7. Characters

The current shared cast is:

- **Lilli** — unicorn Puff;
- **Nino** — owl Bean;
- **Tito** — fox Puff;
- **Momo** — friendly monster Puff.

The character direction is deliberately constraint-native.

## 7.1 Construction grammar

Preferred construction:

- one dominant body mass;
- large readable face;
- tiny/optional appendages;
- identity through silhouette and a few distinctive features;
- no dependence on realistic anatomy;
- motion primarily through whole-character translation/rotation/squash/stretch;
- authored expression variants when the face genuinely changes.

This is not an excuse for low-quality art. Simple geometry must still produce an intentional, polished character.

## 7.2 Shared states

Current shared state vocabulary:

```text
neutral
blink
happy
surprised
sleepy
```

Base motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

`blink` must visibly close the eyes.

Do not redraw a character into a visibly different character just to animate it.

---

# 8. Environment composition architecture

A Greia scene is a stack of reusable layers, not one baked image by default.

Typical order:

```text
0  sky / room base
10 far background
20 mid background
30 ground / playfield base
40 props / interactive assets
50 foreground framing
60 atmosphere / light / shadows / FX
70 characters
80 Activity UI
90 protected Greia system chrome
```

Exact numeric values are composition metadata, not a frozen public API.

## 8.1 Why layered source matters

Layering allows:

- reuse across Activities;
- independent cropping/recomposition at 4:3 / 16:10 / 16:9;
- cheap parallax;
- optional atmosphere;
- dynamic props;
- shared lighting/shadows;
- static fallback;
- future renderer changes without repainting the visual library.

## 8.2 Calm playfield

Environment richness should normally frame or support the gameplay area rather than occupy every pixel.

A useful composition often has:

- richer foreground edges;
- readable side anchors;
- a calmer center;
- clear interactive silhouettes;
- stable high-contrast regions for text/UI.

## 8.3 Independent target compositions

Do not assume 800×600 is a letterboxed 1024×600 image.

Important reference viewports should be composed deliberately from the same source layers.

The goal is one semantic composition system, not separate painted art for every resolution.

---

# 9. Parallax, ambient motion and light

Parallax is metadata-driven composition behavior, not an excuse for a full game engine.

Typical relative depth behavior:

```text
sky                0.00
far hills           0.05–0.10
far tree line       0.10–0.16
mid environment     0.20–0.30
playfield props     0.28–0.38
foreground framing  0.40–0.55
overlay light       often 0.00 or scene-specific
```

These are design ranges, not rigid source constants.

## 9.1 Ambient motion rules

Prefer bounded descriptors such as:

```text
none
slow_drift_x
very_slow_drift
subtle_sway
tiny_water_bob
very_slow_breathe_alpha
slow_rise_fade
expand_fade
bounded_hover_drift
```

Keep amplitudes small.

Avoid continuous motion on every object.

## 9.2 Lighting system

Reusable visual treatments should include:

- contact shadows;
- soft cast shadows;
- warm/cool glows;
- sunlight/window/moonlight shafts;
- haze/fog;
- water reflection/shimmer;
- reward/discovery sparkle treatments.

Lighting should visually ground assets and establish scene depth without requiring expensive runtime effects.

---

# 10. Shared UI artwork system

Greia UI architecture remains owned by ADR 0018 and platform source. The visual library supplies reusable appearance, not a second widget framework.

Reusable visual families include:

```text
panel / sheet
activity card
button: primary / secondary / quiet / icon
tab / selected tab
badge: new / done / favorite / locked
progress track / fill / complete
speech / thought bubble
reward frame
avatar frame
focus ring
soft shadow
highlight sheen
loading / error / empty-state illustration
portal / category framing
```

## 10.1 UI states

State must not rely on color alone.

Use combinations of:

- outline/frame thickness;
- shape;
- badge/icon;
- position/lift;
- local depth;
- short motion;
- text where appropriate.

## 10.2 Motion vocabulary

```text
hover/focus  → tiny lift + depth change
press        → small depress/squash
selected     → stronger frame + depth
launch       → short bounce/squiggle/pop
reward       → pop + restrained sparkle
gentle error → restrained wobble
```

The protected platform Home/Back layer is not Activity artwork and cannot be replaced by this library.

---

# 11. Semantic asset architecture

The runtime-facing visual system extends Greia's existing explicit asset catalogue.

Core source owners:

```text
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/core_icons_v1.toml
assets/catalog/shared_visuals_v1_source.toml
```

## 11.1 One semantic namespace

Icons and shared visuals use one explicit semantic asset namespace.

A visual entry carries concepts such as:

```text
semantic ID
kind
role
explicit variants
default variant
explicit source/runtime path
```

Examples:

```text
ui.shadow.soft
ui.card.activity
ui.button.primary
```

IDs are product semantics. Filenames are implementation details.

## 11.2 No runtime discovery

Forbidden runtime behavior:

```text
scan assets/visual recursively
pick files by naming convention
auto-register arbitrary SVGs
search host directories
```

Explicit manifests are required.

Benefits:

- deterministic content;
- bounded startup work;
- provenance/review clarity;
- duplicate-ID rejection;
- path containment;
- renderer independence;
- predictable package/image composition.

## 11.3 Catalogue merging

The V5 design supports merging explicitly loaded catalogues when they resolve under the same Greia assets root.

Important invariants:

- core icons remain mandatory;
- generated shared visuals are optional at the first launcher bridge;
- IDs remain globally unique;
- mismatched roots fail;
- missing/invalid optional shared visuals preserve the existing static launcher path.

---

# 12. Source artwork versus runtime renditions

Greia keeps high-quality/reviewable masters separate from low-cost runtime images.

Current V5 flow:

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

The exact generated paths are source/build contracts; inspect the current manifest/tool before changing them.

## 12.1 Why SVG is not rendered on target

The low-end target should not need an SVG renderer.

Benefits of build-time rasterization:

- smaller runtime dependency set;
- bounded startup behavior;
- no unexpected SVG parse/render cost;
- predictable dimensions;
- easier cache accounting;
- easier low-resource profiling.

## 12.2 Build authority

Current build tool:

```text
tools/build_visual_renditions.py
```

Current validation tool:

```text
tools/validate_visual_renditions.py
```

Current entry points:

```text
make visual-assets
make visual-assets-check
```

The builder is intentionally transactional: a failed rendition must not destroy the previous known-good generated output.

---

# 13. Pygame runtime adapter

Current Pygame visual surface adapter:

```text
src/greia_platform/pygame_visual_assets.py
```

`PygameVisualSurfaceCache` is the current renderer-specific realization of the semantic visual contract.

Key properties:

- PNG-only runtime paths;
- lazy Pygame import;
- semantic ID + variant + requested size cache key;
- one-time decode/scale on cache miss;
- existing `ui_core.BoundedCache` reuse;
- default 12-entry LRU;
- bounded requested surface area;
- explicit clear;
- no per-frame filesystem/decode work after a hit.

This cache is a renderer adapter, not the whole visual architecture.

A future Web/SDL renderer should implement equivalent semantic behavior without requiring Activity authors to know Pygame internals.

---

# 14. Shell consumption architecture

The first V5 consumer is intentionally small and low-risk.

Current first candidate:

```text
ui.shadow.soft
```

under existing launcher Activity tiles.

Why this is first:

- it proves semantic catalogue → runtime PNG → cache → Shell rendering;
- it does not require a new launcher layout;
- it is decorative and can fail soft;
- current primitive/static rendering can remain fallback;
- it exercises size/caching behavior across viewports.

The first consumer must not:

- change Activity hit geometry;
- create a second launcher card model;
- bypass existing presentation/layout code;
- scan source art;
- load/scale from disk every frame;
- crash the Shell because an optional decorative rendition is missing.

After that seam is accepted, the same contract may gradually consume other reviewed UI families.

---

# 15. Activity consumption direction

Activities should eventually request shared visuals semantically instead of importing arbitrary Greia source paths.

The intended direction is:

```text
Activity asks for semantic visual
→ platform resolves allowed asset/variant
→ runtime adapter obtains renderer-ready rendition
→ Activity receives renderer-appropriate handle/surface/reference
```

The final Activity-facing API is not frozen merely by this design document. Exact source/API must be introduced deliberately when V5 reaches that step.

Rules:

- do not expose the entire host assets filesystem;
- do not expose raw internal catalogue mutation;
- do not make every Activity maintain its own cache;
- Python and future Web runtimes should converge on the same semantic IDs;
- Activity-private art remains allowed for Activity-specific content;
- shared Greia visuals should be reused when semantically appropriate.

---

# 16. Performance and low-resource rules

Visual richness must stay compatible with the extreme low-resource floor.

Hard direction:

- no runtime SVG rasterization;
- no per-frame image file loads;
- no per-frame font construction where avoidable;
- no unbounded texture/surface caches;
- no arbitrary asset-directory scans;
- no giant mandatory atlases;
- no full-screen animation dependency for basic UI meaning;
- keep static fallback valid;
- perform expensive conversion at build time;
- decode/scale once per bounded cache key;
- invalidate/rebuild caches only on meaningful size/theme/state changes.

Simulator evidence can catch gross stalls and visual regressions, but does not prove Acer/Pi physical performance.

---

# 17. Evidence and approval model

Use precise labels.

```text
DESIGN SPEC
SOURCE
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
REJECTED EXPERIMENT
```

Artwork state:

```text
concept
candidate
approved
superseded
rejected
```

`approved` must have scope when ambiguity exists:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Examples:

- an SVG can be a candidate source asset without being runtime-consumed;
- a character can be an approved static style anchor without being release-approved;
- simulator review does not prove physical low-end performance;
- generated runtime PNG presence does not prove successful Shell consumption.

---

# 18. Standard asset-pack workflow

For a new or extended pack:

1. state the real reuse gap;
2. inspect existing packs before drawing;
3. list proposed individual masters;
4. create/revise individual source assets;
5. review assets individually on representative grounds;
6. correct weak assets before composition;
7. record metadata/provenance/status;
8. compose independent target references from the real masters;
9. add only restrained light/parallax/motion that improves depth;
10. record cross-pack reuse explicitly;
11. promote only selected assets into explicit runtime-rendition manifests;
12. build runtime renditions;
13. consume through semantic catalogue/cache;
14. verify through the correct simulator/physical protocol;
15. update plan, handover and this guide if architecture changed.

Do not create another environment family merely because the previous family is finished. Current V4 coverage is intentionally broad enough; V5 integration has priority.

---

# 19. Review checklist for individual assets

Before composition, ask:

- Is the silhouette readable at intended size?
- Does it still work at 800×600 / 1024×600 scale?
- Are alpha edges clean?
- Does it look intentional rather than tutorial-generated?
- Is depth coherent with existing Greia assets?
- Does it require tiny detail to read?
- Is it semantically reusable?
- Does a similar shared master already exist?
- Is the lighting direction compatible with likely scenes?
- Does it have a plausible grounding/contact-shadow strategy?
- Can it be used without animation?

Reject or revise before scene assembly if the answer is poor.

---

# 20. Anti-patterns / rejected directions

Do not repeat these without new evidence:

- detailed traditional quadruped rigs as the default character system;
- one-shot AI sprite sheets assumed production-ready;
- redraws that lose accepted character identity;
- fake face overlays;
- a `blink` animation that does not blink;
- crude primitive backgrounds presented as final direction;
- HTML/mockup presentations before the actual assets deserve presentation;
- baked scene-first production that prevents reuse;
- runtime SVG rendering on old targets;
- arbitrary directory scanning;
- parallel per-Activity asset systems;
- unbounded caches;
- per-frame image decoding/scaling;
- duplicating generic assets between environment packs;
- endlessly adding new packs after broad coverage exists;
- deepening provisional X11 dependency for visual convenience;
- letting Activity artwork imitate/replace trusted platform Home/Back chrome.

---

# 21. Current implementation phase — V5

The broad source library exists. The current active work is **shared consumption/integration**.

Current V5 source surface:

```text
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
Makefile: visual-assets / visual-assets-check
```

Current explicit first runtime selection includes:

```text
ui.panel.base
ui.card.activity
ui.button.primary
ui.shadow.soft
```

The first Shell integration target remains:

```text
ui.shadow.soft
```

The current local-agent execution protocol is:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
```

For that current owner-directed local-agent tranche, **runtime/visual/fallback/responsive test acceptance is handled through the Activity Simulator**. `make visual-assets` remains a build-generation prerequisite rather than a PASS claim.

Do not infer from this document that V5 has already passed. Check the resume file, active plan and current `HANDOVER.md`.

---

# 22. Where to look by task

## I need to make a new Greia asset

Read:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
skills/greia-visual-authoring/SKILL.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
assets/visual/README.md
relevant pack README/REVIEW/catalog
```

## I need to add a character state/animation

Read:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/library_v0.1.toml
```

## I need to compose a background/scene

Read:

```text
this guide: sections 8–9
relevant environment pack COMPOSITION.md / composition.toml
docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md
```

## I need to change shared UI appearance

Read:

```text
docs/adr/0018-lightweight-ui-foundation.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
assets/visual/ui/v0.1/
src/greia_platform/pygame_effects.py
```

## I need to integrate shared assets into runtime

Read:

```text
this guide: sections 11–16
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
```

## I need to continue the current session

Read:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
HANDOVER.md
```

## I need to test current V5 integration locally

Read:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md
```

---

# 23. Documentation maintenance contract

This file should remain the stable visual-system landing page even after the current plan is completed.

Update this guide when any of these materially change:

- source-library structure;
- semantic visual IDs/catalogue architecture;
- build-time rendition pipeline;
- runtime renderer/cache contract;
- Shell/Activity shared-consumption architecture;
- layer/parallax/light/motion model;
- accepted relationship between the visual system and UI architecture;
- evidence/approval model;
- visual-system extension points.

Do **not** use this guide as an append-only progress diary. Current chronology belongs in the active plan. Current continuation belongs in the resume file/HANDOVER.

The goal is simple: a new human or agent should be able to read this file, understand the system, and know exactly where to go next without reconstructing the architecture from chat history.
