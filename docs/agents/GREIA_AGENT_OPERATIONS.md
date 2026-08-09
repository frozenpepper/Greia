# Greia Agent Operations Manual

**Audience:** coding/review/testing agents working on Greia OS  
**Status:** mandatory operating contract for repository and test-hardware work  
**Last reviewed:** 2026-08-09  
**Canonical repository:** `frozenpepper/Greia`  

---

## 1. Purpose

This document tells an agent how to work on Greia safely and reproducibly, including how to use the canonical GitHub repository, build/test the system, connect to developer hardware, operate the graphical OS remotely, collect evidence, and hand work to the next agent.

It is intentionally operational. Architecture rationale remains in the architecture document and ADRs; Activity-authoring guidance lives in `skills/greia-activity-authoring/SKILL.md`.

If this document conflicts with an accepted ADR or `AGENTS.md`, the ADR/`AGENTS.md` rule wins and this document must be corrected in the same work tranche.

---

## 2. Mandatory read order before changing Greia

Read these files before substantive work:

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. accepted ADRs relevant to the work, especially ADR 0012–0017
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
6. `HANDOVER.md`
7. this file
8. narrower testing/review documents referenced by the active phase
9. for Activity work, `skills/greia-activity-authoring/SKILL.md`

Do not rely on chat memory when the repository says something different. GitHub is the project source of truth.

---

## 3. Git and GitHub operating rules

### 3.1 Repository is persistent authority

- Work from the current canonical branch or the active feature branch named in `HANDOVER.md`.
- Resolve the current branch tip before editing; do not assume a SHA from an old handover is still HEAD.
- Commit coherent work frequently enough that a lost execution environment does not destroy a substantial tranche.
- Keep generated disk images, private keys, downloaded package archives, build caches and bulky runtime evidence out of Git.
- Keep `HANDOVER.md` and the active plan current after every substantive tranche.
- Append plan progress; never rewrite historical progress to make the history look cleaner.

### 3.2 GitHub Actions / paid execution

**Do not enable, trigger, rerun, or add GitHub-hosted Actions without explicit repository-owner authorization for that specific paid execution.**

A request such as “move forward”, “test this”, or “verify it” is not authorization.

Use GitHub normally for source persistence, review, branches and PR metadata. Use local or explicitly owner-approved execution for builds/tests/evidence.

### 3.3 Never merge merely to make a conflict disappear

A PR conflict must be understood. Resolve compatible repository-wide governance rules on `main` where appropriate; otherwise reconcile the feature branch without silently dropping either side. Do not merge a draft PR unless the owner has asked for that merge.

---

## 4. Current project/evidence boundary

R0–R6 are source-closed. The active blocking architecture phase is R7 direct graphics/session work.

Production Greia currently remains on the Xorg/xinit compatibility path. Do not turn development conveniences into a production X11 dependency, do not make Activities DRM master, and do not introduce a generic desktop environment/window manager.

The last complete provider-free source gate that is safe to cite is the exact result recorded in current `HANDOVER.md`. Resolve that file before quoting counts; never infer a newer PASS from committed tests.

Source tests do not prove VM or physical-hardware behavior.

---

## 5. Supported operator environments

### 5.1 Operator computer

The owner commonly controls Greia from macOS. The repository-side remote helper is platform-neutral Python and uses the host `ssh`/`scp` clients:

```text
tools/greia_remote.py
```

No special GUI remote-desktop product is required. Screenshot and input operations are exposed as Greia developer controls.

### 5.2 Linux build/test environment

Raw Greia image and installer construction must run on an owner-controlled compatible Linux environment as documented by the relevant build/test protocol. Do not attempt destructive image operations on an unsuitable host merely to get a result.

For current local R7 exact-image work also read:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

### 5.3 Physical reference hardware

The first-generation Acer Aspire One remains the extreme low-resource reference. Current estimated floor until inventory evidence replaces it is roughly:

```text
RAM:        768 MiB
storage:    7 GB
resolution: 1024x600
```

Raspberry Pi 400 and Pi 500 are co-equal future/current ARM reference targets, but Pi board/image adapters and physical evidence belong to R8/R14.

Never claim a hardware family is accepted from source/QEMU tests alone.

---

## 6. Developer image versus normal/release image

