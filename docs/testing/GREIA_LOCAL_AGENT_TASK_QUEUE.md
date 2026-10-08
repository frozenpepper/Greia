# Greia — Local Agent Work Queue

**Owner:** repository owner; **execution:** authorized local agent when available
**Branch:** `main`; **mode:** read/execute/report plus queue-only doc maintenance, never source repairs
**Updated:** 2026-10-08; **queue source baseline:** `01b1f535878d52139ac7660c686b65ce93e584d7` (later docs-only commits permitted)
**Product authority:** `docs/product/CHILD_TIME_AND_ROUTINES.md`
**Existing full P1–P7 acceptance:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`
**Project authority:** `AGENTS.md`, `SETUP.md`, `HANDOVER.md`
**Queue scope:** checks that need the local machine, Simulator, screenshots, hearing or human observation. Do not use this as a second implementation plan.

This file is **the one practical backlog for the local agent** while the GitHub
development session continues independently. Read the actual current source
and `git log` before assuming a command or a task is still relevant. The
queue intentionally distinguishes already reported results from unexecuted
new source. Updates to `main` by other workers take precedence.

## 0. Read this before beginning (mandatory)

1. Read `AGENTS.md`, `SETUP.md`, `HANDOVER.md`, this queue, and
   `docs/agents/GREIA_AGENT_OPERATIONS.md`. For the exact task, read
   its indicated procedure/skill. Do not run unrelated installer/flash tests.
2. Work in the *existing authorized* Greia checkout. Run `git status --short`.
   On an unexpectedly dirty tree, **STOP**; report paths and HEAD. Never
   `git reset`, `git clean`, `git stash`, force checkout, or discard
   someone else's work.
3. `git fetch origin main` then `git switch main` and
   `git merge --ff-only origin/main`. If any fails, **STOP**; no merge,
   rebase or branch. Record `git rev-parse HEAD`, status and
   `git log -8 --oneline`.
4. For each task, confirm any **minimum SHA** is an ancestor:
   `git merge-base --is-ancestor <sha> HEAD`. If absent, STOP and
   report divergence. If HEAD advanced after the SHA, inspect
   `git diff --name-only <sha> HEAD -- <affected paths>`; if task contracts
   changed, re-evaluate from current source rather than running obsolete
   instructions.
5. Establish `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=src` in the
   current shell; use the existing prepared Greia Python environment. If
   dependencies are unavailable, follow `SETUP.md` for a disposable
   developer environment only. Never change production dependencies or
   install privileged OS tooling to make a test green.
6. Each run gets a **new unique** ignored
   `tmp/greia-agent-queue-YYYYMMDD-HHMMSS/` evidence directory, with
   `HEAD.txt`, `git-status.txt`, `COMMANDS.txt`, one log and explicit
   exit code for each command, screenshots, `REPORT.md`, and `README.md`
   linking prior evidence. Never overwrite existing evidence.
7. **First failure in a dependency chain:** STOP that task and every
   downstream task depending on it. Unrelated non-destructive tasks may
   proceed ONLY when failure is fully isolated, workspace is clean and the
   report explicitly documents separation. Source/security ambiguity,
   dirty checkout, broken tooling or possible data loss means STOP ALL.
8. **No automatic source repairs or commits.** This queue authorizes
   testing and task bookkeeping only, not feature changes, production
   release approval, privileged builds, Acer boot/install, real user data
   exposure or new remote providers. Return the first failing command,
   full traceback/logs and a root-cause hypothesis; do not make quick fixes.
9. **Evidence honesty:** SOURCE pass is not GUI pass; SDL dummy frames are
   not real-Shell UI; bridge screenshots are not child-usability proof;
   manual visual review is not preschooler validation; simulated timing
   is not hardware timing. Audio files passing existence checks do not
   mean voices sound correct.
10. Never change `build/first-party-release-activities.toml` status
    from `draft` or move an incubated Activity to `activities/`.
    Greia screen-time/parent policy and trust boundaries must remain
    intact.

## 1. How the local agent MUST maintain this queue

Use status values **TODO**, **READY**, **BLOCKED**, **IN_PROGRESS**,
**PASS**, **FAIL**, **NOT_TESTABLE**. These are evidence states, not
implementation completeness. For each task, preserve its ID, scope,
test commands and expected observable behavior.

- Before starting: refresh current `main`, inspect tasks and dependencies;
  change one selected task to `IN_PROGRESS` in a queue-only documentation commit (owner-authorized 2026-10-08), recording tested HEAD and run directory.
  If commits are not authorized in the current invocation, do not edit
  this file: record the intended status change in the returned
  `QUEUE_UPDATE.md` instead.
- After a task: record `PASS` only if *all* acceptance conditions passed
  at that exact SHA. If a command fails, record `FAIL` (actual defect) or
  `BLOCKED` (precondition/test environment); if no browser/microphone or
  hardware is available, use `NOT_TESTABLE` and say why.
- Update the task's **Last result** as
  `YYYY-MM-DD | SHA | STATUS | evidence relative path | 1-line outcome`.
  For pending steps or an isolated failure, retain *remaining steps*,
  noting precise resume point. Never erase previously recorded attempts;
  append a compact dated line under **Execution history**.
- If a source commit lands while you are testing, **do not transplant a
  PASS to the new SHA**. State `PASS@oldSHA`, reopen only affected
  checks and quote `git diff --name-only`. Leave unrelated previous
  PASS results intact with provenance.
- The owner explicitly authorizes queue-only documentation updates on `main` (unless later revoked). Check current HEAD
  immediately before writing, preserve concurrent work, stage **only this
  file** with `git add docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`,
  commit a descriptive queue/evidence-only message and push fast-forward.
  **Never** amend, force-push or mix source edits. If authorization is
  limited to testing/no commits, submit `QUEUE_UPDATE.md` in evidence ZIP
  so the GitHub worker can merge the update later.
- Do not claim an arbitrary local path is available to ChatGPT. Return the
  evidence ZIP as an attachment; a text report or unuploaded local path alone
  is insufficient for independent review.
- After completing a task, choose the next **READY** task that does not
  require a stopped predecessor. Do as much as safely possible in one session;
  do not need permission between ordinary non-destructive tests.
- Leave this file short: keep detailed command stdout, PNGs, evaluations
  and diagnostics inside one evidence ZIP per run, NOT appended to this MD.
  Do not create dozens of small new acceptance plans.

## 2. Execution queue (priority order)

### GLA-001 — Validate newly owned headless Activity bridge

- **Status:** READY
- **Priority:** P0; **dependency:** none; **minimum source SHA:**
  `fa0526aab1fe688020620513ab3623f8a4516cc6`
- **Why:** the earlier Activity-only runner waited for a server that did
  not exist. A new owned ephemeral `SimulatorRemoteBridge` was committed
  plus a real subprocess smoke regression, but not yet executed.
- **Exact commands (each logged separately):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_headless_greia_activity.py' -v
  python3 -m unittest discover -s tests -p 'test_visual_library_gallery.py' -v
  ```
