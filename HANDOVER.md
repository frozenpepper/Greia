# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume/read order

Before substantive work read, in order:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/architecture/GREIA_ARCHITECTURE.md`;
4. accepted ADRs relevant to the work, especially 0012–0017;
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
6. this `HANDOVER.md`;
7. **`docs/agents/GREIA_AGENT_OPERATIONS.md`** — mandatory repository/build/test-hardware operating manual;
8. **`skills/greia-activity-authoring/SKILL.md`** whenever creating, modifying, reviewing, optimizing, validating, packaging, deploying or testing an Activity;
9. narrower R7/testing/review documents referenced below.

GitHub is the canonical source of truth. Resolve the actual branch tip before work; this handover itself may not be HEAD after continuity commits.

The two agent-facing manuals are living contracts. If implementation changes repository/hardware procedure, update the operations manual. If implementation changes the Activity manifest/API/runtime policy/trust model/shared graphics or UI canon/performance requirements/validation/deployment, update the Activity skill in the same tranche.

---

## 2. Critical paid/hosted execution rule

**Do not enable, trigger, rerun, or add GitHub-hosted Actions without the repository owner's explicit authorization for that specific paid/hosted use.**

Do not infer authorization from “move forward”, “test”, “verify”, an existing workflow, or prior runs.

GitHub remains the source-persistence/review system. Verification and evidence run locally or in an explicitly owner-approved environment.

The remaining general workflow is manual-only and must not be invoked without explicit approval.

---

## 3. Historical/source closure boundary

R0–R6 are source-closed. Do not reopen the old v0.12 recovery incident or deep-refactor accepted trust/storage/session/runtime boundaries without a concrete defect.

The formerly lost post-v0.12 R5 history/progression authority was replaced by a **new reviewed R5 implementation**. Never describe it as recovered historical source.

R7 is the active blocking phase.

Production behavior remains intentionally unchanged:

```text
boot/session:                    Xorg + xinit compatibility path
production compositor:          none selected
serial direct DRM ownership:    evidence candidate only
ActivitySupervisor DRM master:  forbidden
ordinary Activity raw input:    forbidden target direction
```

The installed launcher uses `DisplaySessionCoordinator` with explicit `LegacyXDisplaySessionBackend`. This is a platform ownership/recovery seam, not a graphics-backend migration.

Current X-compatible sandbox concessions such as shared IPC and broad `/dev/dri` remain provisional until a measured replacement is selected; do not remove them blindly while production still uses Xorg.

---

## 4. Verification boundary — do not overclaim

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

Everything newer that has not explicitly run remains **committed but unexecuted**.

No current claim exists for:

- a newer full source-test count;
- strengthened serial KMSDRM suite;
- latest launcher/display integration suite;
- latest hardware-settings/installer adapter suite;
- `tests/test_developer_remote.py`;
- a built `modern-amd64-dev` image;
- SSH/mDNS login on real test hardware;
- real screenshot capture;
- real remote xdotool input;
- real remote Activity deployment/replace/restore;
- active QEMU KMSDRM PASS;
- serial QEMU handoff PASS;
- active seat/input PASS;
- physical Acer direct-graphics PASS;
- Pi direct-graphics PASS.

This documentation tranche itself ran no source/hardware tests and changes no verification count.

---

## 5. Agent-facing living documentation — NEW mandatory project contract

### Project/hardware operations manual

Canonical path:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Purpose: one operational entry point for agents handling Greia itself and the test hardware. It covers:

- mandatory source read order;
- Git/GitHub source-of-truth discipline;
- prohibition on unapproved hosted paid execution;
- current source/evidence boundary;
- operator Mac/computer versus Linux build/test environment;
- reference hardware and low-resource constraints;
- developer versus normal/release image separation;
- developer-image construction;
- wired Ethernet/mDNS assumptions;
- exact `tools/greia_remote.py` connection/control commands;
- screenshots, keyboard, pointer and text injection;
- logs/restart/reboot/poweroff/maintenance shell;
- remote Activity deployment and trust boundaries;
- first-time remote-installation limitation;
- source verification commands;
- physical evidence requirements;
- negative-evidence preservation;
- performance/resource evidence;
- stop conditions;
- handover/continuity duties.

It exists identically on `main` and `r7-direct-graphics` and is listed in `README.md`.

### Activity authoring skill

Canonical path:

```text
skills/greia-activity-authoring/SKILL.md
```

It is an agent-targeted skill with front matter and is the canonical practical guide for building Greia Activities.

It covers:

- actual current manifest contract and canonical source files to re-check;
- stable reverse-DNS Activity identity;
- capability versus permission semantics;
- curated Python runtime/import restrictions;
- lifecycle `mark_activity_ready()` / `activity_stop_requested()`;
- runtime-neutral Greia Storage APIs;
- normalized event/progression API and Greia-owned reward economics;
- profile-facing SDK surface;
- semantic shared asset catalogue and `get_icon_path()`;
- Greia theme integration through `get_theme()`;
- Activity-owned artwork rules;
- 1024×600-first child UX and language-neutral navigation guidance;
- low-end performance/optimization canon;
- Pygame hot-loop anti-patterns and caching/preloading rules;
- stable 30 FPS on C0 as **authoring guidance, not an accepted release threshold**;
- input/audio/error/recovery/state-portability rules;
- OOP/polymorphism guidance without class-for-class-sake;
- provider-free logic testing;
- Activity validation and full `make verify` workflow;
- remote deployment/test loop;
- definitions of done for new/modified Activities;
- exact maintenance triggers for keeping the skill synchronized with source.

Current shared visual reality is stated honestly: Greia has the semantic core icon catalogue and theme APIs, but **does not yet have an accepted general-purpose Activity widget/layout/animation library**. Agents must not invent one in documentation. If a shared graphics/UI/audio library is later accepted, it becomes part of the skill immediately and Activities should prefer it over duplicated private implementations.

`AGENTS.md` now makes both files mandatory and requires their maintenance in the same tranche as governed source changes. `README.md` surfaces both in the repository map. The same governance text is present on `main` and the active branch.

---

## 6. Local R7 evidence path

Current local R7 evidence orchestrator:

```text
tools/r7_local_evidence.py
```

Protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

The orchestrator reuses existing production builder/probes/package measurements/QEMU harnesses. It does not use GitHub Actions, does not auto-install host packages, does not mutate the source production image, and preserves first failure.

It still needs to execute in a controlled Linux checkout.

---

## 7. Developer remote-control/test-console requirement

Normal development/testing should require essentially no physical interaction with the netbook after power-on.

Detailed contract:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Operational agent instructions:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Intended installed developer flow:

```text
power on netbook
 -> wired DHCP + mDNS
 -> greia-dev.local becomes reachable
 -> operator controls/test loop from development computer
