# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Current construction state:** Home + six sections + complete Animals + complete Space + four cross-section pilots  
**Runtime pages:** 27 real executable pages  
**Evidence:** SOURCE-VERIFIED / SIMULATOR-UNVERIFIED  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

## Owner direction that must not drift

- Keep the encyclopedia engine very small.
- Section pages and final entries are executable Python pages with a shared minimal lifecycle contract.
- Subject-specific behavior belongs in the page/module that owns it, not in `enciclopedia_engine.py`.
- Use Greia platform lifecycle, protected Home/chrome, semantic input, localization, typography, shared character visuals and approved runtime policy instead of Activity-local replacements.
- Target Acer Aspire One-class hardware: simple geometry/sprites, bounded state/particles, no per-frame decode/scale/font construction, no heavy physics.
- No speech recognition, runtime narration TTS, runtime AI or network factual lookup.
- All presenter narration is prerecorded during authoring. Dani/system speech is also generated ahead of time and packaged as static audio.
- Italian and English are the initial locales.
- `encyclopedia/VOICE_RECORDING_REQUESTS.md` is the single concurrency-safe audio queue; never silently rewrite a row after recording starts.
- First construction pass is source-first. Do not run Simulator acceptance page-by-page. One consolidated Simulator/visual/input pass comes later.
- Until that pass runs against the final runtime-relevant source, report `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`.

## Product scope

v0.1 remains **43 executable pages**:

- 1 Home;
- 6 sections;
- 36 final entries.

The long-lived product/content authority is `encyclopedia/PLAN.md`. `encyclopedia/PROGRESS.md` is the append-only implementation ledger. The runtime registry contains only pages that actually exist.

## Implemented runtime inventory

Current registry has **27 real pages**:

```text
home

animals
├── animals.lion
├── animals.elephant
├── animals.octopus
├── animals.bee
├── animals.penguin
└── animals.frog

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

earth
└── earth.volcano

body
└── body.heart

machines
└── machines.gears

history
└── history.fossils
```

Animals v0.1 and Space v0.1 are source-complete. The remaining breadth families are Earth & Nature, My Body, Science & Machines, and Long Ago.

## Architecture state

`enciclopedia_engine.py` remains subject-neutral and owns only:

- `EncyclopediaPage` lifecycle;
- `PageContext` dependency seam;
- explicit `PageRegistry`;
- bounded `PageNavigator` history;
- semantic pointer/command input vocabulary.

No animal, planet, volcano, heart, gear or fossil behavior is in the engine.

Important implementation rules now demonstrated in real pages:

- simple independent state stays page-local;
- a small model class is used only where a concept owns real coupled mutable invariants (`FrogLifeCycleModel`, `MoonPhaseModel`, `VolcanoModel`, `HeartModel`, `GearTrainModel`, `FossilDigModel`, `BeePollinationModel`);
- no generic exhibit framework or planet inheritance tree exists;
- section destinations use explicit semantic-ID mappings rather than growing index branch chains;
- `main.py` remains a thin composition root;
- `CachedEncyclopediaTypography` provides a hard-bounded 160-surface cache so static localized text is not rerasterized every frame;
- `VisualLibrary` remains a separate hard-bounded shared-character rendition cache.

## Space section contract

The Space scene deliberately distinguishes content model from navigation:

- `PLANETS` contains exactly the eight major planets;
- Sun is a separate central target;
- Moon is rendered as Earth's satellite, not a ninth planet;
- semantic navigation order is:

```text
Sun -> Mercury -> Venus -> Earth -> Moon -> Mars -> Jupiter -> Saturn -> Uranus -> Neptune
```

All ten targets now map to real pages. Pointer and semantic navigation orders match. Hit regions are at least 64 logical pixels in diameter; Earth/Moon overlap resolves by nearest target.

## Research/provenance state

Research records exist for every implemented factual final entry. Current Space records:

```text
encyclopedia/research/space/sun.md
encyclopedia/research/space/mercury.md
encyclopedia/research/space/venus.md
encyclopedia/research/space/earth.md
encyclopedia/research/space/moon.md
encyclopedia/research/space/mars.md
encyclopedia/research/space/jupiter.md
encyclopedia/research/space/saturn.md
encyclopedia/research/space/uranus.md
encyclopedia/research/space/neptune.md
```

NASA Science is the primary Space authority. Volatile moon counts are intentionally excluded from Jupiter/Uranus/Neptune child content. Factual narration is never added to the recording queue before research exists.

## Audio state

Runtime locale `audio` tables intentionally remain empty until requested recordings are produced and owner-reviewed. Missing custom narration fails soft to silence; it never triggers runtime TTS.

Before appending any future batch:

1. refetch `VOICE_RECORDING_REQUESTS.md` from current `main`;
2. preserve all local-agent status/note changes;
3. never alter wording/path of `RECORDED_UNREVIEWED` or later rows in place;
4. if wording changes after recording, create a revision/new filename and supersede the old row.

The recording queue is currently synchronized through Sun, Mercury, Venus, Earth and Moon. Mars/Jupiter/Uranus/Neptune research and runtime cues are ready; their four bilingual Leo batches are the immediate remaining queue-sync bookkeeping item if not yet present when resuming.

## Current verification state

Focused source contracts live in:

```text
tests/test_activity_enciclopedia.py
```

They now describe:

- the 27-page runtime registry;
- matching Italian/English key sets;
- provenance for every implemented researched entry;
- complete Space semantic target mapping;
- minimum Space hit radius;
- bounded typography cache;
- subject-neutral engine imports/identifiers;
- absence of runtime TTS/speech-recognition backends;
- Python source parsing.

These source contracts were updated but have **not been executed against the final Space-complete SHA in this construction pass**. Do not convert source review into test-execution evidence.

Simulator, rendered visual acceptance, physical Acer/Pi evidence and integrated owner-accepted narration remain deliberately pending.

## Next exact construction tranche

After completing any pending Mars/Jupiter/Uranus/Neptune voice-queue synchronization, move to **Earth & Nature breadth**:

```text
earth.rain
earth.tree
earth.rainbow
earth.rocks
```

`earth.volcano` already exists.

Protocol for each entry:

1. authoritative research first;
2. record scope guardrails and approved bilingual narration;
3. implement one memorable page-local interaction whose motion teaches the fact;
4. do not create a generic nature-page framework unless repeated semantics genuinely require one;
5. wire the existing Earth section via one explicit semantic destination mapping;
6. add short bilingual captions;
7. update registry/source contracts;
8. refetch and append exact voice requests without clobbering recording-agent changes;
9. keep Simulator deferred until the consolidated owner-directed pass.
