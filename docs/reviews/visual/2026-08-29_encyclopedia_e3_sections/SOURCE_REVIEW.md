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
- live planet/Moon target geometry remains runtime-owned and dynamic;
- the SVG now exposes a non-rendering `data-stage="solar-system"` / `data-bounds` rectangle, paired with literal `SOLAR_SYSTEM_CENTER` / `SOLAR_SYSTEM_STAGE_BOUNDS` in `space.py`, so the static source gate can prove that every moving planet, marker and Moon excursion fits inside the authored observation stage.

### Earth & Nature

- one continuous layered landscape, not destination cards;
- rain cloud, tree, rainbow, volcano and ocean are distinct physical features of the same world;
- the rain artwork received a second source pass because the tree canopy hid too much of the rain; near-layer rain streaks now keep the concept readable;
- a later input review found the Rain and Tree pointer rectangles overlapped by 18 pixels; the Rain hit region was shortened while preserving the same authored center `(217,203)`, so the two regions now meet cleanly instead of resolving part of the visible tree to Rain;
- the extra floating yellow corner dot from the prototype focus treatment was removed; authored selection now relies on the shared non-occluding halo only;
- authored subject placement follows the destination semantics exactly;
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

The section contact sheets and follow-up runtime-source review exposed weaknesses before final runtime capture:

```text
Body      too schematic / too close to a mannequin diagram
Machines  miniature gears too simplified / bridge too weak
History   dinosaur silhouette ambiguous
Earth     rain cue too hidden behind the tree canopy
Earth     Rain and Tree pointer regions overlapped
E3 focus  translucent filled patch still washed authored objects toward UI cards
Earth     extra floating yellow focus dot duplicated the selection cue
```

Those were corrected before runtime acceptance. The current six-section source family now passes the intended first recognizability/composition check:

```text
Animals          coherent continuous habitat, corrected lion + elephant
Space            observatory context supports rather than replaces live orbits
Earth & Nature   five destinations read as one landscape; rain remains visible
Body             friendly discovery room with physical learning props
Machines         recognizable mechanisms/objects; gears visibly mesh
History          T-rex/fossil/mammoth/cave/pyramid sequence readable
```

The current maintainer-local contact sheet is `encyclopedia_e3_section_source_contact_v5.png`; it is source-review evidence only and is deliberately not committed as Simulator evidence.

A later local focus-treatment preview was also inspected against the actual Earth/Body/Machines/History authored PNGs. The shared focus treatment now draws only two elliptical perimeter strokes on a transparent overlay. It does **not** paint a translucent filled rectangle over the exhibit, so the authored subject retains its own color, texture and depth. That preview remains **SOURCE / DESKTOP VISUAL REVIEW**, not Simulator evidence.

## Geometry and focus contracts

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

Space cannot use fixed target centers because its Sun, planets and Moon move continuously. Instead, the same suite compares the authored Solar-System stage bounds with literal runtime geometry and proves the maximum visible extent of every orbiting subject remains inside that stage.

`tests/test_encyclopedia_section_hit_geometry.py` separately guards the static E3 selection regions:

- Earth, Body, Machines and History regions remain inside the 1024×600 logical surface;
- each family is pairwise non-overlapping, preventing ambiguous pointer resolution;
- Body/Machines keep deliberately generous authored-object footprints instead of regressing to the old 86×86 prototype hotspots;
- all four authored pages use `draw_focus_patch(...)` when the authored scene is present, while the old rectangular `focus_ring(...)` remains only as fail-soft procedural-state treatment.

`tests/test_encyclopedia_focus_treatment.py` now pins the visual implementation detail that matters here:

- `draw_focus_patch(...)` is outline-only and uses ellipse strokes rather than a filled rectangular overlay;
- the historical translucent yellow fill cannot silently return;
- Earth does not add a second floating corner dot on top of the shared authored focus cue.

This keeps runtime focus visually integrated with the scene rather than reintroducing generic UI cards over authored illustrations.

## Exact-source Simulator evidence contract

The E3 runtime review is source-bound rather than relying on manually transcribed SHAs.

`tools/encyclopedia_v01_section_review_capture.py` now requires a fully clean checkout including untracked files, except for paths ignored by repository policy such as `tmp/`. It records starting `HEAD`, SHA-256 for every Encyclopedia runtime PNG, and the Git blob ID for every runtime PNG committed in that `HEAD`.

Before the first Simulator session, every one of the eleven expected runtime PNGs must therefore satisfy both:

```text
file exists in the working tree
working-tree bytes == committed HEAD blob bytes
```

This closes the loophole where an untracked or merely staged five-PNG E3 pack could otherwise be captured and incorrectly attributed to a Git SHA that did not actually contain those binaries.

The capture then runs exactly Home + the six sections and fails if source, runtime-art hashes, or committed runtime-art blob identities change during capture. It writes:

```text
source-sha.txt
capture-manifest.json
```

The manifest records source SHA, locale, viewport, interface size, selected/completed jobs, runtime-art SHA-256 values, runtime-art Git blob IDs and status.

`tools/encyclopedia_v01_section_review.py` accepts only a `PASS` manifest with exactly the seven required jobs, the complete eleven-PNG art inventory, and valid Git blob IDs for all eleven files, and preserves that provenance beside the curated screenshots/contact sheet.

`tests/test_encyclopedia_e3_review_tools.py` pins that evidence contract without launching Pygame.

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

A recoverable maintainer-local nine-file runtime-art staging bundle also exists outside the repository. It contains the four changed golden-master PNGs plus the five E3 section PNGs; Earth and Body were refreshed to the latest source-reviewed renders after the earlier staging bundle was found stale. This staging bundle is explicitly **not** acceptance evidence and is not allowed to satisfy the exact-committed-art capture precondition.

## Current gate

```text
E1 visual architecture                         COMPLETE
E2/E2R owner visual direction                  APPROVED
latest corrected E2 runtime PNG rebuild        STAGED LOCALLY / NOT COMMITTED
latest corrected E2 exact-SHA Simulator proof  PENDING
E3 six-section source direction                IMPLEMENTED / SOURCE-REVIEWED
E3 static visual/input geometry contract       IMPLEMENTED
E3 Space live-stage geometry contract          IMPLEMENTED
E3 static hit-region non-overlap contract      IMPLEMENTED
E3 non-occluding scene focus treatment         IMPLEMENTED
E3 exact-source + committed-art provenance      IMPLEMENTED
E3 five new runtime PNGs                       STAGED LOCALLY / NOT COMMITTED
E3 six-section Simulator/contact-sheet review  PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until the six section pages are rendered through the real Greia runtime and reviewed together.
