# Greia Encyclopedia v0.1 — Visual Reauthoring Plan

**Status:** ACTIVE SUBPLAN — E1/E2 SOURCE IMPLEMENTED; RUNTIME BUILD + SIMULATOR GOLDEN-MASTER REVIEW CURRENT  
**Date:** 2026-08-28  
**Parent visual authority:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Stable visual architecture:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Forensic audit:** `docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md`  
**Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

This is a **bounded Activity-level visual reauthoring subplan**, not a competing platform implementation plan. The platform R7 architecture plan remains the primary blocking platform authority.

The Encyclopedia runtime/navigation/research architecture is healthy enough to preserve. The old visual layer is not. This plan replaces "polish the existing procedural pages" with a controlled art-system reauthoring.

---

# 1. Goal

Turn the existing mechanically complete 43-page Encyclopedia into a cohesive, beautiful, low-resource Greia experience that feels like a **living illustrated discovery book / toy diorama**, not a Pygame prototype or collection of classroom diagrams.

The target experience for a young child is:

> **I see a beautiful thing → I know what looks touchable → I activate it → the picture comes alive and teaches me something.**

Audio remains the primary explanatory channel for pre-readers. Text supports the experience but must not rescue unclear graphics.

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
- no important information carried by tiny line details.

## 2.3 Depth language

Each page should normally have at least three readable depth bands:

```text
background / atmosphere
hero subject / scene
foreground / discovery controls / character
```

Depth may be created with separate authored layers, contact shadow, overlap and local lighting. It does not require expensive continuous parallax.

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

# 3. New Encyclopedia visual grammar

The Encyclopedia needs reusable visual primitives of its own, implemented on existing Greia seams rather than inventing a second UI/runtime framework.

## 3.1 Page shell

Every page may share:

- quiet title region;
- content-safe hero region;
- internal Back control region;
- optional presenter region;
- optional caption/narration-support ribbon;
- protected Greia Home remains platform-owned and untouched.

The visual shell must not force identical compositions. It defines safe zones and consistent control behavior only.

## 3.2 Discovery token

Replace the old floating white circles with a reusable **DiscoveryToken** presentation.

Desired states:

```text
idle
focused
pressed
activated / recently discovered
```

Visual treatment:

- tactile badge/sticker/felt medallion shape;
- clear pictogram;
- visible shadow or raised rim;
- focus = lift + warm outline/glow + slight scale;
- press = short depress/squash;
- activation = short pop/pulse and scene response.

The semantic input remains `PageCommand` / pointer hit-testing. This is presentation, not new navigation authority.

## 3.3 Hero stage

Factual entry pages should use a reusable layout helper that reserves a dominant **hero stage** rather than letting every page invent coordinates.

Baseline intent at 1024×600:

```text
hero scene / subject: ~55–70% of usable visual attention
interactive discovery tokens: ~15–25%
presenter + caption/support: remaining space
```

Exact percentages are design guidance, not a renderer API.

## 3.4 Presenter integration

Canonical characters must be used intentionally.

Possible roles:

- pointing toward selected discovery;
- reacting to activation;
- holding a prop/lens/flashlight;
- peeking from foreground;
- standing partly behind foreground framing.

Do not reduce every presenter to a tiny mascot in the bottom-right corner.

Presenter should usually be roughly 150–220 logical px tall at 1024×600 when present, adjusted by composition.

## 3.5 Caption support

Keep captions secondary.

- audio explains the fact;
- caption may repeat a short key sentence for readers;
- no long paragraph boxes;
- use a quiet tactile ribbon/speech card with good wrapping;
- never let text dominate the hero illustration.

---

# 4. Page archetypes

The 43 pages do not need 43 unique layout systems. Define a small set of reusable archetypes.

## A. Discovery Home

Purpose: choose one of six domains.

Target:

- an illustrated "book opening / discovery room / meadow of portals" composition;
- six large mini-diorama portals, each visually depicting the domain;
- portals are spatially composed, not generic launcher cards;
- Leo acts as guide, visibly connected to the scene;
- selection lifts/illuminates one portal.

## B. Section Gallery / World

Purpose: choose one final topic.

Examples:

- Animals → explorer field table / habitat window set;
- Space → observatory / solar-system mobile;
- Earth & Nature → landscape field guide / layered terrain scene;
- Body → friendly anatomy discovery room, not a medical mannequin diagram;
- Machines → warm workshop bench with real object silhouettes;
- History → illustrated time trail / museum shelf / excavation table.

Subjects should look like authored miniatures/objects inside the world, not six plain white cards.

## C. Hero Subject + 4 Discoveries

Most factual pages.

Examples:

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

One large hero illustration + 3–4 discovery tokens + visual reveal state.

## D. Process / Transformation

Used where the fact is a sequence or process.

Examples:

```text
frog life cycle
rain cycle
fossil formation
dinosaur/fossil discovery
machine transfer
```

Prefer a visual strip/scene progression rather than four disconnected icons around a central object.

## E. System / Mechanism

Used when relationships matter more than one object.

Examples:

```text
gears
bridge load
lungs breathing
heart circulation
solar-system overview
```

These may retain more diagrammatic drawing, but the diagram must sit inside authored material/context and use polished pictorial elements.

---

# 5. Art-production architecture

## 5.1 REUSE / COMPOSE-ADAPT / CREATE ORIGINAL

For every important object, make an explicit decision.

### REUSE

Strong candidates:

- canonical characters;
- contact shadows;
- clouds;
- atmosphere/light overlays;
- rocks/grass/reeds where appropriate;
- shared UI/focus treatments where they genuinely fit.

### COMPOSE-ADAPT

Likely for:

- section backgrounds;
- nature/landscape framing;
- workshop/history settings;
- generic foreground props;
- atmospheric treatment.

### CREATE ORIGINAL

Required for much of the Encyclopedia's identity:

- animals;
- planets/astronomy hero assets;
- anatomy hero assets;
- specific machines;
- dinosaurs/mammoth/pyramids/cave art;
- topic-specific discovery pictograms.

Do not force a weak generic asset into a page merely because the library contains something related.

## 5.2 Source location

Activity-specific art lives under:

```text
activities/enciclopedia_greia/assets/source/
activities/enciclopedia_greia/assets/runtime/
```

Semantic subfolders may be introduced when page count makes them useful, but the six golden-master masters intentionally remain one shallow set while the direction is still under review. Do not create folder hierarchy for its own sake.

Keep source masters editable and runtime PNGs economical.

## 5.3 Runtime composition

Prefer existing Greia scene/visual seams where useful:

- `SceneDefinition`
- `SceneNode`
- `PygameSceneRenderer`
- canonical character renderer
- bounded PNG cache

Do not force every page into a TOML scene if a small Activity-local compositor/helper is simpler. The key rule is one bounded architecture, no per-page bespoke decode/scaling logic.

The golden-master tranche uses one Activity-local `VisualLibrary` facade with an explicit semantic-id map and bounded cache. Pages do not decode/scale art themselves.

## 5.4 Procedural drawing policy

Procedural primitives remain allowed for:

- focus rings;
- paths/arrows;
- measurement lines;
- particles;
- small diagram annotations;
- dynamic reveal overlays;
- true geometric educational content.

They should not be the primary final artwork for real-world subjects.

---

# 6. Golden-master phase — mandatory before bulk migration

Do **not** reauthor all 43 pages immediately.

Create a representative golden-master set that proves the new visual language on real runtime screens.

Required prototypes:

1. **Home** — proves portal/navigation language.
2. **Animals section** — proves section-world selection.
3. **Lion entry** — proves organic hero subject + discoveries.
4. **Saturn entry** — proves astronomy/material/glow while preserving low-cost runtime.
5. **Gears entry** — proves mechanisms can be beautiful without losing clarity.
6. **Pyramids entry** — proves history/diagram balance.

Optional seventh if needed to resolve anatomy direction:

7. **Body section or Heart entry**.

Why these:

- warm organic;
- dark space;
- technical mechanism;
- historical construction;
- section navigation;
- root navigation.

A single attractive animal page is not enough proof.

## Golden-master acceptance

Before bulk migration:

- capture actual 1024×600 Simulator pixels for all prototypes;
- produce one contact sheet;
- compare against the rejected current screenshots side by side;
- inspect at least one compact and one larger responsive row;
- user/owner explicitly approves the **direction**, not only correctness;
- only then lock reusable Encyclopedia presentation primitives.

If the owner does not like the direction, revise the golden masters. Do not propagate rejected aesthetics.

---

# 7. Migration phases after golden-master approval

## E0 — Freeze and forensic baseline **[COMPLETE]**

- [x] mechanical 43-page breadth proven;
- [x] old visual evidence reviewed;
- [x] systemic visual failure documented;
- [x] old art declared non-final;
- [x] broad acceptance churn stopped while visual direction is being replaced.

## E1 — Encyclopedia visual foundation **[SOURCE + RUNTIME-ART IMPLEMENTED; SIMULATOR GATE PASSED]**

Build only what multiple prototype pages truly share:

- [x] page-shell safe-zone/layout helper (`PageShellLayout`);
- [x] DiscoveryToken component/state language;
- [x] hero-stage safe region/composition contract;
- [x] caption ribbon/helper with adaptive fitting;
- [x] presenter placement reuses the existing shared `draw_presenter` seam plus explicit page composition; no second presenter framework added;
- [x] Activity-local asset loader facade over a bounded visual cache/runtime seam;
- [x] source/runtime folder convention and deterministic authoring-time build recipe;
- [x] focused source contracts for asset mapping/cache/hot-path/source/build invariants; local mirror 6/6 PASS;
- [x] real-checkout focused tests after runtime PNG generation;
- [x] final-SHA Greia Simulator launch/survival after current visual edits.

Avoid abstraction theatre: if a helper is used by only one page, keep it local until a second use proves a shared invariant.

## E2 — Golden masters **[SOURCE + RUNTIME ART + ACTUAL-PIXEL CAPTURE COMPLETE; OWNER DIRECTION PENDING]**

- [x] Home — source integrated with authored discovery-book scene;
- [x] Animals section — source integrated with authored field-table scene;
- [x] Lion — source integrated with authored hero scene + retained discoveries;
- [x] Saturn — source integrated with authored observatory scene + retained discoveries;
- [x] Gears — source integrated with authored workbench scene + retained mechanism model;
- [x] Pyramids — source integrated with authored historical diorama + retained build/reveal model;
- [x] six runtime PNG renditions built and committed on `main` (sha256 verified by `--check`);
- [x] actual 1024×600 Simulator screenshots;
- [x] representative activated-state screenshots;
- [x] compact responsive sample;
- [x] larger responsive sample;
- [x] actual Simulator contact sheet;
- [x] pre-reader/no-reading prototype review;
- [ ] owner direction approval.

**Hard gate:** no E3 before E2 direction approval.

## E3 — Section-page reauthoring

Reauthor all six section pages first so navigation feels coherent:

- [ ] Animals;
- [ ] Space;
- [ ] Earth & Nature;
- [ ] Body;
- [ ] Machines;
- [ ] History.

Run one six-section visual review, not six disconnected acceptance ceremonies.

## E4 — Entry migration by archetype

Migrate in coherent batches:

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

Each batch gets a contact sheet and targeted visual review. Do not run the full 43-page acceptance after every small asset correction.

## E5 — Interaction visual-language pass

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

Only now run a fresh complete 43-page capture against final graphics.

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

rather than runtime vector rendering or procedural reconstruction.

The committed golden-master build tool is:

```text
tools/build_encyclopedia_visual_assets.py
```

`CairoSVG` is authoring/maintainer tooling only. It must not become a Greia child-runtime or Activity runtime dependency.

## 8.2 Surface budget discipline

Avoid multiple unnecessary full-screen RGBA layers. Crop assets to meaningful bounds.

A 1024×600 RGBA surface is ~2.35 MiB before library/runtime overhead. Four full-screen independent decoded overlays already approach ~9.4 MiB. Therefore:

- keep backgrounds flattened when their layers never move independently;
- crop characters/props/FX tightly;
- cache only actual requested renditions;
- clear page-local/cache state on meaningful transitions where architecture permits;
- do not create per-resolution duplicate art unless evidence proves it necessary.

These are engineering estimates, not a claim of measured Acer memory acceptance.

The current golden-master `VisualLibrary` is hard-bounded; actual runtime PNG byte size/RSS must be recorded after local generation rather than inferred from source SVG size.

## 8.3 Animation cost

No particle swarms, per-pixel shaders, large alpha surfaces rebuilt every frame, or dynamic blur.

Use pre-authored glow/shadow overlays and simple transforms.

---

# 9. Visual acceptance rubric

Each golden master and later batch should be reviewed on a 1–5 scale, but scores are diagnostic rather than permission to average away a blocker.

Dimensions:

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

Minimum target before owner review:

- no dimension below 3;
- visual-quality dimensions should generally land at 4+;
- any child-navigation ambiguity is a blocker regardless of average.

The owner remains the final aesthetic authority.

---

# 10. Documentation and evidence

This plan is subordinate to the active Greia visual workstream.

During work:

- update `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md` checkpoint/progress;
- update `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`;
- update `encyclopedia/HANDOVER.md`;
- update `skills/greia-visual-authoring/SKILL.md` only if reusable contributor guidance changes;
- preserve curated review evidence under `docs/reviews/visual/` when a direction is important enough for future comparison;
- do not commit giant redundant screenshot dumps merely because the Simulator can generate them.

---

# 11. Immediate next action

**Do not run another broad 43-page visual acceptance now.**

The rolling local execution authority is:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md
```

Next exact tranche:

```text
refresh main
→ build six runtime PNGs from committed SVG masters
→ run focused tests + required local verification
→ commit/push runtime PNG pack
→ run final-SHA real Greia Simulator launch/survival
→ capture the six golden-master prototypes at 1024×600
→ capture representative ACTIVATE payoffs
→ inspect one compact and one larger responsive sample
→ produce one curated contact sheet
→ perform no-reading prototype review
→ STOP for owner visual direction approval
```

The previous headless capture-settle harness repair remains useful and should be preserved, but it does not justify another full 43-page capture before golden-master approval.

---

# 12. Progress ledger

## 2026-08-28 — E1/E2 source implementation tranche

- Added Activity-local `enciclopedia_presentation.py` with a bounded shared page-shell safe-zone model, tactile DiscoveryToken presentation, authored-scene placement, object focus treatment and adaptive caption ribbon.
- Extended `VisualLibrary` into the single hard-bounded Activity-local facade for canonical characters plus explicitly mapped authored runtime PNGs; page hot paths still do not decode or smoothscale assets.
- Kept `main.py` a thin composition root; it now passes the package root to the visual facade rather than teaching pages about filesystem paths.
- Authored and committed six editable 1024×600 SVG golden-master masters: Home discovery book, Animals field table, Lion savanna, Saturn observatory, Gears workbench and Pyramids diorama.
- Reauthored only the six required golden-master page sources. Stable semantic navigation, factual state models and audio cue IDs were preserved.
- Added authoring-only deterministic SVG→PNG build tool; no runtime SVG/CairoSVG dependency was introduced.
- Added focused source contracts covering source/build agreement, explicit semantic asset mapping, hard cache bounds and absence of page-local image decode/scale.
- Local mirror verification: **6/6 visual-foundation source contracts PASS; changed-source AST parse PASS**. This is source/static evidence only.
- Runtime PNG build/commit, focused tests on the real checkout, final-SHA Simulator launch/survival, actual visual contact sheet, responsive samples and owner direction approval remain pending.
- E3/E4 remain hard-blocked.

## 2026-08-28 — E2 runtime build + real Greia Simulator prototype capture (this work)

- Built the six 1024×600 runtime PNGs from the committed SVG masters using `tools/build_encyclopedia_visual_assets.py` (346 621 bytes total, all real 1024×600 8-bit RGB). Re-running `--check` after the build reported `PASS 6 Encyclopedia runtime PNGs match editable masters`.
- Pushed the generated PNG pack on `main` at SHA `08fe71b077d47b511c105bde5c2e8fdb88be7b92`. Reran `--check` and the focused Encyclopedia tests against the pushed tree: 6/6 PNGs still match, 19/19 focused tests PASS.
- Tightened `tests/test_encyclopedia_authoring_tools.py` so the runtime-cue vs voice-ledger parity check excludes the new `VisualLibrary.ART_ASSETS` scene keys (which are visual identifiers, not narration cues) from the over-broad string-constant heuristic. The fix loads the exact `ART_ASSETS` map as the single source of truth for "not narration".
- `make verify` on the real checkout: **1462/1462 PASS**.
- Added three permanent review tools to `tools/`:
  - `encyclopedia_v01_golden_master_capture.py` — one real Greia Shell session per golden-master page, navigates through the real launcher/profile/catalogue/profile-picker/Shell path, captures initial + ACTIVATE frames, exercises the protected Greia Home return.
  - `encyclopedia_v01_golden_master_review.py` — builds the curated 4-shot review set and the 3×2 primary contact sheet from the captured PNGs.
  - `encyclopedia_v01_golden_master_zip.py` — produces the non-committed owner-transfer ZIP.
- Captured 10 1024×600 PNGs from the headless Greia Simulator at SHA `08fe71b` (Home, Animals, Lion initial+ACTIVATE, Saturn initial+ACTIVATE, Gears initial+ACTIVATE, Pyramids initial+ACTIVATE). All six session jobs reported `PASS`. Every session exercised the protected Greia Home return at the platform-allocated home-hitbox.
- Captured one compact (1024×600 + `interface_size=compact`) and one larger (1280×800 + `interface_size=normal`) responsive row from the same Shell.
- Wrote `docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/` with the curated 4 PNGs, the 3×2 primary contact sheet, `REVIEW.md` and `layout-audit.json` (sourced from the real `PageShellLayout`, `PORTAL_CENTERS` and discovery-token centers, not invented).
- Wrote the non-committed owner-transfer ZIP `GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip` (677 KB) per the visual evidence contract.
- Pre-reader / no-reading review on the six prototypes: `PRE_READER_CORE_FLOW_PASS=yes`, `TEXT_REQUIRED_FOR_GAMEPLAY=no`, `NO_READING_FIRST_ACTION_PASS=yes`, `PRIMARY_INSTRUCTION_CHANNEL=visual`.
- Visible defects recorded honestly in `REVIEW.md` (sun vs Back button on Animals, right-most gear partly behind a rack silhouette on Gears) — neither blocks the gate, both are noted for the design pass.
- This evidence is `SIMULATOR VISUAL REVIEW` only. **Owner direction approval is still pending.** E3/E4 remain hard-blocked until that approval lands.


**Next exact action:** execute `docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md`; stop after the golden-master contact sheet/evidence for owner review.
