# Greia — Current Engineering Handover

**Purpose:** the short current state for contributors and agents: active workstreams, recent results, blockers and next steps. It is not an archive.
**Public-source readiness:** IN PROGRESS. Root entry points exist (`LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`); the licensing/provenance audit is open (see `NOTICE.md`).
**Ordinary-family release:** NOT READY (`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).

Entries dated before 2026-10-15 were removed from this file in the 2026-10-16 open-source cleanup. Read them with `git show 101e332a:HANDOVER.md`; lessons from that period are indexed in `docs/archive/README.md`.

Add new entries at the top of **Recent entries**, newest first.

## Active workstreams

Blocking and lifecycle authorities (rules in `AGENTS.md`):

- **Architecture remediation**: `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` is the blocking plan for its remaining non-lifecycle obligations.
- **Install, update and release lifecycle**: `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md` (ADR 0036 successor).
- **Cross-hardware robustness**: `docs/plans/2026-09-28_CROSS_HARDWARE_ROBUSTNESS_PLAN.md`, subordinate to the remediation plan; root causes go to `docs/INSTALLATION_ISSUES_LOG.md`.
- **Art and visual system**: `docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md`, resumed through `docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md`; Encyclopedia subplan `docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md`.
- **Parent authentication/runtime acceptance**: the single protocol is `docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md`; production pairing and encrypted transport remain release blockers.
- **Testing route**: `docs/testing/LOCAL_AGENT_START_HERE.md`; local-agent queue `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`.

Scoped owner-authorized workstreams (moved verbatim from `AGENTS.md` on 2026-10-16):

**Current owner-authorized Activity release + Creations workstream:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` is the **single unified product/content implementation plan** for the typed child Creations Library, universal pre-reader picker/viewer, adaptable disk budget, Painting/Shape Garden/Theatre/voice/text interoperability, complete built-in Activity quality audit, and deliberate catalogue selection. Continue from `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PROGRESS.md` and append accurate session results. This owner-requested scoped program coordinates those features but **does not supersede** the architectural-remediation and release-install/first-boot lifecycle authorities above; those still govern safety prerequisites, image installation, update, rollback and hardware acceptance. Product/source work may proceed in parallel without making hardware claims. Do not spin up a second competing catalogue, picker, or creative-media plan.

**Owner-authorized localization workstream (2026-10-12):**
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md` is the
scoped implementation plan for reducing misleading language choices,
completing EN/IT gaps, and extending real installer/OS/Parent/Activity
text and voice support to ES/FR. Its standing local-agent speech design and cue-source authority is
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md`.
**Current executable voice-production work order:** `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`
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

## Recent entries

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
