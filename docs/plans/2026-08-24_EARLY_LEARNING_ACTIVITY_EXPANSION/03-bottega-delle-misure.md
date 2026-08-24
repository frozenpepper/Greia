# Session 03 — Bottega delle Misure: compare and measure

**Provider calls:** forbidden; repository art plus local SVG work only
**Prerequisite:** Sessions 00–02 accepted and committed
**Commit:** `feat(activity): add Bottega delle Misure`

## Outcome

`org.greia.bottega-delle-misure` teaches comparison, ordering, and repeated-unit measurement through five parcel challenges with exact no-gap/no-overlap rules.

## Preconditions

- Pull current `main`; verify prior cumulative gate.
- Read the same specialist documents required by Session 01.

## Allowed files

```text
activities/bottega_delle_misure/**
tests/test_activity_bottega_delle_misure.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No real-world unit/scale claim, physics engine, platform or existing-Activity edit, or arbitrary drag tolerance.
- Decorative pixels cannot be measurement authority; domain `units` is authority.

## Evidence and source decisions

Head Start names attribute comparison/order and one repeated non-standard unit. Equal blocks plus visible rails make the unit, origin, gaps, and overlaps inspectable.

## Exact implementation

1. Manifest: `org.greia.bottega-delle-misure`, title key `activity.bottega_delle_misure.title`; `it,en`; `learn,explore`; tags `numbers,puzzles`; education `early_math,measurement,comparison`; difficulty 3, age 5–7, adaptive 2–5; pointer; required `display,pointer`, optional `touch`; milestone `measure.parcel_completed`, completion `measure.delivery_completed`; storage 1.
2. Create thin `main.py` and `measure_model/content/services/art/renderer/app.py`. Define `Attribute(LENGTH,HEIGHT)`, frozen `MeasureItem(item_id,units,attribute)`, `MeasureChallenge(mode,items,target_id)`, `UnitRail(origin,capacity)`, and `MeasureSession`.
3. L1 compare two items 1–4 units; L2 order three 1–5; L3 measure one 2–6; L4 measure then choose exact shelf capacity; L5 mixed length/height and order up to five. Weight is excluded from v1.
4. Map one domain unit to one logical span within a challenge. Decorative thickness/color may vary; authoritative endpoints must align with unit length.
5. Blocks snap only to consecutive indices from zero. Drops farther than half a unit from next index return to tray. Model rejects gaps, duplicates, overlap, overflow, and mixed-unit blocks.
6. Wrong comparison aligns items at one baseline and walks one block along the longer edge; no progress/event mutation.
7. Persist `bottega_delle_misure.progress.v1` with README adaptation. Emit milestone per parcel and completion after five, once each.
8. Reuse/adapt basket, book/paper, wooden blocks, shadows; create parcel, rail, shelf, icon. Dani is guide, never unit. Cache `(item_id,units,orientation,viewport_key)` ≤32 and clear on viewport recreation.
9. Use terminal completion and stop all movement in terminal state.

## Tests

- Deterministic level bounds and uniqueness.
- Compare/order truth independent from decorative dimensions.
- Rail accepts only `[0..n-1]`; rejects gap/duplicate/overlap/wrong-unit/overflow.
- Wrong attempts do not mutate events/progress; storage ≤8; cache ≤32/invalidation.
- Pointer mapping/target sizes across 1024×600, 800×600, 1366×768.

## Local gate

```bash
find activities/bottega_delle_misure -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_bottega_delle_misure -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/bottega_delle_misure
```

Expected: tests and validation exit 0; no cached bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with three portfolio suites and named contracts green.

## Stop conditions

- Visible endpoints disagree with domain truth or decorative size solves the challenge.
- A new global measurement/drag framework appears necessary.

## Handoff

Return the standard packet plus rail cases, visual/domain equivalence proof, cache/event counts, asset provenance/hashes, and SOURCE label.
