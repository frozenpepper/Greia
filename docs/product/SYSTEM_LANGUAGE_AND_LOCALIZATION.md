# Greia System Language and Localization

**Status:** accepted product behavior; selection/persistence source implemented; translation coverage incremental  
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

The initial selector contains:

| Locale | Language | Visual cue |
|---|---|---|
| `en` | English | 🇬🇧 |
| `it` | Italian | 🇮🇹 |
| `es` | Spanish | 🇪🇸 |
| `de` | German | 🇩🇪 |
| `fr` | French | 🇫🇷 |
| `zh-CN` | Chinese (Simplified) | 🇨🇳 |
| `pt` | Portuguese | 🇵🇹 |
| `ar` | Arabic | 🇸🇦 |
| `hi` | Hindi | 🇮🇳 |
| `id` | Indonesian | 🇮🇩 |
| `bn` | Bengali | 🇧🇩 |
| `sw` | Swahili | 🇹🇿 |

English is the initial highlighted choice. The chooser is usable with pointer and keyboard navigation and reflows for the current installer viewport.

The flags are presentation cues only. The canonical locale tag is the actual stored identity. Flags do not mean Greia is selecting citizenship, country or legal region.

The language list is intentionally broader than Western Europe: Portuguese, Arabic, Hindi, Indonesian, Bengali and Swahili provide high-value coverage across South Asia, Southeast Asia, Africa and other lower- and middle-income regions where low-cost/offline computing is especially relevant to Greia's mission.

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

The only product-owned selectable-language registry is:

```text
src/greia_platform/system_language.py
```

The installer and hidden on-device Parent Settings import that registry directly.

The Parent API returns that same registry to HTML/native clients. Browser code must **not** carry a second hard-coded list.

The Chinese alias `zh` canonicalizes to the selected initial Simplified Chinese locale `zh-CN`.

Adding/removing a selectable device language therefore requires a platform change plus appropriate localization/font/layout evidence; editing a browser-only array is not sufficient.

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

## 10. Selection is not translation coverage

This distinction is mandatory:

> **A locale being selectable means Greia can persist and propagate that device preference. It does not by itself prove that every Greia surface or Activity has complete translations for that locale.**

Current source selection/persistence therefore must not be described as “Greia is fully translated into 12 languages.”

Full language acceptance also requires, per applicable surface:

- translated Greia platform string catalogues;
- translated Parent client strings;
- Activity-localized resources where claimed;
- appropriate font/glyph coverage;
- text shaping where required;
- RTL layout and interaction evidence for Arabic;
- responsive layout under longer/shorter translations;
- localized audio where the product uses spoken instructions;
- physical low-resolution/readability evidence.

Until that work exists, unsupported strings use the existing deterministic localization fallback rather than fabricated machine translations or raw semantic IDs.

## 11. Font and script implications

Nunito Sans remains the selected normal Greia interface family, but it does not automatically supply complete glyph/shaping coverage for Chinese, Arabic, Devanagari or Bengali.

The language-setting architecture is intentionally independent from the final script-font fallback stack. Future font additions must remain platform-owned, bounded and measured on the C0/Acer resource floor.

Arabic additionally requires real RTL text/layout acceptance; merely storing `ar` is not RTL completion evidence.

## 12. Current source ownership

```text
src/greia_platform/system_language.py        registry + persistence + typed service
src/greia_installer/entrypoint.py            first-screen flag selector
src/greia_installer/engine.py                InstallRequest + install-record write
src/greia_parent/protocol.py                 Parent capability/resource vocabulary
src/greia_parent/update_api.py               Parent GET/PUT device-language API
src/greia_launcher/parent_panel.py            hidden Parent Settings selector
src/greia_platform/activity_api.py            Activity/profile locale inheritance
runtime/parent-app-client.toml                exact Parents client pin
runtime/parent-app-client.manifest.json       exact Parents runtime byte integrity
```

External HTML client source:

```text
frozenpepper/Greia-Parent-App-Html
src/api.js
src/language_ui.js
```

## 13. Evidence status

The language-selection/persistence source and focused regression tests are committed.

A current-head PASS is **not** established merely by those commits. Owner-controlled verification must execute the focused Greia tests, complete source gate, external Parent-app tests and installer/physical acceptance before this slice is described as verified on hardware.

Physical installer acceptance should prove at minimum:

1. language chooser is the first visible interactive screen;
2. every flag/English label is legible at 1024×600 and the supported smaller viewport;
3. choose Italian, install, reboot, and confirm effective device locale is Italian;
4. change to another locale from Greia Parents and confirm persistence after reboot;
5. change again from hidden Parent Settings and confirm the same API/store sees it;
6. Activities without profile overrides inherit the current device locale;
7. an Activity that lacks the selected translation follows its declared fallback rather than failing;
8. selecting/storing Arabic/Chinese/Hindi/Bengali does not crash the Shell even before complete translation/font acceptance exists.
