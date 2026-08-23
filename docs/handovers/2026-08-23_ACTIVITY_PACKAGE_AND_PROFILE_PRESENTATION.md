# Handover — `.greiaactivity`, profile presentation, and Parent management integration

Date: 2026-08-23

Canonical branch: `main`

Status: **feature source is merged on `main`; the redesigned Parent HTML runtime is reviewed and pinned from Greia `main`. Continue all work directly on `main` unless the owner explicitly requests a branch.**

## Scope

This tranche established three connected product seams:

1. a recognizable single-file Activity distribution format for Parent clients;
2. a small optional child presentation preference for theme seeding and grammatical agreement;
3. the browser Parent management surface required to install/remove Activities and manage the presentation preference.

## `.greiaactivity` package contract

Canonical Parent-facing format:

```text
extension:  .greiaactivity
container:  ZIP
media type: application/vnd.greia.activity+zip
manifest:   activity.toml at archive root
```

Activity contents live directly at ZIP root with no wrapping directory.

Extension and MIME are UX/file-routing hints only. They never establish validity or trust. `ActivityPackageService` remains authoritative for bounded extraction, path checks, manifest validation, runtime compatibility, collision handling, trust source, and activation.

Parent-installed packages are distinct from built-ins. The Parent API exposes package origin/removability so the client does not infer it from names or filesystem paths.

### Removal

`ActivityPackageService.uninstall(activity_id)` removes only Parent-installed package code. Built-in Activities are not removable through this service. Profile-scoped child saves/progress are outside the package transaction and are deliberately preserved.

Package update/replacement/rollback remains separate R10 work.

Normative package documentation:

- `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`
- `docs/product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md`

## Child presentation and grammatical agreement

Presentation is a customization-side preference:

```text
neutral
boy
girl
```

Derived grammatical selector:

```text
neutral -> neutral
boy     -> masculine
girl    -> feminine
```

It must never alter Activity eligibility, discovery, difficulty, permissions, progression, rewards, or inferred interests.

Theme seeding is initial-only:

```text
neutral -> normal default, no redundant theme file
boy     -> sky / turquoise / navy
girl    -> lavender / raspberry / plum
```

A seed is written only when no saved theme exists. Changing presentation later never overwrites a customized theme.

Localization supports bounded semantic variants such as:

```text
feedback.correct
feedback.correct.masculine
feedback.correct.feminine
```

Resolution is per locale: requested variant, then same-locale base, then locale fallback. Text and prerecorded audio for one cue use the same resolved variant. Neutral natural wording remains the preferred baseline where practical.

Normative presentation documentation:

- `docs/adr/0032-profile-presentation-and-grammatical-agreement.md`

## Parent API integration

The Parent protocol defines:

```text
GET/PUT /api/v1/profiles/{profile_id}/presentation
DELETE  /api/v1/activities/{activity_id}
```

Relevant capabilities remain fail-closed in the base protocol and are enabled only by concrete compositions that own the implementation:

```text
profiles.presentation
activities.install
activities.remove
```

Install/remove share the same explicit package-mutation enablement boundary while provisional Parent HTTP transport remains in development.

## Parent HTML application

Canonical repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Canonical development branch:

```text
main
```

The Parent browser app is now a four-job management application:

```text
Home
Children
Activities
This Greia
```

Desktop uses a persistent left rail; mobile uses a bottom navigation. Activities provides search/filtering, per-child visibility, `.greiaactivity` installation, and removal of Parent-installed packages. Children exposes capability-gated Neutral/Boy/Girl Style & wording. This Greia groups the existing typed device controls into System, Network & language, Input/display/sound, and Security & access.

### Reviewed runtime

Reviewed Parent runtime revision:

```text
f64067b093c222fd9e659589617ff867c207572c
```

Validation completed for that runtime:

```text
npm test: 45 / 45 PASS
browser console/page errors: 0
horizontal overflow: 0 at desktop and phone widths
```

Browser interactions exercised Activity install, list refresh, search/filter, removal confirmation/removal, and the child presentation editor.

Core Greia `main` pins that exact reviewed revision through:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The pin generator derives the complete transitive runtime closure from `index.html` and local ES-module/style references, rather than reusing a stale file inventory. Remote runtime dependencies are rejected.

## Important architectural rules

- `main` is the source of truth; historical work branches are not development authority.
- Do not hand-edit generated Parent integrity data when an exact checkout/pin flow is available.
- The browser never becomes a Linux administration layer.
- Greia remains authoritative for package validation/trust and profile storage.
- Child presentation remains presentation/grammar only, never content stereotyping or eligibility logic.
- Parent Activity removal preserves child data.
- No hosted GitHub Actions should be triggered or queried without explicit owner authorization.

## Remaining work

Separate future work includes:

- package update/replacement/rollback;
- signed/provenance-rich Activity catalogue flows;
- production encrypted Parent transport and final pairing security;
- backup/restore management;
- richer Activity detail/provenance views;
- optional future native Parent companion clients.
