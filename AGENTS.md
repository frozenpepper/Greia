# AGENTS.md — Greia for coding agents

Greia is a child-first educational operating system: a small, offline Linux
appliance for old laptops (the reference machine is a first-generation Acer
Aspire One) and, later, Raspberry Pi. Children only ever see the Greia Shell
and its Activities; Linux stays hidden.

This file is for **any coding agent working in a clone of this repository**
(Claude Code, Codex, Cursor, Copilot and others). It tells you where things
are, what you must never break, and how to share useful work back. `CLAUDE.md`
simply imports this file.

- **Your owner** is the person you work for. Greia's rules below limit what
  you build; they never replace your owner's instructions about their own
  machine, money or accounts.
- **The Greia maintainers' own agents** (your owner is the repository owner,
  FrozenPepper, or tells you that you are a core agent) **must also read and
  follow** [`docs/agents/CORE_TEAM.md`](docs/agents/CORE_TEAM.md): branch
  policy, the active plans, handover and progress duties. Other agents can
  ignore that file.

## Start here

| You want to… | Read first |
|---|---|
| Understand the project | [README.md](README.md), then [docs/README.md](docs/README.md) (map of every doc) |
| Set up tools for your role | [SETUP.md](SETUP.md) |
| Find the right manual or skill for a task | [docs/agents/README.md](docs/agents/README.md) |
| Make or change an Activity (game, tool, story) | [skills/greia-activity-authoring/SKILL.md](skills/greia-activity-authoring/SKILL.md), [docs/development/CREATE_AN_ACTIVITY.md](docs/development/CREATE_AN_ACTIVITY.md) |
| Work on the Shell, Parent service, installer, image or hardware support | [skills/greia-os-work/SKILL.md](skills/greia-os-work/SKILL.md), [docs/engineering/ENGINEERING_FOUNDATIONS.md](docs/engineering/ENGINEERING_FOUNDATIONS.md) |
| Add or translate a language | [skills/greia-language-expansion/SKILL.md](skills/greia-language-expansion/SKILL.md) |
| Record or review speech | [skills/greia-voice-production/SKILL.md](skills/greia-voice-production/SKILL.md) |
| Draw or integrate art | [skills/greia-visual-authoring/SKILL.md](skills/greia-visual-authoring/SKILL.md) |
| Build an installer image | [docs/development/BUILD_A_GREIA_IMAGE.md](docs/development/BUILD_A_GREIA_IMAGE.md) |
| Debug a machine that will not install or boot | [docs/engineering/boot/](docs/engineering/boot/), [docs/release/INSTALLER_FAILURE_LOGS_ON_USB.md](docs/release/INSTALLER_FAILURE_LOGS_ON_USB.md) |
| Change architecture | [docs/architecture/GREIA_ARCHITECTURE.md](docs/architecture/GREIA_ARCHITECTURE.md) and the accepted ADRs in [docs/adr/](docs/adr/) |

