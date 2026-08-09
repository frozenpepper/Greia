# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume rules

Read, in order:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/architecture/GREIA_ARCHITECTURE.md`;
4. accepted ADRs, especially 0012–0017;
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
6. this `HANDOVER.md`;
7. R7 dependency/candidate/testing documents referenced below.

GitHub is the canonical source of truth. Resolve the actual `r7-direct-graphics` tip before new work.

### CRITICAL paid-execution rule

**Do not enable, trigger, rerun, or add GitHub-hosted Actions without the repository owner's explicit authorization for that specific paid/hosted use.**

Do not infer permission from a request to “move forward,” from the existence of workflow files, or from previous runs.

GitHub is for source persistence/review. Verification runs locally or on an explicitly owner-approved environment.

---

## 2. Current architectural state

R0–R6 are source-closed. Do not reopen the old v0.12 recovery incident or deep-refactor the completed trust/storage/session/runtime spine without a concrete defect.

The formerly lost post-v0.12 R5 history/progression authority was replaced by a **new reviewed R5 implementation**. Never describe it as historical recovery.

R7 remains open.

Production behavior is intentionally unchanged:

```text
boot/session: Xorg + xinit compatibility path
production compositor: none selected
serial direct DRM ownership: evidence candidate only
ActivitySupervisor DRM master: forbidden
ordinary Activity raw input ownership: forbidden target direction
```

The live installed launcher now uses `DisplaySessionCoordinator` with an explicit `LegacyXDisplaySessionBackend`. This is a platform ownership/recovery seam, **not** a backend migration.

Current X-compatible sandbox concessions such as shared IPC and broad `/dev/dri` must not be removed blindly while production still uses Xorg.

---

## 3. Verification boundary — do not overclaim

Last complete provider-free source gate actually executed successfully:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Focused R7 checks genuinely executed earlier:

```text
DisplaySessionCoordinator isolated fixture: 22 / 22 PASS
compositor-package pure-logic fixture: 14 / 14 PASS
serial KMSDRM fake-SDL/process suite: 8 / 8 PASS before later serial strengthening
```

Everything added after that boundary that has not explicitly been run remains **committed but unexecuted**.

In particular, no current claim exists for:

- latest full source-test count;
- strengthened serial KMSDRM suite;
- current launcher/display integration suite;
- current hardware-settings/installer adapter suite;
- developer-remote tests;
- developer image build;
- SSH/mDNS remote login;
- screenshot capture;
- xdotool GUI control;
- remote Activity deployment;
- active QEMU KMSDRM PASS;
- serial QEMU handoff PASS;
- active seat/input PASS;
- physical Acer direct-graphics PASS;
- Pi direct-graphics PASS.

No GitHub Actions run is authorized to obtain these results.

---

## 4. Paid-CI correction and local R7 evidence path

Automatic hosted R7 workflows were removed and the remaining general verifier is manual-only.

Project policy in `AGENTS.md` now makes paid hosted execution explicitly opt-in.

Current local R7 evidence orchestrator:

```text
tools/r7_local_evidence.py
```

Operator protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

The local orchestrator reuses the existing production builder, passive probe, package-delta probe and active/serial QEMU harness. It does not auto-install host packages, does not use GitHub Actions, does not mutate the source production image, and preserves first failure.

Production remains Xorg until real evidence selects something else.

---

## 5. New developer remote-control/test-console requirement

The operator wants Greia testing to require essentially no physical interaction with the netbook after power-on.

The intended installed developer experience is:

```text
power on netbook
 -> wired DHCP/mDNS
 -> greia-dev.local becomes reachable
 -> operator controls/testing from Mac/computer
