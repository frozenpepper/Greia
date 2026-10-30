# Greia Generic Art Library Taxonomy

**Status:** active design authority  
**Date:** 2026-08-21  
**Parent architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Why this exists

Greia's Activity-authoring art library must be broadly useful across many unrelated Activities.

Historical environment/theme bundles such as `Clinic / Care`, `Reading / Classroom`, `Fantasy / Village / Night`, and `Water / Pond` are useful source/provenance pools, but they are not automatically the right user-facing taxonomy.

The core authoring library should answer questions such as:

- I need a tree / rock / water edge / cloud;
- I need a table / chair / shelf / window / curtain;
- I need paper / books / paint / blocks / containers;
- I need a shadow / light shaft / fog / particles;
- I need a toy / cushion / basket / everyday prop.

It should not require an Activity author to know which historical theme bundle first contained the object.

## 2. Core principle

> **Theme/source bundles are provenance pools; generic semantic collections are the primary authoring interface.**

Generic indexes reference source assets without copying them.

The same source asset may be discoverable through more than one generic semantic collection when useful.

## 3. Core generic authoring collections

### 3.1 Nature & Landscape

Examples:

- trees and tree ingredients;
- bushes, grass, flowers, ferns, reeds;
- rocks, logs, stumps, mushrooms;
- ground edges / dirt / terrain;
- water bases / pond banks / water foliage;
- clouds, hills, distant landscape.

Forest/Meadow and Water/Pond source pools primarily feed this collection.

### 3.2 Interiors & Architecture

Examples:

- wall and floor bases;
- windows and doors/openings;
- curtains and room dividers;
- rugs;
- generic architectural panels / room features.

Workshop, Clinic, Reading/Classroom, Fantasy and other room/building source pools may contribute.

### 3.3 Furniture & Storage

Examples:

- tables / workbenches / side tables;
- chairs / stools / benches / daybeds;
- shelves / cubbies / bookcases;
- cabinets;
- crates / storage boxes / baskets;
- pegboards / display boards.

These are discovered by object role rather than source theme.

### 3.4 Everyday Props & Containers

Examples:

- bowls / basins;
- bottles / jars / cups;
- boxes / baskets;
- paper stacks / notebooks;
- cushions / textiles;
- simple household / tabletop objects;
- generic lamps and small room props.

Only broadly reusable forms belong here. Strongly domain-specific contents remain specialized or Activity-local.

### 3.5 Making, Learning & Play

Examples:

- paint / palette / brushes;
- pencils / paper / drawing tools;
- easels;
- blocks and construction toys;
- books / reading props;
- chalkboards / learning objects;
- generic toys / plush comfort objects.

### 3.6 Lighting, Atmosphere, FX & Shadows

Examples:

- contact shadows;
- window light shafts;
- sunlight / moonlight rays;
- fog / dust / motes;
- fireflies / leaves / bubbles / ripples / shimmer;
- generic feedback accents whose meaning is not domain-specific.

### 3.7 Shared UI

Canonical reusable Greia interface art. Exact consistency is often desirable here, so it remains a stricter family.

### 3.8 Canonical Characters

Recurring Greia characters and shared identity/state assets. This remains separate from generic environment/prop authoring.

## 4. What is not a core generic pack by default

Examples of specialized theme/domain bundles:

- Clinic / Medical;
- Fantasy Village;
- Classroom scene;
- bakery;
- astronomy laboratory;
- pirate ship;
- dinosaur dig;
- farm vet room.

They may remain:

- historical/source bundles;
- optional themed extensions;
- reference compositions;
- Activity-local art;
- source pools from which genuinely generic assets are harvested.

A specialized extension should become a maintained reusable pack only when repeated real Activity needs justify it.

## 5. Generic resource admission states

The semantic index structure is canonical; individual resources may have different admission/quality states.

For authoring-library entries use a simple distinction:

```text
preferred
candidate_reference
```

### `preferred`

A broadly reusable asset that is reviewed/accepted strongly enough that Activity agents should consider it first for direct REUSE.

### `candidate_reference`

A broadly reusable source asset that may help COMPOSE/ADAPT work or serve as reference, but is not yet an owner-approved preferred finished resource.

Specialized, rejected, superseded, or known-weak assets should not masquerade as preferred generic resources.

Source status and authoring-library admission status are related but not identical. A theme source pool may remain candidate while selected generic resources from it are still useful references.

## 6. Maintainer classification vocabulary

When harvesting existing source pools, classify every asset as one of:

```text
PREFERRED_GENERIC
CANDIDATE_GENERIC
REAUTHOR_GENERIC
SPECIALIZED_THEME_ONLY
DUPLICATE_OR_SUPERSEDED
UNRESOLVED
```

