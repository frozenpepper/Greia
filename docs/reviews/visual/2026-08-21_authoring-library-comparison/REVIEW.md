# Visual Review & Benchmark — Greia Visual Authoring Library (Revised Grounding)

**Date:** 2026-08-21  
**Runbook Authority:** `docs/testing/2026-08-21_VISUAL_AUTHORING_LIBRARY_COMPARISON.md`  
**Architecture Authority:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Evidence Class:** `AUTHORING COMPARISON / OWNER VISUAL REVIEW REQUIRED`

---

## 1. Executive Summary & Core Improvements

This revised iteration specifically addresses critical feedback on **grounding, base geometry, and tree authoring discipline**:

1. **Firm Object Grounding & Outward-Flared Bases:**
   - Inward-curving bottom contours and floating stems have been completely eliminated.
   - Trunks now feature **wide, outward-flaring root anchors** resting flat against the ground plane ($y=455$) and directly overlapping the tight contact shadow ellipse, ensuring objects look solidly rooted in the soil rather than floating in mid-air.
   - Boulders and bushes now have **flat horizontal contact bases** ($y=226$) seated squarely into the earth.

2. **Tree Authoring Discipline (No Details for the Sake of Details):**
   - Gratuitous decorative clutter (random berries/flowers on oak canopies, excessive micro-lines) has been stripped away.
   - Canopies are structured around **pure, bold storybook mass hierarchy**: 4–6 harmonious, cloud-like billowing lobes with clear sunlit crests and deep underside form shadows.
   - Sturdy, warm wooden trunks support the canopy through natural structural boughs without busy scribbles.

3. **Consistent Low-Resolution Readability (256px / 128px / 64px):**
   - The simplified, confident mass hierarchy reads with immediate clarity from full resolution down to 64px.

---

## 2. Asset-by-Asset Comparative Critique

### A — Hero Oak Tree (`tree_hero.svg`)
- **What Changed:** Grounded trunk with wide outward root flare spreading across $x=165..415$ at $y=455$, seated directly on the ground contact shadow. Canopy constructed from 5 large, lush cloud-like foliage billows with broad top-left sunlight planes and underside depth shading. Removed noisy micro-details (berries/flowers).
- **Where Challenger is Better:** Firmly planted in the earth (no floating illusion); iconic, readable storybook silhouette; rich but restrained color harmony.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival (64px/128px/256px):** Bold massing reads instantly at all child screen sizes.
- **Style Drift:** None; adheres strictly to Greia storybook/toy-diorama visual language.
- **Authoring Kit Value:** Master reference for grounded root flare and harmonious canopy billow hierarchy.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### B — Secondary Woodland Tree (`tree_secondary.svg`)
- **What Changed:** Outward-flaring root base spreading across $x=195..355$ at $y=455$. Slender graceful trunk with natural bow and branch offshoots supporting 3 airy spring-green foliage billows.
- **Where Challenger is Better:** Solidly anchored to the ground; clear species contrast from the hero oak; clean, uncluttered form.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Crisp silhouette down to 64px.
- **Style Drift:** None.
- **Authoring Kit Value:** Primary reference for secondary slender tree construction.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### C — Flowering Woodland Bush (`bush_flowering.svg`)
- **What Changed:** Flat horizontal base line at $y=226$ seated directly in the contact shadow. 3 plush, rounded foliage lobes with warm sunlight crests and clean, charming 3-petal flower accents.
- **Where Challenger is Better:** Firmly planted in the ground turf; clear volume separation; restrained floral charm.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Clean shapes and color accents remain distinct at 64px.
- **Style Drift:** None.
- **Authoring Kit Value:** Standard recipe for ground foliage clumps and subtle flower accents.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### D — Large Rock Cluster (`rock_cluster_large.svg`)
- **What Changed:** Flat bottom base line at $y=226$ resting firmly on the ground plane. Trio of sculpted river boulders with clear planar facet shading and velvet green moss caps.
- **Where Challenger is Better:** Heavy, solid geological presence anchored into the meadow.
- **Where Challenger is Worse:** None.
- **Runtime Size Survival:** Strong facet edges preserve form down to 64px.
- **Style Drift:** None.
- **Authoring Kit Value:** Master reference for grounded rock and stone props.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### E — Large Cumulus Cloud (`cloud_large.svg`)
- **What Changed:** Volumetric spherical billow domes, sky-blue underbelly shading, golden-white sunlit crest sheen.
- **Where Challenger is Better:** Buoyant, volumetric storybook cloud feel.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### F — Meadow Grass Edge (`grass_edge.svg`)
- **What Changed:** Multi-tier rolling meadow turf with varied organic blade tufts and subtle wildflowers.
- **Where Challenger is Better:** Organic ground contour with seamless 1024px horizontal tiling.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### G — Atmosphere: Sunlight Rays (`sunlight_rays.svg`)
- **What Changed:** Soft feathered volumetric radiant shafts with delicate falloff and floating dust motes.
- **Where Challenger is Better:** Authentic atmospheric lighting without hard polygonal boundaries.
- **Disposition:** **`CHALLENGER CLEARLY BETTER`**

---

### H — Interactive Hollow Tree Study (`hollow_tree_study.svg`)
- **What Changed:** Ancient sheltering oak with wide outward root base firmly anchored in the ground ($y=455$), welcoming dark hollow cavity in the trunk, and clean broadleaf canopy.
- **Where Challenger is Better:** Proves that the Authoring Kit vocabulary enables deriving bespoke interactive gameplay props (e.g. hiding hollows) with solid grounding.
- **Disposition:** **`CHALLENGER CLEARLY BETTER (NEW STUDY)`**

---

## 3. Comparison Summary Table

| Asset Role | Baseline Status | Challenger Status | Disposition |
|---|---|---|---|
| `tree_hero.svg` | Primitive ellipse stack | Grounded outward root base + clean canopy billows | **CHALLENGER CLEARLY BETTER** |
| `tree_secondary.svg` | Symmetrical sparse tree | Grounded base + slender bowed birch with spring foliage | **CHALLENGER CLEARLY BETTER** |
| `bush_flowering.svg` | Row of 6 circles + dots | Flat grounded base + plush billows & flower accents | **CHALLENGER CLEARLY BETTER** |
| `rock_cluster_large.svg` | Flat gray trapezoids | Flat grounded boulders + planar facets & velvet moss | **CHALLENGER CLEARLY BETTER** |
| `cloud_large.svg` | Simple flat gradient arc | Volumetric cumulus with sunlit crest | **CHALLENGER CLEARLY BETTER** |
| `grass_edge.svg` | Flat wave with spike tufts | Multi-tier rolling turf + wildflowers | **CHALLENGER CLEARLY BETTER** |
| `sunlight_rays.svg` | 3 hard trapezoid paths | Soft volumetric radiant shafts + motes | **CHALLENGER CLEARLY BETTER** |
| `hollow_tree_study.svg` | N/A (Missing in baseline) | Grounded ancient oak with interactive hollow cavity | **CHALLENGER CLEARLY BETTER** |

---

## 4. Review Artifacts & Transfer Package

Review files in `docs/reviews/visual/2026-08-21_authoring-library-comparison/`:
- `comparison_contact_sheet.png`
- `comparison_runtime_sizes.png`
- `preview_baseline_scene.png`
- `preview_challenger_scene.png`
- `comparison_detail_crops.png`
- `REVIEW.md`
- `audit.json`

Mandatory transfer package for owner / ChatGPT pixel inspection:
`./GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip`