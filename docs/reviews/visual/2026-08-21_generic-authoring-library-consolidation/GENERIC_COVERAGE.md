# Generic Visual Library Coverage & Classification Report

**Date:** 2026-08-21  
**Gate:** Generic Authoring Library Consolidation Gate  
**Reference Runbook:** `docs/testing/2026-08-21_GENERIC_VISUAL_LIBRARY_CONSOLIDATION.md`  
**Parent Taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Authoring Library Path:** `assets/visual/authoring_library/`  
**Evidence Directory:** `docs/reviews/visual/2026-08-21_generic-authoring-library-consolidation/`

---

## 1. Executive Summary & Philosophy Shift

Greia has completed the structural transition from **monolithic themed art packs** to a **generic semantic authoring library**.

Instead of treating historical environment bundles (`Clinic / Care`, `Workshop`, `Reading / Classroom`) as closed silos that force Activity authors to guess where a table or bowl is stored, existing reviewed and promoted art has been organized into six top-level semantic collections indexed by **what the asset is and what role it serves**.

All source SVGs remain in their respective source/provenance bundles without duplication; the generic collections reference them via stable repository paths and clear semantic discovery IDs.

---

## 2. Six Generic Authoring Collections & Inventory Counts

| Collection Index | File Path | Finished Assets | Ingredients | Primary Scope |
| :--- | :--- | :---: | :---: | :--- |
| **Nature & Landscape** | [`nature_landscape.toml`](../../../assets/visual/authoring_library/nature_landscape.toml) | **21** | **2** | Hero oak, birch, sapling, willow, interactive hollow tree, shrubs, ferns, wildflowers, mushrooms, boulders, logs, terrain edges, horizon hills, clouds. |
| **Interiors & Architecture** | [`interiors_architecture.toml`](../../../assets/visual/authoring_library/interiors_architecture.toml) | **9** | **0** | Plaster & wainscot walls, oak plank floors, arched meadow & orchard windows, draped curtains, braided wool & felt heart rugs. |
| **Furniture & Storage** | [`furniture_storage.toml`](../../../assets/visual/authoring_library/furniture_storage.toml) | **9** | **1** | Craftsman workbench, turned stool, wooden daybed, round bedside table, open & cubby shelving, glass-door cabinet, craft crate, pegboard. |
| **Everyday Props & Containers** | [`everyday_props.toml`](../../../assets/visual/authoring_library/everyday_props.toml) | **10** | **1** | Desk lamps (compact & articulated), ceramic pencil mug, paint jars, apothecary bottles, enamel wash basin, paper ream, tufted cushion, pinboard notes. |
| **Making, Learning & Play** | [`making_learning_play.toml`](../../../assets/visual/authoring_library/making_learning_play.toml) | **6** | **1** | Artist easel, birch paint palette, brush bundle, architectural block sets (house & loose), plush caramel teddy bear. |
| **Lighting, Atmosphere, FX & Shadows** | [`lighting_fx_shadows.toml`](../../../assets/visual/authoring_library/lighting_fx_shadows.toml) | **11** | **0** | Nature godrays, wide & narrow window sunbeams, morning fog mist, fireflies, dust motes, falling leaves, care hearts FX, contact shadows (small & wide). |
| **TOTALS** | | **66** | **5** | **71 Total Reusable Semantic Visual Assets** |

---

## 3. Clinic / Care Candidate Disposition

The Clinic / Care 2026-08-21 candidate pool was evaluated on asset-by-asset generic utility:

- **Total Roles Evaluated:** 19 (17 finished assets + 2 authoring ingredients)
- **`GENERIC_INDEX`:** **15** (14 finished assets + 1 ingredient)
  - *Furniture & Interior:* `furniture.bed.daybed.wooden`, `furniture.storage.cabinet.apothecary_glass`, `furniture.table.side.turned_round`, `interior.wall.plaster_mint_beadboard`, `interior.floor.honey_oak_planks`, `interior.window.arch.orchard`, `interior.window.drapery.curtains`, `interior.textile.rug.felt_heart`.
  - *Props, Play & FX:* `prop.container.bottles.apothecary_trio`, `prop.container.basin.enamel_sponge`, `prop.textile.cushion.linen_tufted`, `play.toy.plush.caramel_bear`, `light.window.beam.gentle_morning`, `fx.accent.care_hearts_sparkle`, `prop.ingredient.fabric_patch`.
