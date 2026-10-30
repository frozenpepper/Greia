# Greia System Language and Localization

**Status:** accepted product behavior; four released languages EN/IT/ES/FR (owner decision 2026-10-17)  
**Date:** 2026-08-19  
**Architecture authority:** ADR 0028  
**Canonical implementation:** `src/greia_platform/system_language.py`

## 1. Product goal

A family must be able to choose the language of a Greia machine before doing anything else in the installer, and must be able to change that choice later without reinstalling the OS.

The same Greia **device-default UI locale** is therefore manageable from three product surfaces:

1. the graphical installer — **first interaction**;
2. Greia Parents — Settings;
3. the authenticated hidden Parent Settings overlay on the Greia itself.

These are three views of one platform-owned setting. They must never maintain independent language lists or incompatible locale identifiers.

## 2. Installer behavior

The first graphical installer screen is a flag-first language chooser. It appears before the normal Greia welcome, keyboard/layout, target-disk, hardware, Wi-Fi and confirmation flow.

**Current selectable registry:**

| Locale | Language | Visual cue |
|---|---|---|
| `en` | English | 🇬🇧 |
| `it` | Italian | 🇮🇹 |
| `es` | Spanish | 🇪🇸 |
| `fr` | French | 🇫🇷 |

The owner released Spanish and French alongside English and Italian on
2026-10-17. These four manifests are installed today; new offered languages
are discovered from the manifest directory when added to a future release.
German `de`, Simplified
Chinese `zh-CN`, Portuguese `pt`, Arabic `ar`, Hindi `hi`,
Indonesian `id`, Bengali `bn` and Swahili `sw` are not supported
product choices at this time. Former twelve-language source/persistence
policy was misleading and has been superseded by the accepted rollout
plan:

```text
docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md
```

English is initially highlighted. The selector supports pointer and
keyboard navigation at the installer's actual viewport. Flags are
presentation cues, not citizenship or legal region.

This is a deliberate reduction of what a parent can select today.
Prior unsupported locales may remain in immutable installed records
or historic preferences; the runtime falls back to English without
rewriting those original records. Choosing a supported language via
the Parent controls atomically replaces the override.

## 3. Installation transfer contract

The selected locale is passed into the real `InstallRequest` and written to the installed system's immutable installation record:

```text
/etc/greia-os/install-record.json
```

Conceptually:

```text
installer flag choice
        ↓
InstallRequest.locale
        ↓
installed install-record.json
        ↓
Greia device-default locale
```

The installation record remains historical evidence of the original installation choice. It is not rewritten merely because a parent later changes the language.

## 4. Later parent changes

A later Parent change is stored atomically in:

```text
/var/lib/greia-system-settings/language.json
```

The current effective language resolves as:

```text
language.json override, when valid
        ↓ otherwise
install-record.json locale
        ↓ otherwise
English
```

This makes the installer choice the initial default while still allowing a family to change languages without reinstalling the machine.

Malformed/missing override state must fail safely to the install-time/default value rather than breaking the child Shell.

## 5. One canonical registry

The only product-owned selectable-language registry is the discovered
set of manifests under:

```text
src/greia_platform/languages/<locale>/manifest.json
```

`src/greia_platform/system_language.py` loads and validates those manifests
at process startup, exposing `SUPPORTED_SYSTEM_LANGUAGES` to the installer,
hidden on-device Parent Settings, privileged helper and Parent API. The
per-language `ui.json` file in the same directory provides optional UI text
resources. Absent manifests are not offered; incomplete translation folders
must not contain a manifest until the language has passed acceptance.

The Parent API returns that same registry to HTML/native clients. Browser code must **not** carry a second hard-coded list.

Legacy `zh` and `zh-CN` values are no longer selectable until Chinese text, script and runtime acceptance. Old records containing them fall back safely to English.

Adding/removing a selectable device language therefore requires a reviewed
language manifest and complete localization/font/audio/layout evidence, **not**
a new Python language registry entry or browser-only array. Extra languages
must be validated on real installer, Shell and Parent surfaces. Existing
hardcoded English/Italian/Spanish/French baseline tables remain as fallbacks;
new translations can be added through language UI JSON resources.

## 6. Greia Parents API

The versioned Parent API exposes:

```text
GET /api/v1/settings/language
PUT /api/v1/settings/language
```

Capability:

```text
settings.language
```

GET returns:

- current locale;
- current selected language metadata;
- canonical selectable-language list.

PUT accepts only a supported locale, e.g.:

```json
{
  "locale": "it"
}
```

It is a typed Greia setting, not an arbitrary locale/file/shell operation.

## 7. Greia Parents UI

The responsive Greia Parents Settings page displays a full-width language card driven by the API-provided registry.

Each choice may show:

- canonical flag cue;
- simple English name;
- native-language name where the browser/font stack can render it.

Changing a language updates the device setting through the typed Parent API. No SSH or shell fallback is permitted.

## 8. Hidden on-device Parent Settings

The authenticated hidden Parent Settings overlay exposes **Language** as its first tab, ahead of Wi-Fi, SSH maintenance and pairing information.

The child-facing launcher account does not gain broad write access to system settings. The overlay uses a narrow privileged operation that accepts only:

```text
set <supported-locale>
```

and the helper validates the locale against the canonical Greia registry before writing the language state.

This is intentionally narrower than granting `greiakid` arbitrary system-settings or shell authority.

## 9. Activity inheritance

ADR 0028 remains authoritative for language inheritance:

```text
Greia device default
        ↓
optional child-profile override
        ↓
resolved child UI locale
        ↓
Activity supported-locale resolution/fallback
```

`get_profile_locale()` reads the active profile override when one exists, otherwise the current device default.

Selecting Italian does **not** make an English-only Activity invalid. The Activity resolves to a supported fallback according to ADR 0028 and should expose the actual launch language through Greia's child-friendly language cue.

## 10. Selectable languages and truthful completeness

As of 2026-10-26 the **currently shipped** selectable manifests are English,
Italian, Spanish and French (owner decision 2026-10-17). This is not a hard
four-language ceiling: the release contract derives required locales from
the manifest set. The existing four have source text/placeholder parity
and shared spoken-bank coverage (`tests/test_four_language_release_contract.py`);
focused source verification passed 59/59 at `bd3aa0a` on 2026-10-26.
The installer/Parent rendering, voice listening and actual image/device
acceptance of a **fifth** language are still unverified. A future locale
is offered only after its source, audio, font, UI and owner acceptance.

Complete acceptance for each promised language requires:

- reviewed installer source/format/error strings;
- Greia Shell, Parent overlay/HTML client and accessible system messages;
- Activities, Creatives/Creations, encyclopedia and profile overrides;
- text fitting and correct glyphs at 1024×600 and 800×480;
- fully reviewed voice assets for all required semantic cues;
- actual installed image/Parent API/installer inheritance acceptance;
- separate source, rendered and hardware evidence.

A missing required translated string or spoken clip is a release
blocker for that language even when deterministic fallback safely
keeps runtime alive. Third-party single-language Activity behavior
from ADR 0028 remains valid.

## 11. Font and script implications

Nunito Sans remains the selected normal Greia interface family, but it does not automatically supply complete glyph/shaping coverage for Chinese, Arabic, Devanagari or Bengali.

The language-setting architecture is intentionally independent from the final script-font fallback stack. Future font additions must remain platform-owned, bounded and measured on the C0/Acer resource floor.

Arabic additionally requires real RTL text/layout acceptance; merely storing `ar` is not RTL completion evidence.

## 12. Current source ownership

```text
src/greia_platform/system_language.py        manifest loader + persistence + typed service
src/greia_platform/languages/*/manifest.json  offered language metadata
src/greia_platform/languages/*/ui.json        optional per-language UI text catalog
tools/scaffold_greia_language.py              English-reference UI + Activity bundle creation
tools/check_greia_language.py                 source completeness/placeholder audit
src/greia_installer/entrypoint.py            first-screen flag selector
src/greia_installer/engine.py                InstallRequest + install-record write
src/greia_parent/protocol.py                 Parent capability/resource vocabulary
src/greia_parent/update_api.py               Parent GET/PUT device-language API
src/greia_launcher/parent_panel.py            hidden Parent Settings selector
src/greia_platform/activity_api.py            Activity/profile locale inheritance
runtime/parent-app-client.toml                exact Parents client pin (tree id of parent-app/)
runtime/parent-app-client.manifest.json       exact Parents runtime byte integrity
```

Browser Parents client source (same repository, `parent-app/`):

```text
parent-app/src/api.js
parent-app/src/localization.js
parent-app/src/views_device.js  # language choices from API, independent browser-chrome catalogs
```

## 13. Evidence status

The language-selection/persistence source and focused regression tests are committed.

Source-level evidence: owner/local agent ran 59/59 focused language tests at
`bd3aa0a25fdd58220ad1b361ebf7ce2715a3ba47` with Python 3.12.7 and
zero source/placeholder findings for EN/IT/ES/FR. Subsequent documentation
and repository-cleanup changes do not imply a new hardware run.
The browser Parents client pulls **device-language choices** from
the API, but its own English/Italian/Spanish/French browser-chrome translation
strings remain in `parent-app/src/localization.js`.
For a new fully localized browser language, that client needs
its own catalog and a repin (`tools/update_parent_client_pin.py`); an OS
manifest does not magically translate browser navigation.

Installer, physical viewport, font, child spoken language and fifth-locale
end-to-end acceptance are **not** established by the source tests.

Physical installer acceptance should prove at minimum:

1. language chooser is the first visible interactive screen;
2. every flag/English label is legible at 1024×600 and the supported smaller viewport;
3. choose Italian, install, reboot, and confirm effective device locale is Italian;
4. change to another locale from Greia Parents and confirm persistence after reboot;
5. change again from hidden Parent Settings and confirm the same API/store sees it;
6. Activities without profile overrides inherit the current device locale;
7. an Activity that lacks the selected translation follows its declared fallback rather than failing;
8. a legacy saved unsupported locale safely falls back to English; newly unsupported locales cannot be selected or stored through the typed service.

## 14. Language-maintenance workflow

For translating, introducing, promoting or retiring languages, use the single
contributor runbook `docs/development/ADD_A_GREIA_LANGUAGE.md` and agent skill
`skills/greia-language-expansion/SKILL.md`. An incomplete `ui.json` folder
does **not** make a language selectable. An accepted `manifest.json` does.
Language selection is loaded at process start; adding files to a running device
does not update its current chooser in real time. Removal requires owner
approval and checking the saved-language fallback, Activity declarations,
audio and Parents browser presentation before rebuilding/releasing.

The superseded September language-tier proposal has been moved to
`LANGUAGE_SUPPORT_TIERS_PROPOSAL_2026-09-27.md` (archived; see git history) as
historical evidence only. The four-language rollout is also dated history;
the live selector authority is now the per-language manifest set.

**Superseded 2026-10-17:** the owner released es and fr; current visible
device choices are en, it, es, fr. All other language tags are retired from device selection
until independently supported. New platform and installer source
commits do not establish unit/visual/hardware acceptance.
