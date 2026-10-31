# Greia Architecture — Living Overview

**Status:** Living architecture synthesis  
**Last reviewed:** 2026-10-24
**Authority:** accepted ADRs are normative; implemented APIs/schemas are owned by source/runtime declarations; this document synthesizes the cross-cutting architecture.  
**Scope:** Product philosophy, platform boundaries, Activity model, runtimes, profiles, storage, progression, Awards/badges/celebrations, package/update model, backup/restore, parent controls, hardware abstraction, ARM/i386 strategy, graphics/input direction, security boundaries, and open questions.

---

## 0. Purpose and how to read this document

Greia is a non-profit, open-source computing platform for children. It is built on Linux, but it is not intended to behave like a conventional Linux desktop distribution.

This document explains the stable product architecture above any particular Linux distribution release, bootloader, graphics backend, CPU family, or Activity runtime.

**It is not a competing ADR/implementation specification.**

- `docs/adr/*` contains accepted normative decisions.
- `docs/DOCUMENTATION.md` defines documentation ownership/precedence.
- source/runtime declarations own exact currently implemented schemas/APIs.
- `skills/greia-activity-authoring/SKILL.md` is the current Activity-authoring specification for agents/developers.
- Current branch and device-test evidence is maintained privately; public release statements must be grounded in verified test artifacts.

Several examples below are deliberately **conceptual/future-facing** to describe stable semantics. A YAML manifest, a simplified `storage.get()` call, a Web SDK example, `.greiaactivity` layout, Award declaration, or capability-class label shown here is not automatically the current authoring API.

Greia should be able to evolve from an old i386 netbook to a Raspberry Pi 400/500 or a modern PC without becoming several different products.

The core rule is:

> **Greia presents one child operating environment, one Activity model, one profile model, one progression/Award/storage model, one input model, and one parent-management model across all supported hardware and runtimes.**

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
- visible progression, rewards, Awards/badges and collection presentation;
- profile customization;
- system Activities designed for the child;
- stable keyboard/pointer/touch/controller navigation conventions.

The shell is not merely an application launcher placed on top of another desktop shell.

A child-facing Activity never becomes the ultimate owner of the child's route back to Greia. ADR 0019 requires platform-owned system navigation above the Activity surface.

Likewise, an Activity is not expected to rediscover and normalize physical controllers by itself. ADR 0020 places standard interaction semantics and physical controller authority at the Greia platform boundary.

ADR 0025 similarly places durable Award authority and the official badge/new-best celebration experience at the Greia platform boundary rather than inside individual Activities.

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
- Award/badge authority and collection semantics;
- permissions;
- parental controls;
- backup/restore;
- lifecycle supervision;
- platform-owned Home/Back system navigation;
- runtime-neutral interaction profiles and input semantics;
- uninstall behavior;
- compatibility/capability checks.

For update ownership, ADR 0038 adds typed application packages over the same
platform-owned Activity/package boundary. Python snapshots, built-in
Activities and combined updates publish through one application generation;
Parent-source Activity changes retain their Parent trust and PERSIST owner.
The stable bootstrap and recovery helper remain outside replaceable
application code. Full Linux/system-slot releases remain the ADR 0036 A/B
path, wrapped as the `full_system` package type where Parent upload is used.
Exact format, source roots and status fields live in the package source and
`docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md`.

## P-03 — Global progression belongs to Greia

Activity code may report facts such as:

- score submitted;
- objective completed;
- level completed;
- educational milestone reached;
- session result;
- optional Activity-defined achievements/events.

The platform decides how those facts affect global progression.

An Activity must not directly grant arbitrary global currency, modify another Activity's progress, rewrite the child's platform-owned reward ledger, or directly mark a platform Award as earned.

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
- earn local progression/rewards/Awards;
- browse their earned Award collection;
- shut down safely.

Cloud services may later add synchronization or convenience. They must not become the sole owner of identity, saves, progression or Awards.

