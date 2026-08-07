# Greia

**Greia** is a non-profit, open-source child-first computing platform built around curiosity, creativity, experimentation, and play.

Greia is not a conventional Linux desktop distribution. Linux provides the kernel and minimal underlying userspace; Greia provides the complete child-facing graphical environment, activity platform, profile system, parental controls, progress and reward services, storage, backup/restore, package management, and hardware abstraction.

From a child's perspective, the machine boots directly into Greia. There is no desktop, shell, package manager, browser chrome, or conventional Linux UI to learn or escape into during normal use.

## Core idea

Greia is **activity-first and runtime-agnostic**.

An activity is a platform object with one universal manifest, lifecycle, storage model, scoring/progress integration, permissions model, installation/update path, and parental-policy surface. Whether that activity happens to run through Python/Pygame, an embedded Web runtime, or a future runtime is an implementation detail below the activity abstraction.

The same Greia experience is intended to run across radically different hardware, including old i386 netbooks and ARM devices such as the Raspberry Pi 400 and Raspberry Pi 500. Hardware architecture must not leak into the child or parent experience.

## Project status

Greia is currently in architecture and early platform-design work. Some implementation choices remain research questions and are deliberately marked as such in the architecture documentation.

The canonical living architecture is:

- [`docs/architecture/GREIA_ARCHITECTURE.md`](docs/architecture/GREIA_ARCHITECTURE.md)

Historical/design-session records are retained under:

- [`docs/decisions/`](docs/decisions/)

## Naming

The project and platform are **Greia**.

Where a distinction is useful:

- **Greia** — project/platform/ecosystem
- **Greia OS** — the installable operating-system image and underlying system
- **Greia Shell** — the child-facing graphical OS environment
- **Greia Parents** — parental-management surface
- **Greia SDK** — developer-facing activity APIs and tooling
- **Professor Pip** — a character/guide inside the child experience, not the platform brand

## Principles in one paragraph

Greia should feel like a console or purpose-built children's computer, not a reduced desktop PC. It should boot into its own graphical world, make Linux disappear during normal use, treat all activities uniformly, own progression and profile data at the platform level, make saves and backups portable across machines and CPU architectures, make activity installation and updates understandable to parents, remain offline-first, avoid unnecessary desktop layers, support very old hardware without limiting richer hardware, and keep its formats and code open.

## License

A project-wide open-source license will be selected before public release. The repository is private during early design work.