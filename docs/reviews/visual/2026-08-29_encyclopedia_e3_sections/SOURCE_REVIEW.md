# Encyclopedia E3 section-world source review

**Date:** 2026-08-29  
**Repository:** `frozenpepper/Greia` / `main`  
**Evidence class:** **SOURCE / DESKTOP VISUAL REVIEW**  
**Runtime/Simulator acceptance:** **NOT YET CLAIMED**

## Decision entering E3

The owner explicitly approved the corrected golden-master visual direction after direct source repairs to Home, Animals, Lion and Gears, including the final Home correction that centers the complete 3x2 portal block on the open book and deliberately lets the middle column straddle the spine.

That closes the aesthetic-direction gate that had blocked E3. It does **not** make the older E2R Simulator screenshots current evidence for the corrected masters: Home, Animals, Lion and Gears changed after that capture, so fresh runtime PNGs and a fresh Simulator run remain required before claiming exact-final-source runtime visual acceptance.

E4 factual-entry migration remains blocked until the six E3 section worlds have been built, run and reviewed together.

## E3 source set

Animals remains the section-world reference:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

Five E3 section-world masters are on `main`:

```text
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

### Animals

- continuous habitat rather than six generic destination cards;
- lion and elephant were directly repaired after owner rejection and are immediately recognizable at 1024x600;
- existing semantic centers/input geometry remain unchanged;
- Tito remains the runtime canonical presenter.

### Space

- authored dark observatory rather than a bare star field;
- arched observation window, star-chart material, telescope and workbench details;
- intentionally leaves the central stage clear for the existing continuously orbiting Solar System model;
- live planet/Moon geometry remains runtime-owned and dynamic;
- the SVG exposes a non-rendering `data-stage="solar-system"` / `data-bounds` contract paired with literal `SOLAR_SYSTEM_CENTER` / `SOLAR_SYSTEM_STAGE_BOUNDS` in `space.py`, so the source gate can prove every moving subject stays inside the authored observation stage.

### Earth & Nature — v6 reauthoring

The earlier E3 landscape had correct semantics but remained visually too flat. The v6 source pass keeps the same five centers while deepening the landscape into one coherent scene:

- layered far/near hills and foreground shoreline;
- a broad old tree with trunk, branches, layered canopy and contact shadow;
- a larger storm cloud with visible rain curtain;
- **near-layer rain streaks remain in front of the tree canopy** so Rain cannot disappear visually;
- a broad atmospheric rainbow rather than a small symbol;
- a larger cratered volcano with lava, smoke and grounded cone;
- a foreground bay/ocean with shore, foam and wave depth;
- the historical Rain/Tree pointer overlap remains corrected while preserving authored center `(217,203)`.

Existing semantic centers remain:

```text
rain     217,203
tree     210,352
rainbow  475,312
volcano  740,370
ocean    467,504
```

### Body — v6 reauthoring

The earlier Body source still looked too much like a mannequin/medical diagram. The v6 source removes that central mannequin entirely and turns the page into a child-scale hands-on discovery room.

Five physical exhibits now carry the semantics:

- **senses** — sculptural eye + ear models on a curved wooden wall shelf;
- **teeth** — large hinged jaw model with inspection mirror;
- **lungs** — paired-lung model inside a translucent museum case;
- **heart** — tactile oversized heart teaching model on a pedestal;
- **bones** — illuminated skeleton-torso lightbox on the rug.

The room adds hanging warm lights, rug, floor depth, contact shadows and museum furniture without introducing selection cards. All five semantic centers remain unchanged:

```text
senses 250,180
teeth  755,180
lungs  250,405
heart  755,405
bones  505,470
```

Lilli remains the runtime canonical presenter rather than being baked into the SVG.

### Machines — v6 reauthoring

The prior section had the correct object list but still read as symbols pinned to a board. The v6 source keeps the workshop setting while making the five choices physical workshop models:

- **gears** — a mounted **three-gear train with 12-tooth silhouettes and two real mesh zones**;
- **magnet** — hanging horseshoe magnet visibly pulling washers/metal pieces;
- **bicycle** — complete miniature bicycle on a wall rail;
- **airplane** — dimensional model aircraft on a low stand;
- **bridge** — tactile suspension-bridge model spanning a bench base.

A warm task lamp, pegboard depth, real workbench, contact shadows and workshop props make the page read as one room rather than five cards. Existing centers remain:

```text
gears     225,220
magnet    500,190
bicycle   775,220
airplane  335,415
bridge    665,415
```

Dani remains the runtime canonical presenter.

### History — v6 reauthoring

The previous History source had recognizable subjects but still read like five objects sitting on a shelf. The v6 source turns it into one continuous time/excavation trail:

- Jurassic jungle ground supports an unmistakable T-rex silhouette;
- fossil appears embedded in a layered excavation slab with a small digging tool;
- mammoth occupies an ice-age patch rather than floating independently;
- cave painting lives inside a rock/cave alcove;
- pyramid sits in a desert patch with grounded sand;
- a continuous layered trail visually links all five eras.

The five explicit centers remain:

```text
dinosaurs       145,345
fossils         315,345
mammoth         485,345
cave_paintings  655,345
pyramids        825,345
```

Leo remains the runtime canonical presenter.

## v6 desktop source review

The maintainer-local six-section contact sheet is now:

```text
encyclopedia_e3_section_source_contact_v6.png
```

Evidence class remains **SOURCE / DESKTOP VISUAL REVIEW** only.

Compared with v5, the v6 sheet materially improves the weakest pages:

```text
Earth     richer layered landscape; rain stays readable in front of tree
Body      mannequin removed; five physical exhibits in a discovery room
Machines  workshop models; three unmistakably toothed meshing gears
History   continuous time/excavation scene rather than shelf objects
```

Animals and Space remain unchanged in this pass because their current section-source compositions are still the stronger references for their respective roles.

A local static audit of the four changed v6 masters confirmed:

```text
SVG semantic-center metadata == expected page centers
render size = 1024x600
render mode = RGB
```

This audit is not a substitute for repository tests or Simulator evidence.

## Focus/input contracts

The source/runtime geometry protections remain unchanged by the v6 art pass.

`tests/test_activity_enciclopedia_visual_foundation.py` compares SVG `data-target` / `data-center` metadata with actual page input geometry for:

```text
Home
Animals
Earth & Nature
Body
Machines
History
```

Space remains dynamic and instead uses the authored Solar-System stage-bounds contract.

`tests/test_encyclopedia_section_hit_geometry.py` guards the static E3 selection regions:

- Earth, Body, Machines and History regions stay inside the 1024x600 logical surface;
- each page's target rectangles remain pairwise non-overlapping;
- Body/Machines retain large authored-object footprints rather than old 86x86 prototype hotspots;
- Earth Rain/Tree cannot regress to overlap;
- authored pages use `draw_focus_patch(...)` while the old rectangular `focus_ring(...)` remains only for fail-soft procedural rendering.

`tests/test_encyclopedia_focus_treatment.py` pins the non-occluding perimeter halo, Earth's duplicate-focus-dot removal, opaque authored-scene loading, and the build-time RGB rendition contract.

## Exact-source Simulator evidence contract

The E3 runtime review remains source-bound and fail-closed.

Before the first Simulator session, every one of the eleven expected runtime PNGs must satisfy:

```text
file exists in the working tree
file exists in the exact captured HEAD
working bytes == committed HEAD blob bytes
```

The capture harness records:

```text
source-sha.txt
capture-manifest.json
runtime_art_sha256       # all 11 PNGs
runtime_art_git_blobs    # all 11 PNGs
```

and fails if source, working-tree state, runtime-art hashes or committed blob identities change during the seven-session capture.

The review builder accepts only a complete `PASS` manifest for exactly:

```text
Home
Animals
Space
Earth & Nature
Body
Machines
History
```

Canonical protocol:

```text
docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md
```

## Runtime staging state

The five E3 pages remain wired through the existing bounded `VisualLibrary`. Missing runtime section PNGs still fail soft to the retained procedural renderers.

The authoring build tool supports:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

and equivalent `--check --group ...` verification.

The runtime contract remains:

```text
golden runtime pack     6 / 6
E3 section runtime pack 0 / 5 or 5 / 5 — never partial
final E3 runtime gate   exact 11 / 11 committed PNGs
```

The previous maintainer-local staging ZIP is now superseded. A new v6 recoverability bundle was produced after the four source reauthorings:

```text
ENCYCLOPEDIA_E3_RUNTIME_ART_STAGING_V6_2026-08-29.zip
```

It contains the nine changed/new renditions (four corrected golden masters + five E3 section worlds) with one authoritative manifest. Saturn and Pyramids are intentionally omitted because their accepted Git runtime blobs are unchanged. The staging ZIP is **not** Simulator acceptance and cannot bypass the exact-committed-art gate.

## Current gate

```text
E1 visual architecture                         COMPLETE
E2/E2R owner visual direction                  APPROVED
E3 six-section source direction                V6 SOURCE-REVIEWED / FROZEN
E3 static visual/input geometry contract       IMPLEMENTED
E3 Space live-stage geometry contract          IMPLEMENTED
E3 static hit-region non-overlap contract      IMPLEMENTED
E3 non-occluding scene focus treatment         IMPLEMENTED
E3 exact-source + committed-art provenance     IMPLEMENTED
E3 v6 nine-image local runtime staging         READY / NOT ACCEPTANCE
complete 11-PNG committed runtime pack         PENDING
build --check / focused current-checkout tests PENDING
fresh exact-SHA real Greia Simulator           PENDING
Home + six-section runtime review              PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until the six section pages are rendered through the real Greia runtime and reviewed together.
