# Greia Encyclopedia v0.1 — LOCAL AGENT NEXT TASK

## E2R — refine the same six golden masters, recapture, then STOP

The first golden-master Simulator run is complete and technically valid.

Primary review authority:

```text
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/PRIMARY_REVIEW_2026-08-29.md
```

Existing evidence:

```text
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/
```

Active plan:

```text
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

Current disposition:

```text
E1 VISUAL ARCHITECTURE: ACCEPTED
E2 RUNTIME/TEST/SIMULATOR EVIDENCE: VALID
E2 VISUAL DIRECTION FOR PROPAGATION: NOT YET APPROVED
E2R GOLDEN-MASTER REFINEMENT: REQUIRED
E3/E4: BLOCKED
```

This is a refinement of the existing six prototypes, **not a restart** and not permission to touch the remaining Encyclopedia pages.

---

# 1. Hard prohibitions

Do **not**:

```text
migrate any additional Encyclopedia page
run the 43-page traversal/recapture
start E3 or E4
generate or integrate narration
change the frozen factual/page scope
rewrite the page engine/navigation/state architecture
invent another asset/cache/scene system
add runtime SVG/CairoSVG or expensive runtime graphics
change protected Greia Home chrome
replace the six concepts wholesale without evidence
use GitHub-hosted Actions
```

Keep the existing authored-art/build/cache architecture and stable mechanics.

---

# 2. Refresh safely

From the existing Greia checkout:

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git rev-parse HEAD
```

Expected clean tree. If local/concurrent owner work exists, STOP and report it; do not discard or overwrite it.

Read before editing:

```text
AGENTS.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/PRE_READER_UX.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/REVIEW.md
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/PRIMARY_REVIEW_2026-08-29.md
```

---

# 3. Preserve what already works

Do not regress:

- Home open-book architecture;
- Animals continuous-world architecture;
- Lion dominant hero composition;
- Saturn dark observatory composition — current strongest reference;
- Gears real mechanism relationships/state model;
- Pyramids construction/diorama concept;
- semantic target-center contract for Home/Animals;
- keyboard/controller/pointer semantic behavior;
- bounded `VisualLibrary` and deterministic build/check flow;
- current title/Back/Home safe regions;
- first-action focus clarity.

This pass improves the visual language; it does not reopen the proven mechanics.

---

# 4. E2R required visual corrections

## 4.1 Discovery controls — highest-priority shared correction

Current problem: Lion/Saturn/Gears/Pyramids still use large pale circular controls that read like instrumentation floating over an illustration.

Keep the semantic hit/focus behavior, but redesign presentation so discoveries feel native to each scene.

Allowed examples:

```text
felt/paper specimen tags
pinned field-guide badges
workshop tokens/labels
observatory/telescope markers
archaeology/excavation markers
small scene-attached medallions
```

Requirements:

- no identical white-circle default across all four pages;
- strong low-resolution silhouette;
- focused state remains obvious;
- pressed/recent state remains tactile;
- do not reduce hit targets merely because visual chrome becomes subtler;
- do not make text labels necessary for understanding the first action.

Shared interaction/state logic may remain one component while page-specific skins/compositions vary.

## 4.2 Presenter integration

Current problem: presenters remain visually detached corner mascots.

Integrate the existing canonical character assets compositionally without skeletal rigs or heavy animation.

Target roles:

```text
Home: Leo visibly connected to/opening/pointing into the book
Animals: Tito peeking through grass / inspecting the habitat
Lion: Tito reacting beside the lion or foreground habitat
Saturn: Leo beside/using the telescope or observing Saturn
Gears: Dani beside the bench, holding/inspecting a tool or mechanism
Pyramids: Leo observing the construction foreground / notebook/field-guide role
```

Use whole-character placement, overlap and simple reaction states. Do not create a new character animation subsystem.

## 4.3 Material and depth

Current problem: clean but still generic flat-vector appearance.

Improve only through authored/build-time art:

- baked subtle paper/felt/paint variation;
- contact shadows;
- edge/overlap treatment;
- foreground/background separation;
- local light/rim accents where appropriate;
- shallow toy-diorama depth.

Do not use runtime shaders, blur, per-pixel effects, large dynamic alpha layers or expensive continuous parallax.

## 4.4 Home

Keep the open book.

Improve the six domain selections from simple symbols toward miniature illustrated worlds:

```text
Animals  -> habitat vignette
Space    -> tiny observatory/planet vignette
Earth    -> landscape/geology vignette
Body     -> friendly body-discovery vignette
Machines -> warm workbench/mechanism vignette
History  -> excavation/pyramid/time vignette
```

Selection still uses the existing 3x2 semantic centers.

## 4.5 Animals

- preserve the continuous landscape;
- remove the sun/Back crowding/overlap;
- improve habitat/context cues so animals feel intentionally placed rather than floating stickers;
- preserve the 3x2 semantic centers and target mapping;
- integrate Tito into the environment.

