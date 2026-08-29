# R7.3 Trusted System Chrome — Source and Acer Acceptance

**Date:** 2026-08-29  
**Status:** execution protocol — source and physical acceptance pending  
**Phase:** R7.3  
**Authority:** subordinate to ADR 0014, ADR 0019, ADR 0020 and `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## 1. Purpose

This protocol accepts or rejects the first real Greia-owned Activity Home boundary on the current Legacy-X compatibility session.

The implementation under test is deliberately narrow:

```text
Activity Pygame/SDL surface
        +
launcher-owned tiny Legacy-X chrome window
        +
SystemChromeCoordinator
        +
TrustedChromeActivitySupervisor
        +
Greia lifecycle graceful/forced return
```

The trusted window covers only `ActivitySystemChromeLayout.protected_region`, draws only Greia Home (Back remains disabled until real launch-origin context is integrated), consumes pointer events delivered to that protected window, and does not proxy Activity pixels.

This is **migration evidence**, not a decision to retain X11. ADR 0014 remains authoritative: X11 is not part of the target Greia architecture. A shared-X11 client with sufficient X authority may be able to interfere with sibling X windows, so R7.3 Legacy-X acceptance proves the platform structure, first-party/non-cooperative behavior, lifecycle integration and performance shape. It does **not** certify shared X11 as a final hostile-third-party isolation boundary.

## 2. Exact implementation under test

Source owners:

```text
src/greia_platform/system_chrome.py
src/greia_launcher/system_chrome.py
src/greia_launcher/system_chrome_legacy_x.py
src/greia_launcher/trusted_chrome_supervisor.py
src/greia_launcher/trusted_presentation.py
src/greia_launcher/child_shell.py
src/greia_launcher/composition.py
build/overlay/usr/local/lib/greia-os/greia-x-session
```

Hostile acceptance fixture:

```text
tests/fixtures/activities/r7_noncooperative_chrome/
```

The fixture deliberately:

- fills the whole Activity surface;
- draws no Greia Home/Back helper;
- ignores keyboard/pointer/QUIT actions;
- does not call `activity_stop_requested()`;
- remains alive after Greia requests graceful stop;
- therefore requires the platform-owned Home path plus bounded forced termination to return to Shell.

Do not modify the fixture to cooperate merely to make the test pass.

## 3. Evidence discipline

Before any execution, record:

```bash
git rev-parse HEAD
git status --short
git log -1 --oneline
```

All source and physical results in one acceptance report must identify the exact SHA actually tested.

Rules:

1. Do not use or query GitHub Actions.
2. Do not weaken Bubblewrap, restore `/dev/dri`, grant `/dev/input`, disable trusted chrome, or reintroduce Activity-side Home authority to obtain PASS.
3. Do not treat an old Acer screenshot/performance result as evidence for the current SHA.
4. Preserve the first genuine failure. Fix source, obtain a new SHA, then start a new acceptance attempt.
5. R7.2 remains an evidence dependency. If the current R7.2 containment source/Acer gate is not green on the same source lineage, R7.3 cannot be declared fully accepted.
6. A simulator/headless PASS cannot replace the Legacy-X physical test because the native chrome window is an Xlib/session behavior.

## 4. Source gate

Run from repository root on the owner-controlled checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_chrome \
  tests.test_system_chrome_legacy_x \
  tests.test_trusted_chrome_supervisor \
  tests.test_r7_child_shell_trusted_chrome_composition \
  tests.test_r7_noncooperative_chrome_fixture \
  tests.test_r7_shell_window_composition \
  tests.test_display_session_legacy_x \
  tests.test_supervisor_display_session \
  tests.test_r7_activity_device_authority \
  tests.test_activity_backend_policy \
  -v
```

Then run the complete Activity backend audit:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
```

Required summary:

```text
blockers=0
```

Migration findings for cooperative first-party Home helpers may still exist until R7.5. Record their exact count; do not hide them.

Then run:

```bash
make verify
```

### Source acceptance

Source gate is PASS only if:

- all focused tests pass;
- Activity backend blockers are zero;
- `make verify` exits zero;
- no source change was made during the gate;
- exact SHA is recorded.

If any source command fails, verdict is `REJECTED` for that attempt and physical testing must not be used to paper over the failure.

## 5. Pre-deployment review

On the exact green source SHA, inspect the implementation contract before touching the Acer:

```bash
grep -R "draw_system_chrome_overlay\|is_home_clicked" \
  src/greia_launcher src/greia_platform/system_chrome.py \
  src/greia_launcher/system_chrome*.py \
  src/greia_launcher/trusted_chrome_supervisor.py || true
