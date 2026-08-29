# Greia — R7.2 Legacy-X Containment Source and Acer Acceptance

**Date:** 2026-08-29  
**Status:** EXECUTION REQUIRED — source changes are committed; source gate and physical Acer evidence remain pending  
**Scope:** R7.2 containment only; this protocol does **not** select the final Greia display backend and does **not** close R7  
**Authority:** subordinate to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`, `docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md`, ADR 0019 and ADR 0020

---

## 1. Purpose

R7.2 keeps the currently proven Xorg/xinit path usable while removing X11/Xorg mechanics from generic Greia and Activity contracts.

The source tranche under test establishes these boundaries:

- Activity source is display/input-backend independent;
- generic launcher/runtime/display-session code does not choose or implement X11 mechanics;
- trusted installed composition explicitly chooses the provisional Legacy-X adapters;
- ordinary Activity sandboxes receive no direct DRM or raw-input device-node authority;
- the current Xorg profile/session/build files remain explicit compatibility plumbing until a replacement backend wins physical evidence;
- no generic Python framebuffer proxy, extra full-frame copy, or high-rate input IPC is introduced.

This protocol answers one narrow question:

> Did the R7.2 containment refactor preserve the known Legacy-X Greia appliance path while making the source boundary stricter?

It does **not** answer whether Xorg, Wayland or direct KMS should be the final Greia userspace stack.

---

## 2. Hard execution rules

1. Work from a fresh/current `main`; record the exact SHA before testing.
2. Do not create a branch for this protocol.
3. Do not use, inspect, rerun or download GitHub-hosted Actions. They are not authorized by this protocol.
4. Do not weaken a test, restore `/dev/dri`, add raw `/dev/input`, or broaden a runtime mount merely to obtain PASS.
5. Stop on the first genuine source-gate failure. Preserve the failing command and complete output before changing source.
6. Physical Acer failures are evidence. Do not hide them behind a simulator/desktop result.
7. Do not change the selected display backend during this acceptance. The Acer phase tests the current Legacy-X compatibility path only.
8. Do not change tap-to-click/default pointer policy as part of this protocol. Current source and repository-level prose disagree on that separate policy question; record the observed state, but do not conflate it with R7.2 containment.
9. Do not claim R7.2 source verification until the exact current-SHA focused suite **and** `make verify` pass.
10. Do not claim R7.2 physical acceptance until the exact source deployed to the Acer passes the physical sequence below.

---

## 3. Preconditions

Required local checkout state:

```bash
git switch main
git pull --ff-only
SHA="$(git rev-parse HEAD)"
echo "$SHA"
git status --short
```

Expected:

- branch is `main`;
- `git status --short` is empty;
- exact `SHA` is recorded in the evidence report.

If the checkout is not clean, stop and reconcile the working tree before testing. Do not delete unknown owner work.

Read before execution:

```text
AGENTS.md
HANDOVER.md
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md
skills/greia-os-work/SKILL.md
```

---

## 4. Focused R7.1/R7.2 source gate

Run exactly:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_activity_backend_policy \
  tests.test_r7_shell_window_composition \
  tests.test_r7_activity_device_authority \
  tests.test_hardware_session \
  tests.test_r7_legacy_x_build_containment \
  tests.test_display_session_legacy_x \
  tests.test_supervisor_display_session \
  -v
```

Required result:

```text
PASS / exit 0
```

The focused gate must prove, at minimum:

- normal SDL/Pygame Activity APIs remain allowed while backend-specific Activity behavior is rejected;
- generic launcher source contains no direct Xlib focus implementation or SDL-backend selection;
- installed trusted composition selects the Legacy-X Shell-window collaborator while development uses the no-op collaborator;
- the Legacy-X Shell collaborator does not sniff `SDL_VIDEODRIVER`/host environment to decide whether it owns the backend;
- generic hardware watcher requires an explicit semantic controller and contains no X command implementation/backend selection;
- the explicit Legacy-X hardware-session entrypoint owns that backend selection;
- the current X session invokes the explicit Legacy-X entrypoint;
- ordinary Activity Bubblewrap commands contain no `/dev/dri`, `/dev/input`, `/sys/class/drm`, or `/sys/class/input` authority;
- typed display transport removes stale competing host backend selectors;
- Legacy-X xinit-style `DISPLAY=:0` without fabricated Xauthority remains representable;
- display prepare/present/restore failures preserve Shell recovery semantics.

