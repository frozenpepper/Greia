# Greia Visual Authoring Kit — Variation Benchmark

**Date:** 2026-08-21  
**Purpose:** prove that the preferred local authoring agent can turn the challenger quality level into a reusable **authoring grammar/kit** that produces coherent but visibly different assets rather than cloning one tree formula.

Read first:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/reviews/visual/2026-08-21_authoring-library-comparison/PRIMARY_REVIEW.md
skills/greia-visual-authoring/SKILL.md
```

## Why this gate exists

The previous benchmark established that the local authoring agent produces stronger environment/nature source art than the current Forest/Meadow baseline.

However, the challenger set also exposed a risk: several foliage assets reuse the same rounded lobe + large pale highlight treatment. If that becomes a recipe copied mechanically, Greia will merely replace one kind of sameness with another.

This gate therefore tests the real Authoring-Kit idea:

> **same Greia style and construction knowledge, genuinely different silhouettes and material treatments.**

Do not do runtime integration in this task.

## 1. Preserve benchmark provenance

Do not overwrite:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/
docs/reviews/visual/2026-08-21_authoring-library-comparison/
```

Create a new candidate Authoring-Kit work area.

Suggested path:

```text
assets/visual/authoring_kit/v0.1-candidate/
```

This remains candidate/source material until owner visual review.

## 2. Correct the benchmark's repeated style weaknesses

Preserve the challenger's strengths:

- dimensional massing;
- grounded silhouettes;
- richer value hierarchy;
- strong low-resolution readability;
- material depth;
- useful source-level detail.

Correct these weaknesses:

- do not use large glossy/specular-looking pale ellipses as the default foliage highlight;
- do not give every canopy/bush the same cloud-lobe construction;
- avoid neon/over-saturated greens;
- avoid dark curved crevice marks that accidentally read as smiles/faces;
- soften overly industrial rock seam lines;
- integrate moss into rock material rather than placing detached green caps;
- keep light overlays restrained enough not to wash a composed scene;
- interactive hollows must have bark thickness, irregular rim, cavity depth and inner value variation, not a plain black oval.

Target tactile storybook / felt-board / toy-diorama richness, not glossy inflatable plastic.

## 3. Build reusable authoring guidance, not a warehouse

Create concise source-level guidance/recipe files for at least:

```text
materials/foliage.md
materials/wood_bark.md
materials/rock_moss.md
materials/cloud_light.md
recipes/tree_construction.md
recipes/grounded_bush.md
recipes/interactive_hollow.md
recipes/contact_grounding.md
```

These recipes must describe:

- silhouette hierarchy;
- light direction;
- allowed palette/value variation;
- material-specific highlight/shadow logic;
- grounding/contact treatment;
- low-resolution simplification rules;
- how to vary the object without leaving the Greia style.

Do **not** prescribe one fixed outline or one fixed canopy arrangement.

## 4. Variation proof — three trees from one kit

Using the same candidate Authoring Kit, create three clearly distinct tree assets:

### A. Broad old oak

- heavy asymmetrical trunk;
- broad low canopy;
- visible structural bough logic;
- strong grounded root flare;
- warm mature bark.

### B. Slender young woodland tree

- much narrower trunk;
- taller/lighter silhouette;
- smaller, airier canopy masses;
- different branch rhythm from the oak;
- still obviously Greia.

### C. Activity-specific hollow tree study

- asymmetrical old trunk;
- readable interactive hollow;
- bark rim thickness and inner cavity depth;
- canopy arranged to support the gameplay silhouette;
- must not look like Tree A with a black oval pasted onto it.

At first glance, all three must read as **different trees in the same illustrated world**, not rescaled siblings.

## 5. Variation proof — foliage and rocks

Create:

- two bushes with different growth habits/silhouettes using the same foliage guidance;
- two rock formations with different massing using the same rock/moss guidance.

Again: same material language, different final objects.

## 6. Runtime-size readability

Render every proof asset at approximately:

```text
256 px
128 px
64 px
```

The 64 px test is not expected to preserve tiny decoration. It must preserve:

- silhouette;
- main light/dark mass;
- material identity;
- interaction-defining feature for the hollow tree.

Do not add micro-detail merely because it looks attractive at source size.

## 7. Comparative composition proof

Create a 1024×600 neutral forest-meadow composition containing all three tree types, both bushes and at least one rock formation.

The scene must prove:

- the kit creates variety;
- the assets still belong together;
- the same highlight shape is not stamped everywhere;
- objects look grounded;
- composition does not become noisy or over-saturated.

Also create a simple close-up showing the hollow tree as a potential child interaction target.

## 8. Review set

Create:

```text
docs/reviews/visual/2026-08-21_authoring-kit-variation/
```

Required files:

```text
01-three-trees.png
02-bush-rock-variation.png
03-runtime-sizes.png
04-composed-scene.png
05-hollow-closeup.png
06-material-detail.png
REVIEW.md
audit.json
```

`REVIEW.md` must answer honestly:

- do the three trees look genuinely different?
- is Greia coherence still obvious?
- where does the kit still create unwanted sameness?
- do foliage highlights still feel plastic/glossy?
- do rocks/moss feel integrated?
- does the hollow read as a constructed cavity rather than a pasted hole?
- which recipes/primitives are actually useful enough to keep?

## 9. Owner attachment ZIP — mandatory

Create at project root:

```text
./GREIA_VISUAL_REVIEW_AUTHORING_KIT_VARIATION_2026-08-21.zip
```

It must contain the six curated PNGs, `REVIEW.md`, and `audit.json`.

Do not commit the ZIP itself. Commit the curated review files and candidate kit sources.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_AUTHORING_KIT_VARIATION_2026-08-21.zip
```

## 10. Stop/fix conditions

Do not call the gate successful if:

- the three trees use substantially the same canopy silhouette;
- the same large pale highlight blobs appear mechanically across foliage;
- the hollow is just a dark oval pasted into a generic trunk;
- trees/bushes float or lack contact grounding;
- all assets use effectively the same green values;
- the scene becomes neon, washed out, or visually noisy;
- 64 px silhouettes collapse;
- the output is merely a larger asset catalogue rather than evidence of reusable construction knowledge.

Fix source-level authoring rules and regenerate affected assets before returning evidence.

## 11. Return

Commit and push candidate Authoring-Kit sources, recipes, review evidence and metadata to canonical `main`.

Report:

- exact commit SHA;
- candidate Authoring-Kit path;
- review directory;
- concise honest judgement of whether the kit produces **coherence without sameness**;
- exact visual review ZIP path.