```

Expected:

- trusted launcher/chrome implementation does not call Activity helper Home functions;
- Activity/shared-helper migration debt may remain elsewhere and is not an R7.3 failure by itself;
- `system_chrome_legacy_x.py` contains no Pygame renderer/process proxy;
- installed `greia-x-session` primary path is `greia_launcher.child_shell` and fallback is `greia_launcher.trusted_presentation`.

## 6. Deploy exact source to the reference Acer

Use the existing owner-approved development deployment route. Do not invent a new privileged transport for this gate.

After deployment/restart, collect and record:

```bash
python3 tools/greia_remote.py --password greia status
python3 tools/greia_remote.py --password greia snapshot ./tmp/r7-r73-acer-before --service launcher --lines 500
```

Confirm the running launcher was started after the deployment and is using the current deployed source. If there is any stale-process doubt, restart the launcher once through the existing developer control and re-record status/snapshot.

## 7. Normal Activity chrome acceptance

Use **Writing** and **Painting** because they are mandatory first-user-ready Activities and exercise text and high-rate pointer paths.

For each Activity:

1. Launch through the real child Shell.
2. Capture a screenshot while the Activity is visibly running.
3. Confirm a platform-owned Home control is visible in the canonical top-left protected region.
4. Interact meaningfully with the Activity away from Home:
   - Writing: enter/edit text;
   - Painting: sustain drawing strokes for at least 10 seconds.
5. Activate the trusted Home control.
6. Confirm return to Shell through Greia lifecycle authority.
7. Confirm save/state behavior remains correct.
8. Inspect launcher logs for platform/chrome/display failures.

Required:

- Home remains visible over the Activity;
- Activity UI does not need to receive a Home event;
- input outside the protected region works normally;
- protected Home activation does not leak through as a Painting stroke, Writing edit, or Activity-local click;
- no Linux/Xorg/terminal surface becomes child-visible during launch/return.

Do not count an Activity-drawn cooperative Home icon as proof. The physical proof is the separate launcher-owned window/input path.

## 8. Non-cooperative hostile-fixture acceptance

Deploy the fixture only to the developer Activity source:

```bash
python3 tools/greia_remote.py --password greia deploy \
  tests/fixtures/activities/r7_noncooperative_chrome
```

Do **not** replace a built-in package.

Launch `org.greia.fixture.r7-noncooperative-chrome` through the real Shell.

Required observations:

1. The Activity fills its own surface with the hostile red screen.
2. The real Greia Home control remains visible above it.
3. Random clicks/keys inside the Activity do not exit it.
4. The Activity cannot visually cover the real Home by filling its complete SDL surface.
5. Click the real Home control.
6. The fixture ignores graceful stop by design.
7. After the existing bounded graceful-stop deadline, Greia forcibly terminates the Activity process tree.
8. Shell returns cleanly with no Linux UI exposure.
9. The trusted chrome window disappears with the Activity and does not remain over Shell.
10. The next ordinary Activity launches normally, proving chrome/display state was reclaimed.

Collect immediately after the first hostile return:

```bash
python3 tools/greia_remote.py --password greia snapshot ./tmp/r7-r73-hostile-return \
  --service launcher --lines 1000
