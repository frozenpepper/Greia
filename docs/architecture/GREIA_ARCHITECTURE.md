# Greia Architecture — Living Overview

**Status:** Living architecture synthesis  
**Last reviewed:** 2026-08-15  
**Authority:** accepted ADRs are normative; implemented APIs/schemas are owned by source/runtime declarations; this document synthesizes the cross-cutting architecture.  
**Scope:** Product philosophy, platform boundaries, Activity model, runtimes, profiles, storage, progression, package/update model, backup/restore, parent controls, hardware abstraction, ARM/i386 strategy, graphics/input direction, security boundaries, and open questions.

---

## 0. Purpose and how to read this document

Greia is a non-profit, open-source computing platform for children. It is built on Linux, but it is not intended to behave like a conventional Linux desktop distribution.

This document explains the stable product architecture above any particular Linux distribution release, bootloader, graphics backend, CPU family, or Activity runtime.

**It is not a competing ADR/implementation specification.**

- `docs/adr/*` contains accepted normative decisions.
- `docs/DOCUMENTATION.md` defines documentation ownership/precedence.
- source/runtime declarations own exact currently implemented schemas/APIs.
- `skills/greia-activity-authoring/SKILL.md` is the current Activity-authoring specification for agents/developers.
- `HANDOVER.md` owns current branch, verification and hardware-evidence state.

Several examples below are deliberately **conceptual/future-facing** to describe stable semantics. A YAML manifest, a simplified `storage.get()` call, a Web SDK example, `.greiaactivity` layout, or capability-class label shown here is not automatically the current authoring API.

Greia should be able to evolve from an old i386 netbook to a Raspberry Pi 400/500 or a modern PC without becoming several different products.

The core rule is:

> **Greia presents one child operating environment, one Activity model, one profile model, one progression/storage model, one input model, and one parent-management model across all supported hardware and runtimes.**

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
Activity exits or Greia Home/Back ends it
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
- system Activities designed for the child;
- stable keyboard/pointer/touch/controller navigation conventions.

The shell is not merely an application launcher placed on top of another desktop shell.

A child-facing Activity never becomes the ultimate owner of the child's route back to Greia. ADR 0019 requires platform-owned system navigation above the Activity surface.

Likewise, an Activity is not expected to rediscover and normalize physical controllers by itself. ADR 0020 places standard interaction semantics and physical controller authority at the Greia platform boundary.

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
- platform-owned Home/Back system navigation;
- runtime-neutral interaction profiles and input semantics;
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
- controller;
- audio;
- Canvas2D;
- WebGL;
- camera;
- microphone;
- accelerometer;
- minimum compatibility/resource class.

It should not normally request `i386` or `arm64`.

Architecture-specific packaging is reserved for cases where native executable code makes it unavoidable.

A controller capability is distinct from an interaction profile: `controller` means controller input is available, while `pointer`, `directional`, `game`, `text`, and related profiles describe how the Activity is intended to be used.

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
- input latency and device-state overhead;
- i386 support where required;
- ARM64 support;
- security-update burden;
- maintenance complexity.

The old-hardware reference floor is a design constraint, not a forgotten compatibility tier.

## P-13 — Children learn Greia input, not each device brand

Controller/joystick support is a Phase-0 platform requirement.

Greia standardizes common interaction intent rather than consumer controller labels. The initial profiles are:

```text
navigation
pointer
directional
game
text
hybrid
```

The simple game baseline is intentionally stable:

```text
keyboard:    arrow keys + Space
controller:  D-pad/left stick + south face button
```

Pointer Activities may receive a Greia virtual pointer from a controller. Text Activities retain real text-entry semantics. Keyboard, pointer, touch and controller can coexist rather than forcing a global input mode.

Physical controller mapping, dead zones, reconnect behavior and reserved system input belong to Greia, not to individual Activities.

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
- physical input/controller backend;
- protected system-input interception;
- trusted Activity system-chrome backend;
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
- runtime-neutral input profile/mapping semantics;
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

