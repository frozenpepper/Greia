# Greia Creations + Activity Release — Progress / Resume Ledger

**Status:** ACTIVE, source-first. No first-party release approval implied.  
**Master plan:** [PLAN.md](./PLAN.md)  
**Run this ledger with:** `AGENTS.md` + `HANDOVER.md` + current `main`.

## 2026-10-15 — P7 Activity Quality Program started

All 45 Activities played headlessly and design-audited (docs/reviews/activities/2026-10-15_activity_design_audit/ (archived; see git history)). Decisions and waves: [P7_ACTIVITY_QUALITY_PROGRAM.md](./P7_ACTIVITY_QUALITY_PROGRAM.md). Child-facing language/case pass over all 45 committed (5086085d, 1c8b8e60, 661df616, 3ee4bda1); Shell Home redesign 5e7e089e. Source + headless desktop evidence only.

## A. At-a-glance checkpoint — 2026-10-08

- Program: **P1 adaptive capacity SOURCE-WIP**, **P2 broker/SDK SOURCE-WIP**, **P3 universal gallery + authenticated trusted modal SOURCE-WIP**, **P4 PNG round-trip SOURCE-WIP**, and **P5 WAV + UTF-8 interoperability SOURCE-WIP**. One shared launcher-composed `VolumeBudget` now guards Activity private storage, Creations and history growth at 75% used / 512 MiB free; shipped private Activity namespaces scale to 25% of the actual writable volume (32 MiB is only the legacy minimum floor). No complete checkout/GUI/audio/text/capacity acceptance has run. Wayland/KMSDRM and P6–P8 remain open.
- P3 integration continuation: the Shell trusted picker now rechecks
  its live broker request while displayed, dismissing a chooser promptly
  when the Activity cancels or the broker times out. It restores the
  Activity, stops Gallery preview audio, and does not apply stale
  input to a later request. Four new host/coordinator regressions
  were committed but NOT EXECUTED; no Simulator display
  focus claim or P3 promotion is made.
- P3 source-first child-flow review (latest 2026-10-08): the actual renderer had an unbound `width/height` on a completely empty Creations gallery or compatible-media picker. That first-use crash is corrected. A second issue let keyboard replay/navigation reach underlying content during the delete-confirmation modal; keyboard confirmation now defaults to Cancel and requires explicit Right → Enter, with visible focus. The audio-only empty picker now displays audio imagery. A new real dummy-Pygame screen regression covers these states but has **not been executed**. No P3 acceptance status changes; see GLA-007.\n- **Current P6 child organization/design (source-only, untested):**
  six genuine shareable-work Create anchors now replace ten misleading
  Create memberships among the 32 draft candidates; Acquario is Explore,
  Cucciolo is Play, Specchi is Learn, Torre is Play. My Creations appears
  immediately after Create with a distinct existing backpack core icon,
  independent of Parent-filtered Create membership. A compact-landscape
  Home presentation adjustment targets 3×2 rather than six vertical rows.
  A bounded [P6 child navigation and visual curation record](./P6_CHILD_NAVIGATION_AND_VISUAL_CURATION.md)
  maps all 32 draft Activities by curriculum family and lists the real
  remaining visual/organizational decisions. No actual Home screenshot
  or refreshed test execution yet. **IT/EN `my_creations.wav` launcher
  recordings are missing**, queued as approval-blocked GLA-010; do not
  mistake text/localization plumbing for spoken pre-reader readiness.
- **Current P6 Play/Learn design tranche (source only):**
  reclassified the saved-voice authoring Activity `storie_della_mia_voce`
  to Create-only and the observational `quattro_stagioni` to
  Explore+Learn, leaving 21 draft Play / 22 draft Learn /
  six draft Create memberships. A complete per-Activity editorial
  matrix in [P6 navigation/visual curation](./P6_CHILD_NAVIGATION_AND_VISUAL_CURATION.md)
  explains why the present five-group limit cannot truthfully
  partition all Activities; child browsing stays direct rather
  than manufacturing categories or hiding music/performance.
  The 13 existing discovery themes now use distinct canonical
  icons rather than sharing palette/book/puzzle artwork.
  The basic and shared-art launcher cards now show localized
  IT `Avvio...` / EN `Starting...` status.
  Real-roster/policy/art/locale regression tests were **authored
  but not executed**; no Simulator/art/listening acceptance.
- First-party `activities/` snapshot: **45** directories = **44 child-content Activities + 1 My Greia/settings Activity**. A new unvoiced **My Time** experiment is separately incubated in `activity_incubator/tempo_di_greia/` and is not a 46th installed Activity. My Greia remains outside child *games* selection but is now mandatorily staged as a trusted system Activity in official target composition (SOURCE-WIP, no live release verification). The earlier catalogue strategy's 41-item figures are historical.
- Catalogue handoff: the earlier **Colline Allegre script-import** and **Quattro Amici difficulty D5** mismatches were corrected in previous source commits. P7 batch 2 repaired Corsa's queued drag, Quattro's chrome exclusion, Torre's direct-script particle import, Delfino's resize and Dragon's nonexistent event. P7 batch 3 additionally repairs Acquario's missing event-loop input pump and real milestone emissions, Baia's feeding/fact event declarations and chrome checks, Cucciolo's drag/focus/event declaration, and Momo's discovery events, safe pointer mapping and resize. P7 batch 4 repairs atomic Monster-gallery persistence, true creation-event invocation and platform-owned Home input, plus Alphabet unique-discovery and honest difficulty declarations. P7 batch 5 repairs Cloud completion/drag/chrome authority; Mondo Contrari's real interaction milestones, English labels and safe letterboxing; Bridge honest placements; Marble responsive drag/input; Memory exit/localized replay; Encyclopedia internal navigation authority. P7 batch 6 repairs Stars platform Home and session identity, Train per-replay milestone identity, Seasons one-shot discovery and safe letterbox mapping, and Submarine undeclared/phantom events plus pointer authority. The false adaptive-D2–D6 Bridge and adaptive-D1–D4 Marble claims were removed. **All these source changes and new regression tests remain UNEXECUTED in the canonical checkout.**
- Release composition: **explicit draft selection is now source-wired into the authoritative owner release path**. `greia_release.py` sets `PIP_RELEASE_BUILD=1`; target composition stages only `build/first-party-release-activities.toml`, validates/indexes the installed subset, and refuses draft/empty policy for official release. Non-release/dev images deliberately keep the full source tree. Policy remains **draft**, so no official Activity release can build yet.
- Exchange status: **PNG, first/second WAV consumers and reciprocal UTF-8 paths are implemented SOURCE-WIP.** Capacity plumbing now uses one shared budget across all variable child-data writers in the launcher process (Activity storage, Creations, history), with adaptive private namespaces and migration/staging headroom. Storie della Mia Voce publishes saved `narration`; Teatrino uses it without microphone contention; Orchestra persists optional backing WAVs; Writing and Posta reciprocally exchange saved UTF-8 snapshots. **No real cross-app GUI/audio/text/capacity flow has been executed yet**; backup and physical evidence remain open.
- OS first-boot/installer: independently **OPEN** on the Acer route; read existing lifecycle plan before any hardware action.
- Historical P1 baseline: `creation_capacity.py`, `creation_media.py`, `creations.py`, `test_creation_library.py`, local mirrored **12/12 PASS**. P2/P3/P4 subsequent source commits supersede the original 'no broker/UI' snapshot; a complete checkout acceptance remains owed.

## B. Phase delivery status

| Phase | Scope | Current state | Release evidence still owed |
|---|---|---|---|
| P0 | repository/source baseline + triage | STARTED | consolidated current-head actual gameplay audit |
| P1 | typed creation repository, codecs, adaptive capacity | SOURCE WIP (shared 75%/512MiB VolumeBudget across private storage/Creations/history; 25% adaptive Activity namespace; deterministic tests committed) | full Greia checkout execution, concurrency/recovery results, real writable-volume calibration |
| P2 | permissions/manifest/broker/SDK | SOURCE WIP (publisher/importer + nonblocking request/poll/cancel and real socket tests committed) | full checkout socket/manifest/supervisor tests; presenter-enabled positive and default-fail-closed negative |
| P3 | universal picker and My Creations viewer | SOURCE WIP (viewer + filtered picker + authenticated async transaction + Legacy-X/Simulator trusted modal backends) | full checkout tests; real Simulator remote-canvas screenshots/input/audio/cancel/Home; installed Legacy-X focus/stacking; future Wayland/KMSDRM backend |
| P4 | Painting–Shape Garden–Theatre PNG round trip | SOURCE WIP (Painting independent import; Shape Garden persistent shape+backdrop project + flattened export; Teatrino persistent custom show backdrops) | full checkout tests; real GUI round trip/reopen/source-delete independence; resource/performance evidence |
| P5 | voice/music and writing/text interoperability | SOURCE WIP (Voice Stories→Teatrino narration; durable Orchestra play-along backing; Writing↔Posta reciprocal UTF-8) | full checkout/audio/text GUI tests; audible preview/isolation; private-copy persistence after shared-source deletion |
| P6 | explicit release catalogue and adaptive grouping | SOURCE WIP (single 32-child draft roster + mandatory My Greia system package on exact-id staging; release remains fail-closed until approval) | execute updated selection/staging and installed-index tests; prove trusted My Greia visibility/grants, exclusion of untrusted system spoofing, Parent policy on actual target |
| P7 | deep per-Activity quality review (45) | SOURCE WIP (**45/45 source-reviewed** across six batches; 32 draft child-content candidates, 12 child-content Activities withheld, 1 My Greia/settings Activity excluded from child-content release, 0 approved) | source-review inventory complete; execute accumulated Simulator/visual/audio evidence, reopen withheld choices and independently assess settings trust before any approval |
| P8 | end-to-end release and physical acceptance | NOT STARTED | real Acer and cross-platform acceptance |

### Activity release-review coverage

**45/45 entries inventoried and SOURCE REVIEWED (32 draft child-content candidates, 12 withheld child-content Activities, 1 settings/system Activity excluded from child-content release); 0/45 release-approved.**

No new Activity is dropped or silently approved merely for having unit tests. Record each review and disposition with evidence under §C entries. Historical R7.3 structural migration PASS does not equal release UX PASS.

### Media interoperability state

| Producer | Consumer | Kind | Status |
|---|---|---|---|
| Painting | Painting | PNG published snapshot becomes a separate editable private painting | SOURCE WIP: child-visible publish/import controls + modal transport wired; untested live |
| Painting | Shape Garden/stamps | PNG as background/base | SOURCE WIP: trusted PNG picker → private content-addressed backdrop + bounded durable shapes |
| Shape Garden | Painting | flattened PNG composition | SOURCE WIP: explicit trusted publish of deterministic flattened `composition` PNG |
| Painting/Shape Garden | Teatrino Fiabe | PNG backdrop | SOURCE WIP: trusted PNG picker + show-local content-addressed private backdrop snapshot |
| Storie della Mia Voce | Teatrino | WAV narration | SOURCE WIP: durable saved-scene publish → audio preview → narration-only picker → private saved-show copy; imported track replaces mic source for that performance |
| Storie della Mia Voce / future music producer | Orchestra Animali | WAV backing track | SOURCE WIP: trusted role-filtered picker → content-addressed private track → explicit Play/Pause live accompaniment; no autoplay |
| Writing | Writing / Posta di Leo | UTF-8 document/postcard | SOURCE WIP: Writing saved document publish + independent document/postcard import; Posta grapheme-safe draft import + saved-postcard publish |
| Any declared writer | My Creations viewer | large visual/audio/text previews | SOURCE WIP: Shell gallery |
| My Creations viewer | library | safe deletion/reclaim | SOURCE WIP: two-stage confirmation |

## C. Append-only dated progress entries

### 2026-10-08 — My Time composition-root launch repair (source only)

Local desktop acceptance at `47a949a0db27bfb078bc5af1d4d574f526f1e0c3` passed the four focused suites (5+7+9+3), library validation (101 resources), incubator package validation and the exact draft composition rules: default staging fails closed; `--allow-draft` stages 32 child Activities plus trusted My Greia (33 total), excluding 12 withheld entries and the incubated Time Activity. The first IT headless Simulator launch failed before screenshots because `activity_incubator/tempo_di_greia/main.py` called nonexistent `LocalizedResources.string()`. No source was modified during that failed run. Evidence was reported under `tmp/time-and-system-acceptance-20261008-042012/` and `time-and-system-acceptance-evidence.zip` on the local agent machine (not independently inspected here).

This bounded source repair changes that composition-root call to the public `LocalizedResources.text()` API and adds a regression that actually enters `main()` under both IT/EN with the real localization bundles and a stub activity event loop. **No headless, GUI, screenshot, audio, hardware or full-suite acceptance is claimed for the repair.** Continue desktop acceptance at its previously blocked Step 4; retain draft/noninstalled classifications unchanged.



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

**Next source work while tests remain deferred:** Orchestra is now the second semantically useful WAV consumer. Return to P1 all-writer proportional-capacity enforcement across profile storage owners; P6–P8 remain open.

---

### 2026-10-07 — P5 reciprocal UTF-8 route: Writing ↔ Posta di Leo; execution deferred

**Pinned latest source/test candidate for this text tranche:** `8d69ee4e7ee076923fbd78256238938b76b59477`. **No tests were executed for this tranche.** All source/unit/GUI checks remain accumulated into the existing desktop acceptance because the local agent is unavailable.

**Writing (SOURCE-WIP):**

- `DocumentRepository.create_text()` creates a new private UTF-8 document first and rolls it back if the index commit fails; imported shared text never overwrites an existing document.
- Writing deliberately publishes only the currently saved private document as `text/plain`, role `document`, with unchanged in-session publication deduplication.
- Its trusted picker is scoped to `text/plain` and semantic roles `document` / `postcard`; one-use selected bytes are SHA256 checked and strict UTF-8 decoded before a new private document is committed.
- The child toolbar exposes the same paper + directional-arrow non-reader affordance used by the other creation flows.
- Deferred regression owner: `tests/test_writing_creations.py`.

**Posta di Leo (SOURCE-WIP):**

- The original compact postcard editor remains the product interaction. Imported Writing/postcard text is normalized into one message, whitespace-compacted and truncated with Greia grapheme boundaries so emoji/ZWJ clusters are not split.
- A large paper-arrow-down editor control opens the same trusted universal picker nonblockingly at a 120 ms bounded cadence.
- Only an already-saved postcard can publish back to My Creations. A saved-card modal exposes a deliberate paper-arrow-up action; unsaved drafts have no publication path.
- Saved postcards now have path-safe durable private UTF-8 source files tied to the authoritative postcard index. New source files are rolled back when the index commit fails; removed-card files are reclaimed only after a successful index commit. Historical path-safe legacy IDs remain supported.
- The older gallery-delete false-success path was repaired: if persistence fails, the in-memory library is restored instead of pretending deletion succeeded.
- Deferred regression owner: `tests/test_posta_di_leo_creations.py`, with the existing `test_activity_posta_di_leo.py` fixture updated for private files.

**Snapshot/role semantics:**

- Writing publishes role `document`; Posta publishes role `postcard`.
- Both consumers accept exactly those two text roles, but each import creates/mutates only its own private state; deleting the My Creations source later cannot break a saved postcard or imported Writing document.
- MIME/role/SHA256/strict UTF-8 validation happens before consumer state changes. Wrong role, digest or encoding preserves existing content.

**Evidence boundary:** this is SOURCE-WIP only. No full checkout, `make verify`, Pygame text interaction, universal picker screenshot, real child flow, Legacy-X, Simulator, Acer/Pi or storage-failure run has been executed for the text tranche.

