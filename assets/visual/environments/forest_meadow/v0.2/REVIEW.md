# Forest / Meadow v0.2 — Desktop Visual Review

**Status:** candidate review; not owner-approved release art and not runtime/hardware acceptance.

## Scope reviewed

The reusable SVG masters were rasterized locally and inspected individually and in representative light/dark/sky contexts. A 1024×600 static composition was also assembled from the real masters to verify that the assets form a coherent layer family without repainting them into one baked scene.

## First-pass corrections made

The first review found four specific weak treatments and they were revised before this review was recorded:

- `tree_sapling.svg` — silhouette/detail balance was weak; revised into a clearer young-tree variant;
- `distant_treeline.svg` — repetitive geometric tree rhythm looked synthetic; changed to a more organic mixed canopy with only sparse conifer cues;
- `fog_strip.svg` — single weak band did not create usable depth; changed to two restrained haze layers;
- `fx_dust_motes.svg` — points were too easy to lose; changed to soft local glow motes while remaining low-count.

## Current coherent candidate subset

Strong enough to use for the first composition/parallax proof, while still remaining candidate assets:

- `tree_hero.svg`
- `tree_secondary.svg`
- `tree_sapling.svg`
- `tree_willow.svg`
- `bush_round.svg`
- `bush_flowering.svg`
- `bush_low.svg`
- `fern_cluster.svg`
- `flower_patch.svg`
- `mushroom_cluster.svg`
- `rock_cluster_large.svg`
- `rock_cluster_small.svg`
- `fallen_log.svg`
- `stump.svg`
- `cloud_large.svg`
- `cloud_small.svg`
- `distant_hills.svg`
- `distant_treeline.svg`
- `grass_edge.svg`
- `ground_dirt_patch.svg`
- `sunlight_rays.svg`
- `fog_strip.svg`
- both contact-shadow variants
- fireflies / dust motes / falling leaves.

This is **not** an approval claim. It means the set is coherent enough for the next proof without hiding known primitive failures.

## Composition boundary

`composition_day.toml` records the intended layer roles and cheap ambient motion guidance. It is design metadata only. `parallax_proof.html` exists solely to exercise the committed SVG layers with simple CSS transforms; it must not become runtime architecture.

## Next review

- check the composition at 800×600 and 1024×600;
- remove any atmosphere/FX that adds noise instead of depth;
- confirm foreground assets do not steal the gameplay focal area;
- then start the next environment family rather than endlessly polishing one forest pack.
