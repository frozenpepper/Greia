# Greia Encyclopedia v0.1 — Visual Reauthoring Plan

**Status:** COMPLETE for E3 — E2 APPROVED; E3 SOURCE + 11-PNG RUNTIME + SIMULATOR ACCEPTED at 03bf76ac; E4 COMPLETE at 7b1f6b2c (2026-10-16); E5 interaction visual-language pass NEXT  
**Date:** 2026-08-28  
**Latest checkpoint:** 2026-10-16 — E4 COMPLETE (`7b1f6b2c`); E5 next  
**Current checkpoint:** 2026-08-30 — E3 ACCEPTED (see `docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime/REVIEW.md` (archived; see git history); evidence HEAD 69cf8966)  
**Parent visual authority:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Stable visual architecture:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Forensic audit:** `2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md` (archived; see git history)  
**Current E3 source review:** `SOURCE_REVIEW.md` (archived; see git history)  
**Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

This is a **bounded Activity-level visual reauthoring subplan**, not a competing platform implementation plan. The platform R7 architecture plan remains the primary blocking platform authority.

The Encyclopedia runtime/navigation/research architecture is healthy enough to preserve. The old visual layer was not. This plan replaces "polish the existing procedural pages" with a controlled art-system reauthoring.

---

# 1. Goal

Turn the existing mechanically complete 43-page Encyclopedia into a cohesive, beautiful, low-resource Greia experience that feels like a **living illustrated discovery book / toy diorama**, not a Pygame prototype or collection of classroom diagrams.

The target experience for a young child is:

> **I see a beautiful thing → I know what looks touchable → I activate it → the picture comes alive and teaches me something.**

Audio remains the primary explanatory channel for pre-readers. Text supports the experience but must not rescue unclear graphics.

The frozen v0.1 information architecture remains:

```text
1 Home
6 section pages
36 factual entries
43 executable pages total
```

Visual work is not permission to change that scope.

---

# 2. Visual thesis

## 2.1 Material language

Use a coherent hybrid of:

- cut-paper / felt-board silhouettes;
- soft painted storybook surfaces;
- toy-diorama shallow depth;
- subtle grain/texture baked into authored assets;
- warm contact shadows;
- restrained highlights and rim light;
- controlled atmospheric overlays.

Avoid photorealism, glossy 3D, generic flat-vector SaaS illustration, and raw geometric programmer art.

## 2.2 Shape language

- large, readable silhouettes;
- rounded but not amorphous forms;
- simplified internal detail only where it reinforces identity or learning;
- strong value separation between subject, interactive elements and background;
- no important information carried by tiny line details;
- real-world subjects must remain immediately recognizable at 1024×600.

For a section-selection subject, the recognition question is deliberately simple:

> **Can a child or adult name what this is immediately, without reading a label?**

If not, the silhouette is not finished.

## 2.3 Depth language

Each page should normally have at least three readable depth bands:

```text
background / atmosphere
hero subject / scene
foreground / discovery controls / character
```

Depth may be created with authored overlap, contact shadow and local lighting. It does not require expensive continuous parallax.

## 2.4 Motion language

Cheap motion only:

- 1–4 px float/bob;
- tiny rotations;
- short squash/pop on activation;
- low-count particles;
- one-shot reveal overlays;
- subtle light/fog/water/star motion;
- simple whole-object transforms.

Motion must enrich a good still image rather than compensate for a bad one.

---

# 3. Encyclopedia visual grammar

## 3.1 Page shell

Shared pages may use:

- quiet title region;
- content-safe hero region;
- internal Back control region;
- optional presenter region;
- optional caption/narration-support ribbon;
- protected Greia Home remains platform-owned and untouched.

The shell defines safe relationships; it must not force every page into the same composition.

## 3.2 Discovery controls

The old identical floating white circles were rejected.

Current accepted direction keeps one semantic interaction component while allowing **scene-native silhouettes** such as:

```text
felt tag
telescope card
workshop tag
excavation marker
```

States remain:

```text
idle
focused
pressed
activated / recently discovered
```

Focus must be visible without turning the scene back into a card-grid UI.

## 3.3 Hero stage

Factual entry pages reserve dominant visual attention for the actual subject/scene.

Baseline intent at 1024×600:

```text
hero scene / subject: ~55–70% of usable visual attention
interactive discoveries: ~15–25%
presenter + caption/support: remaining space
```

These are design targets, not renderer API percentages.

## 3.4 Presenter integration

Canonical characters should be composed into the scene rather than stamped into a corner.

Appropriate roles include:

- leaning over or peeking into a scene;
- pointing at a discovery;
- using a telescope/lens/notebook/tool;
- reacting from the foreground;
- standing partly behind foreground framing.

Runtime canonical character art remains the single source of truth; do not bake duplicate presenters into Activity SVG masters.

## 3.5 Caption support

Captions remain secondary:

- audio explains the fact;
- caption may repeat one short key sentence;
- no long paragraph boxes;
- adaptive fitting/wrapping rather than truncation;
- captions must not rescue ambiguous artwork.

---

# 4. Page archetypes

The 43 pages do not need 43 layout systems.

## A. Discovery Home

Purpose: choose one of six domains.

Current approved source direction:

- oversized illustrated open book;
- six miniature domain worlds;
- complete 3×2 portal block centered on the **book as one object**, not separately on the two pages;
- column centers `x=267 / 512 / 757` at 1024×600;
- the middle Space/Machines column deliberately straddles the `x=512` spine;
- Leo integrated as guide;
- selection/focus geometry matches the authored centers exactly.

## B. Section Gallery / World

Purpose: choose one final topic from an authored environment.

Current section family:

```text
Animals          continuous habitat
Space            observatory + live Solar System
Earth & Nature   layered landscape
Body             friendly anatomy discovery room
Machines         warm workshop/workbench
History          illustrated time/excavation trail
```

Subjects should appear as physical parts of the world, not six generic cards.

## C. Hero Subject + 3–4 Discoveries

Used by many factual entries:

```text
lion
elephant
octopus
bee
planets
heart
lungs
magnet
bicycle
bridge
mammoth
pyramids
```

One dominant subject + a small number of meaningful discovery affordances + an obvious visual response.

## D. Process / Transformation

Used where sequence matters:

```text
frog life cycle
rain cycle
fossil formation
dinosaur/fossil discovery
machine transfer
```

Prefer a scene/strip progression rather than disconnected symbols.

## E. System / Mechanism

Used when relationships matter more than one object:

```text
gears
bridge load
lungs breathing
heart circulation
solar-system overview
```

Mechanisms must remain physically/educationally believable. A gear page whose gears do not mesh is failed art, even if attractive.

---

# 5. Art-production architecture

## 5.1 REUSE / COMPOSE-ADAPT / CREATE ORIGINAL

### REUSE

Prefer accepted shared assets for:

- canonical characters;
- contact shadows;
- clouds;
- atmosphere/light overlays;
- generic rocks/grass/reeds where they genuinely fit;
- shared focus/control treatments.

### COMPOSE-ADAPT

Appropriate for:

- section backgrounds;
- nature/landscape framing;
- workshop/history settings;
- generic foreground props;
- atmospheric treatment.

### CREATE ORIGINAL

Expected for much of the Encyclopedia identity:

- animals;
- planets/astronomy hero assets;
- anatomy hero assets;
- specific machines;
- dinosaurs/mammoth/pyramids/cave art;
- topic-specific discovery pictograms.

Do not force a weak generic asset into a page merely because the library contains something related.

## 5.2 Source/runtime location

Activity-specific art lives under:

```text
activities/enciclopedia_greia/assets/source/
activities/enciclopedia_greia/assets/runtime/
```

Keep source masters editable and runtime PNGs economical.

No normal runtime SVG rasterization. CairoSVG remains authoring-only.

## 5.3 Runtime composition

Use the existing Activity-local `VisualLibrary` facade over a bounded cache.

Pages request explicit semantic art IDs. They do not scan directories, decode image files directly, or smoothscale in page hot paths.

E3 source integration deliberately registers the five new section semantic IDs before their PNG tranche is committed. Missing files return `None`, and the page uses its retained procedural fallback.

## 5.4 Procedural drawing policy

Procedural primitives remain appropriate for:

- focus rings;
- paths/arrows;
- measurement lines;
- particles;
- small annotations;
- dynamic reveal overlays;
- true geometric/mechanical educational state;
- the live orbiting Space model.

They are no longer the default final illustration method for recognizable real-world subjects.

---

# 6. Golden-master gate — direction now approved

Required prototypes were:

1. Home
2. Animals section
3. Lion
4. Saturn
5. Gears
6. Pyramids

The original E2/E2R runtime evidence was technically valid but aesthetically rejected. The owner then directed source repairs to the actual weak objects rather than another delegated bulk pass.

Owner-directed corrections included:

```text
Home      larger book; final centered 3x2 portal block
Animals   recognizable lion + elephant
Lion      unified head/face/mane + attached tail + connected legs
Gears     real toothed, physically meshing gear train
```

After reviewing those direct source corrections, the owner explicitly approved moving forward.

Therefore the **visual-direction gate is closed**:

```text
OWNER VISUAL DIRECTION: APPROVED
```

Evidence caveat:

The newest corrected SVG masters are newer than the old E2R runtime PNGs/Simulator screenshots. Direction approval does **not** mean the latest files have fresh final-SHA Simulator evidence. That runtime closure is folded into the current E3 build/review gate rather than running another separate design cycle.

---

# 7. Migration phases

## E0 — Freeze and forensic baseline **[COMPLETE]**

- [x] mechanical 43-page breadth proven;
- [x] old visual evidence reviewed;
- [x] systemic visual failure documented;
- [x] old art declared non-final;
- [x] broad acceptance churn stopped while visual direction was replaced.

## E1 — Encyclopedia visual foundation **[COMPLETE]**

- [x] `PageShellLayout` safe-zone/layout helper;
- [x] shared DiscoveryToken behavior/state language;
- [x] hero-stage composition contract;
- [x] adaptive caption ribbon;
- [x] presenter placement through existing canonical-character seam;
- [x] bounded Activity-local visual facade;
- [x] source/runtime convention and deterministic authoring build;
- [x] no runtime SVG/CairoSVG;
- [x] no page-hot-path image decode/scale;
- [x] focused source contracts;
- [x] prior real-Simulator proof of the architecture at its then-current source.

## E2 / E2R — Golden masters **[DIRECTION OWNER-APPROVED; LATEST RUNTIME RENDITIONS NEED REBUILD]**

- [x] Home source architecture;
- [x] Animals source architecture;
- [x] Lion source architecture;
- [x] Saturn source architecture;
- [x] Gears source architecture;
- [x] Pyramids source architecture;
- [x] prior six-PNG build + Simulator capture proved the technical pipeline;
- [x] owner inspected actual runtime pixels and rejected weak visual execution;
- [x] direct Home/Animals/Lion/Gears source repairs completed;
- [x] owner explicitly approved corrected visual direction;
- [ ] rebuild current corrected six PNGs;
- [ ] fresh exact-current-source runtime check (combined with E3 section gate).

## E3 — Section-page reauthoring **[SOURCE IMPLEMENTED / SOURCE-REVIEWED; RUNTIME REVIEW PENDING]**

Reauthor all six sections before any entry batch.

### Source state

- [x] Animals — corrected continuous habitat reference;
- [x] Space — authored observatory master around live Solar System;
- [x] Earth & Nature — one layered landscape;
- [x] Body — one discovery room with physical anatomy exhibits;
- [x] Machines — one workshop with recognizable objects/mechanisms;
- [x] History — one time/excavation trail.

Five new masters:

```text
space_gallery_observatory.svg
earth_gallery_landscape.svg
body_gallery_discovery_room.svg
machines_gallery_workbench.svg
history_gallery_time_trail.svg
```

First source review caught and corrected:

```text
Body      panel-like stations
Machines  weak miniature gears / weak bridge
History   ambiguous dinosaur silhouette
```

### Runtime integration state

- [x] five section semantic art IDs registered in bounded `VisualLibrary`;
- [x] Space source-wired while preserving live orbit model;
- [x] Earth source-wired with procedural fallback;
- [x] Body source-wired with procedural fallback;
- [x] Machines source-wired with procedural fallback;
- [x] History source-wired with procedural fallback;
- [x] build tool supports `--group golden|sections|all`;
- [x] source contract forbids partial E3 runtime pack (`0/5` or `5/5` only);
- [ ] build five E3 runtime PNGs;
- [ ] rebuild corrected six golden-master runtime PNGs;
- [ ] verify current 11-PNG pack against SVG masters;
- [ ] run focused tests / required repository verification;
- [ ] fresh final-SHA real Greia Simulator;
- [ ] review Home + six sections together in one runtime contact sheet;
- [ ] close E3.

**Hard gate (historical):** E4 was blocked until the six-section runtime family was accepted; that gate passed and E4 is complete.

## E4 — Entry migration by archetype **[COMPLETE 2026-10-16, `7b1f6b2c`]**

All five archetype batches below are authored as opaque 1024x600 storybook scenes with live moving parts in the E3 ink style (36 entries). Every target centre, input, model and cue is unchanged and the procedural fallback is kept. The canonical raster backend is **cairo** (documented in the build tool); `--check` reproduces 43/43 PNGs byte-for-byte (2.47 MiB). Build groups are `e4_*`. Fixes landed with it: a magnet-page crash on pointer events and a dinosaurs fallback draw crash. Evidence: SOURCE + headless desktop review only; the fresh full 43-page Simulator capture stays E7.

### E4-A Organic/nature

```text
lion elephant octopus bee penguin frog
volcano rain ocean tree rainbow
```

### E4-B Space

```text
sun mercury venus earth moon mars jupiter saturn uranus neptune
```

### E4-C Body

```text
heart lungs bones teeth senses
```

### E4-D Machines

```text
gears magnet bicycle airplane bridge
```

### E4-E History

```text
dinosaurs fossils mammoth cave_paintings pyramids
```

Each batch gets a targeted contact sheet/review. Do not run the full 43-page acceptance after every small correction.

## E5 — Interaction visual-language pass **[NEXT]**

After all pages have strong static art:

- [ ] review first activation payoff on every entry;
- [ ] strengthen subtle interactions;
- [ ] verify selected/focused states;
- [ ] verify keyboard/controller/pointer consistency;
- [ ] review presenter reactions;
- [ ] ensure audio cue timing matches visual response.

## E6 — Responsive + pre-reader acceptance

- [ ] 1024×600 large;
- [ ] 1280×800 normal;
- [ ] 1366×768 compact;
- [ ] 1920×1080 normal;
- [ ] 1111×700 custom/normal;
- [ ] pre-reader first-action review;
- [ ] no-reading navigation review;
- [ ] pointer/semantic parity sample;
- [ ] motion-disabled/static completeness.

## E7 — Final Simulator visual acceptance

Only after E4–E6 run a fresh complete 43-page capture against final graphics.

Narration remains a separate authoring/owner-listening lane.

---

# 8. Performance and low-resource constraints

Visual quality does not authorize expensive runtime behavior.

## 8.1 Build-time richness

Prefer:

```text
editable source master
→ build-time flattened/cropped PNG rendition
→ bounded runtime decode/cache
```

The canonical Encyclopedia visual builder is:

```text
tools/build_encyclopedia_visual_assets.py
```

Current groups:

```bash
python3 tools/build_encyclopedia_visual_assets.py --group golden
python3 tools/build_encyclopedia_visual_assets.py --group sections
python3 tools/build_encyclopedia_visual_assets.py --group all
```

`--check` may be combined with any group.

CairoSVG is maintainer tooling only and must not enter child runtime.

## 8.2 Surface budget discipline

Avoid unnecessary independent full-screen RGBA surfaces.

A 1024×600 RGBA surface is about 2.35 MiB before runtime/library overhead. Therefore:

- flatten static backgrounds;
- crop movable props/characters/FX tightly;
- cache only requested renditions;
- keep cache bounds explicit;
- avoid per-resolution duplicate art unless evidence requires it.

These are engineering estimates, not physical-Acer measurements.

## 8.3 Animation cost

No particle swarms, per-pixel shaders, dynamic blur or large alpha surfaces rebuilt every frame.

Use pre-authored lighting/shadow and simple transforms. Space's orbit model remains lightweight procedural educational state over one static authored observatory surface.

---

# 9. Visual acceptance rubric

Review each golden master/section/batch on:

1. **Subject recognizability**
2. **Composition / hierarchy**
3. **Depth / material quality**
4. **Palette / lighting coherence**
5. **Discovery affordance clarity**
6. **Interaction payoff**
7. **Character integration**
8. **Pre-reader usability**
9. **Low-resolution legibility**
10. **Greia family coherence**

Scores are diagnostic; blockers cannot be averaged away.

Minimum target before owner review:

- no dimension below 3;
- visual-quality dimensions should generally land at 4+;
- any child-navigation ambiguity is a blocker regardless of average;
- any real-world subject that is not immediately recognizable is a blocker;
- any mechanism that is physically misleading is a blocker.

The owner remains final aesthetic authority.

---

# 10. Documentation and evidence

During work:

- update the parent visual-workstream checkpoint/progress;
- update `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`;
- update `encyclopedia/HANDOVER.md`;
- update root `HANDOVER.md` when the active visual checkpoint changes materially;
- preserve meaningful comparison/review records under `docs/reviews/visual/` (archived; see git history);
- do not commit giant redundant screenshot dumps;
- do not convert source-only inspection into a Simulator claim.

Current reviews:

```text
2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md (archived; see git history)
docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/ (archived; see git history)
docs/reviews/visual/2026-08-29_encyclopedia_owner_direct_repairs/REVIEW.md (archived; see git history)
SOURCE_REVIEW.md (archived; see git history)
```

---

# 11. Immediate next action

Do **not** run a broad 43-page visual acceptance and do **not** begin E4.

Current exact gate:

```text
build corrected six golden-master PNGs
+ build five E3 section PNGs
→ verify all 11 current SVG/PNG renditions
→ focused Encyclopedia tests
→ required repository verification
→ commit/push complete current runtime art
→ fresh exact-SHA real Greia Simulator
→ capture/review Home + all six section pages as one family
→ if accepted, mark E3 complete and unblock E4
```

The owner explicitly asked the primary agent to perform the current visual-authoring work directly. Local agents do not take this Encyclopedia visual work (the old local-agent work order stays on HOLD and was archived 2026-10-30) unless the owner later changes that instruction.

---

# 12. Progress ledger

## 2026-08-28 — E1/E2 source implementation tranche

- Added Activity-local `enciclopedia_presentation.py` with page-shell safe regions, DiscoveryToken presentation, authored-scene placement, object-focus treatment and adaptive caption ribbon.
- Extended `VisualLibrary` into the hard-bounded Activity-local facade for canonical characters plus explicitly mapped authored runtime PNGs.
- Kept `main.py` a thin composition root.
- Authored six editable 1024×600 SVG golden-master masters: Home, Animals, Lion, Saturn, Gears and Pyramids.
- Reauthored only the six required golden-master page sources; semantic navigation, factual models and audio cue IDs were preserved.
- Added authoring-only deterministic SVG→PNG build tool; no runtime SVG/CairoSVG dependency.
- Added focused source contracts covering source/build agreement, asset mapping, cache bounds and absence of page-local image decode/scale.
- Local mirror verification passed the source/static contracts at that stage.
- E3/E4 remained blocked pending runtime/owner review.

## 2026-08-28 — E2 runtime build + real Greia Simulator prototype capture

- Built the six 1024×600 runtime PNGs and verified byte agreement through `--check`.
- Pushed the generated pack at `08fe71b077d47b511c105bde5c2e8fdb88be7b92`.
- Focused Encyclopedia tests and `make verify` passed on that then-current tree.
- Added permanent golden-master capture/review/ZIP tooling.
- Captured Home, Animals, Lion, Saturn, Gears and Pyramids through the real Greia Shell/Simulator path, including representative ACTIVATE states and protected Greia Home return.
- Captured compact/larger samples and performed the pre-reader/no-reading prototype review.
- This established technical pipeline evidence, not permanent aesthetic approval.

## 2026-08-28 — E2R visual refinement at `8fa41a3`

- Reworked token silhouettes to scene-native forms while keeping one interaction/state component.
- Removed baked presenters; runtime canonical characters remained the identity authority.
- Strengthened ACTIVATE payoffs for Lion, Saturn, Gears and Pyramids.
- Re-ran focused tests, build check, `make verify`, six real Simulator sessions, protected Home returns and four ACTIVATE captures successfully at that then-current state.
- Owner later rejected visible defects in the resulting real pixels. Green technical evidence was retained only for its actual scope.

## 2026-08-29 — owner-directed golden-master correction and direction approval

- Owner identified four concrete blockers in the real E2R pixels: Home book/card fit, Lion disconnected anatomy, Animals ambiguous lion/elephant, and non-meshing/non-gear-like Gears.
- Primary agent repaired the actual repository source directly; no delegated art pass and no generated mockup substitution.
- Home book enlarged, then the complete 3×2 portal block was centered on the book at `x=267/512/757`, with middle cards intentionally crossing the spine; `home.py` pointer/focus centers were updated identically.
- Animals lion/elephant were redrawn as immediately recognizable full-body silhouettes without moving semantic target centers.
- Lion face/head/mane/tail/body continuity and visible legs were corrected.
- Gears became a physically meshing toothed train and educational reveal coordinates were aligned to the actual contacts.
- Owner reviewed these direct corrections and explicitly approved moving forward with the plan.
- Runtime PNGs/screenshots from the prior E2R capture remain stale for exact-current-source evidence.

## 2026-08-29 — E3 six-section source tranche

- Kept corrected Animals as the section-world reference.
- Added five authored section masters: Space observatory, Earth landscape, Body discovery room, Machines workbench and History time trail.
- First source contact review caught three defects before persistence: Body was still too panel-like, Machines gear/bridge silhouettes were weak, and History's dinosaur was ambiguous. All three were corrected.
- Local source renders for the five new masters parse as valid 1024×600 SVG and rasterize to 1024×600 RGB PNGs.
- Registered the five E3 semantic art IDs in the existing bounded `VisualLibrary`.
- Source-wired Space/Earth/Body/Machines/History to authored scenes with retained procedural fallback while generated E3 PNGs are absent.
- Preserved Space's continuously orbiting Sun/planets/Moon as live teaching state inside the authored observatory.
- Extended the build tool with explicit `golden`, `sections` and `all` groups.
- Extended the visual-foundation contract so E3 generated art is staged atomically: 0/5 during source work or 5/5 when committed; partial section packs are forbidden.
- Added `SOURCE_REVIEW.md` (archived; see git history).
- E3 runtime PNG build, fresh tests/verify, exact-SHA Simulator and six-section runtime review remain pending. E4 remains blocked.

## 2026-10-16 — E4 entry migration complete (SOURCE / DESKTOP VISUAL REVIEW)

`7b1f6b2c` completed E4: nature (elephant, octopus, bee, penguin, frog, volcano, rain, ocean, tree, rainbow), space (sun to neptune inside the Saturn observatory, each with a teaching prop), body (heart model, lungs in a bell jar, X-ray skeleton, mouth model, mirror face; no mannequin, nothing gory), machines (magnet, bicycle, airplane, bridge) and history (dinosaurs, fossils, mammoth, cave paintings) were authored as opaque 1024x600 scenes with live moving parts in the accepted ink style. No behaviour contract changed. The cairo backend is the canonical rasterizer and `--check` reproduces 43/43 PNGs byte-for-byte (2.47 MiB). A magnet-page crash on pointer events and a dinosaurs fallback draw crash were fixed. **E5 (interaction visual-language pass) is next**, then E6 responsive/pre-reader acceptance and E7 fresh complete Simulator capture. Not done: Simulator visual review, native narration lane.

