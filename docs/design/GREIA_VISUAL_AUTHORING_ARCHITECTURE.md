# Greia Visual Authoring Architecture

**Status:** active architecture clarification  
**Date:** 2026-08-21  
**Parent visual authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Generic library taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Practical user-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

This document separates two concerns that must not be conflated:

1. **maintaining Greia's bundled visual toolbox** and deciding what source artwork belongs in it;
2. **teaching arbitrary Activity-authoring agents how to use that toolbox well**, including when to reuse, compose/adapt, or create original Activity-local artwork.

The owner's local-agent art benchmarks belong only to the first concern. They are **not evidence about arbitrary future user agents** and their model-specific strengths must not become Greia architecture.

The stable product goal is:

> **Greia ships strong, varied, generic visual resources; a model-agnostic visual-authoring skill teaches Activity authors how to exploit them and how to create coherent original art when the library does not directly contain what an Activity needs.**

---

## 2. Two separate tracks

### Track A — Maintainer-side visual toolbox production and curation

This is a Greia maintainer/content-production concern.

The owner's local agent was benchmarked only to answer whether it can re-author Greia's existing source artwork at higher quality than the earlier baseline.

That experiment can tell us:

- whether this maintainer-side agent can create stronger source masters;
- which existing assets are worth retaining or replacing;
- which new generic ingredients are worth adding;
- how to improve Greia's bundled authoring toolbox.

It does **not** tell us:

- whether other people's Activity-authoring agents can draw at the same level;
- whether another model will follow the same SVG technique;
- whether the local agent's construction tricks should become universal instructions;
- whether a repeatedly refined specimen predicts future Activity-authoring quality.

#### 2.1 Source bundles are not automatically core packs

Historical/theme-oriented source bundles such as:

```text
forest_meadow
workshop
clinic
reading_classroom
fantasy_village_night
water_pond
```

are useful as provenance, source pools and reference compositions.

They are **not automatically the primary generic authoring taxonomy**.

In particular, a `Clinic / Care` or `Fantasy Village` bundle should not become a core Greia pack merely because it already exists. Specialized bundles are only worth maintaining as reusable extensions when multiple real Activities demonstrate that need.

The primary authoring interface should instead organize reusable resources by broad semantic usefulness. Authority:

```text
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
```

#### 2.2 Generic authoring collections

The intended initial generic collections are:

```text
Nature & Landscape
Interiors & Architecture
Furniture & Storage
Everyday Props & Containers
Making, Learning & Play
Lighting, Atmosphere, FX & Shadows
Shared UI
Canonical Characters
```

These collections may reference assets from multiple historical source bundles without copying them.

A useful cabinet should be discoverable as a cabinet, not only because an agent happened to know it was originally drawn for a clinic scene.

#### 2.3 Maintainer production rule

Maintainer-side art production should work at **generic family / useful toolbox scale**, not by endlessly optimizing one specimen or blindly walking through old themed folders.

The workflow is:

1. preserve reviewed source/provenance;
2. expose useful assets through generic semantic indexes;
3. identify broad reusable coverage gaps;
4. author missing generic assets/families at pack scale;
5. review actual pixels and target-size behavior;
6. promote only the strongest reviewed resources;
7. keep specialized theme art separate unless repeated demand justifies an extension.

---

### Track B — Activity Visual Authoring Skill

This is the **user/developer-facing Greia capability**.

The skill must be useful to a broad range of Activity-authoring agents. It must not assume:

- a specific model family;
- the owner's local agent;
- SVG expertise;
- image-generation access;
- a professional artist;
- one fixed asset-generation technique.

An Activity-authoring agent should be able to:

1. inventory what the Activity visually needs;
2. browse Greia's generic authoring-library indexes by semantic role;
3. inspect relevant source-pack examples/previews where helpful;
4. understand Greia style and runtime constraints;
5. reuse a finished asset when it genuinely fits;
6. compose/adapt existing resources when that efficiently creates a bespoke result;
7. create new Activity-local art when no library object is suitable;
8. keep new art coherent through palette, material, lighting, grounding, typography and child-readability rules;
9. flatten rich authoring work into efficient runtime assets;
10. integrate through Greia's existing package/scene/runtime boundaries;
11. inspect the finished Activity at target sizes.

The skill is about **using the visual ecosystem intelligently**, not about reproducing the maintainer agent's drawing process.

---

## 3. Greia visual resource model

### 3.1 Generic Authoring Library

This is the primary discovery layer for Activity authors.

Recommended index location:

```text
assets/visual/authoring_library/
```

The indexes reference existing source assets and ingredients rather than duplicating files.

Each entry should expose useful semantic metadata such as:

- generic discovery ID;
- source pack / source path;
- source semantic ID where applicable;
- family / role;
- useful tags;
- finished asset vs ingredient;
- recommended size range where known;
- preview/reference metadata where useful.

### 3.2 Source / provenance bundles

Versioned source bundles remain valuable because they preserve:

- original artwork;
- material/style relationships;
- compositions;
- historical provenance;
- themed reference context.

