# Greia — Local Agent Full Test, Repair, Build and Hardware Session

**Date:** 2026-08-18  
**Audience:** the owner's local coding/test agent  
**Repository:** `frozenpepper/Greia`  
**Canonical branch:** `main`  
**Purpose:** run a complete owner-controlled source → Parent App → image → install → hardware → launcher/Activity acceptance session, fixing genuine defects as they are found and committing the fixes to `main`.

---

## 0. READ THIS FIRST — THIS IS AN ACTIVE OWNER DIRECTIVE

This file records explicit owner instructions for the current development/test cycle.

The local agent is **not** being asked to act as a passive test runner. It is authorized and expected to:

- inspect the current implementation deeply;
- run the tests and builds described here;
- diagnose genuine failures;
- edit source, tests and documentation to fix root causes;
- add regression coverage for fixes;
- rerun the smallest relevant test first, then the broader gate;
- commit coherent fixes directly to `main` and push them;
- continue the session after an ordinary repair instead of stopping merely because a test failed.

The agent must **not** obtain a green result by weakening a test, deleting an assertion, hiding an error, hard-coding one Acer model, broadening a security boundary without understanding it, or bypassing Greia's platform abstractions.

The goal is a better Greia, not a cosmetically green log.

### Owner policy amendment that MUST be reconciled before calling the session complete

Some older repository text/source currently reflects an earlier fail-closed developer-SSH/recovery-credential policy. The owner has now explicitly changed the active product/development direction:

1. **The absurd random password/recovery code shown at the end of installation must go.** Do not preserve it as a requirement merely because tests or old docs currently expect it.
2. **Initial Parent/admin credentials are simple and predictable:**
   - username: `greia`
   - password: `greia`
3. Parents must be able to change the **main Parent password** from Greia Parents.
4. Each child may optionally have a **separate Greia-profile password**. A child password is profile-level Greia authentication; it does **not** mean creating one Linux account per child.
5. During active development/hardware bring-up, **developer/test installations must remain reachable over SSH so the local agent can continue working after installation and reboot.** The development/test SSH account is `greia` and its initial password is `greia` unless the parent changes it.
6. Root SSH login remains disabled. Child-facing operation still exposes no shell, login prompt, terminal or desktop.
7. Do not silently turn the development convenience into an unreviewed release-security claim. Development/test SSH availability and final release SSH policy are separate questions. The current session must keep developer/test installs reachable.
8. If changing the main Parent password is intended to change the maintenance/SSH password too, implement that through a **typed Greia-owned privileged operation**, not through arbitrary shell execution from the Parent web server.
9. The Parent API/client must never return stored password material. Child and Parent password storage must use a bounded password-digest mechanism; do not store plaintext password files merely because the initial value is simple.
10. If old `AGENTS.md`, Parent docs, test expectations, installer code, GRUB code, developer-image code or SSH config contradict this owner directive, treat that as **policy drift to reconcile**, not as a reason to ignore this directive.

The agent should update the canonical owner documents while implementing this policy so the repository no longer contains two competing instructions.

---

# 1. Non-negotiable Greia project goals

Keep these goals in mind while diagnosing and repairing:

- Greia is a child-first graphical appliance OS, not a conventional Linux desktop.
- No visible Linux shell in normal child operation.
- The first-generation Acer Aspire One remains the extreme low-resource x86 reference; Pi 400/Pi 500 remain first-class ARM references.
- Fixes must be **hardware-independent at the architecture level**. A hardware-specific build profile is allowed; hard-coded model detection or Acer-only core behavior is not.
- Build-host hardware must never be treated as target-hardware authority.
- Do not deepen X11 coupling. The current Xorg path is provisional compatibility while R7 remains open.
- Preserve clean boundaries between platform, launcher, installer, Parent service, Activities, build system and hardware adapters.
- Prefer cohesive classes, typed data and narrow interfaces. Do not grow giant procedural managers.
- Keep memory, caches, logs and animations bounded for the low-resource reference floor.
- Activities remain sandboxed and do not gain raw `/dev/input`, root, package-manager or arbitrary filesystem authority as a shortcut.
- Parent API root effects go through typed Greia-owned operations/brokers. Never add a generic web-to-shell or generic root RPC.
- A hardware fix is integrated only when the physical problem is resolved, authoritative build/source contains the fix, a hardware-independent regression protects the root-cause class, and living documentation explains the class of failure.

