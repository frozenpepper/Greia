# Greia Visual System — Current Resume File

**Status:** current visual-workstream continuation contract  
**Last reviewed:** 2026-10-16 (all-Activity rework tranche)  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Visual-system guide:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Active visual plan:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Current Activity visual subplan:** `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`  
**Current E3 source review:** `SOURCE_REVIEW.md` (archived; see git history)  
**E3 runtime gate:** `2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md` (archived; see git history)  
**Visual-authoring skill:** `skills/greia-visual-authoring/SKILL.md`

---

# 2026-10-16 — Current phase: Encyclopedia E5 next; Activity-private art awaiting library promotion (read first)

**Phase:** all 45 Activities are reworked on the shared library and control kit (P7 W0-W3; SOURCE + DESKTOP VISUAL REVIEW only; table with commits in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` §6a). Library catalogue is 0.7.0 (62 vocabulary pictures, `a779b10f`). **Encyclopedia E4 is COMPLETE** (`7b1f6b2c`: 36 authored storybook scenes; canonical cairo backend; `--check` reproduces 43/43 PNGs, 2.47 MiB).

**Next actions:**
1. **Encyclopedia E5 interaction visual-language pass** (subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`), then E6 and the fresh full 43-page capture.
2. **Library promotion/migration pass:** Activity-private art candidates (Serra plant stages, Specchi mosaic tiles, Alfabeto pictures, Stelle constellation figures, Morbidi part kit, Teatrino fairy-tale puppets, bridge/marble-run/picnic art, Volo dragon + rings, Colline buggy, instruments, pet props, tokens) are listed in P7 §8; promote once, switch consumers to shared IDs, retire duplicates. Also: left-facing `pose_point` variants, tileable `bg.sky_clouds` mid/fg layers, woodland creature hurt/happy states.
3. **Disk pass** on runtime PNG sizes against the core budget (lossless palette/quantized candidates, verify visually).
4. No Simulator/physical visual review of the reworked Activities exists yet; keep evidence labels accurate.

**Rules unchanged:** one drawing per animal; flat recipe (`GREIA_SVG_AUTHORING_RULES.md`); Opus authors SVG; installed runtime visuals are `assets/visual/runtime/` + catalogues; append new assets only for a demonstrated gap.

---

# 2026-10-15 — Current phase: W2 Activity reworks on the library and kit (superseded by the 2026-10-16 phase above)

