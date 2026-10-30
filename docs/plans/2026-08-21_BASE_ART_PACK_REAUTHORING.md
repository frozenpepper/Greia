# Greia Generic Visual Toolbox Production — Maintainer-Side Plan

**Status:** ACTIVE AUTHORING-WORKFLOW VALIDATION  
**Date:** 2026-08-22  
**Architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**Generic taxonomy:** `docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md`  
**Canonical cast system:** `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`  
**Character grammar:** `docs/design/GREIA_CONSTRAINT_NATIVE_CHARACTER_GRAMMAR.md`  
**Character motion vocabulary:** `docs/design/GREIA_CHARACTER_EXPRESSIONS_AND_MOTION.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Purpose

Use the owner's local maintainer agent where useful to improve Greia's bundled generic visual toolbox, authoring-time discoverability, and canonical character family — while keeping the user/developer-facing workflow model/tool agnostic.

The maintainer agent's drawing ability is not a Greia dependency and is not evidence about arbitrary future Activity-authoring agents.

The practical Activity-author workflow remains owned by:

`skills/greia-visual-authoring/SKILL.md`

## 2. Authoring architecture

Theme/source bundles are provenance pools, not the primary discovery interface.

Generic authoring discovery is organized by semantic need:

1. Nature & Landscape
2. Interiors & Architecture
3. Furniture & Storage
4. Everyday Props & Containers
5. Making, Learning & Play
6. Lighting, Atmosphere, FX & Shadows

Shared UI and Canonical Characters remain separate stronger-consistency families.

## 3. Generic toolbox state

Current generic authoring indexes:

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

The model-agnostic visual-authoring skill already teaches use of this helper and the `preferred` versus `candidate_reference` distinction.

Permanent rules:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

An existing weak asset is a quality gap, not missing inventory.

The library must not become a giant clip-art noun warehouse.

> **Generic assets encode reusable form; Activity-specific meaning and contents remain separable whenever practical.**

Runtime remains economical: rich source work may be flattened into efficient Activity-local runtime assets.

**Generic Batch B is not authorized merely to increase counts.**

## 4. Canonical cast history

### Four-character reauthoring

Candidate commit:

`59336d1c34e119e04c40b32f2c1901e1dbfb1b60`

Review:

`docs/reviews/visual/2026-08-22_canonical-character-cast-reauthoring/PRIMARY_REVIEW.md` (archived; see git history)

Established the five-state/source-component/motion foundation.

### Six-character expansion

Candidate commit:

`cfbb9512723353dd34f6081c174410401e290ca8`

Review:

`docs/reviews/visual/2026-08-22_canonical-cast-expansion/PRIMARY_REVIEW.md` (archived; see git history)

Established Leo, Flash and Dani beside Lilli/Tito/Momo. Leo and Dani were accepted; Flash required one bounded identity correction.

### Flash white-rabbit correction

Candidate commit:

`fba60ff31c8bb7e825163bb349e349bd1b72d0f3`

Review:

`PRIMARY_REVIEW.md` (archived; see git history)

Result: **ACCEPTED**.

### Canonical cast v0.1 runtime promotion and final acceptance

Stable source:

`assets/visual/characters/canonical/v0.1/`

Current six:

```text
Lilli — unicorn                       → creativity / stories / art / imagination
Leo   — owl with integrated glasses  → learning / reading / language / knowledge
Flash — white rabbit + lightning top → games / speed / action / playful challenge
Dani  — friendly robot               → math / logic / patterns / sequencing
Tito  — fox                          → exploration / nature / discovery / investigation
Momo  — monster                      → emotion / music / silly play / celebration
```

Final owner acceptance:

`docs/reviews/visual/2026-08-22_canonical-cast-v01-final-capture/OWNER_REVIEW.md` (archived; see git history)

Evidence class: **SIMULATOR VISUAL REVIEW**.

Accepted runtime family:

- 6 semantic character IDs;
- 5 authored state variants each = 30 runtime PNG renditions;
- states `neutral`, `blink`, `happy`, `surprised`, `sleepy`;
- motions `idle_bounce`, `blink`, `happy_hop`, `celebrate_pop`, `surprised_wobble`, `sleepy_sway`;
- fixed-size whole-character translation motion;
- contact-shadow grounding;
- bounded failed-rendition memory;
- non-default fallback to neutral/default;
- deliberate Activity-level behavior when a required default cannot render.

No further pure-art cast gate or proof-only cast Activity is required before real Activity use.

## 5. Character production/runtime rule

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

## 6. Soft specialization, not hard silos

Useful affinities remain:

```text
create  → Lilli often leads
play    → Flash often leads
learn   → Leo often leads
explore → Tito often leads
```

Dani and Momo are cross-cutting. `my_greia` remains child/profile-centered.

Do not create six top-level Home destinations.

Do not add `lead_character` / `supporting_characters` package metadata merely because it was proposed. Real Activity work must establish whether that schema has value.

## 7. First real Activity visual-authoring exercise — EXERCISED & PACKAGED

Executed runbook:

`docs/testing/2026-08-22_SHAPE_GARDEN_VISUAL_AUTHORING_WORKFLOW_EXERCISE.md`

Activity: `activities/shape_garden/` (`org.greia.shape-garden`)

Executed workflow:

```text
baseline pixels
→ visual-needs inventory
→ generic discovery helper
→ REUSE / COMPOSE-ADAPT / KEEP-EXISTING decisions
→ canonical Dani companion integration
→ Activity-local stems / shadows / delight particles
→ existing scene/shared UI/runtime seams
→ Activity Simulator 10-scenario before/after review
```

Review artifacts packaged:
- Review directory: `docs/reviews/visual/2026-08-22_shape-garden-visual-authoring-workflow/` (archived; see git history)
- Audit report: `AUTHORING_AUDIT.md`
- Structured audit data: `authoring-audit.json`
- Simulator trace: `simulator-trace.json`
- 10 curated PNGs across 4 viewports, motion-disabled mode, and fail-soft resilience proof
- Owner transfer bundle: `GREIA_VISUAL_REVIEW_SHAPE_GARDEN_AUTHORING_WORKFLOW_2026-08-22.zip`

## 8. Exercise findings and decisions

1. **Discovery helper:** Rapidly located relevant generic assets (`ground.grass_edge.01`, `atmosphere.sunlight_rays.01`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `bush.flowering.01`, `ui.shadow.soft`) without manual folder crawling.
2. **Library status states:** `preferred` was directly usable out of the box with zero modifications required.
3. **Generic taxonomy:** The 6 semantic collections matched authoring needs accurately (Nature/Landscape, Lighting/Atmosphere/FX/Shadows).
4. **Activity-local boundaries:** Core educational geometry primitives and sprout stems remained cleanly inside Activity code.
5. **Runtime economy:** Zero runtime SVG parsing, bounded Pygame visual cache, zero per-frame disk I/O.
6. **Canonical companion:** Dani (`character.dani`) fits the math/geometry domain naturally, providing non-intrusive joyful feedback.
7. **Package metadata:** Manifest-level character fields remain **UNNECESSARY**; `SceneActorDefinition` in code is fully expressive.
8. **Library gaps:** **`NO_GAP`**. Generic Pack A + Canonical Cast v0.1 fully satisfied the garden theme. Generic Batch B remains unauthorized.

### Costruiamo Ponti Stress Exercise Summary

- Target: `activities/costruiamo_ponti/` (`org.greia.costruiamo-ponti`).
- Decisions:
  - `REUSE`: `character.flash`, `hills.distant.01`, `cloud.large.01`, `cloud.small.01`, `atmosphere.sunlight_rays.01`, `bush.flowering.01`, `rock.cluster.large.01`, `shadow.contact.small.01`, `ui.shadow.soft`.
  - `COMPOSE_ADAPT`: 3 distinct world terrain environments (`bank_river.png`, `bank_canyon.png`, `bank_space.png`) with distinct geology across River, Canyon, and Space.
  - `CREATE_ORIGINAL`: 4 bridge materials (`block_wood.png`, `block_stone.png`, `block_shroom.png`, `block_rainbow.png`), safety net (`trampoline.png`), and reward goal flag (`goal_flag.png`).
  - `KEEP_EXISTING_INTENTIONAL`: Puzzle mechanics, 4-material requirements, sound synthesis, storage persistence, event emissions, platform Home button.
- Companion: Canonical Flash (`character.flash`) with `neutral` idle, `happy` walking hop, spring bounce, and `surprised` trampoline rebound.
- Evidence: 13 curated simulator PNGs in `docs/reviews/visual/2026-08-22_costruiamo-ponti-visual-authoring-stress/` (archived; see git history) + transfer bundle `GREIA_VISUAL_REVIEW_COSTRUIAMO_PONTI_AUTHORING_STRESS_2026-08-22.zip`.
- Gap outcome: `NO_GAP`. Generic Batch B remains unauthorized.


## 9. Relationship to arbitrary Activity-authoring agents

The intended workflow remains:

```text
inventory Activity visual needs
→ query generic authoring library
→ choose canonical cast presence where appropriate
→ REUSE / COMPOSE-ADAPT / CREATE ORIGINAL
→ keep specialized art Activity-local
→ flatten/build economical runtime renditions
→ integrate through Greia package/scene seams
→ visually review actual pixels
```

The Shape Garden gate tests whether this workflow is actually usable, not merely well documented.

## 10. Explicit drift to avoid

Do not:

- return to theme-by-theme pack production;
- create Generic Batch B merely to increase counts;
- redraw every candidate reference until preferred;
- reopen hero-tree specimen optimization;
- reopen accepted Lilli/Leo/Flash/Dani/Tito/Momo art without a concrete blocker;
- turn canonical characters into skeletal rigs;
- create a runtime clothing system;
- create a second runtime asset system;
- infer arbitrary user-agent capability from the maintainer agent;
- add package character metadata without a demonstrated real Activity use case;
- use another proof-only fixture where a real Activity can exercise the system.

## 11. Platform boundary

R7 remains the primary blocking platform phase. Nothing in this visual-content/authoring workflow closes, reorders, or bypasses R7.

No physical Acer/Pi acceptance should be claimed without actual hardware evidence.