### Failure handling

On failure:

1. stop the protocol;
2. save the exact command, SHA, traceback/output and failing test name;
3. determine whether the failure is product source, test drift, environment, or concurrent-main drift;
4. fix the root cause on current `main` if it is in scope;
5. restart this protocol from §3 on the new SHA.

Do not continue to the aggregate gate on a red focused suite.

---

## 5. Repository-wide Activity backend audit

Run:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py
```

Required summary:

```text
blockers=0
```

`migration_findings` may remain non-zero during R7.2 because Activity-owned cooperative Home/chrome migration is intentionally R7.3/R7.5 work.

Do **not** use `--strict-migration` as an R7.2 pass requirement.

Any backend **BLOCKER** is a stop condition. Fix the Activity/backend violation; do not create an allowlist merely to pass the audit unless the item is proven test/tooling-only and the policy already has the appropriate scoped distinction.

---

## 6. Canonical full source gate

Run:

```bash
make verify
```

Required:

```text
exit 0
```

Record:

- exact SHA;
- total unit-test count reported;
- project-validation result;
- per-Activity validation result/count;
- shell-check result;
- source-footprint result;
- elapsed time if easily available.

A focused PASS is not a substitute for this gate.

If `make verify` fails, stop. Preserve the first genuine failure and repair/re-run on the resulting new exact SHA.

---

## 7. Pre-Acer source/state check

Before deployment, record:

```bash
git rev-parse HEAD
git status --short
```

The SHA must be the same source state that passed §§4–6.

If `main` advanced after the source gate, do **not** call the old result current-head acceptance. Refresh and rerun the source gate for the new SHA before physical acceptance.

The Acer may use the existing explicit developer/test transport. Current developer remote-control procedure is documented in:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

The current X11-backed screenshot/input helper is test compatibility infrastructure, not production architecture evidence.

---

## 8. Deploy to the reference Acer

Use the already accepted developer deployment path for the current device. If the repository helper is still the operator's accepted path, inspect it before execution and run:

```bash
python3 tools/deploy_to_acer.py
```

Then wait for the appliance to return:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
```

Record:

- source SHA deployed;
- device identity/inventory already associated with the reference Acer;
- launcher/service status;
- display backend reported by current platform status where available;
- any service restart or launch failure.

If deployment tooling itself has drifted or would perform an unsafe/unintended operation, stop and use the documented owner-approved developer deployment path instead. Do not invent a new destructive install procedure for this acceptance.

---

## 9. Boot/Shell compatibility acceptance

A full reinstall is not required merely to test source containment, but the **running installed session** must prove the compatibility path remains healthy.

Required observations:

1. Greia Shell is visible at 1024×600 on the reference Acer.
2. No login prompt, terminal, desktop, X root background, or other Linux UI is exposed during the tested restart/recovery path.
3. Keyboard input reaches the Shell in the no-window-manager X session.
4. Pointer/touchpad movement and click/tap behavior function according to the currently installed/settings state.
5. Shell pointer hover/redraw remains responsive; no obvious new frame pacing regression is introduced by the one-shot Shell-window collaborator.
6. Capture at least one current Shell screenshot through the developer test surface for evidence.

Suggested operator actions:

```bash
python3 tools/greia_remote.py screenshot out/r72-shell.png
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py key Right
python3 tools/greia_remote.py key Left
```

Manual owner observation is valid and preferred for final pointer/keyboard feel.

### Focus-specific check

The Shell must accept keyboard input immediately after launcher restart without clicking another window first. This specifically validates the extracted one-shot Legacy-X focus repair.

