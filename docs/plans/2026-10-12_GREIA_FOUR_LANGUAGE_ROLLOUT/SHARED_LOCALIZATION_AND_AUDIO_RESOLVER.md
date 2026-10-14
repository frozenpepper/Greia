# Shared localization and prerecorded speech resolver — implementation design

**Decision:** proposed/owner-directed 2026-10-15; **implementation not complete**.
**Workstream:** `PLAN.md` in this folder; align with ADR 0028 and existing profile/device language selection.
**Goal:** one small Greia-owned localization surface used by Activities, launcher and shared child UI for string lookup and **prerecorded** audio lookup. Do not add a new TTS runtime, giant schema, alternate voice engine, migration of approved audio bytes or a second package registry.

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
