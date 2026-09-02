# Greia R7 — Exact-Candidate Final Evidence Gap Closure

**Updated:** 2026-09-02  
**Scope:** close the remaining R7.2/R7.3 physical evidence and revalidate the post-physical system-control/hardware-session tranche.  
**Candidate:** resolved dynamically from `origin/main` at execution time; never hard-code an old SHA.  

This procedure replaces the earlier `1edb22ce`/34-Activity-specific version. The catalogue and Parent/system-control runtime have advanced since that candidate. Historical evidence remains useful only where the owning runtime seam is unchanged.

---

## 1. Evidence boundary

The trusted Home regression itself was physically closed at `57626d3f65a8bf3ae074eee15b00ee32ba3277bd` on Writing, Painting, Shape Garden and Acquario, including the exhausted-usage-limit `no Starting…` behavior. Do not reopen that bug without contrary evidence.

The important post-`57626d` platform delta is the system-control/hardware-session tranche. Two source defects found during review on 2026-09-02 were corrected:

```text
adec85c4fdf005ac473124dbf973405c37f3ddfa
  relative volume/brightness key changes now compute inside the shared desired-state transaction

e89e2e52d88f31b42c4faf6894bc25893435d362
  Legacy-X media-key listener drains Xlib-buffered events before waiting on the X socket

8610efc7dfb19ef9b82ace7b823a348f728a6f98
  focused behavioral regressions for both contracts
```

These commits are **source corrections awaiting execution**, not accepted evidence.

The remaining final physical R7 evidence is still:

- Writing full real-input/save/relaunch lane;
- Painting sustained real high-rate pointer/save/relaunch lane;
- hostile fixture 10/10 forced returns;
- abrupt Activity crash recovery;
- 20/20 normal launch/return durability;
- performance/log review;
- current system-control/hardware-session physical acceptance.

---

## 2. Rules

1. Work on canonical `frozenpepper/Greia`, branch `main`.
2. Do not use GitHub Actions for this acceptance.
3. Do not edit source, tests, runtime policy, Activities, deployment tooling or acceptance scripts after freezing the candidate.
4. Do not reset, stash, clean, delete or overwrite unknown owner work.
5. Evidence goes under one project-local `./tmp/...` directory. Do not use filesystem-root `/tmp`.
6. Pull exactly once before the gate. Never pull during the frozen run.
7. If `origin/main` advances later, the evidence remains valid for the frozen SHA but is not automatically evidence for the newer source.
8. Do not hard-code Activity count, launcher coordinates or catalogue indices.
9. Launch physical Activities through the child-visible semantic Shell path. Remote coordinate injection may assist observation, but coordinate-only activation is not trusted-Home authority evidence.
10. Trusted Home must be activated through the real protected child-facing control during final physical authority checks.
11. Do not patch timeouts or add extra successful cycles to hide a failure.
12. Stop on the first genuine invariant failure and preserve evidence.
13. Do not advance R7.4 unless this procedure reaches an honest `ACCEPTED` verdict.

---

## 3. Freeze exact candidate

```bash
set -euo pipefail

git fetch origin main
git switch main
git pull --ff-only origin main

git status --short
SOURCE_SHA="$(git rev-parse HEAD)"
ORIGIN_SHA="$(git rev-parse origin/main)"
STAMP="$(date +%Y%m%d_%H%M%S)"
EVIDENCE="./tmp/r7-final-${STAMP}-${SOURCE_SHA:0:8}"
mkdir -p "$EVIDENCE"

printf '%s\n' "$SOURCE_SHA" > "$EVIDENCE/source-sha.txt"
printf '%s\n' "$ORIGIN_SHA" > "$EVIDENCE/origin-main-at-start.txt"
git status --short > "$EVIDENCE/worktree-before.txt"
git log -30 --oneline > "$EVIDENCE/recent-history.txt"
```

Hard requirements:

```bash
test "$SOURCE_SHA" = "$ORIGIN_SHA"
test ! -s "$EVIDENCE/worktree-before.txt"
```

Verify the three new system-control commits are ancestors:

```bash
for c in \
  adec85c4fdf005ac473124dbf973405c37f3ddfa \
  e89e2e52d88f31b42c4faf6894bc25893435d362 \
  8610efc7dfb19ef9b82ace7b823a348f728a6f98
do
  git merge-base --is-ancestor "$c" "$SOURCE_SHA" || {
    echo "required correction missing: $c" >&2
    exit 20
  }
done
```

If the worktree is dirty or the frozen SHA does not equal `origin/main`, report `INCOMPLETE`; do not repair the checkout destructively.

---

## 4. Focused source gate

