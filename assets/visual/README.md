# Greia Visual Asset Library

**Status:** active shared visual-library source; not a runtime loader contract  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`

This tree is the source home for Greia's reusable visual library. Shell and Activities should ultimately share this coherent world rather than accumulate unrelated private art.

**Nothing here authorizes runtime filesystem discovery.** Exact catalogue/loader APIs remain source-owned and require architecture review.

## Production rule

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → one explicit shared consumption seam → Shell/Activity reuse**

Reuse a suitable shared asset before painting a near-duplicate. A weak primitive does not become production art because it is hidden inside a scene.

## Design inventories

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

`library_v0.1.toml` owns the character/archetype/expression/motion seed inventory. `packs_v0.1.toml` owns the current pack-level design/review inventory and reuse dependencies.

Neither file is a runtime discovery contract.

## Current source packs

### Characters / motion seed

```text
assets/visual/characters/
assets/visual/specimens/a1/
assets/visual/specimens/a2/
```

Core cast: Lilli, Nino, Tito, Momo. Static character anchors and motion/expression candidates retain their explicit review scopes; they are not implied release/runtime/physical approval.

### Forest / meadow v0.2

`assets/visual/environments/forest_meadow/v0.2/`

27 candidate SVG masters covering trees, foliage, props, distant layers, ground, light/fog, shadows and optional ambient FX. Includes composition metadata, actual-asset parallax proof, and bounded 1024×600 / 800×600 restraint references.

### Shared UI v0.1

`assets/visual/ui/v0.1/`

Candidate shared masters for panels, cards/states, buttons/states, tabs, badges, progress, bubbles, reward/avatar frames, loading/error/empty/portal art, focus, shadows and highlights. Includes independently composed 1024×600 / 800×600 references.

### Workshop v0.1

`assets/visual/environments/workshop/v0.1/`

19 candidate reusable masters: furniture, creative props, wall/floor bases, window/light and limited composition-critical additions required for layered target-size references.

### Clinic / care v0.1

`assets/visual/environments/clinic/v0.1/`

17 candidate reusable masters covering warm pretend-care furniture/props, room bases, window/light and restrained care FX. Includes reduced-size and target-size desktop review. No medical labels/dosage-like content are embedded.

### Reading / classroom v0.1

`assets/visual/environments/reading_classroom/v0.1/`

17 candidate reusable masters covering room bases, arched window/light, bookcase/books, reading tent/rug/seating, chalkboard and restrained decor. Reuses Workshop block/pencil assets by semantic reference rather than duplicating them.

### Fantasy / village / night v0.1

`assets/visual/environments/fantasy_village_night/v0.1/`

15 candidate reusable masters covering night sky/moon, distant village/castle, cottages, castle tower, bridge, lantern, signpost, well, cobblestone and separate light/FX overlays. Forest vegetation/fireflies remain shared reuse dependencies rather than duplicated night variants.

### Water / pond v0.1

`assets/visual/environments/water_pond/v0.1/`

14 water-specific candidate masters covering pond-water/shoreline, lilies/reeds/duckweed, dock/stepping stones, ripple/shimmer/reflection treatment and restrained fish/dragonfly/bubble FX. Its target references reuse canonical Forest distant hills/tree line and the catalog points to Forest generic rocks/log/grass/flowers rather than duplicating them.

Water/Pond includes independent 1024×600 / 800×600 layered references. The individual review corrected weak dock/lily-pad treatments and the target pass strengthened water/reed depth before recording the candidate review.

Key authority/evidence files per environment pack normally include:

```text
catalog.toml
README.md
REVIEW.md
COMPOSITION.md and/or composition*.toml where relevant
reference_1024x600.svg / reference_800x600.svg where a target-size composition exists
```

## Asset states

Use `concept | candidate | approved | superseded | rejected`.

`approved` must carry meaningful scope where relevant, such as:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Presence in Git never means approved and a weaker approval scope does not imply a stronger one.

## Asset metadata

Reusable assets should record semantic ID, editable/source master, family/role, current state, provenance/license, intended scale where relevant, alpha requirements, layer/parallax role where relevant, and optional ambient-motion/theme variants.

Committed Greia-created artwork still records provenance explicitly.

## Review discipline

Environment/UI families normally progress through:

1. individual source assets;
2. representative grounds and reduced-size review;
3. corrections to weak assets;
4. coherent pack subset;
5. low-resolution composition using only real assets;
6. restrained motion/parallax proof if useful;
7. simulator/runtime/hardware evidence only after real integration.

Do not use a full-screen composition to conceal weak individual assets. Do not replace this workflow with generated scene/concept images.

## Runtime boundary / next phase

Broad candidate environment/UI coverage now exists. Additional environment families require a concrete reusable coverage gap; the next planned work is the V5 shared-consumption seam.

Greia already has explicit platform asset code in:

```text
src/greia_platform/assets.py
src/greia_platform/activity_assets.py
assets/catalog/core_icons_v1.toml
```

Future shared visual consumption must extend that explicit manifest-driven pattern rather than introduce arbitrary directory scans or a second unrelated asset framework.

Any runtime path must remain explicit and bounded:

- semantic IDs/catalogues rather than arbitrary directory scans;
- path containment and duplicate-ID rejection;
- bounded caches;
- no per-frame file/decode work;
- static fallbacks for meaningful animated states;
- no network/CDN dependency for core operation;
- Python and future Web Activities consume the same semantic visual contract rather than parallel art libraries.

All current visual packs remain `runtime_consumed = false` until an architecture-reviewed implementation changes that explicitly.
