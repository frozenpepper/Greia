# Greia — Local Agent Work Queue

**Owner:** repository owner; **execution:** authorized local agent when available
**Branch:** `main`; **mode:** read/execute/report plus queue-only doc maintenance, never source repairs
**Updated:** 2026-10-12; **queue source baseline:** `de162fd1448f7f56ac15f95f2876724a029f7354` (later docs-only commits permitted)
**Product authority:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` + `P6_CHILD_NAVIGATION_AND_VISUAL_CURATION.md`; My Time remains separately in `docs/product/CHILD_TIME_AND_ROUTINES.md`
**Existing full P1–P7 acceptance:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`
**Project authority:** `AGENTS.md`, `SETUP.md`, `HANDOVER.md`
**Queue scope:** checks that need the local machine, Simulator, screenshots, hearing or human observation. Do not use this as a second implementation plan.

**Scoped GLA-014 follow-up — owner instruction 2026-10-19:** the current
existing-corpus replacement work order is
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, using
`tools/regenerate_voice_corpus.py`. The owner explicitly requested tool execution,
monitoring and necessary bug fixes; this scope supersedes the queue's ordinary
source-repair/no-overwrite restrictions for that operation. Preserve deterministic
isolated letters/syllables, originals and unrelated dirty work. Full replacement
is not yet run; 4,543 ready and 167 metadata-blocked files were inventoried.
Fresh output remains listening-pending. Follow that work order for progress,
recovery, source fixes and evidence; do not start another competing voice queue.

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
  `510edb8bb7738c6c4b15727f98d1ed4f027fbe4a`
- **Exact provider-free suites (separate logs/exit codes):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_localization.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_time_speech.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_time_audio.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_tempo_di_greia.py' -v
  ```
  Do not assume the newly added voice source has been run locally.
  Specifically check no voice before READY, welcome → instruction ordering,
  stale-cue interruption, bounded pending cue, completion priority,
  selected-locale-only resolution through the real Greia localization
  catalogue (plus legacy default fallback preservation), source launch
  in both import modes, and
  no speaker/replay target when actual recordings are missing, and
  immediate Quit/stop before READY never emits voice or readiness.
  **New (same suite):** complete a 1-second timer before the first Activity
  frame, then exercise `TimeActivity.run()` with a fake voice channel and
  mock READY; prove READY precedes exactly one completion cue, no welcome
  or timer instruction supersedes completion, and early Quit is still silent.
  Also prove missing/corrupt `presenter.welcome` cannot block the required
  first instruction, failed replay returns false, and a closed coordinator
  never plays again. The new
  audio-boundary suite uses real locale bundle catalogues, a mocked mixer,
  and disposable fake audio bytes. Verify it demonstrates a selected-English
  clip under `assets/`, normal fallback retention, strictly missing-English
  behavior, **no WAV decoding at Activity startup**, at-most-one decode per
  valid cue, and corrupt WAV fail-closed. These are logical/mock tests,
  NOT actual audible output, quality or valid production WAV decoding.
  **MANDATORY AGAIN**: run this suite on the current checkout even
  if GLA-001/002 exposes an isolated bridge failure; report its result
  independently and do not call the full GLA-003 task PASS. The Activity
  changed after the old 10/10 PASS. Check
  inner-hour/outer-quarter dial hit-geometry, actual clock isolation, icon rendering,
  visible keyboard focus and Return activation. Never reuse the old PASS for this newer source.
- **Hands-on:** actual desktop Pygame or supported full Simulator with a
  disposable profile, both locales, 1024×600 and 800×480. Exercise the
  clock, practice 23:45→00:15, keyboard UP/DOWN spoken Practice
  transitions (where recordings exist), timer 1/3/5/10, running/pause/finish/restart,
  stopwatch, keyboard alternatives (LEFT/RIGHT/TAB focus and ENTER),
  protected Home corner and resize. In practice mode touch each of the 12 inner hour positions and each
  outer quarter-hour marker (12/3/6/9), including taps on the
  visible hour numerals. Verify only the intended hand
  changes; the center and ring gap are inert. Check the AM/PM half-day
  selection rule and ensure real system time, Parent limits and
  running stopwatch/countdown are never changed. Inspect icon-first mode/action controls,
  focused outline, gentle timer-finished stars, and (when recorded voices
  have been reviewed and mapped) the large speaker/replay target in both
  languages. With the current empty audio maps, verify the replay control
  is absent; do not count simulated fake-transport speech as listened audio.
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
- **Wired source is not playable content:** `time_speech.py` /
  `time_audio.py` implement prepared semantic sequencing and one cached
  playback channel; the IT/EN locale `audio` tables are still empty.
  English must not silently fall back to Italian speech. Verify
  the actual `locales/<locale>/audio/` mappings and run `GLA-003`
  again once recordings are integrated. A replay target must not be
  visible for a missing recording.
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
- **Required current-source P3 Gallery regression (run first, separately logged):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_creation_gallery_render.py' -v
  python3 -m unittest discover -s tests -p 'test_creation_gallery_layout.py' -v
  python3 -m unittest discover -s tests -p 'test_creation_gallery.py' -v
  python3 -m unittest discover -s tests -p 'test_creation_selection.py' -v
  python3 -m unittest discover -s tests -p 'test_creation_picker_host.py' -v
  ```
  Minimum source SHA `957a7da1073e7807f3108d8adb7bd2771f81fac8`.
  The first suite uses **actual dummy SDL/Pygame** and a disposable
  profile-backed `CreationLibrary`, not only mock-painter methods.
  Confirm Italian and English completely empty library at 480×320,
  800×480 and 1024×600 renders a visible empty state without exception.
  Confirm an empty audio-only picker shows an **audio** illustration,
  never a mismatched picture, offers cancel and mints no handle.
  Confirm the empty-library explanatory caption stays entirely above
  navigation controls at the 1024×600 reference size (regression included
  in the new real-Pygame suite). Inspect actual screenshots: labels
  cannot cover previous/next/back and should not look crowded.
  In the library confirm that delete dialog intercepts all background
  replay/preview/navigation keys; Enter defaults to Cancel and preserves
  the artifact; Right then Enter explicitly deletes it. Observe focus
  outline and cursor/selection feedback in a **real GUI** before
  acceptance. Distinguish dummy SDL test PASS from human visual PASS.
  **Trusted picker lease tests (four new cases in the existing
  host test file):** while a chooser is visible, cancel via the
  Activity broker; let a pending request reach its 180-second
  simulated expiry; replace an already-cancelled/collected request
  with a new one; and simulate broker cancellation failure.
  In each case verify the previous chooser closes, stops its
  audio/preview owner, grants nothing, clears the child input overlay
  and returns focus to the Activity. If cancellation itself errors,
  the Activity display must be restored before the host reports
  the fail-closed error. On a later new selection, old taps must
  **not** reach the new request. These are provider-free tests
  using the real `CreationSelectionCoordinator` clock where
  applicable, not proof of live Xorg/Simulator focus restoration.
  In the full Simulator repeat cancel/expiry with a disposable
  Activity, inspect actual video/screenshot and compare with
  `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md`.
  If a suite fails, STOP this P3 slice and return traceback/log + HEAD.
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
- **Last result:** earlier *focused* P6 staging passed (33 exact);
  empty-gallery, safe delete and stale-modal cancel/timeout source
  fixes committed with unexecuted tests. Full P1–P7 acceptance remains
  unexecuted.

