# Shared Character Reactions v0.1 — Retired

**Status:** RETIRED 2026-08-28 (superseded by `v0.2`)
**Replaced by:** `assets/audio/characters/shared/v0.2/`
**Reason for supersession:** v0.1 was generated on 2026-08-23 from an older Voice Production
Engine build that contained a token-budget heuristic (`_token_budget()`) and an internal-pause
truncation path in `ChatterboxMLXProvider._trim_audio()`. Both behaviours clipped ordinary
short speech, including all 5 natural characters on the most-used 1–3 word reactions.

**What changed in v0.2:**
- `_token_budget()` removed (provider no longer derives an acoustic-token ceiling from text
  word count). Commit `f8b33ad` "Voice skill: make ASR warnings actionable and remove token
  heuristics".
- `_trim_audio` no longer stops at the first internal gap > 120 ms for short phrases; outer
  silence trim only. Commit `1eb4169` "Voice: preserve internal pauses in short Chatterbox
  speech". Commit `fcc9a17` "Voice docs: forbid internal-gap truncation".
- Same canonical voice anchors (Lilli/Leo/Flash/Tito/Momo `.flac` SHA-256 unchanged) and
  same `voice_registry_version = v0.1`.
- Same character + family + variant + locale matrix (6 × 5 × 3 × 2 = 180 shared reactions).
- v0.2 additionally includes 12 character introductions
  (`character.intro.{lilli,leo,flash,dani,tito,momo}` × 2 locales) which v0.1 did not ship.
- Dani continues to use `macos-native-say` (intentionally robotic, no cloned natural voice).

**Why the audio bytes are different:** the v0.1 engine build produced clips that are not
byte-identical to v0.2 for the same text, because the model ran with different (shorter)
token caps and the trim path cut internal pauses. Both versions are valid renderings of
the same canonical text under the same canonical voice reference. v0.2 reflects the
post-`1eb4169` engine contract.

**Owner decision:** 2026-08-28 in-session listening authorization. The owner listened
to the v0.2 candidate set end-to-end, accepted the full 192 clips (180 shared + 12 intros)
including the 27 clips on which `mlx-whisper-tiny` returned `WARN` (verifier noise on
Italian diacritics and 3-syllable exclamatives, not real audio defects). The owner's
authorization and the per-clip `OWNER_ACCEPTED` stamp are recorded in the v0.2 manifest,
review.csv, and engine receipts.

**What is preserved here:** the v0.1 manifest.toml, review.csv, and 150 `.wav` files are
intentionally retained on disk as historical evidence of the 2026-08-23 acceptance ledger
and the engine-state-at-the-time. They are no longer runtime-resolved; the runtime shared
library now resolves from `v0.2/`. Do not delete v0.1; do not regenerate v0.1 against
the current engine (the byte mismatch would not be a meaningful regression test).
