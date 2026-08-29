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

Five new section-world masters were authored on `main`:

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
- authored subject placement follows the existing destination hit regions closely;
- Tito remains the runtime canonical presenter.

### Body

- one warm discovery room with a central friendly body figure;
- senses uses a hanging eye/ear chart;
- tooth/dental mirror, lungs model, heart model and bone/x-ray object are physical exhibits rather than five generic UI cards;
- existing semantic target centers remain unchanged;
- Lilli remains the runtime canonical presenter.

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
- Leo remains the runtime canonical presenter.

## Source review findings

A first six-section source contact sheet exposed three weaknesses before runtime integration:

```text
Body      too many panel-like stations
Machines  miniature gears too simplified / bridge too weak
History   dinosaur silhouette ambiguous
```

Those were corrected before the source masters were persisted. The revised source contact sheet now passes the intended first recognizability/composition check:

```text
Animals          coherent continuous habitat, corrected lion + elephant
Space            observatory context supports rather than replaces live orbits
Earth & Nature   five destinations read as one landscape
Body             physical discovery-room exhibits, not five UI cards
Machines         recognizable mechanisms/objects; gears visibly mesh
History          T-rex/fossil/mammoth/cave/pyramid sequence readable
```

The contact sheet itself is maintainer-local source-review evidence and is not committed as Simulator evidence.

## Staged runtime integration

The five E3 pages are wired to authored semantic IDs through the existing bounded `VisualLibrary`. Until the generated E3 PNG tranche is present, each page deliberately fails soft to its retained procedural rendering.

The authoring build tool now has explicit groups:

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
E3 five new runtime PNGs                       PENDING
E3 six-section Simulator/contact-sheet review  PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until the six section pages are rendered through the real Greia runtime and reviewed together.
