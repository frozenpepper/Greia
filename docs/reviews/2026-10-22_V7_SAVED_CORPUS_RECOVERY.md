# V7 saved corpus recovery — 2026-10-22

**SOURCE + LOCAL TESTS + SAVED-AUDIO SCREENING + JOURNALED INSTALLATION.**
Human listening remains PENDING. This follows the separately versioned
[target-only extractor correction](2026-10-22_TARGET_ONLY_VOICE_EXTRACTION_V7.md).

## Implementation

`tools/recover_voice_candidates.py` creates a new external plan with
`saved_recovery_policy=target-only-v7-saved-v1`. It selects source-journal FAILED
rows only, validates membership and exact semantic fields against the existing
priority JSON, checks original destination audio/receipt and selected registry,
and reuses existing `prepare_saved_candidate` source/master/request validation.

`greia_voice_corpus.saved_recovery` explicitly maps v7 policy/status fields for
CorpusRunner without rewriting historical carrier scripts or extraction policies.
The effective v7 policy remains recorded. Final count/numeric comparison is
required after packaging and recomputed from the retained delivered transcript
when validating installation. Unknown plan policies reject. Existing v6 behavior
is retained outside the explicit saved-recovery plan.

The adapter's engine only packages audio; its generation method raises.
CorpusRunner independently forbids generation for saved-recovery plans even if a
candidate is absent/partial. Cumulative take counts are copied from history,
never incremented/reset by recovery. New synthesis remains stopped.

Stage and install are separate commands. A complete stage records plan, budget
and results identities. Installation checks them and reuses existing RunStore
backups, destination-change checks and crash recovery. No new transaction system
or automatic human approval was added. Exact commands and fault procedures:
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` § V7 saved-provider recovery.

## Actual operation

External root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`

- Source: priority continuation03 `fresh-01`, all **297 FAILED** rows.
- New plan/work: `v7-saved-corpus-recovery-01`.
- Frozen priority SHA256:
  `65e0bd703ea8ce46ee83ebf1ba6d2c268696d517180f0912c053e18012c11ba9`.
- Stage: **27 passing / 270 rejected saved takes**, matching the earlier broad
  final replay (267 extraction rejections plus3 final-quality warnings).
- Install: **27 DONE / 270 PRESERVED**. No new provider submissions.
- Retained cumulative budgets across297:286 rows at2 takes,11 at3; unchanged.
- Every installed receipt retains `human_review=PENDING`.

The post-install audit independently decoded actual installed media, applied the
same final target-quality checks and verified the selected master/hash identities.
It also compared all667 priority audio/receipt pairs with a before-install
snapshot: **exactly27 passing pairs changed;640 others unchanged**. All297
original source audio/receipt pairs, source plan, frozen priority JSON and budget
manifest remained unchanged. All27 journal backup bundles were hash-verified.
Per-file evidence is in `v7-install-audit.json`, stage/results JSON, source/cut
receipts, search evidence, install log and `audit-v7-installed-recovery.py`.

Previous continuation classification292 kept +39 installed +27 new recoveries
leaves **309 unresolved**. `v7-priority-remaining.json` records that exact list;
the old stopped producer's progress file was not rewritten. The309 include39
budget-limited cues omitted from fresh-01. No new review of the prior kept292 or
installed39 is implied by these totals.

Takeboard `v7-recovery-listening.json` contains only the27 recovered installed
files, all unreviewed, compared with their selected masters. Served at
http://127.0.0.1:8806/; CLI manifest validation and HTTP200 passed. No browser
interaction or human listening assessment was performed in this tranche.

## Verification

- Focused voice suite: **121 PASS**, including10 new saved-recovery tests.
  Tests cover actual synthetic PCM packaging, no-provider installation/resume/
  restore, interrupted audio/receipt transaction recovery, absent-candidate
  synthesis prohibition, request mismatch, required verification, explicit plan
  opt-in, extra words, wrong numbers, changed scope/originals/budget manifest.
- Existing corpus suite18 PASS; priority finisher4 PASS.
- Final source-frozen `make verify PYTHON=/opt/anaconda3/bin/python3`:
  **5,721 tests in254.003s;1 failure,3 errors,8 skips — NOT GREEN**.
  Same previously observed ARM64 profile-resolution error, two installer tests
  requiring unavailable macOS `lsblk`, and MBR diagnostic expectation failure.
- Logs: `recovery-focused.log`, `recovery-corpus.log`,
  `make-verify-recovery-v7.log`. Scoped whitespace check passed.

## Remaining authorized work

Recover other preserved raw sources for the309 exact remaining IDs before any
new synthesis. Older extraction/model metadata needs an explicit recovery
adapter extension rather than mutation of frozen plans or permissive bypasses.
Check exact original request, selected master, job/key and source/receipt hashes;
retain cumulative three-take budgets. Completed letter_A job
`20261022-142854-3615cf58` remains in `letterA-provider-job/` and must never be
resubmitted. The unchanged historical v6 producer stays stopped. Deferred scope,
new-synthesis authorization gates and human listening remain distinct.
