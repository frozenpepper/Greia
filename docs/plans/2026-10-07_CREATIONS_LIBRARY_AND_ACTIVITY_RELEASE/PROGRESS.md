# Greia Creations + Activity Release — Progress / Resume Ledger

**Status:** ACTIVE, source-first. No first-party release approval implied.  
**Master plan:** [PLAN.md](./PLAN.md)  
**Run this ledger with:** `AGENTS.md` + `HANDOVER.md` + current `main`.

## A. At-a-glance checkpoint — 2026-10-07

- New program: **P0/P1 initialization in progress**.
- First-party `activities/` snapshot: **45** directories = **44 child-content Activities + 1 My Greia/settings Activity**. The earlier catalogue strategy's 41-item figures are historical.
- Catalogue handoff: four October 1 action/strategy games added. **Colline Allegre script entrypoint broken** via relative imports in top-level `colline_app.py`/related modules; **Quattro Amici** manifest declares D1–D5 but its model config has D1–D4. These are **source inspection findings**, not claims that a fresh production launch test ran.
- Release composition: still source-tree driven; explicit release allowlist/manifest **not implemented**.
- Cross-Activity artifact sharing: **not implemented in real Activities**. Current Painting/Writing/Voice/Theatre use Activity-private persistent file storage. Do not claim user-visible picker/viewer, broker authority, or backup integration exists.
- OS first-boot/installer: independently **OPEN** on the Acer route; read existing lifecycle plan before any hardware action.
- P1 **trusted-only source foundation committed**: `creation_capacity.py`, `creation_media.py`, `creations.py`, `test_creation_library.py`; still no broker, SDK, picker, Activity integration or full-project acceptance. Local mirrored headless test suite 12/12 PASS; actual Greia checkout acceptance still owed.

## B. Phase delivery status

| Phase | Scope | Current state | Release evidence still owed |
|---|---|---|---|
| P0 | repository/source baseline + triage | STARTED | consolidated current-head actual gameplay audit |
| P1 | typed creation repository, codecs, adaptive capacity | SOURCE WIP (trusted core committed; 12 local mirrored tests PASS) | full Greia checkout tests, error/race/recovery, real budget calibration |
| P2 | permissions/manifest/broker/SDK | NOT STARTED | session-authorized cross-Activity flow, adversarial isolation |
| P3 | universal picker and My Creations viewer | NOT STARTED | screenshots, huge thumbnails, playable WAV, delete UX |
| P4 | Painting–Shape Garden–Theatre PNG round trip | NOT STARTED | save/import/edit/export/reopen snapshots |
| P5 | voice/music and writing/text interoperability | NOT STARTED | real recording preview, text import/export |
| P6 | explicit release catalogue and adaptive grouping | NOT STARTED | built-index exact match, Parent policy |
| P7 | deep per-Activity quality review (45) | NOT STARTED | 45 evidence-backed dispositions |
| P8 | end-to-end release and physical acceptance | NOT STARTED | real Acer and cross-platform acceptance |

### Activity release-review coverage

**45/45 entries inventoried in PLAN §5; 0/45 release-reviewed, 0 release-approved.**

No new Activity is dropped or silently approved merely for having unit tests. Record each review and disposition with evidence under §C entries. Historical R7.3 structural migration PASS does not equal release UX PASS.

### Media interoperability state

| Producer | Consumer | Kind | Status |
|---|---|---|---|
| Painting | Painting | PNG bitmap editable again | NOT STARTED |
| Painting | Shape Garden/stamps | PNG as background/base | NOT STARTED |
| Shape Garden | Painting | flattened PNG composition | NOT STARTED |
| Painting/Shape Garden | Teatrino Fiabe | PNG backdrop | NOT STARTED |
| Storie della Mia Voce | Teatrino / compatible composer | WAV voice | NOT STARTED |
| Writing | Writing / genuinely compatible text consumers | UTF-8 | NOT STARTED |
| Any declared writer | My Creations viewer | large visual/audio/text previews | NOT STARTED |
| My Creations viewer | library | safe deletion/reclaim | NOT STARTED |

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

### How to maintain this file

Append a dated entry to §C after every substantive session. Include commit SHA, files changed, actual test command/output and environment, screenshots reviewed if any, real remaining blockers, and **one precise next step**. Update current-state tables in §A/B as facts change; keep dated entries immutable except explicit factual corrections. Every Activity review gets one evidence-backed decision; reference source snapshots instead of pasting thousands of lines. Update `HANDOVER.md` and the appropriate existing architecture/lifecycle ledger without duplicating hardware evidence or inventing another orchestration process.