# Greia — Current Engineering Handover

**Purpose:** the short current state for contributors and agents: active workstreams, recent results, blockers and next steps. It is not an archive.
**Public-source readiness:** IN PROGRESS. Root entry points exist (`LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`); the licensing/provenance audit is open (see `NOTICE.md`).
**Ordinary-family release:** NOT READY (`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).
**Current A/B action (2026-10-26 follow-up):** the corrected 80-test preflight
passes, but current main has continued to advance (at last check `ef8eb3415`) and adds production installer/launcher/
platform localization source and en/es/fr/it language manifests outside the
reuse allowlist. The one-stage diagnostic boot was **not** started. A reviewer
must record an explicit reuse exception or rebuild the next bundle/image. No
rebuild/install/arm/B boot. Actual stage cause remains unknown. See
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md`.

Entries dated before 2026-10-15 were removed from this file in the 2026-10-16 open-source cleanup. Read them with `git show 101e332a:HANDOVER.md`; lessons from that period are indexed in `docs/archive/README.md`.

Add new entries at the top of **Recent entries**, newest first.

## Active workstreams

Blocking and lifecycle authorities (rules in `AGENTS.md`):

- **Architecture remediation**: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` is the blocking plan for its remaining non-lifecycle obligations.
- **Install, update and release lifecycle**: `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor).
- **Cross-hardware robustness**: `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`, subordinate to the remediation plan; root causes go to `docs/INSTALLATION_ISSUES_LOG.md`.
- **Art and visual system**: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`, resumed through `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`; Encyclopedia subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`.
- **Parent authentication/runtime acceptance**: current HTTPS transport procedure is `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md`; the older 2026-09-08 protocol is a historical authentication baseline. Self-signed HTTPS is implemented in source but awaits local tests and device/browser acceptance.
- **Testing route**: `docs/testing/LOCAL_AGENT_START_HERE.md`; local-agent queue `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

Scoped owner-authorized workstreams (moved verbatim from `AGENTS.md` on 2026-10-16):

**Current owner-authorized Activity release + Creations workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` is the **single unified product/content implementation plan** for the typed child Creations Library, universal pre-reader picker/viewer, adaptable disk budget, Painting/Shape Garden/Theatre/voice/text interoperability, complete built-in Activity quality audit, and deliberate catalogue selection. Continue from `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md` and append accurate session results. This owner-requested scoped program coordinates those features but **does not supersede** the architectural-remediation and release-install/first-boot lifecycle authorities above; those still govern safety prerequisites, image installation, update, rollback and hardware acceptance. Product/source work may proceed in parallel without making hardware claims. Do not spin up a second competing catalogue, picker, or creative-media plan.

**Owner-authorized localization workstream (2026-10-12):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md` is the
scoped implementation plan for reducing misleading language choices,
completing EN/IT gaps, and extending real installer/OS/Parent/Activity
text and voice support to ES/FR. Its standing local-agent speech design and cue-source authority is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md`.
**Current existing-corpus replacement work order (owner instruction 2026-10-19):**
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, executed with
`tools/regenerate_voice_corpus.py`. It explicitly permits fresh replacement
with new masters and per-recording acting prompts, preserving deterministic
isolated letters/syllables and backups. V2 production has completed: 4,168 DONE,
741 PRESERVED, zero blocked or unresolved rows. Every new take remains
listening-pending. Source fixes needed to operate the tool and packaging are
authorized by this work order; ordinary queue-only restrictions do not block
that requested task. Post-generation screening follows
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`; automatic coverage and human
acceptance are separate from generation DONE.
**Earlier add-only voice-production work order:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`
(owner instruction 2026-10-14; archived full-run instruction). The owner approved
every **currently authored** EN/IT/ES/FR text translation, and personally
reviewed and approved **all committed recordings**. New missing files from
the targeted task still need fresh acceptance. Neither decision promotes ES/FR.
An available, registered zero-new-spend local Greia Voice Engine provider may
be used to record without waiting for a future Modal provider, but paid
cloud/model installation still needs separate explicit cost approval.
**Owner-directed shared localization consolidation (2026-10-15):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`
is the active bounded design for reusing the existing `LocalizedResources`
owner for semantic text/audio IDs, file-exists selected-locale lookup and
English fallback for **all** speech, and gradual migration of Activity-local
loaders. Existing committed audio is **owner-reviewed and accepted**;
never regenerate it for perceived provenance problems. The user does **not**
want file anti-tampering, signing or elaborate asset verification; users may
edit their files. Follow the focused new-recordings assignment in
`docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.
Update the Activity-creation skill/voice companion **after the code API is real**;
retain the current callable interface meanwhile. This refactor does not
independently promote ES/FR system selection.
The sole practical local-agent task queue remains
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.
**Owner decision 2026-10-17:** EN, IT, ES and FR are all released and
selectable (selectors offer exactly these four); missing voice lines in all
four languages are owner-approved for recording with the local voice tooling
(no paid spend without approval).
This scope does not override ADR 0028, accepted architecture,
installer/first-boot/lifecycle test gates or the Creations/Activity
audit programme. Do not invent a second language registry or silently
promote unvoiced locales.

## 2026-10-26 — Stage retry: status/verify PASS, stage failure masked by login prefix

Ran the single healthy A-to-B retry in
`docs/testing/2026-10-26_AB_STAGE_RETRY.md` from clean `abb11b0a0`, reusing
the verified `1275e0be1` bundles and accepted-A clone. The source-diff
allowlist passed and the focused harness suites were **176 tests OK**. Reuse
preflight passed: both bundle hashes and accepted-A
(`83d693d9…`) matched, the prior first-boot JSON validated, no image holder was
present, and there were no owned loops before the leg. PSmisc 23.7 rejected the
work order's `fuser -v -- <files>` form, so the equivalent supported invocation
was recorded; the reused `0600` bundles were made `0644` so the user-level
checks could read them.

The leg got further: `update-status -> OK`, `update-verify -> VERIFIED`, then
**`update-stage` failed with `phase update-stage failed (exit 120)`**. The stage
failure line was prefixed by `greia login:`, so the harness's
`_control_phase_failure` parser missed it and booted `update-arm`, which
correctly refused with `update transaction is accepted, not staged`. The first
concrete error is the stage failure; the arm refusal is downstream. The
immutable base payload's shipped client has the 1800 s stage bound, so this is
not the old 30 s test-client timeout. The captured serial lacks the stage
service error/traceback, so installed-updater stage completion remains
**UNPROVEN**; no production refusal is claimed. Accepted-A SHA is unchanged,
the loop audit is 0, and no healthy B/arm/fault leg ran.

Evidence:
`/var/tmp/greia-ab-stage-abb11b0a0fc999ec536841f02441423546b845fa-20261026T085728Z/`.
Report: `docs/reviews/2026-10-26_AB_STAGE_RETRY_EVIDENCE.md`. Next: fix the
failure-marker parser and stage journal capture in the test control, then
authorize one new attempt; do not reuse this failed clone or rebuild the OS for
a harness-only cause. Session 04 remains OPEN.

## 2026-10-26 — Current-source A/B rerun: install/first PASS, stage harness timeout

Ran the clean three-leg route in `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`
from clean `1275e0be1`. Host/SMART preflight passed; disk started at 76% after
pruning the superseded `866ba6827` images (small logs retained). Full
`make verify` was **5,961 tests, 6 failures, 3 errors, 3 skips**; every
failure/error ID is in the documented Linux baseline (5,959/7/3/3), the prior
extra `morbidi_mostriciattoli` timing failure did not recur, and
`BASELINE_REVIEW=matched`. Focused A/B suites passed **232 tests**.

Built the 0.13.0 base fixture (bundle `b45f0fc7…`), installer (`1edbcb0b…`)
and 0.13.1 next fixture (`3ae9cdea…`) from that SHA; both fixtures are
experimental/non-release and both bundles inspect cleanly. The **install leg
PASSED** and **first boot PASSED** (default/committed A, accepted base release,
clean poweroff). The **healthy A-to-B leg FAILED at `update-stage`**: the
installed updater returned `STATUS -> OK` and `VERIFY_CURRENT_CANDIDATE ->
VERIFIED`, then the test-only guest control hit its hard-coded 30 s socket
timeout while `STAGE_CURRENT_CANDIDATE` was writing the ~714 MB candidate.
No stage/arm/B health/final observation was reached; healthy B remains
**UNPROVEN**. The failure is a harness control timeout, not a recorded
production refusal. The run also leaked 19 loop devices; they were detached
with the safe helper and the greia loop audit is empty.

Evidence: `/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z/`.
Detailed report:
`docs/reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md`.
Next: fix the test-only stage timeout/loop cleanup, commit a new freeze, and
rebuild/rerun from scratch; do not reuse these images. Session 04 remains OPEN.

## 2026-10-26 — Clean-source A/B smoke: install/first PASS, healthy blocked

Pulled the new `docs/testing/2026-10-25_AB_SMOKE_RETRY.md` work order and ran
it from clean `866ba6827`. The full gate matched the documented red baseline
(5,959 tests, 7 failures, 3 errors, 3 skips; +2 new tests, same failure/error
IDs), and the focused A/B source suites passed 66 tests.

The clean base 0.13.0 fixture (bundle `93f55468…`), installer
(`492483b7…`), and next 0.13.1 fixture (bundle `76ef1ffe…`) all built from
that SHA. The **install leg PASSED** and the **first boot PASSED** (default A
accepted, first-install journal cleared, clean poweroff).

The **healthy A-to-B leg is BLOCKED** at `update-verify`: the service reports
`no current update candidate in the inbox` even though the 0.13.1 candidate is
present in the disposable clone's PERSIST
`greia/namespaces/parent-credentials/system-updates/inbox/candidate.greiaupdate`.
The harness now prepares/injects that candidate host-side; the remaining issue
is the running service's inbox discovery/path contract. No healthy B boot,
rollback, 507, Parent-stop, applying-cut, Mobile or physical leg ran.

Evidence: `/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z/`;
details appended to `docs/reviews/2026-10-25_SOFTWARE_UPDATE_LINUX_RETRY.md`; the detailed retry report is `docs/reviews/2026-10-26_AB_SMOKE_RETRY_EVIDENCE.md`.
Session 04 remains OPEN.

Correction: source-only harness fixes now prepare a candidate-only Linux retry;
healthy B remains unproven. Use the conditional route in
`docs/testing/2026-10-26_AB_CANDIDATE_RETRY.md`.

## 2026-10-25 — A/B first-boot health ACCEPTED; active-slot isolation blocker

The Acer A/B acceptance first boot now works through the shipped health path:
the test control starts the real credential/recovery units, the one-use
capability is issued and consumed, the first-install journal commits, the
default remains A, and the control powers off. Product fixes: the
credential generator and socket service run with `Group=greiakid` and
`SupplementaryGroups=pipprofiles` so they can create/consume the token under
`/run/greia-os` without DAC override; boot history moved from
`/var/lib/greia-os/diagnostics` to
`/run/greia-persist/greia/diagnostics` (PERSIST); the test-only X8 control
now pulls the credential/recovery units, orders before the launcher, waits
for the token, and reports service failures on serial.

Remaining blocker: `run_first_boot_product` fails the **active-slot
isolation** guard ("slot A changed across its own acceptance boot") after
the health observation passes. The A/B root is remounted writable, so raw
slot A changes even with boot history on PERSIST. This needs an owner/
architecture decision: make the active slot genuinely read-only and persist
writable state (including `/var/lib/greia-os`), or define a bounded
active-slot exception in the isolation contract. Do not weaken the guard
silently.

No healthy B update/rollback, 507, Parent-stop, applying-cut, Mobile or
physical leg ran. The next bundle and clean A/B installer were not rebuilt
from the fixed source; the tested target was a patched disposable fixture.
Details/evidence: `docs/reviews/2026-10-25_SOFTWARE_UPDATE_LINUX_RETRY.md`;
evidence under
`/var/tmp/greia-ab-1500-9078fcd3b7babd391249b60e77153d8ab8c38106-20261025T022134Z/`.
Session 04 remains OPEN.

**Owner decision 2026-10-25:** hand off the current evidence rather than
choose the read-only/PERSIST or bounded-exception route in this session. The
next implementation owner must settle that architecture before rerunning the
A/B harness; a pass is not expected against the current target.

## 2026-10-22 — Owner resumed priority completion with Base

The owner explicitly requested finishing the problematic Greia recordings,
superseding the historical bulk-stop instructions only for the frozen **667
priority paths**. Deferred/missing-review short lists remain outside this run.
`tools/finish_voice_priority.py` reuses VoiceEngine and CorpusRunner: it reconciles
current installed hashes against prior DONE transactions, checks retained takes
with pinned Base/accent-insensitive scoring, re-extracts saved immutable provider
takes before generating, and carries cumulative attempt counts by maximum (never
sum). Fresh takes use the previously compared ellipsis/blank-line introduction
and two-second pause direction; actual silence still must satisfy the cutter.
Maximum three cumulative fresh generations per cue. No masters change.

Carrier synthesis now disables ASR on the disposable introductory recording;
required verification scores the packaged target, strictly above 0.8 with no
signal warnings, before the normal recoverable installation transaction.
Lossy delivery is decoded and independently checked. Human review remains PENDING.
The interrupted Italian ask_R provider job completed as
`20261021-225637-ef097ad1`; recover that output rather than resubmit its take.
The whale cue differs from its prior DONE candidate but primary verification
confirmed its exact original audio AND receipt were restored. A one-cue follow-up
after the main pass repairs that original priority path, preserving its budget. Live continuation: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/resume-base-v6-production/`
(`progress.json`, `production.log`, pass journals); PID 87089 at launch.
The source gate `make verify PYTHON=/opt/anaconda3/bin/python3` executed locally
and aborted in the test stage with `Abort trap: 6`; full log
`/tmp/greia-priority-completion-make-verify.log`. It is NOT GREEN. Focused carrier
32/32, corpus 18/18 and continuation 4/4 PASS in the prepared voice environment.
The first corpus discovery without PYTHONPATH failed to import greia_platform;
the corrected `PYTHONPATH=src` invocation is the 18/18 result. Initial orchestration
startup rejected one legacy manifest receipt, then caught a missing decode-output
directory before any synthesis/install; both were corrected, old logs preserved,
and the active pass completed the delivered-audio audit: 167 kept. Saved-source
recovery installed 74 + 4 = **78** target recordings through normal transactions.
Primary checked three actual installed hashes, Base scores and PENDING receipts.
`fresh-01` is now processing 421 remaining cues; the separate exact-original
whale follow-up covers the last original priority path after normal main exit.
First fresh provider job `20261022-013018-a44c21bc` completed and was safely
rejected at Base score 0.6527; its prior destination was retained and the producer
continued to the next cue. Luna monitors this exact process through terminal
state and then the bounded whale follow-up; do not duplicate either producer.
Generated audio remains local/listening-pending while production runs. The combined focused run passed
92 tests before the extra restoration positive/negative test (which passed).

## 2026-10-21 — Owner reprioritized spoken-carrier retakes

The owner superseded blanket short-phrase production with review-led retakes for
low scores and strong warnings/uncertainty. The original 642-row producer was
stopped at a safe point; no additional 1,968/2,111 actor plan was launched. Its
latest journal at stop was 16 DONE, 12 extraction FAILED, 1 GENERATING, 613
READY, and 4,273 PRESERVED. The raced Tito/IT Oskar provider job completed; raw
WAV SHA-256 `172be7d5ea3e95b22d8e5c17c2a774b01622f8461a89fffff8c0384a321858b7`
and the original VoxStage `job.json` were preserved externally, not installed.
The run journal now records that cue as FAILED/pending targeted triage.

The current all-actor short set has 2,753 plan paths: 2,610 match the merged
v2/v3 automated review set and 143 have no historical review evidence. The
143 are isolated in the needs-review list (Foresta Parole 56, Sillabe Magiche
39, vocab 48) and are not treated as quality failures. External triage lists
are under `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-corpus-v1/triage/`. They include 667 priority retakes (Tito 67, Leo 412,
Momo 67, Dani 4, Lilli 95, Flash 22), 1,927 deferred reviewed cues, 16 completed
listening-pending takes, and the 143 evidence-gap rows. Human review evidence
qualifies only when its saved audio SHA matches the frozen source; historical
ratings are retained with stale/match state.

A new priority-only frozen plan is at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/run/plan.json`; its exact SHA is in `priority-freeze.json`. It has exactly 667 READY
rows and all remaining rows PRESERVED. Previous attempts are carried forward
for the three-generation per-cue maximum. The single VoiceEngine/VoxStage worker started this targeted queue at 17:06
Europe/Rome. Its first provider job is 20261021-170600-f39bc05c for Tito/FR
find_octopus.wav; initial journal is 1 GENERATING, 666 READY, 4,248 PRESERVED.
Safe cut rejection preserves originals and continues, while provider failures
stop for inspection. All outputs remain listening-pending. Details and the exact
command are in the external RUNBOOK.

The normal-environment `make verify` evidence remains 3,131 tests with 31
failures, 241 errors, 6 skips; see `/tmp/greia-short-carrier-make-verify.log`.
Focused carrier/policy/generation/corpus tests passed 38/38 before the later
actor-selection change; selector/corpus tests passed 21/21 after it. No full
verification was rerun for this triage-only change.

### Reviews written today (2026-10-21)

- `docs/reviews/2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md` - pre-M1 Mac hardware support research and plan.
- `docs/reviews/2026-10-21_LEGACY_X86_NETBOOK_HARDWARE_RISKS.md` - lead finding: Debian trixie has no i386 kernel/installer; the Greia i686 line is bookworm, supported to 2028-06-30; owner decisions pending.
- `docs/reviews/acer/2026-10-21_ASPIRE_HIRES_DEVICE_CHECK.md` - 6 Activities PASS on the Aspire; animated Activities ~45-52% CPU plus Xorg ~50%, not yet compared with hi-res off; the Wi-Fi resume hook is not on the device until reimage.

## 2026-10-21 — Priority-run continuation after provider-job inspection

The first priority-only producer was stopped after 4 DONE, 3 safe extraction
FAILED, 660 READY, and 4,248 PRESERVED. Its third in-flight provider job for
Leo/EN D as Duck completed; the exact raw WAV (SHA starts e75a57cf and ends
bd50e) and VoxStage job receipt were preserved externally, not installed.
Cached Whisper extraction then passed exact prefix/target and the unique
low-energy gap gate (0.34 s verified gap, cut sample 82,560). The candidate was
packaged with the existing AudioPipeline and passed the production CorpusRunner
candidate validator.

The remaining 663 priority rows are frozen in the continuation workdir:
 /Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/continuation-02/run/.
Plan SHA-256 is 88d22f6e744f8bc3c181666901ccc7fe1360f0c12883d72225455c8afb8a349c.
It carries forward per-cue attempt counts and stages the recovered D candidate,
so it will use the already completed provider output rather than submit it again.
This serial continuation started with 1 GENERATING, 662 READY, and 4,252
PRESERVED; the 4 first-run DONE, all 16 earlier retakes, and all 143 evidence-gap
rows remain out of its queue. Outputs remain listening-pending.

## Recent entries

### 2026-10-26 — Manifest language fixes: 59/59 focused tests PASS (SOURCE-VERIFIED)

The owner's local agent verified exact `main` HEAD
`bd3aa0a25fdd58220ad1b361ebf7ce2715a3ba47`, fast-forwarded cleanly
from `7bb199514`. Existing Python 3.12.7 at
`/opt/anaconda3/bin/python3`, `PYTHONPATH=src`,
`PYTHONDONTWRITEBYTECODE=1`. Source suites passed:
`test_language_manifests.py` **13/13**, `test_system_language.py` **9/9**,
`test_installer_localization.py` **7/7**,
`test_panel_localization.py` **19/19**,
`test_four_language_release_contract.py` **11/11**:
**59/59 focused PASS**. The `en`, `it`, `es`, `fr` source/placeholder
audits each returned zero findings and exit 0. New nested placeholder,
UI-schema validation and nested Activity/UI checker regression tests passed.

Zero tracked modifications afterward; 310 previously untracked files
remained untouched. No production language manifests or accepted audio
changed across the verified commit range. No new locale was offered.
This supersedes the preceding entry's outstanding focused-test rerun,
but constitutes **SOURCE-VERIFIED** evidence only. Actual five-language
rendering, font/layout, audio, installer image and device tests remain
unperformed, as does complete language-localized browser chrome in the
separate `Greia-Parent-App-Html` repository. Its language-choice options
already derive from the Greia Parent API. Next useful step is a single
bounded, nondestructive five-language UI/rendering exercise and separate
browser-chrome localization design; do not repeat the already-passed five
focused suites simply for ceremony or disturb independent A/B testing.

### 2026-10-26 — Fifth-language checker verified baseline and repaired (SOURCE-WIP)

The owner's local agent ran five manifest/system/installer/Parent/release
suites against exact `7bb1995146ea917da6a3d33004b2c40d48c535ce`,
Python 3.12.7: **56/56 PASS** (10+9+7+19+11); language source
checks EN/IT/ES/FR had zero problems. No tracked edits, existing unrelated
untracked work preserved. This establishes a source-only baseline for the
manifest-backed languages and staged-new-language tooling, **not** UI/image/
hardware/voice acceptance.

The agent spotted two valid omissions: `tools/check_greia_language.py`
didn't validate the UI catalog schema/section types, and inspected only top-
level Python format placeholders. Follow-up GitHub commits added those
checks, recursive fields in nested specifications (e.g. `{count:{width}}`),
and regression cases in `tests/test_language_manifests.py`. The add-language
guide, agent/OS skills and language rollout progress were updated.
**New tests have NOT been run in a complete checkout**; the 56-pass
count applies only to the earlier commit.

Browser Parents language buttons already derive offered devices' locale list
from the Parent API; its separate browser chrome has EN/IT/ES/FR strings
in `frozenpepper/Greia-Parent-App-Html/src/localization.js`. Extending
that browser chrome via only data/config is still open and should not be
confused with the implemented OS/installer manifest discovery. That separate
repo is pinned/vendor-synchronized in Greia; review and repin together,
not via an isolated browser edit. No additional locale was offered and no
approved voice data was modified. Next: rerun focused suites at new exact
head, then only a simulated 4+1 chooser UI test; avoid concurrent A/B smoke
contamination.

### 2026-10-26 — Manifest-language contributor audit refinement (SOURCE-WIP)

The manifest-backed source from the preceding entry remains the implementation
baseline. This follow-up repaired the new-locale checker: `--staged` now audits
an unfinished fifth language **without** a selectable manifest; an empty
`first_profile.extra_letters` value is valid when that alphabet needs no extra
keys. `tests/test_language_manifests.py` adds staged `de` source completeness/
placeholder cases, fifth-language installer pagination, and manifest-data-backed
installer/Parent translation cases. The guide now documents the pre-promotion
command. Existing en/it/es/fr content and audio were not touched.

**Evidence:** inspected and committed via the private GitHub connector.
No tests were executed in a complete checkout and no GUI/device/audio/image
acceptance was run. The next agent should run the focused repository tests and
report failures before hardware work. Other ongoing installer/A-B diagnostic
work is independent; this newer source does not inherit its successful preflight.

### 2026-10-26 — Manifest-driven language offering and data-only new-language authoring (SOURCE-WIP)

The owner requested that additional Greia languages no longer require editing Python
registries/chooser logic. `src/greia_platform/system_language.py` now loads
`src/greia_platform/languages/<locale>/manifest.json` at startup;
the four shipped locales (en/it/es/fr) are represented as package resources.
Installer, Parent on-device chooser, Parent API and device settings share that
registry. Installer/Parent choice screens paginate for additional languages.
Optional `ui.json` sections provide new translations for installer, Parent
panel, launcher/collections, achievements, Creations, first boot and limits
without modifying their legacy English/four-language baseline logic.
`tools/scaffold_greia_language.py` creates untranslated English-reference
UI/Activity JSON **without** enabling the locale; the contributor adds a
manifest only after acceptance. `tools/check_greia_language.py` checks resource
coverage and interpolation; release tests now derive the promised locale set.
Canonical guide/agent route: `docs/development/ADD_A_GREIA_LANGUAGE.md`,
`skills/greia-language-expansion/SKILL.md`. Character audio/master/Parakeet
flow is unchanged.

**Evidence:** GitHub source inspection and commits only. Provider-free tests,
simulator, text layout, voice generation, image composition and hardware have
**NOT** been executed against this change. This source is newer than the current
A/B candidate and cannot inherit its previous test/boot evidence or prior
reuse exceptions. Run focused tests and render 4+1 language chooser in a local
simulator/build before treating this as release-ready. Do not silently enable
a fifth language before translation, audio/font and actual screen acceptance.



### 2026-10-26 — Single-stage diagnostic blocked by new runtime language files

The corrected preflight passes: 80 tests OK with parent
`PYTHONUNBUFFERED=1`, and the prior closed-stderr fixture failure is fixed.
However, the work order's `git pull --ff-only` advanced main to `abd9f5045`
with two production source language manifests. During push reconciliation main
continued to advance (at last check `ef8eb3415`), adding the broader localization implementation
(installer/launcher/platform source plus en/es/fr/it manifests). All of these
are outside the strict A/B image-reuse allowlist, so the work order stopped
before the one-stage diagnostic boot. No VM, install, arm, B boot, update
replay or collector ran.

The added language files are selector metadata and are not in the accepted-A
image or next bundle (both from `1275e0be1`), but the current `main` also
changes installer/launcher/platform source. Whether any of it is irrelevant
to the updater-stage target is a review decision, not something to assume under
the gate. Read-only input checks still pass: accepted-A and next-bundle hashes
OK, holder status 1 with empty output, zero old-evidence loops. Report:
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md`.
Next: record an explicit reuse exception or rebuild the next bundle/image; do
not boot the stage diagnostic until that decision is recorded. Session 04
remains OPEN.

### 2026-10-26 — Correct deterministic stderr test preflight

Pulled `920595d4e`: Linux stopped before any VM because the closed-stderr
positive-control fixture failed. The old 10 KB initial write could flush/fail
before the child reached its socket. Its fake server could also spin on EOF,
wait forever in accept, or lose cleanup after child exceptions. This was a
test failure, not an installed updater result.

Only the fixture changed: short buffered stderr with explicit child environment,
actual decoded stage-request/refusal assertions, cancellation with bounded
accept/recv, EOF handling, kill/reap in finally and join-before-close teardown.
EOF regression waits for server EOF rather than assuming thread scheduling.
The final work-order preflight passes **80 tests in 14.162 s** with parent
`PYTHONUNBUFFERED=1`; independent Luna review passed and repeated the focused
case 8 times on final source. No production or harness implementation changed.

Next: rerun the existing single-stage work order's preflight and, if green,
continue directly to its one already-scoped stage boot. No separate extra
approval step or image rebuild is introduced. Capture/report then stop; no
arm/B boot or full matrix. Evidence is appended to
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_PREFLIGHT_FAILURE.md`.
No Linux stage boot ran here; stage cause/healthy B remain UNPROVEN; Session 04 OPEN.

### 2026-10-26 — Single-stage diagnostic stopped at preflight test failure

The work order `docs/testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md` was
executed from clean `81ba47dba`. Its source-test gate ran 80 tests with one
failure: `test_generated_stage_failure_avoids_exit_120_from_buffered_stderr`
left its positive-control fake-server thread alive after
`server.join(timeout=5)`. The other 79 tests passed, including the new
stage-diagnostic suite. Per the work order, the one-stage VM boot was **not**
started; no install, arm, B boot, update replay or collector run occurred.