## P-11 — Open formats

Greia Activity packages and Greia backup archives should be documented, inspectable formats.

Parents should not need proprietary software to understand that their child's drawings, creations, save data and portable progression exist inside an archive.

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

## P-14 — Achievement is platform-owned and child-positive

Greia distinguishes **Rewards**, **Awards/badges**, and **Celebrations**.

Activities report facts and scores. Greia decides when validated evidence satisfies a durable Award rule, records the Award in profile-owned platform state, and presents the official celebration through Greia-owned UI.

A genuine personal-best improvement may be celebrated without creating a permanent badge every time. Activity-specific Awards may eventually be declared through bounded package metadata, but runtime code does not directly write the Award ledger. Cross-Activity Awards are Greia policy because only Greia has authoritative cross-Activity evidence.

Earned Awards survive Activity uninstall and logical backup/restore. Core Award policy must not depend on daily-login streak loss, expiring badges, advertising, purchases, artificial FOMO, public leaderboards, or screen-time-maximizing mechanics.

ADR 0025 is normative; `docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md` owns the child-facing product experience.

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
- bounded platform-owned transient presentation where required by the selected display/session design;
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
- Award/Achievement evaluation and Award Ledger;
- bounded celebration scheduling/presentation state;
- Permission Broker;
- Package Manager;
- Backup/Restore Service;
- Parent Management Service;
- shared asset/language/accessibility services;
- health/recovery state.

### Layer D — Greia Shell

The Greia Shell renders and coordinates the child operating environment, including the post-Activity destination associated with platform Home/Back navigation, standard navigation behavior across available input devices, the child-facing Award collection, and deferred/safe celebration presentation where appropriate.

### Layer E — Activities

Activities use Greia APIs rather than depending directly on Linux, board firmware, CPU architecture, display-server details, raw input devices, controller brands, system-chrome authority, or Greia's private progression/Award ledgers.

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
   ├── bounded Greia-owned transient presentation when needed
   ├── normalized keyboard/pointer/touch/controller input
   └── Greia Shell or supervised Activity surface
```

The trusted system-chrome/input/presentation layer is tiny and fixed-purpose. It is not a taskbar, desktop panel, notification center, or general window-manager surface.

## 6. X11 status

The current installed production path uses a deliberately narrow **Xorg/xinit compatibility backend** while the R7 display/session/input architecture is measured and proven.

That backend is **PROVISIONAL**. It is not an Activity API and does not make X11 part of the intended Greia architectural layer.

The target direction remains direct/appliance-oriented. Xorg may survive only as an explicitly scoped compatibility adapter if physical evidence shows that a reference device requires it.

Even in that case, X11 remains below the platform/Activity contract.

The current Xorg path is not automatically certified for ADR 0019, ADR 0020 or ADR 0025 merely because it can display an Activity and receive keyboard/pointer events. Production certification also requires a trusted system-chrome/input implementation and a bounded platform-controlled presentation path that Activity content cannot own.

## 7. DRM/KMS-first direction

The preferred direction is to use the kernel's modern direct display interfaces and the thinnest practical rendering path.

For Python/Pygame, SDL should use a suitable direct backend where hardware allows.

For a Web Activity runtime, Greia should select an embeddable engine/backend able to fit the appliance model rather than launching a conventional desktop browser.

Direct scanout alone is not the complete product requirement. If an Activity becomes the uncontested owner of both framebuffer and physical input, another trusted layer must still preserve mandatory Greia Home/Back, protected system input, runtime-neutral controller normalization, and the bounded platform-owned transient presentation required by ADR 0025 or an equivalent safe Greia-controlled deferred path.

## 8. Compositor/session-broker policy

Greia does not require a compositor merely because desktop Linux normally uses one.

A tiny compositor or embedded scene-management/session layer may be adopted only if it materially simplifies:

- trusted Home/Back composition above Activity content;
- protected system-chrome/controller input routing;
- bounded Greia-owned Award/celebration presentation;
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

Current renderer-neutral geometry/actions live in `src/greia_platform/system_chrome.py`; the backend-neutral lifecycle/navigation seam lives in `src/greia_launcher/system_chrome.py`. Exact current implementation/evidence status belongs in private maintainer notes.

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

### 8.3 Platform-owned Award and celebration presentation

ADR 0025 requires Greia to own the official Award/badge and personal-best celebration experience.

Granting and presenting are separate operations:

```text
validated event / score
       ↓
