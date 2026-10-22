# Normal-period intro and warm clear reading — 2026-10-22

## Owner direction and implemented defaults

The owner requested a normal period after the spoken intro and direction about
clear reading, a warm tone and careful pronunciation. Normal VoiceEngine short
requests now compose `native intro.\n\nexact target`, without an ellipsis.
Receipt composition policy is `period-separated-intro-v1`. All six default
entries in `character_delivery.json` now read:

> Read clearly in a warm, calm tone. Pronounce every word carefully and naturally.

The separate silent-pause/final-target instruction is retained. Explicit request
delivery may override the default. Selected masters, target wording, Base/accent
policy, canonical count/number comparison and signal thresholds are unchanged.
Historical recording plans and original receipts retain their real prompts.

## Remaining saved-source reconciliation

The five held sources were reconciled against exact completed job/key/media,
actual provider script/direction/master, and independently matching current
frozen destination rows. A new saved processing plan records both source and
baseline provenance; no old plan or raw receipt was rewritten. Native prefix
variants included the historical normal-period+space form.

Four failed unchanged v7 extraction/quality checks. English `letter_C` passed
and was installed through the existing saved-only CorpusRunner transaction.
All667 priority pairs were checked: exactly that one audio/receipt pair changed,
666 unchanged. All five source pairs and baseline plans, plus cumulative budgets,
remained unchanged. Human review PENDING; no new corpus generation.

Total saved recoveries are82 (27+54+1). Current classification is413 kept/installed
and254 remaining:34 exhausted at three takes,220 with two prior attempts.
External evidence: `held-source-reconciliation.json`, `held-reconciled-v7/` and
`after-held-remaining.json` under the existing rejection-investigation directory.

## Versioned normal-API final-take adapter

`greia_voice_corpus.automatic_generation` and
`tools/continue_voice_priority_v7.py` prepare/run the last remaining take through
normal VoiceEngine, with short mode ON, required verification and max_attempts1.
Existing CorpusRunner owns cumulative reservations and installation. Its new
plan policy is `automatic-short-v7-period-warm-v2`; old carrier metadata is kept
as `previous_carrier_plan` instead of adding a second intro.

A known durable one-take `FAILED_QUALITY` result becomes PRESERVED/exhausted,
retaining originals and evidence. Provider/ASR/IO uncertainty stops NEEDS_RECOVERY.
Complete candidates can recover without new submissions. Result.evidence_dir
is a structured lifecycle-state path, avoiding error-message parsing. Final
candidate validation checks the exact target, composition, selected master,
raw provider evidence and delivered canonical/signal gate. No separate verifier
queue was implemented or claimed.

`final-take-v7-01` was PREPARED only and is explicitly SUPERSEDED_UNSTARTED after
the owner changed direction. New `final-take-v7-02` contains220 exact final-take
rows and excludes34 exhausted IDs. **Neither batch has submitted a job.** The
new batch remains paused because the live readiness experiment below failed.

## Real saved provider-rate regression check

Before fresh prompt probes,24 existing completed48kHz provider sources were
selected from known prior recoveries, spanning13 actual actor/locale pairs and
all four languages. These exercise the normal automatic pipeline's native source
rate, separately from the earlier22,050Hz retained-source replays.

With unchanged extraction/packaged quality rules:20 passed,4 held; all24 extra-
word negative controls rejected. This met the predeclared minimum20/24 and zero
negative false accepts. It is not a listening test, a new synthesis experiment,
or proof that all old machine passes survive a source-rate change.
Evidence: `provider-48k-probe/{registered-scope.json,results.json}`.

## Twelve fresh period/warm probes

Fixed before observation: three examples per language, all six selected actors
appearing twice, one provider take per diagnostic cue, separate from production
budgets. Readiness required at least9/12 machine passes and at least2 per language;
per-recording target/cut/signal thresholds were unchanged.

Result: **8 PASS /4 rejected** — EN1/3, IT3/3, FR2/3, ES2/3.
The readiness gate was **not met**; do not launch the220-file batch unchanged.
No diagnostic target was installed into runtime assets. Warmth/style is unreviewed.

Flagged cases: EN Leo `Find Luna` retained a candidate recognized as
`Lister will find Luna.`; EN Tito `Count to ten` recognized `How to 10` (score.7732);
FR Leo `Trouve Luna` recognized `Lansing True Luna`; ES Lilli `El sombrero` had no
eligible cut. These are machine findings, not proof of what a listener hears.
Saved raw/candidate PCM and search observations must be inspected next, without
silently lowering guards or repeatedly rerolling recognition.