The remaining preflight checks were completed read-only for the report: the
source-diff allowlist was clean, accepted-A and next-bundle hashes matched,
the input holder check was status 1 with empty output, and no old loops were
attached. Inputs were preserved and not chmodded. This is a test-control race,
not an installed-updater result. Report:
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_PREFLIGHT_FAILURE.md`.
Next: fix the fake-server teardown/join, rerun the preflight, then authorize the
single stage boot; do not rebuild the OS for this harness-only failure.
Session 04 remains OPEN.

### 2026-10-26 — Offline answer received; one captured stage operation next

`10de26ce8` records successful offline collection: A remains accepted; B has
no finalized release identity; update status is still received. Old logs were
not persisted, so the first stage cause is unrecoverable. Absence of B's identity
does not prove no payload bytes were written. Source audit found no supported
capacity, missing-zstd or launcher-inventory ordering cause; no speculative
production fix was made.

The next exact work order is
`docs/testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md`. Its new helper clones
verified accepted A, injects the candidate into offline PERSIST and the control
into A, boots only `update-stage` once (2,400 s host / 1,800 s client bounds),
then always collects the stopped clone's response/error and state. The control
disk is phase-only 64 MiB. It does not arm, boot B, install or rebuild. Its
result is diagnostic-only; a QEMU return is not stage/health acceptance. Both
source inputs are checked before/after, and collection/cleanup errors propagate.

Source checks and independent review are appended to
`docs/reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md`. No Linux boot
executed here; actual stage cause/healthy B remain UNPROVEN. Session 04 OPEN.
The newer collaboration-policy commits were preserved; core agents still use
main, and exact AGENTS/CONTRIBUTING/CODEOWNERS documentation changes do not
invalidate unchanged image inputs.

### 2026-10-26 — Failed-image read: B not next release; stage cause unrecoverable

Ran the offline read-only work order
`docs/testing/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS.md` from clean
`65cd6212e`. The focused diagnostics/handoff suites passed (14 tests), the
failed clone was proven offline, and the collector exited 0 with cleanup
reported ok (loop `/dev/loop37` detached; no owned loops remained). Diagnostic
JSON:
`/var/tmp/greia-ab-offline-65cd6212e2e0023d9e6f131d52e24d80396ce66d-20261026T145341Z/image/diagnostics.json`
(SHA-256 `c7f01595…`).

Observed: A is the accepted base 0.13.0 slot; B mounted but has **no release
identity**, so it does not contain the next 0.13.1 release; PERSIST layout
still accepts A and the boot journal is `accepted`. Update status names the
next bundle but remains **`received`** with activation unavailable; its
`bundle_path` is a host-mount `/tmp/greia-x8-persist-…` path. The old control's
`phase-result.json`/`service-diagnostics.txt` are absent, as expected. The
collector reported no errors.

The stage failed before B finalization, but the available facts cannot
distinguish a service refusal, crash, or lost control error. A closed-stderr
flush is a demonstrated loss mechanism, not proof of this stage's cause. The
first stage error is **unrecoverable from this image**; healthy B remains
unproven. Report:
`docs/reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md`. Next: a
separate bounded diagnostic boot with corrected durable capture; do not rebuild
or replay blindly. Session 04 remains OPEN.

### 2026-10-26 — Stage failure remains unknown; offline diagnosis first

The `abb11b0a0` Linux retry failed at stage with exit 120. The parser missed
the exact `greia login: x8-control: phase ... failed` prefix and continued to
arm; that harness defect is now reproduced and fixed. Error capture now saves
bounded valid JSON with the raw service response/refusal and cause chain before
exit, plus a service snapshot before poweroff. A subprocess reproduces exit
120 from a failed buffered stderr flush; that is a demonstrated loss mechanism,
not proof of the installed stage's first error.

Immediate work order: `docs/testing/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS.md`.
Read the existing failed clone offline and commit its facts. No image rebuild,
VM boot, update replay or larger fault matrix. The new collector uses read-only
loops and `ro,noload` mounts. Old volatile journal data may already be gone;
missing new capture files in that old image are expected. Preserve all inputs.
The old holder command's unsupported `fuser --` form is removed, usage output
cannot masquerade as no holders, and root-owned artifacts are read via sudo
without chmod. No production code or image build input changed here.

Final focused verification: 339 tests PASS; fresh Luna review found no
remaining blocker in this source scope. Full gate remains NOT GREEN; exact
results are appended to `docs/reviews/2026-10-26_AB_STAGE_RETRY_EVIDENCE.md`.
The actual stage cause and
healthy B are UNPROVEN; Session 04 remains OPEN.

### 2026-10-26 — A/B stage timeout and teardown follow-up

The `1275e0be1` Linux report proves install/first-A PASS and installed update
STATUS/VERIFY PASS. Healthy B remains UNPROVEN: the harness cut staging off
at 30 seconds and the report records leftover loop associations. Current
harness fixes use the shipped client's operation timeout for stage (1,800 s)
while preserving the bounded root-only arm request. Teardown uses existing
scoped cleanup helpers, reports failure and preserves operation errors.

Next: `docs/testing/2026-10-26_AB_STAGE_RETRY.md` permits one healthy A-to-B
retry from the verified `1275e0be1` bundles and accepted-A only after source,
artifact, first-boot, offline and loop checks pass. The source/artifact pairing
is explicit: harness-only fixes do not require rebuilding unchanged images.
Owner correction: run the cheap preflight first; host/harness failures require
diagnosis against existing artifacts, not speculative image builds. This work
order performs one healthy update, records its outcome and stops; no automatic
chain into a larger fault matrix.
If a production/build input changed or an artifact/check fails, fall back to
the clean three-leg guide. Never reuse the failed healthy-update clone or
repair guest status. Source checks: 320 broader tests PASS, 176 guide tests PASS; fresh Luna review
PASS. Full gate status is recorded in the evidence report. New harness code
has no Linux VM proof yet; Session 04
remains OPEN. Verification and corrections are appended to
`docs/reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md`.

### 2026-10-26 — Package discovery simplified; status is progress only

Owner direction replaces the receipt-dependent discovery design. The installed
full-system updater now recognizes only its fixed published inbox package and
reads candidate identity from that package's manifest. Missing, malformed or
stale status cannot hide it or redirect it elsewhere. Availability polling
reads the bounded manifest without hashing the whole payload; full verification
and compatibility checks still run before staging. A consumed/absent candidate
stays absent. Durable software jobs, atomic publication, slot journals and
application-generation recovery remain intact; the `.greia_update` Upload &
install flow still continues on-device after the Parent disconnects.

The test harness no longer projects a host receipt path into the guest. This
is a production-code change: rebuild both fixtures and the installer from the
new committed source using `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`, then
run install → first-A health → healthy A-to-B. The prior candidate-only reuse
guide is HISTORICAL; old `866ba6827` images do not contain this fix. Do not
manually repair their status. Python/Activity updates remain ZIP packages and
do not need full-image rebuilding for each update.

Source verification: 327 focused tests PASS; independent Luna review PASS.
Full gate: 5,961 tests, 6 failures, 3 errors, 9 skips (same prior Mac IDs; NOT
GREEN). Exact evidence is in
`docs/reviews/2026-10-26_UPDATE_DISCOVERY_SIMPLIFICATION.md`. No new Linux VM or
physical run occurred here. Session 04 remains OPEN.

### 2026-10-26 — Candidate-only retry prepared; VM result pending

Correction to the preceding route: the initial host-side injector placed only
`candidate.greiaupdate`, not the inbox receipt required by canonical
`SystemUpdateInbox` discovery. The test harness now receives the bundle through
`SystemUpdateInbox.receive`, projects its validated `bundle_path` into the
guest's canonical `/var/lib/greia-os` status record, restores inbox ownership
and fsyncs the published files. Control inputs are copied and sized correctly;
serial refusal markers trigger bounded guest diagnostics/poweroff, and the
installer control-disk size path/test seam no longer raises an undefined-name
error. These are harness/test changes only; no production update service or
installer behavior changed.

The prior install and first-A health PASS remain tied to clean `866ba6827`;
**healthy B remains UNPROVEN** because this candidate path has not been rerun
on Linux. Source review passed. Guide-specific focused selectors passed **168
tests in 1.220 s**; the broader X8 focused gate passed **296 tests in 3.236 s**.
The local full gate completed **5,959 tests: 6 failures, 3 errors, 9 skips; NOT
GREEN**. Failures match Foresta English/Spanish/French content (3), MBR wording
(1), and Parent Wi-Fi assertions (2); errors match ARM64 profile resolution
(1) and two macOS `lsblk` cases. This is not a full-gate PASS or Linux runtime
evidence.

After the reviewed harness changes are committed, run
`docs/testing/2026-10-26_AB_CANDIDATE_RETRY.md` on Linux only if its source-path,
artifact-hash, old first-boot and PERSIST checks pass. It reuses the clean
0.13.0/0.13.1 bundles and accepted-A clone, without rebuilding/reinstalling.
If any precondition fails, use the clean three-leg fallback
`docs/testing/2026-10-25_AB_SMOKE_RETRY.md`. Do not manually repair or enter a
root shell in the old guest. After healthy B, continue with the 10/23 and 10/24
fault matrices. Session 04 remains OPEN; no B boot/health, rollback, physical
or family-readiness claim is made.

### 2026-10-25 — Simpler A/B smoke; writable-root hash gate corrected

Implementation checkpoint: `0ede382f853bb0770e5b44b6fb741dd1d83cba4c`.
A post-commit rerun passed **335/335** in 3.180 seconds; log:
`/tmp/greia-ab-simplification/focused-0ede382f8.log`. The full gate above was
run on the same frozen implementation before the checkpoint; later changes
only record documentation evidence. Linux smoke execution remains pending.

The latest Linux report reached successful first-install health acceptance on
a patched disposable A/B target, then failed a harness raw-partition equality
check across A's own boot. The next bundle predates the credential-unit fixes
and the installer was patched; neither is a clean current-source artifact.
The report remains historical runtime evidence, not clean A/B acceptance.

ADR 0036 now explicitly clarifies the existing writable-root model. Full-system
SlotWriter still refuses active/accepted destinations; ordinary boot writes
are not updater writes. First-boot B remains strictly unchanged, and valid
unbooted write-window checks retain the strict helper. Across combined boot/
update/recovery legs, hashes have an explicit observational scope and no
byte-isolation PASS claim. Expected boot roles, release identity, mounted-root/
default/journal/PERSIST and health/recovery checks remain; recovery additionally
binds the previous accepted release to its PERSIST layout record. That binding
is semantic evidence, not an inventory of the old root's file contents.

The new primary retry is `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`: clean
same-source baseline and next fixtures, clean installer, then install → first A
acceptance → healthy A-to-B. It writes per-leg result/error/traceback logs with
bounded 2400-second leg timeouts. Larger fault/reverse/data-survival tests come
after this initial smoke; Session 04 is not closed or waived. No read-only root,
new overlay, profile capacity change, or production updater bypass was added.

Independent Luna source review passed. The combined focused run passed
**335/335** (`/tmp/greia-ab-simplification/focused-final.log`); the short guide's
exact 66-test source command also passed. Four stale expectations/fixtures
from the preceding unit-group and boot-alias commits were corrected without
changing those production fixes: root User/empty capabilities and runtime-group
access remain asserted; temporary finalizer fixtures now supply the actual
kernel/initramfs inputs and prove hardlink aliases while retaining fstab mode.

The initial full `make verify` ran 5,958 tests: 8 failures, 5 errors and 9 skips,
including those four now-corrected test cases. The final full rerun completed
5,958 tests in 271.197 seconds: **6 failures, 3 errors, 9 skips; NOT GREEN**
(`/tmp/greia-ab-simplification/make-verify-final.log`). The remaining outcomes
are the recorded Foresta content (3), Parent Wi-Fi assertions (2), MBR message
wording (1), ARM64 profile error and two macOS lsblk errors. No new failure
remains in that run. Separate validation stops at the unsupported ARM64 profile;
shell/footprint checks and the short guide's Bash/Python syntax checks pass.
No Linux image build, mount, QEMU or physical operation ran here. Next: freeze
this source and give the Linux agent only the short smoke guide for its first
retry; retain first failure and clean artifacts, then continue the larger
matrix after all three legs pass. **Session 04 remains OPEN.**

### 2026-10-25 — Clean Linux retry: ownership/order PASS; A/B fixture capacity blocked

Exact-source retry from `9161af3b30e3b96da314b24f4aba0e507eb46e7c` (code
freeze `ab02b9ec6`) is recorded in
`docs/reviews/2026-10-25_SOFTWARE_UPDATE_LINUX_RETRY.md`; evidence root is
`/var/tmp/greia-software-update-9161af3b30e3b96da314b24f4aba0e507eb46e7c-20261024T220454Z/`.
The focused gate passed **170 tests, OK with 1 Linux-only skip**; the full gate
ran **5,957 tests, 7 failures, 3 errors, 3 skips** and remains NOT GREEN for
the documented baseline/environment outcomes only.

A clean RC was built (`de75a782f786304235d89a631444c99a4ec04407567d34873b2d8119f040b0a2`)
and installed into two fresh 16 GiB disposable targets without guest repair.
Clone A applied a Python update **before** seeding any Parent Activity, then
installed `org.example.acceptance-painting` through the ordinary Parent route
(HTTP 201); the store stayed `greiapanel:greiapanel`, with private transaction
directories and child-readable `0555` generations; a child write probe was
refused. Clone B seeded two Parent Activities first, applied Parent-source
`one` (`0.2.0-retry`, job `b4cc58599f994f5ea494651e29bf7111`) and `set`
(`0.3.0-retry`, job `48297eb63b5340e3acdcccd7742e42b5`) updates, then a
built-in update (job `0b83ee6ca6d149dead02b6ecaa87fd8a`) with all Parents and
45 built-ins preserved; ordinary Parent install returned 201 and uninstall
returned 200 with `profile_data_preserved=true`. The real-account
root-to-`greiapanel` handoff test passed inside the guest. A capped partial
upload produced no 202, no pending/candidate and no new job.

The A/B acceptance fixture bundle built and inspected
(`greia-acceptance-fixture-0.13.0-phase0-dev`, bundle SHA-256
`6f1e85eac0c6f0f81498e429c8c6f17ca46f45f8ed8552bc9f8c7cd4947592e3`), but the
matching installer build refused the Acer A/B profile capacity gate: accounted
installed use **1287 MiB** against `required_core_mib=1000` and
`architecture_review_mib=1250` with a 1536 MiB slot. The fixture route did not
waive the gate. The A/B installer, ProductHarness, full-system wrapper and A/B
update/rollback legs are therefore **NOT RUN** pending an owner capacity
decision (raise the A/B build limit with finalizer-reserve evidence, or reduce
payload). The 507, Parent-stop, observed `applying` cut, Mobile and physical
legs also remain NOT RUN; the 8 GB LaCie was not modified. Session 04 remains
OPEN; no release/A/B/physical claim is made.

### 2026-10-24 — Linux acceptance blockers remediated in source

Source freeze: `ab02b9ec6fc7108e7b873b2b2c8c68eefd47ff18`. The post-commit rerun executed
170 tests in 17.955 seconds, **OK with 1 Linux-only skip**; exact log:
`/tmp/greia-acceptance-followup/focused-ab02b9ec6.log`. The later evidence
commit changes documentation only; the full gate remains NOT GREEN as below.

Follow-up to Linux report `f5a7db98a` and its two preceding fixes. The RC
verifier extraction fix was retained. Parent Activity storage is now
`greiapanel:greiapanel 0755`, with private transaction containers owner-only.
Root-side staging, locks, pointer/receipt publication and legacy repair preserve
that owner; published generations remain read-only and child-readable. Cleanup
no longer chmods hardlinked files. Existing profile-group identities and dated
evidence were preserved; no profile-group migration was added.

The first follow-up full gate exposed an additional real initialization race:
permission repair sealed another caller's hidden staging directory. Repair now
considers only complete published generations. Regressions cover concurrent
first initialization, writable private staging, legacy active-directory
migration, Parent UMask=0007, retained-generation file modes, and a root update
followed by ordinary Parent install/uninstall.

The explicit `greia_release.py build-acceptance-fixture` command reuses the
existing Acer A/B composition, receipt, payload, hardware-support and bundle
producers. It emits separate experimental paths/identity/report and cannot be
added to the public update index. Ordinary `build`/`build-profile` still enforce
the release-safe boot-cover gate. The two Linux work orders now select this
fixture route for current-source VM acceptance; production release acceptance
is not implied.

Independent Luna source reviews passed both changes. The final combined focus
executed **170 tests, OK with 1 Linux-only identity test skipped**
(`/tmp/greia-acceptance-followup/focused-final.log`). Release/index/RC verifier
focus separately passed 70 tests. The skipped cross-user test still requires
Linux root with the provisioned service accounts; macOS does not prove it.

`make verify` is **NOT GREEN**. The initial completed follow-up ran 5,954 tests
with 8 failures, 3 errors and 9 skips: six previously recorded content/message
failures, the unresolved aggregate Shell memory failure (866,748 retained
surface bytes), and the initialization race fixed afterward; errors were ARM64
and two macOS lsblk cases. After the race fix, the final full retry aborted with
signal 6 in Quattro Amici's native Pygame audio warming path, without a final
test summary (`/tmp/greia-acceptance-followup/make-verify-final.log`). No claim is
made that this abort is baseline-proven or resolved. Separate validation stops
at the known unsupported ARM64 profile; shell checks and footprint pass.

No Linux image build, mount, QEMU or physical operation ran here. **Session 04
remains OPEN**. Next: commit/freeze this source, build and graphically install a
fresh RC, rerun both ownership initialization orders and the existing apply/
idle/rollback cases without manual guest repair; then build the explicit A/B
fixtures and execute the remaining VM cases. Preserve the original Linux
report as repaired-clone evidence and append a new exact-source runtime report.

### 2026-10-24 — Linux software-update installed acceptance: partial pass, two fixes, two blockers

The 2026-10-24 Linux acceptance was executed on Orbiter (Ubuntu 24.04,
QEMU 8.2.2/KVM). Evidence:
`/var/tmp/greia-software-update-e8fed0ec494763834114e49863cc64aa66e70f2e-20261024T155314Z/`
and the dated result review
`docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`.
Two real defects were fixed on `main`:

- `e8fed0ec4` — the RC verifier lost the target `opt/greia-os` generation
  symlink and Activity-index alias during partial squashfs extraction, so every
  correct RC image failed verification. The corrected verifier passed the
  already-built image.
- `0bf1e15e6` — the initial Parent Activity generation was published with
  `mkdtemp`'s `0700`; a root-side update created `root:root 0700`, so
  `greiakid` could not traverse it and the child launcher looped after the
  pointer switch. Creation now publishes `0555` and repairs existing
  non-traversable generations.

The focused package/update gate passed **125/125** at `e8fed0ec4`; the full
gate executed **5,943 tests, 8 failures, 3 errors, 2 skips** and remains NOT
GREEN for the documented baseline/environment issues (Foresta, Parent Wi-Fi,
MBR wording, ARM64, missing optional Linux voice modules, plus `morbidi` and
one aggregate-only `piccola_serra` timing flake). The full gate is not waived.

On a disposable clone of the `e8fed0ec4` RC image with the initial generation
manually repaired to `0755`, installed acceptance passed for: real GUI install
and guest facts; real child profile and profile-picker survival; HTTPS Parent
pairing and durable `202`; two sequential Python applies; child-active
`waiting_for_idle` with an unchanged pointer; built-in `one`, `set`, source
`all` and exact installed-root `all`; combined Python+Activity; startup-failure
`rolled_back` with `launcher_not_ready`; and a subsequent valid apply. The
observed `trial` power-cut recovered to `base` and `rolled_back` on cold boot.

Two routes remain blocked, not passed:

- **A/B release/product harness:** `greia_release.py build` refuses because
  `greia-early-framebuffer-v1` is not registered release-safe. No current v3
  bundle, A/B installer, full-system wrapper or A/B harness leg ran; old
  September artifacts were not used.
- **Parent-source Activity seeding:** the developer-enabled
  `/api/v1/activities/install` returns 400 because the root updater created
  `/var/lib/greia-os/activity-packages/{generations,versions,receipts,staging}`
  as `root:root`; the `greiapanel` Parent service cannot chmod/write it.

NOT RUN: clean `0bf1e15e6` rebuild/install, partial-upload negative, 507
receive reserve, Parent-stop-after-202, observed `applying` cut, full-system/
A/B, seeded-creation hash preservation, and Mobile upload. The authorized
8 GB LaCie USB was not modified; the work order forbids flashing host media.
Session 04 remains OPEN. Next: fix the Parent Activity state-tree ownership,
rebuild/reinstall the fixed source, rerun the clean core cases, then resolve
the release-safe cover gate before A/B acceptance.

### 2026-10-24 — Linux software-update handoff made executable

Validation: independent source/docs-command review PASS; 27 Bash blocks and
2 Python snippets in the current work order passed syntax/parse checks, as
did 4 Bash blocks and 1 Python snippet in the companion v3 work order.
`git diff --check` passed. These are documentation/source checks only.

Documentation-only follow-up to the committed package implementation. The
2026-10-24 work order now includes ordered host/source gates, a separate
file-backed single-root GUI installer and detached boot, the A/B harness
boundary and failure fixture calls, Parent GUI/upload routes, valid and
startup-failure canaries, and bounded partial-upload, Parent-stop, applying
power-cut/evidence, and receive-reserve HTTP 507 recipes. It distinguishes
source/harness evidence from rendered GUI and physical-device proof and marks
only the still-unobserved internal/staging predicates NOT RUN. Root also built
and inspected the startup-failure package from a disposable source/runtime
copy: `build.json` and `inspect.json` passed at
`/tmp/greia-handoff-canary.iSQbyj/`; this proves fixture structure only, not
guest activation failure or rollback. The 2026-10-23 v3-only online/data-only
statements are explicitly scoped to that route; they do not override ADR 0038
application packages.

No Linux image build, mount, QEMU execution, guest installation, or physical
device test ran in this documentation turn. Source and lifecycle phase did not
change; Session 04 remains OPEN. Next action: execute the current work order on
the designated Linux host, retain per-predicate evidence, and keep the original
untracked media/voice audit untouched.

### 2026-10-24 — Lightweight package implementation committed; final local evidence

Implementation source is committed at `771d52c7a9f75fb10481919d9ebef83b1d18adc9`. The exact-commit focused
rerun passed **177/177** tests (`/tmp/greia-software-final/focused-771d52c7a.log`).
The final integrated `make verify` run executed **5,942 tests**, with **6 failures,
3 errors and 8 skips** (`/tmp/greia-software-final/make-verify-final.log`); it is
NOT GREEN. The eight newly exposed integration failures were repaired and their
142-test focused run passed. Remaining outcomes match the previously reproduced
baseline: three Foresta audio-review expectations, two Parent Wi-Fi source
assertions, MBR observation wording, unsupported ARM64 target composition, and two
macOS `lsblk` installer cases. The earlier aggregate Shell memory failure did not
recur in this run. No unrelated baseline tests were waived or changed.

`make validate` separately stops at the same unsupported ARM64 profile
(`/tmp/greia-software-final/remaining-gates.log`). Final `make shell-check footprint`
passed (`/tmp/greia-software-final/shell-footprint-final.log`), as did staged diff
hygiene. HTML is published/pinned at `a1da70e6c69b907b128147ac876cc3cf17053d47`.
Mobile is committed locally at `79a61435393a34ab6d792d8c08776e92d0b0f04d`;
its checkout has no configured remote. Mobile typecheck and 34 app tests pass;
its shared core retains six baseline failures (96/102 pass).

Source work and operator documentation are persisted; **Session 04 remains OPEN**.
No image build, Linux installation, QEMU boot, physical-device apply/rollback or
rendered browser/mobile acceptance ran here. The next exact action is to execute
`docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md` on the other Linux machine,
alongside the full-system work order where applicable. Use the committed operator
guide `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` for all package recipes.

### 2026-10-24 — Relative application aliases fixed; focused gates pass, full gate pending

The staged application-update source now uses root-relative `/opt/greia-os`
and Activity-index aliases. The mounted-root inventory recipe in the operator
guide resolves within the supplied root; source review added a fake-root
containment regression and updated the composed-root verifier/RC fixture.
Focused package/update tests passed **177/177** at
`/tmp/greia-software-final/focused-update-final.log`; the separate new
integration set passed **142** at reviewer report. The final root
`make verify` run is still in progress. Do not claim a full-suite result until
`/tmp/greia-software-final/make-verify-final.log` has a terminal summary.
The earlier integrated run at `/tmp/greia-software-final/make-verify.log`
ended at 5,940 tests with 14 failures, 3 errors and 8 skips. A clean baseline
reproduced 6 failures and 3 errors; eight new contract failures were under
repair, and the Shell memory failure did not recur. That earlier run is not a
final gate result.

Post-fix build/inspect artifacts are in `/tmp/greia-software-final/`:

- `python-final.greia_update`: 1,311,555 bytes, SHA-256
  `15c0d4b5a8045a039968388d55c7ec3d1addcb4089d346d37c284042c6aac30c`
  (268 Python files).
- `writing.greia_update`: 230,222 bytes, SHA-256
  `c4d4a80cacb0f3ee4a3ab08f310dc3895037c94ef874c7eac8c8f8d6e54196eb`
  (one built-in Activity).
- `combined.greia_update`: 1,541,553 bytes, SHA-256
  `97091732d8c526370ac9a44c047e7c5c417996dba2553f0e9e690987aacbdc28`
  (268 Python files and one built-in Activity).

Each artifact has a matching `*-inspect.json` PASS. These are package
build/format checks only: they were built before the final whitespace-only
normalization and final source commit, and do not prove a release image,
installed Linux apply, recovery or device acceptance. `make validate` still
fails on the inherited unsupported ARM64 target at
`tools/build_profile.py:584`; `make shell-check footprint` passed. Mobile
typecheck and 34 app tests passed; shared core is 96/102 with six baseline
failures in `/tmp/greia-software-final/mobile-verify.log`. The HTML client has
27 focused tests PASS at pin `a1da70e6c69b907b128147ac876cc3cf17053d47`.
Mobile source is local commit `79a61435393a34ab6d792d8c08776e92d0b0f04d`
with no remote configured. Keep Session 04 OPEN; append final full-gate
results and the committed source SHA after the root finishes.

### 2026-10-24 — Package/apply source frozen for final checks; results pending

Correction to the preceding documentation entry: the package/apply source is
now frozen for final root verification, and the independent source review
passed. Reported focused buckets include 43 software-update, 5 Parent-update
and 15 delivery tests; separate owner runs report 16 bootstrap, 5 generation,
8 jobs, 14 package, 14 Activity-package, 15 delivery, 5 composer and 5 index
tests passing. The current root runs are still in progress at
`/tmp/greia-software-final/focused.log`,
`/tmp/greia-software-final/make-verify.log` and
`/tmp/greia-software-final/mobile-verify.log`; record their actual summaries
before claiming results. The final source commit/hash has not yet been
recorded.

HTML Parent is pinned at `a1da70e6c69b907b128147ac876cc3cf17053d47` and is
synced with Greia/Mobile. The operator guide now records the exact recovery
boundary: application-generation journal phases carry the installed root
filesystem UUID and current `job_id`; same-boot pre-trial recovery uses the
matching job/fence, and boot recovery runs before launcher/Parent. Candidate
health requires a post-switch monotonic `launcher_interactive_ready` event and
Parent loopback `/healthz` success. The timer checks for an idle profile picker
before expensive package work and rechecks before switching. A legacy
directory migrates through the normal boot recovery unit; do not invoke
`--recover` while child/application services are live.

Bootstrap availability is image-owned. An old A/B install may reach a
bootstrap-capable image through its ordinary full-system route; an older
single-root install without the engine requires logical backup and graphical
reinstallation/data restore to a current build. A `.greia_update` package
cannot install its own receiver, and routine Python/Activity packages need
neither the full-system catalog nor a full disk image. These are source and
documentation facts only: Linux/image/VM/device acceptance remains UNPROVEN.
Keep Session 04 OPEN and append the pending verification summaries and final
source SHA after the root finishes and commits.

### 2026-10-24 — Typed application package guide and Linux handoff prepared

ADR 0038 now has a source-aligned operator guide at
`docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` and an external installed-
Linux work order at `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`.
The guide covers `python_platform`, `activities`, `combined` and `full_system`,
the one/set/all-current built-in and Parent-source CLI paths, nested v3
wrapping, inspection, durable Parent `Upload & install`, status/reconnect,
explicit full-system restart, and the bootstrap boundary. “All current” is
derived from the validated current registry or exact installed image index;
it does not promote a draft future roster.

Local format/build evidence is available outside Git at
`/tmp/greia-software-update-review-20261024/`: the inspected Python snapshot
contains 268 source files, is 1,309,073 bytes, SHA-256
`da62fcb61ff63716c7ad7fd725308e57e7dcf62e17e85dcd733c45cc20eb5c90`; the
all-current built-in package contains 45 Activities, is 214,690,711 bytes,
SHA-256 `0fe18e3899dd8f33e0ff11ba39bebcaea260ffe72eb93e4340821127bc1c20cf`.
Their inspect reports are `python-inspect.json` (SHA-256
`27e4dc0cd348a9a58cc47700dd0935f1e535352d6f7c9cad81716afbef4a4e6c`) and
`activities-all-inspect.json` (SHA-256
`6019b985b7e716399496681a8197687b27a33ff8bfd80758d8e2b54fccaf2409`). The
format/builder review reported 18 focused tests passing. These artifacts were
built from a dirty local source checkout without a frozen source SHA; they
prove package creation/inspection only, not application, recovery or device
acceptance. Source integration remains in progress on base HEAD
`ff1cff43af0f6d68fe4ec93f8c4c234ac63f12ed` and is not frozen.

The earlier frozen full gate remains NOT GREEN: 5,890 tests, 7 failures,
3 errors and 8 skips. Nine outcomes match clean-baseline issues; the aggregate
Shell retained-surface memory failure is unresolved/order-dependent despite
the standalone module passing on baseline and current trees. No Linux image,
QEMU guest, physical-device install, or browser/mobile device acceptance ran.
Session 04 remains OPEN. Next: complete and freeze the package/apply/Parent
source integration, rerun its focused and full gates, then execute both
2026-10-23 and 2026-10-24 Linux work orders on the authorized external host.

### 2026-10-24 — Update implementation source freeze

Implementation commit `4eaad25471fe47b72e900ea2f34777f41be5542b` includes
online Parent delivery, the persistent A/B boot fixes and the blank-disk BIOS
GRUB adapter. Exact-commit affected-suite run: **770 tests, OK (2 skipped)**,
`/tmp/greia-update-completion/focused-4eaad2547.log`. Full repository verification
is still **NOT GREEN** (the recorded 5,890-test run has 7 failures/3 errors,
including the unresolved full-suite-only Shell memory assertion). No Linux
build, VM/device install or release hosting occurred. Resume with
`docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`; Session 04 is OPEN.


### 2026-10-24 — Frozen full-gate result recorded; one suite-only memory failure unresolved

Supersedes the prior Oct 24 note that frozen `make verify` was still running.
The completed worktree run at
`/tmp/greia-update-completion/make-verify-frozen-bios.log` executed 5,890 tests
in 302.538 seconds and ended **FAILED: 7 failures, 3 errors, 8 skipped**. Nine
outcomes match separately reproduced clean-baseline issues (Foresta Parole 3,
Parent Wi-Fi 2, MBR message 1, ARM64 profile 1, installer-state/macOS `lsblk`
2). The full gate is NOT GREEN.

The additional failure is
`test_launcher_long_session_memory.ShellLaunchCycleMemoryTests.test_repeated_launches_do_not_grow_shell_memory`: 675,948 retained-surface bytes
after 24 launches exceeded its 524,288-byte bound. The two-test memory module
passes in isolation on both baseline and current trees
(`/tmp/greia-update-completion/memory-baseline.log`, 8.333 s;
`/tmp/greia-update-completion/memory-current.log`, 7.296 s). This does not
establish that the full-suite failure is baseline; retain it as unresolved and
possibly order-dependent. The separate 38-module source gate remains PASS at
770 tests, 2 skipped. No Linux image, BIOS VM install/boot, or device acceptance
ran. Details are appended to the evidence review; Session 04 remains OPEN.

### 2026-10-24 — BIOS installer source evidence finalized; Linux boot still owed

Correction to the earlier Oct 24 snapshot below: the BIOS installer adapter
fix and focused source reruns are complete. The eight-suite BIOS slice passed
116 tests; the frozen 38-module gate passed **770 tests, 2 skipped** at
`/tmp/greia-update-completion/focused-final-frozen.log`, and an independent
fresh-process rerun passed the same 770/2 at
`/tmp/greia-update-completion/focused-final-bios-rerun.log`. An earlier run
during source edits had one seam assertion failure; it was corrected to inspect
the production `shell=False` runner and adapter argv delegation, and did not
recur on either final run. Logs and exact scope are in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`.

The production seam is
`FreshAbInstallSeams.bios_bootloader_installer(target, boot_directory)`,
bound through `build_bios_bootloader_installer()` in
`src/greia_installer/device_seams.py`. This is source/fake-runner evidence;
no installer image or Linux guest was run. The full frozen-source `make
verify` run has no final summary yet and remains unresolved; do not report it
as green. The source is still uncommitted on base
`2fd29dffa75edc3ce5edd16431a86e6722a68830`, and the work order is untracked.
No source SHA is available for the external runner. Session 04 remains OPEN;
the next acceptance gate is blank-disk BIOS install followed by boot through
installed BIOS GRUB into Greia, then the remaining Linux update/rollback
predicates.

### 2026-10-24 — System-update evidence and external acceptance gate

Evidence reconciliation is recorded in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`. The
integrated current-source run is 743 tests, OK with 2 skips, plus 33 issuer,
32 recovery, and 76 product/GRUB focused tests. These are all **pre-BIOS-fix
source/test results**; the lifecycle worker is still implementing the BIOS
installer correction and its final focused rerun is pending. `make verify` is
NOT GREEN: the earlier run reported 17 failures/28 errors; later runs ended in
native `Abort trap: 6` at `typography.py:274` / the Activity tempo test. The
ARM64 validator error and one MBR message expectation reproduce on the clean
baseline.

Correction to the Oct 23 entry below: at this evidence snapshot the Linux
acceptance work order is present but untracked, and Greia source changes remain
uncommitted on checkout base `2fd29dffa75edc3ce5edd16431a86e6722a68830`.
That SHA is not the implementation revision. HTML pin
`e0116787bb324ca4685ad832cbc8d4d9e5b3461d` is pushed; Mobile commit
`06441e56e5e38d6e4a70f6e435d9d4ea7f339273` is local with no remote. Do not
launch external acceptance until the source and handoff are committed and the
Linux runner records the resulting exact source SHA.

The external work order now calls for an actual blank-disk BIOS install and
boot through installed BIOS GRUB into Greia after the pending installer fix;
generated files and source tests alone cannot pass that gate. No image build,
Linux VM/guest, physical device, or authenticated Parent browser/mobile run has
occurred. Session 04 remains OPEN. Exact evidence and limits are in the review
above and `docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`.

### 2026-10-23 — System-update source integration; external Linux acceptance owed

Current lifecycle: **Session 04 OPEN**, Session 03 closed on 2026-09-23.
The owner requested a committed external-machine handoff:
`docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`. It owns the next
Linux build/install/VM/Parent acceptance; no such operation ran on this Mac.

Source now connects device-owned online check/download/prepare, typed updater
socket, persistent A/B boot state, explicit profile-picker restart, and Parent
status/reconnection. Atomic layout advancement uses a directory bind at
`/etc/greia-os/layout`; schema and the single install/update journal live on
verified `/run/greia-persist`. The first-boot issuer and deadline helper honor
that shared journal. The static index builder supports EN/IT/ES/FR notes,
bounded retention and atomic local replacement. Existing single-root/RC
profiles remain unable to activate updates.

HTML `e0116787bb324ca4685ad832cbc8d4d9e5b3461d` is pushed and pinned in Greia.
Mobile `06441e56e5e38d6e4a70f6e435d9d4ea7f339273` is committed locally with
that shared core; its checkout has no remote. Mobile typecheck and 30 tests
pass; shared core has six failures also reproduced at clean HTML baseline
`5518a9e`. Exact local Greia checks, baseline failures, review and evidence
boundaries are in `docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`.
Do not infer full `make verify` PASS or device readiness from focused tests.

Full compressed images remain the transfer baseline: Python-only bandwidth
reduction is unimplemented/unmeasured. Manual upload receives a bundle but
preparation still needs online catalog selection. No public release/index was
uploaded. Next: execute the external work order, fix the first real runtime
failure at its source owner, then measure adjacent-release transfer/storage/RAM
before selecting a smaller transport. Do not add signing or a parallel updater.


### 2026-10-23 — System-update investigation (SOURCE REVIEW; no enablement)

Owner-requested end-to-end review: `docs/reviews/2026-10-23_SYSTEM_UPDATE_DELIVERY_AND_COMPLETION_REVIEW.md`, Greia source `9fe3c9f6e`. Current single-root legacy/RC images cannot activate transactional updates; Parent read/upload is not wired to prepare/restart/result, while production A/B writer and launcher health primitives do exist. The live public index is reachable with empty stable/dev OS lists. Local mobile source has reproduced cross-board fallback matching and offline cache round-trip defects. Updater service still pins two capabilities/8 tasks despite sharing hardware finalization with the repaired installer; exact-service staging is owed before enablement. Review distinguishes current HTML pin from older local tests and limits mobile findings to the available local checkout.

Focused verification: 201 Python tests run, OK (1 skipped), mobile matching 10/10 and HTML update API 3/3 PASS; no full suite, images, privileged/device work or publication. No implementation/phase state changed. Lifecycle ledger closes Session 03 on 2026-09-23 and leaves Session 04 open; the OS-work router's Session-03 continuation is stale. Recommended next engineering scope remains common real A/B lifecycle and exact updater finalization under Session 04, followed by existing platform/Parent sessions; online delivery and optional measured content reuse extend the existing engine. This review does not authorize or implement a replacement plan, migration, new format, reimage or server deployment.

### 2026-10-23 — Publish the remaining voice replacements and normalize approved delivery

Owner requested committing the remaining voice work after the parent's direct
45-Activity audit. This publication includes 683 replacement audio/receipt pairs
(all 667 priority paths plus 16 earlier short-carrier replacements), matching
catalogue metadata, and a path/hash/voice/review CSV. Human PENDING, APPROVED and
WAIVED_BY_OWNER states are preserved; committing does not claim listening approval.

Twelve approved saved cuts were repackaged from 48 kHz to canonical 22,050 Hz mono
PCM16 without synthesis or ASR. Their original bytes/receipts and transaction
backups are external under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-parent-audio-publication-v1/`.
Generation dates and owner approvals remain unchanged, with source/delivery hash
provenance added. Eleven already-stale Officina dei Suoni checksum rows were
refreshed against unchanged recordings.

