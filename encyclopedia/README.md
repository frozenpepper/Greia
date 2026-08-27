# Greia Encyclopedia — authoring root

**Status:** v0.1 source breadth complete; closure/audio synchronization in progress  
**Created:** 2026-08-27  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Runtime inventory:** 43/43 planned executable pages  
**Current evidence:** SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED

This directory is the long-lived authoring source of truth for the Greia Encyclopedia workstream. Runtime code lives in the normal first-party Activity package; this root owns the detailed plan, factual research/provenance, voice coordination, deterministic authoring tools and append-only implementation progress.

## Read order for encyclopedia work

1. repository-root `AGENTS.md`;
2. repository-root `README.md`;
3. `skills/greia-activity-authoring/SKILL.md` and its required companions;
4. `skills/greia-visual-authoring/SKILL.md` when creating/integrating visual assets;
5. `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`;
6. `docs/adr/0028-platform-and-activity-localization-language-context.md`;
7. `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`;
8. `PLAN.md`;
9. `PROGRESS.md`;
10. `VOICE_RECORDING_REQUESTS.md`;
11. `HANDOVER.md`;
12. `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md` when executing the frozen-v0.1 closure gate;
13. runtime `activities/enciclopedia_greia/` source relevant to the current task.

The repository's platform authorities remain authoritative. The encyclopedia is one normal first-party Activity and may not bypass Greia lifecycle, protected chrome/Home, semantic input, localization, profile, package or runtime-policy ownership.

## Core architecture

The encyclopedia is **one Greia Activity with a deliberately tiny page engine**.

Each section or final entry is an executable Python page and may behave differently:

- planets orbit;
- a volcano erupts;
- a heart beats;
- gears transfer motion;
- a frog changes through a life cycle;
- a fossil is brushed out of sediment;
- a cave wall is explored with light;
- a pyramid is built through a bounded schematic model.

`enciclopedia_engine.py` standardizes lifecycle/navigation/input seams only. Subject knowledge and subject-specific state stay in page modules. Do not create a generic exhibit/content framework merely to reduce superficial repetition.

## Hard runtime boundaries

The child device must not require:

- speech recognition;
- runtime narration TTS;
- a voice model;
- a language model;
- network access for factual content;
- heavy physics;
- browser/web runtime support.

All presenter narration is prerecorded during authoring. Dani/system speech and pronunciation-critical deterministic speech are also generated ahead of time on parent/development hardware and packaged as ordinary audio assets.

The extreme performance reference remains first-generation Acer Aspire One-class hardware. Runtime animation therefore uses simple shapes/sprites, cached surfaces, bounded collections and lightweight math.

## Runtime/authoring split

```text
encyclopedia/
    PLAN.md                       # product/architecture/content authority
    PROGRESS.md                   # append-only implementation ledger
    HANDOVER.md                   # exact continuation state
    VOICE_RECORDING_REQUESTS.md   # single human/agent recording queue
    voice_ledger.py               # shared deterministic ledger grammar
    sync_voice_requests.py        # research -> recording queue
    integrate_voice_assets.py     # OWNER_ACCEPTED -> runtime assets/maps
    research/                     # one factual authority per final entry
    pages/catalogue.py            # complete planned 43-page v0.1 inventory

activities/enciclopedia_greia/
    activity.toml
    main.py                       # thin composition root
    enciclopedia_app.py           # Activity lifecycle/input composition
    enciclopedia_engine.py        # tiny page lifecycle/navigation contract
    enciclopedia_audio.py         # prerecorded semantic audio playback
    enciclopedia_services.py      # bounded shared presentation services
    enciclopedia_catalogue.py     # exact implemented runtime registry
    pages/                        # 43 executable section/entry modules
    locales/                      # Italian/English runtime resources/audio maps
    assets/audio/                 # only accepted packaged narration
```

## v0.1 source breadth

The source inventory is complete:

```text
1 Home
6 section pages
36 factual final entries
-----------------------
43 executable pages
```

All six planned content families are source-complete:

- Animals — 6/6 entries;
- Space — 10/10 entries;
- Earth & Nature — 5/5 entries;
- My Body — 5/5 entries;
- Science & Machines — 5/5 entries;
- Long Ago — 5/5 entries.

Every factual final entry has a research authority containing accepted claims, scope guardrails, interaction-to-fact mapping, sources and approved Italian/English narration.

## Voice-production pipeline

`VOICE_RECORDING_REQUESTS.md` remains the **single human/agent coordination queue**. The recorder may change only `STATUS` and `RECORDER_NOTES` and add the requested staging audio files.

### 1. Synchronize research into the queue

The deterministic synchronizer prevents factual rows from being hand-transcribed:

```bash
python3 encyclopedia/sync_voice_requests.py
python3 encyclopedia/sync_voice_requests.py --check
```

Expected full-v0.1 invariant:

```text
36 factual topics
378 total bilingual recording rows, including 14 manual Home/section navigation rows
```

It reads exact approved narration from `encyclopedia/research/**`, derives stable cue/locale filenames and staging paths, preserves recorder-owned status/notes, rejects duplicate identities and refuses immutable drift on locked rows.

At the current repository checkpoint the tool exists and is hardened, but `VOICE_RECORDING_REQUESTS.md` has **not yet been regenerated from the old 176-row checkpoint**. Run the synchronizer before treating the queue as complete.

### 2. Record and review

The recording agent processes only `REQUESTED` rows using the voice-production authorities referenced at the top of the queue. A technically valid generated clip becomes `RECORDED_UNREVIEWED`. Only the owner/human listening gate changes it to `OWNER_ACCEPTED`.

Do not edit immutable cue/text/voice/path fields to repair a recorded request. Create a revised cue/filename and supersede the old row instead.

### 3. Package only OWNER_ACCEPTED audio

Once one or more clips are owner-accepted:

```bash
python3 encyclopedia/integrate_voice_assets.py
python3 encyclopedia/integrate_voice_assets.py --check
```

The integrator:

- ignores `RECORDED_UNREVIEWED` and every non-accepted status;
- validates the requested staging path, locale and filename;
- requires an OGG container;
- preflights the complete accepted set before any mutation;
- atomically packages accepted files under `activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...`;
- updates locale `audio` mappings only after their target files exist;
- preserves locale strings and metadata;
- never generates speech and never adds a runtime dependency;
- deliberately does not delete unreferenced files from the runtime audio tree.

This makes partial delivery safe: the local agent may record clips over many sessions, and the runtime can package only the subset the owner has actually accepted.

## Provider-free authoring contracts

`tests/test_encyclopedia_authoring_tools.py` covers the deterministic authoring seams without invoking any model/provider:

- rendered v0.1 queue must contain exactly 378 rows;
- duplicate cue/locale rows are rejected;
- only `OWNER_ACCEPTED` rows are packaged;
- `RECORDED_UNREVIEWED` rows stay unreferenced;
- missing or non-OGG accepted sources fail closed;
- staging path traversal is rejected;
- existing locale strings survive audio-map integration.

These tests are authored but have not yet been executed in this construction pass.

## Current first-pass testing rule

At owner direction, the initial construction pass was source-first. Do not retrospectively claim Simulator evidence for pages that were intentionally built without page-by-page launches.

The current truthful evidence label is:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

The next acceptance stage is the exact fail-closed procedure in:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

It synchronizes the 378-row queue, runs focused + repository source gates, packages only already-`OWNER_ACCEPTED` narration, then performs the deferred full 1024x600 reachability/signature-interaction pass plus input-parity, no-reading and responsive Simulator review. Targeted fixes follow from concrete evidence; new topic breadth remains frozen.
