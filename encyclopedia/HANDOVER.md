# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Construction state:** v0.1 source breadth complete; post-build drift review applied; frozen for local closure  
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
- The repository-wide Voice Production Engine may consume the ledger through the deterministic adapter; it does not replace the ledger or owner listening/`OWNER_ACCEPTED` authority.
- The first construction pass intentionally skipped per-page Simulator gates. Do not claim runtime acceptance until the consolidated source-test + Simulator/visual/input pass actually runs.
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

The authoring catalogue `encyclopedia/pages/catalogue.py` and runtime `enciclopedia_catalogue.py` contain the same 43 IDs. `tests/test_activity_enciclopedia.py` derives the runtime and authoring inventories and guards that exact equality rather than carrying another copied 43-page list.

## Architecture state after freeze review

`enciclopedia_engine.py` still owns only lifecycle, `PageContext`, explicit registry, bounded navigation history and semantic input vocabulary. The freeze review found no subject-specific branch or page-type hierarchy leaking into it.

Small model objects exist only where real coupled state warrants them, including `BeePollinationModel`, `FrogLifeCycleModel`, `MoonPhaseModel`, `WaterCycleModel`, `VolcanoModel`, `HeartModel`, `BreathingModel`, `GearTrainModel`, `DrivetrainModel`, `BridgeLoadModel`, `FossilDigModel` and `PyramidBuildModel`.

There is intentionally no generic exhibit DSL, `PlanetPage`, `AnatomyPage`, `MachinePage`, history base class or physics framework.

Performance owners remain bounded: text-surface cache max 160, character rendition cache max 24, voice-sound cache max 32, page effects finite, and page hot paths should not decode images, smooth-scale reusable assets, build fonts, walk filesystems or perform provider/network work.

One cleanup from the freeze review narrowed `EncyclopediaAudio.play()` from a broad `except Exception` to the canonical `LocalizationError`; ordinary mixer/file failures still fail soft through their explicit bounded exception paths.

## Research/localization state

All **36 factual final entries** have one authority at:

```text
encyclopedia/research/<section>/<entry>.md
```

Each includes sources, accepted claims, misconception/scope guardrails, interaction-to-fact mapping and exact approved Italian/English narration.

The review identified two historical research-document generations:

1. early/pilot authorities use `Child-facing wording contract`, human headings such as `Intro — Tito`, and `Italian` / `English` backticked lines;
2. later authorities use `Approved narration wording`, explicit semantic cue IDs, `Presenter` metadata and `it` / `en` lines.

This is now an explicitly supported compatibility boundary rather than accidental format drift. `sync_voice_requests.py` does **not** rewrite the early authorities. It validates their established ledger cue order, speaker, canonical voice ID and exact bilingual text against research, while generating later rows directly from semantic cue blocks. Missing/mismatched legacy rows fail closed.

Italian and English runtime string bundles cover all 43 pages and have matching child-facing keys.

The review also found and fixed an accepted-audio integration bug: Greia's `LocalizedResources` schema requires audio entries such as:

```json
{
  "encyclopedia.animals.lion.intro": {
    "path": "assets/audio/it/animals/lion/intro-tito.ogg"
  }
}
```

not a bare path string. `integrate_voice_assets.py` and both contract suites now use/validate the canonical object shape.

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

The synchronizer:

- preserves recorder-owned `STATUS` / `RECORDER_NOTES`;
- supports and validates both historical research narration formats;
- rejects duplicate identities;
- validates presenter-to-canonical-voice pairing;
- refuses immutable drift on locked recorded rows;
- enforces the complete 378-row invariant.

`tests/test_encyclopedia_authoring_tools.py` additionally requires the set of semantic narration cue IDs present in runtime page modules to equal the synchronized ledger cue set.

### Step 2 — translate REQUESTED rows to the shared Voice Production Engine contract

New deterministic adapter:

```text
encyclopedia/export_voice_batch.py
```

Example:

```bash
python3 encyclopedia/export_voice_batch.py \
  --output ./tmp/encyclopedia-requested-voices.jsonl
```

This tool performs **no synthesis**. It maps the ledger's already-reviewed semantics into Voice Engine JSONL:

```text
speaker
speech kind
locale
exact text
cue ID
staging output path
verification mode
bounded attempt count
```

It exports only `REQUESTED` rows by default, validates safe locale-scoped encyclopedia staging paths and refuses to overwrite an already-existing requested take unless an operator explicitly bypasses that safety check.

After the repository-wide Voice Production Engine passes its own separate local provider acceptance, the resulting JSONL can be processed by:

```bash
python3 tools/greia_voice.py batch \
  --input ./tmp/encyclopedia-requested-voices.jsonl
```

Until that provider subsystem is locally accepted, the established direct recording workflow remains valid. The adapter exists now so the encyclopedia never needs a second hand-maintained request authority.

