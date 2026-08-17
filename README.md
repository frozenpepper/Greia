# Greia OS

**Stage:** early platform development (`0.13.x`)  
**Docs reviewed:** 2026-08-17

Greia is a non-profit, open-source, Activity-first computing platform for young children. Linux is the substrate; **Greia Shell is the operating-system experience**. Normal child use must not expose a desktop, terminal, login prompt, package manager, filesystem browser, browser chrome, generic window manager, or boot text.

Greia deliberately targets constrained hardware, with the first-generation Acer Aspire One as the extreme low-resource reference and Raspberry Pi / modern x86 systems behind the same platform contracts.

## Start here

1. `AGENTS.md` — non-negotiable repository rules.
2. `docs/DOCUMENTATION.md` — authority, ownership and freshness.
3. `docs/architecture/GREIA_ARCHITECTURE.md` — living architecture synthesis; `docs/architecture/GREIA_PARENT_MANAGEMENT.md` narrows the parent-management subsystem.
4. `docs/adr/` — accepted normative decisions; ADR 0018 owns lightweight UI, ADR 0019 trusted Activity Home/Back, ADR 0020 runtime-neutral input/controller support, ADR 0021 automatic hardware enablement, and ADR 0022 the Parent API/client/pairing/privilege boundary.
5. `docs/engineering/ENGINEERING_FOUNDATIONS.md` — mandatory OOP, polymorphism, dependency, documentation and low-resource guidance.
6. `docs/product/` — accepted product requirements, including Activity navigation/input and `PARENT_MANAGEMENT.md` for Greia Parents.
7. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` — active implementation plan until closed.
8. `HANDOVER.md` — exact current branch, evidence, blockers and next step.
9. `docs/agents/GREIA_AGENT_OPERATIONS.md` — build/test-hardware operations.
10. `skills/greia-activity-authoring/SKILL.md` — Activity-authoring guide.

Current verification counts, branch SHAs and hardware status belong in `HANDOVER.md`, not here.

## Core model

The stable product abstraction is **Activity**, independent of runtime. Greia owns profiles, storage, sessions, permissions, progression, backup, lifecycle, standard input behavior and parent policy.

The child UI is appliance-like, not desktop-like. ADR 0018 defines the small renderer-neutral vocabulary:

```text
Screen
  └── optional Overlay / Sheet
        └── Panel / Card / Collection
              └── Control
