# Greia OS

**Version:** `0.13.0-phase0-dev`  
**Stage:** pre-public development / release-readiness work  
**Documentation reviewed:** 2026-09-02

Greia is an Activity-first computing platform for young children. Linux provides the low-level substrate; **Greia Shell is the child's operating-system experience**.

The product goal is closer to a small educational console/appliance than a simplified desktop PC:

```text
power on
  -> Greia
  -> choose child profile
  -> choose an Activity
  -> play / learn / create
  -> return safely to Greia
```

Normal child use must not expose a Linux desktop, terminal, login prompt, package manager, filesystem browser, browser chrome or generic window manager.

Greia is designed around constrained hardware as a first-class requirement. The first-generation Acer Aspire One remains the extreme low-resource reference floor; Raspberry Pi and modern x86 systems are intended to implement the same platform contracts rather than becoming separate products.

> **Release status:** Greia is not yet an ordinary-family public release. The repository is actively being prepared for open-source/public visibility, but R7 hardware/session evidence, licensing/provenance, security/privacy/community files and other release gates remain open. See `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`.

## Start here

For a new contributor:

```text
README.md
SETUP.md
docs/DOCUMENTATION.md
HANDOVER.md
```

Then use the relevant task router:

```text
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
```

Repository-wide contributor/agent rules are in `AGENTS.md`.

The [official Greia website work in progress](website/index.html) is a standalone static site in `website/`. It includes the parent-facing OS story, [installer release-status page](website/downloads.html) and [individual Activity library](website/library.html). Its public downloads remain disabled until reviewed artifacts exist; see [website/README.md](website/README.md) for asset provenance and publication boundaries.

For current implementation/evidence state, read `HANDOVER.md`. Do not infer current truth from a dated review or old test result.

## Core product model

### Activity is the universal content abstraction

Greia does not expose product categories such as “Python app” or “web app”. It has **Activities**.

An Activity may be a game, drawing tool, writing environment, science simulation, story, music toy, literacy exercise or system-facing child experience. Runtime differences sit below one platform contract.

Greia owns the cross-cutting concerns that must remain consistent and trustworthy:

- child profiles;
- Activity identity, discovery, trust and lifecycle;
- permissions/capabilities;
- profile-scoped storage and session history;
- progression, rewards and Awards/badges;
- platform Home/Back;
- runtime-neutral input conventions;
- package/update/backup policy;
- parent authority;
- localization/shared platform services.

Activities own their educational/creative experience and Activity-private state. They report facts/events rather than directly mutating platform authority.

### Greia-owned Home

Every child-facing Activity must retain the same Greia-owned Home affordance above Activity rendering/input authority. Activity code cannot hide, move, restyle, cover, intercept or disable the real control.

Home ends the Activity through Greia lifecycle authority and returns to the Shell. Optional Greia Back is platform-defined and is not browser history or Activity-internal navigation.

Architecture/product authority:

```text
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

The September 2026 missing-Home regression has been corrected and physically verified on the Acer at its exact tested candidate; current source/evidence scope is maintained in `HANDOVER.md`.

### Learned input, not controller-brand logic

Greia standardizes interaction intent instead of asking each Activity to rediscover hardware.

Examples:

```text
navigation
pointer
directional
game
text
hybrid
```

The simple game baseline is intentionally learnable:

```text
keyboard:   arrow keys + Space
controller: D-pad/left stick + south face button
```

Physical controller ownership, dead zones, protected system input and virtual-pointer policy remain platform concerns. Ordinary Activities do not get raw `/dev/input` merely to support controllers.

See ADR 0020 and `docs/product/ACTIVITY_INPUT_STANDARDS.md`.

### Lightweight UI, not a desktop

Greia's shared semantic UI vocabulary is deliberately small:

```text
Screen
  -> optional Overlay / Sheet
       -> Panel / Card / Collection
            -> Control
