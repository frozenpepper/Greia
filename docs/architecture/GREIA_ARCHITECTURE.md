# Greia Architecture Constitution

**Status:** Living architecture baseline  
**Date:** 2026-08-08  
**Scope:** Product philosophy, platform boundaries, Activity model, runtimes, profiles, storage, progression, package/update model, backup/restore, parent controls, hardware abstraction, ARM/i386 strategy, graphics direction, security boundaries, and open questions.

---

## 0. Purpose

Greia is a non-profit, open-source computing platform for children. It is built on Linux, but it is not intended to behave like a conventional Linux desktop distribution.

The purpose of this document is to define the stable product architecture above any particular Linux distribution release, bootloader, graphics backend, CPU family, or Activity runtime.

Greia should be able to evolve from an old i386 netbook to a Raspberry Pi 400/500 or a modern PC without becoming several different products.

The core rule is:

> **Greia presents one child operating environment, one Activity model, one profile model, one progression/storage model, and one parent-management model across all supported hardware and runtimes.**

Implementation layers are allowed to differ below those contracts.

---

# Part I — Product philosophy

## 1. Greia is an appliance-like child operating environment

Linux supplies the kernel, drivers, filesystems, networking primitives, security primitives, and low-level userspace.

Greia supplies the experience.

From the child's perspective, the machine powers on into Greia. The child should not be expected to know that Linux exists underneath.

The supported normal child journey is approximately:

```text
power on
   ↓
continuous Greia-branded boot experience
   ↓
child profile selection
   ↓
Greia Shell / workshop world
   ↓
choose Activity
   ↓
Activity runs under Greia supervision
   ↓
Activity exits or fails
   ↓
Greia Shell safely returns
```

Normal child use must not expose a conventional desktop, terminal, package manager, browser chrome, filesystem browser, login prompt, taskbar, dock, or generic window-manager interface.

This is closer to a console or dedicated educational computer than to a simplified desktop PC.

## 2. The Greia Shell is the graphical OS surface

The Greia Shell owns the graphical child session.

Its responsibilities include:

- branded boot arrival;
- profile selection;
- child navigation;
- workshop/world presentation;
- Activity discovery and presentation;
- transitions into and out of Activities;
- global return/emergency UI;
- child-safe failure states;
- visible progression/rewards;
- profile customization;
- system Activities designed for the child.

The shell is not merely an application launcher placed on top of another desktop shell.

## 3. Professor Pip is content, not the platform identity

Professor Pip may remain an important guide/character in the child world and may anchor a workshop setting or recurring educational universe.

However, Professor Pip is not the name or architectural root of the platform.

This separation is intentional:

- **Greia** can grow to support different worlds, guides, age groups, and educational styles;
- **Professor Pip** can remain a beloved character without constraining the operating-system identity.

---

# Part II — Constitutional principles

The following are architectural invariants unless superseded by an explicit later ADR.

## P-01 — Activity is the universal content abstraction

Greia does not have separate product categories called “Python games”, “HTML games”, or “browser games”.

It has **Activities**.

An Activity can be a game, simulation, interactive story, art tool, music tool, reading exercise, science lab, settings experience, creative environment, or future hardware-connected experience.

Its runtime is one implementation property.

```text
Greia Activity
    ↓
Runtime Adapter
    ├── Python
    ├── Web
    └── Future runtime
```

Everything above the runtime adapter remains common.

## P-02 — Runtime differences must not fragment platform services

The following must be common to all Activities regardless of runtime:

- metadata and manifest semantics;
- installation and update workflow;
- profile identity;
- save namespace;
- session recording;
- scoring/progression reporting;
- reward authority;
- permissions;
- parental controls;
- backup/restore;
- lifecycle supervision;
- uninstall behavior;
- compatibility/capability checks.

## P-03 — Global progression belongs to Greia

Activity code may report facts such as:

- score submitted;
- objective completed;
- level completed;
- educational milestone reached;
- session result;
- optional Activity-defined achievements/events.

The platform decides how those facts affect global progression.

An Activity must not directly grant arbitrary global currency, modify another Activity's progress, or rewrite the child's platform-owned reward ledger.

## P-04 — Storage placement belongs to Greia

Activities do not invent arbitrary durable filesystem locations.

Every durable Activity namespace is logically:

```text
(profile_id, activity_id)
```

The SDK gives an Activity access only to its own scoped persistent data and explicitly granted shared capabilities.

## P-05 — Session history is automatic