```

A child-visible “folder” is a semantic `Collection`, never a Linux path. `src/greia_platform/ui_core.py` owns renderer-neutral UI semantics/navigation/resource bounds. New shared Pygame consumers import `src/greia_platform/pygame_ui.py`; existing first-party Activities retain `activity_ui.py` as the compatibility implementation surface. This is deliberately not a universal widget framework.

### Universal way home

Every child-facing Activity must retain the same small Greia-owned **Home** affordance in the same place. Activity code cannot hide, restyle, cover, intercept or disable it. Home ends the Activity through Greia's authoritative lifecycle and returns to the child Shell. Greia may also show a platform-owned **Back** control when there is a meaningful previous Greia screen/Collection; it is never browser history or Activity-defined navigation.

The product requirement is `docs/product/ACTIVITY_SYSTEM_NAVIGATION.md`; ADR 0019 makes trusted system chrome and protected input an R7 display/session acceptance requirement. Renderer-neutral geometry/actions live in `src/greia_platform/system_chrome.py`, with the backend lifecycle seam in `src/greia_launcher/system_chrome.py`.

### Learned input across Activities

Controller/joystick support is part of Phase 0, but Activities do not code against controller brands or Linux device paths. ADR 0020 defines runtime-neutral interaction profiles such as `pointer`, `directional`, `game` and `text`.

The simple game baseline is deliberately learnable: **arrow keys + Space** on keyboard, and **D-pad/left stick + south face button** on a controller. Pointer Activities can receive a Greia virtual pointer from the controller rather than becoming controller-specific. Keyboard, pointer, touch and controller can coexist.

`src/greia_platform/input_core.py` owns current semantic mappings/dead-zone/virtual-pointer rules; `src/greia_platform/pygame_input.py` is a Pygame translation/trusted-controller helper. Physical controller authority and reserved system input remain Greia platform concerns, not ordinary Activity `/dev/input` access.

### Greia Parents: web first, one protocol

**Greia Parents** is the parent-management product surface. The first client is a small responsive HTML application served directly by each Greia machine, but the durable product boundary is the versioned **Greia Parent API**, not the HTML implementation.

ADR 0022 requires any future phone/desktop client to use the same discovery, pairing, per-device credentials, capability model and semantic API. Normal network-capable Greia advertises `_greia-parent._tcp` through mDNS/Bonjour. The initial API namespace is `/api/v1`.

The Parent API talks in Greia semantics — profiles, Activity inventory/install operations, input/display/audio/network settings, backups, paired devices and maintenance — while Linux-specific implementation remains behind platform services and typed privileged brokers. It must never expose a generic shell or arbitrary root RPC.

Normal/release Greia keeps SSH **off by default**. SSH is an optional future parent-controlled maintenance capability using key authentication; Greia Parents itself does not require or use SSH as its management protocol.

The current LAN HTTP/pairing bootstrap is development/provisional. Production pairing requires an explicit Greia-local approval flow and authenticated encrypted transport; see `docs/product/PARENT_MANAGEMENT.md`, ADR 0022 and `docs/architecture/GREIA_PARENT_MANAGEMENT.md`.

## Engineering standard

Greia is intended to become a long-lived open-source project. Code must be easy to understand and extend: cohesive domain objects, narrow interfaces at real variation points, purposeful polymorphism, composition by default, explicit ownership/lifecycle, bounded resources, clean dependency direction, useful public docstrings, and tests at the narrowest meaningful layer.

The canonical guidance is `docs/engineering/ENGINEERING_FOUNDATIONS.md`.

## Product invariants

- Greia Shell, not Linux desktop UI, is the child-facing OS.
- Activity is runtime-neutral.
- Every Activity retains Greia-owned Home navigation outside Activity rendering/input authority.
- Controller/joystick support and standard learned input semantics exist from Phase 0.
- Ordinary Activities do not receive raw physical-input authority merely to support controllers.
- Core operation is offline-first.
- Durable child state is profile-scoped and architecture-neutral.
- Privileged authority stays outside Activity processes.
- Greia Parents HTML and future native clients share one Parent API; the network-facing Parent service does not gain generic root/shell authority.
- Normal/release SSH is disabled by default and is not a dependency of Greia Parents.
- ARM and legacy x86 are peers behind common contracts.
- Resource cost is architectural correctness, not a later optimization pass.
- The first user-ready Phase-0 image includes first-party Writing and Painting Activities.
- Installation/destructive operations fail closed.

## Build and evidence

Canonical provider-free source verification:

```bash
make verify
```

VM/physical evidence uses the applicable procedure under `docs/testing/`. Source tests do not prove hardware behavior.

GitHub-hosted execution is opt-in only and requires explicit owner authorization; see `AGENTS.md`.

## Repository map

- `src/greia_platform/` — shared platform contracts/services/UI/input semantics, including system chrome and controller mapping
- `src/greia_launcher/` — child Shell/session orchestration, including trusted system-chrome lifecycle
- `src/greia_parent/` — Greia Parent API, per-device client credentials, responsive HTML client and compatibility parent surface
- `src/greia_installer/` — graphical installer
- `activities/` — curated built-in Activities
- `runtime/` — runtime/policy declarations
- `build/` — image composition/builders
- `tests/` — source/contract tests
- `docs/` — architecture, engineering, product, plan, evidence and operations docs

## Naming

**Greia** is the platform; **Greia OS** is the installable system; **Greia Shell** is the child graphical environment; **Greia Parents** is the parent surface; **Professor Pip** is optional child-facing content, never the technical platform identity.

Greia is intended to be non-profit and open source. A project-wide license must be selected before public release.
