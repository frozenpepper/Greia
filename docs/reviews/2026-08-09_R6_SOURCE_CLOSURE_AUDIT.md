# Greia R6 source-closure audit — 2026-08-09

**Audited clean checkout:** `cd317a862b12ba6e85971bf23d0146a108c5faef`  
**R6.2 implementation milestone:** `94f93941db32a91e77c8af09f0eab4bb7c28bc07`  
**Permanent CI run:** `31282265661` / job `93165386464`  
**Result:** **R6.2 SOURCE ARCHITECTURE PASS; R6 OVERALL NOT CLOSED**  
**Recoverable provider-free suite:** **172/172 PASS**

## Scope

This audit checks the R6 source architecture against ADR 0012, ADR 0014, ADR 0015 and the R6/R6.2 criteria in the active remediation plan. It deliberately separates source-architecture closure from the lost post-v0.12 R5 authority and from hardware-only evidence.

The evidence is not an already-populated local workspace. It comes from the permanent GitHub clean-checkout verifier after the R6 architecture assertions were added to that standing gate.

## R6.1 device/HAL boundary

PASS at source level:

- typed display/input/audio/removable/network/power HAL protocols exist below `GreiaHAL`;
- `DeviceCapabilityService` is the semantic hardware truth exposed upward;
- the installed launcher composition creates one HAL-backed Device Capability Service and injects that same object into PermissionBroker and RuntimeManager;
- Activity manifest/environment strings cannot become hardware authority;
- ActivityAuthority records the device-snapshot token used for capability/permission issuance;
- RuntimeManager launch preparation must use the same semantic device snapshot and fails closed on mismatch;
- legacy X display/input remains explicitly a provisional HAL backend, not an interface-level dependency.

Physical Acer/Pi/direct-graphics behavior is **not** claimed by this source audit.

## R6.2 Runtime Adapter contract

PASS at source level:

1. Activity Registry remains runtime-neutral and owns shared package facts only.
2. Python static/package validation lives behind `PythonRuntimeAdapter`.
3. RuntimeManager owns runtime lookup and compatibility against trusted semantic device capability.
4. Permission authority and runtime compatibility are bound to one semantic device observation.
5. `RuntimeCommand` owns runtime-specific command, package-bounded cwd and bounded runtime environment; Python-only process policy is not in Supervisor.
6. RuntimeManager validates runtime command/cwd/environment before launch and prevents runtime adapters from overwriting Greia/platform authority variables.
7. Runtime adapters own final runtime-handle creation through `RuntimeInvocation`.
8. Runtime adapters own exit collection/normalization, force-stop and runtime-handle cleanup.
9. Platform session identity is allocated independently of runtime transport.
10. Runtime adapters own lifecycle transport through `RuntimeLifecycleBinding`; Python owns its READY/STOP marker implementation.
11. Invalid lifecycle bindings cannot replace platform session identity and are cleaned before failure is propagated.
12. Supervisor contains no Python marker paths, no concrete `ActivityControlChannel`, no direct `Popen`, and no process-group signaling.
13. R4 Universal Storage is shared platform authority: installed composition loads the storage policy/service; Supervisor opens the durable Activity namespace, exposes only broker socket/token, mounts only the ephemeral broker root into Bubblewrap, and tears the broker down with the session.
14. A storage-broker cleanup failure becomes `platform_failure` rather than silently reporting a clean Activity exit.

This is the intended polymorphic seam for future Web/native runtime adapters: they replace runtime validation, runtime-specific environment/cwd, lifecycle transport and runtime-handle behavior without forking Greia identity, permission, device, storage, session or progression policy.

## Executable clean-checkout evidence

Permanent CI at `cd317a862b12ba6e85971bf23d0146a108c5faef` proved:

```text
repository checkout: PASS
Python compile: PASS
R6 typed HAL/device authority assertions: PASS
installed shared composition assertions: PASS
snapshot-coherence assertions: PASS
Universal Storage launch-transport assertions: PASS
runtime-command/session/lifecycle adapter-ownership assertions: PASS
Supervisor runtime-neutrality assertions: PASS
provider-free unit suite: 172/172 PASS
```

The same clean checkout then ran full `make verify`. It completed the entire 172-test unit suite successfully and stopped in `tools/validate_project.py` solely because:

```text
ModuleNotFoundError: No module named 'greia_platform.history'
```

No recoverable unit-test failure precedes that boundary.

## Why R6 is still not closed

This audit does **not** override R0 continuity rules. The post-v0.12 R5 source `src/greia_platform/history.py` and its associated historical test source were never persisted and cannot currently be recovered. That missing authority prevents:

- full clean-clone `make verify` PASS;
- honest restoration of R5 History/Progression policy implementation;
- wiring/verification of the surviving R5 event broker against its real History/Progression authority;
- a repository-complete proof that R1–R6 are mutually coherent as an integrated stack.

Therefore:

```text
R6.1 source architecture: PASS
R6.1 physical-hardware evidence: not claimed here
R6.2 source architecture: PASS
R6 overall phase closure: BLOCKED by R0/R5 source continuity
R7: MUST NOT START
```

## Required decision to move forward

The exact historical R5 source has been exhaustively searched and is unavailable. Continuing now requires an explicit project decision to treat R5 History/Progression as a **new reviewed reimplementation from accepted ADR 0017 plus the surviving R5 policy/protocol/broker contracts**, not as recovered source.

If authorized, that reimplementation must be separately reviewed and tested, restore the event/session/progression integration behind the existing platform-owned boundaries, and then run the complete clean-clone gate. R6 overall can only be re-audited for closure after that succeeds.