A Greia Activity session begins when the supervisor starts an Activity for a child profile and ends when that Activity exits, crashes, is force-stopped, or the machine transitions through another terminal state.

Session creation must not depend on Activity code cooperating.

Typical platform-owned session metadata includes:

- session ID;
- profile ID;
- Activity ID;
- Activity package version;
- runtime family/version;
- start time;
- end time;
- duration;
- exit reason;
- crash/forced-return status;
- optional normalized Activity result.

## P-06 — Parent authority is separate from child authority

Greia Parents is not simply a child Activity with extra filesystem privileges.

Parent management is a separate authority surface responsible for things such as:

- child/profile management;
- system settings;
- hardware settings;
- Activity install/update/remove;
- backup/restore;
- storage management;
- networking;
- permissions/policies;
- diagnostics/recovery.

## P-07 — ARM and i386 are co-equal first-class targets

Greia must not be designed as an x86 system with ARM “ported later”.

Reference hardware includes at minimum:

- old Atom/i386-class netbooks as a hard low-resource compatibility floor;
- Raspberry Pi 400 as an important ARM reference;
- Raspberry Pi 500 as an important current ARM reference;
- modern x86-64 PCs.

The child and parent platform contracts remain the same across these machines.

## P-08 — Activities target capabilities, not CPU families

A normal Activity should request capabilities such as:

- pointer input;
- keyboard input;
- touch;
- audio;
- Canvas2D;
- WebGL;
- camera;
- microphone;
- accelerometer;
- controller;
- minimum compatibility/resource class.

It should not normally request `i386` or `arm64`.

Architecture-specific packaging is reserved for cases where native executable code makes it unavoidable.

## P-09 — Child data is architecture-neutral

A backup created on an old i386 netbook must be conceptually restorable on ARM64 or x86-64.

Portable state should favor documented neutral formats such as JSON, YAML, SQLite, images, audio, and other explicit file formats.

Python pickle, memory dumps, absolute machine paths, opaque native object graphs, and architecture-dependent state are inappropriate as official portable save formats.

## P-10 — Offline-first

Core child operation must continue without an Internet connection.

Children must be able to:

- select profiles;
- use installed Activities;
- save progress;
- create content;
- earn local progression/rewards;
- shut down safely.

Cloud services may later add synchronization or convenience. They must not become the sole owner of identity or saves.

## P-11 — Open formats

Greia Activity packages and Greia backup archives should be documented, inspectable formats.

Parents should not need proprietary software to understand that their child's drawings, creations, and save data exist inside an archive.

## P-12 — Resource cost is an architectural dimension

A component is not acceptable merely because it is convenient or modern.

For every major dependency, Greia considers:

- installed disk cost;
- runtime RSS and peak RAM;
- launch latency;
- steady-state CPU;
- old GPU behavior;
- i386 support where required;
- ARM64 support;
- security-update burden;
- maintenance complexity.

The old-hardware reference floor is a design constraint, not a forgotten compatibility tier.

---

# Part III — System layers

## 4. Layer model

Greia is organized into the following logical layers.

### Layer A — Linux substrate

Responsibilities include:

- kernel and drivers;
- filesystems/block devices;
- DRM/KMS and low-level graphics interfaces;
- input devices;
- audio interfaces;
- networking primitives;
- process/service supervision;
- cryptography and OS security primitives;
- boot and board-specific startup.

This is not a child-facing API.

### Layer B — Hardware/platform adapters and privileged services

Responsibilities include:

- hardware capability probing;
- display backend;
- input backend;
- audio backend;
- removable-media handling;
- Wi-Fi/network configuration;
- power/reboot/shutdown;
- board-specific boot/image behavior;
- privileged install/update operations;
- Activity sandbox creation;
- diagnostics and recovery hooks.

### Layer C — Greia Platform Core

The durable logical core owns:

- Profile Service;
- Activity Registry;
- Activity Runtime Manager;
- Storage Service;
- Session Service;
- Progression Engine;
- Reward Ledger;
- Permission Broker;
- Package Manager;
- Backup/Restore Service;
- Parent Management Service;
- shared asset/language/accessibility services;
- health/recovery state.

### Layer D — Greia Shell

The Greia Shell renders and coordinates the child operating environment.

### Layer E — Activities

Activities use Greia APIs rather than depending directly on Linux, board firmware, CPU architecture, or display-server details.

---

# Part IV — Graphics and graphical session

## 5. No conventional desktop stack

Greia does not require a desktop environment or general-purpose window manager.