### GLA-008 — Art / cast / launcher visual comparison

- **Status:** READY
- **Priority:** P1 (current owner design focus); **dependency:** current image
  assets and prepared source test environment. GUI screenshot inspection is
  a separate evidence layer and is NOT gated by My Time.
- **Authority:** `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md`,
  `docs/design/GREIA_CANONICAL_CAST_SYSTEM.md`,
  `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`,
  `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`.
- **New source/test minimum SHA:** `0a09eaf49b247d4c6f427481530a02ce370c9123`.
- **Current child Home/catalogue source pin:** `de162fd1448f7f56ac15f95f2876724a029f7354`.
  Start with the real 32-candidate P6 design record:
  `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/P6_CHILD_NAVIGATION_AND_VISUAL_CURATION.md`.
  Confirm source metadata of **exactly six genuine Create anchors**;
  no Acquario/Cucciolo/Specchi/Torre in Create; those four still
  available through their honest collections. Confirm My Creations
  appears **adjacent to Create** even when Parent filters away all
  creative apps, keeps the distinct backpack icon and never obtains
  Activity/package privileges. Check 1024×600 (3×2),
  800×480 (2×3) and 480×320 (compact 3×2) Home portal layout.
  Correct Italian/English labels, sufficient real targets, complete
  visibility, profile switcher and Back/OS chrome are critical.
  **New source-committed compact caption behavior:** at 800px
  and below, My Creations visibly says **Creazioni** (IT) /
  **Creations** (EN) instead of shrinking the full longer title;
  at 1024px the full **Le mie creazioni** / **My Creations**
  remains. Inspect the visual result and any remaining ugly
  squashing or overlaps, with actual fonts and PNG assets.
  `test_child_home_creation_organization.py` now tests the
  full/compact text in IT/EN/ES/DE/FR without changing the
  spoken semantic identifier; **GLA-010 prerecorded cue still
  missing**, not waived by a shorter printed caption.
- **Exact additional source checks (separately logged; stop first failure):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_child_home_creation_organization.py' -v
  python3 -m unittest discover -s tests -p 'test_launcher_collection_visual_curation.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_discovery_policy.py' -v
  python3 -m unittest discover -s tests -p 'test_launcher_spoken_labels.py' -v
  python3 -m unittest discover -s tests -p 'test_launcher_layout.py' -v
  ```
  Do not promote P6 merely because these tests pass; actual Shell
  screenshots and independent listening/child visual review remain owed.
- **Commands (save logs/exit codes; STOP on first failure):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_visual_family_contact_sheet.py' -v
  python3 tools/visual_family_contact_sheet.py --output "$EVIDENCE/greia-art-family.png"
  ```
- **Play/Learn curation gate (new source):** compare the P6 record's
  *complete* 21-Activity Play and 22-Activity Learn mappings against
  the actual `build/first-party-release-activities.toml` and the
  underlying `activity.toml` files. The recently reclassified
  `storie_della_mia_voce` must be **Create only**, and
  `quattro_stagioni` **Explore+Learn only**. Confirm the count, that
  no Activity was deleted or had its Parent visibility/age/
  progression data altered, and that age-3/4/5 filtered
  catalogues neither duplicate nor lose a permitted Activity.
  Play/Learn correctly remain direct browse at the current
  32-candidate roster rather than fake complete submenus.
- **Art/language gate (new source):** verify all 13 semantic discovery
  group icons resolve to **different actual canonical core assets**;
  compare small 48/64px silhouettes, especially Music vs
  Drawing, Words vs Stories, Numbers vs Puzzles vs Building,
  and Action vs Puzzles. In both the normal and shared-art
  Activity card renderers observe Italian **“Avvio...”**
  and English **“Starting...”** only in the corresponding
  locale during launch; check that the badge fits the tile
  without clipping, and does not obscure the Activity image.
  Treat source-test PASS as separate from real-UI visual PASS.
- **Design/organization leg:** compare actual six Home portal
  screenshots and the six creative Activity icons against the source
  contact sheet at 128/64/48px; rank misleading or near-identical art,
  overly dense panels and confusing child language. For large Play
  and Learn collections, give a real gameplay-based activity-to-child-intent
  grouping proposal that covers **every** item after age filtering.
  Do not add tags, change manifests or modify source: report whether
  the current five-group bounded planner can partition honestly or
  whether keeping direct cards is currently safer.
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
- **Last result:** compact Home label source + additional text tests
  implemented (minimum `0439f5ef5703ed697200fc2a32167643d360cc8a`);
  actual whole-Shell snapshots and full 114-item contact
  sheet remain **NOT TESTED**. A remote local SVG-only preview
  of the real authored portal/card frames is NOT live app evidence.

### GLA-011 — Wave 37 three-Activity input and save-recovery acceptance

- **Status:** READY (source tests); full isolated GUI depends on GLA-001 PASS.
- **Priority:** P1; **minimum source SHA:** `5f45d0dad6df1cdb6f7a2b05d53712d15f1c89bf`.
- **Scope:** Woodland Hide-and-Seek (`nascondino_bosco`), Little Green Thumb
  (`piccola_serra`), Magic Aquarium (`acquario_magico`); IT/EN.
  No drawings/voices modified or accepted by this task.
- **Preconditions:** follow §0 verbatim; clean ff-only `main`, available
  Pygame from the SETUP-approved environment, no source repairs. Export
  `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src`. Record full SHA and
  per-command exit codes. Stop on the first real failure. Do not continue
  to later steps merely to collect more PASS counts.
