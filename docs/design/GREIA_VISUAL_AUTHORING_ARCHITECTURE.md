# Greia Visual Authoring Architecture

**Status:** active architecture clarification  
**Date:** 2026-08-21  
**Parent visual authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Practical user-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

This document separates two concerns that must not be conflated:

1. **maintaining Greia's bundled base art packs**, including deciding who or what creates the best pack artwork;
2. **teaching arbitrary Activity-authoring agents how to use those packs well**, including when to reuse, compose, adapt, or create original Activity-local artwork.

The recent local-agent art benchmarks belong only to the first concern. They are **not evidence about the capabilities of arbitrary future user agents**, and their model-specific strengths or weaknesses must not become Greia architecture.

The stable product goal is:

> **Greia ships strong, varied, reusable visual art packs; a model-agnostic visual-authoring skill teaches Activity authors how to exploit those packs and how to create coherent original art when the packs do not directly contain what the Activity needs.**

---

## 2. Two separate tracks

### Track A — Base Art Pack Production and Curation

This is a Greia maintainer/content-production concern.

Greia needs excellent bundled visual material covering useful recurring domains such as:

- Forest / Meadow;
- Workshop;
- Clinic / Care;
- Reading / Classroom;
- Fantasy / Village / Night;
- Water / Pond;
- Shared UI;
- canonical characters, FX, lighting, shadows, and other cross-Activity families.

The current owner's local agent was benchmarked because it might be able to **re-author these packs at higher visual quality than the earlier baseline**. That experiment answers only questions such as:

- can this maintainer-side agent produce stronger tree, bush, rock, cloud, room-prop, water, UI, or FX masters than the existing ones?
- is its output worth promoting into Greia's bundled packs?
- which pack families should be re-authored first?

It does **not** answer:

- whether other people's Activity-authoring agents can produce the same quality;
- whether another model will follow the same recipes;
- whether future agents should be taught the local agent's exact SVG techniques;
- whether one repeatedly refined hero tree is a useful proxy for general Activity authoring.

Those are different questions.

#### 2.1 Pack-production rule

Base-pack work should be evaluated **pack-by-pack**, not by endlessly optimizing one specimen.

A useful maintainer-side pack pass should:

1. preserve the existing pack as provenance/baseline;
2. recreate or improve the pack's representative masters;
3. preserve useful role coverage and composability;
4. provide comparison sheets and representative compositions;
5. test important runtime sizes;
6. undergo owner pixel review;
7. promote only the accepted results.

A single asset may receive a correction pass when a clear defect is exposed, but the workstream must not turn into indefinite per-object optimization.

---

### Track B — Activity Visual Authoring Skill

This is the **user/developer-facing Greia capability**.

The skill must be useful to a broad range of Activity-authoring agents. It must not assume:

- a specific model family;
- the owner's local agent;
- SVG expertise;
- access to image generation;
- access to a professional artist;
- one fixed asset-generation technique.

Instead, it teaches a decision process around the visual resources Greia already ships.

An Activity-authoring agent should be able to:

1. inspect the available art packs and their metadata/previews;
2. understand the Greia style and runtime constraints;
3. identify what the Activity visually needs;
4. reuse a finished pack asset when it genuinely fits;
5. compose or adapt existing pack pieces when that produces a bespoke result efficiently;
6. create a new Activity-local asset when no existing asset is a good match;
7. keep the new art coherent with Greia by following pack references, palette/material guidance, typography, lighting, grounding and interaction-readability rules;
8. flatten rich authoring-time work into efficient runtime assets;
9. integrate through Greia's existing package/scene/runtime boundaries rather than inventing a parallel image system;
10. visually inspect the finished Activity at target sizes.

The skill is therefore about **using the art ecosystem intelligently**, not about turning every future agent into the local agent that happened to create some base-pack masters.

---

## 3. The Greia visual resource model

### 3.1 Bundled Art Packs

These are curated Greia-provided visual resources.

A pack may contain a mixture of:

- polished finished reusable assets;
- reusable sub-elements/primitives;
- reference compositions;
- source masters;
- material/style notes;
- semantic role metadata;
- recommended size/composition/parallax/lighting guidance.

Not every asset is intended to be used literally in every Activity.

Examples:

```text
hero tree
secondary tree
bush
rock cluster
fallen log
cloud
fog strip
sunlight shaft
workbench
bookcase
lamp
window
pond edge
reeds
panel frame
contact shadow
```

### 3.2 Shared Runtime Assets

A small subset genuinely benefits from direct canonical runtime reuse, especially:

- Shell/UI frames and controls;
- canonical recurring characters where identity consistency matters;
- generic shadows, light/atmosphere overlays and FX;
- other resources whose sameness is desirable rather than boring.

These use Greia's explicit semantic catalogue/runtime rendition architecture.

### 3.3 Activity-local Visual Assets

An Activity is expected to own bespoke art when its design requires it.

Examples:

```text
activities/my_activity/assets/hollow_tree.png
activities/my_activity/assets/special_machine.png
activities/my_activity/assets/alien_flower.png
activities/my_activity/assets/animal_fox.png
```

The exact source-work area may include SVG, large transparent PNG, or other approved authoring-time representation. Runtime artifacts must follow Greia package and renderer constraints.

Activity-local visual assets are **not automatically promoted** to the shared library.

### 3.4 Authoring references and guidance

The packs and style guides provide visual references and practical rules. They help an agent answer questions such as:

- what color/value language does Greia use?
- how is wood or rock shaded?
- how much detail survives at child-facing sizes?
- how are objects grounded?
- how should an interactive prop separate from decorative scenery?
- how much atmosphere is appropriate?

These are guidance, not rigid geometric templates.

---

## 4. The core Activity-authoring decision

For each important visual object, an agent should choose one of three paths.

### A. REUSE

Use an existing finished pack asset directly when it already fits the Activity well.

Examples:

- a generic cloud;
- a contact shadow;
- a standard UI card;
- canonical Lilli;
- a generic rock cluster that genuinely suits the composition.

### B. COMPOSE / ADAPT

Use available assets or sub-elements as ingredients for a new Activity-specific result.

Examples:

- use a tree/trunk/foliage language from Forest/Meadow to construct a distinct hiding tree;
- combine generic pond-edge, reeds, rocks and lighting into a bespoke interactive pond area;
- reuse a workshop shelf form but alter contents, proportions and detail for a science Activity.

This happens at authoring time. The finished result should normally become one or a few efficient Activity-local runtime assets rather than hundreds of separately rendered fragments.

### C. CREATE ORIGINAL

Create a new Activity-local asset when the existing library does not contain a suitable basis.

Examples:

- a telescope mechanism unique to an astronomy game;
- a fantasy musical machine;
- a special animal pose;
- an unusual puzzle prop;
- an alien plant.

The new asset should use Greia's style references and quality rules, but it does not need to resemble an existing pack object.

The critical rule is:

> **never force an unsuitable shared asset merely to claim reuse, and never keep ugly programmer-drawn primitives merely because the exact finished prop was not already in the pack.**

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

- different silhouettes;
- different proportions;
- different arrangements;
- Activity-specific details;
- newly created assets;
- selective rather than universal literal reuse.

---

## 6. Authoring-time richness, runtime economy

Greia can tolerate rich source construction on a development machine but must remain cheap on the target appliance.

Therefore:

> **rich composition at authoring time; economical composition at runtime.**

An agent may construct an asset using multiple pieces, layers or source techniques, then flatten it into an efficient runtime PNG/WebP or other approved target representation.

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

- review the actual rendered pixels;
- inspect important assets individually;
- inspect the complete Activity composition;
- test representative child-facing sizes;
- reject clipping, tiny text, floating objects, bad grounding, inconsistent lighting, obvious style mismatch and broken hierarchy;
- when owner review is required, package curated PNG evidence into the required transfer ZIP.

The specific evidence contract lives in:

```text
docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md
```

---

## 8. Promotion loop

An Activity-local asset or newly produced pack candidate may be promoted only when it has demonstrated broad value.

```text
candidate/local asset
→ visual review
→ demonstrated reusable value
→ deliberate promotion into a bundled Art Pack or Shared Runtime Assets
```

Do not automatically turn every Activity-specific object into a global asset.

---

## 9. Current maintainer-side benchmark conclusion

The 2026-08-21 comparison established one narrow but useful result:

- the owner's local authoring agent can produce stronger Forest/Meadow source assets than the earlier baseline in several representative cases.

Subsequent tree/Authoring-Kit iterations became too specimen-focused and are **not architectural evidence about arbitrary future Activity agents**.

The correct continuation is:

1. stop hero-tree optimization as a workstream;
2. use the local agent, where helpful, to improve Greia's **base art packs** pack-by-pack;
3. independently develop and maintain the **model-agnostic Activity visual-authoring skill** in `skills/greia-visual-authoring/SKILL.md`;
4. validate that skill later with multiple agents/models as a separate compatibility effort.

Maintainer-side pack plan:

```text
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
```

The local agent's personal strengths are an implementation detail of pack production, not a dependency of Greia Activity authoring.