The intended child graphics architecture is direct and appliance-oriented.

Conceptually:

```text
Linux kernel
   ↓
DRM/KMS + GPU driver
   ↓
minimal Greia display/runtime path
   ↓
Greia Shell or supervised Activity
```

## 6. X11 status

Historic Pip-era Phase-0 work used a minimal Xorg session because it was a pragmatic compatibility path during early implementation.

That work remains valuable as historical evidence and code, but **X11 is not an intended Greia architectural layer**.

The Greia direction is to avoid X11 unless future hard evidence demonstrates that a particular reference device cannot meet the product requirements without a narrowly scoped compatibility path.

Even in that case, X11 would remain a platform adapter detail, not an Activity API.

## 7. DRM/KMS-first direction

The preferred direction is to use the kernel's modern direct display interfaces and the thinnest practical rendering path.

For Python/Pygame, SDL should use a suitable direct backend where hardware allows.

For a Web Activity runtime, Greia should select an embeddable engine/backend able to fit the appliance model rather than launching a conventional desktop browser.

## 8. Compositor policy

Greia does not require a compositor merely because desktop Linux normally uses one.

A tiny compositor or embedded scene-management layer may be adopted only if it materially simplifies:

- safe transitions;
- process/surface ownership;
- Web runtime integration;
- crash recovery;
- input routing;
- multi-surface requirements;

and if its cost is acceptable on reference hardware.

The architectural rule is not “never Wayland”. The rule is **never add an unnecessary desktop layer**.

---

# Part V — Runtime architecture

## 9. Runtime Manager

Greia has one logical Activity Runtime Manager.

A runtime adapter is responsible for:

- validating runtime-specific package requirements;
- preparing a sandbox;
- exposing the Greia SDK bridge;
- launching the Activity;
- readiness handshake;
- pause/checkpoint/resume semantics where supported;
- graceful stop;
- forced termination;
- normalized exit result;
- cleanup.

The platform above this adapter must not care whether the Activity was implemented in Python or Web technology.

## 10. Python runtime family

Python/Pygame is a first-class runtime.

The intended model is one curated platform Python runtime rather than per-Activity virtual environments.

Activities should not install packages on the child machine or bring private package managers.

Reasons:

- deterministic compatibility;
- small disk footprint;
- easier security review;
- fewer dependency conflicts;
- simpler ARM/i386 portability;
- predictable offline installation.

## 11. Web runtime family

Web is intended to become a first-class Activity runtime.

Its value includes:

- HTML/CSS layout;
- SVG;
- Canvas2D;
- JavaScript;
- audio;
- animation;
- potentially WebGL on capable systems;
- access to a large ecosystem of educational/open-source interactive content.

However, Greia Web Activities are **not browser sessions**.

The child should never see:

- URL bar;
- tabs;
- history;
- bookmarks;
- downloads UI;
- browser settings;
- browser developer tools.

The Web runtime should execute packaged local content inside a Greia-controlled fullscreen Activity surface.

Network access is denied by default.

## 12. Web engine selection is still an evidence question

No web engine is constitutionally selected yet.

The likely family to investigate is an embedded WebKit/WPE-style stack rather than Chromium, because the target includes very low-resource machines and ARM devices.

Selection requires real measurements on reference hardware for:

- disk delta;
- idle RSS;
- peak RSS;
- launch time;
- Canvas2D/SVG performance;
- audio latency;
- WebGL behavior;
- crash recovery;
- direct-display integration;
- i386 availability;
- ARM64/Raspberry Pi behavior;
- security-maintenance lifecycle.

The Web runtime may be omitted from a low capability class if no engine satisfies its resource budget, without changing the Activity abstraction.

## 13. Java status

Java is not a planned first-class runtime.

It may be reconsidered only if a compelling body of educational software cannot reasonably be supported through existing Greia runtimes and the added runtime cost is justified.

---

# Part VI — Activity model

## 14. Stable identity

Each Activity has a globally stable ID.

The title is presentation and may change or be localized. The ID is identity and must not change casually.

Example:

```yaml
id: org.greia.maze
version: 1.2.0
```

## 15. Universal manifest

A future normalized manifest should be able to express at least:

```yaml
id: org.greia.constellations
version: 1.2.0

presentation:
  name: Constellation Explorer
  icon: icon.webp
  categories: [science, astronomy]
  age:
    min: 5
    max: 10

runtime:
  type: web
  entrypoint: web/index.html

compatibility:
  minimum_class: C0

capabilities:
  required:
    pointer: true
    audio: true
    canvas2d: true
  optional:
    webgl: true

permissions:
  network: none

storage:
  schema: 2

progress:
  model: levels

scoring:
  model: high_score
```

