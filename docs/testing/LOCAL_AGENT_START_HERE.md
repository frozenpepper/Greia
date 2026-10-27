# Greia — Local Agent / Operator: Start Here

**Status:** LIVING routing document  
**Reviewed:** 2026-09-08  
**Branch policy:** current `main`  
**Repository:** `frozenpepper/Greia`

This file is a router, not a frozen test plan.

Greia has many dated acceptance procedures because evidence is intentionally tied to an exact source state and subsystem. A dated procedure does **not** remain the current global test plan merely because it still exists.

## 1. Resolve current authority first

Before running or changing anything:

```text
1. AGENTS.md
2. HANDOVER.md
3. docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md for lifecycle
   OR docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md for other architecture work
4. skills/greia-os-work/SKILL.md for OS/platform work
   OR skills/greia-activity-authoring/SKILL.md for Activity work
5. the exact testing procedure(s) named by HANDOVER.md / the active plan
```

Before installing/configuring dependencies, also read:

```text
SETUP.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

The current handover owns the **current exact evidence boundary and next legitimate gate**. Do not infer the current gate from the newest-looking filename, a stale result document, or an old phase number.

## Current owner-authorized product/source testing queue

Use [`GREIA_LOCAL_AGENT_TASK_QUEUE.md`](./GREIA_LOCAL_AGENT_TASK_QUEUE.md)
for the postponed Time/visual/gallery/Creations acceptance work.
The owner authorizes **queue-only** evidence/status commits to `main`,
not source edits or hardware access. The queue does not supersede
the exact dated Creations acceptance or the independent installer
and first-boot lifecycle authorization.

## 2. Current install/update/release route

The September lifecycle plan remains the architectural authority; Session 04
is OPEN pending installed evidence. **For the owner's current update repair and
release-acceptance assignment, execute only the consolidated
[Greia update release acceptance](GREIA_UPDATE_RELEASE_ACCEPTANCE.md) as the
top-level work order.** It covers both A/B full-system and typed
`.greia_update` application packages in one coherent Linux/QEMU campaign.
Older dated procedures (especially
[2026-10-23 A/B](2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md) and
[2026-10-24 application](2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md)) provide
details and historical evidence; they are **not additional prerequisites or
source-freeze/stop-after-one-stage gates**.

The owner expressly authorizes this local agent to implement fixes and tests,
build disposable fixtures, run installed update acceptance and commit coherent
changes on `main`. The [delayed local testing queue](GREIA_LOCAL_AGENT_TASK_QUEUE.md)
retains its *separate* evidence-only restriction for Time/Creations and other
queued tasks; that restriction does **not** apply to this update assignment.

Keep measured A/B versus application acceptance distinct, and never target an
actual family disk or data. Don't rerun the frozen 1275-era single-stage job:
its refusal is captured in
[the diagnostic result](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md).
Old POSTR1-P1/Gate-P5 sequencing does not supersede Session 04. The
architecture-remediation plan remains active for non-lifecycle obligations.

Do not automatically run an old R7 closure procedure merely because it remains under `docs/testing/`. Use `HANDOVER.md` and the active plan to choose the exact gate for the work being accepted.

For the owner-approved simple Parents HTTPS implementation, use the current focused acceptance procedure:

```text
docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md
```

The older `docs/testing/2026-09-08_PARENT_UNIFIED_AUTH_RUNTIME_ACCEPTANCE.md` retains the September baseline for the existing password/per-device authentication behavior; its frozen client revision and provisional HTTP instructions must **not** be used as the current HTTPS acceptance authority.

Other subsystem procedures remain active when their owning workstream is being closed, including:

```text
docs/testing/2026-09-04_CHILD_ACTIVITY_POLICY_FAIL_CLOSED_ACCEPTANCE.md
docs/testing/2026-09-03_ACTIVITY_AGE_POLICY_ACCEPTANCE.md
docs/testing/2026-09-02_R7_FINAL_EVIDENCE_GAP_CLOSURE.md
```

Finished one-off procedures from August–September 2026 were deleted or moved to `docs/archive/` (see `docs/archive/README.md`).

Always re-read `HANDOVER.md` immediately before execution. Source may have advanced after an earlier physical or image candidate; old evidence stays scoped to the exact SHA that produced it.

## 3. Dated procedures are scope-specific evidence contracts

Older protocols under `docs/testing/` remain useful when the current handover/plan explicitly names them or when investigating their historical subsystem.

Do **not** run every dated test document as one giant ritual. Select the current gate from the handover and expand only where that gate tells you to.

If two procedures conflict, use the newer procedure only where it explicitly supersedes the older one. Preserve still-valid wider checks rather than silently discarding them.

## 4. Agent role

A coding/test agent is expected to:

- inspect the first real failure rather than weakening the test;
- fix genuine source/build/runtime defects at their owning layer;
- add focused regression coverage for the root cause;
- preserve Greia trust, lifecycle, resource and evidence boundaries;
- work on current `main` and preserve concurrent changes;
- rerun the smallest affected gate, then the required broader gate;
- keep source/browser/simulator/VM/physical/provider evidence clearly separated;
- update the active plan/HANDOVER when implementation or continuation state materially changes.

Never obtain a PASS by:

- moving trusted Home/Back into Activities;
- granting ordinary Activities raw `/dev/input` or `/dev/dri`;
- exposing a Linux shell/desktop path to children;
- bypassing PermissionBroker/lifecycle/package authority;
- hard-coding one Acer resolution/device into shared semantics;
- converting a Simulator result into a physical-backend claim;
- deleting or suppressing useful failure evidence;
- extending timeouts without evidence that the operation is legitimately slow;
- weakening the Parent service sandbox merely to advertise a capability that current authority cannot actually complete;
- reintroducing the retired Parent shared pairing token to make browser authentication easier.

## 5. Baseline source verification

The canonical repository-wide source gate remains:

```bash
make verify
```

Run it on the **exact current checkout** when the active procedure requires the full source gate.

Do not copy a PASS count from this document, an old review or another SHA. Test counts evolve; the retained evidence record owns the count that actually ran.

Subsystem gates come from the current named procedure or task router. Where required, current strict Activity audits are:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Use exact expected summaries from the current procedure rather than inventing a count.

## 6. Evidence storage and result reporting

Bulky screenshots, logs, captures, generated images and machine evidence belong in the procedure's `tmp/`/external evidence root, not permanently at repository root.

Do **not** maintain a growing root `LOCAL_AGENT_RESULT.md` accumulator.

For retained work:

- detailed dated analysis/evidence -> `docs/reviews/` when it merits repository preservation;
- append-only phase history -> active plan when implementation/phase state changed;
- short current continuation/evidence boundary -> `HANDOVER.md`;
- raw/bulky evidence -> outside Git unless a specific authority says otherwise.

A final report should record at least:

```text
exact Greia SHA
exact Parent-App revision when relevant
commands/procedure sections actually executed
evidence class (source / browser / simulator / VM-image / physical)
PASS/FAIL/INCOMPLETE
first failing invariant when not PASS
what remains unverified
```

## 7. Parent App

The exact accepted Parent client revision currently integrated into Greia is owned by:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

At the September 8 cutover the pin is:

```text
01301d285c6ba2a9a1f2948a9768b821d2536729
```

Do not test moving Parent `main` when an acceptance procedure calls for the frozen revision.

Current authentication semantics are:

```text
Greia Parent password
  -> /api/v1/pairing/bootstrap
  -> per-device credential
  -> ordinary Bearer-authenticated API calls