---

# 2. Hard execution policies

## 2.1 Git/GitHub

- Work on `main`.
- Do **not** create a feature/recovery/test branch unless the owner explicitly asks for one.
- GitHub is canonical persistence.
- Commit coherent fixes as you work; do not leave hours of useful work only in the local working tree.
- Push commits to `origin/main` after each coherent repaired tranche when practical.
- Do not discard or overwrite pre-existing uncommitted owner changes.

## 2.2 NO GitHub Actions

Without a new explicit owner instruction, do **not** use GitHub-hosted Actions in any way for this session:

- do not trigger;
- do not rerun;
- do not query run status/jobs/logs;
- do not download hosted artifacts;
- do not add an automatic trigger merely to obtain evidence.

All evidence in this protocol is owner-controlled/local.

## 2.3 Evidence and temporary files

Create one project-local session directory under `out/` and keep the human-readable evidence there. Do not create ZIPs for the owner and do not package the project as part of this protocol.

Suggested setup:

```bash
cd "$(git rev-parse --show-toplevel)"
SESSION_START_SHA="$(git rev-parse HEAD)"
SESSION_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)"
SESSION_ROOT="$PWD/out/local-agent-session-$SESSION_ID"
mkdir -p "$SESSION_ROOT"
printf '%s\n' "$SESSION_START_SHA" > "$SESSION_ROOT/start-sha.txt"
```

Do not put private SSH keys, Wi-Fi credentials, Parent bearer credentials or password dumps into committed evidence.

Repository build scripts may use their own managed temporary directories internally. Do not invent ad-hoc evidence/work trees under filesystem-root `/tmp`.

## 2.4 Destructive operations

Do not guess a disk/device path.

Before writing installation media or erasing a target, identify the exact device from the current machine state. If device identity is genuinely ambiguous, stop **only the destructive step**, preserve what has already been learned, and ask the owner which physical device is intended. Continue any independent non-destructive source work.

Never bypass installer target-eligibility, payload-integrity or identity revalidation merely to complete a test.

---

# 3. Session bootstrap

Run:

```bash
cd "$(git rev-parse --show-toplevel)"
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
```

Expected branch: `main`.

Then fetch repository state without invoking Actions:

```bash
git fetch origin main
printf 'local  %s\n' "$(git rev-parse HEAD)"
printf 'origin %s\n' "$(git rev-parse origin/main)"
```

If the tree is clean and local `main` is only behind `origin/main`, fast-forward:

```bash
git pull --ff-only origin main
```

If there are unknown local changes, **do not reset them**. Inspect and preserve them before integrating remote changes.

Record the actual starting SHA after synchronization:

```bash
git rev-parse HEAD | tee "$SESSION_ROOT/tested-start-sha.txt"
git status --short | tee "$SESSION_ROOT/start-status.txt"
```

---

# 4. Mandatory reading before editing

Read, in this order:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/INSTALLATION_ISSUES_LOG.md
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/product/PARENT_MANAGEMENT.md
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Also read relevant accepted ADRs, especially 0012, 0013, 0018, 0019, 0020 and the Parent architecture ADR referenced by `PARENT_MANAGEMENT.md`.

Do not blindly obey stale text that contradicts the **owner policy amendment in §0**. Reconcile the stale owner/source/test contracts before the session is declared complete.

---

# 5. Baseline source inspection — specifically re-check the installation hell

Before changing anything, inspect the current authoritative source for every root-cause class learned on real hardware.

At minimum review:

```text
build/build-image.sh
build/build-installer-image.sh
build/build-developer-image.sh
build/overlay/etc/initramfs-tools/
build/installer-overlay/etc/initramfs-tools/
build/overlay/etc/systemd/system/greia-launcher.service
build/installer-overlay/etc/systemd/system/greia-installer.service
build/overlay/etc/X11/Xwrapper.config
build/overlay/etc/X11/xorg.conf.d/
src/greia_installer/engine.py
src/greia_installer/main.py
src/greia_platform/grub_security.py
src/greia_platform/developer_control.py
tools/provision_developer_image.py
tools/provision_developer_installer.py
tools/greia_remote.py
tests/test_installation_hardware_regressions.py
```

