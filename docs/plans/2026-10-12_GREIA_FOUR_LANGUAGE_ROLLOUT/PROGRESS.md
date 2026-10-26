# Greia Four-Language Rollout — Progress Ledger

**Product authority:** [PLAN.md](./PLAN.md)  
**Local voice execution:** [LOCAL_AGENT_VOICE_PRODUCTION.md](./LOCAL_AGENT_VOICE_PRODUCTION.md)  
**Single local task queue:** `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`  
**Evidence status:** The separately authorized 2026-10-21 V3 replacement completed with 1,340 pending-review receipts and full policy-v2 automated screening (1,115 PASS / 225 WARN). Human listening remains open. The prior source `make verify` remains NOT GREEN on recorded host/source failures; no GUI, Simulator or physical-install acceptance is claimed.

## 2026-10-26 — Language manifests + contributor data workflow (source only)

Owner-authorized extension of the four-language foundation: the offered-device
language set now loads from one packaged per-locale `manifest.json` directory;
four existing EN/IT/ES/FR entries preserve the currently selected list.
Installer, on-device Parent settings and Parent API use the discovered set.
Paginated selection layouts avoid an ever-growing single-screen tile grid.
Optional `ui.json` overlays provide additional installer/Shell/Parent strings
without new Python language lists; the English-reference Activity+UI scaffold,
manifest/source coverage checker, focused tests and contributor skill/guide
were added. Voice Production Engine, selected v0.3 masters and Parakeet-TDT v3
policy remain unchanged. Missing audio, locale-specific curriculum, glyph
coverage and layout evidence still block introducing a new selectable locale.
This is **SOURCE-WIP**; no provider-free tests, simulator, full OS image, or
real-device language acceptance ran through this GitHub connection. Existing
A/B acceptance evidence is not transferable to new source commits.

## 2026-10-21 — V3 selected-master corpus replacement and automated review complete

The owner-selected Dani v5-02, Momo v3-01 and Tito v3-01 masters were promoted
to semantic IDs `greia.dani.v3`, `greia.momo.v3` and `greia.tito.v3`; the prior
v0.2 canonical master set for Lilli, Leo and Flash is unchanged. The separately
frozen v3 scope completed serially through VoiceEngine with exit 0: **1,340 DONE,
3,575 PRESERVED, and zero READY/FAILED/NEEDS_RECOVERY/BLOCKED**. Counts: Dani 392
(EN/IT 102 each, ES/FR 94 each), Momo 284 (71 per locale), Tito 664 (166 per
locale). The 1,340 selected scripts/locales matched the completed v2 plan; the
new plan retained every prior row/path and six canonical-reference rows. Original
bytes and receipts are recoverable from the external v3 run backups; the frozen
v2 plan/journal remain unchanged. One effectively-silent Dani/EN provider job
was inspected and retried once only after terminal failure and empty queue; the
retry completed and remains PENDING. Exact evidence is in external
`run-v1/recovery-002.md` and the run journal/log.

The full local automated review used cached `mlx-community/whisper-tiny` and
policy `greia-audio-screen-v2`; `full_corpus_coverage=true`,
`eligible_asr_complete=true`: **1,115 PASS / 225 WARN / 0 FAIL / 0 BLOCKED**.
ASR counts: 608 PASS, 199 WARN, 533 `NOT_APPLICABLE_POLICY`; warning flags are
199 ASR mismatch/error, 13 trailing silence ≥1.5s, 11 leading silence, 6 low
level and 1 internal pause. The command exits 2 because warnings are retained;
full traversal and eligible ASR are complete. Identity, acting/mood,
pronunciation truth, independent language identification and small-speaker
intelligibility remain unassessed. All new receipts remain `human_review=PENDING`.

Validated external Takeboard batch contains all 1,340 entries, each human state
`unreviewed`; it is served on fresh port 8799 at
`http://127.0.0.1:8799/`. Existing 8794–8798 review servers were untouched.
Batch and full report/log remain external under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/`. Continue with
human listening across all character/language combinations, emphasizing the
225 machine warnings, 533 ASR policy exclusions, long narration, numbers/words,
identity and acting. The prior `make verify` fast lane is NOT GREEN (2 failures,
4 errors, 8 skipped); the voice source suite was 72/72 PASS. No runtime playback,
image, release, Simulator, physical or human listening acceptance is claimed.

## 2026-10-21 — V2 corpus replacement completed

The frozen V2 plan completed with **4,168 DONE, 741 PRESERVED, and zero READY,
FAILED, NEEDS_RECOVERY, or BLOCKED**. The persisted journal and all DONE receipt
request metadata/output hashes were checked against the frozen plan; every new
recording remains `human_review=PENDING`. Interrupted strawberry was recovered
after establishing no earlier submitted job or candidate and completed as
`20261020-235846-ff7ff0a5`. Bean's timeout was matched by exact key and frozen
request/master data to already-completed job `20261021-000412-50cad22f`; its
result was installed offline without another inference. External originals,
candidates, plan and journal remain under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-v2/`.

The serial runner finished; VoxStage queue was empty and the model was unloaded.
`make verify` ran 5,472 tests: 1 failure, 4 errors, 8 skipped. The failures are
the known macOS host cases: three missing `lsblk` installer errors, the
`tools/build_profile.py` execute-bit error, and an MBR diagnostic-message
mismatch. The corpus-size regression was corrected using the existing packaging
pipeline at bounded Vorbis quality 3, reducing Encyclopedia activity footprint
below its unchanged 50 MiB cap; this reused persisted jobs and did not re-run
inference. Focused packaging/voice tests and activity validation passed. No
ASR, listening, GUI, Simulator or physical acceptance is claimed. See HANDOVER
and the runbook; selectively publish the authorized corpus, receipts, manifests,
leftover deletions and scoped source/docs to `main`.


## 2026-10-19 — Corpus replacement checkpoint: 700 complete

Current status is **700 DONE, 1 GENERATING, 3,842 READY, 167
BLOCKED_METADATA, and 598 PRESERVED**. The active item is Encyclopedia Greia
EN `activities/enciclopedia_greia/assets/audio/en/body/senses_hearing.ogg`;
the serial run is shell session `85073`, external work/log/journal directory
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`, with
VoxStage PID `19719`. English animal and body narration has begun; longer clips
are taking approximately 15–60 seconds each. Progress is healthy with no new
failures since the explicit idle-confirmed retry recorded above.

Every new receipt remains `human_review=PENDING`. Whisper verification is off;
no ASR or human listening acceptance is claimed. The 167 metadata gaps remain
unresolved and are skipped while independent READY cues proceed. Retain the
external journal, candidate outputs and original backups; preserve unrelated
untracked `final.mp4` and `launch-video/`. Continue monitoring the same run and
inspect any uncertain provider job before an explicit retry.


## 2026-10-19 — Corpus replacement checkpoint: 602 complete

Current full-pass status: **602 DONE, 1 GENERATING, 3,940 READY, 167 BLOCKED_METADATA, 598 PRESERVED**; active Costruiamo Ponti IT `too_heavy.wav`. Run session `85073`, external directory/log/journal `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`, VoxStage PID `19719`.

One failed provider output is recorded: Bottega delle Misure ES `prompt_order_length.wav` was rejected as effectively silent (job `20261019-201154-4db4072d`, submission key `greia-58a10aed9a584858a4e3b3b49069ea2f`). The VoxStage job was terminally failed with no result WAV; queue 0/idle was confirmed and original bytes were unchanged. The explicit retry used a new job `20261019-201240-59474c63` and key `greia-aa79d4bc7a31459cb64cd97b2d0d86f0`; it completed, was transactionally installed, and its receipt remains `human_review=PENDING`. The full pass resumed afterward. No source bug was found and no second failure is present.

All current generated receipts remain pending human review; Whisper is unavailable and verification is off. No ASR/listening acceptance is claimed. The 167 blocked legacy rows remain unmodified absent exact source-backed scripts. Continue monitoring the full READY pass and preserve the external journal, originals and log. This checkpoint updates current state without rewriting launch/recovery history.

## 2026-10-19 — Corpus replacement checkpoint: 304 complete

The active owner-authorized full pass now reports **304 DONE, 1 GENERATING, 4,238 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. Baia delle Orche FR activity-title is current. Process session `45485` writes to the external prepared run directory/log; VoxStage PID `19719` is loaded and remains the single worker. Progress heartbeat and transactions are healthy; no failed/recovery rows. New outputs and receipts stay human-review PENDING; no ASR or listening acceptance is claimed.

Alfabeto Leo's four-language set is complete; Baia delle Orche cues continue. No blocked script override has been verified, and READY work advances without them. Continue monitoring, preserve the external journal/backups, and do not regenerate DONE rows. This is a new dated checkpoint; earlier entries remain as history.

## 2026-10-19 — Corpus replacement checkpoint: 198 complete

Latest status for the active owner-authorized full pass: **198 DONE, 1 GENERATING, 4,344 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. Alfabeto Leo IT `ask_G.wav` is active. Shell session `45485`, log and journal `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`, VoxStage PID `19719`. Heartbeats and completed transactions continue; no failures or recovery work. New receipts remain `human_review=PENDING`; no ASR or human listening acceptance is claimed.

Exact-script research has not validated an override yet. Keep blocked rows excluded while READY rows proceed; continue the serial run and recover only substantiated scripts without revisiting DONE cues. This checkpoint supersedes the earlier count above while preserving that launch history.

## 2026-10-19 — Corpus replacement checkpoint: 101 completed cues

Updated checkpoint for the running owner-authorized pass: **101 DONE, 1 GENERATING, 4,441 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. Alfabeto Leo ES `guess_prompt.wav` is in progress. The run remains shell session `45485`, production log/journal `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/production.log`, and shared VoxStage PID `19719`. The worker is loaded with a single active job; progress heartbeat and completed transactions continue.

No FAILED/NEEDS_RECOVERY cue or source bug is present. Completed takes retain explicit acting prompts and `human_review=PENDING`. Whisper remains unavailable and verification is off; no audio has been human-reviewed in this operation. The 167 unresolved legacy rows remain blocked while READY production continues; exact script recovery has not yet established an override. This checkpoint updates the current count while preserving the earlier launch entry as history.

## 2026-10-19 — Owner-authorized existing-corpus replacement launched (LOCAL RECORDING, in progress)

Started the current executable work order, `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, using the prepared external inventory at `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`. The frozen plan's v0.2 registry-manifest SHA matches the current source; all six per-character delivery prompts are present. A bounded 4-cue pilot completed, then the full serial READY pass started and is resumable in shell session `45485`; production log is in the external work directory. The VoxStage shared worker PID is `19719`.

Latest checkpoint: **25 DONE, 1 GENERATING, 4,517 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. The currently active cue is Alfabeto Leo EN `ask_J.wav`. Every completed cue has a replacement receipt whose `human_review` remains `PENDING`; the external journal shows completed transactions. Verification is off because optional Whisper is unavailable on this host (NumPy/Numba import mismatch). No ASR or human listening acceptance is claimed. Existing master/reference files remain outside generation scope and deterministic isolated letters/syllables remain preserved.

The 167 metadata blockers remain excluded while READY work proceeds. Exact source/history recovery is ongoing; no overrides were applied without sufficient script authority. No provider failure or source bug has occurred. Continue monitoring progress and VoxStage job status; resolve only exact recovered scripts without touching DONE cues. On completion, reconcile final counts/retries, report unresolved source gaps, retain the external backups/journal/candidates, update HANDOVER and the active architecture-plan ledger, and commit/push the reviewable PENDING replacements to `main`. Human acceptance and release publication remain separate. Unrelated untracked `final.mp4` and `launch-video/` remain preserved.


## 2026-10-15 — Continuation: shared locale composition across Activities, regional fallback

**Actual implementation on GitHub main:** extended `src/greia_platform/localization.py` so region-tagged locale lookups try the exact variant, then base language, then English for both text and prerecorded speech; the eager `speech_paths()` catalogue uses the same ordering. Conventional filenames preserve semantic variants. No installer, built-in recording, receipt or language-registry asset was changed.

**Removed duplicated Activity localization bootstraps:** Word Forest, Magic Syllables, Rhyme Festival, Sound Workshop, Momo's Lights, Number Garden, Magic Mirrors, Opposites, Orca Bay, Number Forest, Momo's Faces, Four Seasons and Quattro Amici's `build_app` now resolve language via the existing manifest-aware `activity_resources()` rather than rebuilding `ActivityLocaleSupport` in every file. Momo's Faces and Four Seasons titles now use `resources.text("activity.title")`. In Quattro Amici, previously the voice owner received raw profile locale while UI used Activity fallback: it now receives the resolved Activity language.

**Audio-path consolidation:** removed independent prerecorded-file scans from the previous Word Forest, Alphabet Leo, Measurement Workshop and Ten House adapters; all now use the platform `speech_paths()` stem→Path catalogue, retaining their own Pygame sound managers, sound effects and playback timing. Existing standalone SoundManager callers keep their compatibility route. A source inspection of the other 19 audio modules found most remaining modules are synthesized SFX, recording/playback of the child's own creations, or semantic audio callers: these do **not** warrant migration for localization alone.

**Tests:** added three focused cases to `tests/test_shared_localized_audio_paths.py` for `es-MX → es → en`, filename semantic variants and effective IT/EN manifest languages of 13 migrated Activities. GitHub tree/manifest and code readback were used, **but executable Python/Pygame/UI/hardware tests have not been run**. Do not claim acceptance or that all four languages are released. Existing 35 genuinely missing new recordings remain a separate local-agent order; every already committed audio recording remains personally owner-approved.

**Source authority:** [`SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`](./SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md). Next: execute focused localization + launcher + representative Activity tests once in an executable checkout; fix resulting behavioral bugs; verify spoken cue timing and language in a live Simulator. No anti-tamper, redundant language JSON maps or wholesale clip regeneration.

## 2026-10-15 — Shared Activity localization: additional speech integration

**Source implemented on `main`, no changes to any approved voice asset.**

