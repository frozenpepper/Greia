# Greia Bootstrap Handover — 2026-08-08

## Repository state

Canonical repository: `frozenpepper/Greia` (private during early design work).

Greia has been established as the canonical project/platform name.

Current canonical reading order:

1. `README.md`
2. `AGENTS.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. `docs/adr/0001-greia-project-identity-and-pip-migration.md`
5. `docs/adr/0002-first-class-arm-and-direct-graphics-direction.md`

## Source heritage

The latest recovered Pip-era implementation state is `0.12.0-phase0-dev`.

Important facts from that state:

- source validation reported 140 provider-free tests passing;
- image profiles had been converted from executable `.env` fragments to typed TOML declarations;
- package composition had been split into architectural package sets;
- runtime family was explicit in Activity manifests;
- the profile schema recognized ARM64 but the then-current builder intentionally rejected ARM because only the x86 BIOS/MBR/GRUB-PC artifact adapter was implemented;
- the old Acer C0 resource policy remained preferred <=800 MiB and hard <1,000 MiB for the installed core;
- one curated Python/Pygame runtime was implemented;
- Web runtime was architecture-only, not implemented;
- Bubblewrap-based Activity isolation existed in the Pip-era source;
- Xorg and stock Plymouth were still present in that implementation;
- stock Plymouth was explicitly blocked from release because Escape/text fallback could reveal Linux output;
- no produced Linux image or physical reference-hardware acceptance had yet been claimed for v0.12.

## Superseding Greia decisions

The following decisions supersede portions of the old implementation architecture:

### Greia identity

The platform/project is Greia. Professor Pip remains a possible child-facing guide/character.

### ARM is co-equal

Raspberry Pi 400 and Raspberry Pi 500 are explicit first-class reference systems. ARM is not a later portability exercise.

### X11 is not the Greia target architecture

Historic Xorg work is migration/evidence material. New Greia architecture should target a direct appliance graphics path based around DRM/KMS and minimal runtime backends. A compositor or compatibility layer must justify itself with measured value and resource cost.

### Activity-first architecture remains

Python and Web are runtime adapters under one Activity contract. Storage, sessions, progression, permissions, install/update, backup, and parent policy remain platform-owned and runtime-neutral.

## Source-tree migration status

The complete v0.12 source ZIP is known from prior project work and its recorded checksum is:

`7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124`

However, the binary archive is not mounted in the current working runtime, so this bootstrap pass does **not** pretend that the implementation tree has already been imported into GitHub.

When the source archive is available to a working environment, migration should proceed deliberately:

1. verify the archive checksum;
2. extract the complete tree;
3. preserve all history-relevant docs under a `docs/history/pip/` or similar namespace rather than deleting them;
4. inventory persisted/public identifiers (`pip_*` module names, filesystem paths, Activity IDs, backup/package extensions, environment variables, services) before renaming;
5. rebrand user-facing/platform naming to Greia;
6. keep compatibility aliases/migrations where renaming would otherwise break saves or installed state;
7. replace the Xorg-specific target architecture through a dedicated implementation plan rather than deleting display code blindly;
8. add real ARM build adapters and Raspberry Pi profiles below shared Greia contracts;
9. run the existing source test suite after each migration stage;
10. add new tests for Greia naming/migration invariants and direct-display architecture.

## Immediate architecture work still needed

High-priority detailed ADR/specification work:

- Greia Activity manifest/package format;
- Greia storage namespace and save-schema contract;
- `.greiabackup` format and restore semantics;
- session/progression/reward event schema;
- Parent API and authorization model;
- direct graphics/display architecture investigation;
- embedded Web runtime benchmark plan;
- Raspberry Pi 400/500 image/boot adapter design;
- package signing/trust/update chain;
- universal forced-return/watchdog behavior;
- capability-class certification methodology.

## Evidence discipline

Do not claim that direct DRM/KMS, the Web runtime, Raspberry Pi images, or the old Acer work merely because architecture documents describe them.

Architecture declarations and source tests are not physical hardware evidence.
