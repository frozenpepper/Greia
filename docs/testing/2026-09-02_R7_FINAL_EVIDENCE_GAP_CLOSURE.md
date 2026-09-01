# Greia R7 — Final Evidence-Gap Closure at 1edb22ce

**Date:** 2026-09-02  
**Runtime/source candidate under physical acceptance:** `1edb22cec7709aafe3f08519fabf69cb93cb8083`  
**Parent App pinned/reviewed source:** `7db9a94ef652b491fc3b305936cce439bb978b8e`  
**Current repository HEAD may be later documentation-only commits.**  
**Scope:** close only the remaining exact physical evidence gaps for R7.2, R7.3 and the Parent usage-limit/visibility tranche.  

---

## 1. Evidence already accepted — do not repeat

At exact runtime/source `1edb22ce`:

```text
focused R7.2 source gate: PASS
focused R7.3 source gate: PASS
usage-limit focused suites: PASS
backend audit: PASS blockers=0
system-chrome audit --strict: PASS blockers=0
make verify: PASS 1561 tests
project validation: PASS
34 Activity validation: PASS
Shell source gate: PASS
Simulator Encyclopedia/Writing/Painting/Volo/hostile: PASS
Simulator visual review: PASS
physical Acer exact deployment: PASS
Acer Shell boot/pointer: PASS
Acer focus restarts: 5/5 PASS
child-visible Linux: NO
Activity direct /dev/dri required: NO
Activity raw /dev/input required: NO
physical libpng warnings: NO
```

The owner additionally performed the real human-input lanes and reports all PASS:

```text
Writing physical keyboard/editing: PASS
Writing save/return/relaunch persistence: PASS
Painting sustained physical touchpad drawing >=20 s: PASS
Painting multiple strokes/direction changes: PASS
Painting tool/color/brush change: PASS
Painting save/return/relaunch persistence: PASS
physical child keyboard/touchpad feel: PASS
```

Do **not** ask the owner to repeat these.

The previous machine-only attempt also proved:

```text
Parent hide/show API + physical hot reload: PASS
Parent policy restoration: PASS
logs/negative authority sanity: PASS
```

The previous 20/20 and hostile batches are useful supporting evidence but do not close the canonical exact-pattern gates because the driver used fallback coordinates and did not prove the expected process identity per cycle.

---

## 2. Why the previous machine run remained incomplete

All three unresolved machine lanes share one evidence defect:

> a click/screenshot that looks Activity-like is not proof that the intended Activity actually launched.

Observed consequences:

- Shape Garden crash setup produced no proven Activity PID, so abrupt crash was correctly `NOT_RUN`;
- the short-budget test waited 75 s while `profile_used_seconds` remained zero, proving the intended Activity lifecycle had not actually been entered;
- the 20/20 and hostile batches did not verify the intended Activity/Bubblewrap identity per cycle.

The final gate therefore uses **process identity as a hard launch precondition**.

---

## 3. Hard rules

1. Do not modify production/runtime source during this gate.
2. Do not redeploy merely because current `main` contains documentation-only commits after `1edb22ce`.
3. If any non-documentation source changed after `1edb22ce`, stop and request review before combining physical evidence.
4. Do not count a launch until §5 process proof passes for the exact expected Activity ID.
5. Do not count a return until the expected Activity process and its Bubblewrap wrappers are gone.
6. Do not use direct `record_activity_time()` or edit `usage-limits.json` to manufacture expiry evidence.
7. Do not run extra successful cycles to replace a failed numbered cycle.
8. Do not use GitHub-hosted Actions.
9. Do not use manual `windowfocus`, repair clicks or launcher restarts inside a durability/hostile cycle.
10. Stop on the first genuine product/evidence failure and preserve it.

---

## 4. Preflight: preserve the runtime candidate

From the repository:

```bash
git fetch origin
git switch main

git rev-parse HEAD
git rev-parse origin/main
git status --short --untracked-files=all

git diff --name-only 1edb22cec7709aafe3f08519fabf69cb93cb8083..HEAD \
  | tee ./tmp/r7-final-gap-delta.txt
```

The delta from `1edb22ce` must contain only documentation files, currently expected under:

```text
HANDOVER.md
docs/plans/
docs/reviews/
docs/testing/
```

If the delta contains any runtime/source/build/tool file, stop. Do not silently inherit the old physical candidate.

Create evidence root:

```bash
STAMP="$(date +%Y%m%d_%H%M%S)"
E="./tmp/r7-final-gap-${STAMP}-1edb22ce"
mkdir -p "$E"
printf '%s\n' '1edb22cec7709aafe3f08519fabf69cb93cb8083' > "$E/runtime-candidate.txt"
PY=/opt/homebrew/bin/python3.12
```