Verify conceptually that the source still protects these classes of failure:

1. target initramfs decisions come from target-kernel/profile authority, not the build host;
2. live UUID, kernel/initrd/squashfs, installation payload, digest and profile stay coherent;
3. graphical services do not inherit the VT as interactive stdin;
4. systemd runtime paths needed during namespace construction are created with systemd-owned runtime-directory policy;
5. the current Xorg compatibility service has the authority it actually needs without leaking that authority into Activities;
6. Xwrapper policy matches the appliance session rather than desktop-console heuristics;
7. duplicate `/dev/input/mouse*` aliases do not create duplicate pointer handling;
8. Bubblewrap creates private `/run` and bind destinations correctly;
9. the no-WM Xorg path hands keyboard focus explicitly to Greia;
10. installer target identity/payload integrity is rechecked around destructive steps;
11. cleanup does not recursively delete through surviving mounts;
12. architecture-neutral build overlays do not acquire unconditional x86-only module assumptions.

If any hardware fix exists only in documentation or only on the machine but not in build source/tests, repair that before rebuilding.

---

# 6. Mandatory credential/SSH/Parent reconciliation work

This is an explicit objective of this session, not optional polish.

Start with a source audit:

```bash
git grep -nE 'recovery_code|recovery-code|grub-recovery|greiaadmin|PasswordAuthentication|KbdInteractiveAuthentication|AuthenticationMethods|AllowUsers|provision_developer|maintenance\.ssh|secret_action' -- . \
  | tee "$SESSION_ROOT/credential-source-audit.txt"
```

Then reconcile the implementation and tests to the owner policy in §0.

## 6.1 Installer completion UX

The current random recovery-code/password presentation must be removed.

Acceptance requirement:

- installation completes without telling the parent to photograph/write down a generated random code;
- there is no generated per-install random credential that the parent must preserve merely to recover/manage Greia;
- the completion screen gives simple next-step information, not a cryptographic scavenger hunt;
- if it mentions credentials, the initial Parent/admin identity is `greia` / `greia` and tells the parent that it can be changed in Greia Parents.

Do not leave dead random-code generation in the build/installer merely because the UI stopped displaying it. Remove or refactor the obsolete path and update tests/docs.

## 6.2 Parent/admin credential model

Implement or complete one coherent platform-owned main Parent credential with initial values:

```text
username = greia
password = greia
```

Requirements:

- stored as a password digest, not plaintext application state;
- changing it is a typed operation;
- API responses never return the stored password/digest;
- Parent App exposes a clear **Change Parent password** control;
- changing it requires an appropriate current-parent authorization flow;
- do not confuse the Parent password with per-device bearer credentials used by paired Parent clients;
- pairing credentials remain individually revocable.

If bootloader/maintenance authentication is meant to follow the main Parent password, centralize that relationship through an explicit credential service/broker. Do not create three unrelated password stores that drift.

## 6.3 Child profile passwords

The current Greia profile layer already has bounded optional secrets. Preserve that architecture.

Acceptance requirement:

- a child profile may have no password;
- parent may set/replace/clear its password from Greia Parents;
- masking while typing remains a separate per-profile preference;
- no child password/hash is returned by the API;
- child profiles remain app/platform profiles over the Greia child runtime account, not one Linux login per child.

## 6.4 Development/test SSH must stay reachable

For this active development cycle, the installed **developer/test** image must boot with SSH reachable so the agent can continue without local terminal copy/paste.

Required initial development/test SSH identity:

```text
user: greia
password: greia
```

Requirements:

- `sshd` is enabled/listening on developer/test installs after installation and reboot;
- root SSH login is disabled;
- normal child UX still exposes no shell/login prompt;
- development SSH does not grant Activities shell/root authority;
- if the main Parent password is changed and SSH intentionally shares that credential, the change is performed through a typed privileged Greia operation;
- do not rely on a manually copied one-time generated password;
- do not require the owner to copy/paste terminal diagnostics from the Acer when the agent can collect them over SSH.

