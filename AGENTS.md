# AGENTS.md — Greia Project Contracts

This file defines repository-wide rules for contributors and coding agents.

## 1. Read order

Before changing architecture or implementation, read:

1. `README.md`
2. `docs/architecture/GREIA_ARCHITECTURE.md`
3. relevant ADRs under `docs/adr/`
4. the active implementation plan, when present

## 2. Product invariants

Greia is a child-first computing platform, not a themed Linux desktop.

Contributors MUST preserve these invariants unless a superseding ADR explicitly changes them:

- Linux is an implementation substrate; the Greia Shell is the child's operating-system experience.
- Normal child use exposes no desktop environment, login prompt, terminal, shell, package manager, filesystem browser, browser chrome, or conventional window-management UI.
- `Activity` is the universal content abstraction. Python, Web, and future runtimes are implementation adapters below the Activity contract.
- Profiles, storage, sessions, progression, rewards, installation, updates, backup/restore, permissions, and parent controls are platform services and MUST NOT fork by runtime family.
- ARM and i386 are co-equal first-class architecture targets. Raspberry Pi 400 and Raspberry Pi 500 are reference ARM devices; old Atom-class netbooks remain a hard low-resource reference class.
- Activity manifests target capabilities and compatibility classes, not CPU architectures, except where native code makes architecture declarations genuinely unavoidable.
- Durable user data MUST remain portable across CPU architectures.
- Parent management is a separate trust/authority surface, not a privileged child Activity.
- Removable media is never autorun. Media insertion may trigger bounded scanning and parent-facing install/update prompts only.
- Activity installation and updates are transactional and fail closed.
- Uninstalling an Activity MUST NOT destroy child saves by default.
- Global progression/reward authority belongs to Greia, not to Activity code.
- Greia is offline-first; cloud services may extend but may not become the only owner of child identity or saves.
- Package and backup formats should remain documented, inspectable open formats.

## 3. Graphics and display direction

Do NOT introduce X11, a desktop environment, or a general-purpose window manager as a new architectural dependency.

Historic Pip-era Phase-0 work used Xorg provisionally. That implementation is evidence/history, not the intended Greia architecture.

The Greia direction is a minimal direct graphics/input stack built around Linux DRM/KMS and suitable input/audio interfaces, with the Greia Shell owning the graphical session. SDL/Pygame and the future embedded Web runtime should use the thinnest practical platform paths.

If a tiny compositor or other display component is proposed, it must justify its RAM, disk, latency, compatibility, isolation, and maintenance cost with evidence. "Desktop Linux normally uses it" is not sufficient.

## 4. Runtime policy

Python is a first-class runtime family. Web is intended to become a first-class runtime family after measured engine selection.

Activities MUST NOT bring private operating-system-level dependency managers into the child system. For Python this means no per-Activity venv/pip/uv/poetry/conda dependency environment. For Web this means no bundled browser executable or Node/npm runtime on the child machine.

Runtime adapters are platform-owned and curated.

## 5. Old-hardware discipline

Resource use is an architecture concern.

New platform dependencies must be evaluated for:

- installed-size delta;
- idle and peak RAM;
- launch latency;
- steady-state CPU;
- graphics compatibility;
- i386 availability where relevant;
- ARM64 availability and Raspberry Pi behavior;
- update/security maintenance burden.

Do not weaken the low-end reference target merely to simplify implementation.

## 6. Architecture vs evidence

Never claim hardware/runtime behavior from source structure alone.

Use these labels in design work where useful:

- **CONSTITUTIONAL** — stable platform contract;
- **SELECTED** — implementation chosen by ADR;
- **PROVISIONAL** — development/evidence implementation, not final;
- **DEFERRED** — intentionally outside the active phase;
- **UNPROVEN** — designed/implemented but missing required runtime or hardware evidence.

## 7. Code quality

Prefer clean OOP boundaries, typed interfaces, dependency injection at architectural seams, and polymorphism where multiple runtimes/platform adapters exist.

Do not duplicate runtime-specific versions of platform services.

Avoid procedural sprawl and configuration encoded as executable shell when a typed declarative representation is appropriate.

Use existing abstractions before inventing new ones.

## 8. Repository as source of truth

Substantive Greia architecture, implementation, plans, and handovers should be committed to this repository as work proceeds. Chat transcripts are not the canonical specification.