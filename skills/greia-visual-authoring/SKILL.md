---
name: greia-visual-authoring
description: Model-agnostic guide for Activity-authoring agents to discover Greia's generic visual toolbox, reuse or adapt suitable assets, create coherent original Activity art, and integrate it through the existing runtime.
---

# Greia Visual Authoring Skill

**Status:** living user-agent skill  
**Reviewed:** 2026-08-21  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
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

Do not confuse this skill with Greia's maintainer-side process for producing source artwork.

---

## 1. Read the visual authorities before drawing

For substantive visual work, read:

```text
1. docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
2. docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
3. docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
4. docs/design/GREIA_VISUAL_STYLE_GUIDE.md
5. relevant generic authoring-library indexes and previews
6. deeper source-pack README/catalogue/reference material only when useful
7. the Activity's manifest, assets and rendering code
```

At authoring time you may inspect repository source assets and metadata. **Runtime directory scanning remains forbidden.**

---

## 2. Start with the Activity's visual needs

Write a short visual inventory before searching the library.

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

Do not let existing assets dictate the game design merely because something convenient already exists.

---

## 3. Search the generic authoring library with discovery tooling

The canonical generic authoring index lives under:

```text
assets/visual/authoring_library/
```

### Discovery Helper (`tools/visual_authoring_library.py`)

When working in the repository environment, use the discovery CLI helper to search and inspect library assets rather than manually grepping TOML files or scanning directories:

```bash
# List all 6 generic collections and counts
python tools/visual_authoring_library.py collections

# Search for assets across semantic ID, tags, roles, and notes
python tools/visual_authoring_library.py search chair
python tools/visual_authoring_library.py search "book storage" --status preferred

# Inspect full metadata, recommended sizes, and exact source path for an asset
python tools/visual_authoring_library.py show furniture.seating.chair.spindle_wood

# Machine-readable JSON output (ideal for subagents and scripts)
python tools/visual_authoring_library.py search tableware --json
```

### Admission Status Rules

The library explicitly distinguishes between two asset states:

1. **`library_status = "preferred"` (Use First for Direct `REUSE`):**
   - Fully reviewed, high-craft, structurally sound assets.
   - Recommended as first-choice direct reuse art for Activity scenes.
2. **`library_status = "candidate_reference"` (Use for `COMPOSE / ADAPT`):**
   - Useful reference or adaptation material; provisional staging assets.
   - Use these as inspiration, base geometry, or material reference for Activity-local adaptations rather than direct final art.

Shared UI and canonical characters remain their own stronger-consistency families.

The generic indexes may point into several historical source bundles. Follow their source references when you need:

- a higher-resolution master;
- material/style context;
- composition examples;
- a useful ingredient;
- a related visual variant.

### Important

Do **not** assume an Activity should browse or copy a theme such as `Clinic`, `Classroom`, or `Fantasy Village` as a whole.

Those folders may contain useful source art, but Activity authors should normally search by reusable semantic need first.

Example:

```text
need: cabinet
→ furniture/storage index
→ inspect useful cabinet sources
```

not:

```text
maybe a clinic has a cabinet
→ browse medical scene pack
```

---

## 4. For each important asset choose: REUSE, COMPOSE/ADAPT, or CREATE ORIGINAL

### 4.1 REUSE

Reuse a finished Greia asset directly when it genuinely fits.

Good candidates often include:

- canonical UI pieces;
- generic clouds / rocks / ground details;
- furniture or containers that suit the scene without compromise;
- fog/light overlays;
- contact shadows;
- canonical recurring characters.

Do not alter shared source files in place from inside an Activity.

### 4.2 COMPOSE / ADAPT

Use Greia source assets, ingredients, material treatment or examples to create a bespoke Activity-local result.

Examples:

- derive a unique hiding tree from generic nature references;
- combine rocks, reeds, water-edge language and light into a bespoke pond hiding spot;
- adapt a shelf/window/material treatment into a unique science-machine scene;
- use a generic bowl/container vocabulary as the basis for a special Activity prop.

Authoring may be rich. The finished runtime result should normally be flattened into one or a small number of efficient Activity-local assets.

### 4.3 CREATE ORIGINAL

Create original Activity-local artwork when the generic toolbox does not provide a suitable basis.

This is normal and expected.

Examples:

- unique puzzle machines;
- custom animals/poses;
- unusual vehicles;
- fantasy props;
- scientific apparatus;
- medical/specialized equipment;
- bespoke hiding places;
- Activity-specific reward illustrations.

Use Greia's visual relationships so the new asset belongs in the same world.

### Hard rule

> **Never force an unsuitable library asset merely to claim reuse. Never leave ugly programmer-drawn primitives in the finished Activity merely because the exact prop was not already packaged.**

---

