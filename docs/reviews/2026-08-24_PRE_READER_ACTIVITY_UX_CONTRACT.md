# Pre-Reader Activity UX Contract — Review Record

**Date:** 2026-08-24  
**Status:** accepted authoring/product clarification

## Problem

Greia Activity guidance contained pre-reader principles in broad documentation, but they were not prominent enough in the task router or completion gate. This allowed technically working Activities to rely on written instructions even though many target children cannot read.

## Resolution

The following is now a first-class Greia Activity invariant:

> A target child who cannot read must still be able to understand the next meaningful action, act, recover from mistakes, and continue.

Core gameplay instructions may not depend on written prose or button labels.

Preferred communication is:

```text
clear visual hierarchy
+ large icons/pictures/shapes/numbers
+ short visual demonstration/motion
+ reviewed spoken cues when language is useful
+ immediate visual/audio feedback
```

Text remains secondary support.

## Authorities changed

- `skills/greia-activity-authoring/SKILL.md`
  - pre-reader behavior is now a universal rule;
  - every new Activity routes through the focused pre-reader companion;
  - UI/completion work routes through it when child-facing flow changes;
  - completion checklist rejects text-dependent core instructions.

- `skills/greia-activity-authoring/PRE_READER_UX.md`
  - new focused companion owning practical design and no-reading acceptance rules.

- `skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md`
  - new/child-facing Simulator acceptance now includes a no-reading pass and evidence fields.

- `docs/product/ACTIVITY_INPUT_STANDARDS.md`
  - promoted the same rule to accepted product requirement so it is not merely an agent convention.

## Important exception

Reading/literacy Activities may use written language as the learning content. They are **not** exempt from pre-reader operating instructions: how to select, replay, retry, continue, or understand the task must still be communicated without requiring reading.

## Evidence boundary

This tranche changes documentation/authoring acceptance contracts only. It does not claim that every existing first-party Activity has already passed the newly explicit no-reading UX audit. Existing Activities should be reviewed against the contract as they are materially changed or in a dedicated portfolio audit.