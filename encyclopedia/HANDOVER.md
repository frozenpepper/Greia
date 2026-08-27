# Greia Encyclopedia workstream handover

**Updated:** 2026-08-27  
**Construction state:** v0.1 source breadth complete; post-build drift review applied; frozen for local closure  
**Runtime pages:** **43 / 43 planned executable pages**  
**Evidence:** **SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED**  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)

This file is the current continuation contract for the Encyclopedia workstream. Historical implementation detail belongs in `encyclopedia/PROGRESS.md` and dated reviews.

---

## 1. Owner direction that must not drift

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

---

## 2. Exact v0.1 inventory

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

The authoring catalogue `encyclopedia/pages/catalogue.py` and runtime `activities/enciclopedia_greia/enciclopedia_catalogue.py` contain the same 43 IDs. `tests/test_activity_enciclopedia.py` derives those inventories rather than maintaining another copied catalogue.

---

## 3. Architecture state after freeze review

`enciclopedia_engine.py` still owns only lifecycle, `PageContext`, explicit registry, bounded navigation history and semantic input vocabulary. No subject-specific branch or page-type hierarchy leaked into the engine.

Small model objects exist only where real coupled state warrants them, including `BeePollinationModel`, `FrogLifeCycleModel`, `MoonPhaseModel`, `WaterCycleModel`, `VolcanoModel`, `HeartModel`, `BreathingModel`, `GearTrainModel`, `DrivetrainModel`, `BridgeLoadModel`, `FossilDigModel` and `PyramidBuildModel`.

There is intentionally no generic exhibit DSL, `PlanetPage`, `AnatomyPage`, `MachinePage`, history base class or physics framework.

Performance owners remain bounded:

```text
text surfaces       max 160
character renditions max 24
voice sounds          max 32
page effects          finite/page-owned
```

Page hot paths must not decode images, smooth-scale reusable assets, create fonts, walk filesystems or perform provider/network work.

The freeze review also narrowed `EncyclopediaAudio.play()` from broad exception handling to the canonical `LocalizationError`; ordinary mixer/file failures retain their explicit fail-soft paths.

---

## 4. Research/localization state

All **36 factual final entries** have one authority at:

```text
encyclopedia/research/<section>/<entry>.md
```

Each includes sources, accepted claims, misconception/scope guardrails, interaction-to-fact mapping and exact approved Italian/English narration.

Two historical research-document generations intentionally coexist:

1. early/pilot authorities use `Child-facing wording contract`, human headings such as `Intro — Tito`, and `Italian` / `English` backticked lines;
2. later authorities use `Approved narration wording`, explicit semantic cue IDs, `Presenter` metadata and `it` / `en` lines.

`sync_voice_requests.py` supports both fail-closed. It does **not** mass-rewrite early research. Legacy rows must already have established semantic cue IDs in the ledger and their exact bilingual wording, speaker and canonical voice ID must match research. Canonical-format rows are generated directly from semantic cue blocks.

Italian and English runtime string bundles cover all 43 pages and have matching child-facing keys.

The post-build review also fixed the accepted-audio integration schema. Greia requires:

```json
{
  "encyclopedia.animals.lion.intro": {
    "path": "assets/audio/it/animals/lion/intro-tito.ogg"
  }
}
```

not a bare path string. `integrate_voice_assets.py` and the contracts now use the canonical object form.

Durable drift review:

```text
docs/reviews/2026-08-27_ENCYCLOPEDIA_V01_POST_BUILD_DRIFT_REVIEW.md
```

---

## 5. Voice pipeline

### 5.1 Synchronize the complete queue

The checked-in Markdown queue remains the old **176-row** checkpoint until local execution proves otherwise.

```bash
python3 encyclopedia/sync_voice_requests.py
python3 encyclopedia/sync_voice_requests.py --check
```

Expected invariant:

```text
36 factual topics
378 total bilingual rows
```

The synchronizer preserves recorder-owned `STATUS`/`RECORDER_NOTES`, rejects duplicates, validates presenter-to-canonical-voice pairing, refuses immutable drift on locked rows and enforces the complete 378-row invariant.

`tests/test_encyclopedia_authoring_tools.py` also requires runtime semantic narration cue IDs to equal the full synchronized ledger cue set.

### 5.2 Translate REQUESTED rows to the shared Voice Production Engine

Adapter:

```text
encyclopedia/export_voice_batch.py
```

Example:

```bash
python3 encyclopedia/export_voice_batch.py \
  --output ./tmp/encyclopedia-requested-voices.jsonl
```

This performs **no synthesis**. It translates already-reviewed ledger semantics into provider-neutral Voice Engine requests and exports only `REQUESTED` rows by default. It validates locale-scoped staging paths and refuses to overwrite an existing requested take unless explicitly overridden.

After the repository-wide Voice Production Engine passes its separate local provider acceptance:

```bash
python3 tools/greia_voice.py batch \
  --input ./tmp/encyclopedia-requested-voices.jsonl
```

Until that provider subsystem is locally accepted, the established direct recording workflow remains valid.

### 5.3 Record gradually into local staging

Status flow:

```text
REQUESTED
→ RECORDED_UNREVIEWED
→ OWNER_ACCEPTED
```

Only a real owner/human listening decision may set `OWNER_ACCEPTED`.

Queue `FINAL_PATH` means recorder staging destination. Staging is under:

```text
encyclopedia/pages/**/assets/audio/
```

