# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE AUTHORING-TOOLING / CANONICAL-CAST RUNTIME TRACK  
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

## 3. Generic source/toolbox state

Promoted/reviewed source pools include Forest/Meadow v0.3 and Workshop v0.2. Clinic/Reading/Fantasy/Water remain useful source/provenance pools where appropriate; theme-by-theme production is not the roadmap.

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

## 4. Permanent generic rules

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

## 5. Canonical cast source-art history

### Four-character reauthoring

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md`

Established the reusable five-state/source-component/motion-design foundation.

### Six-character expansion

Candidate commit:

`cfbb9512723353dd34f6081c174410401e290ca8`

Primary review:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md`

Established Leo, Flash and Dani beside Lilli/Tito/Momo, with Leo's glasses integration and Dani's friendly-robot identity accepted. Flash's rabbit structure/state/motion system was accepted, but owner review requested one bounded identity correction.

### Flash white-rabbit correction

Candidate commit:

`fba60ff31c8bb7e825163bb349e349bd1b72d0f3`

Owner primary review:

`docs/reviews/visual/2026-08-22_flash-white-rabbit-identity-revision/PRIMARY_REVIEW.md`

Actual owner-transfer pixels were inspected.

**Result: ACCEPTED.**

Flash is now the accepted white/warm-white rabbit with:

- tall pink-inner ears;
- coral/raspberry torso shirt;
- one gold/yellow lightning bolt;
- pom tail;
- spring-loaded/action posture;
- five registered source states.

This closes the intended pure-art cast loop.

## 6. Accepted current canonical cast

Authority:

`docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`

Current six:

```text
Lilli — unicorn                       → creativity / stories / art / imagination
Leo   — owl with integrated glasses  → learning / reading / language / knowledge
Flash — white rabbit + lightning top → games / speed / action / playful challenge
Dani  — friendly robot               → math / logic / patterns / sequencing
Tito  — fox                          → exploration / nature / discovery / investigation
Momo  — monster                      → emotion / music / silly play / celebration
```

This is a **soft lead-mascot system**, not exclusive silos.

Existing platform-owned Collections remain:

```text
create
play
learn
explore
my_greia
```

Natural affinity is allowed (`Create→Lilli`, `Play→Flash`, `Learn→Leo`, `Explore→Tito`), while Dani and Momo remain cross-cutting and `my_greia` remains child/profile-centered.

Historical Nino remains provenance; the current owl identity is Leo.

## 7. Character production/runtime rule

Use:

> **full authored state SVGs + semantic source layers/components for authoring + build-time PNG renditions + simple whole-character runtime transforms.**

Do not replace this with:

- skeletal/bone animation;
- runtime body-part composition;
- runtime clothing/equipment composition;
- dozens of limb sprites;
- frame-by-frame sprite explosions;
- continuously varying raster sizes for animation;
- a second runtime catalogue/cache architecture.

The shared source states remain:

```text
neutral
blink
happy
surprised
sleepy
```

The semantic motion vocabulary remains:

```text
idle_bounce
blink
happy_hop
celebrate_pop
surprised_wobble
sleepy_sway
```

For the first runtime pass, fixed-size state swaps + bounded x/y whole-character translation are sufficient. Do not mechanically reproduce storyboard rotation/squash if that would create per-frame allocation/cache churn.

## 8. Exact current gate

Execute:

`docs/testing/2026-08-22_CANONICAL_CAST_V01_PROMOTION_RUNTIME_SIMULATOR.md`

This gate owns:

1. stable source promotion under `assets/visual/characters/canonical/v0.1/`;
2. six current semantic IDs with historical Nino provenance preserved;
3. 30 build-time runtime renditions (6 characters × 5 states);
4. minimal typed/validated renderer-neutral expression + motion semantics;
5. bounded non-default-state fallback to neutral/default;
6. developer-only Activity fixture using the real semantic character path;
7. all runtime/visual/fallback/responsive acceptance through the Greia Activity Simulator;
8. owner-transfer evidence ZIP.

No additional pure-art cast gate comes before this unless implementation exposes a concrete source defect.

## 9. What follows runtime acceptance

Only after the canonical cast runtime simulator gate is owner-reviewed/accepted:

1. consider optional Activity presentation metadata for lead/supporting canonical characters;
2. exercise the model-agnostic Activity visual-authoring skill/toolbox in real Activity authoring;
3. use actual Activity demand to justify any further generic art quality/variety work;
4. do not resume asset-count production by inertia.

Potential future metadata remains presentation-only and must not alter package trust, permissions, saves, progression or Collection membership.

## 10. Relationship to arbitrary Activity-authoring agents

Maintainer-side character/art production does not define arbitrary-agent capability.

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

## 11. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- create generic Batch B merely to increase counts;
- redraw every candidate reference until preferred;
- reopen hero-tree specimen optimization;
- create six top-level Home destinations from six characters;
- reopen accepted Lilli/Leo/Flash/Dani/Tito/Momo art without a concrete blocker;
- turn canonical characters into detailed skeletal rigs;
- create a runtime clothing system for Flash;
- create a second runtime asset system;
- infer arbitrary user-agent capability from the maintainer agent.

## 12. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring-tooling/canonical-character track closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