Examples include promoted Forest/Meadow and Workshop bundles plus older Clinic/Reading/Fantasy/Water source families.

These are source pools and references, not necessarily the first thing an Activity agent should browse.

### 3.3 Shared Runtime Assets

A small subset genuinely benefits from direct canonical runtime reuse, especially:

- Shell/UI frames and controls;
- canonical recurring characters where identity consistency matters;
- generic shadows, light/atmosphere overlays and FX;
- other resources whose sameness is desirable rather than boring.

These use Greia's explicit semantic catalogue/runtime rendition architecture.

### 3.4 Activity-local Visual Assets

An Activity is expected to own bespoke art when its design requires it.

Examples:

```text
activities/my_activity/assets/hollow_tree.png
activities/my_activity/assets/special_machine.png
activities/my_activity/assets/alien_flower.png
activities/my_activity/assets/animal_fox.png
```

The authoring workspace may use SVG, large transparent PNG, or other approved source representations. Runtime artifacts must follow Greia package and renderer constraints.

Activity-local assets are **not automatically promoted** into the generic library.

---

## 4. The core Activity-authoring decision

For each important visual object, choose one of three paths.

### A. REUSE

Use an existing finished Greia resource directly when it already fits well.

Examples:

- a generic cloud;
- a contact shadow;
- a standard UI card;
- canonical Lilli;
- a useful table, rock or bowl that actually suits the composition.

### B. COMPOSE / ADAPT

Use available assets, ingredients or visual references to build a bespoke Activity-local result.

Examples:

- derive a distinct hiding tree using generic nature references/ingredients;
- combine water-edge, reeds, rocks and lighting into a custom interactive pond area;
- adapt shelf/window/material language into a unique science-machine scene.

This happens at authoring time. The finished runtime result should normally become one or a few efficient Activity-local assets rather than hundreds of fragments.

### C. CREATE ORIGINAL

Create a new Activity-local asset when the library does not provide a suitable basis.

Examples:

- telescope mechanism;
- fantasy musical machine;
- special animal pose;
- unusual puzzle prop;
- alien plant.

The new asset should follow Greia's visual relationships without needing to resemble an existing object.

### Hard rule

> **Never force an unsuitable shared asset merely to claim reuse, and never leave ugly programmer-drawn primitives merely because the exact finished prop was not already packaged.**

---

## 5. Coherence without sameness

Greia does not want every forest to contain the same tree or every room to contain the same shelf.

Coherence comes from:

- palette/value relationships;
- line/edge language;
- material treatment;
- lighting direction and softness;
- grounding/contact behavior;
- child-readable silhouettes;
- typography/UI conventions;
- character language;
- compatible depth/parallax/motion treatment.

Variety comes from:

- different silhouettes and proportions;
- different arrangements;
- Activity-specific detail;
- adaptation/composition;
- newly created local assets;
- selective rather than universal literal reuse.

---

## 6. Authoring-time richness, runtime economy

Greia can tolerate rich source construction on a development machine but must remain cheap on the target appliance.

Therefore:

> **rich composition at authoring time; economical composition at runtime.**

An agent may construct artwork using multiple pieces, layers or source techniques, then flatten it into an efficient runtime rendition.

The low-end runtime must not be required to:

- rasterize normal SVG masters;
- scan source packs dynamically;
- decode many fragments every frame;
- run heavyweight composition software;
- recreate authoring-time layer graphs.

The existing semantic catalogue, bounded visual cache and scene compositor remain the runtime foundation.

---

## 7. Visual review responsibility

The producing agent's prose is not visual evidence.

For meaningful visual work:

- review actual rendered pixels;
- inspect important assets individually;
- inspect complete compositions;
- test representative child-facing sizes;
- reject clipping, tiny text, floating objects, weak grounding, inconsistent lighting and obvious style mismatch;
- package curated PNG evidence when owner review is required.

Evidence contract:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

---

## 8. Promotion and specialization

A candidate/local asset may enter the generic library only when it has demonstrated broad value.

```text
candidate/local asset
→ visual review
→ broadly reusable?
→ generic semantic index / source promotion
```

Highly specialized assets may remain:

- Activity-local;
- source-provenance only;
- optional themed extensions;
- references/examples.

Do not turn every specialized object into a core Greia asset.

---

## 9. Current maintainer-side correction

The local agent has already demonstrated that it can improve source artwork at pack scale. Forest/Meadow v0.3 and Workshop v0.2 are useful source bundles.

The next job is **not** to blindly continue `Clinic → Reading → Fantasy → Water` as core packs.

The immediate maintainer task is:

```text
2026-08-21_GENERIC_VISUAL_LIBRARY_CONSOLIDATION.md (archived; see git history)
```

That task builds the first generic semantic indexes from reviewed/promoted source art, harvests broadly reusable pieces from the Clinic candidate, keeps medical-specific pieces specialized, and identifies the next true generic coverage gaps.

The owner's local agent remains an implementation detail of maintainer-side art production, not a dependency of Greia Activity authoring.