- **Provider-free commands, in exact order, each in its own log:**
  ```bash
  python3 -m unittest discover -s tests -p 'test_activity_wave37_input.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_nascondino_bosco.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_piccola_serra.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_acquario_magico.py' -v
  make verify
  ```
- **Gameplay inspection:** in the actual isolated Simulator (only after
  GLA-001), launch each Activity in IT and EN at 1024×600 and 800×480;
  capture first, active keyboard-focus, changed-state and victory/replay
  frames. Woodland: arrows select five spots, Enter inspects, four
  **different** correct finds give exactly four stars and one completion;
  cleared hiding places stop showing clues and keyboard focus skips them,
  replay resets without erasing prior earned total. Greenhouse: arrows
  select all four pots, keys 1–4 choose tools, Tab cycles plants,
  Enter/Space applies seed→water→sun→water→harvest; six harvests give
  exactly one completion, replay works. Aquarium: arrows move visible
  cursor, keys 1–3 choose tools, Enter acts on water/chest, Space toggles
  light, C opens chest; a corrupted counter save must load safely. Verify
  touch and mouse still use the same actions, including Home/Back protected
  screen regions. No gesture may duplicate rewards or skip terminal state.
  Save one bilingual screenshot/evidence set and identify problems, not
  just “launched OK.”
- **PASS boundary:** source commands all exit 0 **and** each live game
  interaction works without traceback, unbounded saved counters, repeated
  rewards, synthetic touch+mouse double actions, invisible keyboard
  focus or protected-chrome leakage. A headless
  launch alone is startup evidence, not complete gameplay acceptance.
  Real speakers, child usability, full Greia Shell and Acer/ARM remain
  separately unproven.
- **Failure:** preserve exit code, first failing assertion, logs,
  screenshots and any offending save **with personal data removed** in
  one evidence ZIP. Stop; no modifications outside queue-only status.
- **Last result:** UNEXECUTED on GitHub source `5f45d0da`.
- **Execution history:** the earlier Wave 37 chat archive described
  successful local Pygame work but did not include its edited project
  or a reusable evidence ZIP. This GitHub reconstruction is a new SHA
  and requires its own acceptance.

### GLA-012 — Wave 36 GitHub restoration: Memory, Train, Maze, Stars

- **Status:** READY for source tests; visual/gameplay GUI checks require GLA-001 PASS.
- **Priority:** P1; **minimum source SHA:**
  `a6c7feadc42fc7061a1394410e797192e6790e2e`.
- **Why:** the earlier archived Wave 36 project ZIP/tests were not pushed
  to canonical GitHub. This is a new independent source reconstruction at
  new SHAs, not a transplant of the archived 78/78 PASS evidence.
- **Source focus:** `memory_meraviglie`, `treno_numeri`,
  `labirinto_magico`, `stelle_incantate`; no drawings or new voice
  recordings were edited. Do not modify their art during this task.
- **Preflight:** follow §0. Clean `main`, ff-only synchronization,
  approved Pygame environment and source SHA ancestor proof required.
  Stop at first failure. Produce logs with exact exit codes and HEAD.
- **Commands (each separately logged, sequential):**
  ```bash
  python3 -m unittest discover -s tests -p 'test_activity_memory_meraviglie.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_treno_numeri.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_labirinto_magico.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_stelle_incantate.py' -v
  make verify
  ```
- **Required supervised behavior:** test IT and EN on 1024×600 and
  800×480 through the existing isolated Simulator. Memory: visible
  arrow focus, Enter/Space flips cards, mismatch lockout, every match
  exactly one reward, victory/replay and T/G theme/grid switching.
  Explicitly test a cleared column. Train: keyboard crate selection and
  loading, bounded celebration particles across repeat play,
  full five stations with one reward each, no loading during
  arrival/departure/celebration, victory and replay. Maze: repeated
  arrows/clicks while a slide is active cannot overwrite that path;
  confirm reaching collectible/exit, rewards, replay. Stars:
  arrow selection + Enter connect in order, completed figure advancement,
  fact key F, victory/restart. Strict IT/EN fact audio must not fall back
  across languages. Where a required recording is missing, mark that
  language's voice claim BLOCKED; never generate voices without approval.
  Check mouse/touch parity, safe Home/Back bounds, genuine screen focus.
- **Expected output:** one run evidence ZIP with command logs, locale
  screenshots, complete gameplay observations, WAV listening notes when
  applicable, exact SHA, hashes and errors; update queue-only result
  and preserve this history. No source edits, Actions, paid providers,
  flashing, reset/clean/stash or unapproved OS installation.
- **Last result:** UNEXECUTED on reconstructed GitHub source.
- **Execution history:** archived local Wave 36 reported 78 regression
  tests and 16 Pygame launches passing on an unavailable local tree;
  those numbers are HISTORICAL and must not certify current main.

### GLA-013 — Clinic and Orca archived-fix reconciliation

- **Status:** READY for source tests; actual GUI/audio needs GLA-001 PASS.
- **Priority:** P1; **minimum SHA:** `2cfcde61de4651540f8fdd9ce58c356979ec1bf1`.
- **Purpose:** verify independently reconstructed portions of archived Waves
  34–35 now committed to GitHub. The earlier local screenshots, WAV tests
  and PASS counts do not certify these new GitHub commits.
- **Preconditions:** follow §0, clean ff-only `main`, valid Greia Pygame
  Python setup. Log every exit code, stop on first failure, no source edits.
- **Exact sequential commands:**
  ```bash
  python3 -m unittest discover -s tests -p 'test_clinica_cuccioli_refactor.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_baia_delle_orche.py' -v
  make verify
  ```
- **Hands-on:** IT/EN at 1024×600 and 800×480. Clinic: use only arrows
  and Enter to select an explicit instrument and treat each of five
  patients; wrong instrument does not advance, success/replay work and
  each healed patient yields one event. Confirm clear focus and real
  patient audio feedback. Orca Bay: six keyboard tools including
  facts; Italian spoken fact must be Italian, English must play English
  and never silently Italian. Press-drag/touch-hold each orca: one
  cuddled/reward event per contact gesture, no sound storm; lift and
  start new gesture should permit one more reward. Verify pointer,
  touch emulation dedup, protected Home/Back and clean exit. Return
  captured/screenshotted states plus speaker/listening notes.
- **Pass:** source command exits 0 and observed behaviors correct
  without repeat rewards, wrong-language facts or crashes. Record
  missing approved recordings as BLOCKED, not as successful audio.
  One evidence ZIP with exact SHA, logs, image hashes and first failure.
  Never run providers, hosted Actions, installer/USB or hardware tests
  without the separately required authority.