**Single accumulated acceptance owner:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` now includes Writing→Posta→Writing, grapheme/overlong cases, cancel/failure preservation and shared-source deletion independence.

**Next source step:** Orchestra Animali is now implemented SOURCE-WIP as the second semantically useful WAV consumer. Complete P1 proportional capacity enforcement across every profile-writing owner rather than only the Creation Library.

---

### 2026-10-07 — P5 second WAV consumer: Orchestra durable play-along backing; execution deferred

**Pinned latest Orchestra source/test candidate before this documentation commit:** `ae4e5bf6bea6a1adf070de4092c62383056ff17d`. **No tests were executed for this tranche.** All source/unit/GUI/audio checks remain accumulated into the existing desktop acceptance.

**Source review decision:** Orchestra Animali is a free-play instrument/piano stage in current source, not an implemented auditory-memory matching game. Arbitrary child WAV is therefore accepted only as an **optional play-along backing track**; it is not injected into a memory challenge or used to replace instrument sounds.

**Implementation (SOURCE-WIP):**

- New `orchestra_backing.py` owns one content-addressed private backing WAV plus authoritative metadata (`narration`, `song`, or `music`), with strict metadata reads for mutation, failed-pointer rollback, replacement cleanup and integrity-checked load.
- `ImportedBackingTrack` reuses the platform `WavCodec`; `BackingTrackPlayer` reserves mixer channel 0 so rapid live instrument/piano `Sound.play()` calls cannot steal the backing track. It owns explicit Play/Pause/Resume/stop and natural-completion detection.
- Orchestra's trusted picker is nonblocking at the common 120 ms cadence and scoped to `audio/wav` roles `narration` / `song` / `music`. Existing backing playback stops **before** opening the picker so My Creations preview audio has sole ownership. Cancel leaves the private selected track loaded but does not resume/autoplay it.
- Import persists the canonical selected WAV into Orchestra private storage **before** changing the active player. Failed persistence, wrong role/MIME/digest or malformed WAV preserves the previous track.
- Relaunch loads the private track into a ready state but never autoplays. This makes playback independent from later deletion of the shared My Creations source.
- Large pre-reader import and Play/Pause controls occupy the top-left safe HUD area, outside trusted Home chrome. Import visibly disables and has no hit target when trusted Creations/private storage is unavailable; a previously persisted track can still play.
- Live input during backing playback is counted. Natural backing completion emits declared `concert.performed` only when the child actually accompanied it; passive playback is not a creation.

**Adjacent source defect corrected:** Orchestra source emitted `instrument.played` while the manifest declared unused `melody.matched`; Greia rejects undeclared events. The manifest now matches actual free-play behavior: categories `music` / `rhythm` / `creativity`, skills `music.rhythm.perception` + `music.instrument_association`, events `instrument.played` + `concert.performed`, and `audio/wav` consumption. No progression rule referenced the removed legacy event IDs.

**Deferred regressions:**

- `tests/test_orchestra_backing_store.py` — content-addressed save/load/replace, pointer rollback, unreadable metadata denial, corrupt blob fail-closed, clear ordering.
- `tests/test_orchestra_creations.py` — role-scoped picker, unavailable import fail-closed, persistence-before-mutation, wrong role/digest preservation, reserved channel Play/Pause/Resume, concert only with live input.
- `tests/test_orchestra_manifest.py` — truthful pedagogy/event declarations and WAV consumer contract.

**Single accumulated acceptance:** `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` now includes real preview-before-select, no-autoplay import/relaunch, live instrument layering without channel theft, pause/resume, picker-preview isolation, source-WAV deletion independence and concert semantics.

**Evidence boundary:** no complete checkout, `make verify`, Pygame/SDL mixer, audible preview/play-along, Simulator screenshot, Legacy-X, Acer/Pi or physical evidence was produced. Orchestra/P5 remains SOURCE-WIP.

**Next source step:** P1 variable-writer capacity enforcement is now implemented SOURCE-WIP. Move to **P6 explicit release catalogue** and begin **P7 evidence-backed 45-Activity review**, while the accumulated P1–P5 execution remains deferred to the later local-agent run.

---

### 2026-10-07 — P1 shared machine budget + adaptive private namespace source; execution deferred

**Pinned code/test checkpoint for the next accumulated acceptance:** `39e8d77b1099f8a407b2f0bc4efbd3516cf04fba`. Later commits in this tranche are documentation-only. **No tests were executed** for this candidate because the owner asked to carry this turn's checks to the next local-agent slice.

**Implemented SOURCE-WIP:**

- `creation_capacity.py` now exposes a general `VolumeCapacityPolicy` / `VolumeBudget` while retaining backward-compatible `CreationCapacityPolicy` / `CreationSpaceError` names. One held `write_reservation()` serializes filesystem measurement through caller-owned writes and separates final persistent growth from peak temporary staging bytes.
- Positive child-data growth must satisfy **both** the 75% used ceiling and 512 MiB free floor. Non-growing replacements/repair writes may temporarily use reserve space but can never request more bytes than are actually free; this prevents low-space protection from making existing state impossible to update/reclaim.
- `ActivityStorage` uses the budget for atomic KV, private-file and metadata writes. `ActivityStorageService` owns/injects the budget and storage migrations reserve their full working-copy growth before `copytree`. The old direct 64 MiB free-space check is no longer authoritative.
- `CreationLibrary.publish()` holds the same reservation across normalized blob/preview writes + SQLite commit, with conservative transaction/journal headroom. The Activity supervisor injects the exact `ActivityStorageService.volume_budget` into each session library, closing the private-save vs publish stale-check race in one launcher process.
- `PlatformHistoryService/ProfileHistoryStore` shares the same launcher budget. New schema creation, session inserts and event/progression inserts reserve bounded growth; mark-ready/finish/recovery transactions reserve only journal scratch so existing state remains maintainable at the ceiling.
- `LauncherRuntimeServices` now composes one budget and passes it to storage + history; its dataclass keeps a default budget for older tests/development fixtures, while production construction explicitly injects the shared instance.
- `StoragePolicy` gained optional `namespace_quota_fraction` (default 0 for compatibility). Shipped `runtime/storage-policy.toml` uses **0.25**; effective private quota = max(legacy byte floor, fraction × actual writable volume). On an 8 GiB writable volume this is **2 GiB per Activity**, while aggregate positive child-data growth still stops once total used reaches 6 GiB in the owner's 2-used/6-free example. The 16 MiB single-file/media containment bound remains independent.
- Bounded control metadata (profile registry, presentation/theme JSON, achievements, usage-limit ledger) intentionally remains writable inside the protected content reserve for recovery. The 2 MiB wallpaper importer is currently a dormant library/test capability with no production Parent/Shell route; if activated later it must receive the existing shared budget first.

**Deferred regressions:** new `tests/test_profile_volume_budget.py` covers the 8 GiB→2 GiB adaptive quota, legacy fixed-quota compatibility, held reservation serialization across concurrent writers, non-growing update behavior at the ceiling, new private-file denial, storage-migration copy denial and history update-vs-new-growth behavior. Existing `test_creation_library.py` still owns the 8 GiB aggregate example and creation-full rejection. All are **UNEXECUTED at this checkpoint**.

**Evidence boundary:** no complete checkout, `make verify`, real filesystem saturation, concurrent live Activity writers, Simulator, Legacy-X or hardware evidence was produced. This is architecture/source progress only; P1 remains SOURCE-WIP until the accumulated desktop acceptance runs.

**Next source work:** P6 release composition/allowlist, then P7 review of all 45 first-party Activities using source + existing historical evidence now, with live launch/visual/performance acceptance deferred to the same later agent session where necessary.

---


### 2026-10-08 — P6 authoritative release composition + P7 creative-anchor source review (7/45)

**Pinned code/test source candidate:** `d3d9186078a80828995e8be74c29677b308b40ee` plus subsequent P6/P7 source fixes through the current pre-documentation HEAD. **No tests were executed in this continuation**; all source/unit/Simulator/audio/visual checks remain carried to the accumulated acceptance because the owner’s local agent is unavailable.

#### P6 release authority

- `build/first-party-release-activities.toml` is the **single first-party release roster** and remains `status = "draft"`. It contains only the seven Activities that completed this source-review batch; this is a review candidate set, not a final product count.
- `build/lib/compose.sh` previously bypassed that policy by validating/copying/indexing all repository `activities/`. This is repaired: official `PIP_RELEASE_BUILD=1` composition calls `tools/stage_release_activities.py` into the target root, then hygiene-checks, registry-validates and builds the deterministic index from the **installed staged subset**.
- Ordinary development/test target composition still copies the complete source Activity tree. This keeps installer/first-boot debugging and P7 review independent from an unfinished release roster.
- `tools/greia_release.py` now always sets the existing `PIP_RELEASE_BUILD=1` for its privileged release subprocess tree. There is no second release-mode flag.
- `tests/test_greia_release.py` locks the CLI flag and installed-subset/index composition contract. `tests/test_stage_release_activities.py` stages the repository draft roster under explicit `allow_draft=True`. Existing selection/staging tests still cover sorted identity, draft refusal, symlinks and atomic output behavior.
- **Official release remains fail-closed:** the draft policy cannot pass `require_approved()`. No current release is silently reduced to seven apps.

#### P7 batch 1 — creative/interoperability anchors

All seven have manifests reviewed, package-specific regression suites present, Italian + English `activity-title.wav`, matching IT/EN locale key sets, typed Creations declarations matching source flows, and small package Git-blob footprints (roughly 180–483 KB). These are **source facts only**, not GUI/performance/audio acceptance.

| Activity | Source disposition | Fixes/findings in this review | Required evidence before approval |
|---|---|---|---|
| `painting` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED** | Required image anchor; private autosave remains separate from explicit publish/import. Removed stale manifest comment claiming picker mediation was pending. | real publish→picker→independent edit/reopen/delete; 800×480/1024×600/wide screenshots; pointer/touch/undo performance |
| `shape_garden` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED** | Persistent bounded shapes + private imported backdrop + explicit flattened composition. Fixed declared `creation.completed`: emitted once only after a genuinely new successful publish. | real Painting→Garden→Painting; autosave/relaunch; source deletion independence; visual density/touch targets |
| `teatrino_fiabe` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED, COMPLEX** | Removed nonexistent `scene.created`; saved-show completion now emits declared `story.played`; free-stage playback cannot inherit stale saved-show identity. Fixed major locale bug: English profiles previously still loaded Italian UI tables; selected locale now owns UI/puppet/backdrop labels and Italian-only fallbacks were removed. | English + Italian Simulator capture; microphone/imported narration; saved-show replay; PNG backdrop; frame rate/cache behavior; deletion/relaunch |
| `storie_della_mia_voce` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED, HARDWARE-SENSITIVE** | Manifest events match typed event-adapter calls; durable WAV publication is only from saved private scenes, role `narration`; IT/EN title audio present. | real mic/no-mic/busy-device; audible replay + My Creations preview; storage failure/retry; hardware input levels |
| `orchestra_animali` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED** | `instrument.played`/`concert.performed` declarations match actual emissions; imported backing is explicit and non-autoplay. It is the dedicated music family, so preserve absent contrary live evidence. | audible backing + pause/resume; live layering; pedagogical/rhythm usefulness; low-resource mixing |
| `writing` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED (AGE 5+)** | Keyboard+pointer requirements are truthful; grapheme-safe bounded editor; saved UTF-8 publish/import creates an independent private document; no false progress events. | keyboard/emoji/undo/long Unicode; Writing→Posta→Writing; narrow/wide layout |
| `posta_di_leo` | **KEEP / DRAFT CANDIDATE — SOURCE REVIEWED (AGE 5+)** | Grapheme-safe import and deliberate saved-postcard publish. Fixed capability bug: pointer was optional despite recipient/stamp/gallery/shared-text controls; pointer is now required. `postcard.created` matches committed-storage semantics. | recipient/stamp/text/shared-document flow; keyboard+pointer behavior; bilingual screenshots; save/delete/reimport |

**Draft roster (sorted, not approved):** `org.greia.orchestra-animali`, `org.greia.painting`, `org.greia.posta-di-leo`, `org.greia.shape-garden`, `org.greia.storie-della-mia-voce`, `org.greia.teatrino-fiabe`, `org.greia.writing`.

**Evidence boundary:** no `make verify`, focused unit suite, release staging command, actual release composer, Pygame Simulator, screenshot review, audible playback/microphone, Legacy-X, Acer/Pi or physical run was executed. The seven dispositions mean **source-reviewed candidate**, not accepted or approved.

**Next source-review batch:** action/strategy and motor-play risk cluster — `colline_allegre`, `corsa_bacche`, `labirinto_magico`, `quattro_amici`, `torre_forme`, `viaggio_delfino`, `volo_draghetto`. Focus on real difficulty mapping, failure/retry fairness, CPU/opponent behavior, input smoothness and child-readable feedback before adding any to the draft roster.


---

### 2026-10-08 — P7 batch 2: motor, action and strategy games (14/45 source-reviewed)

**Source-only evidence:** inspected all seven current manifests, actual game-model and input/progression paths, existing package tests, and both locale JSONs plus both spoken `activity-title.wav` package directories. All seven have exact Italian/English string-key parity and both title recordings. Five are added to the **draft** release candidate roster, not to a released/approved catalogue. Two remain source-reviewed but withheld. **No tests, live gameplay, screenshots, hardware, accessibility or frame-time measurements were executed**, by owner request.

| Activity | Source disposition | Verified source finding / repair | Evidence still required |
|---|---|---|---|
| `colline_allegre` | **KEEP / DRAFT CANDIDATE** | Five real physics profiles D1–D5 vary hill amplitude, roughness, terrain/obstacles and target distance; model implements sprung wheels, torque/tilt and landings. Earlier direct-script relative-import chain repaired. Best-distance event now emitted only after successful durable improvement. | actual Greia script launch; 5 course profiles, flips/bridges/mud, responsive throttle/brake/tilt, 30Hz Acer budget |
| `corsa_bacche` | **KEEP / DRAFT CANDIDATE** | Five authored maze layouts; gentle critters, naps, rainbow power and recovery at zero hearts rather than hard game-over. Found queued click/drag used global `pygame.mouse.get_pressed()`, unreliable with touch/Simulator event injection. Fixed explicit press/drag/release and focus-loss handling in `corsa_app.py`. | all five layouts reachable/solvable, critter chase fairness/collision safety, tiny touchscreen pointer control, real frame rate |
| `labirinto_magico` | **KEEP / DRAFT CANDIDATE, LARGE-MAZE VISUAL RISK** | Six *actual* size tiers D1–D6 from 13×9 to 59×29, generated paths, collectibles, directional slide controls and terminal victory layer; recent difficulty-roster fix present. Not simply six label variants. | solvability with each size, 800×480 and 1024×600 path legibility, large-tier accessibility, pointer/keyboard/Back, real restart |
| `quattro_amici` | **KEEP / DRAFT CANDIDATE** | Four supported D1–D4 configurations, two-player versus age-calibrated CPU with silly/defensive/smart/minimax tiers; gravity, wins, turn-taking. Earlier false D5 manifest corrected and lifecycle events integrated. Fixed pointer hover/click entry to reject protected trusted-Home regions. | CPU fairness across board states, two-player handoff, native & pointer gamepad navigation, robust undo/restart, high-level move latency |
| `torre_forme` | **KEEP / DRAFT CANDIDATE** | Three genuinely different modes — free geometric matching, slow falling, faster challenge — correspond to *age/difficulty ranges* D1–D2, D3, D4–D5, **not five separately authored modes**. Fixed direct-script failure: particle effects incorrectly imported `.torre_content` inside an event handler; constants now resolve from the package/script-aware module imports. | direct-script snap + clear effects, 3 modes, slow-machine falling/latency, responsive shelf/rotation/controls, visual height/celebration |
| `viaggio_delfino` | **SOURCE REVIEWED / WITHHOLD from draft pending product differentiation** | Sequential marine chapters, sourced animal/nature voice facts and narrated discovery give it a distinct direction from Dragon's endless flight; no declared D1–D6 roster or adaptive tier should be invented. Fixed resize bug: `_handle_events()` rebuilt `self.canvas`, but `run()` used a stale local canvas to draw/present; it now refreshes in the same frame. | full 3-chapter progression, spoken fact comprehension, real 800×480 resize, art/perf, compare experience against Dragon before including both |
| `volo_draghetto` | **SOURCE REVIEWED / WITHHOLD from draft pending depth decision** | Gentle endless flight with stars, rainbows, cloud bounce, accessories and no terminal lose/win; not a D1–D6 progression despite earlier review queue shorthand. Manifest falsely declared `flight.completed`, which the endless app never emits; removed rather than inventing achievement events. | prove sufficiently differentiated motor/reaction progression vs Delfino, actual replay motivation, collision/pacing for ages 4–9, low-resource render |

**New deferred regression source:** `tests/test_action_pointer_boundaries.py` covers queued Corsa press→drag→release→lost focus, Quattro protected-region denial on hover/click, and Delfino's same-frame canvas replacement; `tests/test_activity_torre_forme.py` now exercises snap/clear effects with direct-script module imports; `tests/test_activity_volo_draghetto.py` checks the manifest's honest endless-flight event set. Existing package-specific suites for all seven remain authoritative too. All new/old tests are **unexecuted** for this continuation.

**Draft roster target:** original seven creative candidates + `org.greia.colline-allegre`, `org.greia.corsa-bacche`, `org.greia.labirinto-magico`, `org.greia.quattro-amici`, `org.greia.torre-forme` = **12**. The two other reviewed games are not deleted or dropped from development; they remain discoverable in the full source/dev install. Official release still fails closed while policy is `draft`.

**Next P7 batch:** science, emotional reasoning and early mathematics (`acquario_magico`, `baia_delle_orche`, `clinica_cuccioli`, `cucciolo_mio`, `faccine_momo`, `il_giardino_dei_numeri`, `luci_di_momo`), emphasizing overlapping pedagogy, non-reader interaction and genuine age-2/3 independence. The accumulated one-run local-agent acceptance must include direct-script and low-resource motor-play cases from this batch; no Acer flashing or release build is requested now.



---

### 2026-10-08 — P7 batch 3: early care, emotion, nature and quantity (21/45 source-reviewed)

**Source base:** inherited `18b6f158a797c60537bea7b49658548beb3d52f8`; new repair commits `001368439f3ea35c240e1090f06170ee39e119e1`, `7df80d372b68f382b0158259ee42efb414441ce1`, `6076879ed07513e6f1545e356a6ee0b0e5e07401`. Read the exact seven manifests, lifecycle/model/event paths, available package suites, paired localized JSON and packaged IT/EN title-WAV metadata. All seven IT/EN locale dictionaries have identical key sets; both localized `activity-title.wav` files are present with nonzero sizes for each of the seven. **No Pygame, unit, make verify, first-frame, screenshot, audio listening, input, performance, Simulator or hardware command was executed.** Changes are CODE + TEST SOURCE-WIP only. Title WAV presence does not certify listening quality.

| Activity | P7 source disposition | Evidence and repair | Later evidence required |
|---|---|---|---|
| `acquario_magico` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Eight aquatic characters, fish feeding/interaction, day/night ambience and private aquarium state. Critical defect: `AquariumApp.run` never drained `pygame.event.get()`, making its child input inert. Repaired event pumping/QUIT, emitted declared `aquarium.fish_fed` only on actual consumption and `aquarium.glow_mode_toggled` on real changes, plus local protected-chrome gate. | real first-frame/script launch, toolbar/chest/fish/finger controls, save/restart, crowded aquarium FPS and assets, compare nature depth against Orca/Delfino |
| `baia_delle_orche` | **SOURCE-REVIEWED / WITHHOLD — comparative portfolio decision** | Three differently behaving orcas, feeds/cuddles/breaches/music and spoken Tito facts; more than a passive aquarium copy. Fixed previously undeclared `orca.fact_discovered`, event emission for actual swallowed fish (not merely food placement), pointer gates over Greia chrome/outside view. | real and audible six-fact discovery, Italian/English narration, sufficient unique causal/educational value against Aquarium and Delfino, 800×480 layout, touch responsiveness, singing/physics FPS before candidacy |
| `clinica_cuccioli` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Five patients with intentionally ordered 2–4-step care prescriptions; child must choose an explicit instrument before treatment. `vet.treatment_applied` and `vet.patient_healed` have real model and adapter owners. Separate clinical reasoning from pet care. | all patients, help without reading, recovery from wrong tool, physical hit sizes, localization and save/restart |
| `cucciolo_mio` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Persistent species/accessory/basic care and distinct play/sleep routines. Fixed ball drag that polled global mouse position instead of queued move events, prevented post-drag accidental click and focus-loss stale dragging; added genuinely emitted `pet.played` to manifest. | queued touch/Simulator events, drag/throw and loss-of-focus, tab boundaries, pet save/relaunch, asset/voice/presentation quality and responsive layout |
| `faccine_momo` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Six emotions in free mirror plus two-choice spoken quiz and comfort interaction. Previously declared `emotion_discovered` and `all_emotions_explored` events were never emitted; now new distinct discovery/one-shot all-explored on real free or successful-quiz selection through typed event port. Added Pygame reference canvas contain-mapping, resize, finger input, protected Home rejection and bounded 30 Hz presentation. | launch both locale voices, inspect emotional clarity, 800×480/wide framing, quiz retry/hint and safe chrome, low-end draw cost |
| `il_giardino_dei_numeri` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED, AGE 2–4** | One-at-a-time tapping/counting 1–5, auto-advancing three real quantity tiers, delayed spoken-count celebration, every-third-basket completion and profile progress. Distinct introductory counting from time-limited quantity-memory games. No modification needed. | pre-reader child comprehension, optional audio/no-audio fallback, tiny targets and spoken numbers 1–5, adaptive continuity |
| `luci_di_momo` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED, AGE 4–6** | Five-round sets, four real presentation/reveal tiers, one wrong-answer hint/replay path, bounded attempt-history adaptive level and once-per-session completion. More advanced subitizing than toddler garden. No modification needed. | distractors/reveal fairness, actual speech/noisy timing, hint comprehension, difficulty transitions after sessions, screenshot/CPU/audio evidence |

**Curation:** six additional sorted source-reviewed entries are staged in `build/first-party-release-activities.toml`, for **18 draft candidates** in all; `baia_delle_orche` remains in the full developer source tree, not the draft. Previously withheld `viaggio_delfino` and `volo_draghetto` remain withheld. The roster still says `status = "draft"`: production release must **refuse** it. No item is approved for release; none is deleted.

**Committed deferred tests:** `tests/test_p7_batch3_source_regressions.py` exercises aquarium queued input, actual milestone transitions, Greia chrome safety, Orca event declaration and input safety, Cucciolo queued drag/focus interruption and honest manifest event. `tests/test_activity_faccine_momo.py` exercises unique emotion facts/one-shot completion, correct quiz discovery, reference canvas and chrome rejection. Existing `test_activity_acquario_magico.py`, `test_activity_baia_delle_orche.py`, `test_clinica_cuccioli_refactor.py`, `test_activity_il_giardino_dei_numeri.py` and `test_activity_luci_di_momo.py` remain essential. **All are UNEXECUTED.** Added this tranche to the **one existing** desktop acceptance document; do not spin up a second run or invoke installer/Acer testing.

**Next P7 source-review batch:** inspect seven remaining distinct curriculum/creative gap candidates: `alfabeto_leo`, `bosco_numeri`, `bottega_delle_misure`, `casa_del_dieci`, `festa_delle_rime`, `foresta_parole`, `morbidi_mostriciattoli`. Trace actual difficulty, proof of reading-free interaction, words/number teaching parity, duplication across portfolio and Creations producer capability. Preserve all deferred acceptance obligations; do not approve a roster based solely on source review.


### 2026-10-08 — Batch-3 shared event identity follow-up (source only)

A platform-wide event-semantics defect surfaced during this review: `activity_api.emit_activity_event()` generated its default idempotency key from `id(payload)`, which Python can recycle immediately. Repeated identical but **distinct** child actions therefore risk being treated as the same already-processed history fact. Fixed **centrally** in `src/greia_platform/activity_api.py` at `c6204fbfa524dc3a0272a506cb74e8163d91236a`: omitted keys now use a fresh UUID-based identity; callers supplying an explicit stable idempotency key (for semantic retries) remain unchanged. Added `tests/test_activity_event_idempotency.py` proving distinct default facts and explicit-key stability. **No test or runtime execution was performed**. The shared executable code/test acceptance anchor supersedes the previous batch-3 roster-only `6076879ed...` and is now `c6204fbfa524dc3a0272a506cb74e8163d91236a`. This preserves the same 18 draft candidates and 21/45 review coverage.


### 2026-10-08 — P7 batch 4: pre-reader literacy, older-child numeracy, rhymes, monster authoring (28/45)

**Starting `main`:** `26593f858a84b18f9c6c924ddd6cf5bf8711aeba`. **Source-repair commits:** `f01e7b5f40f29b5ea1b4de75efa53307977630e7` and `88dda4a2e2d52531b61c6c56809d83bbfaf656fc`. Reviewed all seven manifests, actual event/model/entrypoint source, relevant existing test files, locale dictionaries and bilingual title-WAV metadata. Six of seven locale dictionaries share identical IT/EN key sets; **Foresta Parole differs only in intentionally localized word identifiers** (e.g. `word.sole` vs `word.sun`), which are corpus data, not an unresolved UI key mismatch. IT and EN spoken title WAVs exist with nonzero bytes for all seven. **No tests, headless script, GUI, listening, Simulator or hardware were executed.** Existing package tests and this turn's added regressions are source-only.

| Activity | Decision at source-only P7 checkpoint | Source finding / repair | Required live proof |
|---|---|---|---|
| `alfabeto_leo` | **SOURCE-REVIEWED / WITHHOLD pending age/learning calibration** | Full 26 bilingual picture/letter cards and explore vs three-choice quiz, but manifest inaccurately claimed three adaptive D1–D3 levels. Corrected to honest single difficulty with distinct modes. Real `letter.discovered` events now follow **new** letters in explore or quiz; alphabet-completion is once-per-collection, never repeated each correct guess. Restored saves produce no synthetic discoveries. | prove age-2/3 independent interaction without letter-reading, systematic voice/phonics quality, meaningful progression beyond all-at-once 26-letter menu, responsive layout and first frame |
| `bosco_numeri` | **SOURCE-REVIEWED / WITHHOLD pending portfolio differentiation** | Forest counting of 1–10 and 3-choice numeral quiz are real, with gentle retry and progress, but substantially overlap Giardino Numeri's 1–5 counting and Luci Momo's quantity matching. Existing milestone IDs are emitted on completed count/challenge. | side-by-side child-value study vs two existing numeracy candidates; determine whether 6–10 extension/numeral literacy justifies a separate release Activity |
| `bottega_delle_misure` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Five authored levels: compare lengths/heights, order three parcels, non-standard unit counting, shelf capacity, mixed mode; bounded attempt-based adaptation, typed real completion events and protected pointer gating. Not another counting game. | measure/compare comprehension, correct answer distribution, 800×480 visual baselines, input accuracy, prerecorded IT/EN cues, performance |
| `casa_del_dieci` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Five actual level families: construct part-whole 1–5, missing 5–10, addition, subtraction, mixed composition; explicit room toggling/confirm vs answer choices, terminal replay and event persistence. | ensure 5–7-year-olds understand rooms, operation pedagogy, failure/retry hints, full D1–D5 solved sessions, keyboard/pointer and localized spoken prompts |
| `festa_delle_rime` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Separate bilingual reviewed rhyme and alliteration corpora, authored challenge modes for rhyming matches/odd-one-out/alliteration and adaptive D1–D4; queued spoken words distinguish it from letter matching. | listen to every actual spoken pair and wrong option (no accidental rhyme due language), queued prompt/playback sequencing, age-4 pre-reader comprehension, repeat fairness and low-end audio |
| `foresta_parole` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED (OLDER CHILD)** | Word-based letter catching with repeated target orbs, owl feedback, actual three-catch word completion, saved score and IT/EN separate phonics audio/corpus. Distinct later word/phoneme application versus toddler alphabet browsing. Locale-specific `word.*` keys are intentional separate translated curricula. | normal direct-script launch (relative import portability), Italian and English word-prompt audio accuracy, more varied word scaffolding than repeated letter catches, long-run target pacing, 800×480 hit targets |
| `morbidi_mostriciattoli` | **SOURCE-REVIEWED / WITHHOLD pending portable Creations exchange** | Rich six-part creature composition with gallery, names and bounded immutable recipes, but only a private JSON recipe gallery: **no shared image/png publishing for Painting/Theatre/Shape Garden**. Critical source defects fixed: creation event used unsupported `session_id` keyword and silently disappeared; gallery save/delete mutated in-memory child state and played success before durable storage returned. Now stage candidate gallery, commit storage first, then publish event and visible feedback. Local fake Home click no longer terminates Activity; physically protected coordinates are rejected. | child draw/save/delete/restart + full-disk failure, private gallery durability, safe Home behavior, publish flattened monster PNG through the existing platform Creations SDK, import round-trip, 800×480 + picture usability |

**Release policy:** add **only Bottega, Casa, Festa, Foresta** to the single sorted draft roster: **22 source-reviewed draft candidates, 6 withheld total, 0 approved**. Newly withheld Alphabet/Bosco/Monster join Orca/Delfino/Dragon. Nothing removed from source/dev installs. Official release remains explicitly **`draft` / fail-closed**. These are provisional catalogue choices, not final product acceptance.

**Regressions added, UNEXECUTED:** enhanced `tests/test_activity_morbidi_mostriciattoli.py` exercises correct Greia event invocation with privacy-safe payload and stable portrait identity, failed-save/non-mutating rollback, failed-delete preservation and trusted Home non-interception. Updated `tests/test_activity_alfabeto_leo.py` covers honest manifest difficulty, newly discovered letters from exploration and guess, one-shot parade, restored state not replaying events. Existing `test_activity_bosco_numeri.py`, `test_activity_bottega_delle_misure.py`, `test_activity_casa_del_dieci.py`, `test_activity_festa_delle_rime.py`, `test_activity_foresta_parole.py` remain required. Append all to **one** consolidated desktop acceptance, not new gate docs.

**Next source review:** P7 batch 5 physics/executive/social and discovery: `costruiamo_ponti`, `la_discesa_della_biglia`, `memory_meraviglie`, `mondo_contrari`, `nanna_delle_nuvolette`, `nascondino_bosco`, `enciclopedia_greia`, then remaining ten. Cumulative acceptance **must run at the current executable candidate before approving any Activity**. The Acer installer/first-boot route is still independently BLOCKING; do not flash or re-build physical media in this product-content run.



### 2026-10-08 — P7 batch 5: applied physics, observation, calm sequencing and encyclopedia (35/45)

**Source baseline:** `0a85917aaa7a8e5e9ab61f8b80f28b6873a72ad0`. **Source repair commits:**
- `1d4650b2fd0d58e46f42ce74534eb459dffeb2f6` — Cloud real completion-event contract, trusted Home safety, finger/drag focus loss and globally distinct nightly ids;
- `954558a7343d76f917d0e11259a958e306627a42` — Mondo Contrari interaction-earned category/all-five facts and protected letterboxed pointer/resize;
- `3fd56c504cad15142fb4390cc48bc30cb183f68d` — Bridge exact block placement event and repeated-click no-op;
- `fcd482c0cdc7630c34604fecb4673a2fc5481451` — Marble drop tool/reference-canvas scaling, correct drag identity, Home-safe coordinates/focus-loss/resize;
- `f060a262493ee9cdfef2c0c6546cbab7c36bdc00` — actual memory Quit/Escape main-loop stop, Memory New-Game localized label, Mondo English visual labels, honest three fixed Bridge and Marble levels instead of fake adaptive tiers;
- `6e53621d903f8fe1cde22bdb1fed8c0105e7b1fe` — encyclopedia moves Activity-owned internal page-history Back from forbidden Greia Home/Back protected geometry to top-right in-content safe surface.

Reviewed **all seven manifests**, relevant domain/gameplay, rendering, audio/event, storage, locale, launch, testing and life-cycle paths in GitHub; both locale dictionaries have identical IT/EN string key sets in all seven cases (Encyclopedia 246 each, 200 mapped audio cues each). **This turn did not execute any full checkout tests, Pygame runs, GUI, screenshot, voice listening, SDL/Simulator, physical image or Acer tests.** Existing/new tests remain source-only and not accepted.

| Activity | Source review disposition | Actual game / important repair | Evidence gate before release approval |
|---|---|---|---|
| `costruiamo_ponti` | **WITHHOLD — needs structural-physics or pedagogical claim redesign** | Three authored material-placement puzzle bridges (river/canyon/space), with exact required materials per slot. Does not model actual structural forces/load capacity or 2–6 adaptive tiers; removed the dishonest adaptive metadata. Fixed missing `bridge.block_placed` manifest event emission and no-op repeat taps. | Validate age-5 structural-learning benefit, improve mechanics beyond scripted matching or relabel as material pattern puzzle, verify all three worlds and protected input; avoid interpreting particle/crossing animations as force simulation |
| `la_discesa_della_biglia` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Real gravity and multiple tool collisions, movable basket, personal-best, time, 3 authored levels. Fixed tool drag/click/release to use shared contain-mapped 1024×600 canvas on any screen, safe protected chrome and focus/resize cancellation. Dropped nonexistent adaptive fourth tier claim. | Full solution/failed run each of 3 levels at 1024×600 and 800×480, protected input, touch drags, impossible basket, collision correctness, 30 Hz Acer CPU, actual narration, restart and best-time storage |
| `memory_meraviglie` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Authentic variable 2/3/6/8/9-pair matching sizes across four picture themes, turn delay, final success, stored user theme/grid preference. Fixed Quit flag ignored by outer lifecycle loop and Escape, and hardcoded Italian New Game UI in English profile. | 2×2 through largest grid, wrong-pair unflip timing and no accidental duplicate taps, mismatch animations, real English/Italian UI, Home/back, assets and old Acer frame budget |
| `mondo_contrari` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Five true opposite pairs with interactive state toggles, prominent animated child target and spoken words. Declared learning facts previously never emitted and source confused category visits with exploration. Now only actual first interaction per category awards facts and full-five completion once; safe letterbox mapping, finger support, resize and bilingual labels. | Play and hear both sides of every opposite in both locales, no accidental early all-five award, 800×480 top control readability, Home exclusion, low-end performance |
| `nanna_delle_nuvolette` | **WITHHOLD — restore saved bedtime preferences** | Three cloud friends each require a blanket, star and gentle sleep tap. Fixed swallowed unsupported `session_id` event call, unique nights, pointer chrome/focus/touch safety and correct one-shot emission. Source stores favored blanket IDs but next night's model still creates blank presets without loading saved preferences; not honest persisted personalization yet. | Decide preferred-blanket UX without bypassing child sequencing (e.g. preselected palette vs pre-equipped blanket); implement and prove save/reopen/new night and stop/release at protected area, then re-evaluate |
| `nascondino_bosco` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED** | Actual random hidden-animal target/spot inspection with reveal animation, 4-find round success, persistent stars, multilingual voices and no reading dependency. Uses platform canvas and protected pointer. | Distinguish selected animal spoken clues from accidental reveal guessing, repeated target fairness, landscape/800×480 hitboxes and hint, microphone/audio conflict, persistent child progress and full 4-find finish |
| `enciclopedia_greia` | **KEEP / DRAFT CANDIDATE — SOURCE-REVIEWED; FLAGSHIP CONTENT** | 43 registered authored pages over nature/science/body/machines/history, linked to research authority; aligned 246 IT/EN text keys and 200 mapped localized audio cues; resource-bounded artwork and runtime-neutral semantic input. Fixed internal page-history Back illegally drawn and received inside Greia-owned Home+Back hitbox: moved to independently authored content button, which is behind no protected hitbox. | Full 43-page navigation sweep and evidence that new top-right return does not occlude content controls; real narration mapping/assets and hard-fact conceptual correctness, keyboard/controller and finger, offline resume, 800×480 layout and low-resource cache footprint |

**Five new sorted draft candidates:** Marble, Memory, Contrari, Woodland, Encyclopedia. **Source-reviewed draft total 27; withheld 8; none approved, nothing deleted, official release still `status="draft"` and fails closed.** Newly withheld Bridges/Nanna join previous six. Source-only portfolio curation is not a release vote.

**New/updated tests committed, not executed:** `test_activity_nanna_delle_nuvolette.py` (supported API + chrome/focus cancellation); `test_activity_mondo_contrari.py` (exploration earned once, 5-category all-completion, supported adapter + safe pointer); `test_costruiamo_ponti_contract.py` (real block transition and manifest honesty); `test_activity_la_discesa_della_biglia.py` (letterbox protected region, out-of-bounds and drag-kind identity, honest level count); new `test_activity_memory_meraviglie.py` (outer-loop Quit/Escape); new `test_activity_enciclopedia_navigation.py` (trusted chrome cannot be captured by page history). Existing `test_activity_enciclopedia.py`, `test_activity_enciclopedia_visual_foundation.py`, `test_activity_nascondino_bosco.py` remain essential.

**Next:** P7 source-review **remaining ten** entries (inventory authoritative at PLAN §5). Continue non-destructive source work and consolidate the existing one-run desktop acceptance list rather than creating a fresh run. Do not approve draft status without real launcher/gameplay/audio, and do not conflate Acer installer/first-boot acceptance with this product content slice.



### 2026-10-08 — P7 batch 6 final ten: complete 45-entry source review, draft-only 32/44 child catalogue

**Source baseline:** `d3e5867e0ee0c91549354ee0159431c7abd754d9`. **Repairs committed:** `2f27aab0fabe9859f6518699ee963423dd0eb6e8` (Stars/Train identities + Home), `9dde5a48d4ab9a5f2e1e53e6623aeaac9b6c61e0` (Seasons events, Greia-safe canvas/input), `9102d887df41f915aae00e10c5a52149e3cfb477` (Submarine manifests + protected cockpit), `9c5d65e7e665f100aa896b7168c7b9bf3f26dc1f` (Train test fixture correction), and `37e05769f78a4a7104ef69929f6377357513aca4` (new bakery/greenhouse pure-model regressions). Both IT and EN locale string-key sets match in all ten manifests. Nine Activities have nonzero bilingual `locales/*/audio/activity-title.wav` metadata. Submarine has nonzero `audio/{it,en}/sub_title.wav` instead, and its mapped speech cues diverge **59 Italian versus 55 English**: English lacks `voice.btn.alarm`, `voice.creature.coral`, `voice.creature.kelp`, `voice.creature.krill`. Metadata and file presence are **not audible acceptance**.

| Activity | Source-review disposition | Gameplay / source findings / reason | Required real evidence |
|---|---|---|---|
| `officina_dei_suoni` | **KEEP / DRAFT CHILD CANDIDATE** | Genuine authored/adaptive D1 initial-phoneme picture selection, D2 sound/initial-letter discrimination, D3 initial-sound word-building, five challenges/session, scoped milestone and completion events, progress adaptation and audio cue queue. Distinct from syllable assembly, rhymes and letter catch. | Correct Italian/English phoneme-to-word mappings (especially consonant sounds vs letter names), all challenge positions/difficulty transitions, child comprehension with audio replay, low-end audio latency |
| `pasticceria_magica` | **WITHHOLD — no portable created cake** | Real three modes (exact ingredient orders, repeating visual patterns, open-ended decorate/serve), pure bounded topping model, legitimate events on matched recipe/pattern. However free creativity is only transitory animation: no publishable cake PNG or exportable recipe through shared Creations. Added tests for exact ingredient counts, pattern, free non-scoring behavior. | Produce child-selectable flattened cake snapshot and independent reopen/editability, import to other Activities, play/serve/pattern precision and source deletion durability before release promotion |
| `piccola_serra` | **WITHHOLD — incomplete persistence and shallow experiment** | Four plant types/pots, genuine multi-step seed→water→sun→water→harvest sequence, six-harvest finish and declared events. Uses deterministic correct-tool stages with no real growth-variable experimentation; `harvest_count` is saved on exit but NOT loaded, plants/pots not restored. Added pure-model full-harvest and invalid-tool tests. | Define honest plant-care vs science-experiment teaching claim, restore owned child garden/progress consistently or remove false continuation, validate 4 plants/6 harvests, audio, age, 800×480, durable checkpoint |
| `quattro_stagioni` | **KEEP / DRAFT CHILD CANDIDATE** | Authentic seasonal scene, four seasons and four weather states, day/night, apple and snowman side interactions. Previously declared season events never emitted, and initial selection used stretch-to-fill unsafe pointer. Now source emits only new-season and one-time full-cycle facts, letterboxed safely; moved celestial UI fully out of system Home region. | Child playthrough all seasons/weather/day-night, concept accuracy and how learning surpasses button browsing, Italian/English spoken labels, screen-size/long-run particle budget, trustworthy Home behavior |
| `sillabe_magiche` | **WITHHOLD — bilingual phonology coherence** | Explorer, catch-by-syllable and build-two-syllable word modes, real counter progression. But explorer consonant palette is hardwired to `CONSONANTS_IT` in English, while English word set contains multi-letter chunks such as `RAB/BIT`, `ROCK/ET`, `TI/GER`; children may hear inconsistent phoneme and syllable teaching. English audiovisual mapping/recordings not equivalently proven. | Native bilingual phonological review, locale-specific consonant/syllable affordances and recordings, actual early-reading pedagogy, full each-mode word round and keyboard/pointer split |
| `sottomarino_giramondo` | **WITHHOLD — marine overlap + audio/event gaps** | Rich cockpit 3D-like marine biome, steering/throttle, sonar/horn/lights/bubbles, spoken facts, recurring Captain orders and creatures/encounters. **No Creations artifact**, so removed misleading `create` category. Removed nonexistent `submarine.depth_milestone` and spammy undeclared `submarine.maneuver`, declared real `submarine.order_completed`. Protected platform Home from cockpit pointer, cancelled drags on focus/resize. Four English speech cues missing vs Italian (see above); existing marine candidates need child-facing differentiation and depth-control access review. | Live both-locale spoken cues, real biome/depth reachability, no duplicated encounter event, gesture/drag, educational facts and comparisons vs Aquarium/Orca/Delfino, frame/voice queue on Acer |
| `specchi_magici` | **KEEP / DRAFT CHILD CANDIDATE** | Five actual procedurally authored symmetry difficulty tiers, reflected piece shapes/colors/orientations, placement/undo, challenge adaptive history and honest completion events. Distinct mathematical geometry use. | All D1–D5 solvability without ambiguous rotated duplicate pieces, 800×480 accurate tap regions, fair hints/undo, low-end frame, audio cues, saved progression |
| `stelle_incantate` | **KEEP / DRAFT CHILD CANDIDATE** | Real ordered point-to-point constellation creation, star ordering and educational facts with research assets, saved completed ids and progress facts. Repaired false Activity-owned top-left Home click exit; fresh session identity on replay prevents dedupe and restores fact-announcement state. | Full constellation catalogue and facts, visual star numbering, no overlap with Greia top-left, progress/restart events, localized narration, touch/keyboard on 800×480 |
| `treno_numeri` | **KEEP / DRAFT CHILD CANDIDATE** | Fruit load/count, station addition and quantity matching with animated carriage, completed-station events, real terminal journey; stronger object movement/story than pure counting menus. Fixed globally fixed station/journey idempotency keys to unique per new journey, preserving stable key inside that journey. | Test both addition/cardinality, replay with distinct new milestones, no double star on celebration, layout 800×480, voice guidance, 5-station victory, visual/accessibility comparison vs counting Garden/Bosco |
| `workshop_settings` | **SOURCE-REVIEWED / SYSTEM-CONTENT EXCLUDED — NOT A CHILD RELEASE CANDIDATE** | My Greia Settings: per-profile avatar, theme, interface size, removable-media wallpaper import using privileged declared `customization.manage`, `profile.manage_own`, `removable_media.read`. Parent-management/trust entry, **not** a normal child learning Activity or broad built-in entitlement. Excluded from the child-content first-party roster regardless of UI polish; must independently prove Parent policy/privilege lifecycle, media-reader errors/unplug, safe child-facing visibility and platform context. | Shell visibility/authority and Parent policy negative tests, parental authenticated gates, device card/removable media lifecycle, no privilege escalation; clarify separate system packaging, not counted as approved 33rd candidate |

**Final P7 source-inventory arithmetic:** 45 reviewed = **44 child-content + 1 My Greia/settings**. Of 44 child-content, **32 sorted draft candidates + 12 withheld**. The system/settings Activity is excluded by product category. **0 release-approved.** Add only Officina, Quattro Stagioni, Specchi, Stelle, Treno to `build/first-party-release-activities.toml`; official `[release].status = "draft"` remains fail-closed. The five withheld/excluded this batch do not disappear from dev source installs.

**Acceptance debt is NOT closed:** all six source-review batches are complete, not independently tested. New tests (Stars/Train/Quattro/Submarine, Pasticceria, Serra) have been committed but have not run in the canonical checkout. Existing `tests/test_activity_officina_dei_suoni.py`, `test_activity_sillabe_magiche.py`, `test_activity_specchi_magici.py`, `test_activity_stelle_incantate.py` and others remain essential. Advance P7 to **SOURCE REVIEW COMPLETE / LIVE ACCEPTANCE OWED**, keep P1–P6 source-WIP and P8 NOT STARTED. No official release approval, installer build, hardware flashing, GUI screenshots or audio approval occurred.

**Next step:** compare the source dispositions against the actual age-relevant child experience in the **one** existing `docs/testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md` after local agent availability. Triage all test failures by true source owner rather than increasing retry gates. Fix highest-severity withheld failures first (bilingual phonics, missing story/artifact publisher, greenhouse persistence, submarine EN audio) only with owner-authorized quality improvements. Independently finish Acer lifecycle evidence per lifecycle plan.


### 2026-10-08 — System My Greia reconciliation + My Time incubator + visual library browser (SOURCE-WIP)

**Reconciliation:** the accepted `docs/product/MY_GREIA_SETTINGS.md` makes My Greia a child-facing, low-risk, profile-scoped personalization Activity. The P7 source-review bookkeeping had incorrectly risked treating its exclusion from the *educational game* roster as exclusion from production images. The platform now defines one immutable `MANDATORY_SYSTEM_ACTIVITIES` entry in `src/greia_platform/activity_release.py` and the official `tools/stage_release_activities.py` stages it next to approved curated child content, then validates the complete installed index. A curated child roster claiming either the reserved My Greia ID or its package name is refused; missing/invalid trusted source refuses staging atomically. Existing `PIP_RELEASE_BUILD` and `status="draft"` fail-closed behavior remains unchanged. Source/test repair commits: `6ea846cf`; **not runtime/installed/security accepted** until the local negative/grant-policy acceptance is run.

**New cross-product Time direction:** documented in `docs/product/CHILD_TIME_AND_ROUTINES.md`. The initially implemented `activity_incubator/tempo_di_greia/` has a monotonic stopwatch, bounded pauseable countdown, actual read-only analogue/digital clock, independent +/−15min practice clock, UK/IT-en localized labels, responsive Greia-safe canvas and authored candidate clock icon. Source commits `55c0d7a2`, `ad6cfea4`, `9aa37653` (later replaced broken candidate icon), `653f3a6b` (byte-verified rendition), `63528a39` (locale bundles), `bf81be6f` (source incubator relocation), `90b7552e` (time rendering/Italian weekdays). **No prerecorded voice, title WAV, offline-clock validity trust, background alerts, calendar, chapter-style pedagogy or GUI/child acceptance yet.** The prototype was deliberately moved OUTSIDE `activities/` to avoid breaking first-party spoken-label and fixed readiness-list contracts or silently shipping a poor prereader Activity. Its test remains in `tests/test_activity_tempo_di_greia.py` and uses direct incubator imports.

**Shared generic source art discovery:** `tools/visual_authoring_library.py gallery --output ...` now produces an offline browser with large native-source thumbnails and search/status/collection filters using the **same** 101-index six-TOML source metadata. No duplicate runtime registry, cloud browser or child-machine SVG decode. Source commits `4b30dedc` and `445500a0`; `tests/test_visual_library_gallery.py` covers source containment, safe escaping, duplicate IDs and non-overwrite. Visual style/asset admission remain unchanged; no source/browser screenshots reviewed.

**Source count unchanged:** 45 built-in Activity packages; 32 ordinary child-content draft candidates, 12 withheld child Activities, 1 mandatory trusted My Greia system Activity, plus 1 unpromoted Time incubator. **0 release approved, 0 new live acceptances.** Next action is focused GitHub-head source tests plus protected-view/clock/gallery browser captures, followed by accumulated original Creations/Activity acceptance. Keep independent first-boot Acer lifecycle blocked until its own owner-authorized test.

**Addendum 2026-10-08 — source/test pin correction:** final Time implementation commit `cf8c210cb1c2a2267c213191013fd50e6c1b0929` reduced idle dial redraw to 1 Hz (10 Hz while measuring) and added dual-viewport protected-region regression. The canonical accumulated local-agent procedure now pins that exact source candidate and includes My Greia source-package staging and Time/gallery checks in §2ae. GitHub tree static inspection at documentation commit `b9eb38b2`: original 45 built-ins remain, exactly nine Time incubator assets/files exist, 32 unique sorted draft games, trusted My Greia reserved outside roster; IT/EN Time strings have 24 matching keys; icon runtime blob SHA `1c5a86d04901aa569348a684ac342ac58fbdb36d`. These are **source-tree consistency observations only**, not tests, browser or voice acceptance.

### 2026-10-08 — Second local-agent resume / headless harness root cause fixed in source

Owner-agent report at `b96b08d3`: Time regression **10/10 PASS**, full
renderer-state capture **11 PNGs** (IT/EN and clock/timer modes), My Time
bootstrap no localization exception; gallery HTML generated and **101/101**
source preview URLs resolved offline. The agent could not capture actual
interactive browser screenshots because no browser was installed; this remains
visual acceptance debt. Original evidence `time-and-system-acceptance-evidence.zip`
and second `time-resume-acceptance-evidence.zip` remain local to owner agent;
not directly read in this GitHub session.

**New defect was the test harness, not the Activity:** old
`tools/headless_greia_activity.py` launched only
`greia_simulator.python_activity` (client) yet waited for nonexistent
remote server at 8767. Replaced it with a focused runner that owns an ephemeral
`SimulatorRemoteBridge` before child spawn, retains process logs and PNG
evidence, cleans temp session state and supports synthetic input. Source commits
`329b41f5` / `4fd80b6d` add the real Pygame/bridge smoke regression. Fixed
gallery semantic visibility `4d5c0de5`: clock is already in shared asset
TOML tags, but not displayed in the previous gallery title; now shows tags
alongside human-readable roles and canonical IDs. **These new changes have NOT
been executed by the agent or full checkout.** Retest only the two modified
suites and IT/EN headless probes; keep old green staging/domain proofs. No
release promotion, title audio, hardware or child-comprehension approval.

### 2026-10-08 — Continued My Time child UX, 114-art-family reviewer and agent execution queue

The owner requested that GitHub implementation continue while the local agent
is unavailable, and that **one living task list** be maintained for later
non-destructive local work. Created
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` with GLA-001–009,
explicit prerequisites, minimum source SHAs, commands, pass/failure
predicates, evidence ZIP expectations and authorized **queue-only**
status/evidence commits. This is a local execution queue subordinate to the
existing product, architecture, Creations and installer plans—not a new
competing implementation plan.

**My Time**, still in `activity_incubator/` rather than 45 first-party
packages: source commits `31e5d1ab`, `fae0fb2d`, `e324e3ad` and
`3a9b9b8b` add pure quarter-hour dial hit geometry, four large visual
practice markers, meaningful pictograms for Clock/Stopwatch/Timer and
Play/Pause/Reset, bounded non-audio finish stars, visible arrow/Tab
focus and Enter activation. Source tests cover actual quarter-hour
practice changes vs immutable read-only real clock, mouse/keyboard
interactions, and the renderer. **New tests and new pixels are not yet
executed/reviewed**; the prior `PASS@b96b08d3` Time 10/10 suite
does not verify the updated source. Still no prerecorded IT/EN voice,
offline RTC confidence, My Days calendar, Time Workshop, background
alarm/suspend service or installed release.

**Visual coherence tooling**: `tools/visual_family_contact_sheet.py`
(and `tests/test_visual_family_contact_sheet.py`) creates one authoring-only
source-truth comparison sheet from 39 actual catalogued core icons,
45 ordinary built-in Activity icons and 30 canonical cast expression
PNGs, each at 128/64/48px; commit `0a09eaf4` fixes scale placement.
No art masters, semantic indexes or child's runtime changed. Local agent
GLA-008 must run and review the real generated PNG before visual
design decisions are declared accepted.

**Previously reported green evidence unchanged:** mandatory My Greia
appeared as installed package 33 under developer staging, old Time
10/10 model and 11 SDL captures, 101/101 gallery source preview
paths resolved at earlier SHAs. The owned HTTP bridge probe, revised
Time UI and art-family review remain local-agent queued/source-WIP.

**Source follow-up 2026-10-08:** `33b0ddc6` defers consuming a silent
timer-finished one-shot until the child revisits the Timer tab. This avoids
silently losing the only finish cue while the other two modes are visible.
It is not a background notification and is untested in the current
local-agent session; GLA-003 covers returning from Clock/Stopwatch after
the countdown elapses.

### How to maintain this file

Append a dated entry to §C after every substantive session. Include commit SHA, files changed, actual test command/output and environment, screenshots reviewed if any, real remaining blockers, and **one precise next step**. Update current-state tables in §A/B as facts change; keep dated entries immutable except explicit factual corrections. Every Activity review gets one evidence-backed decision; reference source snapshots instead of pasting thousands of lines. Update `HANDOVER.md` and the appropriate existing architecture/lifecycle ledger without duplicating hardware evidence or inventing another orchestration process.

### 2026-10-08 — Practice dial hour and minute touch separation (SOURCE-ONLY)

In the existing incubated My Time Activity, 12 hour selections occupy the
inner dial ring, and four quarter-hour minute selections occupy the outer
dial ring. A deliberate radial gap is inert. The illustrated 12-hour hand
keeps its current AM/PM half-day, and neither input can mutate wall time,
stopwatch, countdown, Parent time policy or platform Home.
Model and actual Activity press-path regression cases added, but **not
executed locally in this GitHub-only session**. Local-agent GLA-003 now
checks both rings in IT/EN at 1024x600 and 800x480. All old and outstanding
voice, source acceptance, Shell, physical and release boundaries remain;
do not promote from incubator.


### 2026-10-08 — Practice hour hit-area/date-label follow-up (SOURCE-ONLY)

Corrected the inner-hour hit radius to include the dial's visible numeral
positions, while keeping a gap from the outer minute ring. Practice now
shows its practice label instead of a misleading real weekday/date when
imaginary time crosses midnight. Additional source assertions cover tapping
a visible hour numeral and the inert gap. No new source or GUI acceptance
was executed; GLA-003 remains open.


### 2026-10-08 — My Time prerecorded voice coordination source (not yet voiced)

In `activity_incubator/tempo_di_greia/`, added a pure, injected
`TimeSpeech` coordinator and a Pygame-local `LocalTimeSpeechTransport`
for cached `LocalizedResources.audio_cue` playback. The coordinator keeps
at most one queued first-use instruction, replaces obsolete mode/help
speech, makes a timer-finished cue supersede pending help, and stops its
channel when the Activity exits. First-use guidance is deferred until
after the first usable READY frame. A large icon-only replay control is
drawn and keyboard-focusable **only when** the current language's real
recording is mapped and available. Cross-language fallback of required
speech is explicitly rejected.

Added `tests/test_activity_time_speech.py` pure fake-transport regression
cases and a Pygame Activity replay-hit case in
`tests/test_activity_tempo_di_greia.py`. The real IT/EN locale audio tables
remain empty; no voice files, provider calls, generated previews, real
listening, GUI screenshots or source test executions happened here.
Consequently the Activity remains in the incubator and pre-reader
readiness/release promotion remain BLOCKED. GLA-003 now includes both
source suites; GLA-005 remains blocked on approved VoiceEngine production
and human listening. System/Parent time policy and installed lifecycle
were not modified or accepted.


### 2026-10-08 — Greia-owned locale-safe audio and lazy prereader cues (SOURCE WIP)

The incubated My Time spoken-guidance adapter no longer decides language
by testing the parent folder of an audio file. Platform localization owns
this decision through `LocalizedResources.audio_cue(...,
allow_fallback=False)`, while normal legacy per-key fallback is unchanged.
This permits validated package audio under any authored directory without
unintentional Italian/English instruction swaps.

Playback now indexes its at-most-seven semantic cue paths at composition,
lazily decodes on first actual playback only after the first READY frame,
reuses each decoded clip, and suppresses further attempts when decoding fails.
Keyboard UP/DOWN Practice activation now updates voice context. Focused
platform fallback, Activity audio adapter and keyboard cue tests were added.

**Evidence:** GitHub source edits and readback only; no complete-checkout
Python/unit/Simulator/screenshots/audio provider/listening/hardware tests.
The new source remains in `activity_incubator/` and P1–P8 release
boundaries remain unchanged. The single deferred queue
`docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` has an exact four-suite
GLA-003 source step plus subsequent hands-on and audio acceptance.


### 2026-10-08 — My Time first-frame voice and terminal-event safety (SOURCE-ONLY)

The incubated `TimeSpeech` coordinator now defers a timer completion
that is already pending before the first Activity frame, and emits it only
after `mark_activity_ready` has been published. This terminal case
supersedes any launch greeting or queued first-use instruction, preventing
invisible or misleading speech. Missing/corrupt greeting playback no longer
consumes the first essential instruction. Missing recordings never
masquerade as successful replay; closing the coordinator prevents further
playback. No extra audio backend, cloud synthesis or platform time policy
was introduced.

Added pure coordinator tests and an `TimeActivity.run()` regression
that drives a deterministic, already-expired countdown through frame
presentation and READY with a fake audio sink.
**Evidence:** GitHub commit/readback only, tests not executed; prereader
UX, real IT/EN voice production, desktop Simulator, actual Shell and
installed hardware remain unverified. GLA-003 in the single existing
local-agent queue is responsible for these exact suites. My Time remains
`activity_incubator/` only; no release acceptance or hardware claims.


### 2026-10-08 — P3 universal Gallery child-first rendering/modal source repair

**Workstream returned to the original Creations plan; no new Time features.**
Traced `CreationsGalleryScreen.draw` →
`CreationsPygamePainter.draw/_grid/_detail` →
`CreationsGalleryController` and verified two P3 defects that threaten
first-use reliability and child input isolation:

1. When a library or filtered picker had zero compatible Creations,
   `_grid` used unbound local names `width` and `height`, raising
   `NameError` while drawing the expected first-use empty state.
   Corrected by sourcing dimensions from the actual surface. A follow-up
   placed the empty-state caption above (rather than over) the footer
   navigation on 1024×600 and added a real-Pygame position regression.
   Empty-state art now reflects an audio-only or text-only picker
   instead of displaying a misleading picture symbol.
2. During library deletion confirmation, the keyboard event handler
   could still send `P`/`R` and other input into the underlying
   detail view; keyboard-only users also could not explicitly confirm.
   Confirmation now consumes background keys, defaults to the safe
   Cancel focus, and requires Right-arrow then Enter for irreversible
   deletion. The chosen action gets a visible non-color-only outline.
   Picker selection/grant ownership, Parent permissions, and the
   storage deletion service were deliberately not modified.

Added `tests/test_creation_gallery_render.py` that creates a real
profile-backed `CreationLibrary`, constructs the actual Gallery
Screen/Painter under dummy SDL, covers IT/EN empty first frames at
480×320, 800×480 and 1024×600, empty scoped audio picker and cancel,
safe keyboard deletion, and visual border pixel checks. Existing
`test_creation_gallery.py` and `test_creation_gallery_layout.py`
remain the complementary controller/layout suites. **All new tests are
committed but UNEXECUTED**; neither a dummy SDL screenshot nor a
green unit suite would replace a real Shell/Simulator view-and-listen
acceptance. P3 remains SOURCE WIP. The existing GLA-007 queue item
names commands, exact source SHA, stop conditions and required evidence.

**Outstanding original-plan obligations unchanged:** real trusted modal
focus/return, audible preview before selection, PNG/WAV/UTF-8 cross-app
round trips, safe deletion/recovery semantics (including the planned
undo window), 45-Activity visual/play/pedagogy acceptance, catalogue
signoff and installed Acer/ARM evidence. Do not silently classify
any as PASS.


### 2026-10-08 — P3 picker cancellation/expiry lifecycle source repair

Traced `ActivityCreationsClient.request_selection/poll_selection`
through the existing trusted `CreationSelectionCoordinator` /
Supervisor broker into the `ActivityCreationPickerHost` display
lease. The coordinator deliberately expires outstanding selection
requests after three minutes and independently supports client
cancellation, but the visible Shell picker was only closed in
response to child UI Back/Choose. This left a stale chooser
visible even after its grant authority was gone, risking a stranded
child and ineffective subsequent input.

The host now checks `pending_creation_selection` on every Shell
poll and closes an obsolete picker if its request is no longer
pending or its ID no longer matches. Stale close doesn't attempt
to cancel a settled request. This preserves the existing
one-request-per-session, fail-closed broker policy. Ordinary
child Back/Cancel still cancels via the trusted broker, but
even if the cancellation call fails, the host restores the
Activity's display/focus before reporting a typed failure.
No new IPC, modal backend, permissions or Activity API was introduced.

Four provider-free tests in `tests/test_creation_picker_host.py`
cover Activity cancellation, an actual
`CreationSelectionCoordinator` clock expiry, replaced request
identity and failure during cancellation with display
restoration. The updated GLA-007 current-source suite also
covers the existing Gallery first-use, audio-only preview
and delete-confirmation fixes.

**Verification:** source committed/readback only. Tests NOT EXECUTED
on a full checkout; trusted real Simulator and installed
Legacy-X focus/stacking, auditory preview, cross-Activity
PNG/WAV/UTF-8, recovery and curation remain OPEN. P1–P7
remain SOURCE WIP; P8 remains NOT STARTED; no release roster
status or hardware claim changed.


### 2026-10-08 — P6 actual child Home and catalogue design/organization

**Product emphasis restored:** simplify the existing first-party
Home and curation, not add more Creations/Time infrastructure.

Audited actual `activity.toml` presentation and education metadata
for each of the 32 **draft** child-release candidates, and the
existing Collection-first Home and adaptive grouping mechanisms.
The major source-organizational problem was **Create**: four
interactive games without a publishable child-made work product
were grouped beside genuine creative Activities. Corrected only
`[presentation].categories` for Acquario Magico (Explore only),
Cucciolo Mio (Play only), Specchi Magici (Learn only) and Torre
Forme (Play only). The six genuine Create entries are Painting,
Shape Garden, Storie della Mia Voce, Teatrino Fiabe, Writing and
Posta di Leo. All game identities, progression, saves, education
metadata, Parent policy and draft-release membership remain
untouched. No new root or child subcollection is invented.

`GreiaChildShell._home_collections` now inserts the existing
trusted My Creations viewer **immediately after Create**, instead
of appending it as the last Home destination. It retains a distinct
existing `backpack` icon (catalogue icon metadata synchronized),
so the prereader can distinguish making from finding saved work.
When no Create apps are Parent-visible, the library remains
present. `CollectionFirstHomeMixin._home_columns` now avoids
an unusable six-rows-high Home on 480×320/640×360 landscape,
with a more compact preexisting portal sizing option.
`tests/test_child_home_creation_organization.py` reads actual
roster/manifests, verifies the six Create entries and four repairs,
checks saved-work portal order/filter fallback/icon, and guards
the compact column count. **Added but not executed here.**

Visual editorial work is captured inside the P6 design record,
which classifies all 32 draft candidates across eight curriculum
families (math 6, literacy 6, nature 4, logic 6, creative 4,
care 3, music 1, action 2). These families are for release
review only, not a new runtime taxonomy. Play/Learn still have
dense listings and require actual screenshot/gameplay-based
complete semantic grouping decisions; fake tags or misc bins
remain disallowed. The art-family contact sheet also remains
unreviewed in the current checkout.

An accessibility omission was verified: the platform-owned
`assets/audio/system/launcher-labels/it` and `en`
directories do not yet contain `my_creations.wav`, despite
existing labels for other collections. GLA-010 is explicitly
BLOCKED on owner-approved voice authoring (Modal only if
authorized), real human listening and Shell playback. GLA-008
is now the prioritized Home/art/collection visualization and
organization acceptance task. Neither voice nor paid providers
were invoked.

**Result:** P6 stays SOURCE WIP / 0 release approvals, P7 is
still 45/45 source-reviewed with gameplay/visual evidence owed,
P8 not started. No hardware, release, trust, profile-policy,
activity distribution or live GUI/audio acceptance claimed.

### 2026-10-08 — P6 Play/Learn child-intent organization and meaningful visual vocabulary

**Scope:** resume original P6 design/navigation and P7 visual curation.
The 32 draft release candidates were reviewed against their
`activity.toml` presentation categories and semantic discovery hints.
Before this tranche, Play held 23 draft candidates and Learn 22.
Two correction-only manifest edits now make Voice Stories a
Create-only authoring tool and Four Seasons an Explore+Learn
observation experience; Play now has **21**, Learn **22**,
Create **six**. Both remain in the 32-candidate draft release.
No change to educational skills, age/difficulty declarations,
progression, saves, permissions or package identity.

The bounded P6 design record now maps **every** Play and Learn
draft candidate once to its primary *editorial* child intent
with no fake `music` or `stories` two-Activity category.
The current runtime `AdaptiveCollectionPlanner` requires
at most five non-singleton groups with exact coverage.
The actual roster cannot satisfy that honestly; therefore
the existing direct Activity-card display is retained.
This avoids creating a spurious navigation layer and honors
Parent filtering at ages 3, 4, 5.

`catalogue_view._DISCOVERY_ICONS` now maps the 13 existing
semantic group labels to **13 distinct existing Greia core
illustrations** instead of visually ambiguous shared
palette/book/puzzle shapes. This improves the shared group
art vocabulary when genuine subcollections are present,
without adding art assets or runtime image generation.
Both primitive and shared-art launcher Activity launch
badges now use the current UI locale (IT `Avvio...`,
EN `Starting...`) instead of hardcoding Italian.

New `tests/test_launcher_collection_visual_curation.py` reads
the **actual 32-file release roster and manifests**, checks
counts, category completeness/no duplicate for age-filtered
catalogues, real asset IDs and unique group silhouettes,
and bilingual feedback. This test is **NOT EXECUTED**.
GLA-008 in the one local-agent queue now records precise
source suites, actual 48/64px art comparison and IT/EN
Home/gameplay screenshots. No P6/P7 launch or final
visual acceptance, and no P8 approval is asserted.


### 2026-10-08 — P6 compact Home caption, actual local SVG render, live screenshot blocker

**Scope:** original child-facing P6 Home design, not picker/backend
work or another architecture. On the real existing Home renderer,
`my_creations` used a long localized single-line caption that
would be shrunk under the 800×480 and 480×320
six-portal layouts. Added `compact` to the existing
`_category_title` presentation function and enabled it
in `CollectionFirstHomeMixin` for canvas width <=800.
The shorter child-facing IT/EN/ES/DE/FR labels are
`Creazioni`, `Creations`, `Creaciones`, `Werke`,
and `Créations`; full normal text and prerecorded
semantic lookup remain unchanged. Added unit assertions
to `test_child_home_creation_organization.py`.
**Source committed; test NOT RUN.** No release
metadata, Parent policy, storage or routes changed.

**Real local rendering attempt:** this execution container
has Python 3.13, Pillow, CairoSVG, Xvfb/SDL libraries.
It lacks an installed `pygame` module and a full private
Greia checkout. Direct clone/archive from GitHub fails
due to network DNS resolution, not a Greia source
failure. The connected GitHub API allows only text
for source; it rejects binary image fetching. We
successfully fetched the genuine textual SVG sources
`assets/visual/ui/v0.1/portal_frame.svg` and
`activity_card.svg`, then rendered both locally
via CairoSVG+Pillow at 256,128,48px into a
clearly **non-runtime** Greia art comparison.
This proves only original authored-asset rasterization,
NOT a real Shell/App screenshot, NOT quality
of actual Activity icon illustrations, and NOT
target frame performance. GLA-008 real GUI
and the complete 114-asset contact-sheet review
remain OPEN. Do not mark any P6/P7 acceptance
as passed or count this as a Simulator capture.

**Next:** obtain a complete working-tree source/archive
(including PNG/SVG runtime assets) with Pygame
available in an authorized Python environment.
Run the existing `tools/headless_greia_activity.py`
and Shell/Simulator capture procedures rather than
building a second screenshot framework; review actual
child UI screens before further art polish.
Existing GLA-008 local-agent task already owns
exact commands, evidence and first failure handling.


### 2026-10-12 — Wave 37 child Activity hybrid-input and save recovery (GITHUB SOURCE WIP)

Reconstructed the interrupted Wave 37 functional-audit tranche from the
archived conversation while preserving the newer authoritative GitHub
`main` history. GitHub at start was `c177276e` (2026-10-08); the
archived local work did **not** arrive as a repository tree or evidence ZIP.

- `nascondino_bosco`: arrow navigation, visible selected-spot focus,
  Enter/Space inspection and victory replay, normalized touch events,
  mouse/keyboard/touch routed to the same `_inspect_spot`. Pure model
  now excludes already found spots from targets and rejects repeat awards.
- `piccola_serra`: selected pot focus, arrow selection, 1–4 tools, Tab
  plant selection, Enter/Space applying the existing staged growth model,
  normalized touch events. Uses existing pointer and model transitions.
- `acquario_magico`: bounded visible keyboard cursor, arrows, Enter for
  tank/creature/chest interaction, 1–3 tools, Space for night/day, C for
  chest, pointer and keyboard sharing the action dispatcher. Invalid or
  negative persisted counters recover to 0; absurdly large counters cap
  at 1,000,000,000 without crashing Activity initialization.
- New `tests/test_activity_wave37_input.py` covers keyboard-only complete
  Woodland and Greenhouse cycles, reward uniqueness, replay reset, keyboard
  Aquarium tool/chest interactions, cursor limits, touch normalization and
  malformed/capped persisted counters. Also guards SDL-generated synthetic
  touch mouse events (otherwise a single tap could apply a tool twice)
  with two dedicated regression methods. GLA-011 in the existing single
  local-agent queue owns full execution and bilingual gameplay evidence.

The follow-up `5f45d0da` hides completed woodland clues and moves
keyboard focus past already-rewarded hiding places, so the new unique
reward invariant is child-visible and usable rather than merely internal.

Source commits: `988bb134`, `26ec9870`, `8a0a4e54`, `b091f24d`, `5f45d0da`.
**Verification boundary:** GitHub source writes/readback only. This
execution environment has no private full checkout or Pygame and cannot
execute `make verify` or the Activity suites. Prior archived local chat
claims do not certify this reconstructed SHA. No graphics or voice changes,
no release promotion, no Shell/Simulator or installed x86/ARM acceptance.
P6/P7 original programme and withheld/draft memberships unchanged.


### 2026-10-12 — Missing Wave 36 functional-audit recovery on GitHub (SOURCE-WIP)

The archived conversation (Archive 33, Wave 34–37) describes Pygame source fixes,
executed local tests and complete local project ZIPs that were not committed to
the canonical GitHub branch. After delivering the reconstructed Wave 37 work
above, we compared Wave 36's four named behavior changes to actual GitHub
source and confirmed each was missing from the active Activity app.

Reconstructed on `main` (new code, not byte-identical replay of a missing ZIP):

- `memory_meraviglie`: arrow-key card navigation, visible focus,
  Enter/Space flips, T/G theme/grid switching, matching and restart
  routed through existing game transitions. Cleared cards are skipped;
  focus can escape a fully cleared column instead of remaining trapped
  by a row-stride step. Touch is normalized and synthetic SDL mouse
  events are filtered to avoid double flips.
- `treno_numeri`: keyboard crate selection/activation calls the same
  `_load_crate` path as pointer/touch, retaining model caps,
  flying-fruit feedback, one reward per completed station and
  idempotency-keyed events. Loading is disabled while traveling.
  Replay now uses one shared `_restart_journey` transaction, with
  selected crate focus visible in the existing renderer surface.
- `labirinto_magico`: `trigger_move` refuses a second movement
  command while the player is traversing queued slide waypoints,
  preventing a stale-grid recomputation from replacing the live path.
- `stelle_incantate`: directional keyboard selection, numbered
  shortcuts, Enter/Space connection and state-aware Next/replay,
  visible selected star, F fact playback, normalized touch with
  SDL synthetic-mouse deduplication, and locale-strict
  `audio_cue(..., allow_fallback=False)` for existing fact voice.
  No audio media were generated or modified.

A new provider-free eleven-method test module
`tests/test_activity_wave36_github_recovery.py` exercises an entire
keyboard Memory round, mismatches and theme/grid changes, a five-station
Train journey with unique event counts, the Maze mid-slide lock, and a
Stars round/fact locale fallback. These tests are committed but **NOT
EXECUTED** because this connector-only environment lacks the private
complete checkout and Pygame; the archived local 78/78 + 16 launch
results are HISTORICAL evidence against a different tree.

Source commits: `8070cfd3`, `5907b0e7`, `3a73add0`,
`d3cf6790`, `93f30a7f`, `b73dde9e`, `a3dc7ea9`, `1677613a`, `1e0392c5`, `a6c7fead`.
The single pre-existing local-agent queue now contains GLA-012 with
exact commands and supervised bilingual complete-cycle expectations.
No P6/P7 release promotion, no graphics/voice acceptance, and no
hardware/lifecycle completion is claimed. Waves 34–35 from the
archived local tree still need a separate GitHub behavioral
reconciliation; do not assume their claimed fixes exist in main.


### 2026-10-12 — Archived Wave 34–35 GitHub recovery: Clinic and Orca (SOURCE WIP)

Continuation of the archive-to-GitHub functional-drift reconciliation,
without drawings, asset review, new narration or providers:

- `clinica_cuccioli/clinic_app.py`: the current GitHub version only
  responded to the mouse and Escape, despite a `hybrid` input profile.
  Added directional keyboard tool focus, explicit Enter/Space selection
  followed by separate Enter/Space patient treatment, terminal replay,
  and touch input with SDL synthetic-mouse deduplication. All successful
  treatments still flow through `ClinicSession.use_selected_tool`
  and the existing Greia event/progress owner. The focus indicator
  uses the existing tool geometry on the Activity reference canvas.
- `baia_delle_orche/orca_app.py`: both spoken-fact entry points read
  `resources.locale`, which does not exist on `LocalizedResources`,
  and therefore silently defaulted to Italian even in English. They now
  share a single fact dispatcher using
  `resources.context.selected.value`. Keyboard key 6 reaches the
  sixth fact tool. Drag handling previously incremented `total_cuddled`
  and replayed sounds every motion frame; a per-gesture orca identity
  set now permits only one cuddle and event per orca per press/drag.
  Finger and synthetic mouse duplications are suppressed.
- New `tests/test_activity_wave34_35_github_recovery.py` contains
  five provider-free regressions: complete five-patient Clinic
  keyboard treatment and replay, selection-then-apply semantics,
  touch normalization/deduplication, exact English fact locale,
  and per-gesture cuddle event/audio bounds.

Source commits: `e2e5a733`, `57bf0c0a`, `2cfcde61`.
**Current evidence:** committed GitHub code and connector readback
only; these tests and real Pygame/Simulator/speaker sessions remain
UNEXECUTED on the current main. GLA-013 in the sole local-agent queue
owns exact execution and human listening. Source for the other
archived Wave 34/35 fixes (Momo speech, Solar System Spaceship,
Bridges, Marble) has not yet been reconciled with GitHub main.
P6/P7 draft/withheld and all OS release/hardware gates remain unchanged.


**2026-10-12 post-review correction:** Stars now ignores numeric shortcuts outside the active constellation's star count; otherwise a shortcut for a nonexistent star could move focus out of range and crash when rendering the focus indicator. Source `a3dc7ea9`; regression `1677613a`, still UNEXECUTED.


**2026-10-12 additional functional review:** Treno Numeri's celebration particles were appended repeatedly but not cleared between stations or replay journeys. The app now caps them at 96 and clears transient lists during replay (commit `1e0392c5`, regression `a6c7fead`). Existing animation/assets remain untouched. Tests remain UNEXECUTED on the new SHA.