### Step 3 — record gradually into local staging

The local recording agent processes only `REQUESTED` rows. It changes only `STATUS` and `RECORDER_NOTES` and adds the requested staging OGG.

Status flow:

```text
REQUESTED
→ RECORDED_UNREVIEWED
→ OWNER_ACCEPTED
```

The existing queue column `FINAL_PATH` means the recorder's final **staging** destination. Staging lives under:

```text
encyclopedia/pages/**/assets/audio/
```

and is git-ignored. Do not commit unreviewed/rejected takes or duplicate accepted audio in both authoring and runtime trees.

Rejected/revised rows use the existing queue protocol; never silently alter immutable text/voice/path after recording starts.

### Step 4 — package only owner-accepted clips

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
- emits canonical Greia locale `audio` objects with a `path` member;
- updates locale maps only after files exist;
- preserves locale strings/metadata and unrelated non-ledger audio mappings;
- never generates speech and is never imported by child runtime.

Only the accepted runtime copy is intended for normal source packaging/shipping.

Shared ledger grammar lives in `encyclopedia/voice_ledger.py` so the synchronizer, Voice Engine adapter and accepted-asset integrator cannot diverge on row parsing.

## Source-contract state — authored, not executed

Runtime/source contracts:

```text
tests/test_activity_enciclopedia.py
```

They now guard:

- runtime catalogue == authoring catalogue == 43 unique pages;
- research files are discovered from the research tree and must exactly cover all factual runtime entries;
- both accepted historical research-document formats;
- high-risk factual guardrails;
- Italian/English string parity;
- canonical Greia audio-object schema and safe package-relative paths;
- complete section destination maps;
- subject-neutral engine imports/identifiers;
- bounded text cache and page hot-loop policy;
- no runtime TTS, speech recognition, AI provider or network-fetch backend;
- Python source parsing.

Authoring-tool contracts:

```text
tests/test_encyclopedia_authoring_tools.py
```

They cover:

- exact 378-row rendered queue;
- runtime semantic cue-set == synchronized ledger cue-set;
- all synchronized `REQUESTED` rows translate into the provider-neutral Voice Engine request contract;
- status-filtered Voice Engine export;
- existing-requested-take overwrite refusal;
- unsafe Voice Engine staging-path rejection;
- duplicate ledger rows;
- OWNER_ACCEPTED-only packaging;
- ignored unreviewed clips;
- missing/corrupt OGG rejection;
- accepted staging path traversal rejection;
- canonical locale-audio object output;
- preservation of locale strings and unrelated audio mappings.

**Neither final contract suite has been executed against this reviewed source in the current GitHub-only construction/review environment.** Do not report them as passing.

## Consolidated acceptance authority

The exact deferred closure procedure is:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

It is intentionally fail-closed and tells the local agent to:

1. preserve any real recorder changes;
2. synchronize and independently verify the 378-row queue;
3. run focused provider-free contracts and `make verify`;
4. package only rows already marked `OWNER_ACCEPTED`;
5. launch the real Activity through Greia Simulator at 1024×600;
6. traverse all six sections and all 36 final entries through normal child navigation;
7. exercise every final entry's signature interaction;
8. test pointer vs semantic keyboard/controller parity on the six architecture-stress entries;
9. perform the mandatory no-reading pass;
10. spot-check responsive layouts;
11. return exact evidence without repairing source inside the acceptance run.

The provider-free contracts now also validate the new ledger → Voice Engine adapter, but the acceptance run still does **not** generate narration. Voice production remains its own workflow.

This Simulator pass can evaluate the frozen visual/input source even if narration production is incomplete. Missing reviewed narration is **audio acceptance pending**, never an invitation to add runtime synthesis. Any later accepted-audio integration changes runtime resources and therefore requires a fresh focused launch/survival/interaction gate on that later exact state.

## Current exact evidence

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

No consolidated Simulator pass, rendered visual acceptance, or physical Acer/Pi acceptance has run against this reviewed final source. The complete 378-row queue has not yet been written into the checked-in Markdown ledger.

## Next exact work

1. Execute `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md` on an owner-controlled local checkout without source repair during the run.
2. The first stage must synchronize the old 176-row queue into the validated 378-row full-v0.1 ledger; stop on any legacy/canonical research mismatch rather than rewriting evidence.
3. Return the exact first failure if any; otherwise return complete test/Simulator/no-reading evidence and the deterministic voice-ledger/runtime-audio diff.
4. In parallel, execute the repository-wide Voice Production Engine's own local provider acceptance. Only after it is green should the new JSONL adapter become the default encyclopedia generation path.
5. Review evidence and fix only concrete UX/performance/content defects as a coherent tranche; rerun invalidated gates on the final repaired source.
6. Let recording continue independently and integrate only `OWNER_ACCEPTED` clips.
7. Do not broaden topic scope until the 43-page v0.1 base is accepted.
