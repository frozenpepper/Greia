---
name: greia-visual-authoring
description: Model-agnostic guide for Activity-authoring agents to use Greia art packs, compose/adapt existing assets, create coherent original Activity art, and integrate it through the existing visual runtime.
---

# Greia Visual Authoring Skill

**Status:** living user-agent skill  
**Reviewed:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Main visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Style guide:** `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`

## 0. Audience and scope

This skill is for **arbitrary agents/models helping a user create or modify a Greia Activity**.

It must not assume:

- a particular model provider;
- the Greia maintainer's local agent;
- image-generation access;
- professional illustration software;
- strong SVG expertise;
- one fixed asset-creation technique.

Your job is to make the Activity look coherent, polished and Greia-native by intelligently using the visual resources already available and creating Activity-local art where necessary.

Do not confuse this skill with Greia's maintainer-side process for producing the bundled base art packs.

---

## 1. Read the visual authorities before drawing

For substantive visual work, read:

```text
1. docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
2. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
3. docs/design/GREIA_VISUAL_STYLE_GUIDE.md
4. the README/catalogue/preview material for the relevant art pack(s)
5. the Activity's existing manifest, assets and rendering code
```

Use pack metadata and previews to understand what exists before inventing replacements.

At authoring time you may inspect repository asset directories and source metadata. **Runtime directory scanning remains forbidden.**

---

## 2. Start with the Activity's visual needs, not with the library

Write a short visual inventory for the Activity.

Typical roles:

```text
background / room base
far scenery
mid scenery
ground / playfield
interactive props
characters / creatures
feedback / clues / rewards
foreground framing
atmosphere / lighting
Activity-local UI
launcher icon
```

For each important role, decide what the finished Activity actually needs visually.

Do not let the existing library dictate the game design merely because a convenient asset exists.

---

## 3. For each asset choose: REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL

This is the central authoring decision.

### 3.1 REUSE

Reuse a finished Greia asset directly when it genuinely fits.

Good candidates often include:

- canonical UI pieces;
- generic clouds;
- fog/light overlays;
- contact shadows;
- generic rocks/grass/flowers;
- canonical recurring characters;
- environment props that match the Activity without awkward compromise.

Do not alter shared source files in place from inside an Activity.

### 3.2 COMPOSE / ADAPT

Use pack artwork as source ingredients/reference and create a bespoke Activity-local result.

Examples:

- create a unique hiding tree from the Forest/Meadow visual language and useful foliage/trunk ingredients;
- combine rocks, reeds, water-edge language and lighting into a custom pond hiding spot;
- adapt workshop shelf/window/material treatment into a unique science-machine scene;
- derive a new prop from an existing material/style treatment while changing silhouette and function.

The composition may be rich during authoring, but the finished runtime object should normally be flattened into one or a small number of efficient Activity-local assets.

### 3.3 CREATE ORIGINAL

Create original Activity-local artwork when the art packs do not provide a good fit.

This is normal and expected.

Examples:

- unique puzzle machines;
- custom animals/poses;
- unusual vehicles;
- fantasy props;
- scientific apparatus;
- Activity-specific hiding places;
- bespoke reward illustrations.

Use Greia's palette, material, lighting, silhouette and child-readability guidance so the new asset belongs in the same visual world.

### Hard rule

> **Never force an unsuitable shared asset merely to claim reuse. Never leave ugly programmer-drawn primitives in the finished Activity merely because the exact prop was not already packaged.**

---

## 4. Where to look for art

Current broad source packs include:

```text
assets/visual/environments/forest_meadow/
assets/visual/environments/workshop/
assets/visual/environments/clinic/
assets/visual/environments/reading_classroom/
assets/visual/environments/fantasy_village_night/
assets/visual/environments/water_pond/
assets/visual/ui/
assets/visual/library/
```

Also inspect:

```text
assets/visual/packs_v0.1.toml
assets/visual/library_v0.1.toml
assets/catalog/shared_visuals_v1_source.toml
```

The exact inventory evolves. Prefer semantic roles and pack metadata over filename guessing.

---

## 5. Visual quality bar

Greia's simplified production constraints are not permission for cheap art.

Aim for:

- polished storybook / toy-diorama presentation;
- strong silhouettes;
- readable major masses before fine detail;
- warm, controlled color relationships;
- material-specific light/shadow rather than one generic gradient everywhere;
- clean alpha edges for composable assets;
- convincing grounding/contact;
- enough internal structure to avoid enlarged-icon appearance at hero sizes;
- restrained detail that survives downsampling;
- coherent but non-identical assets across Activities.

Avoid as final represented art unless intentionally appropriate:

- tutorial circles/rectangles/polygons;
- programmer-placeholder scenery;
- identical trees copied across unrelated Activities;
- floating props;
- glossy balloon foliage used as a universal formula;
- text baked into decorative art where localization should own it;
- excessive micro-detail that disappears at actual runtime size.

---

## 6. Coherence without sameness

Match Greia through relationships, not cloning.

Preserve coherence through:

- palette/value relationships;
- material logic;
- line/edge language;
- soft storybook depth;
- compatible lighting;
- grounding/contact treatment;
- character proportions/style;
- typography and UI conventions;
- similar visual density at equivalent importance levels.

