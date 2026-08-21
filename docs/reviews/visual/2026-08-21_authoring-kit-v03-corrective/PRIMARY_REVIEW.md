# Primary Owner Review — Authoring Kit v0.3 Corrective Benchmark

**Date:** 2026-08-21  
**Reviewed evidence:** owner-attached ZIP, actual PNG pixels  
**Candidate commit:** `373a0736b369b23b8e1cfe4f1fd22989b606b833`  
**Disposition:** **NOT ACCEPTED AS AUTHORING-KIT STANDARD**

## Executive judgement

v0.3 is another real improvement over v0.2, but the evidence does **not** support the candidate's claim that the remaining balloon/vector-icon problem has been solved.

The important distinction is now clear:

- changing an SVG from circles/ellipses to more complicated Bézier paths does not automatically change its **visual read**;
- the v0.3 foliage still reads primarily as rounded green lobes with smooth internal highlight masses;
- the source-detail sheet still looks like enlarged icon art rather than high-craft source masters.

The benchmark therefore remains useful, but the Authoring Kit is still experimental.

## Pixel-level findings

### Mature oak

The v0.3 oak has better branch support and a less mechanical silhouette than v0.2. However, the canopy still reads as a collection of rounded inflated masses. The claim in `REVIEW.md` that the oak is no longer balloon-like anywhere is not supported by the pixels.

The source-detail crop also exposes the deeper issue: bark remains mostly a broad flat brown mass with little convincing material structure. There is no meaningful knot/scar/branch-collar/root-surface information at the advertised source-master scale.

**Disposition:** improved, but not high-craft reference quality.

### Interactive hollow tree

The squat posture and hanging side masses make it more distinguishable from the oak than v0.2. This is a genuine improvement.

However:

- the canopy still uses the same rounded-lobe material grammar as the oak;
- the hollow remains close to a regular dark aperture with a comparatively even concentric rim;
- the tree does not yet look as though decades of growth, damage and healing created the cavity.

The owner requirement was not merely a darker or more asymmetrical portal. It was a **living deformation of the trunk**.

**Disposition:** improved silhouette differentiation, cavity still too designed/installed.

### Upright bramble

The v0.3 bramble is better than v0.2 and its larger grouped leaves survive downsampling more successfully.

At 64 px, though, it remains a very light, line-dominated object. It is visible, but `Solid & Clear` overstates the result. It does not yet have the strong clustered massing expected of a dependable child-facing prop at that scale.

**Disposition:** promising topology; small-scale robustness still marginal.

### Woodland berry bush

This is the strongest counterexample to the candidate's own claim of a `Non-Balloon Organic Storybook Grammar`.

The bush is visibly constructed from multiple smooth rounded green billows over a dark rounded under-mass. The paths may technically be multi-point Béziers, but the resulting image still reads as a pile of blobs.

This demonstrates why authoring rules must be judged on the rendered image, not the primitive type used in the SVG source.

**Disposition:** does not prove the claimed corrected foliage grammar.

### Composed scene

The scene is coherent and readable, but it still reads as **large vector icons assembled onto a simple background**. It does not yet reach the requested high-quality storybook/source-library level of material richness, local color variation, surface detail and authored character.

The oak, hollow tree and bush all share too much of the same smooth rounded foliage language. Generic soft ellipse contact shadows also remain visually repetitive.

## Root-cause conclusion

The project is now spending too much time refining a generalized Authoring Kit before proving that the authoring workflow can produce **one truly excellent hero source asset**.

The local agent has already demonstrated that it can outperform the old Forest/Meadow baseline. What remains unproven is its **quality ceiling**.

Therefore the next benchmark must stop generalizing recipes and stop producing families. It should devote the full effort to one hero asset and answer one question:

> Can the local authoring workflow create a source master that no longer looks like an enlarged vector icon?

Only after that is proven should the project distill the successful construction knowledge back into the Authoring Kit.

## Acceptance boundary

Do not use v0.3 as an accepted Greia Authoring-Kit standard and do not migrate Nascondino gameplay art from it as though the visual problem were solved.

Historical v0.1/v0.2/v0.3 work remains valuable benchmark provenance.

Next gate:

`docs/testing/2026-08-21_VISUAL_HERO_ASSET_QUALITY_CEILING_BENCHMARK.md`