The Greia Shell renders and coordinates the child operating environment, including the post-Activity destination associated with platform Home/Back navigation and standard navigation behavior across available input devices.

### Layer E — Activities

Activities use Greia APIs rather than depending directly on Linux, board firmware, CPU architecture, display-server details, raw input devices, controller brands, or system-chrome authority.

---

# Part IV — Graphics, input and graphical session

## 5. No conventional desktop stack

Greia does not require a desktop environment or general-purpose window manager.

The intended child graphics/input architecture is direct and appliance-oriented.

Conceptually:

```text
Linux kernel + device drivers
   ↓
DRM/KMS + input devices
   ↓
minimal Greia display/session/input authority
   ├── trusted Greia Home/Back + protected system input
   ├── normalized keyboard/pointer/touch/controller input
   └── Greia Shell or supervised Activity surface
```

The trusted system-chrome/input layer is tiny and fixed-purpose. It is not a taskbar, desktop panel or general window-manager surface.

## 6. X11 status

The current installed production path uses a deliberately narrow **Xorg/xinit compatibility backend** while the R7 display/session/input architecture is measured and proven.

That backend is **PROVISIONAL**. It is not an Activity API and does not make X11 part of the intended Greia architectural layer.

The target direction remains direct/appliance-oriented. Xorg may survive only as an explicitly scoped compatibility adapter if physical evidence shows that a reference device requires it.

Even in that case, X11 remains below the platform/Activity contract.

The current Xorg path is not automatically certified for ADR 0019 or ADR 0020 merely because it can display an Activity and receive keyboard/pointer events. Production certification also requires a trusted system-chrome/input implementation and controller path that the Activity cannot control.

## 7. DRM/KMS-first direction

The preferred direction is to use the kernel's modern direct display interfaces and the thinnest practical rendering path.

For Python/Pygame, SDL should use a suitable direct backend where hardware allows.

For a Web Activity runtime, Greia should select an embeddable engine/backend able to fit the appliance model rather than launching a conventional desktop browser.

Direct scanout alone is not the complete product requirement. If an Activity becomes the uncontested owner of both framebuffer and physical input, another trusted layer must still preserve mandatory Greia Home/Back, protected system input and runtime-neutral controller normalization.

## 8. Compositor/session-broker policy

Greia does not require a compositor merely because desktop Linux normally uses one.

A tiny compositor or embedded scene-management/session layer may be adopted only if it materially simplifies:

- trusted Home/Back composition above Activity content;
- protected system-chrome/controller input routing;
- safe transitions;
- process/surface ownership;
- runtime-neutral physical-input brokerage;
- Web runtime integration;
- crash recovery;
- other genuinely required multi-surface behavior;

and if its cost is acceptable on reference hardware.

The architectural rule is not “never Wayland”. The rule is **never add an unnecessary desktop layer**.

### 8.1 Platform-owned Activity system navigation

ADR 0019 defines a universal high-trust child-navigation layer independent of runtime.

**Home** is always present while a child Activity is visible. It ends the current Activity through Greia's existing graceful-stop/forced-return lifecycle and returns toward the child Shell root.

**Back** is optional and appears only when Greia has a meaningful distinct launch origin. It ends the Activity and returns to that Greia Shell/Collection context. It is not browser history and it is not Activity-internal navigation.

The Activity cannot hide, move, restyle, cover, disable, replace or intercept the real system controls. Pointer/touch input in their protected region belongs to Greia before Activity input dispatch.

Where a supported controller reliably exposes a Guide/system control, that control is also reserved to Greia rather than delivered as an Activity action. A fallback multi-button Home chord remains an evidence question rather than an invented default.

Conceptually:

```text
Greia display/session/input authority
├── trusted system chrome
│   ├── Home — mandatory
│   └── Back — context-dependent
├── reserved pointer/touch/controller system input
└── one Activity surface
    ├── Python/Pygame
    ├── Web/HTML
    └── future runtime
```

Current renderer-neutral geometry/actions live in `src/greia_platform/system_chrome.py`; the backend-neutral lifecycle/navigation seam lives in `src/greia_launcher/system_chrome.py`. Exact current implementation/evidence status belongs in `HANDOVER.md`.

