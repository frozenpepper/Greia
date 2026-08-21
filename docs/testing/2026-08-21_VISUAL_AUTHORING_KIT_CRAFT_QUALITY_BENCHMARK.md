# Greia Visual Authoring Kit — Craft Quality Benchmark

**Date:** 2026-08-21  
**Purpose:** test whether the local authoring agent can preserve the previous challenger's quality advantage while escaping simplified repeated vector formulas.

## Read first

```text
AGENTS.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/reviews/visual/2026-08-21_authoring-library-comparison/PRIMARY_REVIEW.md
docs/reviews/visual/2026-08-21_authoring-kit-variation/PRIMARY_REVIEW.md
skills/greia-visual-authoring/SKILL.md
```

Do **not** resume from the v0.1 candidate's self-review alone. The owner review is authoritative for this corrective gate.

---

# 1. Mission

The previous benchmarks established two facts:

1. the local agent can create environment/source assets materially better than the old Forest/Meadow baseline;
2. when the agent turns its own style into fixed geometry recipes, quality collapses toward repeated rounded icon-like forms.

This gate answers the next question:

> Can the agent create **high-craft source masters** and a reusable **relational authoring grammar** without falling back to circles, lobes, fixed coordinates and stamped formulas?

This is not a runtime-integration task and not an asset-volume task.

**Quality over quantity.**

---

# 2. Preserve provenance

Do not overwrite:

```text
assets/visual/authoring_candidates/2026-08-21_forest_meadow_comparison/
assets/visual/authoring_kit/v0.1-candidate/
docs/reviews/visual/2026-08-21_authoring-library-comparison/
docs/reviews/visual/2026-08-21_authoring-kit-variation/
```

Create a new work area:

```text
assets/visual/authoring_kit/v0.2-candidate/
```

and new evidence under:

```text
docs/reviews/visual/2026-08-21_authoring-kit-craft-quality/
```

---

# 3. Rewrite the authoring guidance before drawing

Create revised v0.2 candidate guidance.

The key rule is:

> **Recipes express visual relationships, material behavior and construction logic — not a coordinate template.**

Do not copy fixed formulas from v0.1 such as:

- fixed `y=455` ground line;
- fixed trunk/root x ranges;
- fixed contact-shadow ellipse dimensions;
- “2–3 large billows” as a generic canopy recipe;
- fixed lobe counts;
- fixed branch counts;
- fixed highlight shapes.

A reusable recipe may use **proportions/ranges conceptually**, but should not prescribe one silhouette.

For example, prefer:

```text
BAD:  make 3 canopy circles at x/y coordinates X/Y/Z
GOOD: establish one dominant canopy mass, secondary counter-masses,
      negative-space openings and visible structural support appropriate
      to the species/growth habit
```

Required revised guidance:

```text
materials/foliage.md
materials/wood_bark.md
materials/rock_moss.md
recipes/tree_construction.md
recipes/interactive_hollow.md
recipes/contact_grounding.md
```

Keep the guidance concise enough that an Activity-authoring model can actually use it.

---

# 4. Source-master quality bar

These are **source masters**, not blown-up runtime icons.

Every hero asset must contain three readable scales of information:

## A. Primary silhouette
Readable immediately at 64–128 px.

## B. Mid-scale structure
Readable clearly at 256–512 px, such as:

- branch topology;
- canopy subgrouping;
- root/buttress structure;
- bark planes;
- irregular hollow rim;
- stone planes and erosion breaks;
- leaf/stem grouping;
- moss following crevices/edges.

## C. Restrained fine detail
Visible at source/review size but allowed to disappear when reduced, such as:

- bark knots/scars/ridges;
- subtle hue shifts;
- small leaf-edge notches;
- local reflected light;
- tiny lichen/moss accents;
- small fractures/erosion marks.

Do not add noise for its own sake.

**A 512 px master that looks like a 64 px icon enlarged is a failure.**

---

# 5. Shape-construction restrictions

## 5.1 Foliage

Do not use circles/ellipses/simple rounded blobs as the dominant visible construction of a hero canopy.

Small geometric helpers are fine internally, but the final silhouette should be authored with irregular paths/contours and overlapping masses that read organically.

Requirements:

