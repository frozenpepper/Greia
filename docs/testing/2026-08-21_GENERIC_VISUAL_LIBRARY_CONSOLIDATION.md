# Generic Visual Library Consolidation — Maintainer Runbook

**Date:** 2026-08-21  
**Purpose:** stop themed-pack drift and reorganize existing good source art into a generic authoring toolbox for arbitrary Greia Activity authors.

## 1. Read first

Read:

```text
AGENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
skills/greia-visual-authoring/SKILL.md
docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md
assets/visual/environments/forest_meadow/v0.3/catalog.toml
assets/visual/environments/workshop/v0.2/catalog.toml
assets/visual/pack_candidates/clinic/2026-08-21/catalog.toml
```

## 2. Mission

Do **not** continue Clinic/Care finalization as though `Clinic / Care` were automatically a core generic pack.

The goal is now to create the first **generic semantic authoring-library indexes** over existing reviewed/promoted source art.

The generic library must help an Activity author find broadly reusable assets by what they are and what role they serve, not by the historical theme folder where they were created.

## 3. Do not redraw art in this task

This is a consolidation/classification pass.

Do not:

- reauthor Clinic assets;
- refine trees, lamps, beds, bears, or props;
- touch runtime code;
- change Activity code;
- create another themed pack;
- duplicate source SVGs into a new directory.

Reference existing source assets by path.

## 4. Create generic authoring-library indexes

Create:

```text
assets/visual/authoring_library/
```

with at least:

```text
README.md
nature_landscape.toml
interiors_architecture.toml
furniture_storage.toml
everyday_props.toml
making_learning_play.toml
lighting_fx_shadows.toml
```

Each entry should reference an existing source asset from a promoted/reviewed source bundle.

Recommended fields:

```text
id
source_pack
source_path
family
role
tags
kind = finished | ingredient
min_recommended_px (where known)
max_recommended_px (where known)
notes (brief, practical)
```

Do not invent exact metadata you cannot support. Leave optional fields absent when unknown.

## 5. Source pools to classify

### 5.1 Forest / Meadow v0.3

Classify all broadly reusable assets into the appropriate generic collections.

Most should feed:

- Nature & Landscape;
- Lighting / FX / Shadows.

### 5.2 Workshop v0.2

Classify all broadly reusable assets into:

- Interiors & Architecture;
- Furniture & Storage;
- Everyday Props & Containers;
- Making, Learning & Play;
- Lighting / FX / Shadows.

Preserve distinct semantic variants such as open shelf vs cubby shelf and loose blocks vs block house.

### 5.3 Clinic / Care candidate

Treat the Clinic candidate as a **source pool**, not as an automatically promoted generic pack.

For every candidate role, record one disposition:

```text
GENERIC_INDEX
SPECIALIZED_THEME_ONLY
UNRESOLVED
```

Examples that are likely generic, subject to actual inspection:

- bed/daybed;
- cabinet;
- side table;
- cushion;
- rug;
- curtains;
- window;
- wall/floor bases;
- plush bear;
- generic bottle/container forms.

Examples likely specialized:

- stethoscope;
- care/medical kit;
- bandage-specific box/tin.

Do not force a role into the generic library merely because artwork already exists.

## 6. Semantic IDs

Generic authoring-library IDs should describe the reusable object/role rather than its historical themed origin where possible.

Example direction:

```text
nature.tree.hero.oak
interior.window.arch.tall
furniture.shelf.open
furniture.shelf.cubby
furniture.table.side.round
prop.container.bottle_set
toy.plush.bear
creative.blocks.loose
creative.blocks.house
light.window.wide
shadow.contact.small
```

Do not rename or mutate the source-pack semantic IDs in their original catalogues during this task. The generic index may provide a generic discovery ID that points to the original source asset and records its source ID/path.

## 7. Generic coverage report

Create:

```text
docs/reviews/visual/2026-08-21_generic-authoring-library-consolidation/
```

with:

```text
GENERIC_COVERAGE.md
clinic-disposition.json
audit.json
01-generic-library-overview-a.png
02-generic-library-overview-b.png
03-clinic-generic-vs-specialized.png
04-generic-coverage-gaps.png
```

The PNGs are not for judging new art quality; they are visual inventory evidence showing what the generic library actually exposes.

### `GENERIC_COVERAGE.md` must answer

1. What generic collections now exist?
2. How many finished assets and ingredients does each expose?
3. Which Clinic candidate assets were harvested as generic references?
4. Which Clinic assets remain specialized and why?
5. What obvious generic gaps remain?
6. Which next art-production batch would close the highest-value generic gaps?

## 8. Gap analysis

Do not automatically propose `Reading/Classroom` or `Fantasy/Village/Night` as the next packs.

Instead identify missing **generic** coverage.

Examples of possible gaps:

- doors / arches / room dividers;
- chairs / benches / stools variety;
- baskets / cups / plates / jars / boxes;
- books / paper / cards / labels;
- generic fabric/blanket/pillow pieces;
- simple mechanical pieces / knobs / gears;
- generic signs / boards without baked text;
- water-edge / reeds / splashes;
- toy / play objects;
- generic indoor plants;
- generic decorative trim;
- additional lighting/shadow forms.

Rank gaps by broad usefulness across unrelated Activities.

## 9. Do not promote Clinic/Care in this task

Do not create `assets/visual/environments/clinic/v0.2/`.

The current Clinic candidate remains provenance/source art until we decide whether any specialized Clinic extension is worth maintaining.

Its generic pieces may be indexed by reference without copying or promoting a Clinic theme pack.

## 10. User-agent skill validation

After the indexes exist, perform a documentation-only sanity review of:

```text
skills/greia-visual-authoring/SKILL.md
```

Make sure it tells arbitrary user agents to browse the generic authoring-library indexes first, while themed/source bundles remain available as deeper references.

Do not encode local-agent-specific drawing techniques.

## 11. Final return

Commit and push:

- generic authoring-library indexes;
- generic coverage report/evidence;
- Clinic generic-vs-specialized disposition;
- any necessary documentation pointer updates.

Return:

- exact commit SHA;
- counts per generic collection;
- Clinic `GENERIC_INDEX / SPECIALIZED_THEME_ONLY / UNRESOLVED` counts;
- ranked generic coverage gaps;
- exact next recommended **generic** art-production batch.

No owner ZIP is required unless the generated inventory sheets reveal a visual classification ambiguity that genuinely needs owner inspection.