```

A Collection is a semantic child grouping, never a filesystem folder. Greia does not introduce general-purpose draggable windows, taskbars or arbitrary desktop z-order.

See ADR 0018.

### Responsive child UI

Greia uses one authored semantic layout that adapts to the actual viewport. Activities may use fluid UI, a logical reference canvas, world-camera coordinates or hybrids, but they should not fork layouts per physical device/resolution.

See ADR 0026, ADR 0027 and `docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md`.

### Localization and child text

Greia separates locale selection, translated coverage and release-language certification. A selectable locale is not automatically a fully supported release language.

ADR 0028 owns localization/language context. ADR 0034 owns the child-facing letter-case policy: child UI defaults to CAPITAL presentation, with a profile preference for normal case; child-authored text is preserved as authored.

### Offline-first and child-owned data

Core child operation must work without cloud services. Durable child data is profile-scoped and intended to remain architecture-neutral across supported hardware families.

Greia does not require a cloud account for core use and does not treat advertising/engagement-maximization as a product requirement.

## Greia Parents

**Greia Parents** is the parent-management surface. The current direction is a responsive web client talking to a versioned Greia Parent API; future clients use the same semantic API rather than SSH or a generic privileged shell.

Parent authority includes bounded operations such as profiles, Activity policy, system settings, backups, updates and paired-device management. Linux-specific mechanics remain behind typed platform services.

Normal/release Greia keeps SSH off by default. Developer remote access is an explicit development-image capability, not a parent-management dependency.

Read:

```text
docs/product/PARENT_MANAGEMENT.md
docs/architecture/GREIA_PARENT_MANAGEMENT.md
docs/adr/0022-parent-management-api-client-pairing-and-privilege-boundary.md
```

The production pairing/encrypted-transport release gate remains open; see the public-release checklist.

## Activity Simulator

Greia includes a Mac-first development Activity Simulator:

```bash
python3 tools/greia_simulator.py
```

It composes real Greia registry/trust/profile/runtime/storage/history/lifecycle/layout services over a synthetic development device/workspace seam. It is not a look-alike mock launcher.

Simulator evidence is useful for semantic integration but **does not prove** Bubblewrap isolation, production display/session behavior, trusted-chrome non-coverability, physical controller behavior, boot/install behavior or Acer/Pi performance.

See:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

## Activity authoring

The current public-facing authoring contract starts at:

```text
skills/greia-activity-authoring/SKILL.md
```

Validate an Activity with:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

Greia's authoring goal is that human contributors and software agents can build conforming Activities from repository documentation and deterministic validation rather than hidden project knowledge.

## Voice and prerecorded speech

Greia does **not** run normal narration TTS models on the child device.

New prerecorded speech is produced at authoring time through the canonical Voice Production Engine:

```bash
python3 tools/greia_voice.py doctor
```

Canonical entry point:

```text
tools/greia_voice.py
```

Natural canonical character speech currently uses the accepted Chatterbox/MLX authoring provider on supported Apple-Silicon production workstations; pedagogical/Dani speech uses the deterministic native/system route behind the same semantic engine. Whisper, where used, is advisory only; human listening remains acceptance authority.

The shared character library currently contains an owner-accepted v0.2 set of 180 generic reactions plus 12 character introductions. Runtime integration/placement is a separate concern from authoring acceptance.

Read:

```text
skills/greia-voice-production/SKILL.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

## Architecture and engineering

Normative decisions live in `docs/adr/`. The architecture overview is a synthesis, not a second ADR system:

```text
docs/architecture/GREIA_ARCHITECTURE.md
```

Key current decisions include:

- ADR 0012 — platform architecture constitution;
- ADR 0014 — Greia identity, ARM parity and direct-graphics direction;
- ADR 0018 — lightweight UI foundation;
- ADR 0019 — platform-owned Activity navigation;
- ADR 0020 — runtime-neutral input/controller model;
- ADR 0022 — Parent API/pairing/privilege boundary;
- ADR 0023 — open Activity ecosystem/distribution;
- ADR 0025 — Awards/badges/celebrations;
- ADR 0026/0027 — responsive UI and Activity coordinate spaces;
- ADR 0028 — localization/language context;
- ADR 0029 — real-runtime Activity Simulator/non-drift;
- ADR 0030 — transactional system-update architecture;
- ADR 0031 — platform-owned microphone processing;
- ADR 0032 — profile presentation/grammatical agreement;
- ADR 0033 — fail-soft Activity cross-bindings/dev-noise scrub;
- ADR 0034 — child text letter-case policy.

Engineering implementation guidance:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
```

Greia prefers cohesive domain objects, narrow typed variation seams, purposeful polymorphism, explicit ownership/cleanup, bounded caches/resources and simple low-cost implementations that remain understandable to outside contributors.

## Build and verification

Canonical provider-free source verification:

```bash
make verify
```

Run it on the exact checkout whose result you are retaining. Current PASS counts and physical evidence belong in `HANDOVER.md` / dated evidence, not in this README.

Image/installer/physical procedures are selected by `HANDOVER.md`, the active plan and `docs/testing/`; source or Simulator tests do not substitute for hardware evidence.

GitHub-hosted Actions are opt-in only under repository policy; owner-controlled verification is supported and expected.

## Repository map

```text
src/greia_platform/     shared platform contracts/services
src/greia_launcher/     child Shell and Activity/session orchestration
src/greia_parent/       Parent API/server composition
src/greia_installer/    graphical installer
src/greia_simulator/    development-only real-service simulator composition
activities/             curated built-in Activities
runtime/                runtime/policy declarations
assets/                 reviewed/runtime/source assets and catalogues
build/                  image profiles, overlays and build machinery
tools/                  validation, simulator, release/operator tooling
docs/adr/               normative architecture decisions
docs/product/           accepted product requirements
docs/architecture/      living architecture/subsystem synthesis
docs/engineering/       implementation/performance guidance
docs/testing/           exact evidence procedures
docs/reviews/           dated reviews/evidence/history
docs/release/           public-release gates
skills/                 contributor/agent task routers and authoring guides
```

## Licensing and public-source status

The selected policy is described in:

```text
docs/governance/LICENSING_AND_TRADEMARK.md
```

Current direction includes MPL-2.0 for Greia-owned software, CC BY 4.0 for Greia-owned documentation and separate rights/provenance for third-party components/media. **The mechanical repository-wide licensing/provenance audit is still pending.** Do not interpret the selected policy as a claim that every existing file/asset has already been cleared or relicensed.

Before the repository is made public, the project still needs the required license/notices, security/contribution/privacy/community entry points and history/provenance review defined by the release-readiness gate.

## Current release work

The complete release checklist is:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

The first dedicated documentation/public-repository cleanup review is:

```text
docs/reviews/2026-09-02_PUBLIC_REPOSITORY_DOCUMENTATION_DEEP_DIVE.md
```

Greia may reach **public source** before it reaches **ordinary-family binary release**. Those are deliberately different acceptance thresholds; public visibility must not be used to imply hardware/release readiness that has not been proven.
