# Greia — Current Engineering Handover

**Updated:** 2026-08-29
**Canonical repository:** `frozenpepper/Greia`
**Canonical branch:** `main`
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**
**Current parallel visual focus:** **Encyclopedia E3 six-section source reauthoring after owner approval of corrected golden-master direction**
**Active Activity-modernization plan:** `docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md` (one Activity at a time, sequential, scoped to R7.3)
**Purpose:** short current continuation contract. Detailed chronology belongs in active plans and dated reviews/handovers.

Historical long-form root state remains preserved under:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

and in Git history / dated reviews.

---

## 1. Resume rules

Before substantive work, read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
```

Then load the relevant OS/Activity/visual/voice skill.

For R7 display/session/input work also read:

```text
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md
docs/reviews/2026-08-29_R7_R73_TRUSTED_CHROME_SOURCE_TRANCHE.md
docs/reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

For visual work also read:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Work on current `main`, refresh before writes, preserve concurrent work, and do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution.

No PASS claim may be generalized beyond the exact source/evidence lane that actually executed.

---

## 2. Platform state

R7 remains the first incomplete blocking platform phase. Current installed Greia still uses the provisional Xorg/xinit compatibility path while the ADR-0014 target direct/appliance display/session/input implementation is resolved.

The 2026-08-29 R7 review clarified the execution architecture without closing R7:

- Activity rendering is backend-independent by invariant. Ordinary Pygame/SDL drawing is valid; Activities must not know/select/probe X11, Wayland, DRM/KMS, evdev/libinput or backend-specific environment.
- Do **not** invent a Greia drawing API. SDL/Pygame remains the renderer abstraction.
- `src/greia_launcher/display_session.py` is the polymorphic runtime seam. Complete `DisplaySessionCoordinator` / `DisplaySessionBackend`; do not create a parallel giant HAL.
- `LegacyXDisplaySessionBackend` is the current compatibility implementation. A direct/compositor implementation must sit behind the same contract and require zero Activity changes.
- **Backend independence must not create an abstraction tax.** Preserve precomposed opaque backdrops, converted surfaces, bounded caches, cached transforms, dirty/invalidation rendering, adaptive pacing and direct high-rate SDL pointer/text handling where safe.
- backend-private fast paths are allowed and expected below common contracts.

### R7.1 — Activity backend independence

Materially source-integrated on `main`:

- structured `greia_platform.activity_backend_policy`;
- standalone Activity validation enforcement;
- project validation enforcement;
- installed Python runtime validation;
- repository-wide `tools/audit_activity_backend_independence.py`;
- normal backend-neutral Pygame/SDL APIs remain valid.

No exact-current PASS is inferred merely from committed tests. R7.1 remains part of the current combined source gate.

### R7.2 — Legacy-X containment

Materially source-integrated; exact-current execution and Acer acceptance remain pending.

Implemented:

- generic launcher no longer owns native Xlib focus code;
- `ShellWindowController` is the one-shot Shell-window setup seam;
- installed composition selects `LegacyXShellWindowController`; development uses no-op;
- rich `presentation.py` now uses that same composed hook rather than importing the deleted `_set_x11_input_focus` helper;
- generic hardware watcher is backend-neutral; `hardware_session_legacy_x` owns current executable X selection;
- ordinary Activity Bubblewrap no longer grants `/dev/dri`;
- regression source denies ordinary `/dev/dri`, `/dev/input`, `/sys/class/drm`, `/sys/class/input` host authority;
- Xorg profile/package/service/Xwrapper/xinput/xrandr files remain explicit migration plumbing until replacement evidence exists.

Ownership inventory:

```text
docs/reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md
```