If focus is broken, inspect the Legacy-X collaborator/session and logs. Do not put Xlib calls back into generic launcher code.

---

## 10. Mandatory Activity compatibility — Writing

Launch **Writing** (`org.greia.writing`) from the real Greia Shell.

Required sequence:

1. launch from Shell;
2. confirm first usable Activity frame appears;
3. type/edit meaningful text for at least 15 seconds;
4. exercise pointer/touchpad in the Activity where applicable;
5. trigger/save the Activity's normal durable-state path;
6. return to Shell through the currently available Greia lifecycle/Home path;
7. relaunch and verify the saved state is present where the Activity's accepted UX says it should be;
8. return to Shell cleanly again.

Required observations:

- Activity renders normally despite having no direct `/dev/dri` authority;
- keyboard text input is responsive;
- no `Permission denied`, DRM-open, X transport, SDL backend, or display-socket failure appears;
- save/relaunch remains correct;
- Shell recovery remains correct.

Do not use an Activity-local workaround that opens DRM/input devices.

---

## 11. Mandatory Activity compatibility — Painting

Launch **Painting** (`org.greia.painting`) from the real Greia Shell.

Required sequence:

1. launch from Shell;
2. confirm first usable Activity frame appears;
3. draw continuously with pointer/touchpad for at least 20 seconds, including direction changes and multiple strokes;
4. change at least one normal tool/color/brush option;
5. trigger/save the Activity's normal durable-state path;
6. return to Shell;
7. relaunch and verify the saved creation/state according to the accepted Activity UX;
8. return to Shell cleanly.

Required observations:

- no direct DRM authority is required for ordinary SDL/X11 client rendering;
- drawing remains responsive and visually continuous;
- no new obvious frame hitching or pointer lag is introduced;
- save/relaunch remains correct;
- Shell recovery remains correct.

Painting is the high-rate pointer path. A security refactor that materially degrades drawing responsiveness is not accepted merely because it launches.

---

## 12. Crash recovery

Use an owner-approved developer/test method to terminate one running test Activity process abruptly while it is visible.

Requirements:

1. terminate the Activity process, not Xorg and not the launcher;
2. do not perform graceful in-Activity cleanup first;
3. observe automatic return/recovery to Greia Shell;
4. confirm Shell keyboard and pointer input still work;
5. launch another Activity afterward to prove the display/session path remains usable.

Record the Activity/session exit reason from Greia logs/history where available.

Required result:

- no exposed Linux UI;
- no dead black screen requiring SSH repair;
- no stale Activity surface preventing the next launch;
- Shell remains usable.

---

## 13. Repeated launch/return durability

Perform at least **20** real Shell → Activity → Shell cycles on the reference Acer using a mix of:

- Writing;
- Painting;
- one lightweight/static first-party Activity;
- one continuously animated first-party Activity.

At least 5 cycles must use Writing/Painting.

Required:

- 20/20 successful Activity launches;
- 20/20 successful returns/recoveries;
- no accumulating focus failure;
- no progressive pointer/keyboard loss;
- no display server restart/crash;
- no Activity requiring direct device-node authority;
- no child-visible Linux surface.

If one cycle fails, preserve that failure. Do not simply run extra cycles until the count looks green.

---

## 14. Logs and negative authority evidence

After the physical sequence, inspect bounded launcher/session logs using the developer test surface documented in `docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md`.

Look specifically for:

```text
Permission denied
/dev/dri
/dev/input
DRM
KMS
XOpenDisplay
DISPLAY
XAUTHORITY
SDL_VIDEODRIVER
wayland
traceback
platform_failure
ready timeout
restore failed
```

Interpret context; a literal token in a debug/status line is not automatically a failure.

Hard failures include:

- Activity attempts to open `/dev/dri` or `/dev/input` and fails because product source actually depended on it;
- missing/invalid Legacy-X transport prevents launch;
- Shell restore/focus failure;
- repeated platform failures caused by the containment change.

Do not "fix" such failures by restoring broad device-node access. Identify the real transport/authority requirement.

