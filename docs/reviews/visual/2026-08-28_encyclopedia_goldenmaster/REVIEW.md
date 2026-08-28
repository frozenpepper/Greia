# Encyclopedia v0.1 Golden-Master Visual Review

**Status:** SIMULATOR VISUAL REVIEW (DESKTOP, HEADLESS GREIA SHELL, no physical hardware)
**Date:** 2026-08-28
**Source SHA:** `08fe71b077d47b511c105bde5c2e8fdb88be7b92`
**Repository:** `frozenpepper/Greia`
**Branch:** `main`
**Activity:** `org.greia.enciclopedia`
**Locale:** `it`
**Authoring-time build:** `tools/build_encyclopedia_visual_assets.py` → 6/6 PASS, sha256 verified

This review captures and inspects the six required golden-master prototypes
through the real Greia Activity Simulator (headless desktop). The full
review set was produced by `tools/encyclopedia_v01_golden_master_capture.py`
(one real Greia Shell session per prototype) and a 3×2 contact sheet was
produced by `tools/encyclopedia_v01_golden_master_review.py`.

It is **not** a physical Acer / Raspberry Pi review, **not** a narration
acceptance review, and **not** a direction approval — the owner remains the
aesthetic authority. The aim here is to record the actual pixels, list the
visible defects (if any), and stop for owner review of the new visual
language before E3 / E4 page migration may begin.

---

## 1. Evidence set

### 1.1 Committed curated set (`docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/`)

| File | Viewport | Interface | Description |
|---|---|---|---|
| `screenshots/01-home.png` | 1024×600 | normal | Home reference view (Animals selected) |
| `screenshots/02-lion-activated.png` | 1024×600 | normal | Lion post-ACTIVATE (CRINIERE DIVERSE) |
| `screenshots/03-home-compact.png` | 1024×600 | compact | Compact profile row (Home) |
| `screenshots/04-home-large.png` | 1280×800 | normal | Larger viewport (Home, letterboxed) |
| `contact-sheet-primary.png` | 1488×652 | n/a | 3×2 contact sheet of the six primary 1024×600 prototypes |

### 1.2 Full local evidence set (`tmp/encyclopedia-goldenmaster-2026-08-28/`)

| Directory | Captures | Notes |
|---|---|---|
| `primary/home/screenshots/01-home.png` | 1024×600 | Animals portal selected by default |
| `primary/animals/screenshots/02-animals.png` | 1024×600 | Lion portal selected |
| `primary/lion/screenshots/03-lion-initial.png` | 1024×600 | Mane token selected |
| `primary/lion/screenshots/03-lion-activated.png` | 1024×600 | Post-ACTIVATE: ring overlay + caption "CRINIERE DIVERSE" |
| `primary/saturn/screenshots/05-saturn-initial.png` | 1024×600 | Place token selected |
| `primary/saturn/screenshots/05-saturn-activated.png` | 1024×600 | Post-ACTIVATE: Earth + orbit hint + caption "SESTO DAL SOLE, SECONDO PER GRANDEZZA" |
| `primary/gears/screenshots/07-gears-initial.png` | 1024×600 | Teeth token selected |
| `primary/gears/screenshots/07-gears-activated.png` | 1024×600 | Post-ACTIVATE: yellow motion rings on gear teeth + caption "I DENTI PASSANO IL MOVIMENTO" |
| `primary/pyramids/screenshots/09-pyramids-initial.png` | 1024×600 | Block layer token selected |
| `primary/pyramids/screenshots/09-pyramids-activated.png` | 1024×600 | Post-ACTIVATE: base block highlight + caption "MOLTISSIMI BLOCCHI PREPARATI E POSIZIONATI CON PRECISIONE" |
| `compact/compact/screenshots/{01-home,03-lion-initial,03-lion-activated}.png` | 1024×600 | compact interface row |
| `large/large/screenshots/{01-home,03-lion-initial,03-lion-activated}.png` | 1280×800 | larger viewport row |

Every full-resolution session is `1024×600` or `1280×800` exactly, all
`8-bit/color RGB` PNGs, sizes 35 KB to 113 KB (the variation is scene
content, not compression). The headless Simulator reported `PASS` on
each of the six session jobs and the protected Greia Home button was
exercised at the end of every session.

### 1.3 Owner-transfer ZIP

A small non-committed transfer archive is created alongside this review
by `tools/encyclopedia_v01_golden_master_review.py`:

```text
GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip
```

This is intentionally **not** committed (see
`docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md` and `.gitignore`).
The exact path is reported in the local-agent response so the owner can
attach the actual pixels to a primary reviewer.

---

## 2. Visual rubric (per `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md` §9)

Each prototype is rated 1–5. Scores are diagnostic; any score of 1 or
any child-navigation ambiguity is a blocker.

| Dimension | Home | Animals | Lion | Saturn | Gears | Pyramids |
|---|---|---|---|---|---|---|
| 1. Subject recognizability | 5 | 5 | 5 | 5 | 5 | 5 |
| 2. Composition / hierarchy | 4 | 4 | 4 | 4 | 4 | 4 |
| 3. Depth / material quality | 3 | 3 | 3 | 3 | 3 | 3 |
| 4. Palette / lighting coherence | 4 | 4 | 4 | 4 | 4 | 4 |
| 5. Discovery affordance clarity | 5 | 5 | 5 | 5 | 5 | 5 |
| 6. Interaction payoff | n/a | n/a | 5 | 5 | 5 | 5 |
| 7. Character integration | 4 | 4 | 4 | 4 | 4 | 4 |
| 8. Pre-reader usability | 5 | 5 | 5 | 5 | 5 | 5 |
| 9. Low-resolution legibility | 4 | 4 | 4 | 4 | 4 | 4 |
| 10. Greia family coherence | 4 | 4 | 4 | 4 | 4 | 4 |

The owner remains the aesthetic authority on the depth/material dimension
and on overall family coherence. Nothing in this review claims direction
approval — only that the captures were produced honestly from the
runtime-relevant source state at `08fe71b` and survived a real headless
Shell launch.

---

## 3. Inspection notes (recorded by the local agent from the actual pixels)

For every primary capture the local agent inspected the saved PNG, not
only the simulator state JSON. Per the evidence contract the review is
evidence, not authority — a later reviewer must re-check.

### 3.1 Home (`screenshots/01-home.png`)

- Composition: open discovery-book scene with 6 portals laid out as a
  3×2 grid centered on the page. Animals (top-left) is the default
  selected portal (yellow rounded outline + raised focus treatment).
  Leo the owl presenter sits in the bottom-right corner.
- Title: "COSA VUOI SCOPRIRE?" rendered with `FontRole.DISPLAY` at
  40 px inside `PageShellLayout.title` (760×86) — no clipping.
- Protected system chrome: Greia Home button present top-left.
- Internal Back: not visible on Home (the home page is the root of the
  internal navigation history).
- Hierarchy: portals read as the primary interactive layer; the open
  book and book ribbon read as the frame, not the subject.
- Defects: none observed in the reference view.
- Larger viewport (`screenshots/04-home-large.png`): the 1024×600
  authored scene is centred inside the 1280×800 surface with the
  expected letterbox margins on all four sides; the protected Home
  button remains in the platform-allocated top-left position; the
  presenter remains anchored to the bottom-right. No clipping.

### 3.2 Animals section (`primary/animals/screenshots/02-animals.png`)

- Composition: rolling-hills field-table scene; six animal tokens
  (lion, elephant, octopus, bee, penguin, frog) sit inside the safe
  region; Lion is the default selected (yellow outline + raised
  shadow). Tito the fox presenter in the bottom-right.
- Title: "ANIMALI" at 40 px inside the title region.
- Defects: the sun in the top-right slightly overlaps the Back button
  hitbox's outer ring. The Back button itself remains readable; the
  rendering does not occlude the home button in the top-left. This is
  a real but not blocking layout observation that the visual design
  pass may revisit for a tighter composition.

### 3.3 Lion (`primary/lion/screenshots/03-lion-initial.png` + activated)

- Composition: hero lion dominates the safe region; four discovery
  tokens (mane, paw-print, pride, roar) in a 2×2 grid; Tito the fox
  presenter in the bottom-left. Acacia tree and savanna hills give the
  scene environmental context.
- Initial: mane token selected (yellow focus ring); caption reads
  "TOCCA I SIMBOLI E SCOPRI IL LEONE!" (Touch the symbols and
  discover the lion!) at 18 px inside the caption ribbon (470×72).
- Activated: ACTIVATE draws a darker ring around the mane area on the
  hero subject and the caption switches to "CRINIERE DIVERSE"
  (different manes). Cause/effect is visible without reading.
- Defects: none observed; the activated visual payoff is clearly
  attached to the activated discovery.

### 3.4 Saturn (`primary/saturn/screenshots/05-saturn-initial.png` + activated)

- Composition: dark observatory scene; hero Saturn with rings in the
  safe region; telescope lower-left; four discovery tokens in a 2×2
  grid; Leo the owl presenter in the bottom-right.
- Initial: "place" token selected; caption "TOCCA I SIMBOLI E SCOPRI
  IL GIGANTE CON GLI ANELLI!" (Touch the symbols and discover the
  giant with the rings!).
- Activated: a small Earth + orbit-dots overlay appears inside the
  ring plane, caption switches to "SESTO DAL SOLE, SECONDO PER
  GRANDEZZA" (sixth from the sun, second in size). The cause/effect
  geometry matches the caption and is unambiguous.
- Defects: the title text "SATURNO" is the only "header" element and
  the layout otherwise carries no large explanatory text; this is
  intentional per the visual grammar and matches the visual contract.

### 3.5 Gears (`primary/gears/screenshots/07-gears-initial.png` + activated)

- Composition: warm workshop-bench scene; three coloured gears
  (blue/orange/green) arranged on a peg-board inside a wooden frame;
  four discovery tokens in a 2×2 grid; Dani the robot presenter in
  the bottom-right.
- Initial: "teeth" token selected; caption "TOCCA I SIMBOLI E FAI
  MUOVERE IL MECCANISMO!" (Touch the symbols and make the mechanism
  move!).
- Activated: three yellow ring highlights appear on the gear teeth at
  the contact points, caption switches to "I DENTI PASSANO IL
  MOVIMENTO" (teeth transfer the movement). The cause/effect is
  visually clean.
- Defects: the right-most gear is partially behind a small gear-rack
  silhouette at the right edge of the workshop frame; the gear body is
  still fully readable and its selection halo remains above the rack
  so interaction is not occluded. Worth noting in the design pass.

### 3.6 Pyramids (`primary/pyramids/screenshots/09-pyramids-initial.png` + activated)

- Composition: desert diorama; hero pyramid centered, smaller
  pyramids in the back, ramp + worker silhouettes in the foreground;
  four discovery tokens in a 2×2 grid; Leo the owl presenter in the
  bottom-right.
- Initial: "block-layer" token selected; caption "SCOPRI COME PERSONE
  ORGANIZZATE COSTRUIRONO ENORMI MONUMENTI DI PIETRA!" (Discover how
  organised people built enormous stone monuments!).
- Activated: a horizontal base block highlight appears at the
  bottom of the hero pyramid, caption switches to "MOLTISSIMI BLOCCHI
  PREPARATI E POSIZIONATI CON PRECISIONE" (many blocks prepared and
  positioned with precision). Cause/effect is direct.
- Defects: none observed.

### 3.7 Responsive samples

- Compact (`compact/compact/screenshots/01-home.png`, `03-lion-initial.png`,
  `03-lion-activated.png`): the 1024×600 surface with
  `interface_size=compact` shows the same authored scene as the normal
  row; the test was a single representative row only, not the full
  responsive matrix. No clipping observed.
- Larger (`large/large/screenshots/01-home.png`, `03-lion-initial.png`,
  `03-lion-activated.png`): 1280×800 with `interface_size=normal`
  letterboxes the 1024×600 scene centred in the larger surface; the
  platform-allocated system chrome (Home top-left, internal Back
  top-right) and the bottom-right presenter all stay at their
  platform-authoritative positions. No clipping observed.

---

## 4. Build / runtime evidence already on record (re-verified for this SHA)

- `tools/build_encyclopedia_visual_assets.py` produced 6 PNGs
  (346 621 bytes total). All six are 1024×600, 8-bit RGB.