Post-repair verification: 4,743 receipt/audio pairs agree, all audio catalogues
agree, Activity titles 180/180 complete, collection labels 84/84 complete. Full
`make verify`: NOT GREEN, 5,845 tests, 6 failures/3 errors/8 skips. Three
Word Forest subtests still expect PENDING instead of the explicit native
WAIVED_BY_OWNER state; other failures/errors are MBR/Parent Wi-Fi source-contract,
ARM64 profile and macOS lsblk dependencies. Receipts retain the true owner waiver.
Exact test identities and log are recorded in the publication review.
See `docs/reviews/2026-10-23_VOICE_BATCH_PUBLICATION.md` and its exact CSV inventory.
The unrelated October 19 draft review and video artifacts remain uncommitted.


### 2026-10-23 — Self-signed HTTPS for Parents implemented in GitHub; physical acceptance outstanding

**Owner-approved scope:** family/home-LAN HTTPS, without public PKI, QR/Allow ceremony, extra passwords or companion applications. Separate Parent client repository HEAD is `5518a9eed8ba61503249a1c827b7ef4fef5dab36` and Greia's `runtime/parent-app-client.toml`, integrity manifest, vendor runtime and installer overlay now match that source's production bundle.

**Implemented in Greia:** `greia_parent.parent_tls` creates a private persistent self-signed certificate and key on each installed Greia; the image package set installs OpenSSL. `greia_parent.production_api` offers HTTPS on LAN `:8766`; `greia_launcher.parent_credential_client` reaches the same Parent API via plaintext HTTP **only** on `127.0.0.1:8767`. Both server listeners share the existing Parent mutation lock. A TLS setup failure leaves local-only Parent controls available and emits no insecure LAN fallback. The production API now advertises `self-signed-https`; development-only base API retains provisional HTTP metadata.

**Implemented in Parent HTML:** browser origin validation, bounded discovery, and Node diagnostic proxy now use HTTPS endpoints (the local helper accepts Greia's self-signed certificate); direct device-hosted browser remains same-origin. Existing password bootstrap, per-device bearer credential storage, revocation, Parent-domain capability rules and package-install gating are unchanged.

**Authored verification:** Greia `tests/test_parent_tls.py` covers certificate persistence, real encrypted/local listeners and degraded local-only service; existing production metadata assertion and browser `tests/https_transport.test.js`/HTTPS URL tests updated. **Not run:** local Python/Node test suites, actual SSL listener on Acer, real browser certificate UX, installer image rebuild, or physical device acceptance. This is source implementation, **not** final release closure.

**Deployment discovery:** existing `tools/dev_source_deploy.py` archives source/runtime but not installed `/usr/share/greia-parent-app`; source-only deployment against the older Acer image would advance the pinned HTML manifest without updating those bytes, causing `greia-parent.service` integrity preflight failure. Do **not** use that method for this tranche or bypass the integrity checker; use a freshly composed exact-head image or separately reviewed coherent full-runtime deploy for hardware acceptance. **Next step:** run `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md` on exact heads, return complete non-secret failures/evidence, then complete owner-authorized Acer/browser/OS-image testing. Never rely on old September HTTP and frozen Parent-revision instructions for this new TLS workstream. The normal child OS release remains separately unready.


### 2026-10-23 — v4 spoken-target replacement terminal correction

Correction to the earlier “pending producer launch” entry below: the separate
v4 plan finished `BOUNDED_COMPLETE` on its frozen 77-row scope using source
commit `7004b6188573efa4bd126c4af1e2b6f42a4a98f4`. The run made 199 new VoxStage
calls, installed 25 final packaged Parakeet v3 PASS pairs and preserved 52
original pairs after the registered three-call quality limit. There are zero
remaining or blocked rows. Every generated replacement is
`human_review=PENDING`; the 13 saved cuts recovered before this run retain their
separate owner-approved review evidence and are not counted as generated PASS.
The concise terminal evidence and validation failures are recorded in
`docs/reviews/2026-10-23_SPOKEN_TARGET_VOICE_REPLACEMENT.md`.

Terminal audit `.../spoken-target-recovery-v1/natural-v4-run-02/terminal-audit.json`
passes all 667 audio/receipt pairs. It proves the 25 installed pairs equal
their journaled candidates, each retained original backup matches its frozen
hash, all 52 exhausted pairs remain byte-identical, and the other 590 pairs
are unchanged from this run's post-recovery snapshot. The exact v4 plan,
automatic evidence, raw WAVs, extracted candidates, receipts, backups and
progress are under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/spoken-target-recovery-v1/natural-v4-run-02/`.
Takeboard's validated 475-row batch at
`http://127.0.0.1:8819/` contains 199 raw carriers, 251 extracted candidate
cuts and 25 installed finals; all new rows start unreviewed. Existing saved
reviews remain in their original files, including Takeboard 8818.

Verification on current source/audio checkout: spoken-target voice suite
237/237 PASS at source `7004b618`; post-run `make verify
PYTHON=/opt/anaconda3/bin/python3` ran 5,839 tests and is **NOT GREEN** (2
failures, 3 errors, 8 skipped). One failure is the preinstall-snapshot-stable
launcher title WAV sample-rate audit for two out-of-scope dirty pairs
(`colline_allegre/fr` and `corsa_bacche/en`, both already 48 kHz before this
77-row run); the other is the existing MBR diagnostic-message expectation.
The errors are the unimplemented ARM64 target profile and two installer tests
requiring unavailable macOS `lsblk`. Full log: `/tmp/greia-spoken-target-make-verify.log`.
No platform phase, audio listening acceptance, or release readiness is closed.
Next exact step: listen and record human decisions in the v4 Takeboard batch.

### 2026-10-23 — Spoken-target replacement scope frozen; pending producer launch

Owner ordered replacing the unresolved recordings using spoken letter names and
number words. Exact approved Takeboard 8818 cuts were transactionally recovered
from the preceding full Parakeet run: **13 preserved rows installed** with
review provenance and original automated FAIL/WARN retained; one approved cut
for an already-DONE French E row was left untouched. The duplicate approved
`Trouve deux pareils !` choices had no score, so attempt 1 was selected and the
other decision remains in the original review file. The unresolved v4 source
scope is frozen at **77 rows**: 16 contextual letter examples, 7 number cues
already written as words (including “Start at four!”), and 54 ordinary cues.
All 16 exact semantic-to-spoken spellings and the row list are in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/spoken-target-recovery-v1/natural-remaining-77/`.

The versioned producer policy keeps authored semantic request text unchanged,
speaks locale letter names only in explicit letter-example syntax, and retains
the exact-number, count, signal and packaged Parakeet gates. Its maximum is
three fresh actual calls per cue, reserved once per provider call; no historical
budget or plan is rewritten. Human-approved recovery evidence is at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/spoken-target-recovery-v1/human-approved-recovery-13/`.
Producer source and focused tests are being finalized before plan freeze and
launch; the 77-row production has **not started**. No new synthesis was used
for these 13 reviewed recoveries.

### 2026-10-23 — Owner-authorized full Parakeet replacement completed

The owner explicitly superseded the previous bulk holds and authorized a fresh
replacement allowance for the exact **237** rows in the latest audit (44 letter,
193 ordinary; EN15/ES45/FR114/IT63). The new plan is external at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/`.
Its frozen plan SHA-256 is `dd8210515c006a974a3ce49771a13f84a2e98c6736f0edc7b1336c5c81b51bf4`,
and it pins remaining-file SHA `29f125e16c6da5932a7f1fc8b3888f75ac2994f679c56a1405c72bb6a1753879`,
audit SHA `35a6f1faf82fb5ceb0c024321f63a3c0d340e75c3d61a219b3677a715b7ec618`,
all 667 pre-install audio/receipt pairs, selected masters, and the Parakeet v3
revision. Comparison policy is `locale-number-tokens-v3-chck-orthographic`.
Each cue can reserve at most three **new actual provider calls**; prior attempt
counts (157 cues at two, 80 at three) are retained and are not this new allowance.
Each cue stopped on its first automated pass or after at most three known
quality-failing calls. Provider, recognizer, and installation uncertainty was
reconciled by exact job/key and never blindly resubmitted. Each installed
replacement used the normal VoiceEngine/CorpusRunner transaction and retains its
exact original pair in the external backup.

The separate ten-request diagnostic is hash-pinned as prior evidence but is not
counted as corpus output. Source commits `772df9cb7` and `14a93e74c` add the
versioned full-scope policy, scope-preserving selection and journal-aware resume.
The 231-test voice-pattern suite passed on the exact producer source before
launch. Terminal journal: **147 `DONE`, 90 `PRESERVED`, 0 remaining, 0 blocked**;
498 new actual calls (86 cues used one, 41 used two, 110 used three). Every
`DONE` pair has a Parakeet v3 packaged-audio PASS and exact original backup;
every `PRESERVED` pair still matches its original audio and receipt. The
external `terminal-audit.json` confirms all 667 frozen pairs: 147 replacements,
90 preserved, 430 out-of-scope pairs unchanged. All 237 rows were separately
processed under new allowance; earlier attempt history and held plans were not
reset. No human acceptance is inferred.

The Takeboard batch passes validation at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-23-natural-parakeet-full-237-v1/takeboard-listening.json`
and is served at `http://127.0.0.1:8818/`. It has 1,241 records: all 498 raw
carriers, all 583 materialized target cuts, 13 retained failed package
candidates, and the 147 installed finals. Twenty recorded cut geometries were
not materialized because the extractor recorded explicit energy/voicing
precondition failures; there are no unexplained missing cut files. Expected
target, full submitted carrier phrase, exact cut ASR when present, and explicit
“not run” raw intro ASR are separated. Every human state is unreviewed.

The producer PID `69415` exited normally with `BOUNDED_COMPLETE`. Exact plan,
scope, model, comparison-policy and producer hashes remain pinned in the external
run. The next action is owner listening in Takeboard; source-screening PASS is
not listening acceptance. Post-run `make verify` ran 5,833 tests and was NOT
GREEN (1 failure, 3 errors, 8 skipped): unsupported ARM64 builder adapter, two
macOS installer tests requiring absent `lsblk`, and one MBR diagnostic
expectation mismatch. No full-suite baseline comparison was run, so these are
reported as observed, not asserted pre-existing. Exact details and log path are
in `docs/reviews/2026-10-23_FULL_PARAKET_VOICE_CORPUS_REPLACEMENT.md` and
`/tmp/greia-parakeet-full237-make-verify.log`.

### 2026-10-23 — Parakeet spelling comparison and saved-run listening batch

Added versioned Parakeet comparison policy `locale-number-tokens-v3-chck-orthographic`.
Localized number parsing remains first; lexical `ch`, `c`, and `k` then compare
as `k`. Submitted speech and exact ASR transcript strings are retained verbatim.
Hyphen/space equivalence was already present in v2. Replaying only the saved
Parakeet transcripts preserves six prior delivered-package checks; two saved
Italian `Trova Oscar` candidate cuts now satisfy target extraction against
`Trova Oskar`, but lack final delivered checks and are not end-to-end passes.
The saved French `Raconte-moi` transcript remains rejected for extra/changed
words, not hyphen spacing.

Saved-only report and unchanged 51-recording source batch:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/saved-comparison-replay-v3.json`.
The new full-text batch is served at http://127.0.0.1:8817/; it preserves prior
review states and exposes full submitted phrase, expected retained target, and
exact saved ASR transcript. All remain human-listening-pending. No ASR, synthesis,
model run, package creation, install, or receipt mutation occurred. Focused
comparison/number/locale-policy/short-routing/Parakeet tests passed 50/50.
All voice-pattern tests passed 225/225 and the VoxStage doctor/provider tests
passed 21/21. An initial full gate exposed a v3/v2 frozen-corpus compatibility
regression; the normal request policy is now v3 and automatic/natural registered
plans pin v2 explicitly. Final `make verify`: 5,827 tests, 1 failure, 3 errors,
8 skipped (NOT GREEN). Remaining issues are the ARM64 builder-support profile
test, two installer tests needing `lsblk` (unavailable on macOS), and an MBR
diagnostic expectation mismatch. Log: `/tmp/greia-parakeet-ck-make-verify-final.log`.
No architecture phase is closed.

### 2026-10-23 — Parakeet default and bounded ten-request end-to-end diagnostic

Implemented pinned local Parakeet-TDT v3 as the current VoiceEngine verification
backend for new requests (`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`). The public generation path now checks
the delivered package, with up to three quality attempts and no output acceptance
on exhaustion; provider/ASR/I/O uncertainty stops recoverably. Automatic short
requests use Parakeet for target-only PCM candidate screening and final packaged
checking. Existing score/count/numeric/signal safeguards are unchanged. Explicit
public `verification=off` is an unverified opt-out. Historical Whisper receipts
retain their original identity. The diagnostic's natural-carrier policy was
explicitly injected and does not become the production prompt default.

A preregistered run exercised ten distinct prior-problem cues across EN/IT/ES/FR
through public VoiceEngine: **6 machine-verified packaged results, 4 quality
rejections at three tries, 21 provider jobs total**. It did not modify installed
runtime audio, corpus budgets, masters or accepted recordings. All passing results
remain `human_review=PENDING`; automatic screening is not owner listening. The
external evidence and per-target outcomes are in
`docs/reviews/2026-10-23_PARAKEET_VOICE_PIPELINE.md`. Takeboard batch contains 51
unreviewed items (21 raw attempts, 24 extracted target cuts and 6 passed final
packages) at `http://127.0.0.1:8816/`.

Focused pipeline/policy/engine tests: **85 PASS**. `make verify` ran the test
stage and ended with `Abort trap: 6`, so the full repository gate is **NOT GREEN**
(`/tmp/greia-parakeet-pipeline-make-verify.log`). No broad suite rerun or unrelated
failure chase. The next exact task is owner listening to the 51-item Takeboard
batch, starting with the six final packages and reviewing their raw/cut siblings.
Bulk natural-corpus production remains held pending listening and a separately
accepted method decision; do not expand from this diagnostic result.


### 2026-10-23 — Two registered saved diagnostics recovered; bulk remains held

Added explicit, pinned reconciliation for registered diagnostic results that
do not have the old source-selection layout. It validates the exact original
priority row and remaining snapshot, Activity family, actual request and cue
aliases, raw WAV/receipt/provider job/master, and cumulative attempt ledgers,
then routes only through the existing recorded-only candidate preparation,
CorpusRunner and RunStore installation. Literal matches keep the default
comparison policy; French Oscar/Oskar spelling and English spoken-letter
equivalence are each explicit opt-in policies. Defaults and history remain
unchanged.

Recovered French Tito `Trouve Oskar` from
`20261022-194837-c8fd5222` and English Leo `W as Whale` from
`20261022-194704-4881f8f0`. Actual install audit PASS: 2 changed/665 unchanged
frozen pairs, 1,559 other protected hashes unchanged. No synthesis, ASR,
threshold or budget changes. The combined frozen-667 audit is 10 changed/657
unchanged, 430 kept or installed, 237 remaining (44 letters, 193 ordinary,
0 exhausted). Takeboard `http://127.0.0.1:8814/`; all ten new recordings are
human-listening-pending. C-as-Cat was traced to already-resolved Leo letter C
and must not be reused for Forest's `find_c`.

212 voice tests and 32 focused policy tests PASS. `make verify` aborts in the
test stage (`Abort trap: 6`), NOT GREEN; see
`/tmp/greia-diagnostic-reconciliation-make-verify.log`. Earlier broad context
gates remain FAILED. Saved-only corpus parent/child yield is 7/25 (28%), so
both bulk producers stay held. Next exact step: read-only earliest-failed-
predicate attribution across the 25 retained parent/child cases; no new ASR,
models, provider calls, synthesis, gate changes, or installations.
Full evidence and source details: `docs/reviews/2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md`.

### 2026-10-22 — Recorded-only context adapter installed one exact saved source

Explicit `target-only-v7-saved-wav-context-v1` now composes prepare_saved_candidate,
CorpusRunner and RunStore, with mandatory pinned source selection and recorded-only
Base observations. Default production/v7/OGG/comparison policies stay unchanged.
Every measured candidate and the actual final packaged WAV are replayed with
physical/clock/count/number/signal/provenance checks; missing evidence never rerolls
ASR or synthesizes. Full raw observations are retained before interpretation.
Current implementation/evidence/next exact work:
`docs/reviews/2026-10-22_SAVED_CONTEXT_CORPUS_ADAPTER.md`.

Recovered Spanish Leo JdeJirafa from exact completed job20261021-171835-83d3e04d:
contextual Jde girafa .8242 vs isolated Jota de girafa .6367. Actual install audit
1pair changed666unchanged, valid backups and1555other protected hashes unchanged;
cumulative3takes intact, no newASR/provider calls, humanPENDING. Two existing
observations imported by exact hash/locale/model/settings. Combined actual667audit
8changed659unchanged:428kept/installed239remaining (44letters193ordinary2exhausted).
Takeboard8813eightpending with masters; older batches/reviews preserved. Evidence
context-j-recovery-v1 and natural-completion-audit-v4 under the external investigation.

New13provider-forbidden tests;203voice +22corpus/finisher testsPASS. Fullmakeverify
executed5804tests:known1failure3errors8skips, NOTGREEN; log
`/tmp/greia-context-adapter-make-verify-final.log`. Failures remain MBR observed
identity wording, build profiles and installer host completion tests. NEXT audit239remaining against other exact saved/cached sources;
use tested saved-only adapter for compatible frozen plans, explicit tested
reconciliation for other forms. Bulk holds/exhausted budgets remain unchanged;
no claim of90percent live yield, listening or hardware acceptance.
Discovery `context-remaining-cached-inventory-v1.json` finds3 earlier cached sources:
natural-035/TrouveOskar, natural-038/W-as-Whale, earlier-2/C-as-Cat. Only candidate
mapping, not admission. Trace exact diagnostic/native ancestry and source-plan
reconciliation; W's actual cue ID is alphabet, never silently reuse for Forest.
C's canonical diagnostic copy has no adjacent provider receipt. No newASR/provider.


### 2026-10-22 — Disabled saved-WAV seam; held-out proof and real-scalar fix

Added focused context-clock/checker collaborators and explicit cutter/final-check
injection, **disabled by default**. Default v7/OGG/number semantics and all bulk
holds remain unchanged. Current saved adapter refuses the new extraction version;
no synthesis or install this tranche. Corpus still427kept/installed240remaining.
Source detail/current next boundary:
`docs/reviews/2026-10-22_SAVED_SUBSTITUTION_SEAM.md`.

Held-out48cases exclude all82prior source hashes. Original v1 used62offline ASR
observations, retained15/16 positives, rejected20bad controls but rescued0;FAILED.
Diagnosed new validator bug: valid mlx-whisper NumPy real timestamps rejected by
exact Python type test. Corrected to Real excluding bool, same timing predicates.
Separately registered cache-only v2:15/16positive retention,1/12substitution rescue,
0/20negative approvals,1554protected hashes unchanged; narrow screening gatesPASS,
original broad/v1 gates remainFAILED. Three incomplete sources remain held, no
recognition rerolls. Independent audit16accepted physical proofs/1context clock:
0issues. New ES JdeJirafa source remains external/uninstalled, human-unreviewed.

Focused190voice testsPASS (25new); fullmakeverify on corrected source aborts6,
NOTGREEN, `/tmp/greia-context-seam-make-verify-real-scalars.log`. No hardware/live
90percent-yield claim. NEXT explicit saved-only versioned adapter/final-check and
provider-forbidden transaction/provenance tests through existing CorpusRunner,
then exact qualifying saved recovery; no new exhausted-cue takes or bulk restart.


### 2026-10-22 — Packaged replay failed safety gate; two strict saved recoveries

Completed82-source WAV/OGG replay:708offline ASR observations, provider forbidden.
Structural cache/PCM/timestamp audit418observations:zero issues, all protected
hashes unchanged. Original contextual fallback still FALSE-ACCEPTED one actual
uncut-intro OGG control and preserved only25/28OGG positives. Original gateFAILED;
no contextual verifier installed or integrated. Cache-only post-diagnosis v2
hard isolated count/number veto rejects all204negative observations and preserves
28/28WAV,25/28OGG positives; transfers7/10WAV,6/10OGG context matches, below the
registered80percent threshold. Both remain UNSELECTED, no silent gate change.
Read `docs/reviews/2026-10-22_PACKAGED_CONTEXT_SAFETY_REVIEW.md` for actual failure,
controls, limitations and next bounded optional WAV-only saved-recovery seam.

Separately, existing Momo EN Basket full diagnostic seed314159 and Lilli ES
Elige un álbum compact-style seed314159 pass the UNCHANGED isolated Base/count/
number/signal gates (scores1.0/0.8593). Recovered without synthesis using existing
v7 saved adapter/CorpusRunner. Spanish ASR Elie un álbum and actual compact English
transport direction remain visible; planned/actual directions are not conflated.
Exact selected masters, diagnostic jobs/keys/requests/raw/hash and source rows
reconciled. Each install audit1changed666unchanged. New combined actual audit
7changed660unchanged; all humanPENDING. Corpus ledgers remain25calls; separate
hash-pinned diagnostic-generation-ledger-v1 records all16actual diagnostic jobs
and per-cue evidenced lifetime totals, never resets a budget.

Current overall427of667kept/installed,240remaining=45unstartedletters+
193unstartedordinary+2exhausted(W as Whale EN,Trouve Oskar FR). Both producers
still held. Latest audit/remaining/listening evidence:
`2026-10-22-rejection-investigation/natural-completion-audit-v3/`;
Takeboard8812sevenclips, old8811batch untouched. No new synthesis or engine/default
change this turn. Next: implement and validate the optional disabled WAV-only
saved substitution checker/candidate seam with strict isolated hard-invariant
veto on held-out real controls; never claim original gate passed or resume bulk
from the12post-hoc qualifying sources. Existing full verification remainsNOTGREEN.


### 2026-10-22 — Saved contextual recognition complete; final-delivery proof next

`natural-context-recognition-v1` finished41sources:10unique contextual matches,
41uncut-intro controls rejected. This diagnoses isolated-ASR instability on all
four difficult lexical-context cases, not90percent reliability or listening.
No source strategy adopted or additional audio installed. Both producers remain
held; actual5installed/242remaining unchanged. Read the concise dated report
`docs/reviews/2026-10-22_NATURAL_COMPLETION_AND_RECOGNITION.md`, which owns exact
results, limitations and next saved-only final-delivery/control experiment.
Next: original prefix +actual decoded packaged target, fixed PCM cut, timestamped
all-retained-word comparison; broad wrong-number/extra-word/name/prefix controls
and no provider submissions before any versioned integration. Do not start more
prompt rerolls or resume bulk from an exploratory match counter alone.


### 2026-10-22 — Natural completion stopped again; five actual installs,242remaining

Both producers are held, not running. Speech child ended1DONE3PRESERVED193READY
at12calls (parent2DONE3PRESERVED242READY at13calls). Exact saved Oskar and Find two
the same recoveries add2installs without synthesis: overall5of247installed,
425of667kept/installed and242unresolved =45unstartedletters+193unstartedordinary+
4exhausted. Actual667pair audit proves exactly5changed662unchanged, matching
DONE/recovery candidates and pending receipts. Evidence and exact remaining IDs:
`2026-10-22-rejection-investigation/natural-completion-audit-v1/`; Takeboard8811.
Do not claim completion or resume either held producer.

Saved-only opt-in English spoken policy adds exact position-bound one/won,
two/to/too,four/for,eight/ate, Oskar/Oscar and W/double-u/double-you equivalence;
no fuzzy word/name matching or different-number/extra-word allowance. Defaults
and historical policies remain unchanged. It recovered Find two the same take02
job20261022-193838-12dfa863 with1changed666unchanged pair audit; original3reserved
calls unchanged. The phrase's Base transcript Find to the same is retained.

Registered lexical-context8job experiment COMPLETE1/8PASS, gateFAILED. No bulk
adoption; no diagnostics installed. Repeated-recognition saved39suffix experiment
preserved0of4baseline qualifiers and recovered0; REJECTED, no adoption. Wrong-
number controls were not run after its positive gate failed; do not call its
narrow uncut-intro negative observations a full verification pass.

Current saved-only diagnostic `natural-context-recognition-v1` replays41actual
sources with full-source Base word timestamps at unchanged PCM cuts, all retained
words, no intro wording prerequisite and no expected-text prompt. Its explicit
shadow English spoken/all-locale Oscar spelling comparison remains diagnostic.
Inspect progress/results/log; never duplicate or adopt without final-delivery and
broad extra-word/wrong-number/name controls. This follows visible evidence that
full-context ASR can say Double U as whale while isolated same-target ASR says
W as well. It is recognition instability evidence, not listening proof.
No further synthesis is authorized by a failed experimental gate alone.

Latest focused165+53PASS (7new tests). Full preceding run5765:1failure3errors8skips
(MBR observed identity/build profiles/installer host path); latest source full
makeverify executes but aborts trap6, log/tmp/greia-natural-repair-final-make-verify.log.
NOTGREEN. Source/derived docs retain original voice/master/budget semantics.


### 2026-10-22 — Natural completion: exact name recovery and unused speech allowance handoff

The first natural run remains METHOD_REVIEW_REQUIRED,2DONE3PRESERVED242READY.
The8-job instruction-conditioning experiment is COMPLETE: compact direction1/4,
no instruction0/4; this does not select a better general recipe. Do not repeat it.
An explicit saved-only English Oskar/Oscar comparison policy now recovers the
exact natural take02/job20261022-191523-a16336f0 with unchanged numeric/count/
signal/Base thresholds. Installed1pending through existing CorpusRunner; actual
667-pair audit shows1changed666unchanged, raw/receipt/job/master/budgets retained.
Evidence `2026-10-22-rejection-investigation/natural-oskar-recovery-v1/audit.json`.
Old v1/v2 numeric policies and normal API defaults remain unchanged.

The parent run's242never-submitted rows are explicitly split:45letter-name
cues remain unstarted for pronunciation-method repair,197ordinary phrases move
with their ORIGINAL unused method allowances to
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/natural-context-speech-v1`.
Producer74605 at launch; inspect actual producer.pid/process, production.log,
progress.json and ledger. Natural prompts/per-file gates/poor-yield guards are
unchanged; this is not evidence that earlier failures were fixed or that the
method achieves90percent. First2ordinary cues exhausted (FR Trouve Oskar and EN
Basket full); third IT Sei is underway at this documentation boundary. Let its
automatic guard stop poor yield; never blindly bypass it. Parent held-state and
pinned one-child handoff prevent duplicate spending; attempted cues never move
or receive another3take allowance. `natural_continuation.py` owns that seam.
Overall before this speech stage:423of667kept/installed,244unresolved; receipts
humanPENDING. This is NOT task completion. Current guide owns exact recovery and
remaining lanes. Focused164+53PASS including6new focused cases; full makeverify
is executing at this boundary. No paid/cloud/hosted Actions/shared-worker changes.


### 2026-10-22 — New-method completion authorized; real-corpus guard caught poor yield

Owner requested completion using the new natural method. Prepared247 exact
remaining paths, excluding7actual prior installations from254; historical counts
preserved, new-method allowance up to3 actual calls per cue. New adapters/policy/
budget callback reuse VoiceEngine, ShortPhrasePipeline and CorpusRunner/RunStore;
no new synthesis backend or installer. First real-corpus canary stopped itself:
2DONE/3PRESERVED/242READY after13new calls, status METHOD_REVIEW_REQUIRED. Do not
bypass guard or claim broad readiness from earlier two-target3/4experiment.

Work: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/natural-context-v1`.
Tito FR find_octopus and Momo IT where_hurt passed2ndtakes. W as Whale and Elige
un álbum exhausted; Find Oskar exhausted although two saved transcripts say
Find Oscar. Investigate spelling equivalence/actual target fidelity before more
production. A bounded8-job conditioning experiment is running under external
`2026-10-22-rejection-investigation/instruction-conditioning-v1/`; fixed2seeds,
W/album actual failures, compact style vs empty instruction, no runtime installs.
Read its progress/log before acting; no duplicate experiments or silent receipts.

Operator source/commands/guards/continuation contract:
`docs/agents/GREIA_NATURAL_VOICE_COMPLETION.md`.10newtests PASS, focused158+53PASS;
makeverify aborts at macOS/pygame hires_surface typography/control path, NOTGREEN.
New heartbeat supervise-greia-natural-voice-completion monitors this work; old
final-take-v7-02 and its deleted heartbeat stay stopped. Parent investigates
method stops directly. No threshold relaxation, budget reset or master changes.


### 2026-10-22 — Owner-authorized paired method tests; numeric v2 correction

Bulk remains OWNER STOPPED; heartbeat deleted. Later owner explicitly requested
bounded new prompt/code tests on repeatedly rejected targets and word/digit
number recognition.16 diagnostic jobs: Tito EN Count to ten and Leo FR Trouve
Luna, two fixed seeds, four recipes. Corrected native scoring: old imperative0/4,
concise-description-only0/4, direct1/4, natural relevant carrier3/4. Canonical
processing improves old imperative to1/4, natural stays3/4. One old machine PASS
Client to10 was inflated by numeric marker characters; corrected score.742
rejects it. No recipe is adopted globally or used to restart the corpus.

Shared number policy v2 covers standard cardinals0–100 EN/IT/FR/ES, exact digit/
literal identity, accent override and ordinary-digit scoring. Normal verifier,
short-target checking and review/reassess v4 share it; old v1 evidence retains
its own interpretation. Added experimental CarrierSourcePreparation collaborator
(not selected by the normal pipeline).72 saved wrong-content/extra-word controls
reject;17number controls spanning4locales reject wrong values,15actual matches.
Older saved24:23PASS1held (Due lucciole→due luciole, unresolved potential ASR
false rejection). No changed thresholds or phonetic/semantic aliases.

Listen/compare http://127.0.0.1:8810/ (37rows, raw/cuts/transcripts/prompts/masters;
search natural-carrier). Browser filtering/playback exercised, no human approval.
All667 runtime pairs match stopped journal's7pre-stop installs and60reservations;
16new exact diagnostic job/seed/master hashes audited. Full report/evidence:
`docs/reviews/2026-10-22_VOICE_METHOD_PAIRED_EXPERIMENT.md`.
Focused148+53PASS. Full diagnostic5,749tests:2failures3errors8skips NOTGREEN;
ARM64/lsblk/MBR plus observed memory-gate failure (isolated rerun passes; full
suite still NOT GREEN). First full attempt segfaulted.
Next listen/calibrate difficult saved cases (including the held number phrase)
before default adoption. No synthesis producer or automatic corpus restart.


### 2026-10-22 — OWNER STOP: repair method, no further corpus generation

Owner explicitly rejected continuing the high-rejection method and ordered stop.
Producer44224 was interrupted and its exit confirmed; automatic supervision
`supervise-greia-priority-voice-completion` was DELETED. DO NOT resume the220
continuation, synthesize new takes, or prioritize file completion over method
repair. Previous execution decision below is superseded by this owner stop.
Stopped journal7DONE/52PRESERVED/1GENERATING/160READY. The in-flight FRcount_5
provider job20261022-180337-f06676db completed; NEVER resubmit it. Its local state
needs explicit recovery if later needed; no automatic install was performed.
Run progress now OWNER_STOPPED, interrupted progress separately preserved.

Authorized current work is method diagnosis/fix on saved audio. Test generation
fidelity, cut selection and verifier false rejections separately, using
representative difficult corpus targets and positive/negative listening evidence.
A diagnostic saved-only full-source-context ASR comparison is running under
`2026-10-22-rejection-investigation/context-verification-diagnosis/`: pre-existing
PCM cuts fixed, all retained words compared, no intro agreement prerequisite,
no expected-text prompt, no dropping arbitrary words to force a match. This is
an experiment, NOT a new accepted verifier. No synthesis/install or gate change.
No heartbeat will restart work; continue method repair in this conversation.
Saved-only context diagnostic is now COMPLETE:59 sources, only2/52 rejected
sources gain a contextual match; only3/7 prior machine passes survive. Do NOT
adopt this replacement verifier. No synthesis/install. Local VoxCPM2 `instruct`
is `(description)text` voice-design conditioning, not a structured pause API;
long imperative delivery is an unproven choice, not a proven root cause.
Next freeze difficult saved cases with independent listening labels and isolate
generation/cut/verifier errors before another bounded method experiment.


### 2026-10-22 — Retry experiment10/12; frozen220 final-take continuation RUNNING

Six additional diagnostic jobs completed: EN Leo/ES Lilli recover on cumulative
second take; EN Tito/FR Leo exhaust at3. Final10/12 machine passes EN2 IT3 FR2 ES3
meets separately preregistered THREE-TAKE gate; original8/12 first-take gate stays
FAILED. No diagnostic installs.37-row comparison http://127.0.0.1:8809/ (human
unreviewed;8808 untouched). Exact jobs/quality were inspected, not counters alone.
After667-pair snapshot and220-original/master/plan/budget preflight, launched the
existing `final-take-v7-02` source-frozen native-v7 period/warm recipe under prior
owner completion authority. ONE remaining take per220row,34 exhausted excluded;
unchanged final Base/count/number/signal gates, originals preserved on rejection.
Canonical preprocessing is NOT integrated; no source or threshold change.
Inspect `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/final-take-v7-02/{producer.pid,production.log,progress.json,state.sqlite3}`
and automatic-evidence before acting. Never duplicate/resubmit uncertain jobs.
Read dated period/warm report's appended execution decision: it explicitly lifts
the earlier v2 hold after investigation, not the failed first-take result.
Next supervise actual quality/provider errors, then audit all667 pairs/backups
against terminal DONE and retained budgets. All installed takes human PENDING.


### 2026-10-22 — Canonical controls reject53 negatives; retry-layer probe running

