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

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Accepted foundation:

- complete registered states `neutral`, `blink`, `happy`, `surprised`, `sleepy`;
- cheap shared motion semantics `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`;
- source-level semantic groups/components;
- complete-state swaps + whole-character transforms rather than skeletal rigs.

Disposition:

```text
Lilli → carry forward
Tito  → carry forward
Momo  → carry forward
Nino  → historical/source provenance; current owl target is Leo
```

## 7. Six-character canonical cast expansion — executed and reviewed

Candidate commit:

`cfbb9512723353dd34f6081c174410401e290ca8`

Candidate source:

`assets/visual/pack_candidates/canonical_cast_expansion/2026-08-22/`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`

Actual owner-transfer pixels were reviewed.

Accepted:

```text
Lilli — unicorn      → creativity / stories / art / imagination
Leo   — owl+glasses  → learning / reading / language / knowledge
Dani  — robot        → math / logic / patterns / sequencing
Tito  — fox          → exploration / nature / discovery / investigation
Momo  — monster      → emotion / music / silly play / celebration
```

Flash is structurally accepted as the games/action rabbit:

- silhouette works;
- ears/tail/posture separate him from Tito and Lilli;
- five states work;
- shared motion storyboards work.

One owner-directed identity correction remains before promotion:

> current raspberry fur should become **white/warm-white rabbit fur**, with the action/speed identity moved into a **simple coral/raspberry shirt carrying one large yellow/gold lightning bolt**.

This is a bounded correction, not a cast reopening.

## 8. Current canonical cast design

Authority:

`docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

Current target:

```text
Lilli — unicorn                       → creativity / stories / art / imagination
Leo   — owl with integrated glasses  → learning / reading / language / knowledge
Flash — white rabbit + lightning top → games / speed / action / playful challenge
Dani  — friendly robot               → math / logic / patterns / sequencing
Tito  — fox                          → exploration / nature / discovery / investigation
Momo  — monster                      → emotion / music / silly play / celebration
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

## 9. Exact current art gate

Execute:

`docs/testing/2026-08-22_FLASH_WHITE_RABBIT_IDENTITY_REVISION.md`

This is the **last intended pure-art correction before canonical cast promotion**.

The gate must:

1. preserve Flash's current semantic identity, rabbit silhouette, long ears, pom tail, posture and five-state system;
2. change dominant fur/body to white or warm white;
3. add a simple coral/raspberry shirt or sleeveless top;
4. add one large yellow/gold lightning bolt;
5. preserve Lilli/Leo/Dani/Tito/Momo unchanged;
6. prove revised Flash at 256/128/64 and directly against Lilli/Tito;
7. prove the revised six-character ensemble and one shared motion storyboard;
8. stop for owner pixel review before source promotion/runtime work.

Owner ZIP:

`GREIA_VISUAL_REVIEW_FLASH_WHITE_RABBIT_REVISION_2026-08-22.zip`

## 10. Character production rule

Use:

> **full authored state SVGs + semantic source layers/components for authoring + simple whole-body transforms for runtime motion.**

Do not replace this with:

- skeletal/bone animation;
- runtime body-part composition;
- runtime clothing/equipment composition;
- dozens of limb sprites;
- frame-by-frame sprite explosions;
- cloned one-body formulas for every cast member.

Flash's shirt/bolt may be semantic source groups; they are not a runtime wardrobe API.

## 11. What follows owner approval of revised Flash

After owner pixel acceptance of the bounded Flash revision, **do not create another pure-art cast gate** unless a concrete blocker is identified.

Move directly to:

1. promote the approved six canonical characters/states under stable source identities;
2. explicitly migrate historical Nino identity to current `character.leo` where appropriate while preserving provenance;
3. add all accepted character states to the explicit build-time rendition manifest;
4. extend `SceneActorDefinition` only enough for semantic state/motion selection with whole-character transforms;
5. exercise runtime state/motion/fallback/responsive behavior through the Activity Simulator;
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
- reopen Leo/Dani/Lilli/Tito/Momo during the Flash correction;
- turn canonical characters into detailed skeletal rigs;
- create a runtime clothing system for Flash;
- create a second runtime catalogue/cache architecture;
- infer arbitrary user-agent capability from the maintainer agent.

## 14. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling/character-art track closes, reorders, or bypasses R7.
