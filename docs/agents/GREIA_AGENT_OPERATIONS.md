# Greia Agent Operations Manual

**Audience:** coding, review and test agents working on Greia OS  
**Status:** mandatory derived operating manual  
**Last reviewed:** 2026-08-10  
**Canonical repository:** `frozenpepper/Greia`

---

## 1. Purpose and authority

This is the practical operating manual for working on Greia and its test hardware. It answers questions such as:

- what must an agent read before editing;
- which repository/branch/state is authoritative;
- how source verification differs from hardware evidence;
- how to build an explicit developer image;
- how to connect to a Greia test machine from the operator computer;
- how to capture screenshots, inject bounded input, inspect logs and deploy Activities;
- how to preserve failure evidence;
- when to stop rather than “fixing the test”;
- how to leave the project resumable.

Read `docs/DOCUMENTATION.md` for the documentation authority model.

This manual is derived from `AGENTS.md`, accepted ADRs, source tools and test protocols. It **does not override** them. If it disagrees with the owner of an implemented contract, correct this manual.

Activity-authoring rules live in:

```text
skills/greia-activity-authoring/SKILL.md
```

---

## 2. Start-of-task checklist

Before substantive Greia work:

1. read `AGENTS.md`;
2. read `README.md` and `docs/DOCUMENTATION.md`;
3. read the architecture overview and relevant accepted ADRs;
4. read the mandatory active remediation plan;
5. read the current `HANDOVER.md`;
6. resolve the actual active branch and HEAD from the repository, not chat memory;
7. read the phase-specific testing/review documents named by the handover;
8. for Activity work, read the Activity authoring skill and current API/runtime source owners;
9. identify whether the task is **source work**, **VM evidence**, **physical-hardware evidence**, or a mixture;
10. identify any destructive operation before running it.

If the repository and a previous chat summary disagree, the repository wins.

---

## 3. Repository/Git discipline

GitHub is the persistent source of truth for project source and reviewed documentation.

### Required behavior

- work on the branch named by the current handover unless the task explicitly changes branch strategy;
- resolve the current HEAD before editing;
- commit coherent work frequently enough that loss of the execution environment does not erase a substantial tranche;
- keep `HANDOVER.md` current when continuation state changes;
- keep generated images, private keys, downloaded packages, caches and bulky runtime evidence outside Git;
- preserve historical plan/evidence entries rather than rewriting them to make history cleaner;
- do not merge a draft PR merely to eliminate a conflict;
- do not silently drop a repository-wide rule from either side of a merge.

### Branch/commit evidence

Every hardware/VM evidence attempt must record the exact source SHA used. “Latest” or a branch name alone is not enough.

---

## 4. Hosted execution prohibition

Without explicit owner authorization for that specific use, **do not interact with GitHub Actions as an execution/evidence service**.

That means no:

- trigger;
- rerun;
- manual dispatch;
- automatic trigger addition;
- run/status/job/step/log query;
- artifact query/download.

Reading or editing `.github/workflows/*` as ordinary source is allowed when the task requires source review. Do not execute or interrogate the hosted service.

Use local or otherwise explicitly owner-approved environments for verification/evidence.

A request to “move forward”, “test”, “verify” or “check CI” is not authorization to spend hosted resources or use the Actions execution surface.

---

## 5. Evidence vocabulary

Before testing, classify what the result can prove.

### Source evidence

Examples:

```text
make verify
unit/contract tests
static project validation
Activity validation
shell syntax checks
source footprint checks
```

Source evidence does not prove Linux image behavior, graphics/input, VM boot, physical devices or performance.

### VM/image evidence

Examples:

```text
raw image build
image footprint/package manifest
QEMU boot
KMSDRM acquisition/handoff
installer VM behavior
```

VM evidence does not prove the Acer, Pi 400 or Pi 500 physical path unless the relevant acceptance definition explicitly says so.

### Physical evidence

Physical evidence must identify the actual machine and relevant hardware/runtime facts. It is required for claims tied to reference hardware.

