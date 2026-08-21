# Forest / Meadow Base Art Pack Reauthoring — Local Maintainer Agent Runbook

**Date:** 2026-08-21  
**Purpose:** reauthor the complete Forest/Meadow base art pack at pack scale, using the owner's local agent as a maintainer-side art-production tool.  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Parent plan:** `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`

## 1. Scope and intent

This task is **not** a benchmark of arbitrary future Activity-authoring agents.

You are being used only as a Greia maintainer-side content-production agent to answer:

> can you produce a stronger complete Forest/Meadow base pack than the existing Greia Forest/Meadow baseline?

Do not generalize your own drawing technique into universal Activity-agent rules.

Do not continue the hero-tree optimization loop.

---

## 2. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
skills/greia-visual-authoring/SKILL.md
assets/visual/environments/forest_meadow/v0.2/README.md
assets/visual/environments/forest_meadow/v0.2/catalog.toml
```

Also inspect the actual current Forest/Meadow source assets and existing review compositions.

---

## 3. Preserve provenance

Do **not** overwrite:

```text
assets/visual/environments/forest_meadow/v0.2/
```

Create the candidate pack under:

```text
assets/visual/pack_candidates/forest_meadow/2026-08-21/
```

Keep filenames/role mapping clear enough that baseline and candidate can be compared directly.

---

## 4. Work at PACK SCALE

The central rule of this run:

> **Improve the complete useful pack, not one specimen.**

Inventory every current v0.2 role from `catalog.toml` and preserve or improve its useful coverage.

The candidate should include the complete useful Forest/Meadow family: background layers, trees, bushes/foliage, rocks/logs, ground edges/details, clouds, atmosphere/light and other current pack roles.

You may remove/rework a baseline asset only in the **candidate** when the role is genuinely redundant or better covered by a stronger alternative. Record that explicitly in the audit.

Do not spend repeated iterations perfecting one tree while the rest of the pack remains old-quality.

One cohesive authoring pass plus **at most one correction pass for clearly defective assets** is the intended process.

---

## 5. Quality target

The candidate should be clearly better than the existing v0.2 baseline in overall pack quality.

Aim for:

- polished storybook / toy-diorama presentation;
- high-quality source masters;
- richer color/value shading than the legacy pack;
- material-specific treatment;
- strong silhouettes;
- clean alpha;
- convincing object grounding;
- coherent light direction;
- useful fine detail at large source size without runtime noise;
- readable reduction to child-facing sizes;
- varied objects that do not all look cloned from one formula.

The owner will judge the pixels, not the prose.

---

## 6. Variety requirement

The pack is a toolbox. Avoid literal sameness.

At minimum, the candidate family must visibly contain useful variation in roles where repeated reuse would otherwise become boring, such as:

- more than one tree silhouette/weight;
- different bush/foliage growth habits;
- different rock/detail massing;
- quiet background-support pieces and stronger hero pieces;
- different ground/edge/details appropriate to compositions.

Do not inflate the pack with dozens of tiny near-duplicates.

---

## 7. Authoring ingredients

Where useful, you may add a **small curated set of source-level authoring ingredients** that can help future Activity authors compose bespoke visuals.

Examples:

- foliage cluster/source pieces;
- branch/trunk elements;
- grass/flower groups;
- rock/moss detail pieces;
- generic light/fog/shadow source elements.

Only add ingredients that have clear reuse value.

These are authoring resources, not a requirement that the target runtime draw every fragment independently.

Record them separately from finished pack masters in the candidate metadata.

---

## 8. Do not overfit to the hero-tree experiment

The historical hero-tree benchmark is provenance only.

You may retain useful lessons such as:

- stronger material depth;
- better grounding;
- meaningful source-scale detail;
- clearer structure;

but do **not** turn that exact oak, its foliage grammar, or its SVG construction technique into the mandatory formula for every tree/bush/object.

The pack must show diversity.

---

## 9. Runtime-size review

Choose representative candidate assets from each major family and render them at useful scale tiers, including small child-facing sizes.

At small sizes, fine detail may disappear, but preserve:

- silhouette;
- main value hierarchy;
- material identity;
- role readability.

Do not redesign the runtime architecture in this task.

---

## 10. Required review directory

Create:

```text
docs/reviews/visual/2026-08-21_forest-meadow-base-pack-reauthoring/
```

Required evidence:

```text
01-pack-overview-baseline.png
02-pack-overview-candidate.png
03-trees-foliage-comparison.png
04-rocks-ground-details-comparison.png
05-background-atmosphere-comparison.png
06-runtime-sizes.png
07-baseline-composition.png
08-candidate-composition.png
09-detail-crops.png
REVIEW.md
audit.json
```

You may add one extra sheet only if a major current pack family cannot be reviewed clearly in the required sheets.

---

## 11. Comparison fairness

Baseline and candidate comparison sheets must:

- use comparable neutral backgrounds;
- use comparable display size;
- identify baseline/candidate without marketing language;
- not label your own result `MASTER`, `SUPERIOR`, `CLEARLY BETTER`, etc.;
- avoid clipped text;
- show enough source detail to permit actual owner review.

The two composition previews should use comparable scene intent so the owner can judge overall coherence and richness rather than different layouts.

---

## 12. REVIEW.md

Write a conservative review answering:

1. Which candidate families are visibly better than baseline?
2. Which candidate families are still weak?
3. Did any repeated visual formula infect too much of the pack?
4. Does the candidate provide useful variation without becoming inconsistent?
5. Which current baseline assets, if any, should remain instead of the candidate replacement?
6. Which candidate source ingredients are actually useful to future Activity authors?
7. Is the whole candidate pack ready for owner promotion review, or are specific files still experimental?

Do not infer owner approval.

---

## 13. audit.json

Record at least:

- baseline directory;
- candidate directory;
- every baseline role;
- candidate file serving that role;
- new roles/ingredients, if any;
- dropped/replaced redundant roles and reason;
- review output paths;
- source dimensions/representation where relevant;
- commit SHA after final push.

---

## 14. Mandatory owner attachment ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_FOREST_MEADOW_BASE_PACK_REAUTHORING_2026-08-21.zip
```

Include the nine curated PNGs, `REVIEW.md`, and `audit.json`.

Do not commit the ZIP itself. Commit the candidate pack and review evidence.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_FOREST_MEADOW_BASE_PACK_REAUTHORING_2026-08-21.zip
```

---

## 15. Non-goals

Do not:

- modify Nascondino;
- modify the scene compositor;
- modify Shell UI;
- create a new generic Authoring Kit version;
- continue hero-oak refinement;
- claim your behavior represents other user agents;
- promote/overwrite the live Forest/Meadow pack before owner review;
- run GitHub-hosted Actions.

---

## 16. Return

Commit and push:

- candidate pack sources;
- candidate metadata;
- curated review evidence;
- review/audit.

Return:

- exact commit SHA;
- candidate pack path;
- review path;
- concise conservative self-assessment;
- exact owner ZIP path.
