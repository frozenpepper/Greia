# Greia Creations + Activity Release — Progress / Resume Ledger

**Status:** ACTIVE, source-first. No first-party release approval implied.  
**Master plan:** [PLAN.md](./PLAN.md)  
**Run this ledger with:** `AGENTS.md` + `HANDOVER.md` + current `main`.

## A. At-a-glance checkpoint — 2026-10-07

- Program: **P1/P2 source WIP**; **P3 universal gallery + authenticated request transport + trusted in-Activity modal SOURCE-WIP**; **P4 image round-trip SOURCE-WIP across Painting, Shape Garden and Teatrino**; **P5 WAV interoperability SOURCE-WIP from Storie della Mia Voce into Teatrino**. Legacy-X and Simulator modal backends are implemented in source, but no complete checkout/GUI acceptance has run. Wayland/KMSDRM, UTF-8, second audio consumer and later release phases remain open.
- First-party `activities/` snapshot: **45** directories = **44 child-content Activities + 1 My Greia/settings Activity**. The earlier catalogue strategy's 41-item figures are historical.
- Catalogue handoff: four October 1 action/strategy games added. **Colline Allegre script entrypoint broken** via relative imports in top-level `colline_app.py`/related modules; **Quattro Amici** manifest declares D1–D5 but its model config has D1–D4. These are **source inspection findings**, not claims that a fresh production launch test ran.
- Release composition: still source-tree driven; explicit release allowlist/manifest **not implemented**.
- Exchange status: **Painting, Shape Garden and Teatrino declare the PNG directions they use, and Voice Stories→Teatrino now adds the first real WAV route.** Storie della Mia Voce publishes only already-saved private scene WAVs with role `narration`; the universal picker already supports child-controlled Play/Pause/Resume/Replay before selection. Teatrino requests only narration WAVs, validates/canonicalizes them, and can puppeteer to imported narration without starting the microphone; early Stop trims the imported WAV and the saved show owns its independent private copy. **No real cross-app GUI/audio flow has been executed yet**; UTF-8, second audio consumer, backup and physical evidence remain open.
- OS first-boot/installer: independently **OPEN** on the Acer route; read existing lifecycle plan before any hardware action.
- Historical P1 baseline: `creation_capacity.py`, `creation_media.py`, `creations.py`, `test_creation_library.py`, local mirrored **12/12 PASS**. P2/P3/P4 subsequent source commits supersede the original 'no broker/UI' snapshot; a complete checkout acceptance remains owed.

## B. Phase delivery status

| Phase | Scope | Current state | Release evidence still owed |
|---|---|---|---|
| P0 | repository/source baseline + triage | STARTED | consolidated current-head actual gameplay audit |
| P1 | typed creation repository, codecs, adaptive capacity | SOURCE WIP (trusted core committed; 12 local mirrored tests PASS) | full Greia checkout tests, error/race/recovery, real budget calibration |
| P2 | permissions/manifest/broker/SDK | SOURCE WIP (publisher/importer + nonblocking request/poll/cancel and real socket tests committed) | full checkout socket/manifest/supervisor tests; presenter-enabled positive and default-fail-closed negative |
| P3 | universal picker and My Creations viewer | SOURCE WIP (viewer + filtered picker + authenticated async transaction + Legacy-X/Simulator trusted modal backends) | full checkout tests; real Simulator remote-canvas screenshots/input/audio/cancel/Home; installed Legacy-X focus/stacking; future Wayland/KMSDRM backend |
| P4 | Painting–Shape Garden–Theatre PNG round trip | SOURCE WIP (Painting independent import; Shape Garden persistent shape+backdrop project + flattened export; Teatrino persistent custom show backdrops) | full checkout tests; real GUI round trip/reopen/source-delete independence; resource/performance evidence |
| P5 | voice/music and writing/text interoperability | SOURCE WIP (Voice Stories durable WAV publication + preview-capable universal picker + Teatrino narration consumer without mic contention) | full checkout/audio tests; real audible preview-before-select; saved-show replay after shared source deletion; second audio consumer; UTF-8 producer/consumer |
| P6 | explicit release catalogue and adaptive grouping | NOT STARTED | built-index exact match, Parent policy |
| P7 | deep per-Activity quality review (45) | NOT STARTED | 45 evidence-backed dispositions |
| P8 | end-to-end release and physical acceptance | NOT STARTED | real Acer and cross-platform acceptance |

### Activity release-review coverage

**45/45 entries inventoried in PLAN §5; 0/45 release-reviewed, 0 release-approved.**

No new Activity is dropped or silently approved merely for having unit tests. Record each review and disposition with evidence under §C entries. Historical R7.3 structural migration PASS does not equal release UX PASS.

### Media interoperability state