## 4.6 Lion

Keep the current hero layout and recognizability.

Improve:

- mane/body material depth;
- scene-native discovery presentation;
- Tito relationship to hero;
- first ACTIVATE payoff so the mane change/reveal is more visually emphatic than the current dark ring alone.

Do not replace the lion concept from scratch.

## 4.7 Saturn — reference exemplar

Preserve its palette, hero scale and dark observatory identity.

Improve only:

- discovery markers integrated into observatory/space composition;
- Leo visibly connected to telescope/observation;
- first ACTIVATE payoff larger/clearer than the current small Earth/orbit hint.

Do not make Saturn busier merely to match other pages.

## 4.8 Gears

- preserve true gear relationships and mechanism clarity;
- remove rack/green-gear visual collision;
- increase toy/workbench material depth;
- integrate Dani with the mechanism;
- replace floating white discovery circles with workshop-native controls;
- make first ACTIVATE movement transfer more visually obvious while remaining cheap.

## 4.9 Pyramids

- preserve construction/diorama framing;
- improve workers from stick-figure/prototype treatment into simple authored people/silhouettes appropriate to Greia style;
- reduce classroom-grid dominance on the main pyramid without losing the educational block structure;
- improve foreground tools/ramp/sledge material treatment;
- integrate Leo into the archaeology/construction observation role;
- strengthen first ACTIVATE block-layer reveal substantially.

Do not introduce unsupported historical specifics simply for decoration.

## 4.10 Caption hierarchy

Captions remain useful accessibility/reader support but must stay secondary to the visual teaching action.

If a caption currently explains something the activated image barely shows, strengthen the image rather than enlarging or lengthening the caption.

---

# 5. Source/build/test sequence

Work only in the existing E1/E2 source/runtime seams.

After visual edits:

```bash
python3 tools/build_encyclopedia_visual_assets.py
python3 tools/build_encyclopedia_visual_assets.py --check
python3 -m unittest \
  tests.test_activity_enciclopedia \
  tests.test_activity_enciclopedia_visual_foundation \
  tests.test_encyclopedia_authoring_tools
make verify
```

Expected:

```text
build --check: PASS 6
focused tests: all PASS
make verify: all PASS
```

If a test exposes a genuine changed contract, fix the smallest correct source/test boundary. Do not weaken a test just to allow the new art.

Before committing/pushing, refresh `origin/main` and reconcile safely. Do not overwrite concurrent work.

---

# 6. Simulator evidence after E2R

Once the revised runtime PNGs and source are pushed, capture from the exact final runtime-relevant SHA using the existing golden-master capture tooling / real Greia Simulator path.

Capture only:

```text
Home
Animals
Lion initial + activated
Saturn initial + activated
Gears initial + activated
Pyramids initial + activated
```

Plus the same narrow compact/larger sample if runtime-relevant layout changed.

Do **not** run the full 43-page traversal.

Produce:

- one 3x2 primary contact sheet;
- one concise initial-vs-activated comparison sheet for Lion/Saturn/Gears/Pyramids if tooling supports it;
- updated review notes listing visible defects honestly.

Specifically verify:

```text
discovery markers no longer read as generic floating white instrumentation
presenters are compositionally connected
material/depth is visibly stronger
Home portals read as miniature worlds
Animals sun/Back conflict is gone
Gears rack collision is gone
Pyramids foreground/people are no longer stick-figure prototype quality
first activation payoff is strong without reading caption text
protected Home/internal Back remain clear
```

---

# 7. Separate libpng diagnostic

Every current golden-master child log still emits:

```text
libpng error: bad adaptive filter value
```

Do **not** let this derail E2R and do not guess the cause.

If the warning still appears after the revised capture, record it unchanged. A separate narrow diagnostic may later identify the source asset/load path. Do not perform broad asset rewrites during E2R merely to silence an unattributed warning.

---

# 8. STOP condition

After the revised six-prototype evidence/contact sheet is complete and pushed/documented, STOP.

Return:

```text
final Git SHA
runtime-art SHA tested by Simulator
build --check result
focused test counts
make verify result
6-session Simulator result
new contact-sheet path
activated comparison path if produced
page-by-page visible changes
remaining visible defects
pre-reader/no-reading result
libpng warning present yes/no
anything unverified
```

Do not mark owner direction approved yourself.
Do not start E3/E4.

Current truthful state:

```text
MECHANICAL 43-PAGE FOUNDATION: PROVEN
E1 ARCHITECTURE: ACCEPTED
E2 FIRST GOLDEN-MASTER RUNTIME EVIDENCE: VALID
E2 FIRST ART PASS: PRIMARY REVIEW REQUIRES REFINEMENT
E2R: NEXT TASK
E3/E4: BLOCKED
OWNER DIRECTION APPROVAL: PENDING
NARRATION: SEPARATE / PENDING
PHYSICAL HARDWARE: SEPARATE / PENDING
```