```

The authoritative Activity result should reflect the forced lifecycle semantics rather than a cooperative normal exit.

### Repetition

Repeat hostile fixture launch -> trusted Home -> forced return **10 consecutive times** without restarting the launcher.

Required:

```text
10 / 10 returns to Shell
0 stuck chrome windows
0 stuck Activity processes
0 launcher restarts
0 visible Linux/Xorg fallback surfaces
```

After repetition, launch Writing once more and return via Home.

Remove the fixture using the existing developer Activity removal command after acceptance evidence is captured.

## 9. Failure-path acceptance

At minimum prove:

### A. Abrupt Activity crash

Using an existing safe developer test path or disposable fixture variant, terminate an active Activity process abruptly without orderly SDL/lifecycle cleanup.

Required:

- Shell recovery succeeds;
- trusted chrome is removed;
- next Activity can launch;
- no stale chrome lease/window remains.

### B. Launcher fallback source path

Source gate must prove `greia-x-session` falls back to `greia_launcher.trusted_presentation`, not the untrusted plain presentation path.

A physical deliberate primary-shell failure may be performed only if it can be induced/recovered safely without corrupting the installed device. It is useful evidence but is not mandatory for this R7.3 tranche if the operator cannot create that failure safely.

## 10. Performance acceptance

Performance is part of correctness. The trusted abstraction is unacceptable if it destroys the Acer optimizations already established by the project.

Measure on the same device and exact source state, with comparable workloads.

### Required workloads

1. Shell idle before Activity launch.
2. Writing idle after READY.
3. Writing steady typing/editing.
4. Painting idle after READY.
5. Painting sustained drawing for at least 15 seconds.
6. One static/dirty-render Activity idle.
7. One continuously animated Activity.
8. Activity launch and Home return.
9. Hostile Activity while waiting for forced return.

### Record

For launcher + active Activity where applicable:

- process RSS/PSS where available;
- process CPU over a bounded sample;
- launch-to-READY latency;
- Home-click-to-Shell-return latency;
- Painting responsiveness/frame behavior;
- Writing input responsiveness;
- count of visible chrome redraws/exposes if practical from instrumentation/logging.

### Acceptance principles

- trusted chrome must not create a full-screen frame copy or Python framebuffer proxy;
- no continuous full-screen alpha composition is allowed;
- no separate Pygame chrome renderer process is allowed;
- idle overhead should be near the noise floor of the existing launcher poll cadence;
- Painting and Writing must not show a material user-visible regression;
- added input latency remains within the established `<= 50 ms` platform target where measured;
- the existing ~30 fps smooth-game target on the Atom floor remains available;
- any material CPU/RSS/latency regression requires investigation before acceptance.

Do not manufacture a universal numeric percentage threshold from unrelated old measurements. Record before/after exact workloads and judge materiality against the accepted Acer behavior and resource floor.

## 11. Security/authority interpretation

A Legacy-X PASS means:

- Activities no longer need to draw/handle the **real** platform Home to obtain a return path;
- a deliberately non-cooperative ordinary Pygame Activity cannot cover the trusted window merely by repainting its own fullscreen surface;
- the launcher owns Home lifecycle and pointer handling in the tested compatibility session;
- Activity `/dev/dri` and raw input authority remain denied;
- trusted chrome lifecycle is tied to Activity session cleanup;
- the performance shape is acceptable or explicitly rejected.

It does **not** mean:

- Xorg is now an accepted final Greia architecture;
- a hostile client with broad shared-X protocol authority is cryptographically/security-isolated from the trusted window;
- R7 is closed;
- controller/system-input brokerage is complete;
- Back launch-origin behavior is complete;
- Wayland/direct-compositor comparison is no longer required.

Final third-party trust isolation must be demonstrated on the target direct/appliance backend selected under ADR 0014.

## 12. Verdict

Return exactly one disposition:

### `ACCEPTED`

Only when:

- exact-current source gate is green;
- R7.2 containment prerequisite is green on compatible/current evidence;
- normal Writing/Painting trusted Home works;
- hostile fixture proves non-cooperative forced return;
- 10/10 hostile cycles recover;
- crash recovery succeeds;
- performance shows no material regression;
- no child-visible Linux surface appears.

### `REJECTED`

Use when a required invariant fails, especially:

- Home can be covered or disappears;
- Home input reaches the Activity instead of Greia;
- hostile Activity cannot be forcibly returned;
- chrome state/window leaks across Activity sessions;
- current source gate fails;
- the implementation materially regresses Acer interaction/performance.

### `INCOMPLETE`

Use only when the environment/evidence lane genuinely cannot execute a required portion. List exactly what remains unexecuted; do not convert missing evidence into PASS.

## 13. After acceptance

R7.3 Legacy-X acceptance does **not** authorize immediate deletion of all cooperative Activity Home helpers. The next migration step is controlled:

1. change shared Activity canvas/viewport helpers so they retain safe/protected geometry but stop rendering/hit-testing the real system chrome;
2. migrate Writing/Painting first and remeasure typing/drawing paths;
3. migrate shared-canvas exemplars by pattern;
4. remove the remaining first-party helper calls repository-wide;
5. keep the backend-independence validator green;
6. continue R7.4 physical controller/system-input ownership and the ADR-0014 direct/compositor backend evidence path.

Do not combine that migration with unrelated gameplay/visual rewrites.
