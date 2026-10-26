# Add a Language to Greia

**Status:** manifest-based language selection implemented in source (2026-10-26). Physical installer/OS acceptance of an extra language is still unverified. 
**Audience:** human translators or their local agents working with the full Greia checkout.

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

An English reference manifest looks like this (substitute the new locale and names):

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

Translate values, not JSON keys, IDs, placeholders such as `{count}` or `{ssid}`, or file paths. `first_profile.extra_letters` may remain an empty string when the language does not need additional keyboard letters. Keep educational *content language* separate from UI language; phonemes, letter names, lesson items, number pronunciation and child-friendly grammar require their own native-language review. Add `de` to Activity `activity.toml` language declarations once the Activity's translation is complete (this is configuration, not Python code). The external Greia Parents HTML client draws its available-language choices from the Parent API; its own UI copy still needs localized review in the separately managed `frozenpepper/Greia-Parent-App-Html` repository.

For new languages, `ui.json` is an optional overlay at runtime but required for complete release source review. Existing en/it/es/fr translations still have legacy Python-owned baseline dictionaries; this file interface avoids changing those Python modules for subsequent languages.

Before adding the manifest, audit the staged translation as often as useful:

```bash
PYTHONPATH=src python3 tools/check_greia_language.py de --staged
```

This checks the `ui.json` schema and section types, source catalog completeness, and interpolation keys (including **nested** Python-format fields such as `{count:{width}}`) **without** adding the new language to any device picker. It does not decide whether copied English text has been translated correctly, and Activity TOML declarations must already include the new locale for full source coverage.

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
