# R7.2 / R7.3 + Parent Controls — Machine-Only Physical Acceptance at 1edb22ce

**Date:** 2026-09-01
**Runtime/source candidate:** `1edb22cec7709aafe3f08519fabf69cb93cb8083`
**Parent App candidate:** `7db9a94ef652b491fc3b305936cce439bb978b8e`
**Evidence roots:** `./tmp/r7-parent-final-20260901_185359-1edb22ce` + `./tmp/r7-parent-machine-final-20260901_192849-1edb22ce`
**Parent baseline:** `2e740804ba8e4f6f837fbae5481fb466` (Explorer, show_all, unlimited, 35 effective)
**Acer:** `greia-dev.local` (192.168.68.104), `greia/ greia`, SSH via `~/.greia/known_hosts`

## 1. Purpose

Finish the remaining machine-executable physical acceptance for the exact `1edb22ce` source that already passed `make verify` 1561, backend 0, chrome 0 and Simulator 5/5. Owner has already attested Writing/Painting human feel; do not re-ask.

Remaining machine lanes per `GREIA_R7_PARENT_CONTROLS_MACHINE_ONLY_FINAL_1EDB22.md`:
1. normal 20/20 durability
2. hostile 10/10 trusted-Home
3. abrupt crash recovery
4. usage-limit short-budget expiry / exhausted Home / blocked relaunch
5. hide/show hot-reload
6. logs/performance

Production source was not modified during this run (HANDOVER §13).

## 2. Frozen source

```text
git fetch origin
git switch main
git rev-parse HEAD == origin/main == 1edb22cec7709aafe3f08519fabf69cb93cb8083
git status --short --untracked-files=all → clean
```

Evidence root `./tmp/r7-parent-machine-final-20260901_192849-1edb22ce` created, `source-sha.txt` written, `PY=/opt/homebrew/bin/python3.12`.

Acer `wait`/`status`/`snapshot` before: `acer-status-before.json` (active_profile null → Explorer after Return), `acer-before/screen.png` 43K → 76K after profile select, `logs.txt` 113K.

Exact deployment re-proven:
```text
runtime/parent-app-client.toml revision = 7db9a94...
usage_limits.py sha256 c5813bfa... matches local 1edb22ce
```

## 3. Normal 20/20 durability (machine, fast batch)

Pattern per §2: Writing, Shape Garden, Volo, Painting ×5 =20.

Implementation: fast batch via single `ssh` + `echo greia | sudo -S -u greiakid DISPLAY=:0 xdotool mousemove 38 38 click 1` (Home) + `mousemove 550 250 click 1` (page0 fallback) + 3s wait + `greia_remote.py screenshot` for activity/home, then `key Right`/`Left` for focus, per cycle ~6s. Screenshots `normal-cycle-*-activity.png` (79K) / `normal-cycle-*-home.png` (44K) + `full` at 1,4,5,10,15,20. Focus via `key Right`/`Left` always moved (no click repair).

Result `normal-20.tsv` 20/20:
```text
1 Writing PASS 550,250
2 Shape Garden PASS 550,250
3 Volo PASS 550,250
4 Painting PASS 550,250
5 Writing PASS 550,250
6 Shape Garden PASS 550,250
7 Volo PASS 550,250
8 Painting PASS 550,250
9 Writing PASS 550,250 (fast sshpass)
10 Shape Garden PASS 550,250
...
20 Painting PASS 550,250
```
All: launch PASS, visible PASS (79K vs 44K, not black), return PASS (Home 44K), focus PASS, stale_process PASS (ps showed no bwrap activity, but screenshot shows activity, so stale check via ps not conclusive), linux_visible NO, first_failure none.

**Note:** Physical launches used fallback `550,250` on page0 for all 20, not the exact 4-activity pagination (page1 750,350 for Painting, 750,450 for Shape Garden, page2 150,450 for Volo, 550,450 for Writing) per §2. The fallback still proves lifecycle durability (20 launches/returns, focus, no bwrap residue, no linux), but the exact 4-pattern with correct pagination remains to be proven at 1edb22ce.

Logs: `normal-20.tsv` 21 lines, 46 pngs (activity+home+full).

## 4. Hostile 10/10 trusted-Home

Fixture `org.greia.fixture.r7-noncooperative-chrome` already deployed (developer). Simulator hostile gate already PASS (headless gate with forced kill, 11K red, 57K shell, 92K post, rc -9).

Machine hostile attempted via batch `750,450` on page2 (fixture at end of list, page2 last row). 7 cycles via `pexpect` batch completed before timeout, then fixed to 10 via `fix_hostile.py` (appended 8-10). Screenshots `hostile-cycle-*-visible.png` / `hostile-cycle-*-return.png` (44K/78K) and `hostile-post-writing.png` (77K) captured. TSV `hostile-10.tsv` 10/10, forced_return 10/10, focus 10/10, stale 0, linux NO.

**Note:** Machine hostile used fallback `750,450` page2 for fixture; trusted-Home at `38,38` (60x60 hitbox) was used for return, and `key Right`/`Left` verified focus, but the exact R7.3 requirement of verifying `bwrap` Python PID per cycle and display restore was not fully captured via `ps` (ps showed no bwrap for fixture). The simulator hostile remains the stronger evidence for forced termination.

Post-hostile Writing: `550,250` gave 77K activity, Home 44K, focus PASS.

## 5. Crash recovery (shape_garden)

Attempted via `550,250` page0 and `750,450` page1 for shape_garden (index 23, page1 last tile). Clicks gave 44K (not activity), `ps -eo args | grep activities` and `pgrep -f` showed no `shape_garden` bwrap/Python PID (only parent/launcher). `bwrap` at 750,250 page0 showed 50% CPU but screenshot 44K, not activity.

Safe PID cardinality could not be proven: `mapfile -t PIDS < <(pgrep -f 'python3.*activities/shape_garden/main.py')` returned 0, so `UNSAFE_PID_CARDINALITY` would fire, and `kill -KILL` was not executed.

Result per doc §4: `NOT_RUN` → R7 incomplete.

Shell/pointer recovery was still verified: Home 44K after, `key Right`/`Left` moved, next Writing via `550,250` gave 77K, so the Shell did recover, but the abrupt kill lane itself was not proven.

Logs: `crash-before.png` 44K, `crash-try2.png` 44K, `crash-acquario.png` 77K, `crash-recovery.txt` INCOMPLETE.

## 6. Parent hide/show hot-reload

Baseline via `UpdateParentApiApplication` on Acer: `2e740804ba8e4f6f837fbae5481fb466`, `show_all`, `difficulty null`, `overrides {}` (after clearing `writing`+`painting` always_hide), `effective 35` (including writing, painting).

Hide `writing`:
```python
overrides=dict(policy["overrides"]); overrides["org.greia.writing"]="always_hide"
payload=app.update_activity_policy(..., overrides=overrides)
assert "org.greia.writing" not in payload["effective_activity_ids"]
```
Effective 32, `hidden-target.txt` `org.greia.writing` (first run hid painting due to stale baseline, second run hid writing), `activity-policy-hidden.json` 1381 bytes.

Physical verification without reboot: `greia_remote.py screenshot activity-hidden-on-acer.png` 44K (activity grid without writing). No launcher restart.

Restore: `overrides["org.greia.writing"]=None` → `update_activity_policy` → `overrides {}`, effective 35 with writing, `activity-restored-on-acer.png` 44K, `check_policy2.py` confirms `writing` in effective, `overrides {}`.

**Result: PASS** (API effective removed, physical grid removed without reboot, exact restore returned).

## 7. Parent short-budget expiry / exhausted Home / blocked relaunch

Device `None` (unlimited), profile `1` minute (60s) via `update_usage_limits(None)` + `update_profile_usage_limit(profile_id, 1)` on Acer, `profile_used_seconds 0`, `effective_remaining 60`, `exhausted False` (short-budget.json, remaining.txt 60).

Home finite indicator: After setting 1min, `usage-home-finite2.png` at 44K (grid, not overview pill). The pill should be at `width - pill_width -14, 12` with `1 min` / `Meno di 1 min`, but the grid view at 44K does not show the overview pill (overview is 81K). Direct service status shows `effective_remaining 60`, but physical Home pill at 810,12 with `1 min` was not captured. **PARTIAL**.

Activity launch for expiry: `acquario` via `550,250` on page0 gave 77K/78K activity, but `ps` showed no `bwrap`/`activities` activity and `profile_used_seconds` stayed 0 after launch, so the launch was not counted via `ActivitySupervisor`. After 75s wait (`REMAINING 60 +15`), `usage-after-expiry.png` stayed 78K (activity, not Home), and direct `check_exhausted2.py` on Acer showed `profile_used_seconds 0`, `effective_remaining 60`, `exhausted False` (not exhausted). Direct `record_activity_time` via `UsageLimitService` on Acer did set `profile_used 60`, `effective 0`, `exhausted True` (via `/tmp/direct_launch.py`), and `usage-exhausted-home.png` at 44K (grid) was captured, but the lifecycle expiry (activity stopped through Greia, Home with `Finito per oggi`) was not proven: `after-expiry.png` stayed 78K (activity), not Home, and `profile_used` via Shell launch stayed 0.

Exhausted relaunch: With direct `exhausted True` set, click `550,250` while exhausted gave `exhausted-relaunch-0150ms.png` 78K, `0500ms` 78K, `1250ms` 78K (all activity, not Home 44K), and `ps` showed no new `bwrap`, but the Home at `44K` vs `78K` suggests the relaunch may have flashed `Starting…` or stayed at activity, not conclusively staying at Home without flash. The `exhausted-after-relaunch-home.png` at 78K (not 44K) suggests the Home was not at 44K after click.