Remote developer control is intentionally opt-in.

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
```

Normal/reference profile:

```text
build/profiles/modern-amd64.toml
```

Only the explicit developer profile may include the `developer-remote` package set and provisioning marker.

Normal/release Greia must not become SSH-accessible simply because developer tooling exists in the repository.

Private SSH keys, Wi-Fi passwords, API tokens and other credentials must never be committed.

---

## 7. Before using physical test hardware

An agent must establish all of the following before changing or testing the netbook:

1. current repository/branch/HEAD are known;
2. intended image/profile is named explicitly;
3. the current test protocol has been read;
4. destructive versus non-destructive operations are distinguished;
5. first-failure/stop conditions are understood;
6. evidence destination is outside the source tree;
7. no hosted paid execution is being invoked without authorization.

If installation would erase a disk, use the existing graphical fail-closed installer flow. Do not invent a remote `dd`, unattended wipe endpoint, or generic root command merely for convenience.

---

## 8. Build the installed developer target

On an owner-controlled compatible Linux build host:

```bash
sudo bash build/build-developer-image.sh out
```

This wrapper uses the canonical image builder and then performs developer-only provisioning. It must not fork Greia into a second OS build system.

Expected developer artifacts include:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

Treat the private key as local operator credential material. Do not commit, paste into issues/PRs, or include it in evidence archives intended for sharing.

For exact developer-remote implementation/security details read:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

---

## 9. Physical connection assumptions

For the first remote-control acceptance use wired Ethernet whenever possible.

The installed developer target is intended to acquire wired DHCP, advertise mDNS, and appear as:

```text
greia-dev.local
```

The planned remotely operated developer live installer will use a different identity:

```text
greia-installer-dev.local
```

so the live USB and installed target can have independent SSH host keys while using the same operator public key.

Do not hard-code a guessed IP address into source. If mDNS is unavailable on the LAN, the operator may determine the DHCP lease out of band and pass `--host` to the client without changing Greia source.

---

## 10. Connecting to an installed developer netbook

From the repository checkout on the operator computer, wait for Greia:

```bash
python3 tools/greia_remote.py wait --timeout 180
```

Then inspect status:

```bash
python3 tools/greia_remote.py status
```

If a non-default host/key is required:

```bash
python3 tools/greia_remote.py \
  --host <hostname-or-ip> \
  --key <private-key-path> \
  status
```

The helper uses the dedicated Greia known-hosts file by default:

```text
~/.greia/known_hosts
```

Do not disable SSH host-key verification globally to make a test convenient.

---

## 11. Remote graphical test controls

### 11.1 Screenshot

Capture the actual current display and return the PNG to the operator computer:

```bash
python3 tools/greia_remote.py screenshot out/screen.png
```

The current Xorg developer compatibility backend is an implementation detail. Agents should use the stable command rather than directly scraping X11.

### 11.2 Keyboard

```bash
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py key Escape
python3 tools/greia_remote.py key Left
python3 tools/greia_remote.py key Right
```

### 11.3 Pointer

```bash
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py click 3
```

### 11.4 Text input

```bash
python3 tools/greia_remote.py type "test text"
```

Use screenshots before and after important input sequences. A successful command exit is not proof that the expected UI state appeared.

---

## 12. Logs, status and service recovery

Retrieve bounded launcher logs:

```bash
python3 tools/greia_remote.py logs --service launcher --lines 500
```

Useful groups include:

```text
launcher
parent
network
ssh
developer-remote
installer
all
```

Restart the installed Greia launcher:

```bash
python3 tools/greia_remote.py restart
```

The live developer installer path also defines `restart-installer`, but first-time USB remote installation must not be claimed operational until the canonical installer builder actually integrates and passes the live provisioner.

Reboot/power off:

```bash
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py poweroff
```

After reboot, use `wait` again and prove reconnection.

---

## 13. Maintenance SSH shell

An explicit development/recovery shell exists:

```bash
python3 tools/greia_remote.py shell
```

Use it when inspection genuinely requires a shell. Automated test flows should prefer typed `greia-devctl` operations rather than embedding arbitrary root filesystem/systemd commands.

Never expose a generic privileged shell API to Activities or turn it into a normal product feature.

---

## 14. Remote Activity deployment

For ordinary developer Activities:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

The developer source is:

```text
/var/lib/greia-developer/activities
PackageTrust.DEVELOPER_UNSIGNED
```

The built-in source remains:

```text
/opt/greia-os/activities
PackageTrust.BUILT_IN
```

Remote placement must never upgrade package trust.

Remove an ordinary remote deployment:

```bash
python3 tools/greia_remote.py remove <activity-id>
```

For deliberate built-in testing only:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
python3 tools/greia_remote.py restore <activity-id>
```

