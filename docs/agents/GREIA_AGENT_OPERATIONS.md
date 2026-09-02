# Greia Agent Operations Manual

**Audience:** coding, review and test agents working on Greia OS  
**Status:** LIVING mandatory derived operating manual  
**Reviewed:** 2026-09-02  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`

This is an operating router, not an architecture or evidence archive. Exact current state belongs in `HANDOVER.md`; exact procedures belong in `docs/testing/*`; accepted architecture belongs in ADRs; exact implemented contracts belong in source/runtime declarations.

---

## 1. Mandatory start

Before substantive work:

1. read `AGENTS.md`;
2. read `README.md` and `docs/DOCUMENTATION.md`;
3. read the active blocking plan;
4. read `HANDOVER.md`;
5. read `skills/greia-os-work/SKILL.md` for OS/platform work or the applicable narrower skill;
6. read the task-specific ADR/product/source owners named by those routers;
7. resolve the actual current `main` HEAD before writing;
8. classify the evidence lane the task can genuinely exercise.

Before installing/configuring any Greia toolchain, image builder, Simulator dependency, Parent client, voice backend or developer-remote environment, read `SETUP.md`.

Current test/evidence routing starts at:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

That router follows `HANDOVER.md`. Do not select a dated procedure merely because its filename looks newer or familiar.

---

## 2. Repository and concurrent-work discipline

Repository-wide branch policy is owned by `AGENTS.md`:

- work directly on `main` by default;
- do not create a feature/review/safety/temporary branch unless the owner explicitly asks;
- refresh current `main` before substantive writes;
- preserve concurrent owner/agent work;
- never resolve divergence by resetting, deleting, stashing or cleaning unknown work;
- commit coherent work to canonical GitHub;
- keep generated images, caches, private keys and bulky evidence outside Git unless an authority explicitly requires them.

GitHub is persistent source truth. Chat summaries are navigation hints only.

For any retained test attempt record the exact source SHA. “Latest” and branch names are not evidence identities.

---

## 3. Hosted execution is opt-in only

Without explicit owner authorization for that specific use, do **not** use GitHub Actions as execution/evidence infrastructure.

Do not:

- trigger or rerun workflows;
- dispatch manual workflows;
- add automatic hosted triggers merely to run tests;
- query hosted runs/jobs/logs/artifacts as project evidence;
- download hosted artifacts.

Reading/editing workflow source as ordinary repository source is allowed when the task genuinely concerns it.

A request to “move forward”, “test” or “verify” is not hosted-compute authorization.

---

## 4. Evidence vocabulary

Keep these lanes separate:

```text
SOURCE
AUTHORING PROVIDER + HUMAN REVIEW
SIMULATOR
VM / IMAGE
PHYSICAL DEVICE
```

### SOURCE

Examples:

```text
unit/contract tests
make verify
project/Activity validation
static ownership audits
shell syntax
source footprint
```

Source evidence proves only the tested source contracts.

### AUTHORING PROVIDER + HUMAN REVIEW

Generated voice/art receipts, model success or machine verification prove production provenance/process only. Where Greia requires human listening/visual acceptance, provider success does not substitute for it.

### SIMULATOR

The Activity Simulator exercises substantial real Greia launcher/runtime/profile/storage/lifecycle semantics with synthetic device facts. It does **not** prove production display/session/input authority, Bubblewrap/kernel containment, physical hardware, Acer performance or boot/install behavior.

### VM / IMAGE

Image build/QEMU evidence proves the exact image/VM path exercised. It does not certify Acer/Pi physical behavior unless the named acceptance protocol explicitly says so.

### PHYSICAL DEVICE

Physical claims must name the tested machine/class, exact source/image identity and relevant hardware/runtime facts.

A PASS at SHA A does not certify runtime-affecting source at SHA B.

---

## 5. Current R7 boundary

R7 remains the blocking platform phase until `HANDOVER.md` and the active plan say otherwise.

Do not deepen provisional X11 coupling merely because the installed compatibility path currently uses Xorg/xinit.

Preserve:

- platform-owned Home/Back;
- `DisplaySessionCoordinator` display-session authority;
- `SystemChromeCoordinator` navigation authority;
- `TrustedChromeActivitySupervisor` lifecycle binding;
- runtime-neutral physical input semantics;
- direct safe SDL/Pygame Activity rendering/input hot paths;
- no ordinary Activity raw `/dev/input` or `/dev/dri` authority;
- no avoidable full-frame IPC/copy architecture;
- no Simulator-to-production evidence promotion.

For current R7 work, read the exact procedure named by `HANDOVER.md`. Historical R7/Linux procedures remain useful context only where the current router names them.

Do **not** advance a later R7 subphase while the active plan/handover says an earlier physical authority gate remains blocking.

---

## 6. Simulator work

Before Simulator implementation/testing read:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
HANDOVER.md
```

Rules:

- Simulator uses real Greia semantic/runtime services where defined by ADR 0029;
- do not create a second platform implementation inside Simulator code;
- do not make Activities branch on Simulator identity;
- synthetic device facts must remain visibly synthetic;
- protected remote/headless Home must use platform system-chrome/lifecycle authority, not Activity cooperation;
- screenshots that matter must actually be inspected or marked `NOT_REVIEWED`.

A Simulator PASS never closes production trusted-chrome, production graphics/input, Acer or Pi evidence.

---

## 7. Developer remote-control boundary

Remote control exists only for explicit developer/test images.

Canonical operator client:

```text
tools/greia_remote.py
```

Canonical detailed procedure:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Normal/release Greia must not expose developer SSH/remote-control merely because this tooling exists in source.

Use the stable Greia operator surface rather than scripting private X11/systemd/filesystem details when a supported command exists. Typical operations include:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
python3 tools/greia_remote.py key Return
python3 tools/greia_remote.py mousemove 500 300
python3 tools/greia_remote.py click
python3 tools/greia_remote.py type "test"
python3 tools/greia_remote.py logs --service launcher --lines 500
python3 tools/greia_remote.py restart
python3 tools/greia_remote.py reboot
```

Developer credentials, private keys and Wi-Fi secrets are operator material. Never commit them or include them in shareable evidence.

Do not disable host-key verification to make a reimaged machine convenient. Reconcile a changed host key only after confirming intentional reimage/replacement.

---

## 8. Acer and physical acceptance

The first-generation Acer Aspire One remains the extreme low-resource reference until inventory evidence replaces the current floor assumptions. Raspberry Pi 400/500 remain co-equal ARM references for their assigned phases.

For a physical gate:

1. use the exact procedure named by `HANDOVER.md`;
2. freeze the source candidate before deployment;
3. record `HEAD`, `origin/main`, worktree state and evidence root;
4. do not pull during a frozen run;
5. use canonical deployment/remote tooling without local timeout/source patches;
6. preserve the first genuine failure;
7. do not add later successful cycles to replace a failed numbered cycle;
8. do not convert remote coordinate injection into “physical input” evidence;
9. do not use a scripted click as evidence for sustained high-rate Painting input;
10. do not claim current physical acceptance when the exact tested source differs materially.

If the target is unreachable, return the completed source/Simulator evidence and classify the physical lane `INCOMPLETE`. Do not invent a substitute.

---

## 9. Failure-preservation rules

When a gate fails:

- stop at the first failure when the named procedure says to stop;
- retain exact command, exit code, relevant stdout/stderr/logs/screenshots and source SHA;
- distinguish product failure from evidence/tooling failure;
- do not lengthen timeouts as the first response to a semantic/lifecycle failure;
- do not patch the hostile fixture into cooperation;
- do not weaken a security/authority/performance invariant to make the gate green;
- do not silently rerun until a transient-looking failure disappears;
- do not modify source inside a frozen physical acceptance and then continue calling the evidence same-candidate.

A clean `INCOMPLETE` is better evidence than a manufactured PASS.

---

## 10. Local-agent instruction standard

When delegating local/hardware testing, instructions must include:

```text
prerequisites
exact repository/branch/source freeze
exact commands
expected outputs
hard stop conditions
prohibited actions
evidence directory
what evidence to return
what to do if a command fails
final report schema/verdict vocabulary
```

Additional defaults:

- no GitHub Actions unless explicitly authorized;
- no ZIP unless requested;
- no filesystem-root `/tmp`; use project-local `./tmp/...`;
- preserve owner work;
- no destructive reset/stash/clean;
- hard stops should protect source integrity, safety or evidence validity—not create unnecessary ceremony.

---

## 11. Activity work

For Activity implementation/testing, route through:

```text
skills/greia-activity-authoring/SKILL.md
```

OS/platform agents should not duplicate Activity authoring rules here.

Key platform boundaries still apply:

- Activities do not own real system Home/Back;
- Activities remain backend-neutral;
- Activities do not gain raw device authority to simplify input;
- package/storage/progression/permission contracts remain platform-owned;
- low-resource performance is a correctness requirement.

---

## 12. Build / installer / boot work

Before image/build/installer changes read:

```text
SETUP.md
skills/greia-os-work/BOOT.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
```

Then read the task-specific ADR/product documents named by `skills/greia-os-work/SKILL.md`.

Do not perform destructive physical installation from memory. The exact named procedure must permit it and revalidate target identity before destructive work.

Developer-image convenience must not leak into normal/release profiles.

---

## 13. Source verification defaults

Use the narrowest meaningful gate first, then the broader phase gate required by the current procedure.

Repository unittest discovery is preferred where a third-party `tests` package could shadow the repository namespace:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p '<filename>' -v
```

Current common architecture audits include:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Broad source gate:

```bash
make verify
```

Do not add brittle source-string tests merely because implementation text changed. Test real ownership, lifecycle, trust, policy, state, failure and performance contracts.

---

## 14. End-of-turn handoff

Before calling substantive work complete, record:

```text
exact source SHA changed/tested
authorities read
what changed
verification actually executed
which evidence lane was exercised
what remains unverified
first blocker / next exact legitimate step
whether concurrent main advanced
```

Update the active plan, `HANDOVER.md`, manuals/skills and product/ADR docs only where `AGENTS.md` requires them for the kind of work performed.

Do not rewrite dated historical evidence to make it agree with current source. Append corrections or update the living owner instead.
