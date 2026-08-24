# Session 07 — Posta di Leo: meaningful emergent writing

**Provider calls:** forbidden; repository art plus local SVG work only
**Prerequisite:** Sessions 00–06 accepted and committed
**Commit:** `feat(activity): add Posta di Leo postcard creator`

## Outcome

`org.greia.posta-di-leo` lets a child select a friend/picture stamp, type or mark a short message, save it safely, and revisit/delete up to 20 postcards without duplicating the full Writing editor.

## Preconditions

- Pull current `main`; verify prior cumulative gate.
- Read Activity core/engineering/achievement/discovery/visual routes, `PHASE0_CORE_CREATION_ACTIVITIES.md`, and current Writing source/tests for reuse boundaries.

## Allowed files

```text
activities/posta_di_leo/**
tests/test_activity_posta_di_leo.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No copy of Writing's full editor/gallery, no spell-check/autocorrect, no cloud/share/send transport, no profile-avatar mutation, no auto-eviction, and no arbitrary filesystem path.
- Do not interpret invented spelling or marks as failure.

## Evidence and source decisions

Head Start describes writing for varied purposes through drawings, scribbles, letters, names, and invented spelling. A bounded postcard supplies authentic purpose while the existing Writing Activity remains the general editor.

## Exact implementation

1. Manifest: `org.greia.posta-di-leo`, key `activity.posta_di_leo.title`; `it,en`; collections `create,learn`; tags `writing,stories`; education `writing,print_concepts,creative_expression`; difficulty 2, age min 5 with no max/adaptive range; text input; required `display,keyboard`, optional `pointer,touch`; event `postcard.created` creation; storage 1.
2. Create thin `main.py` plus `postcard_model/content/services/art/renderer/app.py`. Define `RecipientId` for six canonical characters, `PostcardDraft(recipient,stamp_id,text)`, immutable `SavedPostcard(id,created_at,recipient,stamp_id,text)`, and `PostcardLibrary` capped at 20.
3. Flow: large recipient portraits → six picture stamps → one 80-grapheme message line → preview → explicit Save. Each stage is understandable through picture/animation; localized labels are secondary.
4. Text editing uses Greia grapheme helpers for cursor left/right, Backspace/Delete, selection, truncation, and hit testing. Store standard UTF-8. Accept empty text when a stamp is selected; the picture itself may be the message.
5. Save uses `posta_di_leo.library.v1` only after successful Greia Storage write, then emits `postcard.created` once with recipient/stamp and no message text payload. At 20, Save opens a friendly full-library sheet; it never deletes an old card. Gallery delete requires select → large delete control → confirm; cancel preserves card.
6. Storage deserialization rejects unknown schema, >20 entries, duplicate IDs, invalid recipient/stamp, >80 graphemes, and control/NUL violations; fail soft to empty library without overwriting corrupt data.
7. Reuse `character.leo` and canonical character portraits. Adapt paper-stack/book materials; create original postbox, envelope, six language-neutral stamps, postcard frame, icon. No words baked into art.
8. Use fluid safe geometry, GreiaTypography, bounded text surfaces, and invalidation redraw. This open-ended Activity has no completion screen or score.

## Tests

- Grapheme-safe insert/move/delete/truncate with ZWJ, skin tone, flag, keycap, combining mark.
- Empty-text stamp card is valid; >80 graphemes cannot enter/save.
- Save writes before event; write failure emits nothing and retains draft.
- Library cap never evicts; delete confirm/cancel semantics; malformed-state recovery.
- No global profile/avatar mutation/import, no message text in event payload, exact manifest metadata.
- Geometry at representative viewports and zero redraw while static.

## Local gate

```bash
find activities/posta_di_leo -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_posta_di_leo tests.test_writing_emoji_editing -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/posta_di_leo
```

Expected: focused/grapheme tests and validation exit 0; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_officina_dei_suoni tests.test_activity_posta_di_leo tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with seven portfolio suites and named contracts green.

## Stop conditions

- Storage cannot prove write-before-event or any full-library path silently deletes work.
- Implementation becomes a second full text editor, sends data externally, or judges spelling.

## Handoff

Return standard packet plus storage schema examples, 20-card/full/delete proofs, Unicode cases, event privacy proof, asset hashes, and SOURCE label.

## Implementation Checkpoint (2026-08-24)

- **Status:** COMPLETED & VERIFIED
- **Activity:** `org.greia.posta-di-leo` (0.1.0)
- **Validation:** `PASS org.greia.posta-di-leo 0.1.0` (sha256 `5aed54a0341ffe240abcb804f86fdab127fab5e1ac73b9fffad42a6ed3f717fe`)
- **Tests:** 11/11 tests pass in `tests/test_activity_posta_di_leo.py`, cumulative 136 tests pass, full `make verify` (1,268 tests) passes.
- **Evidence:** DESKTOP VISUAL REVIEW passed with 6 rendered frames in `build/review/posta_di_leo/`.

