# Input/Controller Foundation — Adversarial Review

**Date:** 2026-08-15  
**Scope:** ADR 0020 source tranche before execution/physical evidence  
**Status:** REVIEWED SOURCE DESIGN; runtime evidence remains UNPROVEN

## Summary

The Phase-0 input/controller foundation is directionally sound: interaction intent is separated from physical devices, standard mappings are centralized, controller brands/raw indices are kept below the portable contract, text input is protected from game mappings, virtual-pointer behavior is centralized, controller handles are bounded, and ordinary Activities are not granted raw `/dev/input` merely for controller support.

The review found several integration risks and one important capability nuance. The source was tightened where possible and the remaining runtime/evidence obligations are recorded explicitly rather than hidden.

## Finding 1 — keyboard double handling in Shell wrapper — FIXED IN SOURCE

`PygameInputTranslator` intentionally translates both keyboard and controller events. A Shell wrapper that blindly consumed all translated events would therefore process keyboard arrows/Space once through the existing launcher path and a second time through the controller integration.

`ShellInputController` now accepts only translated events whose `InputSource` is `CONTROLLER`. A dedicated regression asserts that a keyboard event returns no Shell-controller action.

## Finding 2 — analog stick repeat belongs to platform policy — FIXED IN SOURCE

Menu navigation requires a repeat delay/interval; placing those constants in `main.py` would recreate per-surface input policy.

`StandardInputPolicy` now owns bounded initial-repeat and repeat-interval values alongside stick dead-zone and virtual-pointer tuning. `ShellInputController` owns only the small transient held-direction/deadline state and resets it at controller ownership boundaries.

## Finding 3 — controller lifecycle must stop at Activity ownership boundary — SOURCE SEAM ADDED, LIVE COMPOSITION PENDING

The Shell must not continue navigating invisibly while an Activity is running. `ShellInputController` therefore has explicit start/close semantics and resets analog state at those boundaries.

The large launcher loop has **not yet** been mechanically rewritten through the GitHub whole-file contents API. After focused source PASS, live Shell composition must suspend/close the Shell controller owner before Activity launch and restart it only when Shell control returns.

This still does not solve Activity controller delivery. That belongs to the trusted R7 semantic input broker/session layer.

## Finding 4 — mapped game controllers versus generic joysticks — OPEN PHASE-0 COMPATIBILITY QUESTION

Pygame exposes two related but distinct APIs:

- SDL game-controller abstraction for devices that have a known standardized mapping;
- lower-level joystick API for generic/unmapped joystick devices.

The current `PygameControllerSet` intentionally uses the standardized controller abstraction because it provides stable positional controls suitable for Greia's brand-neutral semantics.

However, the current Linux HAL presence probe is broader: a conventional joystick device node may exist even when SDL does not classify that device as a mapped game controller. Therefore **raw joystick presence must not eventually be treated as proof that the selected production Greia input backend can provide the standard controller contract**.

Before Phase-0 controller support is certified, Greia must choose and prove one of these policies for generic/unmapped joysticks:

1. provide a bounded parent calibration/mapping flow that promotes a generic joystick into Greia's standard positional/semantic controls; or
2. provide a conservative backend fallback for a deliberately defined subset of generic joysticks (for example two primary axes + primary button/hat), with explicit evidence; or
3. define the supported Phase-0 hardware contract as mapped game controllers only and report generic joystick presence separately rather than advertising the `controller` semantic capability for an unusable device.

Do **not** solve this by exposing raw joystick indices to Activities.

Until this is selected and implemented, `controller` capability behavior on an unmapped generic joystick remains **UNPROVEN** and must be covered by physical acceptance.

## Finding 5 — Guide/system input reservation is correctly above Activity mapping — SOURCE-CLOSED / BACKEND UNPROVEN

`CONTROLLER_GUIDE` is recognized at the physical-control layer but `StandardInputMapper` never returns it as an Activity semantic action. This correctly preserves the ADR 0019/0020 trust direction.

A real production backend still has to prove that the physical Guide/system event reaches Greia before Activity delivery. Pure mapping tests cannot prove device/input isolation.

## Finding 6 — controller capability does not mean Activities must request it — CONFIRMED

Painting (`pointer`) and Writing (`text`) deliberately do not require the `controller` capability. The platform may feed standard alternative controller input into an Activity interaction profile without making that device a hard package compatibility requirement.

An Activity should require `controller` only if it genuinely cannot provide its intended experience without a controller.

## Finding 7 — controller-as-global-mouse would violate the architecture — REJECTED

The Greia virtual pointer is semantic, bounded and Activity-contextual. Global Linux mouse emulation would blur the protected system-input boundary, create surprising behavior in non-pointer Activities, and make runtime-neutral Web delivery harder.

No source in this tranche introduces global controller-to-mouse emulation.

## Finding 8 — physical controller evidence is mandatory — OPEN

The source does not prove:

- actual controller model compatibility;
- neutral-stick drift;
- acceptable dead-zone feel;
- button-to-visible-response latency;
- disconnect/reconnect behavior;
- SDL mapping availability on the Acer image;
- resource/FD/process cost on the Acer floor;
- generic joystick fallback/calibration;
- protected Guide/system interception;
- Activity raw-device denial in the selected production backend;
- Web input bridge behavior.

Use `docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md` after source verification and after the corresponding live integration exists.

## Judgment

**Architecture/design: ACCEPTED.**  
**Current source tranche: suitable for focused verification.**  
**Live Shell integration: pending verification before minimal composition.**  
**Activity controller broker/input delivery: R7 blocker, not implemented.**  
**Generic/unmapped joystick policy: explicit Phase-0 compatibility decision still required.**  
**Physical controller support claim: UNPROVEN.**
