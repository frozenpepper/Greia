# Greia R5 — Session/Event/Progression Source Closure

Date: 2026-08-08

R5 is source-complete in the verified working tree under ADR 0017.

## Implemented

- supervisor-created authoritative session rows before child launch;
- READY, terminal outcome, active duration, launch failure and platform-restart recovery;
- bounded per-profile SQLite history/progression implementation kept outside Activity namespaces;
- normalized manifest-declared event pipeline;
- per-session broker bound to one trusted profile/Activity/session with no identity selector in Activity requests;
- transactional idempotency and conflict detection;
- platform-owned best-score calculation using manifest score ordering;
- Greia-owned progression policy and auditable Reward Ledger;
- Activity payload fields have no reward/profile/session authority;
- bounded history/event/reward retention policy;
- runtime-neutral Activity event client/SDK;
- logical history export hook for future `.greiabackup`;
- bounded authenticated parent progress summaries that omit raw DB paths, event payloads, idempotency keys and internal session IDs;
- corrupt history does not take down parent controls;
- build validation loads history policy and validates progression rules against the canonical Activity catalogue;
- local child progress is product state, not analytics, and R5 adds no upload path.

## Verification

Final local closure command:

```text
make verify
```

Result:

- **213 / 213 provider-free unit tests PASS**;
- project/runtime/Activity/asset/build validation PASS;
- canonical Activity validation PASS for both bundled Activities;
- source footprint approximately **16 MiB**.

Important negative evidence includes:

- forged profile/activity/session fields cannot redirect the event broker;
- forged reward fields such as `diamonds +999999` have no authority;
- only Greia policy maps `org.greia.shape-garden:creation.completed` to `star +1`;
- duplicate identical events do not duplicate rewards;
- conflicting idempotency reuse fails transactionally;
- missing Bubblewrap still creates and closes an authoritative `launch_failure` session;
- Activity event cooperation is optional for session existence;
- parent summary contains no raw database path or event payload.

## Evidence limits

This is source evidence only. Linux/Bubblewrap Unix-socket behavior, low-resource runtime performance, power-loss durability, Acer behavior, and Raspberry Pi behavior remain UNPROVEN until the appropriate later evidence phases.

## Next blocking phase

R6 — Device Capability Service/HAL core + full runtime-adapter integration.

R6 must replace the current Phase-0 static hardware capability assumptions in PermissionBroker with trusted platform-owned capability snapshots, define HAL contracts for display/input/audio/network/removable media, and preserve all R1–R5 authority/storage/session/progression boundaries.

## Repository continuity note

R0 canonical-repository completeness remains open. The repository was bootstrapped documentation/source-fragment-first and still lacks some historical large source/binary files. R5 coherent tranches are being committed as implemented; this closure record must not be interpreted as a claim that GitHub HEAD is yet an independently reproducible full-tree clone.