| Producer | Consumer | Kind | Status |
|---|---|---|---|
| Painting | Painting | PNG published snapshot becomes a separate editable private painting | SOURCE WIP: child-visible publish/import controls + modal transport wired; untested live |
| Painting | Shape Garden/stamps | PNG as background/base | SOURCE WIP: trusted PNG picker → private content-addressed backdrop + bounded durable shapes |
| Shape Garden | Painting | flattened PNG composition | SOURCE WIP: explicit trusted publish of deterministic flattened `composition` PNG |
| Painting/Shape Garden | Teatrino Fiabe | PNG backdrop | SOURCE WIP: trusted PNG picker + show-local content-addressed private backdrop snapshot |
| Storie della Mia Voce | Teatrino | WAV narration | SOURCE WIP: durable saved-scene publish → audio preview → narration-only picker → private saved-show copy; imported track replaces mic source for that performance |
| Writing | Writing / genuinely compatible text consumers | UTF-8 | NOT STARTED |
| Any declared writer | My Creations viewer | large visual/audio/text previews | SOURCE WIP: Shell gallery |
| My Creations viewer | library | safe deletion/reclaim | SOURCE WIP: two-stage confirmation |

## C. Append-only dated progress entries

### 2026-10-07 — Owner-approved unified program and P1 local headless source prototype

**Starting repository head:** `56f22131c60a7fb06ff2dbbe97cdd03aca4165a3` before documentation commits.  
**Documentation delivered:** `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md`; this progress ledger and AGENTS/HANDOVER routing updates are part of the same session.

**Owner requirements accepted:** universal non-reader picker with big thumbnails; playable audio previews *before* choosing; universal viewer with deletion; Painting/Shape Garden/Painting and Theatre media roundtrips; audio/text reuse; scalable storage roughly 75% of actual **writable** persistent volume with floor; holistic 45-Activity release-review and source/visual/performance/test program.

**Local isolated implementation/test environment:** Python with Pillow and SQLite available, but **not** an authenticated full Greia checkout; Pygame is unavailable, no real Greia GUI/Simulator installed. Local package/unit slices may be tested, but there is **no claim** of passing Greia `make verify`, real launcher Pygame tests, screenshots, or target-hardware runs.

**Headless code prototypes prepared:**
- `src/greia_platform/creation_capacity.py` — `VolumeUsage`, 75% occupancy policy + 512 MiB floor, injectible probe.
- `src/greia_platform/creation_media.py` — registered format codecs, bounded canonical PNG/WAV/UTF-8 normalization, PNG thumbnail, audio-playable payload preview.
- `src/greia_platform/creations.py` — one-profile trusted `CreationLibrary` repository with SQLite descriptors, immutable snapshots, typed paging/reads/previews/deletes and integrity checks.
- `tests/test_creation_library.py` — 10 focused tests covering 8-GiB/6-GiB policy example, small volume, PNG thumbnail, playable WAV, UTF-8, isolation between distinct roots, unsupported media, immutability, deletion, capacity refusal and symlink roots.

**Executed local test command:** `PYTHONPATH=src python -Werror::ResourceWarning -m unittest discover -s tests -p test_creation_library.py -v` → **10 tests PASS**, isolated local source, before repository integration. `python -m compileall -q src tests` → PASS. Source implementation may be committed to main separately below; update this entry with actual commit SHA once landed. Do not count these as integrated runtime tests.

**Important incomplete details:** no broker or manifest integration, no per-Activity permissions, no picker/viewer, no USB/backup link, no crash-orphan sweeper/SQLite migration beyond schema v1, no global guard on *other* data writers, and no actual image/audio/text producer/consumer modified. This initial tranche proves feasibility only. Hardware and GUI tests are not requested yet.

**Next exact implementation step:** complete and review P1 in the canonical repo and tests, then P2 supervisor-broker identity and child-confirmed read-handle design. Do not ship `CreationLibrary` as a sandbox-mount or Activity API merely because its repository tests pass.

### 2026-10-07 — P1 core committed; release-triage source repairs committed (same session)

**Canonical source commits (in order):**

- `c829825a` — volume-relative capacity policy.
- `f41b4d2e` — PNG/WAV/UTF-8 codecs with previews.
- `c27a6ce6` — profile-owned immutable creation repository.
- `f278cbaa` — ten initial repository tests.
- `43d41532` — safe SQLite rollback guarding.
- `bc28fc55` — corruption/symlink regressions; local mirrored suite now **12/12 PASS**.

**Additional release triage (NOT full release acceptance):**

- Colline main, model and renderer now all recognize both imported-package and direct Greia script-launch import contexts; eliminated `auto_upright=false if False else False` dead expression. Commits `02b8f2e4`, `1c8a45ee`, `faabb503`, `82ff2d23`; an intermediate model fix `ee917b42` was immediately corrected in `1c8a45ee`.
- New `tests/test_activity_colline_allegre.py` regression checks the real script import context (`runpy.run_path` without executing the frame loop). Commit `93bf54e1`.
- Quattro Amici `difficulty_max` was reduced from five to **four** to agree with actual four `LEVEL_CONFIGS`; added manifest-vs-model range test. Commits `7c444493`, `35cb977f`.
- These game tests were **not executed** in this isolated environment because it lacks the actual Greia repo and Pygame; neither gameplay nor target hardware is claimed verified. Run them in a full local checkout before promoting the source.

