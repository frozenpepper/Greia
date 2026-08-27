# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Construction state:** v0.1 source breadth complete and frozen for closure  
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
- `encyclopedia/VOICE_RECORDING_REQUESTS.md` is the single human/agent coordination authority for encyclopedia-specific voice production.
- The first construction pass intentionally skipped per-page Simulator gates. Do not claim runtime acceptance until the later consolidated source-test + Simulator/visual/input pass actually runs.
- Do not add more v0.1 topics. The 43-page breadth is frozen unless the owner deliberately changes scope.

## Exact v0.1 inventory

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
├── earth.volcano
├── earth.rain
├── earth.ocean
├── earth.tree
└── earth.rainbow

body
├── body.heart
├── body.lungs
├── body.bones
├── body.teeth
└── body.senses

machines
├── machines.gears
├── machines.magnet
├── machines.bicycle
├── machines.airplane
└── machines.bridge

history
├── history.dinosaurs
├── history.fossils
├── history.mammoth
├── history.cave_paintings
└── history.pyramids
```

The authoring catalogue `encyclopedia/pages/catalogue.py` and runtime `enciclopedia_catalogue.py` currently contain the same 43 IDs. `tests/test_activity_enciclopedia.py` now explicitly guards that equality.

## Architecture state

`enciclopedia_engine.py` owns only lifecycle, `PageContext`, explicit registry, bounded navigation history and semantic input vocabulary. No subject knowledge has leaked into it.

Small model objects exist only where real coupled state warrants them, including `BeePollinationModel`, `FrogLifeCycleModel`, `MoonPhaseModel`, `WaterCycleModel`, `VolcanoModel`, `HeartModel`, `BreathingModel`, `GearTrainModel`, `DrivetrainModel`, `BridgeLoadModel`, `FossilDigModel` and `PyramidBuildModel`.

There is intentionally no generic exhibit DSL, `PlanetPage`, `AnatomyPage`, `MachinePage`, history base class or physics framework.

Performance owners are bounded: text-surface cache max 160, character rendition cache bounded, page effects finite, and page hot paths should not decode images, smooth-scale reusable assets, build fonts, walk filesystems or perform provider/network work.

## Research/localization state

All **36 factual final entries** have one authority at:

```text
encyclopedia/research/<section>/<entry>.md
```

Each includes sources, accepted claims, misconception/scope guardrails, interaction-to-fact mapping and exact approved Italian/English narration.

Italian and English runtime string bundles cover all 43 pages and have matching child-facing keys. Runtime `audio` maps remain empty until owner-accepted recordings are packaged.

## Voice pipeline — local-agent workflow

### Step 1 — populate/validate the complete queue

The checked-in Markdown queue is still the older **176-row** checkpoint. The deterministic synchronizer must be run in a repository checkout before the queue is considered complete:

```bash
python3 encyclopedia/sync_voice_requests.py
python3 encyclopedia/sync_voice_requests.py --check
```

Expected result:

```text
36 factual topics
378 total bilingual rows
```

`sync_voice_requests.py` reads exact wording from research, preserves recorder-owned `STATUS`/`RECORDER_NOTES`, rejects duplicates, and refuses immutable drift on locked recorded rows.

### Step 2 — record gradually

The local recording agent processes only `REQUESTED` rows. It changes only `STATUS` and `RECORDER_NOTES` and adds the requested staging OGG.

Status flow:

```text
REQUESTED
→ RECORDED_UNREVIEWED
→ OWNER_ACCEPTED
```

Rejected/revised rows use the existing queue protocol; never silently alter immutable text/voice/path after recording starts.

### Step 3 — package only owner-accepted clips

After one or more clips become `OWNER_ACCEPTED`:

```bash
python3 encyclopedia/integrate_voice_assets.py
python3 encyclopedia/integrate_voice_assets.py --check
```

The integrator:

- ignores all non-`OWNER_ACCEPTED` rows;
- validates staging path/locale/filename and OGG container header;
- preflights the whole accepted set before mutation;
- atomically writes runtime files under `activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...`;
- updates locale `audio` mappings only after files exist;
- preserves locale strings/metadata;
- never generates speech and is never imported by child runtime.

Shared ledger grammar lives in `encyclopedia/voice_ledger.py` so the queue synchronizer and accepted-asset integrator cannot diverge on row parsing.

## Tests authored, not executed

Runtime/source contracts:

```text
tests/test_activity_enciclopedia.py
```

Authoring-tool contracts:

```text
tests/test_encyclopedia_authoring_tools.py
```

The latter covers the 378-row rendered invariant, duplicate ledger rows, OWNER_ACCEPTED-only packaging, ignored unreviewed clips, missing/corrupt OGG rejection, path traversal rejection and preservation of locale strings.

**Neither final contract suite has been executed against the current frozen source in this construction pass.** Do not report them as passing.

## Current exact evidence

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

No consolidated Simulator pass, rendered visual acceptance, or physical Acer/Pi acceptance has run yet. No accepted narration is integrated yet.

## Next work order

1. On a local checkout, run `python3 encyclopedia/sync_voice_requests.py` and commit the resulting 378-row ledger, preserving any recorder changes.
2. Run the focused provider-free source/authoring tests and fix only real failures.
3. Let the recording agent continue independently; integrate only `OWNER_ACCEPTED` clips with `integrate_voice_assets.py` as they become available.
4. When enough narration exists to evaluate the real experience, run the owner-requested **single consolidated** Simulator/visual/input acceptance pass across every section and representative final entries.
5. Fix discovered UX/performance/content defects coherently; do not broaden topic scope until v0.1 is accepted.
