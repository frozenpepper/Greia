# 2026-08-19 — Device Language Selection and Persistence Implementation Review

**Status:** SOURCE IMPLEMENTED / CURRENT-HEAD EXECUTION PENDING  
**Repository:** `frozenpepper/Greia`  
**Branch:** `main`  
**Architecture authority:** ADR 0028  
**Product authority:** `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md`

## 1. Requested product behavior

Greia must expose one device-language choice through three surfaces:

1. the installer, as the **first interactive choice**;
2. Greia Parents;
3. the authenticated hidden Parent Settings panel on the Greia device.

The installer choice must transfer to the installed OS. Later Parent changes must update the same device-default setting without requiring reinstall.

The requested initial list is represented by one canonical platform registry:

```text
en     English              🇬🇧
it     Italian              🇮🇹
es     Spanish              🇪🇸
de     German               🇩🇪
fr     French               🇫🇷
zh-CN  Chinese (Simplified) 🇨🇳
pt     Portuguese           🇵🇹
ar     Arabic               🇸🇦
hi     Hindi                🇮🇳
id     Indonesian           🇮🇩
bn     Bengali              🇧🇩
sw     Swahili              🇹🇿
```

English is the default. `zh` canonicalizes to `zh-CN`.

The non-European additions deliberately include major languages used across South/Southeast Asia and Africa rather than treating localization as a Western-Europe-only feature.

## 2. Canonical authority and persistence

Exact implementation owner:

```text
src/greia_platform/system_language.py
```

`SUPPORTED_SYSTEM_LANGUAGES` is the only product-owned selectable device-language list. Installer and on-device Parent UI import it directly; remote Parent clients receive the same rows from the Parent API.

Effective device language precedence:

```text
/var/lib/greia-system-settings/language.json
        ↓ if valid
/etc/greia-os/install-record.json
        ↓ if valid
English
```

The install record remains historical installation evidence. A later Parent language change creates/replaces `language.json` and does not rewrite the original install record.

Writes are atomic and state is schema-versioned. Malformed persisted override state falls back instead of crashing the child environment.

## 3. Installer integration

New live entry point:

```text
src/greia_installer/entrypoint.py
```

The installed live service launches:

```text
python3 -m greia_installer.entrypoint
```

The entry point runs a mandatory flag-first language chooser and then composes the pre-existing installer. Disk selection, hardware probing, Wi-Fi, safety confirmation and destructive installation remain owned by the existing installer code rather than being duplicated.

`LanguageFirstInstallerApplication` binds the chosen locale into the real `InstallRequest`:

```text
flag choice
  → InstallRequest.locale
  → InstallationEngine
  → installed /etc/greia-os/install-record.json
```

The selector is responsive, keyboard/pointer accessible and defaults to English.

### Live installer font/flag dependency correction

A source audit found that the live installer package set originally lacked the dependencies used by the shared Greia typography/color-emoji renderer. Without correcting that, source-level UI logic could be correct while physical installation showed missing-glyph boxes or failed imports.

`build/package-sets/installer-base.txt` now includes the live-installer dependencies required by the selector's Greia typography path:

```text
fonts-noto-color-emoji
python3-pil
python3-regex
```

A regression in `tests/test_system_language.py` protects this composition requirement.

## 4. Greia Parents API

Canonical typed resource:

```text
GET /api/v1/settings/language
PUT /api/v1/settings/language
settings.language
```

Owners:

```text
src/greia_parent/protocol.py
src/greia_parent/update_api.py
```

GET returns the current locale, selected-language metadata and the canonical registry. PUT accepts only a supported Greia locale.

This is a typed platform-setting mutation. The Parent daemon is not given generic locale-file, shell or arbitrary filesystem authority.

## 5. External Greia Parents HTML client

Source repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Greia's runtime pin for the language-enabled client is:

```text
519651a5931269ed4275324f2a87ad3f0d08a3f6
```

and exact staged-runtime byte integrity is recorded in:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Relevant client source:

```text
src/api.js
src/language_ui.js
index.html
```

The Settings page renders the API-provided registry rather than keeping a browser-specific language array. A change sends only the selected locale through the typed PUT route.

Focused source coverage lives in:

```text
tests/language_api.test.js
```

Later documentation-only Parent-app commits do not require moving the runtime pin because they do not alter staged client bytes.

## 6. Hidden on-device Parent Settings

Owner:

```text
src/greia_launcher/parent_panel.py
```

After Parent-password authentication, Language is the first panel tab, before Wi-Fi, SSH Maintenance and pairing/remote information.

The launcher process is not given arbitrary privileged settings access. The mutation path is a narrow helper:

```text
/usr/local/lib/greia-os/greia-languagectl set <supported-locale>
```

Build inputs:

```text
build/overlay/usr/local/lib/greia-os/greia-languagectl
build/overlay/etc/sudoers.d/greia-language
build/overlay/usr/lib/tmpfiles.d/greia-language-helper.conf
```

The helper validates the requested locale against the canonical registry. The sudo rule does not grant general root command execution.

`/var/lib/greia-system-settings` is already a setgid `pipsettings` state root shared by the bounded settings participants. Language state is mode `0660`, allowing the Parent daemon and the narrow helper path to remain interoperable regardless of which surface changed the language last.

## 7. Activity inheritance

`src/greia_platform/activity_api.py::get_profile_locale()` follows the Greia language-context chain rather than inheriting arbitrary host `LANG` as product authority.

Conceptually:

```text
device default
  → optional child-profile override
  → Activity requested locale
  → Activity-supported-locale fallback
```

An Activity remains installable when it does not support the current device language; it must resolve honestly to a language it actually ships.

Current `main` also contains a separate 2026-08-19 pass adding English/Italian localization resources across all 18 first-party Activities. That is useful source coverage, but it landed after the last recorded aggregate gate and must not be promoted into current-head PASS without execution.

## 8. Selection is not complete localization

This boundary is mandatory:

> A selectable locale proves that Greia can store and propagate that device preference. It does not prove that every Greia surface and Activity is fully translated, shaped and physically accepted in that locale.

The 12-locale registry therefore does not mean “Greia is fully translated into 12 languages.”

Still-separate work includes:

- complete Greia platform string catalogues;
- complete Parent-client translations;
- Activity translations beyond what each package actually declares;
- script-font fallback for Chinese, Arabic, Devanagari and Bengali;
- shaping and bidirectional/RTL behavior for Arabic;
- responsive translated-text acceptance;
- localized speech/audio where required;
- physical low-resolution readability/interaction acceptance.

## 9. Regression source

Primary Greia regression:

```text
tests/test_system_language.py
```

It covers:

- canonical bounded registry and required locales;
- Chinese alias canonicalization;
- install-record bootstrap;
- mutable override precedence/persistence;
- malformed-state fallback;
- Activity API inheritance;
- Parent API resource/capability/read/write behavior;
- installer entry-point wiring;
- narrow privileged helper/sudo boundary;
- helper executable-mode composition;
- live installer typography/color-flag package dependencies.

Related existing suites also exercise installer and Parent-panel integration.

External Parent client:

```text
tests/language_api.test.js
```

## 10. Evidence boundary

The last recorded complete owner-controlled source gate predating this tranche was:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

The selector/persistence work, the later 18-Activity English/Italian localization pass and concurrent child-UX work landed after that evidence. Therefore no current-head aggregate PASS is claimed here.

No rebuilt language-first installer has yet been physically accepted on the Acer/reference hardware in this tranche.

Do not query/run/rerun GitHub-hosted Actions without explicit owner authorization.

## 11. Required next verification

On an owner-controlled current Linux checkout, record exact `main` SHA and preserve first failure.

Focused gate:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_language \
  tests.test_parent_api \
  tests.test_launcher_parent_panel \
  tests.test_installer_engine -v
```

Then:

```bash
make verify
```

External Parent client:

```bash
npm test
```

Physical rebuilt-installer acceptance must prove:

1. language selector is the first interactive screen;
2. all 12 choices have usable flags/labels at the Acer viewport;
3. choosing Italian survives installation/reboot as the device default;
4. Greia Parents changes the same setting and it survives reboot;
5. hidden Parent Settings changes that same state and Parents sees it;
6. Activities inherit the device locale unless a child override exists;
7. unsupported Activity locales follow deterministic fallback;
8. selecting Arabic/Chinese/Hindi/Bengali does not crash even before complete script/RTL translation acceptance exists.

## 12. Current architectural priority

This cross-cutting product work does **not** close or reorder R7. Direct graphics/session/input architecture remains the first blocking platform phase, with production Xorg/xinit still provisional until the R7 evidence/selection gates are satisfied.
