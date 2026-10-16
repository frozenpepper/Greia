# Greia Encyclopedia v0.1 — Post-Build Drift Review

**Date:** 2026-08-27  
**Activity:** `org.greia.enciclopedia`  
**Runtime:** `activities/enciclopedia_greia/`  
**Authoring root:** `encyclopedia/`  
**Scope:** architecture, performance, page ownership, navigation, research/voice coordination, localization/audio integration, tests, repository hygiene, acceptance readiness  
**Evidence:** SOURCE REVIEW ONLY — tests and Simulator not executed in this review environment

## 1. Review purpose

The first construction pass intentionally created the complete 43-page v0.1 source breadth before running the Greia Simulator. This review was therefore performed as a freeze audit before the deferred consolidated acceptance run.

The review specifically looked for:

- engine or architecture drift as page count grew;
- unjustified inheritance/framework growth;
- page-domain state leaking into shared owners;
- hot-loop work inconsistent with the Acer Aspire One floor;
- pointer/semantic navigation divergence;
- runtime TTS/speech-recognition/AI/network creep;
- research authority drift;
- voice-ledger/runtime cue drift;
- localization schema incompatibility;
- recorder/accepted-audio source-control duplication;
- tests that accidentally became a third source of product truth;
- documentation/evidence overclaims.

## 2. Architecture result

The core architecture remains sound.

`enciclopedia_engine.py` is still deliberately small and subject-neutral. It owns only the page lifecycle contract, `PageContext`, explicit page registry, bounded history/navigation and semantic input vocabulary. No animal, planet, anatomy, geology, machine or history-specific behavior has leaked into it.

`main.py` remains a thin composition root. Subject interactions stay in their page modules. Small model objects remain limited to real coupled mutable state rather than class-count consistency.

No generic `PlanetPage`, `AnatomyPage`, `MachinePage`, history base class, exhibit DSL or physics framework is justified by the current source, and none was introduced during the review.

The authoring catalogue and runtime catalogue both contain the same frozen 43-page v0.1 inventory. Tests now compare those two authorities directly rather than maintaining another copied 43-page list.

## 3. Performance/resource review

Existing performance boundaries remain appropriate for the reference floor:

- text surfaces are cached by `CachedEncyclopediaTypography`, max 160;
- shared character renditions are bounded, max 24;
- prerecorded voice sounds are lazy/bounded, max 32;
- effects/particles/timers are page-local and finite;
- pages do not intentionally decode images, smooth-scale reusable assets, construct fonts, walk filesystems or perform provider/network work per frame;
- frame delta is bounded by the Activity app.

No new performance framework was needed.

The review narrowed one overly broad exception in `EncyclopediaAudio.play()`: localization lookup now catches canonical `LocalizationError` instead of arbitrary `Exception`; mixer/file failures retain explicit fail-soft handling.

## 4. Critical defect — locale audio schema mismatch

### Finding

The first version of `encyclopedia/integrate_voice_assets.py` wrote accepted narration into locale bundles as bare strings:

```json
{
  "encyclopedia.animals.lion.intro": "assets/audio/it/animals/lion/intro-tito.ogg"
}
```

Greia's canonical `LocalizedResources` parser does **not** accept that shape. `src/greia_platform/localization.py` requires each audio cue to be an object containing at least `path`:

```json
{
  "encyclopedia.animals.lion.intro": {
    "path": "assets/audio/it/animals/lion/intro-tito.ogg"
  }
}
```

The original packager could therefore have reported its own integration success while producing a locale bundle that Greia would reject later.

### Fix

`integrate_voice_assets.py` now emits the canonical object form and preserves unrelated existing audio objects verbatim. The Activity source contract validates that every locale audio entry is an object with `path`, optional `caption_key`, a safe Activity-relative asset path and supported audio suffix. Authoring-tool tests expect the same canonical shape.

This defect is considered closed in source, but execution evidence is still pending.

## 5. Critical defect — mixed research narration formats

### Finding

The 36 research authorities were created across multiple construction tranches and intentionally preserve two historical document formats.

Early/pilot authorities use human-readable sections such as:

```text
## Child-facing wording contract
### Intro — Tito
**Italian**
`...`
**English**
`...`
```

Later authorities use machine-readable semantic cue blocks:

```text
**Presenter:** Leo (`greia.leo.v1`)
## Approved narration wording
### `encyclopedia.space.mars.intro`
**it:** ...
**en:** ...
```

The first `sync_voice_requests.py` implementation only parsed the newer format. It would have failed immediately on legacy topics such as Lion/Octopus/Saturn and could not have produced the advertised 378-row ledger.

### Fix

The synchronizer now supports both research generations without rewriting historical research files.

For canonical-format topics it derives cue rows directly from semantic headings and validates Presenter -> canonical voice ID.

For legacy-format topics it refuses to invent cue IDs from prose labels. Instead it requires those topics to already exist in the established ledger, preserves their cue IDs/filenames/paths, and validates in order that:

- research block count matches established cue count;
- both locale rows exist;
- Italian and English wording exactly match the research authority;
- named speaker exactly matches the ledger;
- ledger voice ID matches the canonical presenter voice.

Any mismatch fails closed. Recorded wording is never silently rewritten.

## 6. Test-authority drift removed

The Activity source test had started to contain its own full page/topic inventories and assumed only the newer research template. That made the test itself a competing product authority.

It now:

- derives the runtime registry from `enciclopedia_catalogue.py`;
- derives the planned inventory from `encyclopedia/pages/catalogue.py`;
- requires exact equality and 43 unique pages;
- discovers research authorities from `encyclopedia/research/*/*.md` instead of carrying a copied 36-topic list;
- requires discovered research files to exactly cover all factual runtime entries;
- recognizes both documented historical research formats;
- retains targeted high-risk misconception guards instead of reproducing all factual prose.

This keeps tests as guards rather than shadow specifications.

## 7. Runtime cue / voice-ledger parity guard

A new authoring contract renders the complete synchronized ledger and extracts semantic `encyclopedia.*` narration cue constants from runtime page modules. The two cue sets must be equal.

This prevents three failure classes:

- a runtime page asks for a cue the recording pipeline never knows about;
- a voice request survives after runtime stopped using that narration;
- a cue is renamed in one layer without the corresponding authority update.

The rendered ledger is also required to contain exactly 378 cue/locale rows.

## 8. Recorder staging versus shipped audio

Queue `FINAL_PATH` values point into:

```text
encyclopedia/pages/**/assets/audio/<locale>/...
```

Those paths are the recorder's final **staging** destinations. They are not the shipped Activity paths.

The review added this staging tree to `.gitignore` so unreviewed/rejected takes are not accidentally committed and accepted clips are not stored twice.

Only rows already marked `OWNER_ACCEPTED` are copied by `integrate_voice_assets.py` into:

```text
activities/enciclopedia_greia/assets/audio/<locale>/<page-path>/...
```

The runtime copy is the normal committed/shipped asset.

## 9. Audio integration safety

The accepted-audio integrator now has these source-level guarantees:

- only `OWNER_ACCEPTED` rows are managed;
- `RECORDED_UNREVIEWED` is ignored;
- source path, locale and filename must agree;
- path traversal/escape is rejected;
- source must look like an OGG container;
- every accepted source and both locale bundles are preflighted before mutation;
- target OGGs are written atomically;
- locale maps are written only after target audio files exist;
- existing locale strings/metadata remain intact;
- unrelated non-ledger audio mappings are preserved;
- tool is authoring-only and never imported by child runtime.

## 10. Navigation/input review

The six section families retain explicit semantic destination mappings rather than index-specific special cases. Pointer/touch and semantic command paths route through the same page/navigation owners.

The review did not find a reason to add another navigation abstraction. Actual pointer/controller parity remains a Simulator evidence obligation rather than a source-only claim.

## 11. Research/content drift review

The authoritative v0.1 content scope remains unchanged at 43 pages. No new topic was added during review.

Known high-risk scientific guardrails remain represented in research/source contracts, including bee social diversity, penguin habitat diversity, frog reproductive diversity, Venus/Mercury temperature, Moon phases/rotation, clouds, global ocean connectivity, child/adult bone counts, tongue taste-map rejection, magnetic-material scope, energy-neutral gearing, airplane lift misconceptions, bridge scope, dinosaur/bird/human chronology, mammoth taxonomy, cave-art uncertainty and human pyramid engineering.

The earlier accidental `earth.rocks` planning note remains historical only; the actual plan/runtime scope correctly uses `earth.ocean`.

## 12. Evidence boundary

This review used source inspection and persisted source corrections only.

The following have **not** executed against the post-review source:

- `sync_voice_requests.py` producing the real checked-in 378-row ledger;
- `tests.test_encyclopedia_authoring_tools`;
- `tests.test_activity_enciclopedia`;
- focused Activity/project suites;
- `make verify`;
- Greia Simulator launch/survival;
- 43-page reachability/signature interaction pass;
- no-reading visual review;
- responsive Simulator review;
- physical Acer/Pi performance or UX acceptance.

Therefore the truthful current label remains:

```text
SOURCE-REVIEWED / TESTS-UNEXECUTED / SIMULATOR-UNVERIFIED
```

## 13. Next exact gate

Do not add v0.1 breadth.

Execute:

```text
docs/testing/GREIA_ENCYCLOPEDIA_V01_CONSOLIDATED_ACCEPTANCE.md
```

on an owner-controlled local checkout.

The first stage must synchronize the old 176-row Markdown queue into the complete 378-row queue. If legacy/canonical research validation fails, preserve that first failure and return it; do not rewrite authorities during the evidence run.

If source gates are green, continue through the full real-Simulator 1024x600 traversal, signature interactions, pointer/semantic parity, no-reading review and responsive spot checks. Narration may remain partially pending; missing owner-accepted audio must be reported separately and never replaced by runtime TTS.