```

From the operator computer the development system should support:

- status inspection;
- screenshot capture back to the operator machine;
- keyboard/mouse/text injection;
- Activity upload/validation/deployment/removal;
- explicit built-in replacement and restore;
- launcher/service logs;
- launcher restart;
- reboot/poweroff;
- explicit maintenance SSH shell.

This capability is **developer/test only**, never a child/release feature.

Detailed operator/security contract:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

---

## 6. Explicit developer profile

New declarative profile:

```text
build/profiles/modern-amd64-dev.toml
```

Key properties:

```text
profile id: modern-amd64-dev
certification state: experimental
installed hostname: greia-dev
expected mDNS: greia-dev.local
current display adapter: xorg compatibility
runtime: python
```

Dedicated package set:

```text
build/package-sets/developer-remote.txt
```

Current developer-only additions include:

```text
openssh-server
python3-pil
sudo
xdotool
```

The normal `modern-amd64` profile does **not** include `developer-remote`.

The source/overlay may contain dormant developer helpers, but normal/release images have no developer marker, no developer sudoers grant, no provisioned client public key and SSH remains disabled by the normal builder.

---

## 7. Developer target image build/provisioning

Wrapper:

```text
build/build-developer-image.sh
```

Invoke as:

```bash
sudo bash build/build-developer-image.sh out
```

It calls the canonical builder:

```text
build/build-image.sh modern-amd64-dev
```

then provisions the resulting raw image with:

```text
tools/provision_developer_image.py
```

This is not a second OS builder.

Expected output artifacts:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

The private key is operator credential material. Never commit it.

Provisioning behavior:

- exact developer profile/package-set validation;
- per-image Ed25519 operator client key generated using image OpenSSH tooling;
- private key exported only to build output;
- public key installed for `greiaadmin`;
- `greiaadmin` remains password-locked;
- password SSH auth disabled;
- root SSH login disabled;
- passwordless sudo limited to `/usr/local/sbin/greia-devctl`;
- SSH host keys are **not cloned into the image**;
- temporary host keys may be generated for `sshd -t` and are deleted before image close;
- actual netbook generates unique machine host keys on first boot;
- target developer display endpoint is `greiakid@:0`;
- launcher receives only the explicit developer Activity root environment;
- normal production profile is not changed.

---

## 8. Developer wired network preparation

Installed developer remote preparation is handled by:

```text
build/overlay/etc/systemd/system/greia-developer-remote.service
build/overlay/usr/local/lib/greia-os/prepare-developer-remote
```

It is guarded by:

```text
/etc/greia-os/developer-remote
```

Before SSH starts it establishes developer-only wired networking:

```text
Ethernet DHCP: yes
IPv6 RA: yes
mDNS: yes
systemd-networkd/resolved: restarted after policy write
Avahi: restarted when available
```

Recommended first acceptance uses wired Ethernet.

`iwd` exists for Wi-Fi work, but there is currently **no secure initial Wi-Fi credential injection path**. Do not commit Wi-Fi credentials to Git or documentation.

---

## 9. Developer display/session seam

New source:

```text
src/greia_platform/developer_session.py
```

`DeveloperDisplayEndpoint` loads a root-owned descriptor:

```text
/etc/greia-os/developer-display.json
```

Installed developer target declares:

```text
user = greiakid
display = :0
```

The planned live developer installer declares:

```text
user = root
display = :0
```

Screenshot and input controls consume the same typed descriptor instead of hard-coding one display owner.

This is deliberately a development compatibility seam. Current Xorg implementation can later be replaced beneath the same operator surface when R7 selects a direct/compositor design.

---

## 10. Screenshots

Implementation:

```text
src/greia_platform/developer_capture.py
```

Operator command:

```bash
python3 tools/greia_remote.py screenshot out/screen.png
```

Current path:

```text
SSH greiaadmin
 -> sudo -n greia-devctl
 -> root reads developer display endpoint
 -> run capture helper as display-session user
 -> Pillow ImageGrab on DISPLAY=:0
 -> PNG bytes over SSH
 -> local file
