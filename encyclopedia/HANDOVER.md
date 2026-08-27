# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Construction state:** v0.1 source breadth complete  
**Runtime pages:** **43 / 43 planned executable pages**  
**Evidence:** **SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

## Owner direction that must not drift

- Keep the encyclopedia engine tiny and stable.
- Sections and final entries are executable Python pages sharing one minimal lifecycle/navigation contract.
- Subject behavior belongs in its page/module, never in `enciclopedia_engine.py`.
- Reuse Greia lifecycle, protected system chrome, semantic input, localization, typography, visual assets and runtime policy.
- Acer Aspire One-class hardware is the floor: simple geometry/sprites, bounded state, no heavy physics or unbounded effects.
- No speech recognition, runtime narration TTS, runtime AI or network factual lookup.
- Narration is prerecorded during authoring. Dani/system speech is also generated on development/parent hardware and packaged as static audio.
- Italian and English are the initial locales.
- `encyclopedia/VOICE_RECORDING_REQUESTS.md` is the single coordination authority for encyclopedia-specific voice production.
- Do not run per-page Simulator gates during this first construction pass. The owner explicitly wants one consolidated Simulator/visual/input pass after the source base is solid.
- Do not call v0.1 runtime-accepted until that consolidated gate has actually executed on the final runtime-relevant source.

## Product scope — source complete

The original v0.1 target remains exactly:

```text
1 Home
6 section pages
36 final entries
= 43 executable pages
```

All 43 now exist and are registered in `enciclopedia_catalogue.py`.

### Animals — complete

```text
animals
├── animals.lion
├── animals.elephant
├── animals.octopus
├── animals.bee
├── animals.penguin
└── animals.frog
```

### Space — complete

```text
space
├── space.sun
├── space.mercury
├── space.venus
├── space.earth
├── space.moon
├── space.mars
├── space.jupiter
├── space.saturn
├── space.uranus
└── space.neptune
```

### Earth & Nature — complete

```text
earth
├── earth.volcano
├── earth.rain
├── earth.ocean
├── earth.tree
└── earth.rainbow
```

### My Body — complete

```text
body
├── body.heart
├── body.lungs
├── body.bones
├── body.teeth
└── body.senses
```

### Science & Machines — complete

```text
machines
├── machines.gears
├── machines.magnet
├── machines.bicycle
├── machines.airplane
└── machines.bridge
```

### Long Ago — complete

```text
history
├── history.dinosaurs
├── history.fossils
├── history.mammoth
├── history.cave_paintings
└── history.pyramids
```

## Architecture state

`enciclopedia_engine.py` remains subject-neutral and owns only:

- `EncyclopediaPage` lifecycle;
- `PageContext` dependency seam;
- explicit `PageRegistry`;
- bounded `PageNavigator` history;
- semantic pointer/command input vocabulary.

No animal, planet, anatomy, geology, machine or history behavior belongs to the engine.

Model classes exist only where a page owns real coupled mutable invariants. Current examples include:

```text
BeePollinationModel
FrogLifeCycleModel
MoonPhaseModel
VolcanoModel
HeartModel
GearTrainModel
FossilDigModel
BreathingModel
DrivetrainModel
BridgeLoadModel
PyramidBuildModel
```

Simple pages remain page-owned state. Do not manufacture model/manager/ABC layers for consistency alone.

There is intentionally no generic `PlanetPage`, `AnatomyPage`, `MachinePage`, `HistoryPageBase`, exhibit DSL or physics framework.

Shared performance owners remain bounded:

- `CachedEncyclopediaTypography`: max 160 cached text surfaces;
- shared character rendition cache: hard bounded;
- page animations/effects: finite timers/counts;
- no page hot path should decode images, `smoothscale` reusable assets, build fonts, walk filesystems or perform network/provider work.

## Navigation state

All visible planned subjects now lead to real pages.

- Animals uses one explicit subject-ID mapping.
- Space exposes Sun, eight major planets and Earth's Moon; Moon remains a satellite, not a ninth planet.
- Earth & Nature uses five semantic scene destinations.
- My Body uses five body callouts.
- Science & Machines uses five workshop stations.
- Long Ago uses five timeline moments.

Pointer/touch and Greia semantic keyboard/controller paths are intended to reach the same destinations and page actions.

## Research/provenance state

Every one of the **36 factual final entries** has an authoring authority under:

```text
encyclopedia/research/<section>/<entry>.md
```

Each record contains:

- primary source links;
- accepted claims;
- scope/misconception guardrails;
- interaction → fact mapping;
- exact approved Italian narration;
- exact approved English narration.

Important corrections deliberately preserved include:

- most wild bees are solitary; generic bees are not all hive-dwellers;
- not all penguins live on ice;
- classic aquatic frog metamorphosis is common, not universal;
- Venus, not Mercury, is the hottest planet;
- Moon phases are changing views of sunlight and the Moon really rotates;
- clouds are droplets/ice particles, not giant bags of vapor;
- named oceans are regions of one connected global ocean;
- the adult 206-bone count is not taught as the count for every child;
- the tongue taste map is false;
- magnets do not attract every metal;
- bicycle gears do not create energy;
- airplane lift does not use the false equal-transit-time story;
- no bridge type is universally strongest;
- humans never lived alongside non-avian dinosaurs and birds are living dinosaurs;
- mammoths are elephant relatives, not dinosaurs;
- cave-art meanings are not invented when unknown;
- Egyptian pyramids are human engineering, not alien work, and the simplistic chained-slave story is not presented as settled archaeology.

## Localization state

`activities/enciclopedia_greia/locales/it.json` and `en.json` now contain matching child-facing key sets for the complete 43-page source inventory.

Runtime `audio` tables intentionally remain empty until generated clips are technically reviewed and owner-accepted. Missing custom narration must fail soft to silence; it must never trigger child-device TTS.

## Voice-production queue state — IMPORTANT

The unified file is:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

At the last verified synchronization point it still contains **176 `REQUESTED` rows** through:

```text
Space: Sun, Mercury, Venus, Earth, Moon
```

No recorder-owned status/note changes were observed at that synchronization point.

Research-ready narration not yet appended to that queue:

```text
Space:            Mars, Jupiter, Uranus, Neptune                 40 rows
Earth & Nature:   Rain, Ocean, Tree, Rainbow                    42 rows
My Body:          Lungs, Bones, Teeth, Senses                   40 rows
Machines:         Magnet, Bicycle, Airplane, Bridge             40 rows
Long Ago:         Dinosaurs, Mammoth, Cave Paintings, Pyramids  40 rows
                                                               --------
Pending:                                                      202 rows
```

Expected full v0.1 queue after synchronization:

```text
176 existing + 202 pending = 378 exact bilingual recording rows
```

Before changing the queue:

1. refetch it from current `main`;
2. preserve every recorder-owned `STATUS` and `RECORDER_NOTES` change;
3. never rewrite wording/path in place once a row is `RECORDED_UNREVIEWED` or later;
4. if wording later changes, append a revised cue/new filename and mark the old row `SUPERSEDED`.

## Current source-contract state

Focused contracts are in:

```text
tests/test_activity_enciclopedia.py
```

They have been authored to cover:

- exact 43-page runtime inventory and uniqueness;
- one research authority per implemented factual entry;
- research-document structural requirements;
- targeted high-risk misconception guardrails;
- Italian/English key parity;
- complete Space targets;
- Earth/Body/Machines/History semantic destination maps;
- subject-neutral engine imports/identifiers;
- bounded text cache;
- no per-page image decode/smoothscale/font construction in source hot paths;
- no runtime TTS, speech recognition, AI provider or network-fetch backend;
- Python source parsing.

**Those tests have not been executed against the final 43-page source state in this construction pass.** Do not report them as passing until a real local execution does so.

No Greia Simulator run, rendered visual acceptance or physical Acer/Pi evidence has been performed for the complete encyclopedia yet, by explicit owner direction.

## Next exact work

Do not add more v0.1 topics. Scope expansion is forbidden until the 43-page base is reviewed.

Next work order:

1. synchronize the 202 pending exact bilingual requests into the unified voice file;
2. update `encyclopedia/PROGRESS.md` with the Earth/Body/Machines/Long-Ago completion milestones and correction of the old accidental `earth.rocks` note to planned `earth.ocean`;
3. when the owner is ready, execute one consolidated source-test + Greia Simulator + no-reading visual/input acceptance pass across representative paths in every section;
4. review screenshots/interaction quality and fix defects as a coherent acceptance tranche;
5. integrate only technically reviewed + owner-accepted recordings into locale audio tables;
6. only after the 43-page v0.1 base is accepted discuss new packs/topics.