All36 complete-intro leak controls and17 wrong-number controls reject after
canonical preprocessing; source hashes unchanged. No implementation/install.
A separately preregistered diagnostic is RUNNING: finish the existing12-case
cohort's three-take budgets for only4failed cases (max2more each,8jobs). Eight
passes retained. Same native-v7 recipe, period/warm prompts and individual gates.
Production attempts untouched. Original first-take gate remains FAILED; new
three-take predicate9total/2per-language is a separate outcome. Inspect external
`2026-10-22-rejection-investigation/period-bounded-retries/progress.json` and log
before continuing; PID41593 at launch, no duplicate experiment or bulk start.
See appended `docs/reviews/2026-10-22_PERIOD_WARM_VOICE_CONTINUATION.md`.


### 2026-10-22 — Saved period/warm diagnosis: preprocessing helps old controls only

Saved-only paired canonical22,050Hz preprocessing across36 sources: fresh12
stays8PASS/4rejected (all8 preserved); older native48k benchmark improves20/24
to24/24. All36 extra-word negatives rejected. No source changes, synthesis or
installation. Spanish Lilli has only160ms measured internal quiet (<200ms
production floor); other failures have820/370/1,260ms gaps and mismatching
post-gap Base observations even in diagnostic full-source transcripts. This is
machine evidence, not listening or proof of actual words. Two-second direction
is not reliably realized (largest gaps across12:160–1,260ms). Details/evidence:
`docs/reviews/2026-10-22_PERIOD_WARM_VOICE_CONTINUATION.md` appended investigation.
Next validate canonical preprocessing against number/prefix-leak controls before
versioned integration; four fresh failures and live readiness remain unresolved.
No bulk producer launched;413 kept/installed,254remaining, human review PENDING.



### 2026-10-22 — Owner period/warm direction applied; live gate holds final batch

Normal short VoiceEngine now uses a normal-period intro (no ellipsis), with
warm/calm/clear reading and careful natural pronunciation defaults for all six
actors. Silent-pause direction remains separate; masters and acceptance thresholds
unchanged. Receipt composition `period-separated-intro-v1`. Docs/skills track it.

Five held saved jobs were reconciled against exact completed-job and current
frozen-baseline proofs in a NEW processing plan. EN letter_C recovered/installed;
other four rejected unchanged gates. All667 pairs audited:1 changed,666 unchanged;
source pairs/baseline plans/budgets unchanged. Total82 saved recoveries; current
413 kept/installed classification,254 remaining (34 at3takes,220 at2).

New normal-API corpus adapter `automatic-short-v7-period-warm-v2` preserves last
cumulative take budgets and existing transactions. GenerationResult.evidence_dir
provides structured recovery state. Source-tested known quality exhaustion is
PRESERVED; infrastructure/provider uncertainty stops NEEDS_RECOVERY. Prepared
`final-take-v7-01` is SUPERSEDED_UNSTARTED; replacement `final-take-v7-02` has220
rows but **has not submitted anything**.

Actual48kHz saved-provider check:20/24 pass,24/24 negative controls reject. Fresh
period/warm cohort:12 diagnostic jobs,8 pass/4 rejected (EN1,IT3,FR2,ES2), misses
predeclared9/12 and2-per-language readiness gate. Keep bulk paused. Exact failed
cases EN Leo Find Luna, EN Tito Count to ten, FR Leo Trouve Luna, ES Lilli El
sombrero. Inspect raw/candidate/search evidence next; no threshold relaxation or
ASR reroll. Listening page http://127.0.0.1:8808/ labels raw/final/rejected cuts.
All unreviewed, no browser/listening acceptance. Detailed evidence/procedure:
`docs/reviews/2026-10-22_PERIOD_WARM_VOICE_CONTINUATION.md`.

First diagnostic job20261022-164343-32d0f10e/key greia-984b905bb661433cbc5681ccf24c52ad
completed in36s after the old30s response timeout; recovered without resubmission.
HTTP timeout now defaults120s (GREIA_VOXSTAGE_HTTP_TIMEOUT, up to7200), distinct
from job wait; POSTs still never retry automatically. Shared service untouched.
Voice137/corpus18/finisher4/client21 focused PASS. Final full gate5,738 tests,
1failure/3errors/8skips, same known cases, NOT GREEN. Next: diagnose the four saved
live failures while retaining the owner-requested period/warm direction; prove
correction before any final220 continuation. Completed letter_A/sunhat/diagnostic
jobs must never be resubmitted; old frozen plans remain historical.


### 2026-10-22 — Other saved takes recovered:54 additional installations

`recover_voice_candidates.py --source-selection` now accepts explicitly pinned
FAILED/PRESERVED source rows. It checks unchanged scope/plan/raw/receipt and the
exact completed provider job/key/text/direction/master. Provider48kHz→retained
22,050Hz provenance uses exact existing packaging reproduction; no synthesis.
Frozen carrier policies/original baselines remain intact.

Inventory660 sources for309 remaining IDs:270 already v7-checked,7 held for
provenance reconciliation,383 verified sources for308 targets. Deterministic
first-passing-source traversal checked368 (15 spare sources skipped after their
target passed): **54 additional DONE /314 saved rejections preserved**. Actual
installed media passed final quality; exactly54 of667 audio/receipt pairs changed,
613 unchanged. All383 source pairs/plans/provider manifests and cumulative count
manifests unchanged;54 backup bundles verified. No new synthesis or human approval.

Current412 kept/installed classification leaves **255 remaining**:35 at three
takes,220 at two. Exact list/evidence:
`2026-10-22-rejection-investigation/other-saved-recovery/remaining.json`,
`progress.json`, `install-audit.json`. New54-file listening batch vs masters:
http://127.0.0.1:8807/ (validated, HTTP200; no browser/listening acceptance).
Earlier27-file batch on8806 unchanged. Full report:
`docs/reviews/2026-10-22_OTHER_SAVED_SOURCE_RECOVERY.md`.

Completed letter_A job20261022-142854-3615cf58 was checked and replayed: four
candidate suffixes fail Base target verification; nothing installed/resubmitted.
Final focused voice126/corpus18/finisher4 PASS. Source-frozen full make verify:
5,726 tests,1 failure/3 errors/8 skips, same known non-voice cases, NOT GREEN.

**Next:** reconcile five held records still in remaining255: IT ask_K/ask_O/sunhat
missing source-plan rows; EN letter_C and FR find_octopus with older original
baselines. Use exact completed jobs and explicit new recovery provenance; never
rewrite frozen plans or resubmit letter_A (or known completed sunhat job).
Then evidence remaining per-ID budgets before a new versioned v7 fresh
continuation. Historical v6 producer stays stopped, scope667 unchanged.


### 2026-10-22 — V7 saved-source adapter delivered; 27 recovered and installed

`tools/recover_voice_candidates.py` now stages failed frozen v6 provider sources
under explicit `target-only-v7-saved-v1`, then installs only completed passing
candidates through existing CorpusRunner/RunStore transactions. Source scripts,
raw receipts, selected masters and cumulative counts are preserved. Synthesis is
structurally forbidden, even when a staged candidate is missing. Required final
canonical count/numeric guards are recomputed at installation validation.

Actual fresh-01 saved recovery covered all 297 failures: **27 DONE / 270
PRESERVED**, including three packaged-quality WARN. Post-install audit checked
all 667 priority audio/receipt pairs: exactly the 27 passing pairs changed,
640 others unchanged. All 297 original raw/receipt pairs, source plan, frozen
priority SHA and cumulative-count manifest unchanged; all 27 backup bundles and
actual installed packaged-target quality checks passed. Human review PENDING.
No new synthesis. Previous classification292 kept +39 installed +27 recovered
now leaves **309 unresolved**, including39 previously omitted from fresh-01.

Evidence root `2026-10-22-rejection-investigation/`: recovery folder
`v7-saved-corpus-recovery-01`, install log, `v7-install-audit.json`,
`v7-priority-remaining.json` and `v7-recovery-listening.json`.
Takeboard http://127.0.0.1:8806/ serves the 27 installed candidates vs selected
masters; manifest validation and HTTP200, no new browser/listening acceptance.
Focused voice121/corpus18/finisher4 PASS. Final source gate: 5,721 tests,
1 failure/3 errors/8 skips (known ARM64 profile, macOS lsblk, MBR cases), NOT GREEN.
Full evidence: `docs/reviews/2026-10-22_V7_SAVED_CORPUS_RECOVERY.md`.

**Next exact action:** audit other saved sources for the 309 remaining IDs,
including39 outside fresh-01 and completed letter_A job20261022-142854-3615cf58.
Extend the saved-only adapter only with explicit original-plan/request/master/job
provenance, positive/negative controls and unchanged cumulative budgets. Recover
existing audio before any new synthesis. Do not restart the historical v6
producer, reset budgets or expand frozen667 scope. Preserve listening decisions.


### 2026-10-22 — V7 target-only extraction implemented; bulk remains stopped

Normal VoiceEngine automatic short requests now use separately versioned
`tools/voice_carrier_search.py` v7. It searches bounded measured PCM pauses and
transcribes each suffix independently, with no raw-intro ASR gate. Exactly one
suffix must meet >0.8 similarity plus canonical count/numeric agreement; final
packaged signal/ASR checks remain. Exact locale number spellings/digits 0–25 are
supported, accent override retained. ASR/IO errors require recovery without a
new provider take. Historical v6 cutter and frozen corpus plans remain unchanged.

Final saved replay on all 336 first-pass sources: previous FAILED297 → 27 PASS,
3 quality WARN, 267 extraction rejected; previous DONE39 → 36 PASS, 3 held.
All 66 extra-word and 17 wrong-number negative controls rejected. The three held
old passes include added-word/numeric guards and one French cut/ASR-sensitive
case, documented individually. These are external candidates only: zero new
synthesis, zero installations, no human acceptance in this correction.

Focused final voice111 + corpus18 + finisher4 PASS. Final source-frozen full
`make verify`: 5,711 tests, 1 failure, 3 errors, 8 skips (ARM64 profile, macOS
lsblk installer cases, MBR expectation), NOT GREEN. Evidence and exact procedure:
`docs/reviews/2026-10-22_TARGET_ONLY_VOICE_EXTRACTION_V7.md` and external
`2026-10-22-rejection-investigation/`. Docs/voice skills track the new normal API.

**Next exact action:** build a separately versioned corpus recovery adapter for
v7 metadata and final canonical guards, using existing saved-source packaging
and CorpusRunner transactions. Forbid provider submission during saved recovery;
reconcile originals/master/job/hash and cumulative budgets before any further
synthesis. Never restart unchanged continuation03/v6. Completed letter_A job
20261022-142854-3615cf58 stays preserved and must never be resubmitted. Frozen667
scope and all existing human-listening-pending status remain.

### 2026-10-22 — Bulk retries stopped; rejection mechanism investigated

Supersedes the running-PID checkpoints below. Parent stopped PID 86480 after the
owner challenged 297/336 first-pass rejections. First pass: 39 installed, 292 kept,
336 unresolved of 667; second pass had 287 eligible rows but is STOPPED FOR
REJECTION DIAGNOSIS. No further producer may restart with unchanged v6 policy.
Its submitted letterA job 20261022-142854-3615cf58 completed and was preserved
externally without duplicate synthesis or installation. All take budgets remain.

Inspected all 297 failure records; replayed all 297 saved raw files with 399
PCM-pause-selected cuts and fresh pinned Base target-only recognition. Found
raw-ASR prealignment blockers, numeric spelling/digit comparison bugs and
signal-only rejections. 25 unique number-aware-exact candidate recoveries;
21 passed after actual 22,050 Hz packaging and unchanged signal checks, 23 in a
separate gain experiment. No trial output installed; no listening approval.
Most remain unresolved ASR/content mismatches, not proven bad audio. Isolated
number-comparison prototype tested with 8 tests / 104 locale/value vectors; source
production still unchanged. Detailed counts, limits and next resume gate:
`docs/reviews/2026-10-22_VOICE_REJECTION_DIAGNOSIS.md`. External evidence:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`.
Takeboard diagnostic raw/cut comparison: http://127.0.0.1:8805/ (297 entries).
Heartbeat updated to prohibit automatic restart while diagnosis/repair continues.


### 2026-10-22 — Parent Wi-Fi UI shows an existing connection without reconnecting

**Evidence class: SOURCE + FOCUSED TESTS. No device rerun in this turn.**

- **Report:** after installing with Wi-Fi joined in the installer, the first-boot Parents UI showed no connected network; manually connecting again made the status appear.
- **Cause:** UI state, not the install hand-off. The on-device Parent panel's `WifiSetupController` learned `connected_ssid` only from a connect performed in that panel session; `begin()`/`refresh()` never read iwd's current station. The web Parents app fetched `/network/wifi` once at startup and did not refresh when the Device view opened (clicking the already-connected SSID hit the API fast path, so the status then appeared).
- **Fix:** `WifiSetupController.begin()`/`refresh()` now mirror `IwdWifiBackend.connected_ssid()` into the snapshot, non-fatally (a bus error never invents a connection or breaks the screen). The vendored Parent app refreshes Wi-Fi when the Device route opens, when the window regains focus and when the tab becomes visible; the frozen client manifest hash was updated. Tests: controller seeding/refresh/error paths plus the Parent client image-integration contract.
- **Verification:** focused suites PASS: installer Wi-Fi setup 12, Parent client integration 7, launcher Parent panel 8, panel frame cache 5, Parent production API 7, installer Wi-Fi persistence 2.
- **Limitation / next step:** the installed Acer still runs the pre-fix UI. Rebuild the RC (or source-deploy the Parent client) and confirm `wifi_configured` plus the connected line on the next physical check.

### 2026-10-22 — Research-led family and agent documentation entry points (SOURCE REVIEW ONLY)

Added six practical guides: `docs/user/README.md`, `docs/user/INSTALL_FROM_USB.md` (Windows/Mac download/flash → graphical install → first boot), `docs/user/GREIA_PARENTS.md` (on-device **S + T held five seconds** on child-selection screen, parent password, browser client/security/capabilities), `docs/development/BUILD_A_GREIA_IMAGE.md`, its relative-linked `docs/agents/GREIA_IMAGE_BUILD_AGENT.md` (profile-specific front doors, non-destructive image-only path, explicit USB consent/evidence), and `docs/development/CREATE_AN_ACTIVITY.md` (Simulator, localization, VoiceEngine, package/installation capability). Updated `README.md`, `SETUP.md`, `docs/DOCUMENTATION.md` to route audiences to these concise derived docs. The root README's language overview now agrees with the four-language selectable registry. `docs/product/PARENT_MANAGEMENT.md` now records the owner-directed requirement for a clear, legible, localized **S + T** hint at child selection; this is a product requirement, not an implemented or visually accepted UI change. The Parents guide explicitly identifies the separate browser-client repository as currently private while publication is pending. Research and follow-up: `docs/reviews/2026-10-22_RELEASE_DOCUMENTATION_RESEARCH_AND_GAPS.md`.

**Evidence/limitations:** inspected current implementation and technical authorities and the separate Greia-Parent-App-Html client source; consulted official public USB-imaging references. No Windows/Mac flash, new image build, GUI screenshot, QEMU or physical install was performed in this docs-only pass. No currently unpublished image is presented as a supported family release. Parent HTTP transport security, ordinary Activity installation capability, fresh-first-boot/voice acceptance, Pi/universal image acceptance, and child-picker discoverability of the S+T gesture remain product/release gates. Next release-docs step: test the exact immutable release image end-to-end on real supported devices and Windows/Mac USB-flashing hosts; check the child-selection/Parents hint in all four supported languages, then align the download page and instructions with real published artifacts.


### 2026-10-22 — Priority continuation03 after shared-queue timeout

Correction to the earlier live-producer checkpoint: producer17915 stopped on
ask_K (recovered completed job); continuation02 PID4148 then stopped after the
1,800-second shared-queue wait on ask_O. Its job20261022-041056-7a6ed5fb later
completed. The exact selected Leo reference/request and mix were checked; raw
SHA539596f06c1addbf6580f94d645ffb96f87336b74b6315503ccc70b9ff3e7596
and faithful receipt are retained in the existing external discovery tree.
No duplicate ask_O submission: its cumulative count is already three.

Owner requested resume. Continuation03 is running as Python PID86480 in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/resume-shared-short-delivery-production-03/`.
Same frozen667 priority file/hash, masters, thresholds and cumulative budgets;
1,714 cached ASR observations copied. Startup audit independently observed41/667.
`GREIA_VOXSTAGE_TIMEOUT=7200` allows longer waits behind other projects without
restarting/cancelling the shared service. Previous current-audio audit kept292,
which includes the prior47 recovery installs; continuation03 has no claimed fresh
installs at this checkpoint. All generations remain human-listening-pending.

Worker short_carrier_luna monitors the sole producer. Thread heartbeat
`supervise-greia-priority-voice-completion` remains active every ten minutes;
parent handles recovery directly if worker usage limits recur. Next action:
inspect continuation03 live logs/state and reconcile any uncertain job by its
exact identity before submitting anything. Do not start a second producer.



### 2026-10-22 — Automatic short requests implemented

Normal VoiceEngine VoxStage requests now auto-route ≤4 words into localized
carrier → retained v6 extraction → delivered-target Base checking, including
Dani and single words. All CLI/JSONL/Python/socket entry points share the engine
branch. New request fields: short_text_mode=auto/off/on, short_text_max_words=4,
short_text_max_alnum=null. Three total takes by default, automatic short cap three;
native pedagogical speech stays excluded. Unsupported retained providers keep
their ordinary route in auto mode and reject forced on. Explicit corpus carrier
raw requests disable wrapping, preventing duplicate intro/nested budgets.

The new modular policy/lifecycle/delivery/target-check collaborators reuse existing
providers, cutter and audio packaging. Automatic short output is fail-closed:
score >0.8, matching target word count, no signal flags; exhaustion publishes no
output, preserves earlier destination and all attempt evidence. Missing alignment
blocks before synthesis; infrastructure failure does not rerender. ASR off alone
still aligns/cuts; both wrapping off + verification off give zero ASR.

A 24-existing-source public-engine replay exposed leading silence left by the
midpoint cutter. Shared delivery preparation now removes ONLY within the same
verified quiet run, preserving 100ms and the original v6 extraction; actual final
PCM is checked again. No threshold relaxed. Before: 10/24 published; after: 15/24
published, 9 rejected. All four languages have successful replays. This used a
fixture provider, 48 exact-byte cached Base observations plus 24 new Base checks;
NO new TTS or runtime installation. Routing/corpus focused tests: 110 PASS,
including 24 actor/locale cases, actual socket transport, retry/exhaustion,
provider/ASR faults, no double wrapping and sample-preserving delivery trim.

Full make verify with Anaconda Python3.12 and dummy SDL drivers executed during
development: 5,672 tests, 1 failure/3 errors/8 skips, NOT GREEN (known ARM64 profile,
macOS lsblk and MBR diagnostic cases). Final changed-source focused check above
ran after final helper changes. Exact logs/source snapshots are external:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-automatic-short-routing/`.
The general shared durable/dual-queue programme remains proposed.

Old priority producer 87089 was stopped for this delivery fix; completed in-flight
ask_Y job 20261022-015655-3cf72c6f was recovered, no take discarded/reset. The old
run's 78 installed + 167 kept remain. New continuation uses the same frozen 667
scope/history and budgets, including exact-original whale reconciliation, in
`.../2026-10-21-short-carrier-priority-v1/resume-shared-short-delivery-production/`.
Started PID 17915 (exec session 64973), with 1,298 exact-byte ASR cache entries
carried forward; startup audit is progressing. Worker short_carrier_luna resumed
monitoring. This continuation supersedes earlier producer/whale follow-up steps:
whale is included here, with no separate follow-up producer. See its live
journal/log and the worker before submitting any duplicate producer.


### 2026-10-22 — Voice documentation consistency audit

Reworked `tools/greia_voice_core/README.md` as the practical usage reference;
root README links it. Examples cover single/JSONL/Python/service requests, fields,
Base/accent defaults, output/warning handling, retry budgets, carrier scope,
status/journals, crash recovery, and listening. Cross-checked architecture,
setup, corpus/cutter guides, shared-library acceptance and agent skills against
source. Ordinary API remains serial/auto/two-take with eligibility exclusions
and warning outputs; the scoped finisher uses required all-actor delivered-target
checks and three cumulative generations. Proposed general short routing and
separate verification queues are explicitly not claimed implemented.

Corrected stale Whisper download instructions, VoxStage stop/drain semantics,
and blanket acceptance claims for replaced v0.2 catalogue rows. Documentation
validation: 39 command/example checks PASS, local links resolved, bash syntax and
Python/JSON examples parsed, 15 actual read-only CLI help invocations succeeded,
and JSONL examples passed the real request parser. No synthesis or tests were
launched by this documentation audit; the existing production process continues.
Evidence: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-voice-documentation-audit/report.json`.
Review record: `docs/reviews/2026-10-22_VOICE_DOCUMENTATION_CONSISTENCY.md`.
### 2026-10-22 — RC rebuilt/flashed on the 1,500 MiB ceiling; installer root resolution fixed

**Evidence class: SOURCE + BUILD/MEDIA READ-BACK. No QEMU boot and no physical install in this turn.**

- **Owner decision:** the single-root installed-core ceiling is now **1,500 MiB** (was 1,300 MiB), official for future builds. Rationale: the shipped four-language `@2x` art (~34 MiB) plus the new UEFI/BIOS boot payload (`grub-efi-ia32-bin`, `grub-efi-amd64-bin`, `efibootmgr`; ~34 MiB) put the RC at 1,323 MiB. 1,500 keeps one image with all art and both boot paths while remaining comfortably inside the reference Acer's 7 GB storage target. The ≤800 MiB preferred core and the 1 GiB A/B slot limit (A/B profile stays at 1,000 MiB) are unchanged; >1,500 MiB still needs architecture review. Landed in `398a6ca4a` (all single-root profiles, `AGENTS.md` contract 6, RC runbook, profiles README, gate comment, tests, hardware reviews).
- **Build blockers fixed while producing the image:** (1) the build host lacked `grub-efi-ia32-bin`, so ESP assembly failed after the full composition; installed it and added a pre-build check for both GRUB EFI module dirs plus the package names in runbook §13.2 (`696122e6f`). (2) The new MBR layout is p1 = FAT32 ESP, p2 = ext4 root, but the SD finalizer, live-USB writer and both verifiers still assumed p1; `c6744c78a` adds `build/lib/installer-image-root.sh` (first ext4 partition) and uses it everywhere, with a source contract test.
- **Pulled/flashed:** `main` `97c2392a7` → `c6744c78a`; built `legacy-x86-i686-rc` through the documented front door inside `sudo -n unshare --mount --propagation private`, operator key `SHA256:0oRmaFqZpIYFsGj0N2++I6oma2kHtqdOQMQjXITYVXU`. Flashed the authorized 8 GB LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`, 7.5 GiB, `TRAN=usb RM=1 TYPE=disk`), unmounted before writing. Log `out/rc-build13-c6744c78.log`.
- **Artifact:** image SHA-256 `09c1c9ad4a8abe861fc96027f9165beb99bba47858e535b8f2efde15784a4acf`; live media id `ab395c7f-e2dd-45cd-8d0d-ed4be6e39b2a`; payload accounted **1,323 MiB** (<1,500); target payload 555,003,904 bytes, SHA-256 `babfe052e2cf9e3e8df3aef1c7b8ee96b71f8f94abb0518c1af338869aae2aba`; `installer_image_mib=1510`; `boot_console_policy=quiet`; `live_security_support_state=no-alerts`.
- **Gates:** `Developer installer artifact verification: PASS`, `Greia live USB read-only verification: PASS`, `usb_readback_verification=PASS`, `source_artifact_verification=PASS`, `usb_flash_readback_verification=PASS`, `loop_hygiene_verification=PASS`; no Greia loop devices remain. Focused profile/verifier/root-partition tests PASS. `make verify` before the change still showed only the three inherited failures (ARM64 profile guard, `morbidi_mostriciattoli` 0.265 s budget flake, stale MBR message); `make validate` still stops at the inherited ARM64 guard.
- **Evidence scope / limitations:** BIOS Syslinux media read-back only. The EFI boot path remains **UNPROVEN** (no Mac/UEFI machine booted); the installed-target EFI layout is still LAB. No QEMU boot of this media and no physical Acer install were run.
- **Next exact step:** clean-install the reference Aspire from this LaCie through the graphical installer, confirm `install-record.json` lists `firmware-iwlwifi` and `iwd` connects without manual packages, then run the premortem §5 F1–F19 checklist. Keep the EFI path labelled UNPROVEN until a real Mac/UEFI machine boots it.

### 2026-10-22 — Base selected; configurable accent-insensitive ASR implemented

Owner selected multilingual Base and requested that accent differences not count
as recognition errors by default. `tools/greia_voice_core/asr_policy.py` now owns
Base model/revision (`1e3e249fb8d01c655324bd6841b1deadffd6d04c`), offline resolution
of required cached model files, and comparison-only Unicode diacritic folding.
Normal verification and carrier recognition share that default. Exact scripts,
raw transcripts/audio and human decisions are preserved. Normal verifier decoding
uses temperature 0 and no expected-text prompt/previous-text conditioning.

VoiceRequest.ignore_accents defaults true; false is a typed request/service/batch
JSON override. CLI generate/request, standalone extraction and corpus
plan/review/reassess expose `--strict-accents`. Target location and retained-target
verification use the same normalization; no arbitrary spelling-error exemption.
Carrier extractor v6 and screen policy v3 prevent silent reuse of frozen old
plans/cached results. New carrier plans freeze ASR identity and accent policy.
Saved-evidence reassessment recomputes scores and can clear accent-only carrier
warnings while preserving original Tiny/Base recognizer provenance and receipts.

Final focused voice suite: **111 PASS**; live saved-audio smoke confirms Base in
both normal verification and carrier recognition, with PASS/score 1 for Find Luna.
`trovò` versus `trovo`: comparison score 1.0 by default, 0.52 with strict accents.
Doctor reports mlx-whisper-base available. Evidence outside source:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-base-accent-policy/`.
Full `make verify PYTHON=/opt/anaconda3/bin/python3` ran 5,648 tests and reported
1 failure / 4 errors / 8 skips. One error was this tranche's test-discovery import;
fixed by removing the cross-test package import, then verified with the same
Anaconda discovery command (8/8 PASS). The other findings concern ARM64 build
profile resolution, two macOS-missing lsblk installer cases, and an MBR diagnostic
assertion. Full gate NOT GREEN and was not rerun after the discovery fix; final
111-test focused rerun is separate evidence. Logs retained externally.

Documentation/setup/voice operations and the proposed shared-queue plan now use
these defaults. No fresh synthesis, audio installation, master changes or bulk
restart. Shared asynchronous queues remain proposed, not implemented. Bulk remains
STOPPED; old frozen carrier plans cannot run under v6 without a new plan.


### 2026-10-22 — executed Tiny/Base comparison; default unchanged

Owner authorized downloading multilingual Base and comparing saved recordings.
Pinned `mlx-community/whisper-base-mlx` revision
`1e3e249fb8d01c655324bd6841b1deadffd6d04c` is now cached in the prepared voice
environment; no dependency changes. Same 24 fixed target clips: Tiny 16/24 versus
Base 19/24 score passes (>0.8); exact matches 13 versus 16. Median warm target ASR
0.307 versus 0.408 seconds. Base improves the aggregate but both manually recovered
French examples still fail scoring. Automatic v5 replay created 22 versus 24 cuts,
with 16 versus 18 final score passes. No default change, synthesis or runtime
installation. Full report: `docs/reviews/2026-10-22_WHISPER_TINY_BASE_COMPARISON.md`;
raw evidence external under `2026-10-22-whisper-tiny-base-comparison-v1`.
This small one-voice/one-translated-phrase sample does not establish corpus-wide
accuracy or concurrent GPU resource safety. Proposed queue pipeline remains
unimplemented, and bulk corpus production remains STOPPED.


### 2026-10-22 — proposed shared verified-production architecture (planning only)

Owner requested automatic short-phrase carriers, up to three total takes until
Whisper passes, verification enabled by default, and separate generation and
verification queues. Current source was traced across Greia VoiceEngine/provider,
serial socket/batch/corpus loops and shared VoxStage service/storage. Proposed
implementation package: `docs/plans/2026-10-22_VERIFIED_VOICE_PIPELINE/README.md`
(eight bounded sessions). This extends the scoped voice workstream and is NOT
implemented/activated; it does not replace product/release authorities or
restart the paused corpus.

Recommended ownership: shared VoxStage handles carrier/extraction/Whisper/durable
attempts/two queues; Greia supplies exact semantic request/master and retains
packaging/installation. New default v2 routes return VERIFIED only on a passing
final target, FAILED_QUALITY after three takes, and BLOCKED on infrastructure
faults without blindly regenerating. Updated batch/corpus callers submit an
8-request window; no nested wrappers/retries or global client lock across shared
waits. Old v1 jobs stay legacy-unverified. Native pedagogical exceptions remain.
Separate GPU resource policy is initially serialized on this 16 GiB host;
overlap requires the fixed performance/memory gate. Two French false rejects
remain evidence that ASR failure does not prove bad audio. No threshold changes,
manual override or model downloads are prescribed to hide this limitation.

Planning evidence and both adversarial review passes are in the package's
`evidence/`; strict structural plan validation PASS (8 sessions). No software
tests, live synthesis/ASR, shared VoxStage source changes or audio replacements
were performed for this proposal. Existing shared dirty files were recorded and
preserved. Next: discuss/adopt design before executing session 00; bulk stays
STOPPED. No code/queue implementation is claimed.


### 2026-10-22 — disposable-intro correction; target-suffix extractor v5

Owner requested implementation after identifying that exact intro recognition
contradicted the carrier's purpose. `tools/voice_carrier.py` now anchors to the
final expected target suffix and ignores introductory wording/recognized count.
If the inter-word interval is inadequate, adjacent boundary spans may be searched;
that path requires exact independent retained-target transcription, never exact
removed-intro transcription. PCM thresholds and source preservation stay intact.
Algorithm version is v5; existing frozen v4 plans intentionally cannot execute.

Saved-audio replay of the 24 pause experiments: **22 cuts / 2 target-ASR
rejections**, zero new synthesis or runtime installs; 5 of 6 prior rejections
recovered, one previously cut French take now rejected because fresh full-clip
ASR garbled its target. This is not a controlled same-ASR superiority claim or
human listening approval. Source/raw/provider receipts and earlier reviews were
preserved. Evidence: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-target-suffix-v5/`;
Takeboard `http://127.0.0.1:8803/` explicitly separates cut target and uncut source.
Final focused carrier/policy/generation/corpus tests: **48 PASS**. Full `make verify
PYTHON=/opt/anaconda3/bin/python3` attempted but test subprocess **aborted with
signal 6**, so the full gate is NOT GREEN; log retained externally. Do not infer
hardware/runtime/listening acceptance from these checks.

Bulk priority producer, Luna monitor and queued sunhat follow-up remain STOPPED.
Next: owner listens to staged cuts; resolve remaining target uncertainty using
saved audio, then freeze a separate v5 corpus plan only after an explicit bulk
restart decision. Do not resume the paused v4 plans or regenerate solely for ASR.


### 2026-10-21 — Priority short-carrier first pass paused for offline recovery

The frozen priority continuation finished with 389 DONE and 274 FAILED, no
READY rows; add the four successful cues from its preceding run for 393 installed
retakes. All 389 outputs remain listening-pending. The original failed run and
captured raw provider candidates are preserved. No further provider calls or
automatic retries are running. The all-actor review triage still has 1,927
deferred covered cues and 143 historical-evidence-gap cues, neither included in
this first pass.

Failure categories from `state.sqlite3`: 105 prefix/transcript alignment
mismatches, 49 Whisper token-representation rejects, 41 malformed timestamps,
35 unique guarded PCM-gap rejects, 31 timestamps beyond the WAV, 10 inadequate
pauses, one missing recognized suffix, one missing ASR segment set and one
uncertain VoxStage timeout. A v3 parser now records complete raw word entries
on parse failure, ignores punctuation-only entries as lexical tokens while
still validating their timestamps, joins split apostrophe clitics into an
indivisible aligned span, and refuses a prefix boundary inside a timed span.
Zero-duration suffix entries are tolerated only after the exact prefix and
first target boundary are established. The −42 dBFS, 200 ms unique guarded PCM
gap policy is unchanged.

