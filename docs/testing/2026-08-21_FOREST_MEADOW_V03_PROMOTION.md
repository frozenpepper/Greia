# Forest / Meadow v0.3 — Exact Promotion Runbook

**Purpose:** materialize the owner-authorized selective Forest / Meadow v0.3 source pack.  
**Authority:** `docs/reviews/visual/2026-08-21_forest-meadow-pack-finalization/PRIMARY_PROMOTION_REVIEW.md`

## 1. This is mechanical promotion, not another art pass

Do not redraw, refine, reinterpret, or optimize Forest / Meadow again.

The owner has completed pixel review. The selection below is final for this promotion.

Preserve:

```text
assets/visual/environments/forest_meadow/v0.2/
```

Create:

```text
assets/visual/environments/forest_meadow/v0.3/
```

## 2. Exact semantic role selection

Use the **2026-08-21 candidate** for every semantic role except the five explicit legacy retentions below.

Candidate source root:

```text
assets/visual/pack_candidates/forest_meadow/2026-08-21/
```

Legacy source root:

```text
assets/visual/environments/forest_meadow/v0.2/
```

### Retain v0.2 exactly for

```text
tree.willow.01             -> v0.2/tree_willow.svg
treeline.distant.01        -> v0.2/distant_treeline.svg
ground.grass_edge.01       -> v0.2/grass_edge.svg
ground.dirt_patch.01       -> v0.2/ground_dirt_patch.svg
atmosphere.fog_strip.01    -> v0.2/fog_strip.svg
```

### Candidate for all other semantic roles

That means 23 candidate semantic roles plus 5 legacy-retained semantic roles.

Do not alter role IDs during promotion.

## 3. Authoring ingredients

Promote exactly these source-level authoring ingredients into a clearly documented `ingredients/` area in v0.3:

```text
ingredient.bark    -> ingredients/ingredient_bark_knot.svg
ingredient.flower  -> ingredients/ingredient_flower_sprig.svg
```

Do not promote as preferred ingredients:

```text
ingredient.foliage
ingredient.moss
```

Leave those in candidate/provenance history only.

## 4. Metadata

Create/update v0.3:

```text
README.md
catalog.toml
COMPOSITION.md / equivalent pack guidance if used by this pack family
```

The metadata must state clearly:

- v0.3 is the preferred Forest / Meadow authoring pack;
- it is a selective promotion combining reviewed candidate assets and five retained v0.2 roles;
- v0.2 remains provenance/history;
- the pack is an authoring toolbox, not a requirement that Activities reuse exact finished assets;
- Activity authors should follow `skills/greia-visual-authoring/SKILL.md`;
- `runtime_consumed` must reflect actual current runtime state and must not be changed to `true` merely because source promotion occurred.

## 5. Pack indexes

Update the appropriate source-pack inventories/indexes so Forest / Meadow v0.3 is the preferred current authoring version.

Inspect before editing:

```text
assets/visual/packs_v0.1.toml
assets/visual/library_v0.1.toml
```

Do not break historical references to v0.2.

## 6. Runtime boundary

Do not modify:

- `assets/catalog/shared_visuals_v1_source.toml`;
- generated runtime PNG catalogues;
- Nascondino;
- the scene compositor;
- Activity code.

Source-pack promotion and runtime-consumer migration are different changes. This gate only promotes the authoring pack.

## 7. Verification

Verify:

1. v0.2 remains unchanged;
2. v0.3 contains every semantic role in its catalogue;
3. exactly the five owner-retained roles use the legacy artwork;
4. all other semantic roles use the reviewed candidate artwork;
5. only the two authorized ingredients are presented as preferred v0.3 ingredients;
6. all relative paths resolve inside v0.3;
7. pack indexes point to/prefer v0.3 without deleting provenance.

No new visual-review ZIP is required for this mechanical copy/promotion gate. The source selection is already owner-reviewed.

## 8. Commit and return

Commit and push to canonical `main`.

Return:

- exact commit SHA;
- v0.3 pack path;
- semantic role count;
- confirmation: `23 candidate + 5 legacy`;
- preferred ingredient count: `2`;
- confirmation that runtime consumers were not changed.

Then proceed to:

```text
docs/testing/2026-08-21_WORKSHOP_BASE_PACK_REAUTHORING.md
```