```

The browser stores the issued device credential, not the Parent password. The retired shared `parent-pairing-token`, `X-Pip-Token`, token query URL and household-wide bearer fallback are not production authentication mechanisms.

If Parent client source changes, update its own repository first, then repin Greia with exact revision/integrity metadata, vendor bytes and image-overlay bytes together. Do not invent an SSH/shell fallback for a missing Parent API capability.

The installed Greia Parent server remains unprivileged. If `network.manage` is false because direct iwd mutation is unavailable under the service sandbox, preserve that fail-closed truth; privileged mutation belongs behind the narrow typed broker described by the Parent architecture.

## 8. Physical/developer-device work

For owner-authorized developer hardware, use:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

and the exact named physical procedure.

General rules:

- record the deployed SHA;
- deploy one coherent tree/image, not hand-copied source fragments;
- inspect screenshots when visual state matters;
- prove semantic Activity/process identity where the procedure requires it;
- retain the first failure;
- restore temporary Parent/test policy exactly;
- do not use physical navigation coordinates as proof that the intended Activity actually launched;
- do not destroy live Parent credential/password state when a disposable/fresh-state lane is required.

## 9. GitHub-hosted execution

GitHub-hosted Actions are opt-in only. Do not trigger, rerun, query or download hosted workflow execution/evidence unless the owner explicitly authorizes that specific use.

Reading workflow source as repository code is allowed when relevant.

## 10. Maintenance rule

Whenever a newer procedure supersedes the current global or subsystem gate:

1. update `HANDOVER.md`;
2. update this router only if the routing rule or named current gate changed;
3. leave older dated procedures intact as historical evidence unless a dangerous stale instruction needs an explicit supersession notice;
4. never freeze current PASS counts in this router.
