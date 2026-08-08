# ADR 0016 — Universal Storage Service, Ephemeral Runtime State, and Transactional Save Migrations

**Status:** accepted  
**Date:** 2026-08-08  
**Plan:** R4 of `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

## Context

ADR 0012 defines durable Activity state as a Greia platform service logically keyed by `(profile_id, activity_id)`. ADR 0015 makes Activity IDs permanent before that state becomes durable. The Phase-0 prototype, however, originally gave an Activity a writable profile-owned HOME/XDG directory and expected ordinary file access to function as its save system.

That prototype convention is not sufficient for the long-term platform because raw writable profile directories would allow every runtime to invent its own persistence model and would let Activity code bypass:

- storage quotas;
- architecture-neutral serialization rules;
- atomic write/checkpoint semantics;
- save schema versions;
- transactional migrations and rollback;
- `.greiabackup` logical export;
- cross-runtime parity between Python and Web;
- parent storage accounting and recovery policy.

R4 therefore turns storage into an enforced platform boundary rather than a documentation convention.

## Decision

### 1. Authoritative durable state is physically separate from Activity runtime scratch

Each Greia profile has two distinct concepts:

```text
profile
├── activities/<activity_id>/        compatibility / narrow profile-request state
└── storage/<activity_id>/           authoritative durable Activity state
```

The durable `storage/<activity_id>` namespace is owned by Greia. It is not mounted writable—or mounted at all—inside the normal Activity sandbox.

The Activity process instead receives an **ephemeral per-launch runtime workspace** used for:

- HOME;
- XDG cache/config/data directories used only as runtime scratch;
- READY/STOP lifecycle markers;
- other bounded per-launch transient files.

On an installed system this workspace lives under a Greia runtime root such as:

```text
/run/greia-os/activity-runtime/<session_id>
```

and is mounted into the sandbox at the fixed Activity-private runtime path. Developer runs use an equivalent temporary Greia-owned location. The workspace is removed when the Activity session ends.

Consequently, a direct Python `open()` into HOME/XDG cannot silently become a second authoritative save system. Portable saves must use Greia storage semantics.

The existing `activities/<activity_id>` profile namespace is retained only for narrow compatibility/system-request state during the migration from the prototype. It is not the general Activity save root and is not exposed as the Activity's HOME.

### 2. The logical storage API is runtime-neutral

The R4 logical service exposes two durable data models:

1. **JSON-compatible key/value state**;
2. **private binary files/blobs** addressed by relative portable names.

The semantic operations include:

```text
kv.get
kv.set
kv.delete
kv.list

files.read
files.write_atomic
files.delete
files.list