- **PASS:** both exit 0; bridge test produces valid 800×480 PNG, protects
  existing evidence and terminates child; semantic gallery test finds
  `clock` via source TOML tags. No third-party network access.
- **On failure:** stop the task; preserve pytest/unittest output and exact
  failing source. Do **not** rerun unrelated successful Time-model suites.
- **Last result:** UNEXECUTED at source `fa0526aa`.
- **Execution history:** prior *old harness* failed at
  `b96b08d3` (not an acceptance of this new source).

### GLA-002 — Capture My Time via repaired isolated bridge (IT/EN)

- **Status:** READY
- **Priority:** P0; **dependency:** GLA-001 PASS; **minimum source SHA:**
  `fa0526aab1fe688020620513ab3623f8a4516cc6`
- **Exact commands (replace EVIDENCE with this run's absolute directory):**
  ```bash
  python3 tools/headless_greia_activity.py --activity-main activity_incubator/tempo_di_greia/main.py --locale it --viewport 1024x600 --survival-seconds 4 --screenshot-prefix "$EVIDENCE/time-it-1024"
  python3 tools/headless_greia_activity.py --activity-main activity_incubator/tempo_di_greia/main.py --locale en --viewport 800x480 --survival-seconds 4 --screenshot-prefix "$EVIDENCE/time-en-800"
  ```
- **PASS:** each exits 0; `-child.log`, `-01-first-frame.png`,
  `-02-post.png` exist, correct dimensions, legible analog/digital
  clock, correct language, trusted simulator bootstrap overlay, no
  traceback and no forced kill. Preserve actual screenshots.
- **Boundary:** confirms only isolated Activity rendering, not the full
  child Shell or live interaction. The owner-agent previously rendered
  11 valid direct Pygame states, which do not replace this task.
- **Last result:** UNEXECUTED on repaired owned bridge.
- **Execution history:** prior old harness returned exit 3/no screenshot.

### GLA-003 — Current My Time model and real-interaction review

- **Status:** READY
- **Priority:** P1; **dependency:** current checkout required for source suite;
  **GLA-002 PASS required for the hands-on/Simulator leg, not the isolated
  source model suite**; **minimum source SHA:**
  `01b1f535878d52139ac7660c686b65ce93e584d7`
- **Exact suite:** `python3 -m unittest discover -s tests -p 'test_activity_tempo_di_greia.py' -v`
  **MANDATORY AGAIN**: run this suite on the current checkout even
  if GLA-001/002 exposes an isolated bridge failure; report its result
  independently and do not call the full GLA-003 task PASS. The Activity
  changed after the old 10/10 PASS. Check
  inner-hour/outer-quarter dial hit-geometry, actual clock isolation, icon rendering,
  visible keyboard focus and Return activation. Never reuse the old PASS for this newer source.
- **Hands-on:** actual desktop Pygame or supported full Simulator with a
  disposable profile, both locales, 1024×600 and 800×480. Exercise the
  clock, practice 23:45→00:15, timer 1/3/5/10, running/pause/finish/restart,
  stopwatch, keyboard alternatives (LEFT/RIGHT/TAB focus and ENTER),
  protected Home corner and resize. In practice mode touch each of the 12 inner hour positions and each
  outer quarter-hour marker (12/3/6/9), including taps on the
  visible hour numerals. Verify only the intended hand
  changes; the center and ring gap are inert. Check the AM/PM half-day
  selection rule and ensure real system time, Parent limits and
  running stopwatch/countdown are never changed. Inspect icon-first mode/action controls,
  focused outline, and gentle timer-finished stars in both languages.
  For any new child-friendly icon controls verify they work **without**
  reading text. Capture screen before/after actions with a clear file name.
- **PASS:** all functional state transitions correct, no text clipped,
  no input stealing Home, no unexpected dialog, no system clock or parental
  screen-time mutation. Review legibility at actual **800×480 pixels**.
  Source now has new controls, so the old 11 direct-renderer PNGs do not
  replace current screenshot/child-usability review.
- **If no GUI:** `NOT_TESTABLE`, keep SDL dummy proof separately;
  do not invent interaction or visual acceptance.
- **Last result:** previous 10/10 model + 11 SDL dummy frames
  reported `PASS@b96b08d3`; hands-on not tested.

### GLA-004 — Shared developer artwork gallery usability

- **Status:** READY
- **Priority:** P1; **dependency:** GLA-001 PASS for changed gallery suite;
  **minimum source SHA:** `4d5c0de5d1a035732765c5182ef428d6f20becc9`
- **Command:**
  `python3 tools/visual_authoring_library.py gallery --output "$EVIDENCE/visual-library.html"`
  (new file only). Open the local file in an **already available** browser
  without network access. Search `clock`, `tree`, `shadow`; filter
  preferred/candidate; capture wide and 800×600 views.
- **PASS:** 101 asset previews resolve, no remote fetch, known clock-tagged
  `dial_hands` and `axle_hands` visible through `clock` search,
  readable large thumbnails, no overflow, semantic metadata honest.
- **If no browser:** report `NOT_TESTABLE`, attach HTML and source
  preview checks, do not install browser for this alone.
- **Last result:** 101/101 source URLs + HTML generated at `b96b08d3`;
  browser screenshots untested.

### GLA-005 — Produce and listen to My Time bilingual spoken guidance

- **Status:** BLOCKED
- **Priority:** P1; **dependency:** owner-approved voice design and
  local capability / Model authoring access; not GLA-001 dependent.
- **Voice authority:** `skills/greia-activity-authoring/SKILL.md`,
  `tools/greia_voice.py`, `docs/product/CHILD_TIME_AND_ROUTINES.md`,
  and `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md`
  with exact IT/EN cue IDs, words, speaker, triggers and review requirements.
  Before authorizing providers, run **only** `python3 tools/greia_voice.py doctor`.
  Use configured **Modal** authoring when available/approved and existing
  voice workflow; never invent a runtime cloud TTS or invoke paid/live
  providers without explicit authorization.
- **Work when unblocked:** use the reviewed cue table in the VOICE_PRODUCTION_BRIEF
  rather than inventing a speaker, cue name or translated line. Generate
  only through the existing VoiceEngine and stage reviewed WAV
  in correct Activity-local locales and map keys, check mono/22050Hz/
  16-bit title requirements. Listen to all samples in both languages,
  report pronunciation, peak level, timing, interruptions and awkwardness.
- **PASS:** all prerequisite voiced instructions, title WAV and actual
  listen-tested quality; no runtime synthesis, no false prerecorded claim.
- **Last result:** audio arrays currently empty; no voice approval.

### GLA-006 — Normal Greia Shell / My Time route and protected Home

- **Status:** BLOCKED
- **Priority:** P1; **dependency:** GLA-002 plus source-promotion decision
  and required voice/visual acceptance; My Time is still in incubator.
- **Authority:** `tools/headless_greia_simulator.py`,
  `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`.
- **When unblocked:** run the tool with a fresh `--workspace-dir`,
  `--activity-dir activity_incubator/tempo_di_greia`, locale/viewports,
  `--screenshot-prefix`; verify actual Shell → profile → Collection →
  Activity → trusted Home return. **Do not** use the old Activity-only
  harness as proof of this. Check developer-unsigned privileges remain
  correctly bounded. Do not promote automatically based on a headless screenshot.
- **PASS:** matching log/frames showing real Shell navigation, protected
  Home return, clean exit and correct non-privileged Activity identity.
- **Last result:** NOT TESTED.

### GLA-007 — Creations P1–P7 accumulated desktop/audio acceptance

- **Status:** READY
- **Priority:** P1; **dependency:** a clean checkout / prepared environment,
  NOT blocked by a Time-only test.
- **Authority:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`
  (full command list and 74+ scenarios). Read the *current* procedure and
  report changed source since its pin.
- **Do:** test Gallery/typed picker, PNG/WAV/UTF-8 interoperable edits,
  saved-copy independence after shared deletion, bounded disk usage,
  Parent modal trust, release fail-closed and real audio preview. Use
  disposable profile/media only. Record observed visual/differentiation
  quality as well as technical correctness.
- **PASS:** all required tested scenarios at same SHA, evidence ZIP,
  precise source-vs-Simulator-vs-physical classification; draft status
  still retained. If no audio/GUI, mark individual sections NOT_TESTABLE,
  never inflate to full PASS.
- **Last result:** earlier *focused* P6 staging passed (33 exact); full
  P1–P7 acceptance remains unexecuted.

### GLA-008 — Art / cast / launcher visual comparison

- **Status:** READY
- **Priority:** P2; **dependency:** current image assets available.
- **Authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`,
  `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`,
  `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`,
  `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
- **New source/test minimum SHA:** `0a09eaf49b247d4c6f427481530a02ce370c9123`.
- **Commands (save logs/exit codes; STOP on first failure):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_visual_family_contact_sheet.py' -v
  python3 tools/visual_family_contact_sheet.py --output "$EVIDENCE/greia-art-family.png"
  ```
- **Do:** inspect the **single generated contact sheet** with 39 canonical
  core icons, 45 Activity icons and 30 canonical character expression images.
  The same real artwork is rendered side-by-side at 128/64/48 px. Compare to
  existing Greia launcher screenshots separately; do not silently blend
  screenshots into authored art. Judge stylistic mismatch, empty space,
  hierarchy, pre-reader uniqueness, contrast and tiny-size legibility.
- **Expected:** unit test PASS; actual PNG opens, all 114 tiles are present,
  columns do not overlap, original assets unchanged. Developer-only output;
  never staged in the installed OS.
- **Evidence:** contact sheet + ranked severity/fix recommendations,
  source hashes, no source art change or unsupported design PASS.
  Owner approves any major visual redesign direction later.
- **Last result:** NOT TESTED at current source.

### GLA-009 — Installed lifecycle Acer / installer / first boot

- **Status:** BLOCKED
- **Priority:** separate hardware owner gate; **dependency:** explicit owner
  authorization and `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`.
- **DO NOT START** merely because this queue is being executed. Requires
  exact current hardware plan, authorized media safety and full first-boot
  stop conditions. This task is a reminder, not install authorization.
- **Last result:** PHYSICAL NOT TESTED in this workstream.

## 3. Execution history (append a one-line fact here, never fabricate)

- **2026-10-08:** owner-local accepted prior four P6 / Time package tests
  and exact 33-item developer staging at `47a949a0`; blocked at old
  Activity-only bridge topology.
- **2026-10-08:** owner-local resumed at `b96b08d3`; Time suite 10/10,
  eleven SDL dummy frames, 101/101 source gallery previews; old harness
  bridge failure persisted; HTML GUI not available.
- **2026-10-08:** GitHub source added owned bridge + real Pygame test and
  visible gallery tags (`fa0526aa` source/test anchor); NOT executed yet.
- **2026-10-08:** Time incubator gained direct quarter-hour touch, icon-first
  controls, gentle visual timer stars and visible arrow/Tab/Return focus
  (`3a9b9b8b`); refreshed suite and screenshots pending.
- **2026-10-08:** Actual-art contact sheet source generator + tests added
  (`0a09eaf4`); all visual acceptance pending.

- **2026-10-08:** Prepared semantic IT/EN Dani recording requests in the
  Time incubator VOICE_PRODUCTION_BRIEF. No production, audio generation,
  human listening, runtime playback or provider authorization yet.

- **2026-10-08:** Owner GitHub continuation added a 12-position inner hour ring and four outer quarter-hour touch stops in the incubated My Time Activity, with focused real-input/model tests. Unexecuted, no child visual signoff. GLA-003 covers current source acceptance.

- **2026-10-08:** A running Timer completion no longer disappears when
  the child switches to Clock/Stopwatch at the moment it finishes;
  unseen completion stays pending until the Timer mode returns
  (`33b0ddc6`). Current-source GUI review owed in GLA-003.

When the GitHub developer changes an API or acceptance target, update the
affected task in this SAME FILE in the same source commit, preserving all
old evidence references and avoiding standalone mini-plans.