and is git-ignored. Do not commit unreviewed/rejected takes or duplicate accepted audio in both authoring and runtime trees.

### 5.4 Package only owner-accepted clips

```bash
python3 encyclopedia/integrate_voice_assets.py
python3 encyclopedia/integrate_voice_assets.py --check
```

The integrator:

- ignores all non-`OWNER_ACCEPTED` rows;
- validates staging path/locale/filename and OGG container header;
- preflights the whole accepted set before mutation;
- atomically writes runtime files under `activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...`;
- emits canonical Greia locale `audio` objects;
- updates locale maps only after files exist;
- preserves locale strings/metadata and unrelated non-ledger audio mappings;
- never generates speech and is never imported by child runtime.

Shared ledger grammar lives in `encyclopedia/voice_ledger.py` so synchronizer, Voice Engine adapter and accepted-asset integrator share one row parser.

---

## 6. Contract/source-gate state

Primary contract suites:

```text
tests/test_activity_enciclopedia.py
tests/test_encyclopedia_authoring_tools.py
tests/test_encyclopedia_v01_source_gate.py
```

They cover the 43-page inventory/research relationship, high-risk factual guardrails, locale/audio schema, section destinations, engine neutrality, bounded hot-path rules, no runtime AI/TTS/speech recognition, exact 378-row rendering, runtime cue/ledger parity, ledger→Voice Engine translation, overwrite/path safety, OWNER_ACCEPTED-only packaging and the deterministic source-gate helper's fail-closed preflight/exit semantics.

**These final reviewed contract suites have not executed against the current source in this GitHub-only environment. Do not report them as passing.**

---

## 7. Deterministic pre-Simulator source gate

A convenience/fail-closed helper now exists:

```text
tools/encyclopedia_v01_source_gate.py
```

Inspect its planned sequence without mutation:

```bash
python3 tools/encyclopedia_v01_source_gate.py --plan-only
```

Execute the deterministic source phase locally:

```bash
python3 tools/encyclopedia_v01_source_gate.py
```

It performs, in order:

1. `main`/worktree preflight, allowing only legitimate recorder/evidence state;
2. voice-ledger synchronization;
3. `--check` plus independent 378-row/status-count validation;
4. focused provider-free Encyclopedia/project contracts;
5. `make verify`;
6. `OWNER_ACCEPTED` runtime-audio synchronization check;
7. accepted-audio integration only when the integrator reports deterministic drift;
8. post-audio Encyclopedia tests when runtime resources changed;
9. `git diff --check`;
10. timestamped project-local evidence + `source-gate-summary.json`;
11. explicit stop with Simulator still pending.

It deliberately does **not** generate speech, change recorder status, repair source, launch Simulator, commit/push, or use hosted CI.

### Current authority rule

The handwritten runbook remains the canonical acceptance authority until this helper's own local tests execute successfully. The helper is intended to automate the deterministic pre-Simulator stages without changing their semantics; it does not replace the manual visual/input/no-reading Simulator review.

A helper PASS may advance the truthful label only to:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

not Simulator acceptance.

---

## 8. Consolidated acceptance authority

Canonical runbook:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

It requires:

1. preserve real recorder changes;
2. synchronize and independently prove the 378-row queue;
3. run focused provider-free contracts and `make verify`;
4. package only already-`OWNER_ACCEPTED` narration;
5. launch the real Activity through Greia Simulator at 1024×600;
6. traverse all six sections and all 36 final entries through normal child navigation;
7. exercise every final entry's signature interaction;
8. test pointer vs semantic keyboard/controller parity on the six architecture-stress entries;
9. perform the mandatory no-reading pass;
10. spot-check responsive layouts;
11. return exact evidence without repairing source inside the acceptance run.

The provider-free contracts validate the ledger→Voice Engine adapter, but the acceptance run does **not** generate narration.

The Simulator pass can evaluate the frozen visual/input source even if narration production is incomplete. Missing reviewed narration remains **audio acceptance pending**, never an invitation to add runtime synthesis.

Any later accepted-audio integration is a runtime-resource change and requires a fresh focused launch/survival/meaningful-interaction gate on that later exact state.

---

## 9. Current exact evidence

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

Not yet established on the reviewed current source:

- synchronized checked-in 378-row ledger;
- current focused-contract PASS;
- current `make verify` PASS;
- deterministic source-gate helper PASS;
- full 43-page Simulator traversal;
- visual/no-reading/input-parity acceptance;
- physical Acer/Pi acceptance;
- complete owner-approved narration coverage.

---

## 10. Next exact work

1. On the owner-controlled checkout, record exact `main` and preserve recorder state.
2. Run `python3 tools/encyclopedia_v01_source_gate.py --plan-only`.
3. Run `python3 tools/encyclopedia_v01_source_gate.py` exactly once. Stop on its first real failure; do not repair inside the evidence run.
4. If it passes, continue with the **Simulator stages** of `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md`; the helper does not replace them.
5. Return complete evidence and any deterministic voice-ledger/runtime-audio diff.
6. Separately execute the repository-wide Voice Production Engine local provider acceptance. Only after it is green should the JSONL adapter become the default encyclopedia generation path.
7. Fix only evidence-backed UX/performance/content defects as coherent tranches and rerun invalidated gates.
8. Let recording continue independently and integrate only `OWNER_ACCEPTED` clips.
9. Do not broaden topic scope until the 43-page v0.1 base is accepted.
