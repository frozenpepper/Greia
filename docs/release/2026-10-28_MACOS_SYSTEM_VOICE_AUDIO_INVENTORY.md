# macOS System Voice audio inventory — public-release rights review

Date: 2026-10-28 · Status: **ACTIVE PUBLIC-RELEASE BLOCKER**
Machine-readable inventory:
[`2026-10-28_MACOS_SYSTEM_VOICE_AUDIO_INVENTORY.csv`](2026-10-28_MACOS_SYSTEM_VOICE_AUDIO_INVENTORY.csv)

## Why this is a blocker

627 committed recordings currently carry a `.receipt.json` whose
`provider_id` is `macos-native-say`. They were produced with Apple's macOS
`say` command and a macOS System Voice. Apple's published macOS Tahoe 26
software license, section 2.F, permits System Voices for personal,
non-commercial creation but expressly restricts recording, publishing and
redistribution in public, nonprofit or commercial contexts. Earlier macOS
licenses contain substantially similar restrictions. Owner listening
approval is a quality decision, not a redistribution licence.

The current public-release image must not redistribute these files unless
Apple grants a separate permission, or competent counsel identifies another
applicable grant for the exact generating system and voices. A repository
whose full history is made public publishes them as well; deleting them
from the current tree is not a rights remediation.

## Exact current-tree inventory

| Dimension | Count / detail |
|---|---:|
| `macos-native-say` receipt records | **627** |
| Voices | Samantha 179, Alice 160, Thomas 152, Mónica 136 |
| Locales | en 179, it 160, fr 152, es 136 |
| Kinds | pedagogical speech 575, character dialogue 52 |
| Review state | APPROVED 575, WAIVED_BY_OWNER 52 |
| Corpus-replacement records | 52 (all owner-waived, none claimed machine-approved) |
| In shared `assets/audio` (used by every image) | **60** |
| In the 32-activity draft release roster | **197** |
| In built-in activities withheld from the draft roster | 370 |

Per-activity counts in the current tree:

| Scope | Recordings |
|---|---:|
| `assets/audio` shared system audio | 60 |
| `activities/sillabe_magiche` | 355 |
| `activities/foresta_parole` | 146 |
| `activities/officina_dei_suoni` | 33 |
| `activities/alfabeto_leo` | 4 |
| `activities/festa_delle_rime` | 4 |
| `activities/quattro_amici` | 4 |
| `activities/sottomarino_giramondo` | 4 |
| `activities/workshop_settings` | 3 |
| `activities/pasticceria_magica` | 2 |
| 10 other single-file Activities | 10 |

Even the curated 32-activity draft roster would still ship **257** affected
files (197 activity-local + 60 shared). The current technical-preview
composition, which installs all 45 built-in Activities, ships all **627**.

The previous `NOTICE.md` estimate of "about 1,350" was a production-run
cue count, not a current-tree receipt count. It is corrected here and in
`NOTICE.md`.

## Redistribution alternatives

1. **Replace with VoxCPM2/VoxStage speech (preferred).** The selected
   generated-voice stack is documented as Apache-2.0
   (`openbmb/VoxCPM2`) and the retained Chatterbox path as MIT. Generate
   the same cue text with the existing `tools/greia_voice.py` pipeline and
   the current character/pedagogical routes, keeping deterministic isolated
   letters and syllables. This requires new receipts and **fresh owner
   listening approval**; quality approval of the current files is not
   transferable.
2. **Use another redistributable TTS for pronunciation-authoritative
   cues.** Keep the existing deterministic letter/syllable policy, but use
   a provider whose output licence is documented for public distribution.
   Do not silently substitute a different voice for owner-approved
   character dialogue.
3. **Obtain written permission from Apple** for the exact voices and
   redistribution context. No such permission is recorded.
4. **Exclude the affected material from a public snapshot** (source or
   binary) and clearly label those Activities as unvoiced/development-only.
   This is a rights-safe fallback, not a complete product; it does not by
   itself remove copies from the existing Git history.
5. **Keep the repository/image private** until option 1, 2 or 3 is
   completed and the replacement audio is accepted.

## What this does not affect

The VoxCPM2/VoxStage-generated recordings (4,115 receipt records) and the
retained character masters are a separate provenance question. VoxCPM2 is
Apache-2.0 and Chatterbox is MIT; the v0.1 source masters are recorded as
project-owner-supplied synthetic voice-design recordings with a pending
asset-licence decision. They are not covered by Apple's System Voices
restriction.

## Safe public-source options

- Publish a **rights-cleared source snapshot in a new repository** that
  excludes the 627 say recordings and their receipts, with a written
  inventory and a build-time guard. Do not rewrite the existing shared
  history.
- Or keep the existing repository private until replacement audio is
  produced, listened to and accepted. A later clean history rewrite would
  still require explicit owner authorization.
