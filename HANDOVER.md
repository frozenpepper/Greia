# Greia — Standalone Engineering Handover

**Date:** 2026-08-10  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume order

Read before substantive work:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. accepted ADRs relevant to the task, especially ADR 0012–0017;
6. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
7. this `HANDOVER.md`;
8. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
9. `skills/greia-activity-authoring/SKILL.md` for Activity work;
10. the exact R7/testing/review docs named below.

GitHub is canonical. Resolve the actual branch HEAD before editing/testing.

`docs/DOCUMENTATION.md` defines ownership:

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

---

## 2. Critical hosted-execution rule

**Do not use the GitHub Actions execution service without explicit repository-owner authorization for that specific use.**

Without authorization do not:

- trigger/rerun/dispatch hosted workflows;
- add automatic hosted triggers;
- query Actions runs/status/jobs/steps/logs/artifacts as evidence;
- download Actions artifacts.

Reading/editing workflow source as ordinary repository source is allowed when needed. GitHub remains expected for commits/PR review/source persistence.

---

## 3. Current project state

### R0–R6

R0–R6 are **SOURCE-CLOSED** at their recorded source boundaries. Do not reopen the old v0.12 recovery incident without a concrete defect.

The formerly lost post-v0.12 R5 history/progression authority was replaced by a **new reviewed R5 implementation**. Do not describe it as historical recovery.

### R7

R7 is the active blocking phase.

```text
installed production graphics/session: Xorg + xinit compatibility
status:                                PROVISIONAL
production compositor:                 none selected
serial direct DRM ownership:           evidence candidate only
ActivitySupervisor DRM master:         forbidden
ordinary Activity raw input ownership: forbidden target direction
```

The installed Activity lifecycle already uses backend-neutral `DisplaySessionCoordinator` plus `LegacyXDisplaySessionBackend`. This is a real ownership/recovery seam, **not** a completed direct-graphics migration.

Current X-compatible sandbox concessions must not be removed blindly while installed production still uses Xorg.

---

## 4. Verification boundary — do not overclaim

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Focused checks genuinely executed earlier:

```text
DisplaySessionCoordinator isolated fixture: 22 / 22 PASS
compositor-package pure-logic fixture:       14 / 14 PASS
serial fake-SDL/process fixture:              8 / 8 PASS
```

The serial 8/8 result predates later strengthening of that evidence path.

Everything newer that has not explicitly executed remains **UNPROVEN / committed but unexecuted**. No current claim exists for:

- newer complete `make verify`;
- current launcher/display integration regressions;
- current R7 local-evidence tests;
- developer-remote regressions;
- developer image build;
- SSH/mDNS login;
- screenshot/input/deployment/reboot hardware acceptance;
- active KMSDRM QEMU;
- serial KMSDRM QEMU handoff;
- active seat/input;
- physical Acer direct graphics/session;
- Pi 400/500 physical acceptance.

The 2026-08-10 documentation audit executed **no source/unit/VM/hardware verification command** and changes none of these evidence boundaries.

---

## 5. Documentation deep review completed 2026-08-10

Review:

```text
docs/reviews/2026-08-10_DOCUMENTATION_DEEP_REVIEW.md
```

Audited/improved on `r7-direct-graphics`:

```text
docs/DOCUMENTATION.md
README.md
AGENTS.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
HANDOVER.md
```

Key outcomes:

- explicit documentation ownership/precedence/freshness model;
- README is durable orientation instead of a stale second handover;
- architecture overview no longer competes with ADR 0012 as a “constitution”;
- future YAML/Web/package examples are labelled conceptual;
- Activity skill is grounded in current parser/SDK/runtime source;
- agent operations includes first connection, known-host and intentional-reimage procedure;
- hosted Actions prohibition explicitly covers run/status/log/artifact queries;
- current test counts/SHAs belong here or in dated evidence.

### Integration/reconciliation history

The audit versions were briefly committed independently to both `main` and R7. GitHub then reported a merge conflict caused by the independent histories, even where file contents matched.

This was resolved without force pushes and without weakening the workflow policy:

1. duplicate **audit-only** main tree changes were explicitly reverted in `main` commit `06590b484e091617cc96583fb9291034509b7990`;
2. the improved audit versions remained on `r7-direct-graphics`;
3. merge commit `ea5c68953c73571a5d2ab5f73f0638428c7b25c8` incorporated current `main` history into the R7 branch while retaining the newer R7 tree as the explicit conflict resolution;
4. temporary sync PR #5 was closed unmerged;
5. PR #4 returned to **mergeable=true**.

Therefore the **audited documentation versions currently live on the active R7 branch / PR #4**. `main` retains its pre-audit documentation versions until PR #4 or a later deliberate documentation integration brings the reviewed versions across.

### Remaining documentation debt

The active plan is intentionally append-only; some early phase-body status lines remain visually stale relative to later closure entries. Current state is this handover plus latest progress entries.

When the plan next receives a real implementation-state update, add a small current phase-status index near the top without rewriting historical progress.

---

## 6. Current R7 source/evidence primitives

Relevant source/tools:

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

R7 is evidence-comparing:

- serial direct SDL/KMSDRM Shell→Activity→Shell ownership;
- the smallest justified persistent Greia compositor/session broker;
- current Xorg compatibility resource/authority behavior.

