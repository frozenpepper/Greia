# Full Parakeet voice corpus replacement — 2026-10-23

## Outcome

The owner's separately versioned production order processed every row in the
frozen `natural-completion-audit-v5/remaining.json` scope. The run ended
`BOUNDED_COMPLETE` with **147 installed replacements, 90 preserved originals,
zero remaining, and zero blocked**. The outcome is not “237 recordings fixed”:
the 90 quality-exhausted rows retain their original audio and receipt for a later
method decision.

The external plan contains exactly 237 rows (44 letter and 193 ordinary cues;
EN15, ES45, FR114, IT63). It authorized up to three *new actual provider calls*
per row, independent of prior attempt history. It used the frozen natural-carrier
phrase/delivery recipe, local Parakeet-TDT v3 model
`mlx-community/parakeet-tdt-0.6b-v3` revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`, and comparison policy
`locale-number-tokens-v3-chck-orthographic`. It did not change production
defaults, thresholds, masters, locale aliases, or historical plans.

There were **498 new provider calls**: 86 cues used one, 41 used two, and 110
used all three. The 147 installed receipts pass final packaged-audio Parakeet
verification; all are still `human_review=PENDING`. For the other 90 cues, all
three authorized generation attempts were quality-rejected, and the original
audio/receipt pair remains installed.

## Frozen scope and transaction audit

The run is
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/`.
Plan SHA-256: `dd8210515c006a974a3ce49771a13f84a2e98c6736f0edc7b1336c5c81b51bf4`.
It pins the remaining-scope SHA-256
`29f125e16c6da5932a7f1fc8b3888f75ac2994f679c56a1405c72bb6a1753879`, scope
audit SHA-256
`35a6f1faf82fb5ceb0c024321f63a3c0d340e75c3d61a219b3677a715b7ec618`, producer
commit `14a93e74c2e66a4492c0b8efc61980e57aa407ed`, selected master identities,
and the separate prior ten-request diagnostic. The producer exited normally
after its `BOUNDED_COMPLETE` result.

The external `terminal-audit.json` revalidated the frozen plan and all **667**
pre-install audio/receipt pairs:

- 147 changed pairs match their retained candidate pair and completed journal
  transaction; each audio and receipt backup hashes to the exact frozen
  original.
- 90 exhausted pairs remain byte-identical to their frozen originals.
- 430 unselected pairs remain byte-identical to their frozen originals.
- All 237 scopes have one to three distinct new job IDs and idempotency keys,
  matching raw output/receipt hashes and the selected speaker master identity.
- No row remains `READY`, `INSTALLING`, or `NEEDS_RECOVERY`; the terminal audit
  reports no errors.

The audit records Parakeet v3 packaged verification and the human-pending state.
Automated screening does not establish pronunciation quality, child usability,
human acceptance, or device/release behavior.

## Listening evidence

The validated, unreviewed Takeboard manifest is
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/takeboard-listening.json`;
it is served locally at [http://127.0.0.1:8818/](http://127.0.0.1:8818/).
It has 1,241 records:

- 498 raw natural-carrier attempts, with prefix-plus-target submitted phrase
  separate from the expected retained target. The disposable prefix was not
  ASR-transcribed; those entries say `NOT_RUN`.
- 583 materialized target-cut candidates, including rejected cuts and their
  exact recorded recognizer transcripts where available.
- 13 retained candidates rejected by delivered/package verification.
- 147 installed final targets, with the exact final Parakeet transcript and
  verification data.

Twenty additional recorded candidate geometries were intentionally not
materialized because their extractor records an explicit insufficient-voicing
or energy precondition. There are no unexplained missing candidate files. All
Takeboard rows start `unreviewed`; no listening decisions were recorded by this
run.

## Verification

Before the live run, focused corpus-policy tests passed 16/16 and the complete
voice-pattern suite passed 231/231 on the producer source pinned above.
Post-run `make verify` was **not green**. It ran 5,833 tests and ended with one
failure, three errors, and eight skips:

- `test_build_profiles.BuildProfileTests.test_all_repository_profiles_are_typed_toml_and_resolve_both_artifacts` errored because the current builder does not implement the `arm64` target adapter.
- `test_installer_state.InstallerStateTests.test_completion_button_writes_the_root_poweroff_marker` and `test_installer_state.InstallerStateTests.test_completion_marker_failure_shows_the_manual_fallback` errored because macOS lacks `lsblk`.
- `test_mbr_observed_identity.ObservationTests.test_foreign_plan_non_disk_and_deferred_adapters` failed because the observed exception text did not contain the expected `legacy-bios-ab-v1` identifier.

No full-suite baseline comparison was performed in this run, so these failures
are reported as observed rather than asserted to be pre-existing. Full log:
`/tmp/greia-parakeet-full237-make-verify.log`.

## Continuation

Listen to the batch and update only its human-review fields. Do not replace the
90 preserved originals or treat the 147 machine passes as accepted recordings
without a separate owner decision. The old natural-context v1 holds and attempt
history remain historical and unchanged.