```

Required operator capabilities:

- status inspection;
- actual PNG screenshot capture back to operator;
- bounded keyboard/mouse/text injection;
- Activity upload/validation/deployment/removal;
- explicit built-in replacement and restore;
- launcher/service/network/SSH logs;
- launcher restart;
- reboot/poweroff;
- explicit maintenance SSH shell.

This is development/test functionality only, never a child/release feature.

---

## 8. Explicit developer profile and builder

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
```

Key properties:

```text
profile:             modern-amd64-dev
certification:       experimental
hostname:            greia-dev
expected mDNS:       greia-dev.local
current display:     xorg compatibility
runtime:             python
package set:         developer-remote
```

Normal `modern-amd64` does not include `developer-remote`.

Developer image wrapper:

```bash
sudo bash build/build-developer-image.sh out
```

It invokes canonical `build/build-image.sh modern-amd64-dev` and then `tools/provision_developer_image.py`; it is not a second OS builder.

Expected outputs:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

The private key is local operator credential material and must never be committed.

Developer SSH model:

- key-only `greiaadmin`;
- password remains locked;
- password/keyboard-interactive auth disabled;
- root SSH login disabled;
- passwordless sudo restricted to `/usr/local/sbin/greia-devctl`;
- client public key only is installed;
- SSH host keys are not cloned into image;
- actual target generates machine-specific host keys at first boot.

---

## 9. Developer networking/display/input

Developer remote preparation is guarded by `/etc/greia-os/developer-remote` and establishes developer-only wired DHCP/mDNS before SSH. First acceptance should use Ethernet.

There is no committed Wi-Fi credential path; never solve initial Wi-Fi by storing credentials in Git/docs.

Typed developer display endpoint:

```text
src/greia_platform/developer_session.py
/etc/greia-os/developer-display.json
```

Installed target currently declares:

```text
user = greiakid
display = :0
```

Current screenshot implementation:

```text
src/greia_platform/developer_capture.py
Pillow ImageGrab/X11
```

Current input implementation:

```text
src/greia_platform/developer_input.py
fixed /usr/bin/xdotool
```

These are Xorg development compatibility implementations only. The stable operator command surface should survive a later R7 backend change.

---

## 10. Operator remote client

Tool:

```text
tools/greia_remote.py
```

