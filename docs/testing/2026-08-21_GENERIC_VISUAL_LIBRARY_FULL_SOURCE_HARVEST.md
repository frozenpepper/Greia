# Greia Generic Visual Library — Full Source Harvest & True Gap Audit

**Purpose:** finish the generic authoring-library consolidation before any new generic art batch is created.

**This is an inventory/classification/review gate, not an art-production gate.**

---

## 1. Why this gate exists

The first generic consolidation correctly created the semantic authoring-library structure, but its coverage-gap report was incomplete because it harvested only:

- Forest / Meadow v0.3;
- Workshop v0.2;
- Clinic / Care 2026-08-21 candidate.

Greia already contains additional source pools that must be inspected before declaring generic gaps:

- Reading / Classroom v0.1;
- Fantasy / Village / Night v0.1;
- Water / Pond v0.1.

Do not create the proposed 16-asset “Living & Learning Essentials” batch yet.

---

## 2. Read first

Read:

1. `AGENTS.md`
2. `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`
3. `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`
4. `skills/greia-visual-authoring/SKILL.md`
5. `docs/reviews/visual/2026-08-21_generic-authoring-library-consolidation/PRIMARY_REVIEW.md`
6. `assets/visual/authoring_library/README.md`
7. all six current generic collection TOMLs
8. source catalogues for:
   - `assets/visual/environments/reading_classroom/v0.1/catalog.toml`
   - `assets/visual/environments/fantasy_village_night/v0.1/catalog.toml`
   - `assets/visual/environments/water_pond/v0.1/catalog.toml`

Also inspect the source SVGs and any existing pack review/reference images.

---

## 3. Hard rule: no new art in this gate

Do **not** draw new generic assets.

Do **not** reauthor Reading/Classroom, Fantasy/Village/Night, or Water/Pond as themed packs.

Do **not** create new doors, chairs, books, plants, baskets, tableware, water props, etc. yet.

First determine what Greia already owns and whether it is good enough.

---

## 4. Source pools that must be harvested

### 4.1 Reading / Classroom v0.1

Inspect every finished asset, including at minimum:

- walls/floor;
- arched window/light;
- tall bookcase;
- book stack;
- open storybook;
- reading tent;
- round rug;
- beanbag;
- reading chair;
- chalkboard;
- bunting;
- potted plant;
- toy basket;
- hanging mobile;
- floor cushion.

### 4.2 Fantasy / Village / Night v0.1

Inspect every finished asset, distinguishing generic objects from specialized fantasy/village scenery.

Likely generic candidates worth explicit review include:

- stone bridge;
- lantern post;
- wooden signpost;
- stone well;
- cobblestone edge;
- window glow / moonlight / sparkle assets where genuinely broad enough.

Cottages, castle/tower, distant village, etc. may remain specialized unless their form is broadly reusable.

### 4.3 Water / Pond v0.1

Inspect every finished asset, including:

- water base;
- bank edge;
- lily pads;
- reeds;
- water lilies;
- small dock;
- stepping stones;
- duckweed;
- ripple;
- shimmer;
- reflection glow;
- fish shadows;
- dragonfly FX;
- bubble FX.

Many of these are potentially generic Nature/Landscape or Lighting/FX resources and must not be recreated blindly.

---

## 5. Required classification vocabulary

For every inspected source asset assign exactly one disposition:

### `PREFERRED_GENERIC`
The asset is broadly reusable **and** already strong enough/reviewed enough to become a preferred generic authoring-library entry.

### `CANDIDATE_GENERIC`
The asset is broadly reusable and useful as reference/COMPOSE-ADAPT material, but it is not yet owner-approved as a preferred asset.

### `REAUTHOR_GENERIC`
The semantic role is broadly useful, but the existing art is visibly too weak/outdated to expose as a preferred reference. This is a **quality gap**, not a missing-role gap.

### `SPECIALIZED_THEME_ONLY`
The asset is useful only for a narrower theme/domain and should remain discoverable from its source/provenance bundle rather than the primary generic core.

### `DUPLICATE_OR_SUPERSEDED`
A stronger generic asset already covers the same role with no meaningful additional authoring value.

### `UNRESOLVED`
Use only when a real ambiguity remains after inspection.

---

## 6. Generic index status model

Update the generic authoring indexes so each entry exposes an explicit authoring admission state.

Use a field such as:

```toml
library_status = "preferred"
```

or

```toml
library_status = "candidate_reference"
```