**Accepted requirements persisted:** `docs/product/CHILD_CREATIONS_LIBRARY_AND_MEDIA_INTEROPERABILITY.md`; the single program/ledger pointer is in `AGENTS.md`, the documentation map, and both relevant skills.

**Local evidence:** recreated source under `/mnt/data/greia_session` with Python + Pillow + SQLite; `PYTHONPATH=src python -Werror::ResourceWarning -m unittest discover -s tests -p test_creation_library.py -v` → **12/12 PASS**, `python -m compileall -q src tests` → PASS. This is **isolated source testing**, not execution against the authenticated checkout, full `make verify`, GUI screenshots, or physical Acer.

**Known P1 debt before public SDK:** commit-level integration test; strict producer authorization and child-confirmed scoped read-handle via P2; safe crash-orphan recovery / SQLite schema migration; directory ownership inherited from actual active ProfileContext; validate persistent partition reserve with real build geometry; global budget enforcement on all other child-data writers; album/cursor pagination under large collections; backup/restore. All remain OPEN.

**Next exact step:** execute P1 focused tests and new Colline/Quattro script/manifest regressions in a complete Greia checkout, fix any source failure there, then begin P2 trusted session broker/manifest design and implementation.

---

### 2026-10-07 — P2 source implementation: manifest, supervisor, broker, SDK (same-day continuation)

**Source boundary:** current `main`; P2 is **SOURCE WIP / GUI-UNPROVEN / INSTALLER-UNPROVEN**, not a user-facing library.

- Manifest and installed-index metadata: `src/greia_platform/activities.py` validates optional `[creations]` produced/consumed types against explicit PNG/WAV/UTF-8 codecs; `activity_index.py` carries the declarations through the deterministic built-in-index serializer/loader. Undeclared older Activities still opt out. Commits `e59736b9`, `2ba77eb0`.
- Trusted `CreationSessionAccess` (`src/greia_platform/creation_access.py`) binds issued `ActivityAuthority`, same-Activity private storage and a profile-owned `CreationLibrary`. An Activity can publish its **own private file** only if its manifest declares that media type. Import requires a **one-use expiring opaque handle** minted from a selected item by the trusted UI owner, not an Activity method exposed over the socket. No gallery enumeration, delete, grant minting or arbitrary read operation exists in the Activity broker. Commits `99db50c0`, `1e8bacaf`, `2ef428fa`.
- Existing session socket extended with exactly `creations.publish_private` and `creations.import_selected`; broker binds authority **once before launch** and clears handles on stop. `CreationLibrary` lives under `ProfileContext.creations_dir`, not in an Activity mount; the profile's group access remains available for future trusted backup. `ActivitySupervisor` provisions it only if declarations exist. The production broker start signature was preserved, and a failure after broker startup now cleans the socket/thread. Commits `f94b541e`, `5c9e0d82`, `c4676185`, `55557422`, `5a362a3e`, `1fd14a90`, `a28e6be5`, `b8d3007d`.
- New narrow `creation_client.py` + `activity_api.get_creations()` and guarded `ActivityStorageClient.creation_exchange()`. Direct standalone development has **no unsafe shared-folder fallback**. Commits `c4f15453`, `c0e53230`, `e119b745`, `8588b656`.
- New regressions: `tests/test_creation_broker.py` uses real Unix-socket publish/import plus negative enumeration/forgery checks; `tests/test_creation_manifest.py` checks old-manifest compatibility and built-in-index round trip. Commits `7050968a`, `e991706b`, `4aeb1aaf`.

