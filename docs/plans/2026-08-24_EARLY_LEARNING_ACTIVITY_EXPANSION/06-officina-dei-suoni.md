# Session 06 — Officina dei Suoni: phonemes, letters, and word building

**Provider calls:** forbidden; reviewed deterministic/local pedagogical audio only
**Prerequisite:** Sessions 00–05 accepted; Session 00 records exact Officina corpus/status
**Commit:** `feat(activity): add Officina dei Suoni phoneme workshop`

## Outcome

`org.greia.officina-dei-suoni` links reviewed speech sounds to graphemes and bounded word-building challenges without duplicating Sillabe Magiche or Foresta delle Parole.

## Preconditions

- Pull current `main`; verify content/audio evidence and prior gate.
- Read the same specialist routes required by Session 05.

## Allowed files

```text
activities/officina_dei_suoni/**
tests/test_activity_officina_dei_suoni.py
tools/generate_officina_dei_suoni_audio.py
docs/reviews/2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No syllable-catching loop, whole-word initial-letter multiple choice identical to Foresta, unreviewed segmentation, dynamic runtime TTS, microphone, or private font.
- No dormant advanced level when content-lock says `omitted_v1`.

## Evidence and source decisions

IES strongly recommends awareness of speech sounds linked to letters and word-building. The Session 00 corpus is authoritative per locale. Exact package difficulty is mechanically derived from `advanced_corpus.status`, never chosen by this agent.

## Exact implementation

1. Manifest common fields: `org.greia.officina-dei-suoni`, key `activity.officina_dei_suoni.title`; `it,en`; collections `learn,play`; tags `words,puzzles`; education `language,phonemic_awareness,letter_sound,word_building`; difficulty 3, age 5–7; hybrid input; required `display,pointer,audio.basic`, optional `keyboard,touch`; milestone `sound.word_completed`, completion `sound.workshop_completed`; storage 1. If advanced corpus accepted set adaptive 2–5; if omitted set adaptive 1–3.
2. Create thin `main.py` plus `sound_workshop_model/content/services/audio/art/renderer/app.py`. Define `SoundUnit(phoneme,grapheme,audio_id,picture_ids)`, `SoundBox`, `WordChallenge`, `WorkshopSession`.
3. L1 hear isolated phoneme and choose one of three pictures; L2 hear picture word and place its initial grapheme into the first sound box; L3 sort three picture tokens into two initial-sound bays, then build a reviewed word by placing the initial grapheme before a visually grouped remainder.
4. Only when accepted advanced corpus exists: L4 segment a reviewed word into its exact sound-box count; L5 change one reviewed grapheme/sound to make another accepted word. Use exact locale records, never codepoint/letter-count inference.
5. Letter tiles show upper/lowercase together during introduction, then lowercase in building. All text uses Greia typography. Replay speaks isolated sound, then after 0.45 s the whole example word; no mascot imitation.
6. One semantic action handles pointer tile placement and arrow/Space focus activation. Wrong tile returns, plays isolated target only, and highlights the matching mouth/picture motion; it does not advance.
7. Implement SpeechQueue/audio generation/review exactly as Session 05, with separate cue IDs and hashes. Persist `officina_dei_suoni.progress.v1` level/≤8 summaries. Emit milestone per completed word and completion after six.
8. Reuse `character.leo`; create original sound beads, boxes, letter tiles, word machine, picture tokens, icon. Cache glyph/tile/picture/audio resources with finite keys; terminal freezes queue and machine.

## Tests

- Manifest adaptive range exactly matches content-lock advanced status.
- Every phoneme/grapheme/picture/audio ID exists per locale and no code derives segmentation from string length.
- One correct answer each; deterministic distribution; wrong input keeps challenge.
- Speech non-overlap/cancellation; pointer/keyboard equivalence; exact event/idempotency counts.
- Storage ≤8, cache bounds, terminal freeze, protected input, READY after first frame.

## Local gate

```bash
find activities/officina_dei_suoni -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_officina_dei_suoni -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/officina_dei_suoni
```

Expected: tests/validation exit 0; audio hashes/reviewer record complete; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_officina_dei_suoni tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with six portfolio suites and named contracts green.

## Stop conditions

- Corpus/audio review is incomplete or phoneme truth must be inferred from spelling/string length.
- The implemented loop collapses to Foresta's whole-word initial-letter choice or Sillabe's syllable catching.

## Handoff

Return standard packet plus content status, phoneme/grapheme/audio parity, queue/input proof, six seeded challenges/level, event/cache hashes, and SOURCE label.

## Implementation Checkpoint (2026-08-24)

- **Status:** COMPLETED & VERIFIED
- **Activity:** `org.greia.officina-dei-suoni` (0.1.0)
- **Validation:** `PASS org.greia.officina-dei-suoni 0.1.0` (sha256 `f5a2b8ce18e298a281affcd917a5570f5b1d92779bfc5ec4dd52a7d9d570fd9c`)
- **Corpus & Audio Review:** 70 audio clips generated and reviewed in `docs/reviews/2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md`
- **Tests:** 11/11 tests pass in `tests/test_activity_officina_dei_suoni.py`, cumulative 125 tests pass, full `make verify` (1,257 tests) passes.
- **Evidence:** DESKTOP VISUAL REVIEW passed with 5 rendered frames in `build/review/officina_dei_suoni/`.

