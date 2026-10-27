# ADR 0038 — Lightweight application update packages

**Status:** ACCEPTED — explicit owner direction, 2026-10-24
**Extends:** ADR 0023, ADR 0030 and ADR 0036
**Supersedes where conflicting:** the full-slot-only normal update route and the
requirement that every system/Activity code update use a complete OS image.
ADR 0036 continues to own Linux/system-slot releases and A/B installation.

## Decision

Routine Greia updates are ZIP files named `*.greia_update`. A main
`manifest.json` declares the package format, type, version, compatibility and
contents. Supported types are Python platform/launcher, selected Activities,
combined Python plus Activities, and full system. Exact schema names, limits
and CLI flags are source-owned by the package implementation.

Python and Activity updates are the priority. They reuse the image's curated
Python interpreter and installed dependencies; they do not ship or install
Linux, private environments, wheels, native libraries or system packages.
Full-system packages reuse the existing v3 bundle and A/B writer, health and
rollback mechanisms. There is no second OS/image updater.

Python and Activity updates are supported on single-root and A/B installations
that include the new update bootstrap. This is an application-code update,
not a conversion to A/B or an authorization to rewrite a live Linux image.
An old installation without this updater does not advertise the package API.
A package cannot create a missing service/API; use a current installer/reimage
or, on an already supported A/B installation, its existing full-system
upgrade route. For the frozen 1275-era receiver that already has the package
API but rejects language JSON destinations, the source-owned
`build-receiver-bridge` command may build a one-time code-only package from
that exact source base, after confirming the installed application matches
that source. It replaces the complete declared Python/runtime snapshot with
the frozen base snapshot and overlays only the package reader and generation
validator. Never use it on an arbitrary supported image or a newer application
generation. After its normal application-generation health acceptance, a
second current Python/combined package may deliver language resources. This
exception does not bootstrap an installation lacking the existing updater.

## Parent interaction and ownership

The authenticated **Upload & install** action authorizes receipt and subsequent
application. Greia acknowledges only after the complete transfer and job are
durable. Inspection, validation, waiting for an idle child session, applying,
restart/health checks and recovery belong to the installed OS. No catalog,
Internet access, second authorization after validation, open Parent app or
continuing phone connection is required after acknowledgement.

A durable bounded job supplies status on reconnection. Interruption before
acceptance never publishes an incomplete package. Parent-process death after
acceptance must not strand an authorized job: installed boot/service
reconciliation owns continuation independently of that process.

The child is not interrupted automatically. Application-code activation waits
for the real profile picker and uses the existing session lock/fence so a new
child activation cannot race the switch. Full-system installation may prepare
the inactive slot and wait for a separately explicit restart.

## Application publication and recovery

Do not expand new code file-by-file over running code. Stage and validate the
complete declared change first. Publish a complete application generation by
an atomic pointer switch; unchanged assets may be reused without duplicating
their bytes. Combined Python/Activity changes use the same transaction so
partially updated code and Activities are not exposed together.

Python and combined packages include the complete managed language-resource
snapshot under `src/greia_platform/languages/`: paired canonical locale
`manifest.json` and `ui.json` files, English required, and at most 32 offered
locales. Manifest-less staging scaffolds are not offered or packaged. The
receiver validates the staged locale order and UI schema, English key coverage
and interpolation placeholders before switching the pointer. Stale managed
locale JSON is removed only from the private candidate generation; unrelated
files and data outside the application generation remain untouched.

Preserve the previous application generation through startup acceptance.
Broken replacement code or interrupted activation restores it. Bootstrap and
recovery code must be available outside the replaceable application code, so
replacing the Parent/platform/launcher cannot remove the mechanism needed to
finish or recover that replacement. Persist the transition before any
first-install directory-to-pointer migration; boot recovery closes that gap.

Use existing Activity manifests, source/import/capability/path/footprint
validation and trust-source distinctions. A built-in Activity update stays in
the built-in source; a Parent-installed Activity retains its existing source.
One/set/all packages update their listed IDs; built-in “all” is derived from
the validated current built-in registry or exact installed Activity index,
not a draft future-release roster. Missing/unlisted Activities are not deleted. Profiles, creations,
saves, credentials and settings are outside the application payload and are
never replaced by these packages.

## Reliability scope and acceptance

Keep bounded archive extraction, disk-space checks, compatibility, syntax and
Activity validation, interruption recovery, idle activation and startup
rollback. Use hashes only for transfer corruption/debugging. No signatures,
release keys, anti-tampering framework or hostile-local-user threat model is
introduced.

Source tests must cover durable acknowledgement, continuation after Parent
termination, all package types, single-root application updates, incompatible
and truncated packages, startup failure, interruption recovery, preservation
of unlisted Activities and child data, and bounded streaming. Actual Linux
service/bootstrap/installed acceptance is a separate evidence tier. The owner
has directed those builds/installs/tests to another machine with committed
precise instructions; source checks do not certify that tier.

## Continuation authority

The 2026-09-15 lifecycle plan remains authoritative. This owner-approved
application-update scope extends that route; it does not close Session 04 or
create a competing plan. Update its ledger and HANDOVER with actual source
and test evidence, and maintain one operator guide for building/applying the
new package types.