Use `PASS`, `FAIL`, `NOT-RUN`, `UNPROVEN`, `SOURCE-CLOSED`, `PROVISIONAL` and related labels with explicit scope.

The exact most recent executed evidence belongs in `HANDOVER.md` or a dated evidence report—not in durable overview documents.

---

## 6. Current graphics/session boundary

The target architecture is direct/appliance-oriented, but the current installed production path remains an explicit **Xorg/xinit compatibility backend** while R7 is open.

Therefore:

- do not deepen Activity dependence on X11;
- do not remove current X-compatible sandbox concessions blindly while production still uses them;
- do not make ActivitySupervisor the DRM master;
- do not grant ordinary Activities raw input ownership;
- do not select a compositor because it is conventional desktop Linux practice;
- treat serial direct ownership/compositor candidates according to current R7 evidence, not preference.

Exact current R7 implementation/evidence state is in `HANDOVER.md`.

---

## 7. Operator computer prerequisites

The current remote developer client is:

```text
tools/greia_remote.py
```

The operator computer needs:

- Python 3;
- OpenSSH `ssh`;
- OpenSSH `scp`;
- `ssh-keygen` for deliberate dedicated-known-host cleanup after an intentional reimage;
- a checkout of the Greia repository containing the client tool;
- the private operator key emitted by the developer-image build.

The default operator environment may be macOS, but the client uses normal Python/OpenSSH behavior and is not macOS-specific.

Do not copy the private key into the repository.

---

## 8. Linux build/evidence environment

Raw image building and the current R7 image/QEMU evidence path require an owner-controlled compatible Linux environment with root access and the prerequisites named by the exact test protocol.

For R7 local evidence read:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

Rules include:

- use a disposable/root-safe checkout;
- keep run roots outside the repository;
- never mutate the production source image in place;
- preserve first failure;
- do not auto-install host packages from the orchestrator;
- do not weaken classification/timeouts to obtain PASS.

---

## 9. Reference hardware

The first-generation Acer Aspire One is the extreme low-resource reference. Until exact inventory supersedes estimates, design assumptions are approximately:

```text
RAM:        768 MiB
storage:    ~7 GB
resolution: 1024×600
```

Raspberry Pi 400 and Pi 500 are co-equal ARM references, with board/image/physical work assigned to later architecture phases.

Do not redefine the reference floor because development on a modern PC is easier.

Before destructive installation on a physical machine, confirm the current plan/test protocol explicitly allows it.

---

## 10. Normal image versus developer image

Remote control is deliberately opt-in.

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
```

Normal/reference profile:

```text
build/profiles/modern-amd64.toml
```

Only the explicit developer profile may opt into the `developer-remote` package/provisioning path.

Normal/release Greia must not become remotely accessible simply because developer helper source exists.

The developer path must keep:

- password authentication disabled;
- keyboard-interactive authentication disabled;
- root SSH login disabled;
- private operator key outside the image/repository;
- machine SSH host identity generated on the actual booted machine;
- passwordless privilege bounded to Greia-owned `greia-devctl` operations.

---

## 11. Build the installed developer target

On the compatible Linux build host:

```bash
sudo bash build/build-developer-image.sh out
```

This wraps the canonical image builder; it is not a second OS build architecture.

Expected artifacts currently include:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

Treat the private key as secret local operator material:

- mode should remain restrictive;
- never commit it;
- never paste it into an issue/PR/chat handover;
- do not include it in a shareable evidence bundle;
- if the image/key is discarded, discard the private key deliberately.

Implementation/security details:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

---

## 12. First network acceptance

Use **wired Ethernet** for the first developer-remote acceptance whenever possible.

The installed developer target is intended to use DHCP/mDNS and appear as:

```text
greia-dev.local
```

The planned developer live installer uses a separate identity:

```text
greia-installer-dev.local
```

Do not commit Wi-Fi credentials to solve initial connectivity. The current developer path does not define a repository-stored Wi-Fi secret mechanism.

If mDNS is unavailable, obtain the DHCP address out of band and pass it via `--host`. Do not hard-code the address into Greia source.

---

## 13. First connection

From the operator checkout:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
```

