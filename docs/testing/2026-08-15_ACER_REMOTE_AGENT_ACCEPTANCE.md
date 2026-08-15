# Greia — Acer Remote Agent Control Acceptance

**Date:** 2026-08-15  
**Status:** ACTIVE physical acceptance protocol / NOT YET EXECUTED  
**Scope:** installed Acer developer image controlled by an agent/operator computer over the local network  
**Hosted execution:** GitHub Actions is not used by this protocol

## Goal

Prove that after Greia is installed on the Acer Aspire One, an agent running on the operator computer can control, observe, test and monitor the installed development system without routine physical interaction with the netbook.

The accepted loop must support:

```text
agent changes/test plan on operator computer
        ↓
wait for Acer / inspect status
        ↓
inject bounded GUI input
        ↓
capture real Acer screen to local PNG
        ↓
collect bounded Acer logs + machine state
        ↓
agent inspects evidence
        ↓
repeat / restart / reboot / deploy Activity as needed
```

The Acer remains the machine executing Greia. Screenshots and text evidence are transferred back to the operator computer for agent inspection.

## 1. Select the correct Acer developer profile

The repository currently carries three Acer hardware candidates because CPU/PAE support is a physical-evidence question:

```text
acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64-dev
```

Use the developer variant corresponding to the Acer hardware profile actually accepted for the physical unit. Do not substitute `modern-amd64-dev` merely because it is convenient.

The developer variants preserve their matching Acer architecture/kernel/display/resource profile and add only the explicit development remote package set and developer hostname/policy.

## 2. Build the installed developer image

On an owner-controlled x86-64 Debian/Ubuntu build environment:

```bash
PROFILE="acer-aspire-one-i386-dev"   # replace only with the accepted Acer dev profile
sudo bash build/build-developer-image.sh out "$PROFILE"
```

Expected artifacts include:

```text
out/greia-os-${PROFILE}.img
out/greia-os-${PROFILE}-ssh-key
out/greia-os-${PROFILE}-ssh-key.pub
out/greia-os-${PROFILE}-developer-remote.json
```

The private SSH key is operator-only credential material. Never copy it into Git, chat evidence, or the Acer image.

## 3. Install through an already accepted safe path

Install the developer image on the Acer using the currently accepted graphical/device-safe installation path.

Remote first-time graphical installation is a separate feature: `tools/provision_developer_installer.py` exists, but its canonical installer-builder integration remains unproven unless `HANDOVER.md` explicitly says otherwise.

For this acceptance, the requirement begins after the installed developer target boots.

## 4. Network setup

For first acceptance use wired Ethernet.

The installed developer target should request DHCP and advertise:

```text
greia-dev.local
```

If mDNS resolution is unavailable but the Acer has a verified DHCP address, pass that address with `--host`. Do not disable SSH host-key checking.

Set operator variables:

```bash
PROFILE="acer-aspire-one-i386-dev"   # exact installed profile
KEY="out/greia-os-${PROFILE}-ssh-key"
HOST="greia-dev.local"
```

## 5. Prove unattended remote readiness

From the operator computer:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" wait --timeout 180
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" status > out/acer-status-initial.json
```

Expected:

- no password prompt;
- no interactive sudo prompt;
- `developer_remote` is true;
- hostname matches the developer target;
- launcher/developer-remote/SSH state is visible in the returned JSON;
- display endpoint identifies the installed Greia child display session;
- no root SSH login is used.

Failure to connect is evidence. Preserve the error before changing network/security configuration.

## 6. Prove screenshot capture and transfer

Capture the actual Acer screen:

```bash
python3 tools/greia_remote.py \
  --host "$HOST" --key "$KEY" \
  screenshot out/acer-screen-initial.png
```

Acceptance:

1. the local file begins with a valid PNG signature;
2. it opens successfully on the operator computer;
3. its visible content matches the Acer's actual physical screen at the same moment;
4. child UI is fully captured rather than a blank/black/root desktop image;
5. no manual file copy from the Acer is required.

Current Xorg compatibility path is:

```text
operator agent
→ SSH public-key session
→ sudo -n greia-devctl screenshot
→ run capture helper as greiakid on DISPLAY=:0
→ Pillow/ImageGrab
→ PNG bytes over SSH stdout
→ local screen.png
```

The stable operator command must survive a later R7 display-backend migration even though the capture implementation underneath it will change.

## 7. Prove agent-friendly evidence snapshots

Collect a self-contained observation:

```bash
python3 tools/greia_remote.py \
  --host "$HOST" --key "$KEY" \
  snapshot out/acer-observation-001 \
  --service all --lines 500