A production R7 backend is not accepted merely because it can scan out Activity frames. It must also preserve this trusted chrome/input invariant without turning Greia into a desktop/window-manager environment.

### 8.2 Runtime-neutral Activity input

ADR 0020 defines the normal Activity input layer below protected Greia system input and above runtime/device-specific APIs.

Conceptually:

```text
keyboard / mouse / touch / controller
               ↓
      trusted Greia input backend
               ↓
      reserve system Home/Back input
               ↓
      interaction-profile mapping
               ↓
        semantic Activity input
          ┌────┴────┐
        Python      Web
```

Current profiles are:

- `navigation` — focus/menu movement and activation;
- `pointer` — spatial input, including controller virtual pointer;
- `directional` — simple four-direction movement plus primary action;
- `game` — richer game semantics retaining the simple baseline;
- `text` — real text input without stealing normal typing/editing keys;
- `hybrid` — genuinely mixed modes where one default is insufficient.

The platform owns common dead-zone normalization, positional controller mapping, virtual-pointer behavior and physical controller lifecycle. Activities should not inspect `/dev/input`, SDL joystick indices or consumer-brand button labels as their portable control model.

`src/greia_platform/input_core.py` owns current renderer-neutral semantics. `src/greia_platform/pygame_input.py` is a current Pygame translation/trusted-controller helper and remains below the universal contract.

---

# Part V — Runtime architecture

## 9. Runtime Manager

Greia has one logical Activity Runtime Manager.

A runtime adapter is responsible for:

- validating runtime-specific package requirements;
- preparing runtime-specific launch state beneath platform sandbox policy;
- exposing the Greia SDK bridge;
- launching the Activity through the platform-owned session/lifecycle boundary;
- readiness handshake;
- translating/brokering the runtime-neutral Activity input contract where required;
- pause/checkpoint/resume semantics where supported;
- graceful stop;
- forced termination;
- normalized exit result;
- cleanup.

The platform above this adapter must not care whether the Activity was implemented in Python or Web technology.

System Home/Back and protected physical-input ownership are deliberately above the runtime adapter rather than implemented separately by each runtime.

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

Python Activities may use normal in-content navigation, but they do not draw or receive input authority over the real Greia system Home/Back region and should not own raw physical controller devices in the production architecture.

The current source includes Pygame translation helpers so Python-side semantics can converge immediately; that does not make SDL/Pygame raw device ownership the Activity contract.

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

Greia system Home/Back remains outside the page/DOM. Web content cannot style, cover, remove or intercept it, and Greia Back is never mapped to arbitrary browser history.

Standard controller support should cross the Greia input bridge using the same semantic interaction profiles as Python. Ordinary Web Activities should not each need to reinvent browser Gamepad API brand/button mappings for normal Greia controls.

Network access is denied by default.

## 12. Web engine selection is still an evidence question

No web engine is selected yet.

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
- trusted Greia system-chrome integration;
- runtime-neutral keyboard/pointer/touch/controller bridge integration;
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

Conceptual identity example:

```yaml
id: org.greia.maze
version: 1.2.0
```

For the **current implemented manifest**, Activity authors must use `activity.toml` and the authoring skill/source parser rather than this conceptual YAML fragment.

## 15. Universal manifest semantics

A future/runtime-neutral normalized manifest needs to express at least the following semantic concerns:

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

input:
  profile: pointer

compatibility:
  minimum_class: C0

capabilities:
  required:
    pointer: true
    audio: true
    canvas2d: true
  optional:
    touch: true
    controller: true
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

This is **conceptual**, not the current Python manifest syntax. The semantic separation is architectural; `src/greia_platform/activities.py` and `runtime/child-runtime.toml` own the implemented contract.

The current implemented manifest already accepts an `[input] profile = ...` table. Existing API 0.1 packages without it temporarily default to `hybrid` for compatibility; new and materially updated Activities should declare intent explicitly.