The first diagnostic POST timed out after30s although job
`20261022-164343-32d0f10e`, key `greia-984b905bb661433cbc5681ccf24c52ad`, was accepted
and completed in36s. Its exact output/request/master were recovered without a
new submission. The completed cohort contains12 distinct provider jobs: that
recovered job plus11 further submissions. Original timeout evidence is retained.
VoxStageClient now has configurable `GREIA_VOXSTAGE_HTTP_TIMEOUT` (default120s,
allowed1–7200), distinct from job wait. POSTs are still never automatically retried.
No shared service was restarted or cancelled.

External evidence: `period-warm-probes/` original timeout;
`period-warm-probes-resumed/{registered-scope.json,results.json,progress.json}`;
probe/recovery/export scripts and logs. Listening page http://127.0.0.1:8808/:
raw rows show the complete script and are NOT target passes; final rows are
machine PASS; available rejected candidate cuts are explicitly labelled. A case
without a cut has only raw audio. All human states are unreviewed. Manifest
validation and HTTP200 passed; no browser/listening acceptance is claimed.

## Source verification and next exact action

Focused voice137 PASS, corpus18 and finisher4 PASS; VoxStage adapter/client21
PASS, including response-timeout configuration and single-POST control. New
normal-API corpus tests cover single remaining take, no extra submission after
quality exhaustion/uncertainty, required verification, budget guards, candidate
recovery, target-guard validation and immutable preparation. Both22,050/48kHz
synthetic matrices cover all six actors ×four languages.

Final source-frozen `make verify PYTHON=/opt/anaconda3/bin/python3`:5,738 tests
in446.233s;1 failure,3 errors,8 skips — NOT GREEN. Same ARM64 profile, two missing
macOS lsblk installer cases and MBR expectation. Log:
`make-verify-period-warm-final.log`; focused logs and scoped whitespace evidence
are external. No release/hardware or human-listening closure is claimed.

Next inspect the four live failed raw/candidate waveforms and exact transcripts,
determine whether the intro boundary, target pronunciation or recognition is the
first divergence, and prove any correction with saved-audio controls before new
synthesis. Keep the owner-requested period/warm direction. Do not restart frozen
v6 production, mutate frozen plans, spend exhausted budgets or resubmit any
completed letter_A, sunhat or first-diagnostic job.

## Saved-audio sample-rate and boundary investigation (15:16 UTC continuation)

A fixed paired experiment replayed all12 fresh probes and the existing24-source
benchmark after the existing AudioPipeline converted complete native sources to
22,050Hz mono PCM16 **before** extraction. No synthesis, gain adjustment, prompt,
cut padding, comparison threshold or installation changed. Source hashes were
checked before/after. All36 extra-word negative controls rejected.

- Fresh cohort remains8PASS/4rejected; all eight prior passes retained.
- Saved benchmark improves20/24 to24/24 with canonical preprocessing.
- The four fresh failures remain the same; sample rate does not resolve them.

This establishes a useful preprocessing candidate, not a production change or
permission to launch220. Experiment code and registered predicates are external:
`canonical-rate-probe/{registered-scope.json,results.json,progress.json}` and
`probe-canonical-rate.py` under the existing rejection-investigation directory.

A separate diagnostic measured every quiet run down to10ms without changing
production's200ms acceptance floor. Spanish Lilli's largest eligible internal
quiet run is160ms: its rejection is an actual gap-floor rejection, unchanged
at both sample rates. The other three failed sources have measured gaps820ms
(EN Leo),370ms (EN Tito),1,260ms (FR Leo), so they are not missing-pause rejects.
Across all12 sources, the largest measured internal quiet runs range160–1,260ms;
the requested two-second pause is not reliably realized by the provider.

One cached full-source Base observation per failed source was used for diagnosis
only, never as an extraction prerequisite or acceptance vote. It places the
intro before the selected gaps and still reports mismatching target speech
AFTER those gaps: EN Leo `Aliciril find Luna`, EN Tito `Howt to ten`, FR Leo
`L'ending true Luna`. The target-only observations likewise mismatch. Thus there
is no evidence that simply moving a cut later safely recovers the exact intended
words. These ASR observations cannot distinguish pronunciation defects from
recognizer errors or certify audible words. Spanish full-source ASR reports the
expected intro and `el sombrero`, but timestamps are not a substitute for a safe
PCM boundary. Do not use expected-text alignment to manufacture a passing cut.
Evidence: `period-failure-diagnosis.json`, `period-gap-measurement.json`.

Next: independently assess the canonical-preprocessing extension against wrong-
number and prefix-leak controls as well as the extra-word controls, then wire it
through an explicitly versioned recipe only if those gates hold. The remaining
fresh failures still require a bounded, separately evidenced generation/readiness
decision; no threshold relaxation, automatic bulk launch or new production take
is justified by this saved-audio experiment. Counts remain413 kept/installed,
254remaining (34 exhausted,220 final-take-eligible); all human reviews unchanged.

