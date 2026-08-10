# Greia OS

**Project stage:** early platform development  
**Version family:** `0.13.x` development  
**Documentation reviewed:** 2026-08-10

Greia is a non-profit, open-source, Activity-first educational computing platform for young children. Linux is the implementation substrate; **Greia Shell is the operating-system experience**.

During normal child use Linux must disappear: no desktop, terminal, login prompt, package manager, filesystem browser, browser chrome, generic window manager, or boot text should become part of the supported child experience.

The project deliberately targets very constrained hardware. The first-generation Acer Aspire One remains the extreme low-resource reference; Raspberry Pi 400 and Raspberry Pi 500 are co-equal ARM reference targets. Exact current implementation, verification and hardware-evidence state belongs in `HANDOVER.md`, not in this README.

---

## Start here

The documentation is intentionally split by authority and freshness.

1. **`AGENTS.md`** — repository-wide non-negotiable engineering/agent rules.
2. **`docs/DOCUMENTATION.md`** — which document owns which kind of truth and how to resolve drift/conflicts.
3. **`docs/architecture/GREIA_ARCHITECTURE.md`** — living architecture overview/synthesis.
4. **accepted ADRs under `docs/adr/`** — normative architecture decisions.
5. **`docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`** — mandatory Phase-0 writing and painting product requirement.
6. **`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`** — mandatory active implementation plan until its closure criteria are satisfied.
7. **`HANDOVER.md`** — current branch, implementation, verification/evidence boundary, blockers and exact next step.
8. **`docs/agents/GREIA_AGENT_OPERATIONS.md`** — project/build/test-hardware operating manual for agents.
9. **`skills/greia-activity-authoring/SKILL.md`** — canonical Activity-authoring skill.

Do not use this README as a substitute for the current handover.

---

## Product model

Greia is closer to a console or dedicated educational computer than to a simplified desktop distribution.

```text
power on
   ↓
continuous Greia-branded boot/recovery surface
   ↓
child profile picker
   ↓
Greia Shell / child world
   ↓
choose Activity
   ↓
supervised Activity runtime
   ↓
return safely to Greia Shell
```

The stable product abstraction is **Activity**, not “Python app”, “HTML game” or “Linux program”.

```text
Greia Platform
    │
    ├── Profiles / parent policy
    ├── Storage / sessions / progression / rewards
    ├── Permissions / package / backup services
    ├── Device capability / hardware adapters
    ├── Greia Shell
    │
    └── Activity Runtime Manager
           ├── Python/Pygame — implemented first runtime
           ├── Web — planned, engine not yet selected
           └── future runtimes
```

An Activity keeps one platform identity, save namespace, lifecycle, permission model, progression integration and package identity regardless of runtime.

---

## Creative computing from the beginning

The first user-ready Phase-0 Greia image is required to include two first-party built-in creative Activities:

- **Writing** — a simple child-first text editor;
- **Painting** — a simple child-first painting/drawing Activity.

These are baseline Greia product capabilities, not optional demos or later ecosystem extras.

A first source tranche now exists on the active development branch:

```text
activities/writing/
activities/painting/
src/greia_platform/activity_ui.py
```

Writing currently implements a large uncluttered text surface, large readable text by default, multiline/caret navigation, bounded undo, visual gallery and automatic profile-scoped UTF-8 saving. Painting currently implements a large canvas, cheerful palette, three brush sizes, eraser, bounded stroke undo, visual gallery and automatic profile-scoped PNG saving.

They request no privileged permissions and use Greia lifecycle/Storage contracts rather than desktop file workflows.

The first genuinely shared child-UI primitives also now exist in `src/greia_platform/activity_ui.py`: 1024×600-first metrics, cached semantic icons, large rounded icon buttons and a few small shared symbols. This is **deliberately not a general widget toolkit**. Further primitives should be extracted from real repeated Activity needs, not designed speculatively.

Exact product and current acceptance state:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
HANDOVER.md
```

The current source tranche is **not yet execution/hardware evidence**. R7 remains the blocking architecture phase, and final Phase-0/user-ready-image acceptance remains incomplete until both creative Activities pass real low-end visual/input/storage/performance acceptance.

---

## Architectural principles

The accepted architecture is defined by ADRs, especially:

- `docs/adr/0012-platform-architecture-constitution.md` — platform constitution;
- `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md` — declarative image composition;
- `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md` — Greia identity, ARM parity and direct-graphics direction;
- later accepted ADRs that narrow the platform services/runtime/security model.

Important durable principles include:

- Greia Shell, not Linux desktop UI, is the child-facing OS;
- Activity is runtime-neutral;
- global progression/reward economics belong to Greia;
- durable Activity data is profile/activity scoped and architecture-neutral;
- core child operation is offline-first;
- ARM and legacy x86 are peers behind common platform contracts;
- resource cost is part of architectural correctness;
- Activities use a curated runtime and may not install private dependencies;
- privileged authority stays outside Activity processes;
- installation and destructive operations fail closed.

For precedence and current-vs-conceptual examples, read `docs/DOCUMENTATION.md`.

---

## Graphics direction

Greia is not intended to depend architecturally on a conventional desktop display stack.

The target direction is appliance-oriented:

```text
Linux kernel + drivers
        ↓
