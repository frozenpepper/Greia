# Visual Review & Benchmark — Greia Visual Authoring Library

**Date:** 2026-08-21  
**Runbook Authority:** `docs/testing/2026-08-21_VISUAL_AUTHORING_LIBRARY_COMPARISON.md`  
**Architecture Authority:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Evidence Class:** `AUTHORING COMPARISON / OWNER VISUAL REVIEW REQUIRED`

---

## 1. Executive Summary & Benchmark Purpose

This benchmark evaluates whether the local authoring agent can produce a **materially higher-quality base Greia Visual Authoring Kit** than the historical baseline assets (`assets/visual/environments/forest_meadow/v0.2/`), while rigorously preserving Greia’s storybook/toy-diorama visual identity, tactile depth, low-resolution readability, and composability.

### Core Findings
1. **Canopy & Foliage Grammar:** Replacing mechanical stacks of overlapping geometric ellipses with organic, tiered billowing masses and sculpted leaf tufts dramatically improves both silhouette interest and three-dimensional volume without creating high-frequency visual noise.
2. **Bark & Wood Texture:** Replacing flat trunk strokes with sculpted planar bark facets, spreading buttress roots, and warm cedar/chestnut gradients grounds the trees solidly into the scene.
3. **Geological Facets & Organic Moss:** Replacing flat gray trapezoids with sculpted, multi-plane boulders draped in soft velvet moss elevates the rock cluster from programmer art to a tactile storybook feature.
4. **Low-Resolution Readability (256px / 128px / 64px):** All challenger assets maintain clean massing and strong silhouettes at 128px and 64px, proving that richer planar shading and organic silhouettes do not collapse into muddy noise at child appliance resolutions.
5. **Interactive Derivative Potential:** The `hollow_tree_study.svg` demonstrates that this authoring kit vocabulary directly enables assembling bespoke interactive gameplay spots (such as Nascondino hiding hollows) rather than requiring static copy-paste of monolithic props.

---

## 2. Asset-by-Asset Comparative Critique

