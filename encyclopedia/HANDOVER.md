# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28
**Runtime pages:** **43 / 43 planned executable pages**
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)
**Final runtime-relevant SHA (Simulator-captured):** `08fe71b077d47b511c105bde5c2e8fdb88be7b92`
**Current state:** **MECHANICAL RUNTIME FOUNDATION HEALTHY / OLD GRAPHICS REJECTED / E1+E2 SOURCE + RUNTIME ART + SIMULATOR CAPTURE COMPLETE / OWNER DIRECTION APPROVAL PENDING / NARRATION ACCEPTANCE PENDING**

This is the current continuation contract. Historical construction detail remains in `encyclopedia/PROGRESS.md` and dated reviews.

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

The 36 factual entry IDs remain frozen by `encyclopedia/pages/catalogue.py` and the runtime registry. Do not add topics merely because the visual layer is being reauthored.

---

## 2. Runtime architecture invariants to preserve

- `main.py` remains a thin composition root.
- `enciclopedia_engine.py` owns lifecycle, explicit page registry, semantic input and bounded internal navigation.
- Subject behavior stays in page modules/models.
- Runtime remains offline and low-resource: no runtime TTS, speech recognition, AI/LLM, network factual lookup or heavy physics.
- Spoken material is authoring-time prerecorded audio only.
- Greia protected Home remains platform-owned; Encyclopedia internal Back is separate.
- Italian and English remain the initial locales.
- Visual/text/audio caches remain explicitly bounded.
- Acer Aspire One-class hardware remains the performance floor.
- Preserve pragmatic OOP; do not replace page modules with giant procedural scripts or fake abstraction layers.

The visual redesign is not permission to rewrite these stable mechanics.

---

## 3. Research and narration authority

Every factual page has research/wording authority under:

```text
encyclopedia/research/<section>/<entry>.md
```

Canonical narration coordination:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

The source-gate ledger checkpoint was:

```text
378 rows
378 REQUESTED
```

`378` means coordination rows, not 378 generated audio files.

Voice generation/review is separate. Only owner listening may establish `OWNER_ACCEPTED`; only owner-accepted recordings may be integrated into runtime audio assets.

---

## 4. Previously proven mechanical/runtime evidence

### Source gate prior green checkpoint

SHA:

```text
d89809a43cdfe62c85775ccdcfd04eb6e34fbd05
```

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_044052/
```

Proven there:

```text
378 / 378 voice-request rows canonical
focused Encyclopedia tests PASS
make verify PASS
first-party Activity validations PASS
accepted-audio sync check PASS
clean worktree
```

### Real Shell lifecycle smoke

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_070951-headless-route-smoke/
```

Proven:

```text
real Shell -> Encyclopedia PASS
first Activity frame PASS
12-second survival PASS
bounded interaction PASS
protected Greia Home -> Shell PASS
```

### Full 43-page mechanical traversal

Evidence:

```text
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal/
tmp/encyclopedia-v01-acceptance/20260828_074819-mechanical-traversal.zip
```

Mechanically proven:

```text
sections reached                  6 / 6
factual entries reached          36 / 36
semantic ACTIVATE delivered      36 / 36
internal Back returns            36 / 36
section -> Encyclopedia Home     PASS
protected Greia Home -> Shell    PASS
continuous run                   PASS
```

The later screenshot review found a generic capture-settle race for Sun/Neptune before-frames. The generic headless transition-settle repair has since landed on `main` and should be preserved.

These older runtime passes predate the current E1/E2 visual edits and therefore **do not** count as launch/visual acceptance of the new golden-master source.

---

## 5. Important correction — old graphics are NOT accepted

The earlier visual-evidence review was too charitable about the overall art direction.

After owner review, the correct disposition remains:

```text
MECHANICAL PAGE/INPUT ARCHITECTURE: useful
OLD ENCYCLOPEDIA GRAPHICS: rejected as product quality
```

The systemic failure was:

- main illustrated subjects too often built from raw `pygame.draw` circles/ellipses/rectangles/lines/polygons;
- flat sparse backgrounds;
- section pages resembling menus/diagrams rather than inviting illustrated worlds;
- instrumentation-like discovery bubbles;
- canonical characters commonly pasted into corners rather than composed into scenes;
- subtle interaction payoffs;
- too much explanatory burden carried by captions;
- conflict with Greia's accepted storybook/felt-board/toy-diorama visual system.

Authoritative forensic audit:

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
```

---

## 6. Active visual reauthoring subplan

Authoritative plan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

The redesign preserves mechanics and replaces the visual layer with:

- authored hero illustrations;
- layered storybook/toy-diorama scene composition;
- Activity-local source masters + economical runtime PNG renditions;
- tactile reusable DiscoveryToken states;
- reusable page-shell/hero-stage/caption/presenter helpers only where real shared invariants exist;
- meaningful environmental context;
- stronger integrated use of canonical characters;
- clear first-interaction visual payoff;
- audio-first/pre-reader composition;
- bounded low-resource runtime behavior.

Procedural drawing remains appropriate for real diagrams, small annotations, particles, focus rings and dynamic overlays. It is no longer acceptable as the default final illustration method for real-world hero subjects.

---

## 7. E1/E2 source + runtime art + Simulator capture (this work)

The bounded visual-foundation/golden-master tranche is now end-to-end complete on the source, runtime-art and Simulator-capture axes.

### Shared foundation

```text
activities/enciclopedia_greia/enciclopedia_presentation.py
activities/enciclopedia_greia/enciclopedia_services.py
```

Implemented source contracts include:

```text
PageShellLayout safe regions
DiscoveryToken tactile state language
caption ribbon helper
authored-scene placement helper
object focus/lift treatment
bounded package-local authored-art cache
explicit semantic art-id -> runtime PNG map
no page-local image decode / smoothscale
```

`VisualLibrary` remains hard-bounded and is the single Activity-local facade for these authored runtime renditions plus shared canonical characters.

### Editable source masters + committed runtime PNG pack

```text
activities/enciclopedia_greia/assets/source/home_discovery_book.svg
activities/enciclopedia_greia/assets/source/animals_field_table.svg
activities/enciclopedia_greia/assets/source/lion_savanna.svg
activities/enciclopedia_greia/assets/source/saturn_observatory.svg
activities/enciclopedia_greia/assets/source/gears_workbench.svg
activities/enciclopedia_greia/assets/source/pyramids_diorama.svg

activities/enciclopedia_greia/assets/runtime/home_discovery_book.png
activities/enciclopedia_greia/assets/runtime/animals_field_table.png
activities/enciclopedia_greia/assets/runtime/lion_savanna.png
activities/enciclopedia_greia/assets/runtime/saturn_observatory.png
activities/enciclopedia_greia/assets/runtime/gears_workbench.png
activities/enciclopedia_greia/assets/runtime/pyramids_diorama.png
```

All six runtime PNGs are 1024×600 8-bit RGB; the build tool's `--check`
rebuilds them temporarily and byte-compares against the committed pack.

### Golden-master page source

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
```

The page/state/navigation models were retained. The visual code now consumes authored scenes and uses procedural drawing primarily for focus/discovery UI and bounded educational reveal overlays.

### Build, capture, review tooling

```text
tools/build_encyclopedia_visual_assets.py             # authoring-only SVG -> PNG (CairoSVG)
tools/encyclopedia_v01_golden_master_capture.py       # one real Greia Shell session per page
tools/encyclopedia_v01_golden_master_review.py        # curated 4-shot set + 3x2 contact sheet
tools/encyclopedia_v01_golden_master_zip.py           # non-committed owner-transfer ZIP
tests/test_activity_enciclopedia_visual_foundation.py
tests/test_encyclopedia_authoring_tools.py            # tightened to subtract VisualLibrary.ART_ASSETS
```

### Source-gate evidence at the final runtime-relevant SHA `08fe71b`

```text
make verify                                          1462 / 1462 PASS
tests.test_activity_enciclopedia + visual_foundation    19 / 19 PASS
tools/build_encyclopedia_visual_assets.py --check      PASS 6 Encyclopedia runtime PNGs match editable masters
real Greia Simulator launch (6 sessions)               6 / 6 PASS
protected Greia Home return (every session)            6 / 6 PASS
ACTIVATE payoff captured on every factual entry         4 / 4 PASS
```

