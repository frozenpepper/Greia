# Add a Language to Greia

**Status:** manifest-based language selection implemented in source (2026-10-26). Physical installer/OS acceptance of an extra language is still unverified. 
**Audience:** human translators or their local agents working with the full Greia checkout.

## Quick route

**Add a language:** run `PYTHONPATH=src python3 tools/scaffold_greia_language.py <locale>`, translate the generated JSON and Activity TOML, record/review required speech, validate with `PYTHONPATH=src python3 tools/check_greia_language.py <locale> --staged`, then add `<locale>/manifest.json` **only when approved for release**. The installer, OS and on-device Parents UI read the offered manifests automatically at next startup. No Python language list needs editing.

**Maintain an existing language:** edit values in its UI/Activity locale files or update its existing manifest metadata; recheck placeholders, speech references and actual screens. Do not run the scaffold over an existing language: it deliberately refuses to overwrite translations.

**Retire an offered language:** owner-approved removal of the manifest stops it being selectable in the next release; saved old preferences fall back according to the platform policy. Preserve approved recordings and historic evidence.

For a family changing language, use [the Greia Parents guide](../user/GREIA_PARENTS.md#change-greias-language). For product behavior, see [the language policy](../product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md); for voice authoring, use the voice-production skill linked below.

## Tell your agent

> Let's add a new Greia language: German (`de`). Prepare all OS, installer, Parent and Activity text, phonics/curriculum work and the missing audio. Use the canonical Voice Studio with the selected masters and Parakeet verification. Do not offer the unfinished language in the installer until it has been reviewed.

The exact locale, native language name, script and translator should be substituted as appropriate.

Read `AGENTS.md`, `SETUP.md`, `skills/greia-language-expansion/SKILL.md` and `skills/greia-voice-production/SKILL.md`. Outside contributors use review branches and pull requests, not direct pushes to `main`.

## One folder owns each offered language

The *only* list of device-selectable languages is the set of valid manifests in:

```text
src/greia_platform/languages/
  en/manifest.json
  it/manifest.json
  es/manifest.json
  fr/manifest.json
  de/                       # translation staging: NOT selectable until manifest exists
    ui.json                  # text resources for installer and OS
```

Example manifest **for German** (use the exact locale tag, native name and appropriate emblem for your new language):

```json
{
  "schema_version": 1,
  "locale": "de",
  "name": "German",
  "native_name": "Deutsch",
  "flag": "🇩🇪",
  "order": 40,
  "direction": "ltr"
}
```

When `de/manifest.json` is added, the installer language-first chooser, the hidden on-device Parent Settings, Greia Parents API and device language persistence automatically discover `de` at the next process start. Installer language tiles and Parent language tiles paginate automatically when there are more than four. The current four languages and their accepted text/audio remain unchanged.

**Important:** a manifest is the decision to *offer* the language, not merely start translating it. A missing manifest keeps a work-in-progress language out of the product. Greia will fall back to English for missing optional messages, but that is not a claim of completed translation. Complex scripts, right-to-left presentation, specialized literacy curricula, and unsupported speech-model languages can still require technical work.

## Prepare the files (no Python changes)

From the full repository, with `PYTHONPATH=src` and development dependencies available:

```bash
PYTHONPATH=src python3 tools/scaffold_greia_language.py de
```

The scaffold creates `src/greia_platform/languages/de/ui.json` containing English reference strings for these data-driven UI surfaces:

- `installer` and `installer_dynamic` (including Wi-Fi/disk/power warnings);
- `parent`, `parent_constants`, `parent_audio_presets` (hidden Parent Settings);
- `collections`, `discoveries`, `launcher_feedback`, `first_profile`, `usage_limit`, `achievements`, `gallery` (child Shell, profile wizard and Creations).

It also creates `activities/<activity>/locales/de.json` for each English-authored built-in Activity, retaining semantic keys and replacing inherited audio declarations with empty entries. This is **reference English copy to translate**, not German. Existing files are never overwritten. No manifest or model is installed by the scaffold.

Translate values, not JSON keys, IDs, placeholders such as `{count}` or `{ssid}`, or file paths. `first_profile.extra_letters` may remain an empty string when the language does not need additional keyboard letters. Keep educational *content language* separate from UI language; phonemes, letter names, lesson items, number pronunciation and child-friendly grammar require their own native-language review. Add `de` to Activity `activity.toml` language declarations once the Activity's translation is complete (this is configuration, not Python code). The Greia Parents HTML client (`parent-app/`) draws its available-language choices from the Parent API; its own UI copy (`parent-app/src/localization.js`) still needs localized review and a repin.

For new languages, `ui.json` is an optional overlay at runtime but required for complete release source review. Existing en/it/es/fr translations still have legacy Python-owned baseline dictionaries; this file interface avoids changing those Python modules for subsequent languages.

Before adding the manifest, audit the staged translation as often as useful:

```bash
PYTHONPATH=src python3 tools/check_greia_language.py de --staged
```

This checks the `ui.json` schema and section types, source catalog completeness, and interpolation keys (including **nested** Python-format fields such as `{count:{width}}`) **without** adding the new language to any device picker. It does not decide whether copied English text has been translated correctly, and Activity TOML declarations must already include the new locale for full source coverage.

## Manage an existing language

**Where it belongs.** Device language identity and native display names come only
from `src/greia_platform/languages/<locale>/manifest.json`. Installer, Shell,
first-profile wizard, on-device Parents and usage/achievement/gallery copy use
the optional `ui.json` sections documented above. Each Activity owns its
actual `activity.toml` supported-locale declaration, `locales/<locale>.json`
text and approved sound files. The browser Parents client (`parent-app/`, in
this repository) uses the device API for the list of languages it can select,
**but** its own browser navigation text is maintained separately in
`parent-app/src/localization.js`. After editing it, run `make parent-app-test`,
commit `parent-app/`, then run `python3 tools/update_parent_client_pin.py` and
commit the pin, manifest and overlay it rewrites, so the image ships the new
catalog. An added OS manifest is *not* proof that the browser chrome has been
translated.

**Change a family's language.** A parent chooses it as the first step in the
installer, later through Greia Parents' **Device → Language** section, or
through the hidden on-device Parents panel opened by holding **S and T
together for five seconds at the child-selection/login screen**, then
authenticating. The single device language store persists the change and the
child-session's profile override takes precedence where one is configured.
Greia re-resolves Activity UI language from declared Activity support; an
English-only Activity is still allowed on an Italian-language computer.

**Fallbacks and content.** Regional variants resolve exact locale, then base
locale, then English where the Activity's declared policy allows. Text and
semantic prerecorded speech resolve through the shared platform localization
handler, never by guessing filenames with custom per-Activity code. Fallback is
resilience, *not* an excuse to mark a language as completed: the child may
need spoken instructions in the selected language. The educational **target
language** of a phonics, rhyming or writing lesson is separate from ordinary
UI locale and may require native pedagogy/content authoring.

**Update, fix or remove a language.** Edit translation values, reviewed sound
assets or the metadata manifest, not a Python list. Keep placeholders and
semantic cue IDs stable; add new keys across **all offered locales**. For a
country/region variant, use the canonical BCP-47 tag/directory and test exact
locale versus base fallback before publishing. To discontinue a selectable
language, first secure explicit owner approval, remove its offered
`manifest.json` in a reviewed release, check existing saved preferences
fall back cleanly, and reconcile Activity/voice/client claims. Do not delete
approved voice files or prior evidence as an accidental side effect.
Manifests and UI resources are loaded at process startup: rebuild the image
or restart the relevant process to see a new offered language. Never edit
live-installed files to simulate a released language in a family build.

**Troubleshooting.** A new locale missing from the installer almost always
means it has no valid shipped manifest, was staged without promotion, or the
process has not restarted. A visible locale with English strings needs a
`ui.json`/Activity bundle coverage review, *not* another selector entry. A
blank flag or clipped text is a font/renderer and viewport issue; test
800×480 and 1024×600. Missing speech needs a semantic cue and native
recording review; do not invent a TTS runtime on the child's OS.
Run `tools/check_greia_language.py <locale> --staged` before promotion and
without `--staged` after it, alongside the focused release tests.

## Record and verify spoken material

Follow `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` and `tools/greia_voice_core/README.md`. The Voice Studio entry point is **`tools/greia_voice.py`**. It uses:

- **VoxCPM2** via the shared **VoxStage** worker for character speech (Chatterbox remains an explicit alternate provider).
- Immutable canonical masters at `assets/audio/characters/canonical/v0.3/manifest.toml`: Dani, Tito and Momo selected v0.3; Lilli, Leo and Flash retain their exact v0.2 identities.
- Pinned local **Parakeet-TDT v3** for current generation verification; older Whisper Base is retained for historical comparisons. The exact pinned Parakeet model/revision is in `tools/greia_voice_core/asr_policy.py`.
- Human listening before final acceptance. ASR PASS does not certify pronunciation, emotion or language accuracy. New language recognition and native pedagogical pronunciation require explicit capability checks.

On the owner's **already-provisioned** Apple Silicon authoring host:

```bash
voxstage start
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

Read the selected provider, reference and `verifier.available` statuses independently. For each reviewed script generate into temporary review staging via `greia_voice.py generate` or a serialized `batch`, then use the existing Takeboard/manual review workflow and integrate accepted audio paths. The external private `frozenpepper/voxstage` tool and Takeboard are not automatically installed or made accessible by a Greia clone; a fresh volunteer machine still needs a separately arranged, compatible voice workstation. Never silently download models, use paid cloud compute, or overwrite approved audio.

## Promote and validate

After the translated text and audio are in place and the owner approves offering the new language, add `de/manifest.json` and verify all product areas:

```bash
PYTHONPATH=src python3 tools/check_greia_language.py de
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_language_manifests.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_system_language.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_installer_localization.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_four_language_release_contract.py' -v
make verify
```

`check_greia_language.py` checks that the offered locale has its UI text sections, matching placeholders, Activity manifests and Activity text bundles. The release contract also checks shared voice-bank availability. Both are source-only checks; they cannot replace human audio review, font and text-fit acceptance at 800×480/1024×600, actual installer/Parents behavior, full image composition or playback on physical hardware.

**Do not ship the new manifest on a family image until the language actually works.** Moving a language from a translation-only folder into the offered set requires no edits to the core language registry, installer language chooser, on-device Parent language chooser, or their API. Restart the appropriate application/rebuild the image to load newly added manifests; the registry is read at startup, not rescanned every frame.

## Evidence and caveats

Report the locale, changed translation/resource files, exact untranslated/fallback items, missing narrated/phonics cues, voice provider/master and verifier readiness, test results, GUI/device screenshots, playback review and any unsupported script features. The current four-language rollout remains en/it/es/fr until a new language is explicitly promoted. Avoid claiming that adding an RTL/non-Latin language is automatically equivalent to adding another Latin-language resource pack.
