# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Current construction state:** Home + all six v0.1 section pages implemented as first-party Activity source  
**Evidence:** SOURCE-VERIFIED / SIMULATOR-UNVERIFIED  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

## Owner direction that must not drift

- Keep the encyclopedia engine very small.
- Treat section pages and final entries as executable Python pages.
- Different pages may use very different lightweight interactions.
- Explicit accepted examples: slowly orbiting Solar System, erupting volcano.
- Do not assume child speech recognition.
- Do not assume on-device/runtime narration TTS.
- Normal character narration is prerecorded during authoring.
- Dani/system TTS and pronunciation-critical system speech are also generated ahead of time on parent/development hardware and packaged as files.
- Initial languages: Italian and English.
- Maintain one unified, precise voice-recording request file so a separate local agent can generate audio independently while page implementation continues.
- **First construction pass testing rule:** do not run Simulator acceptance after each intermediate page/phase. Build a solid coherent base first, then run the relevant Simulator/visual/input paths together in one consolidated acceptance pass.
- Until that consolidated pass executes, use `SOURCE-VERIFIED / SIMULATOR-UNVERIFIED`; do not call the Activity runtime-accepted.

## Authoring/runtime sources

```text
encyclopedia/README.md
encyclopedia/PLAN.md
encyclopedia/PROGRESS.md
encyclopedia/VOICE_RECORDING_REQUESTS.md
encyclopedia/HANDOVER.md
encyclopedia/pages/catalogue.py

activities/enciclopedia_greia/activity.toml
activities/enciclopedia_greia/main.py
activities/enciclopedia_greia/enciclopedia_app.py
activities/enciclopedia_greia/enciclopedia_engine.py
activities/enciclopedia_greia/enciclopedia_audio.py
activities/enciclopedia_greia/enciclopedia_services.py
activities/enciclopedia_greia/enciclopedia_catalogue.py
activities/enciclopedia_greia/pages/
activities/enciclopedia_greia/locales/
```

## v0.1 product scope remains

43 planned executable pages:

- 1 home;
- 6 sections;
- 36 final entries.

The authoring catalogue remains the complete planned inventory. The runtime registry contains only pages that actually exist.

## Implemented runtime pages now

```text
home
animals
space
earth
body
machines
history
```

### `home`

- six large visual world portals;
- Leo presenter;
- pointer/touch selection;
- Greia navigation-profile directional/activate input;
- stable `encyclopedia.home.welcome` semantic voice cue request.

### `animals`

- Tito presenter;
- habitat-style collage;
- six planned v0.1 anchors: lion, elephant, octopus, bee, penguin, frog;
- selection interaction without pretending the still-unimplemented final entries exist.

### `space`

- Leo presenter;
- Sun plus all eight major planets;
- lightweight math-driven continuous orbits;
- pointer and directional planet selection;
- no physics engine.

### `earth`

- Tito presenter;
- rain/ocean/tree/rainbow/volcano scene;
- touching the volcano triggers a bounded eruption animation.

### `body`

- Lilli presenter;
- friendly schematic body;
- breathing lungs;
- heartbeat loop;
- touching the torso temporarily emphasizes heartbeat.

### `machines`

- Dani presenter;
- linked rotating gear train;
- touching the mechanism temporarily accelerates it;
- visual hints for other planned machine topics.

### `history`

- Leo presenter;
- visual timeline anchors for dinosaurs, fossils, mammoth, cave paintings and pyramids;
- pointer/directional selection.

## Architecture state

The runtime engine deliberately knows only:

- page lifecycle;
- stable page IDs;
- explicit page factories;
- bounded internal navigation history;
- pointer/command input vocabulary;
- draw/update dispatch.

Subject-specific behavior remains inside page modules. There are no engine branches for planets, volcanoes, hearts, gears, animals or history.

Greia integration uses existing platform seams:

- `PygameReferenceCanvas` for 1024x600 logical authoring;
- platform-owned Home chrome and protected pointer exclusion;
- `PygameInputTranslator`/Greia input profile for semantic navigation;
- `LocalizedResources` for it/en text and future audio cues;
- `GreiaTypography` for child-facing text policy;
- semantic shared character visual lookup with a hard-bounded cache;
- fail-soft prerecorded audio owner.

The Activity does not open controller devices itself.

## Audio state

The independent recording queue remains:

```text
encyclopedia/VOICE_RECORDING_REQUESTS.md
```

Current requested E0 navigation/section cues were not rewritten in this source pass.

Runtime code already requests the matching semantic cue IDs, but `activities/enciclopedia_greia/locales/{it,en}.json` intentionally have empty `audio` tables until accepted files are integrated. Missing voice files therefore produce silence rather than runtime synthesis or fake substitute narration.

Do not add factual entry narration to `REQUESTED` until its page research/provenance exists.

## New Activity design decisions

- **Pre-reader strategy:** large visual worlds, direct scene manipulation, spoken cues; labels are secondary support.
- **Presenters:** Leo home/space/history; Tito animals/earth; Lilli body; Dani machines.
- **Speech:** prerecorded only.
- **Child microphone/recording:** considered and intentionally excluded from the encyclopedia v0.1 base; it adds no useful core interaction here.
- **Score:** deliberately none.
- **Durable progress:** deferred until Discovery/collection semantics are designed; do not invent fake completion meters.
- **Events/Stars/achievements:** none in the base. Later semantic discovery milestones may report facts to Greia after the design is accepted.
- **Network:** none.

## Verification actually performed for this construction pass

Before persistence, the authored source was checked with:

- `ast.parse` for every new Python file;
- `py_compile` for every new Python file and the new test source;
- `tomllib` parse for the manifest;
- JSON parsing + matching it/en key sets;
- current curated import-root/static policy review;
- capability/permission/discovery-tag checks;
- scan for runtime TTS/speech-recognition backend imports.

Repository fixtures were reconciled for the 33rd built-in Activity:

```text
tests/test_activity_enciclopedia.py
tests/test_activity_contract.py
tests/test_first_party_activity_audience_metadata.py
tests/test_first_party_activity_readiness.py
```

No GitHub-hosted Actions were used.

## Explicitly not verified yet

- no Greia Simulator launch/survival/interaction gate;
- no runtime screenshots/visual acceptance;
- no physical Acer or Pi evidence;
- no integrated prerecorded voice assets;
- no final factual entry pages;
- no factual claim provenance for the pilot entries yet;
- no Discovery-book persistence/progression.

This is deliberate under the owner's first-pass testing instruction, not evidence that those gates are unnecessary.

## Next exact construction tranche

Implement the six architecture-stress pilot final entries from the plan:

```text
animals.octopus
space.saturn
earth.volcano
body.heart
machines.gears
history.fossils
```

For each pilot:

1. research the small set of factual claims first;
2. save trustworthy provenance in page-local research notes;
3. author the interactive page as its own Python module/package;
4. keep subject-specific behavior outside `enciclopedia_engine.py`;
5. write short child-safe Italian and English narration from the verified facts;
6. append exact bilingual recording requests to `VOICE_RECORDING_REQUESTS.md`;
7. do source-level checks while construction continues;
8. defer the consolidated Simulator/visual/input gate until the coherent first-pass base is ready, per owner direction.
