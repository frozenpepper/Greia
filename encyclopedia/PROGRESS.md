# Greia Encyclopedia — implementation progress ledger

**Purpose:** append-only operational progress for the long-lived `encyclopedia/PLAN.md` workstream.  
**Plan authority:** `encyclopedia/PLAN.md` remains the product/architecture/content plan.  
**Runtime implementation:** `activities/enciclopedia_greia/`.

Do not rewrite older entries to make history cleaner. Append corrections.

---

## 2026-08-27 — first source-construction pass: Activity shell + all six sections

Owner testing direction for this construction pass:

- do **not** interrupt first-pass construction with Simulator acceptance after every phase/page;
- build a solid coherent source base first;
- run the real Greia Simulator/interaction/visual acceptance as one consolidated later pass;
- until that later pass, use the exact label **SOURCE-VERIFIED / SIMULATOR-UNVERIFIED** rather than claiming runtime acceptance.

Implemented on `main`:

- first-party Activity manifest `org.greia.enciclopedia`;
- thin `main.py` composition root;
- `EncyclopediaApp` lifecycle/input owner;
- tiny Activity-local executable page engine (`EncyclopediaPage`, explicit `PageRegistry`, bounded `PageNavigator`);
- no runtime filesystem page discovery or dynamic imports;
- semantic page input vocabulary mapped from Greia input translation;
- Greia protected Home remains platform-owned;
- distinct Activity-internal Back tab for encyclopedia page navigation, outside protected system chrome;
- fixed 1024x600 reference canvas through Greia's shared Pygame canvas adapter;
- bounded shared-character rendition cache with fail-soft fallbacks;
- bounded prerecorded-audio owner using `LocalizedResources.audio_cue()`; no runtime synthesis;
- bilingual `it`/`en` runtime resource bundles;
- runtime page registry now implements exactly seven pages: Home + six section pages.

Implemented section behavior:

1. `home` — six large visual worlds, Leo presenter, keyboard/controller grid navigation and pointer/touch selection;
2. `animals` — Tito-hosted habitat collage containing the six v0.1 animal anchors (lion, elephant, octopus, bee, penguin, frog);
3. `space` — Leo-hosted lightweight Solar System with all eight major planets continuously orbiting and selectable;
4. `earth` — Tito-hosted nature scene with rain/ocean/tree/rainbow and a touch-triggered volcano eruption;
5. `body` — Lilli-hosted body schematic with breathing lungs and animated/touch-emphasized heartbeat;
6. `machines` — Dani-hosted workshop with linked animated gears and touch acceleration plus mechanism hints;
7. `history` — Leo-hosted visual timeline for dinosaurs, fossils, mammoth, cave paintings and pyramids.

Audio state:

- page code requests the existing stable semantic cue IDs from `VOICE_RECORDING_REQUESTS.md`;
- runtime locale audio tables deliberately remain empty until accepted prerecorded files are integrated;
- no runtime/on-device TTS, speech recognition, LLM, network knowledge lookup or voice model exists;
- existing `REQUESTED` voice rows were not rewritten during this source pass.

Product decisions recorded for the Activity-authoring contract:

- presenter plan: recurring Greia cast as listed above;
- pre-reader strategy: visual worlds/scenes and direct manipulation; text is supporting labels only;
- microphone/child recording: considered and intentionally excluded from this encyclopedia v0.1 base because it does not materially improve the core browse/discovery interaction;
- score: deliberately none;
- durable Activity progress: deliberately deferred until the Discovery/collection semantics are designed; no fake completion score or badge farming;
- events/Stars/global achievements: none in this base; later discovery milestones may report semantic facts only after their contract is designed;
- locales: Italian and English first;
- speech: all presenter narration prerecorded during authoring/parent-device production.

Source checks actually executed during authoring before persistence:

- all new Python source parsed with `ast.parse`;
- all new Python source passed `py_compile` in the construction workspace;
- Activity TOML parsed with `tomllib`;
- locale JSON parsed and locale key sets matched;
- manual/static curated-import-policy check against current `runtime/child-runtime.toml` roots passed;
- manifest capability sets are disjoint/allowed and request no permissions/network;
- discovery tag uses the platform-owned `nature` vocabulary;
- explicit scan found no runtime TTS/speech-recognition backend imports.

Repository test fixtures reconciled for the 33rd built-in Activity:

- `tests/test_activity_contract.py`;
- `tests/test_first_party_activity_audience_metadata.py`;
- `tests/test_first_party_activity_readiness.py`;
- new `tests/test_activity_enciclopedia.py`.

Not claimed / deliberately deferred:

- no Simulator launch/survival evidence yet;
- no rendered screenshot/visual acceptance yet;
- no physical Acer/Pi evidence;
- no factual final-entry narration/research yet;
- no final entry pages yet;
- no accepted recordings integrated yet;
- no completion/progression/discovery-book persistence yet.

Next construction tranche:

1. review the seven-page source base for architecture drift and fix any source-level defect found;
2. implement the six stress-test final entries from the plan: `animals.octopus`, `space.saturn`, `earth.volcano`, `body.heart`, `machines.gears`, `history.fossils`;
3. for each factual pilot, research claims first and create provenance before requesting factual narration;
4. append bilingual factual cues to the unified recording queue only after wording is research-ready;
5. keep the tiny engine free of subject-specific branches;
6. after the coherent first-pass base is sufficiently broad, run one consolidated Greia Simulator/visual/input acceptance pass as directed by the owner.

---

## 2026-08-27 — E3 six architecture-stress pilots source-ready

The planned one-entry-per-section stress tranche was completed in source:

```text
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

For every pilot:

- authoritative authoring-time provenance exists under `encyclopedia/research/`;
- short Italian/English child-facing captions exist;
- stable semantic narration cue IDs are requested by runtime code;
- exact bilingual narration was appended to the unified recording queue only after research;
- pointer and semantic controller/keyboard interaction use the same page-owned state transitions;
- subject-specific behavior remains outside `enciclopedia_engine.py`.

Architecture review result:

- the engine did not need a subject framework, physics system or content DSL;
- `VolcanoModel`, `HeartModel`, `GearTrainModel` and `FossilDigModel` exist only because those pages own non-trivial mutable invariants;
- Octopus and Saturn remain page-owned state without artificial model layers;
- Fossils completion announcement was encapsulated inside `FossilDigModel` rather than mutated by the page;
- Gears received a source-level geometry correction so pitch-circle distances, tooth counts, angular ratios, pinion rotation and rack motion agree with the teaching visual.

Research-quality corrections preserved:

- Heart does not depict oxygen-poor blood as literally blue;
- Saturn avoids a changing moon-count fact;
- Volcano does not imply all eruptions are explosive;
- Fossils are presented as evidence of past life, not simply `old bones`.

Evidence remains:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

No per-page Simulator run was performed, per owner direction.

---

## 2026-08-27 — E4 Animals breadth tranche 1: Lion, Elephant, Bee

Implemented and registered:

```text
animals.lion
animals.elephant
animals.bee
```

Runtime registry increased to 16 real pages.

### Lion

- Smithsonian-backed research record;
- Tito presenter;
- bounded mane variation;
- pride reveal;
- visual roar-wave interaction;
- foreleg/paw emphasis;
- real lion audio deliberately deferred until a licensed/provenance-reviewed sound source exists.

### Elephant

- Smithsonian-backed research record;
- Tito presenter;
- three deterministic trunk poses;
- bounded water-spray visualization;
- accelerated ear-flap/cooling visualization;
- second-elephant trunk-touch social interaction;
- no fluid simulation or species-specific weight/lifespan trivia.

### Bee

- USDA-backed research record;
- Tito presenter;
- `BeePollinationModel` owns the causal pollen-transfer state;
- nectar/pollen reveal;
- bounded flight between two flowers;
- visible pollen carried on the bee and transferred to the next flower;
- pollination/seed-fruit visual consequence;
- explicit solitary-wild-bee vs honey-bee-colony comparison.

Important science correction:

> A generic bee page must not teach that all bees live in hives. Most wild bees are solitary; honey bees are a familiar social colony case.

Animals section navigation was generalized with one explicit `animal_id -> implemented page_id` mapping rather than growing special-case index branches. Penguin and Frog remain visible but intentionally non-navigable until their pages exist.

Italian/English locale bundles and `tests/test_activity_enciclopedia.py` were updated for the 16-page state and nine research-backed final entries.

The unified recording queue was refetched immediately before modification; no recording-agent status/note changes were present. Lion, Elephant and Bee added 30 Tito recordings, bringing the queue to 106 exact bilingual rows at that synchronization point.

Next exact tranche:

```text
animals.penguin
animals.frog
```

These two pages will complete Animals v0.1 source breadth. Generic wording must preserve species diversity: not all penguins live on ice, and the familiar aquatic egg -> tadpole -> frog route is common but not universal among frogs.

---

## 2026-08-27 — E4 Animals source breadth complete

Implemented and registered:

```text
animals.penguin
animals.frog
```

Animals now has all six planned v0.1 final entries and no dead subject anchors. Runtime registry reached 18 real pages.

Quality decisions preserved:

- Penguin explicitly avoids the myth that every penguin lives on Antarctic ice; the page demonstrates cold, temperate and warmer Southern Hemisphere habitats;
- Frog presents egg -> tadpole -> froglet -> adult as a common route rather than a universal rule;
- `FrogLifeCycleModel` owns ordered stage/metamorphosis state because that sequence is a real domain invariant;
- Penguin remains page-owned state because its demonstrations do not justify a separate model class;
- section navigation remains one explicit subject-ID mapping rather than a growing branch chain.

The voice queue added Penguin/Frog bilingual Tito batches after a fresh synchronization, reaching 126 exact rows at that point.

Evidence remains `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`; Simulator is still intentionally deferred.

---

## 2026-08-27 — fast architecture/drift review before E5

Review covered engine neutrality, page responsibility, hot-loop cost, navigation parity, localization/audio boundaries and stale documentation.

Findings:

- no subject-specific behavior leaked into `enciclopedia_engine.py`;
- `main.py` remains a thin composition root;
- shared visual cache is bounded;
- page modules remain comfortably below the engineering decomposition threshold;
- no generic planet/exhibit inheritance hierarchy is justified yet;
- one repeated performance smell was real: static title/caption surfaces were being rerasterized every frame even though fonts themselves were cached.

Fix:

- introduced `CachedEncyclopediaTypography`, a bounded Activity-owned substitution of `GreiaTypography` with a 160-surface LRU-style text cache;
- the existing `PageContext.typography` seam required no page changes and no platform widening;
- cleanup remains explicit through the normal composition-root lifetime.

A Space product mismatch was also found: prerecorded section narration already told children they could touch the Sun, planets or Moon, while the section originally exposed only planet targets. Rather than rewriting coordinated narration, the section was corrected to make Sun and Moon genuine semantic targets as their pages arrived.

---

## 2026-08-27 — E5 Space breadth complete

Space v0.1 is now source-complete. Added researched executable entries:

```text
space.sun
space.mercury
space.venus
space.earth
space.moon
space.mars
space.jupiter
space.uranus
space.neptune
```

Together with the earlier `space.saturn`, the Space section now has real destinations for the Sun, all eight major planets and Earth's Moon. Runtime registry is now **27 real pages** overall.

Architecture/UX outcomes:

- eight planets remain the only members of the orbiting `PLANETS` tuple;
- Moon is rendered and navigated explicitly as Earth's satellite, not a ninth planet;
- semantic order is `Sun -> Mercury -> Venus -> Earth -> Moon -> Mars -> Jupiter -> Saturn -> Uranus -> Neptune`;
- pointer target order matches keyboard/controller semantic order;
- all Space targets use at least a 64 logical-pixel hit diameter and overlapping Earth/Moon regions resolve by nearest target;
- the old Saturn-only navigation branch was replaced by one explicit `body_id -> page_id` mapping;
- no planet base class or planet-specific branch was added to the engine.

Research/provenance now exists for every Space final entry under `encyclopedia/research/space/`, using NASA Science as primary authority. Volatile moon counts were deliberately excluded from Jupiter/Uranus/Neptune content.

Notable science/visual guardrails:

- Mercury is not taught as the hottest planet; Venus is;
- Mars is red because iron-rich minerals oxidized, not because it is hot;
- ancient Martian water is shown as past evidence, not modern open rivers;
- Jupiter's visible bands are atmospheric clouds, not a solid surface;
- Uranus's near-98-degree axial tilt is shown as orientation, without claiming a collision cause as certain;
- Neptune is not portrayed as a solid blue ocean world; methane contributes to its blue appearance;
- Moon phases are changing views of sunlight, not ordinary Earth-shadow events;
- Earth's seasons are tied to axial tilt, not changing Sun distance.

`tests/test_activity_enciclopedia.py` now describes the 27-page runtime, all researched Space provenance, complete Space semantic target mapping, bounded text-cache contract, bilingual key parity and engine neutrality.

No Simulator was run, by owner direction. Exact evidence remains:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Next breadth family after documentation/audio synchronization: **Earth & Nature** (`earth.rain`, `earth.tree`, `earth.rainbow`, `earth.rocks` alongside the already implemented `earth.volcano`).

---

## 2026-08-27 — correction: Earth & Nature scope and E7 completion

The preceding Space-era note incorrectly listed `earth.rocks`. The authoritative `PLAN.md` scope was re-read before implementation and the mistake was not allowed into runtime scope. Earth & Nature v0.1 is:

```text
earth.volcano
earth.rain
earth.ocean
earth.tree
earth.rainbow
```

The section is now source-complete and all five visible destinations map to real pages. Runtime inventory reached 31 pages.

Quality/architecture outcomes:

- `WaterCycleModel` owns bounded rain-process state without forcing a false one-way water-cycle conveyor;
- Ocean uses a finite depth-zone model rather than a generic scrolling/camera framework;
- Tree keeps simple page-owned state and explicitly compares deciduous/evergreen behavior without implying every tree follows one seasonal costume;
- Rainbow interaction makes Sun/viewer/droplet geometry causal and shows the complete circular geometry truthfully;
- the old Earth `ACTIVATE -> Volcano` special case was removed in favor of one semantic destination set;
- no Earth/Nature-specific behavior entered the encyclopedia engine.

Research guardrails include clouds as droplets/ice rather than bags of vapor, named oceans as connected regions of one global ocean, variable tree root/season behavior, and rainbows as observer-dependent optical phenomena rather than physical arches.

---

## 2026-08-27 — E8 My Body source breadth complete

Implemented and registered the remaining Body entries:

```text
body.lungs
body.bones
body.teeth
body.senses
```

Together with `body.heart`, the section is source-complete and the runtime inventory reached 35 pages. The Body section now has one five-target semantic/pointer map rather than the earlier `ACTIVATE -> Heart` shortcut.

OOP remained selective:

- `BreathingModel` owns coupled inhale/exhale/exercise timing;
- Bones, Teeth and Senses remain flatter page-owned state because they do not need ornamental model layers.

Important medical/educational guardrails include lungs not inflating themselves like balloons, children not being taught the adult 206-bone count as universal, eruption/tooth counts varying with age, no tongue taste-map myth, inclusive sensory language, and no painful/loud/flash-based demonstrations.

The encyclopedia source-contract test was also refactored here so research coverage is structural/scalable rather than a growing wall of hand-copied factual phrases; high-risk misconceptions retain explicit guard assertions.

---

## 2026-08-27 — E9 Science & Machines source breadth complete

Implemented and registered:

```text
machines.magnet
machines.bicycle
machines.airplane
machines.bridge
```

Together with `machines.gears`, the workshop is source-complete and runtime inventory reached 39 pages. The section now exposes five real 86x86 visual/semantic stations instead of `ACTIVATE -> Gears`.

Architecture outcomes:

- no generic `MachinePage` hierarchy was introduced;
- `DrivetrainModel` owns coupled bicycle crank/ratio/rear-wheel state;
- `BridgeLoadModel` owns finite bridge form/load/path state;
- Magnet and Airplane remain page-owned state;
- Magnet's first visual implementation was corrected because its facing-pole colors contradicted its attraction/repulsion state.

Scientific guardrails include magnets not attracting all metals, gear ratios trading force/motion rather than creating energy, NASA's explicit rejection of the false equal-transit-time lift story, and bridge load paths/force diagrams being schematic rather than universal structural claims.

---

## 2026-08-27 — E10 Long Ago and 43/43 v0.1 source breadth complete

Implemented and registered:

```text
history.dinosaurs
history.mammoth
history.cave_paintings
history.pyramids
```

Together with `history.fossils`, Long Ago is source-complete. The timeline's Fossils-only navigation special case was removed; all five moments are now real destinations.

The runtime registry now matches the original v0.1 scope exactly:

```text
1 Home
6 section pages
36 factual final entries
-----------------------
43 executable pages
```

Every factual entry has an authoring research authority with sources, accepted claims, scope guardrails, interaction-to-fact mapping and approved Italian/English narration.

History guardrails preserve that birds are living dinosaurs, non-avian dinosaurs and humans did not coexist, mammoths are elephant relatives rather than dinosaurs, cave-art meanings are often uncertain, and Egyptian pyramids are human engineering by organized workforces rather than alien construction or a simplistic one-line slave myth.

A source review removed dead Cave Paintings drafting residue and encapsulated Pyramid reveal transitions behind `PyramidBuildModel` methods rather than letting the page mutate model timers directly.

At this point new v0.1 topic breadth is frozen. Further work should be closure, audio production/integration, consolidated testing and targeted fixes unless the owner deliberately changes scope.

---

## 2026-08-27 — voice coordination and accepted-audio integration tooling

The original manually maintained factual queue became large enough that continued hand transcription was itself a drift risk. Two authoring-time tools now own the deterministic coordination seams:

```text
encyclopedia/sync_voice_requests.py
encyclopedia/integrate_voice_assets.py
```

A shared `encyclopedia/voice_ledger.py` owns the Markdown row grammar and duplicate detection.

`sync_voice_requests.py`:

- reads exact approved narration from all 36 research authorities;
- preserves the manually-owned E0 Home/section navigation rows;
- preserves recorder-owned `STATUS` and `RECORDER_NOTES`;
- refuses immutable drift once a row is recorded/accepted/rejected/superseded/blocked;
- fails closed on duplicate topic/batch/cue-locale identities;
- enforces exactly 36 factual topics and **378 total bilingual v0.1 recording rows**.

The checked-in `VOICE_RECORDING_REQUESTS.md` is still the earlier 176-row checkpoint until this synchronizer is actually executed in a repository checkout. Do not claim it is already synchronized.

`integrate_voice_assets.py`:

- considers only `OWNER_ACCEPTED` rows;
- ignores `RECORDED_UNREVIEWED` and all other statuses;
- validates staging paths, locale/filename identity, OGG container headers and Activity-root containment;
- preflights every accepted source before writes;
- packages narration under `activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...`;
- rewrites only the locale `audio` maps while preserving child-facing strings/metadata;
- writes packaged OGGs atomically and updates locale mappings only after assets exist;
- supports a non-mutating `--check` mode;
- deliberately does not delete unreferenced files from the Activity audio tree.

Provider-free contracts were added in `tests/test_encyclopedia_authoring_tools.py` for the 378-row render invariant, duplicate rows, partial OWNER_ACCEPTED integration, ignored unreviewed clips, missing/corrupt OGG rejection and path traversal rejection.

These tests have been **authored but not executed** in this construction pass.

Current truthful evidence label for the frozen v0.1 source is therefore:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

No page-by-page Simulator run was performed, per owner direction. The next major runtime stage is one consolidated source-test + Simulator/visual/input acceptance pass after the voice ledger is synchronized and enough accepted recordings exist to make audio behavior meaningful.

---

## 2026-08-27 — post-build drift review before consolidated acceptance

Performed a source-wide freeze review covering the page engine, app/composition seams, navigation maps, low-resource hot paths, localization/audio integration, research authorities, voice-ledger synchronization, contract tests and repository hygiene.

Architecture result:

- `enciclopedia_engine.py` remains subject-neutral; no animal/planet/body/machine/history branch leaked into the engine;
- `main.py` remains a thin composition root;
- model classes remain limited to real coupled state rather than consistency-for-its-own-sake inheritance;
- typography, character and sound caches remain explicitly bounded;
- the Activity still owns no runtime TTS, speech recognition, AI/provider or network-fact dependency.

Concrete drift defects found and fixed:

1. **Canonical locale-audio schema:** `integrate_voice_assets.py` had been emitting bare path strings even though Greia's `LocalizedResources` requires each audio cue to be an object containing `path`. The integrator and both contract suites now emit/validate the canonical object form and preserve unrelated audio objects.
2. **Mixed historical research formats:** early research authorities use `Child-facing wording contract` + human headings/Italian/English blocks, while later authorities use semantic cue IDs under `Approved narration wording`. The first synchronizer implementation only understood the later format and would have failed before reaching 378 rows. It now supports both generations fail-closed: established legacy rows are validated against exact research wording/speaker/voice IDs and retained; canonical rows are generated from semantic cue blocks.
3. **Test inventory/template drift:** the Activity contract had become a third copied topic inventory and assumed only the newer research template. It now derives runtime vs authoring catalogue equality directly and discovers research files from the authority tree, while deliberately accepting the two documented research generations.
4. **Runtime cue/recording drift:** the authoring-tool suite now requires the runtime page semantic narration cue set to equal the full synchronized ledger cue set.
5. **Exception hygiene:** `EncyclopediaAudio.play()` no longer catches arbitrary `Exception` from localization; it handles `LocalizationError` explicitly while mixer/file failures retain their own fail-soft paths.
6. **Recorder staging hygiene:** `encyclopedia/pages/**/assets/audio/` is now git-ignored. Queue `FINAL_PATH` means the recorder's local final staging destination; only owner-accepted copies under the runtime Activity audio tree are intended to be committed/shipped.

The complete queue is still **not claimed synchronized** because this GitHub-only environment did not execute `sync_voice_requests.py`. The checked-in Markdown remains the old 176-row checkpoint; local execution must produce and prove exactly 378 rows.

No focused tests, `make verify`, Simulator launch, responsive review or physical hardware run executed against this post-review source. The evidence label therefore remains exactly:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

The exact next step is the fail-closed local procedure at `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md`. Do not add more v0.1 topics before that evidence is reviewed.