progression transaction
       ↓
Award grant / best-score update
       ↓
bounded celebration request
       ↓
Greia chooses an appropriate safe presentation moment
```

The durable grant must survive a crash/reboot even if the animation has not yet appeared. Conversely, a timed puzzle, drawing gesture or text entry must not be destroyed merely because a progression transaction completed.

The selected display/session architecture therefore needs the smallest bounded capability to present Greia-owned transient UI above Activity content when safe, **or** a safe Greia-controlled transition/deferred presentation path that preserves the same product semantics.

This is not authorization for a desktop notification system, arbitrary windows, Activity-owned overlay access, unbounded z-order, or background application surfaces. The mandatory Home/Back route remains authoritative and must not be obscured/disabled by celebration presentation.

Exact source/API/presentation implementation is not yet selected. See `docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md`.

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

System Home/Back, protected physical-input ownership, progression/Award authority, and official Award celebration presentation are deliberately above the runtime adapter rather than implemented separately by each runtime.

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

Likewise, the official Greia Award celebration is not a DOM widget controlled by Web content. Web Activities report the same factual event/score semantics and Greia owns award evaluation/presentation outside the page's authority.

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
- bounded Greia-owned transient presentation integration;
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

ADR 0025 adds a future package concern without changing today's manifest: an Activity may eventually declare a bounded catalogue of **Activity-scoped Award definitions** bound to its own validated factual events/scores. That future metadata does not give runtime code a `grant_badge()` authority and does not permit an Activity to define Greia-wide Awards. The exact schema remains future source-owned work.

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

The same principle applies to Greia Award presentation: a C0 machine may use a simpler bounded 2D reveal than a higher-capability machine, while Award identity, persistence and child meaning remain the same.

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
- **earned Awards/badges and collection state**;
- child creations.

The exact underlying Unix UID strategy is an implementation/security decision and may evolve independently.

## 19. Profile isolation

One Activity session for one profile must not receive arbitrary access to another profile's data.

Platform APIs should scope storage automatically.

Runtime sandboxes should fail closed when required isolation cannot be established.

Awards/badges are likewise profile-scoped. One child earning an Award does not silently grant it to sibling profiles on the same device.

---

# Part VIII — Storage, sessions, saves, progression, and Awards

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
- Award definitions/earned-Award ledger and sufficient portable presentation metadata when implemented;
- Activity registry/install history;
- backup metadata;
- parental policies.

Activity-owned private state includes:

- puzzle/game state;
- current local level;
- child drawings/projects;
- Activity-local settings;
- Activity-defined content state.

An Activity's private save area is not the authoritative place to record a Greia Award.

## 22. SQLite is suitable internally

Greia may use SQLite for platform-owned structured data such as sessions, registry entries, progression events, Award grants and installation records.

Activity authors should not be forced to interact with the platform database directly.

Their official SDK exposes simpler portable logical operations.

## 22.1 Rewards, Awards, and celebrations remain distinct

ADR 0017 already establishes score/progression/reward authority. ADR 0025 extends it with durable Awards and transient celebrations.

Conceptually:

```text
Activity fact / score
      ↓
Greia progression engine
      ├── best-score aggregate
      ├── reward balance/ledger
      └── Award rule evaluation
              ↓
          Award ledger
              ↓
      bounded celebration request
