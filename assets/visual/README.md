# Greia Visual Asset Library

**Status:** active shared visual-library source; not a runtime loader contract  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`

This tree is the staging/source home for Greia's reusable visual library. It exists so Shell and Activities can share a coherent visual world instead of accumulating unrelated private art.

**Nothing here authorizes runtime filesystem discovery.** Exact catalogue/loader APIs remain source-owned and require architecture review.

## Production rule

Greia visual work is asset-first:

> excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → Shell/Activity reuse

A weak primitive does not become production art because it is hidden inside a scene.

## Current real source packs

### Characters / motion seed

```text
assets/visual/characters/
assets/visual/specimens/a1/
assets/visual/specimens/a2/
```

Working core cast:

- Lilli — unicorn Puff;
- Nino — owl Bean;
- Tito — fox Puff;
- Momo — friendly monster Puff.

Accepted character grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

Character expression/motion design remains separate from release/runtime approval:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
```

### Forest / meadow v0.2

```text
assets/visual/environments/forest_meadow/v0.2/
```

Candidate reusable environment pack containing 27 SVG masters across trees, foliage, props, backgrounds, ground, atmosphere, shadows and ambient FX.

Key files:

```text
catalog.toml
REVIEW.md
composition_day.toml
parallax_proof.html
```

The pack is candidate/source + desktop-review evidence only. `parallax_proof.html` uses the actual reusable SVGs and exists only to test layered motion; it is not runtime architecture.

### Shared UI v0.1

```text
assets/visual/ui/v0.1/
```

Candidate reusable visual masters for panels, cards, buttons, tabs, badges, progress, bubbles, reward/avatar frames, focus, shadows and highlight treatment.

Key files:

```text
catalog.toml
REVIEW.md
```

The UI pack follows `runtime/theme-defaults.toml` but does not replace Greia's accepted semantic UI architecture or protected system chrome.

## Asset states

Use:

- `concept`
- `candidate`
- `approved`
- `superseded`
- `rejected`

`approved` must always carry meaningful scope when relevant. Presence in Git never means approved.

Examples of approval scopes:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Do not infer a stronger scope from a weaker one.

## Asset metadata

Reusable assets should record enough information to establish:

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

Committed source artwork created directly for Greia should still say so explicitly; provenance is not only for third-party files.

## Review discipline

Environment/UI asset families should normally be reviewed in this order:

1. individual source assets;
2. representative light/dark/theme backgrounds;
3. coherent pack subset;
4. low-resolution composition;
5. subtle motion/parallax proof if relevant;
6. simulator/runtime/hardware evidence only when actual integration reaches that stage.

Do not use a full-screen composition to conceal weak individual assets.

## Runtime boundary

Any future runtime path must remain explicit and bounded:

- semantic IDs/catalogues rather than arbitrary directory scans;
- bounded caches;
- no per-frame file/decode work;
- static fallbacks for meaningful animated states;
- no network/CDN dependency for core operation;
- Python and future Web Activities should ultimately consume the same semantic visual system rather than maintaining parallel art libraries.