info
checkpoint
```

Python exposes these through `ActivityStorageClient` and `greia_platform.activity_api.get_storage()`.

The semantics are intentionally independent of Python. A future Web runtime must bridge to the same logical operations rather than inventing authoritative `localStorage`, IndexedDB, or another save silo.

### 3. Activity code never receives the physical durable-storage path

For each Activity session, the trusted supervisor opens exactly one `ActivityStorage` instance for the current profile and Activity, then creates an `ActivityStorageBroker` bound to that storage object.

The child receives only:

- a per-session Unix-domain socket path;
- a random per-session broker token.

It does **not** send a profile ID or Activity ID to select another namespace. The broker is already bound to the one namespace selected by trusted Greia code.

In a Bubblewrap sandbox, only the broker runtime directory is selectively exposed at a fixed child path. The durable storage root remains outside the namespace.

This preserves R1 authority: possession of an Activity-controlled string cannot redirect storage to a sibling profile or Activity.

### 4. The broker transport is internal, bounded, and versioned

The current local transport is a versioned framed Unix-domain socket protocol.

Each frame consists of:

1. a fixed-size header-length prefix;
2. bounded JSON metadata;
3. a raw binary payload.

Raw payloads avoid base64 expansion for files. Protocol version 1 is an internal Greia runtime transport, not the `.greiaactivity` package format and not a promise that every future platform must use Unix sockets internally.

The broker is deliberately resource bounded for the C0 reference class:

- socket file mode is `0600` inside a `0700` session directory;
- each launch gets a random token;
- header and payload sizes are bounded;
- KV payloads are rejected against the KV value limit before JSON decoding;
- at most two broker requests execute concurrently;
- accept backlog is bounded;
- stalled requests time out after two seconds;
- broker runtime directories are removed at session cleanup;
- Activity-visible storage errors do not reveal host filesystem paths or internal trace details.

These source contracts still require Linux/Bubblewrap runtime evidence in R14.

### 5. Storage policy belongs to Greia, not the Activity package

`runtime/storage-policy.toml` defines Phase-0 platform policy.

The current defaults are:

- namespace quota: 32 MiB per Activity/profile;
- KV total: 2 MiB;
- individual KV value: 256 KiB;
- key length: 128 bytes;
- individual private file: 16 MiB;
- private file count: 512;
- relative private path: 512 bytes;
- protected free-space reserve: 64 MiB;
- rollback snapshots: at most 2.

These values are Phase-0 defaults, not constitutional constants. Future parent/build/capability policy may vary them deliberately, but Activity packages do not grant themselves more storage.

Growth is refused when it would exceed the Activity quota or the protected machine free-space reserve. Existing data remains readable when the machine is low on free space; the reserve constrains growth rather than making saves disappear merely because the disk became full elsewhere.

### 6. Key/value state is portable JSON

Authoritative KV values must be JSON-compatible:

- `null`;
- booleans;
- strings;
- finite numbers;
- arrays;
- objects with string keys.

The implementation rejects:

- NaN/infinity;
- non-string object keys;
- excessive nesting;
- normalized Unicode key collisions;
- keys containing path/control characters;
- values beyond configured limits.

Data is written as deterministic UTF-8 JSON through atomic replace.

This excludes Python pickle, runtime-native object serialization, host paths, and architecture-specific memory representations from the portable save contract.

### 7. Private files use portable relative names

Private-file names are validated relative paths beneath the Greia-owned file root.

The Phase-0 implementation deliberately accepts a conservative portable component vocabulary to avoid case-insensitive/cross-platform collisions and rejects:

- absolute paths;
- `..` traversal;
- backslash/path ambiguity;
- overlong paths;
- symbolic-link traversal;
- final-component symlinks;
- files beyond configured size/count limits.

Existing namespaces are revalidated when opened. Greia does not silently grandfather corrupted storage containing symlinks, oversized files, excess file counts, malformed metadata/KV state, or total data beyond the namespace quota.

### 8. Writes are atomic and storage metadata is platform-owned

KV files, metadata, and private-file writes use temporary files, `fsync`, permission setting, atomic replacement, and directory synchronization where available.

Each namespace has platform metadata containing at least:

- storage format version;
- Activity ID;
- save schema version;
- created/updated timestamps;
- last checkpoint timestamp/token;
- last writer package version.

Metadata is strictly typed and fails closed when malformed rather than coercing booleans/objects/numbers into plausible strings or integers.

A Greia lock file serializes operations for the namespace. The lock itself may not be a symbolic link.

### 9. Every Activity manifest declares a save schema version

The universal manifest now requires:

```toml
[storage]
schema_version = 1
```

The schema version describes the Activity's **logical save schema**, not Greia's storage-container format.

When opening storage:

- stored schema == requested schema → open normally;
- stored schema < requested schema → raise `StorageMigrationRequired`;
- stored schema > requested schema → fail with `StorageSchemaTooNew`.

An ordinary Activity launch never silently upgrades or downgrades its only save copy.

### 10. Save migration is Activity-authored but platform-transacted

`ActivityStorageService.begin_migration()` creates a migration transaction owned by Greia.

The transaction follows this model:

```text
active old save
      │
      ├── remains authoritative during migration
      │
      └── copied to Greia working namespace
                    │
                    ↓
             migration changes
                    │
                    ↓
           validate target schema/quota
                    │
                    ↓
       atomic active-version switch
              /             \
        success             failure
          │                    │
          ↓                    ↓
 old save → rollback      old save remains active
 snapshot
