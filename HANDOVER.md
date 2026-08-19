# Greia — Standalone Engineering Handover

**Date:** 2026-08-19  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting source tranches after the last executed aggregate gate:** **device-language selection/persistence + R13B transactional updates + Activity Simulator/emoji/Writing**  
**External Parent HTML runtime revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6`

This file owns the current continuation/evidence boundary. Historical implementation detail belongs in the append-only active plan and dated reviews. Exact APIs and limits remain source-owned.

---

## 1. Repository / execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests into PASS merely because the files exist.
- Active plan: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- R7 remains the first incomplete blocking architecture phase. Cross-cutting product work does not close or skip R7.

---

## 2. Current evidence boundary

The latest recorded owner-controlled aggregate source gate before the new device-language tranche is:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

That historical gate covered the then-current Activity Simulator/Remote Bridge, Unicode/color-emoji + Writing work, on-device Parent Settings/Wi-Fi/SSH foundation, UI performance work and six additional first-party Activities.

**The device-language source described below landed after that gate and is UNPROVEN until a fresh current-head run executes.**

No current-head aggregate PASS, language-selector physical PASS, system-update activation/rollback PASS, current-head QEMU A/B PASS or Pi A/B PASS is claimed.

Retained physical evidence from 2026-08-19: a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer booted on the reference Acer Aspire One, installation completed, and the installed OS reached the launcher. Later source—including the new language-first installer—requires a rebuilt image before that physical claim extends to it.

---

# 3. 2026-08-19 — Device-default language selection and persistence

Architecture authority remains:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
```

Product/implementation synthesis:

```text
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
```

## 3.1 Core rule

Greia has one device-default UI locale. It is selected during installation and can later be changed from either Parent-management surface.

```text
installer first-screen choice
        ↓
InstallRequest.locale
        ↓
/etc/greia-os/install-record.json   (historical initial choice)
        ↓
current device default
        ↑
/var/lib/greia-system-settings/language.json   (later Parent override)
```

Effective value precedence:

```text
valid language.json override
        ↓ otherwise
valid install-record locale
        ↓ otherwise
English
```

A later Parent change does not rewrite the historical install record.

## 3.2 Canonical selectable-language registry

Exact source owner:

```text
src/greia_platform/system_language.py
```

Initial registry:

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

There must be no installer-only or browser-only copy of this list. The installer and hidden panel import it directly; the Parent browser receives it from Greia through the API.

Flags are presentation cues, not geographic/citizenship authority.

## 3.3 Installer — language is now the first interaction

New entry point:

```text
src/greia_installer/entrypoint.py
```

Installed live service now launches:

```text
python3 -m greia_installer.entrypoint
```

rather than starting `greia_installer.main` directly.

The new entry point adds only a mandatory flag-first language chooser in front of the existing installer. It does **not** duplicate disk-selection, hardware, Wi-Fi or installation-engine logic.

The selector:

- is the first visible interactive installer screen;
- uses the canonical registry;
- defaults to English;
- supports pointer and keyboard navigation;
- reflows between three/two columns according to viewport;
- uses Greia typography/emoji rendering for flags;
- passes the selected locale into the real `InstallRequest`.

`src/greia_installer/engine.py` already writes `InstallRequest.locale` into the installed `install-record.json`; the previously missing UI binding is now present.

## 3.4 Parent API

Canonical semantic route:

```text
GET /api/v1/settings/language
PUT /api/v1/settings/language
settings.language
```

Implementation:

```text
src/greia_parent/protocol.py
src/greia_parent/update_api.py
```

GET returns current locale, selected-language metadata and the canonical language registry. PUT accepts only a supported locale and atomically persists the device override.

The Parent service remains unprivileged `greiapanel`; this is a typed settings mutation, not a generic shell/filesystem API.

## 3.5 Greia Parents HTML app

Greia pins runtime revision:

```text
frozenpepper/Greia-Parent-App-Html@519651a5931269ed4275324f2a87ad3f0d08a3f6
```

with exact per-file integrity in:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

New/changed client source:

```text
src/api.js
src/language_ui.js
index.html
```

The Settings page adds a capability-driven full-width Greia Language card. The browser requests the language rows from Greia and therefore has no independent hard-coded registry. It displays flag + simple name + native name when available and PUTs only the selected locale.

Focused Parent client test:

```text
tests/language_api.test.js
```

The async invalid-locale assertion was corrected in the pinned revision. No `npm test` run is claimed in this connector session.

## 3.6 Hidden on-device Parent Settings

Source:

```text
src/greia_launcher/parent_panel.py
```

The authenticated hidden Parent Settings panel now opens on **Language** as its first tab, ahead of Wi-Fi, SSH Maintenance and Remote/Pairing.

The panel uses the same canonical registry and highlights the current device locale. Pointer/keyboard selection applies the language immediately.

The child launcher account is **not** granted general write access to system settings. It uses a narrow root helper:

```text
build/overlay/usr/local/lib/greia-os/greia-languagectl
build/overlay/etc/sudoers.d/greia-language
```

The only authorized operation is conceptually:

```text
set <supported-locale>
```

The helper validates the locale against the product registry and exposes no generic shell/filesystem operation.

`/var/lib/greia-system-settings` is already a setgid `pipsettings` directory and both `greiapanel` and `greiakid` are members of that group. The language state is mode `0660`, so changes made via the root helper remain writable by the Parent daemon and vice versa.

## 3.7 Activity inheritance

`src/greia_platform/activity_api.py::get_profile_locale()` now resolves:

1. explicit profile override when supplied by Greia;
2. explicit device locale launch context when supplied;
3. otherwise the current `SystemLanguageStore` value.

This preserves ADR 0028's chain:

```text
device default → optional child override → Activity supported-locale fallback
```

An English-only Activity remains valid on an Italian/Hindi/etc. device and falls back to a language it actually ships.

## 3.8 Critical evidence distinction

**Selectable does not mean fully translated.**

The current tranche implements language selection, persistence, API/client control and locale propagation. It does **not** prove that every Greia surface/Activity has translations, glyph coverage, shaping or RTL layout for all twelve selectable locales.

In particular:

- Chinese/Arabic/Hindi/Bengali require a reviewed platform script-font/fallback strategy beyond normal Nunito coverage;
- Arabic requires real RTL shaping/layout/input acceptance;
- installer/launcher/Parent string catalogues still need systematic translation work;
- individual Activities advertise/fallback according to the translations they actually ship.

Do not describe Greia as “fully translated into 12 languages” until that separate work is complete and evidenced.

## 3.9 Language focused regressions

Greia source:

```text
tests/test_system_language.py
```

covers:

- exact canonical product registry and required locale set;
- `zh` → `zh-CN` canonicalization;
- install-record bootstrap followed by state override;
- malformed-state safe fallback;
- Activity API inheritance;
- Parent resource/capability and read/update behavior;
- first-screen installer entry-point contract;
- narrow sudo helper contract;
- runtime helper executable-mode tmpfiles contract.

These tests are committed but **not executed in this connector session**.

---

# 4. Transactional Greia system-update foundation

Architecture/product/operator docs:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Implemented: signed `.greiaupdate` schema, Ed25519 trust helpers, compatibility metadata, bounded/single-copy Parent upload inbox, release CLI and Parent update status/upload UI.

Current x86 profiles remain `bios-single-ext4`; therefore:

```text
system.update.activate = false
A/B staging             = not implemented
boot confirmation       = not implemented
automatic rollback      = not implemented
```

No in-place active-root fallback is authorized.

Next R13B work is still A/B backend/layout measurement/design (RAUC vs minimal Greia backend), canonical slot-payload build, trusted-key provisioning, inactive-slot writer, boot-attempt/health confirmation and rollback evidence.

---

# 5. R7 / display / input

R7 remains the primary blocking platform phase.

Current production path remains provisional **Xorg/xinit**; no compositor is selected. `DisplaySessionCoordinator`, ADR 0019 trusted Home/Back and ADR 0020 platform-owned input/controller semantics remain the mandatory architecture boundary.

Do not deepen X11 or grant Activities raw DRM/input authority as a shortcut for unrelated UI/localization work.

---

# 6. Boot / installer / Acer facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is **syslinux/FAT32**, not GRUB-MBR USB.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed target initramfs uses target-kernel-aware storage policy; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- The earlier 2026-08-19 Acer install/launcher PASS predates the language-first installer and must not be reused as language-selector physical evidence.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 7. Exact verification sequence now

On an owner-controlled current Linux checkout, resolve and record the exact current `main` SHA first. Preserve the first failure.

### A. Device-language focused gate

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_language \
  tests.test_parent_api \
  tests.test_installer_engine -v
```

### B. Existing later-tranche focused gates

Run the relevant system-update, emoji/Writing and simulator focused suites named in their docs/HANDOVER history.

### C. Complete source gate

```bash
make verify
```

### D. External Parent client

At Greia's pinned runtime revision or a later revision containing the same runtime source plus docs:

```bash
npm test
```

### E. Physical installer/language acceptance

Rebuild the current legacy developer installer and verify on the Acer/reference viewport:

1. language chooser is the first interactive screen;
2. all twelve choices/flags are visible, legible and reachable;
3. choose Italian, complete install, reboot, confirm device default is Italian;
4. change to another locale in Greia Parents, reboot, confirm persistence;
5. change again through hidden Parent Settings and confirm Parents sees the same current value;
6. launch a language-aware Activity and confirm inherited locale/fallback behavior;
7. selecting `ar`, `zh-CN`, `hi` or `bn` never crashes even where complete translation/font acceptance remains pending.

No PASS is claimed for this sequence yet.

---

# 8. Immediate continuation priorities

1. Run `tests.test_system_language` and the relevant Parent/installer suites on owner-controlled current `main`.
2. Run current `make verify`; preserve first failure and record exact SHA.
3. Run Parent HTML `npm test` at the reviewed language-enabled revision.
4. Rebuild current installer and physically verify the language-first flow + install transfer on Acer.
5. Continue R7 as the first blocking architecture phase.
6. Start the separate localization-content tranche: platform string catalogues, script-font coverage, shaping/RTL and responsive translated-text acceptance—without conflating it with the now-implemented selector/persistence.
7. Continue R13B backend work only after its existing measurements/prerequisites.

---

# 9. Non-negotiable continuation rules

- `main` only unless owner changes branch policy;
- GitHub is canonical source truth;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- no visible Linux UI during normal child use;
- one canonical device-language registry; no browser/installer forks;
- installer language choice transfers through the real `InstallRequest` into installed Greia state;
- Parent language changes use typed Greia APIs/services, never shell/locale-file shortcuts;
- language selection is not a claim of translation/font/RTL completion;
- Activity fallback remains honest to the translations each Activity actually supplies;
- R7 remains open and Xorg/xinit provisional;
- trusted Home/Back remain outside Activity authority;
- ordinary Activities do not gain raw `/dev/input` or DRM authority;
- current single-root profiles keep system-update activation false;
- source/build/VM/physical evidence scopes remain explicit and honest.

Resolve the exact current `main` SHA before every owner-controlled verification/build run and record that SHA with the returned evidence.