Defaults are owned by `tools/greia_remote.py`; at this review they are:

```text
host:        greia-dev.local
user:        greiaadmin
key:         out/greia-os-modern-amd64-dev-ssh-key
known-hosts: ~/.greia/known_hosts
```

Override a non-default host/key explicitly:

```bash
python3 tools/greia_remote.py \
  --host <hostname-or-ip> \
  --key <private-key-path> \
  status
```

The client uses a **dedicated Greia known-hosts file**. Do not disable SSH host-key checking globally.

### Intentional reimage / changed host key

A new image or live environment is expected to generate a new SSH host identity. A host-key mismatch is therefore meaningful and must not be bypassed automatically.

If—and only if—you know the machine was intentionally reimaged/replaced:

1. preserve the previous `~/.greia/known_hosts` as evidence if relevant;
2. confirm the expected target identity/reimage;
3. remove only the affected host entry from the dedicated Greia file, for example:

```bash
ssh-keygen -f ~/.greia/known_hosts -R greia-dev.local
```

4. reconnect and allow the client to accept the new key;
5. record the identity rollover in the evidence if the test concerns host-key behavior.

Do not use `StrictHostKeyChecking=no` as a shortcut.

---

## 14. Stable remote control surface

Agents should use the repository client rather than scripting internal systemd/X11/filesystem details directly.

### Status

```bash
python3 tools/greia_remote.py status
```

### Screenshot

```bash
python3 tools/greia_remote.py screenshot out/screen.png
```

A successful command exit is not enough for a visual test; inspect/retain the PNG when the visible state matters.

### Keyboard

```bash
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py key Escape
python3 tools/greia_remote.py key Left
python3 tools/greia_remote.py key Right
```

### Pointer

```bash
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py click 3
```

### Text

```bash
python3 tools/greia_remote.py type "test text"
```

### Logs

```bash
python3 tools/greia_remote.py logs --service launcher --lines 500
```

Current bounded groups are defined by source and include:

```text
all
launcher
installer
parent
ssh
developer-remote
network
```

### Service/power controls

```bash
python3 tools/greia_remote.py restart
python3 tools/greia_remote.py restart-installer
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py poweroff
```

After reboot, run `wait` again and prove reconnection.

The current screenshot/input backend uses Xorg compatibility implementation details underneath `greia-devctl`. Agents should use the stable operator commands so R7 can replace those internals later.

---

## 15. Maintenance SSH shell

An explicit developer/recovery shell is available:

```bash
python3 tools/greia_remote.py shell
```

Use it for investigation when the bounded controls are insufficient.

For repeatable automated tests, prefer `greia-devctl`-backed client commands. Do not encode arbitrary privileged shell commands as the normal test API.

The shell does not change Activity trust or create a product-facing shell feature.

---

## 16. Remote Activity deployment and trust

Ordinary developer deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

The developer Activity source is:

```text
/var/lib/greia-developer/activities
trust = DEVELOPER_UNSIGNED
```

The built-in source remains:

```text
/opt/greia-os/activities
trust = BUILT_IN
```

Remote file placement must never upgrade package trust.

Ordinary developer deployment is revalidated and must not obtain privileged permissions merely because the operator uploaded it.

Remove a developer deployment:

```bash
python3 tools/greia_remote.py remove <activity-id>
```

### Explicit built-in replacement

