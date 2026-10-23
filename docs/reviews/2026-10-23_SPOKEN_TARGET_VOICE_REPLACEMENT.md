# Spoken-target voice replacement — terminal evidence

**Status:** bounded generation and transaction scope complete; human listening
pending. This records the owner-authorized v4 run and does not accept audio or
close a Greia architecture/release phase.

## Frozen operation

- Source revision: `7004b6188573efa4bd126c4af1e2b6f42a4a98f4`.
- Plan: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/spoken-target-recovery-v1/natural-v4-run-02/plan.json`
  (SHA-256 `1e408d7a0f663d3f24faa39803791f413683e85333fa30e06c45437355561b3c`).
- Scope: 77 exact remaining cues after the separate 13-cut human-approved
  recovery: 16 contextual letter examples, 7 already-worded number cues, and
  54 ordinary cues. The source semantic text and selected master identities
  were pinned; spoken letter names were a versioned separate target.
- Policy: `automatic-natural-context-parakeet-v4-spoken-target-v1`, comparison
  `locale-number-tokens-v4-spoken-target-v1`, locale-spelled-target policy
  `locale-spoken-letter-and-cardinal-v1`.
- Verifier: `mlx-community/parakeet-tdt-0.6b-v3`, revision
  `ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`. Each cue had a maximum of three
  fresh provider calls, stopping on first final packaged PASS. No retry was
  made for provider/ASR/IO uncertainty.

## Terminal result and audit

The producer ended `BOUNDED_COMPLETE`: **25 installed packaged PASS**, **52
PRESERVED** after quality rejection, **0 remaining**, **0 blocked**, and **199
actual provider calls**. Every generated replacement receipt remains
`human_review=PENDING`; automated verification is not listening acceptance.
The 13 previously recovered exact Takeboard approvals remain separate human
review evidence and are not counted in the 25 automated passes.

`terminal-audit.json` independently checks all 667 audio/receipt pairs against
the post-recovery preinstall snapshot. It passed with exactly 25 journaled
candidate pairs installed, each original backed up byte-for-byte, 52 exhausted
cue pairs unchanged, and 590 other pairs unchanged. The audit also confirms
the installed receipts carry the pinned Parakeet model and comparison policy.

External run directory:

`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/spoken-target-recovery-v1/natural-v4-run-02/`

It contains the frozen plan, reservations, per-attempt WAVs and receipts,
candidate cuts/search witnesses, packaged candidates, exact backups, terminal
progress, and the full audit. Takeboard batch
`takeboard-natural-v4-run-02.json` validates with 475 entries: 199 raw
carriers, 251 extracted candidates and 25 installed finals. It displays the
full submitted phrase, expected retained spoken target, and exact available
Parakeet transcript; raw composite carriers are explicitly labeled
`NOT_RUN_DISPOSABLE_CARRIER`. New entries are unreviewed. Listening page:
`http://127.0.0.1:8819/`. Prior review files, including Takeboard 8818, were not
modified.

## Verification

- Focused spoken-target voice pattern: **237/237 PASS** on source revision
  `7004b618` using `/opt/anaconda3/bin/python3` with
  `PYTHONPATH=src:tools:tests`.
- `make verify PYTHON=/opt/anaconda3/bin/python3`: **NOT GREEN**, 5,839 tests,
  2 failures, 3 errors and 8 skipped. The launcher title parity failure is
  reproducible from two dirty preinstall-snapshot files outside this 77-row
  scope: `activities/colline_allegre/locales/fr/audio/activity-title.wav` and
  `activities/corsa_bacche/locales/en/audio/activity-title.wav` are not the
  required 22,050 Hz; both bytes were unchanged by this run. The other failure
  is `test_foreign_plan_non_disk_and_deferred_adapters`, whose observed MBR
  error text omits the test's expected `legacy-bios-ab-v1`. Errors are one
  ARM64 Phase-0 target-profile builder support error and two installer tests
  that require unavailable macOS `lsblk`. No baseline comparison is claimed.
- Full log: `/tmp/greia-spoken-target-make-verify.log`.

No generated output in this run has been manually heard or owner-accepted.
Next step is human review in the v4 Takeboard session; preserve rejected and
unreviewed outcomes without another recording run unless the owner gives a new
direction.
