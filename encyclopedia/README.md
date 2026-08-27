# Greia Encyclopedia — authoring root

**Status:** design/foundation workspace; not yet registered as a Greia Activity  
**Created:** 2026-08-27  
**Owner intent:** build a small, visual, spoken, interactive children's encyclopedia for Greia over multiple sessions.

This directory is the working source of truth for the Greia Encyclopedia workstream.

## Read order for encyclopedia work

1. repository-root `AGENTS.md`;
2. repository-root `README.md`;
3. `skills/greia-activity-authoring/SKILL.md`;
4. `skills/greia-activity-authoring/ENGINEERING.md`;
5. `skills/greia-activity-authoring/PRE_READER_UX.md`;
6. `skills/greia-activity-authoring/PRESENTERS_AND_CURIOSITY.md`;
7. `skills/greia-activity-authoring/VOICE_GENERATION.md`;
8. `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`;
9. `docs/adr/0028-platform-and-activity-localization-language-context.md`;
10. `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`;
11. this directory's `PLAN.md`;
12. this directory's `VOICE_RECORDING_REQUESTS.md`;
13. this directory's `HANDOVER.md`.

The repository's active architecture-remediation plan remains authoritative and blocking. This encyclopedia plan is a subordinate feature workstream and must not be used to bypass platform prerequisites.

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

Greia still owns trusted Home/Back, lifecycle, input policy, localization context, profile state, package trust and other platform authority. The encyclopedia does **not** become a second OS.

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

All presenter narration is prerecorded during authoring. Dani speech and pronunciation-critical pedagogical speech are also generated ahead of time on the parent/development device and packaged as ordinary audio assets.

The extreme reference remains first-generation Acer Aspire One-class hardware. Animation therefore uses simple sprites, cached surfaces, bounded particles and lightweight math.

## Directory status

`engine/` contains only the first small internal contracts needed to anchor future work. It is intentionally not wired into the Greia Activity registry yet; integration happens in PLAN Phase E1 after the final Activity package shape is implemented and can be validated as a whole.

`pages/` is populated gradually. Do not create dozens of empty placeholder page scripts merely to make the tree look complete.

`VOICE_RECORDING_REQUESTS.md` is the single coordination queue between encyclopedia implementation and the independent local voice-production agent.

Provider-free foundation smoke check:

```bash
PYTHONPATH=. python3 encyclopedia/smoke_test.py
```
