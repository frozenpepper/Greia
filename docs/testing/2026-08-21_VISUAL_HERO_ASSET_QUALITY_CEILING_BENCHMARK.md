# Greia Visual Authoring — Hero Asset Quality Ceiling Benchmark

**Date:** 2026-08-21  
**Purpose:** stop generalizing the Authoring Kit temporarily and determine the actual maximum craft quality the local authoring workflow can achieve on **one** source master.

## Why this benchmark exists

The v0.1–v0.3 Authoring Kit iterations improved structure and variation, but the owner review still finds the rendered output too close to enlarged vector-icon art:

- rounded inflated foliage masses remain dominant;
- bark/material detail remains weak;
- cavities and grounding are still too formulaic;
- broad rules are being generalized before the project has proved one genuinely excellent source master.

This benchmark therefore asks only one question:

> **Can the local authoring workflow produce one hero environmental asset at a quality level genuinely worth using as a Greia Authoring Kit reference?**

Do not build another kit version in this task.

Do not touch Nascondino.

Do not create a family of assets.

Spend the available effort on **one excellent hero tree**.

---

## 1. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/reviews/visual/2026-08-21_authoring-library-comparison/PRIMARY_REVIEW.md
docs/reviews/visual/2026-08-21_authoring-kit-variation/PRIMARY_REVIEW.md
docs/reviews/visual/2026-08-21_authoring-kit-v03-corrective/PRIMARY_REVIEW.md
skills/greia-visual-authoring/SKILL.md
```

Inspect the actual v0.3 source and review evidence before starting.

---

## 2. Single target

Create **one new mature hero woodland tree**.

Use a new workspace, for example:

```text
assets/visual/authoring_candidates/2026-08-21_hero-tree-quality-ceiling/
```

Do not overwrite prior candidates.

The result should be suitable as a future **reference master**, not merely a runtime sprite.

---

## 3. Quality target

The owner explicitly wants:

- extremely high quality;
- real detail;
- multiple shades and local color variation;
- strong material treatment;
- rich storybook character;
- excellent silhouette;
- high-quality source craftsmanship;
- graceful simplification at runtime scale.

The target is **not** photorealism.

The target is a polished child-friendly storybook / painted-toy / illustrated-diorama asset with enough source richness that a 512–1024 px master does **not** look like a 64 px icon enlarged.

---

## 4. Source format is not the benchmark

Do **not** optimize for proving that handwritten SVG is clever.

The visual result is the benchmark.

For this benchmark only, the source master may use the highest-quality practical lossless authoring form available in the local environment, including:

- SVG;
- layered or high-resolution transparent PNG source;
- a combination where appropriate.

Do not introduce an online service, hosted dependency, or runtime-heavy format.

Do not change Greia runtime architecture merely to accommodate this experiment.

If SVG is used, do not artificially constrain complexity to a few primitive paths. If another local source representation produces materially better art, preserve it as benchmark evidence and document the workflow.

The future runtime rendition may still be a flattened PNG.

---

## 5. Required visual construction

### 5.1 Silhouette

The tree must have a convincing large-scale silhouette:

- asymmetrical but balanced;
- clear trunk weight;
- believable crown spread;
- distinct large bough direction;
- rooted posture;
- no floating masses.

At first glance it must read as one coherent living tree, not a trunk plus separately placed foliage blobs.

### 5.2 Branch anatomy

Show enough branch structure to make the crown believable.

Requirements:

- primary boughs visibly grow from the trunk;
- branch collars/junctions feel structurally continuous;
- secondary branch direction explains major foliage groups;
- no branch ends pointing into empty air without purpose;
- no foliage island should appear unsupported.

### 5.3 Bark / wood material

At source-master size, the trunk must show meaningful material information.

Include restrained but visible examples of:

- local hue/value variation;
- bark plane changes;
- one or more knots, scars, healed branch marks or irregular growth features;
- root/buttress transitions;
- branch collar structure;
- subtle grain or bark rhythm where useful.

Do not use dense noisy line hatching.

Do not leave the trunk as a mostly flat brown fill with one gradient.

### 5.4 Foliage material

The foliage must not visually reduce to a pile of smooth green balloons.

Requirements:

- coherent crown silhouette first;
- irregular exterior edge rhythm;
- nested internal foliage groups whose shapes follow branch/topology logic;
- varied local green values/hues;
- soft but non-plastic light;
- restrained fine-scale leaf/cluster cues at source size;
- shadow pockets created by overlap and volume, not identical dark backing blobs.

Do not use one repeated highlight patch across every mass.

### 5.5 Grounding

The tree must feel planted in the world.

Grounding may use:

- root flare;
- visible overlap with grass/soil;
- local occlusion;
- cast/contact shadow;
- subtle soil/grass interaction.

Do **not** rely on a generic floating ellipse beneath the tree as the entire grounding solution.

### 5.6 Color / light

Use a coherent light direction, but avoid flat formulaic gradients.

The master should contain enough local variation to feel authored:

- warm/cool shifts;
- local light and shadow color changes;
- subtle variation between canopy regions;
- bark variation responsive to form.

Avoid neon greens and washed-out highlights.

---

## 6. Three information scales

The master must demonstrate:

### Large scale
- silhouette
- posture
- primary crown/trunk relationship

### Mid scale
- branch topology
- major foliage groups
- root structure
- major bark planes

### Fine scale
- restrained bark/leaf/material accents
- local variation
- small characterful growth details

Fine detail must support the larger form rather than become texture noise.

---

## 7. Deliberate anti-icon test

Before finalizing, ask:

> If this were shown at 700–1000 px tall, would it still look intentionally authored at that scale, or would it look like a small game icon enlarged?

If it still looks like an enlarged icon, keep working.

The following are automatic warning signs:

- four or five rounded canopy blobs dominate the image;
- trunk is one smooth brown shape with minimal local information;
- highlights are simple large pale capsules;
- shadow is a generic ellipse unrelated to roots/ground;
- detail crops reveal almost no more information than the full-size thumbnail.

---

## 8. Runtime simplification test

Render the final master at approximately:

```text
512 px
256 px
128 px
64 px
```

The master may lose fine detail at smaller sizes, but must preserve:

- silhouette;
- trunk/crown identity;
- primary light/dark organization;
- grounded posture.

Do not redesign the source around the 64 px case. The source master should remain rich; runtime rendition is allowed to simplify.

If useful, produce a separately optimized small rendition and document that it is derived from the same master rather than forcing one source representation to do everything.

---

## 9. Comparison evidence

Create:

```text
docs/reviews/visual/2026-08-21_hero-tree-quality-ceiling/
```

Required files:

### `01-v03-vs-hero.png`
Side-by-side:
- v0.3 mature oak
- new hero master

Use comparable displayed size.

### `02-hero-master.png`
A clean large presentation of the new hero asset on a neutral background.

### `03-material-detail.png`
Large crops showing:
- trunk/bough junction;
- bark/root material;
- foliage edge and internal foliage construction;
- grounding/contact region.

This sheet is critical. It must prove that source-master detail actually exists.

### `04-runtime-sizes.png`
Show:
- 512 px
- 256 px
- 128 px
- 64 px

### `05-neutral-scene.png`
Place the hero tree into a restrained 1024×600 neutral Greia-style setting to verify that the richness survives composition and does not become noisy.

Do not create a whole new environment pack.

### `06-silhouette-value-test.png`
Show at least:
- black silhouette view;
- grayscale/value view;
- normal-color view.

This verifies that form is not being carried only by saturated color.

### `REVIEW.md`
Answer conservatively:

1. Does the new master still look like an enlarged vector icon?
2. What source details are genuinely visible at 512+ px that did not exist in v0.3?
3. Is the foliage still dominated by smooth blob masses anywhere?
4. Is the trunk materially richer than v0.3?
5. Does grounding depend on a generic ellipse?
6. What is still weak?
7. Is this finally good enough to become a **reference master** for future Authoring Kit rules?

### `audit.json`
Record:
- source representation used;
- source path(s);
- tools/workflow used locally;
- generated review files;
- v0.3 comparison source;
- provenance.

---

## 10. Review-sheet honesty

Do not label the new asset:

- `MASTER`
- `HIGH CRAFT`
- `CLEARLY BETTER`
- `ACCEPTED`

inside the evidence graphics before owner review.

Use neutral labels such as:

```text
v0.3 candidate
hero quality-ceiling candidate
```

The evidence must help the reviewer decide; it must not tell the reviewer what conclusion to reach.

---

## 11. Stop/fix conditions

Do not return the benchmark as successful if:

- the new hero still reads mainly as rounded foliage blobs;
- bark remains visually flat at source size;
- branch anatomy is not credible;
- grounding is still just a generic ellipse;
- detail crops fail to reveal meaningful source richness;
- the new version is merely a larger or more complicated SVG without a clearly better rendered result;
- review prose says the problem is solved when the pixels do not demonstrate it.

Fix the actual art before packaging evidence.

---

## 12. Owner transfer ZIP

Create at project root:

```text
./GREIA_VISUAL_REVIEW_HERO_ASSET_QUALITY_CEILING_2026-08-21.zip
```

Include:

```text
01-v03-vs-hero.png
02-hero-master.png
03-material-detail.png
04-runtime-sizes.png
05-neutral-scene.png
06-silhouette-value-test.png
REVIEW.md
audit.json
```

Do not commit the ZIP itself.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_HERO_ASSET_QUALITY_CEILING_2026-08-21.zip
```

---

## 13. Return

Commit and push:

- candidate source master(s);
- curated visual evidence;
- review and audit.

Report:

- exact commit SHA;
- candidate source path;
- source representation used;
- review directory;
- honest self-assessment;
- exact owner ZIP path.

Do not touch runtime integration, Nascondino, Shell work, R7, or GitHub Actions in this benchmark.
