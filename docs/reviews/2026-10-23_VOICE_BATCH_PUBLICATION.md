# Voice batch publication — 2026-10-23

Owner requested committing the remaining recent voice work after the parent
agent's direct committed/local audit. This publishes the pending recordings;
it does not retrospectively approve listening-pending character takes.

## Scope

- 683 replacement audio/receipt pairs, including all 667 priority replacements
  and 16 additional earlier short-carrier replacements.
- Existing changed Activity audio checksum catalogues and shared character
  manifest/review rows are published with their corresponding audio.
- All 45 built-in Activities retain their audio paths. The independent review
  found no missing current or committed corpus files, 2,327 selected-language
  Activity resolver lookups and 724 shared lookups without missing-language
  fallback. The corpus contains 4,915 tracked audio files.
- The final 237-cue resolution comprises 147 initial Parakeet installations,
  13 exact owner-approved saved recoveries, 25 spoken-target installations,
  and 52 native system-TTS fallbacks. The 52 carry the owner's explicit
  review waiver. Existing pending, approved and waived states remain distinct.
- The exact published path/hash/voice/review inventory is
  `2026-10-23_VOICE_BATCH_PUBLICATION_FILES.csv` beside this report.

## Pre-publication repair

Twelve owner-approved recovered targets had been copied at native 48 kHz.
The parent repackaged those exact bytes through the existing AudioPipeline
into 22,050 Hz mono PCM16, without synthesis or ASR. Original generation dates,
semantic scripts, recognition evidence and human APPROVED states were retained.
Receipts now bind the new output hashes and bytes and explicitly identify the
previous machine-verification source hash in `delivery_format_normalization`.
Original audio/receipts and each installation are backed up and transactionally
journaled under the external publication workspace.

The eleven stale Officina dei Suoni checksum entries were refreshed against
the existing audio, without replacing or regenerating those phonics files.

External publication workspace:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-parent-audio-publication-v1/`

Original direct review and detailed per-Activity census:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-parent-full-audio-review-v1/`

## Verification

- 4,743 receipt/audio pairs: output hashes agree; no orphan receipts.
- All seven Activity checksum catalogues and shared manifest rows: hashes agree.
- Activity title audit: 180/180 complete, no missing text, mapping, file or
  unsafe path; previously two titles failed only their 48 kHz delivery format.
- Collection labels: 84/84 complete.
- Full `make verify PYTHON=/opt/anaconda3/bin/python3`: NOT GREEN; 5,845
  tests, 6 failures, 3 errors, 8 skipped (278.488 seconds). Log:
  `/tmp/greia-audio-publication-make-verify.log`.
  Three Word Forest subtest failures expect PENDING for EN/ES/FR cue receipts
  that truthfully carry the owner-authorized native fallback WAIVED_BY_OWNER
  state; the review waiver was not falsified to satisfy those assertions.
  Remaining failures: the MBR diagnostic message expectation and two Parent
  client Wi-Fi source-contract assertions. Errors: ARM64 profile support and
  two installer tests requiring macOS-unavailable lsblk. No unrelated source
  or test changes were added to this audio publication.

No source implementation or voice identity changed in this publication. The
unrelated October 19 draft review, `final.mp4` and `launch-video/` remain outside
this commit. New audio is not claimed heard merely because it is committed.