Exact schema syntax remains subject to implementation ADRs; the semantic separation is constitutional.

## 16. Capability classes

Greia should classify machine capability separately from CPU architecture.

For example:

- **C0** — extreme low-resource compatibility class;
- **C1** — modest but comfortable 2D class;
- **C2** — modern baseline with richer multimedia/GPU capability;
- **C3** — high-capability optional features.

The precise thresholds must be measured and versioned.

A Raspberry Pi 500 may be substantially more capable than an old Atom netbook even though both are first-class platform targets.

## 17. Progressive enhancement

An Activity may offer optional richer features while retaining a lower baseline.

Example:

```text
C0 machine → SVG/Canvas2D effects
C2 machine → higher-resolution assets + WebGL effects
```

This should be one Activity package whenever practical, not separate “old computer” and “new computer” products.

---

# Part VII — Profiles and multi-user identity

## 18. Greia profiles are not Linux desktop accounts

The child chooses a Greia profile through the shell.

Each profile can own:

- avatar;
- optional simple password/PIN policy;
- language;
- accessibility preferences;
- visual customization;
- Activity saves;
- Activity settings;
- scores and progression;
- rewards/unlocks;
- child creations.

The exact underlying Unix UID strategy is an implementation/security decision and may evolve independently.

## 19. Profile isolation

One Activity session for one profile must not receive arbitrary access to another profile's data.

Platform APIs should scope storage automatically.

Runtime sandboxes should fail closed when required isolation cannot be established.

---

# Part VIII — Storage, sessions, saves, and progression

## 20. Storage is a core platform service

A Python Activity should receive logical APIs such as:

```python
storage.get("current_level")
storage.set("current_level", 7)
storage.write_file("drawing.png", data)
```

A Web Activity should receive equivalent semantics, for example:

```javascript
await Greia.storage.get("current_level");
await Greia.storage.set("current_level", 7);
```

Both map into the same profile/activity namespace.

## 21. Separate platform-owned data from Activity-owned data

Platform-owned data includes:

- profile identity;
- session journal;
- global scores/progression indexes;
- reward ledger;
- Activity registry/install history;
- backup metadata;
- parental policies.

Activity-owned private state includes:

- puzzle/game state;
- current local level;
- child drawings/projects;
- Activity-local settings;
- Activity-defined content state.

## 22. SQLite is suitable internally

Greia may use SQLite for platform-owned structured data such as sessions, registry entries, progression events, and installation records.

Activity authors should not be forced to interact with the platform database directly.

Their official SDK can expose simpler JSON-compatible key/value and file/blob semantics.

## 23. Save schema versions

Activity save schema versions are distinct from Activity package versions.

An update may keep the same save schema or introduce a migration.

When a migration is required, Greia should snapshot/transactionally preserve the previous state before activating the migrated data.

Migration failure should not silently destroy the previous save.

## 24. Uninstall does not mean erase

Default Activity uninstall behavior should remove the package while retaining child data.

Parents may explicitly request deletion of saved data separately.

Reinstallation should automatically reconnect to the preserved namespace.

---

# Part IX — Backup and restore

## 25. Whole-family export

Parents must be able to export portable child state to a single archive.

The backup should include, according to policy:

- child profiles;
- avatars;
- profile preferences;
- Activity saves;
- child creations;
- scores/progression;
- rewards/unlocks;
- workshop customization;
- Activity inventory/version metadata;
- portable parent settings where appropriate.

Installed Activity binaries should not normally be embedded by default because that can make backups unnecessarily large.

## 26. Restore onto another architecture

A backup made on i386 must be restorable on ARM64 when compatible Activities exist.

Activity data for an Activity not currently installed should still be restored and retained dormant.

Installing that Activity later should make its preserved state available again.

## 27. Backup format

The future canonical extension should be Greia-branded, for example `.greiabackup`.

The archive should be versioned and documented.

A reasonable internal structure could contain:

```text
manifest.yaml
profiles/
activity-data/
progress/
rewards/
shared/
```

The exact schema requires a dedicated format ADR.

---

# Part X — Activity packaging, installation, updates, and rollback

## 28. Single Activity package model

Python and Web Activities use the same outer package concept.

A future package extension may be `.greiaactivity`.