Only when intentionally testing an already installed built-in:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
```

Restore the preserved original:

```bash
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` to bypass a normal developer-package validation/trust failure.

For Activity authoring/validation rules use the Activity skill.

---

## 17. First-time remote installation boundary

The intended eventual developer flow is:

```text
boot developer USB
→ greia-installer-dev.local becomes reachable
→ remotely capture/drive the existing graphical installer
→ installer performs normal eligible-target/payload/device safety checks
→ reboot
→ installed target appears as greia-dev.local
```

Remote installation must preserve the **existing graphical fail-closed installer**. Never replace it with a remote `dd`, generic disk-write endpoint, unattended wipe or arbitrary root command for convenience.

Source contains `tools/provision_developer_installer.py`, but whether it is integrated into the canonical installer artifact is a **current-state fact owned by `HANDOVER.md`**. Check the handover before claiming remote first-install capability.

---

## 18. Standard source verification

Canonical source gate:

```bash
make verify
```

Focused unit iteration:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Focused developer-remote regression suite:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v
```

Do not copy an old test count into a new claim. State the commit and command actually executed.

---

## 19. R7 local image/QEMU evidence

Use the exact active protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

Typical operator shape (verify against the current protocol/tool before execution):

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

The first failed attempt is evidence. Do not reuse its run root or silently rerun the same active/serial proof until it passes.

---

## 20. Physical test evidence record

For every meaningful physical attempt preserve at minimum:

- repository branch and exact SHA;
- image/profile identity and hash where applicable;
- machine identity/inventory relevant to the test;
- connection path (wired/mDNS/IP as relevant);
- exact command/input sequence;
- timestamps or ordered step numbers;
- stdout/stderr and bounded logs;
- screenshots before/after visible transitions;
- PASS/FAIL/NOT-RUN classification for each expected result;
- first failure exactly as seen;
- reboots/power cycles;
- manual intervention required;
- any intentional host-key rollover/reimage event.

Keep heavyweight raw evidence outside the repository. Commit concise reviewed findings/protocol changes when appropriate.

---

## 21. Performance/resource evidence

Greia performance is a correctness concern.

Measure relevant changes rather than relying on desktop intuition:

- installed bytes/delta;
- idle and peak RSS;
- steady/busy CPU;
- launch-to-first-usable-screen time;
- transition/recovery latency;
- process/file-descriptor count when relevant;
- graphics/backend behavior;
- 1024×600 usability;
- behavior at the low-memory reference floor;
- Activity frame pacing and hot-loop cost for nontrivial games/animations.

Do not introduce a dependency solely because it is conventional on desktop Linux.

---

## 22. Stop conditions

Stop the current evidence attempt and report the boundary when any of these occurs unless the exact protocol explicitly says otherwise:

- wrong branch/SHA/profile/image;
- unexpected dirty source tree;
- build/test tooling unexpectedly modifies canonical source;
- destructive target identity is ambiguous;
- image/payload integrity mismatch;
- SSH host identity changes without a known intentional reimage;
- required security/isolation boundary is absent;
- first authoritative test/hardware failure is reached;
- mount/loop cleanup cannot be proven;
- proceeding would require unapproved hosted execution;
- proceeding would require inventing credentials;
- proceeding would require bypassing installer/device/trust/sandbox checks.

Partial truthful evidence is preferable to a manufactured PASS.

---

## 23. End-of-task continuity

After substantive work:

- commit coherent source/documentation changes;
- update `HANDOVER.md` when continuation state changed;
- update the active plan when implementation/phase state changed;
- update this manual if repository/build/hardware/remote operating procedure changed;
- update the Activity skill if its governed authoring contracts changed;
- preserve exact verification/evidence scope and unproven gaps;
- state the next legitimate step;
- leave no generated images, private keys, caches or bulky evidence in the source tree.

Documentation-only reviews need not create a fake implementation-plan progress entry when no implementation/phase state changed. Preserve the review under `docs/reviews/` and refresh the handover if the continuation documentation changed.

---

## 24. Drift check for future maintainers

When modifying developer tooling, check these implementation owners against this manual:

```text
tools/greia_remote.py
src/greia_platform/developer_control.py
src/greia_platform/developer_input.py
src/greia_platform/developer_capture.py
src/greia_platform/developer_session.py
build/profiles/modern-amd64-dev.toml
build/build-developer-image.sh
tools/provision_developer_image.py
tools/provision_developer_installer.py
```

When those contracts change, update the manual in the same tranche.