```

The local directory must contain:

```text
screen.png
status.json
logs.txt
snapshot.json
```

This is the preferred observation primitive for an autonomous/local agent. It gives the agent visual state, structured machine state and bounded logs in one local directory without broad remote filesystem access.

## 8. Prove remote keyboard control

Record a snapshot before each step when visual state matters.

Examples:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" key Right
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" snapshot out/acer-after-right --service launcher --lines 200

python3 tools/greia_remote.py --host "$HOST" --key "$KEY" key Return
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" snapshot out/acer-after-return --service launcher --lines 200
```

Acceptance:

- the expected Greia selection/navigation changes;
- screenshots prove the visible transition;
- input is injected into Greia, not a terminal/root session;
- no unrestricted executable or shell command is accepted through the GUI-input API.

## 9. Prove remote pointer control

Use a visible target in the current Greia UI:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" mousemove 500 300
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" click
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" snapshot out/acer-after-click --service launcher --lines 200
```

Acceptance:

- the visible Greia pointer/target behavior matches the commanded coordinate/click;
- screenshot proves the resulting state;
- mouse coordinates remain bounded by the developer-input API.

## 10. Prove typed input where applicable

For a child/profile text surface that expects normal text:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" type "Greia test"
```

The developer API deliberately bounds text length and rejects multiline/shell-shaped control strings.

## 11. Prove logs and monitoring

Examples:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" logs --service launcher --lines 500
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" logs --service network --lines 500
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" status
```

An agent may repeat `snapshot` at meaningful checkpoints. Do not create a high-frequency screenshot loop on the Acer; observation cadence should follow actual test actions/events.

## 12. Prove launcher restart and recovery

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" restart
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" wait --timeout 120
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" snapshot out/acer-after-launcher-restart --service launcher --lines 500
```

Acceptance:

- launcher returns without touching the Acer;
- screenshot proves child-facing Greia is back;
- status/logs expose any restart failure.

## 13. Prove reboot and reconnect

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" reboot
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" wait --timeout 180
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" snapshot out/acer-after-reboot --service all --lines 500
```

Acceptance:

- SSH disconnect caused by reboot is treated as expected by the client;
- Acer reappears without physical login/terminal interaction;
- the same operator client key still authenticates;
- screenshot and status are obtainable after boot.

## 14. Prove Activity iteration

For a developer Activity with an ID that does not collide with an installed built-in:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" deploy path/to/test-activity
```

Then use screenshots/input to launch and test it.

Acceptance:

- package is revalidated on the Acer;
- it remains `DEVELOPER_UNSIGNED`;
- privileged permission requests are rejected for ordinary developer deployment;
- launcher refreshes after deployment;
- removal works remotely:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" remove <activity-id>
```

Built-in replacement is an explicit separate operation using `--replace-system` and must preserve restore capability.

## 15. Platform-source development boundary

The current remote surface is sufficient to control/test/monitor the **installed Greia system** and to iterate Activities.

It does not currently provide an arbitrary privileged “replace `/opt/greia-os/src`” endpoint. This is intentional: one bad platform upload must not destroy the very recovery/control tool needed to restore the machine.

Platform/core changes currently require either:

- a new developer image/reinstall through a safe path; or
- a future dedicated recoverable platform-overlay mechanism designed so `greia-devctl` remains outside the code being replaced.

Do not bypass this boundary by granting the agent unrestricted root SSH/sudo.

## 16. Maintenance shell

If bounded controls are insufficient for diagnosis:

```bash
python3 tools/greia_remote.py --host "$HOST" --key "$KEY" shell
```

This opens an explicit unprivileged `greiaadmin` maintenance shell. It is useful for inspection and diagnostic commands, not a replacement for bounded privileged automation.

## 17. Security acceptance

Verify:

- password authentication fails;
- root SSH login fails;
- `greiaadmin` cannot use unrestricted passwordless `sudo`;
- `sudo -n /usr/local/sbin/greia-devctl ...` is the passwordless privileged automation surface;
- normal/non-dev Acer profiles do not enable developer remote control;
- developer private key is absent from the Acer image;
- first-boot machine SSH host keys are unique to that installed Acer;
- a host-key mismatch after an unexpected identity change causes connection failure rather than silent acceptance.

## 18. Evidence to return

Preserve at minimum:

```text
exact repository SHA
exact Acer dev profile ID
image SHA-256 / developer-remote report
Acer hardware inventory relevant to architecture/PAE
initial status JSON
initial screenshot PNG
keyboard-navigation before/after screenshots
pointer before/after screenshots
launcher restart observation
reboot/reconnect observation
bounded logs for failures
final agent snapshot directory
```

Do not include the private SSH key.

## 19. PASS meaning

A PASS proves that the tested Acer developer image can be remotely **controlled, observed and exercised by an agent on the operator computer**, including real screenshot transfer and reboot/reconnect.

It does not prove:

- release images expose SSH (they deliberately must not);
- first-time USB installation is remotely operable;
- arbitrary platform source hot-deployment exists;
- future non-Xorg capture/input backends already work;
- Pi remote-development acceptance.

Those remain separate implementation/evidence claims.
