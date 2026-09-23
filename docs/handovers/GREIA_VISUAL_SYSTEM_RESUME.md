# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-30  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current Activity visual subplan:** `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`  
**Current E3 source review:** `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md`  
**E3 runtime gate:** `docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md`  
**Visual-authoring skill:** `skills/greia-visual-authoring/SKILL.md`

---

# 1. Current focus — Encyclopedia E3 runtime closure

The owner rejected the earlier Encyclopedia/E2R pixels, then directly reviewed the primary-agent source repairs to Home, Animals, Lion and Gears.

The final Home correction enlarged the book and centered the complete 3×2 category block on the book as one composition:

```text
column centers x = 267 / 512 / 757
middle Space/Machines column deliberately straddles the x=512 spine
```

After inspecting the corrected source direction, the owner explicitly approved moving forward with the visual-reauthoring plan.

The subsequent E3 section-family source review reached **v6** after the primary agent rejected its own flatter Body/Earth/Machines/History v5 designs and reauthored those four pages again.

Current disposition:

```text
E1 visual/asset architecture            COMPLETE
E2/E2R visual direction                 OWNER APPROVED
E3 six-section source direction         V6 SOURCE-REVIEWED / FROZEN
E3 target geometry/stage contracts      HARDENED
E3 focus treatment                      NON-OCCLUDING HALO / SOURCE-REVIEWED
E3 runtime scene surface policy         OPAQUE FULL-SCREEN SCENES OPTIMIZED
E3 staging-import recovery path         IMPLEMENTED / MAINTAINER-ONLY
E3 evidence-integrity tooling           HARDENED
E3 committed 11-PNG runtime pack        COMPLETE at 03bf76ac (evidence HEAD 69cf8966)
E3 exact-SHA Simulator review           ACCEPTED (7/7 sessions, 11/11 SHA-256, 11/11 Git blobs)
E4 factual-entry migration              UNBLOCKED / NEXT (deferred per post-activity-pass protocol)
```

E3 is ACCEPTED per `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (Disposition: ACCEPTED, SHA 03bf76ac, visual ACCEPTED). Do not rerun E3 merely because unrelated Activities changed.

---

# 2. E1 architecture to preserve

Activity-local source owners:

```text
activities/enciclopedia_greia/enciclopedia_presentation.py
activities/enciclopedia_greia/enciclopedia_services.py
```

Preserve:

```text
PageShellLayout safe zones
bounded VisualLibrary
explicit semantic-id -> runtime PNG mapping
source SVG -> authoring-time PNG build
no runtime SVG
no page-hot-path image decode / smoothscale
semantic PageCommand input
protected Greia Home ownership
fail-soft missing authored renditions
```

The visual migration is not permission to invent a second compositor/cache/navigation system.

---

# 3. Owner-approved golden-master repairs on main

Direct corrections include:

```text
Home      oversized open book + centered 3x2 portal block
Animals   recognizable full-body lion and elephant
Lion      unified face/head/mane, attached tail, connected visible legs
Gears     real toothed three-gear train with actual mesh points
```

Primary correction record:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
```

The owner asked the primary agent to perform this visual work directly. Do not hand the current aesthetic-authoring lane to the local agent.

---

# 4. E3 six-section source family — v6

Animals remains the section-world reference:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

Section masters:

```text
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

Current family:

```text
Animals          continuous habitat; corrected lion + elephant
Space            authored observatory around the live Solar System
Earth & Nature   layered landscape; storm/tree/rainbow/volcano/bay
Body             hands-on discovery room; no central mannequin
Machines         real workshop with physical teaching models
History          continuous time/excavation trail rather than shelf objects
```

The v6 pass specifically corrected the remaining source-quality issues:

```text
Earth     deeper landscape; rain curtain remains visible in front of tree
Body      mannequin removed; five physical museum-style exhibits
Machines  physical workbench; three clearly toothed gears visibly mesh
History   jungle -> dig -> ice age -> cave -> desert continuous trail
```

All four reauthored v6 pages preserved their existing semantic centers. A local static audit confirmed their SVG target metadata still equals the page centers and their direct renders remain 1024×600 RGB. This is source evidence only.

Current source review:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

Current maintainer-local six-section contact sheet:

```text
encyclopedia_e3_section_source_contact_v6.png
```

Evidence class: **SOURCE / DESKTOP VISUAL REVIEW** only.

---

# 5. E3 runtime integration, geometry and focus

`VisualLibrary.ART_ASSETS` registers the five E3 semantic IDs in addition to the six golden-master assets.

The five pages are source-wired:

```text
space.py      encyclopedia.space.gallery.observatory
earth.py      encyclopedia.earth.gallery.landscape
body.py       encyclopedia.body.gallery.discovery_room
machines.py   encyclopedia.machines.gallery.workbench
history.py    encyclopedia.history.gallery.time_trail
```

Behavior while generated E3 PNGs are absent:

- each page deliberately falls back to its previous proven procedural rendering;
- no runtime SVG or source scan occurs;
- semantic destinations/input/page IDs remain unchanged;
- Space always retains its live orbiting Sun/planets/Moon model; the authored scene is only the observatory context.

Static source/input alignment is machine-checkable for Home, Animals, Earth, Body, Machines and History through SVG `data-target`/`data-center` metadata and focused tests.

Space is runtime-dynamic, so it uses an authored **Solar System stage contract** instead of fake fixed target centers. The observatory SVG carries `data-stage="solar-system"` bounds, `space.py` exposes matching literal center/stage constants, and the visual-foundation test proves the full moving planet discs, Saturn ring/marker margin and Moon excursion remain inside that stage.

Body and Machines use generous exhibit/object pointer regions instead of the old uniform 86×86 prototype hotspots. History target centers are explicit constants. Earth Rain/Tree regions are disjoint.

Authored Earth/Body/Machines/History selection uses `draw_focus_patch(...)`, a transparent perimeter halo rather than a filled card-like overlay. The older rectangular `focus_ring(...)` remains only for procedural fail-soft presentation. Space's moving selected subject owns its focus; its bottom label remains neutral.

All eleven authored scene renditions are flattened opaque full-screen RGB assets. `VisualLibrary.art()` uses display-optimized `Surface.convert()` for those scenes. Canonical character sprites continue to use `convert_alpha()` because their transparent silhouettes require it.

Build groups:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

The corresponding `--check` path validates size/color type and verifies committed renditions byte-for-byte against rebuilt masters.

Runtime-pack contract:

```text
golden tranche   6 / 6
E3 tranche       0 / 5 or 5 / 5; partial section packs forbidden
final E3 review  exact 11 / 11 committed PNGs required
```

---

# 6. Runtime-art staging recovery path

The current out-of-repository v6 recoverability bundle is:

```text
ENCYCLOPEDIA_E3_RUNTIME_ART_STAGING_V6_2026-08-29.zip
```

It contains exactly the nine changed/new renditions:

```text
Home
Animals
Lion
Gears
Space section
Earth section
Body section
Machines section
History section
```

Saturn and Pyramids are intentionally omitted because their accepted runtime Git blobs are unchanged.

The previous staging ZIP is superseded because it contained stale Body/Earth metadata and earlier source renders. Do not use it.

Maintainer-only helper:

```text
tools/import_encyclopedia_runtime_art_staging.py
tests/test_encyclopedia_runtime_art_staging.py
```

The importer:

- requires exactly one `runtime-manifest.json` and rejects legacy duplicate `manifest.json`;
- rejects unsafe ZIP paths/symlinks;
- requires exactly the nine expected staged PNGs and no extra PNG;
- verifies manifest SHA-256, byte count, 1024×600 dimensions and RGB mode metadata;
- validates the actual PNG header/dimensions/color type;
- refuses unexpected runtime PNGs;
- requires the existing Saturn/Pyramids runtime files to remain present and valid;
- prevalidates the entire staging payload before writing;
- uses temporary files plus `os.replace` for each of the nine changed/new targets;
- requires the post-import runtime directory to contain exactly 11 expected PNGs.

This helper does **not** make the staging ZIP authoritative. After import, `build_encyclopedia_visual_assets.py --check --group all`, focused tests, `make verify`, commit/push and exact-SHA Simulator evidence remain mandatory.

---

# 7. E3 Simulator review harness

Runtime gate tooling:

```text
tools/encyclopedia_v01_section_review_capture.py
tools/encyclopedia_v01_section_review.py
tests/test_encyclopedia_e3_review_tools.py
tests/test_encyclopedia_focus_treatment.py
tests/test_encyclopedia_runtime_art_staging.py
```

The capture tool reuses the existing golden-master Shell driver. It runs exactly Home plus the six section worlds through the real Greia Shell/profile/catalogue route, captures one reference frame per page, and exercises protected Greia Home return. It does not walk factual entries.

Evidence binding is fail-closed:

- checkout must be clean, including non-ignored untracked files;
- exactly 11 Encyclopedia runtime PNGs must be present;
- every PNG must already exist in the exact `HEAD` being captured;
- each working PNG must hash to the same Git blob as `HEAD:<path>`;
- the manifest records source SHA, SHA-256 of all 11 PNGs and all 11 committed Git blob IDs;
- HEAD, working status, PNG SHA-256 inventory and Git-blob inventory are rechecked after all seven sessions;
- the review builder refuses evidence that lacks the complete Git-bound manifest.

Canonical protocol:

```text
docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md
```

---

# 8. Critical evidence boundary

Therefore:

```text
OWNER VISUAL DIRECTION                  APPROVED
E3 V6 SOURCE FAMILY                     CURRENT / FROZEN
OLDER E2R RUNTIME PNG/SIMULATOR PIXELS  STALE FOR EXACT CURRENT SOURCE
OLDER PRE-V6 STAGING ZIP                SUPERSEDED
V6 NINE-PNG STAGING BUNDLE              RECOVERABLE / NOT COMMITTED EVIDENCE
COMPLETE 11-PNG COMMITTED PACK          COMPLETE at 03bf76ac (11/11 PNGs, 11/11 Git blobs)
FRESH FINAL-SHA SIMULATOR               PASS at 03bf76ac (Home+6, 7/7 sessions)
E3 RUNTIME VISUAL ACCEPTANCE            ACCEPTED at 03bf76ac
E4                                       UNBLOCKED / NEXT
```

E3 is ACCEPTED per `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md`. The pack remains valid until an Encyclopedia source/runtime change.

---

# 9. Stable generic/runtime foundation to preserve

Generic toolbox remains the established semantic visual library and canonical six-character cast. Generic Batch B remains unauthorized unless real demand proves a concrete generic gap.

Runtime invariants remain:

```text
explicit semantic visual catalogues
build-time source/SVG -> runtime PNG renditions
bounded Pygame visual cache
bounded failed-rendition memory
SceneDefinition / SceneNode / SceneCamera
PygameSceneRenderer
SceneActorDefinition / actor_scene_sample
Greia Activity Simulator real Shell/runtime composition
```

No arbitrary runtime source scanning, runtime SVG rasterization, per-frame disk decode/scale, or unbounded caches.

---

# 10. Immediate next action

E3 is ACCEPTED; E4 is UNBLOCKED but deferred per `GREIA_POST_ACTIVITY_PASS_R7_ACCEPTANCE_AGENT_INSTRUCTIONS_2026-08-30.md`.

```text
E1 COMPLETE
E2/E2R APPROVED
E3 COMPLETE / ACCEPTED at 03bf76ac (11/11 PNGs, 7/7 Simulator, visual ACCEPTED)
E4 UNBLOCKED / NEXT — deferred until post-activity-pass R7 acceptance window ends
```

Post-activity-pass acceptance SHA is e2b831da (Activity modernization COMPLETE, source gate green, Simulator 5/5 final decompositions PASS, focused R7.2/R7.3 PASS; physical Acer INCOMPLETE due to no hardware in this environment). Do not rerun E3 merely because unrelated Activities changed.

`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains HOLD unless the owner explicitly changes the direct-work instruction.

---

# 11. Drift to avoid

- no E4 entry migration before E3 runtime review;
- no 43-page broad recapture during the section gate;
- no local-agent aesthetic delegation under the current owner instruction;
- no generated mockup substituted for repository source art;
- no second runtime asset/cache/scene system;
- no runtime SVG/CairoSVG;
- no Generic Batch B by inertia;
- no narration integration in this visual lane;
- no R7/hardware claims from Activity visual work.

The standalone public website explorations at `docs/design/website_mocks_2026-09-23/` are DESIGN SPEC / DESKTOP VISUAL REVIEW only. They reuse existing Greia art and do not alter the current Encyclopedia E4 or R7 continuation route.
