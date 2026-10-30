# Greia Encyclopedia workstream handover

**Updated:** 2026-08-30  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Frozen scope:** **43 / 43 planned executable pages**  
**Last real-Simulator visual SHA:** `03bf76acb3e4c3f6d40b346d510f55a4763efc2d` — E3 ACCEPTED (11-PNG runtime pack, 7/7 Simulator sessions); evidence HEAD `69cf8966199896dfef38394e67d49cd993920258`  
**Current state:** **E1 COMPLETE / E2/E2R APPROVED / E3 COMPLETE / ACCEPTED at 03bf76ac / E4 UNBLOCKED / NEXT / NARRATION SEPARATE**

This is the short Encyclopedia continuation contract. Historical detail remains in `encyclopedia/PROGRESS.md`, Git history, and dated reviews.

---

## 1. Frozen product/runtime scope

Exactly:

```text
1 Home
6 section pages
36 factual entries
43 executable pages total
```

The factual entry IDs remain frozen by `encyclopedia/pages/catalogue.py` and the runtime page registry. Visual work is not permission to change the information architecture.

Preserve:

- thin `main.py` composition root;
- `enciclopedia_engine.py` lifecycle/registry/semantic-input/internal-navigation authority;
- subject behavior in page modules/models;
- Greia-owned protected Home, separate from Encyclopedia internal Back;
- Italian + English initial locales;
- offline/low-resource child runtime;
- no runtime AI/LLM, speech recognition, TTS, network factual lookup or CairoSVG;
- authoring-time prerecorded speech only;
- bounded caches;
- no page-hot-path disk decode/smoothscale;
- fail-soft procedural fallback for missing authored renditions;
- opaque RGB full-screen scene PNGs, with transparent canonical characters remaining on the shared alpha-aware character path.

Older evidence already proves the mechanical foundation:

```text
43 / 43 page reachability
36 / 36 entry semantic ACTIVATE delivery
36 / 36 internal Back returns
protected Greia Home -> Shell
continuous real-Shell lifecycle
```

That evidence is mechanical only; it does not prove the current visual files.

---

## 2. Golden-master direction — OWNER APPROVED

The original E2/E2R pixels were technically functional but visually rejected. The primary agent then repaired the real source assets directly:

```text
Home      enlarged book; complete 3x2 category block centered on whole book
          x = 267 / 512 / 757; middle column deliberately crosses spine
Animals   recognizable full-body lion and elephant
Lion      unified head/face/mane; connected tail and load-bearing legs
Gears     unmistakable toothed gear train with real mesh points
```

The owner reviewed those direct repairs and explicitly approved moving forward.

```text
E1 visual/asset architecture        COMPLETE
E2/E2R visual direction             OWNER APPROVED
E3 section-world source family      V6 SOURCE-REVIEWED / FROZEN
E3 exact-current runtime review     ACCEPTED at 03bf76ac (11/11 PNGs, 7/7 Simulator, 59/59 tests, verify PASS)
E4 factual-entry migration          UNBLOCKED / NEXT
```

