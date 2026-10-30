# Greia Activity package format (`.greiaactivity`)

Status: **v1 distribution contract — implemented for new installs; package update/rollback remains R10 work**

Date: 2026-08-23

Related authority:

- `docs/adr/0015-activity-identity-capabilities-permissions-and-events.md`
- `docs/adr/0023-open-activity-ecosystem-and-official-catalogue-boundary.md`
- `docs/product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md`
- `src/greia_platform/activity_packages.py`
- `src/greia_platform/activity_package_format.py`

## Purpose

A Greia Activity should be easy to distribute as one file that a Parent client can identify in a file picker and hand to Greia for installation.

The v1 distribution format is intentionally simple:

> **A `.greiaactivity` file is an ordinary ZIP archive with Greia's normal Activity package tree at the archive root.**

No proprietary compression or binary wrapper is added.

The custom extension is a product/distribution signal. It is **not** a security boundary and is never proof that an archive is valid or trusted.

## Stable identifiers

| Property | v1 value |
| --- | --- |
| File extension | `.greiaactivity` |
| Container | ZIP |
| Media type | `application/vnd.greia.activity+zip` |
| Required root manifest | `activity.toml` |
| Manifest/runtime contract | normal Greia Activity contract |

Canonical constants live in `src/greia_platform/activity_package_format.py` so the OS, tools, simulator, and Parent surfaces do not invent parallel spellings.

## Archive layout

The contents of the Activity directory are stored directly at ZIP root. Do **not** add an extra wrapping directory.

Correct:

```text
my-activity.greiaactivity
├── activity.toml
├── main.py                 # or the declared runtime entrypoint
├── assets/
│   ├── icon.png
│   └── ...
├── locales/
│   ├── en.json
│   └── it.json
└── audio/
    └── ...
```

Incorrect:

```text
my-activity.greiaactivity
└── my-activity/
    ├── activity.toml
    └── ...
```

The canonical installer requires `activity.toml` at archive root.

## What the extension means

The extension exists so that:

- desktop/mobile Parent clients can use a narrow file picker;
- parents can distinguish Activity packages from ordinary ZIP files;
- share sheets and future platform integrations have one recognizable type;
- documentation and tooling have one stable distribution name.

Parent clients should normally offer only `.greiaactivity` in the Activity-install picker.

Developer/simulator tools may also accept raw Activity directories or `.zip` for convenience, but those are development input forms, not the normal parent-facing distribution contract.

## What the extension does *not* mean

Renaming `anything.zip` to `anything.greiaactivity` does not make it a valid Greia Activity.

Greia does not derive trust from:

- extension;
- MIME/media type supplied by a browser;
- original filename;
- the fact that a ZIP can be opened successfully.

The Parent HTTP upload currently carries raw bytes and may receive generic ZIP/octet-stream transport media types for compatibility. The receiving service still sends those bytes through the same canonical package validation path.

## Installation validation and security

`ActivityPackageService` remains the authoritative new-install boundary. Before activation it performs bounded ZIP inspection/extraction and normal Activity validation, including protections against archive traversal, unsafe/special entries, unsupported file types, collisions, package-size/decompression abuse, malformed/missing root manifests, invalid Activity manifests, package-owned resource errors, and identity collisions.

The install transaction then publishes validated package state through Greia's existing package trust and atomic activation model.

The custom extension must never replace or weaken those checks.

## Package ownership and immutability

A `.greiaactivity` contains Activity-owned code and resources. Runtime-generated profile state does not belong in the package.

Do not include:

- child saves/progress;
- profile customizations;
- machine hardware configuration;
- Parent credentials;
- generated caches;
- virtual environments;
- source-control metadata;
- build-machine absolute paths.

The installed package is treated as immutable executable/resource content. Per-profile durable state continues to use Greia's storage service.

## Localization and audio

Localized bundle/audio assets are normal files inside the package. No special outer packaging rule is needed.

For child-directed grammatical agreement, use ADR 0032 and the Activity authoring skill. A cue may contain a neutral base plus optional semantic `masculine` / `feminine` variants. Those resources remain ordinary files and localization entries inside the same `.greiaactivity` archive.

## Versioning

The `.greiaactivity` outer container currently has no independent format-version header. Compatibility is governed by the package's normal `activity.toml` contract, including the Activity/runtime API version and Activity version.

This is deliberate: v1 should not duplicate version authorities.

If a future outer-container feature genuinely cannot be represented safely by the manifest/package contract (for example a signed envelope), it should be introduced through a new reviewed ADR and migration path rather than silently changing ZIP semantics.

## Installation vs update

The v1 file format is the distribution container for both initial packages and future Activity versions, but **safe package update/rollback policy is a separate lifecycle concern**.

As of this document:

- canonical new install is implemented;
- the Parent upload/install seam is advertised when the real package store is writable and the operator has not disabled it; installs and removals require the profile picker and hold the shared profile-session lock;
- replacement/update, migration, rollback, and recovery remain part of R10 completion work.

Consumers must not infer that because they can parse `.greiaactivity`, arbitrary replacement of an installed Activity is safe.

## Authoring/export rule

The exported filename should end in `.greiaactivity`; `src/greia_platform/activity_package_format.py` provides `ensure_activity_package_filename()` for tooling that needs the canonical name.

When building the archive, package the **contents** of the Activity directory, not the directory itself. The resulting archive should contain `activity.toml` directly at root.

Before distribution, validate the source Activity and exercise the produced archive through Greia's package validation/install test path. Do not treat a successful ZIP creation as package validation.

## Parent client rule

A normal Parent install picker should use:

```text
.greiaactivity,application/vnd.greia.activity+zip
```

and reject a generic `.zip` selection in the UI with a clear message.

This improves UX only. Server-side validation remains authoritative.