It is acceptable to retain key authentication as an additional automation path, but it must not make the required `greia` / `greia` development login disappear.

The local agent should update stale `AGENTS.md`, `docs/agents/GREIA_AGENT_OPERATIONS.md`, `docs/product/PARENT_MANAGEMENT.md`, installation docs/reviews and source tests in the same repaired tranche so the repository ends with one coherent policy.

---

# 7. Focused source gate for the 2026-08-18 tranche

Run this first and capture the complete output:

```bash
set -o pipefail
PYTHONPATH=src python3 -m unittest \
  tests.test_installation_hardware_regressions \
  tests.test_ui_motion_scroll \
  tests.test_launcher_presentation \
  tests.test_activity_packages \
  tests.test_activity_contract \
  tests.test_parent_api -v \
  2>&1 | tee "$SESSION_ROOT/focused-2026-08-18.log"
```

### If it fails

Do **not** just report the first ordinary failure and stop the whole assignment.

Instead:

1. preserve the failing log unchanged;
2. identify whether failure is product/source defect, stale test, environment/dependency issue, or owner-policy drift;
3. fix the root cause;
4. if source behavior changes, add/update a regression test that captures the **general invariant**;
5. do not add Acer model/name/serial-specific logic to satisfy the test;
6. run the smallest relevant test module again;
7. when that passes, rerun the focused set above;
8. commit the coherent fix and push it;
9. continue.

A test may be changed when the **accepted owner/product requirement changed** (notably the credential policy in §0). In that case, update the test to the new requirement and also update the owning documentation/source. Do not describe this as “weakening” the test; it is a contract migration and must be explicit.

---

# 8. External Greia Parent App review and test

Greia deliberately keeps the main Parent HTML client in a separate repository. The current pin is declared by:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The current pinned repository is:

```text
frozenpepper/Greia-Parent-App-Html
```

Do not assume the revision printed in this document is still current. Read `runtime/parent-app-client.toml` at session time and use its exact revision.

## 8.1 Locate or obtain the Parent-App checkout

Prefer an existing owner checkout. If none exists and Git credentials allow it, clone the private repository into an ordinary owner workspace. Do not clone it inside Greia's tracked source tree.

Record:

```bash
git -C <parent-app-checkout> status --short
git -C <parent-app-checkout> rev-parse HEAD
```

Check out the revision currently pinned by Greia before establishing baseline behavior.

## 8.2 Run baseline Parent-App tests

From the Parent-App checkout:

```bash
npm test 2>&1 | tee "$SESSION_ROOT/parent-app-npm-test.log"
```

Current package contract uses Node's built-in test runner; do not add a heavyweight JS framework just for this session.

## 8.3 Review actual Greia ↔ Parent-App coupling

Review together:

```text
Greia:
  src/greia_parent/protocol.py
  src/greia_parent/api_server.py
  src/greia_parent/package_api.py
  src/greia_parent/credentials.py
  src/greia_parent/server.py
  runtime/parent-app-client.toml
  runtime/parent-app-client.manifest.json

Parent App:
  src/api.js
  src/app.js
  src/activity_install_ui.js
  src/credential_store.js
  tests/*.test.js
```

Verify:

- browser code uses the versioned Parent API rather than Linux filesystem/shell assumptions;
- same-origin `/api/v1` behavior is preserved for the installed client;
- per-device pairing credentials remain distinct/revocable;
- main Parent-password management is represented separately from device bearer credentials;
- child profile create/update can set/replace/clear optional child password;
- Activity installation UI is capability-driven;
- `.greiaactivity` upload remains raw bounded bytes through the typed package endpoint;
- Parent-installed Activities keep `PARENT_TRUSTED_UNSIGNED` provenance;
- changing Parent/child passwords does not expose password material in API responses or logs.

## 8.4 If the Parent App must change

Make the required changes in `Greia-Parent-App-Html`, run `npm test`, commit and push there first.

Then update in Greia:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

with the exact new Parent-App revision and file integrity values. Run Greia validation afterward. Do not point Greia at an uncommitted Parent-App working tree or a floating branch name.

---

# 9. Full source verification

Once focused Greia tests and Parent-App tests are green after any fixes:

```bash
set -o pipefail
make verify 2>&1 | tee "$SESSION_ROOT/make-verify.log"
```

Record the actual counts from the run. Never copy old counts from `HANDOVER.md` into a new result.

If `make verify` fails, use the repair loop in §7. Do not skip the failed gate and proceed as if the produced image were trustworthy.

After any source repair performed during `make verify`, rerun the focused test for that subsystem and then rerun `make verify` completely.

---

# 10. Choose the correct build profile without turning one Acer into the architecture

Do not guess the target architecture from the build host.

Current Acer candidate profiles are documented under `build/profiles/README.md`. Use current evidence from the target machine/repository to select the correct **development/test** profile.

If the target is already reachable, collect architecture facts automatically over the existing remote channel rather than asking the owner to manually transcribe terminal output.

Examples of useful target facts:

```bash
uname -m
getconf LONG_BIT
lscpu
cat /proc/cpuinfo
```

Profile selection is allowed to be machine-specific. Core fixes are not.

For an Acer developer profile, the current family includes variants such as:

```text
acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64-dev
```

Use the one supported by actual target evidence. Do not alter common overlays to force an x86-only assumption onto ARM.

Record the selected profile and why in:

```text
$SESSION_ROOT/selected-profile.txt
```

---

# 11. Build a fresh graphical installer from the repaired source

Use an owner-controlled Debian/Ubuntu x86 build environment with root access and the dependencies required by the canonical builder.

Do not reuse an old installer image after source fixes.

From the Greia checkout:

```bash
BUILD_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$BUILD_SHA" > "$SESSION_ROOT/build-sha.txt"
mkdir -p "$SESSION_ROOT/build"
sudo bash build/build-installer-image.sh <selected-dev-profile> "$SESSION_ROOT/build" \
  2>&1 | tee "$SESSION_ROOT/build-installer.log"
```

The canonical builder must remain the authority. Do not manually assemble a one-off rootfs that cannot be reproduced from the repository.

### Build acceptance

Confirm the build produced the expected image/profile/report artifacts and that the reports identify the requested profile/architecture.

Inspect the generated artifact for the installation lessons already learned:

- live-media UUID exists and matches the value embedded in the live initramfs/boot command line contract;
- payload digest matches the payload;
- installer and payload profile manifests are present/coherent;
- target-kernel boot-critical storage support is present for the selected x86 target without shared-overlay x86 hard-coding;
- graphical installer service has noninteractive stdin;
- target launcher service/runtime directory/Xwrapper/input alias/Bubblewrap contracts match the reconciled source;
- the installed developer/test payload is configured so SSH will remain reachable after first boot under the current `greia` / `greia` development policy;
- no end-install random recovery-password dependency remains.

Do not claim physical support from image inspection alone.

---

# 12. Installation-media writing — do not guess device identity

The exact removable-media device is machine-specific. Inspect it immediately before writing.

On Linux, use tools such as:

```bash
lsblk -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN,RM,RO,MOUNTPOINTS
```

On macOS, use the owner machine's normal disk-inspection tooling.

Before any raw write, confirm all of the following:

- the selected device is the intended removable installation media;
- it is **not** the build host's system disk;
- its size/model/transport match the physical media;
- mounted partitions are unmounted safely;
- the source image path and SHA are the image built in §11.

Use the repository's established writing procedure/tool if one exists for the current host. If there is no safe established write path and the device identity is ambiguous, stop this destructive step and tell the owner exactly what must be selected. Do not invent a device path.

Record image SHA256 before writing:

```bash
sha256sum "$SESSION_ROOT"/build/*.img | tee "$SESSION_ROOT/image-sha256.txt"
```

Use the platform-equivalent hashing command on macOS if needed.

---

# 13. Physical graphical installer acceptance

Boot the newly built installer on the target machine.

The expected path is graphical. No Linux login/shell should appear during the supported installer flow.

Exercise at minimum:

1. boot to the Greia installer;
2. keyboard-layout selection/detection;
3. eligible-target selection;
4. tap-to-click/default hardware settings;
5. Wi-Fi path if supported, otherwise explicit offline path;
6. final destructive confirmation;
7. installation progress;
8. completion screen;
9. shutdown/reboot into the installed target.