```

The migration working copy has the target save schema and new package version. Commit verifies target schema/quota, renames the previous active namespace to a bounded rollback snapshot, and atomically promotes the working copy.

If activation fails after moving the old namespace, Greia attempts to restore it. Exiting an uncommitted transaction deletes the working copy and leaves the old save active.

Migration creation also respects the machine protected-free-space reserve because the working copy temporarily duplicates data.

R4 supplies the transaction mechanism. R10 package/update orchestration decides **when** a newly installed Activity release is allowed to run its migration and when activation/rollback should occur.

### 11. Prototype Activity IDs migrate both compatibility and durable namespaces

ADR 0015's trusted one-time legacy-ID migration applies to both:

```text
activities/<legacy_id>
storage/<legacy_id>
```

The migration is preflighted and fail-closed. If old and new durable namespaces both exist, Greia refuses to merge them automatically.

This ensures that the prototype → permanent-ID transition occurs before backups and package lineage make the storage keys long-lived.

### 12. Checkpoints are platform-visible markers, not full backup snapshots

`checkpoint()` records a new platform-owned token and timestamp in namespace metadata.

This gives lifecycle/package/backup code a stable marker for “the Activity reached a deliberate durable-save point.” It does **not** mean Greia copies the whole namespace at every checkpoint.

Full package-update migration snapshots and `.greiabackup` exports are separate mechanisms.

### 13. Trusted Greia services may access storage directly

Activity code uses the broker/client boundary.

Trusted platform components—such as future Package Manager, Backup/Restore Service, parent storage administration, migration orchestration, and R5 session/progression integration—may use `ActivityStorageService` directly because they already execute in Greia's trusted authority domain.

They must still obey schema/quota/path/integrity contracts. “Trusted process” does not mean “raw filesystem free-for-all.”

## Consequences

### Positive

- Python raw file access can no longer bypass authoritative save quotas and backup semantics;
- Web can reuse the same storage model instead of creating a second persistence ecosystem;
- durable child data stays architecture-neutral;
- physical profile paths are hidden from Activities;
- one Activity cannot choose another Activity/profile storage namespace through the storage protocol;
- save migrations keep the old state active until commit;
- package update/rollback and `.greiabackup` now have a stable storage authority to build upon;
- low-resource broker behavior is explicitly bounded;
- corrupted/restored namespaces are revalidated rather than silently trusted.

### Costs

- Activities must use the Greia storage API for authoritative saves;
- direct file writes to runtime HOME/XDG are ephemeral and disappear after the session;
- migration temporarily requires enough free space for a working copy;
- the local broker adds a small process/thread/socket coordination cost;
- old prototype raw Activity-data folders are preserved for compatibility but are not automatically reclassified as authoritative save data.

## Rejected alternatives

### Keep the Activity's profile HOME as its save directory and add quotas later

Rejected. Raw filesystem access would remain an ungoverned second save API and would undermine Web parity, migrations, backup, and policy enforcement.

### Mount durable storage directly but ask Activities to use the SDK voluntarily

Rejected. An Activity could bypass the SDK with ordinary filesystem calls. The architecture requires platform-owned placement/semantics, not documentation-only discipline.

### Use Python pickle for convenient object persistence

Rejected because it is runtime-specific, unsafe for untrusted data, brittle across code versions, and unsuitable for architecture-neutral backups.

### Give the broker profile/activity IDs on every request

Rejected because it unnecessarily creates a confused-deputy surface. One broker instance is already bound to exactly one trusted namespace.

### Use an unbounded threaded broker

Rejected for the 768 MiB reference class. Broken or hostile Activity code must not be able to create arbitrary broker threads/RAM pressure.

### Migrate the only save copy in place

Rejected because a failed migration would directly destroy or partially mutate the child's authoritative state.

### Treat checkpoint as a complete snapshot

Rejected because copying the entire namespace on every checkpoint would add unnecessary write amplification, disk use, and latency on old storage hardware.

## Source closure evidence

R4 source closure requires provider-free tests for:

- storage namespace separation from runtime scratch;
- real child-process access through the broker without physical path exposure;
- KV portability and limits;
- private-file atomic CRUD and path safety;
- final-component/parent symlink rejection;
- current-policy revalidation of existing storage;
- namespace/file/KV quota enforcement;
- bounded broker concurrency/timeouts/authentication;
- metadata strictness and corruption failure;
- save schema comparison;
- working-copy migration with old state remaining active;
- bounded rollback snapshots;
- failed migration cleanup;
- legacy Activity-ID migration of both compatibility and durable namespaces;
- explicit manifest storage schema;
- runtime workspace cleanup and absence of durable-storage mounts from the Activity sandbox.

Source tests do not prove Unix-socket/Bubblewrap behavior on Debian/Acer/Raspberry Pi. That runtime evidence remains an R14 gate.
