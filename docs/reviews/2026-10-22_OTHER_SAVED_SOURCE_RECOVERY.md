# Other saved-source recovery — 2026-10-22

**SOURCE + LOCAL TESTS + SAVED-AUDIO SCREENING + JOURNALED INSTALLATION.**
No new synthesis. Every new receipt remains human-listening-pending.

## Inventory and provenance

Starting from the exact309 remaining IDs after the previous27 saved recoveries,
`collect_history` found660 distinct saved PCM sources covering all309 targets.
270 were already checked in the previous v7 pass and were not rerolled.
Seven other source records had missing source-plan rows or changed-original
identities and were held for explicit reconciliation. The remaining383 sources
for308 targets passed exact source/master/request/original checks.

The new `--source-selection` index permits pinned FAILED/PRESERVED rows, with
unchanged source plan, remaining list, frozen priority, raw and receipt hashes.
`greia_voice_corpus.source_selection` verifies the exact completed job/key,
unsplit recording, text, acting direction, selected voice/reference and provider
output. Existing v6 frozen carrier rows remain unchanged; no older extraction
policy was silently accepted or historical original baseline rewritten.

An initial direct provider/retained WAV hash comparison falsely blocked all383:
provider output is48kHz, while VoiceEngine had packaged retained carriers to
22,050Hz. The corrected validator reproduces the **existing packaging transform**
and requires its exact hash to match the retained source. Positive cross-rate
and wrong-provider-output controls were added. This does not waive a mismatch,
use ASR to prove provenance, or synthesize replacement evidence.

## Actual saved traversal and installation

External evidence root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`

Sources were grouped in a deterministic order by earliest provider creation time
then work path. A target stops at its first passing saved source; no highest-score
selection or repeated ASR reroll. The existing exact audio/locale/Base cache was
used.15 spare sources for already passing targets did not need another trial.

| External pass | Saved sources checked | Installed PASS | Preserved rejection |
|---|---:|---:|---:|
| pass-01 |306|48|258|
| pass-02 |12|2|10|
| pass-03 |33|3|30|
| pass-04 |17|1|16|
| Total |368|54|314|

All54 were installed through existing CorpusRunner/RunStore transactions, with
no provider capability and unchanged final packaged Base/count/numeric/signal
gates. Independent post-install decoding/checking passed all54. Comparing all667
priority audio/receipt pairs against the pre-install snapshot found exactly54
changed and613 unchanged. All54 backup bundles were verified. All383 inventoried
source audio/receipt pairs, source plans and provider manifests, frozen priority
and each recovery budget manifest remained unchanged.

Current classification:292 previously kept +39 previously installed +27 earlier
saved recoveries +54 additional saved recoveries =412 kept/installed, with
**255 remaining**. This does not re-certify the earlier292/39. Remaining budgets
are35 at three takes and220 at two. No take counts were reset or incremented.
`other-saved-recovery/remaining.json` includes exact IDs, budgets and per-target
saved trial findings. Machine rejection is not proof of bad audible speech.

Other durable evidence: `other-saved-source-inventory.json`,
`other-source-preflight.json`, `other-verified-provider-sources.json`,
`other-saved-recovery/progress.json`, pinned selection files and four pass
journals, `install-audit.json`, replay/install audit scripts and ASR/search JSON.

Listening batch: `other-saved-recovery/listening.json`,54 unreviewed installed
files vs selected masters, http://127.0.0.1:8807/. Manifest validation and HTTP200
passed; no browser interaction or human listening acceptance is claimed. The
separate earlier27-file batch on8806 remains intact.

## Completed letter_A job

The preserved job `20261022-142854-3615cf58` was hash-checked against its completed
provider manifest and replayed through v7 with no resubmission. Four independent
PCM candidate suffixes did not meet target verification for `A come Ape`.
`letterA-v7-replay/result.json` retains the transcripts and evidence. No target
was installed. Source media and original receipt are unchanged; this is ASR
screening, not a listening judgment. Never resubmit that completed job.

## Verification and next exact work

- Final voice suite126 PASS, including15 saved-recovery tests and five new
  selection/provenance controls. Existing corpus18 and finisher4 PASS.
- Final source-frozen `make verify PYTHON=/opt/anaconda3/bin/python3`:5,726 tests
  in267.610s;1 failure,3 errors,8 skips — NOT GREEN. Same ARM64 profile error,
  two macOS-missing `lsblk` installer cases and MBR diagnostic expectation.
  Logs: `selection-focused-final.log`, `selection-corpus.log`,
  `make-verify-selection-final.log`. Scoped whitespace check passed.
- Five held source records still concern remaining targets: Italian ask_K,
  ask_O and sunhat lack a source-plan row; English letter_C and French
  find_octopus have an older original baseline. Reconcile exact completed jobs,
  request/master/PCM/receipt provenance and current frozen destination identities
  in an explicit new recovery plan. Do not bypass checks or rewrite old plans.
- Recover any qualifying held sources first. Then account for the35 exhausted
  and220 remaining one-take budgets before an explicitly versioned v7 production
  continuation. Never restart the unchanged historical v6 producer, expand667
  scope, relax approval thresholds or label installed candidates human-approved.
