# R7.3 Trusted System Chrome — Source and Acer Acceptance

**Date:** 2026-08-29  
**Status:** execution protocol — source and physical acceptance pending  
**Phase:** R7.3  
**Authority:** ADR 0014, ADR 0019, ADR 0020 and the active architecture-remediation plan.

This gate proves the current Greia-owned Activity Home boundary on the Legacy-X compatibility session. It is migration evidence only; it does not make X11 the target architecture.

## 1. Evidence rules

Record before testing:

```bash
git rev-parse HEAD
git status --short
git log -1 --oneline
```

Use one exact SHA for the complete attempt. Do not use/query GitHub Actions. Do not weaken Activity sandbox/device authority or restore Activity-owned Home behavior to obtain a PASS.

A source failure ends that attempt. Fix it, commit a new SHA, and start again.

## 2. Source gate

Run:

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
  tests.test_activity_system_chrome_audit \
  -v
```

Then:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
make verify
```

Required:

```text
Activity backend blockers: 0
Activity system chrome ownership audit: blockers=0
make verify: exit 0
```

The AST-based system-chrome audit is the canonical catalogue check. Do not add a second grep/string-presence test for the same rule.

Renderer-neutral protected/safe geometry remains valid. The forbidden ownership is Activity rendering/input handling of the real Home/Back action.

## 3. Deploy exact source

Only after the source gate is green, deploy the exact tested SHA through the existing Greia developer deployment route.

Capture baseline:

```bash
python3 tools/greia_remote.py --password greia status
python3 tools/greia_remote.py --password greia snapshot ./tmp/r7-r73-acer-before --service launcher --lines 500
```

If the deployed/running source is uncertain, disposition is `INCOMPLETE` until resolved.

## 4. Writing and Painting

From the real child Shell test both Activities.

### Writing

- launch normally;
- trusted Home is visible in the canonical protected region;
- type/edit text normally;
- Home activation does not leak into Writing input;
- return to Shell is clean;
- saved state remains correct.

### Painting

- launch normally;
- trusted Home is visible;
- draw continuously for at least 10 seconds;
- drawing remains responsive;
- Home activation creates no stray stroke;
- return to Shell is clean;
- saved state remains correct.

No Linux/Xorg/terminal surface may become child-visible during launch or return.

## 5. Non-cooperative fixture

Deploy:

```bash
python3 tools/greia_remote.py --password greia deploy \
  tests/fixtures/activities/r7_noncooperative_chrome
```

Launch:

```text
org.greia.fixture.r7-noncooperative-chrome
```

The fixture deliberately fills its own SDL surface, draws no Home, ignores normal local exit input, and ignores graceful STOP.

Required first cycle:

- hostile red Activity surface is visible;
- trusted Greia Home remains above it;
- Activity input does not exit it;
- trusted Home requests return;
- graceful stop is ignored by the fixture;
- bounded platform force-termination occurs;
- Shell returns cleanly;
- no stale chrome or Activity process remains;
- the next normal Activity still launches.

Then repeat launch -> trusted Home -> forced return **10 consecutive times without restarting the launcher**.

Required:

```text
10/10 returns
0 stale chrome windows
0 stuck Activity processes
0 launcher restarts
0 Linux/Xorg/terminal exposure
```

After cycle 10, launch Writing once more and return via Home.

## 6. Crash recovery

Use an existing safe disposable test path to terminate an active Activity abruptly.

Required:

- Shell recovers;
- trusted chrome disappears;
- no stale lease/window remains;
- next Activity launches normally.

If no safe existing mechanism is available, do not invent one on the device; report this portion `NOT_RUN` and the overall result `INCOMPLETE`.

## 7. Performance

Performance is correctness on the Acer floor. Observe/measure where practical:

- Shell idle;
- Writing idle and typing;
- Painting idle and >=15 s sustained drawing;
- one static/dirty Activity;
- one continuously animated Activity;
- launch -> READY;
- Home -> Shell;
- hostile fixture while awaiting forced termination.

Record CPU/RSS/PSS/latency where available, and clearly separate `MEASURED`, `OBSERVED`, and `NOT MEASURED`.

Reject designs that introduce:

- Python framebuffer/pixel proxying;
- avoidable full-frame copies;
- continuous full-screen alpha composition;
- a second Pygame chrome process;
- high-rate pointer/text IPC;
- material Writing/Painting responsiveness regression.

Do not invent numerical improvements without measurement.

## 8. Verdict

Return exactly one:

### `ACCEPTED`

Requires all source gates green, compatible R7.2 evidence, Writing/Painting physical success, hostile 10/10 success, crash recovery, acceptable performance, and no child-visible Linux surface.

### `REJECTED`

Use for a real required invariant failure.

### `INCOMPLETE`

Use when a required evidence lane genuinely could not execute. State exactly what remains.

## 9. After acceptance

Only after R7.3 physical acceptance:

1. promote the zero-debt system-chrome rule into normal Activity validation;
2. remove any remaining temporary compatibility API once zero callers are confirmed;
3. preserve protected/safe geometry;
4. continue R7.4 physical controller/system-input ownership and ADR-0014 direct/compositor evidence.