Confirm the Acer remains reachable and on the accepted runtime bundle using the already-proven file/hash identity check:

```bash
"$PY" tools/greia_remote.py --password greia wait --timeout 180
"$PY" tools/greia_remote.py --password greia status \
  | tee "$E/acer-status-before.json"
"$PY" tools/greia_remote.py --password greia snapshot \
  "$E/acer-before" --service all --lines 1000
```

Do not redeploy if exact `1edb22ce` runtime identity is still proven.

---

## 5. Canonical Activity-process proof

### 5.1 Do not match host Activity paths with `pgrep`

Inside Bubblewrap, the final Python child may not expose the host path expected by:

```text
pgrep -f 'python3.*activities/shape_garden/main.py'
```

That is why the previous crash probe could return zero even when a sandbox might exist.

Greia already passes the authoritative semantic identity into the Activity environment:

```text
GREIA_ACTIVITY_ID=<activity id>
```

Bubblewrap wrapper processes can inherit that variable too, so environment identity **alone** is also insufficient. Filter by both:

```text
GREIA_ACTIVITY_ID == expected ID
AND executable basename is python/python3/python3.*
```

### 5.2 Probe helper to run on the Acer maintenance shell

Open:

```bash
"$PY" tools/greia_remote.py --password greia shell
```

Define this function exactly:

```bash
activity_probe() {
  expected="$1"
  echo greia | sudo -S -p '' sh -s -- "$expected" <<'EOS'
expected="$1"
python_count=0
bwrap_count=0

for proc in /proc/[0-9]*; do
  pid="${proc##*/}"
  [ -r "$proc/environ" ] || continue

  if ! tr '\0' '\n' < "$proc/environ" 2>/dev/null \
      | grep -Fxq "GREIA_ACTIVITY_ID=$expected"; then
    continue
  fi

  exe="$(readlink -f "$proc/exe" 2>/dev/null || true)"
  base="${exe##*/}"
  user="$(ps -p "$pid" -o user= 2>/dev/null | xargs)"
  args="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"

  case "$base" in
    python|python3|python3.*)
      python_count=$((python_count + 1))
      printf 'PYTHON pid=%s user=%s exe=%s args=%s\n' "$pid" "$user" "$exe" "$args"
      ;;
    bwrap)
      bwrap_count=$((bwrap_count + 1))
      printf 'BWRAP pid=%s user=%s exe=%s args=%s\n' "$pid" "$user" "$exe" "$args"
      ;;
  esac
done

printf 'SUMMARY expected=%s python_count=%s bwrap_count=%s\n' \
  "$expected" "$python_count" "$bwrap_count"

[ "$python_count" -eq 1 ] || exit 41
[ "$bwrap_count" -ge 1 ] || exit 42
EOS
}
```

Example:

```bash
activity_probe org.greia.shape-garden
```

A launch is proven only when:

```text
python_count=1
bwrap_count>=1
Python process owner is greiakid
```

Record the exact PID output for every required cycle.

### 5.3 Return/cleanup proof

After Greia Home returns to Shell, wait up to 3 s and prove that no process still carries the Activity ID:

```bash
activity_absent() {
  expected="$1"
  echo greia | sudo -S -p '' sh -s -- "$expected" <<'EOS'
expected="$1"
count=0
for proc in /proc/[0-9]*; do
  [ -r "$proc/environ" ] || continue
  if tr '\0' '\n' < "$proc/environ" 2>/dev/null \
      | grep -Fxq "GREIA_ACTIVITY_ID=$expected"; then
    exe="$(readlink -f "$proc/exe" 2>/dev/null || true)"
    base="${exe##*/}"
    case "$base" in
      python|python3|python3.*|bwrap)
        printf 'STALE pid=%s exe=%s\n' "${proc##*/}" "$exe"
        count=$((count + 1))
        ;;
    esac
  fi
done
printf 'STALE_COUNT=%s\n' "$count"
[ "$count" -eq 0 ]
EOS
}
```

Do not count the return if `activity_absent` fails.

---

## 6. Exact 1024×600 Activity-grid geometry

The current Shell page controls at 1024×600 are generated from `main.py` with a 72 px side control at vertical center `324`.

Use these centers:

```text
Previous page: (50, 324)
Next page:     (974, 324)
Trusted Home while Activity is running: (38, 38)
```

The exact target tile centers recorded from the accepted current catalogue are:

```text
Painting     page 1  (750, 350)  org.greia.painting
Shape Garden page 1  (750, 450)  org.greia.shape-garden
Volo         page 2  (150, 450)  org.greia.volo-draghetto
Writing      page 2  (550, 450)  org.greia.writing
```

### Page normalization

Before selecting a target inside the Create grid:

1. click Previous `(50,324)` twice; on page 0 the absent control leaves this side margin inert;
2. for page 1 click Next `(974,324)` once;
3. for page 2 click Next `(974,324)` twice;
4. click the exact target tile;
5. **immediately prove expected process identity with §5.**

If process proof fails, the cycle has not started. Capture the Shell screenshot and stop to diagnose navigation; do not wait and do not count it.

### Returning to Create Home/grid when needed

The already-observed physical route is:

```text
Create activity grid -> BackSpace -> Collection Home
Collection Home -> clamp selection to first Collection (Create) with repeated Left/Up -> Return
```

Do not press BackSpace a second time after reaching Collection Home because Back at root may return to profile selection.

---

## 7. Exact normal durability 20/20

Use exactly this pattern:

```text
1  Writing
2  Shape Garden
3  Volo del Draghetto
4  Painting
5  Writing
6  Shape Garden
7  Volo del Draghetto
8  Painting
9  Writing
10 Shape Garden
11 Volo del Draghetto
12 Painting
13 Writing
14 Shape Garden
15 Volo del Draghetto
16 Painting
17 Writing
18 Shape Garden
19 Volo del Draghetto
20 Painting
```

This gives five cycles each of:

```text
Writing high-value text path
Painting high-value pointer path
lightweight/static path
continuously animated path
```

For each numbered cycle:

1. normalize Create grid/page with §6;
2. click the exact tile;
3. within 3 s run `activity_probe EXPECTED_ID` and save output;
4. capture at least a compact screenshot proof that the expected Activity is visible;
5. let it run for at least 2 s;
6. give one ordinary safe bounded input;
7. activate trusted Home at `(38,38)`;
8. wait for Shell;
9. run `activity_absent EXPECTED_ID`;
10. without any focus-repair click, send one Left and one Right Shell key and verify visual selection response;
11. append the cycle result.

Create:

```text
$E/normal-20.tsv
```

Columns:

```text
cycle	activity_id	python_pid	bwrap_count	visible	return	process_cleanup	focus	linux_visible	note
```

Capture full snapshots at cycles:

```text
1, 4, 5, 10, 15, 20, and first failure
```

Required final result:

```text
20/20 exact expected Activity identities
20/20 usable visible frames
20/20 trusted-Home returns
20/20 process cleanup proofs
20/20 automatic Shell focus proofs
0 launcher/display restarts
0 child-visible Linux
```

A failed numbered cycle ends the attempt.

---

## 8. Exact hostile R7.3 10/10

Deploy the canonical fixture if it is not already present:

```bash
"$PY" tools/greia_remote.py --password greia deploy \
  tests/fixtures/activities/r7_noncooperative_chrome \
  2>&1 | tee "$E/hostile-deploy.log"
```

Identity:

```text
org.greia.fixture.r7-noncooperative-chrome
```

The fixture belongs to the `learn` Collection.

From Collection Home:

1. clamp selection to Create with repeated Left/Up;
2. press Right twice to select Learn;
3. press Return;
4. navigate to the fixture using the already-observed Learn-page route;
5. **do not trust the tile click itself** — require `activity_probe org.greia.fixture.r7-noncooperative-chrome`.

If the previously used page-2 `(750,450)` location does not produce the exact fixture process, stop and inspect the Learn screenshot/catalogue. Do not count a different Activity as hostile evidence.

### First cycle

Required before Home activation:

```text
hostile red surface visible
activity_probe exact fixture: PASS
trusted Greia Home visible in canonical protected corner
```

Then:

1. give ordinary Activity input and verify fixture remains active;
2. activate trusted Home at exactly `(38,38)`;
3. verify the fixture ignores graceful stop and platform performs bounded force termination;
4. verify `activity_absent` for the fixture;
5. verify Shell focus with Left/Right without repair;
6. launch and return from Writing once with exact process proof.

Only if first cycle passes, repeat hostile launch -> Home -> forced return **10 consecutive times without launcher restart**.

Create:

```text
$E/hostile-10.tsv
```

Columns:

```text
cycle	python_pid	bwrap_count	red_visible	trusted_home	forced_return	cleanup	focus	stale_surface	linux_visible	note
```

Required:

```text
10/10 exact fixture process identities
10/10 forced returns
10/10 complete process cleanup
10/10 focus recovery
0 stale hostile surface/chrome
0 launcher restart
0 Linux/Xorg/terminal exposure
post-cycle Writing exact launch/return PASS
```

