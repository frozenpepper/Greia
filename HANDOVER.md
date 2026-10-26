# Greia — Current Engineering Handover

**Purpose:** the short current state for contributors and agents: active workstreams, recent results, blockers and next steps. It is not an archive.
**Public-source readiness:** IN PROGRESS. Root entry points exist (`LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`); the licensing/provenance audit is open (see `NOTICE.md`).
**Ordinary-family release:** NOT READY (`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).
**Last recorded A/B diagnostic checkpoint (2026-10-26; not a current HEAD claim):**
the corrected 80-test preflight passed for the earlier candidate, but main
subsequently gained production installer/launcher/platform localization changes
and language manifests outside that candidate's artifact-reuse allowlist.
The one-stage diagnostic boot was **not** started under that evidence.
Before any new boot/install attempt, consult the latest exact A/B work order,
recheck source and artifact identities, and obtain the existing gate's explicit
reuse decision or rebuild. No B-boot/rollback or ordinary-family release
acceptance is established by this checkpoint. See
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md`.

Entries dated before 2026-10-15 were removed from this file in the 2026-10-16 open-source cleanup. Read them with `git show 101e332a:HANDOVER.md`; lessons from that period are indexed in `docs/archive/README.md`.

Add new entries at the top of **Recent entries**, newest first.

**Release-documentation and repository-hygiene note (2026-10-26):**
The live language guide is `docs/development/ADD_A_GREIA_LANGUAGE.md`;
supported languages are derived from per-locale manifests, not a frozen
four-language Python list. 59 focused source tests passed at `bd3aa0a`.
Language GUI/physical acceptance is separate. Historical language-tiers
proposal and the September website mock studies were retired from the
working tree; the archive index preserves their lessons and Git history
preserves their full content. No production voice or build artifacts
were touched during that cleanup.

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

### 2026-10-26 — Documentation and historical capture hygiene, source-reviewed

Release documentation cleanup continued on GitHub after the original
manifest-language and user-guide consolidation. Reviewed the tracked
Markdown inventory and relative links for 240 maintained-candidate documents
at source HEAD `254faddfb55bd0b9ef94d663b988da9f2ead6612`:
**no broken repository-relative Markdown links in that source-level sweep**.
The read-only `tools/audit_repository_docs.py --scope maintained` helper now
also treats `docs/archive/README.md` as a maintained navigation index
(regression test corrected). This remote review is not a local test execution
and does not establish semantic accuracy of every historical document.

Retired nine 2026-08-22 PNG captures from completed historical visual-review
folders (514,381 bytes); Git history preserves them. No current Activity,
canonical artwork, voice, release image, tests, A/B diagnostic evidence, or
approved assets were touched. Preserved legacy audio acceptance reports,
Encyclopedia visual golden masters and 2026-10 installer/A-B evidence.
Historic review text may refer to now-retired screenshots; such links are
historic context, not live instructions. Next useful full-worktree check:
`python3 tools/audit_repository_docs.py --scope maintained` and
`python3 tools/audit_repository_docs.py --scope all` at the exact latest HEAD.
Leave current independent A/B acceptance undisturbed.

### 2026-10-26 — Release documentation and repository hygiene (GitHub source review)

Owner-directed cleanup audited repository tree metadata (15,753 tracked blobs
before cleanup, including 136 maintained Markdown manuals/skills/docs in the
live scope and dated historical plans/reviews). Read and source-compared
living language, installer, family, voice, Parent, Activity and release
guidance; reviewed the **136 maintained Markdown documents for repository
relative link targets via GitHub**: no missing in-repository paths found.
Historical evidence links in archived/daterun docs were **not** rewritten to
claim present-day correctness. Added
`tools/audit_repository_docs.py --scope maintained|all` and focused
`tests/test_repository_docs_audit.py` for repeatable, read-only local runs.
Those newly added Python tests and the full-checkout audit **have not yet
been executed**.

Reconciled manifest-based language support/maintenance and existing language
switching across the Activity-authoring and voice skills, product/first-party
release gate, developer and family guides, and agent routing. Corrected
historical Whisper/Chatterbox advice versus present VoxStage/VoxCPM2 and
Parakeet-TDT v3, and fixed the stale network-HTTP statement in the family
Parents guide. Browser Parents chrome is still an independent EN/IT/ES/FR
localization catalog in the separate pinned HTML repository and needs its
own new-locale work.

**Safe cleanup:** moved the superseded twelve-language proposal from live
`docs/product/` to `docs/archive/plans/`; retired 21 September website
prototype files (3,518,032 bytes) after verifying `website/` uses none,
and preserved a concise dated archived design decision with exact Git
recovery SHA; condensed this handover from 290,542 to 43,508 characters
(before adding this entry), with older entries recoverable through Git
history. Added ignores for disposable logs, coverage, test-result and
dependency-cache folders. No tracked test suite, actively relevant A/B
report, approved audio asset, canonical art master or release build payload
was deleted. Git/source docs review does **not** constitute full source gate,
browser acceptance, USB image/hardware testing, or approved new-language
readiness. Current next step: one bounded read-only local documentation
link audit and its three-unit-test suite on the exact new main commit;
report live errors separately from historical links, do not bulk-delete
evidence. Other in-progress A/B and voice work is unaffected.

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


## Older handover entries

Older entries have been retired from this **living** handover to keep the
release checkout navigable. This is not evidence deletion: detailed dated
plans/reviews remain under `docs/plans/` and `docs/reviews/`; the exact former
290 KB handover is recoverable from Git at
`91df2f0deff1774b17cc5c479e9a01ba856f3d4e`:

```bash
git show 91df2f0deff1774b17cc5c479e9a01ba856f3d4e:HANDOVER.md
```

Do not use those older "next step" or "PASS" statements to overwrite the
current workstream/gate decisions above. For current status, read the top
of this handover, then the exact active plan and procedure it names.
