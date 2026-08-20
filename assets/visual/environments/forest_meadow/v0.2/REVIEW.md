# Forest / Meadow v0.2 — Desktop Visual Review

**Status:** candidate review; not owner-approved release art and not runtime/hardware acceptance.

## Scope reviewed

The reusable SVG masters were rasterized locally and inspected individually and in representative light/dark/sky contexts. The pack was then composed at both supported low-resolution references using the real masters rather than a baked scene.

## First-pass corrections made

Earlier desktop review corrected:

- `tree_sapling.svg` — stronger young-tree silhouette;
- `distant_treeline.svg` — less synthetic repeated geometry;
- `fog_strip.svg` — more usable layered haze;
- `fx_dust_motes.svg` — clearer low-count glow motes.

## Final restraint pass

The bounded 2026-08-20 restraint pass added:

- `reference_restraint_1024x600.svg`;
- `reference_restraint_800x600.svg`;
- `RESTRAINT_REVIEW.md`;
- revised `composition_day.toml`.

The default day reference now:

- keeps a calm central playfield;
- frames the edges with hero/secondary trees and bounded foliage;
- reduces sunlight and fog opacity;
- excludes `fx_fireflies.svg`, `fx_dust_motes.svg` and `fx_falling_leaves.svg` from the default simultaneous layer set;
- treats those three FX as optional event/evening/weather ingredients;
- composes 800×600 separately instead of letterboxing/scaling the 1024×600 reference.

## Coherent candidate subset

The full 27-master pack remains available. The normal day composition uses only the calmer subset needed for depth and framing.

This is still **candidate SOURCE + DESKTOP VISUAL REVIEW**, not approval.

## Composition boundary

`composition_day.toml` records intended layer roles and cheap ambient-motion guidance. `parallax_proof.html` exists solely to exercise committed SVG layers with simple CSS transforms. Neither is runtime architecture.

## Next review

The planned forest restraint pass is complete. Do not keep polishing this pack without a concrete visual defect. Next actions are owner revision when useful and, later, simulator/runtime/hardware evidence only after actual integration.
