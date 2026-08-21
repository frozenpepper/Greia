# Greia Visual Authoring Architecture

**Status:** active architecture clarification  
**Date:** 2026-08-21  
**Parent visual authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Practical authoring skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Core correction

Greia's shared visual system must **not** become a giant runtime warehouse containing every finished tree, cave, bush, hollow, reed cluster, room prop, etc. That would be repetitive, impossible to cover exhaustively, visually boring, and contrary to the original goal.

The shared visual library is primarily an **authoring-time system** for the model/agent creating a Greia Activity.

The authoring agent should be able to:

- read Greia's visual style and construction rules;
- inspect reference assets and examples;
- reuse primitives and reusable construction pieces;
- reuse recipes and best practices;
- reuse a finished shared asset only when it genuinely fits;
- compose, adapt, derive and create new bespoke artwork for the specific Activity.

The finished Activity then ships its own composed assets, while the Greia runtime renders them efficiently.

The intended principle is:

> **coherence through shared style, grammar, primitives and recipes — variety through Activity-specific authored assets.**

---

## 2. Four-layer architecture

### Layer A — Greia Visual Authoring Kit

The Authoring Kit is the shared source-level creative toolkit used by Activity-authoring models/agents.

It should contain:

- visual style rules and visual grammar;
- palette families and color-shading guidance;
- material rules for wood, foliage, bark, water, rock, cloth, light and shadow;
- excellent example finished assets;
- reusable source primitives and pieces such as:
  - trunk sections;
  - canopy/leaf clusters;
  - branches;
  - foliage clumps;
  - bark patches/details;
  - hollows/openings;
  - rock pieces;
  - flowers/mushrooms;
  - grass/ground edges;
  - roof/window/door pieces;
  - shadows/highlights/glow pieces;
- composition recipes and best practices such as:
  - how to build a readable Greia tree;
  - how to make an interactive hollow tree;
  - how to make a readable bush hiding spot;
  - how to build a kid-friendly prop silhouette;
  - how to construct a scene-safe contact shadow;
  - how to preserve material richness without visual noise.

This layer is primarily an **authoring aid**, not a promise that every piece is directly rendered at runtime.

### Layer B — Shared Runtime Assets

This is a deliberately small canonical runtime-shared set.

Appropriate examples:

- Shell UI assets such as cards, panels, buttons, portal/profile frames, loading/error/empty-state art;
- canonical recurring characters where a globally recognizable identity is desired;
- generic FX/support assets such as contact shadows, fog strips, sunlight rays, shimmer and common particle sprites;
- a limited number of environment support assets that are truly generic.

This set must remain curated. It is not the home for every Activity-specific tree, cave, house or game prop.

### Layer C — Activity Visual Package

This is bespoke source art created for one Activity.

For example, *Nascondino nel Bosco* may need:

- a big old hollow tree;
- a berry hiding bush;
- a rock/burrow hiding spot;
- a pond/reed hiding spot;
- a tall perch tree;
- bespoke animal visuals;
- clue/found-state artwork.

The Activity-authoring agent should:

1. inspect the Authoring Kit;
2. reuse relevant style, primitives and recipes;
3. reuse exact finished assets only where they genuinely fit;
4. create the missing Activity-specific final artwork.

Example Activity-local sources:

```text
activities/nascondino_bosco/art/src/hollow_tree.svg
activities/nascondino_bosco/art/src/berry_bush.svg
activities/nascondino_bosco/art/src/rock_burrow.svg
```

Another Activity can create a different tree using the same visual language and some of the same primitive ingredients. This gives Greia coherence without cloning the same scenery everywhere.

### Layer D — Runtime Scene System

The runtime consumes both:

- Shared Runtime Assets;
- Activity Visual Package assets.

through one semantic rendering architecture.

It handles:

- responsive placement;
- z/layer ordering;
- parallax;
- cheap ambient motion;
- light/atmosphere passes;
- bounded caching;
- fail-soft behavior.

The runtime should not care whether the source asset was created entirely from scratch, derived from shared primitives, or directly reused from the shared runtime set.

---

## 3. The correct meaning of reuse

Reuse is not only “render the exact same PNG again.”

Greia supports several levels of reuse:

1. **Style reuse** — the same visual language.
2. **Grammar reuse** — the same construction/readability rules.
3. **Primitive reuse** — leaf clusters, bark elements, shadows, highlights, etc.
4. **Recipe reuse** — a proven method for constructing a prop or scene element.
5. **Finished-asset reuse** — the exact same completed asset, when appropriate.

For environment props, the first four are often more important than literal finished-asset reuse.

For Shell UI, literal finished-asset reuse is normally desirable.

For canonical characters, identity consistency is normally more important than environmental variety.

---

## 4. Why this is viable

This architecture combines:

- **variety** — each Activity can have bespoke artwork;
- **coherence** — all artwork derives from shared Greia rules and ingredients;
- **scalability** — the project does not need to predict every possible tree or prop;
- **performance** — target devices consume flattened final renditions, not hundreds of source fragments;
- **quality** — authoring effort is spent on what the actual Activity needs.

It also avoids the failed middle state where the shared system upgrades only the background while primitive programmer-drawn gameplay assets remain visually incompatible.

---

## 5. Authoring-time richness, runtime economy

The authoring process may be compositionally rich:

```text
trunk
+ branch pieces
+ canopy groups
+ bark details
+ hollow
+ highlights
+ shadows
```

but the build process should flatten that authored composition into one or a few efficient runtime renditions.

Therefore:

> **rich composition at authoring time; economical composition at runtime.**

The runtime compositor should handle meaningful scene objects/layers, not hundreds of individual leaf fragments.

---

## 6. Promotion loop

Activity-created artwork must not automatically flood the shared library.

A new local asset or primitive may be promoted only when it proves genuinely general and reusable.

Promotion flow:

```text
Activity-local derived asset
→ visual review
→ demonstrated general value
→ deliberate promotion into Authoring Kit or Shared Runtime Assets
```

Examples that might deserve promotion:

- a useful generic hollow-opening primitive;
- a new contact-shadow treatment;
- a high-value foliage cluster;
- a reusable decorative frame;
- a generic interaction highlight.

This lets the library grow organically from real needs.

---

## 7. Activity-authoring workflow

For a new or visually migrated Activity, the authoring agent should:

1. identify the important visible objects the Activity genuinely needs;
2. read the Greia visual style/authoring authorities;
3. inspect/search the Authoring Kit for relevant finished assets, primitives and recipes;
4. reuse an exact finished asset only when it truly fits;
5. otherwise compose/modify primitives and create missing bespoke artwork;
6. visually review important newly authored assets individually;
7. assemble the Activity scene from accepted assets;
8. add suitable depth, grounding, lighting, parallax and ambient motion;
9. build source art into low-cost runtime renditions;
10. register those final assets in an Activity-local semantic catalogue/package;
11. test the complete Activity visually through the Activity Simulator;
12. promote newly created pieces to the shared kit only if they have demonstrated broad reuse value.

The Activity remains authoritative for game logic, state, hit testing, scoring and progression. The visual authoring/runtime systems provide coherent artwork and presentation infrastructure.

---

## 8. Nascondino lesson

The first Scene Compositor integration in *Nascondino nel Bosco* proved useful runtime plumbing, but it also exposed the architectural distinction this document formalizes:

- shared environment/background art improved;
- old primitive gameplay props and animals remained;
- the result looked like two visual systems glued together.

That is not a complete visual migration.

A proper migration should use the Authoring Kit to create bespoke Nascondino final assets for its hiding spots, animals and other major gameplay visuals, while continuing to use the shared runtime compositor and semantic asset pipeline.

---

## 9. Current open question: who should create the base Authoring Kit?

Before expanding the library further, Greia should compare the quality of the current authored base assets against a fresh high-ambition set produced by the local authoring agent.

The immediate benchmark therefore asks the local agent to recreate/reinterpret representative current visual assets at **extremely high quality**, then produce comparative screenshots for independent owner review.

The purpose is not to automatically replace the existing library. It is to learn:

- who produces the stronger base assets;
- which asset families the local agent handles best;
- whether its work is suitable for Authoring Kit primitives/references;
- whether the project should rely more heavily on the local agent for future source-art generation.

Exact runbook:

```text
docs/testing/2026-08-21_VISUAL_AUTHORING_LIBRARY_COMPARISON.md
```

No result from that benchmark is accepted until the owner has received the generated visual-review ZIP and independently inspected the pixels.