- varied edge rhythm;
- asymmetry;
- clear major/minor masses;
- negative-space openings where appropriate;
- branch support visibly connected to foliage structure;
- different growth habits must produce genuinely different topology, not merely different width/height.

## 5.2 Trees

A branch cannot end in open air beneath a floating leaf blob.

Every visually independent canopy group must either:

- visibly connect to a supporting branch/bough; or
- clearly overlap into a continuous supported canopy mass.

Trunk width/taper/bough thickness must visually support the canopy's apparent weight.

## 5.3 Grounding

Grounding is **not** a mandatory straight bottom cut.

Use object-appropriate combinations of:

- root flare;
- soil/grass overlap;
- lower contour compression;
- contact occlusion;
- cast/contact shadow;
- terrain penetration/overlap.

Avoid the repeated visual formula “flat horizontal base + oval shadow.”

## 5.4 Hollow cavities

A natural hollow must be irregular and structurally integrated.

It should show some combination of:

- asymmetrical opening;
- bark fracture / growth deformation;
- non-uniform rim thickness;
- internal bark/wood transition;
- cavity depth gradient;
- lower shelf/inner plane only where physically plausible;
- surrounding trunk grain reacting to the opening.

It must **not** read like an oval door installed in a trunk.

## 5.5 Rocks

Avoid:

- symmetric stacked steps;
- cake-like layers;
- mechanical diagonal seam lines;
- detached green moss caps.

Prefer:

- irregular weathered massing;
- softened plane changes;
- believable erosion / fracture direction;
- moss concentrated along moisture-catching ledges, cracks and upper surfaces;
- asymmetrical profiles.

---

# 6. Required asset set — deliberately small

Create only these five proof assets.

## A. High-craft mature oak

Must be clearly better than both:

- old Forest/Meadow `tree_hero.svg`;
- v0.1 candidate `tree_broad_oak.svg`.

Requirements:

- irregular broad silhouette;
- visibly supported branch structure;
- convincing trunk taper and buttress/root logic;
- bark/material richness;
- multiple foliage value/hue zones without plastic gloss;
- source-scale detail without noise.

## B. High-craft young/slender woodland tree

Must not be a thin trunk with three balls.

Requirements:

- visibly different branching topology;
- airy negative space;
- smaller leaf-cluster groupings;
- visible bough/branch support;
- species/growth-habit identity distinct from the oak;
- enough material richness to work as a source master.

## C. Activity-specific hollow tree

Must be visually distinct from the mature oak **before** the viewer notices the hollow.

Requirements:

- different trunk history/posture;
- irregular integrated cavity;
- natural bark deformation;
- compelling interaction readability;
- still coherent with the same Greia material language.

## D. Upright bramble / woody bush

Must look topologically different from a low plump bush.

Requirements:

- visible cane/stem logic;
- leaf groupings attached to stems;
- vertical rhythm;
- negative-space gaps;
- natural base/ground contact;
- optional berries/flowers only as restrained accents.

## E. Weathered shelf/outcrop rock

Must not look like stacked slabs/cake.

Requirements:

- irregular weathered ledge silhouette;
- believable stone plane changes;
- erosion/fracture logic;
- moss integrated along cracks/ledges;
- no symmetric tier stack.

---

# 7. Color and material richness

Use richer color logic than one gradient per object.

For important materials, aim for several coordinated local values/hues, for example:

- bark: lit warm plane, midtone, cool/deep occlusion, local knot/scar values, subtle reflected ground hue;
- foliage: sun-facing mass, middle mass, deep overlap shade, a small number of local hue shifts;
- stone: warm/cool plane variation, occlusion, weathered edge variation, moss influence.

Do not mechanically force a fixed number of colors. The rule is **material-specific richness**, not palette counting.

Avoid neon saturation and plastic specular gloss.

---

# 8. Mandatory self-inspection before evidence generation

Before generating the final review sheets, render each candidate individually on a neutral background at large review size.

Actually open/view the rendered pixels.

For each asset, answer privately before proceeding:

- does anything float?
- does every canopy mass have structural support?
- is the silhouette obviously different from the other assets?
- does it look authored at source scale rather than enlarged from an icon?
- are material details coherent rather than random?
- are gradients/shadows following form?
- is the ground contact natural?
- does any contour look mechanically circular or symmetric without reason?

If any answer is bad, fix the source **before** building the curated evidence.

Do not rely on SVG path validity as visual acceptance.

---

# 9. Comparison evidence

Create:

```text
docs/reviews/visual/2026-08-21_authoring-kit-craft-quality/
```

Required files:

```text
01-tree-progression.png
02-hollow-progression.png
03-bramble-rock.png
04-source-detail.png
05-runtime-sizes.png
06-composed-scene.png
REVIEW.md
audit.json
```

## 9.1 `01-tree-progression.png`

Show at useful large size:

```text
old baseline hero tree
v0.1 candidate oak
v0.2 high-craft oak
v0.1 slender tree
v0.2 high-craft slender tree
```

Do not shrink the assets so much that detail cannot be judged.

## 9.2 `02-hollow-progression.png`

Show:

```text
v0.1 hollow tree
v0.2 hollow tree
large close-up of v0.2 cavity/trunk integration
```

## 9.3 `03-bramble-rock.png`

Show v0.1 vs v0.2 bramble and shelf/outcrop side by side.

## 9.4 `04-source-detail.png`

Large detail crops of:

- bark/branch junction;
- foliage edge/massing;
- hollow rim/depth;
- rock/moss integration.

## 9.5 `05-runtime-sizes.png`

Show the v0.2 assets at roughly 256/128/64 px.

64 px must preserve silhouette and interaction identity, but it is expected to lose fine source detail.

## 9.6 `06-composed-scene.png`

Create a restrained 1024×600 scene using the v0.2 proof assets.

The scene must demonstrate:

- no floating objects;
- no repeated cloud-ball tree formula;
- believable scale/ground plane;
- coherent lighting;
- distinct object identities;
- enough richness to look like a storybook world rather than a vector-icon demo.

---

# 10. Review-sheet quality

The evidence itself must be professionally reviewable.

Do not ship:

- clipped explanatory text;
- labels extending outside cards;
- tiny thumbnails that hide the details being judged;
- misleading captions;
- self-congratulatory prose that contradicts the pixels.

If a review sheet has clipped text, fix the sheet before returning.

---

# 11. Honest REVIEW.md questions

Answer explicitly:

1. Which v0.2 asset is clearly better than v0.1?
2. Which asset is still weak?
3. Does any tree still rely on circular lobe construction?
4. Is every canopy group structurally connected/supported?
5. Does the hollow look natural rather than installed?
6. Does the bramble actually show a distinct woody growth habit?
7. Does the outcrop look geological rather than stacked?
8. Which v0.2 authoring rules are general enough to keep?
9. Which rules still risk producing sameness?
10. Is the v0.2 kit good enough to use as an Activity-authoring reference, or should it remain experimental?

Do not mark the result successful merely because all requested files exist.

---

# 12. Owner attachment ZIP — mandatory

Create at project root:

```text
./GREIA_VISUAL_REVIEW_AUTHORING_KIT_CRAFT_QUALITY_2026-08-21.zip
```

Include:

- all six PNG review sheets;
- `REVIEW.md`;
- `audit.json`.

Do not commit the ZIP itself.

Final response must include exactly:

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_AUTHORING_KIT_CRAFT_QUALITY_2026-08-21.zip
```

---

# 13. Stop/fix conditions

Do not return this gate as successful if any of these remain visible:

- thin trunk + floating/ball canopy;
- oak/hollow same silhouette with hole added;
- regular oval-door hollow;
- bush growth habits differentiated only by aspect ratio;
- stacked-cake rock outcrop;
- repeated straight-cut grounding formula;
- source masters visually no richer than 64–128 px icons;
- obvious plastic gloss;
- review-sheet clipping;
- claims in `REVIEW.md` contradicted by the PNGs.

Fix and regenerate before returning evidence.

---

# 14. Return

Commit and push:

- `assets/visual/authoring_kit/v0.2-candidate/`;
- curated review evidence;
- truthful review metadata.

Do not promote v0.2 to accepted Authoring Kit status. Owner visual review decides that.

Report:

- exact commit SHA;
- candidate v0.2 path;
- evidence path;
- concise self-assessment;
- exact owner attachment ZIP path.
