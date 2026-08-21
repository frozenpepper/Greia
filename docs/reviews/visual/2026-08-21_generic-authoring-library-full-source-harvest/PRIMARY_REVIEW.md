# Primary Review — Generic Visual Library Full Source Harvest

**Date:** 2026-08-21  
**Reviewed commit:** `2dcf306589efb721db4cac6bca7233c342fcfaa1`  
**Evidence reviewed:** actual owner-transfer PNGs from `GREIA_VISUAL_REVIEW_GENERIC_LIBRARY_FULL_SOURCE_HARVEST_2026-08-21.zip`

## Verdict

The full-source harvest is accepted as the first sufficiently complete inventory/gap baseline for the generic authoring library.

The important result is not merely the 89 indexed resources. The gate correctly distinguishes:

- existing broadly useful candidate references;
- weak-but-semantic existing assets that are `QUALITY_GAP`, not missing;
- specialized theme-only art;
- superseded assets;
- genuinely missing broad roles.

The screenshots support the classifications. Reading/Classroom contains the expected book/seating/plant/basket roles but the current drawings are visibly flat and weak. Fantasy contains several useful generic night/lighting references plus bridge/sign/well/lantern roles that need reauthoring. Water/Pond contains useful water/FX references while reeds/lily pads/dock/stepping stones remain clear quality gaps.

The `preferred` versus `candidate_reference` split is also visually justified. Several candidate references — especially water base/ripple/shimmer/dragonfly/night assets — are useful source/reference material but are not strong enough to be presented as preferred finished assets.

## Accepted findings

The following gap conclusions are accepted:

- doors / room openings: `TRUE_MISSING`;
- standard dining/desk chair: `TRUE_MISSING`;
- books/storybooks: `QUALITY_GAP`;
- reading armchair/bookcase: `QUALITY_GAP`;
- indoor plant/basket: `QUALITY_GAP`;
- water botanical/structure roles: `QUALITY_GAP`;
- generic bridge/sign/well/lantern: `QUALITY_GAP`;
- basic tableware: `TRUE_MISSING`;
- general mechanical/manipulative pieces: substantially under-covered / `TRUE_MISSING` at the generic-component level.

## Important correction to the proposed next batch

The proposed 16-object batch is directionally useful but must not become an arbitrary household-object checklist.

The generic library exists to maximize **cross-Activity authoring leverage and composability**, not to become an encyclopedia of pre-finished clip-art objects.

Therefore new generic art should prefer semantic neutrality and separable meaning where that broadens reuse.

Examples:

- prefer an **empty ceramic plate** over `plate.ceramic_toast`; toast/food should be separate if later needed;
- prefer an **empty bowl** over a bowl with cereal baked into it;
- a teacup/saucer may be a generic finished object, but the liquid should not be the only usable form;
- prefer generic gear/dial/lever components over one overly specific teaching-machine object;
- an open storybook may contain abstract/non-readable picture shapes, but should not bake in a specific story or localized text;
- signs/boards should remain blank unless their semantic role explicitly requires authored symbols.

This rule is now part of the generic-library architecture:

> **Generic assets should encode the reusable object/form; Activity-specific meaning and contents should remain separable whenever practical.**

## Authorized next production direction

Proceed with one bounded cross-category batch focused on the highest-leverage true/quality gaps, with neutral/composable semantics.

Authorized scope is defined in:

`docs/testing/2026-08-21_GENERIC_CORE_ESSENTIALS_BATCH_A.md`

The batch intentionally mixes architecture, seating, reading/storage, neutral everyday props, and mechanical components. It does not reopen themed pack production.

## Not authorized

- no Clinic v0.2 completion;
- no Reading/Classroom pack reauthoring as a theme;
- no Fantasy or Pond pack reauthoring as themes;
- no giant food/kitchen pack;
- no attempt to fill every inventory noun;
- no direct runtime integration during this source-art batch;
- no claim that the owner's maintainer agent predicts arbitrary user-agent capability.