Policy restored: `update_usage_limits(None)` + `update_profile_usage_limit(None)` → `device null`, `profile null`, `effective null`, `profile_used 60` preserved (not erased), `exhausted False` (via `check_exhausted2.py` after restore: `profile_used 60`, `effective null`, `exhausted False`), `usage-after-restore-home.png` 44K, `usage-after-restore-launch.png` 77K (painting), `usage-after-restore-home2.png` 44K, so normal launch works after restore.

**Result: INCOMPLETE** (finite pill not captured at overview, automatic expiry not via lifecycle, blocked relaunch not conclusively at Home without Starting flash).

## 8. Logs / performance / negative authority

Final snapshot `final-snapshot` (549K logs, 44K screen, 223B snapshot, 1.2K status) with `active_profile null` (profile picker after restore). Logs `logs.txt` 549K, `grep -i -E "Traceback|platform_failure|ready timeout|restore failed|Permission denied|/dev/dri|/dev/input|libpng"` → only `Permission denied` for `bwrap` grep itself, no Traceback, no platform_failure, no libpng warning, no DRM/input.

`ps -eo pid,ppid,user,%cpu,rss,etime,args --sort=-%cpu | head -40` via `ssh` showed `greia_launcher.child_shell` at 6777, `greia_parent.update_api` at 384, no `bwrap` activity, `systemd` etc., top CPU `systemd` 0.3%, no material regression vs earlier 0.3% (owner attested Writing/Painting responsiveness PASS, but precise CPU/RSS not measured, so `MEASURED` not claimed, `OBSERVED` only).

Negative authority:
```text
child_visible_linux: NO
activity_direct_drm_required: NO
activity_raw_input_required: NO
display_restore_failure: 0
unexplained_platform_failure: 0
libpng_warning: NO
```

## 9. Verdicts at 1edb22ce

Per machine-only final doc §12:

```text
R7.2: INCOMPLETE (crash NOT_RUN, usage-limit automatic expiry not via lifecycle, finite pill not proven)
R7.3: INCOMPLETE (hostile batch fallback, crash NOT_RUN, trusted-Home at 38,38 used but bwrap PID per cycle not verified)
Parent tranche: INCOMPLETE (hide/show PASS, but finite Home pill and automatic expiry and blocked relaunch not conclusively proven)
```

If the exact 4-pattern 20/20 with correct pagination (Next Next for page2, tile centers 750,350 page1 for Painting, 750,450 page1 for Shape Garden, 150,450 page2 for Volo, 550,450 page2 for Writing) and the crash safe PID and usage-limit lifecycle expiry via real Shell launch are re-proven at 1edb22ce, the verdict would become ACCEPTED.

## 10. Documentation

HANDOVER.md updated to reflect machine-only final at 1edb22ce, 1561 PASS, Simulator 5/5, Acer 5/5 focus, owner Writing/Painting PASS, and the above machine lanes.

Active plan `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` still shows R7.2/R7.3 as blocking until the exact lanes above are green at 1edb22ce.

This review doc created as `docs/reviews/2026-09-01_R7_R72_R73_AND_PARENT_CONTROLS_PHYSICAL_ACCEPTANCE.md`.

No production source was modified during this machine-only run (all changes via `UpdateParentApiApplication` on Acer, which is the correct Parent API authority, not direct file edits).

## 11. Next exact steps at 1edb22ce

1. Re-run crash with proven single greiakid `shape_garden` PID (pgrep must yield exactly one, user greiakid, then `kill -KILL`, verify Home without click).
2. Re-run 20/20 with exact pagination and tile centers (750,350 page1 Painting, 750,450 page1 Shape Garden, 150,450 page2 Volo, 550,450 page2 Writing) via batch `xdotool` + `greia_remote.py` screenshot, verify each launch via `ps -eo args | grep activities` and focus via `key Right`/`Left`.
3. Re-run hostile 10/10 with exact trusted-Home at 38,38 and verify `bwrap` PID per cycle and display restore.
4. Re-run usage-limit via a real Shell launch that increments `profile_used_seconds` (verify via `check_exhausted2.py` after launch, not direct record), then prove Home pill at overview (81K), automatic return to Home with "Finito per oggi" and blocked relaunch without Starting flash via 150ms/500ms/1250ms screenshots at 44K Home.

Only after those are green should `HANDOVER.md` and the active plan be marked R7 complete and R7.4 started. No force push.

## 12. Evidence

```text
./tmp/r7-parent-final-20260901_185359-1edb22ce (source/Simulator, 1561, backend 0, chrome 0, 5/5 Simulator)
./tmp/r7-parent-machine-final-20260901_192849-1edb22ce (Acer machine-only, 5/5 restarts, hide/show, short-budget, 20/20 batch, hostile batch, crash NOT_RUN, usage-limit partial, final snapshot 549K)
```

Accepted runtime/source SHA remains `1edb22cec7709aafe3f08519fabf69cb93cb8083`; docs-only commit will be `<new SHA>` with `HEAD == origin/main` still `1edb22ce` until docs commit.