System Home/Back is intentionally absent from Activity manifest authority: an Activity does not request permission to show, hide or configure mandatory Greia system navigation.

Similarly, an interaction profile is not permission to open physical devices. An Activity requests `controller` capability only if it genuinely requires a controller, not merely to benefit from Greia mapping a controller onto an otherwise usable interaction profile.

## 16. Capability classes

Greia should classify machine capability separately from CPU architecture.

For example:

- **C0** — extreme low-resource compatibility class;
- **C1** — modest but comfortable 2D class;
- **C2** — modern baseline with richer multimedia/GPU capability;
- **C3** — high-capability optional features.

The precise thresholds must be measured and versioned. These labels must not acquire invented numeric thresholds merely because they appear in examples.

A Raspberry Pi 500 may be substantially more capable than an old Atom netbook even though both are first-class platform targets.

## 17. Progressive enhancement

An Activity may offer optional richer features while retaining a lower baseline.

Conceptually:

```text
C0 machine → simpler 2D effect path
C2 machine → higher-resolution/richer optional effect path
```

This should be one Activity package whenever practical, not separate “old computer” and “new computer” products.

Input also follows progressive enhancement: a pointer Activity can remain fully usable with mouse/touch while gaining a controller virtual pointer when controller input exists.

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

The stable semantic contract is key/value state plus private files/blobs scoped to `(profile_id, activity_id)`.

Conceptually:

```python
storage.get("current_level")
storage.set("current_level", 7)
storage.write_file("drawing.png", data)
```

and future Web Activities should receive equivalent semantics.

**Current Python implementation:** use `get_storage()` and `ActivityStorageClient.kv_get/kv_set/file_*` as documented by `skills/greia-activity-authoring/SKILL.md`; the simplified calls above are architectural shorthand.

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

Their official SDK exposes simpler portable logical operations.

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

The intended future canonical extension is `.greiabackup`.

The archive must be versioned and documented.

A conceptual internal structure could contain:

```text
manifest.yaml
profiles/
activity-data/
progress/
rewards/
shared/
```

This is not yet the implemented format; the exact schema requires its dedicated implementation/format decision.

---

# Part X — Activity packaging, installation, updates, and rollback

## 28. Single Activity package model

Python and Web Activities use the same outer package concept.

The intended future package extension is `.greiaactivity`.

Conceptual contents:

```text
manifest
activity payload
assets
integrity/authenticity metadata
```

This is not the current development directory schema. Current authors use `activity.toml` and the repository validator.

## 29. Parent-friendly removable-media installation

Inserting a USB stick or SD card may cause Greia to scan it automatically for valid Activity packages once the package-install phase is implemented.

No code is executed from the removable medium.

Greia reads bounded package metadata, validates packages, compares stable IDs and versions, then shows the parent a simple result.

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

Current source already distinguishes built-in and developer-unsigned origins for development/runtime authority. The **distribution signing/community trust chain** remains a future package-system decision.

The parent UI should eventually communicate trust without requiring cryptographic expertise.

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
- controller/virtual-pointer preferences if later exposed as bounded platform policy;
- tap-to-click;
- language/accessibility;
- storage usage;
- diagnostics/recovery.

Any controller setting exposed to parents must remain typed/bounded platform policy rather than arbitrary device-command execution.

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
                   ├→ Linux + Greia Platform → same Shell/Activity/input contracts
