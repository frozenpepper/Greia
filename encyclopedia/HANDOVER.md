# Greia Encyclopedia workstream handover

**Updated:** 2026-08-29  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Last Simulator-captured visual SHA:** `8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f` — technically valid E2R capture, aesthetically superseded  
**Current state:** **MECHANICAL FOUNDATION HEALTHY / E1 COMPLETE / GOLDEN-MASTER DIRECTION OWNER-APPROVED AFTER DIRECT REPAIRS / E3 SECTION SOURCE IMPLEMENTED + SOURCE-REVIEWED + GEOMETRY/FOCUS/EVIDENCE-HARDENED / COMMITTED 11-PNG PACK + FRESH SIMULATOR EVIDENCE PENDING / E4 BLOCKED / NARRATION SEPARATE**

This file is the current continuation contract. Historical construction detail remains in `encyclopedia/PROGRESS.md`, Git history, and dated visual reviews.

---

## 1. Frozen v0.1 scope

Exactly 43 executable pages:

```text
home
animals + 6 entries
space + 10 entries
earth + 5 entries
body + 5 entries
machines + 5 entries
history + 5 entries
```

The 36 factual entry IDs remain frozen by `encyclopedia/pages/catalogue.py` and the runtime registry. Visual migration is not permission to change factual scope.

---

## 2. Runtime architecture invariants to preserve

- `main.py` remains a thin composition root.
- `enciclopedia_engine.py` owns lifecycle, explicit page registry, semantic input and bounded internal navigation.
- Subject behavior stays in page modules/models.
- Runtime remains offline and low-resource: no runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Spoken material remains authoring-time prerecorded audio only.
- Greia protected Home remains platform-owned; Encyclopedia internal Back is separate.
- Italian and English remain the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- Acer Aspire One-class hardware remains the performance floor.
- Keep the Activity-local authored-art source/runtime split and deterministic SVG→PNG authoring build.
- No runtime SVG/CairoSVG and no page-hot-path image decode/scale.
- Missing authored renditions must fail soft without inventing a second asset system.

---

## 3. Mechanical foundation already proven

Older evidence established:

```text
43 / 43 page reachability
36 / 36 entry semantic ACTIVATE delivery
36 / 36 internal Back returns
protected Greia Home -> Shell
continuous real-Shell lifecycle
focused source gates / make verify
```

That evidence remains valid for mechanics. It does not substitute for fresh visual/runtime evidence after runtime-relevant asset changes.

---

## 4. Golden-master visual direction — OWNER APPROVED

The original E2R Simulator pixels were rejected by the owner despite technical success. The owner then directed the primary agent to repair the actual source assets directly rather than delegate another art pass.

Direct corrections on `main` included:

```text
Home      book enlarged; final 3x2 category block centered on the whole book
          at x=267 / 512 / 757, with the middle column deliberately crossing the spine
Animals   lion and elephant replaced with immediately recognizable full-body silhouettes
Lion      face/head/mane unified; tail connected to rump; visible load-bearing legs added
Gears     three unmistakably toothed gears physically mesh; teaching overlays use real mesh points
```

After inspecting those direct source repairs, the owner explicitly approved moving forward with the plan. Therefore:

```text
E1 VISUAL/ASSET ARCHITECTURE:       COMPLETE
E2/E2R VISUAL DIRECTION:            OWNER APPROVED
E3 SECTION-PAGE REAUTHORING:        UNBLOCKED / ACTIVE
E4 FACTUAL-ENTRY MIGRATION:         BLOCKED UNTIL E3 SIX-SECTION REVIEW
```

Primary direct-repair record:

```text
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
```

---

## 5. Evidence boundary after the owner-approved repairs

The old E2R runtime PNGs and Simulator screenshots predate the final Home/Animals/Lion/Gears repairs.

Therefore:

```text
owner visual-direction decision                         CURRENT / APPROVED
corrected editable SVG source                          CURRENT
old committed runtime PNGs for changed golden masters STALE
old E2R Simulator screenshots                         STALE FOR EXACT CURRENT SOURCE
local nine-PNG staging bundle                         RECOVERABLE / NOT COMMITTED EVIDENCE
fresh final-source Simulator acceptance               PENDING
```

Do not turn the owner approval into a false claim that the newest files have already passed final-SHA Simulator acceptance. A locally rendered PNG is not current Simulator evidence until it is committed, byte-bound to the tested `HEAD`, and captured through the real Greia runtime.

---

## 6. E3 section-world source tranche

Animals remains the accepted section-world reference:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

Five authored section masters are now on `main`:

```text
activities/enciclopedia_greia/assets/source/space_gallery_observatory.svg
activities/enciclopedia_greia/assets/source/earth_gallery_landscape.svg
activities/enciclopedia_greia/assets/source/body_gallery_discovery_room.svg
activities/enciclopedia_greia/assets/source/machines_gallery_workbench.svg
activities/enciclopedia_greia/assets/source/history_gallery_time_trail.svg
```