**Executed environment evidence:** only the isolated local Python/Pillow/SQLite mirror of `creation_capacity.py`, `creation_media.py`, `creations.py` and `creation_access.py` was run, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -Werror::ResourceWarning -m unittest discover -s tests -p 'test_creation_*.py' -v` → **18/18 PASS** and isolated AST parse `4/4` PASS. This is **NOT the complete Greia checkout**. Newly committed **broker socket (3 tests)** and **manifest/index (4 tests)** suites, full `make verify`, integration/Simulator/Pygame, screenshots and real hardware have **NOT** run; do not promote source to accepted until that happens.

**Current blockers/risk:** no Activity claims `[creations]` yet; the universal large-thumbnail/audio-preview trusted picker cannot mint handles for a child, so no production child sharing path is live. Profile backup/restore, recovery after interrupted SQLite/blob operations, media quota pressure, and enforcing adaptive disk headroom on **all** writers remain open. The published metadata includes no hidden cross-profile sharing. Source code still needs complete-checkout tests and architecture/performance review before an installed image.

**Next exact step:** run the seven newly committed broker/manifest tests plus 18 media/access tests and existing supervisor/storage/index suites in a complete Greia checkout; repair any failures at real owners. Then develop P3 trusted picker/viewer UI and visual screenshot acceptance, with first Painting↔Shape Garden↔Theatre PNG vertical slice. No destructive USB/Acer test requested in this source-only session.

---


**Additional P2 hardening:** `3c6a4a7b` makes the PNG codec report a typed media-unavailable error if Pillow is absent rather than failing during exception handling. The same isolated 18-test Python/Pillow/SQLite suite was rerun **18/18 PASS** against the amended local mirror; full repository/broker/index tests remain owed.

### 2026-10-07 — P3 visual-gallery source and Painting→Creations producer (session continuation)

**Pinned SOURCE candidate:** `d63b9f530e684819e80e9e5a271c13bd953cc001` — includes the final illustrated-empty-state polish, explicit empty-picker-media fail-closed fix (`89074d19`) and regression (`6595621a`). The earlier `ca9dc87d` audio-test commit remains an ancestor. Follow-on test/progress documentation commits are documentation-only. **No Acer/installer/source-acceptance promotion implied.**

**Source delivered:**

1. **Universal platform state owner**: `creation_gallery.py` implements one bounded controller for `LIBRARY` and `PICKER`, indexed mixed-media filters, two/three huge cards per page, detail/open/zoom, audio Play/Pause/Resume/Replay, on-demand audio only after Play, cancellation/focus, one-use trusted selection callback, and viewer-only two-stage explicit deletion. `creations.py` added bounded SQL multi-type indexed filtering, avoiding unbounded Python-wide gallery enumeration. Source commits include `ac90d958`, `f21b2830`, `9d71ada5`, `de5fac95`, `bdf07253`, `c77cf6ce`.
2. **Shared renderer-neutral responsive geometry + Pygame view**: `creation_gallery_layout.py`, `creation_gallery_painter.py`, `creation_gallery_screen.py`. At 1024×600 target two very large visual cards, real image pixel-data previews, original PNG when expanded, large audio Play/Pause/Replay/progress UI, illustrated text and bounded text excerpt, safe delete confirmation/cancel, IT/EN labels, keyboard/pointer focus and Greia chrome-safe title region. Resolutions in pure geometry tests: 480×320, 640×360, 800×480, 1024×600, 1280×720, 1366×768, 1920×1080. **Real Pygame screenshots and full input proof pending.**
3. **Audio owner**: `creation_audio_pygame.py` owns an interruptible on-demand SDL mixer channel; genuine Pause/Resume/Replay rather than Play/Stop masquerading as Pause, bounded WAV input, frozen progress on pause and teardown on gallery exit. Repaint is requested only while audio actually runs; idle doesn't animate. Relevant commits `83a6a336`, `5c205a24`, `6e78b145`, `e0c66967`, `7a868da0`. Mock mixer regression `test_creation_audio_pygame.py` committed at `ca9dc87d`.
4. **Trusted Home entry**: `catalogue_view.py` gained a localized `my_creations` label/semantic palette icon. `GreiaChildShell` adds a dedicated My Creations Home portal and trusted gallery mode without making it a fake Activity/manifest. It uses the active profile's managed library, closes playback on profile logout/change and returns to Home; `presentation.py` integrates paced audio-progress repaint. Commits include `0f0c6a93`, `0ece3e64`, `a1547d47`, `03cadab6`.
5. **Painting becomes first declared producer**: `activities/painting/activity.toml` declares `[creations] produces = ["image/png"]`; `painting_model.py` validates private PNG names; `painting_app.py` adds a child-visible deliberate share-to-Creations action, saves private draft first, publishes via trusted broker, and avoids repeated identical snapshot publication in the same session; `painting_renderer.py` draws a safe central share icon only in paint mode; `painting/main.py` wires guarded SDK, with no unsafe standalone shared-folder fallback. `tests/test_painting_creations.py` committed but only runnable in Pygame-capable full checkout. Relevant commits `861935a4`, `f318557b`, `7642856d`, `041847d9`, `d95a7914`, `0ccc4478`, `088ff48d`.
6. **Source regressions**: `test_creation_gallery.py` (paging beyond 64, arbitrary-ID denial, no autoplay, click-to-play, paused state, replay, pick-only handle, delete confirmation), `test_creation_gallery_layout.py` (7 screen sizes), `test_creation_audio_pygame.py` (fake mixer clock/freezing, device failure), `test_painting_creations.py` (pure publication object without display).

**Executed evidence:** in this assistant's restricted Python container, Pygame is **not installed**, and a disposable pip attempt failed due to blocked DNS/network. It does not have the authenticated Greia checkout or running Simulator. A local isolated **mirror** of the creation repository/access/controller/geometry and the audio owner/mock tests ran:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/data/greia_session/src \\
  python -Werror::ResourceWarning -m unittest discover \\
  -s /mnt/data/greia_session/tests -p 'test_creation_*.py' -q
# 33 tests PASS (isolated source mirror, NOT canonical repository)
```