Remove only the developer fixture after evidence if normal cleanup policy requires it.

---

## 9. Abrupt crash recovery — use semantic process identity

Use `org.greia.shape-garden`.

1. launch Shape Garden through the exact Create page-1 `(750,450)` route;
2. require `activity_probe org.greia.shape-garden`;
3. capture its visible frame;
4. from the probe output record the **one Python PID** only.

Do not kill a Bubblewrap wrapper, launcher, Xorg/xinit, SSH or any unrelated process.

Re-confirm immediately before kill:

```text
PID still exists
process owner greiakid
/proc/PID/environ contains GREIA_ACTIVITY_ID=org.greia.shape-garden
/proc/PID/exe basename is python/python3/python3.*
```

Then abruptly kill only that exact Python child through the owner-approved maintenance shell:

```bash
echo greia | sudo -S kill -KILL "$PID"
```

Required afterward:

```text
Shell automatically returns
activity_absent org.greia.shape-garden: PASS
Shell keyboard focus works without click
pointer remains usable
no black screen
no stale surface
no child-visible Linux
next Writing exact process launch/return PASS
```

If semantic PID proof is not exact, do not kill anything; return `NOT_RUN` and R7 remains incomplete.

---

## 10. Parent usage-limit lane — prove a real lifecycle before waiting

The previous run correctly rejected its own expiry evidence because `profile_used_seconds` remained zero. Do not repeat that mistake.

Use only the authenticated versioned Parent API (`/api/v1`) and preserve the exact baseline before modifying policy.

### 10.1 Baseline and short budget

Save:

```text
device limit
profile limit
profile activity policy
profile used seconds
```

Temporarily make device limit unlimited and choose a valid whole-minute profile limit that leaves between 1 and 60 seconds based on current `profile_used_seconds`.

Do **not** decrement or edit prior real usage history.

### 10.2 Finite Home indicator must be captured on Collection Home

The usage pill is rendered by `GreiaChildShell._render_collection_home()`, not the Activity grid.

Before screenshot:

1. make sure no Activity is running;
2. from Create grid press BackSpace **once** to Collection Home;
3. capture the top-right pill.

Expected Italian wording:

```text
1 min rimasti oggi
```

or below one minute:

```text
Meno di 1 min per oggi
```

There must be no seconds ticker.

If the screenshot is an Activity grid without the Collection portals, the Home-indicator evidence is invalid.

### 10.3 Launch Shape Garden and prove accounting starts

Return to Create and launch exact page-1 Shape Garden `(750,450)`.

Immediately require:

```text
activity_probe org.greia.shape-garden: PASS
```

Then wait **at least one normal accounting checkpoint** (20 s is sufficient) and query the Parent API again.

Hard precondition before waiting out the budget:

```text
profile_used_seconds AFTER > profile_used_seconds BEFORE
```

If usage has not increased while the exact Shape Garden process is proven active, STOP and report a product lifecycle/accounting failure. Do not wait the remaining minute and do not call `record_activity_time()` manually.

### 10.4 Natural expiry

Once real accounting increment is proven, allow the same Activity to remain active until the authoritative remaining budget reaches zero, plus bounded graceful-cleanup time.

Required:

```text
exact Shape Garden process disappears through lifecycle
Shell Collection Home returns automatically
Parent API exhausted=true
effective_remaining_seconds=0
Home says Finito per oggi
Shell focus works without repair
```

### 10.5 Exhausted relaunch UX

The exhausted-return path intentionally returns to Collection Home. Therefore, to test relaunch:

1. navigate back into Create;
2. select Shape Garden exact page-1 `(750,450)`;
3. press normal activation;
4. capture at ~150 ms, ~500 ms and ~1250 ms.

Required:

```text
no Shape Garden Python process appears
no Bubblewrap wrapper appears
no Starting… overlay is observed
Shell stays/returns on Collection Home
Finito per oggi remains available on Home
```

This behavior is expected because the Shell performs a friendly exhausted pre-check, while the supervisor remains authoritative enforcement.

### 10.6 Restore policy exactly

Restore the saved device/profile limits and Activity policy through Parent API.

Do not erase the real usage accumulated by this acceptance run.

After restoration, verify a normal Activity launch works again if the restored policy permits it.

Never include pairing/device credentials in repository evidence.

---

## 11. Final logs and performance sanity

Collect a bounded final snapshot:

```bash
"$PY" tools/greia_remote.py --password greia snapshot \
  "$E/final-snapshot" --service all --lines 5000
```

Review for real failures involving:

```text
Traceback
platform_failure
ready timeout
restore failed
Permission denied
/dev/dri
/dev/input
DRM
KMS
XOpenDisplay
DISPLAY
XAUTHORITY
SDL_VIDEODRIVER
libpng
```

Required:

```text
child-visible Linux: NO
Activity direct DRM required: NO
Activity raw input required: NO
display restore failures: 0
unexplained platform_failure: 0
physical libpng warning: NO
material performance regression: NO
```

The owner's already-accepted Writing/Painting responsiveness evidence is retained; do not ask for it again.

---

## 12. Verdict rules

### R7.2 `ACCEPTED` only if

```text
all inherited source/Simulator evidence remains valid
owner Writing/Painting physical evidence accepted
exact normal durability 20/20 PASS
abrupt crash recovery PASS
focus/process cleanup PASS
no Linux exposure
no direct DRM/raw-input dependency
no material performance regression
```

### R7.3 `ACCEPTED` only if

```text
compatible R7.2 evidence accepted
exact hostile first cycle PASS
hostile 10/10 PASS
forced cleanup/process absence PASS
focus recovery PASS
no stale trusted/hostile surface
no launcher restart
no Linux exposure
```

### Parent usage-limit/visibility tranche `PHYSICALLY ACCEPTED` only if

```text
reviewed Parent App/pin evidence retained
physical hide/show PASS retained
finite Collection-Home indicator PASS
real Activity usage accounting increment PASS
automatic expiry/return PASS
exhausted API state PASS
Finito per oggi PASS
exhausted relaunch blocked with no Starting flash PASS
policy restored exactly PASS
```

A real invariant failure is `REJECTED`.
A lane that genuinely cannot execute is `INCOMPLETE`.

Do not start R7.4 until R7.2 and R7.3 are accepted.

---

## 13. Documentation after final physical verdict

Only after this gate finishes:

1. update `HANDOVER.md`;
2. append exact evidence to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
3. update `docs/reviews/2026-09-01_R7_R72_R73_AND_PARENT_CONTROLS_PHYSICAL_ACCEPTANCE.md` or append a dated final correction review;
4. update `docs/design/PARENT_CONTROLS_USAGE_LIMITS_AND_ACTIVITY_VISIBILITY.md` if the physical Parent tranche becomes accepted;
5. clearly distinguish:

```text
accepted runtime/source SHA: 1edb22cec7709aafe3f08519fabf69cb93cb8083
final documentation-only HEAD: <later SHA>
```

Do not rewrite earlier failed/incomplete evidence to make history appear cleaner.

---

## 14. Final report shape

```text
GREIA_R7_FINAL_EVIDENCE_GAP_CLOSURE_REPORT

SOURCE_LINEAGE:
  runtime_candidate_sha:
  current_docs_head:
  delta_from_runtime_candidate:
  runtime_source_changed_since_candidate:
  exact_runtime_still_deployed:

INHERITED_OWNER_PHYSICAL:
  writing:
  painting:
  input_feel:

NORMAL_20:
  result:
  exact_pattern:
  expected_process_proofs:
  launch_passes:
  return_passes:
  cleanup_passes:
  focus_passes:
  launcher_restarts:
  first_failure:

HOSTILE_10:
  fixture_id:
  first_cycle:
  expected_process_proofs:
  cycles:
  forced_returns:
  cleanup_passes:
  focus_passes:
  stale_surfaces:
  stuck_processes:
  launcher_restarts:
  post_writing:
  first_failure:

CRASH_RECOVERY:
  target_activity:
  semantic_pid_proof:
  killed_pid:
  shell_recovered:
  process_cleanup:
  focus_recovered:
  next_writing:
  result:

PARENT_USAGE_LIMIT:
  profile_id:
  baseline_device_limit:
  baseline_profile_limit:
  starting_profile_used_seconds:
  short_limit_minutes:
  starting_remaining_seconds:
  collection_home_indicator:
  exact_activity_process_proof:
  profile_used_increased_while_running:
  automatic_expiry_return:
  exhausted_api:
  exhausted_home_wording:
  exhausted_relaunch_process_absent:
  starting_flash_seen:
  policy_restored:
  result:

NEGATIVE_AUTHORITY:
  child_visible_linux:
  activity_direct_drm_required:
  activity_raw_input_required:
  display_restore_failure:
  unexplained_platform_failure:
  libpng_warning:
  material_performance_regression:

R72_VERDICT:
R73_VERDICT:
PARENT_USAGE_VISIBILITY_TRANCHE_VERDICT:

EVIDENCE_DIR:
DOCS_COMMIT_SHA:
FINAL_HEAD:
FINAL_GIT_STATUS:
```