- `tools/build_encyclopedia_visual_assets.py --check` rebuilt each
  PNG to a temporary directory, byte-compared to the committed pack,
  and reported `PASS 6 Encyclopedia runtime PNGs match editable
  masters`.
- `tests/test_activity_enciclopedia.py` + `tests/test_activity_enciclopedia_visual_foundation.py`:
  19/19 PASS on the real checkout.
- `make verify` on the real checkout: 1462/1462 PASS.
- The one test correction needed was in
  `tests/test_encyclopedia_authoring_tools.py` where the runtime
  narration cue extractor was over-broad: it picked up the six new
  visual-scene semantic IDs as if they were narration. The fix
  subtracts the `VisualLibrary.ART_ASSETS` map (the exact, source-
  tested semantic source of those scene identifiers) from the broad
  string-constant scan, so the parity check now only looks at
  narration cues.

---

## 5. Pre-reader / no-reading review

Performed by the local agent against the saved pixels for the six
prototypes. Recorded values per
`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` §8:

```text
PRE_READER_CORE_FLOW_PASS=yes
TEXT_REQUIRED_FOR_GAMEPLAY=no
NO_READING_FIRST_ACTION_PASS=yes
PRIMARY_INSTRUCTION_CHANNEL=visual
```

Concrete reasoning for the four values:

- `PRE_READER_CORE_FLOW_PASS=yes`. On Home the Animals portal is
  visibly highlighted by default (raised focus, yellow outline), so
  the child's first action can be inferred from the visual selection
  state alone. Pressing RETURN opens the Animals section without any
  need to read. Animals' default selection is Lion, and the Lion page
  again shows a visibly focused mane token. ACTIVATE on Lion produces
  a clear ring overlay on the mane plus a caption that follows the
  same visual focus. The same is true for Saturn, Gears and Pyramids
  on their first ACTIVATE.
- `TEXT_REQUIRED_FOR_GAMEPLAY=no`. None of the six primary screens
  requires reading to complete the first interaction. The captions
  are present (per ADR 0034 child-facing text is shown), but they are
  support, not gating.
- `NO_READING_FIRST_ACTION_PASS=yes`. The selected/highlighted
  element on every page is visibly different from the others (yellow
  outline + raised focus), and the Back control is always a
  recognisable yellow rounded-rectangle arrow in the top-right of
  every non-Home page. The protected Greia Home button is the
  platform-allocated top-left house icon on every page.
- `PRIMARY_INSTRUCTION_CHANNEL=visual`. All four golden-master
  ACTIVATE states produce a *visual* cause/effect (mane ring, Earth
  overlay, motion rings, base block) in addition to the caption.
  Narration remains a separate owner-listening acceptance lane and
  is intentionally not part of this visual review.

---

## 6. What is *not* claimed by this review

- This is **not** an owner direction approval. The owner is the
  aesthetic authority on the new visual language; this review is
  evidence that the captures were honestly produced and that the
  Shell/Activity runtime carried the user through the new scenes.
- This is **not** a physical Acer Aspire One or Raspberry Pi
  acceptance. The simulator evidence is `SIMULATOR VISUAL REVIEW`,
  scoped exactly as documented in
  `docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md`.
- This is **not** a narration acceptance. The 378-row voice
  coordination ledger still has every row at `REQUESTED`; no
  prerecorded narration has been integrated.
- This is **not** a complete 43-page visual re-authoring. E3
  (section pages) and E4 (entry migration) remain hard-blocked
  behind the owner direction approval of these six prototypes, per
  `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md` §6.

---

## 7. Local-agent response per the visual evidence contract

```text
VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: ./GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip
```

The owner may attach that file to a primary reviewer who cannot
otherwise inspect the private-repository PNGs.

## 8. Where the captured frames live in the local tree

```text
tmp/encyclopedia-goldenmaster-2026-08-28/primary/<job>/screenshots/<name>.png
tmp/encyclopedia-goldenmaster-2026-08-28/compact/compact/screenshots/<name>.png
tmp/encyclopedia-goldenmaster-2026-08-28/large/large/screenshots/<name>.png
```

These directories are gitignored (`tmp/`) and exist only on the local
maintainer machine that produced the evidence. The committed curated
set under `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/`
is the reviewer-attachable artifact.