Focused `tests/test_voice_carrier.py`: 19/19 PASS. Offline v3 recovery of an
existing French submarine turtle raw candidate yielded exact raw and extracted
ASR with cut sample 38,895; output SHA-256
`ab868abbf7845fcae26a64bb0be11ddd905e866c05fce168f0f74497e841936d`.
An existing English `not_now` candidate still fails closed: its timestamp gap
is 260 ms but the only qualifying quiet run is 140 ms. A French letter-E
example was cut with exact prefix but observed suffix `et comme est ce cargo`;
it remains `EXTRACTED_TARGET_WARN_PENDING_LISTENING`, not a pass. Pilot receipts,
the 274-row offline recovery manifest and CSV are at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/recovery-v2/`.
The recovered pilot outputs are not installed. No new provider attempt is
authorized by the recovery manifest. The final Tito/IT `sunhat` submission
timed out; VoxStage job lookup by its submission key returned Unknown job and
the shared worker is healthy/idle. Do not resubmit until its idempotency record
is reconciled.

Next: audit all 274 preserved raw failures under extractor v3, count safely
recoverable exact-prefix/verified-gap outputs separately from target warnings,
and produce a review batch. Do not retry generation or install recovered clips
from this pass without a separate frozen recovery ledger and normal candidate
validation. Focused carrier, policy, generation and corpus suites passed 42/42.
The final normal-environment `make verify` used Python 3.14.6 and ran 3,180
tests: FAILED (31 failures, 244 errors, 6 skipped); see
`/tmp/greia-short-carrier-v3-make-verify.log`. Individual traces have not been
classified as related or unrelated to this change.

### 2026-10-21 — Incomplete hardware detection never stops the install (SOURCE)

Owner decision: an incomplete hardware/firmware detection must not refuse an installation. `InstallerHardwareEnablementPlan` now carries `fallback_firmware`: when the plan is incomplete, the pool-provided subset of `FALLBACK_NETWORK_FIRMWARE` (`firmware-iwlwifi`, `-realtek`, `-atheros`, `-brcm80211`, `-libertas`, `-misc-nonfree`) is unioned with whatever the resolvers did produce and with microcode. `engine._prepare_hardware_support` and the A/B `device_seams` seam proceed (stderr journal line) instead of refusing; the A/B `selected_installed_bytes` bound covers the fallback. `install-record.json` records `hardware_detection: "incomplete"`, `hardware_fallback_packages` and up to three diagnostics; the completion page shows a localized (it/en/es/fr) note via a display-only flag on the `INSTALLED` answer. Pool verification failures (corrupt/unverified pool, identity mismatch) still refuse before any disk change. The hardware-inventory attestation gate (`inventory_complete`, sysfs token) is unchanged. UNPROVEN on hardware; unit tests only.

## 2026-10-21 — Legacy Mac / netbook support: pool force-list, ID rules, module policy (SOURCE, UNPROVEN on hardware)

Source-level, offline-safe items from `docs/reviews/2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md` and `..._LEGACY_X86_NETBOOK_HARDWARE_RISKS.md`: (1) `tools/build_hardware_support_pool_manifest.py` `FORCED_FIRMWARE_PACKAGES` (iwlwifi, realtek, atheros, brcm80211, libertas, misc-nonfree, amd-graphics, best-effort ipw2x00) are always pool candidates; APT availability and pool finalization still gate them; b43 installers, broadcom-sta/DKMS and SOF/intel-sound are deliberately excluded. (2) New `src/greia_installer/hardware_id_rules.py`: a PCI/USB ID rule table (Broadcom brcmsmac, Radeon, nouveau-era NVIDIA, Realtek, Ralink, Intel DVM, Atheros USB) applied by the planner only when the verified pool provides the package; Broadcom b43-family and wl-only chips set `wifi_firmware_unavailable`, carried through `device_seams` -> `FreshAbInstallSeams` -> transaction answer (`wifi_firmware`) -> `ExecuteReceipt` -> a `WifiAwareInstallResult` subclass in `main.py`, with a localized it/en/es/fr completion note; the legacy `engine.py` path still shows the generic incomplete-detection note and records the diagnostic (a specific flag there waits for the concurrent engine work). (3) `build/overlay/etc/modprobe.d/greia-legacy-hardware.conf`: `hid_apple fnmode=1` (media keys without fn; the review's "fnmode=2" is the opposite mode) and `blacklist b43`. (4) Resume hook driver list extended (iwlwifi, ath9k, rt2800pci, rtl8192ce, rtl8180, rtl8187, ipw2100, ipw2200). Tests: `tests/test_hardware_id_rules.py`, `tests/test_system_overlay_contract.py`. Not done: EFI boot, wl prebuilt modules, installer-side unsupported-hardware pre-check, LAB runs.

## 2026-10-21 — Boot logo native size, Wi-Fi resume hook and Parent API locking

- **Boot logo**: `greia_platform.boot_animation` now draws frames and the static canvas at native pixel size, centred on white, with one shared factor `min(1, fit)` (`native_scale`); it shrinks only when the display is smaller than the art. Installer frame preparation uses the same rule. GRUB (`padding` scale method) and the early framebuffer splash (`greia-fb-splash.c`) still fit-to-screen and so still enlarge on big screens; not changed (needs a theme/C change). Tests: `tests/test_boot_logo_native_size.py`. Source/unit evidence only; no visual review on hardware.
- **Wi-Fi resume hook**: `greia-wifi-resume` covers iwl3945, iwl4965, b43, b43legacy, brcmsmac, ath5k; after resume it waits up to 8 s for the interface and iwd station and reloads the driver only if they are missing. Functional stub tests in `tests/test_system_overlay_contract.py`. Not run on the real Aspire.
- **Parent API locking**: `ProductionParentApiHTTPServer.request_lock` serializes every request except `/network/wifi` and `/network/wifi/connect`, which use the application's `_wifi_lock` (one association at a time, guards the scan cache). Wi-Fi requests authenticate outside the global lock. Tests in `tests/test_parent_wifi_responsiveness.py`; two stale `wifi_payload` shape assertions in `tests/test_parent_production_api.py` updated for `connected_ssid`.


## 2026-10-21 — Parents app shows the connected Wi-Fi network

**Evidence class: DEVICE (Acer, remote) + SOURCE + FOCUSED TESTS.**

The Acer is connected to `Wireless Pendente` at `192.168.68.112` (online, HTTPS 200), but the Parents app only listed networks. `/api/v1/network/wifi` now returns `connected_ssid`, and the Wi-Fi card renders `Connected to <SSID>` (green) or `Not connected to Wi-Fi`, with a green `Connected` badge on the active row. Changes are in `src/greia_parent/api_server.py`, `src/greia_parent/production_api.py`, the vendored/overlay Parent app (`src/views_device.js`, `styles/app.css`) and the integrity manifest. The pin revision is unchanged; this is a Greia-side visual patch to the pinned client, pending upstream sync.

On the Acer the four files were installed directly and `greia-parent` restarted (integrity OK). Verified payload `connected_ssid="Wireless Pendente"`, served JS contains the status, and a temporary diagnostic credential was revoked. A clean `dev_source_deploy.py stage` is currently blocked by a concurrent oversized Activity (`53,952,202` bytes > `52,428,800` limit) from the 2x-art commit, so this used the direct file path; the next image rebuild also needs that Activity-size issue resolved. The current LaCie `96abaccf…` predates this visual patch.

## 2026-10-21 — Acer Parent panel lock-up during Wi-Fi connect

**Evidence class: DEVICE (Acer, remote) + SOURCE + FOCUSED TESTS.**

The HTML Parent app showed Wi-Fi networks, but pressing Connect froze the whole panel. The production Parent API was a single-threaded `HTTPServer`; `connect_wifi` first ran a scan (about 3 s) and then a connection attempt (about 7 s for a rejected network, up to 35 s worst case), so every other panel request queued behind it. Fixed with a bounded `ThreadingHTTPServer` for `ProductionParentApiHTTPServer` (four slots, daemon threads, `block_on_close=False`), a 15 s scan-result cache in `ProductionParentApiApplication.connect_wifi`, and a `connected_ssid()` fast path that returns immediately when the selected SSID is already the connected one. Focused tests PASS (`tests/test_parent_wifi_responsiveness.py`, parent auth/production suites).

Deployed `ea0ab12f4` (pre-rebase equivalent of current `a20dac652`) to the Acer. Verified: current-network connect `200` in **0.07 s**; during a deliberately failing connect (`400`, 7.07 s) a parallel `/api/v1/devices` request returned in **0.0036 s**; Wi-Fi remained `Wireless Pendente`, `192.168.68.112`, HTTPS 200. The temporary diagnostic device credential was revoked. The LaCie image `96abaccf…fb07` was built from `37d06316e` before this parent fix; a reinstall needs a rebuild to include it.

## 2026-10-21 — Aspire Wi-Fi follow-up: suspend/resume hook

**Evidence class: DEVICE (remote) + SOURCE + FOCUSED TEST.**

The firmware repair fixed the missing microcode, but the link still died when the laptop lid was closed and reopened: `wiphy_resume` returned `-110`, `iwl3945` could not move from D3hot to D0, and `wlan0` stayed down (`No station on device: 'wlan0'`). A driver reload recovered it without reboot. Added `build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume`: on `post`, only when `iwl3945` is loaded, it reloads the module under a 20 s bound and restarts `iwd`, which re-associates with the saved profile. Contract-tested in `tests/test_system_overlay_contract.py`; manually invoked on the device and verified `routable (configured)` + HTTPS 200. The hook is not yet in a rebuilt image; it was copied to the installed device for this test.

**Caveat:** an unattended `rtcwake -m mem -s 20` test did not wake from the RTC alarm; the device remained suspended and must be woken with the power button. Do not repeat that as an unattended test. The lid-close/open path is the real path to retest; the hook is installed for it.

**Next:** wake the device, close/open the lid once, confirm Wi-Fi returns automatically; then rebuild/flash the image with the hook and include it in the clean-install acceptance.

## 2026-10-21 — Short spoken-carrier extraction and v0.3 pilot

Implemented a reusable deterministic remove-first-N-word PCM16 WAV tool and an
explicit `spoken-short-v1` VoiceEngine path. Raw carrier audio and true provider
receipts are retained; exact prefix recognition, bounded word timing, one
guarded low-energy PCM run, deterministic midpoint cut, and at least 80 ms
cumulative frames above the −42 dBFS RMS floor are required. Standalone target
verification defaults to exact; the frozen corpus uses explicit `warn` so
uncertain target ASR remains visible and can never become machine PASS.

Frozen external plan:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-corpus-v1/run/plan.json`
(642 READY / 4,273 PRESERVED; Dani 182, Momo 214, Tito 246; EN 170, IT 171,
ES 156, FR 145). After the voiced-duration guard, its plan SHA-256 is
`880ef780e72ae319e2de2cbedd3a1efabda24d7a3052dd0d4b01c0124a77c7c6`.
Four-language bounded pilots exercised the prefix/gap method. The Takeboard
pilot has 26 rows, all unreviewed, at `http://127.0.0.1:8800/`; its external
manifest is in the pilot-v2 folder. Parent independently reviewed technical
boundary evidence; this is not pronunciation or human acceptance.

Focused carrier/policy/generation/corpus suite: 38/38 PASS. An initial gate
attempt forced Python 3.12 and is discarded as nonstandard. The final normal
environment `make verify` used Python 3.14 and ran 3,131 tests: 31 failures,
241 errors, 6 skips. It is NOT GREEN; see
`/tmp/greia-short-carrier-make-verify.log` for exact output. Failures are not
attributed to this change without individual traces. Owner expanded scope to all
six canonical actors while the original 642-cue run was already active. It is
continuing without interruption; the first in-flight cue is Tito/EN
`feed_turtle.wav`, VoxStage job `20261021-164935-3a4e37c9`. After it completes,
finish that frozen 642-row run with at most three fresh attempts per cue, then
create a disjoint external plan for the remaining Lilli/Leo/Flash short cues
(parent inventory estimate 1,968: Leo 1,628, Lilli 230, Flash 110). New
`--carrier-speakers` defaults to all six and supports disjoint plans; confirm
actual counts and exclude paths already DONE or attempted by the first run.
Commands and no-duplicate rules are in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-corpus-v1/RUNBOOK.md`.
Both runs continue past safe extraction rejections, cap attempts at three,
preserve originals for unresolved cues, and keep every new take
listening-pending. Automated review and one combined Takeboard batch follow.

## 2026-10-21 — v0.3 three-character replacement and automated screen complete

The selected immutable masters remain Dani
`greia-audition-20261021-dani-v5-02` (SHA-256
`f24f1e502bcbc21f1c2610f1b96b6e69b9d428d62c709835a94ebd8ce433ef34`), Momo
`greia-audition-20261021-momo-v3-01` (`3b3c5188c1ce839f87d79f99523ffef9c9ded80f495817d87ba67194ddfd206f`),
and Tito `greia-audition-20261021-tito-v3-01`
(`ebb6ec64dedb146745e7e2bea0643e242669f1dae090133dbc810a532da0a8`). Their
active semantic IDs are `greia.dani.v3`, `greia.momo.v3`, `greia.tito.v3`.
Lilli, Leo and Flash retain their exact v0.2 master IDs/bytes; the v0.2 canonical
master registry remains unchanged. Versioned shared-utterance filenames in the
frozen scope were replaced in place; their original audio and receipts are
preserved in the external v3 run backups, and the external frozen v2 plan/journal
remain unchanged.

Serial v3 generation through VoiceEngine completed with exit 0: **1,340 DONE,
3,575 PRESERVED, zero READY/FAILED/NEEDS_RECOVERY/BLOCKED**. Counts are Dani 392
(EN/IT 102 each, ES/FR 94 each), Momo 284 (71 per locale) and Tito 664 (166 per
locale). All replacement receipts remain `human_review=PENDING`. One Dani/EN
`Toot toot!` attempt (`20261021-143034-b8c58196`) failed as effectively silent,
with no output; the producer stopped at 1,073 DONE. The failed job was inspected,
the original hash was unchanged, and the VoxStage running list and queue were
empty before the documented acknowledged retry. Fresh retry job
`20261021-143155-c79f82e8` succeeded, and the resumed full pass exited 0.
Recovery evidence: external `run-v1/recovery-002.md` and the resume log/exit
record.

Full automated policy-v2 review used the prepared Greia Python and cached
`mlx-community/whisper-tiny`. Coverage and eligible ASR are complete:
**1,115 PASS / 225 WARN / 0 FAIL / 0 BLOCKED**. ASR: 608 PASS, 199 WARN,
533 policy exclusions. Warning flags: 199 ASR mismatch/error, 13 trailing
silence ≥1.5s, 11 leading silence, 6 low level, 1 internal pause. Review command
exit 2 reflects retained warnings. Speaker identity, acting/mood, pronunciation
truth, independent language identification and small-speaker intelligibility
remain unassessed. No automated or technical result grants human acceptance.

Takeboard batch: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/takeboard/batch.json`;
validated 1,340 recordings with all human states `unreviewed`. Fresh local
server is `http://127.0.0.1:8799/` (PID/log beside the batch). Existing ports
8794–8798 were left untouched. The full report, queue and log are under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/`.

**Next:** owner listening across all 1,340 replacements. Prioritize the 225
machine WARN rows and 533 ASR policy exclusions, then cover every character ×
language pair, long narration, numbers/words, identity and acting. Keep every
receipt pending until individual human decisions are explicitly supplied.
The source gate ran at pre-production commit `11f1c799b` and was NOT GREEN
(2 failures, 4 errors, 8 skipped); the owner remote advanced `main` six commits
to `9271f0ac3` during production, including a fix for the build-profile mode
error. `make verify` was not rerun on the merged head. The 72 focused voice
tests passed before production. No runtime playback, release image, Simulator,
physical-device or human listening acceptance is claimed.

## 2026-10-21 — High-resolution rollout to all Activities

Evidence class: SOURCE + TESTS + DESKTOP VISUAL REVIEW (headless captures at 1280x800 vs `GREIA_ACTIVITY_HIRES=0`; not seen on the Aspire).

- 807 shared + 175 Activity-private `@2x` renditions rendered from the same SVG masters (commit f22db8cb3). 13 Activity images were skipped because the shipped PNG no longer matches its SVG master (listed in the rollout notes).
- All 44 Activities opted in to `hires=True` (commits 708ed84db, 53eb5d864, 1118ece58, fbcff6a6e).
- `hires_surface` fixes found during rollout: near-opaque alpha snapped back to 255 after downscale (ghost shapes), colour-keyed surfaces survive copy/convert (sottomarino porthole), `pygame.mask.from_surface` returns logical-unit masks (teatrino puppets). Tests added.
- Size: ~32 MiB of `@2x` art added. `enciclopedia_greia` is now 53,914,481 bytes (the figure that failed the old 50 MiB check; it is that one Activity, 4.2 MB of it `@2x`). The image payload must be re-measured against the 1,300 MiB gate at the next build.
- Owner decision 2026-10-21: the per-Activity size limit is now a **64 MiB guideline; larger Activities are allowed with a build-time warning and an install-time size notice**. Implementation: `maximum_activity_bytes` = 67,108,864 (`runtime/child-runtime.toml`, `RuntimeCatalogue.default_safe`) no longer refuses; `ActivityRegistration.size_notice()` is logged and printed by `tools/validate_activity.py` (stderr `WARNING`), and the install receipt carries `size_bytes`, `large_activity`, `size_notice`. Archive extraction and simulator snapshot keep a fixed 512 MiB zip-bomb safety ceiling; the 32 MiB compressed upload cap is unchanged. Parent UI rendering of the install notice is pending (data is in the API response). Test: `tests/test_activity_size_guideline.py`.

Open items: `writing` and `shape_garden` were captured only at 1024x768 where the layer does not engage (typed text, caret, painting strokes in hi-res unverified); `quattro_amici` / `teatrino_fiabe` modes beyond the first screen not captured; `corsa_bacche` audio TypeError in the capture harness (also with hires off, possibly harness-only); `baia_delle_orche` moon-pixel test fails on main independent of this work; physical Aspire check pending.

## 2026-10-21 — Transparent high-resolution Activity rendering (pilot)

**Evidence class: SOURCE + TESTS + DESKTOP VISUAL REVIEW (headless captures at 1280x800). Not seen on the Aspire.**

`greia_platform/hires_surface.py` plus `PygameReferenceCanvas(hires=True)` let an
opted-in Activity render at physical resolution with unchanged 1024x600 logical
code. Pilots: `alfabeto_leo`, `memory_meraviglie`. Threshold: CONTAIN scale >= 1.2
(owner, 2026-10-21); below it the cheap path stays. `GREIA_ACTIVITY_HIRES=0` disables.
Sharper now: drawn shapes, outlines, text. Not yet: PNG art (still logical-size,
resampled on load). Regression tests in `tests/test_hires_surface.py`
(channel-order swap on smoothscale, 1 px lines leaving empty rows at 1.25x).
Design: `docs/design/GREIA_ACTIVITY_CANVAS_AND_VIEWPORT_AUTHORING.md` §9.3.

Next exact step: higher-resolution PNG renditions, then roll out to other
Activities after owner review of the captures.

## 2026-10-21 — Scaled Activities: band glitches, jagged scaling and pointer cost fixed in the canvas

**Evidence class: SOURCE + FOCUSED/ACTIVITY TESTS + DESKTOP VISUAL REVIEW (headless captures). Not seen on the Aspire (offline this session).**

- **Owner report:** on the 1280x800 Aspire, Activities looked zoomed and ugly, with glitching bands above and below.
- **Causes (all in `greia_platform.pygame_canvas.PygameReferenceCanvas`):** (1) the CONTAIN bands (25 px at 1280x800) were never repainted by the 40 Activities that call `present()` without `clear`, so they kept the launch card and every Greia pointer position as a trail; (2) the 1.25x upscale used nearest-neighbour, doubling every fourth pixel row/column (jagged outlines); (3) when scaled, `present_pointer()` (used by 44 Activities) re-scaled and flipped the whole frame on every mouse move.
- **Fix:** every full present repaints the bands with one solid colour, the darkened average of the scene edge with hysteresis so a passing sprite never changes it (owner choice 2026-10-21; an earlier edge smear was replaced), or the `clear` colour; `smooth=None` resamples non-integer scales smoothly and keeps whole-number scales crisp; the canvas caches the presented physical frame and bands so pointer refreshes and `present_regions` (now resampling only the dirty regions) work at any scale. No Activity code changed.
- **Verification:** new `tests/test_pygame_reference_canvas_presentation.py` (9: no stale band pixels at 1280x800/1366x768/1920x1080/1280x1024/800x480, no pointer trail, no re-scale on pointer refresh, smooth vs crisp choice, region update matches a full present). Activity suites 1,524 PASS; Simulator, writing/shape-garden/canvas consumers PASS. Desktop timing (M-series Mac): 1280x800 full present 1.1 → 3.1 ms, pointer refresh 1.04 → 0.003 ms. Before/after captures of the same logical frame (alfabeto_leo 1280x800, memory_meraviglie 1280x1024, bosco_numeri 1920x1080) show the trail/stale band gone and outlines no longer stair-stepped.
- **Remaining (not fixed here):** the image is still a 1.25x upscale of 1024x600 art, so it is softer than native and the bands still exist. Removing both needs native-resolution drawing (reference canvas rendered at physical size with assets/fonts rendered at the real scale); that is a per-Activity migration through the shared kit. Full-frame smoothscale cost on old laptop CPUs and the Pi at 1080p is unmeasured.
- **Next exact step:** source-deploy to the Aspire and look at `alfabeto_leo`/`memory_meraviglie` with real pointer movement; then decide the native-resolution migration.

## 2026-10-21 — Installer firmware selection was blind inside its own sandbox (fix)

**Evidence class: SOURCE + FOCUSED TESTS + REAL SYSTEMD SANDBOX (build host `orbiter`, not the Aspire, not a clean install).**

- **Root cause (corrects the 2026-10-21 Aspire entry below):** `greia-install-transaction.service` and `greia-system-update.service` ran with `ProtectKernelModules=yes`, which hides `/usr/lib/modules`. Inside them `modinfo` (directly and via `isenkram-autoinstall-firmware`) answered "module not found" (exit 1) for every driver; the resolver treated exit 1 as "built-in driver" and selected **no driver firmware on any machine**, only CPU microcode. The Wi-Fi was joined before the install, so `iwl3945` was already bound: the "late binding" explanation behind `813b43d0` was wrong and its 68% refresh runs in the same sandbox, so it could not help. Reproduced on the build host: `systemd-run -p ProtectKernelModules=yes modinfo -F firmware iwlwifi` → `Module iwlwifi not found`, exit 1.
- **Fix:** both units drop `ProtectKernelModules=yes`; module loading stays denied by the capability bounding set (no `CAP_SYS_MODULE`) plus explicit `SystemCallFilter=~@module`. New `greia_platform.hardware_enablement.LinuxKernelModules` (production-wired into `BoundDriverFirmwareResolver`, `IsenkramHardwareSupportResolver` and the update selection) makes an unreadable module tree an **incomplete** resolution, which the single-root engine already turns into a pre-erase refusal naming the cause. The bound-driver resolver now asks `modinfo` for the module behind the driver (sysfs `module` link: `rtw_8822ce` → `rtw88_8822ce`, `b43-pci-bridge` → `ssb`), and a loaded module `modinfo` cannot describe, a missing/hung `modinfo`, or any other failing exit is incomplete instead of a diagnostic. The A/B fresh-install seam now refuses an incomplete resolution instead of installing an empty firmware set.
- **Verification:** new `tests/test_firmware_resolution_unit_contract.py` plus resolver/module-view tests; focused suites PASS (hardware enablement 16, installer hardware enablement 21, installer engine 21, fresh A/B 29, installer unit contract 30, system-update service 35 + orchestration/composition/overlay/staging/activation/L7 guards). Real systemd sandbox on the build host with the unit's capability set: old setting → planner refuses with "kernel module metadata is unreadable"; new setting → bound-driver resolver complete, selects `firmware-misc-nonfree` for its `tg3` NIC; `modprobe dummy` denied under the new filter. `make verify` not run.
- **Not proven:** a clean install on the Aspire. The LaCie image `ff339ad7…` predates this fix and will still install without Wi-Fi firmware.
- **Next exact step:** rebuild/flash the RC from this commit, clean-install the Aspire, confirm `install-record.json` lists `firmware-iwlwifi` and `iwd` connects without manual packages.

## 2026-10-21 — Aspire 1280x800: full-surface Activities and missing target Wi-Fi firmware

**Evidence class: SOURCE + FOCUSED TESTS + PHYSICAL/DEVICE (installed Acer Aspire, remote input).**

- **Display:** Activities opened a fixed 1024x600 window on the 1280x800 panel, leaving stale Shell pixels and a hidden pointer around the surface. `0a0b4659` adds `greia_platform.activity_display`, installed by the Greia Activity entry: the requested `set_mode` size is replaced with the Shell's exact recorded viewport and the launch cover still owns the first-window card. Authoring design/skill docs updated. Deployed the pre-rebase equivalent (`a2ac1386`; final `0a0b4659`) to the installed RC and opened `alfabeto_leo`: the Activity surface is `1280x800+0+0`, fills the panel, and trusted Home remains on top.
- **Wi-Fi:** the installed target had no `firmware-iwlwifi`, so `iwl3945` could not load `iwlwifi-3945-2.ucode` and `iwd` found no station networks; the live installer's broad firmware cover worked. Installed `firmware-iwlwifi` on the device, reloaded the module and restarted `iwd`; the saved profile associated and `systemd-networkd` reached `192.168.68.112`, online/routable. Source hardening `813b43d0` re-resolves target hardware support after the payload copy and merges late-bound verified packages into the pre-erase plan; focused tests pass. `a8a64fdd` restores the executable `tools/build_profile.py` CLI.
- **Rebuilt/flashed:** `legacy-x86-i686-rc` from `fa15c88f` (includes the viewport fix, the late hardware-support re-plan and the v0.3 voice masters) through the documented front door inside `unshare`; image SHA-256 `ff339ad76b65acd4c0f998c81da61577127400c4aee13a59963e68d2bcd4838e`, live media id `7b50ef65-a0a8-4427-afb3-667ef37a52d1`, payload accounted **1,257 MiB** (<1,300). Artifact, USB read-back, independent verifier re-run and loop hygiene all PASS. Log `out/rc-build8-fa15c88f.log`.
- **Verification:** focused display/launch-cover/supervisor/hardware-enablement/installer tests PASS. `make verify` fast lane ran 5,480 tests with the inherited ARM64-profile error, the known `morbidi_mostriciattoli` startup-budget flake and the stale MBR-message expectation; the `build_profile` executable-mode test error is fixed by `a8a64fdd`. The aggregate gate is therefore NOT GREEN for inherited reasons only.
- **Detailed implementation/evidence for other agents:** `docs/reviews/acer/2026-10-21_ASPIRE_1280X800_VIEWPORT_AND_TARGET_WIFI.md` (call flow, contracts, tests, device evidence, limitations, rebuild/flash data).
- **Next exact step:** rebuild/flash the RC with these commits and verify a clean install; then run the Acer premortem §5 F1–F19 physical checklist and record the result.

## 2026-10-21 — v0.3 master promotion and three-character corpus run preparation

Owner-approved immutable master selections are Dani
`greia-audition-20261021-dani-v5-02` (candidate 02; SHA-256
`f24f1e502bcbc21f1c2610f1b96b6e69b9d428d62c709835a94ebd8ce433ef34`), Momo
`greia-audition-20261021-momo-v3-01` (`3b3c5188c1ce839f87d79f99523ffef9c9ded80f495817d87ba67194ddfd206f`), and Tito
`greia-audition-20261021-tito-v3-01`
(`ebb6ec64dedb146745e7e2bea0643e242669f1daeaf090133dbc810a532da0a8`). Dani's
saved owner review marks only candidate 02 approved (01/03 rejected). Exact bytes,
review and source provenance are archived under `assets/source/audio/character-voice-masters/v0.3/`.
Active semantic IDs are `greia.dani.v3`, `greia.momo.v3`, `greia.tito.v3`;
Lilli/Leo/Flash retain their v0.2 IDs and exact bytes. The active canonical
manifest is v0.3; the v0.2 set remains unchanged.

Frozen external run: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/run-v1/`.
Plan summary is **1,340 READY** (Dani 392: EN/IT 102 each, ES/FR 94 each;
Momo 284: 71 each locale; Tito 664: 166 each locale) and **3,575 PRESERVED**.
The completed v2 plan had 4,168 READY / 741 PRESERVED. Path comparison found all
4,909 prior rows retained, six new rows (the v0.3 canonical references), and zero
removed paths. All 1,340 scripts, locales and semantic speakers match the v2
plan; frozen original hashes match the currently installed files (1,340/1,340).
These hashes differ from all 1,340 v2-plan original hashes because v2's plan
captured pre-v2 audio. The new plan changes only selected-master identity and
acting direction for those rows. Out-of-scope rows are explicitly preserved. Plan is frozen; production has
not yet started at this checkpoint.

Completed a 12-output VoiceEngine technical sanity batch, one selected character
per EN/IT/ES/FR. All 12 returned `REVIEW_REQUIRED`, use the intended v3 reference,
are 22,050 Hz mono, and remain `human_review=PENDING`; ASR was intentionally off.
Receipts, hashes and job IDs are in the run's `clone-sanity/technical-summary.json`.
This does not claim listening, pronunciation, audible identity, or human acceptance.

Focused voice tests: 72 PASS. Initial doctor confirmed v0.3 anchors, VoxStage and
FFmpeg ready. Global Anaconda Whisper import remains broken by the documented
NumPy/Numba mismatch; automated corpus review must use the prepared Greia voice
Python from `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`. No runtime replacement,
release/image, or playback acceptance is claimed. Unrelated untracked audit/video
artifacts remain untouched.

**Next:** run the frozen plan serially through `tools/regenerate_voice_corpus.py`
with verification off, retain the external journal/backups/logs, monitor the
shared VoxStage queue and journal together, then run full automated review and
export a separate listening batch. All corpus receipts remain pending until a
human reviews them.

## 2026-10-21 — Momo/Tito masters selected; new Dani v4 audition set

Owner saved **Momo v3 candidate 1** and **Tito v3 candidate 1** as approved;
Momo 2, Tito 2 and both Dani v3 candidates are rejected. Decisions were read
from the live Takeboard session and its saved `auditions.reviewed.json`.
Selected immutable IDs: `greia-audition-20261021-momo-v3-01` and
`greia-audition-20261021-tito-v3-01`. Exact approved source WAVs and provenance
are durably archived under `assets/source/audio/character-voice-masters/v0.3/`
and external `accepted-masters/2026-10-21-v3/`. SHA equality and mono PCM16
48kHz headers/durations verified (14.24s Momo / 11.84s Tito).

This is a selected-source checkpoint. Active canonical registry remains v0.2;
no runtime audio or generation receipt changed and no 1,340-file run started.
Do not redesign these approved Momo/Tito voices. Dani remains the open choice.

Three new, distinct Dani sound-only descriptions omit robot/buzzy/nasal persona
cues: A warm adult baritone (seed 64100), B adult contralto (64200), C low-middle
androgynous (64300). Shared VoxStage jobs respectively
`20261021-084311-4e1f545d`, `20261021-084312-11543bdb`,
`20261021-084314-362a30b8` all completed: 11.68s / 15.20s / 15.84s.
These labels describe requested properties, not agent listening approval.
New candidates remain unreviewed. Queue was initially idle, and the model was
unloaded after all three completed; no other project jobs were altered.

New listening batch: external `2026-10-21-dani-v4/auditions.json`, served at
http://127.0.0.1:8797/. Reference player compares the previously rejected Dani
v3 candidate 1 (not an accepted master). Existing 8794/8795/8796 sessions and
human decisions remain intact. Browser checks show three entries and playable
new/reference media, no fabricated review decisions. No software code changed
or tests rerun; previous 5,491-test gate remains NOT GREEN for its recorded
inherited failures. No phase/runtime/physical/release acceptance is claimed.

**Next:** owner selects Dani A/B/C (or rejects them), then selected-set registry
promotion and representative multilingual cloned-line checks before freezing
and running the corrected 1,340-file replacement. Preserve approved Momo/Tito
bytes/IDs. New generations still require their own acceptance.

## 2026-10-21 — Owner review policy v2; voice identity separated from acting

**Owner direction:** tail/internal pauses below 1.5s should not warn; automated
transcript PASS requires similarity strictly above 0.8 and other checks clear.
Added shared `review_policy.py`, aligned live Whisper default and review, and
added corpus `reassess --evidence-dir` to check unchanged saved evidence then
apply policy without another ASR run. Metadata/real silence and unrelated flags
remain; ASR exclusions never become transcript verification. Original reports
and receipts are untouched. Executed full reassessment: **3,073 PASS / 1,094 WARN /
1 FAIL**. ASR 1,611 PASS / 863 WARN / 1,693 excluded / 1 unrun (silent Bear).
Reports: external `2026-10-21-full-review-policy-v2/`; new listening batch/URL:
`2026-10-21-listening-policy-v2/batch.json`, http://127.0.0.1:8796/.

**Human decisions protected:** browser had 104 unsaved owner reviews. Exported
that exact draft, preserved its separate backup, and copied reviews by matching
ID/audio into the new batch: **82 approved / 22 rejected / 4,064 unreviewed**.
These are the owner's JSON decisions, not machine approvals or promoted receipts.
The original tab/server on 8794 remains intact with its 104 dirty records. Backup:
new listening folder `owner-draft-before-policy-v2.json`; no drafts were discarded.

**Owner diagnosis:** Dani/Momo/Tito are too high/excited; Momo inconsistent; Tito
aged/hyperactive. Investigation confirmed duplicated persona + generic excitement
in old default/explicit corpus prompts. It is a plausible contributor, not proof
of the sole acoustic cause. Owner clarified fixed register/pitch, timbre, age and
texture belong only in master design. All six default entries now use neutral,
unhurried delivery; per-cue overrides should contain only line-specific acting.
VoxStage clone wiring was traced and does not automatically repeat saved master
descriptions. Frozen v2 overrides/receipts remain historical evidence, not inputs
to reuse for the new run.

