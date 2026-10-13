# Greia Four-Language Rollout — Progress Ledger

**Product authority:** [PLAN.md](./PLAN.md)  
**Local voice execution:** [LOCAL_AGENT_VOICE_PRODUCTION.md](./LOCAL_AGENT_VOICE_PRODUCTION.md)  
**Single local task queue:** `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`  
**Evidence status:** GitHub source commits, no newly executed full checkout tests / GUI / recording / physical install in this session.

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
