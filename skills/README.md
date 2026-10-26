# Greia contributor skill architecture

**Status:** repository convention  
**Reviewed:** 2026-10-26

Greia skills use **progressive disclosure**.

## Rule

A top-level `skills/<skill>/SKILL.md` is a **small task router**, not a complete manual.

It should contain only:

- the skill's scope;
- a small set of universal non-negotiable rules;
- a task-to-local-document/source map;
- a short completion/evidence checklist.

Detailed architecture, procedures, examples, postmortems, testing protocols and specialist rules belong in:

```text
skills/<skill>/<TASK>.md
```

or in the existing canonical repository documents under:

```text
docs/adr/
docs/architecture/
docs/design/
docs/product/
docs/engineering/
docs/development/
docs/testing/
docs/agents/
```

Exact implemented contracts remain source-owned where appropriate.

## Why

Agents should load the smallest context needed for the actual task. Huge always-read skill files:

- waste context;
- mix unrelated subsystems;
- make critical instructions easy to miss;
- duplicate canonical docs and become stale;
- encourage agents to treat derived prose as architecture authority.

The router should therefore say **what to read**, not re-explain everything those documents already own.

## Progressive-disclosure pattern

Example:

```text
user asks to change Activity imports
    -> skills/greia-activity-authoring/SKILL.md
    -> ENGINEERING.md
    -> LAUNCH_ACCEPTANCE.md
    -> runtime_adapter.py / child-runtime.toml as exact source authority

user asks to add child voice recording to an Activity
    -> skills/greia-activity-authoring/SKILL.md
    -> MICROPHONE_RECORDING.md
    -> ADR 0031 / GREIA_AUDIO_SERVICE.md / activity_api.py as exact authority

user asks to change the Greia microphone processing platform
    -> skills/greia-os-work/SKILL.md
    -> ADR 0031 / GREIA_AUDIO_SERVICE.md
    -> physical microphone acceptance evidence when hardware claims are involved

user asks to work on boot
    -> skills/greia-os-work/SKILL.md
    -> BOOT.md
    -> current boot design/postmortem/source files

user asks to create a canonical character pose
    -> skills/greia-visual-authoring/SKILL.md
    -> canonical-cast / character-grammar / motion docs

user asks to add, translate, stage, switch or retire a Greia language
    -> skills/greia-language-expansion/SKILL.md
    -> docs/development/ADD_A_GREIA_LANGUAGE.md
    -> per-locale manifests, UI JSON, Activity bundles and the shared voice skill

user asks to record new character dialogue or language narration
    -> skills/greia-voice-production/SKILL.md
    -> docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
    -> canonical v0.3 masters, VoxStage/VoxCPM2 and Parakeet verifier
```

Do not load unrelated voice-generation, boot, achievement, packaging, visual-library, Parent or simulator manuals merely because they exist in the same project. In particular, generated Greia character speech and child microphone recording are separate task routes.

## When to create a new companion document

Create a focused local companion such as `BOOT.md`, `LAUNCH_ACCEPTANCE.md` or `MICROPHONE_RECORDING.md` when:

- the procedure is important enough to be reused;
- several tasks need the same operational guidance;
- the instructions are too detailed for the router;
- no existing canonical project document cleanly owns the practical procedure.

Do **not** create another companion when an accepted ADR/product/engineering/testing document already owns the subject well. Link to that existing local path instead.

## Maintenance rule

When contributor guidance changes:

1. update the canonical source/ADR/product document that owns the fact first;
2. update the task-specific companion if its practical procedure changed;
3. update `SKILL.md` only when routing/universal rules changed;
4. remove duplicated explanatory prose from the router rather than copying new detail into it.

Current top-level routers:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-os-work/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-language-expansion/SKILL.md
skills/greia-voice-production/SKILL.md
```

All future Greia skills should follow the same pattern.
