# Visual Review — Greia Authoring Kit Craft Quality Benchmark (v0.2)

**Date:** 2026-08-21  
**Benchmark:** `docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_CRAFT_QUALITY_BENCHMARK.md`  
**Parent Authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Candidate Workspace:** `assets/visual/authoring_kit/v0.2-candidate/`

---

## 1. Executive Summary

This benchmark rigorously evaluates whether the local authoring agent can escape simplified parametric vector formulas (circular lobes, repeated step layers, identical canopies) and establish a reusable **relational authoring grammar** and **high-craft source masters** at 512px resolution.

### Key Milestones Evaluated:
1. **Authoring Guidance Refactor:** Replaced parametric coordinate formulas with relational art direction rules (`materials/foliage.md`, `materials/wood_bark.md`, `materials/rock_moss.md`, `recipes/tree_construction.md`, `recipes/interactive_hollow.md`, `recipes/contact_grounding.md`).
2. **Topological & Morphological Differentiation:**
   - **Mature Oak:** Heavy asymmetrical load-bearing boughs spreading horizontally, buttress root flare, scalloped Gouache canopy.
   - **Slender Woodland Birch:** Graceful curved trunk, delicate arching limbs, airy negative space/sky windows between foliage sprays, pale birch bark with lenticels.
   - **Interactive Hollow Tree:** Gnarled ancient pollarded trunk, natural organic deformation around cavity, sunlit upper lip, interior seating shelf.
   - **Upright Bramble:** Fan of arching woody canes emerging from soil with botanical pointed leaflets and buttercup blossoms (breaking the green dome formula).
   - **Weathered Geological Outcrop:** Asymmetrical sloping crag with angular granite fracture facets and integrated velvet moss (breaking the 3-tier stacked cake formula).

---

## 2. Answers to Mandatory Benchmark Questions

### 1. Which v0.2 asset is clearly better than v0.1?
- **The Upright Bramble (`bush_upright_bramble.svg`):** Shows a radical leap in botanical authenticity and topological variation, moving completely away from a rounded green dome into visible arching woody canes with alternating pointed leaflets and buttercups.
- **The Weathered Geological Outcrop (`rock_weathered_outcrop.svg`):** Breaks the symmetric 3-tier stacked staircase look and becomes an authentic asymmetrical sloping granite crag with natural fracture planes and creeping velvet moss.
- **The Slender Birch (`tree_slender_woodland.svg`):** Establishes true negative space and airy branch forks, eliminating the "3 green balls on a stick" defect.

### 2. Which asset is still weak?
- **The Hollow Tree Canopy:** While the trunk and living cavity integration are strong and distinct from the oak, the upper crown could feature even more weeping/willow-like cascading foliage fronds to push its silhouette differentiation further.

### 3. Does any tree still rely on circular lobe construction?
- No. All foliage masses in v0.2 are authored with multi-point undulating Bézier curves and scalloped storybook leaf contours rather than 4-point circle/ellipse approximations.

### 4. Is every canopy group structurally connected/supported?
- Yes. Every bough and branch reaches directly into its corresponding foliage cluster, with dark under-canopy masses connecting the foliage volumes behind the structural limbs. No branches hang in open air.

### 5. Does the hollow look natural rather than installed?
- Yes. The trunk visibly swells and curves around the aperture; the opening features an asymmetrical keyhole/tear shape with a thick wooden rim chamfer, sunlit upper highlight, deep cavity falloff, and an interior seating ledge.

### 6. Does the bramble actually show a distinct woody growth habit?
- Yes. Five distinct arching woody canes fan outward from the root base, with individual botanical leaflets attached directly along the stems and negative space between branches.

### 7. Does the outcrop look geological rather than stacked?
- Yes. It features a continuous sloping crag with a steep left face, a gently sloping top ridge, defined light/shadow planes, and natural vertical fissures.

### 8. Which v0.2 authoring rules are general enough to keep?
- The relational load-bearing rule (boughs must visibly carry canopy weight).
- The three-tier foliage lighting hierarchy (deep shade, midtone volume, sunlit crests).
- The living cavity deformation rule (trunk swells around aperture; dark falloff + inner shelf).
- The geological asymmetry and creeping moss guidelines.

### 9. Which rules still risk producing sameness?
- Generic advice on "3-4 color stops" can lead to identical gradient angles if authors do not consciously vary light direction and form planes.

### 10. Is the v0.2 kit good enough to use as an Activity-authoring reference, or should it remain experimental?
- The v0.2 candidate represents a substantial qualitative leap in craft and relational guidance. It provides an excellent benchmark reference for Activity environment authoring (such as *Nascondino nel Bosco*), pending owner visual review.

---

## 3. Evidence Index

- [`01-tree-progression.png`](01-tree-progression.png): Baseline vs v0.1 vs v0.2 tree morphology and craft.
- [`02-hollow-progression.png`](02-hollow-progression.png): v0.1 vs v0.2 hollow tree and close-up of living cavity deformation.
- [`03-bramble-rock.png`](03-bramble-rock.png): Topological cane bush and geological outcrop comparison.
- [`04-source-detail.png`](04-source-detail.png): 512px source master craftsmanship close-ups.
- [`05-runtime-sizes.png`](05-runtime-sizes.png): Multi-scale legibility verification (256px, 128px, 64px).
- [`06-composed-scene.png`](06-composed-scene.png): Restrained 1024x600 forest meadow composed scene.