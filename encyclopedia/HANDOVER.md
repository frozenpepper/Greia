# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Current construction state:** Home + six section pages + six architecture-stress final entries implemented  
**Evidence:** SOURCE-VERIFIED / SIMULATOR-UNVERIFIED  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

## Owner direction that must not drift

- Keep the encyclopedia engine very small.
- Section pages and final entries are executable Python pages with a shared minimal lifecycle contract.
- Subject-specific behavior belongs in the page/module that owns it, not in `enciclopedia_engine.py`.
- Use Greia platform lifecycle, Home/chrome, semantic input, localization, typography, shared character visuals and approved runtime policy instead of Activity-local replacements.
- Target Acer Aspire One-class hardware: simple geometry/sprites, bounded state/particles, no per-frame decode/scale/font construction, no heavy physics.
- No speech recognition, runtime narration TTS, runtime AI or network factual lookup.
- All presenter narration is prerecorded during authoring. Dani/system speech is also generated ahead of time and packaged as static audio.
- Italian and English are the initial locales.
- `encyclopedia/VOICE_RECORDING_REQUESTS.md` is the single concurrency-safe audio queue; do not silently rewrite rows once recording has begun.
- First construction pass is source-first. Do not run Simulator acceptance page-by-page. One consolidated Simulator/visual/input pass comes later.
- Until that pass runs against the final runtime-relevant source, report `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`.

## Product scope

v0.1 remains **43 executable pages**:

- 1 Home;
- 6 sections;
- 36 final entries.

The authoring catalogue owns the full planned inventory. The runtime registry contains only pages that actually exist.

## Implemented runtime pages

Current registry has **13 real pages**:

```text
home
animals
animals.octopus
space
space.saturn
earth
earth.volcano
body
body.heart
machines
machines.gears
history
history.fossils
```

### Six pilot entries

`animals.octopus`
- Tito presenter;
- camouflage state cycling;
- arm/sucker reveal;
- bounded ink cloud;
- three-heart reveal.

`space.saturn`
- Leo presenter;
- gas-band motion;
- separate ring-particle reveal;
- schematic size/location cue;
- ring viewing-angle/tilt states.

`earth.volcano`
- Tito presenter;
- `VolcanoModel` owns pressure/style/timers;
- magma/vent teaching state;
- flowing vs bounded explosive eruption;
- bounded ash particles.

`body.heart`
- Lilli presenter;
- `HeartModel` owns pulse/circulation/exercise state;
- four-chamber reveal;
- simplified lungs/body circulation;
- heartbeat/valve emphasis;
- temporary exercise speed-up;
- oxygen-poor blood is not misleadingly rendered blue.

`machines.gears`
- Dani presenter via prerecorded system-speech path;
- `GearTrainModel` owns idealized gear relationships;
- adjacent pitch circles, tooth counts and angular ratios were reconciled after source review;
- direct neighbors reverse direction;
- visible speed-ratio comparison;
- pinion/rack rotary-to-linear demonstration.

`history.fossils`
- Leo presenter;
- finite 4×3 sediment grid;
- pointer brushing and semantic-controller progressive brushing share the same finite model;
- body/trace, burial and clue reveals;
- `FossilDigModel` owns the exactly-once completion announcement invariant.

## Architecture state

`enciclopedia_engine.py` remains subject-neutral. It owns only:

- `EncyclopediaPage` lifecycle;
- `PageContext` dependency seam;
- explicit `PageRegistry`;
- bounded `PageNavigator` history;
- semantic pointer/command input vocabulary.

It contains no subject-specific branches or imports for Octopus, Saturn, Volcano, Heart, Gears or Fossils.

Complex pilot pages use small model classes only when they own real mutable invariants. No generic exhibit framework has been introduced.

## Research/provenance state

Research records now exist for all six pilots:

```text
encyclopedia/research/animals/octopus.md
encyclopedia/research/space/saturn.md
encyclopedia/research/earth/volcano.md
encyclopedia/research/body/heart.md
encyclopedia/research/machines/gears.md
encyclopedia/research/history/fossils.md
```

Factual narration is never added to the recording queue before its research record exists.

## Audio state

The unified queue currently contains the E0 navigation batch plus six pilot batches, **76 bilingual recording rows** total at the last synchronization point.

Runtime locale `audio` tables intentionally remain empty until files are actually produced and owner-reviewed. Missing custom narration fails soft to silence; it never triggers runtime TTS.

Before appending any future batch:
1. refetch `VOICE_RECORDING_REQUESTS.md` from `main`;
2. preserve all local-agent status/note changes;
3. never alter wording/path of `RECORDED_UNREVIEWED` or later rows in place.

## Current verification state

Source-level checks/tests are maintained in:

```text
tests/test_activity_enciclopedia.py
```

The focused contract checks runtime inventory, bilingual key parity, research presence, subject-neutral engine code, forbidden speech-recognition/TTS backends and Python parsing.

Simulator, rendered visual acceptance, physical Acer/Pi evidence and integrated owner-accepted narration remain deliberately pending.

## Next construction tranche

Proceed with Phase E4 in small breadth tranches. First target:

```text
animals.lion
animals.elephant
animals.bee
```

Protocol for each:
1. research authoritative claims first;
2. record child-safe Italian/English wording and scope guardrails;
3. implement a page-local memorable interaction;
4. wire Animals section navigation through the existing `PageHost` seam;
5. add short bilingual captions;
6. update runtime registry and focused source-contract tests;
7. refetch and append exact voice requests without clobbering recording-agent changes;
8. keep Simulator deferred until the consolidated owner-directed pass.

Important Bee correction already identified for E4: a generic bee page must not imply that all bees live in hives/colonies. Most wild bees are solitary; honey bees are the familiar social colony case.