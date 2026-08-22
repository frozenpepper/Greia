# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE CONTENT-PRODUCTION / AUTHORING-TOOLING / CANONICAL-CHARACTER TRACK  
**Date:** 2026-08-22  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
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

Theme/source bundles are provenance pools. Generic authoring discovery is organized by semantic need:

1. Nature & Landscape
2. Interiors & Architecture
3. Furniture & Storage
4. Everyday Props & Containers
5. Making, Learning & Play
6. Lighting, Atmosphere, FX & Shadows

Shared UI and Canonical Characters are separate stronger-consistency families.

Canonical characters are not interchangeable generic props; identity consistency matters.

## 3. Established generic source state

### Forest / Meadow v0.3

Promoted source pool with 28 semantic roles: 23 reauthored + 5 retained legacy + 2 preferred ingredients.

### Workshop v0.2

Promoted source pool with 24 finished semantic assets: 14 direct replacements + 5 retained baseline variants + 5 candidate coexistence variants + 2 preferred ingredients.

### Clinic / Reading / Fantasy / Water

These remain useful source/provenance pools. Generic resources have been harvested/classified; specialized theme-specific art is not a reason to resume theme-by-theme pack production.

## 4. Generic library consolidation — complete enough for current phase

The full source harvest and Core Essentials Batch A are complete.

Current generic authoring indexes after admission/discovery tooling:

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

No generic Batch B is authorized merely to increase counts.

## 5. Permanent generic rules

Coverage questions distinguish:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

An existing weak asset is a quality gap, not missing inventory.

The library must not become a giant clip-art noun warehouse.

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Runtime remains economical: rich source work may be flattened into efficient final runtime assets.

## 6. Four-character canonical reauthoring — completed and reviewed

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Candidate source:

`assets/visual/pack_candidates/canonical_characters/2026-08-22/`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Actual owner-transfer pixels were reviewed.

Accepted as the next-system foundation:

- complete registered states `neutral`, `blink`, `happy`, `surprised`, `sleepy`;
- cheap shared motion semantics `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`;
- source-level semantic groups/components for future authoring;
- complete-state swaps + whole-character transforms rather than skeletal rigs.

Disposition:

```text
Lilli → carry forward current candidate
Tito  → carry forward current candidate
Momo  → carry forward current candidate
Nino  → preserve as historical/source provenance; current owl target is Leo
```

Do not promote the old four-character lineup as the final canonical family.

## 7. Current canonical cast design

Authority:

`docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

Current target:

```text
Lilli — unicorn      → creativity / stories / art / imagination
Leo   — owl+glasses  → learning / reading / language / knowledge
Flash — rabbit       → games / speed / action / playful challenge
Dani  — robot        → math / logic / patterns / sequencing
Tito  — fox          → exploration / nature / discovery / investigation
Momo  — monster      → emotion / music / silly play / celebration
```

This is a **soft lead-mascot system**, not exclusive silos.

Do not create six Home categories. Existing platform-owned Collections remain:

```text
create
play
learn
explore
my_greia
```

Natural affinity is allowed (`Create→Lilli`, `Play→Flash`, `Learn→Leo`, `Explore→Tito`), while Dani and Momo remain cross-cutting and `my_greia` remains child/profile-centered.

## 8. Exact current art gate

Execute:

`docs/testing/2026-08-22_CANONICAL_CAST_EXPANSION_LEO_FLASH_DANI.md`

This bounded gate must:

1. refine the current owl foundation into **Leo** with integrated signature glasses;
2. create **Flash** as a silhouette-distinct rabbit;
3. create **Dani** as a cute rounded toy-like robot;
4. author the same five complete states for Leo/Flash/Dani;
5. preserve Lilli/Tito/Momo unless a concrete six-cast collision is demonstrated;
6. prove all-six identity at 256/128/64 px and silhouette-only 128/64;
7. show shared motion vocabulary across all six at storyboard/design scope;
8. stop for owner pixel review before runtime promotion or ID migration.

Candidate workspace:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`

Owner ZIP:

`GREIA_VISUAL_REVIEW_CANONICAL_CAST_EXPANSION_2026-08-22.zip`

## 9. Specific visual risks to control

### Leo

The current owl's large circular eye treatment is already visually dominant. Glasses must be integrated with the eye-mask/eye disks, not stacked on top as extra rings. The old teal badge is optional if glasses provide enough identity.

### Flash

Flash must not become:

- Tito recolored with longer ears;
- Lilli without horn;
- a racing-costume mascot with activity-specific props baked into identity.

Silhouette must communicate rabbit + stored speed before color.

### Dani

Dani must not become a generic device icon or dense sci-fi robot. Face/emotion is primary; mechanical detail remains sparse and toy-like. No baked numerals/text.

## 10. Character production rule

Use:

> **full authored state SVGs + semantic source layers/components for authoring + simple whole-body transforms for runtime motion.**

Do not replace this with:

- skeletal/bone animation;
- runtime body-part composition;
- dozens of limb sprites;
- frame-by-frame sprite explosions;
- cloned one-body formulas for every cast member.

## 11. What follows owner approval of the six-cast candidate

Only after owner pixel acceptance:

1. promote approved canonical states under stable source identities;
2. explicitly migrate historical Nino identity to current `character.leo` where appropriate;
3. add accepted character states to the explicit build-time rendition manifest;
4. extend `SceneActorDefinition` only enough for semantic state/motion selection with whole-character transforms;
5. exercise runtime/fallback/responsive behavior through the Activity Simulator;
6. then consider optional Activity presentation metadata for lead/supporting canonical characters;
7. return to exercising the user-facing visual-authoring skill/toolbox in real Activity authoring rather than increasing art counts by inertia.

## 12. Relationship to arbitrary Activity-authoring agents

Maintainer-side character production does not define arbitrary-agent capability.

Activity authors should eventually be able to:

```text
inventory Activity visual needs
→ query generic authoring library
→ choose canonical cast lead/support when appropriate
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ keep specialized art Activity-local
→ flatten/build economical runtime renditions
→ integrate through Greia package/scene seams
→ visually review
```

## 13. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- create generic Batch B merely to increase counts;
- redraw every candidate reference until preferred;
- reopen hero-tree specimen optimization;
- create six top-level Home destinations from six characters;
- promote Nino automatically without Leo review;
- turn canonical characters into detailed skeletal rigs;
- create a second runtime catalogue/cache architecture;
- infer arbitrary user-agent capability from the maintainer agent.

## 14. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling/character-art track closes, reorders, or bypasses R7.
