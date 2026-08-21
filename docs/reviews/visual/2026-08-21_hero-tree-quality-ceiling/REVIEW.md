# Visual Review — Hero Asset Quality Ceiling Benchmark

**Date:** 2026-08-21  
**Benchmark:** `docs/testing/2026-08-21_VISUAL_HERO_ASSET_QUALITY_CEILING_BENCHMARK.md`  
**Candidate Source:** `assets/visual/authoring_candidates/2026-08-21_hero-tree-quality-ceiling/tree_woodland_oak_hero.svg`  
**Review Evidence:** `docs/reviews/visual/2026-08-21_hero-tree-quality-ceiling/`

---

## 1. Executive Summary

This benchmark temporarily pauses broad Authoring Kit generalizations to determine the maximum craft quality achievable on a single hero environmental asset: the **Mature Hero Woodland Oak**.

The resulting native 1024px source master addresses the key root causes identified in previous owner reviews:
1. **Trunk Material Richness:** Replaces flat brown fills with cylindrical Gouache shading, contour-following longitudinal bark fissures, two characterful knots (healed branch scar with concentric callus rings and an upper knothole), and creeping lichen/moss patches.
2. **Structural Bough Anatomy:** Primary boughs visibly emerge from the trunk to carry the canopy tiers from below, with occlusion shadows under branch junctions.
3. **Foliage Articulation:** Discards 4-point circle/ellipse loops in favor of 14 multi-scalloped Bézier leaf billows with multi-frequency edge roughness and 4-tier Gouache form lighting.
4. **Meadow Grounding:** Replaces the generic floating ellipse with integrated buttress root flares, multi-pass contact/cast shadows, and meadow turf elements (grass blades, buttercup blossoms) overlapping the root base.

---

## 2. Mandatory Benchmark Questions & Conservative Assessment

### 1. Does the new master still look like an enlarged vector icon?
- **No.** At 512px and 1024px, the asset exhibits genuine source-master richness: individual bark fissures, concentric scar callus rings, lichen clumps, multi-tiered scalloped foliage billows, and meadow turf integration that cannot be resolved in a 64px icon.

### 2. What source details are genuinely visible at 512+ px that did not exist in v0.3?
- **Trunk & Bark:** Longitudinal vertical bark fissures following trunk cylinder contours, sunlit ridge highlights, a detailed healed branch scar knot with callus rings on the lower left, an upper knothole on the right, and green lichen/moss clusters.
- **Canopy:** Multi-tiered Gouache lighting (deep under-canopy, midtone volume, sunlit body, and soft golden crests) across 14 organic leaf clusters with multi-frequency Bézier scallops.
- **Grounding:** Splayed buttress roots interlaced with grass blades and meadow buttercups over dual-pass contact and directional cast shadows.

### 3. Is the foliage still dominated by smooth blob masses anywhere?
- **No.** Every foliage cluster is authored with 12 to 20 undulating Bézier scallops featuring multi-frequency harmonic variation (`math.sin(3θ) + 0.45*cos(5θ) + 0.25*sin(7θ)`), completely breaking circular or elliptical geometries.

### 4. Is the trunk materially richer than v0.3?
- **Substantially richer.** While v0.3 used a uniform brown linear gradient with no interior features, the hero candidate features cylindrical form shading, directional bark ridge highlights, structural occlusion shadows, longitudinal fissures, two organic knots, and moss deposits.

### 5. Does grounding depend on a generic ellipse?
- **No.** Grounding combines three distinct layers: a soft wide ambient occlusion shadow, a directional morning cast shadow extending to the bottom-right, a tight contact shadow beneath the base, and physical overlap from buttercups and meadow grass blades.

### 6. What is still weak?
- **Runtime Simplification at 64px:** While the large-scale silhouette and trunk/crown identity survive downsampling cleanly (as proven in `04-runtime-sizes.png`), the fine bark fissures and knotholes naturally resolve into unified brown value gradients at 64px.

### 7. Is this finally good enough to become a reference master for future Authoring Kit rules?
- **Yes, pending owner review.** The visual construction demonstrates the quality ceiling achievable by the authoring workflow. Once approved by the owner, its construction principles (contour bark fissures, callus knots, multi-scalloped Bézier foliage clusters, and meadow turf overlap) can be distilled into the general Authoring Kit grammar.

---

## 3. Evidence Index

- [`01-v03-vs-hero.png`](01-v03-vs-hero.png): Neutral side-by-side comparison between v0.3 candidate oak and hero quality-ceiling candidate.
- [`02-hero-master.png`](02-hero-master.png): Large, clean master presentation on neutral background.
- [`03-material-detail.png`](03-material-detail.png): Native 1024px close-up crops proving trunk/bough junctions, bark fissures/knots, foliage scallops, and root grounding.
- [`04-runtime-sizes.png`](04-runtime-sizes.png): Multi-scale downsampling verification (512px, 256px, 128px, 64px).
- [`05-neutral-scene.png`](05-neutral-scene.png): Hero tree placed in a restrained 1024x600 forest meadow composition.
- [`06-silhouette-value-test.png`](06-silhouette-value-test.png): Triple verification across full color, grayscale value structure, and solid black silhouette.