- `PREFERRED_GENERIC` → generic index with `library_status = "preferred"`.
- `CANDIDATE_GENERIC` → generic index with `library_status = "candidate_reference"`.
- `REAUTHOR_GENERIC` → broad role is useful, but current art is a quality gap; do not pretend the role is missing.
- `SPECIALIZED_THEME_ONLY` → keep in source/domain bundle.
- `DUPLICATE_OR_SUPERSEDED` → stronger generic coverage already exists without meaningful extra variation.
- `UNRESOLVED` → genuine ambiguity remains.

## 7. Full-source harvest before new gap claims

A generic coverage report is authoritative only after Greia's existing source pools have been harvested.

At minimum, current source pools include:

```text
assets/visual/environments/forest_meadow/
assets/visual/environments/workshop/
assets/visual/pack_candidates/clinic/
assets/visual/environments/reading_classroom/
assets/visual/environments/fantasy_village_night/
assets/visual/environments/water_pond/
```

Shared UI and canonical characters are evaluated separately in their own stricter families.

Do **not** declare an object role missing merely because it is absent from the current generic index. Search the source pools first.

Concrete existing examples include:

- Reading/Classroom already contains book stack, open storybook, reading chair, beanbag, potted plant, toy basket, bookcase, chalkboard and floor cushion.
- Fantasy/Village/Night already contains a stone bridge, lantern post, signpost, well and cobblestone edge among more specialized assets.
- Water/Pond already contains water base, bank edge, lily pads, reeds, dock, stepping stones, ripple/shimmer/reflection and water FX.

These may be preferred, candidate, weak, specialized, or superseded — but they are not nonexistent.

## 8. Gap vocabulary

After full harvest, every reported coverage gap must be classified as:

```text
TRUE_MISSING
QUALITY_GAP
VARIETY_GAP
NO_GAP
```

### `TRUE_MISSING`
No suitable source asset exists anywhere in the reviewed pools.

### `QUALITY_GAP`
A suitable semantic role exists, but current artwork is not strong enough to become a preferred reference.

### `VARIETY_GAP`
Strong coverage exists, but another meaningfully different form would provide broad reusable value.

### `NO_GAP`
Existing preferred/candidate resources already provide sufficient useful coverage.

This distinction prevents wasteful duplicate production.

## 9. How existing source work maps into the model

### Forest / Meadow v0.3

Promoted source pool feeding Nature/Landscape plus cross-cutting lighting/FX.

### Workshop v0.2

Promoted source pool feeding Interiors/Architecture, Furniture/Storage, Everyday Props, Making/Learning/Play and Lighting/FX.

### Clinic / Care candidate

Source pool only. Generic room/furniture/comfort/neutral-container art may be harvested. Strongly medical props remain specialized unless repeated use justifies a domain extension.

### Reading / Classroom v0.1

Source pool that must be harvested before claiming gaps in books, reading props, chairs, potted plants, bookcases, baskets, cushions or classroom-adjacent generic objects.

### Fantasy / Village / Night v0.1

Source pool that may contribute generic architecture/props/lighting while cottages/castles/village-specific forms remain specialized where appropriate.

### Water / Pond v0.1

Source pool that should substantially feed Nature/Landscape and Lighting/FX after quality/admission review.

## 10. Primary discovery structure

```text
assets/visual/authoring_library/
  nature_landscape.toml
  interiors_architecture.toml
  furniture_storage.toml
  everyday_props.toml
  making_learning_play.toml
  lighting_fx_shadows.toml
```

Each indexed entry should expose at least:

- semantic ID;
- source pack/path;
- broad family;
- role;
- tags/keywords;
- recommended size range where known;
- alpha/opaque behavior where useful;
- finished-vs-ingredient kind;
- `library_status` (`preferred` or `candidate_reference`);
- optional preview/reference path.

## 11. Relationship to Activity-local art

The generic library is a toolbox, not a completeness promise.

An Activity author still chooses:

```text
REUSE
COMPOSE / ADAPT
CREATE ORIGINAL
```

A medical Activity may create its own diagnostic toy; an astronomy Activity may create its own telescope; a fantasy Activity may create its own machine. That is expected.

## 12. Maintainer workflow

1. preserve good source art already created;
2. harvest **all existing source pools** into generic classifications;
3. expose strong generic assets through semantic indexes without duplication;
4. distinguish preferred resources from candidate references;
5. recompute true missing roles versus quality/variety gaps;
6. create the highest-value missing/inadequate generic families at pack scale;
7. maintain specialized theme packs only when repeated real Activity needs justify them.

Current full-harvest gate:

`2026-08-21_GENERIC_VISUAL_LIBRARY_FULL_SOURCE_HARVEST.md` (archived; see git history)

## 13. Success criterion

A future Activity-authoring agent should be able to ask:

> What generic visual resources and references do I have for this thing I need?

and receive useful results without knowing the historical source theme, while also knowing which assets are preferred for direct reuse and which are merely candidate/adaptation references.