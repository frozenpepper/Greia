# Greia Encyclopedia — authoring root

**Status:** v0.1 source breadth complete; closure/audio synchronization ready for local execution  
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
5. **`skills/greia-voice-production/SKILL.md` and `tools/greia_voice_core/README.md` whenever producing narration**;
6. `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`;
7. `docs/adr/0028-platform-and-activity-localization-language-context.md`;
8. `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`;
9. `PLAN.md`;
10. `PROGRESS.md`;
11. `VOICE_RECORDING_REQUESTS.md`;
12. `HANDOVER.md`;
13. `docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md` when executing the frozen-v0.1 closure gate;
14. runtime `activities/enciclopedia_greia/` source relevant to the current task.

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
    VOICE_RECORDING_REQUESTS.md   # request/review/status authority
    voice_ledger.py               # shared deterministic ledger grammar
    sync_voice_requests.py        # research -> recording queue
    export_voice_batch.py         # REQUESTED ledger rows -> VoiceEngine JSONL
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

The source review deliberately preserves two historical research-document generations rather than rewriting research history:

- early entries use `Child-facing wording contract` with named human headings and `Italian` / `English` lines;
- later entries use `Approved narration wording` with explicit semantic cue IDs and `it` / `en` lines.

`sync_voice_requests.py` understands both forms. Legacy topics are retained only when their already-established queue cue IDs, presenter, voice ID and bilingual wording exactly match their research authority. New/canonical topics are generated directly from semantic cue blocks. A mismatch fails closed rather than silently changing a recorded request.

# Voice-production pipeline

The Encyclopedia uses the **repository-wide Greia Voice Production Engine** for all new narration generation. It does not maintain a second Chatterbox/native-TTS/Whisper implementation.

```text
VOICE_RECORDING_REQUESTS.md
        -> export_voice_batch.py
        -> tools/greia_voice.py batch
        -> staging audio + engine receipts
        -> human review/status update
        -> OWNER_ACCEPTED
        -> integrate_voice_assets.py
        -> runtime Activity assets
```

The ledger remains authority for exact text, semantic cue, speaker, target path and review status. The Voice Engine owns provider mechanics.

If historical prose in `VOICE_RECORDING_REQUESTS.md` describes direct Chatterbox/native provider mechanics, that mechanical guidance is superseded by:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
```

Do **not** bypass the engine. Preserve the queue's semantic rows and status ownership.

## 1. Synchronize research into the queue

Run:

```bash
python3 encyclopedia/sync_voice_requests.py
python3 encyclopedia/sync_voice_requests.py --check
```

Expected full-v0.1 invariant:

```text
36 factual topics
378 total bilingual recording rows, including 14 manual Home/section navigation rows
```

The synchronizer reads exact approved narration from `encyclopedia/research/**`, preserves recorder-owned status/notes, rejects duplicate identities, validates canonical presenter/voice pairing and refuses immutable drift on locked rows.

At the current repository checkpoint `VOICE_RECORDING_REQUESTS.md` is still the old 176-row checkpoint. The first local closure action is therefore to run the synchronizer and prove the 378-row result before the queue is called complete.

## 2. Probe the canonical production environment

Before synthesis:

```bash
python3 tools/greia_voice.py doctor
```

If a required provider is unavailable, follow:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Do not replace an unavailable canonical route with direct ad-hoc TTS/model commands.

## 3. Export REQUESTED rows to VoiceEngine

```bash
python3 encyclopedia/export_voice_batch.py \
  --output ./tmp/encyclopedia-requested-voices.jsonl
```

The exporter does **not** synthesize speech. It only converts eligible ledger rows into the stable semantic request contract:

```text
speaker
speech kind
locale
exact reviewed text
semantic cue ID
staging output path
```

Safety rules:

- only selected ledger statuses are exported; default is `REQUESTED`;
- staging paths must remain inside `encyclopedia/pages/**/assets/audio/<locale>/`;
- filename/locale/path mismatches fail closed;
- unsupported kinds/speakers fail before a provider is invoked;
- by default a requested row whose staging OGG already exists fails closed instead of overwriting a possibly unrecorded status update;
- the exporter never edits `VOICE_RECORDING_REQUESTS.md` and never marks a clip accepted.

## 4. Generate through the shared engine

Run the exported queue as one warm, single-worker batch:

```bash
python3 tools/greia_voice.py batch \
  --input ./tmp/encyclopedia-requested-voices.jsonl
```

The engine automatically owns:

```text
canonical reference/hash validation
Chatterbox vs deterministic system routing
Dani routing
model loading/reuse
single-worker locking
MLX cache cleanup
short-output rules
optional Whisper verification
WAV/OGG packaging
machine receipts
```

No Encyclopedia-specific authoring script should duplicate those mechanics.

Every generated clip is still **unreviewed** even when the engine returns `REVIEW_REQUIRED` and Whisper reports a plausible transcript.

## 5. Recorder staging and human review

The recording agent processes only `REQUESTED` rows.

After a technically viable generated take has been listened to and is ready for owner review, set:

```text
RECORDED_UNREVIEWED
```

Only the owner/human listening gate sets:

```text
OWNER_ACCEPTED
```

The queue column `FINAL_PATH` is the recorder's staging destination, not the shipped Activity location. Staging lives under:

```text
encyclopedia/pages/**/assets/audio/
```

and is intentionally git-ignored. This avoids committing hundreds of unreviewed/rejected takes and storing accepted audio twice.

Do not edit immutable cue/text/voice/path fields to repair a recorded request. Create a revised cue/filename and supersede the old row instead.

## 6. Package only OWNER_ACCEPTED audio

```bash
python3 encyclopedia/integrate_voice_assets.py
python3 encyclopedia/integrate_voice_assets.py --check
```

The integrator:

- ignores `RECORDED_UNREVIEWED` and every non-accepted status;
- validates staging path, locale and filename;
- requires OGG;
- preflights the complete accepted set before mutation;
- atomically packages accepted files under `activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...`;
- writes Greia's canonical locale-audio schema (`"cue": {"path": "assets/..."}`);
- updates locale audio mappings only after targets exist;
- preserves locale strings/metadata/unrelated audio entries;
- never generates speech and never adds a runtime dependency.

The accepted runtime copy is the file that may be committed and shipped.

## Provider-free authoring/source contracts

`tests/test_encyclopedia_authoring_tools.py` covers deterministic authoring seams without invoking a provider:

- rendered v0.1 queue must contain exactly 378 rows;
- runtime semantic narration cue IDs must equal synchronized ledger cues;
- every synchronized `REQUESTED` row must translate to a valid Voice Engine request;
- export is status-filtered and refuses existing requested outputs/path traversal by default;
- duplicate cue/locale rows are rejected;
- only `OWNER_ACCEPTED` rows are packaged;
- `RECORDED_UNREVIEWED` rows stay unreferenced;
- missing/non-OGG accepted sources fail closed;
- existing locale strings/unrelated audio mappings survive integration.

`tests/test_activity_enciclopedia.py` separately guards catalogue/research parity, accepted research formats, misconception guardrails, locale-audio schema, page navigation/engine boundaries and bounded resource behavior.

These contracts are authored but have **not** yet executed against the current reviewed source. Do not turn source inspection into a PASS claim.

## Current first-pass testing rule

The current truthful evidence label is:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

The next acceptance stage is:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

It synchronizes the queue, runs focused + repository source gates, packages only already-`OWNER_ACCEPTED` narration, then performs the deferred full Simulator traversal/input/no-reading/responsive review. Targeted fixes follow concrete evidence; new topic breadth remains frozen.
