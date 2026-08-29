# Encyclopedia E3 — Home + Six-Section Runtime Review

**Status:** PENDING EXECUTION ON A REAL GREIA CHECKOUT  
**Date:** 2026-08-29  
**Activity:** `org.greia.enciclopedia`  
**Scope:** E2 corrected runtime-art closure + E3 six-section runtime visual review  
**Not a delegated local-agent task:** this protocol documents the maintainer/owner gate; `GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains HOLD unless the owner explicitly changes that instruction.

---

## 1. Purpose

Close the runtime evidence gap after the owner-approved golden-master source repairs and the E3 section-world source tranche.

This protocol deliberately does **not**:

- migrate E4 factual-entry artwork;
- rerun the broad 43-page visual traversal;
- generate/integrate narration;
- claim physical Acer/Raspberry Pi evidence;
- use GitHub-hosted Actions.

Required visual family:

```text
Home
Animals
Space
Earth & Nature
Body
Machines
History
```

The review exists to answer one question before E4:

> Do the six section worlds form one recognizable, coherent, child-usable visual family through the real Greia runtime?

---

## 2. Preconditions

Use a real local checkout of `frozenpepper/Greia`.

Before execution:

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
```

Stop if the checkout contains unrelated owner/contributor changes. Do not overwrite or clean them away.

Read:

```text
AGENTS.md
encyclopedia/HANDOVER.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

E4 must still be blocked when this protocol starts.

---

## 3. Build the complete current Encyclopedia art pack

Build both visual tranches from the committed editable masters:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group all
python3 tools/build_encyclopedia_visual_assets.py --check --group all
```

Expected current set: **11 / 11** 1024×600 PNG renditions:

```text
home_discovery_book.png
animals_field_table.png
lion_savanna.png
saturn_observatory.png
gears_workbench.png
pyramids_diorama.png
space_gallery_observatory.png
earth_gallery_landscape.png
body_gallery_discovery_room.png
machines_gallery_workbench.png
history_gallery_time_trail.png
```

Stop on:

```text
missing source
missing runtime PNG
BUILD-DRIFT
wrong dimensions
partial 1..4-file E3 section tranche
```

CairoSVG remains an authoring/maintainer dependency only. Do not add it to the child runtime.

---

## 4. Focused source/runtime tests before capture

Run:

```bash
python3 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation \
  tests.test_encyclopedia_authoring_tools
```

The focused visual-foundation suite must prove at least:

- eleven editable masters are known to the build contract;
- `VisualLibrary` maps exactly the eleven runtime PNGs;
- page hot paths do not decode/scale assets;
- E3 section pages use the authored-scene seam with fail-soft fallback;
- Home/Animals/Earth/Body/Machines/History source target centers match actual input geometry;
- the golden runtime tranche is complete;
- the E3 runtime tranche is all-or-none, never partial.

Then run the repository-local aggregate gate required by current `main`:

```bash
make verify
```

Do not use or inspect GitHub-hosted Actions as evidence.

---

## 5. Commit the generated runtime state before Simulator evidence

The Simulator must capture one exact committed source/runtime state.

Review the generated diff:

```bash
git status --short
git diff --stat
git diff -- activities/enciclopedia_greia/assets/source \
             activities/enciclopedia_greia/pages \
             activities/enciclopedia_greia/enciclopedia_services.py \
             tools/build_encyclopedia_visual_assets.py \
             tests/test_activity_enciclopedia_visual_foundation.py
```

The SVG/source/code should already be committed. The expected new generated diff is the current runtime PNG pack.

Commit/push the coherent runtime-art state on `main`, then record:

```bash
git rev-parse HEAD
```

Against that exact pushed SHA rerun:

```bash
python3 tools/build_encyclopedia_visual_assets.py --check --group all
python3 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation \
  tests.test_encyclopedia_authoring_tools
```

If the pushed SHA no longer matches the source/runtime state that was tested, stop and reconcile before Simulator capture.