Typical workflow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py type "hello"
python3 tools/greia_remote.py logs --service launcher --lines 500
python3 tools/greia_remote.py deploy path/to/activity
python3 tools/greia_remote.py restart
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py shell
```

Defaults use `greia-dev.local`, `greiaadmin`, the dev-image private key under `out/`, and `~/.greia/known_hosts`.

---

## 11. Remote Activity trust boundary

Security-sensitive invariant:

```text
/opt/greia-os/activities
  trust = BUILT_IN

/var/lib/greia-developer/activities
  trust = DEVELOPER_UNSIGNED
```

The launcher only registers the developer source when the provisioned dev image supplies `GREIA_DEVELOPER_ACTIVITY_ROOT`. Built-in and developer roots may not be equal or nested.

Ordinary deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

revalidates the Activity, keeps `DEVELOPER_UNSIGNED` trust, refuses privileged permission requests, seals the package read-only and restarts the launcher.

Explicit built-in testing only:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
python3 tools/greia_remote.py restore <activity-id>
```

The original built-in remains recoverable in root-only backup state.

Activity authors must use `skills/greia-activity-authoring/SKILL.md` rather than reverse-engineering these boundaries from deployment code.

---

## 12. Live graphical installer remote control — still not fully integrated

Source exists:

```text
tools/provision_developer_installer.py
```

Designed live state:

```text
hostname/mDNS:      greia-installer-dev.local
SSH:                key-only greiaadmin
operator key:       same public key as target
host identity:      generated at live boot
current display:    root@:0
wired DHCP/mDNS:    yes
remote UI/logs:     screenshot/input/restart via greia-devctl
unattended install: NO
```

The provisioner is **not yet wired into `build/build-installer-image.sh`**. Do not claim first-time remote USB installation works yet.

When integrated, remote installation must drive the existing graphical fail-closed installer and preserve eligible-target, payload-digest, target-identity and confirmation checks. Never add a remote unattended disk-wipe shortcut.

---

## 13. R7 graphics evidence primitives

Passive installed probe:

```text
src/greia_platform/direct_graphics_probe.py
```

Active SDL/Pygame KMSDRM acceptance:

```text
src/greia_platform/kmsdrm_acceptance.py
```

Serial Shell→child→Shell handoff evidence candidate:

```text
src/greia_platform/kmsdrm_serial_handoff.py
```

Disposable QEMU harnesses:

```text
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

Compositor/reference package probe:

```text
tools/r7_compositor_package_probe.py
```

Fixed references remain Cage, Weston and wlroots-runtime for measurement only. No production compositor is selected.

---

## 14. Exact next legitimate sequence

### Documentation governance is now in place

Future agents must use and maintain:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
```

### Next execution work

On an owner-controlled Linux checkout:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify

sudo bash build/build-developer-image.sh out
```

Then boot/install the developer image through an existing safe path and execute the developer-remote acceptance checklist from the operator computer:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

First physical acceptance should prove:

1. normal image still has SSH disabled/no dev marker;
2. developer target generates unique SSH host keys;
3. password/root SSH fail;
4. operator key succeeds as `greiaadmin`;
5. wired DHCP/mDNS works without local interaction;
6. `wait`/`status` work;
7. screenshot matches the visible screen;
8. keyboard/mouse/text controls drive the GUI;
9. normal remote Activity remains `DEVELOPER_UNSIGNED`;
10. built-in collision fails without explicit replacement;
11. replace/restore is reversible;
12. launcher restart recovers graphically;
13. reboot disconnects then remote control returns.

Preserve first failures instead of weakening tests.

Only after installed developer control is proven should the live-installer provisioner be hooked into the canonical installer builder and remote graphical installation tested.

Separately execute the current local R7 exact-image/package/QEMU evidence path. Active seat/input evidence remains a separate required step. Only after real evidence should a compositor/session-broker candidate be prototyped and compared against serial ownership and Xorg.

---

## 15. Continuity checklist for the next agent

Before ending any substantive tranche:

- commit coherent source/docs to GitHub;
- append, never rewrite, active-plan progress;
- refresh this `HANDOVER.md`;
- state exactly which tests actually executed;
- preserve VM/physical evidence gaps;
- update `docs/agents/GREIA_AGENT_OPERATIONS.md` if project/test-hardware procedure changed;
- update `skills/greia-activity-authoring/SKILL.md` if Activity-facing contracts/canon changed;
- do not use GitHub-hosted Actions without explicit owner authorization;
- do not merge PR #4 merely for convenience;
- leave production on Xorg/xinit until R7 evidence justifies migration.
