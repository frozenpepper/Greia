# ADR 0028 — Platform and Activity Localization / Language Context

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Scope:** Greia Shell/launcher, profiles, Parent controls, installer, platform chrome, Activities, localized audio, future Web runtime and package authoring

**Implementation note (2026-10-27):** The Context below describes the
August 2026 gap that motivated this accepted decision; statements such as
"profiles currently have no language override" are **historical baseline**
facts, not a report on present source. The accepted *decision* still governs
the separation of device/profile/Activity UI versus learning-content language.
For the now-implemented device-language manifest directory, optional
`ui.json` resources, actual four offered locales and a practical extension
procedure, use `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md` and
`docs/development/ADD_A_GREIA_LANGUAGE.md`. Browser Parents chrome has a
separate localization catalog; adding an OS manifest does not translate it.

## Context

Greia is intended for young children, many of whom cannot yet read. Activities may also be distributed independently and many will realistically ship in only one language. User-facing words, spoken instructions and language-sensitive media therefore need a platform contract that works both for richly localized Activities and for a perfectly valid English-only Activity installed on an Italian Greia system.

The current API-0.1 Activity manifest has a broad `activity.languages` field, but the platform has no complete locale-selection or localized-resource service. Profiles currently have no language override. First-party Activities largely avoid text, so this missing architecture has not yet been forced into the open.

Several concepts must remain distinct:

1. Greia device default UI language;
2. optional per-child UI language override;
3. an Activity's ordinary UI/spoken-instruction language;
4. an Activity's launcher/catalogue name language;
5. a language that is itself Activity content, such as an English-writing or language-learning mode;
6. the Parent HTML client's own display language;
7. the Linux process locale (`LANG`), which is an implementation detail and not child-facing authority.

Without a clear distinction, Greia would accumulate hard-coded strings, mismatched audio, per-resolution language hacks, confusing per-Activity settings and launcher titles that cannot be translated independently from gameplay.

## Decision

### 1. Greia has one inherited child UI-language authority chain

The ordinary child-facing UI language resolves as:

```text
Greia device default UI locale
        ↓
optional child-profile UI locale override
        ↓
resolved UI locale for the child session
        ↓
Activity UI locale resolution at launch
```

The device default is selected during installation/setup and manageable later from Greia Parents.

A child profile may optionally override the device default. This supports multilingual households without creating separate Linux users or OS locales.

If no override exists, the profile inherits the device default automatically.

### 2. Ordinary Activities do not get a generic per-Activity UI-language preference

By default an Activity follows the active child's Greia UI locale as closely as its package support allows.

Greia does **not** make parents configure a UI language separately for every Activity. That would fragment the experience and create configuration work proportional to installed Activities.

An Activity may explicitly opt into a pre-launch language chooser when language choice is part of its product design. That exception is declared in Activity metadata and presented by Greia, not reinvented by every Activity.

### 3. Single-language Activities remain valid and installable

An Activity that supports only English may be installed on an Italian Greia system.

Example:

```text
child profile UI locale:      it-IT
Activity supported UI locale: en
resolved Activity UI locale:  en
launcher language emblem:     British flag
Activity runs:                 English
Greia Home/Back/system UI:     Italian
```

Lack of an Italian translation is **not** an installation failure unless the Activity falsely claims Italian support.

The launcher must make the language mismatch understandable before launch using a child-friendly visual cue.

### 4. Child-facing language cues are flag-based and platform-owned

Many target children cannot read. Two-letter badges such as `EN`, `IT` or `ES` are therefore not the primary child-facing language indicator.

Greia uses familiar **flag emblems** as the normal visual language cue, under one platform-owned canonical mapping. Product policy explicitly selects language flags rather than treating them as country-selection controls.

Examples:

```text
English    → British flag
Spanish    → Spain flag
Italian    → Italy flag
French     → France flag
German     → Germany flag
Portuguese → Portugal flag
```

The mapping is owned by Greia, initially represented by:

```text
src/greia_platform/language_presentation.py
```

A region-specific locale such as `en-US` still uses the canonical **English/British** language emblem unless a future product requirement explicitly creates a different content concept. The flag represents the language convention, not citizenship or geography.

The flag is dynamic and launcher-owned. Activities do **not** bake a flag into their icon artwork.

### 5. Language marker behavior in the launcher

For a language-neutral Activity that has no translatable/spoken Activity content, no language flag is required.

For a language-specific/localized Activity, the launcher overlays or places a small platform-owned flag corresponding to the locale the Activity will actually use if launched now.

Therefore:

- Italian profile + multilingual Activity resolving to Italian → Italy flag;
- Italian profile + English-only Activity → British flag;
- English profile + multilingual Activity resolving to English → British flag;
- profile changes language → multilingual Activity flag changes automatically;
- remembered/selectable launch language changes → flag reflects the selected launch language.

The Activity package icon remains its own identity; language presentation is composited by Greia.

### 6. Platform-owned pre-launch language chooser

An Activity may declare that its UI language is selectable at launch.

When enabled, Greia presents a child-friendly chooser before the Activity receives display authority. The chooser should be visual/audio-first:

- large flag choices;
- selection/focus feedback;
- optional spoken language name;
- minimal/no reading required;
- controller/pointer/touch compatible;
- same responsive layout rules as the rest of Greia.

The Activity does not implement its own duplicate language-selection shell merely to choose its runtime locale.

The default selection should normally be:

1. the child's profile language if supported;
2. otherwise a remembered per-child/per-Activity choice if valid and product policy selects remembering first;
3. otherwise the Activity default language.

The exact remember/default precedence must be deterministic and tested. A remembered choice is preference state, not package authority.

### 7. UI language and content/learning language are separate concepts

Some Activities need a language that belongs to their content rather than their UI.

Example: an Italian child uses a Writing Activity to practise English.

A clean model is:

```text
Greia UI locale:          it-IT
Writing Activity UI:      Italian or language-neutral icons
content/document locale:  English
spell/audio/letter rules: English
Home/Back:                Italian
```

Similarly, an English-learning Activity may provide Italian instructions while its lesson words/audio are English.

Therefore Activity architecture distinguishes concepts such as:

```text
ui_locale
content_locale
```

rather than one ambiguous `language` variable.

An Activity may declare one or more content locales and may opt into a Greia pre-launch content-language chooser. A single fixed content language needs no chooser.

### 8. Launcher/catalogue title localization is independent from in-Activity UI support

Activity names/titles shown in the launcher must be localizable.

Crucially, launcher-title localization can be broader than the Activity's own UI localization.

Example:

```text
Activity internal UI:          English only
Activity launcher title:       Italian + English translations available
Italian launcher displays:     Italian title + British flag
Activity launch experience:    English
```

This is desirable because a child/parent should be able to identify an English-only Activity from the surrounding Italian system before opening it.

`activity.title_key` is semantic identity, not final display text. The launcher resolves it through the package/platform localization catalogue using the child profile locale and deterministic fallback.

The current humanization fallback that turns IDs/keys into words remains compatibility/development behavior, not the target final localization contract.

### 9. Localization bundles are cross-runtime declarative resources

Package localization resources live beneath a conventional directory:

```text
activity.toml
main.py
locales/
├── en.json
├── it.json
└── ...
assets/
...
```

JSON is selected because both Python and a future Web runtime can consume it without executable localization code.

Initial bundle shape:

```json
{
  "schema_version": 1,
  "locale": "it",
  "direction": "ltr",
  "strings": {
    "activity.title": "Scriviamo!",
    "instruction.choose": "Scegli la risposta"
  },
  "audio": {
    "instruction.choose": {
      "path": "locales/it/audio/choose.ogg",
      "caption_key": "instruction.choose"
    }
  }
}
```

Runtime-neutral implementation begins in:

```text
src/greia_platform/localization.py
```

### 10. Package metadata distinguishes catalogue, UI and content support

The current broad API-0.1 `activity.languages` field is not precise enough to represent the complete architecture.

A future-compatible manifest contract should distinguish, conceptually:

```toml
[localization]
language_neutral = false
catalogue_locales = ["en", "it"]
ui_locales = ["en"]
default_ui_locale = "en"
ui_selection = "follow_profile"  # or "prelaunch_chooser"

[content_language]
locales = ["it", "en"]
default_locale = "it"
selection = "prelaunch_chooser"
```

Exact schema/version migration belongs to implementation review and tests; the important contract is the separation of responsibilities.

For a truly language-neutral icon/game Activity:

```toml
[localization]
language_neutral = true
catalogue_locales = ["en", "it"]
```

It may still have translated launcher titles even though the Activity itself contains no language-specific child-facing UI.

### 11. `languages = ["*"]` must not mean “hard-coded English works everywhere”

Existing packages use `languages = ["*"]` as a broad compatibility declaration. This is insufficient as localization evidence.

Language-neutral must mean the Activity's own child-facing UI/audio does not require linguistic interpretation, not that English strings are hidden behind a wildcard declaration.

During migration, existing manifests must be reviewed and classified honestly.

### 12. User-facing strings are looked up by semantic key

Activity logic should request semantic IDs such as:

```text
activity.title
instruction.choose
feedback.correct
feedback.try_again
```

rather than embedding prose inside game logic.

Named variable insertion belongs to the localization layer so word order can differ by locale.

Until Greia deliberately adopts a richer plural/gender/select message system, authors should prefer whole semantic messages over English-specific string concatenation.

Bad:

```text
translated("you_have") + count + translated("apples")
```

Better:

```text
complete localized message for the intended semantic situation
```

### 13. Spoken/audio localization uses semantic cue IDs

Spoken instructions/feedback use semantic cue IDs such as:

```text
instruction.choose
feedback.correct
character.professor.welcome
```

Each locale maps the cue to its own package audio asset.

The initial portable localized-audio subset is bounded OGG/WAV package assets. More formats/codecs require runtime review rather than assuming a developer machine has a decoder.

A cue may reference a caption/text key for accessibility, debugging and translation review.

### 14. Missing locale resources use deterministic fallback

A child requesting `it-CH` may resolve through supported package locales such as:

```text
it-CH
it
Activity default UI locale, e.g. en
```

only where those locales are actually declared/supplied.

Resource fallback is per semantic key, so an optional untranslated audio cue can fall back without crashing the entire Activity.

Missing required localized resources must be visible during validation/testing and must not silently surface semantic machine IDs to children.

### 15. Single-language fallback must remain obvious but not punitive

If an Activity falls back from the child's profile language to its only supported language:

- installation remains allowed;
- launcher title should still use the best available catalogue translation;
- the flag shows the actual Activity launch language;
- the Activity receives the resolved locale explicitly;
- Greia system chrome remains in the child's normal locale;
- no warning dialog full of text is required merely because the languages differ.

The flag itself is the default child-facing advance signal.

### 16. Platform strings live in a platform localization catalogue

Greia-owned strings—installer, launcher categories, profile screens, system chrome accessibility labels, platform errors and settings—belong to the Greia platform catalogue, not copies inside each Activity package.

Activities cannot redefine Greia Home/Back/system-authority strings.

Platform and Activity localization should use the same locale/context semantics even when the storage roots differ.

### 17. Profile language is app-level preference state

Children remain Greia application profiles over one appliance account model.

A child UI locale override belongs in profile preference/state. It does not create a Linux account or mutate `/etc/passwd`.

The launcher/session resolves device-default + child override and passes the result into Activity runtime context through a typed Greia binding/API.

### 18. Linux `LANG` is not product authority

Greia may set a child Activity's process locale for library compatibility, but Activity code must not treat inherited host `LANG` as the authoritative child preference.

An explicit Greia Activity locale context/API is required so Python and future Web runtimes have the same semantics.

### 19. Localization must cooperate with responsive layout

Translations vary in length. Activities and Greia UI must not compensate by adding language-specific coordinate tables.

Localized strings flow through ADR 0026 responsive layout:

- wrap/reflow automatically;
- text containers grow/shrink within bounds;
- collections reflow;
- essential actions remain reachable;
- no Italian-layout/English-layout coordinate fork.

For canvas/world games, translatable HUD/UI belongs in fluid/safe UI layers where practical. If text is intentionally embedded in a reference-canvas scene, the authored logical bounds must allow localized text fitting/wrapping according to shared helpers.

### 20. Activity authoring guidance should actively encourage localizability

Generated and manually authored Activities should be structured so translation is easy even when only one language ships initially.

The authoring skill must instruct agents to:

- keep user-facing strings out of gameplay logic;
- use semantic localization keys from the start;
- put spoken instructions behind semantic audio cue IDs;
- keep launcher title/name localizable;
- declare actual supported UI/content languages honestly;
- avoid concatenating translated sentence fragments;
- make layouts tolerate translated text length;
- add a second locale when feasible;
- if only one locale is supplied, still structure the Activity so adding another requires data/assets rather than rewriting gameplay code.

This way automatically generated Activities have a much better chance of being translatable even when the initial request is English-only or Italian-only.

## Consequences

Positive:

- English-only Activities work correctly on Italian systems;
- children get a visual flag cue instead of relying on reading language initials;
- multilingual Activities follow profile language automatically;
- selected launch language is visible dynamically without changing package icons;
- launcher titles can be translated even when an Activity itself is single-language;
- Writing/language-learning Activities can distinguish UI language from content language;
- localization data is portable across Python and future Web runtimes;
- responsive layout rather than per-language coordinate hacks absorbs text-length differences.

Costs:

- current wildcard `activity.languages` declarations need semantic migration/review;
- device/profile locale persistence and Parent controls must be implemented;
- launcher needs dynamic flag composition and localized-title lookup;
- platform-owned language chooser UI and flag assets are required;
- first-party Activities need extraction of any user-facing strings/audio as they gain them;
- package validators need localization-bundle checks.

## Non-goals

This ADR does not:

- require every Activity to support multiple languages;
- reject an Activity merely because it supports only one language;
- require every child to have a profile-language override;
- turn flags into geopolitical country selection;
- make per-Activity UI language a universal settings page;
- force content-language choice when an Activity does not need it;
- choose a cloud translation service;
- authorize runtime network translation;
- require language-specific layout/source forks.
