# Acer Remote Agent Control — Source Review

**Date:** 2026-08-15  
**Scope:** installed Greia developer target controlled by an agent on the operator computer  
**Result:** SOURCE-DESIGNED / PHYSICAL ACCEPTANCE NOT RUN

## Question

Can Greia be installed on the Acer Aspire One and then be controlled, tested and monitored remotely by an agent running on another computer, including obtaining screenshots on the operator computer?

## Answer

**At the source/architecture level: yes for the installed developer target.**

The existing developer-control path already provides the right appliance-style remote loop, and this review closed an Acer-profile gap and added an agent-friendly evidence snapshot command.

**At the physical-evidence level: not yet proven.** The current branch has not been built/installed and exercised on the physical Acer after these changes, so no runtime PASS is claimed.

## What the operator agent can do

Using `tools/greia_remote.py` over key-only SSH, the operator can:

- wait until Greia is remotely ready;
- read machine/service/hardware/profile status as JSON;
- capture the actual Greia display as PNG bytes and save them directly on the operator computer;
- collect a local snapshot directory containing screenshot + status + bounded logs;
- inject bounded keyboard input;
- move/click the pointer;
- type bounded single-line text;
- collect bounded journal groups;
- restart the Greia launcher;
- reboot or power off the target and reconnect after boot;
- deploy/remove ordinary developer Activities while preserving `DEVELOPER_UNSIGNED` trust;
- explicitly replace/restore an installed built-in Activity for deliberate integration testing;
- open an unprivileged maintenance SSH shell when bounded controls are insufficient.

This is sufficient for an agent to execute visual interaction tests, inspect screenshots locally, correlate them with status/logs, and repeat test steps without routine physical interaction with the Acer.

## Screenshot transfer

The screenshot path is not “take screenshot on Acer, then manually copy it.” It is one remote operation:

```text
operator agent
  → SSH public-key transport
  → sudo -n /usr/local/sbin/greia-devctl screenshot
  → fixed capture helper runs as greiakid on the declared display
  → Pillow/ImageGrab captures current Xorg display
  → PNG bytes are written to SSH stdout
  → tools/greia_remote.py validates PNG signature
  → local operator file is written
```

The current implementation is Xorg compatibility code. R7 may replace the capture backend, but the operator-level `screenshot` contract should remain stable.

## Agent observation primitive

This review added:

```bash
python3 tools/greia_remote.py snapshot <local-directory> --service all --lines 500
```

The resulting local directory contains:

```text
screen.png
status.json
logs.txt
snapshot.json
```

This is the preferred observation unit for a local autonomous agent: visual state, structured target state and bounded logs are all local and can be inspected together.

## Acer architecture gap found and closed

Before this review, the explicit remote developer image profile was only `modern-amd64-dev`, which was not sufficient for a first-generation Acer whose exact CPU/PAE profile remains a physical evidence question.

The branch already carried three Acer candidates:

```text
acer-aspire-one-i386
acer-aspire-one-i386-nonpae
acer-aspire-one-amd64
```

Matching development-only variants now exist:

```text
acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64-dev
```

Each developer variant preserves the corresponding Acer architecture, kernel, display package set, C0 compatibility class, image size/layout and runtime, while adding only the explicit developer remote package set and `greia-dev` hostname/policy.

`build/build-developer-image.sh` now accepts the exact developer profile as an optional second argument while preserving the previous default behavior.

`tools/provision_developer_image.py` now validates the exact requested developer profile and still independently requires the embedded `developer-remote` package set. It cannot be used to silently turn an arbitrary normal image into a remotely managed developer image.

## Security/recovery properties

The reviewed design intentionally does not use unrestricted root SSH automation.

- password authentication is disabled;
- keyboard-interactive authentication is disabled;
- root SSH login is disabled;
- `greiaadmin` authenticates with the provisioned public key;
- the private key remains on the operator side;
- each installed target generates its own SSH host keys;
- passwordless privileged automation is restricted to `/usr/local/sbin/greia-devctl`;
- GUI input invokes only fixed `/usr/bin/xdotool` with bounded arguments;
- screenshot runs through the root-owned display descriptor as the actual Greia display user;
- ordinary developer Activity deployment does not upgrade package trust.

Normal/release profiles remain remote-disabled.

## Important remaining development-workflow boundary

The remote console controls/tests/monitors the **installed system** and supports remote Activity iteration.

It does **not yet provide arbitrary hot replacement of `/opt/greia-os/src`** for Greia core/platform Python changes.

That restriction is intentional and useful at this stage. `greia-devctl` itself currently imports its trusted implementation from the immutable installed source tree. Allowing an arbitrary platform upload to replace the same code that provides recovery could make one bad upload destroy remote recovery.

Therefore core/platform changes currently require a rebuilt developer image/reinstall before they can be executed on the Acer.

A future developer-only platform overlay can remove this friction safely if it obeys one critical design rule: **the immutable remote recovery/control implementation must remain outside the replaceable platform overlay**, with an atomic rollback command available even when the uploaded launcher/platform source crashes immediately.

Do not solve the limitation by granting unrestricted root sudo/SSH to the agent.

## First-time remote installation boundary

`tools/provision_developer_installer.py` exists for remotely driving the existing graphical installer, but it is not yet integrated and physically accepted through the canonical installer-image builder.

Therefore this review does not claim that the very first USB installation can be performed entirely remotely. The accepted remote-agent workflow begins once the development image is installed through an existing safe path and boots on the Acer.

## Physical acceptance required

Run:

```text
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

The physical gate proves:

- target appears on the LAN;
- key-only authentication works;
- screenshot corresponds to the real physical Acer display;
- screenshots transfer to the operator computer;
- keyboard/pointer injection changes the expected child UI;
- status/log monitoring works;
- launcher restart works;
- reboot/reconnect works;
- Activity deployment remains correctly trusted;
- developer security boundaries remain intact.

## Evidence status

No new source test or physical Acer test was executed in this review environment.

The last genuinely executed full project source gate remains the earlier recorded 232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`.

New remote-control/profile/snapshot source is committed but **UNEXECUTED**.

## Judgment

- **Remote control of installed developer Acer:** source architecture READY FOR PHYSICAL ACCEPTANCE.
- **Screenshot capture + transfer to operator computer:** source implementation PRESENT; physical proof pending.
- **Agent-friendly status/log/screenshot monitoring:** PRESENT, including the new `snapshot` bundle.
- **Remote Activity iteration:** PRESENT in source; physical proof pending.
- **Remote core/platform hot deployment:** NOT YET IMPLEMENTED; rebuild/reinstall required for core changes.
- **First-time fully remote installer:** NOT YET ACCEPTED.
- **Release/normal image remote access:** deliberately ABSENT.
