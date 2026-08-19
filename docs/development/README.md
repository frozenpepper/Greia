# Greia Developer Manuals

**Status:** living navigation index  
**Date:** 2026-08-19

This directory contains practical developer/operator manuals below Greia's accepted architecture and source-owned implementation contracts.

For documentation authority and precedence, read `docs/DOCUMENTATION.md` first.

## Current manuals

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
