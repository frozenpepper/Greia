# Greia — Standalone Engineering Handover

**Date:** 2026-08-10  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Resume without chat history

Before substantive work read, in this order:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. accepted ADRs relevant to the task, especially ADR 0012–0017;
6. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
7. this `HANDOVER.md`;
8. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
9. `skills/greia-activity-authoring/SKILL.md` for any Activity work;
10. the exact R7/testing/review documents named below.

GitHub is canonical. Resolve the actual branch HEAD before editing or testing; do not assume the SHA in a previous chat summary is still current.

### Documentation authority

`docs/DOCUMENTATION.md` now defines the project documentation model:

```text
AGENTS.md                    repository-wide work/product rules
accepted ADRs                normative architecture decisions
source/runtime declarations  exact implemented APIs/schemas/commands
active remediation plan      ordering and closure criteria
HANDOVER.md                  current branch/evidence/blocker state
docs/testing/*               exact named test/operator procedures
agent operations/skills      derived living manuals
reviews                      dated evidence/analysis snapshots
```

Do not choose whichever document is convenient when two statements differ. Correct the stale derived document according to the owner of the fact.

---

## 2. Critical hosted-execution rule

**Do not use the GitHub Actions execution service without the repository owner's explicit authorization for that specific use.**

Without authorization do not:

- trigger, rerun or dispatch hosted workflows;
- add automatic hosted triggers;
- query Actions runs/status/jobs/steps/logs/artifacts as project evidence;
- download Actions artifacts.

Reading/editing workflow source files as normal repository files is allowed when required by a source task.

GitHub remains expected for commits/PR review/source persistence. Verification runs locally or on another explicitly owner-approved environment.

---

## 3. Current high-level project state

### R0–R6

R0–R6 are **SOURCE-CLOSED** at their recorded source boundaries. Do not reopen the old v0.12 recovery incident or reconstruct superseded history without a concrete defect.

The formerly lost post-v0.12 R5 history/progression implementation was replaced by a **new reviewed R5 implementation**. Never describe it as historical recovery.

### R7

R7 is the active blocking architecture phase.

Current production implementation remains:

```text
installed graphics/session: Xorg + xinit compatibility
status:                     PROVISIONAL
production compositor:      none selected
serial direct DRM:          evidence candidate only
ActivitySupervisor DRM:     must not become DRM master
ordinary Activity raw input ownership: forbidden target direction
```

The real installed Activity lifecycle already uses the backend-neutral `DisplaySessionCoordinator` with an explicit `LegacyXDisplaySessionBackend`. This is the live ownership/recovery seam, **not** a completed direct-graphics migration.

Current X-compatible sandbox concessions such as shared IPC / display transport and broad graphics-device compatibility must not be removed blindly while installed production still uses Xorg.

---

## 4. Verification boundary — do not overclaim

