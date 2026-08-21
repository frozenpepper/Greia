# Generic Visual Library — Full Source Harvest & True Gap Audit

**Date:** 2026-08-21  
**Gate:** Full Source Harvest & True Gap Audit Gate  
**Reference Runbook:** `docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md`  
**Parent Taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Evidence Directory:** `docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/`

---

## 1. Executive Summary

This audit completes the harvest across **all six repository source pools**:
1. `Forest / Meadow v0.3` (Promoted preferred source pool)
2. `Workshop v0.2` (Promoted preferred source pool)
3. `Clinic / Care 2026-08-21 Candidate` (Reviewed candidate source pool)
4. `Reading / Classroom v0.1` (Harvested legacy source pool)
5. `Fantasy / Village / Night v0.1` (Harvested legacy source pool)
6. `Water / Pond v0.1` (Harvested legacy source pool)

### Key Conclusions:
- **No Art Duplication:** All assets remain in their respective source directories and are indexed by reference with explicit admission status (`library_status = "preferred"` vs `library_status = "candidate_reference"`).
- **Previous Gap Claims Corrected:** Storybooks, reading armchairs, bookcases, potted plants, baskets, water reeds, docks, stone bridges, and signposts were **incorrectly labeled as missing inventory**. They exist in v0.1 pools as **Quality Gaps** (`REAUTHOR_GENERIC`), not missing roles.
- **True Missing Roles Identified:** True missing roles (where zero assets exist anywhere in Greia) are confined to: **Doors & Doorway Dividers**, **Spindle Dining Chairs**, **Tableware (Plates, Teacups, Bowls)**, and **Mechanical/Learning Manipulatives (Gears, Clocks)**.

---

## 2. Comprehensive Classification Breakdown (46 Harvested v0.1 Assets)

| Pool | Total Assets | Preferred Generic | Candidate Generic | Reauthor Generic (Quality Gap) | Specialized Theme | Duplicate / Superseded |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Reading / Classroom v0.1** | 17 | 0 | 3 | 8 | 0 | 6 |
| **Fantasy / Village / Night v0.1** | 15 | 0 | 6 | 4 | 5 | 0 |
| **Water / Pond v0.1** | 14 | 0 | 9 | 4 | 0 | 1 |
| **TOTALS (Harvested v0.1 Pools)** | **46** | **0** | **18** | **16** | **5** | **7** |

---

## 3. Generic Authoring Library Total Inventory Counts

Across the six generic collection TOMLs in `assets/visual/authoring_library/`:

| Collection | Preferred Finished Assets | Candidate Reference Finished Assets | Total Finished Assets | Authoring Ingredients |
| :--- | :---: | :---: | :---: | :---: |
| **Nature & Landscape** | 21 | 6 | **27** | 2 |
| **Interiors & Architecture** | 4 | 6 | **10** | 0 |
| **Furniture & Storage** | 6 | 3 | **9** | 1 |
| **Everyday Props & Containers** | 7 | 3 | **10** | 1 |
| **Making, Learning & Play** | 5 | 3 | **8** | 1 |
| **Lighting, Atmosphere, FX & Shadows** | 9 | 11 | **20** | 0 |
| **TOTALS** | **52** | **32** | **84** | **5** |

*(Total across the generic authoring toolbox: **89 reusable visual resources**)*

---

## 4. True Gaps vs Quality Gaps Audit

### Mandatory Sanity Check Resolutions:
1. **Books & Storybooks:** `QUALITY_GAP` (Exist in `reading.book.stack`, `reading.open.storybook`; need Gouache reauthoring).
2. **Reading Chair / Soft Seating:** `QUALITY_GAP` (Exists in `reading.reading.chair`, `reading.beanbag`).
3. **Potted Indoor Plants:** `QUALITY_GAP` (Exists in `reading.potted.plant`).
4. **Baskets & Containers:** `QUALITY_GAP` (Exists in `reading.toy.basket`).
5. **Water, Reeds & Pond Assets:** `QUALITY_GAP` (Reeds, lily pads, dock, stepping stones exist in `water_pond.v0.1`; ripples and shimmer are candidate references).
6. **Signs, Bridges & Wells:** `QUALITY_GAP` (Bridge, lamppost, signpost, well exist in `fantasy_village_night.v0.1`).
7. **Doors & Room Dividers:** `TRUE_MISSING` (Zero doors exist in any repository pool).
8. **Tableware (Plates, Teacups, Bowls):** `TRUE_MISSING` (Zero plates, teacups, or dining bowls exist).
9. **Mechanical & Learning Manipulatives:** `TRUE_MISSING` (Zero standalone gears or clock faces exist without baked text).

---

## 5. Recommended Next Generic Art-Production Batch

**Batch Name:** `Batch 2026-08-22: Core Generic Gaps & Living Essentials`  
**Target Size:** 16 finished assets addressing the highest-value combination of True Gaps (8 assets), Quality Gaps (7 assets), and Variety Gaps (1 asset):

1. `interior.door.timber_closed` (*TRUE_MISSING* — Closed paneled wooden interior door)
2. `interior.door.timber_ajar` (*TRUE_MISSING* — Open/ajar wooden interior door)
3. `interior.doorway.arch_divider` (*TRUE_MISSING* — Open arched room transition portal)
4. `furniture.seating.chair.spindle_oak` (*TRUE_MISSING* — Classic 4-leg wooden spindle-back dining chair)
5. `furniture.seating.armchair.reading_upholstered` (*QUALITY_GAP* — Reauthors `reading.reading.chair`)
6. `furniture.storage.bookcase.tall_shelves` (*QUALITY_GAP* — Reauthors `reading.tall.bookcase`)
7. `prop.reading.storybook.open_illustrated` (*QUALITY_GAP* — Reauthors `reading.open.storybook`)
8. `prop.reading.books.stack_leaning` (*QUALITY_GAP* — Reauthors `reading.book.stack`)
9. `prop.reading.journal.closed_leather` (*VARIETY_GAP* — Closed leather-bound journal with ribbon)
10. `prop.decor.plant.potted_fern_terracotta` (*QUALITY_GAP* — Reauthors `reading.potted.plant`)
11. `prop.storage.basket.woven_wicker` (*QUALITY_GAP* — Reauthors `reading.toy.basket`)
12. `prop.tableware.plate.ceramic_toast` (*TRUE_MISSING* — Glazed ceramic plate with toast slice)
13. `prop.tableware.teacup.saucer_porcelain` (*TRUE_MISSING* — Porcelain teacup and saucer with warm tea)
14. `prop.tableware.bowl.ceramic_cereal` (*TRUE_MISSING* — Glazed ceramic breakfast/fruit bowl)
15. `play.manipulative.gears.wooden_interlocking` (*TRUE_MISSING* — Pair of interlocking wooden gears)
16. `play.manipulative.clock.wooden_hands` (*TRUE_MISSING* — Wooden teaching clock face with movable hands)