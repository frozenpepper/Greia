# Greia Canonical Character Voice Registry v0.1

**HISTORICAL — superseded for new production on 2026-10-19 by v0.2, then v0.3 on 2026-10-21.** The active canonical manifest is `assets/audio/characters/canonical/v0.3/manifest.toml`. These earlier bytes are retained for historical recordings/provenance; new generation does not load this registry.

This directory owns the reviewed **production-anchor registry** used by the local Activity voice-generation workflow.

The binary FLAC anchors are canonical private-project repository assets and belong in this directory beside `manifest.toml`. They are not ordinary Activity playback assets and must not be copied into every `.greiaactivity` package.

A fresh authorized checkout is not voice-production ready when the registered FLAC files are absent. Do not replace that missing state with an undocumented side pack or silently regenerate different references. Restore the exact reviewed bytes and verify them against `manifest.toml`.

## Registry

```text
greia.lilli.v1 → lilli-reference-v1.flac
greia.leo.v1   → leo-reference-v1.flac
greia.flash.v1 → flash-reference-v1.flac
greia.tito.v1  → tito-reference-v1.flac
greia.momo.v1  → momo-reference-v1.flac
```

Dani deliberately has no cloning anchor:

```text
greia.dani.system-v1 → Greia OS text-to-speech policy
```

The current designed Dani candidates did not sound clearly robotic. A generic natural clone would weaken the character identity, so system TTS is the accepted v0.1 route.

## Source masters and derivation

The full owner-supplied WAV source recordings belong at:

```text
assets/source/audio/character-voice-masters/v0.1/
```

Each production anchor in this directory is a deterministic, lossless FLAC export of the first 12.000 seconds of its source master:

```text
mono · 24,000 Hz · 16-bit PCM content · FLAC
```

This keeps voice cloning efficient while preserving the full recording separately for provenance and future anchor review.

Exact source and anchor metadata and SHA-256 values are in `manifest.toml`.

Do not modify source masters or production anchors in place. Any replacement or newly selected excerpt requires a new version, explicit provenance and human review.

## Use

Read:

```text
SETUP.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Keep model weights, caches, environments and generated scratch output outside this directory.

## Provenance and release status

The project owner supplied the source recordings as synthetically generated character-voice candidates. No real-person cloning is intended.

They are accepted for the current private Greia project workflow. Before public redistribution, record the final asset-license decision in the project's governance/licensing authority rather than inventing a license here. Public-release licensing uncertainty does not require omitting the canonical bytes from the current private repository.