---

## 6. Real Greia Simulator capture

Use the dedicated bounded E3 harness:

```bash
rm -rf tmp/encyclopedia-e3-section-review-2026-08-29
python3 tools/encyclopedia_v01_section_review_capture.py \
  --evidence-root tmp/encyclopedia-e3-section-review-2026-08-29 \
  --locale it \
  --viewport 1024x600 \
  --interface-size normal
```

Expected jobs:

```text
home
animals
space
earth
body
machines
history
```

The harness reuses the established golden-master Simulator driver. Every job must:

- launch built-in `org.greia.enciclopedia` through the real Greia Shell/profile/catalogue path;
- navigate from Encyclopedia Home using semantic input;
- capture the requested page;
- exercise protected Greia Home return before shutdown.

Stop on the first failed session. Do not substitute direct page-module rendering or isolated Pygame screenshots.

---

## 7. Build the bounded review set

After all seven jobs pass:

```bash
python3 tools/encyclopedia_v01_section_review.py \
  --evidence-root tmp/encyclopedia-e3-section-review-2026-08-29 \
  --output-root docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime
```

Expected curated outputs:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/screenshots/01-home.png
.../02-animals.png
.../03-space.png
.../04-earth.png
.../05-body.png
.../06-machines.png
.../07-history.png
.../contact-sheet.png
```

Do not commit raw duplicate screenshot trees from `tmp/`; only the bounded curated review set is eligible for preservation after review.

---

## 8. Visual review criteria

Review the actual Simulator contact sheet at 100% and each 1024×600 frame individually.

### Home

- enlarged book visibly contains the six mini-world portals;
- complete 3×2 portal block is centered on the book;
- middle Space/Machines column may cross the central spine deliberately;
- no category looks like an unrelated button floating outside the page.

### Animals

- lion, elephant, octopus, bee, penguin and frog are immediately recognizable;
- elephant trunk/ear/body silhouette survives netbook scale;
- continuous habitat still reads as one world.

### Space

- authored observatory and live Solar System complement one another;
- observatory does not obscure moving planet/Moon targets;
- dynamic targets remain visually dominant enough to select.

### Earth & Nature

- rain, tree, rainbow, volcano and ocean read without labels;
- rain remains visible despite tree overlap;
- focus treatment does not make the landscape look like a card menu.

### Body

- page reads as a friendly discovery room, not a medical mannequin diagram;
- senses board, jaw/teeth model, lungs, heart and bones box are recognizable physical exhibits;
- focus/hit treatment follows the visible exhibit rather than a tiny central hotspot.

### Machines

- gears unmistakably have teeth and visibly mesh;
- magnet, bicycle, airplane and bridge are recognizable at 1024×600;
- focus/hit areas follow the complete authored objects rather than the old 86×86 prototype circles.

### History

- T-rex is immediately recognizable;
- fossil, mammoth, cave painting and pyramid remain distinct;
- left-to-right time/excavation trail reads as one authored scene, not five cards.

### Whole family

Block E3 closure for:

- unrecognizable subject silhouettes;
- detached/floating body parts;
- mechanically false diagrams;
- visual/input mismatch;
- clipped/occluded protected system chrome;
- text required to identify the primary choices;
- one section falling visibly back to programmer-art presentation because its authored PNG failed to load.

Small local polish issues may be logged without blocking E3 if they do not undermine recognizability, hierarchy, interaction or family coherence.

---

## 9. Disposition

If the seven real-runtime frames are accepted:

```text
E1 visual architecture                  COMPLETE
E2/E2R owner visual direction           APPROVED
E3 six-section runtime family           COMPLETE / ACCEPTED
E4 factual-entry migration              UNBLOCKED
```

Then update:

```text
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
HANDOVER.md
```

If the runtime family fails visually, keep E4 blocked and correct only the affected section/master. Do not restart a 43-page redraw and do not average a visual blocker away with green tests.
