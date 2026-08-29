# Greia Encyclopedia workstream handover

**Updated:** 2026-08-29  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Last Simulator-captured visual SHA:** `8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f` — technically valid E2R capture, aesthetically superseded  
**Current state:** **MECHANICAL FOUNDATION HEALTHY / E1 COMPLETE / GOLDEN-MASTER DIRECTION OWNER-APPROVED AFTER DIRECT REPAIRS / E3 SECTION SOURCE IMPLEMENTED + SOURCE-REVIEWED / RUNTIME PNG + FRESH SIMULATOR EVIDENCE PENDING / E4 BLOCKED / NARRATION SEPARATE**

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
fresh final-source Simulator acceptance               PENDING
```

Do not turn the owner approval into a false claim that the newest files have already passed final-SHA Simulator acceptance.

---

## 6. E3 section-world source tranche

Animals remains the accepted section-world reference:

```text
activities/enciclopedia_greia/assets/source/animals_field_table.svg
```

Five new authored section masters are now on `main`:

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

A first source contact review caught and corrected three issues before persistence:

```text
Body      too panel-like -> converted lungs/heart/bones into physical exhibits
Machines  weak gear/bridge silhouettes -> real meshing gear pair + clearer suspension bridge
History   ambiguous dinosaur -> unmistakable T-rex silhouette
```

Current source-review authority:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

Evidence class remains **SOURCE / DESKTOP VISUAL REVIEW**, not Simulator acceptance.

---

## 7. E3 staged runtime integration

The five section pages are now wired to semantic authored-scene IDs through the existing bounded `VisualLibrary`:

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

The build tool now supports explicit visual tranches:

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

This staged state is intentional; it keeps `main` fail-soft while source authoring advances.

---

## 8. Current E3 gate

```text
Animals section source                         READY
Space section source                           READY
Earth & Nature section source                  READY
Body section source                            READY
Machines section source                        READY
History section source                         READY
five new E3 runtime PNGs                       PENDING
rebuild corrected golden-master PNGs           PENDING
build --check on complete current art pack     PENDING
focused real-checkout tests / make verify      PENDING
fresh final-SHA real Greia Simulator           PENDING
six-section runtime contact-sheet review       PENDING
E4 factual-entry migration                     BLOCKED
```

Do not begin E4 until all six section pages are rendered through the real Greia runtime and reviewed together.

---

## 9. Local-agent boundary

The owner explicitly asked the primary agent to perform this visual work directly. Do **not** delegate the current art-authoring work to the local agent.

`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains a HOLD notice unless the owner later authorizes a new bounded execution task.

---

## 10. Narration remains separate

Canonical coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

The historical ledger checkpoint remains 378 REQUESTED rows. Only owner-listened `OWNER_ACCEPTED` clips may enter runtime audio. This visual lane does not generate or integrate narration.

---

## 11. Immediate next step

Do **not** start E4.

Next exact runtime closure for the current art tranche:

```text
rebuild corrected six golden-master PNGs
+ build five E3 section PNGs
→ verify 11/11 current SVG->PNG renditions
→ focused Encyclopedia tests
→ required local repository verification
→ commit/push complete current runtime art
→ real Greia Simulator on the exact final SHA
→ review Home + six section pages together, with interaction/navigation sanity
→ if E3 runtime family is accepted, close E3 and unblock E4
```

---

## 12. Current authorities

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md

docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```
