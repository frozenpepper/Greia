# Review — Greia skill progressive-disclosure architecture

**Date:** 2026-08-24  
**Scope:** contributor skill/document routing only  
**Runtime implementation changed:** no  
**Platform phase closed:** no

## Problem

Greia's top-level skill files had grown into large always-loaded manuals. This made unrelated context unavoidable, duplicated canonical project documentation, and allowed critical task-specific requirements to become buried inside tens of kilobytes of prose.

Observed pre-correction sizes were approximately:

```text
skills/greia-activity-authoring/SKILL.md   ~21 KB
skills/greia-os-work/SKILL.md              ~34 KB
skills/greia-visual-authoring/SKILL.md      ~14.6 KB
```

The Activity skill also had a ~49 KB `CORE.md`; that broad synthesis remains available but is no longer mandatory first reading for ordinary Activity work.

## Accepted structure

All Greia top-level skills now follow progressive disclosure:

```text
SKILL.md
    small router
    universal non-negotiable rules
    task -> local companion / canonical docs / exact source owner
    concise completion/evidence check

specialist companion or canonical project doc
    detailed procedure / architecture / examples / acceptance protocol
```

Shared convention:

```text
skills/README.md
```

## Current router sizes after correction

Approximate current sizes at the time of this review:

```text
skills/greia-activity-authoring/SKILL.md   ~7.5 KB
skills/greia-os-work/SKILL.md              ~8.9 KB
skills/greia-visual-authoring/SKILL.md      ~8.2 KB
```

Detailed specialist files remain deliberately larger where justified because they are loaded only for the relevant task. Examples:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/REFACTORING.md
skills/greia-os-work/BOOT.md
```

Existing canonical ADR/design/product/engineering/testing docs should be linked directly instead of copied into another companion whenever they already own the subject.

## Important Activity rule retained

The Activity router keeps the hard final-source Simulator launch rule visible at top level while routing the detailed procedure to:

```text
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
```

This prevents `ImportError`, startup exception, immediate exit, dead first frame or first-interaction crash from being hidden behind passing source tests.

## Important OS rule retained

Boot/recovery work routes immediately to:

```text
skills/greia-os-work/BOOT.md
```

so recovered Acer safety, developer SSH continuity, GRUB/initramfs change scope and pre-reboot validation are task-specific mandatory context rather than diluted inside a general OS manual.

## Important visual rule retained

Visual work routes directly to the relevant visual architecture/style/library/scene/evidence documents. Activity visual changes that affect runtime assets/code also route through the Activity skill and launch acceptance gate.

## Maintenance rule

Future contributors should not grow `SKILL.md` into a second encyclopedia. When new guidance is needed:

1. update the canonical owner first;
2. add/update a focused companion only if no existing document cleanly owns the practical procedure;
3. change `SKILL.md` only to add/adjust routing or a truly universal rule;
4. remove duplicated prose rather than copying specialist detail into the router.