When two documents disagree, [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
says which one owns the fact. Do not pick whichever is convenient; fix the
stale one.

## Run and test

```bash
python3 -m pip install -r requirements-dev.txt   # Python 3.11+
python3 tools/greia_simulator.py                 # the real Shell on your desktop
PYTHONPATH=src python3 -m unittest discover -s tests   # quick unit run
make verify                                      # the full gate before a pull request
```

The Simulator and desktop tests prove source behaviour only. Never claim they
prove a VM or a real computer, and never claim a test you did not run.

## Sharing what you found

Greia gets better when agents report back. If you:

- built something that other Greia users or contributors would want (an
  Activity, a fix, a tool, a translation);
- got Greia installing or running on **hardware not yet listed** in
  [docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md](docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md);
- fixed a driver, boot, Wi-Fi, sound, screen or input problem on some machine;
- or found a bug you could not fix,

then **ask your owner** whether they want to share it. Never open a pull
request, issue or email without their OK. Offer the two routes below.

### Route 1: a pull request on GitHub

1. Fork `frozenpepper/Greia` (or use a branch if you have write access).
   Never push to `main`.
2. Keep one topic per pull request. Follow the rules in this file and the
   skill for that area.
3. Run `make verify`, or at least the tests for what you touched plus
   `make validate` (it checks every Activity package).
4. Fill in the pull request template. Say exactly **where** you tested:
   Simulator, VM, or a real computer (make, model, CPU, RAM, disk, firmware
   BIOS/UEFI). Say what you did **not** test.
5. For hardware work, attach the evidence: `lspci -nn`, `lsusb`, `dmesg`
   excerpts, the installer failure logs from the USB stick, before/after
   behaviour.

Details for humans: [CONTRIBUTING.md](CONTRIBUTING.md).

### Route 2: an email

If a pull request is too much, your owner can simply email
**greia@frozenpepper.it** with:

- the computer's make and model (and CPU/RAM if known);
- the Greia version or image name;
- what worked, what failed, and the exact messages;
- logs and your fix or patch, if any (`git diff` or `git format-patch`).

### Never send

Passwords, Wi-Fi keys, SSH keys, tokens, real children's names, photos,
recordings or saved work, or anything your owner has not approved. Strip
personal paths and hostnames from logs when you can.

Security problems go privately, as described in [SECURITY.md](SECURITY.md),
never in a public issue.

## Contributing rules for outside agents

- Work on a branch or fork and submit a pull request; never push to `main`.
- Do not use paid services, hosted CI runs or model downloads on your owner's
  behalf without their explicit approval (see below).
- Do not add dependencies an Activity would install, download or compile at
  run time (product contract 7).
- Update the skill or doc that governs what you changed, in the same pull
  request, when your change makes it wrong.
- Keep build caches, virtual environments, disk images, private keys and bulky
  test evidence out of the repository.

## Pre-release policy

Greia has
never been publicly released. Do **not** build or preserve backward-compatibility
mechanisms for old development snapshots, historical package formats or
legacy receiver bridges. Reinstall fresh current development images rather
than maintaining upgrade paths from them. Current-generation update recovery
and rollback to the last healthy installed release **are required** product
features and must not be confused with backward compatibility.

## Standing owner decisions

- committed recordings are owner-reviewed and accepted; never regenerate them for perceived provenance problems. New speech goes through `tools/greia_voice.py` and needs fresh human acceptance;
- scoped owner exception (2026-10-19, extended by owner direction 2026-10-21): the requested corpus replacement uses `tools/regenerate_voice_corpus.py` and `docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`, with the selected masters for that run (the completed v2 run used v0.2; the separately authorized v3 run uses the exact selected v0.3 identities), acting-only prompts, deterministic isolated letter/syllable preservation, recoverable originals and new listening-pending receipts. This does not retrospectively accept any new takes;
- do not add file anti-tampering, signing or elaborate asset verification; users may edit their own files;
- the canonical selectable language set is loaded from `src/greia_platform/languages/<locale>/manifest.json`; currently en, it, es, fr are owner-released and ship with their audio. Additional languages require an owner-authorized, fully translated and accepted manifest/data pack. Do not create another language registry.

## New-language contributor route

When asked to add, translate, stage or release a new Greia language, start with `skills/greia-language-expansion/SKILL.md` and `docs/development/ADD_A_GREIA_LANGUAGE.md`. Read the voice-production skill for speech work. The original four released languages remain en/it/es/fr; new left-to-right languages use a language folder manifest plus localized data/resources instead of Python registry edits. Never offer an unfinished locale before translation, voice, layout and owner acceptance.

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

Do not treat available hosted compute as implicit permission to spend money. Installing or using a paid cloud model/provider likewise needs explicit owner cost approval.

## Developer remote-control boundary

Greia developer/test images may expose a remote-control surface so an operator can deploy test Activities, collect screenshots/logs/status, inject bounded test input, restart Greia services, reboot/power off, and use an explicit maintenance SSH shell without physically operating the target machine.

Owner decision 2026-10-29: the live graphical installer also offers an explicit
Wi-Fi-page SSH toggle, off by default on ordinary installer images, using the `greia` / `greia` account.
It applies only to the running installer, not the installed release; root SSH
remains disabled. Normal password-authenticated sudo is available there for
owner recovery.

Owner decision 2026-10-30: installed normal images also offer an explicit
Parent-controlled SSH switch, off by default, with `greia` / `greia` login.
Root SSH remains disabled. Other developer remote-control operations remain
development-only; ordinary Parent management uses the Parent API.

This capability is **development-only**:

- normal/release profiles must not enable SSH merely because developer tooling exists in the repository;
- developer remote-control enablement requires an explicit developer image/profile marker and provisioning; the owner-authorized Parent SSH switch and live-installer toggle are separate explicit exceptions;
- developer images provide the owner-approved `greia` / `greia` SSH login; normal images start with SSH off and enable the same login only through the explicit Parent switch; root SSH login remains disabled;
- never commit private keys, Wi-Fi passwords, tokens, or other operator credentials;
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
6. **Disk budget:** preferred installed core ≤800 MiB; owner-accepted ceiling (2026-10-21) ≤1,500 MiB for the four-language release image; anything above 1,500 MiB requires architecture review. The 2026-10-17 1,300 MiB ceiling was raised by the owner to keep the shipped four-language `@2x` art renditions and the UEFI/BIOS boot payload in one image while remaining comfortably inside the reference Acer's 7 GB storage target; the ≤800 MiB preferred core is unchanged. Owner decision 2026-10-25: the Acer A/B acceptance-build accounting gate is 1,500 MiB and the A/B system slot is 1,664 MiB (1,500 MiB installed core plus measured hardware-support/initramfs headroom); the finalizer capacity check and the reference Acer 7 GB storage target remain authoritative.
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

`docs/engineering/ENGINEERING_FOUNDATIONS.md` is mandatory implementation guidance for these rules. `skills/greia-os-work/SKILL.md` operationalizes them for OS/platform work. ADR 0018 applies them specifically to the lightweight UI foundation; ADR 0019 applies them to trusted Activity navigation chrome; ADR 0020 applies them to runtime-neutral input and controller ownership.

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
- `greiaadmin` — explicit operator/recovery key-authentication identity;
- `greia` — managed development/admin SSH identity (base images lock it and keep SSH off; explicit developer provisioning enables the `greia` / `greia` login);
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

Do not claim a test result that did not execute against the stated commit/checkout. Exact current executed evidence belongs in `HANDOVER.md` (core team) or in your pull request description.

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

For visual/art work, additionally use the scope labels defined by the current art plan: **DESIGN SPEC**, **SOURCE**, **DESKTOP VISUAL REVIEW**, **SIMULATOR VISUAL REVIEW**, **PHYSICAL VISUAL REVIEW**, and **REJECTED EXPERIMENT**.