This **does not** test the complete Greia `main` checkout, Pygame drawing, launcher MRO, actual audio hardware, actual Unix-socket test suite, built-in image index or full `make verify`. Never promote this to SIMULATOR or PHYSICAL PASS. `tests/test_painting_creations.py`, broker/manifest and full-source suites **are unexecuted** here.

**Architectural finding blocking in-Activity picker activation:** `LauncherApplication._launch_selected` synchronously waits in a supervisor poll loop while the Activity owns the display. Drawing the same `CreationsGalleryScreen` in normal Shell Home does not bring a trusted picker over a running Activity. The master PLAN P3 now requires one proper Activity request → supervisor → trusted display/picker handoff → same-session child-selected token response. Do not bolt a custom raw chooser into Painting/Shape Garden or silently call the Home renderer behind an Activity.

**Next exact acceptance procedure (NO hardware, pinned to `d63b9f53`):** [docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md](../../testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md). On an actual complete checkout: test all focused creation suites, Painting, index, supervisor, profile and `make verify`; inspect real Simulator screenshots at 1024×600, 800×480 and 1366×768. Stop on first failure and report evidence. No Acer image flash/install.

**Next implementation step after source/GUI evidence:** fix real source/UX regressions, then design/implement P3 trusted Activity-picker session mediation; connect Painting shared-import and Shape Garden/Theatre in P4. Audio/text production and backup / adaptive budget for ALL writers still pending. Catalogue review 0/45 accepted.

---

### 2026-10-07 — P3 async request transport, Painting PNG receiver, no live tests (current source continuation)

**Source candidate for next combined desktop acceptance:** `1904e74921b62b78181f45206f394a6b6bf40dd6`; newer commits in this ledger/PLAN/test contract are documentation only. **No current-turn tests were run** because a complete authenticated local checkout/GUI environment is not available in the assistant container and the user's local agent is unavailable. The previous session's isolated 33/33 mirror run remains historical, not evidence for this new candidate.

**Implemented and committed directly to `main`:**

- `src/greia_launcher/creation_selection.py`: one active per-session `SelectionRequest` with opaque ID, MIME-type subset and optional role scopes, short non-blocking polls, request cancellation, absolute request expiry, bounded retention of uncollected terminal results, session close, and trusted-only grant completion. A new **presenter-availability gate defaults OFF**: the broker immediately rejects any Activity request until a real trusted display backend is ready (no silent 180-second wait with invisible UI). Relevant commits `d2811594`, `17545946`, `9c8daafb`, `ced2d7ae`.
- `src/greia_launcher/storage_broker.py`, `src/greia_platform/storage_client.py`, `src/greia_platform/creation_client.py`: exactly `creations.request_selection`, `creations.poll_selection`, `creations.cancel_selection` alongside existing publish/private and import/handle; no library listing, arbitrary-ID read/delete, chosen-item grant or frontend-enable action on the Activity socket. Only trusted host code may call `enable_creation_picker()`, `pending_creation_selection()`, `complete_creation_selection()`, `cancel_creation_selection()`. `ActivitySupervisor` delegates these through the **currently RUNNING** session's owned broker, never an inactive/stale Activity. Relevant commits `a0e16b3d`, `67a30412`, `20f27ee4`, `64fc91f7`, `4d0e46f6`.
- `CreationSessionAccess.grant_child_selection` now also enforces request-time MIME/role scopes; selected bytes still require the same one-use session-specific handle. `CreationLibrary.list` has bounded parameterized SQL role+type filters with indexes; shared picker Screen/controller applies identical filters so a child isn't shown irrelevant files. Relevant commits `d5791f08`, `de52e3e4`, `2e10f7b1`, `18b88f6b`.
- `activities/painting/painting_app.py` added `accept_selected_png(handle)`: validate MIME+digest, decode before write, create a **new private editable** project without modifying the shared original or existing canvas on failure. Painting manifest declares both PNG `produces` and `consumes`. It is **not wired to an Activity-visible picker yet**, because display mediation remains unimplemented; no false UI affordance was added. Commits `6f8e7115`, `c83064aa`.
- Source regression additions `tests/test_creation_selection.py` (validation, scope denial, replay/forgery, uncollected expiry, lifecycle cancellation, absent display), `tests/test_creation_broker.py` (real socket request/resolve/one-use imported copy; no unauthorized enable via socket), `tests/test_creation_gallery.py` (role-scoped view), `tests/test_painting_creations.py` (independent saved copy, invalid integrity retains original). **All newly added tests are UNEXECUTED in canonical checkout.**

**Architecture correction:** Actual `shape_garden` source is a transient animated shape-growing environment with **no persistent editable artwork/project repository**. It is not a ready-made stamp editor, contrary to earlier shorthand. A proper project model or an evidence-backed alternative Activity selection must precede claims of painting→stamps→painting interoperability. See [P3 display contract](./P3_TRUSTED_PICKER_DISPLAY_CONTRACT.md).

