# ADR 0015 — Permanent Activity Identity, Capability Requirements, Permissions, and Events

**Status:** accepted  
**Date:** 2026-08-08  
**Plan:** R3 of `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## Context

Greia's prototype Activity manifests predated the platform constitution. They used short IDs such as `shape_garden`, mixed hardware/runtime requirements and privileged operations in one `runtime.capabilities` list, and allowed Activity packages to declare concrete global reward amounts.

Those shortcuts are unsafe to carry into durable storage, sessions, package updates, backup/restore, or a third-party Activity ecosystem:

- Activity ID becomes a durable key for `(profile_id, activity_id)` storage, sessions, progression, package lineage and backup state;
- a manifest requirement such as `display` means something fundamentally different from a permission such as `profile.manage_own`;
- package-declared reward amounts would let package metadata define Greia's global economy rather than report facts to platform policy;
- allowing arbitrary packages to claim legacy IDs would let them attempt to inherit another Activity's data.

R3 therefore normalizes the manifest contract before R4/R5 begin persisting new platform-owned state.

## Decision

### 1. Canonical Activity IDs are permanent reverse-DNS identifiers

Canonical IDs use lower-case reverse-DNS naming and are intended never to change after public release.

Greia first-party Activities use the `org.greia` namespace. The current built-ins become:

- `org.greia.shape-garden`
- `org.greia.workshop-settings`

The canonical ID is not a display name, directory name chosen by the parent, runtime type, architecture, or localized title. It is the durable package identity used by storage, sessions, progression, package/update, backup/restore and policy.

The validator requires a multi-component lower-case reverse-DNS identifier with safe ASCII segments. Prototype single-token IDs are no longer valid canonical IDs.

### 2. Legacy IDs are explicit migration aliases, not alternate identities

A manifest may carry `activity.legacy_ids` only to migrate a known previous identity.

For the Greia v0.13 prototype transition:

```toml
[activity]
id = "org.greia.shape-garden"
legacy_ids = ["shape_garden"]
```

and:

```toml
[activity]
id = "org.greia.workshop-settings"
legacy_ids = ["workshop_settings"]
```

Phase 0 accepts legacy aliases only from a package source classified by Greia as `BUILT_IN`.

An unsigned/developer/external package cannot claim a legacy alias, even if its canonical ID looks plausible. Future repository/package updates may support lineage-backed identity migration only through R10 package authenticity/update policy. Merely writing an alias into `activity.toml` never establishes lineage.

The registry rejects canonical/legacy collisions across discovered Activities.

### 3. Profile Activity-data migration is no-merge and fail-closed

The profile layer receives only trusted ID migrations from the registry/package layer.

For each profile, a legacy Activity data directory may be atomically renamed to the canonical ID when:

- the legacy namespace exists;
- the canonical namespace does not exist;
- neither path is a symlink;
- the migration mapping is unambiguous.

If both legacy and canonical namespaces already exist, Greia refuses to merge or guess. Child data is never silently overwritten or combined.

A completed migration is idempotent.

### 4. Capability requirements are not permissions

The old `runtime.capabilities` list is rejected.

The manifest now separates platform/runtime capability requirements:

```toml
[requirements]
required_capabilities = ["display", "pointer"]
optional_capabilities = ["removable_media"]
```

from privileged permission requests:

```toml
[permissions]
requested = [
  "customization.manage",
  "profile.manage_own",
  "removable_media.read",
]
```

Capability requirements describe what the environment must or may be able to provide. Examples include display, pointer, audio, removable-media support, future touch, WebGL, microphone, camera or controller capabilities.

Permission requests describe authority an Activity would like Greia to grant. A request never grants itself. `PermissionBroker` still intersects the request with package trust/origin, security policy, build policy, parent policy and available platform capability.

### 5. Required and optional capabilities have different launch semantics

A missing **required** capability prevents Greia from issuing launch authority for that Activity on the current system.

A missing **optional** capability does not prevent launch. The capability is simply absent from effective capabilities, and any permission depending on it cannot be granted.

This distinction is central to Greia's capability-class strategy: one Activity package can progressively enhance itself without becoming separate ARM/x86 or old/new-machine products.

Phase 0 still uses provisional static capability sets. R6 replaces those inputs with the Device Capability Service/HAL. This ADR defines semantics, not hardware certification.

### 6. Runtime catalogue has separate capability and permission vocabularies

The curated runtime configuration now declares:

```toml
[capabilities]
allowed = [ ... ]