Use unittest discovery rather than dotted `tests.*` imports because a third-party `tests` package has shadowed this repository before.

```bash
patterns=(
  test_system_control_transactions.py
  test_hardware_session.py
  test_activity_backend_policy.py
  test_r7_activity_device_authority.py
  test_display_session_legacy_x.py
  test_supervisor_display_session.py
  test_system_chrome.py
  test_system_chrome_legacy_x.py
  test_trusted_chrome_supervisor.py
  test_r7_child_shell_trusted_chrome_composition.py
  test_r7_noncooperative_chrome_fixture.py
  test_activity_system_chrome_audit.py
  test_usage_limits.py
  test_usage_limited_supervisor.py
  test_usage_limit_presentation.py
  test_child_shell_usage_limit_launch.py
)

: > "$EVIDENCE/focused-source.log"
for pattern in "${patterns[@]}"; do
  test -f "tests/$pattern" || {
    echo "missing focused test: tests/$pattern" | tee -a "$EVIDENCE/focused-source.log"
    exit 21
  }
  echo "===== $pattern =====" | tee -a "$EVIDENCE/focused-source.log"
  PYTHONPATH=src python3 -m unittest discover -s tests -p "$pattern" -v \
    2>&1 | tee -a "$EVIDENCE/focused-source.log"
done
```

Any failure stops the gate before deployment.

---

## 5. Canonical authority audits and full verify

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities \
  2>&1 | tee "$EVIDENCE/backend-audit.log"

PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict \
  2>&1 | tee "$EVIDENCE/chrome-audit.log"

make verify 2>&1 | tee "$EVIDENCE/make-verify.log"
```

Required:

```text
backend audit blockers=0
system-chrome audit blockers=0
make verify exit=0
project validation PASS
all currently discovered Activities validate
Shell/source/footprint checks PASS
```

Record the actual Activity and test counts from output. Never compare to historical `34`, `36` or any other hard-coded count.

---

## 6. Simulator smoke for changed authority seams

Run the existing real-Shell/headless Simulator path on the frozen SHA for:

1. Writing;
2. Painting;
3. one continuously animated first-party Activity;
4. `tests/fixtures/activities/r7_noncooperative_chrome`.

Use `tools/headless_greia_simulator.py` with fresh project-local workspaces and 1024×600. For each target require:

- real Shell route;
- first Activity frame;
- meaningful interaction where applicable;
- survival window;
- protected Home return;
- Shell restored;
- no traceback/platform failure/READY timeout;
- clean workspace teardown.

For the hostile fixture, normal local exit may be ignored; trusted Home must still produce bounded platform termination and Shell return.

Inspect the generated screenshots. If the executing agent cannot visually inspect them, report `visual_review: NOT_REVIEWED`; do not invent a pass.

A Simulator failure stops deployment.

---

## 7. Recheck candidate before Acer

```bash
git status --short > "$EVIDENCE/worktree-before-acer.txt"
test ! -s "$EVIDENCE/worktree-before-acer.txt"
test "$(git rev-parse HEAD)" = "$SOURCE_SHA"

git fetch origin main
git rev-parse origin/main > "$EVIDENCE/origin-main-before-acer.txt"
```

Do not pull. If `origin/main` moved, continue only as frozen-SHA evidence and state that clearly in the final report.

---

## 8. Acer reachability and exact deployment

```bash
python3 tools/greia_remote.py --password greia wait --timeout 30 \
  2>&1 | tee "$EVIDENCE/acer-wait.log"
```

If unreachable: verdict `INCOMPLETE`; return source/Simulator evidence.

If reachable:

```bash
python3 tools/deploy_to_acer.py \
  2>&1 | tee "$EVIDENCE/acer-deploy.log"

python3 tools/greia_remote.py --password greia wait --timeout 180 \
  2>&1 | tee "$EVIDENCE/acer-wait-after-deploy.log"

python3 tools/greia_remote.py --password greia status \
  2>&1 | tee "$EVIDENCE/acer-status-after-deploy.log"

python3 tools/greia_remote.py --password greia snapshot \
  "$EVIDENCE/acer-after-deploy" --service launcher --lines 500 \
  2>&1 | tee "$EVIDENCE/acer-snapshot-after-deploy.log"