**Entire deferred test set is preserved and expanded**, including all previous source/UI screenshot checks, at [P3 desktop/source acceptance](../../testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md). The user expressly deferred the run until their local agent is available. **Do not ask for Acer flashing**, do not claim live GUI, socket, full-checkout or physical PASS. When the agent is available, test the latest pinned source candidate with `make verify`, real Pygame Simulator screenshots and the listed privacy/rollback/performance negatives; report first failure with evidence.

**Next engineering step:** implement actual trusted display-owned modal presentation/focus bridge through existing `DisplaySessionCoordinator`/system chrome backend behind one runtime-neutral contract; only then may the Shell enable a pending Activity's picker. After that connect real user-facing Painting import + separate Shape Garden saved project + Theatre backdrop, then WAV/text, all-writer proportional disk limit and curated 45-Activity release review.

---

### 2026-10-07 — P3 trusted modal source + Painting live import wiring; all execution deferred

**Pinned source/test candidate for the next combined acceptance:** `dae96e9b63bb537456579fa51ad1d9539cf0c204`. Commits after that SHA in this session are documentation-only. **No tests were executed for this candidate**: the user's local agent remains unavailable, and the assistant environment still lacks the complete authenticated Greia checkout/Pygame runtime. The earlier isolated 33/33 mirror result predates this modal source and is not current evidence.

**Implemented directly on `main`:**

- **Runtime-neutral trusted modal lease:** `ShellActivityModalLease` now carries only exact session ID, generation and supervised Activity PID. X11/native surface handles are private backend state, preventing Legacy-X assumptions from leaking into Wayland/KMSDRM/Simulator contracts.
- **Legacy-X modal backend:** `LegacyXShellWindowController` reuses Greia's existing Shell SDL window. It enables presenter capability for the live Activity session, then immediately before modal presentation re-reads the currently focused non-Shell X11 window's `_NET_WM_PID` and requires an exact match with the supervised Activity process. It raises/focuses the Shell, keeps the verified Activity window private for restoration, and restores that exact window afterward. It revalidates again at show time so an SDL window recreated after READY is not restored from stale state.
- **Trusted Home/Back preservation:** `SystemChromeBackend/SystemChromeCoordinator` gained a narrow `ensure_visible` restack operation. Legacy-X re-raises/redraws its already-prepared protected chrome after the full-screen Shell modal rises; `TrustedChromeActivitySupervisor.ensure_system_chrome_visible` is exact-running-session bound. The modal never becomes higher trust than Home.
- **Trusted host:** new `creation_picker_host.py` binds the active profile's managed `creations_dir`, pending request scopes and the shared `CreationsGalleryScreen`. It drops pre-modal input, draws only on opening/input/audio progress, completes selection only through Supervisor, restores Activity immediately on choose/cancel, and now performs unconditional abnormal cleanup: cancel pending request, disable presenter gate, stop Screen/audio, dismiss/abandon modal lease and clear Shell events.
- **Launcher lifecycle integration:** `LauncherApplication._launch_selected()` creates the host only for `creations.consumes` Activities, prepares the concrete modal backend after RUNNING, services the real picker inside the existing supervisor loop while Activity stays alive, and wraps the host in `finally` so unexpected unwind/Simulator stop cannot strand modal authority.
- **Simulator canonical modal:** new `greia_simulator.shell_window.SimulatorShellWindowController` uses the existing `SimulatorSystemChromeRemoteBridge`, not a fake picker. While modal is active the Activity's `/api/events` drain receives no ordinary input, Shell consumes that same queued input, Activity frame uploads cannot replace the trusted picker frame, and protected Home remains system-owned. `GreiaSimulatorChildShell` composes this backend and the launch loop calls existing input hooks only while the picker is visible.
- **Painting child-visible import:** its private gallery now shows the shared picture-arrow-down affordance. It requests only `image/png`, polls no faster than every **120 ms**, handles cancel/unavailable state without blocking frames, consumes one ready selection handle, validates MIME + digest, decodes before state mutation, creates a new independent private editable project and leaves the shared source unchanged. Existing up-arrow publish and private autosave semantics remain separate.
- **Regression source added/expanded (UNEXECUTED):** `test_shell_window_legacy_x.py` exact-object/PID/recreated-window restoration; `test_system_chrome.py` restack same lease; `test_trusted_chrome_supervisor.py` running-session restack; `test_simulator_system_chrome.py` modal input/frame diversion and Home; `test_creation_picker_host.py` open/select/cancel/show failure/chrome failure/abnormal teardown; `test_painting_creations.py` explicit request, duplicate suppression, bounded polling, cancel, unavailable presenter and one-use import.

**Architecture/evidence boundary:** this advances P3 from “request transport only” to **modal implementation SOURCE-WIP**. It does **not** prove that Legacy-X `_NET_WM_PID`/stacking behaves correctly on the installed Acer, that the Simulator remote canvas visually presents/restores correctly, that Pygame input or audio is correct, or that the full source suite typechecks/passes. Future Wayland/KMSDRM backends still need the same `ShellWindowController` semantic implementation.

