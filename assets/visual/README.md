# Greia Visual Asset Library

**Status:** active shared visual-library source; not a runtime loader contract  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`

This tree is the source home for Greia's reusable visual library. Shell and Activities should ultimately share this coherent world rather than accumulate unrelated private art.

**Nothing here authorizes runtime filesystem discovery.** Exact catalogue/loader APIs remain source-owned and require architecture review.

## Production rule

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse**

A weak primitive does not become production art because it is hidden inside a scene.

## Current source packs

### Characters / motion seed

```text
assets/visual/characters/
assets/visual/specimens/a1/
assets/visual/specimens/a2/
```

Core cast: Lilli, Nino, Tito, Momo. Character grammar and motion design are useful shared foundations but are not release/runtime/physical approval.

### Forest / meadow v0.2

```text
assets/visual/environments/forest_meadow/v0.2/
```

27 candidate SVG masters covering trees, foliage, props, distant layers, ground, light/fog, shadows and optional ambient FX. Includes composition metadata, actual-asset parallax proof, and bounded 1024×600 / 800×600 restraint references.

### Shared UI v0.1

```text
assets/visual/ui/v0.1/
```

Candidate shared masters for panels, cards and states, buttons and states, tabs, badges, progress, bubbles, reward/avatar frames, loading/error/empty/portal art, focus, shadows and highlights. Includes independently composed 1024×600 / 800×600 references.

### Workshop v0.1

```text
assets/visual/environments/workshop/v0.1/
```

19 candidate reusable masters: furniture, creative props, wall/floor bases, window/light and the limited composition-critical additions needed for layered 1024×600 / 800×600 references.

### Clinic / care v0.1

```text
assets/visual/environments/clinic/v0.1/
```

17 candidate reusable masters covering warm pretend-care furniture/props, room bases, window/light and restrained care FX. Includes reduced-size and target-size desktop review. No medical labels/dosage-like content are embedded.

### Reading / classroom v0.1

```text
assets/visual/environments/reading_classroom/v0.1/
```

17 candidate reusable masters covering room bases, arched window/light, bookcase/books, reading tent/rug/seating, chalkboard and restrained decor. The pack reuses existing Workshop block/pencil assets by semantic reference rather than drawing duplicates.

Key authority/evidence files per environment pack normally include:

```text
catalog.toml
README.md
REVIEW.md
COMPOSITION.md and/or composition*.toml where relevant
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

Reusable assets should record:

- semantic ID;
- editable/source master;
- family;
- current state;
- provenance/license;
- intended scale range where relevant;
- alpha/transparency requirements;
- layer/parallax role where relevant;
- optional ambient-motion role;
- optional theme variants.

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

Do not use a full-screen composition to conceal weak individual assets. Do not replace this workflow with generated scene concept images.

## Runtime boundary

Any future runtime path must remain explicit and bounded:

- semantic IDs/catalogues rather than arbitrary directory scans;
- bounded caches;
- no per-frame file/decode work;
- static fallbacks for meaningful animated states;
- no network/CDN dependency for core operation;
- Python and future Web Activities should ultimately consume the same semantic visual system rather than parallel art libraries.

All current packs remain `runtime_consumed = false` unless their own catalogue explicitly changes after architecture-reviewed integration.