Example contents:

```text
manifest.yaml
activity/
assets/
signature/
```

Only the runtime metadata and payload layout differ inside.

## 29. Parent-friendly removable-media installation

Inserting a USB stick or SD card may cause Greia to scan it automatically for valid Activity packages.

No code is executed from the removable medium.

Greia reads bounded package metadata, validates packages, compares stable IDs and versions, then shows the parent a simple result.

Example:

```text
Maze          1.0  → NEW / INSTALL
Animals       1.2  → UPDATE from installed 1.1
Drawing Lab   1.0  → ALREADY INSTALLED
```

Parents do not browse Linux paths or use package-manager terminology.

## 30. Transactional install/update

Updates must not overwrite a working version in place.

Conceptually:

```text
install new version alongside old
       ↓
validate
       ↓
activate new version atomically
       ↓
health check
       ↓
success → retain/remove previous according to policy
failure → roll back
```

Unexpected media removal or power loss should not corrupt the previous working package.

## 31. Signature/authenticity

Open source does not mean arbitrary unsigned code should be indistinguishable from trusted distribution content.

The precise trust model remains to be specified, but Greia needs a clear distinction among:

- official Greia-signed packages;
- trusted community/source packages;
- locally developed/test packages;
- invalid/tampered packages.

The parent UI should communicate trust without requiring cryptographic expertise.

---

# Part XI — Parent controls

## 32. One parent-management model across hardware

A Raspberry Pi 500 and an old netbook should expose the same conceptual parent settings wherever the capability exists.

Board-specific implementation remains below a typed hardware/settings service.

Parent controls may include:

- profile creation/removal;
- child password/PIN policy;
- Activity install/update/remove;
- backup/restore;
- allowed categories/Activities;
- networking policy;
- sound/volume;
- display resolution/mode;
- pointer/touchpad sensitivity;
- tap-to-click;
- language/accessibility;
- storage usage;
- diagnostics/recovery.

## 33. Local and remote parent surfaces

The architecture may support both on-device parent mode and a remote/local-network parent companion.

Both should call typed, bounded platform operations rather than exposing a shell as the normal administration API.

---

# Part XII — Hardware and image architecture

## 34. One platform, multiple boot/image adapters

Greia cannot assume one universal boot image format across PCs and Raspberry Pi hardware.

The architecture should converge above the hardware/boot seam:

```text
PC BIOS/UEFI path ─┐
                   ├→ Linux + Greia Platform → same Shell/Activity contracts
Raspberry Pi path ─┘
```

PC and Pi boot firmware/partition details may differ substantially without producing separate Greia products.

## 35. Declarative image profiles

The previous project already moved toward typed declarative image profiles rather than executable shell profile fragments. That direction should continue.

A build profile should declare intent such as:

- platform family;
- architecture;
- board/boot adapter;
- compatibility class;
- package sets;
- runtime families;
- display adapter;
- resource budget.

Runtime hardware probing then establishes what the actual machine can do.

Declarations are not evidence.

## 36. Reference hardware policy

Reference machines are acceptance authorities for their class.

At minimum the project should maintain physical or reproducible acceptance targets for:

- low-end i386/Atom-era PC;
- Raspberry Pi 400;
- Raspberry Pi 500;
- representative modern amd64 PC.

As hardware availability evolves, specific models may be retired through an ADR while preserving portable child data.

---

# Part XIII — Security and trust boundaries

## 37. Activities are not automatically trusted because they are educational

Greia must assume that Activity code can be buggy and that third-party packages may eventually exist.

Isolation should cover as appropriate:

- profile filesystem boundaries;
- process namespace/lifecycle;
- network permissions;
- removable-media permissions;
- device permissions;
- parent-state access;
- sibling Activity data;
- privileged OS operations.

## 38. Network denied by default

Especially for Web Activities, arbitrary network access should not be the default.

An ordinary offline Activity should not be able to silently become a tracking client.

Network capability must be declared and mediated by policy.

## 39. Child-safe crash behavior

If an Activity crashes or hangs, Greia should reclaim control and return to a safe child-facing surface.

A terminal traceback, browser error page, Linux crash dialog, or frozen black screen is not an acceptable normal failure experience.

The platform owns a universal forced-return/watchdog mechanism.

## 40. Fail closed

If a security-critical sandbox, package verifier, privileged helper, or destructive-operation safety gate is unavailable, Greia should refuse the unsafe operation rather than silently falling back to a weaker path.