- **`SPECIALIZED_THEME_ONLY`:** **4** (3 finished assets + 1 ingredient)
  - `clinic.toy.stethoscope`, `clinic.care.kit`, `clinic.bandage.box`, `ingredient.bandage`.
  - *Rationale:* These props represent doctor/first-aid pretend play. While high in craft, they are domain-specific and should not clutter the primary generic catalog; they remain accessible directly in their candidate/theme source pool.
- **`UNRESOLVED`:** **0**

---

## 4. Generic Coverage Gap Analysis & Ranked Next Batch

With 71 generic assets now indexed, clear gaps exist across general Activity authoring needs.

### Ranked Generic Gaps

1. **Doors, Arches & Room Openings (Priority: HIGH)**
   - *Current State:* 0 assets.
   - *Impact:* Indoor activities currently have windows and walls but cannot depict entering/exiting rooms or transitioning between indoor spaces.
   - *Target Assets:* Arched wooden door (open & closed states), timber doorframe with beadboard lintel, curtained doorway opening.
2. **Chairs, Benches & Seating Variety (Priority: HIGH)**
   - *Current State:* Only 1 turned stool and 1 daybed.
   - *Impact:* Dining, reading, and tea-party activities lack standard dining chairs, soft armchairs, and outdoor garden benches.
   - *Target Assets:* Spindle-back wooden chair, upholstered reading armchair, rustic garden bench.
3. **Books, Notebooks & Paper Objects (Priority: HIGH)**
   - *Current State:* Only 1 paper ream and 2 pinboard notes.
   - *Impact:* Educational, storytelling, and study activities lack readable book props.
   - *Target Assets:* Open storybook with illustrated pages, closed leather-bound journal, leaning stack of storybooks.
4. **Tableware, Cups, Plates & Food Containers (Priority: MEDIUM-HIGH)**
   - *Current State:* Only 1 ceramic mug, 1 glass jar set, 1 bottle set, and 1 wash basin.
   - *Impact:* Kitchen, dining, and picnic activities lack basic plates, cups, and bowls.
   - *Target Assets:* Ceramic bowl, plate with toast/apple slice, glass water tumbler, woven wicker picnic basket.
5. **Indoor Potted Plants & Floral Vases (Priority: MEDIUM-HIGH)**
   - *Current State:* 0 indoor plants (only 1 sprout on window sill).
   - *Impact:* Bringing organic warmth and decorative interest into interior room scenes.
   - *Target Assets:* Potted parlor fern in terracotta pot, tabletop succulent in ceramic bowl, glazed ceramic flower vase with daisies.
6. **Simple Mechanical & Crafting Elements (Priority: MEDIUM)**
   - *Current State:* 1 pegboard with tools and 1 wood joint ingredient.
   - *Impact:* Interactive maker activities lack standalone mechanical/crafting manipulatives without baked text.
   - *Target Assets:* Wooden gears (interlocking pair), clock face with adjustable hands, brass lever / switch, wooden measuring ruler.

---

## 5. Recommended Next Generic Art-Production Batch

**Batch Name:** `Batch 2026-08-22: Generic Living & Learning Essentials`  
**Target Output:** 16-18 finished generic assets closing the top 4 gaps:
- 3 Room Openings (Timber door closed, Timber door ajar, Arched doorway divider)
- 3 Seating Objects (Spindle chair, Reading armchair, Garden bench)
- 4 Reading/Paper Props (Open storybook, Closed leather book, Book stack, Open notebook with pencil)
- 4 Tableware/Container Props (Ceramic plate, Teacup & saucer, Cereal bowl, Woven wicker basket)
- 2 Indoor Potted Plants (Potted fern, Tabletop ceramic succulent)