# Primary Promotion Review — Forest / Meadow v0.3

**Date:** 2026-08-21  
**Reviewed candidate commit:** `714d084`  
**Evidence inspected:** owner attachment ZIP `GREIA_VISUAL_REVIEW_FOREST_MEADOW_PACK_FINALIZATION_2026-08-21.zip`  
**Candidate:** `assets/visual/pack_candidates/forest_meadow/2026-08-21/`

## Disposition

**AUTHORIZE A SELECTIVE/HYBRID FOREST / MEADOW v0.3 PROMOTION.**

The local maintainer agent has already won the original pack-production comparison: the reauthored Forest / Meadow pack is materially stronger than the old v0.2 pack overall. No more Forest / Meadow art-optimization loop is justified.

However, the producing agent's proposed `28 / 28` candidate promotion is too aggressive. Pixel review of the finalization ZIP shows that several revised support assets are still weaker than the existing v0.2 role. Greia should promote the strongest toolbox, not force 100% replacement.

## Promote candidate for 23 semantic roles

Promote the 2026-08-21 candidate for every semantic role **except** the five explicit legacy retentions below.

The candidate is clearly preferable across the main trees, bushes/bramble/ferns/flowers, rocks, log/stump/mushrooms, clouds/hills, sunlight, shadows, fireflies/dust/leaves, and the new interactive hollow-tree role.

## Retain v0.2 for exactly five roles

### `tree.willow.01`
Retain legacy v0.2. The final candidate reads as a rigid umbrella with a small number of heavy vertical fronds rather than a convincing weeping willow. The legacy is simpler, but its hanging canopy reads more naturally for this support role.

### `treeline.distant.01`
Retain legacy v0.2. The revised candidate turns the far layer into a repeated jagged triangular ridge that can read as mountains/teeth rather than a quiet distant tree crown rhythm. The legacy remains the safer atmospheric support layer.

### `ground.grass_edge.01`
Retain legacy v0.2. The candidate is visually a large rectangular green gradient slab with only minimal top-edge variation. The legacy edge has a much clearer meadow-edge silhouette and actual grass/flower articulation.

### `ground.dirt_patch.01`
Retain legacy v0.2. The candidate is essentially a brown ellipse with a few dots and loses the more authored ground-patch treatment of the legacy asset.

### `atmosphere.fog_strip.01`
Retain legacy v0.2. The candidate is a simple uniform blurred horizontal band. The legacy has layered, irregular mist contours and is materially more useful for natural atmosphere.

## Authoring ingredients

Do **not** automatically promote all four candidate ingredients merely because they were produced during the pack pass.

Promote:

- `ingredient.bark` / `ingredient_bark_knot.svg` — genuinely useful source-level wood-detail ingredient;
- `ingredient.flower` / `ingredient_flower_sprig.svg` — simple but useful compositional accent.

Keep experimental/provenance-only:

- `ingredient.foliage` — too close to the repeated rounded/puffy foliage grammar and risks teaching sameness;
- `ingredient.moss` — current shape does not convincingly read as a moss/crevice treatment on its own.

## Final pack result

The promoted v0.3 should therefore be:

```text
23 candidate semantic roles
+ 5 retained v0.2 semantic roles
+ 2 promoted authoring ingredients
+ legacy v0.2 preserved untouched as provenance
```

This is an owner-authorized selection. Do not create another Forest / Meadow correction benchmark to try to turn the five retained roles into candidate wins.

## Next action

1. Materialize `assets/visual/environments/forest_meadow/v0.3/` from the exact selective map above.
2. Update source-pack metadata/indexes so v0.3 is the preferred Forest / Meadow authoring pack while keeping v0.2 available as provenance.
3. Do **not** change existing runtime consumers merely to complete this source-pack promotion.
4. Immediately move the maintainer-side content-production track to the **Workshop** base pack.

The separate model-agnostic Activity-authoring skill remains responsible for teaching arbitrary user agents how to `REUSE`, `COMPOSE/ADAPT`, or `CREATE ORIGINAL`; this maintainer-side pack decision does not imply those agents share the local maintainer agent's art capability.