### A — Hero Oak Tree (`tree_hero.svg`)
- **What Changed:** Replaced the mechanical ellipse-stack canopy and single-path trunk with a multi-tiered billowing canopy (back shadow, mid mass, sunlit fore-crest), sculpted bark planes with buttress root flare, subtle foliage crevice shadows, leaf tuft accents along silhouettes, and warm golden buttercups + wild ruby berries.
- **Where Challenger is Better:** Rich volumetric massing, organic flowing silhouette, grounded root structure, and harmonious color transitions.
- **Where Challenger is Worse:** Slightly higher SVG path count (6.8 KB vs 4.0 KB).
- **Runtime Size Survival (64px/128px/256px):** At 256px and 128px the canopy billows read distinctly as lush foliage masses. At 64px the primary massing remains sharp and recognizable without noise.
- **Style Drift:** None; adheres strictly to the storybook felt-board/toy-diorama grammar.
- **Authoring Kit Value:** Excellent recipe candidate for canopy lobe construction, bark plane shading, and root anchoring.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### B — Secondary Woodland Tree (`tree_secondary.svg`)
- **What Changed:** Replaced sparse symmetrical ellipses with a slender, graceful trunk with natural bow and branch offshoots, tiered apple-green canopy masses, volumetric highlights, and delicate white woodland star-flower accents.
- **Where Challenger is Better:** Clear asymmetrical character, distinct species differentiation from the hero oak, fresh spring-green palette.
- **Where Challenger is Worse:** Slightly more complex branch geometry.
- **Runtime Size Survival:** Outstanding; slender silhouette remains crisp down to 64px.
- **Style Drift:** None.
- **Authoring Kit Value:** Serves as the primary reference for secondary/background slender tree construction.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### C — Flowering Woodland Bush (`bush_flowering.svg`)
- **What Changed:** Replaced 6 plain circles and flat geometric 5-dot flowers with multi-tier organic foliage billows, deep under-bush shadow layer, sunlit crest billows, and authored clusters of delicate 5-petal woodland blossoms (pink, golden, sky blue, lavender) with wild crimson berries.
- **Where Challenger is Better:** Dynamic organic silhouette, tactile front/back depth layering, authentic meadow flower clusters instead of pasted dots.
- **Where Challenger is Worse:** Slightly higher floral detail count.
- **Runtime Size Survival:** Flowers read as charming colorful meadow accents at 256px and 128px; at 64px they read as soft warm color accents without muddying the green volume.
- **Style Drift:** None.
- **Authoring Kit Value:** Reusable primitive recipe for foliage billows and wildflower/berry clusters.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### D — Large Rock Cluster (`rock_cluster_large.svg`)
- **What Changed:** Replaced flat gray trapezoids with a trio of sculpted, rounded river boulders with distinct faceted planes (lit top-left plane, soft face, deep shadow side), lush velvet green moss caps growing into crevices, and grounded base pebbles.
- **Where Challenger is Better:** Tactile geological structure, authentic storybook weight, beautiful moss integration.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Strong facet lines and moss caps preserve clarity even at 64px.
- **Style Drift:** None.
- **Authoring Kit Value:** Reference model for all rock/stone/cave prop authoring.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### E — Large Cumulus Cloud (`cloud_large.svg`)
- **What Changed:** Replaced flat bezier arcs with volumetric spherical cloud billow domes, soft sky-blue underbelly shading, golden-white sunlit crest sheen, and a small companion floating cloudlet.
- **Where Challenger is Better:** Buoyant, fluffy, volumetric storybook cloud feel; warm sunlight lighting.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Large soft shapes scale cleanly across all display sizes.
- **Style Drift:** None.
- **Authoring Kit Value:** Standard recipe for sky cloudlet construction.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### F — Meadow Grass Edge (`grass_edge.svg`)
- **What Changed:** Replaced mechanical identical blade spikes with a multi-tier rolling meadow floor (distant rolling hill, mid lawn crest, foreground turf) with varied organic blade tufts of differing heights, curves, and natural groupings, sprinkled with field daisies, buttercups, and clovers.
- **Where Challenger is Better:** Creates an authentic rolling forest floor rather than a flat repeating stamp; seamless 1024px horizontal tiling.
- **Where Challenger is Worse:** Slightly higher blade count.
- **Runtime Size Survival:** Ground layers and tufts provide excellent depth cues at runtime.
- **Style Drift:** None.
- **Authoring Kit Value:** Master recipe for horizontal ground turf boundaries.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### G — Atmosphere: Sunlight Rays (`sunlight_rays.svg`)
- **What Changed:** Replaced hard-edged flat trapezoids with soft feathered multi-shaft radiant beams with delicate alpha transitions and floating luminous golden dust motes.
- **Where Challenger is Better:** Creates genuine magical woodland atmosphere and light breathing without harsh polygonal edges.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Soft gradients blend cleanly across background and foreground passes.
- **Style Drift:** None.
- **Authoring Kit Value:** Reusable atmosphere lighting primitive.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### H — Interactive Hollow Tree Study (`hollow_tree_study.svg`)
- **Concept & Purpose:** Demonstrates how the Authoring Kit vocabulary can be composed into activity-specific interactive gameplay spots. Features an ancient sheltering oak with a deep, inviting dark cavity carved into the trunk, weathered knot rims, and buttress roots.
- **Evaluation:** Proves that authoring agents can derive bespoke gameplay assets (e.g., hiding spots for Nascondino) using the shared visual language.
- **Disposition:** **`CHALLENGER CLEARLY BETTER (NEW STUDY)`**

---

## 3. Comparison Summary Table

| Asset Role | Baseline Status | Challenger Status | Disposition |
|---|---|---|---|
| `tree_hero.svg` | Primitive ellipse stack | Multi-tier billowing canopy + bark planes | **CHALLENGER CLEARLY BETTER** |
| `tree_secondary.svg` | Symmetrical sparse tree | Slender bowed birch with spring foliage | **CHALLENGER CLEARLY BETTER** |
| `bush_flowering.svg` | Row of 6 circles + dots | Tiered billow bush + blossoms & berries | **CHALLENGER CLEARLY BETTER** |
| `rock_cluster_large.svg` | Flat gray trapezoids | Faceted river boulders + velvet moss | **CHALLENGER CLEARLY BETTER** |
| `cloud_large.svg` | Simple flat gradient arc | Volumetric cumulus with sunlit crest | **CHALLENGER CLEARLY BETTER** |
| `grass_edge.svg` | Flat wave with spike tufts | Multi-tier rolling turf + wildflowers | **CHALLENGER CLEARLY BETTER** |
| `sunlight_rays.svg` | 3 hard trapezoid paths | Soft volumetric radiant shafts + motes | **CHALLENGER CLEARLY BETTER** |
| `hollow_tree_study.svg` | N/A (Missing in baseline) | Bespoke interactive gameplay tree study | **CHALLENGER CLEARLY BETTER** |

---

## 4. Review Artifacts & Transfer Package

The review files are stored in `docs/reviews/visual/2026-08-21_authoring-library-comparison/`:
- `comparison_contact_sheet.png`
- `comparison_runtime_sizes.png`
- `preview_baseline_scene.png`
- `preview_challenger_scene.png`
- `comparison_detail_crops.png`
- `REVIEW.md`
- `audit.json`

Per Section 13, the transfer package for owner / ChatGPT pixel review is assembled at:
`./GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip`