# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-08-29  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current Activity visual subplan:** `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`  
**Current E3 source review:** `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md`  
**E3 runtime gate:** `docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md`  
**Visual-authoring skill:** `skills/greia-visual-authoring/SKILL.md`

---

# 1. Current focus — Encyclopedia E3 section worlds

The owner rejected the earlier Encyclopedia/E2R pixels, then directly reviewed the primary-agent source repairs to Home, Animals, Lion and Gears.

The final Home correction enlarged the book and centered the complete 3×2 category block on the book as one composition:

```text
column centers x = 267 / 512 / 757
middle Space/Machines column deliberately straddles the x=512 spine
```

After inspecting the corrected source direction, the owner explicitly approved moving forward with the visual-reauthoring plan.

Current disposition:

```text
E1 visual/asset architecture            COMPLETE
E2/E2R visual direction                 OWNER APPROVED
latest corrected golden runtime PNGs    STALE / REBUILD PENDING
latest exact-source Simulator proof     PENDING
E3 six-section source direction         IMPLEMENTED / SOURCE-REVIEWED
E3 target geometry/stage contracts      HARDENED
E3 evidence-integrity tooling           HARDENED
E3 committed 11-PNG runtime pack        PENDING
E3 exact-SHA Simulator review           PENDING
E4 factual-entry migration              BLOCKED
```

Owner approval is an aesthetic-direction decision. It does not retroactively make the old E2R Simulator screenshots current evidence for the repaired source.

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

# 4. E3 six-section source family

Animals remains the section-world reference:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

New source masters:

```text
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

Current source direction:

```text
Animals          one continuous habitat
Space            authored observatory around the live Solar System
Earth & Nature   one layered landscape with five physical destinations
Body             one discovery room with physical anatomy exhibits
Machines         one workshop with real object/mechanism silhouettes
History          one time/excavation trail rather than five cards
```

Source contact review caught and corrected issues before runtime acceptance:

```text
Body      mannequin/schematic feeling -> friendly room + physical learning props
Machines  weak gear/bridge read -> meshing toothed pair + clearer bridge
History   ambiguous dinosaur -> explicit T-rex silhouette
Earth     rain hidden by tree canopy -> visible near-layer rain streaks
```

Current source review:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

Current maintainer-local six-section contact sheet:

```text
encyclopedia_e3_section_source_contact_v5.png
```

Evidence class: **SOURCE / DESKTOP VISUAL REVIEW** only.

---

# 5. E3 staged runtime integration and geometry

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

Space is runtime-dynamic, so it does not use a static target-center equality assertion. Instead it now has an explicit authored **Solar System stage contract**: the observatory SVG carries `data-stage="solar-system"` bounds, `space.py` exposes matching literal center/stage constants, and the visual-foundation test proves the full moving planet discs, Saturn ring/marker margin and Moon excursion remain inside that authored stage.

Body and Machines no longer use the old uniform 86×86 prototype pointer areas. Their hit/focus rectangles follow the actual authored exhibit/object footprints while retaining the same semantic centers and keyboard/controller order.

History target centers are explicit constants rather than implicit positional arithmetic.

Build groups:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

The corresponding `--check` path verifies committed renditions byte-for-byte.

Runtime-pack source contract:

```text
golden tranche   6 / 6
E3 tranche       0 / 5 or 5 / 5; partial section packs forbidden
final E3 review  exact 11 / 11 committed PNGs required
```

---

# 6. E3 Simulator review harness

The runtime gate has dedicated bounded tooling:

```text
tools/encyclopedia_v01_section_review_capture.py
tools/encyclopedia_v01_section_review.py
tests/test_encyclopedia_e3_review_tools.py
```

The capture tool reuses the existing golden-master Shell driver. It runs exactly Home plus the six section worlds through the real Greia Shell/profile/catalogue route, captures one reference frame per page, and exercises protected Greia Home return. It does not walk the factual entries.

Evidence binding is now fail-closed:

- checkout must be clean, including non-ignored untracked files;
- exactly 11 Encyclopedia runtime PNGs must be present;
- every PNG must already exist in the exact `HEAD` being captured;
- each working PNG must hash to the same Git blob as `HEAD:<path>`;
- the manifest records source SHA, SHA-256 of all 11 PNGs and all 11 committed Git blob IDs;
- HEAD, working status, PNG SHA-256 inventory and Git-blob inventory are rechecked after all seven sessions;
- the review builder refuses evidence that lacks the complete Git-bound manifest.

This specifically prevents an untracked or stale generated E3 PNG from being presented as evidence for a Git SHA that did not contain it.

The review builder copies the seven bounded reference frames and creates one contact sheet. It does not auto-score or auto-approve visuals.

Canonical protocol:

```text
docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md
```

---

# 7. Critical evidence boundary

The current editable SVG source is newer than the previous E2R runtime pack.

Therefore:

```text
OWNER VISUAL DIRECTION                  APPROVED
LATEST SOURCE ART                       CURRENT
OLDER E2R RUNTIME PNG/SIMULATOR PIXELS  STALE FOR EXACT CURRENT SOURCE
LOCAL NINE-PNG STAGING BUNDLE           RECOVERABLE / NOT COMMITTED EVIDENCE
FIVE E3 SECTION PNGs                    NOT COMMITTED YET
FRESH FINAL-SHA SIMULATOR               NOT RUN YET
E3 RUNTIME VISUAL ACCEPTANCE            NOT CLAIMED
```

A local recoverability bundle may exist for the nine changed/new renditions, but it is not `--check` evidence and must never be used to bypass the committed-art requirement.

Do not call E3 complete until the full current 11-PNG art pack is built, committed, checked and the six sections are reviewed together through the real Greia runtime.

---

# 8. Stable generic visual foundation

Generic toolbox remains:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

```text
tools/visual_authoring_library.py
```

Permanent rules remain:

- `preferred` is first-choice direct reuse;
- `candidate_reference` is reference/adaptation material;
- Activity-specific hero/topic art may remain Activity-local;
- Generic Batch B remains unauthorized unless real demand proves a concrete generic gap.

Canonical cast remains the accepted six-member family:

```text
Lilli / Leo / Flash / Dani / Tito / Momo
```

---

# 9. Stable runtime foundation to preserve

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

Runtime rules:

- no arbitrary runtime source scanning;
- no normal runtime SVG rasterization;
- no per-frame disk decode/scale;
- bounded caches;
- Activity-local assets remain inside Activity packages;
- rich authored art is flattened into economical runtime surfaces.

---

# 10. Immediate next action

Do not begin E4.

Next exact visual gate:

```text
build corrected six golden-master PNGs + five E3 section PNGs
→ verify all current SVG/PNG renditions
→ focused Encyclopedia tests + required repository verification
→ commit/push the exact complete 11-PNG runtime-art state
→ rerun --check and focused tests on that pushed SHA
→ fresh exact-SHA real Greia Simulator
→ capture Home + all six section pages with the Git-bound E3 review harness
→ inspect the single runtime contact sheet + interaction/navigation sanity
→ if accepted, close E3 and unblock E4
```

This execution environment does not contain a real Greia checkout/Shell runtime, so no current `make verify` or Simulator PASS is claimed here.

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