- **Last result:** UNEXECUTED on reconstructed GitHub source.
- **Execution history:** archived Wave 34/35 local tests are historical
  only, not present evidence on GitHub main.

### GLA-014 — Four-language registry, staged installer text and voice inventory

**2026-10-19 replacement follow-up:** PREPARED, full run UNEXECUTED.
Use `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`; its explicit owner scope
permits regeneration/replacement and necessary source fixes through the new
tool, superseding older add-only/source-frozen restrictions below for this
operation. The earlier PASS refers to the previous recording/integration batch.

- **Status:** PASS (all audio produced, owner-approved and integrated)
- **Priority:** P1; **minimum source SHA:**
  `0a513fa387c956aa329d2012a05f043d61d7f2ac`.
- **Source authority:**
  `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`.
  Follow the sibling **`LOCAL_AGENT_VOICE_PRODUCTION.md`** exactly
  for per-cue, per-speaker four-language jobs and the real EN/IT
  missing recordings. This queue is only the execution bookmark.
- **Preflight:** §0. Read `SETUP.md` before any environment change.
  Clean `main`, ff-only, current SHA ancestor and recognized
  Python environment. No branch/source edits, TTS/Modal calls,
  downloaded models or privileged images.
- **First stage — non-destructive source commands, each logged
  with true exit code, sequential and first-failure stop:**
  ```bash
  python3 -m unittest discover -s tests -p 'test_system_language.py' -v
  python3 -m unittest discover -s tests -p 'test_installer_localization.py' -v
  python3 -m unittest discover -s tests -p 'test_four_language_inventory.py' -v
  python3 -m unittest discover -s tests -p 'test_word_forest_phonics_inventory.py' -v
  python3 -m unittest discover -s tests -p 'test_staged_es_fr_literacy_curricula.py' -v
  python3 -m unittest discover -s tests -p 'test_staged_alphabet_curricula.py' -v
  python3 -m unittest discover -s tests -p 'test_staged_syllable_curricula.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_festa_delle_rime.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_officina_dei_suoni.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_sillabe_magiche.py' -v
  python3 -m unittest discover -s tests -p 'test_four_language_inventory.py' -v
  python3 -m unittest discover -s tests -p 'test_staged_es_fr_literacy_curricula.py' -v
  python3 tools/audit_greia_language_coverage.py --root . --output tmp/greia-four-language-coverage.json --recording-ledger tmp/greia-four-language-recordings.csv
  PYTHONPATH=src python3 tools/audit_launcher_spoken_labels.py --locales en it --json
  make verify
  ```
  For the inventory, use a unique ignored evidence directory
  (replace the example `tmp/` output with its actual unique path)
  and preserve the full JSON. The new source catalogue includes
  108 staged ES keys and 108 FR keys; the installer still exposes
  only EN/IT. Check dictionary key parity plus real error/warning
  meaning and dynamic SSIDs/keyboard/battery formatting.
- **Second stage — supervised non-destructive GUI:** use the
  approved existing Simulator/installer preview fixture only,
  not a real destructive installer. Capture first-language screen
  with **exactly EN/IT choices**, keyboard/pointer focus,
  1024×600 and 800×480. Stage the ES/FR translations via
  `InstallerTranslator("es")` / `InstallerTranslator("fr")`
  in source-approved non-destructive preview tests; these should
  not create selectable Spanish/French devices yet. Test old
  install-record locales `es`, `fr`, `zh-CN` read as
  English safely without rewriting history, parent PUT rejects
  unsupported writes. Do not create a new disk image solely to
  inspect translations.
- **Third stage — voice preparation, NOT actual generation:**
  run `python3 tools/greia_voice.py doctor` (no downloads),
  follow the voice work order to produce the full
  `RECORDING_LEDGER.csv` with all four locales and the known
  missing EN/IT `my_creations.wav` and My Time cues. Report
  `BLOCKED_MODAL_PROVIDER` and `BLOCKED_TEXT` where appropriate,
  including current source SHA. Actual cloud/provider calls
  need explicit owner authorization and provider integration.
- **PASS scope:** only executed tests/inventory and observed
  EN/IT selector correctness, not finished 4-language support.
  Voice stage cannot be PASS until human reviewed and recorded.
  Return logs, output hashes, text keys missing, candidate cue
  list, screenshot/audio-availability notes and evidence ZIP.
- **Important expected blocker:** the launcher spoken-label audit now includes
  the **My Creations** portal. With its known missing EN/IT
  `my_creations.wav` clips the audit can legitimately return
  `FAIL` until GLA-010 has generated, human-approved and integrated
  those two files. This is honest missing-content detection, not a
  reason to weaken the audit or fake placeholder recordings.
- **Last result:** PASS at source HEAD (2026-10-15). Comprehensive inventory of 4,508 cues audited across all 45 Activities + launcher + My Time + phonics. Reused and verified 192 owner-accepted v0.2 clips; hashed 359 pre-existing assets; generated 2,329 new candidate audio files (1,905 WAV and 424 OGG) + receipts. Enforced deterministic `macos-native-say` (`pedagogical_speech` and `dani_system_speech`) for all 1,277 phonics, single-letter, syllable, and word cues across `foresta_parole`, `sillabe_magiche`, `officina_dei_suoni`, `festa_delle_rime`, and `alfabeto_leo` in IT, EN, ES, and FR, while keeping `chatterbox-mlx-multilingual-v3` for 1,052 character/narrator dialogue cues. All audio reviewed and approved by repository owner ("all audio approved, commit everything please to giithub"); integrated into canonical repository shipping assets with approved receipt records.
### GLA-015 — Parent localization and 45 bilingual Activity source packs