**Phase:** the art-direction reset waves are done (cast poses, P0 Activity icons, complete flat core icons) and the **shared art library v1 is registered** (catalogue 0.6.0; `bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `fx.*`, cast variants; inventory in `assets/visual/README.md`). The shared Activity control kit (ADR 0037) and the storybook Shell redesign (Home, picker, Collection pages, Sea theme folder, My Creations, launch screen) are committed. Execution record: `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` (wave W2 = number, literacy and creative ladders first; no Activity merges; grouping by Shell theme folders). Evidence: SOURCE + headless desktop review only.

**Next actions:**
1. Reworked Activities take scenes, props, creatures, HUD glyphs, FX and cast poses from the library by semantic ID and controls from the kit; no Activity-private cast or biome redraws, no emoji as content.
2. Add an asset only for a demonstrated gap: author per `docs/design/GREIA_SVG_AUTHORING_RULES.md` (Opus), append to `assets/catalog/shared_visuals_v1_source.toml` (an identical source/output/size under a second ID is an alias and renders once), run `make visual-assets` then `make visual-assets-check`, commit SVG + PNG + catalogues together.
3. Strengthen the theme-folder tile silhouette; enlarge the delete-confirm dialog; then a Simulator visual review of the redesigned Shell (still only headless desktop reviewed).
4. Owner voice approval is pending (shared spoken numbers, Sound Blender/Story Time); it is not an art task.

**Rules:** one drawing per animal; flat recipe only; installed runtime visuals are `assets/visual/runtime/` + catalogues (~8.9 MB), never SVG masters; label evidence accurately (SOURCE, DESKTOP VISUAL REVIEW); the Encyclopedia E3 pack and E4 subplan are unaffected.

---

# 2026-10-15 — Art direction reset

Decisions (main agent, 2026-10-15; evidence: `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md` (archived; see git history)):

- `docs/design/GREIA_SVG_AUTHORING_RULES.md` is the ACCEPTED, binding SVG recipe (flat shapes, one cocoa contour, no filters/text/raster, `rsvg-convert` at build time); tile hues per Collection accepted.
- Opus is the selected SVG authoring model (bake-off winners `icon_marble_run`, `leo_celebrate`, `scene_river_valley`).
- The glossy-3D core icons, blur-filter environment/UI dialects and Activity-drawn off-model cast art are being replaced; the audit owns inventory, verdicts and backlog. The audit's "safe to remove now" set (generated variants, authoring kit/candidates, core-icon contact sheet, superseded forest/workshop pack candidates) was retired; the image now installs only `assets/visual/runtime/` + catalogues (`build/lib/compose.sh::compose_install_runtime_assets`, contract test `tests/test_build_runtime_assets_contract.py`).
- Active production waves (in order): (1) cast poses (`pose_cheer`/`pose_point` per canonical character, then on-model Activity/puppet replacements); (2) P0 Activity icons (placeholder and metaphor-duplicate icons); (3) core icons, Home-visible first.
- The Encyclopedia E3 pack stays ACCEPTED (section 1 below); this reset does not reopen it.

---

# 1. Current focus — Encyclopedia E3 runtime closure (ACCEPTED; context preserved)

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

E3 is ACCEPTED per `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (archived; see git history) (Disposition: ACCEPTED, SHA 03bf76ac, visual ACCEPTED). Do not rerun E3 merely because unrelated Activities changed.

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
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md (archived; see git history)
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
SOURCE_REVIEW.md (archived; see git history)
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

**Canonical rasterization environment (2026-10-16).** Byte-for-byte reproduction of every committed PNG (golden, sections and the `e4_*` batches, 43 total) requires the **Homebrew** libcairo 1.18.x through CairoSVG/cairocffi; the MacPorts libcairo (`/opt/local/lib`) anti-aliases some masters differently (e.g. `saturn_observatory`, `machines_gallery_workbench`, `bicycle_park`) and yields false `BUILD-DRIFT`. On macOS run both build and check as `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 tools/build_encyclopedia_visual_assets.py --check --group all`. The tool exits with an explanatory message if libcairo cannot be loaded. The 43-PNG pack is about 2.5 MiB, under the 4 MiB runtime-pack test cap.

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
2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md (archived; see git history)
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

E3 is ACCEPTED per `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (archived; see git history). The pack remains valid until an Encyclopedia source/runtime change.

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

Local agents do not take this Encyclopedia visual work (the old local-agent work order stays on HOLD and was archived 2026-10-30) unless the owner explicitly changes the direct-work instruction.

---

> 2026-10-21 note: shared and Activity runtime PNGs now have `<name>@2x.png` siblings built by `tools/build_visual_renditions.py` (same SVG, exact 2x, optional, used only by the high-resolution layer at >=1.2x). New or redrawn SVG assets must get their `@2x` through the build tool. 13 Activity PNGs lack one (shipped PNG differs from its SVG). SOURCE + DESKTOP VISUAL REVIEW only.

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

(2026-10-30: the website source left this repository; now the owner's private repository `frozenpepper/greia-website`, published with `site-ftp`.) The owner promoted the first website direction to the official site work in progress at `website/index.html`, with `website/downloads.html`, `website/library.html` and `website/README.md`. After owner rejection of the guessed wide landscape, the opening was rebuilt around the discovered original 1080×2922 rendered boot artwork: the original high-resolution final frame supplies the central G/Greia/forest, while a website-only generated panorama extends its specific palette, mountain lines, pine silhouettes, small warm-window village and lilac flowers. The 17 August patch contains Plymouth playback code and 222×600 rendered frames, not editable scene source. The 52 unchanged small frames still animate, then the original high-resolution final frame appears. Continuous pointer-responsive fireflies remain. Asset origin, hashes and the derived-background boundary are in `website/README.md`. The site uses English real-service Simulator captures except for an explicit English/Italian language comparison, a readable single-screen Parent enlargement, six real cast voice clips, and fuller parent-facing OS, hardware, architecture, network, agent-authoring and educational messaging. Installer and per-Activity package controls remain disabled until verified files exist. The old first-concept URL redirects to the official WIP; Wonder Map and Scribble Machine remain historical alternatives. The transparent small identity derivative remains website-specific, not an accepted brand master. Evidence is DESIGN SPEC / DESKTOP VISUAL REVIEW plus development Simulator visual captures only; Encyclopedia E4 and R7 continuation routes are unchanged. Next website step is owner visual review of the corrected opening.


## 2026-10-08 — Parallel developer visual-library gallery (source, NOT E3 closure)

The authoring library can now be inspected through
`python3 tools/visual_authoring_library.py gallery --output tmp/greia-visual-library.html`.
This uses the same six semantic indexes, not another asset manifest. Local
host-browser screenshots and core gallery unit tests are pending, so no
new asset is approved. The My Time source candidate stays outside installed
Activities until the icon, large clock/timer render and bilingual speech
pass real Simulator/child review. Its illustrative icon SVG/WebP is a
candidate, not a new core visual primitive. Resume Encyclopedia E3/E4
according to their own exact-state evidence and plan; this entry documents a
parallel tooling improvement, not a competing art subphase.

## 2026-10-08 — Actual asset-family review workstream (SOURCE)

Source/test `tools/visual_family_contact_sheet.py` renders one
developer-only PNG from 39 core + 45 Activity + 30 cast-expression
art at small 128/64/48px sizes. No output accepted or runtime asset
changed. Task GLA-008 in `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`
owns exact-SHA execution/review; previously frozen Encyclopedia E3/E4
direction is unaffected. New My Time control iconography is also an
unverified UI source experiment requiring the local agent's screenshots.