**Deferred acceptance owner:** [`docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md`](../../testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md) is being advanced to this exact source SHA. When the local agent returns, run that **single accumulated procedure**; do not discard earlier Gallery, broker, security, Painting publication, resolution or visual checks. No Acer flash/install is requested by this workstream.

**Next source step while testing is deferred:** start P4's next legitimate consumer: define Shape Garden's persistent editable picture+shape project model (or formally choose a better stamp-style Activity after gameplay review), then wire the already-common picker rather than adding another chooser. Theatre backdrop persistence follows. In parallel, P5 WAV/text and P1 all-writer proportional capacity remain open; catalogue review is still 0/45 accepted.

---

### 2026-10-07 — P4 Shape Garden + Teatrino PNG interoperability source; execution still deferred

**Pinned code/test candidate for the next accumulated desktop acceptance:** `60832f87e2ff432ccadb1189ba1cb726cb2e1394`. Documentation commits after this checkpoint only describe the candidate. **No tests were executed for this candidate**: the owner explicitly asked to carry this turn's tests into the next slice while the local agent is unavailable. Historical mirror/unit results do not validate this code.

**Shape Garden implementation (SOURCE-WIP):**

- Kept the existing child experience: tapping still grows randomized colored shapes in the garden; it was not turned into a desktop-style editor.
- Added a pure bounded persistent project model: only durable shape geometry/color and optional backdrop digest are serialized; spark particles, reaction timers and grow-in animation state remain transient.
- Added profile-private repository ownership with a content-addressed imported PNG backdrop, integrity verification, bounded orphan cleanup and one replace-in-place export staging file. Project metadata commits only after backdrop bytes are safe; failed metadata writes preserve the previous committed project.
- Added child-visible nonblocking PNG import through the **same trusted universal picker**. One-use transfer is MIME+SHA256 checked and decoded before the current project mutates. Cancel/integrity failure preserves current work.
- Added explicit flattened PNG publication with role `composition`; transient sparkles are excluded from the deterministic snapshot. Re-publishing an unchanged in-session snapshot is deduplicated.
- Added bounded autosave of shape edits and exit save. Blank projects retain the original Greia garden backdrop; an imported Painting replaces only the upper visual backdrop while soil and grown shapes remain Shape Garden-owned.
- New deferred regressions: `test_shape_garden_project.py`, `test_shape_garden_creations.py`.

**Teatrino implementation (SOURCE-WIP):**

- Added PNG consumption through the same nonblocking trusted picker; importing is disabled while actively recording and cancel/failure preserves the current stage.
- A custom Painting/Shape-Garden picture becomes the stage backdrop without replacing built-in scene assets; choosing a built-in scene explicitly returns to built-in scenery.
- Saved shows keep an **independent private backdrop snapshot**. Backdrops are content-addressed and deduplicated across the 16-show library, so many stories using one picture store one PNG rather than N copies.
- Reference-aware cleanup removes a backdrop only after the last saved show stops referencing it; dropped-over-cap and deleted show JSON/WAV files are reclaimed.
- Existing silent-save-loss behavior was tightened: with real Greia storage present, an unreadable catalogue refuses save/delete rather than treating it as empty; failed file/index commits roll back unique new files and raise `ShowStorageError`. The app shows a localized failure and emits no `story.recorded` event/applause unless the repository actually committed. No-storage development mode retains the bounded in-memory fallback.
- New deferred regressions: `test_teatrino_shared_backdrop_repository.py`, `test_teatrino_shared_backdrop.py`, plus existing `test_activity_teatrino_fiabe.py`.

**Shared/P3 refinements:**

- Added `greia_platform.pygame_png` as the common Pygame/Pillow conversion seam; source payload bytes, source side length/pixel count, target dimensions and encoded output bytes are bounded before expensive conversion. Painting can migrate fully onto the helper in a later small refactor; Shape Garden and Teatrino already use it.
- The trusted picker host now pre-renders and flips the first picker frame **before** raising the hidden Shell, preventing an old Home framebuffer flash on Legacy-X. The normal post-show launcher frame/capture remains authoritative for Simulator remote display.
- Added deferred `test_pygame_png.py` and expanded picker-host regression source.

**Evidence boundary:** all new Shape Garden, Teatrino, PNG-boundary and first-frame tests are **UNEXECUTED**. No complete checkout, `make verify`, real Pygame, Simulator screenshot, microphone/audio, native Legacy-X or hardware evidence was produced. P4 remains SOURCE-WIP, not accepted.

