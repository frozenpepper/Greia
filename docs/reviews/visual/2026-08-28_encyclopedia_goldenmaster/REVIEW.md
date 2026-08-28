# Encyclopedia v0.1 Golden-Master E2R — Visual Review

**Status:** SIMULATOR VISUAL REVIEW (DESKTOP, HEADLESS GREIA SHELL)
**Date:** 2026-08-28
**Source SHA:** `8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f` (pushed to `origin/main`)
**Reviewed repository head:** `8fa41a3e9ab4b8cff6cce9607c32492fedc6ae8f`
**Evidence:** `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` plus full local evidence at `tmp/encyclopedia-goldenmaster-2026-08-28-e2r/`
**Activity:** `org.greia.enciclopedia` (built-in, real Greia Shell)
**Locale:** `it`

This is the E2R refinement pass mandated by
`docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/PRIMARY_REVIEW_2026-08-29.md`.
Every required correction in
`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` §4 was addressed
on the same six golden-master pages; no other Encyclopedia page was
touched. The owner remains the aesthetic authority; this is
**SIMULATOR VISUAL REVIEW** evidence only.

---

## 1. Evidence validity

The evidence is valid for the runtime-art source state at `8fa41a3`:

- the six 1024×600 runtime PNGs are committed and sha256-verified by
  `tools/build_encyclopedia_visual_assets.py --check`;
- `tests.test_activity_enciclopedia + visual_foundation`: 19/19 PASS;
- `make verify` on the real checkout at `8fa41a3`: 1462/1462 PASS;
- all six golden-master sessions launched through the real Greia Shell
  profile-picker/launcher path;
- every session survived ≥ 12 s after first Activity frame, exercised
  `RETURN` (ACTIVATE) on Lion/Saturn/Gears/Pyramids, and ended with the
  protected Greia Home click at the platform home-hitbox returning to
  `mode=activities` followed by clean SIGTERM/SIGKILL escalation;
- the recurring `libpng error: bad adaptive filter value` line is
  still present in the child log. Per §7 of the local-agent brief, the
  E2R work does not guess a cause; the warning remains an unresolved
  diagnostic and is recorded unchanged.

---

## 2. Page-by-page visible changes (vs. PRIMARY_REVIEW 2026-08-29 baseline)

### 2.1 Home

- Six portals are now miniature illustrated worlds on small picture
  cards: animals habitat vignette, space observatory with telescope,
  Earth landscape, friendly body, warm workbench, excavation diorama.
  Each portal has its own ground/sky band and a small authored prop.
- Leo sits over the book on the right, looking down into the page
  (runtime canonical character at the integrated perch); a small
  magnifying glass floats above the book on the left.
- The default selected portal (Animals) is still clearly highlighted
  by the existing raised focus patch.
- The protected Greia Home button is preserved top-left; the internal
  Back area is clear.

### 2.2 Animals

- The sun moved from the top-right (where it previously crowded the
  Back button) to the top-left. The Back area is now clear.
- The six animals are placed on small habitat props: lion on a rock,
  elephant in the field, octopus on a coral, bee on a flower, penguin
  on an ice floe, frog on a lily pad. The scene is one continuous
  landscape with three readable depth bands (sky / hills / pond and
  sand).
- Tito peeks in the foreground grass (runtime canonical character),
  not in a corner stamp.
- The default selected animal (lion) is still clearly highlighted.

### 2.3 Lion

- The mane is the visual focus, with concentric ring detail and
  layered savanna hills in the background. Acacia tree and grass
  tufts give the scene context. The sun is now top-right so the Back
  area is clear.
- Tito points at the lion from the foreground-left (runtime
  canonical character).
- Discovery tokens are scene-native **felt tags** (rounded paper with
  punch hole) instead of identical white circles. Hit geometry,
  focus / recent state, and selection are unchanged.
- First ACTIVATE: two growth rings + 8 spike marks + a mane color
  shift. The change is visible at a glance without reading the
  caption.

### 2.4 Saturn — reference exemplar preserved

- Deep space palette retained. The planet has an atmospheric halo,
  banding detail, ring tilt, Cassini-like ring gap, a glow, a
  highlight and a storm spot.
- The scene adds a wall compass, a star chart on the floor, and a
  tripod-mounted telescope in the foreground. Leo sits beside the
  telescope (runtime canonical character at the integrated perch).
- Discovery tokens are scene-native **telescope cards** (rounded
  rectangle with inset frame and corner stars). The page now uses a
  different silhouette from Lion, Gears, and Pyramids.
- First ACTIVATE: sun marker on the left, a 34-dot orbit path
  crossing the upper part of the scene, a small Earth along the
  orbit, and a Saturn marker on the right. The child can read
  "Saturn is the sixth planet from the sun" visually.

### 2.5 Gears

- Real workshop wall with hanging tools (wrench + hammer on pegs),
  a pegboard shelf, a small chalkboard with a chart, and a
  blueprint. Wooden workbench with wood grain, edge highlights, and
  four corner bolts.
- Three gears (blue / orange / green) sit on the bench and mesh
  correctly. The small green gear is on its own shaft at the right
  with no rack collision.
- Dani stands on the right side of the bench, holding a wrench
  toward the gears (runtime canonical character at the integrated
  perch).
- Discovery tokens are scene-native **workshop tags** (rivet plate
  with four corner rivets).
- First ACTIVATE: three large contact-point rings at the meshing
  boundaries plus three small motion arrows above each contact
  showing direction of motion transfer.