## Additional canonical-source controls and bounded retry experiment

Saved-audio controls now exercise the actual final target checker with the full
uncut intro+target supplied as delivery (36 sources), plus v7 extraction against
17 deliberately wrong-number expectations after canonical preprocessing. All53
reject; zero false accepts; original source hashes unchanged. These complement
the previous36 extra-word controls. Registration/results/progress and script:
`canonical-controls/` and `probe-canonical-controls.py` under the external
rejection-investigation root. The diagnostic harness's placeholder model label
is not a production receipt; actual observations come from the pinned exact
Base cache. No controls are installed or accepted.

A separate bounded diagnostic experiment now completes the existing twelve-case
cohort's three-take budget for ONLY the four failed cases: one prior take plus
at most two additional normal automatic-engine attempts each (maximum8 new jobs).
The eight passing original cases are retained, not regenerated. It preserves
the period/warm prompt, native source v7 pipeline and all individual gates; it
does not yet integrate canonical preprocessing. This tests the actual retry
contract, since the earlier first-take experiment intentionally disabled retries.
The first-take gate remains FAILED, regardless of later results. New three-take
cohort criterion was registered before any submission: at least9 final passes
and at least2 per language. This is a separate experimental outcome; it cannot
be reported as the first-take gate succeeding. Production budgets are untouched,
no installation occurs, and an uncertain job stops without resubmission.
Current process/log/evidence: `probe-period-bounded-retries.py`,
`period-bounded-retries.log`, `period-bounded-retries/{registered-scope.json,
progress.json,results.json,evidence/}`. Inspect current progress before any
further work; do not duplicate this experiment or launch the220 production rows.

## Retry results and source-frozen final-take continuation

The bounded retry experiment completed with6 distinct additional completed jobs,
18 diagnostic jobs overall. EN Leo `Find Luna` and ES Lilli `El sombrero` pass
on their second cumulative take (actual packaged Base1.0, no flags). EN Tito
`Count to ten` and FR Leo `Trouve Luna` still reject after three cumulative takes.
They retain wrong/extra-word target observations; no rejection was overridden.
Final cohort:10/12 machine passes (EN2,IT3,FR2,ES3), satisfying the separately
preregistered **three-take** criterion. Original first-take result remains8/12,
FAILED. Two diagnostic cases are exhausted. No diagnostic audio was installed.

The37-row comparison preserves the original raw/final/rejected rows and adds
all six retry raws and available final/rejected cuts, each linked to its exact
job and master: http://127.0.0.1:8809/ . Original8808 and human review saves were
not changed. CLI schema validation and HTTP200 passed; no listening or browser
interaction acceptance is claimed.

**Execution decision:** proceed with the owner-authorized final cumulative take
for the220 still-eligible production rows, using the already source-tested,
frozen `automatic-short-v7-period-warm-v2` recipe. The diagnostic three-take
experiment is evidence that the automatic acceptance/rejection/retry mechanism
works with this prompt, not a guarantee of the220-row success rate. Each corpus
row has ONLY ONE remaining take; the prior two attempts are NOT reset. The
per-file packaged Base/count/number/signal checks remain the installation gate;
failed takes preserve originals and become exhausted. No threshold changed.
Canonical preprocessing remains a separate enhancement and is **not integrated**
in this source-frozen run: this avoids claiming that the live native-source
experiment proved a changed implementation.

Preflight rechecked all220 original audio/receipt pairs, exact frozen667 scope,
source/remaining/priority/registry hashes, all selected master hashes and current
history budgets (220 at2,34 at3). It snapshotted all667 current audio/receipt pairs
and budgets without reserving a take. Decision/evidence:
`final-take-v7-02/{preinstall-snapshot.json,readiness-decision.json,plan.json}`
under the existing priority-v1 root. No old plans or prior receipts were rewritten.

The existing continuation is now RUNNING, using prepared voice Python and both
VoxStage timeout settings7200. Observe its `producer.pid`, `production.log`,
`progress.json`, state.sqlite3 and automatic-evidence. Do not start a duplicate,
restart shared VoxStage, or retry uncertain submissions. Source is unchanged
since635de89b7; existing source verification applies, full gate still NOT GREEN.
At terminal completion audit actual changed667 pairs against DONE, backups,
installed final quality and provenance; report bounded installed/exhausted/blocked
counts with human review PENDING. This decision explicitly supersedes the earlier
hold on this exact v2 continuation after the documented investigation/retry gate;
it does not retrospectively change the failed first-take experiment.