```

Do not modify the deployment helper or its accepted Atom extraction timeout.

---

## 9. Current system-control / hardware-session physical gate

This lane is mandatory because it landed after the previously accepted trusted-Home candidate.

### 9.1 Boot/input sanity

After launcher/session restart, without clicking to repair focus:

- Shell keyboard navigation works immediately;
- touchpad/pointer works;
- no Linux desktop/login/terminal is exposed;
- 1024×600 presentation is correct on the reference Acer.

### 9.2 Physical media keys

With the Shell visible, exercise each available Greia-owned physical key:

- volume up;
- volume down;
- mute/unmute;
- brightness up;
- brightness down.

Require the real machine to change state and remain responsive. A missing physical key on this particular keyboard is `NOT_AVAILABLE`, not fabricated evidence; record exactly which keys exist.

### 9.3 Buffered/burst media-key behavior

Press a supported volume or brightness key rapidly several times in one burst. Required:

- each intended step is observed or reflected in final state;
- no first-key-only behavior;
- no ~poll-interval stalls between already-buffered key presses;
- launcher/session remains responsive.

This physically exercises the source correction that drains Xlib events before waiting on the socket.

### 9.4 Parent state + physical key composition

Using the **normal authenticated Parent UI/API**, set a known non-default system-control value, then apply one physical relative key step.

Example only (use a value exposed by the real client):

```text
Parent volume -> 35%
physical Volume Up -> expected desired state 40%
```

Required:

- the physical key applies relative to the latest Parent value;
- it must not jump back toward a stale earlier value;
- unrelated brightness/mute state is preserved;
- Parent UI/API subsequently reports the committed result.

Do not edit `system-controls.json` directly.

### 9.5 Active-Activity ownership

Launch Writing or Painting through the child Shell. While it is active, press the system media keys.

Require:

- volume/brightness still operate as platform controls;
- the media keys do not become Activity gameplay/text input;
- trusted Home remains functional;
- Activity and Shell recover normally.

Record system-control service/log diagnostics after the lane.

---

## 10. Writing real-input persistence lane

From the real child Shell, semantically navigate to Writing; do not use a stored coordinate/index from an older catalogue.

Required:

1. first usable Writing frame;
2. real physical keyboard editing for at least 15 seconds;
3. real touchpad/pointer interaction;
4. normal save/autosave path;
5. physical trusted Home return;
6. relaunch from the child Shell;
7. saved state present;
8. second clean trusted Home return;
9. no focus repair, black frame, Linux UI or direct-device workaround.

---

## 11. Painting sustained high-rate pointer lane

From the real child Shell:

1. launch Painting semantically;
2. confirm canvas/palette;
3. draw continuously with the **real touchpad/pointer path for at least 20 seconds**;
4. include direction changes and multiple strokes;
5. change a normal tool/color/brush option;
6. normal save path;
7. physical trusted Home return with no stray stroke from Home activation;
8. relaunch and verify saved creation/state;
9. return cleanly.

Remote single-click injection is not a substitute for this high-rate physical lane. Material pointer lag or frame hitching is a failure requiring investigation.

---

## 12. Hostile fixture 10/10

Deploy the existing fixture:

```bash
python3 tools/greia_remote.py --password greia deploy \
  tests/fixtures/activities/r7_noncooperative_chrome
```

Identity:

```text
org.greia.fixture.r7-noncooperative-chrome
```

First cycle must prove:

- hostile Activity surface visible;
- trusted Greia Home visible above it;
- Activity ignores its normal exit/STOP behavior as designed;
- physical trusted Home requests return;
- bounded platform force-termination occurs;
- Shell returns cleanly;
- no stale Activity/chrome process remains;
- next normal Activity launches.

Then perform 10 consecutive launch → physical trusted Home → forced-return cycles **without restarting the launcher**.

Required exactly:

```text
10/10 returns
0 stale chrome windows
0 stuck Activity processes
0 launcher restarts
0 Linux/Xorg/terminal exposure
```

If cycle N fails, preserve it and stop. Do not run extra cycles to manufacture 10 green results.

---

## 13. Abrupt Activity crash recovery

Use only an existing documented safe developer/test mechanism to terminate one running Activity process abruptly.

Do not kill Xorg or the launcher.

Require:

- Shell automatically recovers;
- trusted chrome/session lease is cleaned;
- keyboard and pointer work after recovery;
- a second Activity launches normally;
- no Linux UI or SSH repair is required.

If no safe existing mechanism exists, mark this lane `NOT_RUN` and final verdict `INCOMPLETE`. Do not invent a dangerous process-kill path.

---

## 14. 20/20 normal durability

Prepare the 20-cycle sequence **before** starting. Mix:

- Writing;
- Painting;
- one lightweight/static first-party Activity;
- one continuously animated first-party Activity.

At least five cycles must be Writing/Painting.

For the first 20 planned cycles record:

```text
cycle	activity_id	launch	trusted_home_return	input_after_return	focus_repair	linux_visible
```

Required:

```text
20/20 launches
20/20 trusted Home returns
0 focus repairs
0 progressive pointer/keyboard loss
0 launcher/X restarts
0 child-visible Linux UI
```

Do not substitute later successes for an earlier failed cycle.

---

## 15. Performance and logs

Performance is correctness on the Acer floor. Separate `MEASURED`, `OBSERVED`, and `NOT_MEASURED`.

Collect where practical:

- Shell idle CPU and RSS/PSS;
- system-control helper CPU/RSS;
- Writing idle/typing responsiveness;
- Painting sustained drawing responsiveness;
- one animated Activity frame pacing;
- launch → READY latency/feel;
- Home → Shell latency/feel;
- hostile fixture while waiting for forced termination.

Reject evidence of:

- Python framebuffer/full-frame proxying;
- continuous avoidable full-screen composition;
- high-rate pointer/text IPC;
- a second Pygame chrome process;
- material Writing/Painting responsiveness regression.

Capture final logs:

```bash
python3 tools/greia_remote.py --password greia snapshot \
  "$EVIDENCE/acer-final" --service launcher --lines 1000 \
  2>&1 | tee "$EVIDENCE/acer-final-snapshot.log"
