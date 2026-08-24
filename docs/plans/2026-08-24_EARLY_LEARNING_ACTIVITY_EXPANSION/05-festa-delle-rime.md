# Session 05 — Festa delle Rime: rhyme and alliteration

**Provider calls:** forbidden; reviewed deterministic/local pedagogical audio only
**Prerequisite:** Sessions 00–04 accepted; Session 00 rhyme/sound records all accepted
**Commit:** `feat(activity): add Festa delle Rime listening game`

## Outcome

`org.greia.festa-delle-rime` launches as an audio-first eight-match rhyme/alliteration game whose Italian and English corpora/audio are independently reviewed and whose printed text never reveals an answer.

## Preconditions

- Pull current `main`; verify prior cumulative gate and content hash.
- Read Activity core/engineering/terminal/achievement/discovery/voice routes and visual authorities.
- Confirm an already configured deterministic/native pedagogical speech path plus named fluent reviewers; do not install/download a voice toolchain.

## Allowed files

```text
activities/festa_delle_rime/**
tests/test_activity_festa_delle_rime.py
tools/generate_festa_delle_rime_audio.py
docs/reviews/2026-08-24_FESTA_DELLE_RIME_AUDIO_REVIEW.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No character cloning, downloaded model, arbitrary host voice in place of a mascot, microphone, spelling test, printed rhyme ending, or translation-derived corpus.
- No overlapping speech/SFX and no per-click event.

## Evidence and source decisions

Head Start places rhyme/alliteration in preschool phonological awareness before print. IES supports deliberate sound-segment work. The Session 00 corpus is authority; recordings are pedagogical speech, not Leo dialogue.

## Exact implementation

1. Manifest: `org.greia.festa-delle-rime`, key `activity.festa_delle_rime.title`; `it,en`; collections `learn,play`; tag `words`; education `language,phonological_awareness,rhyme`; difficulty 2, age 4–6, adaptive 1–4; pointer; required `display,pointer,audio.basic`, optional `touch`; milestone `rhyme.match_completed`, completion `rhyme.festival_completed`; storage 1.
2. Create thin `main.py` plus `rhyme_model/content/services/audio/art/renderer/app.py`. `RhymeItem` contains semantic/picture/audio IDs only; `RhymeChallenge` stores target, three choices, answer, mode; `RhymeSession` owns eight challenges.
3. L1 choose one of two pictures that rhymes after hearing target; L2 one of three; L3 identify the non-rhyming picture among three; L4 use the accepted alliteration families and choose same initial sound. Never show answer words during the decision.
4. Generate balanced eight-challenge sets with each accepted pair used at most once, unique picture choices, no semantic duplicate, deterministic seed, and no immediate repeated answer slot.
5. Replay button repeats target. Wrong choice plays choices sequentially with 0.45 s gaps and highlights mouths/lanterns, then restores the same challenge. Correct sequence is target word → matched word → nonverbal chime → next target after 0.90 s.
6. Implement bounded `SpeechQueue` length four with cancellation on new set/STOP. Decode reviewed clips once; speech and SFX use separate channels with explicit exclusion.
7. Audio tool accepts `--locale it|en --output-dir <outside-package-review-dir>` and writes WAV masters plus SHA manifest; no network. Human review checks every word for correctness, clipping, stress, noise, and cue/file mapping. Copy only accepted OGG/WAV files into package and record hashes.
8. Persist `festa_delle_rime.progress.v1` with level/≤8 summaries; emit exact events once.
9. Reuse `character.leo`; create/adapt lantern/picture-token art and distinct icon. No words in art. Cache finite picture/audio surfaces. Terminal freezes animation and queue.

## Tests

- Package corpus equals accepted content-lock IDs/hashes; both locales complete and independently mapped.
- Every challenge has one correct answer and no written answer leakage.
- Deterministic level/mode distribution and no repeated answer slot.
- Speech queue never overlaps, stays ≤4, cancels stale cues, and sequences exact gaps with fake clock/audio.
- Wrong/replay keeps challenge; eight correct emits one completion; storage/cache/terminal/safe-input contracts.

## Local gate

```bash
find activities/festa_delle_rime -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_festa_delle_rime -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/festa_delle_rime
```

Expected: tests and validation exit 0; every packaged clip hash appears as accepted in the audio review; no bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_festa_delle_rime tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with five portfolio suites and named contracts green.

## Stop conditions

- Any cue lacks fluent human approval or the local deterministic toolchain is unavailable.
- Text/orthography reveals a listening answer or two speech/SFX streams overlap.

## Handoff

Return standard packet plus corpus/audio hash parity, reviewer disposition, queue timing proof, challenge matrix, event counts, asset hashes, and SOURCE label.
