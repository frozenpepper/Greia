# Greia Encyclopedia v0.1 — detailed implementation and content plan

**Status:** ACTIVE SUBORDINATE FEATURE PLAN  
**Created:** 2026-08-27  
**Target:** first coherent, offline, bilingual (Italian/English) Greia encyclopedia release  
**Runtime target:** first-generation Acer Aspire One floor, plus normal Greia ARM/x86 peers  
**Planned v0.1 scale:** 1 home page + 6 section pages + 36 final entries = **43 executable pages**

---

## 0. Why this document exists

This plan is deliberately detailed because the encyclopedia will be built over many ChatGPT sessions while a separate local agent can independently generate requested audio.

Every future encyclopedia session should be able to answer, without reconstructing previous conversation:

- what the encyclopedia is;
- what it is not;
- how its internal page system works;
- which v0.1 pages are planned;
- which pages are complete;
- which factual claims still need research;
- which audio has been requested, recorded, reviewed or superseded;
- what the next exact implementation tranche is.

This plan is the long-lived design/sequencing authority for the encyclopedia feature. It does **not** supersede Greia repository ADRs, source contracts, the repository active blocking plan, or Activity-authoring rules.

---

# 1. Product thesis

The Greia Encyclopedia is not a miniature Wikipedia and not a menu of text articles.

It is a **visual discovery Activity for pre-readers and early readers**:

1. choose a broad world visually;
2. enter a lively section page;
3. touch a subject;
4. discover a few memorable ideas through picture, motion, sound and short spoken character narration;
5. move laterally to another interesting subject.

The child should be able to use the core experience without reading.

Text remains useful as a caption/support layer for older children, parents, accessibility and language reinforcement, but no essential navigation or explanation may depend exclusively on text.

The target emotional response is:

> "I touched something and it came alive, and one of my Greia friends told me something interesting."

Not:

> "I opened an article and had to read a lesson."

---

# 2. Core architecture decision: tiny engine, executable pages

## 2.1 The encyclopedia is one Greia Activity

The encyclopedia should eventually be registered as one first-party Activity, tentatively:

```text
technical id: org.greia.encyclopedia
working folder when integrated: activities/enciclopedia_greia/
runtime: python / Pygame
interaction profile: pointer or hybrid, finalized during E1
locales v0.1: it, en
```

The current `encyclopedia/` directory is an authoring/foundation workspace so unfinished work does not enter Activity discovery prematurely.

## 2.2 Each section and entry is a page object

The engine knows only that a page:

- has a stable page ID;
- can enter/leave;
- receives bounded semantic input/events;
- updates with `dt`;
- draws itself;
- may request navigation to another page;
- may request a prerecorded semantic audio cue;
- may record a local "discovered" fact through the Activity's approved state/event seam later.

A page can otherwise be unique.

Examples:

```text
space.solar_system
    -> slowly orbiting planets

earth.volcano
    -> cross-section + pressure/eruption sequence

body.heart
    -> pulsing heart + simplified circulation animation

machines.gears
    -> linked gear train the child can turn

history.fossils
    -> brush/scrape reveal interaction
```

The page engine must never evolve into a giant configuration language just to avoid writing Python.

## 2.3 Sections and final entries use the same page contract

There is no architectural distinction between "section", "subsection", "entry", "interactive exhibit" and "topic page".

Those are content roles.

Technically they are pages.

That lets a section be as interactive as an entry. The Solar System section can itself be one of the strongest encyclopedia experiences rather than a passive menu.

## 2.4 Page-local complexity is allowed; giant scripts are not

A small page may be:

```text
pages/animals/lion/page.py
```

A complex page may be:

```text
pages/earth/volcano/
    page.py
    model.py
    renderer.py
    particles.py
    assets/
    research/
```

`page.py` remains the page composition/entry module, not necessarily its entire implementation.

Apply Greia Activity engineering standards:

- cohesive objects;
- thin composition roots;
- composition over inheritance;
- polymorphism at genuine substitution seams only;
- no giant `main.py`;
- no giant page scripts merely because "each page is Python";
- reuse shared Greia primitives where they already own the behavior;
- promote an encyclopedia helper only after repeated semantics justify it.

---

# 3. Runtime constraints and non-goals

## 3.1 No speech recognition

Do not design voice search, open-ended child questions, speech commands or pronunciation recognition.

The reference child hardware and young-child pronunciation make this an inappropriate v0.1 assumption.

Navigation is visual/touch/pointer/controller based.

## 3.2 No runtime TTS

There is no general on-device narration synthesis requirement.

All v0.1 spoken encyclopedia content is prepared ahead of time and packaged.

This includes:

- canonical Lilli/Leo/Flash/Tito/Momo narration;
- Dani's robotic system-TTS identity;
- any deterministic system-TTS asset used for pronunciation-critical material.

System/native TTS is an **authoring-side producer**, not something the child machine must run live.

## 3.3 No runtime AI or factual retrieval

No runtime LLM, web search, dynamic fact generation or network lookup.

All factual claims are finite, reviewed and sourced during authoring.

## 3.4 No heavy simulation

Pages should fake complexity intelligently.

Allowed examples:

- `sin/cos` orbits;
- sprite state machines;
- 20–50 bounded particles;
- simple spring/tween interpolation;
- small procedural curves;
- cached transformed sprites.

Avoid:

- general physics engines;
- fluid simulation;
- large particle counts;
- runtime vector tessellation in hot loops;
- per-frame asset decoding/scaling;
- expensive blur/shader systems;
- uncontrolled allocation.

## 3.5 No fixed encyclopedia visual template

Do not force every entry into:

```text
title
picture
four buttons
fact card
```

Consistency comes from:

- Greia system chrome;
- typography;
- interaction affordances;
- character presentation;
- audio behavior;
- navigation;
- input semantics;
- page transitions;
- performance discipline.

The subject chooses the explanatory interaction.

---

# 4. Internal engine: intentionally small

The first engine should own only recurring mechanics that genuinely belong to the encyclopedia as a whole.

## 4.1 Planned engine responsibilities

```text
EncyclopediaApp
    Greia Activity lifecycle and top-level frame loop
    owns one PageNavigator

PageNavigator
    current page
    optional bounded back stack inside the Activity
    page transition requests

PageRegistry
    stable page-id -> factory mapping
    explicit catalogue, not runtime filesystem magic

EncyclopediaPage
    minimal lifecycle contract

PageContext
    narrow services passed to pages:
        localization/text lookup
        prerecorded semantic audio playback
        navigation
        prepared/cached assets
        page/discovery state
        safe viewport facts
        approved Activity event/storage seam as implemented

EncyclopediaAudio
    semantic cue resolution
    one presenter-voice channel policy
    replay/cancel behavior
    bounded preload/cache strategy

EncyclopediaProgress
    Activity-local discovered-page state only
    later emits factual Activity events through Greia
```

## 4.2 What the engine must not own

Do not put these into the engine merely because several pages could theoretically use them:

- volcano physics;
- orbit geometry;
- skeleton construction;
- fossil brushing;
- animal animation;
- gear simulation;
- specific fact wording;
- section taxonomy;
- individual page art layouts.

A small reusable helper can emerge only when several implemented pages show the same semantic need.

## 4.3 Explicit registry over dynamic discovery

For v0.1 prefer an explicit Python registry/catalogue generated or edited during authoring.

Avoid clever runtime import walking.

Reasons:

- simpler package validation;
- easier source review;
- clearer missing-page failures;
- no hidden filesystem semantics;
- easier low-resource startup;
- easier deterministic tests.

If authoring later becomes tedious, a build-time catalogue generator may produce the explicit runtime registry.

---

# 5. Navigation and child UX

## 5.1 Navigation depth

Normal exploration depth should stay shallow:

```text
HOME
  -> SECTION
      -> ENTRY
```

Entries may link laterally to related entries.

Do not expose scientific classification hierarchies to a preschool child unless a particular page makes them fun and meaningful.

## 5.2 Home page

The home page presents six large visual worlds:

1. Animals
2. Space
3. Earth & Nature
4. My Body
5. Science & Machines
6. Long Ago

No reading is required to identify them. Each receives a strong illustration/symbol and optional spoken cue.

The home page itself should feel alive but calm: small ambient movement only, not six competing animations.

## 5.3 Section pages

Each section page is an interactive illustrated scene or exhibit, not a grid unless a grid is genuinely the clearest representation.

Examples:

- Space = miniature Solar System with slow orbits.
- My Body = friendly body silhouette with softly pulsing/highlighting areas.
- Science & Machines = workshop table with moving gears, magnet, bicycle wheel, wing and bridge.
- Long Ago = horizontal visual time journey with different "windows" into the past.

## 5.4 Entry pages

A normal entry should aim for:

- one strong central visual idea;
- 2–5 meaningful things to touch;
- 3–5 short factual narration cues;
- one especially memorable interaction or transformation;
- one easy path back;
- optional links to 1–3 related pages.

Not every entry needs all of these. Some subjects are best with one excellent interaction and two facts.

## 5.5 Spoken content length

Default target per spoken cue:

```text
roughly 4–12 seconds
one idea
natural sentence
easy to interrupt/replay
```

Avoid minute-long narration.