Primary repair review:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md (archived; see git history)
```

---

## 3. E3 six-section source family — v6

Section masters:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

Current family:

```text
Animals          continuous habitat; corrected lion + elephant
Space            observatory around existing live Solar System
Earth & Nature   layered weather/tree/rainbow/volcano/bay landscape
Body             hands-on discovery room with no central mannequin
Machines         real workshop with physical teaching models
History          continuous jungle/dig/ice-age/cave/desert time trail
```

The v6 pass deliberately reauthored the four weaker section pages again rather than accepting visually flat source merely because contracts were green.

### Earth & Nature v6

- deeper far/near/foreground landscape;
- broad old tree with readable trunk/branches/canopy;
- storm cloud + rain curtain;
- near-layer rain stays visible **in front of** the tree canopy;
- broad rainbow;
- larger grounded cratered volcano with lava/smoke;
- foreground bay with shore/foam/wave depth;
- semantic centers unchanged.

### Body v6

- removed central mannequin entirely;
- senses = sculptural eye + ear;
- teeth = hinged jaw + inspection mirror;
- lungs = paired model in translucent case;
- heart = tactile teaching model on pedestal;
- bones = illuminated skeleton-torso lightbox;
- room gains hanging warm lights, rug, furniture and contact depth;
- semantic centers unchanged.

### Machines v6

- physical workshop/pegboard/workbench;
- mounted **three-gear toothed train with two visible mesh zones**;
- horseshoe magnet visibly attracts metal pieces;
- complete bicycle model;
- model airplane on stand;
- tactile suspension-bridge model;
- semantic centers unchanged.

### History v6

- one continuous environment rather than shelf objects;
- Jurassic T-rex patch;
- layered fossil dig + tool;
- ice-age mammoth patch;
- cave-painting rock alcove;
- desert pyramid patch;
- semantic centers unchanged.

Source-review authority:

```text
SOURCE_REVIEW.md (archived; see git history)
```

Current maintainer-local contact sheet:

```text
encyclopedia_e3_section_source_contact_v6.png
```

Evidence class: **SOURCE / DESKTOP VISUAL REVIEW** only.

A local static audit of the four v6 reauthorings confirmed expected SVG target-center metadata and 1024x600 RGB direct renders. This is not a repository-test or Simulator PASS.

---

## 4. Runtime integration and geometry/focus contracts

Five new section semantic IDs are registered in the existing bounded `VisualLibrary`; the page modules are source-wired to them.

Space keeps the continuously orbiting Sun/planets/Moon as the true teaching model; authored art supplies observatory context only.

Until section PNGs exist, pages retain their proven procedural fallback.

Contracts protect the migration:

- Home/Animals/Earth/Body/Machines/History SVG target centers equal actual input geometry;
- Earth/Body/Machines/History static pointer regions remain in-bounds and pairwise non-overlapping;
- Earth Rain/Tree cannot regress to overlap;
- Body/Machines use generous authored-object regions rather than old 86x86 hotspots;
- Space uses authored Solar-System stage bounds proving complete live body extents fit the observatory;
- History centers are explicit constants;
- authored section selection uses a non-occluding perimeter halo via `draw_focus_patch(...)`;
- Earth has no duplicate floating focus dot;
- Space's selected live body owns focus while its text plaque remains secondary.

Relevant tests:

```text
tests/test_activity_enciclopedia_visual_foundation.py
tests/test_encyclopedia_section_hit_geometry.py
tests/test_encyclopedia_focus_treatment.py
```

---

## 5. Runtime-art build/performance contract

All eleven authored scene renditions are flattened 1024x600 opaque RGB backdrops.

`VisualLibrary.art()` uses display-optimized `Surface.convert()` for scenes. Canonical character sprites keep `convert_alpha()` because their silhouettes require transparency.

Builder:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

Equivalent `--check` modes validate:

```text
valid PNG
1024x600 exact dimensions
PNG color type 2 / opaque RGB
byte-for-byte equality with rebuild from committed SVG
```

Inventory contract:

```text
golden tranche     6 / 6
E3 section tranche 0 / 5 or 5 / 5; never partial
final E3 gate       exact 11 / 11 committed PNGs
```

---

## 6. v6 runtime-art staging recovery path

The old staging ZIP is superseded because it carried earlier Body/Earth renders and stale duplicate metadata.

Current recoverability bundle outside the repo:

```text
ENCYCLOPEDIA_E3_RUNTIME_ART_STAGING_V6_2026-08-29.zip
```

It contains the nine changed/new renditions:

```text
Home / Animals / Lion / Gears
Space section / Earth v6 / Body v6 / Machines v6 / History v6
```

Saturn + Pyramids are intentionally omitted because their accepted Git runtime blobs are unchanged.

Maintainer-only helper and regression source:

```text
tools/import_encyclopedia_runtime_art_staging.py
tests/test_encyclopedia_runtime_art_staging.py
```

The importer fails closed on:

- unsafe paths/symlinks;
- legacy/duplicate manifests;
- missing/extra PNGs;
- SHA/byte/dimension/mode mismatch;
- bad/non-RGB PNGs;
- missing preserved Saturn/Pyramids;
- unexpected runtime files;
- final inventory other than exact 11/11.

It validates the complete payload before writing, then replaces only the nine changed/new targets using temporary files + `os.replace`.

**This is recovery tooling, not an alternate authority.** After import:

```bash
python3 tools/build_encyclopedia_visual_assets.py --check --group all
```

is mandatory. Any mismatch means stop and rebuild normally; never weaken the source comparison to preserve staged bytes.

---

## 7. Exact-SHA real-Simulator gate

Canonical protocol:

```text
2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md (archived; see git history)
```

Capture/review tools:

```text
tools/encyclopedia_v01_section_review_capture.py
tools/encyclopedia_v01_section_review.py
```

Bounded runtime family:

```text
Home
Animals
Space
Earth & Nature
Body
Machines
History
```

Capture requires:

- clean checkout including non-ignored untracked files;
- exact 11 runtime PNGs;
- every PNG already committed in the exact captured `HEAD`;
- working bytes equal the committed `HEAD:<path>` Git blob;
- manifest records exact source SHA, SHA-256 and Git blob ID for all 11 assets;
- HEAD/status/hash/blob inventories unchanged across all seven sessions;
- each page launched through real Greia Shell/profile/catalogue route;
- protected Greia Home return exercised.

The review builder refuses incomplete, non-PASS, wrong-SHA, non-11-art or non-Git-bound evidence.

Old E2R screenshots do not prove current v6 source.

---

## 8. Current hard gate

```text
E1 visual architecture                         COMPLETE
E2/E2R owner visual direction                  APPROVED
E3 six-section source family                   V6 SOURCE-REVIEWED / FROZEN
E3 geometry/stage/input contracts              IMPLEMENTED
E3 non-occluding authored focus                IMPLEMENTED
E3 opaque-scene runtime/build contract         IMPLEMENTED
E3 staging importer + regression source        IMPLEMENTED
E3 v6 nine-image recoverability bundle         READY / NOT ACCEPTANCE
complete 11-PNG committed runtime pack         COMPLETE (11/11 at 03bf76ac, committed at 69cf8966)
build --check on exact current 11-art pack      PASS
focused current-checkout tests                 PASS (59/59)
make verify                                    PASS at accepted SHA
fresh exact-SHA real Greia Simulator           PASS (7/7 sessions, Home+6)
Home + six-section runtime contact review      ACCEPTED
E4 factual-entry migration                     UNBLOCKED / NEXT
```

E3 is ACCEPTED per `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (archived; see git history) (Disposition: ACCEPTED, SHA 03bf76ac, 11/11 SHA-256, 11/11 Git blobs, visual ACCEPTED). Do not rerun E3 merely because unrelated Activities changed.