### Mandatory completion-screen check

The old generated random recovery code/password must **not** appear.

The completion UX should be simple. The active initial Parent/admin credentials are:

```text
greia / greia
```

and the parent should be directed to Greia Parents to change the main Parent password.

### Installation failure repair loop

If the installer fails:

- preserve the first failure exactly;
- collect installer logs automatically where possible;
- identify the root-cause class rather than patching a symptom on the Acer;
- fix authoritative source/build inputs;
- add a hardware-independent regression for the cause where feasible;
- update `docs/INSTALLATION_ISSUES_LOG.md` if this is a new failure class or materially changes an existing one;
- commit/push the fix;
- rerun focused tests and `make verify`;
- rebuild a **fresh** installer;
- retry installation.

Do not hand-edit the installed target and call the repository fixed. A manual machine repair is diagnostic evidence only until the build source reproduces it.

---

# 14. First installed boot and SSH continuity

After first boot, the local agent must regain remote access and continue the session.

Prefer mDNS if available; otherwise discover the DHCP address without hard-coding it into source.

Expected development/test login:

```text
user: greia
password: greia
```

Confirm:

```text
- SSH service is listening after reboot;
- greia login works;
- root SSH login does not work;
- child launcher remains the normal local screen;
- no local terminal/login prompt is exposed to the child;
- reboot preserves remote accessibility.
```

Once connected, collect a machine-readable hardware/runtime record directly into the session evidence. Do **not** ask the owner to copy/paste terminal output from the Acer.

Useful facts include:

```bash
uname -a
cat /etc/greia-os/build-info 2>/dev/null || true
cat /etc/greia-os/base-system-manifest 2>/dev/null || true
systemctl --no-pager --full status greia-launcher.service greia-parent.service ssh.service
ip -brief address
```

Redact secrets before committing any summary.

Keep an SSH session open while testing a Parent-password change so a bug in credential synchronization does not unnecessarily strand the agent.

---

# 15. Real Parent App connection acceptance

This is not satisfied by unit tests alone.

From another machine/browser on the same owner-controlled LAN:

1. verify the Greia Parent service is reachable;
2. load the actual Parent HTML application served/pinned by the Greia integration path;
3. verify `/api/v1/meta` and the authenticated API flow behave as designed;
4. complete the currently supported pairing/bootstrap flow without exposing secrets in logs;
5. verify device credential persistence/revocation behavior;
6. verify system status and Activities list;
7. verify input/display settings round-trip;
8. verify child-profile create/update/delete;
9. verify child password set/replace/clear and masking preference;
10. verify the new main Parent-password change control;
11. if main Parent password intentionally owns the development SSH password, prove synchronization using a **second** SSH connection before closing the first;
12. verify the previous password is rejected after a successful change;
13. return the development password to `greia` if that is required for the rest of the current owner test session;
14. verify paired-device credentials remain valid/revocable independently of the human-readable Parent password unless the accepted architecture explicitly defines otherwise.

Any Parent App/API mismatch must be fixed on the correct side of the API boundary, with tests in both repositories where appropriate.

---

# 16. Parent Activity-install acceptance

On an explicitly developer/owner-enabled machine, verify the real Parent HTML Activity installation path.

Acceptance:

- UI exposes install only when `activities.install` capability is true;
- upload is a bounded `.greiaactivity` package;
- malformed/traversal/symlink/compression-bomb/casefold-duplicate packages are rejected;
- existing Activity ID collision is rejected;
- package-owned PNG/WebP icon validation happens before activation;
- install transaction is serialized and receipt/immutable/active ordering remains atomic;
- Activity remains `PARENT_TRUSTED_UNSIGNED`;
- running launcher discovers the Activity only after runtime/permission/history/supervisor authority has rebuilt successfully;
- installed Activity appears with its name, category and unique icon;
- it launches and returns through the ordinary authoritative lifecycle path.

Do not bypass the capability gate by copying the Activity directly into `/opt`.

---

# 17. Launcher/UI physical acceptance at 1024×600

Inspect the actual rebuilt launcher on the low-resource target.

Check all of these deliberately:

### Activity tiles