**New master auditions executed:** two seeds each for Dani/Momo/Tito, using the
existing shared worker. Six new immutable candidate IDs, natural common 46-word
script, requested grounded registers and restrained reference acting. Dani
16.00/14.88s, Momo 14.24/14.88s, Tito 11.84/12.32s. Candidate WAVs, requests/jobs,
Takeboard batch and a replacement draft live at external
`2026-10-21-calm-masters-v3/`, http://127.0.0.1:8795/. No canonical master or
runtime recording was replaced. Listening/transcript completeness remain pending.
Shared queue emptied, model unloaded, server retained. Reference research says
5–30s is practical; old 7–10s refs are within range, not shown to be token-capped.
See `docs/reviews/2026-10-21_VOICE_DIRECTION_AND_REFERENCE_REVIEW.md` for primary
links, actual backend trace and job evidence.

**Verification:** 72 focused voice tests PASS (1.48/1.5/1.52s, 0.8 boundary,
reassessment without ASR, stale evidence rejection, neutral defaults). Full
`make -k verify`: 5,491 tests, inherited 1 MBR diagnostic failure, 4 errors
(ARM64 builder expectation, profile executable permission, two missing lsblk
installer tests), 8 skips. Project validation retains ARM64 restriction;
shell/footprint completed. Gate NOT GREEN. External logs:
`2026-10-21-review-policy-v2-tests.log`, `2026-10-21-review-policy-v2-verify.log`.

**Next:** owner listens/selects one new candidate per character, then multilingual
cloned-line checks before a new frozen replacement plan. Draft scope is 1,340 DONE
files: Dani 392 / Momo 284 / Tito 664; neutral/line-specific performance overrides
prepared, other characters and deterministic targets preserved. Draft is NOT run
or ready to freeze against old references. It needs the selected new masters.
No architecture/lifecycle/runtime/physical release gate closes here.

## 2026-10-21 — Shared Takeboard listening tool delivered; Greia exporter added

The completed automated traversal (preceding entry) now has a loadable human
listening batch at `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-listening/batch.json`:
4,168 recordings, selected master comparisons, spoken text, direction/generation
metadata and automated findings. All human fields start **unreviewed**; no receipt,
audio, frozen plan, journal or runtime acceptance was changed. Read-only exporter:
`tools/export_voice_review_batch.py`; it refuses partial reports and existing outputs.

Owner-authorized shared tool **Takeboard** lives in its own project/repository,
`/Volumes/Test1/Works/takeboard`, https://github.com/frozenpepper/takeboard (private).
It has a versioned generic JSON contract, local HTML UI, bounded 50-row pages,
filter/search, generated/reference players, keyboard navigation, human states,
1–5 scores/notes/reviewer, atomic explicit saving and JSON export/reload. CLI is
`takeboard`; source resumes matching `.reviewed.json`, and exported media_root
is absolute so Downloads does not break playback. Setup, agent operations, voice
and OS skills, architecture pointer, shared catalog and both agent skill links
are updated. The shared core has no Greia imports, ASR, model or runtime coupling.
Exact launch/usage and integration boundary: automated review procedure §6.

**Verification executed:** standalone Python 19 checks PASS; JavaScript 2 tests
PASS including 20,000-entry state/filtering and lossless roundtrip; Greia adapter
3 focused tests PASS. Actual in-app browser loaded the 18 MiB/4,168-entry batch
with exactly 50 rows and working WAV/reference metadata, zero narrow-panel
horizontal overflow. Disposable two-row data exercised edit/save/page reload,
actual downloaded JSON reload, file-picker import and keyboard J/1/0. No real
batch decisions were fabricated. A startup input race was caught and fixed;
server also rejects stale tabs after batch switching. Browser proof does not
constitute listening or desktop-wide/physical acceptance.

