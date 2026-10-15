# Shared localization and prerecorded speech resolver — implementation design

**Decision:** owner-directed 2026-10-15; **implementation in progress** (shared core, launcher, all surveyed localized Activity voice loaders and shared character voice lookup integrated; runtime acceptance remains).
**Workstream:** `PLAN.md` in this folder; align with ADR 0028 and existing profile/device language selection.
**Goal:** one small Greia-owned localization surface used by Activities, launcher and shared child UI for string lookup and **prerecorded** audio lookup. Do not add a new TTS runtime, giant schema, alternate voice engine, migration of approved audio bytes or a second package registry.

## First implementation slice — source committed 2026-10-15

- `src/greia_platform/localization.py`: added `activity_resources(package_root, requested_locale=...)` factory backed by `activity.toml` + Greia's existing profile/device locale owner; a single `LocalizedResources.audio_path(key, filename=None)` returning an existing file or `None`; preserved compatible `audio_cue(key)`. Resolution first tries selected-locale semantic mapping, then projects the canonical EN path (or an existing legacy IT-only path) into the selected locale, then checks conventional assets, then English. Existing text lookup now prefers English before package-default compatibility text for missing selected-locale keys. No playback, mutation, TTS or file authenticity layer.
- `src/greia_launcher/spoken_labels.py`: launcher **Activity title** speech now uses the shared path resolver; platform collection-label playback stays unchanged.
- **Existing semantic users gain ES/FR files without new per-locale audio maps:** `activities/enciclopedia_greia/enciclopedia_audio.py`, `activities/viaggio_delfino/delfino_audio.py`, `activities/sottomarino_giramondo/sub_app.py` already call `LocalizedResources.audio_cue`. Their code was not rewritten; staged fixtures now resolve existing ES/FR audio via English filename projection. Normal installed OS locale selection is unchanged (EN/IT).
- **Five legacy Activity sound owners adapted:** Measurement Workshop (`measure_audio.py`), Ten House (`ten_house_audio.py`), Magic Syllables (`sillabe_audio.py`), Alphabet Leo (`alfabeto_audio.py`) and Word Forest (`foresta_app.py`). Each keeps its preloading/on-demand decode, mixer channels, gameplay/synth SFX and original asset filenames but delegates selected-language + English fallback to `audio_path`. Their composition roots pass the shared resources. Bottega/Casa/Alphabet composition uses the new `activity_resources` factory.
- **Real source tests authored, NOT executed:** `tests/test_shared_localized_audio_paths.py` tests existing ES/FR Encyclopedia, Dolphin and Submarine paths, fallback, actual filename conventions, IT-only alarm alias, manifest/profile localization composition, missing audio, and conventional files; existing `tests/test_localization.py` updated for the owner's EN-only speech fallback instead of a legacy Italian fallback. No GitHub status checks or workflow results reported.
- **Skill updated to the implemented API:** `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `LAUNCHER_SPOKEN_LABELS.md`. New Activities now use `activity_resources`, `.text` and `.audio_path` rather than inventing local file/language lookups; nonstandard approved older filenames remain supported.
- **No audio bytes, selector registries, manifests or approved recordings changed.** No local agent requests, hardware tests, GUI tests, Pygame tests or whole-tree unit tests were executed in this GitHub-only implementation slice. Staged ES/FR actual playback/visual acceptance remains open.

**Next code slice:** review and migrate other speech-owning Activity loaders without converting procedural effects, add regression around locale-specific sound start/stop and sample playback, then review whether a shared resource factory should be adopted by all 45 (only when an Activity actually uses localization). Audio coverage and real hardware acceptance are separate tasks. Avoid turning this into a rewrite or broad governance project.

## Second implementation slice — broad Activity speech migration (2026-10-15)

After auditing every `activities/*/*audio.py` and checking the real GitHub asset tree, the shared resolver now also supports the older `locales/<locale>/audio/<stem>.wav` directory, alongside `assets/audio/<locale>/<stem>.wav`. The small `LocalizedResources.speech_paths()` method enumerates short voice clips for legacy eager-loading SoundManagers, preferring selected-locale files and using English when absent. It handles mixed-case filenames through one neutral semantic alias; no WAV/OGG assets or receipts changed.

**Additional Activity migrations on `main`:**

- `bosco_numeri/bosco_audio.py`: replaced the explicit Italian fallback with shared `audio_path`.
- `festa_delle_rime/rhyme_audio.py`, `officina_dei_suoni/sound_audio.py`, `luci_di_momo/firefly_audio.py`: injected resources from their existing composition roots; loading via shared `speech_paths`.
- `faccine_momo/momo_audio.py`, `mondo_contrari/contrari_audio.py`, `quattro_stagioni/tree_audio.py`: adopted `speech_paths`, retaining sound queues and procedural effects. These were especially important: the existing EN/IT WAVs live under `locales/<locale>/audio`, while the already-approved ES/FR recordings are physically under `assets/audio/<locale>`. The new resolver reaches both without migration/duplication.
- `il_giardino_dei_numeri/giardino_audio.py`, `specchi_magici/mirror_audio.py`, `baia_delle_orche/orca_audio.py`: voice file selection delegated to shared resolver; Activity playback and SFX unchanged.
- `quattro_amici/quattro_audio.py`: uses `shared_character_audio_path(project_root, speaker, cue_id, locale)` for the existing accepted shared v0.2 Flash/Leo clips, with English fallback rather than an Italian fallback. This is a separate existing **shared** resource scope, not an Activity voice-file copy.
- Added test cases to `tests/test_shared_localized_audio_paths.py`: mixed-case name resolution, both directory conventions, English fallback from the legacy `locales` folder, accepted v0.2 character recordings, and **actual committed ES/FR audio filenames across ten migrated Activities**. Corrected expected Spanish curriculum stems to source-native names (`gato`, `barco`) instead of invented English equivalents; verified expected physical paths against the complete nontruncated Git tree.

**Boundaries:** nonverbal-only synth engines (`maze_audio`, `dragon_audio`, `sky_audio`, etc.) are not localization migrations. No game-rule rewrites, no bulk sound regeneration, no selector changes, no increased mandatory metadata. The shared resolver does not own Pygame playback. Any remaining code-specific ad hoc voice selection outside the surveyed sound owners may be cleaned incrementally when discovered.

**Verification classification:** GitHub source/asset paths reviewed; new tests authored and path expectations checked against Git tree; **no Python unittest/Pygame/GUI execution performed in this connector-only session**. GitHub Actions had no registered results for the earlier HEAD. Do not report PASS or four-language runtime acceptance. Continue with focused source/runtime tests when a runnable checkout is available, and repair any regressions before advertising ES/FR.

## Third implementation slice — My Time compatibility and tests (2026-10-15)

- Audited all remaining top-level `activities/*/*audio.py` modules: the unconverted modules are procedural-effects engines or runtime recording/live user audio, not unintegrated packaged voice locale selectors. Also checked incubated `tempo_di_greia` and found a real missing connection.
- **My Time repaired:** `activity_incubator/tempo_di_greia/time_audio.py` previously used `audio_cue(key, allow_fallback=False)` even though both EN/IT `locales/*.json` catalogues have empty audio maps. All 14 interaction recordings (seven EN, seven IT) were physically present under `locales/<locale>/audio/<semantic_key_with_underscores>.wav`. The transport now uses `audio_path(key, filename=key.replace('.', '_') + '.wav')`, selecting actual requested-language audio then English if missing. It still lazily decodes after first frame and owns its single channel.
- `activity_incubator/tempo_di_greia/main.py` now uses `activity_resources(package_root)`, removing another locale/profile bootstrap implementation.
- **Launcher title alias:** `LocalizedResources.audio_path('activity.title')` handles either standard `activity-title.wav` or legacy `activity_title.wav` under `locales/<locale>/audio`, selected language then English. This makes My Time's two accepted title recordings accessible through the unchanged launcher title controller.
- **Regression tests updated/added:** `tests/test_activity_time_audio.py` corrects an obsolete expectation of Italian fallback when English voice absent, tests all real My Time accepted semantic files, and tests French-file/English-file mixing by key. `tests/test_shared_localized_audio_paths.py` and `tests/test_launcher_spoken_labels.py` check standard and underscore title compatibility without renaming files.
- `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md` updated from stale 'nothing recorded' status to owner-approved EN/IT recordings and **unverified live playback**. No WAV/OGG/receipt modifications, no new provider calls, no extra process/scaffolding.
- **Execution status:** GitHub source commits and exact media paths checked. Python test runs, Pygame UI, local-device voice playback and complete release acceptance have **not** yet run. My Time remains incubated; ES/FR system selector stays disabled. **Next high-value action:** run focused Python suites on a runnable checkout and fix actual failures, then continue only demonstrated remaining language path issues.

## 2026-10-15 continuation — regional fallback and Activity-composition cleanup

**Committed on GitHub main, source-level only.** The shared system is no longer just a pilot: it now serves the semantic voice players, launcher Activity-title speech, the 11 subsequent speech integrations and My Time incubator documented in `PROGRESS.md`, plus the remaining legacy voice-bank cleanup below.

- **One regional-fallback rule:** `LocalizedResources` now looks for the selected regional language, then its base language, then English. This applies to strings, semantic voice IDs and `speech_paths()`. Examples: `es-MX → es → en`, `fr-CA → fr → en`. The Activity's Italian UI default is not substituted for the English **speech** fallback. Missing audio still returns `None` from `audio_path`; user-modified files are allowed.
- **No duplicated eager speech scans in four earlier pilots:** `Foresta Parole`, `Alfabeto Leo`, `Bottega delle Misure`, and `Casa del Dieci` now obtain a stem→Path set from `LocalizedResources.speech_paths()`; the game retains its Pygame mixer, caching, SFX, speaking/retry decisions and timing. The legacy directly constructed sound-manager API still works for existing callers.
- **Manifest/profile composition standardized:** `Foresta Parole`, `Sillabe Magiche`, `Festa delle Rime`, `Officina dei Suoni`, `Luci di Momo`, `Giardino dei Numeri`, `Specchi Magici`, `Mondo Contrari`, `Baia delle Orche`, `Bosco dei Numeri`, `Faccine di Momo`, `Quattro Stagioni` and `Quattro Amici` (in its builder) now call `activity_resources` rather than independently duplicating hard-coded language-selection and JSON-loading logic. The currently declared `activity.toml` languages are still only IT/EN.
- **Real language split corrected:** `Quattro Amici` previously resolved its captions using a fallback Activity locale while constructing the character-voice player from the raw requested locale. Both now use the same effective locale. Momo's Faces and Four Seasons use their localized `activity.title` instead of an Italian-only window title.
- **Other audio modules intentionally retained:** remaining engines examined that only synthesize nonverbal effects, or handle child microphone recordings, have no prerecorded language decision to centralize. Do not rewrite them to satisfy a superficial Activity count.
- **Regression coverage authored:** `tests/test_shared_localized_audio_paths.py` exercises regional/base/English lookup, semantic variant filenames, manifest-based context for the migrated Activities, selected-language path precedence and actual approved staged files. **Not run** in the GitHub-only environment. This is not a claim of working GUI playback or readiness to enable Spanish/French.

**Next high-value step:** run focused existing Python tests in a real checkout, review any failures, then test actual selected and English-fallback playback in representative Pygame Activities/launcher. Continue fixing any remaining genuinely localized hard-coded strings, rather than refactoring procedural-only audio modules or adding approval/security machinery. Keep ES/FR selector promotion separate until usable UI and playback have been checked.

## Accepted owner decisions

- Every previously committed voice recording was personally reviewed and **approved by the owner**. Its bytes are final: preserve; do not regenerate or reapprove.
- Users may inspect, edit, swap and replace game audio/text files. No anti-tamper or asset-authentication system is wanted. Limit path handling to basic package-root containment and sensible errors; don't build crypto/signing/checksum gates for user-modifiable content.
- All speech, **including phonemes/letters/syllables for now**, may fall back to English if the selected-language recording is missing. Treat an English fallback as a working compatibility feature, not an automatic crash/rejection. Optional diagnostics can still report language coverage separately.
- The source currently keeps ES/FR unselectable at the OS release level; this refactor does **not** itself promote languages or certify screens/voice playback. It makes the same runtime resolver usable once the separate release decision is made.
- New missing recordings are handled independently by `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`. This design should **reuse** the thousands of approved assets already in the repository.

## Current source — how close?

| Owner | Existing implementation | Gap |
| --- | --- | --- |
| `src/greia_platform/activity_api.py:get_profile_locale()` | Profile/device-selected locale exists | Many callers independently read and resolve it |
| `src/greia_platform/localization.py:ActivityLocaleSupport, resolve_activity_locale, LocalizedResources` | Working JSON bundles, semantic `.text(key, variables, variant)`, `.audio_cue(key, variant, allow_fallback)`, capitalization and substitution | Audio lookup requires explicit per-language `audio` key; selected-locale files can be unreachable when locale `audio={}`; default locale fallback currently follows package default (often IT), not consistent EN compatibility |
| `src/greia_launcher/spoken_labels.py` | Shared launcher collection labels try requested locale file then English | Activity titles still depend on JSON audio cue declarations; duplicate fallback logic |
| `activities/enciclopedia_greia/enciclopedia_audio.py`, `activities/viaggio_delfino/delfino_audio.py`, `activities/sottomarino_giramondo/sub_app.py` | Semantic audio calls are already in place | ES/FR narrator files are present but mapped nowhere |
| `activities/foresta_parole/foresta_app.py`, `activities/sillabe_magiche/sillabe_audio.py`, `activities/alfabeto_leo/alfabeto_audio.py`, `activities/bottega_delle_misure/measure_audio.py` | Good per-Activity caching, timing, Pygame playback | Each separately reads locale directories, constructs filenames, picks fallback, and sometimes maintains locale-specific case statements |
| `skills/greia-activity-authoring/SKILL.md` and `VOICE_GENERATION.md` | Strong semantic-IDs intent and producer separation | Guide currently demands per-locale audio JSON mapping and suppresses English fallback for required speech; update after actual shared code is ready |

**Assessment:** shared localization model exists and most text lookup is already correct. The substantial work is **audio ownership/adoption**, not a new service architecture or a new recording campaign.

## Target responsibilities and minimal public surface

A single Greia-owned **runtime-neutral** resolver remains in `greia_platform.localization`. It is **bound to one resource scope** (Activity package, launcher/system namespace, or shared Greia asset catalogue) and one effective language setting; no globally merged flat keyspace and no Pygame dependency inside this resolver.

Example intended use by new and migrated Activities:

```python
resources = activity_localization(package_root)   # one factory; honors profile/device and manifest
resources.text("instruction.find_letter", {"letter": "A"})
resources.audio_path("presenter.welcome")           # Path | None, no playback side effects
resources.audio_path("phonics.letter_a")            # same English fallback policy for now
```

Exact factory and method names should be selected when editing the existing module, not duplicated in another abstraction. Keep `LocalizedResources.text()` and `LocalizedResources.audio_cue()` as compatible APIs while migrating; the new path-oriented method can delegate to their shared core. **No playback should be performed by localization itself.** Existing Pygame sound managers remain responsible for voice channels, mixer init, decoding, preloading/caching, interruption, sound effects and timing. They receive a resolved audio path from the shared resolver.

Semantics:

1. The Activity passes a stable **meaning key** (e.g., `presenter.welcome`), not a translated sentence, locale-specific condition or raw TTS command.
2. Localization reads the child's selected locale from the existing Greia profile/device language owner once when the Activity is composed. Make isolated explicit-locale injection available for staging and tests.
3. `text(key)`: prefer selected-locale string; fallback to `en` if missing, then an existing declared package-default compatibility option when that is needed to avoid regressions. Preserve `variables`, `variant`, child letter-case policy and existing exception behavior for genuinely unknown IDs.
4. `audio_path(key)`: find a matching **existing physical** file in requested locale; if absent, try English; otherwise return `None`. Do this for phonemes as well (current owner choice). Locale fallback should test actual files, not merely JSON declarations. A malformed/unsupported file is an ordinary playback error for the Activity audio owner, not a security incident.
5. Do not infer that the English filename is the semantic key: **one stable key→filename scheme is necessary**. See compatibility rules below.
6. No new clip or runtime synthesis. The existing authoring-time `tools/greia_voice.py` and its approved assets stay untouched.

## Key→filename resolution, without duplicating locale catalogues

For **new Activities**, adopt one documented convention:

```text
locales/<locale>.json              strings: { "presenter.welcome": "...", ... }
assets/audio/<locale>/<cue-id>.wav  (or .ogg, with stable suffix preference)
locales/<locale>/audio/activity-title.wav   (existing launcher title convention)
```

IDs and filenames are stable across translations: translate spoken/text **content**, not cue identifiers. For an unambiguous new cue ID `presenter.welcome`, a literal file named `presenter.welcome.ogg` is fine. If packages prefer a different filename, declare a **single canonical mapping**, not N locale copies.

For **existing Activities, preserve approved current paths and names**, using the English bundle where it already declares them:

```text
audio["encyclopedia.animals.intro"] = "assets/audio/en/animals/intro.ogg"
 requested "fr"
   -> "assets/audio/fr/animals/intro.ogg" if it exists
   -> "assets/audio/en/animals/intro.ogg" otherwise
```

Do the same for paths `audio/en/sub_fact_whale_1.wav` and `locales/en/audio/activity-title.wav`. Only replace a complete recognized locale **directory component**; never run arbitrary substring replacement. For legacy code-driven stems such as `find_a`, `syl_ma`, `letter_A`, `sub_btn_alarm`, use the new convention where it matches, otherwise add a **small package-local alias** identifying the existing filename once. Avoid one alias entry per locale and do not mass rename recordings.

Lookup precedence for an ordinary voice key:

1. Exact selected-locale semantic mapping if already declared (compatibility).
2. Canonical stable filename mapping (single package source mapping, often `en.json`) projected to the selected-locale folder, if matching physical file exists.
3. New convention based on semantic key under `assets/audio/<selected-locale>/`, checking supported formats.
4. Repeat the same resolution against English.
5. Return `None` (fail soft).

Do **not** make step 1 return a nonexisting path and stop early. Keep path resolution bounded within the resource scope. Avoid speculative filename guessing, recursive searches and large eager directory scans on Acer-class hardware. A bounded per-package key/locale lookup cache is sufficient, ideally reusing existing module caching patterns.

## Scope and decisions to preserve

- **Two independent namespaces:** Localized UI `text` and prerecorded `audio` share locale but do not require a 1:1 key mapping. Some audio is longer than captions, and sound effects are language-neutral.
- **Separate resource scopes:** Activity media belongs to the Activity package, launcher/system collection speech belongs to its platform asset root, shared character speech belongs to the accepted library. A common resolver API can use distinct namespace/source adapters rather than forcing every asset into one directory.
- **Fallback is determined centrally:** no Activity-level `if locale=="it"` purely for UI/speech routing. Legitimate per-language **lesson content** (phonics curricula, examples and game mechanics) stays in pedagogical/content modules. Do not translate syllable rules as plain UI strings.
- **Language changes:** On next Activity launch, instantiate resources for the current effective profile/device language. For an Activity that permits in-place language changes, explicitly rebind/clear its sound cache and redraw its captions. Don't read locale on every frame.
- **Installed package size:** keep lazy or bounded caching. Encyclopedia should not preload all ~200 narration clips per language onto the small Acer reference hardware.
- **Existing status:** ES/FR assets and source texts are staged but Activity manifests and profile selection still advertise EN/IT; don't conflate runtime-resolver support with enabling a release language.

## Implementation order (do real code, relevant tests, then update skills)

**A. Shared resolver first.** Extend existing `greia_platform.localization` instead of creating a parallel module; one factory for Activity context/profile, centralized English fallback and file-aware `audio_path`/compatible `audio_cue`, with English canonical name projection and bounded key lookup. Preserve old public signatures where possible. Add focused unittest fixtures for ES present / ES missing→EN / both missing→None, empty ES `audio` maps, English legacy path variations, title conventions, text substitution/variants/defaults, package boundary and caching. Keep existing `tests/test_localization.py` passing.

**B. Prove real approved recordings work.** Migrate `EncyclopediaAudio`, `PygameDelfinoAudio` and `SubmarineApp` to the shared path resolver without rewriting hundreds of JSON maps. Add source-facing integration tests using actual committed files: look up a real Spanish/French Encyclopedia entry, Dolphin fact, Submarine fact and verify it chooses the ES/FR file, not EN, when present. When absent, assert EN chosen. Keep EN/IT behavior and existing sound channels intact.

**C. Migrate file-owning legacy Activities.** Prioritize `ForestaApp.SoundManager`, `SillabeAudio.SoundManager`, `AlfabetoAudio`, `MeasureAudio`, `TenHouseAudio`, then the other speech-owning Activities found by inventory. Retain each owner's *sound playback/SFX semantics*, remove only duplicate locale and path selection. Test cache/first-frame loading, output paths, absence behavior and progress/scene timing. Do not create a huge common AudioManager with every game's effects.

**D. Share launcher path resolution.** Keep `SpokenLabelPlayer` owning focus/repetition/playback, but route launcher title and collection speech path selection through the same fallback logic once it can resolve platform and Activity scopes. Preserve the current guaranteed EN fallback.

**E. Finish with current generator skill and cleanup.** Only **after A–D are running**, update `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `LAUNCHER_SPOKEN_LABELS.md` and any OS authoring guide with the new real factory/method names, fallback behavior, one canonical cue ID, new package convention and examples. Remove outdated instructions that require one audio JSON table per locale or prohibit an English audio fallback. Revise/extend Activity template and validation if they exist; no speculative unimplemented API in skills. Update active rollout `PROGRESS.md` in place rather than starting another task governance system.

**Acceptance:** a new Activity authored according to the updated skill needs *no new per-Activity localization infrastructure*. Existing approved IT/EN/ES/FR audio remains byte-identical. A test Activity asks for text and audio by semantic ID; selected language wins when available, English file is used otherwise, missing audio fails softly, current EN/IT releases keep working, and real ES/FR assets are reachable via isolated staged fixtures. Only then consider separate four-language selector/visual launch acceptance.

## Notes on engineering scope

This is a **moderate migration**, not a system rewrite. The common string/audio API and effective language owner already exist; the work is removing several file-lookup implementations and adapting older filename patterns. The riskiest changes are real playback ownership, cache invalidation and accidental wrong-resource selection, not file tampering. No new automated policy/checksum framework, no distributed service, no provider calls and no new user-facing settings required.

## 2026-10-16 - Shared vocabulary audio bank

Wonder Match (`memory_meraviglie`) needed approved noun clips already owned by Rhyme Party, Word Forest and Magic Syllables. Rather than copy them per Activity, the 38 byte-identical clips (21 EN, 17 IT, with receipts) now live once in the platform-owned `assets/audio/vocab/v1/<locale>/<noun_id>.wav` bank (README documents ids and sha256 provenance; originals in the source Activities are untouched). `greia_platform.localization.shared_vocab_audio_path(project_root, noun_id, locale)` resolves it with the standard locale chain -> base -> English -> `None` policy, validating only the simple concept id (no path escape, no decoding). It is reached via `project_root` exactly like `shared_character_audio_path`, and `build/lib/compose.sh` already installs `assets/audio/**`. Wonder Match uses the bank and carries no private audio. Migrating Rhyme Party / Word Forest / Magic Syllables to the bank (to drop their duplicate copies) is a separate owner-gated step because their committed files must not be moved.