[permissions]
allowed = [ ... ]
```

A permission no longer has to masquerade as a hardware/runtime capability merely so one parser can recognize it.

For Phase 0, `removable_media.read` depends on the platform capability `removable_media`. The permission is denied when that capability is unavailable even if package trust and parent/build policy would otherwise allow it.

### 7. Activity packages declare facts/events, not global rewards

`education.rewards` is forbidden.

An Activity package may declare normalized event types that it can later emit, for example:

```toml
[education]
events = [
  { id = "creation.completed", kind = "creation" },
]
```

The durable event identity is the pair:

```text
(activity_id, event_id)
```

An Activity event is a fact about Activity state or child interaction. It is not a request to mint global currency.

Allowed initial event kinds are intentionally small:

- `completion`
- `creation`
- `milestone`
- `score`

R5 may expand this vocabulary through an ADR/schema version when there is a concrete need.

### 8. Score events describe comparison semantics, not reward value

A `score` event must declare whether higher or lower values are better:

```toml
{ id = "round.score", kind = "score", score_order = "higher_better" }
```

or:

```toml
{ id = "solve.time", kind = "score", score_order = "lower_better" }
```

This lets Greia interpret and present scores consistently without conflating score magnitude with stars/tokens/unlocks.

Non-score events may not carry `score_order`.

### 9. Global progression mapping is Greia-owned policy

R3 defines the boundary but does not implement the R5 Progression Engine.

Conceptually:

```text
validated Activity event
        ↓
(activity_id, event_id, payload)
        ↓
Greia event validation / session context
        ↓
Greia-owned progression policy
        ↓
progress / achievements / stars / discoveries / unlocks / no global effect
```

The same Activity event may map differently in later platform releases without changing the Activity package's authority. Activities cannot write the Reward Ledger directly.

## Consequences

### Positive

- durable child state gets stable identity before Storage/Session/Backup are implemented;
- capability matching becomes architecture-neutral and suitable for Pi, old x86 and future Web Activities;
- PermissionBroker authority is no longer encoded in a mixed capability list;
- package metadata cannot define global reward economics;
- one-time prototype ID migration preserves existing child data without creating permanent alias ambiguity;
- external packages cannot steal data by claiming a built-in legacy ID;
- score semantics can be shared across runtimes without turning scores into currency.

### Costs

- all prototype manifests/tests/configuration must migrate at once;
- profile startup/catalogue refresh gains a bounded legacy-ID migration step;
- future package/update work must preserve stable IDs and explicit lineage rather than treating package names as mutable labels;
- existing prototype `runtime.capabilities` manifests are intentionally rejected rather than silently reinterpreted.

## Rejected alternatives

### Keep short IDs because Greia is not public yet

Rejected. R4/R5 would immediately make those IDs durable storage/session keys, making a later cleanup significantly more dangerous.

### Allow Activities to choose any old ID as an alias

Rejected. Alias migration moves child data and is therefore an authority operation. It requires platform-trusted package lineage.

### Keep one capability list and classify strings later

Rejected. It obscures the difference between machine capability and Activity authority and already contributed to the R1 security ambiguity.

### Let Activities declare star/token values but validate a maximum

Rejected. A bounded amount is still package-owned global economy policy. Activities report events; Greia owns mapping.

### Use score as a reward value

Rejected. Scores are Activity-domain measurements. Global rewards are platform policy and may depend on context, progression rules, age/policy, repetition limits or other factors.

## Evidence / tests required for source closure

R3 source closure requires tests proving:

- built-ins use permanent reverse-DNS IDs;
- prototype IDs migrate to canonical storage namespaces without losing data;
- migration collisions fail closed;
- external packages cannot declare trusted legacy aliases;
- canonical/legacy ID collisions are rejected;
- capability requirements and permission requests parse separately;
- missing required capability refuses launch authority;
- missing optional capability does not prevent launch but blocks dependent permission;
- unknown capabilities/permissions are rejected;
- old `runtime.capabilities` is rejected;
- `education.rewards` is rejected;
- score events require explicit score ordering;
- bundled manifests contain no package-owned global reward amounts.

Hardware capability truth remains UNPROVEN until R6/R14 evidence. This ADR does not claim actual display/audio/removable-media capability on any reference machine.