## 5. The generic library is a toolbox, not a completeness promise

Greia should not ship a finished object for every imaginable Activity need.

A generic pack should provide broadly reusable assets, ingredients and visual references.

Specialized objects often belong in the Activity itself.

Examples:

```text
generic library:
window, table, bowl, bottle, cushion, tree, rock, light shaft

Activity-local:
stethoscope puzzle device, alien microscope, pirate telescope mechanism,
special tree with a coded door, one-off fantasy musical machine
```

A specialized theme pack should only become a maintained Greia extension when several real Activities justify it.

---

## 6. Visual quality bar

Greia's simplified production constraints are not permission for cheap art.

Aim for:

- polished storybook / toy-diorama presentation;
- strong silhouettes;
- readable major masses before fine detail;
- warm controlled color relationships;
- material-specific light/shadow rather than one generic gradient everywhere;
- clean alpha edges;
- convincing grounding/contact;
- enough internal structure to avoid enlarged-icon appearance at hero sizes;
- restrained detail that survives downsampling;
- coherence without identical cloning.

Avoid as final represented art unless intentionally appropriate:

- tutorial circles/rectangles/polygons;
- programmer-placeholder scenery;
- identical assets copied everywhere;
- floating props;
- glossy balloon foliage used as a universal formula;
- text baked into decorative art where localization should own it;
- excessive micro-detail that disappears at runtime size.

---

## 7. Coherence without sameness

Match Greia through relationships, not literal copying.

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

---

## 8. Scene and gameplay integration

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

## 9. Authoring-time richness, runtime economy

Preferred flow:

```text
generic Greia art/reference
+ Activity-specific source work
        ↓
authoring-time reuse/composition/adaptation
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

Use existing Greia semantic/shared visual APIs and package boundaries. Do not introduce a parallel global asset catalogue or cache.

---

## 10. Shared runtime assets versus Activity-local assets

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

Activity-local art should remain portable with the package and must not reach arbitrary host filesystem paths.

If a needed Activity-local scene case is not yet supported, extend the existing Greia package/scene boundary cleanly instead of inventing a one-off unbounded loader.

---

## 11. Characters

Working shared cast:

- Lilli — unicorn Puff;
- Nino — owl Bean;
- Tito — fox Puff;
- Momo — friendly monster Puff.

Canonical recurring characters should preserve recognizable identity across Activities.

Default grammar:

- dominant readable body mass;
- large face;
- limited anatomy;
- identity through silhouette/color/ears/horn/tuft/tail/accessory;
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

---

## 12. UI and typography

Use Greia's typography roles and shared UI language for normal Activity controls.

Do not create a separate tiny desktop-style UI inside each Activity.

Important rules:

- Nunito Sans is the normal interface family;
- child-facing text must remain large/readable;
- meaningful text should respect accepted low-size guardrails;
- standard controls should use shared visual treatment where appropriate;
- protected Home/Back semantics remain platform-owned;
- Activity art must not imitate trusted platform chrome.

---

## 13. Review before integration

Review important newly created assets individually before hiding them inside a full scene.

Check:

- silhouette;
- grounding;
- material treatment;
- alpha edges;
- target-size readability;
- compatibility with adjacent Greia assets;
- whether it is too obviously copied from a reference;
- whether it still looks like a programmer placeholder.

Then inspect the composed Activity.

Never use a busy scene to conceal weak assets.

---

## 14. Visual acceptance

A prose `PASS` from the producing agent is not enough.

For meaningful visual work:

1. render through the Activity Simulator when runtime behavior is involved;
2. capture representative screenshots;
3. inspect clipping, hierarchy, scaling, grounding, occlusion and visual coherence;
4. include responsive evidence where relevant;
5. follow `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`;
6. prepare the requested screenshot ZIP when owner review is required.

Visual evidence must represent what was actually rendered.

---

## 15. Promotion rule

Do not automatically add every Activity-created asset to the generic/global library.

Promotion is deliberate:

```text
Activity-local asset
→ proven visually useful
→ broadly reusable?
→ maintainer review
→ optional generic-library/source-pack promotion
```

Likewise, a specialized source asset may remain theme-only even when it is visually good.

---

## 16. Explicit failure patterns

Do not:

- assume a specific model can reproduce the maintainer's art workflow;
- treat one maintainer benchmark as a universal capability claim;
- make Activity authors browse themed folders as the primary discovery method;
- copy exact pack objects everywhere when adaptation/original art would be better;
- create a giant runtime warehouse for every possible prop;
- leave primitive gameplay art behind a polished background;
- create one-off runtime image loaders/caches;
- rasterize normal SVG source masters on the low-end target;
- scan arbitrary visual directories at runtime;
- overfit authoring rules into rigid geometric templates;
- claim visual quality without inspecting actual pixels.