Do not invent many states. The indexes need only distinguish what arbitrary Activity agents should preferentially reuse from what is mainly a reference/adaptation source.

Rules:

- `PREFERRED_GENERIC` → `library_status = "preferred"`
- `CANDIDATE_GENERIC` → `library_status = "candidate_reference"`
- `REAUTHOR_GENERIC`, `SPECIALIZED_THEME_ONLY`, `DUPLICATE_OR_SUPERSEDED` → do not present as preferred generic finished assets

Do not duplicate SVG files. Keep stable source paths/provenance.

---

## 7. Correct the existing generic library metadata

The current authoring-library README must no longer imply that the first 66 finished assets are all equally canonical/preferred.

Update it to state clearly:

- the semantic index structure is canonical;
- individual indexed resources carry their own admission/quality status;
- preferred assets should be tried first for direct REUSE;
- candidate references may still be valuable for COMPOSE/ADAPT or as inspiration;
- specialized theme assets live outside the primary generic core.

Keep finished assets and authoring ingredients counted separately.

---

## 8. Required visual review evidence

Create:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/`

Required PNG sheets:

1. `01-reading-generic-candidates.png`
   - show every Reading/Classroom asset proposed as `PREFERRED_GENERIC`, `CANDIDATE_GENERIC`, or `REAUTHOR_GENERIC`
2. `02-fantasy-generic-candidates.png`
   - same for Fantasy/Village/Night
3. `03-water-generic-candidates.png`
   - same for Water/Pond
4. `04-generic-library-expanded-overview-a.png`
5. `05-generic-library-expanded-overview-b.png`
6. `06-true-gaps-vs-quality-gaps.png`
   - visually and textually distinguish true missing roles from roles that already exist but need better art

Text evidence:

- `FULL_SOURCE_AUDIT.md`
- `source-dispositions.json`
- `true-gap-audit.json`
- `audit.json`

The producer must inspect the actual pixels before assigning `PREFERRED_GENERIC`.

---

## 9. Gap analysis rules

Recompute coverage only after all existing source pools above are classified.

Every proposed gap must be one of:

### `TRUE_MISSING`
No suitable source asset exists anywhere in the reviewed source pools.

### `QUALITY_GAP`
A source asset exists for the role, but it should be reauthored before becoming preferred.

### `VARIETY_GAP`
At least one strong generic asset exists, but another meaningfully different form would provide broad reusable value.

### `NO_GAP`
Existing preferred/candidate resources already provide enough useful coverage.

Do not call an omitted-from-index asset “missing.”

---

## 10. Mandatory sanity checks against the previous report

Explicitly revisit these previous claimed gaps:

- books/storybooks;
- reading chair / soft seating;
- potted indoor plants;
- baskets/containers;
- water/reeds/pond assets;
- signs/bridges/wells;
- room architectural pieces.

For each, state whether it is now:

- `TRUE_MISSING`
- `QUALITY_GAP`
- `VARIETY_GAP`
- `NO_GAP`

The old coverage report is not authoritative until superseded by this audit.

---

## 11. Recommended next production batch

Only after the full-source harvest, recommend one next **generic** art-production batch.

The batch must target the highest-value combination of:

- true missing roles;
- quality gaps;
- important variety gaps.

Do not choose assets simply because they belong to the same old themed environment.

Do not propose more than roughly 12–18 finished assets in one batch unless there is a very strong reason.

---

## 12. ZIP for owner visual review

Create:

`./GREIA_VISUAL_REVIEW_GENERIC_LIBRARY_FULL_SOURCE_HARVEST_2026-08-21.zip`

It must contain:

- the six required PNG sheets;
- `FULL_SOURCE_AUDIT.md`;
- `source-dispositions.json`;
- `true-gap-audit.json`;
- `audit.json`.

The ZIP is for transfer and should not be committed unless repository policy explicitly requires it.

Final response must include exactly:

`VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_GENERIC_LIBRARY_FULL_SOURCE_HARVEST_2026-08-21.zip`

---

## 13. Stop conditions

Stop and report rather than inventing data if:

- a source file cannot be found;
- an asset cannot be rendered for review;
- provenance is ambiguous;
- classification remains genuinely uncertain.

Do not compensate by drawing a replacement during this gate.

---

## 14. Completion criterion

This gate is complete only when we can answer, with evidence:

> Across all visual source pools Greia already owns, what generic resources do we truly have, which are preferred, which are only candidate references, which need reauthoring, and what is actually still missing?

Only then should new generic art production resume.