# Greia Encyclopedia — authoring root

**Status:** active multi-session authoring/research/voice workspace  
**Created:** 2026-08-27  
**Runtime Activity:** `activities/enciclopedia_greia/` (`org.greia.enciclopedia`)  
**Current evidence:** SOURCE-VERIFIED / SIMULATOR-UNVERIFIED

This directory is the long-lived authoring source of truth for the Greia Encyclopedia workstream. Runtime code lives in the normal first-party Activity package; this root owns the detailed plan, planned 43-page catalogue, research/voice coordination and append-only implementation progress.

## Read order for encyclopedia work

1. repository-root `AGENTS.md`;
2. repository-root `README.md`;
3. `skills/greia-activity-authoring/SKILL.md`;
4. task-specific Activity skill companions required by that router;
5. `skills/greia-visual-authoring/SKILL.md` when creating/integrating visual assets;
6. `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` for voice identity;
7. `docs/adr/0028-platform-and-activity-localization-language-context.md`;
8. `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`;
9. `PLAN.md`;
10. `PROGRESS.md`;
11. `VOICE_RECORDING_REQUESTS.md`;
12. `HANDOVER.md`;
13. runtime `activities/enciclopedia_greia/` source relevant to the current page.

The repository's active architecture-remediation plan remains authoritative and blocking for platform work. The encyclopedia is a subordinate Activity workstream and may not weaken or bypass platform authority.

## Core product idea

The encyclopedia is **one normal first-party Greia Activity**. Inside that Activity is a deliberately tiny page engine.

The engine does not try to express all content declaratively. Each section or final entry may be its own Python page module and may behave differently:

- planets can orbit;
- a volcano can erupt;
- a heart can beat;
- gears can turn;
- a frog can change from tadpole to adult;
- a fossil can be uncovered;
- a section can simply be a beautiful tappable scene.

Greia still owns trusted Home/lifecycle/input/localization/profile/package authority. The encyclopedia does **not** become a second OS.

## Hard runtime boundaries

The child device must not require:

- speech recognition;
- runtime TTS;
- a voice model;
- a language model;
- network access;
- factual content generation;
- heavy physics;
- a browser/web runtime.

All presenter narration is prerecorded during authoring. Dani/system TTS and pronunciation-critical pedagogical speech are also generated ahead of time on parent/development hardware and packaged as ordinary audio assets.

The extreme reference remains first-generation Acer Aspire One-class hardware. Animation therefore uses simple sprites/shapes, cached surfaces, bounded particles and lightweight math.

## Runtime/authoring split

```text
encyclopedia/
    PLAN.md                       # detailed architecture/content/sequencing authority
    PROGRESS.md                   # append-only implementation ledger
    VOICE_RECORDING_REQUESTS.md   # one independent bilingual recording queue
    HANDOVER.md                   # exact continuation state
    pages/catalogue.py            # complete planned v0.1 43-page inventory

activities/enciclopedia_greia/
    activity.toml
    main.py                       # thin composition root
    enciclopedia_app.py           # Activity lifecycle/input composition
    enciclopedia_engine.py        # tiny page lifecycle/navigation contract
    enciclopedia_audio.py         # prerecorded semantic audio playback
    enciclopedia_services.py      # bounded shared presentation services
    enciclopedia_catalogue.py     # implemented-page registry only
    pages/                        # executable section/entry modules
    locales/                      # runtime localization bundles
```

Do not create dozens of empty runtime page modules merely to make the implementation look complete. Add a runtime page only when it has real behavior.

## Current first-pass testing rule

At owner direction, the initial encyclopedia construction pass is **source-first**. Do not stop after every page/phase to run Simulator acceptance. Build a coherent base and then perform one consolidated Simulator/interaction/visual pass.

This does **not** waive Greia's final Activity acceptance contract. Until that later pass executes against the final runtime-relevant state, report the Activity as:

```text
SOURCE-VERIFIED / SIMULATOR-UNVERIFIED
```

Never call it Simulator-accepted or hardware-accepted before those gates actually run.

## Voice-production coordination

`VOICE_RECORDING_REQUESTS.md` is the single coordination queue between encyclopedia implementation and the independent local voice-production agent. Existing requested rows remain stable while the recording agent works; implementation must not silently rewrite recorded wording.