```

A new personal best normally updates the best-score aggregate and may trigger a `New Best!` celebration. It does not create a new permanent badge for every improvement. Specific milestone Awards are separate policy.

Activity-specific Awards may eventually be declarative package metadata; Greia-wide Awards remain platform policy.

## 22.2 Earned Awards outlive Activity installation

Uninstalling an Activity must not erase platform Award history.

The Award representation/backup contract must preserve enough stable identity and bounded child-facing representation to render an earned Award even when the package that originally defined it is absent. A missing package path must never turn the collection into a broken-image/filesystem-error surface.

## 23. Save schema versions

Activity save schema versions are distinct from Activity package versions.

An update may keep the same save schema or introduce a migration.

When a migration is required, Greia should snapshot/transactionally preserve the previous state before activating the migrated data.

Migration failure should not silently destroy the previous save.

## 24. Uninstall does not mean erase

Default Activity uninstall behavior should remove the package while retaining child data.

Parents may explicitly request deletion of saved data separately.

Reinstallation should automatically reconnect to the preserved namespace.

Platform progression and Award history are also separate from normal package uninstall and must remain unless an explicit future progression-reset operation says otherwise.

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
- **earned Awards/badges and enough portable presentation state to preserve the collection**;
- workshop customization;
- Activity inventory/version metadata;
- portable parent settings where appropriate.

Installed Activity binaries should not normally be embedded by default because that can make backups unnecessarily large.

## 26. Restore onto another architecture

A backup made on i386 must be restorable on ARM64 when compatible Activities exist.

Activity data for an Activity not currently installed should still be restored and retained dormant.

Installing that Activity later should make its preserved state available again.

Earned Awards must remain visible after restore even before the originating Activity is reinstalled; exact presentation metadata/fallback mechanics are defined by the future Award storage/backup schema.

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
awards/
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

Future package work may add validated Activity-scoped Award metadata/assets, but that is not a current manifest field and must not be invented by documentation before source owns the schema.

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

An Activity update may improve Award names/artwork/definitions, but stable earned Award identity must not silently disappear or duplicate because presentation metadata changed.

## 31. Signature/authenticity

Open source does not mean arbitrary unsigned code should be indistinguishable from trusted distribution content.

Current source already distinguishes built-in and developer-unsigned origins for development/runtime authority. The **distribution signing/community trust chain** remains a future package-system decision.

The parent UI should eventually communicate trust without requiring cryptographic expertise.

Award metadata/assets from third-party packages are part of the content that future package validation/trust policy must bound and validate; remote badge artwork is not required for normal offline operation.

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
- diagnostics/recovery;
- a bounded read-only summary of child progression/Awards where product requirements justify it.

Any controller setting exposed to parents must remain typed/bounded platform policy rather than arbitrary device-command execution.

Normal product parent controls do not fabricate arbitrary child Awards; Awards represent trusted progression evidence.

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
                   ├→ Linux + Greia Platform → same Shell/Activity/input/Award contracts
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

Award/celebration presentation must also remain bounded enough for the C0/Acer floor; richer machines may use richer visuals without changing Award semantics.

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
- platform progression/reward/Award ledgers;
- privileged OS operations;
- the platform-owned system-navigation and transient-presentation surface/input region.

Controller support must not become a reason to expose broad `/dev/input` access to ordinary Activities.

Award support must not become a reason to expose direct Award-ledger mutation or a general trusted-overlay API to Activities.

## 38. Network denied by default

Especially for future Web Activities, arbitrary network access should not be the default.

An ordinary offline Activity should not be able to silently become a tracking client.

Network capability must be declared and mediated by policy.

Normal Award evaluation, grant, collection browsing and celebration must not require network connectivity.

## 39. Child-safe crash, return and input behavior

If an Activity crashes or hangs, Greia must reclaim control and return to a safe child-facing surface.

A terminal traceback, browser error page, Linux crash dialog, or frozen black screen is not an acceptable normal failure experience.

The platform owns the universal forced-return/watchdog mechanism.

ADR 0019 additionally gives the child a universal learned route home while the Activity is visible: the Greia Home control is outside Activity rendering/input authority, requests graceful stop, and relies on the same platform forced-return path if the Activity does not cooperate.

ADR 0020 requires physical controller/system input to be normalized/intercepted on the platform side so an Activity cannot consume a controller system button before Greia has a chance to act on it.

ADR 0025 requires Award grants to persist independently from presentation. A crash after the grant but before the ceremony must not lose the Award, and recovery must not create an unbounded replay storm of stale celebrations.

For current implementation details consult the source; hardware evidence and work-session checkpoints are private.

## 40. Fail closed

If a security-critical sandbox, package verifier, privileged helper, destructive-operation safety gate, or production mandatory-system-chrome/input boundary is unavailable, Greia should refuse the unsafe operation rather than silently falling back to a weaker path.

Award presentation failure is different: the durable Award must remain granted even if a non-security-critical animation cannot be shown. Greia may defer/simplify the ceremony rather than corrupt progression state.

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
- **Greia Award** — durable platform-owned achievement identity; badge is the initial child-facing presentation form;
- **Professor Pip** — child-world character/guide where appropriate.

## 42. Legacy technical identifiers

Old implementation identifiers beginning with `pip_`, old paths, and old package extensions are migration debt, not architectural vocabulary.

They should not be mass-renamed blindly if doing so would break persisted Activity IDs, save paths, Award IDs, or compatibility boundaries.

Renames should preserve migration mappings and be tested.

---

# Part XV — Explicit rejected architectures

## 43. Conventional Linux desktop

Rejected because it exposes implementation substrate, increases resource cost, fragments the child experience, and creates unnecessary escape/failure surfaces.

## 44. Runtime-first platform

Rejected because separate Python/Web install, save, progress, Award, parent, input, or system-navigation systems would duplicate core logic and break portability.

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

## 50.4 Activity-owned authoritative badges and reward popups

Rejected. Activities may provide ordinary local feedback, but durable Greia Awards, cross-Activity achievement rules, personal-best authority and the official Greia collection/celebration cannot live in runtime-specific Activity save/UI code.

## 50.5 Desktop notification/window manager justified by Awards

Rejected. ADR 0025 requires only a bounded Greia-owned transient presentation path or safe platform-controlled deferred presentation. It does not justify a general notification center, movable/resizable windows, arbitrary z-order, background apps or desktop shell.

---

# Part XVI — Open research and implementation questions

The following are intentionally not settled by this living overview. Current phase status belongs in the active plan/handover.

## 51. Direct graphics/input stack

R7 requires evidence to select the exact shell/display/input architecture across old Intel and future Raspberry Pi paths.

Questions include:

- SDL KMSDRM behavior on reference machines;
- whether one tiny compositor/session broker materially improves trusted system-chrome ownership, input brokerage, bounded Award/celebration presentation and Web runtime integration;
- GPU fallback behavior;
- mode switching and resolution control;
- boot-to-shell continuity without architectural X11 dependence;
- how protected Home/Back pointer/touch/controller input is consumed before Activity input;
- how a bounded Greia-owned transient celebration can be composed or safely deferred without Activity authority;
- how controller/device reconnect is handled without exposing raw devices to Activities;
- handling of multiple Activity surfaces if ever genuinely required.

## 52. Web engine

Need benchmarked comparison of WPE WebKit / WebKit variants and any other realistic embedded engines on required architectures, including integration beneath the external Greia system-chrome/transient-presentation layer and runtime-neutral input bridge.

## 53. Boot cover

Need a genuinely noninteractive branded boot path that never reveals normal Linux output through ordinary child input and degrades safely when graphics initialization fails.

## 54. Exact backup/package schemas

Need versioned format decisions and migration rules, including the Award state/presentation representation required by ADR 0025.

## 55. Package distribution trust chain

Need signing-key lifecycle, community package policy, offline authenticity verification, rollback, and recovery design above the already implemented development/built-in trust-origin distinction. Future Activity-scoped Award metadata/assets must participate in the same bounded package validation/provenance model.

## 56. Trusted system-chrome and transient-presentation backend evidence

The Home/Back product semantics are settled by ADR 0019. ADR 0025 adds a bounded Greia-owned transient presentation requirement for Awards/celebrations. R7 still needs evidence for the concrete backend that enforces these properties across real Activity content.

Required evidence includes:

- Home remains visible above arbitrary Activity rendering;
- protected pointer/touch/controller system input is consumed before Activity delivery;
- Home initiates graceful stop and still returns from an unresponsive Activity through the existing forced-return authority;
- Back appears only from a valid Greia launch origin;
- a bounded platform-owned celebration can be shown at a safe moment or deterministically deferred to a Greia-controlled transition without giving the Activity trusted-overlay authority;
- celebration presentation cannot obscure/disable mandatory Home/Back;
- the layer has acceptable RAM/disk/process/FD/startup/input/render cost on the Acer floor;
- future Web content cannot manipulate the system controls or official Greia Award presentation.

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

## 57.1 Award subsystem implementation

ADR 0025 settles the authority/product boundary but not the exact source schema.

A future implementation tranche still needs to define and test:

- stable Award definition and earned-grant schemas;
- transactional/idempotent Award evaluation over ADR 0017 evidence;
- personal-best celebration generation without badge spam;
- Activity-scoped declarative Award metadata and bounds;
- Greia-wide cross-Activity Award policy;
- bounded celebration queue and safe-presentation scheduling;
- Shell collection model/rendering and accessibility/localization;
- durable presentation fallback/snapshot behavior when an Activity is uninstalled;
- logical `.greiabackup` export/import with originating Activity absent;
- optional bounded Parent API achievement summary;
- C0/Acer CPU/RAM/disk/render/input measurements.

Until these exist and execute, Awards/badges/celebrations are **SELECTED architecture and accepted product requirements**, not an implemented runtime feature.

## 58. Capability classes

Need measured thresholds and certification tests rather than invented labels.

## 59. ARM image strategy

Raspberry Pi 400/500 must be first-class, but board/image details require their own implementation profiles/testing rather than pretending x86 GRUB/MBR logic transfers to ARM.

---

# Part XVII — Architecture summary

## 60. One-sentence architectural summary

> **Greia is a console-like child operating environment centered on runtime-independent Activities, with platform-owned identity, lifecycle, storage, sessions, progression, rewards/Awards, installation, backup, permissions, parent controls, system navigation, input semantics, child-safe celebration/collection, and hardware abstraction over a deliberately replaceable Linux/runtime/display/input substrate.**

## 61. Core diagram

```text
                           PARENTS
                              │
                    Greia Parents / Policy
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      GREIA PLATFORM CORE                         │
│ Profiles • Registry • Storage • Sessions • Progression          │
│ Rewards • Awards • Packages • Backup • Permissions • Input      │
│ Assets • Celebration scheduling • Parent semantic services       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                      universal Activity contract
                   input profile + lifecycle + factual events
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
              ┌─────────────────┴──────────────────┐
              │ Greia display/session/input       │
              │ Home/Back + protected input       │
              │ bounded Greia celebration path    │
              │ device normalization/brokerage    │
              └─────────────────┬──────────────────┘
                                │
                   hardware/platform adapters
                                │
               ┌────────────────┼─────────────────┐
               │                │                 │
          i386 netbook      Raspberry Pi       amd64 PC
                             400 / 500
```

The supported hardware may change. Runtime implementations may change. Linux distributions, boot mechanisms, display backends and controller hardware may change. The contracts above them are what make the system Greia.