Fixed package/reference candidates currently include:

```text
cage
weston
wlroots-runtime
```

They are benchmark candidates, not selected production dependencies.

---

## 7. Local R7 evidence execution

Exact protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

On owner-controlled disposable/root-safe x86-64 Linux:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"

python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

First failure is authoritative for the attempt. Do not reuse the run root or repeat active/serial evidence merely to manufacture PASS.

Active seat/input and physical Acer evidence remain separate requirements.

---

## 8. Developer remote-control/test console

Feature/security protocol:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

General operator procedure:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
hostname/mDNS: greia-dev / greia-dev.local
status: experimental developer-only
current display: Xorg compatibility
```

Build on compatible owner-controlled Linux:

```bash
sudo bash build/build-developer-image.sh out
```

Expected artifacts:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

Private key is operator secret material and must never enter Git/shared evidence.

SSH model:

```text
user:                    greiaadmin
password auth:           disabled
keyboard-interactive:    disabled
root SSH:                disabled
operator auth:           public key
machine SSH host keys:   generated on actual machine
passwordless privilege:  bounded through /usr/local/sbin/greia-devctl
```

Use wired Ethernet for first acceptance. No repository-stored Wi-Fi secret provisioning is implemented.

Remote client:

```text
tools/greia_remote.py
```

Commands:

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

Dedicated known-hosts file:

```text
~/.greia/known_hosts
```

Intentional reimage host-key rollover is documented in the operations manual; do not disable host-key verification globally.

---

## 9. Developer Activity trust boundary

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

Normal deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

must not upgrade trust or grant privileged system permissions merely because an operator uploaded it.

Explicit built-in test replacement only:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` to bypass ordinary validation/trust failures.

---

## 10. Live graphical installer remote boundary

Source exists:

```text
tools/provision_developer_installer.py
```

Intended live identity:

```text
hostname/mDNS:    greia-installer-dev.local
display endpoint: root@:0
SSH:              key-only greiaadmin
wired DHCP/mDNS:  developer-only
```

The operator must remotely drive the **existing graphical fail-closed installer**, preserving:

- eligible-target discovery;
- removable-media exclusion;
- payload digest verification;
- target identity revalidation;
- explicit graphical confirmation.

### Current limitation

The live provisioner is **not yet wired into `build/build-installer-image.sh`**.

First-time remote USB installation is therefore **not claimed operational**.

Never substitute a remote `dd`, unattended disk wipe or generic destructive root endpoint.

---

## 11. Current Activity authoring snapshot

Canonical skill:

```text
skills/greia-activity-authoring/SKILL.md
```

Current implementation facts:

```text
development manifest: activity.toml
runtime:              Python/Pygame
runtime API:          0.1 (verify current runtime source before authoring)
package hard ceiling: 50 MiB
storage:              brokered Greia KV/private-file API
events:               Greia broker; 64 KiB encoded event-message ceiling
shared graphics:      semantic core icon catalogue + theme API
general widget kit:   NOT IMPLEMENTED
Web SDK/runtime:       future/deferred
.greiaactivity:        future package phase
.greiabackup:          future backup phase
```

Do not turn conceptual architecture examples into current APIs without checking source/runtime owners.

---

## 12. Exact next developer-remote acceptance step

On owner-controlled Linux at actual branch HEAD:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify
sudo bash build/build-developer-image.sh out
```

Then install/boot through an existing safe path with wired Ethernet first.

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

Acceptance must prove:

- connectivity;
- key-only login and password/root denial;
- real machine-generated host identity;
- real display screenshot;
- bounded input changes expected UI;
- ordinary deployment remains `DEVELOPER_UNSIGNED`;
- built-in collision/replacement/restore semantics;
- reboot/reconnect;
- normal/release profile remains unaffected.

Preserve first real failures.

---

## 13. Exact next R7 graphics/evidence step

In parallel, run the local R7 evidence protocol once at actual branch HEAD:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

Then, from evidence:

1. inspect installed SDL/direct capability;
2. inspect Cage/Weston/wlroots package deltas;
3. inspect active/serial QEMU where applicable;
4. obtain active seat/input evidence;
5. compare serial vs minimal compositor/session broker vs Xorg resource/authority behavior;
6. require physical legacy Intel/Acer scanout/input/suspend/crash acceptance before production migration;
7. defer Pi physical display acceptance to R8/R14 after Pi image/board adapters exist.

No compositor should be selected before evidence supports it.

---

## 14. Invariants to preserve

- no visible Linux UI in normal child operation;
- explicit Greia profile selection;
- Activity remains runtime-neutral;
- global progression/reward economics remain platform-owned;
- durable child state remains architecture-neutral;
- per-Activity isolation/trust stays fail-closed;
- developer remote access never appears implicitly in release images;
- remote placement never upgrades Activity trust;
- X11 compatibility does not become Activity API;
- ActivitySupervisor never becomes DRM master;
- destructive installation remains graphical/device/payload revalidated;
- no private credentials in Git;
- no unapproved hosted Actions execution/query surface.

---

## 15. Continuity files

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

After the next substantive implementation tranche:

- commit coherent work;
- append plan progress if implementation/phase state changed;
- update this handover;
- update operations/Activity skill when their source contracts changed;
- record exactly what verification ran;
- preserve VM/physical gaps;
- state the next exact legitimate step.