```

The SSH account is not given generic X authority.

Current implementation is Xorg-development compatibility only. Runtime/hardware acceptance is still required to prove real screenshot capture.

---

## 11. GUI input from operator computer

Implementation:

```text
src/greia_platform/developer_input.py
```

Only the fixed `/usr/bin/xdotool` executable is invoked, under the declared display-session user.

Operator examples:

```bash
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py key Escape
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py type "hello"
```

Bounds exist for key expressions/count, mouse coordinates/buttons and typed text. This is not arbitrary command execution.

Again: Xorg developer compatibility only, not the R7 production input decision.

---

## 12. Greia-owned developer control surface

Entry point:

```text
/usr/local/sbin/greia-devctl
```

Python implementation:

```text
src/greia_platform/developer_control.py
```

It requires:

- root execution through the bounded sudo policy;
- developer marker;
- valid developer display endpoint.

Current bounded operations include:

```text
status
screenshot
logs
restart-launcher
restart-installer
key
mousemove
click
type
deploy-activity
remove-activity
restore-activity
reboot
poweroff
```

Interactive maintenance shell remains an ordinary `greiaadmin` SSH shell; privilege is not implicitly granted there.

---

## 13. Remote Activity trust boundary

This is security-sensitive and must not regress.

Built-in source remains:

```text
/opt/greia-os/activities
trust = BUILT_IN
```

Ordinary remotely deployed source is:

```text
/var/lib/greia-developer/activities
trust = DEVELOPER_UNSIGNED
```

`src/greia_launcher/main.py` registers the developer root only when:

```text
GREIA_DEVELOPER_ACTIVITY_ROOT
```

is explicitly supplied by the provisioned developer image.

The built-in and developer roots may not be equal or nested.

Ordinary remote deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

revalidates the package, preserves `DEVELOPER_UNSIGNED` trust and refuses privileged permission requests.

It must never become built-in merely because an operator uploaded it remotely.

Developer deployment packages are sealed read-only after acceptance.

---

## 14. Explicit built-in replacement/restore

For deliberate testing of an already installed built-in:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
```

This path is explicitly different from normal developer deployment.

It requires an existing system Activity, backs the original package up under root-only developer backup state, installs the replacement read-only and records the original location.

Restore:

```bash
python3 tools/greia_remote.py restore <activity-id>
```

Ordinary developer deployment must never use `--replace-system`.

---

## 15. Operator-side client

Tool:

```text
tools/greia_remote.py
```

Defaults:

```text
host: greia-dev.local
user: greiaadmin
key: out/greia-os-modern-amd64-dev-ssh-key
known hosts: ~/.greia/known_hosts
```

Typical installed-target workflow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
python3 tools/greia_remote.py logs --service launcher --lines 500
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py deploy path/to/activity
python3 tools/greia_remote.py restart
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py shell
```

SSH uses key-only batch mode and a dedicated Greia known-hosts file.

---

## 16. Live graphical installer remote control — source exists, canonical hook still open

New source:

```text
tools/provision_developer_installer.py
```

It is intended to provision the **existing graphical live installer**, not replace it.

Designed live developer state:

```text
hostname: greia-installer-dev
expected mDNS: greia-installer-dev.local
SSH user: greiaadmin
same operator public key as target
host key: generated at live boot, not cloned
display endpoint: root@:0
wired DHCP/mDNS: yes
remote screenshot/input/log/restart: yes
unattended destructive install: NO
```

The operator would remotely drive the existing graphical installer and retain all eligible-target, payload digest, target identity and confirmation checks.

### Important current limitation

`tools/provision_developer_installer.py` is source-implemented, but it is **not yet wired into `build/build-installer-image.sh`**.

Do not claim remote first-time USB installation works yet.

Reason for stopping at this boundary: the canonical installer builder creates both the target payload and live root. Hooking provisioning at both points should be a small change, but it affects destructive installation media and should be made/tested on a real Linux builder rather than hidden in an unexecuted wrapper or broad whole-file rewrite.

Once integrated and accepted, intended flow is:

```text
boot developer USB
 -> greia-installer-dev.local
 -> remote screenshot/input drive existing graphical installer
 -> safe install completes
 -> reboot
 -> greia-dev.local
 -> continue remote testing with same client key