**Single deferred acceptance owner:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` now carries the earlier P1–P3 checks **plus** P4 Shape Garden/Teatrino source and GUI round trips. Do not flash/rebuild/reboot the Acer for this workstream.

**Next source work while execution is deferred:** proceed to P5's genuine WAV/text producers/consumers and P1 all-writer proportional-capacity enforcement, while keeping the 45-Activity release review separate and still 0/45 accepted.

---

### 2026-10-07 — P5 first WAV route: durable Voice Stories narration → Teatrino performance; execution deferred

**Pinned latest source/test candidate for the next accumulated desktop acceptance:** `cb9bc32c680ddd3953d256b8bc0c4311e194bfad`. Later documentation commits only update acceptance/state. **No tests were executed for this candidate** because the owner asked that all current testing be carried to the next slice while their local agent is unavailable.

**Producer — Storie della Mia Voce:**

- Existing private story storage was reviewed before use. A scene can be published only after the story/files are durably present in the Activity's private store; `private_scene_wav_name()` rejects forged/unsaved stories.
- `activity.toml` declares `audio/wav` production. The saved-story/library UI exposes deliberate per-scene sharing; each share uses the trusted broker with role `narration` and a child-readable title. Repeated same-scene taps are deduplicated within the session.
- Publication still passes through the platform `WavCodec`, so malformed/private bytes cannot become a shared Creation merely because the Activity claims WAV.
- Relevant source/tests pre-existed this consumer slice at `70d28b22...`: `test_voice_creations.py`, `test_voice_creations_storage.py`. They remain **UNEXECUTED** in the combined candidate.

**Consumer — Teatrino:**

- `activity.toml` now consumes both `image/png` and `audio/wav`.
- `ImportedNarrationTrack` in `teatrino_audio.py` owns canonical WAV validation, the Theatre-specific maximum duration, mixer playback and PCM-prefix trimming for an early child Stop. The app does not duplicate RIFF parsing.
- The stage adds a compact pre-reader saved-voice import control in the existing toolbar gap. It requests exactly `media_types=("audio/wav",)` and `roles=("narration",)`; a pending PNG picker and a pending audio picker cannot coexist.
- Selection is one-use and fail-closed: MIME, semantic role and SHA256 are checked before `ImportedNarrationTrack` replaces the current narration source. Cancel/invalid selection preserves the prior source.
- When imported narration is selected, REC starts playback of that track and records puppet motion/SFX **without starting microphone capture**. Auto-stop follows narration duration. Manual Stop trims the canonical WAV to elapsed performance time before the show is saved. Without an imported narration source, the original microphone path is unchanged.
- A saved show receives its own WAV bytes through the already-authoritative `ShowRepository`; later deletion of the My Creations narration must not break saved replay. Playback channels are stopped on show completion and Activity shutdown.
- The microphone control acts as an explicit source switch: when a shared narration is selected, tapping the mic control clears that selection and returns to live microphone mode.
- A mechanical indentation defect was introduced in the first large run-loop edit at `84f37b27...`, caught immediately by static source review, and corrected at `ad9a606e...` before this ledger update. It has **not** been execution-tested.

**New deferred regressions:** `tests/test_teatrino_audio_narration.py` covers canonical WAV parsing/duration/trim; `tests/test_teatrino_shared_narration.py` covers narration-only picker scope, cancellation, integrity/role checks, imported-source recording with zero microphone starts, early-stop trimmed persistence and unchanged legacy microphone behavior. These are source only; no PASS is claimed.

**Single accumulated acceptance:** the existing `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` is now pinned to `cb9bc32c...` and adds: real Voice Stories recording/publication; audible My Creations Play/Pause/Resume/Replay **before selection**; Teatrino narration-only picker; no microphone contention during imported narration performance; early-stop trim; saved show replay after deleting the shared source WAV; and a return to the ordinary mic source. All P1–P4 tests/screenshots remain in the same procedure.

**Architecture choice for second audio consumer:** source review rejects `Officina dei Suoni` for arbitrary child audio because it is structured phonemic-awareness training. `Orchestra Animali` is the better future candidate for a narration/backing-track play-along workflow; do not dilute Officina's pedagogy merely to satisfy interoperability counts.

**Evidence boundary:** no complete checkout, `make verify`, Pygame/audio, Simulator, microphone, audible preview, Legacy-X, Acer/Pi or physical evidence was produced. P5 WAV is SOURCE-WIP only.

**Next source work while tests remain deferred:** implement a real UTF-8 producer/consumer path using Writing and only semantically compatible existing Activities; then add Orchestra Animali as a useful second audio consumer if the source design remains clean. P1 all-writer capacity and P6–P8 remain open.

---

### How to maintain this file

Append a dated entry to §C after every substantive session. Include commit SHA, files changed, actual test command/output and environment, screenshots reviewed if any, real remaining blockers, and **one precise next step**. Update current-state tables in §A/B as facts change; keep dated entries immutable except explicit factual corrections. Every Activity review gets one evidence-backed decision; reference source snapshots instead of pasting thousands of lines. Update `HANDOVER.md` and the appropriate existing architecture/lifecycle ledger without duplicating hardware evidence or inventing another orchestration process.