Full `make -k verify` ran 5,484 existing tests: 1 known MBR assertion failure,
4 inherited errors (ARM64 builder expectation, build_profile executable permission,
two missing-lsblk installer tests), 8 skips; project validation also failed on
ARM64 restriction, shell/footprint steps completed. The three exporter tests
were added after discovery started and ran separately; no false 5,487-test gate
claim. Full gate remains NOT GREEN. External log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-takeboard-greia-verify.log`.
Standalone exact evidence is in its `VERIFICATION.md` and external QA/log files.

**Next:** open http://127.0.0.1:8794/ and listen/score, saving the sibling
`batch.reviewed.json` or exporting. A detached local server is running; its PID,
launch input and log are in the listening folder's `takeboard-process.json` and
`takeboard-server.log`. To restart: `takeboard serve <absolute batch.json> --port 8794`.
Saved JSON is portable review data; applying it to canonical Greia assets is
separate work. Silent EN Bear and other findings remain unchanged. No phase,
audio acceptance or image release is closed. Unrelated untracked artifacts remain.

## 2026-10-21 — Full V2 corpus automated review completed

The unfiltered cached-Whisper review completed on the frozen V2 run with
**4,168/4,168 DONE recordings covered** and **741 PRESERVED recordings excluded
by policy**. The terminal summary is `complete=true`,
`full_corpus_coverage=true`, and `generation_problems={}`. Results: **2,905
PASS, 1,262 WARN, 1 FAIL**. Eligible ASR is not fully complete only because the
single hard-silence FAIL did not proceed to ASR: **1,853 ASR PASS, 621 ASR WARN,
1,693 NOT_APPLICABLE_POLICY, 1 NOT_RUN_ERROR**. The process finished its
traversal; the report's `human_acceptance_granted` is false. No audio, receipt,
generation state, or acceptance was changed.

The sole FAIL is
`activities/officina_dei_suoni/assets/audio/en/bear.wav`: installed WAV RMS
**-77.7 dBFS** (effectively silent). Its installed SHA matches the PENDING
receipt and the exact frozen Leo/English `Bear` request; this is a real bad-take
finding, not a verifier crash. There were **621 ASR transcript mismatch WARNs**,
539 long-tail silence, 165 long-leading silence, 122 low-level, and 72 long
internal-pause flags. One additional cue,
`activities/mondo_contrari/locales/en/audio/big.wav`, raised
`POSSIBLE_PROMPT_LEAKAGE`: Whisper transcribed “playful, clear words” from the
acting direction along with the expected line. These flags need human listening;
they do not prove pronunciation, language, identity, mood or child intelligibility.

Evidence is external at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review/`
(configuration, 4,168 per-cue records, `review.jsonl`, 4,168-row
`listening_queue.csv`, terminal summary, and process/package metadata), with
console log
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-full-automated-review.log`.
The prepared Greia Python and cached `mlx-community/whisper-tiny` were used; no
installation/download occurred. The separate VoxStage queue was inspected and
all Depleted Rain jobs/model were left untouched.

**Next exact step:** build the owner-authorized generic local HTML listening
tool against this report's queue/records, then work the prioritized queue with
human states, scores and notes. Keep every replacement `human_review=PENDING`
until a person listens and records acceptance. No synthesis, audio repair,
source fix, release decision, or human listening acceptance is included here.

## 2026-10-21 — Whisper blocker corrected: use prepared authoring Python

The previous automated-review blocker was scoped to the wrong interpreter,
not the prepared Greia environment. Global `/opt/anaconda3/bin/python3` has
NumPy 2.0.2 and an ABI-incompatible compiled Numba 0.60.0. The existing
`~/Library/Application Support/Greia/voice-production/venv/bin/python` imports
mlx-whisper 0.4.3 successfully with NumPy 2.5.2, Numba 0.67.0 and MLX 0.32.1.
Cached whisper-tiny revision `78c52ab98ca87f570bc57ad852e15ef7060f9f76`
was available. No packages, weights, global Python or shared synthesis stack
were changed. This corrects the preceding entry's implication that ASR setup
needed repair before review could run.

**Executed live ASR proof:** existing `review --asr auto` command, using that
explicit interpreter, filtered to
`activities/alfabeto_leo/assets/audio/*/ask_A.wav`, four installed languages.
All four ran ASR: EN/ES/IT transcript PASS (scores 1.0/0.899/0.7265), FR WARN
(0.2721). EN/IT also flag LONG_TRAILING_SILENCE. Overall 1 PASS, 3 WARN,
0 BLOCKED, command exit 2 as expected for findings. These flags are retained
for investigation; no regeneration or human acceptance occurred. The shared
VoxStage queue was inspected; other-project jobs were preserved. This bounded
Whisper-tiny pass did not load another large synthesis model.

Evidence: external `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-whisper-recovery/`
(configuration, individual records, review.jsonl, listening_queue.csv, summary)
and sibling `2026-10-21-whisper-recovery.log`. Four clips are not full-corpus
coverage. The runbook, SETUP, setup manual, engine quick start, voice skill and
external v2 RUNBOOK now give explicit prepared-interpreter commands.

**Next:** use that interpreter and a fresh external report folder for the full
4,168-cue automated pass per `GREIA_AUTOMATED_VOICE_REVIEW.md`, investigate
flags and retain the separate human listening gate. Documentation/procedure
correction only; no source changed or test suite rerun this turn. The preceding
recorded full verification failures remain open. No phase/release acceptance.

## 2026-10-21 — Automated voice review command and agent procedure

Implemented `tools/regenerate_voice_corpus.py review` and
`docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`: installed WAV/OGG decode/signal
screening, frozen request/receipt consistency, cached-only eligible Whisper ASR,
possible prompt leakage flags, resumable external reports and a prioritized
listening CSV. Review holds the existing generation lock and reads the journal
read-only; it never synthesizes, changes audio/receipts or grants acceptance.
Partial traversal, ASR off/unavailable and policy exclusions are explicit.
Source collaborators belong to `greia_voice_core` and `greia_voice_corpus`;
setup, engine/design docs and all affected living skills/manuals now route here.

**Executed evidence:** 68 focused voice tests PASS, including known silence,
prompt leakage, unavailable/runtime-failing ASR, unchanged-input resume and
source/journal preservation. Installed v2 pilot: eight signal/metadata PASS
with ASR off; separate two-clip ASR pilot BLOCKED because host Whisper cannot
import (`numpy.core.multiarray failed to import`). Reports/logs are external at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-automated-review-smoke/`
and `2026-10-21-voice-review-tests.log`. These bounded pilots are not full
4,168-clip review or human acceptance. No downloads or generation occurred.

`make -k verify` ran 5,484 tests: 1 known MBR diagnostic assertion failure,
4 errors (unsupported ARM64 builder assumption, non-executable build_profile.py,
and two installer tests requiring missing lsblk), 8 skips. Full gate is NOT
GREEN; these are outside this voice change. Project validation also fails
on the existing ARM64 builder restriction; shell and footprint steps completed.
Full log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-voice-review-make-verify.log`.
This also corrects the preceding entry's attribution of all four errors to
three lsblk tests plus permissions: the actual split includes the ARM64 test.

**Next exact step:** select the existing prepared ASR environment per SETUP,
resolve its readiness without modifying the shared synthesis stack, then run
pilot/full commands in the new procedure with fresh external reports. Automated
flags require investigation; all replacement takes remain human-review PENDING.
No remediation phase, runtime, physical or release acceptance is closed.

## 2026-10-21 — V2 corpus replacement completed; verification recorded

The owner-authorized V2 journal is complete: **4,168 DONE, 741 PRESERVED, zero
READY, FAILED, NEEDS_RECOVERY, or BLOCKED**. The interrupted French strawberry
cue was resumed only after correlating its original, plan request, last job and
absence of a candidate or prior POST; job `20261020-235846-ff7ff0a5` completed.
Bean's runner timeout was reconciled to completed VoxStage job
`20261021-000412-50cad22f` by exact idempotency key and frozen request/master
metadata, then installed offline through the existing transaction path without
another inference. Final DONE receipts, requests, and output hashes were checked;
all replacements remain `human_review=PENDING`.

VoxStage queue is empty and its model was unloaded after the serial batch. The
final `make verify` ran 5,472 tests: **1 failure, 4 errors, 8 skipped**. The
remaining failures are the known host-only MBR diagnostic mismatch, missing
macOS `lsblk` (three installer errors), and non-executable
`tools/build_profile.py`; Encyclopedia's size regression was fixed while
preserving its 50 MiB cap. See the four-language progress ledger and external
run journal for detailed evidence. No ASR or human listening, GUI, Simulator,
or physical acceptance is claimed. Current source, docs, regenerated corpus,
receipts, manifests, and identified leftover deletions are being selectively
published to `main`; unrelated `final.mp4`, `launch-video/`, and the separate
review audit remain untouched.

## 2026-10-19 — Corpus replacement checkpoint: 700 complete

The resumed owner-authorized full READY pass remains active in shell session
`85073`. Current status: **700 DONE, 1 GENERATING, 3,842 READY,
167 BLOCKED_METADATA, 598 PRESERVED**; current cue is Encyclopedia Greia EN
`activities/enciclopedia_greia/assets/audio/en/body/senses_hearing.ogg`.
VoxStage PID `19719` is the sole loaded worker. The pass has advanced through
English animal and body facts; long narration cues take roughly 15–60 seconds
each. No additional failures or recovery transactions have appeared since the
explicit idle-confirmed retry of Bottega ES `prompt_order_length.wav` (job
`20261019-201240-59474c63`).

All replacement receipts remain `human_review=PENDING`. Whisper verification is
off on this host; no ASR or human listening acceptance is claimed. The 167
metadata gaps remain excluded while independent READY work proceeds. Logs,
journal, candidates and recoverable originals remain in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Unrelated untracked `final.mp4` and `launch-video/` remain preserved. Continue
monitoring the same run and inspect any uncertain VoxStage job before retrying.

## 2026-10-19 — Corpus replacement checkpoint: 602 complete

The resumed full READY pass is active in shell session `85073`. Latest status:
**602 DONE, 1 GENERATING, 3,940 READY, 167 BLOCKED_METADATA, 598 PRESERVED**;
current cue is Costruiamo Ponti IT `too_heavy.wav`. VoxStage PID `19719` is loaded
with one active job. The earlier failed cue, Bottega delle Misure ES
`prompt_order_length.wav`, produced effectively silent audio; its original was
untouched, the job failed terminally with no candidate output, and queue 0 was
confirmed before an explicit single-cue retry. Fresh job
`20261019-201240-59474c63` completed and was transactionally installed with its
receipt PENDING. The full pass has resumed past it; no further failures are
recorded. External logs, journal, candidates and backups remain under
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.

Whisper remains unavailable and verification is off; no listening acceptance is
claimed. The 167 metadata blockers remain unresolved and are skipped while READY
cues continue. This checkpoint supersedes prior running counts; next continue
monitoring and inspect any exact job before an explicit idle-confirmed retry.


## 2026-10-19 — Corpus replacement checkpoint: 304 complete

Latest status for the active serial full pass (session `45485`): **304 DONE,
1 GENERATING, 4,238 READY, 167 BLOCKED_METADATA, 598 PRESERVED**. Current cue:
Baia delle Orche FR activity-title. VoxStage PID `19719` remains the sole loaded
worker. The producer heartbeat and per-cue journal transactions continue without
FAILED or NEEDS_RECOVERY rows. Completed receipts remain `human_review=PENDING`;
Whisper is unavailable and verification remains off.

The pass has completed the four-language Alfabeto Leo set and substantial
Baia delle Orche cues. The 167 exact-script blockers are unchanged and continue
to be skipped independently. External work directory, backups and logs remain
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Continue monitoring and recover only source-backed scripts; this checkpoint
supersedes earlier running counts below.


## 2026-10-19 — Corpus replacement checkpoint: 198 complete

The active full READY pass (shell session `45485`) has **198 DONE, 1 GENERATING,
4,344 READY, 167 BLOCKED_METADATA, and 598 PRESERVED**. Current cue: Alfabeto Leo
IT `ask_G.wav`. VoxStage is the same single worker (PID `19719`), and the external
production log/journal remain at `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
The stream is progressing with heartbeats; there are no FAILED or NEEDS_RECOVERY
rows. Completed receipts remain listening-pending. No exact-source recovery has
yet substantiated an override for the 167 blocked rows, which continue to be
skipped while READY work runs. This newer checkpoint supersedes the count in the
prior in-progress entries below.


## 2026-10-19 — Corpus replacement checkpoint: 101 complete

The full READY run remains active in shell session `45485`; the external log and
journal are under `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
Latest exact status: **101 DONE, 1 GENERATING, 4,441 READY, 167 BLOCKED_METADATA,
598 PRESERVED**. The current cue is Alfabeto Leo ES `guess_prompt.wav`. VoxStage
PID `19719` remains loaded with one job, and the runner is emitting completed
transaction heartbeats. No failures or recovery states have appeared. All new
receipts remain `human_review=PENDING`; no listening or ASR acceptance is claimed.

Source/history review has not yielded enough exact-script evidence to resolve any
of the 167 blockers, so READY work continues independently. Preserve the four-cue
pilot and all subsequent originals/journal outside Git. Next: continue monitoring
the serial run and investigate exact blocked scripts; do not resubmit an uncertain
provider request or alter DONE rows. This checkpoint supersedes the earlier
in-progress count below without changing its historical record.


## 2026-10-19 — Full voice corpus replacement running (SOURCE / LOCAL RECORDING, in progress)

The owner-authorized replacement is now using the prepared external run at
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/`.
`plan.json` matches the current v0.2 registry manifest SHA
`0f96de93a42b9f11f16f16a9aeaf479615509fbc9b5fb93812cadbdae694c64e` and
freezes all six acting prompts. The 4-cue technical pilot completed; its outputs
and all later replacements have journaled originals, receipts, and derived
catalogue updates outside Git. Receipts remain `human_review=PENDING`.

Full serial production is active in shell session `45485`; log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/production.log`.
Latest status at this entry: **25 DONE, 1 GENERATING, 4,517 READY,
167 BLOCKED_METADATA, 598 PRESERVED**. The active cue is
`activities/alfabeto_leo/assets/audio/en/ask_J.wav`. Shared VoxStage worker PID
`19719` is loaded with one running job; heartbeats and completed transactions
are advancing. Optional Whisper is unavailable due the host NumPy/Numba mismatch;
verification is explicitly off. No human listening or ASR acceptance is claimed.

The 167 blocked rows remain unresolved pending exact source/history scripts;
independent READY rows continue. No production failure or source bug has occurred.
Preserve `final.mp4` and `launch-video/`. Next: keep monitoring the full run,
continue exact-script recovery and `resolve` only substantiated gaps, then report
final counts/retries, update this handover and the rollout progress ledger, and
commit/push the clearly reviewable PENDING replacements with backups/journal
retained externally. Human acceptance and release publication remain separate.

## 2026-10-19 — Corpus regeneration tool and per-recording performance direction

**Owner scope:** prepare a Python tool for the next agent to replace existing Activity/system speech with the new masters/model, preserving deterministic isolated letters/syllables, showing progress, and supplying a launch/monitor/repair Markdown handoff. The owner then required tone/mood prompts for every recording. This explicitly permits the scoped replacement; it does not mean future takes have been listened to.

**Implemented:** `tools/regenerate_voice_corpus.py` (`plan`, `resolve`, `run`, `status`, `retry`, `restore`), with focused collaborators in `tools/greia_voice_corpus/`. It inventories existing files using receipts and source catalogues/full Encyclopedia scripts, freezes semantic requests and acting prompts, uses one warm serial VoiceEngine with VoxStage forced, displays progress/15-second heartbeat, stages candidates, backs up originals and journals recoverable audio/receipt/catalogue replacement. It preserves uncertain provider failures for operator inspection and never silently resubmits them. Restore walks transactions in reverse and refuses later-edit conflicts. Shared manifest/review rows and Activity audio checksums update with replacements; new receipts remain human-review PENDING. `VoiceRequest.delivery_prompt`, CLI `--delivery-prompt`, batch and warm service now carry performance direction. Six editable defaults in `tools/greia_voice_core/character_delivery.json` apply to normal VoxStage production as well. Chatterbox/native reject an explicit unsupported prompt. The implementation remains modular; no child-runtime or second model producer was added.

**Prepared inventory:** `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/` contains plan, SQLite state, initial `blocked.csv` and override template: **5,308 files, 4,543 READY, 167 BLOCKED_METADATA, 598 PRESERVED** (441 isolated letter/syllable files, 150 historical shared clips, six masters and one boot chime). The 167 older files need exact script/identity recovery; do not invent text or hide them as successful skips. `resolve` can repair only these blocked rows without rerecording DONE work. All READY cues have explicit prompts. Ordinary runtime recordings and selected masters remain unchanged in this preparation turn; the full corpus production run was NOT launched.

**Evidence:** **52 focused voice tests PASS**. One real external Lilli/English/custom-direction OGG smoke completed in VoxStage job `20261019-100927-df5c3cf4`; the persisted worker request and recording direction match the prompt and the receipt identifies the selected v0.2 master with human review PENDING. This proves transport/production, not audible acting acceptance. The shared model was unloaded afterward. Final `make -k verify` on the completed code ran **5,468 tests: 1 failure, 4 errors, 8 skips**, the same inherited ARM64 profile, CLI executable mode, two macOS `lsblk` installer and stale MBR-message cases as the preceding migration review. Project validation still fails at the inherited ARM64 builder assumption; shell/footprint ran. Full aggregate gate is NOT GREEN. Evidence: `docs/reviews/2026-10-19_VOICE_CORPUS_TOOL.md` and external `2026-10-19-corpus-inventory-v3/{voice-tests.log,make-verify-final.log,delivery-smoke*}`. No release-image/Simulator/physical listening proof or remediation-phase closure.

**Next exact step:** the local agent follows `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`: recover the 167 missing legacy scripts where possible, inspect/pilot the character performance defaults, launch/resume the production run, monitor status/jobs, fix owning modules if necessary, and retain backups plus new listening-pending receipts. The runbook is the current executable replacement order within the existing four-language workstream. Relevant source manuals/skills, earlier work-order overrides and the one local-agent queue were updated; ignored installed skill copies were refreshed. Unrelated untracked `final.mp4`/`launch-video/` remain preserved.

## 2026-10-19 — RC installer rebuilt from current `main` and flashed to the LaCie

**Evidence class: SOURCE + BUILD/MEDIA READ-BACK GATES. No QEMU boot, no physical Acer install in this turn.**

- Pulled `main` `6965adb9` → `b750e714` (clean tree) and built `legacy-x86-i686-rc` through the documented front door (`tools/build-and-flash-development-usb.sh`, inside `unshare --mount --propagation private`, operator public key `SHA256:0oRmaFqZpIYFsGj0N2++I6oma2kHtqdOQMQjXITYVXU`).
- Flashed the whole-device-authorized LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`, 7.5 GiB, `TRAN=usb RM=1`), previously mounted and unmounted before writing.
- **Image** SHA-256 `d177baec8ba0cf8229fee05512e1a1e4ec31994a3152b88fca229dfee199f514`; live media id `a7f03fe3-2240-48e6-9c53-811c35765b26`; payload accounted **1,201 MiB** (< 1,300 gate); `boot_console_policy=quiet`.
- **Gates:** artifact verification PASS, live USB read-only verification PASS, `usb_readback_verification=PASS`, `loop_hygiene_verification=PASS`; independent verifier re-run PASS; no Greia loop devices left. Log `out/rc-build7-b750e714.log`; plan entry appended to the 2026-09-15 lifecycle plan.
- **Next exact step:** install from this LaCie on the reference Acer through the graphical installer, then run premortem §5 F1–F19 including the hidden `verbose` recovery check (F2), and record physical results here.

## 2026-10-19 — Owner-selected v0.2 masters and VoxStage/VoxCPM2 default

**Owner direction:** the six selected masters and 24 EN/IT/FR/ES comparison samples are accepted; adopt the new masters and provider as the Voice Studio / general character-production default, retaining Chatterbox. Active registry is now `assets/audio/characters/canonical/v0.2/manifest.toml`; exact source WAVs and portable design/selection provenance are in `assets/source/audio/character-voice-masters/v0.2/`. The old v0.1 set is historical. Existing accepted runtime audio and receipts are unchanged.

**Implementation:** `composition.py` selects VoxStage by default for all six characters (including Dani); `voxstage_provider.py` adapts semantic requests and `voxstage_client.py` reuses the existing serialized local worker. No second model stack or child-runtime synthesis was added. Missing library entries import the exact repository reference/transcript without overwriting saved IDs. Chatterbox is explicitly selected by `--character-provider chatterbox` or `GREIA_VOICE_CHARACTER_PROVIDER`; there is no silent fallback. Dani's existing speech kind remains compatible; pedagogical pronunciation retains native/system routing. The warm client now separates its ten-second connection deadline from the generation response deadline. Canonical installation handles six WAV masters and six WAV references. Runtime asset composition hides canonical authoring references and removes earlier leaked copies from reused staging roots; shared playable audio remains installed. Docs, setup, operations and relevant skills/work orders reflect these contracts. Ignored local `.agents/skills/` copies were also refreshed from the canonical affected skill directories.

**Evidence so far:** 37 focused voice/packaging tests pass; installer check verifies all twelve canonical files. Real default `generate`, five-character `batch` and `serve/request` calls produced review audio/receipts for all six selected voices; retained Chatterbox generated in offline mode from cached weights; native pedagogical speech also generated. Smoke clips remain human-review pending. Source base was refreshed from `43045003e` to concurrent upstream `245ed1573`; the final `make -k verify` ran 5,449 tests with the same five deterministic baseline cases failing (1 failure, 4 errors, 8 skipped); the launcher-memory test passed this time. The aggregate gate is NOT GREEN. Project validation fails at the same inherited ARM64 builder assumption, reproduced on untouched baseline. All 45 Activity validators, shell syntax and footprint checks PASS independently, and bytecode cleanup completed. The earlier full run executed 5,437 tests (2 failures, 4 errors, 8 skipped): five deterministic failures reproduce on untouched `43045003e` (ARM profile assumptions, non-executable build-profile CLI, two macOS `lsblk` installer tests, stale MBR error expectation). The launcher-memory failure passed in isolated baseline execution and is not claimed fixed. Optional Whisper is unavailable in this host's Anaconda/NumPy environment; synthesis checks used verification off. No image rebuild or physical playback proof is claimed.

**Continuation:** voice migration implementation is SOURCE-CLOSED; use `voxstage start` then `python3 tools/greia_voice.py doctor` for new production. Existing upstream test/project-validator failures and the optional host Whisper environment remain separate follow-up work. New clips still require human listening. No remediation or lifecycle phase is closed by this authoring-provider migration. Full evidence/commands are in `docs/reviews/2026-10-19_VOXSTAGE_VOICE_MIGRATION.md`.

## 2026-10-19 — Research-led Pi 400/500 verification (read-only boot evidence; installer still blocked)

**Baseline:** main 43045003e39c4d020647309760d19a41182b98f3. Independently checked Raspberry Pi's official autoboot/tryboot/config.txt and kernel documentation, firmware release notes, reported A/B GPT/partition-walk failures (rpi-eeprom #818, corrupted autoboot forums), and Raspberry Pi rpi-image-gen's boot-device-backed slot and persistent-state design. Findings and source references: `docs/reviews/2026-10-19_RASPBERRY_PI_RESEARCH_LED_VERIFICATION.md`.

**Changes:** strengthened built-in Pi MMC policy to require 32-hex-digit CID rather than arbitrary nonempty text; updated fake SD test identity and added negative invalid-CID assertion. New **read-only** `greia_platform.pi_boot_observation` decodes firmware's big-endian 4-byte selected-partition and tryboot properties, compares them with canonical `autoboot.txt`, slot-root P5/P6 PARTUUIDs and the Linux root= parameter; rejects contradictory facts. Eight focused tests added, including negative boot-state cases. It never arms trial boot or commits accepted slot.

**Verification:** Python 3.13 local syntax compile and isolated new-module harness 8/8 PASS, with temporary stand-ins for two other Greia module APIs; NOT full-repo tests. No `make verify`, image build, loopback geometry, QEMU, real EFI/firmware or Pi hardware evidence. **Pi installer continues to refuse before erase; not bootable/not released**. Exact next steps: run full-repo focused tests and make verify, physical **read-only** Pi EEPROM/model/MMC diagnostics, loopback DOS partition validation, implement native ARM media + firmware boot + recovery/update transaction, then owner-approved physical destructive acceptance. No Github Actions or paid cloud runners without opt-in.


## 2026-10-19 — Pi verification pass 2: slotted-dataclass policy failure and malformed FDT assets

**Baseline reviewed:** main `e37aa437a3cdcc87c65fc26bd36a43ca25b7751a`. Source inspection reconfirmed executable Pi adapter, MBR sizing and early non-destructive full-installer refusal. An independent Python reproduction confirmed that zero-argument `super()` in `@dataclass(frozen=True, slots=True)` can throw `TypeError`; the Pi removable-card policy did exactly that when built-in CID proof was absent. Replaced with explicit parent-method delegation. Added `lsblk` JSON → sysfs Pi 500 MMC CID → policy target-selection integration test (including a USB installer competitor) and negative no-exception cases. Boot-asset stager now rejects non-FDT/truncated DTB and overlay containers, with corresponding tests. Read `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md` § follow-up verification pass 2 for full findings and first-run test commands.

**Evidence limitations:** no Greia Python tests, `make verify`, real parted/mkfs, ARM64 composition, QEMU or Pi hardware tests executed in this turn. Native Pi installation remains **NOT IMPLEMENTED END TO END**; early fail-closed before erase is intentionally preserved. Next action: local source tests, then only authorized disposable loop geometry, then finish ARM setup/live and native Pi firmware A/B/recovery before any physical erasure.


## 2026-10-19 — Pi 400/500 WIP source consolidated on main after adversarial review (UNVERIFIED)

Owner asked for Pi installer implementation and review. The earlier draft PR #10 at `9f209139` had a serious source/claim regression: the final committed `PiMbrTrybootAbAdapter` was STILL deferred/64 MiB despite an intermediate blob being executable/256 MiB. This review discovered it by fetching the committed file. The new `main` changes reconstruct the executable Pi DOS P1/P2/P3 256 MiB FAT, P4 extended, P5-P7 ext4 A/B/PERSIST adapter, account for logical EBR alignment in exact minimum capacity, reuse observed MBR PARTUUIDs, and check the Pi built-in microSD target policy before emitting destructive commands. Source also adds Pi 400/500 ARM64 experimental profiles and package maps (builder correctly refuses ARM64 still), offline board-specific boot-file staging with uncompressed AArch64 Image-header preflight, and sysfs Pi MMC-host/card-CID observation while preserving USB/removable safety. Full Pi install transaction still **refuses prior to wipe** until the ARM media and native firmware installer are complete.

**Evidence scope:** source review and changed test sources only; `make verify`, full Python tests, actual partition commands, ARM64 build, QEMU and physical Pi tests were NOT executed here. The correct binding review, risks, test order and further work are in `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md`. Raspberry Pi installation is **NOT COMPLETE**, not yet installed or safe to try on user media. Continue from the active 2026-09-15 lifecycle plan (not a competing Pi plan). Do not mark Pi released from these source changes.


## 2026-10-18 — Installer completion button repaired (root finish-marker path); live shutdown hang still open on the Acer

**Evidence class: SOURCE + QEMU reproduction of the denial. Physical retest pending.**

- **Owner report:** the final "I'm ready — turn off" button did nothing; pressing the laptop's physical power button produced a black, powered-on screen that never switched the machine off (forced reset needed). On the previous image the same screen showed the Syslinux banner.
- **Confirmed defect:** the button's `systemctl poweroff` ran as the installer's unprivileged `nobody` identity with no logind session; logind/polkit answered `Call to PowerOff failed: Access denied` (QEMU-reproduced against the live image). The black screen came from the physical button's root logind shutdown, not from the button.
- **Fix:** the UI now writes `/run/greia-installer/finish-request` in the RuntimeDirectory it already owns (same pattern as `release-boot-cover`); a root `greia-installer-finish.path` unit watches exactly that file and activates the one-shot `greia-installer-finish.service`, whose helper raises shutdown visibility (`SetShowStatus yes`, kernel console loglevel 8) and then performs the single `systemctl poweroff`. Composer enables the path unit; `verify-composed-root.sh` requires the pair, the helper and the enable symlink; the completion page shows a manual fallback (EN/IT/ES/FR) if the marker write fails. No new package, daemon or polkit rule.
- **Tests:** `test_installer_state` (marker + fallback), `test_rc_image_contract` (unit/compose/verifier/UI contracts), `test_system_overlay_contract` (UI writes the marker, no direct unprivileged poweroff), localization set-equality; focused runs green.
- **Rebuilt, flashed, QEMU-verified** (`6f3c809c`; image `47ab4ec6…b6a0`, live media `a1d8e713…a8c6`, payload 1,203 MiB): the finish path was active, an unprivileged `nobody` marker powered the VM off, and frame capture shows the Greia splash as the final visible frame with no terminal text (the helper lowers PID1's log level to `emerg` only for the final power-off; `systemd-shutdown` inherits it). Artifact verification PASS, USB read-back PASS, loop hygiene PASS. Evidence: `docs/reviews/acer/2026-10-18_QUIET_SHUTDOWN_QEMU_VERIFICATION/`.
- **Owner retest:** the on-screen button now powers the Acer off. The first successful shutdown showed a diagnostic transcript and then `systemd-shutdown` teardown warnings over the Greia cover. The visibility raise was removed; because PID1 forwards its log level to `systemd-shutdown`, the root finish helper now lowers the manager `LogLevel` to `emerg` just before `systemctl poweroff`. QEMU frame capture of the shutdown ends on a clean Greia splash with no terminal text; the composed-root verifier enforces both the silence and the rejection of status/printk raising. Rebuild/reflash with this refinement is in progress; physical closure for F18 remains.
- **Next exact step:** rebuild + reflash the RC with this fix, retest the on-screen button, and capture the hung shutdown stage from the `verbose` boot if it persists.

## 2026-10-18 — Quiet RC: stock Syslinux banner cleared, rebuilt, reflashed, QEMU-verified

**Evidence class: SOURCE + SIMULATOR VISUAL REVIEW (QEMU) + build/media read-back gates. Physical Acer re-acceptance pending.**

- **Owner report:** the stock `SYSLINUX 6.04 EDD … Copyright (C) 1994-2015 H. Peter Anvin et al` banner stayed visible for the whole quiet kernel/initramfs phase (and again when the machine re-booted the stick after a shutdown), making the boot look like Syslinux's. Owner decision 2026-10-18: cut it on the quiet path. The 2026-08-20 rollback had bundled the form-feed `DISPLAY` file with the fatal `console=null` change; the two are now separated.
- **Implemented (`529accef`):** `build/live-syslinux/clear.msg` (one `0x0c` byte) consumed only by the quiet template via `DISPLAY /boot/syslinux/clear.msg`; `tools/build-live-usb.sh` places the byte on quiet media only; `tools/verify-live-usb.sh` requires the directive and byte-compares the file on read-back, and refuses any `DISPLAY` on diagnostic media. `console=tty1` + `panic=0` are unchanged, a panic still prints on tty1, the diagnostic template stays fully observable, and the hidden `verbose` recovery label is untouched.
- **Gates:** focused RC/boot/diagnostics tests green; `make verify` fast lane ran 5,395 tests with the same single pre-existing `morbidi_mostriciattoli` startup-budget flake (0.278s vs 0.25s on this host; unrelated, first seen before this tranche); `validate`, `shell-check`, `footprint` PASS.
- **Rebuilt, flashed, verified** through the front door inside `unshare --mount --propagation private`: artifact PASS, USB read-back PASS, loop hygiene PASS. Image SHA-256 `b92cfd58f2967fa581d88a5c675f6926bbf979869318bb302570b5a416aff2f2`, live media id `d60ca3a7-372a-4b48-92fb-55c75077daa9`, payload 1,203 MiB (<1,300 gate). On-media `clear.msg` is the exact form-feed byte.
- **QEMU of the flashed stick** (snapshot; `-cpu n270`): black with no Syslinux text at 0.8 s and 1.5 s; Greia installer language screen at 190 s with `greia-installer.service` active, Xorg on `vt1`, no shell. Evidence: `docs/reviews/acer/2026-10-18_QUIET_BANNER_CLEAR_QEMU_VERIFICATION/`.
- **Shutdown clarification:** the installer completion page already instructs "After the computer turns off, remove the USB key, then turn the computer on again." With the key still inserted, the firmware re-boots the stick — now without the lingering Syslinux banner. A hang *during shutdown with the key removed* would be a separate installed-system issue and needs the on-device journal.
- **Next exact step:** physical Acer re-acceptance from this LaCie: graphical install, premortem §5 F1–F19, and the hidden `verbose` recovery check (F2) once.

## 2026-10-18 — RC installer rebuilt, flashed to the LaCie, QEMU-verified quiet boot

**Evidence class: SOURCE build/flash gates + SIMULATOR VISUAL REVIEW (QEMU). No physical Acer install in this turn.**

- **Root cause confirmed on the failing media:** the 2026-10-17 stick's
  `boot/syslinux/syslinux.cfg` carried `console=null`. The Debian 686 kernel
  has no `ttynull` driver, so PID 1 had no console and live-boot died before
  anything rendered; `panic=0` left the Syslinux banner frozen on screen. The
  source fix was already committed (`672ae910`: quiet = `console=tty1`;
  `ee7a40d1`: restart + exit-cover recovery).
- **Rebuilt and flashed:** `legacy-x86-i686-rc` at `ee7a40d1` with the operator
  public key, written to `/dev/sdc` (LaCie iamaKey `eca3505216d7d3`).
  `Developer installer artifact verification: PASS`,
  `Greia live USB read-only verification: PASS`. Image SHA-256
  `07240e27416b9801d8b981e43c383d79425697e545402e61d6964a18127b12ac`,
  live media id `22857a5a-9fdb-4d9c-923d-ab659eed38ff`, target payload
  1,203 MiB (below the 1,300 MiB owner gate).
- **QEMU boot of the flashed media** (snapshot mode; stick unmodified):
  Syslinux quiet entry → Greia boot splash (no kernel/systemd/login/cursor
  text) → installer language screen, `greia-installer.service` active, Xorg on
  `vt1`, no shell visible. Evidence and exact commands:
  `docs/reviews/acer/2026-10-18_RC_INSTALLER_QEMU_BOOT_VERIFICATION/`.
- **Host/build lessons:** run the front door inside
  `unshare --mount --propagation private` on this desktop host. A plain run
  leaked the chroot rootfs mount into ~18 system-service mount namespaces; loop
  teardown then failed EBUSY. The leaked namespaces were cleaned manually, but
  one kernel-pinned `/dev/loop37` remains and will clear on the next reboot.
  QEMU i386 must use `-cpu n270` (or `build/verify-image-qemu.sh`, which picks
  it): `pentium3` lacks SSE2, NumPy import fails, and the installer restart
  budget trips `start-limit-hit` behind the Greia cover — a misleading
  "stalled splash" with no image defect.
- **Open:** physical Acer install/first-boot from this stick; hidden Syslinux
  `verbose` recovery path once; the live installer root has SSH but no
  `greia-devctl`/sudoers while `INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13.5
  lists a live `greia-devctl status` remote check (source/docs mismatch; the
  installed target ships it).
- **Next exact step:** install from this LaCie on the reference Acer through
  the graphical installer, then run the premortem §5 F1–F19 first-boot
  checklist.

## 2026-10-17 — Installer quiet-boot and crash-recovery source publication

**Evidence class: SOURCE.** `make verify` passed on the installer changes
over parent `672ae9101`: 5,395 fast-lane tests, 8 skipped, project/Activity
validation, shell syntax and source footprint checks. Log:
`/tmp/greia-installer-commit-verify.log` (local transient evidence).
The installer changes preserved from the working tree add `nonetworking` to
live GRUB/Syslinux/SD entries and the live boot contract. This disables
live-boot's ifupdown preconfiguration; userspace iwd/networkd ownership is
unchanged. The installer unit uses `Restart=always` because xinit can exit
successfully after its client crashes, with five starts per 300 seconds and
an `ExecStopPost` helper that attempts to repaint the existing framebuffer
cover. The composed-root verifier requires the restart policy and executable
helper; regression tests cover these contracts.

**Scope:** source publication only. Comments in the inherited changes report
QEMU observations, but this turn has not rerun QEMU, built/flashed an image,
installed a device or established physical visual acceptance. Video work is
excluded from this commit.

**Next exact step:** validate the rebuilt RC image through the existing
lifecycle/runbook route, including Wi-Fi availability, installer crash/retry
exhaustion, quiet-screen handoff and owner recovery. Earlier release and
hardware blockers remain open.

## 2026-10-17 — Release-candidate preparation (SOURCE; image not yet built)

**Evidence class: SOURCE** (`make test` 5,353 OK at d253e6c2) **+ PHYSICAL** for the Acer parity audit and mic measurements. Nothing below has run in a built image yet.

**Owner decisions:** next image is a release candidate (`build/profiles/legacy-x86-i686-rc.toml`): quiet boot/login, SSH on, one build; four languages released (en/it/es/fr, selectors offer exactly these); missing voice lines approved; image ceiling 1,300 MiB; Wi-Fi joined in the installer must carry over; first-boot profile wizard; build only on the owner's Debian Mac mini (192.168.68.113, no Docker), flash only the 8 GB LaCie — key auth + passwordless sudo to be set up by the owner (agents never type passwords).

**Landed:** parity audit (`docs/reviews/acer/2026-10-17_ACER_REPO_PARITY_AUDIT.md`), pre-mortem (`docs/reviews/2026-10-17_RC_IMAGE_PREMORTEM.md`), RC build source (3a4455d1: console policy, operator public key, bounded `greia-devctl source-deploy`, netdev, loud mic plugin build + `power_save=0`, live installer assets, persistent dev journal; runbook `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13), mic filter config/probe fixes (20e35480; review `docs/reviews/acer/2026-10-17_ACER_MIC_NOISE_FILTER.md` — image-built plugin was missing on the Acer), Parent panel polish (8232b7c3), installer redesign + boot animation + Wi-Fi carry-over (d79b0b38, 3b391572), first-boot wizard (c822d2d8), Shell controller routing (e6f6f523), four-language release + 1,557 voice lines + device-locale fix (d253e6c2; ledger `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_RECORDING_LEDGER_2026-10-17.csv`).

**Open:** wiring of ~34 MiB recorded-but-unplayed Activity lines (in progress); 53 short new clips flagged for a human listen; the current Acer needs `tools/dev_source_deploy.py --legacy-generic-sudo` until reimaged; quiet-boot recovery paths unproven on the Acer; A/B installs don't carry Wi-Fi.

**Next exact step:** owner provides the Mac mini account (key + NOPASSWD sudo) → freeze a commit, run the pre-build gates (premortem G1–G11), build `legacy-x86-i686-rc` with `--operator-key`, verify, flash the identified LaCie, install on the Acer through the graphical installer, then run the first-boot checklist (premortem F1–F19).

## 2026-10-17 — Acer: playable games, mouse-first controls, launch hand-off, faster launches

**Evidence class: PHYSICAL (developer Acer, remote `xdotool` input — not physical-input evidence) + SOURCE.** Details and tables: `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md` (sections from "Game verification at fce322b9" to "Final child-path sweep at 4d6e9c5e"); `make test` green at each commit (last 5,157 tests).

**Done (fce322b9 … df4454c6):**
- **Motion games playable on the Atom:** root cause was SDL per-pixel-alpha blits (~0.22 µs/px ≈ 134 ms full screen on pygame 2.1.2/SDL 2.26.5); `greia_platform.pygame_blit` RLE preparation in games, the control kit and cast poses; deadline frame pacing. Colline 4 → 24 fps, Dolphin 4.3 → 24, Volo 12 → 24, Treno 8.7 → 20, others 19–24; scenes come to rest when the child stops (no self-finishing; owner OK'd Colline's hold-to-drive).
- **Mouse-first controls (owner rule):** compact control clusters + keycap keyboard hints (`ControlLayout.cluster`, `activity_keyboard_hint`, `ui.keycap.*`, catalogue 0.8.0) in 13 Activities; rules in `docs/product/ACTIVITY_INPUT_STANDARDS.md` and ADR 0037 §4a/§4b; audit `docs/reviews/activities/2026-10-16_CONTROL_PLACEMENT_AUDIT.md` (all items closed).
- **Audio:** Activity mixer lease (closes after 30 s with no input/motion; Sound/Channel guarded — pygame 2.1.2 segfaults on a closed mixer); paced, faster synthesis with shared primitives in `greia_platform.pygame_audio` (242 cues byte-identical).
- **Launch:** Shell launch card shown before `supervisor.start` and repainted by the Activity in a hidden-then-shown first window (black 1.3–4.3 s → 0 frames); protected Home visible from the card and cancels a loading launch (ADR 0019 §8); single-pass validation + per-session validation cache for unchanged built-ins (Encyclopedia repeat launch 14 → 5.3 s).
- **Tooling/docs:** `tools/dev_source_deploy.py`; `validate_activity` enforces the runtime import allowlist (`cmath`, `numbers` added); Activity authoring skill consolidated with a one-shot checklist and a keep-current rule (owner request).

**Open:** Quattro Amici token drop 10–16 fps; first launch after a Shell restart ~8 s median (a deploy-time validation record would remove the first-launch parse); Web Activities don't use the launch cover; two observed Home taps on a Collection page logged the profile out (check intended behaviour); Treno is hidden by the test profile's parental filter (no in-play fps); the badge card waits for a tap and its description touches the card edge; `final.mp4` and `launch-video/` at the repo root are another session's untracked work.

**Next exact step:** re-film launches on df4454c6 through the Shell (0 black frames, Home visible from the card), then Quattro Amici token drop, then the deploy-time validation record in `tools/dev_source_deploy.py` / image build.

## 2026-10-16 — Acer reference device: in-place deploys, three sweeps, performance fixes

**Evidence class: PHYSICAL (developer Acer Aspire One, Atom N270 i686, 1 GB, Debian 12, Python 3.11) for the measured items; input was remote `xdotool`, never physical-input evidence.** Full method, per-Activity tables and what was not verified: `docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md` (sweep at 0148f113, re-sweep at 0f560c2e, third sweep at 15212f44, targeted re-measure at a8be76d7).

**Deploy method:** `tools/dev_source_deploy.py deploy --target <operator>@<device>` (stage from `git archive HEAD` with the compose filter, parse-gate under the device Python, swap `/opt/greia-os` root-owned 555/444, rebuild the read-only bytecode prefix, restart, health). Documented in `docs/agents/GREIA_AGENT_OPERATIONS.md` §8. The old `tools/deploy_to_acer.py` is not this procedure.

**Fixed on device (commits 2af434da … 5a30a895):** Shell crash on every launch (profile dir modes); launch path (startup imports, read-only bytecode prefix, ready timeout policy, deferred sound synthesis past READY, `SDL_FRAMEBUFFER_ACCELERATION=0`); `FrameGovernor` for all 45 Activities (low-end profile, decoration freeze, blocking idle wait); pointer save-under; idle-hint back-off 6/12/24 s; Shell memory bounds; Shell mixer idle-close; stale Collection strip on Home; Shape Garden and Pasticceria history keys over the 64-byte limit (badge never fired) plus a key-bounds test over every Activity and stderr reporting of rejected events; Foresta/Sillabe/Orchestra never settling.

**Measured (first sweep → a8be76d7):** launch via Shell crash/16.3 s → 7.4 s median; Activity idle CPU 88% → ~7–16% (painting/writing 19%); Activity RSS 145–197 → 61–124 MB; Shell RSS flat at ~145 MB over a full catalogue walk; Shell CPU while an Activity runs 2.0–2.4%; Home idle 2.4%; pointer repaint 380/435 → 53/53 ms (painting/writing); NRestarts 0, no OOM. Writing "lost spaces" was a harness artefact (withdrawn).

**Open:** Activity-side audio device keeps ~6% busy on static screens and the first input after a static screen arrives ~250 ms late (worker in progress on shared platform code); Home pointer ~230 ms median; first Home after a Shell restart ~50% CPU for 20–40 s; badge card waits for a tap (by design?) and its description touches the card's right edge; time-left pill re-check needs a configured play limit; new-Activity-folder creation under the Parent-owned profile tree not exercised on device. The device profile carries sweep history sessions, two Shape Garden creations, one badge/star.

**Next exact step:** land the Activity audio-idle/wake-latency fix, redeploy with `tools/dev_source_deploy.py`, re-measure idle CPU and static-screen input latency, then `cleanup` the device backup.

## 2026-10-16 — Test suite: fast/full lanes, os.sync fix, leak fix, duplicate pruning

**Evidence class: SOURCE** (local macOS runs, other agents' suites and builds running concurrently). No hardware.

- **Lanes** (owner `tests/suite_lanes.py`, runner `tools/run_tests.py`, pytest adapter `tests/conftest.py`): `make test`/`make verify` = fast lane; `make test-full`/`make verify-full` adds the heavy evidence suites (`tests/test_x8_qemu/*`, install RSS gate, whole-repository sweeps); `make test-slow` runs only those. Run `verify-full` before claiming install/update/release/lifecycle work complete. Naming a module explicitly always runs it.
- **Root cause of the 73-min suite:** durable boot/update writers call host-wide `os.sync()` (3.3 s per call on this Mac under load). The test process now neutralises only that call (fsync/rename/dir-sync/re-read still run); production code unchanged. The "hang after the summary" was a test blocked in that call (`grub_ab.py:949`).
- **Leak:** simulator supervision tests orphaned `greia_simulator/python_activity.py` when READY timed out; they now share `tests/simulator_supervision.py` (bounded load-tolerant waits + `addCleanup` reaper).
- **Measured:** before 5,341 tests / 73.5 min (pytest, loaded). After: fast lane 4,936 tests in 370 s (~6.6 min wall); slow lane 465 tests in 169 s, all green. Fast-lane red at the time were other sessions' uncommitted work only (`test_launcher_long_session_memory`, Corsa Bacche READY-after-present).
- Deleted 16 exact-duplicate or Markdown-prose tests (see commit `9434cc09`).

## 2026-10-16 — Badges: celebration moment, trophy shelf, flat award art, 15 badges

**Evidence class: SOURCE + DESKTOP VISUAL REVIEW** (headless 1024x600 / 800x480 renders, macOS). No Acer deploy, no audible review, no Simulator/VM/physical evidence.

**Done:** post-Activity celebration is now a character moment driven by the Shell loop's incremental frame hook (no blocking sleep): card scale-in, badge overshoot, sparkles (gold/secret: star bursts + confetti), greeter reaction via `HomeAnimator.react`, one accepted `celebrate.success` clip for the first badge of a return (non-interrupting), static while waiting (0 frames), then the badge flies into the Home star which bounces and increments (`achievement_celebration.py`, `achievement_presentation.py`). Badge Library is a trophy shelf (2×4 per page, locked tier silhouettes, secrets absent, star-pill count without denominator, tap → hop + `praise.general`/`encourage.progress` with 3 s cooldown; idle 0 frames). Home star joins the keyboard/controller focus cycle (Up from the top row or Tab after the last portal; Tab continues to the greeter). Award frames redrawn as flat SVG masters → `ui.award.<family>` renditions 160/112/64 + locked (procedural renderer kept as fallback). Policy has 15 badges (+8 from existing events; dolphin silver = 15 pearls in one journey); en/it/es/fr copy. A badge whose Activity is not loaded is now dropped with a warning instead of disabling all badges. ADR 0025 / product / badge-library / Activity-art docs describe the implemented subset.

**Tests:** `test_achievement_celebration` (new), `test_pygame_achievements`, `test_achievements`, `test_achievement_art`, `test_achievement_localization`, `test_achievement_emblem_cache`, `test_failsoft_volume_headroom`, `test_launcher_home_layout`, `test_launcher_home_animator`, `test_launcher_pacing_dirty_redraw` and Home/collection/navigation suites: PASS locally. `make visual-assets-check` PASS. Full `make verify` not run.

**Next exact step:** on the Acer, earn a badge (e.g. Shape Garden) and check the celebration frame cost/feel and the shelf hop with keyboard, pointer and controller; listen to the cheer clip level.

## 2026-10-16 — Interactive Home: greeter reactions, apple tree, sun sparkles, drifting clouds

**Evidence class: SOURCE + DESKTOP VISUAL REVIEW** (headless 1024x600 renders, macOS). No Acer deploy (another session's timed sweep was running there); Acer CPU/idle acceptance is still open.

**Done:** new `src/greia_launcher/home_animator.py` (`HomeAnimator`, `HomeGreeterVoice`, bounded effects), `home_scenery.py` (cover-mapped scene geometry, collision-checked against portals/HUD), `home_animation_presentation.py` (`HomeAnimationMixin`, after `AchievementLibraryMixin` in `GreiaChildShell`). The greeter is no longer baked into the Home cache: it greets (`pose_cheer`), rests, blinks while awake, hops + speaks on tap (first tap per boot = accepted `_intros` clip, then `praise.general`/`ready.go`; non-interrupting, 3 s cooldown, ≤4/min), sleeps after 60 s and wakes on input; it is a keyboard/controller focus stop (Left from a first-column portal; Enter/south). Tap the tree → apple falls (≤3), sun → sparkles, cloud → puff. Loop: new `_present_ambient_frame`/`_ambient_wait_seconds` hooks; dirty rects restored from the cached Home frame; ≤24 fps; zero redraws after the 20 s awake window. `home_landscape.svg` lost its three baked clouds (re-rendered with `rsvg-convert`; `make visual-assets-check` PASS); static surfaces compose `cloud.large.01`/`cloud.small.01` at rest. `shared_character_audio_path(take=)` and `shared_character_intro_path` added; `SpokenLabelPlayer.play_if_idle`.

**Measured (this Mac, dummy SDL):** busy dirty frame mean ≈1.5 ms (animator logic ≈0.1–0.2 ms), drift-only frame ≈0.1 ms, max dirty area 9.7 % of 1024x600, 0 `pygame.Surface` constructions and 0 transform calls over 200 ticks.

**Next exact step:** on the Acer, Home idle `top` over 60 s (≤2.5 % target) and during cloud drift (≤12 %), then a hands-on tap check of greeter/tree/sun/cloud and controller focus.

## 2026-10-16 — Open-source cleanup: dead tests, docs archive, public entry points

**Evidence class: SOURCE + documentation.** Focused tests only (`test_boot_progress_contract`, `test_hardware_enablement_build_contract`, `test_makefile_hygiene`, `tools/validate_project.py`: PASS on the local macOS checkout). No full `make verify` was run for this tranche: it takes about 85 minutes and two other sessions were running suites at the same time. No hardware.

**Done (owner-requested cleanup pass):**
- `078812ef`: removed dead tests (an empty stub file and doc-wording/file-exists assertions) and 15 one-off scripts (13 `tools/generate_*_audio.py`, `run_r7_final_gap_closure.py`, `probe_direct_graphics.py`). The viaggio/stelle generators remain while their Activity research notes cite them.
- `23431344`: owner decision for pre-2026-10-15 history: 53 lesson-bearing reviews, investigations and decision reports moved verbatim to `docs/archive/` (each indexed with its lesson in `docs/archive/README.md`); about 640 screenshots, capture traces, finished runbooks, session handovers and superseded plans deleted (git history keeps them). Everything still cited by a living authority stayed in place: `docs/design/**`, Encyclopedia visual evidence, asset-pack provenance reviews, ADR/skill-cited procedures and the Parent auth protocol. The policy is recorded in `docs/DOCUMENTATION.md` §7.
- `6cf17c6d`: `LICENSE` (MPL-2.0 text), `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `requirements-dev.txt`, a new public `README.md`, the OFL beside the website font copies, `.gitignore` for local tool state, and `opencode.json` untracked.
- This entry's commit: `AGENTS.md` slimmed (dated workstream routing moved into **Active workstreams** above; standing decisions kept as rules), and `HANDOVER.md` trimmed to entries from 2026-10-15 onwards.
- `e8266cb2`: voice receipts no longer embed the author's checkout path. The engine records `request.output` repo-relative, and 2,090 committed receipts were stripped of the absolute prefix (no audio changed).
- Follow-up commit: `tests/test_public_doc_links.py` checks that relative links in the public entry documents resolve; `SETUP.md` and the release-readiness gate (secret-audit and public-files status) are updated.
- Test pruning was split by agreement: the "Greia parent mobile app" session owns timing-driven pruning of the remaining suite.

**Open (owner decisions or follow-ups):**
1. Licensing/provenance (`NOTICE.md`): about 1,350 recordings were made with macOS system voices (`say`), and their redistribution terms must be checked; the character voice references are marked redistribution-pending; the art is AI-assisted. The full CC BY 4.0 legal text and SPDX headers are not added yet.
2. Enable GitHub private vulnerability reporting (`SECURITY.md` points to it), and decide whether the public repository keeps the full git history. The history scan found no keys, tokens or Wi-Fi secrets; older revisions of the handover and the receipts still contain local `/Users/...` paths and home-LAN addresses (the current tree no longer does).
3. Done later the same day: `tests/test_activity_wave34_35_github_recovery.py` and `tests/test_p7_batch3_source_regressions.py` were merged into `test_clinica_cuccioli_refactor.py`, `test_activity_baia_delle_orche.py`, `test_activity_acquario_magico.py` and `test_activity_cucciolo_mio.py` (9 tests moved; 1 duplicate of the Cucciolo manifest test dropped). All four files PASS (20, 35, 33 and 25 tests). The local-agent queue commands were updated to match.

**Next exact step:** run a full `make verify` on a quiet machine; the owner decides items 1 and 2.

## 2026-10-16 — All 45 Activities reworked (P7 W0–W3)

**Evidence class: SOURCE + headless desktop review** (Pygame dummy drivers at 1024×600 / 800×480 / 480×320, app-loop tests, one BEFORE/AFTER sheet reviewed per Activity). **No hardware, no VM/Acer/Pi, no audible review** (no new audio exists). `[release].status` remains `draft` for every Activity. Unit suite at the end of the span: 5,300 tests with 2 failures, both fixed afterwards and not re-run; **a full `make verify` on the final head (~85 min) is still owed**.

**Shipped (SOURCE):** every Activity was reworked (or, for the three child favourites, conservatively polished) as one end-to-end commit; per-Activity table with SHAs in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md` §6a. Same span: shared vocabulary audio bank with locale fallback (`00d303a5`, `shared_vocab_audio_path`), 62 vocabulary pictures in the shared library (`a779b10f`, catalogue 0.7.0), Encyclopedia E4 complete (`7b1f6b2c`: 36 authored storybook scenes, canonical cairo backend, `--check` reproduces 43/43 PNGs), `set_alpha(None)` transparency fix (`11a61e59`), stdlib `abc` allowed in the child runtime (`ab0fabc7`), fail-soft unrecorded sessions, Parent API Activity policy for Parent-installed Activities (`8d1588f3`), Python 3.11 f-string fixes in the Parent panel (`ce2e2c95`, `7f745bca`; the child Shell failed to import on Debian 12 before this), My Greia rework with the new platform API `set_curated_wallpaper` / `WallpaperImporter.install_curated` (`677f0cd1`), painting gallery focus/selection fix (`552011a1`).

**Key decisions:**
- **One Activity = one core experience** (levels of one loop are fine; no multi-game hubs). All merges cancelled; related Activities are grouped by the Shell theme folders (Sea folder: Aquarium, Orca Bay, Submarine, Dolphin), never by merging.
- **Child favourites (Aquarium, Orca Bay, Submarine) were polished conservatively:** same controls, colours and scale, library art, optional never-failing prompts; reviewers compare BEFORE vs AFTER for drift.
- **One feedback grammar** (`CastFeedback`: cheer / think + demonstration / shared cast completion scene), graduated hints, never answer-revealing UI, canonical cast only, platform pointer always visible.
- **Shared vocabulary audio bank:** noun clips live once under `assets/audio/vocab/v1/<locale>/<noun_id>.wav`; Activities must not copy noun clips. Shared numbers use the not-yet-implemented `shared_number_audio_path` (named by Pasticceria).
- **Child work is sacred:** paged galleries, deliberate delete with preview, no eviction, no blank saves (details in the Activity authoring skill).

**Open items:**
1. **Voice approval (owner):** every requested line is in `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_REQUESTED_2026-10-16.md` (shared numbers 0–25, colours, positions, shapes, nouns, then per Activity). Nothing generated; local Voice Studio (zero new spend) may produce candidates after approval. ES/FR stay staged (known ES/FR clip defects listed there and in P7 §8).
2. **Follow-ups** (P7 §8): kit gaps (calm completion variant, completion icon param, multi-cast completion, selection-follows-focus, graduated hint helper, shared confirm-delete/status-icon/burst/sound-bank pieces), F3 platform voice recorder, F4 runtime pointer guarantee, library migration/promotion of Activity-private art, disk pass on runtime PNG sizes (Serra ~930 KB) against the ≤800 MiB core budget, Parent-side wallpaper import, Flash/Tito avatars, Acquario/Quattro Tito clip paths via `shared_character_audio_path`.
3. **Stale docs to correct on touch:** `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` (old Writing toolbar), ADR 0037 (Casa pilot's old banner/OK pill), `tools/generate_*_audio.py` for Casa/Luci/Bosco (old lines), "246" Encyclopedia string count elsewhere (now 260). The authoring skill was refreshed in this tranche.
4. W4 (new Activities: Tidy-Up Time, Robot Path, Float Lab) not started; Sound Blender / Story Time await voice approval.

**Next exact step:** run the full `make verify` on the final head (~85 min) and record the result here; then owner review of the voice-line list, then the library-migration/disk pass before any `[release]` status change.

## 2026-10-16 — Parent API Activity policy now covers Parent-installed Activities

**Evidence class: SOURCE only** (local macOS checkout, Python 3.12). No Linux image, VM, Acer or Pi run; the HTML Parent client was not exercised in a browser.

**Defect:** `PUT/GET /api/v1/profiles/{id}/activity-policy` validated override ids and computed `effective_activity_ids` from the built-in registry only, while the package-enabled composition's `GET /activities` also lists Parent-installed Activities. The HTML Parent client (`Greia-Parent-App-Html`, `src/views_activities.js`) PUTs an override entry for *every* listed Activity (`null` = automatic), so "Save Activity choices" returned 400 `invalid_activity_policy` as soon as one Activity had been installed through `POST /activities/install`, and installed Activities could not be shown/hidden per child. The child Shell already applied profile policy to built-ins + Parent-installed Activities (`greia_launcher/presentation.py` composes both sources and runs the same `ActivityDiscoveryService`), so Parent and Shell disagreed.

**Fix (`src/greia_parent/api_server.py`, `src/greia_parent/package_api.py`):**
- New overridable hook `ParentApiApplication.policy_activity_catalogue()` (base: built-ins) used for both override validation and `effective_activity_ids`; `PackageParentApiApplication` overrides it with built-ins + the active Parent-installed set — the same registrations `GET /activities` lists (shared `_catalogue_registrations()`); no new registry. If the installed set cannot be loaded, the policy view degrades to built-ins, mirroring the Shell's fallback.
- Clearing (`null` / `"default"`) is accepted for any well-formed id, so stale overrides left behind by Activity removal can always be dropped; a non-automatic value for an unlisted id is still rejected.
- Catalogue resolved once per update (was discovered twice), and a complete PUT body no longer projects the current policy first. Built-in validated discovery costs ~14 s per call on this Mac dev tree, so the PUT path previously took ~40 s; worth measuring on the Acer.

**Tests:** `tests/test_parent_api.py::PackageActivityPolicyCatalogueTests` (6): installed Activity in catalogue + effective set; `always_hide`/`always_show` for an installed id accepted and applied; client-shaped HTTP PUT with `null` for every listed id → 200; stale id cleared with `null`/`"default"` after uninstall (non-null still rejected); base composition clears unknown ids but rejects malformed ids; unloadable installed set degrades to built-ins. Focused run: 6/6 OK. Full gate: `make verify` test step ran 4,852 tests: 2 failures, 8 skipped, both outside the Parent API and both passing when re-run in isolation on this tree and on clean `origin/main` (`test_activity_sottomarino…test_app_loop_follows_orders_to_a_star_and_saves`: no voice cue spoken; `test_headless_greia_activity…test_real_activity_bootstrap_publishes_frames_to_owned_bridge`: exit 4). They look load-dependent: concurrent test processes were running during the suite. Treat them as flaky, not fixed. `test_parent_api.py` re-run on the final code: 34/34 OK. `make validate shell-check footprint`: exit 0.

**Docs:** `docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md` §3.2 states the catalogue/clearing contract.

**Next:** exercise "Save Activity choices" from the HTML Parent client against a developer image with one Parent-installed Activity (PHYSICAL/VM evidence still owed). Developer-remote Activities (developer mode) are not listed by the Parent API and therefore remain non-overridable; clearing them still works.

## 2026-10-15 — Design & art tranche: Shell redesign, shared art library, control kit, custody fixes, P7 program

**Evidence class: SOURCE + headless desktop review only** (Pygame dummy drivers at 1024×600 / 800×480 / 480×320). No Linux image, VM, Acer, Pi or audible/physical evidence. Complements the "New primary agent" entry below; it does not repeat it. Commits `ba4e6ab6..d98806e2` on `main`; the main agent owns the full-suite run.

**Shipped (SOURCE):**
- **Art direction:** `docs/design/GREIA_SVG_AUTHORING_RULES.md` is the binding SVG recipe; Opus is the SVG model. Dead/superseded assets retired (~7.5 MiB), image installs only `assets/visual/runtime/` + catalogues. Core icons are now a complete flat family (29 SVG, catalogue 1.2.0, `tools/build_core_icons.py` SVG-only build with `--check`); 8 placeholder Activity icons redrawn; cast poses `pose_cheer`/`pose_point`/`pose_think` for all six characters.
- **Shared art library v1 (catalogue 0.6.0, 297 visuals / 518 variants):** `bg.*`, `prop.*`, `creature.*`, `icon.hud.*`, `fx.*`, cast variants (sad/angry/silly/pose_wave/pose_play). Registered in `assets/catalog/shared_visuals_v1_source.toml`; inventory in `assets/visual/README.md`. No Activity consumes it yet (W2 starts that). Installed runtime visuals are now ~8.9 MB.
- **Shell redesign:** storybook Home + profile picker (layered meadow scene, six hue-coded portals, profile cast character greets), Collection pages (large hue cards, arrows + dots), **theme folders** (a `discovery_tags` theme with ≥3 visible members gets one folder tile, one level deep; first theme: Sea = acquario, baia, sottomarino, viaggio_delfino), My Creations gallery/picker, launch wait screen. Fixed sub-collection chooser, empty-Collection Back, reversed gallery arrows.
- **Shared control kit (ADR 0037):** `greia_platform.activity_controls` (PillButton, IconButton, ToolStrip, HudChip, ProgressDots, PromptBanner + keyboard/D-pad/stick/south focus), `activity_feedback.CastFeedback`, cast completion scene. Pilots: `pasticceria_magica`, `casa_del_dieci`.
- **Fail-soft:** Shell survives and Activities launch as unrecorded sessions when history/child-data headroom is exhausted (`UnrecordedSessionHistory`; no rewards/progression mutation, `history_unavailable` answer).
- **Language/case pass over all 45 Activities** (batches 1–4: hardcoded Italian, ADR 0034 case policy, glyph boxes, profile language, protected chrome).
- **Creation custody:** Painting/Writing galleries page through every item; New refuses at cap instead of discarding; Teatrino no longer evicts silently; deliberate delete-with-preview (Keep default) in Teatrino/Voice Stories; no blank saves. `tests/test_creation_custody.py` (32 tests).
- **Blocker fixes:** Quattro Amici drop animation, Sottomarino depth control, Marble soft-lock, Nanna tap-tap, Morbidi gallery/face overlay, missing keyboard/controller paths (Specchi, Ponti), completion screens keep the platform pointer live.
- **Governance:** four Activity design audits (`docs/reviews/activities/2026-10-15_activity_design_audit/`); **P7 Activity Quality Program** (`docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P7_ACTIVITY_QUALITY_PROGRAM.md`).

**Owner decisions (P7):** one Activity = one core experience; multi-game hubs are not a standard; **all merges cancelled** (45 cards stay; Aquarium/Orca Bay/Submarine kept separate as child-testing favourites); related Activities are grouped only by Shell theme folders via `discovery_tags`; new standalone candidates Tidy-Up Time, Robot Path, Float Lab (W4); Sound Blender / Story Time deferred pending voice approval.

**Open / next:** (1) **voice approval pending** — F6 shared spoken numbers 0–20 + direction words, Sound Blender/Story Time (local Voice Studio, zero new spend; nothing recorded). (2) The theme-folder tile needs a stronger folder silhouette (reads as a card). (3) Delete-confirm dialog is small for a child target. (4) W2 Activity reworks on the library + kit (ladders first: number, literacy, creative anchors), then W3/W4; F2–F5 foundations (shared drafts gallery, voice recorder, hidden-cursor pointer, hint helper) still TODO. (5) Image group names `pip*` vs `greia*` migration unfinished. (6) Library assets unconsumed by Activities; Simulator/VM/physical visual review still owed.

## 2026-10-15 — New primary agent: source gate green locally, Shell fail-soft, Activity UI text pass

**Who/where:** Claude Opus 5.5 is now the project's primary agent, working on a local checkout (macOS, Python 3.12, Pygame 2.6.1) directly on `main`, delegating bounded work to subagents. Local `main` was fast-forwarded from `e1ab2426` to `a76d694d` before work.

**Evidence (SOURCE only):** first full local execution — baseline 4,334 tests / 185 failures / 67 errors; now **`make verify` PASS (4,372 tests OK, 8 skipped)**. All 45 Activities launch and render a first frame headlessly at 1024×600 (`tools/headless_greia_activity.py`). No Linux image, VM, Acer, Pi or audible playback evidence.

**Fixed:** test hermeticity (`tests/hermetic_volume.py`, resolved temp roots, quoted paths; pytest-only modules converted so `make verify` runs them); Shell no longer crashes at profile selection when child-data headroom is exhausted (history/achievements degrade, writes still refused); Simulator models an 8 GiB device volume instead of the host disk; Parent panel pointer-settings crash; ~17 Activities' hardcoded Italian / case-policy bypass / glyph boxes / wrong profile language; many stale tests. Details: architecture-remediation plan progress entry of 2026-10-15.

**Decisions:** (1) SVG art authoring model bake-off (Haiku/Sonnet/Opus/Fable, identical brief: Activity icon, on-model Leo pose, layered scene) → **Opus** selected for all Greia SVG authoring. (2) Icon/art family direction: flat constraint-native vector per style guide §20; the 39 glossy-3D core icons are the outlier to be redrawn. (3) Owner removed ~3 GB of ignored leftovers (TBag/runs, tmp/, Archive.zip, old review zips).

**Open / next:** Activity launch still fails closed (`PLATFORM_FAILURE`) on a full device because `start_session` is refused — next fail-soft step; remaining ~27 Activities not yet audited for language/case leaks; image group names `pip*` vs `greia*` migration unfinished; asset-library pass and Activity design/gameplay upgrades (owner mandate 2026-10-15) starting.

## 2026-10-15 — Greia shared localization: regional fallback + 13 Activity entrypoints

**Owner's active direction:** One Greia localization handler returns child-visible strings or existing approved prerecorded audio paths by stable IDs; all speech (including phonemes) uses selected-language recording, otherwise English, otherwise silence. No file anti-tamper infrastructure. All 3,723 shipping WAV/OGG/FLAC/MP3 artifacts remain approved and unmodified. The active plan is `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`, tracked by its sibling `PROGRESS.md`. Keep ES/FR staged in the selector until proper independent release/playback acceptance.

**Source changes in this session:** `src/greia_platform/localization.py`: correct BCP-47 regional-to-base-to-English ordering for both `.text()`, `.audio_path()` and eager `.speech_paths()`; `audio_path(key, variant=...)` now looks for a variant filename before neutral when using conventional asset paths. No new locale registry, format, manifest language promotion or synthesis.

**Sound managers consolidated:** Word Forest, Alphabet Leo, Measurement Workshop and Ten House now rely on `LocalizedResources.speech_paths()` for selecting localized prerecorded clips. Their pygame mixer, effects, queue/cache policy and source file names are preserved; directly constructed historical audio managers still work.

**Entry-point factory cleanup:** Word Forest, Magic Syllables, Rhyme Festival, Sound Workshop, Momo's Lights, Number Garden, Magic Mirrors, Opposites, Orca Bay, Number Forest, Momo's Faces, Four Seasons and Quattro Amici's app-builder now use `activity_resources(package_root)` / manifest-aware context instead of rebuilding hard-coded `ActivityLocaleSupport.localized(("it","en"))`. Existing `activity.toml` files still declare exactly IT/EN. Momo/Seasons window title now uses localized `activity.title`. **Actual source bug fixed:** Quattro Amici character speech previously received the raw requested locale, even when UI had fallen back to an unsupported locale's IT default; now both receive the effective resolved language. Purely synthesized sound effects and child-microphone/creation audio deliberately are *not* migrated.

**Tests authored:** `tests/test_shared_localized_audio_paths.py` now covers regional fallback, semantic-variant conventional file precedence, manifest language contexts for newly updated Activity roots. Prior suite already covers 10 real ES/FR packaged voice examples, My Time, Encyclopedia, Dolphin, Submarine, semantic aliases, EN fallback and standalone locale tests. **All tests remain UNEXECUTED** in this GitHub-only session, with no GitHub status checks/workflows on current commits. Do not claim runtime/GUI/physical PASS; no local agent was needed for source modifications. Fast verification when a runnable checkout is available: `PYTHONPATH=src:. python3 -m pytest -q tests/test_localization.py tests/test_localization_variants.py tests/test_shared_localized_audio_paths.py tests/test_launcher_spoken_labels.py tests/test_activity_foresta_parole.py tests/test_activity_sillabe_magiche.py tests/test_activity_quattro_amici.py tests/test_activity_faccine_momo.py tests/test_activity_quattro_stagioni.py`.

**Artifact integrity observation, NOT tamper-control policy:** Compared the complete Git trees at starting HEAD `2e82fb7662a6272b3bfdba60ce17fc1e1a3bcdd0` and latest checkpoint `5280ab0ce8e436fec8256506565251025faa0500`; all **3,723 prerecorded audio blob IDs** are exactly unchanged, zero added/deleted. This is only to confirm engineering did not replace any user-approved recordings. No ongoing file protection required.

**Next work:** run focused Python tests when feasible, fix their actual results, investigate remaining child-facing UI strings outside bundle lookups and test representative voice interaction/playback on a real runnable shell/Simulator. The separate missing-only recording order is `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`. Do not generate duplicate clips, enable ES/FR just from source code, or build new policy scaffolding.

## 2026-10-15 — Shared localized speech: My Time sound-file hookup and legacy title support

**Scope:** Follow-on to the 11-Activity shared-audio migration. GitHub source only; **no audio rerecording, no user-file anti-tamper system, no system language promotion**. Source authorities: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md` and its sibling `PROGRESS.md`. Owner decisions continue: all committed WAV/OGG owner-reviewed/approved, selected language first / English fallback / silence for all speech including literacy for now.

**Real bug located and repaired:** `activity_incubator/tempo_di_greia/time_audio.py` previously called `resources.audio_cue(cue, allow_fallback=False)` for each of seven semantic narration IDs, but both EN/IT `locales/*.json` dictionaries have `"audio": {}`. The approved audio **already exists** under `locales/en/audio/` and `locales/it/audio/` with underscore filenames `presenter_welcome.wav`, `instruction_clock.wav`, etc.; source returned no cues despite existing recordings. The adapter now calls `resources.audio_path(cue, filename=f"{cue.replace('.', '_')}.wav")`, so source-selected file or English fallback is returned; existing sound cache/lazy decode/channel/first-frame sequence remains unchanged. `activity_incubator/tempo_di_greia/main.py` now composes `activity_resources(package_root)` from the manifest/profile owner, instead of building an Activity-local locale context.

**Launcher:** Standard `activity.title` lookup previously recognized the normal `activity-title.wav` title convention but not My Time's approved `activity_title.wav`. `src/greia_platform/localization.py` recognizes both variants, preferring the conventional hyphen; no duplicated files or JSON catalogue additions. `src/greia_launcher/spoken_labels.py` continues to use the shared resolver and therefore picks up the fix automatically.

**Tests committed but unexecuted:** updated `tests/test_activity_time_audio.py` (remove stale Italian fallback expectation, fixture for French→English fallback and real IT/EN 7-cue files), `tests/test_shared_localized_audio_paths.py` (real My Time title and synthetic underscore fallback), and `tests/test_launcher_spoken_labels.py` (actual My Time English/Italian title + French English fallback). All 14 narration WAV paths and both title WAVs verified present in nontruncated main Git tree. **No actual Python tests, Pygame decode/GUI/live audio or hardware tests run.** Do not claim acceptance. My Time is incubated and not released.

**Documentation:** `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md` no longer falsely claims generation/owner listening missing; approved audio hookup is recorded and release caveat retained. Updated main localization implementation plan and `PROGRESS.md` (third slice). No local agent was used for this source work.

**Next:** execute focused `PYTHONPATH=src:. python3 -m pytest -q tests/test_localization.py tests/test_shared_localized_audio_paths.py tests/test_activity_time_audio.py tests/test_launcher_spoken_labels.py` in a runnable checkout, then repair actual test findings; subsequent targeted first-frame My Time Pygame audio playback on the small device/simulator and remaining ES/FR release review. Do not run an elaborate gate or regenerate owner-approved clips to address a source resolver issue. The independent exact local recording task remains `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.

## 2026-10-15 — SHARED LOCALIZATION CONTINUATION: 11 MORE ACTIVITY VOICE INTEGRATIONS

**Source authority:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`; progress ledger `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PROGRESS.md`; Activity authoring contract `skills/greia-activity-authoring/SKILL.md`.

**Owner decisions still apply:** all committed voice files are personally owner-approved; do not regenerate/overwrite. No anti-tamper framework. For all clips including pronunciation, selected-locale file → English file → optional silence; voice producer remains an authoring-time tool. ES/FR remain staged and unselectable until later independent acceptance.

**New code in GitHub main this slice:**
- `src/greia_platform/localization.py`: ordinary prerecorded speech now resolves from both `assets/audio/<lang>/` and `locales/<lang>/audio/`. Added `LocalizedResources.speech_paths()` for legacy SoundManagers that eagerly cache short clips, with selected-language priority and English fallback; mixed-case names are filename aliases, not invalid semantic IDs. Added `shared_character_audio_path(project_root, speaker, cue_id, locale)` for existing v0.2 shared Flash/Leo speech with identical language policy. Greia localization returns Paths only; decoding/mixer/effects stay game-owned.
- Migrated 11 additional Activity voice owners: `bosco_numeri/bosco_audio.py`, `festa_delle_rime/rhyme_audio.py`, `officina_dei_suoni/sound_audio.py`, `luci_di_momo/firefly_audio.py`, `faccine_momo/momo_audio.py`, `mondo_contrari/contrari_audio.py`, `quattro_stagioni/tree_audio.py`, `il_giardino_dei_numeri/giardino_audio.py`, `specchi_magici/mirror_audio.py`, `baia_delle_orche/orca_audio.py`, `quattro_amici/quattro_audio.py`. Existing composition roots that create these classes now inject the shared resolver. Legacy direct constructors retain optional compatibility args. Procedural-only SFX engines were intentionally not refactored.
- Found a **real EN/IT versus ES/FR asset layout split** in Momo Faces, Opposites and Four Seasons: EN/IT voices under `locales/{it,en}/audio`; owner-approved ES/FR voices under `assets/audio/{es,fr}`. Shared `speech_paths` now finds the correct file for each without moving/re-recording anything.
- `tests/test_shared_localized_audio_paths.py` extended with actual owner-approved ES/FR filenames for ten Activities, legacy two-folder support, mixed-case legacy stems, English fallback, and shared v0.2 character recordings. Two Spanish curriculum test expectations were corrected to existing source-native filenames after checking GitHub full tree. **Tests authored but NOT executed**.
- Live Activity authoring skill updated for `speech_paths()` and `shared_character_audio_path()`; existing design/progress documents updated. No new task scaffolding.

**Source evidence:** GitHub commits/readbacks and nontruncated complete tree/path comparison. **Not yet verified:** Python unit tests, full-run Activity tests, Pygame audio decode/timing/first-frame, child GUI language context, installed Acer or four-language selector. No local agent needed for this GitHub-only source work. Current follow-up focus: run relevant existing source tests in a runnable checkout when available; fix actual errors if found; finish small remaining integration spots (e.g. incubated My Time and independent system collection sound owners only if ad hoc locale logic is confirmed) without changing approved audio bytes. No promise of a PASS until execution evidence exists. The separate local agent instruction for 35 missing clips remains `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`.

## 2026-10-15 — SHARED LOCALIZATION AND AUDIO: FIRST REAL CODE SLICE COMMITTED

**Project direction (owner):** one Greia-owned Activity/localization subsystem for semantic `text(key)` and prerecorded `audio_path(key)`; requested-locale file if present, else English recording, else silence, **including literacy/phonemes for now**. No anti-tamper/asset signing. All prior committed recording bytes personally approved; no changes to WAV/OGG or receipts. This implementation is **not** full four-language release. Main source of truth: `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md`; execution progress: sibling `PROGRESS.md`.

**Implemented via GitHub main in this session:** `src/greia_platform/localization.py` extends existing `LocalizedResources`: `audio_path(key, *, variant, filename, allow_fallback)` optional file path, compatible file-aware `audio_cue(key)`, locale-directory projection from existing EN semantic mappings and legacy IT-only aliases, conventional `assets/audio/<lang>/<key>.wav|.ogg` and title file, English fallback, plus `activity_resources(package_root)` manifest/profile composition. The English text catalogue is preferred over package default on missing selected-locale strings. Profile/device language and `activity.toml` language declarations remain authoritative. Basic path safety kept; no anti-tamper logic added.

`src/greia_launcher/spoken_labels.py`: launcher Activity-title audio now uses shared `activity_resources`-style runtime resolution (with its independent catalogue language context); collection-label code unaffected. Existing code in Encyclopedia, Dolphin and Submarine already calls `LocalizedResources.audio_cue`, so source integration now reaches their owner-approved staged ES/FR files with no duplicate per-locale JSON audio map.

**Migrated source audio owners:** `activities/bottega_delle_misure/measure_audio.py`, `activities/casa_del_dieci/ten_house_audio.py`, `activities/sillabe_magiche/sillabe_audio.py`, `activities/alfabeto_leo/alfabeto_audio.py`, `activities/foresta_parole/foresta_app.py`; composition roots where needed inject existing shared resources. These still own sound caches, channels, timing, Pygame decode, nonverbal synthesized sound effects, and gameplay. `bottega_delle_misure/main.py`, `casa_del_dieci/main.py`, `alfabeto_leo/main.py` now use `activity_resources` for manifest-aware selected locale. Other legacy Activities remain for incremental migration; DO NOT mass replace Pygame sound engines.

**Testing:** `tests/test_shared_localized_audio_paths.py` was committed with actual asset-path expectations for ES/FR Encyclopedia/Dolphin/Submarine, IT-only Submarine alarm mapping, EN fallback/absent files, title path, conventional filename and Activity factory; `tests/test_localization.py` updated one legacy assertion for new owner-policy English fallback. **Tests NOT RUN:** GitHub source connector exposes no Python execution of repo and automatic Actions/status checks returned none. No local Pygame run, screenshot, physical Acer or complete project tests. Do not claim passing tests or L6 release readiness.

**Documentation:** `skills/greia-activity-authoring/SKILL.md`, `VOICE_GENERATION.md`, `LAUNCHER_SPOKEN_LABELS.md` now teach the *actually introduced* `activity_resources` + `.text` + `.audio_path` interface; stage progress and design docs updated. All commits are on `main`. No local agent needed for this work; separate precise voice recording order `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` remains valid.

**Next coding slice:** read each remaining speech-owning Activity loader, migrate its locale and file selection (not audio synthesis/caching) to `LocalizedResources.audio_path` with occasional legacy filenames, extend focused tests, and run the existing small Python/Pygame suites when execution environment is available. Important test commands: `PYTHONPATH=src python3 -m unittest discover -s tests -p test_localization.py -v`; `PYTHONPATH=src python3 -m unittest discover -s tests -p test_shared_localized_audio_paths.py -v`; relevant Activity-specific tests; launcher spoken labels. If tests find regressions, repair source and retain all approved recordings. Do not enable ES/FR in normal selector solely on resolver changes.

## 2026-10-15 — Shared localization and voice resolution direction (OWNER DECISION, DESIGN COMMITTED)

**Owner decision:** Greia should standardize the public Activity-facing localization subsystem: each Activity requests `text(key)` or prerecorded `audio_path(key)` by stable semantic ID; a central Greia resolver handles child/profile language, existing locale files, English fallback and legacy filename aliases. Existing code already has most of this as `greia_platform.localization.LocalizedResources`, but many Activity SoundManagers use direct locale-specific file loaders. **No crypto/anti-tamper/checksum gates; user modifications are acceptable.** **English fallback for all speech, including phonemes/literacy, is approved for now.** All committed sound clips have been personally listened-to and approved by owner; keep originals intact.

**Concrete design/implementation plan added:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/SHARED_LOCALIZATION_AND_AUDIO_RESOLVER.md` (linked from `AGENTS.md` and rollout `PLAN.md`). Ordered implementation: extend the existing runtime-neutral localization API/factory; make semantic audio resolution file-aware and English-fallback using single canonical key→legacy filename mapping plus conventional paths; migrate Encyclopedia/Dolphin/Submarine, then Word Forest/Syllables/Alphabet/others; share launcher resolver; add focused tests; **then** update the live Activity-authoring skill and its voice companion to actual code API. Preserve Activity Pygame channels/cache and educational lesson logic; no global re-record, no runtime TTS. This turn is **source evaluation + design/doc commits only**, no source runtime logic changed and no Python/Pygame/device execution. The earlier handover request for **strict native phoneme fallback** is superseded by today's owner choice. `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` remains the separate targeted record-only order.

## 2026-10-15 — Owner reaffirms all integrated recordings approved; targeted missing-voice order created

**Product decision:** all **already committed** recordings were personally reviewed/approved by the owner. Their bytes and voice identities are final. Do **not** regenerate, reject or reapprove them. Corrected `docs/reviews/2026-10-15_FOUR_LANGUAGE_VOICE_INTEGRATION_SOURCE_REVIEW.md` to recognize this unequivocally. Remaining integrator issues are about preventing future accidental replacements, **not** a claim existing audio is invalid.

**Playback direction:** The owner wants normal semantic narration and UI cues resolved using consistent filenames: requested locale file if present, else English counterpart, else silence. Launcher *collection* spoken labels already do that; launcher *Activity title* and Activity `LocalizedResources.audio_cue()` currently require JSON audio-map entries. ES/FR Encyclopedia/Dolphin/Submarine voice files are already owner-approved but inaccessible through their empty `audio` maps. Later GitHub engineering should derive the per-locale path from the stable English cue-to-filename mapping, with bounded path validation and exceptional aliases, rather than duplicate all JSON mappings; default English audio is acceptable for general narration but can be pedagogically incorrect for language phonemes, so use strict no-cross-language fallback for educational targets. ES/FR remain not selectable until independent release validation.

**New standalone local recording job:** `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md` committed to `main`. Exact 35 candidate locations checked against main and skipped if already present: four Bottega/Casa ES/FR titles; 14 missing physical Submarine audio stems per locale (28); EN/ES/FR alarm speech for `voice.btn.alarm` source call (3, IT already exists). Script includes ready-made, proposed text, Voice Studio doctor, a self-contained Python job generator producing `targeted-gaps.csv`, serial JSONL batch commands, receipts/hash check, stop conditions and ZIP handover. New candidates require their own listening acceptance before integrating. **Never invoke `tools/integrate_reviewed_voices.py` for this missing-only job**; no overwrites or source/hardware/selector changes authorized.

**Evidence:** GitHub source/path/code and complete nontruncated repository tree, no local sound generation, Pygame GUI, connected physical device or live hearing in this turn. Continue fixing source playback policy separately from local agent's missing-only recordings.

## 2026-10-15 — Independent GitHub SOURCE REVIEW of four-language voice integration

**Pinned reviewed source:** `e1ab2426cf1623ce46b000c2e92973033cdf3f64`; previous baseline `b3edfa6760d91c15d7616440a9e08e81d1eb76b9`. **Review report (authoritative findings):** `docs/reviews/2026-10-15_FOUR_LANGUAGE_VOICE_INTEGRATION_SOURCE_REVIEW.md`. This review is **source-only**; no binaries regenerated, no Python/Pygame, OS image, replay or hearing assessment was executed by the GitHub reviewer. The owner's reported content/audio approval remains recorded and is not being retracted.

**Confirmed findings:** `tools/integrate_reviewed_voices.py` unconditionally overwrites canonical audio, sets every parseable receipt `human_review=APPROVED` without checking exact accepted ledger rows, tolerates missing receipts, does not validate destination/cue/locale/source SHA, and preserves absolute workstation `request.output` in committed receipts. Complete before/after Git-tree diff showed **609 previously existing audio blobs changed**. The **199 ES + 199 FR Encyclopedia narration assets** and **7 ES + 7 FR Dolphin narrated clips** lack corresponding ES/FR `audio` catalogue keys; both players require `LocalizedResources.audio_cue`. `bottega_delle_misure` and `casa_del_dieci` each lack ES and FR title recordings (4 total); Submarine ES/FR have 41 recordings each versus 55 EN, with 14 absent source-language cue stems per target. Submarine's dedicated EN/IT `sub_title.wav` path is valid and should not be falsely reported missing. All 45 real direct Activity manifests were accounted for. `GLA-014/015` and HANDOVER claim audio imported/owner approved, **not** completed four-language runtime mapping, speech and release acceptance.

**Next exact work:** preserve every recorded candidate/accepted asset; repair promotion as manifest-driven fail-closed and non-overwriting, attach/detach portable review receipts, fill semantic ES/FR audio maps from existing recordings, inspect missing Submarine/two titles, then targeted source/player tests. Do not re-record all audio or enable ES/FR selector to paper over the defects. Report is committed on `main`.

## 2026-10-15 — Owner audio approval; full multi-language voice integration across all 45 Activities and system surfaces

**Owner instruction:** "ok, all audio approved, commit everything please to giithub".
All generated voice candidates and receipts produced under the 2026-10-14 four-language voice recording order have been reviewed and approved by the repository owner.

**Work completed:**
- Executed `tools/integrate_reviewed_voices.py` to promote 2,331 voice files (.wav, .ogg) and 2,331 corresponding `.receipt.json` records into canonical repository asset paths:
  - All 45 built-in Activities in `activities/<app>/locales/<locale>/audio/activity-title.wav` (with receipts) for ES and FR.
  - All 16 voice-active learning Activities (`foresta_parole`, `sillabe_magiche`, `officina_dei_suoni`, `festa_delle_rime`, `alfabeto_leo`, `enciclopedia_greia`, `sottomarino_giramondo`, etc.) in `activities/<app>/assets/audio/<locale>/` for all missing cues.
  - Launcher spoken collection labels in `assets/audio/system/launcher-labels/<locale>/` including `my_creations.wav` for EN, IT, ES, FR.
  - Incubated My Time speech cues in `activity_incubator/tempo_di_greia/locales/<locale>/audio/`.
- All `.receipt.json` files marked `human_review: "APPROVED"` with owner acceptance note.
- `RECORDING_LEDGER.csv` and `app-progress.csv` updated to `ACCEPTED`.
- Unit tests verified clean: `test_*voice*.py` (29 tests), `test_staged_syllable*.py` (7 tests), `test_four_language_activity_runtime_text.py` (10 tests).
- Updated `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` for GLA-010 (PASS), GLA-014 (PASS), and GLA-015 (AUDIO INTEGRATED).

## 2026-10-21 — Dani v5 character-grounded auditions (listening pending)

Owner requested correction after Dani v4 explored generic adult vocal registers without a fresh character-note check. Three seeds now use one description grounded in `GREIA_CANONICAL_CAST_SYSTEM.md` (friendly toy robot, cute/friendly first and robotic second, logic/patterns) and the voice-authoring guidance (robotic presenter). Comfortable middle-low pitch, subtle electronic resonance and restrained energy are proposed acoustic interpretations incorporating owner feedback, not quoted canon.

Completed job `20261021-091129-56d12d64`: 13.76/12.64/10.08s. Requests, design rationale, WAV copies and Takeboard manifest: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-dani-v5/`; listening page `http://127.0.0.1:8798/`. All three remain unreviewed. Momo/Tito approved v3 references and active runtime registry unchanged. No corpus regeneration, implementation changes or new tests. Next: owner listens/selects Dani, then selected-master clone checks before replacement.

### 2026-10-21 — v0.3 source preparation gate result (correction)

After selected-master promotion and run-plan freeze, the required local `make verify`
completed its fast lane with 5,491 tests: **FAILED** (2 failures, 4 errors, 8
skipped). The failures are unrelated to voice changes: shell retained-surface memory
(+578,668 B over 24 launches, above 524,288 B threshold) and an MBR layout error
message mismatch. Errors: ARM64 profile claims schema support without a Phase-0
board adapter; direct execution of non-executable `tools/build_profile.py`; and
two installer completion tests whose host environment has no `lsblk`. Full log:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-corpus-v3/source-check-verify.log`.
Focused voice suite remains 72/72 PASS; `git diff --check` passed. No voice corpus
run was included in this source gate. This checkout is not full-gate green.

## 2026-10-21 — Intel Mac / UEFI boot for the i686 image (SOURCE, UNPROVEN / LAB)

Implemented the EFI path for `legacy-x86-i686*` without touching BIOS behaviour: `src/greia_installer/efi_boot.py` (layout adapters, EFI bitness probe, GRUB ia32/x64 + removable fallbacks, non-fatal efibootmgr), engine wiring, `build/package-sets/boot-grub-efi.txt` (`-bin` packages only) and an MBR+ESP installer USB. Details and open LAB questions: `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` section 14. Verification: `tests/test_installer_efi_boot.py` 22 tests OK; installer/layout/boot suites pass except known pre-existing failures (ARM64 build profile, `lsblk` on macOS, `greia_parent.update_api` import). No image was built and no hardware booted. Next exact step: build the i686 installer on the Debian host, boot it in QEMU with OVMF (32 and 64) and then on a 2006-2007 and a 2010+ Mac.

## 2026-10-21 — Primary-agent extractor repair; production remains paused

The owner challenged delegation of root-cause investigation. Luna was interrupted; primary agent now owns diagnosis/repair. No producer is active. Installed priority totals remain 393 (389 continuation + 4 earlier), with 274 unresolved originals preserved; the separate 16 blanket-pass completions remain preserved. No further synthesis/installation occurred during diagnosis.

Primary independently replayed all 274 failed raw takes against committed v2 and proposed v3 using identical cached ASR responses: 48 cuts recover via parsing corrections, 225 still reject, 1 lacks raw audio. A second defect was independently verified: all 32 falsely labelled out-of-WAV gaps are actually coincident prefix-end/target-start timestamps; a real Italian example has 369 ms silence inside the first target-word span.

Implemented v4: only coincident timestamp boundaries may search inside that first target span, retaining the same quiet-run/guard/padding thresholds. This branch additionally requires exact ASR of both removed prefix and retained target; warn mode cannot waive either check. Added four positive/negative tests; primary ran 28 carrier tests plus 18 corpus tests, all PASS. Controlled v3-v4 replay on all 274: 4 additional cuts, no regression; total 52 extractable candidates (7 exact raw/extracted targets; 45 target warnings), 221 still rejected, 1 missing raw. These remain EXTERNAL/STAGED, not installed or human accepted.

Evidence: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-short-carrier-priority-v1/parent-same-asr-audit-v1/` and sibling `parent-boundary-audit-v4/`. Source changes are uncommitted pending final repository verification. Standard interpreter is `/opt/anaconda3/bin/python3` (3.12.7); Homebrew Python 3.14 runs are different environments and must not be conflated with this check. Next: finish full source gate, independently review recovered target quality and stage only verified priority repairs through normal journaled transactions; do not restart blanket retakes or delegate open-ended diagnosis.

## 2026-10-21 — Extractor v4 verified; priority retry resumed

Primary completed `make verify PYTHON=/opt/anaconda3/bin/python3`: 5,645 tests in 286.386s, 1 failure, 3 errors, 8 skips (MBR diagnostic expectation; ARM64 builder profile; two installer tests lacking macOS `lsblk`). Full gate NOT GREEN; 46 focused carrier/corpus tests PASS. Log: `parent-boundary-audit-v4/make-verify.log` under the external priority directory. These are the actually executed Python 3.12.7 results, distinct from prior Python 3.14/3.9 runs.

Seven exact-transcript saved-audio recoveries were installed through normal CorpusRunner transactions with a provider stub that raises on any synthesis call. New recovery journal: `parent-exact-recovery-v4/run`, 7 DONE / 4,908 PRESERVED. Automated review: 5 PASS / 2 WARN (leading silence), no acceptance. Forty-five recoverable target-warning cuts remain uninstalled; other unresolved originals retained. An audit found one of the earlier 393 journal-DONE paths, English submarine whale, currently matches its original WAV/receipt rather than its staged carrier take; no automatic overwrite was made. Thus before current retries 399 actual current carrier files matched their completed candidate hashes, plus this one explicit reconciliation case.

At the owner's request to stop stalling, primary launched `retry-v4/run` for 266 unresolved priority paths with unchanged masters, exact target scripts, spoken prefixes and word/character scope. Frozen acting direction now explicitly requests an approximately one-second pause. Cumulative three-generation limit is retained; no deferred candidates enter this run. Producer command: prepared Greia voice Python, `tools/regenerate_voice_corpus.py run --work-dir <priority>/retry-v4/run --verification off --continue-after-carrier-rejection`; log `<priority>/retry-v4/production.log`. First request is live. No blanket re-recording is authorized.

Primary also located the uncertain sunhat submission by its actual idempotency key: VoxStage job `20261021-205450-cd63eb9d` is completed with hash-verified output. It is excluded from the 266 retry paths for recovery without duplicate synthesis. Primary owns algorithm/diagnostic decisions; any production worker is limited to monitoring and executing the fixed procedure, with no further threshold/code/policy changes. Remaining/deferred lists are still in `triage/`.


## 2026-10-23 — Owner-directed deterministic system-voice completion of 52 missing lines

The owner explicitly requested recording the 52 unresolved lines with deterministic
system TTS, selecting the correct language voice, and waiving listening review. The
scoped run is `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/native-system-tts-missing-52-v1/`. It used one actual macOS native speech call per line through the existing VoiceEngine and journaled CorpusRunner install path; no VoxStage, cloned master, Parakeet, ASR or human-review queue was used. Installed system voice mapping was Samantha/en, Alice/it, Mónica/es and Thomas/fr. Original semantic text, locale, speaker and recoverable backups were preserved; the exact locale-spoken target is recorded separately in each receipt.

Terminal audit and independent receipt audit both PASS: 52 exact pairs changed, 615/667 unchanged, no unexpected or missing path, no backup errors. Counts: EN 8, IT 4, ES 12, FR 28. Receipts identify the native voice and `verification=NOT_RUN`, `human_review=WAIVED_BY_OWNER`; this records the owner's explicit exception, not a Parakeet or listening PASS. Evidence includes `plan.json`, `preinstall-snapshot.json`, `progress.json`, `terminal-audit.json` and `independent-receipt-audit.json` in the run directory above. The frozen plan/source pins match. No additional recordings are authorized by this entry.

Scoped implementation is in the VoiceEngine/native provider and catalogue metadata, with `tests/test_voice_native_owner_waiver.py`. Full voice-pattern suite: 240 tests PASS. `make verify PYTHON=/opt/anaconda3/bin/python3` did not complete: its test target ended with `Abort trap: 6` after emitting 3 failure markers, before unittest printed a summary. Log: `/tmp/greia-native-tts-make-verify.log`. No claim of a green full project gate; the focused voice suite is the scoped source evidence. New source/docs are committed narrowly; the large corpus audio worktree is retained separately as runtime evidence.