```

Review relevant launcher/session/system-control logs for:

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
traceback
platform_failure
ready timeout
restore failed
system control state lock failed
```

Interpret context. Literal diagnostic tokens are not automatically failures.

---

## 16. Final repository check

```bash
git status --short > "$EVIDENCE/worktree-after.txt"
git fetch origin main
git rev-parse origin/main > "$EVIDENCE/origin-main-at-end.txt"
```

The acceptance must not dirty tracked files. Do not pull after the freeze.

---

## 17. Required report

Return one report:

```text
GREIA_R7_FINAL_EXACT_CANDIDATE_REPORT

source_sha: <40-char frozen SHA>
origin_main_at_start: <SHA>
origin_main_before_acer: <SHA>
origin_main_at_end: <SHA>
main_advanced_during_gate: YES|NO
working_tree_clean_before: PASS|FAIL
working_tree_clean_after: PASS|FAIL

SOURCE
system_control_transactions: PASS|FAIL
focused_r7_gate: PASS|FAIL
backend_audit_blockers: <n>
chrome_audit_blockers: <n>
make_verify: PASS|FAIL
make_verify_test_count: <actual>
activity_validation_count: <actual>
project_validation: PASS|FAIL

SIMULATOR
writing: PASS|FAIL
painting: PASS|FAIL
animated: PASS|FAIL
hostile_forced_home: PASS|FAIL
visual_review: PASS|FAIL|NOT_REVIEWED
runtime_warnings: <none or exact>

SYSTEM_CONTROLS_PHYSICAL
shell_boot_input: PASS|FAIL|INCOMPLETE
available_media_keys: <list>
volume_up_down: PASS|FAIL|NOT_AVAILABLE
mute: PASS|FAIL|NOT_AVAILABLE
brightness_up_down: PASS|FAIL|NOT_AVAILABLE
rapid_key_burst: PASS|FAIL|NOT_AVAILABLE
parent_then_relative_key: PASS|FAIL|INCOMPLETE
media_keys_do_not_leak_to_activity: PASS|FAIL|INCOMPLETE

R7_PHYSICAL
writing_full_lane: PASS|FAIL|INCOMPLETE
painting_high_rate_lane: PASS|FAIL|INCOMPLETE
hostile_first_cycle: PASS|FAIL|INCOMPLETE
hostile_cycles: <n>/10
abrupt_crash_recovery: PASS|FAIL|NOT_RUN
normal_cycles: <n>/20
child_visible_linux: YES|NO
activity_direct_drm_required: YES|NO
activity_raw_input_required: YES|NO
material_performance_regression: YES|NO|NOT_MEASURED
logs_reviewed: YES|NO

first_failure: <NONE or exact first failure>
evidence_dir: <project-local path>
verdict: ACCEPTED|REJECTED|INCOMPLETE
```

Verdicts:

- `ACCEPTED`: all required source, Simulator, current system-control physical, Writing/Painting, hostile 10/10, crash, 20/20, performance/log and no-Linux-exposure lanes pass.
- `REJECTED`: a required product/security/performance invariant actually fails.
- `INCOMPLETE`: a required lane cannot honestly execute.

If `origin/main` advanced during the gate, state clearly that the verdict is for `source_sha`; do not silently promote it to the later source.

---

## 18. After the verdict

Only after execution, append factual evidence to:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

and update `HANDOVER.md` with the exact evidence boundary.

Do not rewrite historical facts and do not mark R7.4 started unless this gate is genuinely `ACCEPTED`.