Create variety through:

- silhouette;
- proportion;
- pose;
- object arrangement;
- local detail;
- Activity-specific storytelling;
- original assets.

Two forest Activities should be able to feel like the same Greia world without containing the exact same forest.

---

## 7. Scene and gameplay integration

A visual overhaul is incomplete if only the background uses good art while gameplay remains primitive.

The final Activity should visually integrate:

- environment;
- interactive objects;
- characters/creatures;
- feedback;
- UI.

Interactive objects must remain readable against decoration.

Typical layer order:

```text
sky / room base
far background
mid background
ground / playfield
interactive props
characters / actors
foreground framing
atmosphere / light / FX
Activity-local UI
protected Greia platform chrome
```

Use the existing scene/runtime system where appropriate instead of creating another compositor.

---

## 8. Authoring-time richness, runtime economy

The development machine may use rich source assets and composition. The target device must remain cheap.

Preferred flow:

```text
shared art-pack source/reference
+ Activity-specific source work
        ↓
authoring-time composition/adaptation
        ↓
reviewed Activity-local master
        ↓
build/flatten to efficient runtime rendition
        ↓
Greia package/runtime resolver + scene renderer
```

Do not make the target appliance:

- rasterize ordinary SVG masters at runtime;
- scan source directories to discover visuals;
- decode or scale images every frame;
- rebuild complex authoring compositions during play;
- maintain an unbounded image cache.

Use Greia's existing semantic/shared visual APIs and package boundaries. Do not introduce a parallel global asset catalogue or cache.

---

## 9. Shared runtime assets versus Activity-local assets

### Shared runtime asset
Use a semantic shared visual when sameness is useful and the asset is already promoted into the shared runtime catalogue.

Examples:

```text
ui.card.activity
ui.panel.base
ui.shadow.soft
character.lilli
```

Use the established semantic resolver/API rather than hard-coding host paths.

### Activity-local asset
Keep bespoke Activity art inside the Activity package, normally under its `assets/` tree.

Activity-local art should remain portable with the Activity package and must not reach out to arbitrary host filesystem paths.

If the current Activity-local semantic scene integration does not yet support a needed case, extend the existing Greia package/scene boundary cleanly rather than inventing a one-off unbounded loader.

---

## 10. Characters

Working shared cast:

- Lilli — unicorn Puff;
- Nino — owl Bean;
- Tito — fox Puff;
- Momo — friendly monster Puff.

Canonical recurring characters should preserve recognizable identity across Activities.

Default character grammar:

- dominant readable body mass;
- large face;
- limited anatomy;
- identity through silhouette, color, ears/horn/tuft/tail/accessory;
- whole-body motion rather than detailed skeletal rigs.

Shared motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

A blink must visibly close the eyes.

Activity-specific creatures do not need to reuse the canonical cast, but should fit the Greia visual language.

---

## 11. UI and typography

Use Greia's typography roles and shared UI language for normal Activity controls.

Do not create a separate tiny desktop-style UI inside each Activity.

Important rules:

- Nunito Sans is the normal interface family;
- standard child-facing text should remain large and readable;
- meaningful text should generally stay above the accepted low-size guardrails;
- standard controls should use shared visual treatment where appropriate;
- protected Home/Back semantics remain platform-owned;
- Activity art must not imitate trusted platform chrome.

Expressive/pedagogical content may use Activity-specific art/type treatment where justified.

---

## 12. Review before integration

Review important newly created assets individually before hiding them inside a full scene.

Check:

- silhouette;
- grounding;
- material treatment;
- alpha edges;
- target-size readability;
- whether it looks compatible with adjacent Greia assets;
- whether it is too obviously copied from a shared reference;
- whether it still looks like a programmer placeholder.

Then inspect the composed Activity.

Never use a busy scene to conceal weak assets.

---

## 13. Visual acceptance

A prose `PASS` from the producing agent is not enough.

For meaningful visual work:

1. render the actual Activity through the Activity Simulator when runtime behavior is involved;
2. capture representative screenshots;
3. inspect text clipping, hierarchy, scaling, grounding, occlusion and visual coherence;
4. include responsive evidence where relevant;
5. follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`;
6. when owner review is requested, prepare the required screenshot ZIP for attachment.

Visual evidence must represent what was actually rendered, not hand-written claims.

---

## 14. Promotion rule

Do not automatically add every Activity-created asset to the global packs.

Promotion is deliberate:

```text
Activity-local asset
→ proven visually useful
→ broadly reusable?
→ maintainer review
→ optional promotion to a bundled art pack/shared runtime set
```

This keeps the art library useful instead of turning it into a random asset dump.

---

## 15. Explicit failure patterns

Do not:

- assume a specific model can reproduce the maintainer's local-agent art workflow;
- treat one local-agent benchmark as a universal capability claim;
- copy exact pack objects everywhere when adaptation/original art would be better;
- create a giant runtime warehouse for every possible prop;
- leave primitive gameplay art behind a polished shared background;
- create one-off runtime image loaders/caches;
- rasterize normal SVG source masters on the low-end target;
- scan arbitrary visual directories at runtime;
- make content meaning depend on continuous animation;
- overfit authoring rules into rigid geometric templates;
- claim visual quality without inspecting the actual pixels.
