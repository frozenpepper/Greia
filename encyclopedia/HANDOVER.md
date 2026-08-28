# Greia Encyclopedia workstream handover

**Updated:** 2026-08-28  
**Runtime pages:** **43 / 43 planned executable pages**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Current state:** **MECHANICAL RUNTIME FOUNDATION HEALTHY / CURRENT GRAPHICS REJECTED / VISUAL REAUTHORING ACTIVE / NARRATION ACCEPTANCE PENDING**

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

---

## 5. Important correction — current graphics are NOT accepted

The earlier visual-evidence review was too charitable about the overall art direction.

After owner review, the correct disposition is:

```text
MECHANICAL PAGE/INPUT ARCHITECTURE: useful
CURRENT ENCYCLOPEDIA GRAPHICS: rejected as product quality
```

The problem is systemic:

- main illustrated subjects are too often raw `pygame.draw` circles/ellipses/rectangles/lines/polygons;
- backgrounds are flat and sparse;
- section pages resemble menus/diagrams rather than inviting illustrated worlds;
- discovery controls look like small instrumentation bubbles;
- canonical characters are commonly pasted into corners rather than composed into scenes;
- interaction payoffs are frequently subtle diagram changes;
- text/caption strips carry too much of the explanatory burden for a pre-reader-first Activity;
- the current result conflicts with Greia's accepted storybook/felt-board/toy-diorama visual system.

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

## 7. Golden-master gate before bulk migration

Do **not** redraw all 43 pages immediately.

Required representative prototypes:

```text
Home
Animals section
Lion
Saturn
Gears
Pyramids
optional Body/Heart proof
```

These must demonstrate:

- root navigation;
- section navigation;
- organic illustration;
- astronomy/dark-scene treatment;
- mechanical/diagram treatment;
- history/scene treatment;
- optional anatomy direction.

Required workflow:

```text
E1 shared visual foundation
→ E2 golden-master implementation
→ actual Simulator screenshots
→ one contact sheet
→ primary/owner visual review
→ explicit direction approval
→ only then migrate remaining pages
```

If the owner rejects the direction, revise the golden masters rather than propagating them.

---

## 8. Previous small fixes to retain

Already landed and still valid:

- Pyramids caption safe fitting/wrapping;
- Body Teeth target contrast improvement;
- generic headless page-transition settle repair.

These fixes solve real local defects but do not constitute visual acceptance.

---

## 9. Current local-agent authority

Rolling pointer:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Current rule:

```text
DO NOT run another broad 43-page visual recapture yet.
DO NOT start final pointer/responsive acceptance yet.
DO NOT bulk-redraw all pages.
```

Next implementation work is **E1 + E2** from the visual reauthoring plan, ending in a small curated prototype evidence set for review.

---

## 10. `libpng` warning

Prior headless runs emitted:

```text
libpng error: bad adaptive filter value
```

No broad visible missing-asset/fallback pattern was identified in the old evidence. The warning remains unresolved diagnostic evidence and must not be attributed to a specific cause without direct proof.

Do not let speculative warning repair derail the graphics reauthoring unless new evidence points to a concrete asset failure.

---

## 11. Acceptance still pending

```text
golden-master visual direction approval
complete visual migration
interaction visual-language pass
pointer vs semantic-keyboard parity sample
pre-reader/no-reading final acceptance
responsive viewport/profile matrix
narration owner acceptance/integration
physical Acer/Pi acceptance
```

Only after final visual/input/pre-reader/responsive Simulator gates pass may the Encyclopedia become:

```text
SOURCE + SIMULATOR ACCEPTED / NARRATION ACCEPTANCE PENDING
```

---

## 12. Current authorities

```text
docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md

docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
skills/greia-visual-authoring/SKILL.md
```
