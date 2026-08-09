# AGENTS.md — Greia Project Contracts

This repository implements a child-first educational Linux appliance/platform. These rules apply repository-wide.

## Authoritative read order and ACTIVE plan

Before changing implementation or architecture, read:

1. `README.md`;
2. `docs/architecture/GREIA_ARCHITECTURE.md`;
3. `docs/adr/0012-platform-architecture-constitution.md`;
4. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`;
5. relevant narrower ADRs, especially ADR 0013 for image composition;
6. **`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md` — MANDATORY ACTIVE IMPLEMENTATION PLAN**;
7. `HANDOVER.md`;
8. `docs/plans/2026-08-06_PHASE0_BOOTABLE_VERTICAL_SLICE.md` only as supporting Phase-0 history/evidence context where it is not superseded by the active remediation plan.

The architecture-remediation plan is the single active implementation plan until its final completion criteria are satisfied. Resume from the first incomplete phase in that plan. Do not create a competing implementation plan or jump ahead to a more visible feature while an earlier authority/safety prerequisite remains open.

After every substantive implementation turn:

1. append an accurate progress entry to `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
2. update `HANDOVER.md` with the exact current phase, implemented work, verification/evidence, blockers, and next exact step;
3. run the verification required by the active phase before claiming it complete;
4. commit coherent work to the canonical GitHub repository.

Do not rewrite earlier progress entries to make history appear cleaner. Append corrections explicitly.

When—and only when—the active remediation plan's final completion criteria are all satisfied, the contributor closing it MUST mark the plan complete, append final evidence, update `HANDOVER.md`, and **remove this active-plan reference and these special resume/progress instructions from `AGENTS.md`**. The completed plan remains under `docs/plans/` as historical evidence.

## GitHub Actions and paid execution

**GitHub-hosted Actions are opt-in only. Never enable, trigger, rerun, or add an automatic GitHub Actions workflow without the repository owner's explicit authorization for that specific use.** This includes pull-request, push, schedule, and manual `workflow_dispatch` runs when they consume hosted-runner minutes or other paid resources.

Repository commits/pushes are allowed and expected for source persistence. Verification should run locally or on an explicitly owner-approved external/local environment. Existing workflow definitions may be retained only as manual reference tooling; automatic triggers must not be reintroduced without explicit owner approval.

Do not treat CI availability as implicit permission to spend money. Do not infer authorization from earlier runs, from the existence of a workflow file, or from a request to “move forward.”

## Non-negotiable product contracts

1. **No visible Linux shell during normal child operation.** No boot text, login prompt, terminal, desktop, window manager, package manager, filesystem UI, or browser chrome may appear in the supported child path.
2. **Greia Shell is the child's graphical OS.** Linux is the substrate, not the product surface.
3. **Activity is the universal abstraction.** Python, Web, and future runtimes are adapters below common Activity/package/storage/progression/permission/lifecycle contracts.
4. **Reference floor:** first-generation Acer Aspire One remains the extreme low-resource reference, currently estimated around 768 MiB RAM, 7 GB storage, and 1024×600 until inventory evidence replaces estimates.
5. **ARM is co-equal with legacy x86.** Raspberry Pi 400 and Raspberry Pi 500 are explicit first-class ARM reference devices. ARM is not a later port.
6. **Disk budget:** current C0 preferred installed core ≤800 MiB; required target <1,000 MiB; >1,250 MiB requires architecture review.
7. **One curated environment per runtime family.** Phase 0 has one shared Python runtime. Activities may not install, download, compile, or resolve private dependencies. No Activity venvs, wheels/site-packages bundles, package managers, browser binaries, or executable installers.
8. **Curated Activities only.** Packages must pass manifest, source/import, path-safety, capability, and footprint validation before inclusion.
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

## Graphics and display direction

Do not introduce a desktop environment or general-purpose window manager.

**Do not deepen X11 dependency.** The existing hardened Xorg path is a temporary Phase 0 migration/evidence baseline inherited from v0.12. ADR 0014 makes the target direction direct/appliance-oriented around DRM/KMS and the thinnest practical session/surface layer. New graphics architecture work must move toward that target.

A tiny compositor may be selected only if evidence shows it materially improves safe surface ownership, transitions, crash recovery, Web-runtime integration, or input routing at acceptable RAM/disk/latency cost. “Desktop Linux normally uses it” is not a justification.

## Engineering rules

- Preserve clean boundaries between `greia_platform`, `greia_launcher`, `greia_parent`, `greia_installer`, Activities, build system, runtime adapters, and platform/hardware adapters.
- Image composition follows ADR 0013: declarative `build/profiles/*.toml` plus composable `build/package-sets/`. Never restore executable shell-sourced profiles or one universal dependency list.
- Build profiles describe intended composition; runtime probing/certification remains authoritative for actual hardware capability.
- Prefer typed dataclasses/protocols and dependency injection at architectural seams. Use polymorphism when multiple runtime/platform adapters genuinely exist.
- Reuse existing systems before inventing parallel ones. Runtime-specific copies of storage, progression, backup, install/update, or parent policy are forbidden.
- Child and installer processes invoke external commands with argument arrays and `shell=False`; never interpolate disk paths into shell command strings.
- Never expose privileged operations directly to Activities.
- Keep logs/caches bounded. Do not add persistent caches without explicit limits.
- Use canonical asset IDs/catalogues rather than filesystem discovery as product logic.
- Profile state remains bounded under `/var/lib/greia-profiles`; every child gets one customization root and one Activity-data root.
- Removable child media stays read-only at the platform boundary.
- Preserve fail-closed Bubblewrap/namespace behavior until a replacement sandbox is evidence-accepted.
- Do not claim source tests prove hardware behavior.

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

## Evidence labels

Use these terms accurately:

- **CONSTITUTIONAL** — stable platform contract;
- **SELECTED** — implementation selected by ADR;
- **PROVISIONAL** — development/evidence implementation, not release architecture;
- **DEFERRED** — intentionally outside the current phase;
- **UNPROVEN** — designed/implemented but lacking required runtime/hardware evidence.

## Packaging and continuity

Every substantive work turn should leave:

- updated `HANDOVER.md`;
- updated active plan/ADRs where decisions changed;
- no build caches, venvs, downloaded package archives, disk images, or heavyweight transient evidence inside the source tree.

The GitHub repository is the canonical long-term source of truth; chat transcripts are not.