- `LocalizedResources.audio_path` now checks both existing ordinary speech layouts: `assets/audio/<lang>/` and `locales/<lang>/audio/`. `LocalizedResources.speech_paths()` enumerates the localized or fallback-English prerecorded files for older eager-preloading Activities; mixed-case filenames are accepted via explicit filename aliases. This consolidates path lookup without moving or regenerating recordings.
- Migrated **11 additional Activity-level speech consumers**: Number Forest, Rhyme Festival, Sound Workshop, Momo's Lights, Momo's Faces, Opposites, Four Seasons, Number Garden, Orca Bay, Magic Mirrors, and Quattro Amici. The first ten now use `audio_path`/`speech_paths` for Activity-packaged voice; Quattro Amici uses `shared_character_audio_path` for the shared v0.2 character recordings. Each Activity retains sound effects, speech queues, channels and mixer ownership. All updated composition roots pass existing shared localization resources where applicable.
- Source inventory identified that `faccine_momo`, `mondo_contrari` and `quattro_stagioni` have prior EN/IT voice WAVs under `locales/<lang>/audio/`, while newly accepted ES/FR equivalents were committed under `assets/audio/<lang>/`. This was a real accessibility defect; file-aware shared resolution now spans both instead of copying files into new locations.
- `tests/test_shared_localized_audio_paths.py` extended to exercise both layouts, mixed-case stems, real shared character clips, and ten real ES/FR Activity clip filenames; their expected paths were verified against the nontruncated current GitHub tree, including Spanish curriculum-specific stems. No new test suite or governance machinery created.
- Skills updated for `speech_paths` and platform-owned shared character voice lookup. Exact rationale/paths live in `SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md` (same plan folder).
- **Testing:** GitHub source readback and path inventory only. No runnable checkout, Python unit invocation, audio decode/Pygame GUI playback, installer or physical-device acceptance in this session. These are **UNEXECUTED**, not PASS. Existing selector remains EN/IT; ES/FR release decision still open. The 35 narrowly missing voice files remain assigned to the separate local agent recording order.

## 2026-10-15 — Third shared localization slice: My Time silent-audio repair

Connected My Time's **14 already-approved IT/EN instructional recordings** (seven speech cues per language) through the shared `LocalizedResources.audio_path` filename convention. Previous My Time audio loader required explicit JSON `audio` entries which were empty and blocked playback even when `locales/en/audio/*.wav` and `locales/it/audio/*.wav` existed; new adapter uses `filename=cue.replace(".", "_") + ".wav"`. My Time composition now uses `activity_resources`, and launcher title resolver supports both `activity-title.wav` and legacy `activity_title.wav` (two approved My Time files). Pure source tests for actual installed voice files, French→English fallback and launcher titles updated; obsolete Italian-from-English fallback test corrected.

**Verification:** source reviewed, files known present in GitHub; tests have **not yet executed**, no Pygame listening evidence. My Time remains in `activity_incubator/`; ES/FR OS release selection stays EN/IT-only. All owner-approved audio bytes unchanged. Updated `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md` to remove stale unrecorded claims. Full code plan: `SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`.

## 2026-10-15 — Shared Activity localization + prerecorded audio resolver: first implementation

**Owner direction:** simple centralized semantic `text(key)` / `audio_path(key)`; the selected-language audio file wins, otherwise English, otherwise no speech (including phonemes for now). User modifications are allowed; no anti-tamper scheme. All previously committed recordings are personally owner-approved, untouched. This is the active new work slice in [`SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`](./SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md).

**Implemented on GitHub `main`:**
- `greia_platform.localization` now owns file-aware language lookup: `LocalizedResources.audio_path`, compatible `audio_cue`, canonical English audio-path projection, legacy Italian-only semantic alias projection, `activity_resources` manifest + profile factory, English missing-string fallback.
- Launcher Activity title routing delegates to shared resolver. Its existing collection fallback still works.
- Five Activity sound owners adopted shared path selection without touching Pygame SFX/gameplay: Measurement Workshop, Ten House, Magic Syllables, Alphabet Leo, Word Forest; factory used by the first two and Alphabet.
- Encyclopedia, Dolphin and Submarine already used the shared `audio_cue` method, so their staged ES/FR narrator assets are now discoverable by a shared lookup. No duplicate ES/FR audio tables authored.
- `tests/test_shared_localized_audio_paths.py` added, plus owner-directed fallback expectation updated in `tests/test_localization.py`. Tests include actual committed ES/FR asset paths and IT-only Submarine alarm path. **Authored only, not run in the GitHub connector environment.**
- `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `LAUNCHER_SPOKEN_LABELS.md` now describe the **implemented** new Activity API and legacy compatibility. Approved audio bytes, `activity.toml` supported-language declarations, OS language selector, installed system and installer remain untouched.

**Still open:** other legacy file-scanning Activity sound owners; exact full Pygame/source regression and live playback; ES/FR acceptance and staged-to-release locale promotion; separately requested 35 genuinely missing new clips by local recording agent. Current project-wide validation is **UNVERIFIED**, not a PASS. Do not turn source code review into audio/GUI acceptance.

## 2026-10-12 — Initial owner-authorized implementation: L0 + L1 tooling + L2 installer catalogue staging

### Context

The canonical Greia OS currently advertised **twelve** selectable
languages while its installer `i18n.py` had an English source
vocabulary and an Italian translation map only. The on-device
Parent Settings, Parent API and installer drew from the same overbroad
`SUPPORTED_SYSTEM_LANGUAGES` registry. The browser Parent client
was checked: its language grid reads `snapshot.language.languages`
from the API rather than a duplicated twelve-item hard-code; it does
still have English UI strings independently requiring L3 extraction.
Built-in Activity localizations primarily had `en` and `it` only,
with legacy voice gaps.

The owner requested an honest selector now, a full Spanish/French
integration project, and a separate detailed local-agent voice work
order covering ES/FR plus missing EN/IT.

### Implemented

1. **L0, source:** `src/greia_platform/system_language.py` now
   advertises only `en` and `it` through the canonical registry.
   Installer chooser, on-device Parent panel, Parent API and narrow
   privileged language helper already use that same registry, so
   all four selector/mutation interfaces narrow together.
   There is no migration that rewrites immutable installation records
   or historical unsupported `language.json` state. Reading legacy
   unsupported locale safely falls back to English until a parent
   explicitly selects a supported value. Updated
   `tests/test_system_language.py` to cover the two-language
   registry, rejected legacy tags, safe historical persistence,
   current Parent API list and settings.
   Source: `132b10ea`, `f511e5a4`.
2. **L2, staged source:** `src/greia_installer/i18n_es_fr.py`
   provides **108 Spanish and 108 French string entries**, with
   exactly the same initial key set as existing Italian installer
   copy. `InstallerTranslator` now handles `es` and `fr`
   internally for staging/preview, including dynamic statuses for
   SSID, typed key, pressed counts, battery, pointer and display.
   These languages are **still NOT exposed in the device picker**.
   Updated `tests/test_installer_localization.py` for static
   parity, destructive warning preservation and dynamic-safe
   values. This is a **draft translation**, requiring native
   speaker proofreading, source key audit and rendered installer
   checks; it is not fully reviewed live copy.
   Source: `8c8085cb`, `4d8c565e`, `ed0d6152`.
3. **L1, inventory tooling:** added offline
   `tools/audit_greia_language_coverage.py` with key parity
   source census and per-locale declared speech/file inventory;
   the output deliberately calls out text blockers, missing audio,
   mapping omissions and custom-code voice modules requiring manual
   review. It does not invent a text prompt for an audio file or
   falsely claim to find all dynamic hardcoded speech.
   Added `tests/test_four_language_inventory.py` with fake
   locale trees, unsafe paths, missing catalogue portal recording
   and source-derived vocabulary proof.
   Source: `e332349a`, `2555b874`, `c11b0be0`,
   `028b6a15`, `6e86d8f6`, `46321689`.
4. **Missing existing EN/IT recording uncovered:** the canonical
   `my_creations` portal previously had **no** launcher label
   WAV for Italian or English. Existing
   `tools/audit_launcher_spoken_labels.py` did not require this
   portal. Added platform-owned `MY_CREATIONS_PORTAL_ID` in
   `src/greia_launcher/catalogue_view.py` and included that
   portal in both voice inventory and launcher spoken-label release
   audits. Missing recordings now remain visible as expected
   requirements, even if no seed WAV is present.
   Source: `ae124511`, `27613150`, `c11b0be0`,
   `46321689`.
5. **Local speech work order:** created
   `LOCAL_AGENT_VOICE_PRODUCTION.md` with exact read order,
   clean-checkout commands, four-language semantic cue ledger,
   source gap reconciliation, accepted speaker/voice kinds,
   audio paths, staging/receipts, QA, format/size checks,
   per-clip native listening, acceptance, evidence delivery and
   stop conditions. Explicit known EN/IT gaps:
   `assets/audio/system/launcher-labels/{en,it}/my_creations.wav`
   and My Time's eight semantic lines per existing locale
   (`activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md`).
   Other older Momo/presenter voice claims require fresh source
   reconciliation. Modal is **preferred**, but it is not implemented
   as a Greia VoiceEngine provider yet; running it requires
   integration and separate hosted-budget authorization.
   Source: `c071c7ac`, `63755cdf`.
6. **Documentation:** accepted language product doc now describes
   two selectable baseline languages and gated es/fr staging;
   old twelve-language proposal is marked historical, ADR 0028
   fallback architecture retained. `AGENTS.md` references
   this scoped plan; OS/Activity skills aligned.
   `src/greia_launcher/panel_strings.py` now documents that the
   installed on-device Parent panel remains untranslated
   beyond English despite the current en/it selector.
   Local task `GLA-014` added to the existing queue
   for current-head tests, GUI preview and voice inventory.

### Explicitly NOT complete

- No full repository unit runs, `make verify`, headless/live Pygame,
  GUI screenshots, parent browser acceptance, authentic system
  install, QEMU/physical Acer or ARM tests on these commits.
- No new ES/FR selection in installer, OS panel or Parent API;
  the registry intentionally remains en/it until acceptance.
- No complete OS Shell/Parent HTML/client ES/FR string catalogue
  or complete Activity/encyclopedia `es.json`/`fr.json` sets yet.
- No translation completeness guarantee even for older en/it
  built-in speech/OS messages; these must be audited.
- No Modal provider implementation, voice generation, ASR receipts
  or human listening performed in this session.
- No installation/update/release gate promoted.

### Next exact GitHub engineering slice

1. Execute or obtain local-agent GLA-014 source evidence, resolve
   any focused tests (no manual pretending). The actual local agent
   should first return EN/IT missing audio list and es/fr text gaps.
2. Inventory Shell/Parent/launcher/Activity source for **inline
   English or Italian text** not in semantic locale JSON; start L3
   platform resource ownership with simple typed substitutions.
   Refactor without architecture duplication or per-language
   scene coordinate forks.
3. Implement/test remaining installer source messages and GUI
   length/line wrapping; native-review current 108 draft ES/FR
   entries, including destructive warnings.
4. Extend built-in Activity translations in batches and implement
   current sound/dialogue cue sheets, starting with the known
   missing My Creations, My Time and previous voice gaps.
5. Design a bounded optional authoring-time Modal `VoiceProvider`
   behind the existing Greia VoiceEngine seam; no live cloud calls
   until authorization and source checks. Coordinate output
   integration/QA with the local agent.


## 2026-10-13 — L3 on-device Parent chrome and L4 first six Activity text packs (SOURCE WIP)

**Previous language gate unchanged:** installer/Parent API/on-device
selector shows only EN/IT. ES/FR are still deliberately unavailable in
global language choices while the complete product/voice rollout runs.

### GitHub implementation

- Added `src/greia_launcher/panel_localization.py`, a small
  semantic, no-I/O, four-language message catalogue covering the
  **on-device** Parent password prompt, rejection/unavailability,
  primary title, all eight tab labels, and device language
  selection/confirmation/error. All four locales have identical
  semantic keys and named interpolation parameters; arbitrary
  child names/SSIDs/password values are NOT translated by scanning
  their text. Runtime device locale is resolved through the
  existing `SystemLanguageService`; stage-only test stubs can
  preview ES/FR without exposing them to families.
- `src/greia_launcher/parent_panel.py` now consumes those exact
  semantic IDs and translates these screens at render time.
  `_device_locale` participates in both composite-frame and
  precomposed-chrome cache keys to prevent English UI from
  persisting visually after switching to Italian. The source
  language setting still uses the existing typed Parent helper.
  Auth and language labels are bounded via existing
  `panel_layout.fit_single_line` to avoid low-resolution overflow.
  Added ten provider-free cases in
  `tests/test_panel_localization.py`, including key/placeholder
  parity, exact IT/ES/FR expressions, safe dynamic values,
  switching/invalidation and rejected actions. This is a
  localized *subset* of Parent UI, not the entire panel.
  Source: `06237731`, `a4579e98`, `4f751756`,
  `43b8e394`, `007e69fb`, `8c952587`.
- Installer language-first chooser now lays out the two
  supported options as a centered, suitably sized pair rather
  than preserving the 12-language table's orphaned top row.
  Removed the unsupported "Idioma / Langue" initial-language
  subtitle and used native names for language choices. The
  installed locale/transaction/fail-closed disk safety API is
  unchanged. Source `2b4c78e8`, non-destructive
  source-only until rendered installer acceptance.
- Staged **12 new JSON locale files** at the actual
  `activities/<name>/locales/{es,fr}.json` paths for:
  `painting`, `writing`, `shape_garden`,
  `piccola_serra`, `memory_meraviglie` and
  `clinica_cuccioli`. Each has exactly the existing EN
  semantic string keys with Spanish/French translations,
  preserved interpolation fields and `direction=ltr`.
  Total per new language: **66 localized string entries**
  (6+5+6+13+16+20), 132 new translated string entries.
  These are language-ready **text only**, with empty
  `audio` mappings; source manifests continue to declare only
  en/it. No falsely linked voice paths or premature
  catalogue/installed-language support.
  Source `f8baa8fe`, validated structurally at authoring
  by comparing keys/placeholder sets to EN inputs. Three
  additional provider-free regressions in
  `tests/test_staged_activity_translations.py`
  enforce bundle parity and honest manifest language lists
  (`357e36ca`).
- Added GLA-015 to the ONE local-agent queue with exact
  unittest commands for Parent localization, cache/layout,
  staged Activity texts, current-hardware-sized UI previews
  and missing-voice inventory. ES/FR first-party title WAVs
  for these six Activities remain unrecorded, so their
  semantic `activity.title` entries are concrete items for
  the four-language voice recording ledger.

### Evidence and remaining work

**SOURCE COMMITTED only; UNEXECUTED** `unittest`,
`make verify`, runtime Pygame, human language/text/voice
review, screen captures, Parent HTML pin/release, or
real installed image/hardware acceptance. No Modal
provider calls, recordings or asset changes. Do not
describe the full Parent panel or built-in Activities
as translated on the basis of this first slice.

**Next GitHub slice:** translate remaining Parent settings
forms and Shell notifications into semantic catalogues,
inspect and correct first-party Activity inline text
outside bundles, and stage additional ES/FR Activities
with complete placeholder parity; produce the exact
approved dialogue text/recording ledger before the
local agent is unblocked to produce voices.


## 2026-10-13 — Additional L4 Activity translation staging: seven more built-ins

Added accurate Spanish and French authored text bundles for
`acquario_magico` (16 messages), `torre_forme` (12),
`volo_draghetto` (12), `colline_allegre` (10),
`quattro_stagioni` (12), `corsa_bacche` (11)
and `bottega_delle_misure` (14). That is **87 more translated
message keys per language**, 174 new localized messages in
14 JSON files. These include everyday controls, victory labels,
animal names, seasons and elementary measurement instructions.
The measurement comparison distinguishes *shorter length*
from *lower height* in Spanish and French; native-context review
remains necessary before release.

**L4 tally at this checkpoint:** 13 Activity packages, 26
staged `es/fr` locale JSONs, **153 text keys per new
language** (306 localized key values), all currently
matching existing English/Italian semantic key sets.
`tests/test_staged_activity_translations.py` now covers
the 13-pack roster. `GLA-015` was updated to the latest
source SHA and mandates explicit review of the height-versus-length
distinction. `LOCAL_AGENT_VOICE_PRODUCTION.md` now explicitly
lists **26 new ES/FR spoken title candidate rows** for these
13 Activities, pending authoring approval and human recording.

No `activity.toml` language advertisement or audio mapping
has been added. No runtime source tests, GUI screenshots,
actual sound generation or native-language proofreading
performed. Both translation rounds are **SOURCE WIP**
until the acceptance queue runs. Later L4 stages must still
include all other first-party Activities, the encyclopedia,
custom-code narrated text and platform Shell/Parent forms.
Source `bb0d855c`; expanded test roster `1e75dafe`.


## 2026-10-13 — L3 Parent forms completed to current controller copy; L4 expanded to 27 text-bundled Activities; usable audio ledger

### L3: installed on-device Parent tabs

- `src/greia_launcher/panel_localization.py` gained a reviewed-structure
  translation table for **50 named English source constants** in
  `panel_strings.py`, all with EN/IT/ES/FR:
  microphone recording gain, input meter, presets, processing,
  child account creation, rename, permanent deletion warnings,
  password change/security and service status messages.
  Original `panel_strings` remains the sole English baseline,
  so the translated table cannot silently fork source copy.
  `ParentSettingsOverlay` consumes named localized entries
  at actual text/render/action paths; unrelated profile names,
  credentials, SSIDs and backend diagnostics are preserved.
- Added ~70 other semantic localized labels and statuses for
  pointer speed/toggle/testing, Wi-Fi selection and errors,
  SSH enablement/administration, and browser Parent pairing.
  Stable tab IDs, service/API calls, numeric gain and pointer
  preset values are unchanged. Dynamic IPs, SSH shell
  connection strings and SSIDs are interpolated literally,
  not passed to an English-word replacement function.
- Pointer speed selections formerly rendered both *very slow*
  and *very fast* as the same abbreviated first word. Added
  distinct bounded locale-aware short labels for all five
  speed levels without altering stored semantic values.
  Added measured text fitting for important long titles,
  pointer hints, actions and SSH/Info lines on smaller displays;
  actual screenshots and text-clipping acceptance remain
  pending.
- **Real functional fix found while translating:**
  `_set_pointer_preset` and `_toggle_pointer_setting`
  used to show "success" after the hardware/Parent API
  had reported failure. The second assignment overwrote
  the actual error. Both now rely on the single
  `_apply_hardware_change` authoritative outcome;
  status messages are localized. New provider-free
  tests cover no false success, French feedback, 50
  message parity, pointer options and dynamic network
  field interpolation.
  Commits include `973de157`, `3cd8841e`,
  `21c9b034`, `535b9b8a`, `b6f7843f`,
  `b86c750b`, `ff64ece6`, `06c33682`,
  `192dafe5`. **These changes remain SOURCE ONLY.**

### L4: third Activity staging batch

Fourteen more Activities now have complete *currently bundled
text-key* maps in `locales/es.json` and
`locales/fr.json`: `bosco_numeri`,
`il_giardino_dei_numeri`, `faccine_momo`,
`luci_di_momo`, `costruiamo_ponti`,
`casa_del_dieci`, `workshop_settings`,
`specchi_magici`, `nascondino_bosco`,
`nanna_delle_nuvolette`, `orchestra_animali`,
`treno_numeri`, `quattro_amici`,
`pasticceria_magica`.

- **Third-wave addition:** 14 packages × 2 locale files,
  154 ES + 154 FR messages (308 newly translated text values).
- **Total active L4 stage:** **27 of 45 built-in packages**,
  **54 locale files**, **307 semantic strings per new
  language** (614 translated values), excluding any
  unextracted inline UI text. All newly staged voice
  tables remain empty and each Activity manifest still
  truthfully declares `en,it` only.
- `tests/test_staged_activity_translations.py`
  covers all 27 with key and `{variable}` parity,
  `$num`/`$target` numeric prompt contract and
  explicit Number Train grammar blocker.
  Source `9a8d8520`, tests `2ffa9dfd`.
- Remaining **18** packages need more work:
  `alfabeto_leo`, `baia_delle_orche`,
  `cucciolo_mio`, `enciclopedia_greia`,
  `festa_delle_rime`, `foresta_parole`,
  `la_discesa_della_biglia`, `labirinto_magico`,
  `mondo_contrari`, `morbidi_mostriciattoli`,
  `officina_dei_suoni`, `posta_di_leo`,
  `sillabe_magiche`, `sottomarino_giramondo`,
  `stelle_incantate`, `storie_della_mia_voce`,
  `teatrino_fiabe`, `viaggio_delfino`.
  Alphabet/phonics/rhymes must adapt teaching content,
  not merely translate presentation strings. The
  Encyclopedia and Submarine contain large language-
  dependent voiced datasets and require separate deep
  content/audio reconciliation.

### L1 + L5 voice work order advanced into executable inventory

- `tools/audit_greia_language_coverage.py` now accepts
  `--recording-ledger PATH` alongside its JSON output.
  It creates a deterministic UTF-8 CSV with the precise
  fields demanded by `LOCAL_AGENT_VOICE_PRODUCTION.md`.
  Existing title audio is hashed using the correct
  Activity-local/package path; **file presence NEVER
  counts as human listening acceptance**. Rows remain
  `EXISTING_REVIEW_PENDING`, `MISSING_AUDIO`,
  `BLOCKED_TEXT` or `PATH_REVIEW_REQUIRED` until
  author/providership review. Unsafe source paths are
  never emitted as recording destinations.
- Collection labels' actual four-language text is
  derived from the canonical `catalogue_view.py`
  source AST (no imports/execution), including missing
  `my_creations.wav` for IT/EN and proposed ES/FR
  spoken labels. The generated ledger is **only the
  initial declarative audit**; dynamic/code-loaded
  Activity, Parent, Shell, Encyclopedia and My Time
  voice cues still require human inventory and merging.
  Tests expanded in
  `tests/test_four_language_inventory.py`.
  Source `d79f59dd`, fixes `6ffbb37f`,
  `7897afbf`, `2eb0167a`, `9bdaac9b`,
  tests `0fbc5195`, `90399e1a`.
- The local-agent recording plan now instructs one exact
  source command producing both JSON and CSV, and includes
  **54 ES/FR title candidate recordings for 27 translated
  Activities**, plus real absent EN/IT voice, all other
  bundled/non-bundled narration, and text/pedagogy review.
  The agent must **NOT** feed a raw inventory CSV to the
  VoiceEngine: no speaker/kind/ASR/human provenance yet.

### Evidence and current strict boundary

All work is **GitHub source committed and source-readback
only**. No local complete checkout `unittest`,
`make verify`, rendered GUI, system audio generation,
human listening, native-language proofread, Parent
HTML client deployment, installer build or hardware
testing was run on these source changes. GLA-014 and
GLA-015 specify exact source commands and visual/audio
gap evidence. Missing Spanish/French selection is
intentional until the four-language gate; missing
English/Italian recordings are also not accepted.

**Next:** finish the 18 remaining built-ins,
resolve Number Train singular/plural usage at its
actual prompt construction (not just strings),
audit all inline Shell/Parent messages, and align
separate Parent HTML client localization with its
own pinned build. Extend native reviewed voice
scripts and only then authorize voice production
and real device acceptance.


## 2026-10-13 — L4 fourth wave and science/curriculum separation (SOURCE WIP)

### Current source stage: all 45 built-in Activity folders represented

**Do not read file presence as delivered language support.**
English/Italian remain the only advertised Activity and system
languages. No new Spanish/French WAVs or OGGs have been recorded.

| Source-stage classification | Packages | ES+FR files | Meaning |
| --- | ---: | ---: | --- |
| Full *declared string-key parity* | **39** | 78 | All currently declared English/Italian text keys translated, but still missing audio and possibly inline UI |
| Literacy/phonics interface stage | **5** | 10 | Four have UI-key parity without language-specific lesson adaptation; Word Forest intentionally omits 24 English-specific phonics/word keys |
| Encyclopedia partial stage | **1** | 2 | 51/246 keys in ES and FR, 195 missing per language; audio not copied |
| **Total** | **45** | **90** | Source-stage bundles only, **0 ES/FR Activities promoted** |

Translated staged text values now total approximately **682 per target
language** (1,364 ES+FR text entries). Of these, 583 keys per target
are in the 39 full-key packages, 48 are in the five literacy UI
bundles and 51 are in the partial Encyclopedia bundle.
Actual missing declared strings in these packages: **219 per
new language** (24 Word Forest content words + 195 Encyclopedia).
These counts exclude text hardcoded outside the locale catalogues
and content/voice adaptations, which remain a separate audit.

### Actual added content

- Eleven more *full-key text* packages:
  `baia_delle_orche`, `cucciolo_mio`,
  `la_discesa_della_biglia`, `labirinto_magico`,
  `mondo_contrari`, `morbidi_mostriciattoli`,
  `posta_di_leo`, `stelle_incantate`,
  `storie_della_mia_voce`, `teatrino_fiabe`,
  `viaggio_delfino`. These add **199** translated
  values per new language, including Orca Bay facts,
  Dolphin Journey narration scripts, constellations,
  storage/delete warnings and accessible visual/game controls.
  Source `458d852d`.
- `sottomarino_giramondo`: **77** ES/FR text
  entries each, with nautical left/right orders, 32
  marine facts, multiple legacy voice aliases and
  buttons. The source holds **55 cue mappings per locale**
  and ES/FR `audio` stays empty until recorded,
  speaker-assigned, verified, human listened and integrated.
  Source `3c317b35`; tests `81bd3a10`.
- Five literacy Activities have translated
  ES/FR UI/instructions: `alfabeto_leo`,
  `festa_delle_rime`, `officina_dei_suoni`,
  `sillabe_magiche`, `foresta_parole`.
  Do not claim that Italian/English letters, phoneme mappings,
  rhymes or spelling tasks automatically translate.
  Word Forest intentionally excludes its 24
  `word.*`/`phonics.*` strings, preserving precise
  pending adaptation rather than introducing wrong-target
  pedagogical content. Added **48** UI string values
  per new language. Source `1a730529`.
- Encyclopedia now has the first **51** ES/FR
  keys: activity title, navigation, six animal
  groups, detailed lion/elephant/octopus/bee/penguin/frog
  explanations. **195 keys per locale remain**.
  Source EN/IT declares 200 audio cues per locale;
  none was copied or fabricated in ES/FR.
  The short English topic titles are not approved
  transcripts of the source narration.
  Source `f34ee05f`.
- Dolphin Journey's seven rich narrator/curiosity
  cue IDs in both EN and IT now explicitly declare their
  actual `caption_key` instead of appearing as
  title-less `*.voice` audio in the source/voice
  inventory. This is transcript *association* pending
  human checking, not transcript acceptance.
  Source `8bdffaa1`.

### Quality corrections, testing and voice planning

- Prior Number Train "1 fruit" singular bug was
  *hypothetical*. A source trace of
  `treno_content.py`, `treno_model.py`,
  `treno_app.py` and `treno_renderer.py`
  shows generated counts **at least two**, and
  `prompt.load` is currently not rendered.
  Updated test pins the actual reachable target
  contract rather than pretending a reproduced
  live grammar bug. Count-sensitive phrasing is
  a requirement **only when** the text/speech
  prompt is introduced and one-item cases exist.
- `tests/test_staged_activity_translations.py`
  now explicitly recognizes all 45 built-ins:
  39 full-key, five literacy/UI, one partial
  Encyclopedia, and checks source-key/placeholder
  parity, hidden ES/FR support, curriculum gaps,
  77 Submarine text keys/voice aliases and
  seven Dolphin caption mappings.
- `tools/audit_greia_language_coverage.py`
  now parses `activity.toml` and reports
  `advertised_languages`,
  `advertised_by_manifest`, and stages
  `NO_BUNDLE`, `INCOMPLETE_TEXT_KEYS`
  and `SOURCE_TEXT_KEYS_ONLY` separately.
  The audit cannot mislabel an ES/FR text pack
  as advertised production support.
  Additional tests in `tests/test_four_language_inventory.py`.
- The local-agent recording brief now identifies
  **at least 90 new ES/FR title recording candidates**,
  Submarine's 55 cue owners per locale, Dolphin narrator
  and six curated Encyclopedia chapters, the entire
  remaining source fact/phonics cue backlog, and
  existing EN/IT missing recordings.
  No Modal/provider calls or generation authorized.

### Acceptance status and next code work

**SOURCE COMMITTED via GitHub; UNEXECUTED locally.**
No `unittest` suite, `make verify`, Simulator,
audio provider, child GUI or hardware acceptance
has been executed against the current SHA.
Native-language proofread and scientific/phonics
authoring approval remain necessary for all new text.
GLA-014/015 in the one local-agent task queue now
describe the actual staged boundary and current
CSV/script review requirements.

**Next:** translate the remaining **195 Encyclopedia
keys per target locale**, using science/narration
review by chapter; adapt Word Forest's 24 actual
spelling/phoneme curriculum keys per locale and
similar English/Italian-only learning rules in the
other four literacy packages; reconcile inline
runtime strings and all source audio owner scripts;
integrate the separate Parent HTML client. Only
then proceed to human-reviewed voice and selectable
locale promotion under the accepted plan.


## 2026-10-13 — FINAL source-text checkpoint: 44/45 exact key parity, 90 ES/FR bundles, voices still blocked

**This section supersedes the intermediate 51/246
and 180/246 Encyclopedia statements above.** The
Encyclopedia's Spanish and French text packs now
each contain **all 246** English/Italian source
semantic string keys. Its six animal chapters,
the Sun/planets/Moon, natural Earth systems,
human physiology, machines/flight/bridges and
ancient-history chapters have authored ES/FR
text. Source commits `880848ab` (Space),
`3f271e65` (Earth + Body), and `447c72e9`
(Machines + History). The Spanish and French
Encyclopedia audio maps are **both empty**.
The existing English and Italian source packs
each declare **200 voice cues**; those are
not verified full transcripts of the UI
headings. Native language/scientific copy review,
exact narration transcription and approved
recordings remain blocking.

### Exact current 45-Activity text source classification

- **40 regular packages** (including Submarine and
  Encyclopedia): all source strings present in
  both ES and FR, but new audio missing.
- **Four literacy packages:** all declared UI
  source strings present, but underlying
  syllable/phoneme/rhyme/alphabet lessons
  still require source-language-relative
  curricula, pronunciation and gameplay tests.
- **One Word Forest:** ES and FR have 10
  interface keys; 24 English-dependent
  `word.*`/`phonics.*` keys per locale remain
  intentionally omitted rather than misaligned
  to English-only spelling targets.

**Result:** **44/45 source-key-complete packs**;
**one intentionally partial** pack. **90 Spanish/
French JSONs**, 45 each target language; **877
translated string entries per target locale**,
**1,754 combined**, against 901 EN/IT reference
keys. Exactly **24 explicitly missing declared
text keys per locale** remain, but many more
runtime-inline/voice/curriculum requirements
remain unmeasured. These are source inventory
numbers, **NOT a percentage of accepted product
localization**. All 45 `activity.toml` manifests
and the global device/installer selector
still list only English/Italian.

Updated automated source regressions
(`tests/test_staged_activity_translations.py`)
expect the complete 246-key Encyclopedia,
empty ES/FR voice maps and correct 45-package
classification. Provider-free locale inventory
now reports `SOURCE_TEXT_KEYS_ONLY` versus
`INCOMPLETE_TEXT_KEYS` and separately reads
manifest-advertised locales. GLA-014/015 and
`LOCAL_AGENT_VOICE_PRODUCTION.md` now route
the local agent through exact source verification,
script provenance and human/content review
before any approved speech production.

**Unexecuted:** unit tests, `make verify`,
Pygame GUI/fit screenshots, native speaker
proofreading, spoken recording/listening,
Parent browser app localization/release pin,
installer build or Acer/Pi installed-device
acceptance. These remain planned checks;
source readback/commit is not their substitute.

**Next engineering:** adapt Word Forest and
other literacy teaching datasets to ES/FR,
reconcile the **200 Encyclopedia audio cue
IDs per source locale** to exact source
narration scripts and review all language-specific
facts, complete Submarine/other Activity
action/character speech, then finish Shell/
Parent-browser UI and run actual tests.
Never add ES/FR to the canonical registry
until the full L6 acceptance gate passes.


### 2026-10-13 — Contributor skill identity incident detected and repaired

A previous GitHub-only file-update loop selected the wrong
string variable and accidentally wrote the entire
`greia-os-work` skill into the `greia-activity-authoring`
path, and the entire Activity skill into the OS path.
The mismatch was **not** a desired architecture change.
We detected it by comparing frontmatter names with
the requested paths, restored both full skill contents
atomically to the correct canonical paths at
`4957bc96` and verified the frontmatter through
GitHub readback. Added
`tests/test_greia_skill_identity.py`
at `b1d2e14b` (three tests) to fail whenever
the two skill-path/name/content contracts diverge;
GLA-015 includes this focused source gate.
No test execution was claimed.

This skill incident does not alter or close the
remaining locale content/voice gates. Explicitly
preserve the existing EN/IT support restriction.


### 2026-10-13 — GitHub readback structural audit (EXECUTED on source blobs, not Python runtime)

Performed eight readback batches directly against GitHub
`main` covering **all 45 built-in Activities × both
staged target locales = 90 translated JSON files**.
For each package, compared ES/FR semantic string keys
against current `locales/en.json`, required complete
key equality except the **24 deliberately omitted**
`word.*`/`phonics.*` keys in Word Forest,
checked named `{variable}` and `$name`
template-token parity, and verified each new ES/FR
`audio` dictionary is empty. Combined output:
**1,754 translated string entries inspected, zero
schema-key/placeholder/audio-mapping discrepancies**.
This is source-content structural evidence only;
it does not validate factual accuracy, native
grammar, authentic spoken scripts, game action
semantics, Pygame rendering, performance, or
shipping release eligibility.

After detecting swapped OS/Activity skill file
contents, restored the files to their canonical
locations and verified both `name:` frontmatter
values through GitHub readback. Three additional
local source tests were added to prevent recurrence,
but those Python tests still await the local
agent's actual execution.


### 2026-10-13 — Word Forest real ES/FR candidate lessons and code-owned recording inventory

**Supersedes the earlier 44/45, 877/901 and 24 omitted
keys as the current source checkpoint.** GitHub source
now contains **45/45 full EN/IT-declared text-key
parity** in ES and FR: **901 strings per locale,
1,802 ES+FR strings combined**, no new Activity
`audio` mappings and no ES/FR manifest promotion.

Actual new implementation:
- `activities/foresta_parole/foresta_content.py`:
  **21 Spanish + 21 French** language-relative
  letter/example-word lesson tuples, reusing the existing
  six-field domain vocabulary contract; no English words
  substituted as phonics examples. The existing EN/IT
  catalogues and all model/renderer semantics remain.
- The two Word Forest locale JSONs now have the
  **24 previously missing** `word.*` and `phonics.*`
  translations each, all semantic keys and named
  placeholders source-parity checked by GitHub readback.
  These are authored candidates requiring native
  phonological and pedagogical proofread.
- `foresta_app.SoundManager` discovers code-owned
  lesson banks by `PHONICS_DATA` locale, with no
  synthetic language speech or manifest exposure.
  The only selectable Word Forest locales remain IT/EN.
- `tools/audit_greia_language_coverage.py` now
  parses `PHONICS_DATA` as a source-only AST literal,
  without importing or executing Activity code.
  The CSV inventory adds **252 lesson audio cue
  candidates** (20 IT, 22 EN, 21 ES, 21 FR ×
  letter + prompt + example word). **126 ES/FR
  clips are new/unrecorded**. A spoken word's
  text can be inferred from its approved-candidate
  printed example; whether the letter cue is a name
  or phoneme and the exact find-letter prompt
  **cannot** be inferred: marked `BLOCKED_TEXT`
  until real reviewed scripts are authored.
- `alfabeto_leo/alfabeto_audio.py` no longer falls
  back to Italian when a locale's phonics WAVs
  are missing. `alfabeto_model.LetterItem` now
  also rejects unknown curriculum languages
  instead of silently returning English words
  and symbols. Both are fail-closed source
  corrections; authentic ES/FR alphabet lesson
  examples/voices are not yet authored.
- Provider-free tests added/extended:
  `tests/test_word_forest_phonics_inventory.py`
  (source AST non-execution, cue counts, no fake
  ES/FR speech); `tests/test_staged_activity_translations.py`
  (real initial-letter, word-audio stem, and
  45/45 key equality); `tests/test_activity_alfabeto_leo.py`
  (no missing-locale audio fallback). GLA-014/015
  source commands/pins and voice brief updated.

**Evidence:** Finished eight GitHub source-readback
batches for all 90 ES/FR Activity JSONs and a
post-edit two-file Word Forest parity readback.
Zero structural key/placeholder/audio-map
mismatches were observed; 45/45 total is now
source-key complete. These are **not Pygame/UI,
native linguistic, classroom, ASR, human voice,
source `unittest` or hardware execution tests**;
those remain UNEXECUTED and belong to GLA-014/015.
Four other literacy lesson engines, Encyclopedia
narration, Submarine, Parent HTML and all
missing EN/IT title WAVs remain OPEN.


### 2026-10-13 — Staged phonics curricula for Rhyme Festival and Sound Workshop (SOURCE-WIP)

Two further literacy engines now have genuinely locale-relative candidate
curricula rather than a translated UI surrounding Italian content:

- `festa_delle_rime/rhyme_content.py`: 8 Spanish and 8 French rhyme pairs,
  plus 6 native-language alliteration families for each target locale.
  The rhyme-generation algorithm is unchanged; only the corpus is new.
- `officina_dei_suoni/sound_content.py`: 8 target phoneme/grapheme
  groups per language, each with 3 real first-sound picture words (24 per
  locale). Source word IDs are audio stems; visible labels retain
  French/Spanish orthography (e.g. FÉE / BÉBÉ / LÁPIZ).
- Both `get_corpus` and `get_sound_units` resolve regional locale
  tags by base language, preserve EN/IT data, and raise for any
  unsupported curriculum instead of silently returning Italian.
  This fixes a latent wrong-language teaching trap at the owner seam.
- Added focused pure-source regression
  `tests/test_staged_es_fr_literacy_curricula.py` for lesson counts,
  referential phoneme invariants, deterministic playable challenge
  factories, fallback rejection and **no ES/FR manifest promotion**.

**Not accepted for children:** the ES/FR vocabulary, pictures and rhyme/
phoneme acoustics are authoring candidates, not native-speaker-reviewed
lesson audio. Neither Activity's `activity.toml` changes from EN/IT.
New word and phoneme audio remains missing, including existing EN/IT
coverage gaps. Cue IDs are owned by the respective corpus (`item_id`,
`audio_id` and `word_id`), and must be reconciled to exact scripts
before Modal generation. Do not use an ASCII filename as the spoken
accented script. The exact word inventory is now in source, not an
approved voice manifest. No tests, listening, GUI or device runtime
executed in this GitHub-only implementation slice; focused tests are
written and awaiting local execution as already queued under GLA-015.
Next curricula: Alphabet Leo (Spanish Ñ and French example/letter
phonetics) and Magic Syllables (locale-true segmented words).


### 2026-10-13 — Code-owned bilingual-literacy voice ledger expansion (SOURCE-WIP)

The four-language source inventory now **reads the actual staged
`RHYME_PAIRS_*`/`ALLITERATION_FAMILIES_*` and `SOUND_UNITS_*` data
as a narrowly whitelisted Python AST**, without importing Activity
code or evaluating arbitrary expressions. One recording cue is emitted
for each distinct word or sound used by Rhyme Festival and Sound
Workshop, using their real runtime file stem and locale path.

Current ES/FR candidates: **31 + 29** Rhyme Festival (including
`prompt_odd` in each locale) and **32 + 32** Sound Workshop
(8 isolated sound phonemes + 24 full words in each locale), totaling
**124 Spanish/French code-owned recording candidates**. Existing
IT/EN recordings are inventoried through the same source path and
remain subject to the ledger's review states.

The rhyme `item_id` is not a safe written pronunciation script
(e.g. words with accents); every rhyme word and the odd-one-out cue
remains `BLOCKED_TEXT` until source captions/scripts are approved.
Isolated Sound Workshop phonemes also remain `BLOCKED_TEXT`,
while written `WordItem.label` is preserved as the word-cue
candidate, with accented `fée`, `bébé`, `lápiz` properly retained.
No automatic recording, native review, human listening, or Activity
language promotion. Added focused AST nonexecution, expected counts,
voice-path and blocked-text test coverage to
`tests/test_staged_es_fr_literacy_curricula.py`. The tests have been
authored but not yet executed in a local checkout.


### 2026-10-13 — Alphabet Leo and Magic Syllables multilingual candidate curricula; real code-audio census (SOURCE-WIP)

**Four of five literacy Activities now have candidate ES/FR domain
content** (Word Forest, Rhyme Festival, Sound Workshop, Alphabet Leo,
Magic Syllables = five total; all five have staged ES/FR content).
This statement covers source candidates only, NOT finished pedagogical
curricula: e.g. Magic Syllables' explorer/catcher still use a legacy
Italian-derived consonant × vowel teaching grid, and alphabet H / French
grapheme behavior need native phonological assessment.

**Magic Syllables:**
- Added 16 real candidate two-written-syllable words in Spanish,
  16 in French, with exact per-locale picture glyphs, syllable
  boundaries and ASCII recording stems preserving accented display
  words. The staged French data includes e.g. `VÉ-LO`, `BÉ-BÉ`,
  `CHA-PEAU`, `GÂ-TEAU`; *actual spoken syllable divisions
  require specialist approval*.
- Pure `SyllableCurriculum` and `get_syllable_curriculum(locale)`
  now own word corpus, consonant/vowel inventory, 3 mode titles,
  consonant header and praise IDs. App palette hit-testing, drawing,
  displayed mode titles, domain setup and audio praise dispatcher use
  the resolver. Rejects unsupported languages rather than silently
  displaying English words and Italian labels. EN/IT source arrays
  and praise IDs retained.
- `test_staged_syllable_curricula.py` added for word segmentation,
  app domain model progression, unsupported locales, existing IT/EN
  parity and nonpromotion.

**Alphabet Leo:**
- Kept original 26 EN/IT `LetterItem` records unchanged, staged
  26 ES and 26 FR native-language written example words and pictures,
  and added **Ñ as a real 27th Spanish alphabet letter**, correctly
  placed between N and O. All navigation, guessing, discovery/parade,
  strip rendering, shared tone inventory and SDL TEXTINPUT path
  use the locale-relative alphabet. A child's saved discovered letters
  are filtered against the currently selected curriculum.
- Existing-only unsupported `word_for()` errors now allow staged
  ES/FR source data; unknown target languages and attempts to use Ñ
  under EN/IT still fail closed. Crucially, this does not teach
  Spanish H as a spoken /h/; whether to play letter NAME or phoneme
  must be pedagogically and acoustically reviewed.
- `test_staged_alphabet_curricula.py` covers ES 27-letter
  navigation, FR accents, two-language manifests, new saved
  progress semantics, and exact new code-owned voice cue counts.
  The old `test_activity_alfabeto_leo.py` unsupported-locale
  check was updated to assert only actually unsupported tags.

**Real source-owned recording census (no code execution/import):**
- `tools/audit_greia_language_coverage.py` now reads literal
  syllable and alphabet source data via AST, accounts for source
  runtime playback (not only locale JSON `audio` bindings), and
  exposes required *ES/FR* candidates as:
    - Alphabet Leo: **58 ES**, **56 FR** (two spoken cues per alphabet
      letter plus 4 shared prompts; including `letter_Ñ` and
      `ask_Ñ`).
    - Magic Syllables: **173 ES**, **190 FR** (letter, generated
      CV syllable, find-syllable, word-builder, praise and all 17
      additional French written-syllable audio stems).
    - Combined **477 ES+FR source-owned voice candidates** in
      these two Activities, additive to the previously inventoried
      124 from Rhyme/Sound and 126 from Word Forest.
  Read-only sources are safely parsed and never evaluated.
  The words retain accent-bearing candidate written scripts;
  the pronounced phoneme, instruction, letter-name, and praise
  scripts remain `BLOCKED_TEXT`. Existing EN/IT cues are also
  inventoried as gaps/review targets, not automatically accepted.
- Two new test modules now cover literal-inventory counts, refusal
  to execute malicious catalogue expressions, cue uniqueness/path
  reconciliation and no unsupported-locale manifest promotion.

**Evidence boundary:** all source committed on GitHub `main`,
with exact blob/head readbacks where noted. Python tests,
`make verify`, Pygame, native curriculum review, actual audio
generation/listening, device provisioning and 4-language release
promotion have **NOT RUN**. Spanish/French remain neither
manifest-selectable in these Activities nor globally selectable.
GLA-015 was extended in the sole local-agent task queue with
current source test commands. Next work: deeper native phonemic
datasets (especially French explorer/catcher), authentic scripts,
remaining Parent HTML and Shell text and on-device acceptance;
no release gate is being closed.


### 2026-10-13 — Corrected locale-native Magic Syllables generation + Parent HTML browser integration (SOURCE-WIP)

**Corrections to the preceding audio totals:** The previous source
staged ES/FR written words, but the actual explorer/catcher and
word-builder still generated too many Italian-derived C+V syllables.
Those were *not reviewed native-language teaching units*. GitHub
commits `5a53c016` and `07a70031` replace the ES/FR
algorithmic generator with curated `_FAMILIES_ES` (8 groups,
40 voiced candidate syllables) and `_FAMILIES_FR` (5 groups,
25 syllables, including accents such as `MÉ`). The actual
`SillabeSession` now uses these explicit lists for explorer,
catcher targets/distractors and builder distractors; EN/IT retain
their previous generation path. Source regression covers
family validation, playable round counts, correct/duplicate
targets, no nonexistent grapheme combinations, and recorded
syllable stem selection. This remains **pending native phonetic
and teacher review**, not verified spoken French/Spanish.

The AST-only `tools/audit_greia_language_coverage.py`
now inventories the actual ES/FR authored source families
rather than the old 14×5 grid. **New current source audio
requirements for Magic Syllables: 115 ES and 93 FR,
208 combined**; builder-only syllables are inventoried as
`syl_*`, but not as nonexistent `find_*` prompts.
This supersedes the prior 173 ES / 190 FR / 363 combined.
The corrected aggregate of staged ES/FR *code-owned
literacy* cue candidates in the five Activities is now
**572**, not 727: Word Forest 126, Rhyme Festival +
Sound Workshop 124, Alphabet Leo 114, Magic Syllables 208.
These are source-reported requirements and not recordings.
All ambiguous letter/phoneme/prompt scripts remain BLOCKED_TEXT.

**External Parents browser source:**
`frozenpepper/Greia-Parent-App-Html` main has advanced through
source commits `957bb847`, `f95cc5a6`, `32c0b552`,
`8b456728`, `b5abee3b`, and `a6df96c2`.
It now has a first-party `src/localization.js` staged catalogue
with **61 semantic text keys in each of EN/IT/ES/FR**, and
source integration for primary navigation, browser chrome,
confirmation buttons, system-status labels, language-settings
card, device grouping, Wi-Fi unavailable copy and speaker
controls. The current parent app uses the device's actual
`snapshot.language.locale` for authenticated browser
chrome and the browser's supported preferred language
preauthentication; the **API's language list** still
owns which device languages are selectable. No duplicate
browser-side device registry, network access or HTML
injection was added. Targeted Node source tests
and existing static source expectations were updated.

**Not a pinned or releasable Parent browser:** many Home,
Children, Activities, discovery/authentication and device
detail strings remain English; full locale parity, visual
legibility and native copy review are absent. The Greia OS
`runtime/parent-app-client.toml` and byte-integrity
manifest are intentionally **UNCHANGED**. Until the external
client's entire source is localized, `npm test` and real
browser/app acceptance pass, and the established release
pin procedure republishes exact checked bytes, the
installed OS has no claim to these new HTML strings.

All work here is GitHub source-only. Executed evidence:
GitHub branch/blob readbacks of changed source.
No Python/Node suites, Pygame/DOM rendering, child tests,
voices, physical Greia installs or hardware acceptance
were run. Task queue GLA-015 tracks future source/GUI
checks; do not ask a device agent to do paid voice work
without exact approved scripts.


### 2026-10-13 — External Parents browser discovery/authentication text integration

After the initial 61-key browser chrome slice, the separately
owned `frozenpepper/Greia-Parent-App-Html` repository advanced:
- `3b0003cf` adds 39 additional semantic EN/IT/ES/FR copy
  messages for discovery, connecting, chooser, retry/errors,
  loading and password authentication.
- `ed4ac5d9` integrates those messages into the actual
  Parent first-run/connection/authentication paths, preserving
  existing Parent API password pairing, device-scoped
  credentials, and safe `textContent` rendering.
- `ec0bf413` updates the separate repository's handover
  and developer README.

The external first-party source now contains **100 distinct
EN/IT/ES/FR staged browser message IDs** (100×4 translations),
superseding the preceding 61-key checkpoint. The device
language chooser STILL uses the API's live
`snapshot.language.languages`, never those message IDs.
All four source translation sets are authored but not
human-reviewed. This is not full browser UI coverage:
Home/Children/Activities and deeper device forms remain
English; live normal login/discovery, browser layout,
Node tests and production file-integrity sealing are
**not executed**. No change to Greia OS's installed Parent
client pin. No ES/FR device promotion.


### 2026-10-13 — Parent browser Home/Children/Activities four-language source integration

The separate `frozenpepper/Greia-Parent-App-Html` repository
advanced to `11f43f63f51cda5da260d26488435615f67289ae`
on its `main` branch (source only).
The Parents browser now has **272 semantic UI text keys in each
of EN/IT/ES/FR**, superseding the 100-key partial checkpoint.
Real UI integration now includes:
- Home selected-child overview, recent sessions, status,
  star/usage metrics and device management navigation;
- Children list, age/style/challenge badges, individual/shared
  daily Activity-time editing, profile creation/modification,
  secure password fields and deletion confirmation;
- Activities search/categories, policy age/difficulty
  controls, visibility overrides, installation/removal,
  child data preservation text and feedback.

Common time/age/category/challenge formatters were converted
to the same locale service rather than duplicating per-view
localized logic. Dynamic profile names and API-provided text
continue to render only as plain text.

**Verification actually performed in the GitHub-authoring
environment:** exact HEAD and blob readback; in-session
V8 JavaScript syntax compilation of all **13** `src/*.js`
browser source modules (all pass after repairing a missing
parenthesis in the first Activity removal edit); pure
translation smoke evaluation in each locale; static
identification of **246 distinct referenced semantic keys**
with zero missing IDs and matching four-language placeholder
sets. No `innerHTML` in the 13 inspected client source
modules. Source tests now include
`tests/localization_source_contract.test.js`, whose
`npm test` run will independently check `node --check`
for every JS module, literal translation references,
and API call boundaries.

**Not executed:** actual Node `npm test`, real browser
rendering/layout, device discovery/password interaction,
native linguistic review, installed image, physical hardware.
Deep Device management forms and some dynamic/API errors
remain untranslated. These changes have **not been shipped**
into Greia OS's pinned/verified Parent client; the OS pin and
runtime integrity manifest are deliberately unchanged.
ES/FR still must NOT become selectable system languages or
Activity languages. Continue translating real UI owners,
then run normal source/browser tests and repin only after
the accepted exact-byte integration procedure.


### 2026-10-13 — Complete first-pass deep Parent HTML Device UI text integration and audited distance-to-text-completion (SOURCE-WIP)

External browser source owner `frozenpepper/Greia-Parent-App-Html`
advanced to `db14662dbdf6879b6883ab5172dfb3869821e44b`
on `main`. Actual Device management controls now use
EN/IT/ES/FR semantic translations for Wi-Fi network connection,
input/display/microphone processing, Parent password,
SSH maintenance, paired devices, OS update upload/status, and
accessibility/initial HTML. The Parent source catalogue has
**373 distinct message IDs**, each with all four language
values and matching variable-placeholder sets. The menu
model's unused English copies were removed.

**Source verification actually performed:** all 13 browser
`src/*.js` files pass in-session JavaScript syntax parsing
(no Node `npm test` yet); static key-reference audit,
including `index.html`, found **357 distinct literal
referenced IDs, zero missing entries, zero interpolation
mismatches**, and zero occurrences of `innerHTML` in those
13 source modules. The semantic device API/capability
and existing operating language constraints were unchanged.
A focused deep Device messages source test was committed
but is unexecuted under Node. The installed Greia Parent
client remains at its previous pinned exact-byte version;
the new external source is NOT shipped or promoted.

**Measured text authoring facts rather than a fake global
percentage:**
- Installer has **108 identical reference keys** in current
  IT, ES and FR maps, with English as source/fallback.
  Actual rendering/translated warning review is unaccepted.
- **45/45 built-in Activities** have EN/IT/ES/FR JSON text
  bundles with the pre-existing reference-key parity audit.
  That audit explicitly does NOT prove absence of inline
  strings or complete educational/encyclopedia content.
  Five language-learning Activities have native ES/FR
  candidate curricula, not teacher-approved linguistic facts.
- External Parent HTML now has **373/373 complete locale
  entries per language**, with source wiring for main UI
  views and Device controls. Server-returned dynamic
  error strings are separate OS/API localization work.
- On-device Parent is further along than old comments
  suggest: `src/greia_launcher/panel_localization.py`
  already owns four-language semantic strings and named
  form translations. A discovered set of **three invalid
  `//` comments** in this Python file was repaired to
  `#` at Greia commit `68434184`; the complete Python
  suite has not been run to prove runtime import.
- Shell/creations/launcher inline text, user-visible
  generated strings and encyclopedia knowledge text still
  require an exhaustive extraction-and-use audit. Merely
  counting text keys cannot provide a defensible global
  100%-completion percentage.

**Outstanding *text-only* completion work:**
1. Enumerate and remove the residual unowned runtime
   English/Italian literals in Shell/Creations/launcher,
   Activity mechanics and Parent API error paths; prove
   every visible copy owner resolves EN/IT/ES/FR.
2. Audit content completeness/accuracy: encyclopedia facts,
   language-learning phonemes/segmentation/grammar, nouns,
   plurals and child-facing labels in ALL 45 Activities.
3. Run source checks (including the Python import after
   the corrected panel source), full `npm test`, real
   translated UI screenshots at target viewports, and
   native EN/IT/ES/FR editorial proofread.
4. After complete accepted browser source, execute the
   separate existing Parent client content-pin and hash
   integration. System ES/FR language selection still
   remains disabled by intentional L6 policy, independently
   of text staging. Voice/recording work remains a separate
   non-text release blocker.

No images were built, no hardware was operated, no audio was
generated and neither Python nor Node full suites ran in this
GitHub-only source continuation. The earlier source key
counts must not be used as a claim of shipped translation.


### 2026-10-13 — Runtime Shell launch copy and Word Forest foreign-language fallback repair (SOURCE-WIP)

After the staged four-language structured-bundle census, the next
actual runtime text audit found two independent user-visible
language leaks, now repaired on Greia `main`:

1. `9297e8a7`: The child's actual full-screen Activity
   launch overlay rendered English `Starting…` and `Please wait…`
   regardless of profile language; the smaller launch tile
   badge supported only Italian and English. A tiny pure
   `src/greia_launcher/launch_feedback.py` now owns
   typed EN/IT/ES/FR `overlay`, `badge` and `wait` phrases.
   The pre-READY and repeated launch overlay, subtitle and
   small Activity badge all consume the effective
   already-selected Shell/profile UI locale. Unknown historic
   locales use the existing safe English text fallback. No
   Shell/Activity locale registry, launch timing, protected
   overlay, Pygame geometry or speech backend was changed.
   Focused pure `tests/test_launcher_launch_feedback_localization.py`
   was authored for four locales, region tags, and fallback.
2. `ba7f87e7`: Word Forest's correct-letter and finished-word
   messages used literal *Italian* compliments if its
   `LocalizedResources` lookup was unavailable or failed,
   even under an English profile or staged ES/FR curricula.
   Normal success paths still use
   `feedback.correct`/`feedback.word_complete` from the
   relevant locale JSON bundle. The degraded-display
   fallback is now the language-neutral visual `✨`/`🌟`,
   with NO Italian sentence and no silent cross-language
   instructional speech. `tests/test_word_forest_phonics_inventory.py`
   now checks that the runtime source lacks the old Italian
   fallbacks and the four actual bundles own those messages.

**Evidence boundary:** GitHub content, exact anchored replacements
and branch/commit writes only. Neither new focused test nor the
cumulative Python suite nor real visual/sound/hardware acceptance
was executed. A wider batch attempt to inspect all Activity
`*_app.py`/`*_renderer.py` files was stopped by the
GitHub connector's per-execution call limit and yielded
**no usable coverage evidence**. Do not treat 45/45
bundle-key parity as proof of zero inline literals.
The rest of the Shell/Activities/Creations/encyclopedia
audit and four-language human review remains OPEN.

**Next:** use bounded GitHub file batches grouped by
Activity family, record actual render-site ownership,
fix text leaks with shared runtime localization, run
`python3 -m unittest discover -s tests
-p 'test_launcher_launch_feedback_localization.py' -v`
and `python3 -m unittest discover -s tests
-p 'test_word_forest_phonics_inventory.py' -v`
in the existing local-source testing task, then visually
check the actual overlay at a real profile locale after
source tests pass. This is source-only; it does not
authorize ES/FR manifests, language selector promotion,
recording synthesis, or installed-device changes.


### 2026-10-13 — Bounded Activity render-path audit: Painting save status four-language fix (SOURCE-WIP)

A bounded source read of ten Activity app/renderer/content modules
identified a third visible language leak (after Shell launch and
Word Forest praise). Painting had three **Italian** status
literals `Salvo`, `Salva...`, `Errore` outside
all four locale bundles; prior 45/45 bundle-key parity
was not sufficient proof of runtime UI completeness.

**Source correction `5a4b33bd`:**
- Added `status.saved`, `status.saving`,
  `status.error` to each EN/IT/ES/FR Painting bundle.
- Painting's actual Activity owner resolves effective profile
  UI locale through `ActivityLocaleSupport`,
  `resolve_activity_locale` and `LocalizedResources`,
  still advertising only EN/IT. Renderer receives text
  once at construction and caches by semantic save-state
  IDs. A standalone renderer without language context
  uses neutral symbols `✓`/`…`/`!`, never Italian
  text under another locale.
- Pill width now measures cached labels instead of
  assuming the width of the old short Italian strings.
- `tests/test_painting_contract.py` checks that legacy
  literals are absent and all four bundles own the
  new keys.

**Evidence:** GitHub anchored edits/commits only. Python
tests, screenshots, font/accent rendering and installed
device have NOT run. Measured text width still needs
visual acceptance. The ten-file Activity source sample
does not exhaust all 45 built-ins; broader code-level
runtime-inline text work remains OPEN. The attempted
large-batch source sweep was aborted by GitHub call
budget without actionable output and is not counted.

Next focused source test:
`python3 -m unittest discover -s tests
-p 'test_painting_contract.py' -v`.
No audio/manifest/language registry promotion.


### 2026-10-13 — Live Activity text audit: Magical Labyrinth and Wonder Match (SOURCE-WIP)

**Scope:** continued L1/L4 render-path audit on canonical Greia `main`, after the previously documented Painting/Word Forest/Shell corrections. Actual runtime display branches—not only JSON file inventories—were inspected. The other 43 Activity runtime paths, encyclopedia educational accuracy and Shell/Creations remain open.

**Labyrinth:** The UI previously ignored its locale bundles for the visible difficulty, biome and “new maze” HUD controls, and showed hardcoded Italian completion copy. `activities/labirinto_magico/maze_app.py` now resolves its effective Greia Activity locale using the existing `ActivityLocaleSupport` and `LocalizedResources`; `maze_renderer.py` consumes a typed `MazeHudLabels` value and preserves neutral labels for independent renderer use. The four locale JSON bundles gained the six actual model difficulty labels, four real biome IDs and a short new-maze caption (11 additional keys per locale). Completion title, message and replay now use pre-existing translated semantic keys. Labels are resolved when selection changes, not in each drawing loop. No maze generation, inputs, activity profile policy, media or layout geometry changed.

**Wonder Match:** `activities/memory_meraviglie/memory_app.py` previously rendered card and theme names via a two-branch IT/EN lookup, meaning staged ES/FR would silently inherit English gameplay vocabulary even though the four locale bundles passed a structural inventory. Live rendering now resolves `item.<id>` for all **64 actual matching illustrations** and `theme.<id>` for all four categories using the existing Activity `LocalizedResources`; all four source bundles received complete card-word translations (64 × 4 = 256 entries). Only neutral visual symbols are used if language resources are not available. The old model labels remain as compatibility data, not displayed copy. Card rules and gameplay state were untouched.

**Regression/evidence:** Added `tests/test_four_language_activity_runtime_text.py` (four provider-free tests) validating actual modeled IDs, every four-language semantic key and use of the runtime semantic display path. A connector-only readback/static cross-check verified 6 difficulty IDs, 4 biome IDs, 64 card IDs and 4 theme IDs in each language with **zero missing keys** and inspected the updated source display call sites. **No Python test executed, no Pygame launch/screenshots, no voice synthesis/listening, no Parent browser build, no image or hardware acceptance.** Current `main` source/test anchor before documentation: `02213ed37e9d8e8b0318902a908225ef5b1d2cff`.

**Hard boundary:** Both Activities still declare EN/IT as effective supported languages; ES/FR JSON is staged authoring data. No change to `SUPPORTED_SYSTEM_LANGUAGES`, manifests, Parent client integrity pin or release gates. ES/FR may not yet be selected. Add the focused test and 1024×600 / 800×480 visual review to the existing local-agent GLA-015, not a new testing workflow. Continue bounded inspections of actual Activity and Shell/Creations display paths, educational meaning and pronunciation; don't infer global localization completeness from four-file parity.


### 2026-10-13 — Follow-up: language-neutral completion fallbacks in Train and Wonder Match (SOURCE-WIP)

A neighbouring source-only render-path check confirmed that Number Train and Wonder Match had fully localized normal completion strings but **Italian-only default values in the rare missing/broken resources path**. Commits `54fb09174be94d32b82ee17066a01fc4adc26a3a` and `6f8e59d5462df0bb57486e85921af5bed4c1b7c8` replace those Italian fallback sentences/buttons with concise language-neutral visual symbols. The normal semantic `victory.*` and `btn.play_again` bundles remain the primary path and were not changed. One more provider-free regression was added to `test_four_language_activity_runtime_text.py` (now five tests), commit `7bd94b329f4649535fc9a85026b856dc19151181`. These are Github source read/edit observations, not Python execution or rendered evidence; investigate visually whether the tiny emergency fallback feels sufficient and ensure recordings do not cross locales. The current external Parent app pin, ES/FR selectable policy and release gates remain unchanged.


### 2026-10-13 — Actual instruction/toolbar text and silent localization API repair (SOURCE-WIP)

**Continued L1/L4 current-runtime audit, not a language-promotion gate.** After fixing the Maze and Wonder Match user-visible labels, the next bounded five-Activity source review found that `activities/sillabe_magiche/sillabe_app.py` was still presenting fixed Italian instructions in real English play despite staged four-language JSON files. The Magic Syllables explorer heading, tile instruction, catcher prompt and both word-builder slot hints now resolve five new semantic keys via the existing `LocalizedResources.text()` (all four EN/IT/ES/FR files updated). The explorer header uses `SillabeSession.explorer_syllables()` for **the actual current lesson family**, so staged French `MÉ` is displayed truthfully; it refreshes on a consonant change, not per frame. No curriculum or audio recognition/recording was approved or changed; ES/FR literacy remains staged and pedagogically unaccepted.

**Little Greenhouse real runtime leak:** `serra_content.TOOL_DEFS` contained four Italian display labels `SEME`, `ACQUA`, `SOLE`, `RACCOLTA` independently of already-complete `tool.*` JSON translations. It now stores semantic keys only; the app resolves those labels at construction from `tool.seeds/water/sun/harvest`, the renderer receives them without its own locale logic, and an isolated renderer has neutral icon defaults. No gardening rules, key inputs, storage or pixel positions changed. The Greenhouse's three Italian completion default strings were also replaced with neutral emergency symbols; normal localized content still comes from the existing keys.

**Critical API defect / correction to previous source interpretation:** Inspecting the actual platform class revealed that `src/greia_platform/localization.py` defines `LocalizedResources.text(key, variables=None)` and **does not implement `LocalizedResources.string()`**. The Wonder Match `_localized` helper, Number Train's `t` helper, and Greenhouse's `t` helper called that nonexistent method inside exception-catching paths. Consequently their supposed localized victory copy was **not being displayed even in normal EN/IT execution**; previously reported language-neutral victory fallbacks would have been shown instead. The three owners now correctly call `.text(key)` so their normal localized strings are resolved and honor the child text-case policy. This is a correction of an actual integration defect, not merely missing translation coverage.

**Code and evidence:** `tests/test_four_language_activity_runtime_text.py` now contains eight focused provider-free tests, including String.Template dynamic formatting, all real current locale keys, original Italian literal absence, semantic greenhouse tool keys, and consistency with the actual platform `.text()` API. Updated both existing authoring/OS skills with the correct API and UI/lesson separation. GitHub readback confirmed all five new Syllables keys in four languages, Greenhouse tool keys in four languages, no known `.string()` invocation in the three corrected owners, and eight source test definitions. **No Python test runner, local renderer, English/Italian live play, ES/FR staged injection, audio listening, installed OS or hardware ran.** Last source/skill commit before documentation: `5c5e84a40002ba62adea37c1cdb589c5313f2481`.

**Immediate follow-up:** GLA-015 must run `python3 -m unittest discover -s tests -p 'test_four_language_activity_runtime_text.py' -v`, existing `test_staged_activity_translations.py`, `test_staged_syllable_curricula.py`, `test_activity_piccola_serra.py`, and relevant activity/runtime suites; test actual normal EN/IT instructions, time to first frame, Greenhouse toolbar and victory screens at 1024×600 and 800×480. ES/FR may only be viewed by staged test injection; neither system selector, manifests nor voice packs may be promoted. Continue remaining Activity, Shell, Creations, phonics and encyclopedia render-source audit. Historical aggregate 901-key counts in older queue entries are **snapshot counts**, not the new current full-audit total after authored UI/card keys.


### 2026-10-13 — Opposites World state/toolbar text and Dolphin completion fallback (SOURCE-WIP)

**Actual text render-path audit:** `activities/mondo_contrari` bundles already included 10 opposite concept words for each EN/IT/ES/FR locale but the five scene render functions **hardcoded all ten state banners in Italian**, and `ContrariRenderer._render_toolbar` selected only between two embedded dictionaries (IT vs EN). This was an existing English runtime defect and a future ES/FR release blocker, not an untranslated JSON-key gap. The renderer now maps every lesson state and category to the package's existing `opposite.*` keys, resolves them **once per Activity**, uses GreiaTypography for accented glyphs and rendered symbol-plus-text controls, fits longer words to bounded buttons, and caches the ten possible banner surfaces and active/inactive toolbar label surfaces. Its no-resource standalone fallback is visual/pictographic. No gameplay/physics/progression/input/recorded audio changed.

`activities/mondo_contrari/main.py` now passes real `LocalizedResources` derived from the profile's `resolve_activity_locale` and uses `activity.title` for the Pygame window caption; production language support remains **it/en only**. ES/FR rendering is possible **only by explicit test fixture resource injection** until phonics, recorded voice, hardware and L6 acceptance close. `tests/test_activity_mondo_contrari.py` gained a Pygame-based visual/source render-path exercise covering all five categories and ten state keys in all four catalogue languages; **test authored but not executed**.

`activities/viaggio_delfino/delfino_app.py` had correct localized `completion.*` keys and normal `_text` resolution but still used fixed `BRAVO!`/`ANCORA!` as failure-path defaults. It now uses neutral `🐬🌟`/`🔄` symbols when package resources cannot resolve, preserving normal localized completion and audio behavior. `tests/test_four_language_activity_runtime_text.py` now contains **10** source tests (previous 8), covering both this fallback and Opposites semantic-key usage. The four target JSON inventories remain structurally intact; this turn added **zero locale keys** because the ten Opposites strings and Dolphin completion words already existed.

**Evidence and release boundary:** Verified the GitHub source definitions and committed changes; did **not** run Python/unittest, actual graphics at 1024×600 or 800×480, Pygame font/glyph test, speech recording/listening, installed OS or human semantic QA. GLA-015 now includes dedicated Opposites four-locale renderer suite, English/Italian child-facing state labels, ES/FR test-only injection, and Dolphin completion missing-resource path. No supported-language registry change, no manifest promotion, no Parent external-client pin change and no claim of complete four-language localization.


## 2026-10-14 — Owner-approved existing text translations; voice work order dispatched (DOCUMENTATION/AUTHORIZATION)

The owner explicitly **approves all currently authored English, Italian,
Spanish and French text translations** and requests recording **every
missing voice in all four languages**, going through **all 45 built-in
Activities** as well as all other Greia spoken surfaces. This authorizes
using already available zero-new-spend local registered Greia Voice Engine
providers immediately for source-backed exact utterances. New paid Modal
cloud jobs, large provider/model installation and open-ended spending were
not authorized; those require separately specified resources and approval.
The Modal `VoiceProvider` is not implemented at this source checkpoint.

Created the standalone task-specific execution document
`LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md` in this plan folder.
The agent must enumerate 45 apps, inspect code-loaded as well as
catalogue-declared audio, record the 45×4 app/locale status matrix, work
each Activity EN/IT/ES/FR, then shared Shell/launcher/Parent, system
labels, My Time and character speech. The script includes exact Git
sync, inventory, doctor, canonical batch engine, review, resumability
and evidence handoff instructions. It makes the existing
`LOCAL_AGENT_VOICE_PRODUCTION.md` its detailed cue/voice policy and
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` its sole status queue.

**Scope accuracy:** owner approval accepts extant text *as content for
voice authoring*, not not-yet-written full narration transcripts,
unstated name/phoneme pronunciations, or any genuinely unlocalized
inline runtime copy. Missing distinct spoken scripts remain
`BLOCKED_SCRIPT` for the relevant cue only, while other ready clips
proceed. Approval is not a substitute for a person hearing generated
audio, for tests, correct rendering, accessibility, offline acceptance
or L6 Spanish/French system-language promotion.

**Evidence:** the GitHub worktree's committed contents plus readback;
no voice generation, hardware or locally run Pygame/CLI executed
in this authoring session. The local agent will produce the actual
recording ledger, WAV/OGG candidates, receipts, review evidence,
gap list and resumable ZIP under ignored `tmp/` and hand it back for
reviewed integration into `main`.

## 2026-10-16 — Voice-line request list from the P7 reworks (DOCUMENTATION)

Created [`VOICE_LINES_REQUESTED_2026-10-16.md`](./VOICE_LINES_REQUESTED_2026-10-16.md): every voice line requested by the 45 Activity reworks (commits `39733dd9..HEAD`), EN + IT, grouped as shared sets first (numbers 0-25 via a future `shared_number_audio_path`, colour names, position words, shape names, noun names for the `assets/audio/vocab/v1/<locale>/<noun_id>.wav` bank, with current bank coverage computed from the committed files) and then per Activity. Row texts are taken from the reworks' design backlog; lines the backlog only described are marked as proposed/to be authored. Also recorded: known ES/FR defects (Luci `prompt_choose`, Colline empty audio maps, Specchi Lilli voice, Casa ES `prompt_add`) and EN/IT receipts missing in Foresta.

**Evidence:** DESIGN SPEC / request list only. No voice was generated, recorded or listened to; no audio file or receipt was touched; no hardware. The owner review of the list is the next step; ES/FR remain unselectable.


## 2026-10-17 — ES/FR released; selectors trimmed to four; missing voice recorded in all four languages (SOURCE + LOCAL RECORDING, executed)

**Owner decisions (2026-10-17):** EN/IT/ES/FR are all released; every selector offers exactly these four; all missing voice lines approved ("I approve all lines"); image ceiling 1.3 GB.

**Registry and selectors.** `SUPPORTED_SYSTEM_LANGUAGES` in `src/greia_platform/system_language.py` now holds en/it/es/fr (plus a derived `SUPPORTED_SYSTEM_LOCALES`); no second registry. The installer language-first screen, on-device Parent panel, Parent API and `greia-languagectl` already read it; the developer simulator's own five-language list (with German) now reads it too. All 44 localized built-in manifests declare `["it", "en", "es", "fr"]` (Shape Garden stays `["*"]`); Submarine and Dolphin's hard-coded `("it", "en")` supports gained es/fr. The Creations gallery painter (Shell) was a two-branch IT/EN lookup; it now has a four-language table. Tests that encoded "ES/FR staged / not selectable" now require four-language parity; new `tests/test_four_language_release_contract.py` covers registry, selectors, manifests, four-way key/placeholder parity and the shared spoken banks.

**Shell device language.** The Shell, the Activity launch environment (supervisor) and achievement chrome fell back to a hard-coded `"it"` when no `GREIA_*` locale variable was set (always on an installed device). New `resolve_device_locale` / `resolve_child_locale` / `CachedDeviceLocale` in `system_language.py` read the persisted device language (parent override, else the installer's choice), validated against the registry, falling back to `en`; `tests/test_shell_device_locale.py`.

**Text parity.** All 45 Activities already had identical string keys and placeholders in en/it/es/fr (0 keys added); Parent panel, installer and achievement tables were already four-language. Stelle Incantate ES/FR facts were recorded under underscore names the resolver could not find (English played); the ES/FR bundles now map them.

**Voice inventory and recording.** Resolver-aware inventory (`LocalizedResources`, shared resolvers and static scan of code-probed cues) plus the two request lists (`VOICE_LINES_REQUESTED_2026-10-16.md`, `VOICE_LINES_FIRST_BOOT_WIZARD.md`). Full table: [`VOICE_RECORDING_LEDGER_2026-10-17.csv`](./VOICE_RECORDING_LEDGER_2026-10-17.csv) (1,595 rows; 1,557 recorded, 38 existing). Recorded with `tools/greia_voice.py` (Chatterbox MLX for Leo/Lilli/Flash/Tito/Momo with their canonical anchors; macOS `say` for Dani and `pedagogical`: Samantha/Alice/Mónica/Thomas). Every take matches the provider, voice and anchor of the existing approved receipts for the same speaker and language. Integrated with `tools/integrate_reviewed_voices.py --layout mirror`, which now refuses to overwrite any existing file (0 committed audio/receipt files changed).

| set | EN | IT | ES | FR |
|---|---|---|---|---|
| shared character v0.2 (30 cues × 3 takes + intro, 6 characters) | – | – | 96 | 96 |
| first-boot wizard (Leo) | 8 | 8 | 8 | 8 |
| launcher label `sea` / missing titles (Bottega, Casa) | 1 | 1 | 3 | 3 |
| Submarine (buttons, encounters, creatures; EN alarm) | 1 | – | 15 | 15 |
| literacy gaps (ES Ñ, ES/FR syllable praise, FR é syllables) | – | – | 5 | 11 |
| numbers bank 0–25 (new `shared_number_audio_path`) | 26 | 26 | 26 | 26 |
| wired per-Activity cues (Giardino count 6–10 + how_many, Stelle count 1–20, Treno 1–10, Bosco 0, Luci 6–10, Specchi rhombus/heart) | 45 | 45 | 45 | 45 |
| vocabulary bank (nouns, colours, positions, shapes) | 98 | 102 | 119 | 119 |
| per-Activity requested lines (section B) | 139 | 139 | 139 | 139 |
| **total** | **318** | **321** | **456** | **462** |

Disk: +70.1 MiB audio (EN 13.5, IT 14.6, ES 21.4, FR 20.7) + 2.0 MiB receipts. Of that, 33.9 MiB is section-B requested lines that **no Activity code plays yet** (files sit at `activities/<id>/assets/audio/<locale>/<cue>.wav`, resolvable by `audio_path("<cue>")`); wiring them is per-Activity follow-up.

**Listen-check (programmatic, no human listening).** All 1,557 decode, no silence or truncation; 114 clips with Whisper-tiny WARN < 0.6 were re-taken once and the better take kept. 53 short Chatterbox lines (mostly French: "On réessaie !", "Encore une fois !") still have low Whisper-tiny scores with plausible durations; they are marked in the ledger (`asr`/`asr_score`) and should be heard first. FR "Un !" is 0.18 s (single nasal syllable). Receipts carry `human_review = APPROVED` with a note that approval was given before listening.

**Not recorded (no script / needs design):** variable-number templates (`thats_n`, `write_n`, `show_n`, `order_n`, `order_n_toppings`); constellation names, story titles, shelf-full lines, per-friend thank-you, coloured-blanket, per-plant harvest, 12 further aquarium missions, season mission prompts, monster name syllables, Sound Workshop stage-3 phonemes, new Word Forest lessons (not yet in the lesson source), `this_is_letter`. Not overwritten (approved files kept): Luci ES/FR `prompt_choose` wrong instruction, Specchi ES/FR shape lines in Leo's voice, Dolphin welcome mentioning mouse/space, Bosco intro "count to ten". Installer has no spoken UX (boot chime only); Parent panel does not speak.

**Evidence:** focused suites green (1,834 Activity/contract/localization tests); `make test` (fast lane) ran 5,353 tests: OK, 8 skipped. No rendered, installed-image or hardware run.


## 2026-10-19 — Owner-selected new canonical voices and default renderer

The owner accepted the six selected voice designs and their 24 EN/IT/FR/ES comparison samples, then authorized adoption as the active masters and default Voice Studio renderer. New character production now uses v0.2 cloned masters and local shared-worker VoxStage/VoxCPM2 by default, including Dani. Chatterbox remains explicitly selectable; pedagogical pronunciation remains the native/system route. Existing accepted shipping audio/receipts were preserved; this change is not a catalogue-wide re-recording. Source owners, current setup and living producer/Activity guidance were updated. Real engine integration smoke outputs remain review-pending technical evidence, separate from the owner's acceptance of the original comparison batch. Current verification and inherited suite blockers are recorded in `docs/reviews/2026-10-19_VOXSTAGE_VOICE_MIGRATION.md` and HANDOVER; no runtime/hardware language-acceptance claims are added.


## 2026-10-19 — Existing-corpus replacement tool and per-recording direction prepared

The owner explicitly requested a Python tool to regenerate/replace existing Activity and system speech with the selected v0.2 masters/VoxStage model, preserving deterministic isolated letters/syllables, showing progress and providing an agent launch/monitor/repair handoff. The subsequent instruction adds a tone/mood prompt for every recording. `tools/regenerate_voice_corpus.py` and `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` now own this scoped execution operation within this existing rollout; older add-only/no-overwrite instructions are explicitly overridden for it. Fresh output remains human-review pending.

The modular tool inventories exact scripts/identities, resolves blocked metadata, uses one serial VoiceEngine with frozen character performance prompts, stages new takes, backs up original audio/receipts/catalogue metadata, journals recoverable replacement, displays progress/heartbeat, supports status/retry and restores a run in reverse transaction order. It stops on provider errors and does not auto-resubmit uncertain jobs. CLI/batch/warm-service `delivery_prompt` and six editable character defaults also support ordinary generation; Chatterbox/native reject explicit unsupported direction.

Prepared inventory outside Git: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`: **5,308 files; 4,543 READY; 167 BLOCKED_METADATA; 598 PRESERVED**, including 441 isolated teaching targets, 150 historical shared clips, six canonical references and boot chime. All READY requests have an explicit prompt. Scripts missing from the older eight Activity corpora require recovery, not guessing. `resolve` can fill those gaps while retaining completed work. Full corpus replacement was **NOT launched**, and no existing runtime audio or accepted master was replaced during tool preparation.

Evidence: 52 focused voice tests PASS; one real external Lilli English/custom-prompt smoke completed (job `20261019-100927-df5c3cf4`), exact prompt visible in persisted worker request and recording direction, receipt PENDING; worker unloaded. Final `make -k verify`: 5,468 tests, 1 failure/4 errors/8 skips, same inherited profile/executable/macOS installer/MBR failures; global validator still blocks on ARM64 builder assumption. Shell/footprint ran; aggregate NOT GREEN. See `docs/reviews/2026-10-19_VOICE_CORPUS_TOOL.md` and HANDOVER. No new human listening, Simulator/physical playback or release-image acceptance. The next local agent follows the new runbook, resolves legacy script gaps, pilots and runs/monitors the corpus operation, fixing owning modules as needed.

### 2026-10-21 — Automated review after corpus production

Added the read-only `review` subcommand and agent procedure
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. Existing engine audio/verifier
owners handle bounded installed-rendition signal analysis and cached-only eligible
ASR; corpus review adds frozen metadata checks, resumable external reports,
coverage fields and a prioritized listening queue. No media, receipt acceptance,
master or generation state is changed. Missing ASR cannot pass speech screening.

Executed 68 focused voice tests PASS; eight installed technical pilot cues PASS
(ASR off), two eligible ASR pilot cues BLOCKED by the host NumPy/Whisper import.
Full automated corpus review and human acceptance remain unexecuted.
`make -k verify`: 5,484 tests, 1 inherited MBR assertion failure, 4 inherited
errors (ARM64 builder expectation, profile executable permission, two missing
lsblk installer tests), 8 skips; full gate NOT GREEN. This corrects the preceding
entry's error attribution where applicable. Exact logs and next commands are
in HANDOVER and the new procedure. No architecture or release phase closed.

Final gate clarification: project validation also failed on the existing ARM64
builder restriction; shell/footprint checks completed. No full-gate PASS claimed.

### 2026-10-21 — Corrected Whisper interpreter and executed multilingual ASR

The earlier NumPy import blocker came from global Anaconda, not the prepared
Greia venv. Existing Greia Python imports Whisper and finds cached tiny weights;
no installation or package changes were necessary. SETUP, review instructions,
setup manual, quick start and voice skill now use the explicit interpreter.
Live corpus `review --asr auto` on four installed Alphabet ask_A clips completed
all four ASR calls: EN/IT/ES transcript PASS, FR mismatch WARN; EN/IT trailing
silence warnings. Overall 1 PASS, 3 WARN, 0 BLOCKED; expected exit 2. Evidence
is external `2026-10-21-whisper-recovery` under Greia-voice-auditions. Full corpus
review and human acceptance remain pending; no speech changed. Documentation
correction only; no tests rerun or architecture/release phase closed. See HANDOVER
for exact interpreter/package versions and retained prior verification failures.

### 2026-10-21 — Full V2 corpus automated review completed

The unfiltered `review --asr auto` completed against the frozen V2 run using the
prepared Greia Python and cached `mlx-community/whisper-tiny`; no dependencies,
weights, synthesis jobs, or shared VoxStage state were changed. It covered
**4,168/4,168 DONE** recordings; **741 PRESERVED** files remain outside scope.
The report has `complete=true`, `full_corpus_coverage=true`, and no generation
problems. Results: **2,905 PASS / 1,262 WARN / 1 FAIL**. ASR counts are **1,853
PASS / 621 WARN / 1,693 NOT_APPLICABLE_POLICY / 1 NOT_RUN_ERROR**. Thus every
selected recording has a review record, while eligible ASR is incomplete only
for the one clip that failed the hard silence check.

The confirmed FAIL is EN `activities/officina_dei_suoni/assets/audio/en/bear.wav`
(Leo, exact request “Bear”): the installed WAV measures **-77.7 dBFS RMS**. Its
SHA-256 matches its PENDING receipt and the frozen request. No repair or
regeneration occurred. Aggregate warning flags: **621 transcript mismatches,
539 long trailing silence, 165 long leading silence, 122 low-level, 72 long
internal pause**, plus one possible prompt-leakage cue. The latter is EN
`activities/mondo_contrari/locales/en/audio/big.wav`; Whisper included “playful,
clear words” from the acting prompt in the transcript. These are screening and
listening-priority findings; they do not establish audible pronunciation,
identity, acting, independent language correctness, or child intelligibility.
All records retain `human_acceptance_granted=false`; no human listening
acceptance is claimed.

Evidence: external
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review/`
(configuration, per-cue records, `review.jsonl`, terminal summary, and complete
`listening_queue.csv`) and sibling
`2026-10-21-full-automated-review.log`. Process/package metadata is retained in
the report directory. The concurrent Depleted Rain VoxStage jobs were left
untouched. No source changed and no tests were run for this review-only turn.

**Next:** use the owner-authorized generic local HTML listening/review tool with
this report as its manifest input, then work the prioritized queue and record
human states, scores, and notes. Keep every new take pending until listening
acceptance is explicitly recorded.

### 2026-10-21 — Generic HTML human listening desk and Greia adapter

Delivered owner-authorized shared Takeboard in `/Volumes/Test1/Works/takeboard`
(private own repository/catalog/agent skill), with generic JSON import, generated/
master players, bounded list, filters, state/score/notes, atomic saving and JSON
export/reload. Greia owns only `tools/export_voice_review_batch.py`: full reports
export to a 4,168-entry external listening batch, all human states unreviewed.
No audio/receipt/acceptance/journal changed. The real batch is served on 8794.

Executed standalone Python 19 checks and JS 2 tests PASS (including 20k-entry
state/persistence), Greia exporter 3 tests PASS; actual browser small/large batch,
save/reload/export/file-picker/keyboard proof on disposable decisions. Full
`make -k verify`: 5,484 existing tests, same inherited 1 failure/4 errors/8 skips,
ARM64 project validation failure; shell/footprint completed. Exporter tests ran
separately after full-suite discovery. No full-gate green or listening/physical/
release acceptance claimed. Exact evidence/next commands in HANDOVER and
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` §6. Shared core is project-neutral;
application of human JSON decisions to Greia assets remains a separate workflow.

### 2026-10-21 — Owner policy v2 and voice identity/performance separation

Live and saved-evidence reviews share policy v2: ASR >0.8, trailing/internal
silence WARN at ≥1.5s; other checks retained. Full fingerprint-checked reassessment
(no ASR rerun) yielded 3073 PASS/1094 WARN/1 FAIL. 104 unsaved owner decisions
were backed up and copied exactly into the new listening batch on 8796; original
8794 tab preserved. Human JSON decisions are not automatic receipt promotion.

Removed fixed persona traits from default per-recording prompts (all six neutral).
Pitch/register/timbre/voice age belong in masters, acting only per cue. Historical
v2 explicit PERSONA overrides remain untouched but must not be reused. Owner
rejects current Dani/Momo/Tito voices; six new unselected immutable master
auditions generated (two each, 11.84–16.00s), listener on 8795. Shared worker
unloaded after jobs finished. Source research/trace/job evidence is in
`docs/reviews/2026-10-21_VOICE_DIRECTION_AND_REFERENCE_REVIEW.md`; 5–30s is
practical guidance, not proof that old refs were invalid. New master selection
and cloned-line checks precede the draft 1340-file replacement (392/284/664).
No master/runtime file changed; no new corpus regeneration launched.

72 focused tests PASS; full `make -k verify` 5491 tests, same inherited 1 failure/
4 errors/8 skips, ARM64 validation failure, shell/footprint completed. Full gate
NOT GREEN; no phase/runtime/physical/release acceptance. Exact paths and source
constraints are in HANDOVER and automated review procedure §3a.

### 2026-10-21 — Momo/Tito master selection and Dani v4 auditions

Owner-approved exact Momo v3 candidate 1 and Tito v3 candidate 1 are archived in
source `character-voice-masters/v0.3/` with IDs/hash/provenance and selected-source
status. Other four v3 auditions are rejected. Active registry/runtime unchanged.
Three distinct Dani v4 sound-only directions generated: baritone 11.68s, contralto
15.20s, lower androgynous 15.84s; all unreviewed on Takeboard 8797, comparing the
previously rejected v3 Dani. Existing user review sessions preserved. Master source
bytes/WAV headers checked; no code changes/tests rerun or release acceptance.
Shared queue finished and model unloaded. Next is Dani selection, selected-set
registry/clone checks, then the existing corrected 1340-file replacement scope.
Exact job IDs and external paths in HANDOVER. Do not substitute approved references.

### 2026-10-21 — v0.3 masters selected; replacement scope re-frozen

Owner approval verified from saved review: Dani v5 candidate 02 only; Momo
v3 candidate 01; Tito v3 candidate 01. Active IDs are `greia.dani.v3`,
`greia.momo.v3`, `greia.tito.v3`, backed by exact immutable VoxStage IDs and
archived hashes/provenance. Lilli, Leo and Flash remain byte-identical v0.2
masters. The v0.2 manifest/source set and old run/journal/receipts are untouched.

New plan `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/run-v1/`
freezes 1,340 READY records: Dani 392 (EN/IT 102 each, ES/FR 94 each), Momo 284
(71 each locale), Tito 664 (166 each locale). The plan retains all 4,909 earlier
v2 paths and adds only six v0.3 canonical-reference rows; no path was removed.
All 1,340 scripts, locales and semantic speakers match the v2 plan; frozen
original hashes match currently installed files. Those hashes differ from the
v2 plan's pre-v2 input hashes after that run installed its output. New neutral or
line-specific acting prompts replace the old character direction. Other cast,
deterministic letters/syllables, historical assets and unrelated user artifacts
are preserved. Twelve VoiceEngine sanity outputs (3 speakers × 4 languages) are
technical-only, verification off, all `human_review=PENDING`; exact job IDs and
hashes are in `clone-sanity/technical-summary.json`. Focused voice suite: 72 PASS.
Bulk serial production, automated review and human listening remain open. No
runtime/product/physical or release acceptance is claimed.

### 2026-10-21 — local source validation result

The focused voice tests pass 72/72. Local `make verify` fast lane completed 5,491
tests and is **not green**: 2 failures, 4 errors, 8 skips, all outside the voice
scope (shell retained-surface threshold, MBR message mismatch, unsupported ARM64
profile build, build_profile executable bit, and missing host `lsblk` in two
installer tests). The complete output is retained externally at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/source-check-verify.log`.


### 2026-10-23 — Owner-directed native system voice for the exact 52 unresolved rows

The owner requested recording the missing 52 with the appropriate installed system voice and waived listening review. Run: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/native-system-tts-missing-52-v1/`. The existing VoiceEngine and journaled CorpusRunner path made 52 one-call native macOS recordings and installed them transactionally; no character clones, VoxStage, ASR or Parakeet were involved. Locale mapping: EN Samantha (8), IT Alice (4), ES Mónica (12), FR Thomas (28). Exact semantic request and separately pinned spoken text are preserved in receipts.

Terminal and independent receipt audits PASS: 52 changed, 615 of 667 unchanged; all original backups and provenance reconciled. Each receipt truthfully states `verification=NOT_RUN` and `human_review=WAIVED_BY_OWNER` under authorization `owner-2026-10-23-native-system-tts-missing-52`; no machine or listening pass is claimed. The old Parakeet plans and review decisions remain unchanged. Focused voice-pattern verification passed 240 tests. `make verify PYTHON=/opt/anaconda3/bin/python3` ended at its test target with `Abort trap: 6` after 3 failure markers and before a unittest summary; it is NOT GREEN. Log: `/tmp/greia-native-tts-make-verify.log`; HANDOVER records this boundary.

### 2026-10-26 — Manifest-based language extension follow-up (source-only)

Continued the owner-requested source-first manifest architecture after the en/it/es/fr
folder registry and common installer/OS/Parent resource integrations were committed.
Fixed `tools/check_greia_language.py` to support `--staged`: contributors can
validate a fifth locale's UI JSON, Activity TOML, and Activity strings before
adding a selectable `manifest.json`. Optional `first_profile.extra_letters`
can legitimately remain empty; previously the checker treated it as a blocker.
Added fifth-language tests covering staged audits, placeholder mismatch
detection, installer language-page navigation, and installer/on-device Parent
strings supplied through new-language data rather than new Python translations.
Updated the practical language contributor guide with the staged command.

**Verification:** GitHub source review and committed regression tests only.
No local Python tests, `make verify`, GUI/installer image, real device, or
physical playback executed in this remote session. The new test cases must be
run from a full local checkout before acceptance. Manifest-driven selection
is implemented in source, but fifth-language release remains NOT ACCEPTED.
The separate Parents browser app still needs language-specific browser chrome
copy for full translation coverage, and Voice Studio is an external authoring
workstation dependency. No existing approved audio was changed.

### 2026-10-26 — Post-agent source verification: 56 PASS; schema/nested placeholder repairs untested

Local agent verified exact head `7bb1995146ea917da6a3d33004b2c40d48c535ce`
on macOS with Python 3.12.7 (`/opt/anaconda3/bin/python3`),
`PYTHONPATH=src`, bytecode disabled. The five suites passed:
`test_language_manifests.py` 10; `test_system_language.py` 9;
`test_installer_localization.py` 7; `test_panel_localization.py` 19;
`test_four_language_release_contract.py` 11 = **56/56 PASS**.
The per-language source checker returned zero findings for EN, IT, ES and FR.
No active tracked modifications; pre-existing untracked voice audit, `final.mp4`
and `launch-video/` preserved. This is **source-only** evidence, not
rendering, image composition or hardware acceptance.

Agent findings: `check_greia_language.py` did not reject invalid UI schema
and omitted placeholders nested inside format specifications (e.g.
`{count:{width}}`). Subsequent GitHub commits updated the checker to reject
invalid `ui.json` schema/sections/string types and recursively inspect
format-spec placeholders. Added focused tests for invalid schema, nested
UI/Activity placeholders, and retained the separate staged-language flow.
Updated language guide and OS/language agent skills. **These later changes
are NOT covered by the 56-pass evidence**; execute focused suites on the latest
head before any acceptance claim. Browser-based Greia Parents still maintains
independent four-language browser-chrome translations in
`frozenpepper/Greia-Parent-App-Html/src/localization.js` but the device
language choices there already consume the API's manifest-derived language
list. Converting browser chrome to locale data and validating it requires a
separate targeted change and pinned-client integration, not a hardware flash.
No runtime manifests or accepted audio were added or altered.

### 2026-10-26 — Manifest checker rerun: 59/59 focused PASS

Owner's local agent executed requested source suites at exact commit
`bd3aa0a25fdd58220ad1b361ebf7ce2715a3ba47`, Python 3.12.7,
`PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`:
manifest 13, device language 9, installer 7, Parent panel 19, release
contract 11 = **59/59 PASS**. Explicit regressions for nested format
placeholders, UI schema errors and nested staged UI/Activity placeholders
all passed. EN/IT/ES/FR checker: 0 errors each, exit 0.

Worktree remained clean for tracked files, 310 existing untracked files
preserved; no production manifests or audio modified. This closes the
previous entry's *focused source verification* request. **Not evidence
of** a fifth language's rendered UI/font suitability, voice/audio quality,
installer image, physical hardware or complete browser Parents chrome.
Avoid unnecessary repeated checks and defer device work until it can be
combined with an appropriate existing local acceptance session.

### 2026-10-26 — Release docs/skills language-authority correction and cleanup

The owner requested comprehensive release documentation clarity and removal of
old disposable test/demo material. A GitHub source audit examined maintained
language-related documentation, corrected the Activity-authoring skill's
permanent "exactly four" claim to **four currently offered per-locale
manifests**; expanded `docs/development/ADD_A_GREIA_LANGUAGE.md` to
cover existing-language switching, regional fallback, staging, maintenance
and retirement; aligned `SYSTEM_LANGUAGE_AND_LOCALIZATION.md`, release gate,
family Parents guide, voice authoring guides and skill index. New speech still
uses the selected VoxStage/VoxCPM2 and Parakeet-TDT v3 verification;
historical Whisper instructions remain explicitly historical. Old
twelve-language proposal moved to `docs/archive/plans/`.

Repository-wide, safe clean-up removed only the obsolete September website
prototype tree (21 historical files / 3,518,032 bytes), and shortened the
living handover while preserving dated history by Git SHA; accepted voice,
assets, production tests, and A/B evidence remain untouched. Added a
read-only documentation relative-link scanner and unit tests; remote GitHub
inspection of 136 maintained Markdown docs found zero unresolved relative
links. **New scanner tests and full local checkout audit have not executed**,
and neither this nor the previous 59/59 source-localization PASS constitutes
actual fifth-language GUI/image/device/voice or browser-chrome acceptance.

### 2026-10-26 — Release-documentation continuation and duplicate-auditor consolidation

Consolidated the owner's documentation and test-artifact cleanup after
manifest-language source verification. The maintained guide already explains
how to add, stage, enable, change, fall back, and retire a Greia language;
the first-party device lists follow shipped manifests, and the separate
browser Parents chrome still needs its own locale resources. The frozen
corpus Whisper review guide now explicitly distinguishes its historical
workflow from the current pinned Parakeet-TDT v3 default for new VoiceEngine
speech. Contributor/developer indexes point to the existing read-only
`tools/audit_repository_docs.py --scope maintained|all` audit. A duplicate
auditor/test introduced during this review was removed, preserving a single
doc-audit tool. The release-readiness checklist's 2026-08 audit PASS count
was explicitly labelled historical, not a certification of current main.

Previous GitHub cleanup removed 21 website prototype files and nine older
visual-review PNGs, and condensed living handover history with Git recovery
notes. Remaining dated A/B evidence, Encyclopedia visual golden masters,
approved voice recordings and provenance remain intact by design.
**Verification:** GitHub source review only for this continuation; previous
59/59 focused language tests were executed at an earlier HEAD. The existing
three-unit-test documentation auditor and both maintained/all link inventory
modes still need one read-only run in a full checkout. No runtime, generation,
image-build, device, cloud or hosted testing was performed.
