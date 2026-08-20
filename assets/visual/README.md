# Greia Visual Asset Library — Starter Contract

**Status:** design/library seed; not a runtime loader contract  
**Active art plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Authoring skill:** `skills/greia-visual-authoring/SKILL.md`

This directory is the staging home for the constraint-native Greia visual library.

The directory exists so art work can become a coherent reusable library instead of accumulating as unrelated files inside individual Activities. **Nothing in this README authorizes runtime filesystem discovery.** Exact runtime catalogue/loader APIs remain source-owned and will be designed only if/when phase A7 reaches that work.

## Intended semantic families

```text
assets/visual/
  characters/
    heroes/
    standard/
    activity_cast/
    object_friends/
  expressions/
  animations/
  props/
  environments/
  ui/
  fx/
  specimens/
  library_v0.1.toml
```

Folders should be added when real reviewed assets exist; do not create empty directory noise merely to satisfy the conceptual tree.

## Asset tiers

### Tier A — canonical shared foundations

Carefully reviewed Greia-owned/repository-approved assets intended for reuse across Shell/Activities.

Examples:

- core cast;
- body archetype exemplars;
- common face/expression pieces where reusable;
- common FX;
- common props;
- shared UI illustration assets.

### Tier B — guided generated/contributed content

Reviewed secondary characters, Activity cast, props and scene variants produced under the Greia visual-authoring skill.

### Tier C — local/disposable content

One-off decoration/content where style drift cannot undermine system identity or gameplay comprehension. Tier C still needs appropriate provenance/license treatment if committed/distributed.

## Approval scope is explicit

The inventory may use `approved`, but that word is never enough by itself. An approved item should record a scope such as:

```text
design_grammar
static_style_anchor
runtime_asset
release_asset
physical_acceptance
```

Do not infer a stronger scope from a weaker one.

For example, the current A1 cast is approved as:

```text
approval_scope = "static_style_anchor"
runtime_ready = false
```

That means the visual direction is accepted; it does not freeze the SVGs as release art or create a runtime character API.

## Current core cast

The first owner-reviewed static style anchors are:

- `lilli` — unicorn Puff;
- `nino` — owl Bean;
- `tito` — fox Puff;
- `momo` — friendly monster Puff.

Accepted character grammar:

```text
docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md
```

A1 review source:

```text
assets/visual/specimens/a1/review.html
```

## Accepted archetypes

- `puff`
- `bean`
- `cutout_critter`
- `object_friend`

These are approved at `design_grammar` scope.

## A2 expression/motion candidates

Current semantic expression/motion work is intentionally still candidate-level:

```text
docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md
assets/visual/specimens/a2/base_motion_v0.1.toml
assets/visual/specimens/a2/review.html
```

Base motion set:

- `idle_bounce`
- `blink`
- `happy_hop`
- `celebrate_pop`
- `surprised_wobble`
- `sleepy_sway`

These are semantic design names. The A2 TOML explicitly declares `runtime_consumed = false`; no runtime API is implied.

## Provenance

Every canonical distributed visual asset eventually needs enough metadata to answer:

- where did it come from;
- who/what created it;
- what license/rights apply;
- whether it was generated, contributed or derived;
- which file is the editable/source master;
- what raster derivatives were produced from that master;
- whether it is approved, provisional, rejected or superseded;
- what the approval scope actually covers.

Do not delete provenance just because an asset has been rasterized or copied into a build layer.

## Review states

Use these human-facing states in the library inventory:

- `concept` — design slot only;
- `candidate` — asset exists and awaits visual review;
- `approved` — approved for its explicit `approval_scope`;
- `superseded` — replaced but retained where history/migration needs it;
- `rejected` — experiment intentionally not used.

Do not label an asset `approved` merely because it exists in Git.

## Small-size masters/derivatives

For characters/icons intended to appear small, review at 256/128/64 px as appropriate. Prefer an editable vector/high-resolution master plus deterministic derivatives when that preserves quality and size, but do not make SVG a dogma when a clean raster/sprite asset is more appropriate.

## Runtime boundary

The future runtime path must remain explicit and bounded:

- semantic IDs/catalogues rather than arbitrary directory scans;
- bounded caches;
- no per-frame file/decode work;
- static fallbacks for meaningful animated states;
- no network/CDN dependency for core operation;
- future Web runtime should consume the same semantic asset system rather than inventing a separate visual library.
