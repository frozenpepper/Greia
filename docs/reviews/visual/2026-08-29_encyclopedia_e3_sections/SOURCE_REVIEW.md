# Encyclopedia E3 section-world source review

**Date:** 2026-08-29  
**Repository:** `frozenpepper/Greia` / `main`  
**Evidence class:** **SOURCE / DESKTOP VISUAL REVIEW**  
**Runtime/Simulator acceptance:** **NOT YET CLAIMED**

## Decision entering E3

The owner explicitly approved the corrected golden-master **visual direction** after direct source repairs to Home, Animals, Lion and Gears, including the final Home correction that centers the complete 3×2 portal block on the open book and deliberately lets the middle column straddle the spine.

That closes the aesthetic-direction gate that had blocked E3. It does **not** make the older E2R Simulator screenshots current evidence for the corrected masters: Home, Animals, Lion and Gears changed after that capture, so fresh runtime PNGs and a fresh Simulator run remain required before claiming exact-final-source runtime visual acceptance.

E4 factual-entry migration remains blocked until the six E3 section worlds have been built, run and reviewed together.

## E3 source set

Animals remains the section-world reference and already has its corrected authored master:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

Five new section-world masters are now authored on `main`:

```text
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

### Space

- authored dark observatory rather than a bare star field;
- arched observation window, star-chart material, telescope, compass/workbench details;
- intentionally leaves the central stage clear for the existing continuously orbiting Solar System model;
- live planet/Moon target geometry remains runtime-owned and dynamic.

### Earth & Nature

- one continuous layered landscape, not destination cards;
- rain cloud, tree, rainbow, volcano and ocean are distinct physical features of the same world;
- the rain target received a second source pass after review because the tree canopy hid too much of the rain; near-layer rain streaks now keep the concept readable without changing its hit region;
- authored subject placement follows the existing destination hit regions exactly;
- Tito remains the runtime canonical presenter.

### Body

The first E3 Body draft was still too close to a mannequin/schematic and was revised again before runtime acceptance.

The current source is a warm child-scale discovery room:

- a friendly central wooden/cloth explorer figure provides body context without acting as a medical diagram;
- **senses** is a framed eye-and-ear learning board;
- **teeth** is an oversized jaw/tooth model with inspection mirror;
- **lungs** is a tactile paired-lung model on a low stool;
- **heart** is an oversized museum-style heart model on a small pedestal;
- **bones** is an illuminated x-ray-style discovery box on the floor;
- all five existing semantic target centers remain unchanged;
- Lilli remains the runtime canonical presenter.

This correction specifically addresses the visual-plan requirement that Body feel like a friendly anatomy discovery room rather than a medical mannequin diagram or five generic UI cards.

### Machines

- one workshop/pegboard/workbench scene;
- real toothed meshing gear pair, horseshoe magnet, recognizable bicycle, airplane and suspension-bridge model;
- objects sit in the workshop rather than inside identical selection bubbles/cards;
- existing semantic centers remain unchanged;
- Dani remains the runtime canonical presenter.

### History

- one continuous museum/excavation time trail;
- T-rex silhouette was explicitly revised after the first source review because the initial draft was not recognizable enough;
- fossil slab, mammoth, cave-painting fragment and pyramid mini-diorama remain distinct at 1024×600;
- existing left-to-right semantic chronology is preserved;
- the five target centers are now explicit page constants rather than implicit arithmetic, so source metadata and pointer geometry can be compared directly;
- Leo remains the runtime canonical presenter.

## Source review findings

The section contact sheets exposed weaknesses before runtime integration:

```text
Body      too schematic / too close to a mannequin diagram
Machines  miniature gears too simplified / bridge too weak
History   dinosaur silhouette ambiguous
Earth     rain cue too hidden behind the tree canopy
```

Those were corrected in source. The current six-section source family now passes the intended first recognizability/composition check:

```text
Animals          coherent continuous habitat, corrected lion + elephant
Space            observatory context supports rather than replaces live orbits
Earth & Nature   five destinations read as one landscape; rain remains visible
Body             friendly discovery room with physical learning props
Machines         recognizable mechanisms/objects; gears visibly mesh
History          T-rex/fossil/mammoth/cave/pyramid sequence readable
```

The current maintainer-local contact sheet is `encyclopedia_e3_section_source_contact_v5.png`; it is source-review evidence only and is deliberately not committed as Simulator evidence.

## Geometry contract

E3 now carries the same visual/input alignment protection that caught the earlier Home drift.

`tests/test_activity_enciclopedia_visual_foundation.py` compares SVG `data-target` / `data-center` metadata with the actual page input geometry for:

```text
Home
Animals
Earth & Nature
Body
Machines
History
```

Space is intentionally excluded from the static-center check because its Sun, planets and Moon move continuously and runtime owns those positions.

This means an authored object cannot silently move away from the region that receives pointer/controller focus without breaking the focused source contract.

## Staged runtime integration

The five E3 pages are wired to authored semantic IDs through the existing bounded `VisualLibrary`. Until the generated E3 PNG tranche is present, each page deliberately fails soft to its retained procedural rendering.

The authoring build tool has explicit groups:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

and equivalent `--check --group ...` verification.

The source contract requires:

```text
golden runtime pack     6 / 6 when runtime art exists
E3 section runtime pack 0 / 5 or 5 / 5 — never partial
```

This allows source integration to advance without pretending missing generated images are current runtime evidence.

## Current gate

```text
E1 visual architecture                         COMPLETE
E2/E2R owner visual direction                  APPROVED
latest corrected E2 runtime PNG rebuild        PENDING
latest corrected E2 exact-SHA Simulator proof  PENDING
E3 six-section source direction                IMPLEMENTED / SOURCE-REVIEWED
E3 static visual/input geometry contract       IMPLEMENTED
E3 five new runtime PNGs                       PENDING
E3 six-section Simulator/contact-sheet review  PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until the six section pages are rendered through the real Greia runtime and reviewed together.
