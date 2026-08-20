# Greia Developer Manuals

**Status:** living navigation index  
**Date:** 2026-08-20

This directory contains practical developer/operator manuals below Greia's accepted architecture and source-owned implementation contracts.

For documentation authority and precedence, read `docs/DOCUMENTATION.md` first.

## Current manuals

### Developer boot diagnostics

`GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md`

Read this when a development Greia image reaches the installed root filesystem but does not reach the child launcher, or when SSH is needed to diagnose a graphical boot failure. It explains:

- why a persistent `PIP_ROOT: clean ...` line does not prove that boot stopped at filesystem checking;
- the `greia-dev.local` network/SSH probe path;
- the development-only SSH host-key bootstrap and authentication contract;
- the exact systemd/journal/Xorg evidence to capture before changing services;
- the current provisional launcher/Xorg chain;
- how to reason about older images that predate the SSH bootstrap.

Historical Acer root-mount/service failures remain documented in `docs/INSTALLED_OS_BOOT_POSTMORTEM.md`.

### System update release workflow

`GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`

Read this when creating, inspecting or pushing a `.greiaupdate` release candidate. It gives the concise operator path for:

- one-time Ed25519 release key generation;
- deriving target identity from a canonical Greia build profile;
- building one signed `.greiaupdate` bundle;
- local signature verification;
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

## Activity-authoring entry point

The living practical Activity guide remains:

```text
skills/greia-activity-authoring/SKILL.md
```

For typography/emoji work, use that skill together with `GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md`. Do not treat chat history as the contract.