- every Activity tile visibly shows its Activity name;
- names fit or gracefully shrink/ellipsis without distorted glyphs;
- package icon is never the only identifier;
- shadows are subtle and do not look like thick desktop drop shadows;
- icon/image scaling remains crisp enough at the reference resolution.

### Categories

- root view shows the semantic categories;
- entering a category shows a persistent header with **Back + category icon + category title**;
- the category header stays visible while the Activity list scrolls;
- Backspace/Esc/local Back behavior matches the design hierarchy;
- education tags are not confused with launcher navigation categories.

### Scrolling

- more Activities than the visible grid can be reached;
- keyboard selection keeps the selected Activity visible;
- mouse wheel scrolls semantic rows;
- scroll buttons appear only when needed;
- no unbounded Surface/widget creation occurs while scrolling.

### Motion/effects

- hover/selection gives a small lift/scale/outline cue;
- launch has the short squiggle/bounce flourish before the normal starting overlay;
- effects remain responsive on the Acer floor;
- no obvious runaway CPU loop is introduced when idle.

### Input/focus

- keyboard focus works after boot without a window manager;
- touchpad/mouse is not double-counted via legacy aliases;
- Activity launch/return keeps focus correctly;
- ordinary Activity sandbox/input authority remains intact.

Capture screenshots for visible failures and after meaningful fixes.

---

# 18. Resource sanity on the target

Do not treat visual success as enough on the low-resource reference.

Measure/inspect at minimum:

- idle launcher RSS;
- CPU when launcher is idle;
- CPU while hovering/scrolling/launching;
- process count;
- unexpected crash/restart loops;
- free disk space;
- launch-to-usable-screen behavior;
- Parent service responsiveness while the launcher is active.

Use bounded observation. Do not install a giant profiling stack onto the target just for convenience.

If a UI feature is materially too heavy, optimize the implementation rather than disabling the feature reflexively.

---

# 19. Cross-hardware sanity

The Acer is a reference, not the hidden definition of x86.

After the Acer path is healthy, run at least one additional available x86 sanity path when practical (another machine or an appropriate owner-controlled VM) using the same authoritative source.

The purpose is to catch fixes that accidentally rely on one Acer-specific device name, storage controller, display quirk or input topology.

Do not claim ARM hardware acceptance from x86 testing. Do not add x86-specific core policy to make the additional x86 test pass.

---

# 20. When to STOP rather than repair autonomously

The local agent should repair ordinary source/test/build/runtime failures autonomously. Stop or ask the owner only when proceeding would cross a genuine owner/safety boundary, for example:

- the destructive target disk/media cannot be identified safely;
- pre-existing owner changes would need to be discarded or overwritten;
- a required private credential is unavailable and cannot be derived safely;
- an action would require GitHub Actions/paid hosted execution without authorization;
- a design choice would materially redefine an accepted architecture rather than repair its implementation;
- the only apparent fix would expose generic root/shell/filesystem/package-manager authority to the Parent web API or Activities;
- evidence shows source/image identity is not the one being tested;
- cleanup cannot prove mounts/loop devices/resources are detached safely;
- a remote host-key change is unexplained by a known reimage.

Do **not** stop merely because:

- a unit test fails;
- a build fails;
- the installer hits a reproducible bug;
- the launcher crashes;
- the Parent App/API disagree;
- the new credential requirement contradicts an old test/doc;
- a regression needs a source fix.

Those are the work.

---

# 21. Commit discipline while fixing

For each coherent fix:

```bash
git status --short
git diff --check
git diff -- <relevant paths>
```

Stage only the intended files, then commit with a terse descriptive message.

Examples:

```text
installer: remove random recovery credential UX
remote: keep developer installs reachable
parent: add main Parent password management
parent: preserve optional child profile passwords
build: persist target-kernel storage fix
launcher: repair category header layout
```

Push to `origin/main` after coherent commits when possible.

Do not create a branch solely because an automated Git workflow normally prefers one; the owner has explicitly selected `main` as the working branch for Greia.

---

# 22. Required documentation updates for fixes

Before concluding, reconcile the living docs with what is actually implemented.

Depending on the changes made, update:

```text
AGENTS.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/INSTALLATION_ISSUES_LOG.md
docs/product/PARENT_MANAGEMENT.md
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Preserve historical statements as historical evidence where appropriate, but append/correct the **current** policy clearly. Do not rewrite an old hardware failure so it looks as if it never happened.

If Parent-App source changes, update that repository's own handover/docs too.

---

# 23. Final rerun after all repairs

After the final code change, run the complete current gates again from the final SHA.

Greia:

```bash
FINAL_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$FINAL_SHA" > "$SESSION_ROOT/final-sha.txt"

set -o pipefail
PYTHONPATH=src python3 -m unittest \
  tests.test_installation_hardware_regressions \
  tests.test_ui_motion_scroll \
  tests.test_launcher_presentation \
  tests.test_activity_packages \
  tests.test_activity_contract \
  tests.test_parent_api -v \
  2>&1 | tee "$SESSION_ROOT/final-focused.log"

make verify 2>&1 | tee "$SESSION_ROOT/final-make-verify.log"
```

Parent App, at the exact revision finally pinned by Greia:

```bash
npm test 2>&1 | tee "$SESSION_ROOT/final-parent-app-npm-test.log"
```

If final source changed after the image used for physical acceptance was built, **that physical evidence belongs to the older SHA**. Either rebuild/retest the relevant physical scope or state it truthfully as needing rerun. Never relabel old hardware evidence as evidence for a newer source SHA.

---

# 24. Required final report

Create:

```text
$SESSION_ROOT/LOCAL_AGENT_RESULT.md
```

It must contain, at minimum:

```text
# Greia local-agent session result

Start SHA:
Final SHA:
Branch:
Selected build profile:
Physical target:
Parent-App start revision:
Parent-App final/pinned revision:

## Owner credential policy
- random end-install password/code removed: PASS/FAIL/NOT-RUN
- initial Parent/admin greia/greia: PASS/FAIL/NOT-RUN
- Parent password change from Parent App: PASS/FAIL/NOT-RUN
- optional child password set/replace/clear: PASS/FAIL/NOT-RUN
- developer/test SSH greia/greia survives reboot: PASS/FAIL/NOT-RUN
- root SSH rejected: PASS/FAIL/NOT-RUN

## Source gates
- focused suite:
- make verify:
- Parent App npm test:

## Build
- profile:
- image path:
- image sha256:
- build result:
- initramfs/storage contract:
- media UUID/payload contract:

## Physical installation
- graphical boot:
- disk selection safety:
- installation:
- random recovery-code UX absent:
- first installed boot:

## Parent App live integration
- service reachable:
- pairing/auth:
- main Parent password:
- child profiles/passwords:
- Activity install:

## Launcher 1024x600
- Activity names:
- categories:
- category header/back/icon:
- scrolling:
- shadows/hover:
- launch flourish:
- focus/input:

## Resource observations

## Bugs found and fixes committed
For each: symptom -> root cause -> source fix -> regression -> commit SHA

## Remaining failures / unproven scope

## Exact next legitimate step
```

Do not ZIP this evidence. Leave the directory in place and report its path to the owner.

---

# 25. Definition of a successful session

A successful session does **not** mean “the script returned zero once.”

The desired end state is:

- current `main` has coherent source/docs/tests;
- focused source tests pass on the final SHA;
- `make verify` passes on the final SHA;
- Parent-App tests pass at the exact revision Greia pins;
- installation is reproducible from canonical builders;
- the hardware-derived installation fixes are present in source, not merely patched on the Acer;
- graphical install and first boot work on the target;
- there is no random end-install recovery password/code UX;
- initial Parent/admin credentials are `greia` / `greia`;
- main Parent password can be changed from Greia Parents;
- child passwords are optional per Greia profile and parent-manageable;
- developer/test SSH remains reachable after install/reboot as `greia` / `greia` (or the current changed Parent password when the implemented policy deliberately shares it);
- Parent App can actually connect to the installed Greia and exercise its supported management API;
- Parent Activity installation works when developer/owner-enabled;
- launcher names/categories/scrolling/icons/effects work at 1024×600;
- fixes remain architecture-clean and do not encode one Acer as the platform;
- all claims are tied to exact SHAs and actual executed evidence.

If some physical step cannot be completed, deliver the truthful partial result and continue all independent repair/verification work that can still be done.