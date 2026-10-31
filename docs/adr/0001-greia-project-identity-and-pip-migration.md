# ADR 0001 — Greia Project Identity and Pip-Era Migration

**Status:** Accepted  
**Date:** 2026-08-08

## Context

The project began under working names centered on “Pip Kids OS” and Professor Pip. During architecture work it became clear that Professor Pip is a character/world element while the project itself is a broader child computing platform.

The platform was conceived as a community-oriented open-source project; this historical statement does not claim incorporation as a nonprofit or restrict licensing-compliant independent commercial distribution. The selected project identity is **Greia**, a family-inspired name derived during project brainstorming.

A blind textual replacement of every historic `Pip` identifier would be unsafe because some identifiers may already be compatibility boundaries for saves, Activity IDs, paths, or tests.

## Decision

The canonical platform/project name is **Greia**.

Use these names in new architecture and user-facing work:

- Greia — platform/ecosystem/project;
- Greia OS — installable operating-system image/system where a distinction is useful;
- Greia Shell — child-facing graphical operating environment;
- Greia Parents — parent-management surface;
- Greia SDK — developer APIs and tooling;
- Greia Activity — runtime-neutral content package.

Professor Pip remains available as a child-facing character and guide. It is not the operating-system brand.

Historic Pip-era implementation identifiers must be migrated deliberately. Stable persisted IDs and save compatibility boundaries must not be renamed without migration logic and tests.

New file/package/namespace identifiers should use Greia naming unless compatibility requires otherwise.

## Rationale

Separating the platform brand from one character allows Greia to support multiple worlds, characters, educational styles, age ranges, and future runtimes without rebranding the system.

A deliberate migration policy prevents cosmetic rebranding from destroying progress or breaking old Activity packages.

## Consequences

- New documentation uses Greia terminology.
- Pip-era documents are historical sources, not current naming authority.
- Future source migration must inventory persisted/public identifiers before renaming.
- Professor Pip content can continue naturally inside Greia.
- Package extensions proposed under old names, such as `.pipactivity` and `.pipbackup`, are design history; Greia-native format ADRs should select final extensions such as `.greiaactivity` / `.greiabackup` or another explicitly chosen form.
