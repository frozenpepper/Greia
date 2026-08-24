# Session 08 — Tre Carte, Una Storia: narrative sequencing

**Provider calls:** forbidden; accepted Session 00 content plus local art only
**Prerequisite:** Sessions 00–07 accepted and committed
**Commit:** `feat(activity): add Tre Carte Una Storia`

## Outcome

`org.greia.tre-carte-una-storia` lets children order three picture events, hear/choose or type a caption, and save up to 12 bilingual story artifacts with exact semantic sequencing.

## Preconditions

- Pull current `main`; verify Session 00 story captions/content hash and prior gate.
- Read Activity core/engineering/achievement/discovery/voice/visual routes and current Teatrino/Writing sources to preserve differentiation.

## Allowed files

```text
activities/tre_carte_una_storia/**
tests/test_activity_tre_carte_una_storia.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No microphone/recording, stage sandbox, generated story, network, scoring by typing, auto-eviction, or text baked into cards.
- No event before durable save and no raw child caption in event payload.

## Evidence and source decisions

Head Start expects retelling two/three events in order and developing cause/effect/prediction. This Activity fixes that sequence as domain truth while Teatrino remains open stage storytelling.

## Exact implementation

1. Manifest: `org.greia.tre-carte-una-storia`, key `activity.tre_carte_una_storia.title`; `it,en`; collections `create,learn`; tags `stories,puzzles`; education `narrative,sequencing,comprehension,writing`; difficulty 2, age min 5 with no max; hybrid input; required `display,pointer`, optional `keyboard,touch,audio.basic`; events `story.sequence_completed` completion and `story.created` creation; storage 1.
2. Create thin `main.py` plus `story_cards_model/content/services/audio/art/renderer/app.py`. Define `StorySeed(id,ordered_card_ids,caption_keys)`, `StoryDraft(seed_id,card_order,caption_mode,caption_text)`, `SavedStory`, `StoryLibrary` cap 12.
3. Load exactly the eight accepted Session 00 seeds/captions. Shuffle cards with injected RNG while forbidding the correct order at start. Drag or semantic focus/Space reorders three slots.
4. Wrong confirm preserves order and animates a clue: card-edge arrows plus first/then/last positions; after two wrong attempts briefly previews only the first correct card. Correct confirm emits `story.sequence_completed` once and opens caption stage.
5. Caption stage offers three large illustrated/voice-backed caption choices from accepted content plus optional custom text up to 80 graphemes when keyboard exists. Choosing a preset must not require reading: focus/tap plays its semantic audio and animates the matching card sequence.
6. Save to `tre_carte_una_storia.library.v1` before `story.created`; at 12 show full-library sheet and allow explicit confirmed deletion. No silent eviction. Event contains seed/caption mode, never caption text.
7. Audio is optional; when present it uses accepted deterministic pedagogical/narrative clips and bounded non-overlap queue. Visual interaction remains complete without output.
8. Reuse `character.lilli` and adapt open-book/paper assets. Create 24 original card illustrations, frames, timeline, icon. Each card image is language-neutral and separately reviewed at target size.
9. Use grapheme helpers, finite prepared surfaces, invalidation redraw. After save return to gallery/new-story choice; no fullscreen victory overlay.

## Tests

- Exactly eight bilingual three-card seeds/captions equal content-lock IDs.
- Initial shuffle never correct; ordering/confirmation deterministic; two-error hint reveals only first card.
- Sequence event once; storage-before-creation event; no caption text payload.
- 12-item cap/no eviction/delete confirm; malformed data recovery; 80-grapheme safety.
- Pointer/focus equivalence, optional-audio fail-soft, cache/idle/safe geometry.

## Local gate

```bash
find activities/tre_carte_una_storia -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_tre_carte_una_storia -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/tre_carte_una_storia
```

Expected: tests and validation exit 0; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_officina_dei_suoni tests.test_activity_posta_di_leo tests.test_activity_tre_carte_una_storia tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with eight portfolio suites and named contracts green.

## Stop conditions

- Any illustration/caption pair is ambiguous or lacks accepted bilingual review.
- Implementation duplicates Teatrino's stage/recording or stores/emits child text outside Activity storage.

## Handoff

Return standard packet plus all eight order fixtures, content/art hash map, storage/event privacy proof, audio fallback result, cache bounds, and SOURCE label.

## Implementation Checkpoint (2026-08-24)

- **Status:** COMPLETED & VERIFIED
- **Activity:** `org.greia.tre-carte-una-storia` (0.1.0)
- **Validation:** `PASS org.greia.tre-carte-una-storia 0.1.0` (sha256 `c077724e4806a7bc9266789074b5abbc867449ef8ccb56278c0cbb815e0410a6`)
- **Tests:** 9/9 tests pass in `tests/test_activity_tre_carte_una_storia.py`, cumulative 145 tests pass, full `make verify` (1,284 tests) passes.
- **Evidence:** DESKTOP VISUAL REVIEW passed with 6 rendered frames in `build/review/tre_carte_una_storia/`.