---

## 9. Local-agent and narration boundaries

The owner explicitly asked the primary agent to perform current visual-authoring work directly. Local agents do not take this Encyclopedia visual work (the old local-agent work order stays on HOLD and was archived 2026-10-30) unless the owner explicitly changes that instruction.

Narration remains separate:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Only owner-listened `OWNER_ACCEPTED` clips may integrate. This visual lane does not generate or integrate narration.

---

## 10. Next exact action

E3 is ACCEPTED; E4 is UNBLOCKED but deferred per `GREIA_POST_ACTIVITY_PASS_R7_ACCEPTANCE_AGENT_INSTRUCTIONS_2026-08-30.md` until post-activity-pass R7 acceptance window ends.

```text
E1 COMPLETE
E2/E2R APPROVED
E3 COMPLETE / ACCEPTED at 03bf76ac (evidence HEAD 69cf8966)
  11/11 runtime art PASS, 59/59 focused tests PASS, verify PASS, 7/7 Simulator PASS, 11/11 SHA-256, 11/11 Git blobs, visual ACCEPTED
E4 UNBLOCKED / NEXT — do not start until this acceptance window ends and owner explicitly authorizes
```

Current post-activity-pass acceptance SHA is e2b831da (Activity modernization COMPLETE, source gate green, Simulator 5/5 final Activity decompositions PASS, focused R7.2/R7.3 PASS; physical Acer INCOMPLETE due to no hardware in this environment). See `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (archived; see git history).