Design intent:

```text
Space            authored observatory around the existing live Solar System
Earth & Nature   one layered landscape containing rain/tree/rainbow/volcano/ocean
Body             one friendly discovery room with physical anatomy exhibits
Machines         one real workbench with recognizable gears/magnet/bicycle/plane/bridge
History          one continuous time/excavation trail with T-rex/fossil/mammoth/cave/pyramid
```

Source/runtime review caught and corrected issues before final Simulator acceptance:

```text
Body      mannequin/schematic feeling -> friendly room + physical learning props
Machines  weak gear/bridge silhouettes -> real meshing gear pair + clearer suspension bridge
History   ambiguous dinosaur -> unmistakable T-rex silhouette
Earth     rain hidden behind tree canopy -> visible near-layer rain streaks
Earth     Rain/Tree hit regions overlapped -> Rain region shortened, authored center preserved
E3 pages  generic authored-scene focus rings -> soft scene-native focus patches
Space     bottom text carried duplicate yellow focus -> selected live subject now owns focus
```

Current source-review authority:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

Current maintainer source contact sheet:

```text
encyclopedia_e3_section_source_contact_v5.png
```

It is **SOURCE / DESKTOP VISUAL REVIEW**, not Simulator acceptance.

---

## 7. E3 runtime integration, geometry and focus

The five section pages are wired to semantic authored-scene IDs through the existing bounded `VisualLibrary`:

```text
space.py      encyclopedia.space.gallery.observatory
earth.py      encyclopedia.earth.gallery.landscape
body.py       encyclopedia.body.gallery.discovery_room
machines.py   encyclopedia.machines.gallery.workbench
history.py    encyclopedia.history.gallery.time_trail
```

Important behavior:

- Space preserves the continuously orbiting Sun/planets/Moon as the actual interactive teaching model; authored art supplies the observatory context.
- Earth/Body/Machines/History let authored art carry the primary pictorial burden when present.
- Until the five E3 runtime PNGs are generated, every page deliberately falls back to its previous proven procedural rendering.
- Existing semantic destinations, input handling and page IDs are preserved.

The static section worlds have a machine-checkable source/input alignment contract. `tests/test_activity_enciclopedia_visual_foundation.py` compares SVG `data-target`/`data-center` metadata with page input geometry for:

```text
Home
Animals
Earth & Nature
Body
Machines
History
```

Space remains dynamic rather than pretending to use fixed target centers. Its authored observatory carries a non-rendering `data-stage="solar-system"` / `data-bounds` contract, while `space.py` exposes literal `SOLAR_SYSTEM_CENTER` and `SOLAR_SYSTEM_STAGE_BOUNDS`. The visual-foundation test parses every `Planet(...)` orbit and proves the complete rendered planet discs/markers, Saturn ring margin, and Moon excursion remain inside the authored observation stage.

History target centers are explicit page constants rather than implicit arithmetic. Body and Machines no longer use the old uniform 86x86 prototype hit boxes: pointer/focus rectangles follow actual authored exhibit/object footprints while preserving semantic centers and keyboard/controller ordering.

`tests/test_encyclopedia_section_hit_geometry.py` checks Earth, Body, Machines and History selection geometry directly:

- all static authored hit regions stay inside the 1024×600 logical surface;
- each page's target rectangles are pairwise disjoint, preventing one visible subject from resolving to another;
- Body/Machines keep generously sized authored-object target areas;
- Earth Rain/Tree cannot regress to their earlier overlap;
- authored Earth/Body/Machines/History use `draw_focus_patch(...)`, while `focus_ring(...)` is retained only for procedural fail-soft presentation.

Animals already uses `draw_focus_patch(...)`. Space does not need a static object patch: the selected live Sun/planet/Moon draws its own yellow subject ring, while the bottom text plaque is deliberately neutral and secondary.

The build tool supports explicit visual tranches:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

and equivalent `--check --group ...` verification.

The visual-foundation source test requires:

```text
golden runtime tranche    6 / 6 when runtime assets exist
E3 section tranche        0 / 5 or 5 / 5 — a partial E3 pack is forbidden
```

---

## 8. E3 Simulator review tooling — exact-SHA and committed-art bound

Two narrow tools exist for the E3 gate:

```text
tools/encyclopedia_v01_section_review_capture.py
tools/encyclopedia_v01_section_review.py
```

The capture tool reuses `encyclopedia_v01_golden_master_capture.py` rather than introducing a second Shell/Simulator harness. It runs exactly seven small sessions:

```text
Home
Animals
Space
Earth & Nature
Body
Machines
History
```

