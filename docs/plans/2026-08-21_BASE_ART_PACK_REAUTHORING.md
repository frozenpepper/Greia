# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION / AUTHORING-TOOLING / CANONICAL-CHARACTER TRACK  
**Date:** 2026-08-22  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Character motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent, where useful, to improve Greia's bundled **generic visual toolbox**, authoring-time discoverability, and the separate canonical character family.

The maintainer agent's drawing ability is not a Greia dependency and is not evidence about arbitrary future Activity-authoring agents.

The user/developer-facing workflow remains owned by:

`skills/greia-visual-authoring/SKILL.md`

## 2. Authoring architecture

Do not organize toolbox work primarily as themed packs such as Clinic, Classroom, Fantasy Village, or Pond.

Theme/source bundles are provenance pools. The primary authoring interface is the generic semantic library:

1. Nature & Landscape
2. Interiors & Architecture
3. Furniture & Storage
4. Everyday Props & Containers
5. Making, Learning & Play
6. Lighting, Atmosphere, FX & Shadows
7. Shared UI
8. Canonical Characters

Canonical Characters are intentionally **separate** from the six generic object/environment collections because identity consistency matters more than open-ended semantic interchangeability.

Authority:

`docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`

## 3. Established source pools

### Forest / Meadow v0.3

Promoted source pool with 28 semantic roles: 23 reauthored roles + 5 retained legacy roles + 2 preferred ingredients.

### Workshop v0.2

Promoted source pool with 24 finished semantic assets: 14 direct reauthored replacements + 5 retained baseline variants + 5 candidate coexistence variants + 2 preferred ingredients.

### Clinic / Care candidate

Useful reviewed source pool. It is **not** a core generic pack. Generic furniture/interior/comfort/container assets are harvested by reference; strongly medical props remain specialized.

### Reading / Classroom, Fantasy / Village / Night, Water / Pond

These remain source/provenance pools. Their generic assets have been harvested/classified rather than treated as required theme packs.

## 4. Generic library consolidation and full source harvest

Commit `cc1d7f1` created the first six semantic indexes under:

`assets/visual/authoring_library/`

Commit `2dcf306` completed the full source harvest across Reading/Classroom, Fantasy/Village/Night and Water/Pond.

Harvest state before Batch A admission:

```text
52 preferred finished assets
32 candidate-reference finished assets
5 authoring ingredients
89 total indexed reusable resources
```

Owner review:

`docs/reviews/visual/2026-08-21_generic-authoring-library-full-source-harvest/PRIMARY_REVIEW.md`

## 5. Accepted gap model

Every coverage question must distinguish:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

An existing weak asset is a quality gap, not missing inventory.

## 6. Permanent composability rule

The generic library must not become an encyclopedia of arbitrary pre-finished clip-art nouns.

> **Generic assets should encode reusable form; Activity-specific meaning and contents should remain separable whenever practical.**

Examples:

- empty plate/bowl rather than food permanently baked in;
- books without readable titles or one fixed story;
- blank signs/boards where Activity/localization owns text;
- reusable gear/dial/lever components rather than one narrowly themed machine;
- source-level ingredients only when they genuinely improve authoring leverage.

Runtime remains economical: rich source work may be flattened into efficient runtime assets.

## 7. Generic authoring-library admission state

The semantic index structure is canonical. Individual resources expose:

```text
preferred
candidate_reference
```

- `preferred` → strong enough to consider first for direct REUSE.
- `candidate_reference` → useful for COMPOSE/ADAPT/reference, but not owner-approved first-choice direct-use art.

The purpose of these states is to avoid endless redraw loops merely to force every useful source into `preferred`.

## 8. Generic Core Essentials Batch A — reviewed and admitted

Candidate commit:

`574f19530ee292a81225ff14c09ad8b35f6cf933`

Primary review:

`docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`

Owner disposition:

```text
9 finished assets → preferred
7 finished assets → candidate_reference
2 authoring ingredients → preferred
```

Admission/discovery implementation commit:

`de37aad978c57b3de88a64ffb1f6cf70c5a89c5b`

Current generic indexes contain:

```text
57 preferred finished assets
37 candidate-reference finished assets
7 preferred authoring ingredients
101 indexed reusable visual resources
```

Discovery helper:

`tools/visual_authoring_library.py`

Focused tests:

`tests/test_visual_authoring_library.py`

No Batch B is authorized merely to increase asset count.

## 9. Why Canonical Characters are now a justified maintainer-side art gate

The generic-object toolbox has reached useful breadth and now has discovery tooling. A separate, high-value weakness remains: Greia's recurring canonical cast is still only partially productized.

Current repository facts:

- A1 neutral characters live under `assets/visual/specimens/a1/` as accepted **style anchors**, not frozen release art;
- `assets/visual/library/catalog.toml` still describes the shared character library as `candidate` and `runtime_consumed = false`;
- each of Lilli, Nino, Tito and Momo currently has only a separately authored `blink.svg` under `assets/visual/characters/<name>/`;
- the design vocabulary already names `neutral`, `blink`, `happy`, `surprised`, and `sleepy` states plus six shared motions;
- only Lilli currently has a narrow `default`/`blink` runtime rendition in `assets/catalog/shared_visuals_v1_source.toml`;
- `SceneActorDefinition` currently implements cheap whole-character idle + blink rather than a detailed rig.

This makes canonical character production a much more justified next maintainer-art task than another generic prop batch.

## 10. Exact current character-art gate

Execute:

`docs/testing/2026-08-22_CANONICAL_CHARACTER_CAST_REAUTHORING_AND_STATE_SET.md`

This gate asks the local maintainer agent to attempt:

```text
4 canonical characters
× 5 complete authored states
= 20 finished state SVGs
```

States:

```text
neutral
blink
happy
surprised
sleepy
```

It also requires source-level semantic groups/components and storyboard proof against the existing motion vocabulary:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

### Boundary

This first gate is **art/state/motion-design evidence only**.

Do not modify runtime manifests, Activities, or `SceneActorDefinition` before owner pixel review. After the candidate cast is accepted, a separate runtime gate may:

1. promote approved canonical state art;
2. add all four characters/states to the explicit build-time visual manifest;
3. extend renderer-neutral SceneActor semantic motion support without skeletal rigs;
4. exercise the resulting motion/state behavior through the Activity Simulator.

## 11. Character production rule

Canonical character identity and authoring flexibility both matter.

Use:

> **full authored state SVGs for finished reusable states + semantic source layers/components for future authoring; simple whole-body transforms for runtime motion.**

Do not replace this with:

- skeletal/bone animation;
- dozens of body-part runtime sprites;
- frame-by-frame sprite explosions;
- identical generic face stamps across all four characters.

The accepted grammar remains: identity from silhouette + face + a few strong cues; life from expression + whole-body motion.

## 12. Relationship to the user-agent skill

The maintainer track builds and curates the toolbox and canonical cast.

Arbitrary Activity agents should conceptually:

```text
inventory Activity needs
→ query the generic semantic library
→ reuse canonical Greia characters by stable identity/state when appropriate
→ prefer reviewed/preferred generic assets where they fit
→ inspect candidate/source references when useful
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ create Activity-local final art where needed
→ flatten/build runtime rendition
→ integrate through Greia package/scene seams
→ visually review
```

After the canonical-character candidate and runtime gates, return to exercising this user-facing workflow in real Activity authoring. Do not treat maintainer-agent character quality as arbitrary-agent capability evidence.

## 13. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- immediately create generic Batch B merely to increase counts;
- redraw every candidate reference until it becomes preferred;
- create a giant noun warehouse;
- bake arbitrary food/text/story meaning into generic bases;
- infer arbitrary user-agent capability from the maintainer agent;
- reopen hero-tree specimen optimization;
- turn canonical characters into detailed skeletal rigs;
- create a second runtime catalogue/cache architecture.

## 14. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling/character-art track closes, reorders, or bypasses R7.
