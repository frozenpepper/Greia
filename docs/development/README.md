# Greia Developer Manuals

**Status:** living navigation index  
**Reviewed:** 2026-10-26

This directory contains practical developer/operator manuals below Greia's accepted architecture and source-owned implementation contracts.

For documentation authority and precedence, read `docs/DOCUMENTATION.md` first.

## Historical Acer recovery lesson (not the current release gate)

A 2026-08-20 boot-polish change regressed a then-working Acer installer into
a grey-screen/reboot loop. The reviews below preserve useful hardware
lessons. **Do not treat this old incident as the current Acer/A-B test order**:
read `HANDOVER.md` and `docs/testing/LOCAL_AGENT_START_HERE.md` for the
present candidate, exact source state and accepted procedure before touching
bootloaders, boot artwork or USB writers. Historical reading:

```text
docs/archive/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md
```

The current recovery rule is deliberately conservative: the proven Syslinux/FAT32 writer and observable `console=tty1` development boot are restored; final-media integrity checking lives in the separate read-only `tools/verify-live-usb.sh`. Do not reintroduce the rejected Syslinux clear-screen/`console=null` or raw-full-colour boot-art experiments before a new physical acceptance pass.

## Current manuals

### Developer boot diagnostics

`GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md`

Read this when a development Greia image reaches the installed root filesystem but does not reach the child launcher, or when SSH is needed to diagnose a graphical boot failure. It explains:

- why a persistent `PIP_ROOT: clean ...` line does not prove that boot stopped at filesystem checking;
- the simple development SSH contract for both live installer and installed OS;
- the `greia-installer.local` and `greia-dev.local` network/SSH probe paths;
- the fail-closed `tools/build-development-installer.sh` build wrapper;
- artifact-level verification through `tools/verify-development-installer.sh`;
- the development-only machine-local Ed25519 host identity bootstrap;
- the exact systemd/journal/Xorg evidence to capture before changing services;
- the current provisional launcher/Xorg chain;
- how to reason about older images that predate the hardened SSH bootstrap.

For present physical Acer/update acceptance, the **current** handover and
release/install lifecycle plan own the execution boundary. The August review
remains a cautionary case study, not a standing instruction to flash its image.

Historical Acer root-mount/service failures remain documented in `docs/INSTALLED_OS_BOOT_POSTMORTEM.md`.

### Lightweight application update packages

`GREIA_SOFTWARE_UPDATE_PACKAGES.md`

Read this for typed `.greia_update` Python, Activity, combined and full-system
packages, the exact source builder commands, Parent `Upload & install`,
durable status and the bootstrap boundary. Device acceptance is separate and
owned by `../testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`.

### System update release workflow

`GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`

Read this when creating or inspecting an unsigned v3 `.greiaupdate` full-system
candidate for the existing A/B writer. For Python/Activity package types and
Parent upload, use `GREIA_SOFTWARE_UPDATE_PACKAGES.md`. It gives the concise
operator path for:

- deriving target identity from a canonical Greia build profile;
- building the real ext4 slot payload from the composed target root;
- verifying the payload read-only before bundling;
- building one unsigned `.greiaupdate` v3 bundle;
- inspecting the bundle locally before distribution;
- streaming the bundle to a development Greia through the Parent API;
- reading update status;
- understanding why upload is not activation authority;
- the current single-root/A-B implementation boundary and next R13B step.

Normative architecture is ADR 0030 and product behavior is `docs/product/SYSTEM_UPDATES.md`. Exact implementation is owned by:

```text
src/greia_platform/system_updates.py
src/greia_parent/update_api.py
tools/greia_update.py
```

### Activity text, typography and emoji

`GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md`

Read this before implementing or reviewing a Python/Pygame Activity that displays significant text, accepts child-authored text, lays out mixed text + emoji, or provides emoji input.

It explains the current Activity-facing contract for:

- `GreiaTypography` and semantic `FontRole` usage;
- Nunito Sans + Noto Color Emoji fallback;
- Unicode extended grapheme clusters;
- grapheme-safe cursor movement, deletion, wrapping, hit testing and truncation;
- standard UTF-8 persistence;
- the bounded `EmojiPalette` picker model;
- the distinction between expressive emoji and trusted Greia semantic icons;
- low-resource/cache/lifecycle requirements;
- current limitations and focused tests.

Exact implementation remains owned by:

```text
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
```

The first-party reference consumer is:

```text
activities/writing/main.py
```

### Activity Simulator

`GREIA_ACTIVITY_SIMULATOR.md`

Read this when using the desktop Greia Activity Simulator. It explains the canonical-runtime composition boundary, synthetic HAL facts, source/package loading, evidence limitations and operator workflow.

Normative architecture is ADR 0029; exact implementation lives under `src/greia_simulator/` and canonical launcher/platform services.

### Add or maintain a Greia language

Use [`ADD_A_GREIA_LANGUAGE.md`](ADD_A_GREIA_LANGUAGE.md) for the complete
manifest + UI/Activity JSON/TOML workflow, working with an unfinished locale
without offering it, voice production and Parakeet verification, and updating,
switching or retiring existing languages. Agents start with
[`skills/greia-language-expansion/SKILL.md`](../../skills/greia-language-expansion/SKILL.md).
The currently offered four locales (EN/IT/ES/FR) are just the manifests that
ship today; adding an ordinary new language does not require changing a
Python selector registry. The separately managed browser Parents App still
needs its own browser-chrome translation resources and integration.

## Documentation check before release

Run `python3 tools/audit_repository_docs.py --scope maintained` from the repo root to check Markdown links throughout current manuals, skills and developer/user guides. The tool reports historical broken links separately; it is read-only and does not replace tests, voice listening or release-image evidence.

## Activity-authoring entry point

The living practical Activity guide remains:

```text
skills/greia-activity-authoring/SKILL.md
```

For typography/emoji work, use that skill together with `GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md`. Do not treat chat history as the contract.