Last complete source gate genuinely executed successfully:

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
compositor-package pure-logic fixture:       14 / 14 PASS
serial fake-SDL/process fixture:              8 / 8 PASS
```

The serial 8/8 result predates later strengthening of that evidence path; do not claim the strengthened suite executed from that result.

Everything newer that has not explicitly been run remains **UNPROVEN / committed but unexecuted**.

No current claim exists for:

- a newer complete `make verify` count;
- current launcher/display integration regressions;
- current R7 local-evidence tests;
- current developer-remote regressions;
- developer image construction;
- SSH/mDNS developer-target login;
- real screenshot capture;
- real remote keyboard/mouse/text input;
- real remote Activity deployment/trust behavior;
- reboot/reconnect acceptance;
- active KMSDRM QEMU PASS;
- serial KMSDRM QEMU handoff PASS;
- active seat/input PASS;
- physical Acer direct graphics/session PASS;
- Pi 400/500 physical acceptance.

The 2026-08-10 documentation audit ran **no source/unit/VM/hardware verification command** and changes none of these evidence boundaries.

---

## 5. Documentation deep review completed 2026-08-10

Review report:

```text
docs/reviews/2026-08-10_DOCUMENTATION_DEEP_REVIEW.md
```

Repository-wide documentation added/rewritten during the audit:

```text
docs/DOCUMENTATION.md
README.md
AGENTS.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
```

These long-lived documents were synchronized independently onto `main` as well as the active R7 branch so their governance/authoring guidance does not depend on PR #4 merging.

Key outcomes:

- README is now durable orientation, not a stale second handover;
- architecture overview is explicitly synthesis rather than a competing “constitution”;
- conceptual future YAML/Web/package examples are separated from current APIs;
- Activity skill now follows actual current parser/SDK/runtime declarations;
- operations manual now covers first connection, dedicated known-host handling and intentional reimage host-key rollover;
- hosted Actions prohibition now explicitly includes run/status/log/artifact queries;
- current test counts/SHAs belong here or in dated evidence, not in durable overview docs.

### Known documentation debt deliberately not rewritten

The active plan is append-only and some early phase-body status lines remain visually stale relative to later closure entries. Current state is this handover plus the latest progress log.

A future plan-format cleanup should add a current phase-status index near the top **without rewriting historical progress**. Do that during a real implementation-state plan update rather than manufacturing a documentation-only phase transition.

---

## 6. Current R7 display/session implementation

Existing R7 source includes:

```text
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_platform/direct_graphics_probe.py
src/greia_platform/kmsdrm_acceptance.py
src/greia_platform/kmsdrm_serial_handoff.py
tools/r7_compositor_package_probe.py
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
tools/r7_local_evidence.py
```

### Display session

`DisplaySessionCoordinator` owns typed Shell↔Activity session transitions/leases above backend-specific mechanics.

The installed launcher composes `LegacyXDisplaySessionBackend` today. ActivitySupervisor coordinates lifecycle timing but does not own DRM master semantics.

### Direct evidence candidates

R7 is comparing, from evidence rather than preference:

- serial direct SDL/KMSDRM Shell→Activity→Shell ownership;
- a minimal persistent Greia-owned compositor/session broker where justified;
- the current Xorg compatibility cost/behavior baseline.

No compositor is selected.

### Package candidate measurement

The fixed compositor/runtime candidates currently measured by the package probe are:

```text
cage
weston
wlroots-runtime
```

These are benchmark/reference candidates, not production dependencies.

---

## 7. Local R7 evidence execution

Exact protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

On an owner-controlled disposable/root-safe x86-64 Linux checkout:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"

python3 tools/r7_local_evidence.py \
  --run-root "$RUN_ROOT" \
  --plan-only

sudo -E python3 tools/r7_local_evidence.py \
  --run-root "$RUN_ROOT"
```

The protocol runs the current source gate, production image build, passive installed probe, exact package deltas and conditional active/serial QEMU evidence.

The **first failure is authoritative for that attempt**. Do not reuse the same run root or rerun active/serial evidence merely to manufacture PASS.

Active seat/input and physical Acer evidence remain separate requirements even if the local orchestrator completes.

---

## 8. Developer remote-control/test-console source

Detailed feature/security protocol:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

General agent/operator procedure:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

### Developer profile

```text
build/profiles/modern-amd64-dev.toml
```

Properties include:

```text
explicit experimental developer profile
installed hostname: greia-dev
expected mDNS:      greia-dev.local
current display:    Xorg compatibility
remote package set: developer-remote
```

Normal/release `modern-amd64` does not opt into the developer-remote path.

### Build

On compatible owner-controlled Linux:

```bash
sudo bash build/build-developer-image.sh out
```

Expected artifacts include:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

The private key is operator secret material and must never enter Git/shared evidence.

### SSH/security model

Developer target is designed for:

```text
user:                    greiaadmin
password auth:           disabled
keyboard-interactive:    disabled
root SSH:                disabled
operator auth:           public key
machine SSH host keys:   generated on actual machine
passwordless privilege:  bounded through /usr/local/sbin/greia-devctl
```

First acceptance should use wired Ethernet. No repository-stored Wi-Fi secret provisioning is implemented.

### Remote client

```text
tools/greia_remote.py
```

Current commands:

```text
wait
status
screenshot
logs
restart
restart-installer
key
mousemove
click
type
deploy
remove
restore
reboot
poweroff
shell
```

The client uses a dedicated:

```text
~/.greia/known_hosts
```

Intentional reimage host-key rollover procedure is documented in the operations manual. Do not globally disable SSH host-key checking.

---

## 9. Developer Activity trust boundary

This must not regress.

Built-in source:

```text
/opt/greia-os/activities
trust = BUILT_IN
```

Ordinary remote developer source:

```text
/var/lib/greia-developer/activities
trust = DEVELOPER_UNSIGNED
```

Normal remote deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

must not upgrade trust or permit privileged system permissions simply because the operator uploaded it.

