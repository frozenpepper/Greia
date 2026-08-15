# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4  
**Blocking phase:** **R7 — Direct graphics/session/input architecture**

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

GitHub is canonical. Resolve the actual branch HEAD before editing or testing.

## Hosted execution boundary

Do **not** use, query, trigger, rerun, inspect or download GitHub Actions runs/jobs/logs/artifacts without explicit owner authorization for that specific hosted use.

Repository source/PR operations are allowed. No GitHub Actions service was used in the 2026-08-15 UI/input/remote-control tranches.

## Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer is **UNPROVEN** unless explicitly recorded otherwise. Do not infer PASS from committed tests or source review.

## R7 production state

```text
installed display path:          Xorg + xinit compatibility
status:                          PROVISIONAL
production compositor:           none selected
serial direct DRM:               evidence candidate only
trusted Activity Home/Back:      contracts/coordinator source implemented; concrete backend UNPROVEN
controller semantic core:        source implemented; UNPROVEN
Shell controller helper:         source implemented; live composition pending verification
production Activity input broker: NOT IMPLEMENTED
physical Acer R7 evidence:       NOT RUN for current branch
Pi evidence:                     later R8/R14
```

Production migration still requires physical legacy Intel/Acer evidence. Ordinary Activities do not become DRM or raw-input owners.

## ADR 0018 — lightweight UI foundation

Renderer-neutral UI source:

```text
src/greia_platform/ui_core.py
```

Current stable vocabulary:

```text
Screen
Overlay / Sheet
Panel / Card / Collection
Control
```

A child-visible folder-like thing is a semantic `Collection`, never a Linux path.

The foundation includes bounded `PagedGrid`, `BoundedCache`, `InvalidationTracker` and `SurfaceNavigator`. New shared Pygame code imports `pygame_ui.py`; current implementation remains in `activity_ui.py` for compatibility.

First-party Writing and Painting source exists and remains unexecuted/hardware-unproven.

## ADR 0019 — mandatory Greia Home/Back

Product requirement:

```text
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Every child-facing Activity must retain Greia-owned **Home** outside Activity rendering/input authority. Optional **Back** returns to a valid Greia launch origin; it is not browser history or Activity-internal navigation.

Source:

```text
src/greia_platform/system_chrome.py
src/greia_launcher/system_chrome.py
```

The current Xorg path does **not yet** provide a physically accepted trusted overlay/protected-input implementation, so ADR 0019 remains an R7 blocker.

## ADR 0020 — runtime-neutral input/controller support

Product requirement:

```text
docs/product/ACTIVITY_INPUT_STANDARDS.md
```

Interaction profiles:

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
pointer: mouse/touch plus Greia semantic controller virtual pointer
text: preserve real keyboard typing/editing semantics
```

Key source:

```text
src/greia_platform/input_core.py
src/greia_platform/pygame_input.py
src/greia_launcher/shell_input.py
src/greia_platform/hal.py
src/greia_platform/device_capabilities.py
```

Important invariants:

- controller is a device capability, not an Activity-specific controller stack;
- consumer-brand button names terminate at backend adapters;
- Guide/system input is platform-reserved where available;
- ordinary Activities do not receive broad `/dev/input`;
- controller-to-pointer behavior is semantic, not a global fake Linux mouse;
- Writing declares `text`; Painting declares `pointer`;
- mapped game controllers and generic/unmapped joysticks remain distinct compatibility cases; see `docs/reviews/2026-08-15_INPUT_CONTROLLER_FOUNDATION_ADVERSARIAL_REVIEW.md`.

`ShellInputController` is source-ready but is intentionally **not yet composed into `greia_launcher.main`**. After source PASS, integrate it narrowly without combining that change with the larger Shell UI migration.

## Acer remote-agent development control

### Goal

After a **developer image** is installed on the Acer, an agent running on the operator computer should be able to control, observe, test and monitor the target without routine physical interaction.

Source review:

```text
docs/reviews/2026-08-15_ACER_REMOTE_AGENT_CONTROL_REVIEW.md
```

Physical acceptance protocol:

```text
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

### Acer developer profiles

The physical Acer profile is still an evidence question, so the repository carries three normal candidates and three matching developer variants:

```text
normal                              developer remote
acer-aspire-one-i386                acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae         acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64               acer-aspire-one-amd64-dev
```

Each `*-dev` profile preserves the matching Acer architecture, kernel, Xorg/video packages, C0 resource policy and image layout, adds `developer-remote`, uses hostname `greia-dev`, and remains `experimental`.

Do **not** use `modern-amd64-dev` on the Acer merely for convenience.

Build shape:

```bash
PROFILE="acer-aspire-one-i386-dev"   # replace only after physical profile selection
sudo bash build/build-developer-image.sh out "$PROFILE"
```

The wrapper still defaults to `modern-amd64-dev` if the optional profile argument is omitted, preserving existing behavior.

`tools/provision_developer_image.py` now validates the exact requested profile and independently requires the embedded `developer-remote` package set, so it cannot silently convert a normal profile into a remote developer image.

### Installed remote-control surface

Operator client:

```text
tools/greia_remote.py
```

Stable operations include:

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

Transport/security:

- key-only SSH as `greiaadmin`;
- password and keyboard-interactive authentication disabled;
- root SSH disabled;
- private operator key remains off the target;
- target generates its own SSH host keys;
- dedicated Greia known-hosts file;
- passwordless privileged automation restricted to `/usr/local/sbin/greia-devctl`;
- no unrestricted root command API;
- normal/release profiles remain remote-disabled.

First physical acceptance should use wired Ethernet/DHCP + mDNS. Expected host:

```text
greia-dev.local
```

### Screenshot transfer

The screenshot path is already end-to-end in source:

```text
operator agent
→ SSH
→ greia-devctl screenshot
→ fixed capture helper as greiakid on declared display
→ current Xorg compatibility capture via Pillow/ImageGrab
→ PNG bytes on SSH stdout
→ tools/greia_remote.py validates PNG
→ local operator file
```

There is no separate manual screenshot-copy step.

Example:

```bash
python3 tools/greia_remote.py \
  --host greia-dev.local \
  --key out/greia-os-${PROFILE}-ssh-key \
  screenshot out/acer-screen.png
