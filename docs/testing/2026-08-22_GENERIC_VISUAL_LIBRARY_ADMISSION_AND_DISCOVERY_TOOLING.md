# Generic Visual Library — Batch A Admission and Discovery Tooling

**Status:** EXECUTE  
**Date:** 2026-08-22  
**Authority:** `docs/reviews/visual/2026-08-21_generic-core-essentials-batch-a/PRIMARY_REVIEW.md`

## Purpose

Selectively admit Batch A and make the generic authoring library easy for arbitrary Activity-authoring agents to query. This is not an art-production or runtime gate.

Do not redraw Batch A. Do not create Batch B. Do not modify Activities or runtime consumers.

## Exact Batch A admission

Create stable preferred source under:

`assets/visual/generic/core_essentials/v0.1/`

Promote exactly these 9 finished assets:

- `interior.door.timber.closed`
- `interior.opening.arch.simple`
- `furniture.seating.chair.spindle_wood`
- `furniture.storage.bookcase.tall_open`
- `prop.storage.basket.woven_empty`
- `prop.tableware.bowl.ceramic_empty`
- `prop.tableware.cup_saucer.ceramic`
- `component.mechanical.gears.interlocking_pair`
- `component.mechanical.dial_hands.blank`

Promote exactly these 2 ingredients:

- `ingredient.hardware.door_hinge_handle`
- `ingredient.mechanical.axle_hands`

Preserve the Batch A candidate workspace unchanged for provenance.

Keep exactly these 7 resources as `candidate_reference` pointing to the candidate source; do not copy or redraw them:

- `interior.door.timber.ajar`
- `furniture.seating.armchair.soft_reading`
- `prop.book.open.picture_book`
- `prop.books.stack.mixed`
- `prop.decor.plant.potted_fern`
- `prop.tableware.plate.ceramic_empty`
- `component.mechanical.gear.wooden`

Update the six generic collection TOMLs with sensible primary placement and the owner-authorized `library_status` values. Do not create a new top-level collection.

Use conservative size metadata. Do not claim 32px/48px quality support when it was not actually demonstrated.

## Authoring discovery helper

Create:

`tools/visual_authoring_library.py`

This is authoring/development tooling only. It must not be imported by Greia runtime code.

Provide simple commands equivalent to:

```text
python tools/visual_authoring_library.py collections
python tools/visual_authoring_library.py list
python tools/visual_authoring_library.py list --collection furniture_storage
python tools/visual_authoring_library.py list --status preferred
python tools/visual_authoring_library.py search chair
python tools/visual_authoring_library.py search "book storage" --status preferred
python tools/visual_authoring_library.py show furniture.seating.chair.spindle_wood
python tools/visual_authoring_library.py validate
```

Support `--json` for agent-friendly output.

Search only authoring metadata such as semantic ID, collection, family, role, tags and notes. Keep it deterministic, local and dependency-light: no model calls, embeddings, network service or database.

Each result should expose semantic ID, collection, admission status, family/role, source path, useful tags, size guidance when available and short notes.

`validate` should report structural problems such as malformed TOML, missing source file, conflicting duplicate IDs, unsupported status, malformed required fields or paths outside the expected asset tree. It must not judge subjective visual quality.

## Tests

Add focused tests using existing repository conventions. Cover at least:

- all six generic indexes parse;
- expected collections are discovered;
- `search chair` finds the spindle chair;
- preferred filtering excludes Batch A candidate references;
- exact `show` returns source/status metadata;
- candidate references remain searchable;
- conflicting duplicate IDs fail validation;
- missing source paths fail validation;
- JSON output is valid and stable enough for agent use.

Do not add a large harness.

## User-agent skill

After the helper exists and tests pass, update `skills/greia-visual-authoring/SKILL.md` so arbitrary Activity-authoring agents are told to:

1. inventory visual needs first;
2. use the discovery helper when available;
3. prefer `preferred` assets for direct reuse;
4. use `candidate_reference` mainly as adaptation/reference material;
5. inspect actual source/preview before integrating;
6. create original Activity-local art when the toolbox does not fit;
7. never assume the maintainer's local drawing agent or technique exists.

## Documentation

Update:

- `assets/visual/authoring_library/README.md`
- `docs/plans/2026-08-21_BASE_ART_PACK_REAUTHORING.md`
- `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`

Record that Batch A is selectively admitted, discovery tooling exists, and **no Batch B is currently authorized**. The next milestone after this gate is to exercise the user-facing visual-authoring skill/toolbox in a real Activity-authoring workflow rather than increasing asset count by inertia.

## Non-goals

Do not create new art, themed packs, runtime catalogue entries, runtime PNGs, Activities, compositor changes, databases or network services. Do not claim arbitrary-agent compatibility from this maintainer-side execution.

## Return

Commit/push coherent changes and report:

- commit SHA;
- stable preferred source path;
- preferred/candidate counts;
- updated generic-index counts;
- discovery helper path;
- example list/search/show output;
- focused test commands/results;
- confirmation that no new art/runtime consumers were created.
