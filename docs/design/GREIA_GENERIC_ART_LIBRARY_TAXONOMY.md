# Greia Generic Art Library Taxonomy

**Status:** active design correction  
**Date:** 2026-08-21  
**Parent architecture:** `docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md`  
**User-agent skill:** `skills/greia-visual-authoring/SKILL.md`

## 1. Why this exists

Greia's user-facing art library must be broadly useful across many unrelated Activities.

A mistake in the current maintainer workflow was to treat earlier environment/theme bundles such as `Clinic / Care`, `Reading / Classroom`, and `Fantasy / Village / Night` as if each were automatically a core generic pack worth reauthoring one-by-one.

That is not the intended product architecture.

A themed bundle can be useful as provenance, a reference composition, or a source pool, but it is not automatically a good generic authoring pack.

The core authoring library should answer questions such as:

- I need a tree / rock / ground edge / cloud;
- I need a table / shelf / window / curtain / rug;
- I need paper / paint / blocks / books / containers;
- I need a shadow / light shaft / fog / particles;
- I need a comfort object / toy / cushion;

It should not require an Activity author to guess that a useful generic bowl lives in a medical pack or that a useful cabinet lives in a clinic-themed folder.

## 2. Core principle

> **Theme bundles are source/provenance pools; generic semantic collections are the primary authoring interface.**

Generic collections may reference assets from multiple promoted source packs without copying them.

The same source asset may be discoverable through more than one generic semantic collection when appropriate.

## 3. Generic authoring collections

The initial core taxonomy should be small and broad:

### 3.1 Nature & Landscape

Examples:

- trees and tree ingredients;
- bushes, grass, flowers, ferns, reeds;
- rocks, logs, stumps, mushrooms;
- ground edges / dirt / terrain;
- water edges / pond pieces;
- clouds, hills, distant landscape.

Forest/Meadow and Water/Pond source bundles primarily feed this collection.

### 3.2 Interiors & Architecture

Examples:

- wall and floor bases;
- windows and doors;
- curtains;
- rugs;
- generic room-light relationships;
- architectural panels / room features.

Workshop, Clinic, Reading/Classroom and other room source bundles may contribute here.

### 3.3 Furniture & Storage

Examples:

- tables / workbenches / side tables;
- chairs / stools / daybeds;
- shelves / cubbies;
- cabinets;
- crates / storage boxes;
- pegboards / display boards.

These should be discoverable by object role rather than by the themed room they first came from.

### 3.4 Everyday Props & Containers

Examples:

- bowls / basins;
- bottles / jars;
- boxes / baskets;
- paper stacks;
- cushions / textiles;
- simple household / tabletop objects.

Only broadly reusable forms belong here. Highly domain-specific contents remain themed or Activity-local.

### 3.5 Making, Learning & Play

Examples:

- paint / palette / brushes;
- pencils / paper / drawing tools;
- easels;
- blocks and construction toys;
- books / reading props;
- generic toys / plush comfort objects.

This is broader than a `Workshop` or `Classroom` theme and can support many Activities.

### 3.6 Lighting, Atmosphere, FX & Shadows

Examples:

- contact shadows;
- window light shafts;
- sunlight rays;
- fog / dust / motes;
- fireflies / leaves / simple ambient particles;
- generic feedback accents whose meaning is not domain-specific.

### 3.7 Shared UI

Canonical reusable Greia interface art.

This remains stricter than environment art because exact consistency is often desirable.

### 3.8 Canonical Characters

Recurring Greia characters and shared identity/state assets.

This is separate from generic environment/prop authoring.

## 4. What is not a core generic pack by default

The following are examples of **specialized theme/domain bundles**, not automatically core generic packs:

- Clinic / Medical;
- Fantasy Village;
- specific school/classroom scenes;
- a bakery;
- astronomy laboratory;
- pirate ship;
- dinosaur dig;
- farm vet room.

They may exist as:

- historical/source bundles;
- optional themed extensions;
- reference compositions;
- Activity-local art;
- sources from which genuinely generic assets are harvested into the generic indexes.

A specialized extension should only become a maintained reusable pack when multiple real Activities demonstrate the need.

## 5. How existing work maps into this model

### Forest / Meadow v0.3

This remains valuable and promoted, but should be understood primarily as a strong source bundle feeding `Nature & Landscape`, plus some cross-cutting lighting/FX roles.

### Workshop v0.2

This remains valuable and promoted, but its assets should be discoverable primarily through:

- `Interiors & Architecture`;
- `Furniture & Storage`;
- `Making, Learning & Play`;
- `Everyday Props & Containers`;
- `Lighting, Atmosphere, FX & Shadows`.

### Clinic / Care candidate

Do **not** automatically promote a core `Clinic / Care` pack merely because a candidate exists.

Instead, review it as a source pool and classify each useful asset:

Likely generic contributions include things such as:

- daybed;
- cabinet;
- side table;
- cushion;
- rug;
- curtains;
- window;
- wall/floor bases;
- plush toy;
- generic bottle/container/basin forms where the art is not intrinsically medical.

Likely specialized assets include things such as:

- toy stethoscope;
- bandage-specific container;
- care/medical kit;
- other strongly medical props.

Specialized assets may remain in provenance/reference form or later become an optional domain extension. They should not drive the core generic library.

## 6. Primary discovery layer

Activity-authoring agents should eventually browse **generic semantic indexes**, not only themed folder names.

Recommended structure:

```text
assets/visual/authoring_library/
  nature_landscape.toml
  interiors_architecture.toml
  furniture_storage.toml
  everyday_props.toml
  making_learning_play.toml
  lighting_fx_shadows.toml
```

These indexes should reference source assets in promoted packs rather than duplicate files.

Each indexed entry should expose at least:

- semantic ID;
- source pack/path;
- broad family;
- role;
- useful tags/keywords;
- recommended size range where known;
- alpha/opaque behavior;
- whether it is a finished reusable asset or authoring ingredient;
- optional preview/reference path.

## 7. Relationship to Activity-local art

The generic library is a toolbox, not a completeness promise.

An Activity author still chooses:

```text
REUSE
COMPOSE / ADAPT
CREATE ORIGINAL
```

A medical Activity may create its own unique diagnostic toy, examination prop or character pose even if Greia has generic furniture, bowls, bottles, fabric, lights and UI available.

That is expected.

## 8. Maintainer workflow correction

Do not continue blindly through the old themed sequence:

```text
Clinic → Reading/Classroom → Fantasy/Village/Night → Water/Pond
```

as though each theme were a required core pack.

Instead:

1. preserve the good source art already created;
2. build generic semantic authoring indexes over promoted/reviewed assets;
3. harvest generic assets from existing themed candidates where useful;
4. identify genuine generic coverage gaps;
5. author missing generic families/assets at pack scale;
6. only maintain specialized theme packs when repeated real Activity needs justify them.

## 9. Success criterion

A future Activity-authoring agent should be able to ask, conceptually:

> What generic visual ingredients and references do I have for this thing I need?

and get useful answers without knowing the historical theme bundle in which an asset was originally drawn.

That is the purpose of the generic Greia art library.
