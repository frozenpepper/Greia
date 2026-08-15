# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Current main HEAD before this handover commit:** `6019eb06134478861010cdcfae649a921f1ffc7d`  
**Blocking phase:** **R7 — Direct graphics/session/input architecture**

## Branch policy

The repository owner has explicitly requested a **single-branch workflow**.

From 2026-08-15 onward:

- `main` is the only development/integration branch;
- do not create feature, recovery, archive or work branches unless the owner explicitly changes this policy;
- commit coherent work directly to `main` as work proceeds;
- GitHub remains the persistent source of truth;
- old branch refs were collapsed onto the same `main` commit after review so no divergent current source remains;
- the available GitHub connector did not expose branch-ref deletion, so duplicate ref names may remain visible until deleted through a GitHub surface that supports ref deletion. They contain the same commit as `main` and must not be used for development.

PR #4 (`r7-direct-graphics`) was merged into `main` with merge commit:

```text
6019eb06134478861010cdcfae649a921f1ffc7d
```

Before collapse, the remaining non-main branches were reviewed. Branch-only material not already in `main` consisted only of obsolete recovery/probe payloads and old recovery GitHub Actions workflows, not current project source. Those obsolete artifacts were deliberately **not reintroduced into `main`**; the refs were moved to current `main` instead.

## Resume order

Read, in order:

1. `AGENTS.md`
2. `README.md`
3. `docs/DOCUMENTATION.md`
4. `docs/architecture/GREIA_ARCHITECTURE.md`
5. accepted ADRs through ADR 0020
6. `docs/engineering/ENGINEERING_FOUNDATIONS.md`
7. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
8. this handover
9. applicable testing/review docs
10. `docs/agents/GREIA_AGENT_OPERATIONS.md`
11. `skills/greia-activity-authoring/SKILL.md` for Activity work

Always resolve the current **`main` HEAD** before editing or testing.

## Hosted execution boundary

Do **not** use, query, trigger, rerun, inspect or download GitHub Actions runs/jobs/logs/artifacts without explicit owner authorization for that specific hosted use.

Repository source operations are allowed. Verification runs locally or on an explicitly owner-approved execution environment.

## Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer remains **UNPROVEN unless explicitly recorded otherwise**. Do not promote source presence to runtime or hardware PASS.

## Current Phase-0 UI / system-navigation state

ADR 0018 owns the lightweight Greia UI foundation:

```text
Screen
  -> optional Overlay / Sheet
       -> Panel / Card / Collection
            -> Control
```

Renderer-neutral implementation lives in:

```text
src/greia_platform/ui_core.py
```

ADR 0019 requires immutable Greia-owned Activity navigation:

- Home is mandatory whenever an Activity is visible;
- Home is outside Activity rendering/input authority;
- Home always ends the Activity through Greia lifecycle authority;
- Back is optional only when there is a meaningful previous Greia origin;
- Python, Web and first-party Activities receive no exemption.

Relevant source:

```text
src/greia_platform/system_chrome.py
src/greia_launcher/system_chrome.py
```

No concrete production trusted `SystemChromeBackend` has yet passed real hardware acceptance.

## Phase-0 input/controller state — ADR 0020

Controller/joystick support is a Phase-0 requirement. Activities declare interaction intent rather than controller brands or Linux device paths.

Current profiles:

```text
navigation
pointer
directional
game
text
hybrid
```

Learned baseline:

```text
navigation: arrows / D-pad-or-left-stick; Space/Enter / south face activate
simple game: arrows + Space; D-pad/left-stick + south face primary
pointer: mouse/touch plus Greia controller virtual pointer; south face primary
text: preserve real typing/editing semantics
```

Core source:

```text
src/greia_platform/input_core.py
src/greia_platform/pygame_input.py
src/greia_launcher/shell_input.py
```

Important boundaries:

- controller is a HAL/device capability, not an Activity-specific hardware API;
- ordinary Activities do not receive broad `/dev/input` merely for controller support;
- Guide/system controller input is platform-reserved where the backend exposes it reliably;
- `ShellInputController` is source-ready but still requires minimal verified composition into the real Shell loop;
- production Activity controller delivery still requires the trusted R7 physical-input broker/session layer;
- generic unmapped joysticks remain a specific Phase-0 compatibility question: calibration/mapping, a conservative fallback or an explicit mapped-controller support contract must be chosen and physically proven.

Physical acceptance procedure:

```text
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

## First-party Phase-0 creative Activities

Source exists for:

```text
org.greia.writing  -> text input profile
org.greia.painting -> pointer input profile
```

Writing and Painting remain source-implemented but current execution/hardware evidence is unproven.

## Developer remote-control / Acer agent workflow

The installed developer-image architecture is designed so an agent running on the operator computer can remotely test and monitor Greia over the LAN.

Operator client:

```text
tools/greia_remote.py
```

Supported operations include:

```text
wait
status
screenshot
snapshot
logs
key
mousemove
click
type
deploy
remove
restore
restart
restart-installer
reboot
poweroff
shell
```

`screenshot` streams the actual Greia display as PNG bytes over SSH directly to the operator computer.

`snapshot` collects a local evidence directory containing:

```text
screen.png
status.json
logs.txt
snapshot.json
```

This is the intended primitive for a local development agent to observe -> interact -> observe repeatedly.

Explicit Acer developer profiles now exist for all current Acer architecture candidates:

```text
acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64-dev
```

Matching non-development Acer profiles remain remote-disabled.

The generalized developer-image builder is:

```bash
sudo bash build/build-developer-image.sh out <developer-profile>
```

The provisioner checks the exact requested profile plus the explicit `developer-remote` package set before provisioning key-only SSH.

Security invariants:

- password authentication disabled;
- root SSH login disabled;
- private client key stays on the operator machine;
- actual machine creates its own SSH host identity;
- privileged automation is bounded through `/usr/local/sbin/greia-devctl`;
- normal remotely deployed Activities remain `DEVELOPER_UNSIGNED`;
- current remote screenshot/input are Xorg developer-compatibility implementations, not R7 production architecture.

Physical Acer remote-agent acceptance:

```text
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

Current status is **SOURCE-IMPLEMENTED / PHYSICAL ACCEPTANCE NOT RUN**.

Important remaining distinction: Activities can be deployed remotely, but arbitrary hot replacement of Greia's own immutable `/opt/greia-os/src` platform code is not yet exposed. A future developer-only rollback-safe platform overlay may provide that workflow while keeping the recovery/control surface immutable.

## R7 production state

```text
installed display path:       Xorg + xinit compatibility
status:                       PROVISIONAL
production compositor:        none selected
serial direct DRM:            evidence candidate only
trusted system chrome:        contract/coordinator source implemented; backend unproven
controller semantic core:     source implemented; unproven
trusted Pygame controller set: source implemented; Shell composition pending verification
production Activity input broker: NOT IMPLEMENTED
physical controller evidence: NOT RUN
Acer remote-agent physical evidence: NOT RUN
```

Do not make `ActivitySupervisor` the DRM master. Do not broaden Activity raw input authority. Do not select a compositor merely because desktop Linux commonly uses one.

## Exact next source verification

On an owner-controlled current checkout of `main`:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_input_core \
  tests.test_pygame_input \
  tests.test_activity_input_contract \
  tests.test_activity_input_api \
  tests.test_hal_legacy_x \
  tests.test_shell_input \
  tests.test_system_chrome \
  tests.test_ui_core \
  tests.test_ui_core_lifecycle \
  tests.test_activity_ui \
  tests.test_core_creation_activities \
  tests.test_activity_theme_access \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting

PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify
```

Stop on first real failure and preserve exact stdout/stderr. Do not weaken tests to manufacture PASS.

## Next implementation after source PASS

Keep changes incremental and commit directly to `main`:

1. minimally compose `ShellInputController` into `greia_launcher.main`, with explicit suspend/resume/cleanup around Activity presentation;
2. verify Shell controller navigation/reconnect on owner-controlled hardware;
3. implement the R7 trusted physical-input broker beside display-session/system-chrome authority so Activities receive normalized semantic controller input without `/dev/input` ownership;
4. integrate controller virtual-pointer behavior into Painting;
5. prove one simple directional/game Activity using keyboard/controller parity;
6. prove Guide/system input is withheld from Activity content;
7. execute Acer input/resource/latency evidence;
8. build/install the correct Acer developer profile and execute the remote-agent acceptance protocol;
9. later expose the same semantic input bridge to the Web runtime;
10. only after real evidence, decide whether the production display/session implementation is serial direct ownership, a tiny Greia-owned compositor/session broker, or a retained explicit compatibility adapter.

Do not combine the small Shell input integration with a broad UI rewrite.

## Invariants

- `main` is the sole development branch unless the owner explicitly changes policy;
- no visible Linux UI in normal child operation;
- Activity remains runtime-neutral;
- every child-facing Activity retains Greia-owned Home outside Activity authority;
- controller/joystick support is a platform concern, not per-Activity raw hardware code;
- ordinary Activities do not gain raw `/dev/input` merely for controller support;
- progression/rewards remain platform-owned;
- child state remains portable/profile-scoped;
- Acer remains the extreme resource floor and ARM remains co-equal;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- strong OOP/polymorphic seams with bounded resource ownership;
- source/VM/physical evidence boundaries remain explicit and honest.
