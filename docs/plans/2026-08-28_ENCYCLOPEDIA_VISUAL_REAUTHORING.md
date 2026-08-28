# Greia Encyclopedia v0.1 — Visual Reauthoring Plan

**Status:** ACTIVE SUBPLAN OF THE GREIA VISUAL WORKSTREAM  
**Date:** 2026-08-28  
**Parent visual authority:** `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`  
**Stable visual architecture:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`  
**Forensic audit:** `docs/reviews/2026-08-28_ENCYCLOPEDIA_GRAPHICS_FORENSIC_AUDIT.md`  
**Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

This is a **bounded Activity-level visual reauthoring subplan**, not a competing platform implementation plan. The platform R7 architecture plan remains the primary blocking platform authority.

The Encyclopedia runtime/navigation/research architecture is healthy enough to preserve. The visual layer is not. This plan replaces "polish the existing procedural pages" with a controlled art-system reauthoring.

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

Replace the current floating white circles with a reusable **DiscoveryToken** presentation.

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

Activity-specific art should live under a clear package-local structure such as:

```text
activities/enciclopedia_greia/assets/source/
activities/enciclopedia_greia/assets/runtime/
```

Recommended semantic subfolders:

```text
shell/
sections/
animals/
space/
earth/
body/
machines/
history/
discovery_tokens/
fx/
```

Keep source masters editable and runtime PNGs economical.

## 5.3 Runtime composition

Prefer existing Greia scene/visual seams where useful:

- `SceneDefinition`
- `SceneNode`
- `PygameSceneRenderer`
- canonical character renderer
- bounded PNG cache

Do not force every page into a TOML scene if a small Activity-local compositor/helper is simpler. The key rule is one bounded architecture, no per-page bespoke decode/scaling logic.

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

## E0 — Freeze and forensic baseline **[CURRENT]**

- [x] mechanical 43-page breadth proven;
- [x] current visual evidence reviewed;
- [x] systemic visual failure documented;
- [x] current art declared non-final;
- [ ] stop broad acceptance churn while visual direction is being replaced.

## E1 — Encyclopedia visual foundation

Build only what multiple prototype pages truly share:

- [ ] page-shell safe-zone/layout helper;
- [ ] DiscoveryToken component/state language;
- [ ] hero-stage composition helper;
- [ ] caption ribbon/helper;
- [ ] presenter placement/reaction helper;
- [ ] Activity-local asset loader facade over existing bounded visual cache/runtime seams;
- [ ] source/runtime folder conventions and deterministic build recipe;
- [ ] focused tests for containment/cache/fallback/layout contracts.

Avoid abstraction theatre: if a helper is used by only one page, keep it local until a second use proves a shared invariant.

## E2 — Golden masters

- [ ] Home;
- [ ] Animals section;
- [ ] Lion;
- [ ] Saturn;
- [ ] Gears;
- [ ] Pyramids;
- [ ] optional Body/Heart proof;
- [ ] actual Simulator contact sheet;
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

## 8.2 Surface budget discipline

Avoid multiple unnecessary full-screen RGBA layers. Crop assets to meaningful bounds.

A 1024×600 RGBA surface is ~2.35 MiB before library/runtime overhead. Four full-screen independent decoded overlays already approach ~9.4 MiB. Therefore:

- keep backgrounds flattened when their layers never move independently;
- crop characters/props/FX tightly;
- cache only actual requested renditions;
- clear page-local/cache state on meaningful transitions where architecture permits;
- do not create per-resolution duplicate art unless evidence proves it necessary.

These are engineering estimates, not a claim of measured Acer memory acceptance.

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

The next implementation tranche is:

```text
E1 visual foundation
+
E2 first golden-master prototypes
```

Start with Home + Animals section + Lion, then add Saturn/Gears/Pyramids using the same visual grammar. Produce actual Simulator screenshots and a contact sheet for owner review before bulk migration.

The previous headless capture-settle harness repair remains useful and should be preserved, but it no longer justifies another full 43-page capture before the graphics are reauthored.
