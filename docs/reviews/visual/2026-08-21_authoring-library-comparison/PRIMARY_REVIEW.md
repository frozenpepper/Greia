# Primary Review — Visual Authoring Library Benchmark

**Date:** 2026-08-21  
**Reviewed benchmark head:** `9b1a9dbd15ddda1775433e2536eb68a24961fa12`  
**Review basis:** owner-supplied `GREIA_VISUAL_REVIEW_AUTHORING_LIBRARY_COMPARISON_2026-08-21.zip`, inspected directly as rendered PNG evidence.  
**Scope:** source-art authoring capability only; this is not runtime/hardware acceptance.

## Verdict

The **local authoring agent wins this benchmark clearly** for environment/nature source-art creation.

The challenger set is materially stronger than the current Forest/Meadow baseline in:

- dimensional form;
- grounding;
- material separation;
- silhouette confidence;
- shading and value hierarchy;
- readability at 256/128/64 px;
- ability to derive a new Activity-specific prop from the same visual vocabulary.

This result answers the benchmark question: for the next phase of Greia's **Visual Authoring Kit**, the local authoring agent should be treated as the preferred source-asset author for environment/nature primitives and reference assets, subject to visual review and style discipline.

The existing baseline remains useful as architectural/style history and as a simpler fallback reference. The benchmark does **not** justify bulk replacement without review.

## Asset-by-asset visual assessment

### Hero tree

**Challenger wins.** The trunk, canopy massing and grounded base read much more convincingly than the baseline. The result survives downscaling well.

Remaining issue: the bright canopy highlights are oversized and glossy enough to push the object toward an inflatable/plastic cartoon look. Future authoring should retain the form depth while reducing specular-looking highlight blobs.

### Secondary tree

**Challenger wins, but variation is not yet sufficient.** It has better shape and grounding than the baseline, but the canopy language is still too close to the hero tree. The Authoring Kit must teach *construction grammar*, not encourage cloning the same lobe arrangement at different sizes.

### Flowering bush

**Challenger wins.** Better volume, better ground contact and stronger silhouette.

Remaining issue: the dark crevice strokes can read like facial/smiling marks, and the large pale highlight patches again create a glossy/plastic feel. Use more botanical/asymmetric shadow breaks and subtler highlight planes.

### Rock cluster

**Challenger wins on depth and readability.** The faceting is much stronger than the flat baseline.

Remaining issue: the dark seams/facets are slightly severe and industrial, while the moss reads as a separate green cap. Future versions should integrate moss more naturally and soften a few internal lines while preserving the strong massing.

### Cloud

**Challenger wins.** Better volume and better small-scale readability.

Remaining issue: the center crest is close to overexposed white and uses the same glossy highlight logic seen in foliage. Keep the volumetric billows but make the light treatment softer and less synthetic.

### Grass edge

**Challenger wins clearly.** This is one of the strongest results. The richer ground gradient, varied blades and small accents improve the scene without becoming unreadable at runtime scale.

### Sunlight rays

**Challenger is directionally better**, with softer/more numerous shafts, but this asset must remain restrained in full scenes. In the challenger scene the cumulative lighting overlay is already strong enough to wash parts of the scene. Authoring recipes should explicitly cap opacity and density.

### Hollow-tree study

**Useful proof of the architecture, not yet a finished high-end prop.** It demonstrates that the agent can derive a bespoke interactive prop from the tree vocabulary, which is exactly the desired Authoring-Kit workflow.

However, the hollow currently reads too much like a black oval cut into the trunk. A production-quality interactive hollow should have bark rim thickness, cavity depth, asymmetry, inner shadow/value variation and a more naturally integrated trunk deformation.

## Full-scene comparison

The challenger scene is substantially richer and more coherent than the baseline scene. It has better grounding, better object presence and stronger visual hierarchy.

The main style correction needed before promotion is **less synthetic gloss / more tactile storybook material**. Several challenger assets share the same large pale elliptical highlight treatment. If repeated across an Activity, that becomes a new form of sameness. The Authoring Kit must therefore encode:

- varied highlight shapes by material;
- fewer and subtler canopy specular-like patches;
- more asymmetry and species/form variation;
- richer local color variation without neon saturation;
- softer integration of shadows/moss/details;
- no repeated 'same lobe + same highlight' formula across trees and bushes.

## Runtime-scale evidence

The 256/128/64 px comparison supports the challenger approach. The important masses remain legible and the extra detail does not collapse catastrophically at 64 px.

This is important: the benchmark shows Greia does **not** need to choose between richer source art and low-resolution readability. The authoring agent can produce richer masters while maintaining strong silhouettes.

## Architectural consequence

The benchmark validates the corrected authoring architecture:

> shared Authoring Kit = style + grammar + primitives + recipes + references; Activity authoring agent = composes/adapts/creates bespoke final art; runtime = consumes flattened semantic assets efficiently.

The next phase should therefore build the Authoring Kit around **recipes and reusable construction ingredients**, not around a giant catalogue of finished identical trees.

## Promotion decision

Do not wholesale-promote the challenger directory as finished canonical production art.

Instead:

1. use the challenger work as the preferred quality baseline;
2. refine material/highlight discipline;
3. extract reusable construction guidance/primitives where genuinely useful;
4. keep the candidate sources intact as benchmark provenance;
5. make the local authoring agent the preferred creator for the next environment/nature Authoring-Kit tranche;
6. require owner-visible comparison ZIPs for future major library promotions.