Acceptance:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
```

### R7.3 — trusted Greia Home + Activity ownership migration

R7.3 is **source-integrated but unexecuted/unaccepted**. Beginning this isolated source tranche does not retroactively close R7.2 and does not authorize final backend migration.

Trusted source boundaries now include:

```text
src/greia_platform/pygame_canvas.py
src/greia_launcher/system_chrome_legacy_x.py
src/greia_launcher/trusted_chrome_supervisor.py
src/greia_launcher/trusted_presentation.py
src/greia_launcher/system_chrome.py
src/greia_launcher/child_shell.py
src/greia_launcher/composition.py
src/greia_simulator/python_activity.py
build/overlay/usr/local/lib/greia-os/greia-x-session
tools/audit_activity_system_chrome_ownership.py
```

Architecture:

- `SystemChromeCoordinator` remains runtime/backend-neutral authority;
- `LegacyXSystemChromeBackend` is a migration adapter, not target architecture;
- current Legacy-X adapter owns one tiny launcher-process X11 window covering only `ActivitySystemChromeLayout.protected_region`;
- it does not copy Activity pixels, create a second Pygame renderer/process, or add a full-screen composition layer;
- chrome is drawn on show/expose only and input polling is nonblocking;
- `TrustedChromeActivitySupervisor` binds the chrome lease to the authoritative Activity session and existing graceful/forced stop lifecycle;
- the installed `GreiaChildShell` composes trusted chrome; its X-session fallback uses `greia_launcher.trusted_presentation`, which composes the same authority rather than falling back to plain unprotected presentation;
- the Simulator's trusted Python bootstrap independently draws/intercepts its compatibility Home above Activity code, so Activity migration does not remove Simulator navigation;
- Home is the first mandatory action closed here. Optional Back remains disabled in the installed supervisor until real launch-origin context is passed through the trusted boundary;
- chrome prepare/show/poll/cleanup failures fail the Activity path closed as `platform_failure`;
- failed preparation performs one bounded rollback attempt and returns the coordinator to `HIDDEN` when cleanup succeeds; if rollback fails, the coordinator remains `FAILED`.

The shared Activity canvas no longer renders trusted chrome:

- `PygameReferenceCanvas.present()` retains renderer-neutral safe/protected viewport geometry and Activity-local pointer presentation;
- the legacy `system_chrome=` keyword is temporarily accepted but ignored during catalogue migration;
- new Activity code must not use that keyword or the retired cooperative helper functions.

Explicit migrated exemplars now include:

```text
activities/writing/main.py
activities/painting/main.py
activities/labirinto_magico/maze_app.py
activities/volo_draghetto/dragon_app.py
activities/shape_garden/main.py
activities/storie_della_mia_voce/voice_app.py
```

For these Activities the edits were authority-only: Activity-owned Home drawing/hit-testing was removed while platform stop handling, safe-region geometry, gameplay, storage, microphone routing and direct Pygame performance paths were preserved.

Catalogue-wide authority inventory is now source-owned by:

```text
tools/audit_activity_system_chrome_ownership.py
```

It is AST-based and reports retired helper imports/calls plus lingering `PygameReferenceCanvas.present(system_chrome=...)` requests. The R7.3 acceptance protocol now requires:

```bash
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

with:

```text
Activity system chrome ownership audit: blockers=0
```

**Do not claim catalogue-wide zero debt yet:** the strict scanner has not executed on this current source state in this connector-only tranche. If it reports remaining callers, migrate exactly those callers without gameplay/visual rewrites, then restart the source gate on the new SHA.

Permanent hostile acceptance fixture:

```text
tests/fixtures/activities/r7_noncooperative_chrome/
```

It fills its complete SDL surface, draws no Home, ignores local input, ignores the graceful STOP marker and therefore can return only through trusted Home + bounded platform forced termination.

R7.3 regression source now includes:

```text
tests/test_system_chrome.py
tests/test_system_chrome_legacy_x.py
tests/test_trusted_chrome_supervisor.py
tests/test_r7_child_shell_trusted_chrome_composition.py
tests/test_r7_noncooperative_chrome_fixture.py
tests/test_activity_system_chrome_audit.py
tests/test_r7_first_wave_activity_trusted_chrome_migration.py
```

Exact source + Acer protocol:

```text
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

The protocol requires both Activity audits, Writing, Painting, hostile non-cooperative Home/forced return, 10/10 hostile cycles, crash cleanup and exact-device performance evidence.

**Important limitation:** shared X11 cannot become final hostile-third-party isolation merely because a sibling trusted window works against ordinary/non-cooperative Pygame content. ADR 0014 still requires replacement by the target DRM/KMS-centered direct/appliance architecture; a minimal compositor is allowed if measurement shows it is the thinnest practical trusted session path.

### Current provisional debt / constraints

- `greia-x-session` still contains literal `SynPS/2 Synaptics TouchPad` startup tuning. It is contained Legacy-X plumbing but should not survive into the final common input/session architecture.
- `Xwrapper.config` remains security-sensitive migration plumbing. Retaining Xorg as a target shipping architecture would require an explicit amendment/supersession of ADR 0014.
- a future Wayland Activity transport cannot simply pass host `XDG_RUNTIME_DIR`: Activity sandbox masks `/run`; project only the required compositor socket into a narrow child runtime directory.
- **tap-to-click policy contradiction remains unresolved:** current runtime source intentionally sets `touchpad_tap = true` after the 2026-08-23 Acer responsiveness fix, while `AGENTS.md` still says defaults off. Do not silently change working touchpad behavior inside R7; resolve product policy explicitly and align source/tests/docs together.
- catalogue-wide absence of retired Activity Home helpers remains **unverified until the strict audit executes**; do not infer zero from the six migrated exemplars or incomplete GitHub code search.

R7 invariants:

- Greia owns display/session authority;
- real Home/Back remain outside Activity rendering/input authority;
- protected system input is consumed before Activity delivery;
- controller discovery/normalization is platform-owned;
- ordinary Activities do not get raw `/dev/input` or DRM authority;
- backend selection belongs to trusted composition/profile, never Activity logic;
- no generic Python framebuffer/IPC pixel proxy;
- trusted chrome stays bounded/event-driven and must not impose permanent full-screen redraw/composition cost;
- Activity optimization opportunities remain available on every production backend;
- backend and hardware claims require exact-source evidence.

Primary authorities remain:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
```

The first-generation Acer Aspire One remains the low-resource floor.

---

## 3. Visual workstream

Stable architecture:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
```

Active art plan:

```text
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Current resume:

```text
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Existing accepted visual/runtime foundations remain valid: semantic visual catalogues, build-time PNG renditions, bounded Pygame cache, scene composition runtime, shared UI, canonical six-character cast, and previously owner-reviewed Activity productization work.

The current visual lesson is that mechanically complete Activities may still fail the product quality bar. Final real-world subjects must not default to crude programmer-drawn primitives merely because they are fast and deterministic.

---

## 4. Greia Encyclopedia v0.1 — current parallel Activity workstream

Activity:

```text
activities/enciclopedia_greia/
org.greia.enciclopedia
```

Frozen runtime scope:

```text
1 Home
6 section pages
36 factual entries
43 executable pages total
```

Prior owner-machine evidence established the mechanical runtime foundation: source gate at its accepted SHA, real Shell lifecycle, 43/43 reachability, 36/36 semantic ACTIVATE, 36/36 Encyclopedia-internal Back, protected Greia Home -> Shell. The headless page-transition capture race has since been repaired on `main`.

Golden-master direction is owner-approved after direct source repair. Current gate remains:

```text
E1 VISUAL/ASSET ARCHITECTURE:        COMPLETE
E2/E2R VISUAL DIRECTION:             OWNER APPROVED
LATEST CORRECTED RUNTIME PNGS:       REBUILD PENDING
LATEST EXACT-SOURCE SIMULATOR PROOF: PENDING
E3 SECTION-PAGE REAUTHORING:         ACTIVE
E4 FACTUAL-ENTRY MIGRATION:          BLOCKED UNTIL E3 REVIEW
```

Animals remains the section-world reference. Five authored section masters are on `main`:

```text
space_gallery_observatory.svg
earth_gallery_landscape.svg
body_gallery_discovery_room.svg
machines_gallery_workbench.svg
history_gallery_time_trail.svg
```

Source-review authority:

```text
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
```

The five section pages are source-wired through bounded `VisualLibrary`; missing E3 generated PNGs fall back to the prior procedural scene. Space preserves its live orbiting Solar System model. Runtime section art is either 0/5 during staged source work or 5/5 after generation; partial pack is forbidden.

Current Encyclopedia continuation authority:

```text
encyclopedia/HANDOVER.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/SOURCE_REVIEW.md
docs/plans/2026-08-28_ENCYCLOPEDIA_VISUAL_REAUTHORING.md
```

No local-agent visual-authoring task is currently authorized; the owner asked the primary agent to perform this work directly.

Narration remains separate from graphics acceptance. Canonical coordination is `encyclopedia/VOICE_RECORDING_REQUESTS.md`; only owner-listened `OWNER_ACCEPTED` clips may integrate and no runtime TTS is allowed.

---

## 5. Greia Voice Production Engine

Canonical authoring-time voice subsystem:

```text
tools/greia_voice.py
tools/greia_voice_core/
skills/greia-voice-production/SKILL.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

Boundaries:

- authoring-time only;
- canonical characters route through the Voice Engine, not Activity-owned TTS code;
- deterministic pedagogical/Dani system paths remain engine/provider controlled;
- Whisper verification is advisory and cannot owner-accept audio;
- one warm model/service path and cross-process lock prevent duplicate inference workers;
- every new recording requires human listening acceptance.

Owner workstation Apple-Silicon setup/doctor and narrow smoke generation succeeded. Shared character reaction/introduction library v0.2 has 192 owner-accepted clips; v0.1 remains retired historical evidence. Do not introduce voice models, Whisper or `tools/greia_voice.py` into child runtime.

---

## 6. Parent / microphone / updates

The external Parent client remains source-pinned/integrity-checked. Production pairing/encrypted transport remains separate from provisional development transport.

Runtime microphone cleanup remains platform-owned and lightweight by default; advanced processing requires explicit parent opt-in and real availability. Build-time prerecorded voice generation and child microphone capture are separate systems.

Current x86 update architecture remains provisional single-root; signed-update foundations do not authorize unsafe active-root mutation.

---

## 7. Immediate next work

### Blocking platform lane — R7

Do **not** restart R7.1/R7.2/R7.3 implementation from scratch and do not claim acceptance from committed source alone.

