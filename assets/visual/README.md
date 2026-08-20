# Greia Visual Asset Library

**Status:** active shared visual-library source + V5 explicit-consumption implementation seed  
**Main visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current visual resume:** `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`

This tree is the source home for Greia's reusable visual library. Shell and Activities should ultimately share this coherent world rather than accumulate unrelated private art.

For the complete architecture, production model, runtime rendition/caching flow and documentation index, start with `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`. This README is the source-tree summary.

**Nothing here authorizes runtime filesystem discovery.** Runtime consumption is explicit, semantic and bounded.

## Production rule

> **excellent individual assets → reusable asset packs → layered composition → subtle parallax / ambient motion / light / shadow → shared UI system → one explicit shared consumption seam → Shell/Activity reuse**

Reuse a suitable shared asset before painting a near-duplicate. A weak primitive does not become production art because it is hidden inside a scene.

## Design inventories

```text
assets/visual/library_v0.1.toml
assets/visual/packs_v0.1.toml
```

`library_v0.1.toml` owns the character/archetype/expression/motion seed inventory. `packs_v0.1.toml` owns pack-level design/review inventory and reuse dependencies.

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

14 water-specific candidate masters covering pond-water/shoreline, lilies/reeds/duckweed, dock/stepping stones, ripple/shimmer/reflection treatment and restrained fish/dragonfly/bubble FX. Target references reuse canonical Forest distant hills/tree line and the catalog points to Forest generic rocks/log/grass/flowers rather than duplicating them.

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

## V5 explicit runtime-rendition / consumption seed

V5 deliberately extends the existing platform asset catalogue instead of adding directory discovery or a parallel framework.

Source authority:

```text
src/greia_platform/assets.py
src/greia_platform/pygame_visual_assets.py
src/greia_launcher/visual_assets.py
assets/catalog/shared_visuals_v1_source.toml
tools/build_visual_renditions.py
tools/validate_visual_renditions.py
Makefile: visual-assets / visual-assets-check
```

### Lookup

`AssetCatalogue` supports explicit shared visuals with semantic ID, bounded kind, role and named variants while preserving the old icon contract. IDs share one namespace; paths are existence-checked and contained inside the assets root. Explicit catalogues may be safely merged only under the same assets root and only with globally unique IDs.

### Build-time renditions

`shared_visuals_v1_source.toml` is the first explicit selection of reviewed SVG UI masters/variants for runtime PNG generation.

`tools/build_visual_renditions.py` uses build-host `rsvg-convert`/librsvg to generate PNG renditions and an explicit `assets/catalog/shared_visuals_v1.toml`. It validates source/output containment, kinds/variants, dimensions, duplicate output paths and generated PNG dimensions and publishes output transactionally.

The target device does **not** need an SVG renderer.

`make visual-assets` is the explicit generation entrypoint.

`tools/validate_visual_renditions.py` / `make visual-assets-check` owns generated-output freshness/mapping/PNG validation as a source/build contract.

### Runtime Pygame cache

`PygameVisualSurfaceCache`:

- consumes only explicit catalogue PNG paths;
- rejects SVG runtime paths;
- keys by semantic ID + variant + requested size;
- reuses `ui_core.BoundedCache`;
- defaults to a 12-entry LRU;
- limits each requested cached surface to 1024×600 pixels by default;
- loads/scales only on a cache miss;
- imports Pygame lazily and avoids display-dependent `convert()`/`convert_alpha()` in the loader.

Provider-free cache tests are committed. An isolated local harness using the exact new cache source passed 9/9; this is not a repository-wide current-head PASS.

### Current runtime boundary

The previous execution environment did not provide `rsvg-convert`; therefore the generated runtime PNGs/catalogue were not built there. The explicit launcher bridge exists, but no Shell/Activity path is yet accepted as consuming this catalogue/cache.

All source visual packs therefore remain `runtime_consumed = false`.

Current first integration candidate:

```text
ui.shadow.soft
```

under existing launcher Activity tiles, preserving the current static/primitive fallback.

Current owner-directed local-agent protocol:

```text
docs/testing/2026-08-20_V5_VISUAL_INTEGRATION_SIMULATOR_LOCAL_AGENT.md
```

For that tranche, runtime/visual/fallback/responsive acceptance is performed through the real Greia Shell in the Activity Simulator. Check `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md` before resuming.

## Review discipline

Environment/UI families normally progress through:

1. individual source assets;
2. representative grounds and reduced-size review;
3. corrections to weak assets;
4. coherent pack subset;
5. low-resolution composition using only real assets;
6. restrained motion/parallax proof if useful;
7. explicit build-time runtime renditions where selected;
8. one bounded real consumer;
9. simulator/runtime/hardware evidence only after real integration.

Do not use a full-screen composition to conceal weak individual assets. Do not replace this workflow with generated scene/concept images.

## Runtime invariants

- semantic IDs/catalogues rather than arbitrary directory scans;
- path containment and duplicate-ID rejection;
- pre-render SVG to PNG on build host, never on low-end target;
- bounded caches and bounded requested surfaces;
- no per-frame file/decode work;
- static fallbacks for meaningful animated states;
- no network/CDN dependency for core operation;
- Python and future Web Activities ultimately consume the same semantic visual contract rather than parallel art libraries.