# Primary Review — Forest / Meadow Base Art Pack Reauthoring

**Date:** 2026-08-21  
**Reviewed candidate commit:** `d0ac3c1ff505a824d9de9fd9ad950f86bd083e39`  
**Evidence inspected:** owner attachment ZIP `GREIA_VISUAL_REVIEW_FOREST_MEADOW_BASE_PACK_REAUTHORING_2026-08-21.zip`  
**Candidate pack:** `assets/visual/pack_candidates/forest_meadow/2026-08-21/`

## Disposition

**PACK-SCALE RESULT: CLEARLY BETTER THAN THE LEGACY FOREST/MEADOW BASELINE, BUT NOT YET READY FOR WHOLE-PACK PROMOTION.**

This run is sufficient to settle the original maintainer-side producer comparison for this pack family: the owner's local maintainer agent is producing a materially stronger Forest/Meadow source pack than the earlier Greia v0.2 baseline overall. This is a maintainer-side content-production conclusion only; it is not evidence about arbitrary future Activity-authoring agents.

The correct continuation is one bounded pack-finalization pass, then promotion review, then move to Workshop. Do not return to specimen/hero-tree optimization.

## What is clearly improved

The candidate is visibly stronger than v0.2 in the important pack-wide sense:

- tree silhouettes and trunk/bough structure are substantially more intentional;
- bramble/foliage growth-habit variety is much better than the old generic green mounds;
- granite rocks have much stronger mass/value separation;
- mushroom, log and stump props are more readable and materially distinct;
- clouds and hills have better depth than the legacy flat shapes;
- the candidate 1024×600 composition is substantially richer and more coherent than the baseline composition;
- representative candidate assets survive the 512/256/128/64 px scale sequence without losing their primary identity.

The new ingredient concept is also appropriate for the future toolbox: foliage spray, bark knot, moss-crevice and flower-sprig sources are plausible authoring-time ingredients rather than runtime obligations.

## What is not accepted yet

### 1. The owner-review evidence does not actually show the complete mapped pack

`audit.json` maps 28 semantic roles, but the candidate overview visually presents only a subset of them. A whole-pack promotion cannot be justified by a role map alone.

Important roles that need direct final visual evidence include at least:

- `tree.willow.01`;
- `ground.grass_edge.01`;
- `ground.dirt_patch.01`;
- `atmosphere.fog_strip.01`;
- `shadow.contact.small.01`;
- `shadow.contact.wide.01`;
- `fx.fireflies.01`;
- `fx.dust_motes.01`;
- `fx.falling_leaves.01`.

The finalization evidence must show every role proposed for promotion, not merely list it.

### 2. Some candidate roles are weaker or unresolved

- **Distant treeline:** the candidate is cleaner but too featureless/smooth compared with the more articulated legacy treeline. It may work as a far atmospheric silhouette, but the current evidence does not justify claiming it is automatically superior. Revise it or deliberately retain the legacy role.
- **Flower patch:** the candidate becomes extremely sparse and line-thin. The legacy patch is crude, but it has stronger immediate child-scale presence. Revise or deliberately retain the stronger role.
- **Fern cluster:** botanically more varied than baseline, but its thin fronds need direct small-size proof before promotion.
- **Rounded foliage family:** the birch/sapling/round/low bushes still share some puffy rounded mass language. This is not a blocker by itself because the pack now also contains bramble, ferns and other genuinely different growth habits, but the producing agent's claim that no repeated formula remains is too strong.

### 3. The candidate composition contains a misleading overlap

The right-side birch aligns with the foreground rock in a way that makes the tree appear to grow out of / sit on the rock. This is a composition-evidence defect, not necessarily an asset defect. Correct the final comparison composition so grounding relationships are visually unambiguous.

### 4. Self-review overclaims whole-pack replacement

The statement that no v0.2 asset should remain is not yet supported. Greia promotion is allowed to be selective. If a legacy support asset remains better for a role, keep it until a stronger replacement exists.

## Pack-level conclusion

The important question has been answered: **yes, the local maintainer agent can reauthor this base pack better than the earlier Greia baseline at useful pack scale.**

Do not keep polishing the already-strong tree/rock/log families. Perform one bounded finalization pass only on missing/weak evidence and roles, produce a complete promotion map, and then stop Forest/Meadow work.

Expected next state after successful finalization:

```text
legacy v0.2 preserved as provenance
+ reviewed candidate replacements
+ deliberate legacy retention where candidate is weaker
→ promoted Forest/Meadow v0.3
→ move immediately to Workshop pack reauthoring
```

## Status

- Local maintainer agent versus old Forest/Meadow baseline: **DECIDED — LOCAL AGENT PREFERRED FOR BASE-PACK REAUTHORING**.
- Current candidate as a source pool: **OWNER-REVIEWED / STRONGER OVERALL**.
- Whole candidate as direct replacement: **NOT YET PROMOTED**.
- Further hero-tree optimization: **NOT A MILESTONE**.
