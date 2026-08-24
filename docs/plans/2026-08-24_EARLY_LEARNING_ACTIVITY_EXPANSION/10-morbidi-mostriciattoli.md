# Session 10 — Morbidi Mostriciattoli: cute age-three creator

**Provider calls:** forbidden; local reviewed art only
**Prerequisite:** Sessions 00–09 accepted and committed
**Commit:** `feat(activity): add Morbidi Mostriciattoli`

## Outcome

`org.greia.morbidi-mostriciattoli` lets a three-year-old assemble, name optionally, and save a silly soft monster portrait from large bounded choices. Saved portraits are portable semantic recipes owned by this Activity and never become profile avatars.

## Preconditions

- Pull current `main`; verify Sessions 00–09 packets and cumulative gate.
- Inspect `shape_garden`, `painting`, `workshop_settings`, shared card/collection UI, Storage, event, grapheme, and visual-authoring owners before writing.

## Allowed files

```text
activities/morbidi_mostriciattoli/**
tests/test_activity_morbidi_mostriciattoli.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No profile/avatar/theme mutation, freehand paint canvas, filesystem export, random asset discovery, score, wrong choice, forced naming, or silent deletion.
- No saved raster blob when a bounded semantic recipe can reproduce the portrait.

## Evidence and source decisions

This is the second explicitly age-three concept: large-choice visual composition, fine-motor selection, and personal expression without a correctness demand. It stays separate from Shape Garden's free scene, Painting's canvas, and Workshop Settings' platform-owned customization.

## Exact implementation

1. Manifest: `org.greia.morbidi-mostriciattoli`, title key `activity.morbidi_mostriciattoli.title`; `it,en`; collections `create,play`; tags `making,art`; education `creative_expression,choice_making,fine_motor`; difficulty 1, age min 3 with no max, adaptive false; pointer input; required `display,pointer`, optional `keyboard,touch,audio.basic`; event `monster.portrait_created` kind `creation`; storage schema 1.
2. Create thin `main.py` plus `monster_model.py`, `monster_services.py`, `monster_audio.py`, `monster_art.py`, `monster_renderer.py`, and `monster_app.py`. Define validated IDs for six body shapes, eight body colors, six eye sets, six mouths, six tufts, and six accessories. A `MonsterRecipe` stores those six IDs plus optional `name` of at most 24 graphemes.
3. Show one 96×96-or-larger card for each visible option and six category tabs with icon plus localized accessible label. A tap/focus activation immediately replaces that category and animates a bounded 0.25-second squash/stretch preview. There is no invalid combination.
4. Add `surprise_me`, `undo`, `save`, and `gallery` controls. Inject RNG into `surprise_me`; it selects one known ID per category and must produce a recipe different from the current one. Keep a maximum undo stack of eight recipes; a new edit after undo truncates redo state.
5. Name entry is optional and opens the established lightweight text sheet. Enforce 24 graphemes with the shared grapheme helper, preserve child spelling, and make save available without a name. Keyboard absence never blocks creation.
6. Save `morbidi_mostriciattoli.gallery.v1` as at most 24 recipes with stable UUID, created UTC, six known IDs, and optional name. Write before `monster.portrait_created`; event payload contains `{portrait_id, named: bool}` and no name. At cap, open a full-gallery sheet; deletion requires explicit confirm and there is no silent eviction.
7. Gallery thumbnails render from recipes through the same compositor; do not store PNG bytes. Limit thumbnail cache to 12 least-recently-used entries and clear it when leaving the gallery. Persist no undo state.
8. Create original SVG masters for the complete part catalogue, fuzzy edge overlay, studio background, category icons, and distinct launcher icon. Use coherent soft toy materials with readable silhouettes, avoid face details below 8 logical pixels, and review every legal overlay attachment at 1024×600. Reuse only contact shadows and `character.momo` as optional guide.
9. Optional audio uses six short nonverbal category sounds and one save chime with two channels maximum. All state is visible without audio. Render static editor/gallery screens on invalidation and precompose the current portrait only when its recipe changes.
10. Use semantic focus order: category tabs, visible option cards, surprise, undo, name, save, gallery. Space activates; Escape cancels a held sheet or returns from gallery; protected system navigation remains outside Activity authority.

## Tests

- Every catalogue cardinality and ID validates; all legal recipes compose; unknown IDs recover to documented defaults.
- Surprise differs and is deterministic under injected RNG; undo/redo cap eight and branch truncation are exact.
- Optional name supports Unicode graphemes up to 24 and save works unnamed.
- Storage-before-event, 24-item cap, no eviction, explicit deletion, privacy-safe event payload, malformed-state recovery.
- Thumbnail cache cap 12/clear-on-exit, no saved raster blobs, pointer/focus equivalence, audio fail-soft, invalidation idle, READY/STOP.
- Manifest metadata/event parity, localization completeness, target geometry, icon distinctness, and no profile API call.

## Local gate

```bash
find activities/morbidi_mostriciattoli -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_morbidi_mostriciattoli -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/morbidi_mostriciattoli
```

Expected: tests and validation exit 0; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_officina_dei_suoni tests.test_activity_posta_di_leo tests.test_activity_tre_carte_una_storia tests.test_activity_nanna_delle_nuvolette tests.test_activity_morbidi_mostriciattoli tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with ten portfolio suites and named contracts green.

## Stop conditions

- Any code writes profile customization, saves opaque images instead of recipes, or makes naming/keyboard use mandatory.
- Overlay geometry fails for any legal part pair or the 24-portrait gallery exceeds its bounded cache.

## Handoff

Return the standard packet plus the complete part-ID matrix, legal-overlay visual contact sheet, recipe migration fixtures, storage/event ordering proof, cache/audio bounds, gallery cap/delete evidence, and SOURCE label.
