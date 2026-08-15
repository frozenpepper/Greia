# AGENTS.md — Greia Project Contracts

This repository implements a child-first educational Linux appliance/platform. These rules apply repository-wide.

## Authoritative read order and active plan

Before changing implementation or architecture, read:

1. `README.md`;
2. **`docs/DOCUMENTATION.md` — documentation authority, ownership and freshness model**;
3. `docs/architecture/GREIA_ARCHITECTURE.md`;
4. `docs/adr/0012-platform-architecture-constitution.md`;
5. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`;
6. relevant narrower accepted ADRs, especially ADR 0013 for image composition and later ADRs for trust/runtime/storage/progression boundaries;
7. **`docs/adr/0018-lightweight-ui-foundation.md` — mandatory lightweight Screen/Overlay/Collection UI architecture and low-resource UI rules**;
8. **`docs/adr/0019-platform-owned-activity-system-navigation.md` — mandatory platform-owned Activity Home/Back chrome and protected-input architecture**;
9. **`docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md` — mandatory runtime-neutral input profiles, controller support and physical-input authority**;
10. **`docs/engineering/ENGINEERING_FOUNDATIONS.md` — mandatory OOP, polymorphism, maintainability, dependency and performance guidance**;
11. **`docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md` — mandatory first-user-ready-image writing and painting requirement**;
12. **`docs/product/ACTIVITY_SYSTEM_NAVIGATION.md` — mandatory universal Home/Back child-navigation requirement**;
13. **`docs/product/ACTIVITY_INPUT_STANDARDS.md` — mandatory Phase-0 keyboard/pointer/touch/controller interaction standards**;
14. **`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` — MANDATORY ACTIVE IMPLEMENTATION PLAN**;
15. `HANDOVER.md`;
16. **`docs/agents/GREIA_AGENT_OPERATIONS.md` — mandatory project/build/test-hardware operating manual for agents**;
17. `skills/greia-activity-authoring/SKILL.md` whenever creating, modifying, reviewing, validating, optimizing, packaging, deploying, or testing an Activity;
18. phase-specific testing/review documents referenced by `HANDOVER.md` or the active plan;
19. `docs/plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md` only as historical/supporting Phase-0 context where it is not superseded.

`docs/DOCUMENTATION.md` defines which document class owns which fact. In short:

- `AGENTS.md` owns repository-wide work rules and non-negotiable product constraints;
- accepted ADRs own normative architecture decisions;
- source/runtime declarations own exact implemented APIs/schemas/command vocabularies;
- product requirement documents own explicit child-facing scope/UX requirements where referenced here;
- the active plan owns sequencing and closure criteria;
- `HANDOVER.md` owns current branch/evidence state;
- `docs/testing/*` owns exact named test procedures;
- agent operations/skills are derived living manuals and must track their implementation owners.

Do not resolve contradictions by choosing whichever document is convenient. Identify the owner of the fact and correct stale derived documentation.

The architecture-remediation plan is the single active implementation plan until its final completion criteria are satisfied. Resume from the first incomplete blocking phase in that plan. Do not create a competing implementation plan or jump ahead to a more visible feature while an earlier authority/safety prerequisite remains open.

After every substantive **implementation** turn:

1. append an accurate progress entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
2. update `HANDOVER.md` with the exact current phase, implemented work, verification/evidence, blockers, and next exact step;
3. run the verification required by the active phase before claiming it complete;
4. update `docs/agents/GREIA_AGENT_OPERATIONS.md` if repository/build/test-hardware/remote-control procedure changed;
5. update `skills/greia-activity-authoring/SKILL.md` in the same tranche whenever the Activity manifest/API/runtime policy/trust model/shared assets or UI/input canon/performance requirements/validation or deployment workflow changed;
6. update `docs/DOCUMENTATION.md` when documentation ownership/precedence/freshness rules change;
7. update the applicable `docs/product/*` requirement when accepted child-facing product scope or UX changes materially;
8. update `docs/engineering/ENGINEERING_FOUNDATIONS.md` when repository-wide implementation/extension rules change materially;
9. commit coherent work to the canonical GitHub repository.

For substantive documentation-only work, update `HANDOVER.md` when the continuation contract changes and preserve a dated review when useful; an implementation-plan progress entry is required only when implementation/phase state actually changes.

Do not rewrite earlier progress entries to make history appear cleaner. Append corrections explicitly.

The agent operations manual and Activity authoring skill are **living derived contracts**. A source change that makes either materially wrong is not completely documented until the affected manual is corrected.

When—and only when—the active remediation plan's final completion criteria are all satisfied, the contributor closing it MUST mark the plan complete, append final evidence, update `HANDOVER.md`, and **remove this active-plan reference and these special resume/progress instructions from `AGENTS.md`**. The completed plan remains under `docs/plans/` as historical evidence.

## GitHub Actions and paid/hosted execution

**GitHub-hosted Actions are opt-in only. Do not use the Actions execution surface unless the repository owner explicitly authorizes that specific use.**

Without that explicit authorization, agents must not:

- enable or add automatic hosted workflow triggers;
- trigger or rerun a hosted workflow;
- dispatch a manual hosted workflow;
- query Actions runs/status/jobs/steps/logs/artifacts as part of project execution or evidence gathering;
- download hosted workflow artifacts;
- infer permission from the existence of workflow files, previous runs, CI availability, or a request to “move forward”, “test”, or “verify”.

Reading/editing workflow **source files** as ordinary repository source is allowed when required by the task; executing or interrogating the hosted Actions service is not.

Repository commits/pushes/PR review are allowed and expected for source persistence. Verification runs locally or on an explicitly owner-approved execution environment.

Do not treat available hosted compute as implicit permission to spend money.

## Developer remote-control boundary

Greia developer/test images may expose a remote-control surface so an operator can deploy test Activities, collect screenshots/logs/status, inject bounded test input, restart Greia services, reboot/power off, and use an explicit maintenance SSH shell without physically operating the target machine.

This capability is **development-only**:

- normal/release profiles must not enable SSH merely because developer tooling exists in the repository;
- remote enablement requires an explicit developer image/profile marker and key provisioning;
- password authentication and root SSH login remain disabled; never commit private keys, Wi-Fi passwords, tokens, or other operator credentials;
- passwordless privilege escalation must stay behind a bounded Greia-owned control command such as `greia-devctl`, not generic passwordless sudo/root APIs;
- ordinary remotely deployed Activities retain `DEVELOPER_UNSIGNED` trust and live in a source distinct from `/opt/greia-os/activities`; remote file placement must never upgrade package trust;
- deliberate replacement of a built-in Activity requires an explicit developer operation and a recoverable original backup;
- screenshot/input implementations may use the current Xorg compatibility backend on a developer image, but this is not an R7 production display/input architecture decision;
- remote installation must drive the existing graphical fail-closed installer and its target/payload revalidation. Do not add an unattended destructive disk-install shortcut merely for convenience;
- developer tooling must preserve negative evidence and must not bypass Bubblewrap, PermissionBroker, lifecycle, installer or hardware acceptance gates.

## Non-negotiable product contracts

1. **No visible Linux shell during normal child operation.** No boot text, login prompt, terminal, desktop, generic window manager, package manager, filesystem UI, or browser chrome may appear in the supported child path.
2. **Greia Shell is the child's graphical OS.** Linux is the substrate, not the product surface.
3. **Activity is the universal abstraction.** Python, Web, and future runtimes are adapters below common Activity/package/storage/progression/permission/lifecycle contracts.
4. **Reference floor:** first-generation Acer Aspire One remains the extreme low-resource reference, currently estimated around 768 MiB RAM, 7 GB storage, and 1024×600 until inventory evidence replaces estimates.
5. **ARM is co-equal with legacy x86.** Raspberry Pi 400 and Raspberry Pi 500 are explicit first-class ARM reference devices. ARM is not a later port.
6. **Disk budget:** current C0 preferred installed core ≤800 MiB; required target <1,000 MiB; >1,250 MiB requires architecture review.
7. **One curated environment per runtime family.** Phase 0 has one shared Python runtime. Activities may not install, download, compile, or resolve private dependencies. No Activity venvs, wheels/site-packages bundles, package managers, browser binaries, or executable installers.
8. **Curated Activities only.** Packages must pass manifest, source/import, path-safety, capability, trust and footprint validation before inclusion.
9. **Offline-first.** Core shell, Activities, saves, progression, language packs, and parent management must function without cloud services.
10. **Language-neutral child navigation.** Prefer symbols, color, position, animation, and optional speech; text appears when educationally purposeful.
11. **Platform-owned progression and child data.** Activities report facts/events and write only their own profile-scoped state. They do not directly mutate global rewards/progression.
12. **Portable state.** Durable child data and backups must be architecture-neutral across i386/ARM64/amd64.
13. **Removable media is untrusted and never autorun.** Media scanning is bounded; executable Activity code is never run in place from USB/SD.
14. **Installation is graphical and fail-closed.** Whole-disk installation may offer only verified eligible targets; payload and device identity must be rechecked before destructive work.
15. **Tap-to-click defaults off.** Hardware settings are typed/bounded platform policy, never arbitrary shell/xinput/xrandr command injection.
16. **Every child uses an explicit Greia profile.** Boot shows the profile picker; no silent last-user resume. Saves, customizations, rewards, language state, and Activity data are profile-scoped.
17. **Uninstall and data deletion are separate.** Removing an Activity preserves child saves by default.
18. **Backups are logical/open.** `.greiabackup` must not be a raw filesystem dump or architecture-specific serialization.
19. **Creative computing exists from the beginning.** The first user-ready Phase-0 Greia image must ship first-party built-in **writing/text-editing** and **painting/drawing** Activities. They must be simple, fast, cute, uncluttered and child-sized; writing defaults to large readable text; painting provides a large responsive canvas and a small tool set; both autosave profile-scoped creations through Greia Storage and expose no Linux file-management workflow. Exact product requirements live in `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`.
20. **Greia UI is a lightweight appliance surface, not a desktop.** The common vocabulary is Screen → optional Overlay/Sheet → Panel/Card/Collection → Control. A Collection is a semantic child grouping, never a Linux filesystem folder. Do not introduce general-purpose draggable/resizable windows, taskbars, arbitrary z-order, or a desktop window manager. ADR 0018 owns the exact UI architecture.
21. **Every child-facing Activity has immutable Greia system navigation.** Home is always present in the same protected location, outside Activity rendering/input authority, and always returns toward the Shell through Greia lifecycle authority. Greia may add Back beside it only for a meaningful Shell/Collection launch origin. Activities cannot hide, move, restyle, cover, intercept, disable or replace the real system controls. This applies equally to Python, Web and first-party Activities. Exact product behavior is in `docs/product/ACTIVITY_SYSTEM_NAVIGATION.md`; ADR 0019 owns the architecture.
22. **Controller/joystick support and learned input standards exist from Phase 0.** Activities declare a runtime-neutral interaction profile (`navigation`, `pointer`, `directional`, `game`, `text`, or `hybrid`) rather than controller brands or raw button/device identifiers. Simple game-like Activities default to arrows + Space and D-pad/left-stick + south face button; pointer Activities may use a Greia virtual pointer; text Activities retain real text-key semantics. Keyboard, pointer, touch and controller can coexist. Physical controller ownership, dead zones, mapping and reserved system input are platform concerns; ordinary Activities must not gain raw `/dev/input` authority merely for controller support. Exact product behavior is in `docs/product/ACTIVITY_INPUT_STANDARDS.md`; ADR 0020 owns the architecture.

## Graphics and display direction

Do not introduce a desktop environment or general-purpose window manager.

**Do not deepen X11 dependency.** The installed production path currently uses an explicit Xorg/xinit compatibility backend while R7 measures/selects the target display/session design. Xorg is therefore **PROVISIONAL implementation**, not the Greia architectural API.

ADR 0014 makes the target direction direct/appliance-oriented around DRM/KMS and the thinnest practical Greia-owned session/surface layer. New graphics architecture work must move toward that target or preserve compatibility without expanding X11 coupling.

ADR 0019 adds a mandatory R7 acceptance property: the selected production display/session design must preserve a tiny Greia-owned Home/Back layer above the Activity surface and route input in its protected region to Greia before Activity input dispatch. A raw direct-ownership design that gives the Activity uncontested framebuffer/input authority is not sufficient by itself.

ADR 0020 additionally requires the R7 input/session path to own controller devices, normalize controller input, intercept reserved system controls before Activity delivery, and feed the same interaction semantics to Python and future Web runtimes. Do not solve controller support by broadening ordinary Activity access to `/dev/input`.

A tiny compositor/session broker may be selected when evidence shows it is the smallest reliable way to preserve trusted system chrome, safe surface ownership, transitions, crash recovery, Web-runtime integration, or input routing at acceptable RAM/disk/latency cost. “Desktop Linux normally uses it” is not a justification, and this requirement does not authorize desktop/window-manager features.

## Open-source architecture, OOP and maintainability

**A strong, clean object-oriented base is a permanent project requirement.** Greia is intended to become an important open-source project; contributors must be able to understand where behavior belongs, substitute implementations safely, and extend the system without copying monoliths or reconstructing architecture from chat history.

Mandatory rules:

- Model stable domain concepts, invariants, lifecycle and resource ownership with cohesive classes/dataclasses. Do not create classes merely to inflate abstraction count; small pure functions remain appropriate for local calculations.
- At genuine variation points, define narrow typed protocols/abstract base classes and use polymorphic implementations. Runtime adapters, display/session backends, system-chrome backends, input backends, hardware adapters, storage implementations, UI Screens/Overlays/Controls and renderer-specific implementations are examples.
- Prefer polymorphic dispatch over repeated `if backend/type/runtime == ...` trees spread through callers when the branches represent substitutable implementations.
- Prefer composition over inheritance. Use inheritance only where the subtype is genuinely substitutable for the base contract; avoid deep inheritance trees and mixin webs.
- Keep interfaces narrow and dependencies explicit. Inject services/adapters at architecture seams rather than discovering them through mutable global state.
- Every long-lived resource must have an obvious owner, bound and cleanup lifecycle. This includes subprocesses, threads, display leases, system-chrome leases, controller handles, mounts, caches, histories, queues, surfaces and hardware authority.
- Avoid god classes, giant cross-domain `manager` objects, circular dependencies, hidden globals, parallel implementations of existing platform services, and speculative general frameworks.
- Public architectural classes/protocols/extension points require useful docstrings. Non-obvious algorithms require comments explaining **why**. Accepted extension seams must also be described in repository documentation.
- Architecture and code organization must make it easy for outside contributors to locate the correct extension point without tracing unrelated subsystems.
- Clean architecture never excuses wasteful runtime behavior. On Greia, explicit ownership, bounded structures and reusable services are also performance requirements.

`docs/engineering/ENGINEERING_FOUNDATIONS.md` is mandatory implementation guidance for these rules. ADR 0018 applies them specifically to the lightweight UI foundation; ADR 0019 applies them to trusted Activity navigation chrome; ADR 0020 applies them to runtime-neutral input and controller ownership.

## Engineering rules

- Preserve clean boundaries between `greia_platform`, `greia_launcher`, `greia_parent`, `greia_installer`, Activities, build system, runtime adapters, and platform/hardware adapters.
- Image composition follows ADR 0013: declarative `build/profiles/*.toml` plus composable `build/package-sets/`. Never restore executable shell-sourced profiles or one universal dependency list.
- Build profiles describe intended composition; runtime probing/certification remains authoritative for actual hardware capability.
- Prefer typed dataclasses/protocols and dependency injection at architectural seams. Use polymorphism when multiple runtime/platform adapters genuinely exist.
- Reuse existing systems before inventing parallel ones. Runtime-specific copies of storage, progression, backup, install/update, parent policy, or standard input mapping are forbidden.
- Child and installer processes invoke external commands with argument arrays and `shell=False`; never interpolate disk paths into shell command strings.
- Never expose privileged operations directly to Activities.
- Keep logs/caches bounded. Do not add persistent caches without explicit limits.
- UI caches, histories, collection pages and animation/transient state must have explicit bounds appropriate to the Acer resource floor. Avoid per-frame image decoding, font construction, filesystem IO, or unnecessary off-screen Surfaces.
- Controller/device ownership and reconnect state must be explicitly bounded; centralize dead zones, virtual-pointer behavior and common mappings rather than copying them into Activities.
- Static Shell UI should move toward invalidation/event-driven redraw rather than continuously repainting unchanged content; do not weaken input responsiveness or animation correctness to achieve this.
- Mandatory Activity system chrome must stay tiny and platform-owned; do not turn Home/Back into Activity widgets, DOM injection, or justification for a general compositor/window toolkit.
- Use canonical asset IDs/catalogues rather than filesystem discovery as product logic.
- Profile state remains bounded under `/var/lib/greia-profiles`; every child gets one customization root and one Activity-data root.
- Removable child media stays read-only at the platform boundary unless a distinct trusted parent/system workflow owns a write operation.
- Preserve fail-closed Bubblewrap/namespace behavior until a replacement sandbox is evidence-accepted.
- Do not claim source tests prove VM or physical-hardware behavior.
- Do not turn conceptual examples in architecture docs into implementation without checking the current source/runtime contract.
- First-party built-in Activities must obey the same platform lifecycle/storage/profile/display/session/system-chrome/input boundaries as other Activities; built-in status is not permission to bypass the architecture.

## Greia technical identities

The old prototype identities have been migrated. Active implementation uses Greia technical names such as:

- `greiakid` — child shell/Activity Unix identity;
- `greiapanel` — parent service identity;
- `greiaadmin` — explicit advanced parent/recovery identity;
- `greiaprofiles` — bounded profile-tree group;
- `greiasettings` — bounded hardware/settings group;
- `/etc/greia-os`, `/var/lib/greia-profiles`, `/opt/greia-os`;
- `GREIA_*` environment/build variables.

Do not reintroduce Pip-prefixed technical identifiers. **Professor Pip** is reserved for the character/content layer.

## Validation

Before packaging or committing a substantive implementation change:

```bash
make verify
```

For focused unit work, first remove `__pycache__` and use:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Activity validation intentionally rejects cached bytecode inside Activity folders.

Do not claim a test result that did not execute against the stated commit/checkout. Exact current executed evidence belongs in `HANDOVER.md` or a dated evidence report.

## Evidence labels

Use these terms accurately:

- **CONSTITUTIONAL** — stable platform contract;
- **SELECTED** — implementation selected by accepted decision;
- **PROVISIONAL** — current implementation/evidence candidate, not final release architecture;
- **SOURCE-CLOSED** — source scope closed at a recorded boundary while runtime/hardware evidence may remain;
- **DEFERRED** — intentionally outside the current phase;
- **UNPROVEN** — designed/implemented but lacking required runtime/hardware evidence;
- **HISTORICAL** — retained snapshot, not current instruction;
- **COMPLETE** — explicitly named closure criteria satisfied.

## Packaging and continuity

Every substantive implementation turn should leave:

- updated `HANDOVER.md`;
- updated active plan/ADRs where implementation state or decisions changed;
- updated product requirements when accepted child-facing scope changed;
- updated agent operations/Activity skill when their governed contracts changed;
- updated engineering foundations when repository-wide implementation/extension rules changed;
- no build caches, venvs, downloaded package archives, disk images, private keys, or heavyweight transient evidence inside the source tree.

The GitHub repository is the canonical long-term source of truth; chat transcripts are not.