Deliberate testing of an existing built-in requires explicit replacement:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
```

and the original must remain recoverable with:

```bash
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` as a shortcut around an ordinary developer validation/trust failure.

---

## 10. Live graphical installer remote-control boundary

Source exists:

```text
tools/provision_developer_installer.py
```

Intended live identity:

```text
hostname/mDNS: greia-installer-dev.local
display endpoint: root@:0
SSH: key-only greiaadmin
wired DHCP/mDNS: developer-only
```

The intended workflow is to remotely **drive the existing graphical fail-closed installer** while preserving:

- eligible-target discovery;
- removable-media exclusion;
- payload digest verification;
- target identity revalidation;
- explicit graphical confirmation.

### Current limitation

The live installer provisioner is **not yet wired into `build/build-installer-image.sh`**.

Therefore first-time remote USB installation is **not currently claimed operational**.

Do not replace this gap with a remote `dd`, unattended disk wipe or generic destructive root endpoint.

After the installed developer target is proven, add the two narrow canonical installer-builder hooks on a real Linux build/test path and then test remote graphical installation.

---

## 11. Current Activity authoring contract

Canonical skill:

```text
skills/greia-activity-authoring/SKILL.md
```

Important current implementation facts:

```text
development manifest: activity.toml
runtime:              Python/Pygame
runtime API:          0.1 (verify current runtime file before authoring)
package hard ceiling: 50 MiB
storage:              Greia brokered KV/private-file API
events:               Greia broker; 64 KiB encoded event-message ceiling
shared graphics:      semantic core icon catalogue + theme API
general widget kit:   NOT IMPLEMENTED
Web SDK/runtime:       future/deferred
.greiaactivity:        future package phase
.greiabackup:          future backup phase
```

Current exact implementation owners are listed in `docs/DOCUMENTATION.md` and the skill.

Do not turn conceptual YAML/Web examples from architecture into current code.

---

## 12. Exact next developer-remote acceptance step

On an owner-controlled Linux checkout at the actual current branch HEAD:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify

sudo bash build/build-developer-image.sh out
```

Then install/boot the developer target through an existing safe path, preferably with wired Ethernet for first acceptance.

From the operator computer:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/boot.png
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py logs --service launcher --lines 500
python3 tools/greia_remote.py deploy path/to/valid-test-activity
python3 tools/greia_remote.py screenshot out/activity.png
python3 tools/greia_remote.py reboot
python3 tools/greia_remote.py wait --timeout 180
```

Acceptance must prove, not assume:

- `greia-dev.local` reachable or explicit DHCP address used;
- public-key login succeeds;
- password/root SSH remain denied;
- machine host key is actual-machine generated;
- screenshot is real visible-screen PNG;
- bounded GUI input affects expected UI state;
- ordinary deployed Activity remains `DEVELOPER_UNSIGNED`;
- built-in collision/replacement policy behaves correctly;
- reboot/reconnect works;
- normal/release profile remains unaffected.

Preserve the first real failure rather than repeatedly modifying/retrying until it passes.

---

## 13. Exact next R7 graphics/evidence step

In parallel with developer-target acceptance, run the existing controlled local R7 evidence protocol once on the actual branch HEAD:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

Return/archive the complete run root.

Then, from evidence rather than preference:

1. inspect exact installed SDL/direct capability;
2. inspect Cage/Weston/wlroots package/file deltas;
3. inspect active/serial QEMU result where KMSDRM is compiled;
4. obtain active seat/input evidence;
5. compare serial ownership vs the smallest justified compositor/session-broker prototype vs Xorg resource/authority behavior;
6. require physical legacy Intel/Acer scanout/input/suspend/crash acceptance before migrating production;
7. leave Pi physical display evidence to R8/R14 after the Pi image/board adapter exists.

No compositor should be selected before that evidence exists.

---

## 14. Product/security invariants to preserve

- no visible Linux UI in normal child operation;
- one Greia profile explicitly selected at boot;
- Activity is runtime-neutral;
- Activities do not own global progression/reward economics;
- portable profile/Activity data stays architecture-neutral;
- per-Activity durable isolation/trust boundaries stay fail-closed;
- developer remote access never silently appears in normal/release images;
- remote file placement never upgrades package trust;
- current X11 compatibility must not deepen into an Activity API;
- ActivitySupervisor must not become DRM master;
- destructive installation remains graphical and device/payload revalidated;
- no private credentials/keys in Git;
- no unapproved hosted Actions execution/query surface.

---

## 15. Continuity files

Primary current files:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
HANDOVER.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
docs/reviews/2026-08-10_DOCUMENTATION_DEEP_REVIEW.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

Before ending the next substantive implementation tranche:

- commit coherent work;
- append active-plan progress if implementation/phase state changed;
- update this handover;
- update the operations manual or Activity skill when their source contracts changed;
- record exactly what verification actually ran;
- preserve remaining VM/physical evidence gaps;
- state the next exact legitimate step.
