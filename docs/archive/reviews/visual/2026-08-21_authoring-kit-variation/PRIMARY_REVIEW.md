# Primary Owner Review — Greia Visual Authoring Kit v0.1 Candidate

**Date:** 2026-08-21  
**Reviewed evidence:** owner-transfer ZIP produced by `docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_VARIATION_BENCHMARK.md`  
**Reviewed source head:** `4307a463fbf294130c97f071699eff6899757a2a`  
**Disposition:** **REJECTED AS AUTHORING-KIT QUALITY / KEEP AS BENCHMARK PROVENANCE**

## 1. What improved

The correction pass fixed one real structural defect in the first variation output: the slender tree no longer has obviously detached branches ending beneath floating foliage. Ground contact is also more deliberate than the old Forest/Meadow baseline, and the runtime-size sheet confirms that the principal silhouettes remain legible at 256/128/64 px.

Those are useful improvements, but they do **not** make this candidate Authoring Kit ready for promotion.

## 2. Main failure: the kit is still generating enlarged icon art

The source masters are too simple for the intended Greia source-art quality bar. They read like 64–128 px icon designs enlarged to 512 px rather than rich source masters designed at high quality and then simplified by downsampling.

The desired hierarchy is:

```text
large-scale silhouette
+ mid-scale structural form
+ restrained material/detail layer
→ remains readable when reduced
```

The current candidate largely stops after the first level plus a broad gradient.

Missing or weak examples include:

- convincing branch topology and branch thickness transitions;
- irregular canopy-edge language;
- bark planes, knots, scars, ridges and local hue/value variation;
- leaf-cluster structure beyond a few rounded masses;
- believable moss/stone integration;
- weathering and geological irregularity;
- source-scale detail that enriches 256–512 px presentation without becoming noise at 64 px.

**Low-resolution readability is a constraint on simplification, not permission to make the source master simplistic.**

## 3. Tree variation is insufficient

### Broad old oak

The oak is readable and grounded, but its canopy is still dominated by a small number of smooth circular/billowing blobs. The trunk is a clean tapered vector mass with too little bark/material character for a hero source asset.

### Slender young tree

The corrected version is structurally better than the first pass because the boughs now reach the canopy. However, visually it is still essentially a thin trunk supporting three rounded green balls. It does not convincingly read as an airy young woodland tree with a distinct branching/canopy morphology.

### Interactive hollow tree

This is still too close to the broad oak. In the three-tree sheet, Tree A and Tree C share nearly the same canopy grammar and overall massing. The hollow tree therefore still reads substantially as **the oak formula plus a hole**.

That directly fails the benchmark's intended distinction.

## 4. The hollow is still too constructed/door-like

The cavity now has multiple dark values and a rim, which is better than a plain black oval. But the opening remains too regular and architectural:

- near-perfect oval silhouette;
- comparatively uniform rim thickness;
- little bark fracture / growth deformation around the opening;
- insufficient relationship between the cavity and the trunk's grain/taper/knots.

A good activity-specific hollow should look like a natural break/growth cavity that the tree has formed around, while remaining highly readable as an interaction target.

## 5. Bush variation does not match the written claim

The `Plump Berry Bush` and `Tall Leafy Bramble` are still very similar rounded-lobe constructions.

The review claims the bramble has “visible woody stems,” but the comparison image does not communicate a materially different upright woody growth habit. It looks like another rounded bush with a taller central blob.

A real variation proof needs differences in topology, not just aspect ratio and decoration.

Examples:

- low dense berry shrub: low lateral branching, clustered leaves, weighted fruit-bearing tips;
- upright bramble: visible cane/stem logic, alternating leaf groups, gaps/negative space, vertical rhythm.

## 6. Rock variation is also too formulaic

The rounded boulder cluster is an improvement over the old baseline, but the dark diagonal facet/seam lines still feel mechanically drawn.

The `Layered Shelf Outcrop` reads visually like a stacked cake / three symmetric steps rather than naturally weathered geological strata. Real variation should come from different geological massing and erosion, not geometric stacking.

Moss is also still mostly a green cap treatment rather than fully integrated edge growth following moisture/crevice logic.

## 7. Grounding rule became too literal

Fixing floating objects was necessary, but the candidate guidance overcorrected into a repeated “flat horizontal base + ellipse shadow” formula.

Grounding should be an outcome of:

- root flare / weight-bearing geometry;
- occlusion at the soil contact;
- overlap with grass/ground material;
- believable cast/contact shadow;
- object-specific weight and posture.

It should **not** require every organic object to terminate in an obvious straight cut line.

## 8. The candidate recipes are too parametric

The v0.1 recipe files contain exact coordinates/ranges and repeated construction formulas such as fixed lobe counts, fixed root widths, fixed ground lines and “2–3 large billows.” That is precisely the kind of recipe that teaches an authoring agent to stamp one geometry repeatedly.

A Greia Authoring Kit recipe should primarily encode **relationships and constraints**, for example:

- trunk width should visually support canopy weight;
- boughs must actually connect/support visible foliage masses;
- canopy segmentation should follow species/growth habit;
- root flare/contact should match apparent mass and terrain;
- material shading should respond to form and light;
- interaction features must deform surrounding structure rather than being pasted on.

Exact pixel coordinates belong in a particular asset, not in a reusable visual grammar.

## 9. Evidence quality issue

`05-hollow-closeup.png` itself contains clipped explanatory text on the right side of the callout panel. This does not invalidate the asset pixels, but it is another reminder that visual review artifacts must themselves be inspected before being presented as polished evidence.

## 10. What the benchmark actually proves

The previous one-off challenger benchmark showed that the local agent can improve meaningfully on the old Forest/Meadow baseline.

This variation benchmark shows a second, equally important fact:

> **the agent can produce stronger one-off assets, but when its own construction rules become too explicit/formulaic, it collapses back into repeated simplified vector grammar.**

Therefore:

- the local agent remains the preferred challenger for environment/source-asset creation;
- the v0.1 Authoring Kit is **not** accepted or promoted;
- the next benchmark must optimize for **craft quality + morphological/topological variation**, not asset count;
- reusable recipes must be relational art-direction guidance, not parametric shape templates.

## 11. Required next gate

Proceed with:

```text
docs/testing/2026-08-21_VISUAL_AUTHORING_KIT_CRAFT_QUALITY_BENCHMARK.md
```

That gate deliberately reduces output quantity and raises the source-master craftsmanship bar before any Activity migration resumes.