Each session uses the real Greia Shell/profile/catalogue launch path, semantic internal navigation, one reference screenshot, and protected Greia Home return. It does not walk the 36 factual entries.

Evidence integrity is part of the tool rather than a manual convention. Before launching even the first session it requires:

```text
clean checkout, including non-ignored untracked files
exact complete 11-PNG Encyclopedia runtime-art inventory
every one of those PNGs committed in the exact HEAD being captured
working PNG bytes identical to HEAD:<path> Git blob bytes
```

For each PNG the harness resolves the committed blob with `git rev-parse HEAD:<path>` and compares it with `git hash-object <path>`. This prevents an untracked/generated/stale E3 PNG from being presented as evidence for a Git SHA that did not contain it.

It then writes:

```text
source-sha.txt
capture-manifest.json
```

The manifest records:

```text
source_sha
locale / viewport / interface_size
selected_jobs / completed_jobs
runtime_art_sha256       # all 11 PNGs
runtime_art_git_blobs    # all 11 PNGs
status / failure
```

At the end the tool fails if `HEAD`, working status, runtime-PNG SHA-256 inventory, or committed Git-blob inventory changed during capture.

The review builder accepts only:

```text
status = PASS
selected_jobs = Home + all six sections
completed_jobs = Home + all six sections
runtime_art_sha256 = exact complete 11-PNG Encyclopedia pack
runtime_art_git_blobs = exact complete 11-PNG committed blob inventory
source-sha.txt = capture-manifest source_sha
```

It validates SHA formats and preserves both integrity files beside the seven curated screenshots/contact sheet. `tests/test_encyclopedia_e3_review_tools.py` pins the seven-job scope, exact eleven-art precondition, clean-checkout rule, committed-art rule and evidence-integrity contract without launching Pygame.

Canonical maintainer protocol:

```text
docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md
```

---

## 9. Current E3 gate

```text
Animals section source                         READY
Space section source                           READY + LIVE-STAGE BOUNDS GUARDED
Earth & Nature section source                  READY + NON-OVERLAPPING INPUT
Body section source                            READY + AUTHORED-OBJECT INPUT
Machines section source                        READY + AUTHORED-OBJECT INPUT
History section source                         READY + EXPLICIT TARGET GEOMETRY
static visual/input geometry contract          IMPLEMENTED
static hit-region non-overlap contract         IMPLEMENTED
authored scene-native focus treatment          IMPLEMENTED
exact 11-art capture precondition              IMPLEMENTED
committed-art Git-blob capture contract        IMPLEMENTED
exact-SHA Simulator evidence contract          IMPLEMENTED
five new E3 runtime PNGs                       PENDING COMMIT
rebuild corrected golden-master PNGs           PENDING COMMIT
build --check on complete current art pack     PENDING
focused real-checkout tests / make verify      PENDING
fresh final-SHA real Greia Simulator           PENDING
Home + six-section runtime contact sheet       PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until all six section pages are rendered through the real Greia runtime and reviewed together.

---

## 10. Local-agent boundary

The owner explicitly asked the primary agent to perform this visual work directly. Do **not** delegate the current art-authoring work to the local agent.

`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains a HOLD notice unless the owner later authorizes a new bounded execution task.

---

## 11. Narration remains separate

Canonical coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

The historical ledger checkpoint remains 378 REQUESTED rows. Only owner-listened `OWNER_ACCEPTED` clips may enter runtime audio. This visual lane does not generate or integrate narration.

---

## 12. Immediate next step

Do **not** start E4 and do not continue speculative section-art polishing without runtime pixels.

Next exact runtime closure for the current art tranche:

```text
rebuild corrected six golden-master PNGs
+ build five E3 section PNGs
→ verify 11/11 current SVG->PNG renditions
→ focused Encyclopedia tests:
   tests.test_activity_enciclopedia
   tests.test_activity_enciclopedia_visual_foundation
   tests.test_encyclopedia_authoring_tools
   tests.test_encyclopedia_e3_review_tools
   tests.test_encyclopedia_section_hit_geometry
→ required local repository verification
→ commit/push exact complete current 11-PNG runtime art
→ rerun build --check + focused tests on that pushed SHA
→ real Greia Simulator on the exact final SHA
→ capture Home + six section pages with source SHA + SHA256 + committed Git-blob manifest
→ build the bounded provenance-preserving review set
→ inspect the single runtime contact sheet + interaction/navigation sanity
→ if E3 runtime family is accepted, close E3 and unblock E4
```

This environment currently has no real Greia checkout/Shell runtime, so no `make verify` or Simulator PASS is claimed here.

---

## 13. Current authorities

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
docs/testing/2026-08-29_ENCYCLOPEDIA_E3_SECTION_RUNTIME_REVIEW.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md

docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```