---

## 15. Resource/performance sanity

R7.2 is intended to have effectively zero steady-state rendering cost beyond existing behavior:

- Shell-window focus repair is one-shot after Shell window creation;
- hardware-session composition changes where backend selection occurs, not polling cadence;
- removing Activity `/dev/dri` is an authority reduction, not a rendering proxy.

On the reference Acer, collect practical before/after sanity evidence against the latest accepted Acer baseline available for the same path:

- launcher CPU while idle;
- launcher RSS/PSS if available;
- Writing typing responsiveness;
- Painting sustained-drawing responsiveness;
- launch-to-usable-frame and return feel;
- obvious frame pacing/hitching during tested animated Activity.

If existing project profiling tools cover a tested path, use them rather than inventing a new measurement framework.

A material regression requires investigation before acceptance. Do not wave away a regression because the architecture is cleaner.

---

## 16. Required evidence report

Return one concise report containing:

```text
R7.2 LEGACY-X CONTAINMENT ACCEPTANCE
source_sha: <40-char SHA>
working_tree_clean_before_test: PASS|FAIL
focused_r7_source_gate: PASS|FAIL
activity_backend_audit: PASS|FAIL
activity_backend_blockers: <integer>
make_verify: PASS|FAIL
make_verify_test_count: <integer if reported>
acer_device: <reference device identity/inventory label>
acer_shell_boot_and_focus: PASS|FAIL
acer_pointer_touchpad: PASS|FAIL
writing_launch_input_save_relaunch_return: PASS|FAIL
painting_launch_draw_save_relaunch_return: PASS|FAIL
abrupt_activity_crash_recovery: PASS|FAIL
launch_return_cycles: <successful>/20
child_visible_linux: NO|YES
activity_direct_drm_required: NO|YES
activity_raw_input_required: NO|YES
material_performance_regression: NO|YES|UNRESOLVED
logs_reviewed: YES|NO
tap_to_click_observed_state: <record only; no policy mutation>
first_failure: <none or exact failure>
verdict: ACCEPTED|REJECTED|INCOMPLETE
```

Also return:

- exact failing traceback/log excerpt if any;
- filenames/paths of screenshots or measurement evidence;
- any source changes made after the initial test and the final SHA retested.

Do not package secrets, private SSH keys or Wi-Fi credentials into evidence.

---

## 17. Acceptance / stop conditions

### `ACCEPTED`

Only when all are true:

- focused source gate PASS;
- backend audit reports `blockers=0`;
- `make verify` PASS on the exact accepted SHA;
- Acer Shell focus/input path PASS;
- Writing and Painting real-path acceptance PASS;
- abrupt Activity crash returns to a usable Shell;
- 20/20 launch-return cycles PASS;
- no child-visible Linux;
- no ordinary Activity requires direct DRM/raw-input authority;
- no material unresolved performance regression.

### `REJECTED`

Use when a genuine product/source/hardware failure is reproduced and blocks the containment contract.

### `INCOMPLETE`

Use when source is green but required physical evidence was not executed, or when the run stops for an environment/operator prerequisite before the product behavior can be judged.

---

## 18. What acceptance means — and does not mean

An R7.2 `ACCEPTED` verdict means:

- the current Legacy-X compatibility backend remains usable after containment;
- X-specific behavior is better isolated behind trusted adapters/session/build composition;
- ordinary Activities do not require direct DRM/raw-input device authority;
- the backend-neutral Activity/display-session contract survived physical reference-hardware use.

It does **not** mean:

- Xorg is selected as Greia's final userspace graphics architecture;
- Wayland has failed or passed;
- direct KMS is selected;
- trusted Home/Back is fully moved outside Activity rendering/input authority;
- controller/system-input brokerage is complete;
- R7 is closed;
- Pi support is proven.

If this protocol accepts, the next blocking implementation tranche is **R7.3 trusted system chrome/input authority on the current compatibility backend**, while backend comparison/Wayland experimentation remains isolated behind the already-established contracts.