```

---

## 17. Developer remote regression suite

Current regression file:

```text
tests/test_developer_remote.py
```

Coverage includes:

- normal profile does not opt into developer remote;
- developer target/live package composition;
- developer display endpoint validation;
- screenshot runs as declared display user;
- developer marker enforcement;
- developer Activity root readable while staging/backups remain root-only;
- Activity ID/path rejection;
- launcher `BUILT_IN` vs `DEVELOPER_UNSIGNED` source separation;
- source-root overlap rejection;
- constrained fixed xdotool invocation;
- target provisioner exact-profile and no-cloned-host-key rules;
- operator SSH key/known-host behavior;
- screenshot PNG transfer;
- client GUI/service operations staying inside `greia-devctl`;
- live-installer remote-but-not-unattended policy;
- developer builder wrapping the canonical image builder.

**These tests have not executed.**

---

## 18. Existing R7 display evidence primitives remain unchanged

Passive probe:

```text
src/greia_platform/direct_graphics_probe.py
```

Active KMSDRM:

```text
src/greia_platform/kmsdrm_acceptance.py
```

Serial handoff:

```text
src/greia_platform/kmsdrm_serial_handoff.py
```

Disposable active/serial QEMU:

```text
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

Compositor package deltas:

```text
tools/r7_compositor_package_probe.py
```

Fixed candidates remain Cage, Weston and `wlroots-runtime`/`libwlroots-0.18`.

No real current package/QEMU evidence exists yet.

---

## 19. Exact next engineering sequence

Do not add another graphics mechanism merely for progress.

On an owner-controlled Linux checkout:

1. resolve current `r7-direct-graphics` head;
2. run the focused developer remote suite:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_developer_remote.py' -v
   ```

3. run current complete source gate:

   ```bash
   make verify
   ```

4. preserve the actual count/failure; do not weaken tests;
5. build the developer target:

   ```bash
   sudo bash build/build-developer-image.sh out
   ```

6. install/boot it through an existing safe path;
7. with wired Ethernet attached, execute the acceptance checklist in `docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md`;
8. preserve first failures for SSH/mDNS/screenshot/input/deployment/reboot;
9. once the installed target remote console is proven, add the two small canonical hooks for `tools/provision_developer_installer.py` to `build/build-installer-image.sh` and perform a real live-installer build/boot;
10. prove remote graphical installation without changing installer safety predicates;
11. separately continue the existing R7 local exact-image/package/QEMU evidence path;
12. only after real graphics/resource evidence exists select a compositor/session-broker candidate, if any;
13. physical legacy Intel/Acer acceptance remains mandatory before production graphics migration.

---

## 20. Key references

```text
AGENTS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_platform/developer_session.py
src/greia_platform/developer_control.py
src/greia_platform/developer_capture.py
src/greia_platform/developer_input.py
tools/greia_remote.py
tools/provision_developer_image.py
tools/provision_developer_installer.py
build/profiles/modern-amd64-dev.toml
build/build-developer-image.sh
tests/test_developer_remote.py
```

---

## 21. Bottom line

The installed Greia developer target now has a coherent **source-level remote test console design**: key-only SSH transport, bounded privileged `greia-devctl`, screenshots, GUI input, logs/service/power operations, and trust-preserving remote Activity deployment.

It is **UNPROVEN until local Linux build/runtime acceptance**.

The live graphical installer remote-control provisioner also exists at source level but is intentionally **not yet integrated into the canonical installer builder**.

Production remains Xorg/xinit, no compositor is selected, and no GitHub-hosted execution is authorized.