```

The capture backend is Xorg compatibility implementation. When R7 changes display ownership, the backend below this stable operator command must change.

### Agent-friendly observation bundle

New `snapshot` command:

```bash
python3 tools/greia_remote.py \
  --host greia-dev.local \
  --key out/greia-os-${PROFILE}-ssh-key \
  snapshot out/acer-observation-001 \
  --service all --lines 500
```

Local output:

```text
screen.png
status.json
logs.txt
snapshot.json
```

This is the preferred observation primitive for an agent on the operator computer. It gives visual state + structured machine state + bounded logs in one local directory.

### Remote GUI testing

Current developer input uses fixed `/usr/bin/xdotool` beneath bounded Greia commands. The agent can:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" key Right
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" key Return
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" mousemove 500 300
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" click
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" type "Greia test"
```

Input is bounded and executed against the declared Greia display user rather than a root desktop/session.

### Status/log/restart/reboot monitoring

The agent can collect machine-readable status and bounded journal groups, restart the launcher, reboot/power off, wait for the machine to reappear, and collect a new snapshot.

Typical unattended loop:

```text
wait
→ snapshot
→ inject input
→ snapshot
→ inspect local PNG/status/logs
→ repeat
→ restart/reboot if needed
→ wait
→ snapshot
```

### Activity iteration

`deploy`, `remove`, and `restore` are source-implemented. Ordinary developer Activities remain `DEVELOPER_UNSIGNED`; remote file placement cannot upgrade trust. Built-in replacement requires explicit `--replace-system` and preserves the original for restore.

### Important current limitation — Greia core hot-deployment

The remote surface is sufficient to **control/test/monitor the installed system and iterate Activities**, but it does **not yet provide arbitrary hot replacement of `/opt/greia-os/src`** for Greia platform/core changes.

That is intentional today because `greia-devctl` itself uses the immutable installed source. A bad arbitrary platform upload must not be able to destroy the recovery/control implementation needed to revert it.

Core/platform Python changes therefore currently require a rebuilt/reinstalled developer image before executing them on the Acer.

If a developer platform-overlay mechanism is added later, it must keep `greia-devctl` and rollback authority outside the replaceable tree and support atomic rollback after an immediately crashing upload. Do not solve this by granting unrestricted root SSH/sudo.

### First-time remote installation limitation

`tools/provision_developer_installer.py` exists, but the remote developer live-installer path is **not yet wired/physically accepted through the canonical installer image builder**.

Therefore do not claim the very first USB installation is remotely operable. The current accepted remote-agent workflow starts after the developer target has been installed through an existing safe path and boots.

### Physical proof status

No Acer developer image built from this new source has yet been physically booted and exercised. Therefore these are **source capabilities, not a hardware PASS**.

Physical certification requires `docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md`, including:

- remote discovery/readiness;
- key-only authentication;
- screenshot matching the actual physical Acer display;
- PNG transfer to the operator computer;
- keyboard/pointer interaction with before/after screenshots;
- status/log monitoring;
- launcher restart;
- reboot/reconnect;
- Activity deploy/remove/restore;
- developer security boundary checks.

## New remote-control regression source

Committed but unexecuted:

```text
tests/test_developer_remote.py
tests/test_developer_remote_profiles.py
tests/test_developer_remote_snapshot.py
```

Focused remote verification on an owner-controlled checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_developer_remote \
  tests.test_developer_remote_profiles \
  tests.test_developer_remote_snapshot \
  -v
```

Then run the broader current input/UI/creative focused suite and:

```bash
make verify
```

Stop on first real failure. Do not weaken security/profile/screenshot contracts to manufacture PASS.

## Exact next physical remote-agent step

After source PASS:

1. identify which Acer hardware profile the physical unit actually supports;
2. build the matching `*-dev` image;
3. install it through the existing safe graphical path;
4. connect wired Ethernet for first acceptance;
5. run `docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md` from the operator computer;
6. preserve screenshot/status/log evidence and first failure;
7. only after that claim the Acer is remotely agent-operable.

## Other immediate R7 work after source verification

- minimally compose `ShellInputController` into the Shell;
- implement the trusted production Activity input broker beside ADR 0019 system chrome;
- prove controller/joystick behavior physically;
- continue exact-image/direct-graphics/package/resource evidence;
- do not select a production compositor without evidence;
- do not big-bang rewrite Shell/installer UI.

## Invariants

- no visible Linux UI in normal child operation;
- Activity remains runtime-neutral;
- every child Activity retains Greia-owned Home outside Activity authority;
- controller/joystick semantics are Greia-owned and runtime-neutral;
- ordinary Activities do not receive broad raw input access;
- developer remote control is explicit dev-image capability, never release default;
- screenshot/input automation stays behind bounded developer commands;
- private SSH keys never enter the image/repository/evidence bundle;
- remote Activity placement does not upgrade trust;
- Acer remains the extreme resource floor and ARM remains co-equal;
- GitHub remains canonical source persistence;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- strong OOP/polymorphic seams with bounded resource ownership;
- source/VM/physical evidence boundaries remain explicit and honest.