DRM/KMS / GPU backend
        ↓
minimal Greia-owned display/session layer
        ↓
Greia Shell or supervised Activity
```

**Current implementation note:** the installed production path still uses an explicit Xorg/xinit compatibility backend while the direct/session architecture is measured and proven. That backend is **PROVISIONAL**, not an Activity API and not permission to deepen X11 dependence.

A small compositor/session broker may be selected only if evidence shows that it improves surface ownership, transitions, crash recovery, Web integration or input routing at acceptable resource cost.

Exact current R7 status and evidence live in `HANDOVER.md`.

---

## Hardware strategy

Greia designs around capability/resource classes rather than CPU family alone.

Reference families include:

- legacy Atom/i386 netbook — extreme low-resource floor;
- modern amd64 PC — compatibility/development reference;
- Raspberry Pi 400 — ARM64 reference;
- Raspberry Pi 500 — ARM64 reference.

The Acer floor is currently estimated around 768 MiB RAM, approximately 7 GB storage and 1024×600 until exact hardware inventory supersedes those estimates. The current C0 installed-core policy targets a preferred ≤800 MiB and requires <1,000 MiB; exact measured certification remains an evidence task.

Do not treat source tests, QEMU results or a modern development PC as proof of physical legacy-hardware acceptance.

---

## Activity development

Use:

```text
skills/greia-activity-authoring/SKILL.md
```

It is the maintained agent/developer guide for:

- `activity.toml` and current validation rules;
- Python runtime/import policy;
- lifecycle READY/STOP handling;
- Greia Storage and event APIs;
- capabilities, permissions and trust;
- shared semantic icons/theme integration;
- the current small shared Activity UI layer;
- 1024×600 child UX;
- low-end performance/optimization;
- validation and remote deployment/testing.

The exact implemented Activity schema/API is owned by source/runtime declarations listed in `docs/DOCUMENTATION.md`. Conceptual YAML/Web/package examples in architecture documents are not current Python authoring specifications.

---

## Developer/test hardware control

The explicit developer profile supports a development-only remote test console intended to make routine netbook testing possible from the operator computer after power-on.

Start with:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

The developer control path includes bounded status/log/screenshot/input/deploy/service/power operations and an explicit maintenance SSH shell. Normal/release Greia does not inherit that access merely because the source exists.

First-time remote graphical installer provisioning remains subject to the exact current boundary recorded in `HANDOVER.md`; no unattended destructive install shortcut is an accepted substitute.

---

## Build and verification

The canonical provider-free source gate is:

```bash
make verify
```

It covers unit tests, project/Activity validation, shell checks and source footprint checks.

For image/hardware work, use the exact applicable procedure under `docs/testing/`. Source verification never substitutes for VM/physical evidence.

**GitHub-hosted execution is not implicitly authorized.** Repository policy in `AGENTS.md` requires explicit owner authorization for hosted/paid execution; normal source persistence/review through GitHub remains expected.

---

## Repository map

- `AGENTS.md` — repository-wide engineering/agent contracts.
- `HANDOVER.md` — current continuation/evidence snapshot.
- `docs/DOCUMENTATION.md` — documentation ownership, precedence and freshness rules.
- `docs/product/` — explicit child-facing product/UX requirements, including mandatory Phase-0 core creation Activities.
- `docs/architecture/` — living architecture synthesis.
- `docs/adr/` — accepted/proposed architecture decisions.
- `docs/plans/` — active and historical implementation plans.
- `docs/reviews/` — dated reviews/evidence snapshots.
- `docs/testing/` — exact operator/evidence protocols.
- `docs/agents/` — agent operational manuals.
- `skills/` — reusable project skills, including Activity authoring.
- `src/greia_platform/` — shared platform contracts/services, including the narrow shared Activity UI primitives.
- `src/greia_launcher/` — child shell and Activity supervision.
- `src/greia_parent/` — bounded parent-management service.
- `src/greia_installer/` — graphical installer/whole-disk engine.
- `activities/` — curated built-in Activities, including Writing and Painting source tranches.
- `assets/` — canonical shared visual assets/catalogues.
- `runtime/` — curated runtime and policy declarations.
- `build/` — profiles, package sets, overlays and builders.
- `tools/` — validation/developer/evidence tooling.
- `tests/` — provider-free source/contract tests.

---

## Naming

- **Greia** — project/platform/ecosystem
- **Greia OS** — installable operating-system image and underlying system
- **Greia Shell** — child-facing graphical operating environment
- **Greia Parents** — parental-management surface
- **Greia SDK** — Activity-facing APIs and developer tooling
- **Professor Pip** — optional recurring child-facing guide/character, never the technical platform identity

---

## License

Greia is intended to be non-profit and open source. A project-wide license must be selected before public release; the repository remains private during early development.