### 2.6 Pyramids

- Hero pyramid with capstone, light/dark sides, subtle block seams
  (no classroom grid).
- Three **authored** workers: one pulling a sledge loaded with
  blocks, one carrying a block on his shoulder, one supervisor
  pointing with a staff. No more stick figures.
- Wooden ramp on the right side of the hero pyramid.
- Leo integrated left foreground in a field-guide role, with a
  small field notebook on the ground next to him.
- Distant pyramids for depth.
- Discovery tokens are scene-native **excavation markers** (small
  stake + flag base).
- First ACTIVATE: an outlined base block at the bottom of the hero
  pyramid plus two label arrows pointing at it. The block-layer
  reveal is now visually emphatic.

---

## 3. Specific E2R checklist from the primary review

| # | Required correction | Result |
|---|---|---|
| 1 | discovery controls no longer read as identical floating white instrumentation circles | done (felt tag / telescope card / workshop tag / excavation) |
| 2 | presenters are compositionally connected to each scene | done (Leo on book, Tito peeking in grass, Tito pointing at lion, Leo at telescope, Dani at bench, Leo as field guide) |
| 3 | each page has visibly stronger material/depth treatment baked into authored art | done (paper grain overlay, 3+ depth bands, contact shadows, scene props) |
| 4 | Home domains read as miniature worlds rather than abstract icons | done |
| 5 | Animals composition/habitat placement is tightened and the Back/sun collision is gone | done |
| 6 | first activation payoff on Lion/Saturn/Gears/Pyramids is visually stronger without relying on caption text | done |
| 7 | Gears rack/gear overlap is corrected | done (green gear on its own shaft, no rack) |
| 8 | Pyramids workers/construction foreground feels illustrated rather than stick-figure/prototype | done (authored people in robes with head wraps) |
| 9 | the low-resource architecture and semantic behavior remain unchanged | done (no source or runtime changes outside the six pages; token interaction state, semantic input, page engine, navigation) |
| 10 | capture only the same six golden masters again, not the full 43-page catalogue | done |

---

## 4. Visible defects observed in E2R (recorded honestly)

- **Pyramids activated**: the caption ribbon partially overlaps the
  bottom of the Leo figure when Leo is in field-guide pose. The
  visual change itself is clear (outlined base block + label
  arrows), but the caption could be slightly shorter or moved up
  to give Leo more headroom.
- **Saturn**: Leo is partially behind the telescope, which is
  intentional (he is observing through it), but the head
  silhouette touches the barrel. Reads fine in motion; worth a
  small pose adjustment if a future revision occurs.
- **Gears**: the rightmost tag (rack) sits on the wood-grain right
  edge; it is fully readable but a fraction of its right edge is
  close to the wood-bench edge highlight. Not a clipping problem.
- **Home**: the Body portal's heart character sits on a subtle
  pink background that some displays may render slightly cooler
  than the rest; the silhouette is unambiguous.
- **Animals**: the felt tag token silhouettes are very pale; in
  screenshots the contrast against the green hills is fine but on
  lower-contrast monitors the Animals section page could be
  rebalanced later. Not a blocker.

No text clipping, no truncation, no broken hierarchy, no occluded
protected chrome.

---

## 5. Pre-reader / no-reading review (per `LOCAL_AGENT_NEXT.md` §8)

Recorded against the six E2R prototypes:

```text
PRE_READER_CORE_FLOW_PASS=yes
TEXT_REQUIRED_FOR_GAMEPLAY=no
NO_READING_FIRST_ACTION_PASS=yes
PRIMARY_INSTRUCTION_CHANNEL=visual
```

Reasoning:

- The default-selected portal/animal/discovery is always visibly
  raised and clearly the largest/most-illuminated thing on the
  page. Pressing `RETURN` opens it without needing to read.
- Activated states now show cause/effect without depending on
  captions: lion mane growth rings, Saturn orbit path, Gears
  contact-point rings + motion arrows, Pyramids outlined base
  block + label arrows.
- The Back control is a recognisable yellow rounded-rectangle
  arrow on every non-Home page. The protected Greia Home button
  is the platform-allocated top-left house icon on every page.
- Home/Animals use visual portals/animals, not text lists.
- Captions remain secondary accessibility/reader support.

---

## 6. Visible things E2R deliberately did not touch

- page engine, navigation, state architecture, lifecycle, input
  vocabulary, semantic-id ↔ discovery-center contract;
- the four "preserve" decisions listed in §3 of the local-agent
  brief (open book, continuous Animals world, Lion dominant hero,
  Saturn dark observatory);
- `PageShellLayout` safe regions, title geometry, caption-ribbon
  geometry, the `VisualLibrary` hard-bounded cache, the build/
  check pipeline;
- the remaining 37 Encyclopedia pages (E3/E4 remain
  hard-blocked).

---

## 7. Owner-transfer archive

```text
GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip
```

(Built at final-SHA `8fa41a3` by `tools/encyclopedia_v01_golden_master_zip.py`.
Not committed; see `.gitignore`.)

## 8. Local evidence tree (gitignored, not committed)

```text
tmp/encyclopedia-goldenmaster-2026-08-28-e2r/<job>/screenshots/<name>.png
tmp/encyclopedia-goldenmaster-2026-08-28-e2r-compact/compact/screenshots/<name>.png
tmp/encyclopedia-goldenmaster-2026-08-28-e2r-large/large/screenshots/<name>.png
```

Full 10-capture primary set per job, plus compact and larger
responsive samples for Home and Lion.