Total entry narration should usually remain well under two minutes even if every optional cue is played.

---

# 6. Presenter/character philosophy

Characters are authored into pages; the runtime does not "decide who knows what."

Affinities guide authors:

```text
Lilli  -> wonder, creativity, stories, imagination, gentle observation
Leo    -> warm oldish savvy knowledge, patient explanation, history/language
Flash  -> motion, speed, energetic demonstrations
Tito   -> animals, nature, exploration, investigation
Momo   -> music, emotion, playful experiments, surprises
Dani   -> logic, numbers, machines, patterns; deliberately robotic
```

Use supporting characters sparingly. The encyclopedia must not become a talking cast show that blocks exploration.

Generic praise/retry should come from Greia shared utterance families rather than new custom encyclopedia recordings.

---

# 7. Factual-content contract

Every factual sentence that will ship must be researched before it enters the voice queue.

## 7.1 Per-entry research file

When an entry is implemented, create:

```text
pages/<section>/<entry>/research/facts.md
```

For every semantic fact cue record:

```text
semantic cue ID
canonical meaning
source organization/title
source URL or stable publication identifier
publication/retrieval date where relevant
second corroborating source when quantitative/surprising/nuanced
child-safe simplification note
Italian wording
English wording
```

## 7.2 Source preference

Prefer:

- NASA/ESA/space agencies;
- NOAA, USGS, meteorological/geological agencies;
- recognized museums;
- universities;
- peer-reviewed/expert-reviewed sources;
- major scientific institutions;
- trusted historical/archaeological institutions.

Do not use model memory as provenance.

## 7.3 Accuracy over cute myths

Avoid common child-encyclopedia falsehoods and over-simplifications.

Examples of traps to check explicitly during research:

- "the tongue has separate taste zones";
- "blood is blue inside the body";
- "the Great Wall is visible from the Moon";
- "dinosaurs and humans lived together";
- "airplane lift is explained by one simplistic Bernoulli story";
- misleading planet size/distance scales;
- anthropomorphic animal motives presented as scientific fact.

If the visual is deliberately schematic, say so in source comments and do not let narration imply scale fidelity.

---

# 8. v0.1 content scope: 43 pages

The first version is intentionally broad enough to prove the engine across very different explanatory modes, but small enough to finish.

## 8.1 Page 00 — Home

### `home`

Purpose:
- teach the encyclopedia's interaction language;
- expose six sections visually;
- host one short welcome cue;
- remain fast and quiet.

Signature behavior:
- each section illustration has a tiny idle motion;
- selecting one gives immediate visual focus and enters it;
- no text required.

---

# 9. Section A — Animals (6 entries)

Lead affinity: **Tito**, with occasional Leo/Lilli where appropriate.

Section page ID: `animals`

Section visual:
- illustrated "world window" composition showing sea, grassland, flowers, ice and pond;
- each planned animal is visible in a meaningful habitat fragment;
- ambient motion is sparse and bounded.

## A1 `animals.lion`

Core ideas:
- big cat;
- mane as a visible feature of many adult males;
- powerful paws/claws;
- social pride behavior;
- roar.

Signature interaction:
- touch mouth to hear a real lion sound;
- mane/paw hotspots animate/highlight.

## A2 `animals.elephant`

Core ideas:
- trunk;
- ears;
- herd/social life;
- very large body.

Signature interaction:
- move/spray water with the trunk;
- simple human/elephant scale silhouette.

## A3 `animals.octopus`

Core ideas:
- eight arms;
- suckers;
- camouflage;
- ink;
- unusual anatomy facts only after careful sourcing.

Signature interaction:
- change skin appearance against 2–3 backgrounds;
- ink-cloud reveal.

## A4 `animals.bee`

Core ideas:
- flowers/nectar/pollen;
- pollination;
- hive/colony;
- bee movement.

Signature interaction:
- guide/tap bee between flowers and watch pollen move.

## A5 `animals.penguin`

Core ideas:
- bird adapted to swimming;
- feathers/insulation;
- colony;
- egg/chick care simplified carefully by species.

Signature interaction:
- toggle waddle/swim;
- underwater movement much faster than land animation.

## A6 `animals.frog`

Core ideas:
- amphibian;
- frog life cycle;
- jumping;
- wet habitat.

Signature interaction:
- scrub/advance a simple egg -> tadpole -> froglet -> frog sequence.

---

# 10. Section B — Space (10 entries)

Lead affinity: **Leo** for knowledge/wonder, **Dani** for numbers/mechanics.

Section page ID: `space`

The section page **is the Solar System experience**.

Signature behavior:
- Sun centered;
- eight planets orbit slowly using lightweight math;
- visual spacing/planet diameters are explicitly schematic for usability;
- every displayed major planet is interactive in v0.1;
- Moon is reached from Earth and also appears as a small orbiting object when practical.

## B1 `space.sun`

Interaction:
- slow rotation;
- touch edge for a stylized prominence;
- compare Sun/Earth size with a schematic diagram.

## B2 `space.mercury`

Interaction:
- crater reveal / day-night rotation.

## B3 `space.venus`

Interaction:
- toggle outer cloud view and simplified surface view;
- emphasize thick atmosphere only after sourced wording.

## B4 `space.earth`

Interaction:
- rotate Earth;
- day/night terminator;
- link to Moon and Earth & Nature.

## B5 `space.moon`

Interaction:
- light-source phase demonstration;
- crater zoom.

## B6 `space.mars`

Interaction:
- rotate globe;
- reveal volcano/canyon landmark windows;
- optional rover visual only if licensing/art provenance is clean.

## B7 `space.jupiter`

Interaction:
- banded rotation;
- Great Red Spot focus;
- moon dots kept decorative unless individually supported.

## B8 `space.saturn`

Interaction:
- rotate/tilt ring view;
- reveal that rings consist of many pieces only with sourced child wording.

## B9 `space.uranus`

Interaction:
- visibly "sideways" rotation demonstration.

## B10 `space.neptune`

Interaction:
- animated cloud/wind streaks kept lightweight;
- no exaggerated speed claim until researched.

---

# 11. Section C — Earth & Nature (5 entries)

Lead affinity: **Tito** with Leo support.

Section page ID: `earth`

Section visual:
- one landscape cross-section from sky/clouds to mountains/volcano, river/tree and ocean.

## C1 `earth.volcano`

Core ideas:
- magma below ground;
- pressure/gas and rising molten rock explained carefully;
- lava at surface;
- volcanoes are not all constantly erupting.

Signature interaction:
- child increases a simple pressure/readiness state;
- stylized eruption with bounded particles and lava sprite layers;
- reset and replay immediately.

## C2 `earth.rain`

Core ideas:
- evaporation/condensation/precipitation as a simple water cycle;
- clouds consist of tiny droplets/ice crystals depending conditions.

Signature interaction:
- warm water -> rising vapor -> cloud -> rain loop.

## C3 `earth.ocean`

Core ideas:
- salt water;
- surface/deep layers;
- light fades with depth;
- huge habitat.

Signature interaction:
- drag/scroll downward through a shallow-to-deep schematic column.

## C4 `earth.tree`

Core ideas:
- roots;
- water transport;
- leaves/light;
- seasons without pretending all trees behave identically.

Signature interaction:
- toggle simplified seasonal states;
- reveal underground root layer.

## C5 `earth.rainbow`

Core ideas:
- sunlight + water droplets;
- light separates into colors;
- rainbow position relationship simplified carefully.

Signature interaction:
- move a sun/rain control until the rainbow appears.

---

# 12. Section D — My Body (5 entries)

Lead affinity: **Lilli** for gentle body curiosity, Leo where careful explanation helps.

Section page ID: `body`

Section visual:
- friendly neutral child silhouette;
- internal systems are illustrations, not graphic medical imagery;
- no body shame, fear or gendered assumptions.

## D1 `body.heart`

Core ideas:
- heart is a muscle/pump;
- beats continuously;
- moves blood around the body.

Signature interaction:
- tap/pump heart and watch simplified circulation loop.

## D2 `body.lungs`

Core ideas:
- breathing moves air;
- lungs expand/contract;
- oxygen/carbon-dioxide explanation only at appropriate simple level.

Signature interaction:
- drag or press to breathe in/out and watch lungs inflate.

## D3 `body.bones`

Core ideas:
- skeleton supports/protects;
- joints allow movement;
- bones are living tissue if used, only with clear source.

Signature interaction:
- assemble a few large skeleton regions or toggle skin/skeleton.

## D4 `body.teeth`

Core ideas:
- different tooth shapes/jobs;
- baby/adult teeth only if age-safe and clearly explained;
- basic care may be included without fear.

Signature interaction:
- tap tooth groups and see what kind of food motion each shape is good at.

## D5 `body.senses`

Core ideas:
- sight, hearing, smell, taste and touch;
- explicitly reject false "tongue taste map";
- multiple senses work together.

Signature interaction:
- choose a sensory object and see which senses help explore it.

---

# 13. Section E — Science & Machines (5 entries)

Lead affinity: **Dani** for mechanisms/numbers; Flash for motion demonstrations.

Section page ID: `machines`

Section visual:
- friendly workshop table with visible gear pair, magnet, bicycle wheel/chain, wing and small bridge.

## E1 `machines.gears`

Core ideas:
- touching teeth transfer motion;
- neighboring gears reverse direction;
- size changes speed/torque only with carefully simplified wording.

Signature interaction:
- drag one gear and watch connected gears rotate.

## E2 `machines.magnet`

Core ideas:
- attraction/repulsion;
- some materials respond strongly, many do not;
- poles.

Signature interaction:
- move two magnets and small material samples.

## E3 `machines.bicycle`

Core ideas:
- pedals, chain, gears, wheels;
- turning pedals transfers motion to wheel.

Signature interaction:
- turn pedal crank and watch chain/wheel.

## E4 `machines.airplane`

Core ideas:
- wings and moving air produce lift, explained without a false one-rule story;
- thrust moves aircraft forward;
- control surfaces change motion if included.

Signature interaction:
- simple wind/wing demonstration with visible airflow lines as schematic art.

## E5 `machines.bridge`

Core ideas:
- bridge carries loads to supports;
- different shapes distribute forces differently;
- no engineering formula requirement.

Signature interaction:
- place a small load on 2–3 simple bridge shapes and watch exaggerated-but-labelled deformation/force paths.

---

# 14. Section F — Long Ago (5 entries)

Lead affinity: **Leo**.

Section page ID: `history`

Section visual:
- simple journey backward through time;
- explicitly not to scale;
- no implication that every item existed at the same time.

## F1 `history.dinosaurs`

Core ideas:
- dinosaurs lived long before humans;
- different body plans/diets;
- birds are living dinosaurs only if phrased and sourced appropriately for age.

Signature interaction:
- switch among a few representative silhouettes/animations rather than creating separate v0.1 species pages.

## F2 `history.fossils`

Core ideas:
- remains/traces preserved in rock;
- fossilization takes a very long time and special conditions;
- paleontologists study evidence.

Signature interaction:
- brush away a top layer to uncover a fossil.

## F3 `history.mammoth`

Core ideas:
- woolly mammoths lived in cold environments;
- related to elephants;
- lived long after non-avian dinosaurs disappeared.

Signature interaction:
- reveal warm coat/body adaptations and compare silhouette with elephant.

## F4 `history.cave_paintings`

Core ideas:
- people made images on cave/rock surfaces long ago;
- animals/hands/geometric forms;
- meaning is not always known, so do not invent stories as fact.

Signature interaction:
- light a cave wall and reveal painted forms;
- optional safe "make a mark" interaction without modifying source art.

## F5 `history.pyramids`

Core ideas:
- ancient Egyptian pyramids were monumental tombs/complexes;
- built by organized human labor, not aliens/slave-myth simplification;
- enormous stone construction.

Signature interaction:
- stack a few schematic layers / reveal simple cross-section.

---

# 15. Content deliberately deferred beyond v0.1

Possible later packs/sections:

- music and instruments;
- art and color;
- countries/places;
- insects and tiny life expansion;
- ocean expansion;
- dinosaurs by species;
- ancient civilizations expansion;
- weather expansion;
- plants/food;
- vehicles;
- everyday technology;
- rocks/minerals;
- microbes;
- "how it is made";
- language/writing history.

Do not expand scope until the 43-page v0.1 list is either complete or deliberately revised by the owner.

---

# 16. Audio production architecture

## 16.1 Single coordination file

The canonical queue is:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Future implementation sessions append requests there.

The independent local recording agent may work from that file without waiting for encyclopedia code work.

## 16.2 Cue lifecycle

Statuses:

```text
PLANNED
REQUESTED
RECORDED_UNREVIEWED
OWNER_ACCEPTED
REJECTED_REDO
SUPERSEDED
BLOCKED
```

Only `REQUESTED` rows are ready to record.

`OWNER_ACCEPTED` means the human listening gate has passed.

## 16.3 Never silently change recorded wording

Once a row reaches `RECORDED_UNREVIEWED` or later:

- do not edit the exact text in place;
- do not reuse the same output filename for new wording;
- create a new semantic revision/cue row;
- mark the old row `SUPERSEDED`;
- update code only when the replacement is available or the page can fail soft.

This prevents this ChatGPT workstream and the local recording agent from racing.

## 16.4 Character path

Lilli/Leo/Flash/Tito/Momo:
- canonical voice IDs;
- Chatterbox Multilingual V3 authoring;
- one model process per batch;
- clear MLX cache + GC after every clip;
- human listening review;
- package only final reviewed audio.

Dani:
- `greia.dani.system-v1`;
- generated using the accepted deterministic/native system-TTS production path on the parent/development machine;
- packaged as static audio;
- never synthesized live on the child device.

Pronunciation-critical educational speech:
- system/native deterministic producer;
- static packaged audio;
- fluent human review where pronunciation is educational truth.

## 16.5 Page-local final audio

Final custom dialogue belongs with the page that owns it.

Target pattern:

```text
pages/<section>/<entry>/assets/audio/it/<filename>.ogg
pages/<section>/<entry>/assets/audio/en/<filename>.ogg
```

Section/root cues use their own page directories.

Review WAV masters remain in the external/local Greia voice-production workspace unless project policy later establishes a committed source-master location for encyclopedia-owned recordings.

## 16.6 Text/audio parity

Every custom cue needs:

```text
semantic ID
speaker
voice ID
speech kind
Italian exact text
English exact text
Italian final path
English final path
```

Displayed captions should communicate the same semantic meaning as the audio.

---

# 17. Asset and visual strategy

## 17.1 Runtime art should be cheap

Prefer:

- pre-rendered raster artwork;
- WebP/PNG where current Activity policy supports it;
- sprite sheets or small frame sets;
- pre-scaled/cached surfaces;
- simple line/shape overlays;
- bounded procedural particles;
- reusable Greia character expression assets.

## 17.2 Factual imagery can differ by subject

Do not force one medium:

- stylized Greia illustration for navigation and most interactive scenes;
- simplified diagrams for body/machines;
- scientifically informed reconstruction for historical subjects;
- real animal sounds when licensing/provenance permits;
- photographs only when they genuinely improve the child experience and fit visual/licensing constraints.

All third-party assets require provenance/license tracking under Greia policy.

## 17.3 Animation principle

Animate the **fact**, not decoration.

Good:
- planets orbit;
- lungs expand;
- gears rotate;
- volcano erupts;
- frog develops.

Bad:
- everything floats/bounces constantly just because animation is available.

Idle motion should be sparse to preserve attention and CPU.

---

# 18. Localization

v0.1 supports:

```text
it
en
```

Rules:

- semantic page IDs never contain localized wording;
- semantic cue IDs never contain localized wording;
- page logic never branches on language for gameplay;
- visible child words go through Greia localization/presentation policy;
- captions and audio remain semantically aligned;
- no one-locale presenter feature in a page advertised as complete for both locales.

Future language packs must not require page-code rewrites.

---

# 19. Progress and discovery

The encyclopedia is exploration, not a quiz.

Potential Activity-local state:

```text
discovered page IDs
first-discovery timestamps/order only if useful and bounded
possibly favorite/recent pages later
```

Platform-facing events may eventually include:

```text
encyclopedia.page_discovered
encyclopedia.section_explored
```

But exact event schema must be designed against current Greia event/progression authority during integration.

Do not directly grant badges or Stars from page code.

Possible future platform achievements:

- first discovery;
- 10 different discoveries;
- one section broadly explored.

Avoid completion anxiety such as "36/36 MUST BE FINISHED".

Undiscovered silhouettes may be used only if they encourage curiosity rather than pressure.

---

# 20. Performance budget

The encyclopedia must remain friendly to Acer Aspire One-class hardware.

Initial engineering targets to validate, not assume:

- 30 fps child-visible target is sufficient for most pages;
- no page requires 60 fps;
- no unbounded particle/list growth;
- no per-frame image decode;
- no per-frame font construction;
- no per-frame audio decode for frequently used cues;
- page exit releases page-specific large resources where useful;
- only current/near-current page assets need to remain hot;
- section pages should not preload all 36 entries;
- audio playback must not cause frame-loop stalls;
- persistent/event IPC must not be performed synchronously in a hot interaction if current Greia APIs are blocking; use the accepted platform/Activity pattern rather than inventing a new unsafe shortcut.

Actual acceptance requires Simulator and then physical Acer evidence for representative worst-case pages.

Representative performance pages:
- Solar System (continuous animation);
- Volcano (particles);
- Body/Heart (continuous diagram animation);
- Gears (continuous linked motion);
- a heavily illustrated section page.

---

# 21. Page authoring workflow for every entry

For each page, future ChatGPT sessions should follow this order.

## Step 1 — inspect current state

Read:
- `PLAN.md`;
- `HANDOVER.md`;
- `VOICE_RECORDING_REQUESTS.md`;
- relevant Greia Activity/visual/audio authorities.

## Step 2 — research

Create/update the page's `research/facts.md`.

No factual voice request before provenance is recorded.

## Step 3 — define the page's one memorable idea

Write in the page/module docstring or a concise adjacent note:

```text
what the child sees first
what they can touch
what changes when touched
what fact that interaction communicates
what the presenter says
what links lead elsewhere
```

## Step 4 — implement page

Keep page composition cohesive. Split model/rendering only when complexity warrants it.

## Step 5 — localization

Add Italian and English semantic strings/captions.

## Step 6 — append audio requests

Append exact requests to `VOICE_RECORDING_REQUESTS.md`.

Do not generate audio inside the child runtime.

## Step 7 — source tests

Test pure page behavior where practical:
- navigation targets;
- bounded state;
- interaction sequence;
- no duplicate IDs;
- deterministic reset;
- locale cue parity.

## Step 8 — visual/runtime acceptance

Once integrated as an Activity:
- run repository verification;
- run real Greia Simulator launch/survival/interaction/Home gate for runtime-relevant edits;
- later run representative physical Acer performance/visual acceptance.

## Step 9 — audio integration

When local-agent recordings appear:
- verify exact path/filename;
- verify locale/speaker;
- owner listens;
- mark `OWNER_ACCEPTED`;
- wire cue if not already wired;
- rerun affected runtime acceptance.

---

# 22. Implementation phases

## Phase E0 — Foundation workspace and contract

**Goal:** create a stable multi-session source of truth without prematurely registering a broken Activity.

Deliverables:
- `encyclopedia/README.md`;
- this plan;
- unified voice queue;
- encyclopedia-specific handover;
- tiny pure-Python page/navigation foundation;
- explicit v0.1 page catalogue.

Exit:
- all 43 planned page IDs are documented;
- voice coordination contract exists;
- no runtime Greia claim is made.

**Status: IN PROGRESS in the founding turn.**

## Phase E1 — Real Greia Activity shell

Goal:
- move/compose this foundation into the actual first-party Activity location;
- create valid `activity.toml`;
- thin `main.py`;
- `EncyclopediaApp`;
- Greia locale integration;
- protected Home behavior through platform authority;
- input profile;
- real PageNavigator;
- one renderable HomePage.

Acceptance:
- `make verify`;
- package validation;
- Simulator launches final source;
- Home page remains alive;
- one dummy/real section transition works;
- Greia Home returns cleanly.

No encyclopedia page content is called complete before this.

## Phase E2 — Home + six section pages

Build:
- home;
- animals;
- space/Solar System;
- earth;
- body;
- machines;
- history.

This validates:
- large illustrated navigation;
- continuously animated section;
- body diagram section;
- workshop scene;
- time/travel scene.

Queue section narration early so local voice work can proceed independently.

## Phase E3 — Six pilot entries, one per section

Implement first:

```text
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

Why these:
- camouflage/state visual;
- orbit/rings;
- particle event;
- biological loop;
- mechanical linked motion;
- reveal/brush interaction.

If these six can share the small engine without special-case engine growth, the architecture is probably healthy.

Exit review:
- inspect engine for accidental over-abstraction;
- measure startup/page-switch memory;
- simplify before scaling.

## Phase E4 — Complete Animals

Remaining:
- lion
- elephant
- bee
- penguin
- frog

Then perform section consistency review and animal-sound licensing/provenance review.

## Phase E5 — Complete Space

Remaining:
- sun
- mercury
- venus
- earth
- moon
- mars
- jupiter
- uranus
- neptune

Solar System page must have no dead displayed major planet.

Perform physical Acer performance pass because this is a continuous-animation stress case.

## Phase E6 — Complete Earth & Nature

Remaining after volcano:
- rain
- ocean
- tree
- rainbow

Review scientific simplifications as a set.

## Phase E7 — Complete My Body

Remaining after heart:
- lungs
- bones
- teeth
- senses

Perform child-safety/body-language review.

## Phase E8 — Complete Science & Machines

Remaining after gears:
- magnet
- bicycle
- airplane
- bridge

Perform "oversimplified mechanism" review, especially airplane lift.

## Phase E9 — Complete Long Ago

Remaining after fossils:
- dinosaurs
- mammoth
- cave paintings
- pyramids

Perform chronology/myth audit.

## Phase E10 — v0.1 closure

Required:
- all planned page states reconciled;
- all shipped facts sourced;
- Italian/English text parity;
- all required custom audio recorded and owner-accepted;
- no dead page links;
- no missing displayed planet;
- Activity package validation;
- full relevant source tests;
- final Simulator acceptance;
- representative physical Acer performance and interaction review;
- documentation/handover reconciliation;
- explicit list of deferred v0.2 ideas instead of scope creep.

---

# 23. Session sizing rule

This feature is intentionally built slowly.

Default future implementation tranche:

```text
1 complex page
or
2–3 simple pages
or
one engine/integration milestone
```

Do not mass-produce ten shallow entries in one turn.

A page counts as meaningfully advanced only when code, facts, localization, requested audio and acceptance state are all recorded.

---

# 24. Definition of page states

Use exactly these planning states:

```text
PLANNED
RESEARCHED
IMPLEMENTING
SOURCE_READY_AUDIO_PENDING
AUDIO_RECORDED_REVIEW_PENDING
SIMULATOR_READY
PHYSICAL_REVIEWED
COMPLETE
BLOCKED
```

`COMPLETE` means the page has all required v0.1 factual, bilingual and audio coverage plus runtime acceptance appropriate to its state.

---

# 25. v0.1 page ledger

| Page ID | Role | Signature interaction | State |
|---|---|---|---|
| `home` | root | six living visual worlds | PLANNED |
| `animals` | section | habitat collage | PLANNED |
| `animals.lion` | entry | roar + mane/paw hotspots | PLANNED |
| `animals.elephant` | entry | trunk spray + size compare | PLANNED |
| `animals.octopus` | entry | camouflage + ink | PLANNED |
| `animals.bee` | entry | flower-to-flower pollination | PLANNED |
| `animals.penguin` | entry | waddle/swim toggle | PLANNED |
| `animals.frog` | entry | life-cycle sequence | PLANNED |
| `space` | section | complete major-planet Solar System orbits | PLANNED |
| `space.sun` | entry | rotation + Earth scale compare | PLANNED |
| `space.mercury` | entry | crater/day-night reveal | PLANNED |
| `space.venus` | entry | clouds/surface toggle | PLANNED |
| `space.earth` | entry | rotation + day/night | PLANNED |
| `space.moon` | entry | phase demonstration | PLANNED |
| `space.mars` | entry | landmark reveal | PLANNED |
| `space.jupiter` | entry | bands + Great Red Spot | PLANNED |
| `space.saturn` | entry | ring tilt/rotation | PLANNED |
| `space.uranus` | entry | sideways rotation | PLANNED |
| `space.neptune` | entry | bounded wind/cloud motion | PLANNED |
| `earth` | section | sky-to-ocean landscape | PLANNED |
| `earth.volcano` | entry | pressure -> eruption | PLANNED |
| `earth.rain` | entry | water-cycle loop | PLANNED |
| `earth.ocean` | entry | surface-to-depth journey | PLANNED |
| `earth.tree` | entry | roots + seasons | PLANNED |
| `earth.rainbow` | entry | sun/rain alignment | PLANNED |
| `body` | section | friendly body map | PLANNED |
| `body.heart` | entry | beat + circulation | PLANNED |
| `body.lungs` | entry | breathe in/out | PLANNED |
| `body.bones` | entry | skeleton reveal/assemble | PLANNED |
| `body.teeth` | entry | tooth-shape jobs | PLANNED |
| `body.senses` | entry | multi-sense exploration | PLANNED |
| `machines` | section | interactive workshop | PLANNED |
| `machines.gears` | entry | linked gear train | PLANNED |
| `machines.magnet` | entry | attract/repel/materials | PLANNED |
| `machines.bicycle` | entry | pedal-chain-wheel | PLANNED |
| `machines.airplane` | entry | wing/airflow schematic | PLANNED |
| `machines.bridge` | entry | load/force-path compare | PLANNED |
| `history` | section | visual journey backward in time | PLANNED |
| `history.dinosaurs` | entry | representative dinosaur forms | PLANNED |
| `history.fossils` | entry | brush reveal | PLANNED |
| `history.mammoth` | entry | cold-adaptation compare | PLANNED |
| `history.cave_paintings` | entry | light/reveal rock art | PLANNED |
| `history.pyramids` | entry | layer/cross-section build | PLANNED |

---

# 26. Founding progress ledger

## 2026-08-27 — E0 foundation started

Decisions accepted from owner conversation and encoded here:

- encyclopedia engine remains tiny;
- encyclopedia is one Greia Activity, not a new platform runtime;
- every section/entry may be its own Python page script/module;
- pages are free to use subject-appropriate lightweight animation/interaction;
- Solar System planets may orbit continuously;
- volcano may erupt;
- no speech recognition assumption;
- no runtime/on-device narration TTS assumption;
- all normal presenter speech is prerecorded during content creation;
- Dani/system/pedagogical TTS is likewise generated ahead of time on parent/development hardware and packaged;
- Italian and English are the initial locales;
- a single unified voice request queue coordinates independent audio production;
- factual narration is not queued until its claim has authoring-time provenance.

Next exact phase after the E0 files are committed:
1. review the foundation files for coherence;
2. implement E1 real Activity shell against current Greia source contracts;
3. once the Home page shape is stable, expand the already-created navigation voice requests only as necessary;
4. then build E2 section pages and E3 pilot pages.
