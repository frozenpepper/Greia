# Greia

**Greia** is a non-profit, open-source child-first computing platform built around curiosity, creativity, experimentation, and play.

Greia is not a conventional Linux desktop distribution. Linux provides the kernel and minimal underlying userspace; Greia provides the complete child-facing graphical environment, Activity platform, profile system, parental controls, progress and reward services, storage, backup/restore, package management, and hardware abstraction.

From a child's perspective, the machine boots directly into Greia. There is no desktop, shell, package manager, browser chrome, or conventional Linux UI to learn or escape into during normal use.

## Core idea

Greia is **Activity-first and runtime-agnostic**.

An Activity is a platform object with one universal manifest, lifecycle, storage model, scoring/progress integration, permissions model, installation/update path, and parental-policy surface. Whether an Activity happens to run through Python/Pygame, an embedded Web runtime, or a future runtime is an implementation detail below the Activity abstraction.

The same Greia experience is intended to run across radically different hardware. ARM and i386 are co-equal first-class targets: old Atom-class netbooks remain a hard low-resource reference class, while Raspberry Pi 400 and Raspberry Pi 500 are explicit ARM reference devices. Hardware architecture must not leak into the child or parent experience.

## Project status

Greia is currently consolidating the architecture and implementation created during its Pip Kids OS prototype phase.

The canonical living architecture is:

- [`docs/architecture/GREIA_ARCHITECTURE.md`](docs/architecture/GREIA_ARCHITECTURE.md)

Architecture decisions are recorded under:

- [`docs/adr/`](docs/adr/)

Repository-wide contributor/agent contracts are in:

- [`AGENTS.md`](AGENTS.md)

Historic Pip-era source and documentation remain valuable migration material, but they are not automatically current Greia authority where superseded by the Greia constitution or newer ADRs. In particular, historic Xorg work is provisional/history; X11 is not an intended Greia architectural layer.

## Naming

The project and platform are **Greia**.

Where a distinction is useful:

- **Greia** — project/platform/ecosystem
- **Greia OS** — installable operating-system image and underlying system
- **Greia Shell** — child-facing graphical OS environment
- **Greia Parents** — parental-management surface
- **Greia SDK** — developer-facing Activity APIs and tooling
- **Professor Pip** — a character/guide inside the child experience, not the platform brand

## Principles in one paragraph

Greia should feel like a console or purpose-built children's computer, not a reduced desktop PC. It should boot into its own graphical world, make Linux disappear during normal use, treat all Activities uniformly, own progression and profile data at the platform level, make saves and backups portable across machines and CPU architectures, make Activity installation and updates understandable to parents, remain offline-first, avoid unnecessary desktop layers, support very old hardware without limiting richer hardware, and keep its formats and code open.

## License

A project-wide open-source license will be selected before public release. The repository is private during early design work.