### Simulated visual evidence

```text
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/
  REVIEW.md
  layout-audit.json
  contact-sheet-primary.png
  screenshots/01-home.png
  screenshots/02-lion-activated.png
  screenshots/03-home-compact.png
  screenshots/04-home-large.png
GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip   # NOT committed
tmp/encyclopedia-goldenmaster-2026-08-28/                       # full local evidence
```

Pre-reader / no-reading review recorded against the six prototypes:

```text
PRE_READER_CORE_FLOW_PASS=yes
TEXT_REQUIRED_FOR_GAMEPLAY=no
NO_READING_FIRST_ACTION_PASS=yes
PRIMARY_INSTRUCTION_CHANNEL=visual
```

---

## 8. Golden-master hard gate before bulk migration

Required representative prototypes remain:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
optional Body/Heart proof only if needed later
```

Required workflow is now:

```text
E1/E2 source landed
→ build six runtime PNGs on local maintainer checkout
→ focused real-checkout tests
→ commit/push generated runtime PNGs
→ final-SHA real Greia Simulator launch/survival
→ actual 1024×600 prototype screenshots
→ compact + larger responsive sample
→ one curated contact sheet
→ owner visual review
→ explicit direction approval
→ only then E3/E4 migration
```

If the owner rejects the direction, revise these six prototypes rather than propagating them.

**No remaining Encyclopedia page may be migrated before this gate.**

---

## 9. Previous small fixes to retain

Already landed and still valid:

- Pyramids caption safe fitting/wrapping intent; the new shared caption ribbon retains adaptive fitting rather than truncation;
- Body Teeth target contrast improvement;
- generic headless page-transition settle repair.

These fixes solve real local defects but do not constitute current visual acceptance.

---

## 10. Current local-agent authority

Rolling pointer:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

It now owns the exact next execution task:

```text
refresh main
build six runtime PNGs
run focused tests / local verification
commit runtime PNG pack
run final-SHA real Simulator gate
capture six prototypes + responsive samples
produce contact sheet
perform no-reading review
update evidence/docs
STOP for owner review
```

Explicitly prohibited before owner approval:

```text
another broad 43-page visual recapture
final all-page pointer/responsive acceptance
narration generation/integration
bulk redraw/migration of remaining pages
```

---

## 11. `libpng` warning

Prior headless runs emitted:

```text
libpng error: bad adaptive filter value
```

No broad visible missing-asset/fallback pattern was identified in the old evidence. The warning remains unresolved diagnostic evidence and must not be attributed to a specific cause without direct proof.

The new golden-master runtime PNGs must be checked normally when built. Do not assume the old warning applies to them and do not let speculative warning repair derail the visual gate without concrete evidence.

---

## 12. Acceptance still pending

```text
golden-master owner direction approval           (captures ready, owner is the aesthetic authority)
complete visual migration                        (E3 sections + E4 entries, hard-blocked)
interaction visual-language pass                  (E5)
pointer vs semantic-keyboard parity sample        (E6)
pre-reader/no-reading final acceptance            (E6, narrow prototype pass already yes)
responsive viewport/profile matrix                (E6; one compact + one larger row already captured)
narration owner acceptance/integration            (separate lane, 378 rows still REQUESTED)
physical Acer/Pi acceptance                      (separate lane)
```

Only after final visual/input/pre-reader/responsive Simulator gates pass may the Encyclopedia become:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

Current truthful status:

```text
E1/E2 SOURCE + RUNTIME ART + SIMULATOR CAPTURE COMPLETE
  (1462/1462 make verify PASS at SHA 08fe71b,
   6/6 runtime PNGs committed and sha256-verified by --check,
   6/6 headless Shell sessions PASS at the final SHA,
   protected Greia Home return verified on every session,
   4/4 ACTIVATE payoffs captured and visible.)
OWNER DIRECTION APPROVAL: PENDING (contact sheet and owner ZIP ready)
NARRATION ACCEPTANCE: SEPARATE / PENDING
```

---

## 13. Current authorities

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md

docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/PRE_READER_UX.md
```