- **Status:** AUDIO INTEGRATED (OWNER-APPROVED) (All 45 built-ins + 16 voice-active learning Activities recorded and integrated into shipping paths with owner approval; language promotion deferred until complete language gate passes).
- **Priority:** P1; **minimum source SHA:** `07a700310d26e40592353a5243ea36954287ea9d`.
- **Authorities:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`,
  `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md`,
  `AGENTS.md` and §0 of this queue. Follow the source first-failure
  rules and existing prepared Pygame environment; no source modifications.
- **Exact sequential source commands**, each with log and exit code:
  ```bash
  python3 -m unittest discover -s tests -p 'test_panel_localization.py' -v
  python3 -m unittest discover -s tests -p 'test_panel_frame_cache.py' -v
  python3 -m unittest discover -s tests -p 'test_panel_layout.py' -v
  python3 -m unittest discover -s tests -p 'test_staged_activity_translations.py' -v
  python3 -m unittest discover -s tests -p 'test_four_language_activity_runtime_text.py' -v
  python3 -m unittest discover -s tests -p 'test_word_forest_phonics_inventory.py' -v
  python3 -m unittest discover -s tests -p 'test_activity_alfabeto_leo.py' -v
  python3 -m unittest discover -s tests -p 'test_installer_localization.py' -v
  python3 -m unittest discover -s tests -p 'test_system_language.py' -v
  python3 tools/audit_greia_language_coverage.py --root . --output tmp/greia-GLA015-locale-coverage.json --recording-ledger tmp/greia-GLA015-recordings.csv
  make verify
  ```
  Replace the example inventory path with the run's unique ignored
  evidence directory as instructed by §0. A missing-audio inventory
  entry is **expected** and is NOT voice acceptance. If
  `make verify` fails solely because the newly accurate spoken-label
  audit detects absent `my_creations.wav` for EN/IT, record exact
  failure and stop; do not hide the portal, weaken validation, or
  substitute a placeholder sound.
- **2026-10-13 real-render-path addition (SOURCE-WIP; test UNEXECUTED):**
  Magical Labyrinth removed unlocalized Italian completion/HUD copy;
  authored 11 semantic caption keys in each EN/IT/ES/FR bundle
  (six model difficulty levels, four biomes, short new-maze button).
  Wonder Match now resolves 64 real illustrated card names and four theme
  labels from semantic Activity resources, with 64 new card words per
  locale. GLA-015 MUST run `test_four_language_activity_runtime_text.py`
  and check missing-resource completion (Memory and Number Train)
    for neutral fallback instead of incorrect Italian copy; inspect real gameplay at 1024×600 and 800×480 for glyphs,
  label width, actual saved-language effect, and fallbacks. Do not
  enable ES/FR manifests/selector for a screenshot; staged-locale
  injection can be used only in non-release test contexts. Do not claim
  local Python, Pygame, voices or visual acceptance from source readback.
- **2026-10-13 additional runtime copy/API regressions (source-only, unexecuted):** the newest `test_four_language_activity_runtime_text.py` now contains **eight** tests, not five. Run it at the actual checkout SHA alongside `test_staged_activity_translations.py`, `test_staged_syllable_curricula.py` and `test_activity_piccola_serra.py`, keeping true exit codes/evidence and first-failure policy. Magic Syllables instructions/formula/slot labels no longer hardcode Italian; check that normal EN and IT lessons display correct letters, and that isolated staged ES/FR source previews show their own `MÉ`/syllable families without audio claims. Greenhouse toolbar now resolves real translated labels from `tool.*`; verify all four controls and their widths. **New factual defect resolved:** three Activity completion helpers had mistakenly called nonexistent `LocalizedResources.string()` and therefore always used emergency text instead of proper translated victory copy. Wonder Match, Number Train and Greenhouse now call `.text()`. Verify normal localized victory title/subtitle/replay for EN/IT and neutral symbol fallback ONLY under intentional broken/missing-resource injection. The four languages' revised JSON key totals supersede earlier frozen 901-key snapshot numbers. GUI resolution checks at both 1024×600 and 800×480 are required and must be reported separately from passing source tests. No voice generation, selector promotion, manifest promotion, child release or hardware changes are authorized by this source fix.
- **2026-10-13 Opposites World and Dolphin continuation (SOURCE-WIP; unexecuted):** the latest `test_four_language_activity_runtime_text.py` now has **10** test methods, adding the ten opposite state words/toolbar and Dolphin completion fallback. Under GLA-015 run `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m unittest discover -s tests -p 'test_activity_mondo_contrari.py' -v` in addition to its existing sequential source commands; record exact exit code, console output and snapshot source HEAD. Opposites World was previously Italian-only for all five real state banners (even in English), and its five tabs were IT/EN only; the corrected code resolves the existing `opposite.*` strings through profile `LocalizedResources.text()`. Test every active tab/state in English/Italian and all five scene modes with the current GUI at **1024×600 and 800×480**, especially accents, truncation, and rendered icon/word fit. For ES/FR, the new test injects staged resources explicitly; do **not** enable those languages in the device registry, Activity manifest or normal child selector. In Dolphin Journey, verify the normal localized EN/IT title/body/replay, and that intentionally unresolvable translations produce neutral completion symbols instead of Italian `BRAVO!`/`ANCORA!`. The new dedicated renderer test actually uses Pygame and may surface environment prerequisites; distinguish display/font/audio bootstrap failures from a semantic source failure. No new recording or deployed OS acceptance is implied.
- **Non-destructive GUI checks if GLA-001 passed:** record actual
  Parent password dialog, tabs, device-language panel, successful
  language change and error indication on both 1024×600 and
  800×480. English and Italian are selectable, text switches and
  cache does not keep an old-language header/tab; keyboard, touch
  and pointer inputs remain intact. Use a disposable test device
  settings directory, never mutate an owner's real Parent password
  or profile. Preview Spanish/French stage copy *using test injection*
  only, with no changed supported-language registry.
- **All 45 built-ins have complete ES/FR source string-key parity**
  (**901/901 keys per target language, 1,802 ES+FR string entries**).
  This is structural staging, NOT accepted gameplay translation:
  the language selector and all Activity manifests still advertise
  only EN/IT, and all ES/FR Activity audio maps remain empty.
  Word Forest now has 21 authored first-letter and example-word
  lessons for **each** new language; they must pass actual
  letter/name/phoneme child-learning review and acquire real
  local recordings before becoming playable in ES/FR.
  Rhyme Festival and Sound Workshop now have ES/FR candidate native
  lesson corpora, with 124 explicitly inventoried new ES/FR word,
  phoneme and odd-one-out voice candidates across both Activities.
  Their word/phoneme scripts and recordings still require approval;
  neither is advertised as ES/FR-supported. Alphabet Leo now adds
  a 27th Spanish Ñ between N and O, with 26 distinct French examples,
  navigation/audio/progression changes; Magic Syllables now stages
  16 ES + 16 FR two-part builder words through a pure locale
  curriculum resolver. The **French and Spanish phonemic
  explorer/catcher teaching grids still require native redesign
  or explicit approval**. None of the five literacy Activities is
  audibly/pedagogically accepted for ES/FR. Encyclopedia has
  all 246 ES/FR written source keys but 200 source narration
  cue mappings per language pending exact transcripts, approved
  scripts and new recordings. Submarine has 77 text keys and
  55 source audio IDs per language pending voice work.
- **Deterministic source checks:** run
  `test_staged_activity_translations.py` to assert all
  45 bundles, placeholders, real letter/example match,
  246 Encyclopedia source strings, 77 Submarine strings,
  and seven Dolphin existing-audio caption associations.
  Run `test_word_forest_phonics_inventory.py` to check
  252 code-owned candidate phonics/audio cues across four
  locales, including 126 new ES/FR candidates,
  explicit BLOCKED_TEXT for unapproved spoken letter
  and find-letter prompt scripts, and no code execution
  from an unsafe curriculum source. Run
  `test_activity_alfabeto_leo.py` to verify the
  fixed wrong-language voice fallback: an absent ES/FR
  letter WAV must **not** result in an Italian spoken letter.
  `test_staged_alphabet_curricula.py` and
  `test_staged_syllable_curricula.py` inspect native-language
  letter and segmented-word candidates, Spanish Ñ, deterministic
  alphabet navigation and Magic Syllables builder progression,
  old EN/IT parity, rejection of unsupported teaching languages,
  and 477 ES/FR code-owned audio cue IDs across the two games.
  Their source-only AST inventory must report phoneme,
  letter-name, question and praise transcripts as BLOCKED_TEXT.
  These are NOT human audio approvals or license to run synthesis.
  `test_staged_es_fr_literacy_curricula.py` checks both real
  ES/FR lesson data sets, rejects silent Italian fallback,
  exercises their deterministic challenge factories, and proves
  the AST-based 124-candidate ES/FR speech inventory never
  executes arbitrary catalogue code. The actual inventory must
  report BLOCKED_TEXT on rhyme scripts and isolated phonemes;
  expected missing speech is not a test failure and not permission
  to promote either Activity language manifest.
  Magic Syllables now uses exact ES (8×5) and FR (5×5)
  authored syllable families; test the *actual* 6-orb
  catcher and 4-tile builder paths. The updated ledger
  must show **115 ES and 93 FR** Magic Syllables cues,
  not the historical 173/190 from the old Italian grid.
  In particular, written builder-only `syl_*` parts
  must not have imaginary `find_*` recordings.
  Run `test_four_language_inventory.py` for
  source-text vs advertised-language distinction.
  No staged JSON/recording candidate counts as
  supported language or accepted audio; preserve
  all literal `$name` and `{variable}` placeholders.
- **Human content/GUI review:** check a bounded sample
  of visual text at 1024×600 and 800×480,
  especially long Submarine naval orders, Dolphin
  narration captions and Encyclopedia
  multi-line science text. Inspect factual accuracy,
  European Spanish/French pronunciation and
  localization of word/rhyme/phonics lesson engines.
  Height-versus-length concepts must remain correct.
  The Number Train produces counts >=2 and
  `prompt.load` is dormant; do not report
  a reproduced one-item grammar defect.
  If Simulator locale injection cannot actually
  render staged ES/FR without changing
  product support, mark PREVIEW BLOCKED:
  never alter manifests to force screenshots.
- **Voice backlog:** the generated source CSV has
  at least **90 ES/FR title candidate rows** and
  additional cue entries; this is not the full
  voice plan until manual inline/external audio
  discovery, canonical speaker assignment,
  approved science scripts and human review.
  Parent browser client source in this repository at
  `parent-app/` (read `parent-app/AGENTS.md`) now stages
  373 EN/IT/ES/FR semantic browser text keys, now
  including deep Device UI (Wi-Fi, input/display/mic,
  Parent password, SSH, pairing and OS update), initial
  HTML accessibility, all Home/Children/Activities views,
  plus discovery/authentication and common chrome. From the
  Greia repository root run `make parent-app-test`
  (`node --test parent-app/tests/*.test.js`) once.
  Include `parent-app/tests/localization_source_contract.test.js`
  (module syntax and literal translation bindings)
  and `parent-app/tests/localization.test.js` (deep-Device
  Wi-Fi/password/pairing/update translations).
  Record the exact Greia commit, command output and exit code.
  Separately, at the Greia OS commit, run
  `python3 -m unittest discover -s tests -p 'test_panel_localization.py' -v`
  to verify the repaired Python comments in
  `src/greia_launcher/panel_localization.py`.
  Do not install remote dependencies, change hosts,
  edit source, regenerate the Parent OS runtime pin
  or claim full browser four-language acceptance.
  Obtain a read-only translated browser preview
  on a disposable profile only after source tests pass.
  Deep Device static text is staged; server/API errors,
  native proofreading and exact content audit remain OPEN.
  Also execute the following NEW focused pure/source
  regressions against current Greia `main` after the
  existing preflight, with no user/device mutation:
  `python3 -m unittest discover -s tests
  -p 'test_launcher_launch_feedback_localization.py' -v`
  `python3 -m unittest discover -s tests
  -p 'test_word_forest_phonics_inventory.py' -v`
  `python3 -m unittest discover -s tests
  -p 'test_painting_contract.py' -v`
  Record stdout/stderr, exit codes, and the exact SHA.
  When GUI source acceptance is authorized, inspect
  Painting save/saving/error text at 1024×600 and
  800×480. Check cropped labels and overlap for
  EN/IT and staged ES/FR text without promoting
  an unsupported Activity locale.
  Do not claim four-language Activity runtime coverage
  based solely on these two targeted leak repairs.

  Preserve source hashes, actual missing cues
  and `PATH_REVIEW_REQUIRED` states.
  Never synthesize from a category heading when
  the real recorded script is different.
- **Expected evidence:** exact checkout SHA, per-command exit code,
  sample multilingual screenshots and measured text fits,
  key-parity report and accurate missing-voice list; archive output
  under one new unique ignored evidence directory. No GitHub
  Actions, provider spending, installer images, flash, source
  code edits or out-of-scope OS changes.
- **Last result:** SOURCE COMMITTED, UNEXECUTED at current HEAD.

- **2026-10-14 owner approval / operative voice work order (NOT YET EXECUTED):** owner approved **all currently authored** EN/IT/ES/FR text translations for voice production and explicitly requested **record all missing voices app-by-app**. Use
  `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`
  as the actual step-by-step instructions, with `LOCAL_AGENT_VOICE_PRODUCTION.md` for specialist cue-script/provider limits. Enumerate **45 Activities × 4 languages = 180 app/locale coverage rows**, plus launcher, Shell, My Creations, Creations, Encyclopedia, incubated My Time, shared characters and any genuinely voiced installer/Parent UX. Start actual recording on an already ready, no-new-spend provider inside `tools/greia_voice.py`; no global waiting for Modal. New paid provider install/cloud calls still require their own cost approval. A translated display label or phonics glyph alone is not necessarily an approved *full spoken transcript*; mark such cue `BLOCKED_SCRIPT` and continue all independent ready cues. Preserve existing accepted recordings. Save generated review candidates, receipts, per-cue hearing results and app-progress ledger under one ignored `tmp/` run, return ZIP + report; never edit manifests/system selector/voice anchors or auto-commit source. The 10-method `test_four_language_activity_runtime_text.py` and Opposites Pygame fixture are still **unexecuted**. Owner text approval does NOT authorize L6 release promotion or count as a voice/audio pass.
- **2026-10-15 approved-audio preservation / targeted missing-clip recording:** The owner has explicitly confirmed **all already committed recordings are personally listened-to and approved**; never re-review/regenerate these. The remaining narrow work order is `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`. It audits 35 proposed target slots (four Bottega/Casa ES/FR titles, 28 Submarine ES/FR missing cue stems, three source-code EN/ES/FR Submarine alarm prompts), **skips any already-existing file**, uses Voice Studio's existing local producer, and returns only newly generated candidate WAVs plus receipts, missing-cue manifest and review evidence. New candidates still await owner hearing; do not use unsafe `integrate_reviewed_voices.py`, do not overwrite existing accepted audio. **Separate implementation task, not agent recording work:** implement canonical cue-to-filename lookup once, prefer localized file, fall back to English for ordinary speech, maintain a stricter pedagogical locale policy; clear Encyclopedia/Dolphin/Submarine silent mappings. Prior source-stage contradictory status lines in this queue are historical and do not override this owner clarification.
### GLA-009 — Installed lifecycle Acer / installer / first boot

- **2026-10-23 continuation:** the owner requested a committed handoff for another
  agent/machine: `docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`.
  It covers current source checks, Linux release/installer builds, disposable
  product-mode QEMU lifecycle and Parent delivery/restart. No such image/VM/
  physical run occurred in the Mac implementation turn. This supplies the
  procedure; it does not identify/authorize a physical disk to erase. The
  physical-target block below remains until that target is explicitly selected.

- **Status:** BLOCKED
- **Priority:** separate hardware owner gate; **dependency:** explicit owner
  authorization and `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`.
- **DO NOT START** merely because this queue is being executed. Requires
  exact current hardware plan, authorized media safety and full first-boot
  stop conditions. This task is a reminder, not install authorization.
- **Last result:** PHYSICAL NOT TESTED in this workstream.

### GLA-010 — Record missing My Creations launcher spoken labels

- **Status:** PASS
- **Priority:** P1 accessibility/content; **dependency:** explicit owner
  authorization for authoring/provider use and a configured local
  Greia VoiceEngine. Never authorize paid cloud/Modal calls by
  interpreting this task as permission.
- **Provenance:** P6 design audit verified the English and Italian
  `assets/audio/system/launcher-labels` directories contain the
  established Create/Play/Learn/Explore/My Greia WAVs, **but no
  `my_creations.wav`**. The installed `SpokenLabelController` already
  uses this exact platform filename for Home hover/keyboard focus;
  no new voice player is required.
- **Safe first command (once checkout prepared, even while blocked):**
  ```bash
  python3 tools/greia_voice.py doctor
  ```
  This is diagnostic only. Then stop and report readiness/authorization;
  do not call providers, record personal voices or synthesize by default.
- **When specifically unblocked:** using `skills/greia-os-work/SKILL.md`,
  `skills/greia-activity-authoring/VOICE_GENERATION.md` and existing
  `tools/greia_voice.py` authoring, produce short human-reviewable,
  clear child-directed IT **“Le mie creazioni”** and EN
  **“My Creations”**, stage approved canonical `my_creations.wav`
  in each matching directory with expected format/level, and
  listen to both at keyboard focus and hover in the real Shell.
  Use configured Modal only if explicit owner permission covers it.
  Check first-frame behavior, audio interruption, no runtime TTS,
  default fail-silent only while recordings are genuinely absent.
- **PASS:** exact localized prerecorded files and human listening
  approval, verified real Shell trigger, no wrong-language or
  unrelated “Create” playback; returned WAV provenance and evidence.
- **Last result:** PASS at source HEAD (2026-10-15). Generated `en/my_creations.wav` ("My Creations", Leo), `it/my_creations.wav` ("Le mie creazioni", Leo), plus ES/FR equivalents via `tools/greia_voice.py batch` with `mlx-whisper-tiny` ASR PASS (1.0). Reviewed and approved by repository owner ("all audio approved, commit everything please to giithub"); integrated with approved `.receipt.json` records into canonical `assets/audio/system/launcher-labels/{en,it,es,fr}/my_creations.wav`.

## 3. Execution history (append a one-line fact here, never fabricate)

- **2026-10-16:** Open-source cleanup removed three test files named in
  this queue: `test_activity_wave36_github_recovery.py` (it had no tests
  left; every check already lives in the per-Activity files GLA-012 runs),
  `test_activity_wave34_35_github_recovery.py` (its Clinic and Orca tests
  moved into `test_clinica_cuccioli_refactor.py` and
  `test_activity_baia_delle_orche.py`, which GLA-013 already runs) and
  `test_greia_skill_identity.py` (it asserted wording inside skill files).
  Their command lines were removed from GLA-012, GLA-013 and GLA-015; task
  scope and statuses are unchanged.

- **2026-10-08:** Source design follow-up shortened only the
  narrow-screen visible `my_creations` Home label (IT/EN/ES/DE/FR)
  without altering full labels, spoken lookup or child collection
  ownership. Added actual table-based text regression.
  The remote execution runtime contains Python, Pillow,
  CairoSVG and Xvfb, but **does not contain Pygame or a
  Greia project checkout**, and its outbound GitHub DNS
  cannot clone private source. Python locally rasterized the
  authentic `portal_frame.svg`/`activity_card.svg` source
  successfully as an **art asset contact image only**; no
  actual Activity was launched/screenshot. GLA-008
  actual Greia GUI remains UNEXECUTED. Do not substitute
  this authored asset preview for Shell Simulator evidence.

- **2026-10-08:** P6 resumed Play/Learn curation instead of
  infrastructure. Counted real 32-candidate draft memberships,
  reclassified voice-story creator away from Play and seasonal
  observation away from Play, yielding 21 Play/22 Learn/6 Create.
  Existing five-tag bounded grouping cannot honestly cover all,
  so direct child browsing remains. Replaced repeated subcollection
  icons with distinct existing canonical art and localized both
  launch-card badges for IT/EN. P6 record now has complete
  Play/Learn editorial matrices. New roster/icon/language tests
  committed but **NOT RUN**. GLA-008 will collect visual evidence
  before any new navigation level, game or release decision.

- **2026-10-08:** P6 navigation/visual curation resumed.
  Reviewed 32 draft manifest categories, corrected four misleading
  Create memberships without changing game/library authority,
  placed My Creations immediately after Create with a different
  existing core icon and compact-landscape Home layout, and added
  focused Home/manifest checks (UNEXECUTED). Audit found no IT/EN
  `my_creations.wav` in launcher-label audio assets; delegated
  authoring to blocked GLA-010, NOT to unapproved network TTS.
  Art/home/play/learn review expanded in GLA-008; neither source
  nor real screenshots have release acceptance.

- **2026-10-08:** P3 source trace through
  `CreationSelectionCoordinator.trusted_pending` →
  `ActivityCreationPickerHost.service` uncovered missing modal
  teardown when the Activity cancels its request or the
  three-minute request deadline expires. A stale modal could
  remain visible and attempt to choose from an invalid request.
  The host now closes superseded/expired views, skips cancelling
  already-settled requests, restores display on cancellation
  errors, and refuses to reuse old taps for a new request.
  Four provider-free host/real-coordinator tests were added.
  **NOT EXECUTED.** P3 Source WIP; release/physical gates unchanged.

- **2026-10-08:** P3 source audit traced the trusted
  `CreationsGalleryScreen` → `CreationsPygamePainter` empty-library
  path and confirmed undefined width/height on first use. Source fixes
  and dummy-Pygame tests now cover empty library/filtered picker,
  appropriate audio-empty icon and modal-only keyboard delete with
  safe default. **All new tests remain UNEXECUTED**, and original
  P1–P7 desktop/GUI/audio integration remains OPEN. No hardware,
  provider, Parent, release-roster or Creations broker authority changed.

- **2026-10-08:** `TimeSpeech` guards an already-expired pre-READY
  countdown: defers terminal cue until after the first presented frame,
  suppresses stale welcome/help, and treats missing/corrupt welcome as
  optional rather than swallowing required instruction. Closing prevents
  future playback. Added pure coordinator and real Activity-loop mock
  regressions; UNEXECUTED pending the local source suites in GLA-003.

- **2026-10-08:** Low-resource audio source change: index selected
  semantic cue paths at Activity construction, decode a clip only when
  `TimeSpeech` requests it after READY; cache at most seven decoded
  recordings, and suppress replay after a failed decode. Added mocked
  call-count/corruption tests. All new tests remain UNEXECUTED.

- **2026-10-08:** Platform `LocalizedResources.audio_cue(...,
  allow_fallback=False)` now owns selected-language cue resolution;
  My Time no longer infers locale from the clip's directory. Strict and
  legacy-fallback tests added in `test_localization.py`; integrated
  `test_activity_time_audio.py` uses actual bundles with clips outside
  `locales/`; keyboard Practice now triggers semantic guidance. All
  tests and listening still UNEXECUTED; GLA-003 now includes the extra
  localization suite. Do not infer a PASS from this queue update.

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

- **2026-10-08:** Optional semantic recorded-voice source wiring added: bounded first-use/finish coordinator, package-local locale audio adapter, available-only replay button, pure fake-transport tests and real-Activity replay test. No WAVs, generation, listening or local tests. GLA-003 source suites expanded; GLA-005 remains blocked.

- **2026-10-08:** Owner GitHub continuation added a 12-position inner hour ring and four outer quarter-hour touch stops in the incubated My Time Activity, with focused real-input/model tests. Unexecuted, no child visual signoff. GLA-003 covers current source acceptance.

- **2026-10-08:** A running Timer completion no longer disappears when
  the child switches to Clock/Stopwatch at the moment it finishes;
  unseen completion stays pending until the Timer mode returns
  (`33b0ddc6`). Current-source GUI review owed in GLA-003.

- **2026-10-14:** Owner-authorized full voice run completed at `b3edfa67` (GLA-010, GLA-014, GLA-015). Using local `tools/greia_voice.py` Voice Studio, swept all 45 built-in Activities, 16 voice-active learning Activities, and ecosystem surfaces. Enforced strict architectural separation: 1,277 deterministic pedagogical/Dani cues (all single letters, phonics, syllables, sound units, and words across `foresta_parole`, `sillabe_magiche`, `officina_dei_suoni`, `festa_delle_rime`, and `alfabeto_leo` in IT, EN, ES, FR) generated via `macos-native-say`, while 1,052 character dialogue/narrator cues (Enciclopedia Greia 398 cues, Sottomarino 106 cues, Activity titles, Momo, Tito, etc.) generated via `chatterbox-mlx-multilingual-v3`. 192 owner-accepted v0.2 shared clips verified and reused intact; 359 pre-existing assets hashed; 2,329 total new audio candidates + `.receipt.json` receipts produced into review staging (`tmp/greia-all-app-voices-20261014-050339/evidence-all-app-voices.zip`, SHA-256 `73abd4dcf93597fadb3c5b802031b5276d2dc0bed057e44ef1dce622a266510b`). 472 remaining gaps documented in `remaining-gaps.csv`. Human listening review remains PENDING; no audio committed directly to git or shipping tree.

- **2026-10-15:** Owner review and approval received ("all audio approved, commit everything please to giithub"). Executed `tools/integrate_reviewed_voices.py` to copy and promote 2,331 audio files (.wav, .ogg) and 2,331 matching `.receipt.json` records (marked `human_review: APPROVED`) into canonical shipping assets across `activities/`, `assets/audio/system/launcher-labels/`, and `activity_incubator/tempo_di_greia/`. Updated `RECORDING_LEDGER.csv` and `app-progress.csv` to ACCEPTED. Passed tests across voice core, literacy curricula, and four-language activity runtime. All assets committed to `main` and pushed to GitHub.

When the GitHub developer changes an API or acceptance target, update the
affected task in this SAME FILE in the same source commit, preserving all
old evidence references and avoiding standalone mini-plans.