The original built-in must remain recoverable. Do not use `--replace-system` as the default development loop.

For authoring/validation rules see `skills/greia-activity-authoring/SKILL.md`.

---

## 15. First-time remote installation boundary

Source includes a developer live-installer provisioner, but agents must check the current handover before claiming it is integrated.

The intended eventual flow is:

```text
boot developer USB
→ greia-installer-dev.local becomes reachable
→ operator captures screenshots and drives existing graphical installer remotely
→ existing eligible-target/payload/device checks remain authoritative
→ reboot
→ installed target appears as greia-dev.local
```

**Never replace this with an unattended destructive disk-wipe command.**

If current `HANDOVER.md` says the live provisioner is not wired into `build/build-installer-image.sh`, installation still requires the existing safe local interaction path.

---

## 16. Standard source verification

The canonical source gate is:

```bash
make verify
```

It runs provider-free unit tests, project/Activity validation, shell syntax checks and source-footprint checks.

For focused iteration:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Developer-remote focused suite:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v
```

Do not claim PASS unless the command actually executed in the current checkout and you have the result.

---

## 17. Evidence discipline on real hardware

For every meaningful physical test, record at minimum:

- repository branch and exact commit SHA;
- image/profile identity;
- image hash when applicable;
- machine identity/inventory relevant to the test;
- command sequence;
- timestamps or sequence ordering;
- stdout/stderr/logs;
- screenshots before/after visible transitions;
- explicit PASS/FAIL/NOT-RUN classification;
- first failure exactly as observed;
- whether a reboot/power cycle occurred;
- whether any manual intervention was required.

Keep large evidence archives outside the repository. Commit only concise reviewed summaries/protocol updates when appropriate.

### Negative evidence is evidence

If an operation fails, preserve the failure. Do not weaken the test, silently change the environment, or retry repeatedly until it passes unless the protocol explicitly authorizes a new attempt.

If a test must be rerun after a fix, make the new attempt distinguishable from the failed one.

---

## 18. Performance/resource evidence

Greia targets very constrained machines. When testing a new system dependency, runtime, display path or nontrivial Activity, measure rather than assume.

Relevant dimensions include:

- installed bytes/delta;
- idle and peak RSS;
- CPU load/steady-state usage;
- launch time and first usable frame;
- transition/recovery latency;
- file-descriptor/process count where relevant;
- GPU/backend behavior;
- 1024x600 usability;
- behavior under the low-memory reference class.

Do not justify a dependency because it is common on desktop Linux. Greia's resource floor is architectural.

---

## 19. Agent stop conditions

Stop the current evidence attempt and report clearly when any of these occurs unless the applicable protocol explicitly says otherwise:

- wrong branch/SHA/profile/image;
- source tree becomes unexpectedly dirty;
- build/test tool modifies canonical source artifacts unexpectedly;
- destructive target identity is ambiguous;
- image/payload integrity mismatch;
- SSH host identity/key state contradicts the developer-image contract;
- a required security boundary is absent;
- first authoritative hardware/evidence failure is reached;
- proceeding would require unapproved paid hosted execution;
- proceeding would require inventing credentials or bypassing a safety check.

Partial, truthful evidence is better than a manufactured PASS.

---

## 20. Handover duties after substantive work

Before ending a substantive Greia work tranche:

1. commit coherent source/documentation changes to GitHub;
2. append an accurate progress entry to the active remediation plan;
3. update `HANDOVER.md` with exact implemented/unimplemented state;
4. record exactly which tests actually ran and their results;
5. record hardware/VM evidence still missing;
6. state the exact next legitimate step;
7. update this manual if project/test-hardware operating procedure changed;
8. update `skills/greia-activity-authoring/SKILL.md` if the Activity SDK, package schema, shared assets/UI canon, performance requirements or validation workflow changed.

These two agent-facing documents are living contracts and must not be allowed to drift behind the implementation.