---

# Part XIV — Naming and migration from Pip-era work

## 41. Canonical names

Use:

- **Greia** — platform/project;
- **Greia OS** — installable OS/system image where distinction is useful;
- **Greia Shell** — child graphical environment;
- **Greia Parents** — parent-management product/surface;
- **Greia SDK** — Activity APIs/tooling;
- **Greia Activity** — universal content package;
- **Professor Pip** — child-world character/guide where appropriate.

## 42. Legacy technical identifiers

Old implementation identifiers beginning with `pip_`, old paths, and old package extensions are migration debt, not architectural vocabulary.

They should not be mass-renamed blindly if doing so would break persisted Activity IDs, save paths, or compatibility boundaries.

Renames should preserve migration mappings and be tested.

---

# Part XV — Explicit rejected architectures

## 43. Conventional Linux desktop

Rejected because it exposes implementation substrate, increases resource cost, fragments the child experience, and creates unnecessary escape/failure surfaces.

## 44. Runtime-first platform

Rejected because separate Python/Web install, save, progress, and parent systems would duplicate core logic and break portability.

## 45. Per-Activity Python environments

Rejected for normal deployment because of disk use, dependency drift, update complexity, offline installation problems, and cross-architecture maintenance.

## 46. Chromium as the assumed Web runtime

Rejected as the default assumption because its footprint/process model is poorly aligned with the extreme low-resource target. This does not prohibit evidence-based use on a future high capability class, but the architecture must not depend on it.

## 47. X11 as a permanent platform dependency

Rejected. Historical Xorg work remains useful as migration/evidence material, but Greia should not carry X11 simply because it is conventional.

## 48. Java as a default first-class runtime

Rejected for now because the added runtime/maintenance cost lacks a compelling ecosystem payoff compared with Python + Web.

## 49. Backups containing only installed Activities

Rejected because child data must survive uninstall and restore even when the Activity is temporarily absent.

## 50. In-place package updates

Rejected because interruption or a bad package can destroy the working installation.

---

# Part XVI — Open research and implementation questions

The following are intentionally not settled by this constitution.

## 51. Direct graphics stack

Need evidence to select the exact shell/display architecture across old Intel and Raspberry Pi hardware.

Questions include:

- SDL KMSDRM behavior on reference machines;
- whether one tiny compositor materially improves Web runtime integration;
- GPU fallback behavior;
- mode switching and resolution control;
- boot-to-shell continuity without X11;
- handling of multiple Activity surfaces if ever required.

## 52. Web engine

Need benchmarked comparison of WPE WebKit / WebKit variants and any other realistic embedded engines on i386 and ARM64.

## 53. Boot cover

Need a genuinely noninteractive branded boot path that never reveals normal Linux output through ordinary child input and degrades safely when graphics initialization fails.

## 54. Exact backup/package schemas

Need versioned format ADRs and migration rules.

## 55. Package trust chain

Need signing-key lifecycle, community package policy, offline trust/verification, rollback, and recovery design.

## 56. Activity forced-return input

Need a universal child/parent emergency-return interaction that works across runtime families without interfering with educational gameplay.

## 57. Capability classes

Need measured thresholds and certification tests rather than invented labels.

## 58. ARM image strategy

Raspberry Pi 400/500 must be first-class, but board/image details require their own implementation profile and testing rather than pretending x86 GRUB/MBR logic transfers to ARM.

---

# Part XVII — Architecture summary

## 59. One-sentence constitution

> **Greia is a console-like child operating environment centered on runtime-independent Activities, with platform-owned identity, lifecycle, storage, sessions, progression, installation, backup, permissions, parent controls, and hardware abstraction over a deliberately replaceable Linux/runtime/display substrate.**

## 60. Core diagram

```text
                           PARENTS
                              │
                    Greia Parents / Policy
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                     GREIA PLATFORM CORE                       │
│ Profiles • Registry • Storage • Sessions • Progression       │
│ Rewards • Packages • Backup • Permissions • Health • Assets  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                     universal Activity contract
                               │
                     Activity Runtime Manager
                     ┌─────────┼─────────┐
                     │         │         │
                   Python      Web      Future
                     │         │         │
                     └─────────┼─────────┘
                               │
                  Greia hardware/platform adapters
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
         i386 netbook      Raspberry Pi       amd64 PC
                            400 / 500
```

The supported hardware may change. Runtime implementations may change. Linux distributions and boot mechanisms may change. The contracts above them are what make the system Greia.