The exact next gate is combined evidence on current `main`:

```text
refresh current main
→ run the R7.3 focused source suite from
  docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
→ Activity backend audit (blockers=0)
→ Activity system-chrome ownership audit --strict (blockers=0)
→ if that strict audit reports remaining callers: migrate exactly those callers,
  preserve Activity behavior/performance/safe geometry, commit, restart source gate
→ make verify
→ if source green, deploy exact SHA to reference Acer
→ satisfy remaining R7.2 focus/pointer/Writing/Painting/crash/cycle evidence
→ prove trusted Home with migrated Writing + Painting
→ deploy hostile r7_noncooperative_chrome fixture
→ hostile fullscreen cannot cover Home
→ Home request -> fixture ignores graceful STOP -> bounded forced return
→ 10/10 hostile return cycles, no stale chrome/window/process
→ crash cleanup + next launch
→ exact workload CPU/RSS/latency/performance review
→ ACCEPT / REJECT / INCOMPLETE honestly
```

Only after the exact R7.3 gate is accepted:

1. promote the zero-debt Activity system-chrome rule into normal Activity validation;
2. remove the temporary ignored `PygameReferenceCanvas.present(system_chrome=...)` compatibility keyword after zero callers are proven;
3. preserve renderer-neutral protected/safe geometry;
4. continue R7.4 physical controller/system-input ownership and ADR-0014 direct/compositor backend evidence.

Do not combine Activity authority migration with unrelated gameplay/visual refactors.

Separate policy item: resolve tap-to-click `AGENTS.md` versus runtime-source contradiction explicitly; do not mutate R7 evidence opportunistically.

### Activity-modernization tranche (2026-08-29, plan-only)

A new Activity-modernization plan has been written to drive the R7.3 strict-queue Activity work, one Activity at a time, against current `main`:

```text
docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md
```

The plan is staged:

- **Stage A** — repair the two source-gate failures that are independent of Activity work: the `test_r7_noncooperative_chrome_fixture` docstring false positive, and the three contract tests that still expect the retired `-m greia_launcher.presentation` substring in `greia-x-session` (now `-m greia_launcher.trusted_presentation`). Both are pre-existing on the current SHA.
- **Stage B** — process the strict-audit queue (17 Activities) one at a time, with the lighter architecture/performance pass for the remaining 16 (excluding `enciclopedia_greia`, which is owned by the E3/E4 plan). One Activity per coherent commit. Ledger rows appended; HANDOVER updated at session boundaries.
- **Stage C** — final repository gate: `audit_activity_system_chrome_ownership.py --strict` → `blockers=0`; `audit_activity_backend_independence.py activities` → `blockers=0`; `make verify` → exit 0.

The plan is subordinate to this R7.3 acceptance gate. Do not begin Acer acceptance from the Activity-modernization plan; Acer acceptance continues to be owned by `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md`.

### Current Encyclopedia visual lane

Do **not** begin E4.

Next exact visual gate:

```text
build corrected six golden-master PNGs + five E3 section PNGs
→ verify all 11 current SVG/PNG renditions
→ focused Encyclopedia tests + required repository verification
→ commit/push complete current runtime-art state
→ fresh exact-SHA real Greia Simulator
→ review Home + all six section pages as one family
→ if accepted, close E3 and unblock E4
```

`docs/testing/GREIA_ENCYCLOPEDIA_V01_LOCAL_AGENT_NEXT.md` remains HOLD unless the owner explicitly changes the direct-work instruction.

---

## 8. Non-negotiable continuation reminders

- `main` is canonical; preserve concurrent work;
- GitHub is canonical persistence;
- no unauthorized hosted Actions execution/inspection;
- Activity `main.py` stays a bootstrap/composition boundary;
- Activities are display-backend independent;
- backend plumbing terminates in trusted Greia composition/adapters;
- Activities never implement the real Home/Back or own physical controller/device authority;
- Activities may reserve Greia protected geometry but must not import/call retired cooperative Home helpers or request Activity-side canvas chrome;
- performance is a correctness contract on the Acer floor;
- preserve Activity-side optimization strategies and allow backend-private fast paths;
- do not add generic pixel proxying, avoidable full-frame copies, continuous chrome redraw/composition or high-rate input IPC for symmetry;
- multiple physical inputs converge on semantic/domain actions;
- child-facing flows remain offline-first and pre-reader friendly;
- no runtime AI/TTS/speech recognition merely to fill content gaps;
- all new prerecorded speech production uses Greia Voice Production Engine;
- visual/runtime/Activity caches stay bounded with explicit invalidation;
- performance claims require measurement on claimed execution scope;
- **simplified graphics means low production/runtime complexity, not crude final art**;
- R7 remains open until its own evidence/closure criteria are satisfied.