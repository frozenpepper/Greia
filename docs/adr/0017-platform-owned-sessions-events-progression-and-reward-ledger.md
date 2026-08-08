# ADR 0017 — Platform-Owned Sessions, Activity Events, Progression, and Reward Ledger

**Status:** accepted  
**Date:** 2026-08-08  
**Plan:** R5 of `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## Context

Greia's architecture requires sessions, progress, scores, achievements, and rewards to belong to the platform rather than to any individual runtime. R2 established a runtime-neutral Activity lifecycle. R3 established permanent Activity identities and declared factual event semantics. R4 established brokered durable Activity storage. R5 connects those boundaries into one authoritative local history/progression pipeline.

The platform must ensure that sessions exist even without Activity cooperation, events cannot escape their live Activity/session, retries do not duplicate progression, scores follow declared semantics, global rewards remain Greia policy, parent controls get bounded logical summaries, and all state remains local/offline by default.

## Decision

### 1. Sessions are created automatically by the supervisor

Before runtime adapter, storage broker, Bubblewrap, or child process launch proceeds, Greia creates an authoritative session containing the platform-generated session ID, profile ID, canonical Activity ID, package version/digest, runtime type, and start timestamp.

READY and terminal state are written by the supervisor. Missing runtime adapters, missing required Bubblewrap, crash, READY timeout, forced stop, shutdown, and platform-service failure all become normalized session outcomes. On Greia restart, unfinished rows are recovered as `platform_restart`.

Activity cooperation is therefore not required for session existence.

### 2. Session/progression state is one profile-owned Greia database

Each profile owns an internal SQLite database under its progress namespace. Activities never receive its path, connection, schema, or SQL access.

The database stores bounded platform state for sessions, normalized events, event-count aggregates, best-score aggregates, reward balances, reward-ledger rows, and once-per-session rule applications.

SQLite is an implementation detail, not an Activity API or backup format. Foreign keys are enabled; durability uses synchronous FULL; journal mode remains deliberately simple for the current offline low-resource appliance target.

### 3. History policy is bounded and Greia-owned

`runtime/history-policy.toml` currently bounds retained sessions, events/session, payload size, idempotency key size, reward-ledger rows, parent summary rows, score magnitude, and SQLite busy timeout.

Old detailed rows may be pruned while aggregate progression remains authoritative. Auxiliary once-per-session rows cascade with pruned sessions. These are platform defaults, not Activity authority.

### 4. Event transport is per-session and identity-bound

The supervisor starts one event broker per live Activity session. It is constructor-bound to exactly one trusted profile history store, validated Activity manifest, progression policy, and session ID.

The Activity request contains no profile/activity/session selector. The child receives only a random token and per-session Unix socket path. In an installed sandbox only the broker socket root is exposed; the database remains outside the Activity namespace.

The broker uses bounded versioned JSON framing, mode-0600 socket inside a mode-0700 runtime directory, at most two active requests, backlog two, and two-second request timeout. Runtime broker state is removed at session cleanup.

### 5. Activities report declared factual events only

The runtime-neutral SDK operation is conceptually:

```text
emit(event_id, idempotency_key, optional score, portable payload)
```

Greia validates the event against the manifest attached to the live broker session. Unknown, closed, wrong-Activity, undeclared, invalid-score, overlarge, or excess events are rejected.

Payload fields named `reward_id`, `reward_delta`, `profile_id`, `activity_id`, `session_id`, `stars`, or similar have no authorization meaning.

### 6. Idempotency is transactional

`(session_id, idempotency_key)` is unique.

Repeating the same key with identical normalized content returns the existing event as a duplicate and applies no new progression. Reusing the key for different content is rejected transactionally.

### 7. Scores are compared by Greia

R3 declares `higher_better` or `lower_better` for score events. R5 validates finite bounded numeric scores and updates the platform best-score aggregate according to that declared ordering. Activities cannot write best-score state directly.

### 8. Global progression/reward economics are Greia policy

`runtime/progression-policy.toml` maps validated Activity events to platform consequences. The initial rule proves the boundary:

```text
org.greia.shape-garden : creation.completed
        → once per session
        → star +1
```

The Activity manifest does not contain `star +1`, and an Activity payload cannot replace or augment it.

Greia transactionally updates balances and appends an auditable ledger row linking session, event, policy rule, reward ID, delta, and resulting balance. Activities have no direct Reward Ledger write path.

### 9. Parent summaries are logical, bounded, and resilient

Authenticated parent controls read through a bounded `ParentProgressReader`, not the SQLite file.

Parent-visible data includes reward balances, event counts, best scores, and recent session summaries. It deliberately omits raw database paths, broker tokens, event payloads, idempotency keys, and internal session IDs.

Corrupt/unavailable history returns `available: false` with an empty summary rather than taking down the parent controls needed to recover the machine. R12 may improve presentation, but R5 establishes the platform-readable contract.

### 10. R11 backup uses logical export

`ProfileHistoryStore.export_state()` returns JSON-compatible logical state. `.greiabackup` must consume logical state rather than treating SQLite bytes as the portable backup contract.

### 11. Child progress is local product state, not telemetry

R5 history exists for the local Greia experience: recent Activity history, scores, stars/rewards, parent summaries, and backup. It is not analytics telemetry and is not uploaded by default. R5 introduces no analytics endpoint, cloud account, tracker, advertiser path, or remote reporting path.

### 12. Platform failure is distinct from Activity failure

R5 adds `platform_failure`. If required Greia history/event/storage authority fails after launch begins, Greia fails the Activity closed and reports a platform failure rather than misclassifying it as an Activity crash.

## Consequences

Benefits include automatic session history, one cross-runtime event/progression model, safe event retries, platform-owned reward economics, bounded parent summaries, low-resource history bounds, logical backup hooks, and local-only progress by default.

Costs include one small SQLite database per profile, a small event broker per live Activity session, deliberate pruning of detailed old history, and progression policy becoming validated Greia platform configuration.

## Rejected alternatives

Rejected: Activity-owned scores/rewards; trusting profile/activity/session selectors sent by an Activity; reward instructions inside event payloads; one progression database per Activity; raw SQLite as backup format; and default cloud analytics upload.

## Source closure evidence

R5 source evidence proves automatic session existence and launch-failure recording; restart recovery; supervisor-owned READY/terminal state; broker identity binding; undeclared/closed/wrong-session rejection; transactional idempotency; payload/event/score bounds; manifest score ordering; forged reward fields having no authority; Greia-only reward deltas; once-per-session deduplication; bounded history/ledger pruning; parent-summary path/session/event-payload omission and corrupt-history resilience; logical export; and build-policy validation.

Final local R5 source verification on 2026-08-08: **213/213 tests PASS**, project/runtime/Activity/asset/build validation PASS, source footprint approximately **16 MiB**.

Linux/Bubblewrap/real-hardware broker performance and durability remain UNPROVEN until later controlled evidence phases.