Raspberry Pi path ─┘
```

PC and Pi boot firmware/partition details may differ substantially without producing separate Greia products.

## 35. Declarative image profiles

Greia uses typed declarative image profiles rather than executable shell profile fragments.

A build profile declares intent such as:

- platform family;
- architecture;
- board/boot adapter;
- compatibility class;
- package sets;
- runtime families;
- display/input adapter;
- resource budget.

Runtime hardware probing/certification establishes what the actual machine can do.

Declarations are not evidence.

## 36. Reference hardware policy

Reference machines are acceptance authorities for their class.

At minimum the project should maintain physical or reproducible acceptance targets for:

- low-end i386/Atom-era PC;
- Raspberry Pi 400;
- Raspberry Pi 500;
- representative modern amd64 PC.

Controller/input acceptance should use representative supported USB/Bluetooth hardware as appropriate to the target's actual capabilities rather than assuming one brand/model defines the platform contract.

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
- raw device/input permissions;
- parent-state access;
- sibling Activity data;
- privileged OS operations;
- the platform-owned system-navigation surface/input region.

Controller support must not become a reason to expose broad `/dev/input` access to ordinary Activities.

## 38. Network denied by default

Especially for future Web Activities, arbitrary network access should not be the default.

An ordinary offline Activity should not be able to silently become a tracking client.

Network capability must be declared and mediated by policy.

## 39. Child-safe crash, return and input behavior

If an Activity crashes or hangs, Greia must reclaim control and return to a safe child-facing surface.

A terminal traceback, browser error page, Linux crash dialog, or frozen black screen is not an acceptable normal failure experience.

The platform owns the universal forced-return/watchdog mechanism.

ADR 0019 additionally gives the child a universal learned route home while the Activity is visible: the Greia Home control is outside Activity rendering/input authority, requests graceful stop, and relies on the same platform forced-return path if the Activity does not cooperate.

ADR 0020 requires physical controller/system input to be normalized/intercepted on the platform side so an Activity cannot consume a controller system button before Greia has a chance to act on it.

Exact current source/evidence status belongs in `HANDOVER.md`.

## 40. Fail closed

If a security-critical sandbox, package verifier, privileged helper, destructive-operation safety gate, or production mandatory-system-chrome/input boundary is unavailable, Greia should refuse the unsafe operation rather than silently falling back to a weaker path.

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

Rejected because separate Python/Web install, save, progress, parent, input, or system-navigation systems would duplicate core logic and break portability.

## 45. Per-Activity Python environments

Rejected for normal deployment because of disk use, dependency drift, update complexity, offline installation problems, and cross-architecture maintenance.

## 46. Chromium as the assumed Web runtime

Rejected as the default assumption because its footprint/process model is poorly aligned with the extreme low-resource target. This does not prohibit evidence-based use on a future high capability class, but the architecture must not depend on it.

## 47. X11 as a permanent platform dependency

Rejected. The current Xorg/xinit path is a **provisional compatibility implementation** while R7 evidence is gathered; it must not become permanent merely through inertia.

## 48. Java as a default first-class runtime

Rejected for now because the added runtime/maintenance cost lacks a compelling ecosystem payoff compared with Python + Web.

## 49. Backups containing only installed Activities

Rejected because child data must survive uninstall and restore even when the Activity is temporarily absent.

## 50. In-place package updates

Rejected because interruption or a bad package can destroy the working installation.

## 50.1 Activity-owned mandatory Home controls

Rejected. A Python helper drawn by Activity code or a DOM element injected into Web content cannot satisfy the invariant because the Activity runtime would retain the ability to cover, restyle, intercept or otherwise interfere with it. Mandatory system navigation belongs to Greia's higher-trust display/input layer.

## 50.2 Per-Activity controller stacks and raw input ownership

Rejected. Ordinary Activities must not implement the platform by opening raw joystick nodes, hard-coding SDL button indices/controller brands, inventing their own dead zones/reconnect policy, or obtaining broad `/dev/input` access. Those details belong below ADR 0020's runtime-neutral input contract.

## 50.3 Controller-as-global-Linux-mouse

Rejected as the general pointer architecture. Pointer-profile Activities may receive a Greia semantic virtual pointer, but globally emulating a host mouse creates surprising cross-context behavior and weakens the separation between Activity input and protected system input.

---

# Part XVI — Open research and implementation questions

The following are intentionally not settled by this living overview. Current phase status belongs in the active plan/handover.

## 51. Direct graphics/input stack

R7 requires evidence to select the exact shell/display/input architecture across old Intel and future Raspberry Pi paths.

Questions include:

- SDL KMSDRM behavior on reference machines;
- whether one tiny compositor/session broker materially improves trusted system-chrome ownership, input brokerage and Web runtime integration;
- GPU fallback behavior;
- mode switching and resolution control;
- boot-to-shell continuity without architectural X11 dependence;
- how protected Home/Back pointer/touch/controller input is consumed before Activity input;
- how controller/device reconnect is handled without exposing raw devices to Activities;
- handling of multiple Activity surfaces if ever genuinely required.

## 52. Web engine

Need benchmarked comparison of WPE WebKit / WebKit variants and any other realistic embedded engines on required architectures, including integration beneath the external Greia system-chrome layer and runtime-neutral input bridge.

## 53. Boot cover

Need a genuinely noninteractive branded boot path that never reveals normal Linux output through ordinary child input and degrades safely when graphics initialization fails.

## 54. Exact backup/package schemas

Need versioned format decisions and migration rules.

## 55. Package distribution trust chain

Need signing-key lifecycle, community package policy, offline authenticity verification, rollback, and recovery design above the already implemented development/built-in trust-origin distinction.

## 56. Trusted system-chrome backend evidence

The Home/Back product semantics are settled by ADR 0019. R7 still needs evidence for the concrete backend that enforces them across real Activity content.

Required evidence includes:

- Home remains visible above arbitrary Activity rendering;
- protected pointer/touch/controller system input is consumed before Activity delivery;
- Home initiates graceful stop and still returns from an unresponsive Activity through the existing forced-return authority;
- Back appears only from a valid Greia launch origin;
- the layer has acceptable RAM/disk/process/FD/startup/input/render cost on the Acer floor;
- future Web content cannot manipulate the system controls.

## 57. Controller/input backend evidence

The semantic model is settled by ADR 0020, but R7 still needs real backend and controller evidence.

Required evidence includes:

- Shell navigation with keyboard and supported controller;
- simple directional/game mappings with D-pad and analog left stick;
- pointer-profile virtual-pointer quality and latency;
- controller dead-zone behavior on representative hardware;
- disconnect/reconnect without losing keyboard/pointer operation;
- Guide/system input withheld from Activity content where the device exposes it;
- no broad raw `/dev/input` Activity authority;
- bounded controller handles/device state and acceptable Acer resource cost;
- equivalent transport semantics ready for future Web.

The exact fallback controller chord for Home, if one is needed, remains open until child accidental-activation testing justifies it.

## 58. Capability classes

Need measured thresholds and certification tests rather than invented labels.

## 59. ARM image strategy

Raspberry Pi 400/500 must be first-class, but board/image details require their own implementation profiles/testing rather than pretending x86 GRUB/MBR logic transfers to ARM.

---

# Part XVII — Architecture summary

## 60. One-sentence architectural summary

> **Greia is a console-like child operating environment centered on runtime-independent Activities, with platform-owned identity, lifecycle, storage, sessions, progression, installation, backup, permissions, parent controls, system navigation, input semantics, and hardware abstraction over a deliberately replaceable Linux/runtime/display/input substrate.**

## 61. Core diagram

```text
                           PARENTS
                              │
                    Greia Parents / Policy
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                     GREIA PLATFORM CORE                       │
│ Profiles • Registry • Storage • Sessions • Progression       │
│ Rewards • Packages • Backup • Permissions • Input • Assets   │
└──────────────────────────────┬────────────────────────────────┘
                               │
                     universal Activity contract
                  input profile + lifecycle + services
                               │
                     Activity Runtime Manager
                     ┌─────────┼─────────┐
                     │         │         │
                   Python      Web      Future
                     │         │         │
                     └─────────┼─────────┘
                               │
                 Activity content surface
                               │
             ┌─────────────────┴─────────────────┐
             │ Greia display/session/input      │
             │ Home/Back + protected input      │
             │ device normalization/brokerage   │
             └─────────────────┬─────────────────┘
                               │
                  hardware/platform adapters
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
         i386 netbook      Raspberry Pi       amd64 PC
                            400 / 500
```

The supported hardware may change. Runtime implementations may change. Linux distributions, boot mechanisms, display backends and controller hardware may change. The contracts above them are what make the system Greia.
