# Greia — Standalone Engineering Handover

**Date:** 2026-08-18  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Source head reviewed immediately before this handover commit:** `0e3eea018fc0299cd7511aa6e3155149cc9974c2`  
**External Parent HTML revision currently pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@e30bcbcab393354b8ffb63d5829c08711d8023bd`

This file owns the **current** implementation/evidence boundary. Historical hardware detail remains in the dated reviews and installation issue log; exact APIs/limits remain source-owned.

---

## 0. Branch, execution and evidence policy

`main` is the owner-required development/integration branch. Do not create feature/recovery/work branches unless the owner explicitly changes that policy. GitHub is canonical persistence; commit coherent fixes as work proceeds.

Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution. Verification runs on an owner-controlled environment.

Do not promote committed tests into PASS merely because the files exist.

### Last genuinely executed source evidence

A 2026-08-18 owner-controlled local-agent session, **before the later responsive/layout/localization/My-Greia source tranche**, recorded:

```text
make verify: 663 PASS
focused installation/UI/package/Parent/credential suites: 114 PASS
Parent-App npm test at pinned e30bcbc: 10 PASS
```

A follow-up 2026-08-18 local-agent run on the merged current head
(`edda4e6`) re-executed the complete source gate **after** the
responsive/layout/localization/My-Greia tranche:

```text
make verify: 679 PASS
current-ui-platform focused gate (installation-hardware, ui-motion-scroll,
  responsive-layout, activity-viewport, ui-preferences, theme-snapshot,
  activity-theme-access, activity-ui-preferences, child-shell-visual-context,
  my-greia-settings-contract, my-greia-runtime, customization, activity-ui,
  launcher-presentation, activity-packages, activity-contract, parent-api,
  localization, language-context, language-presentation): 131 PASS
Parent-App npm test at pinned e30bcbc: 10 PASS
```

The 663-PASS result is historical evidence for the earlier source boundary. The
679-PASS result is the current executed evidence at `edda4e6` and reflects the
merged responsive/layout/localization/My-Greia tranche.

A rebuilt installer-image and fresh physical Acer acceptance remain the next
required evidence; no rebuilt-image or fresh physical Acer PASS is claimed in
this handover.

---

# 1. Owner credential / SSH policy — active

The owner explicitly changed the credential/remote-development direction on 2026-08-18:

1. There is **no generated random end-install password/recovery code** that a parent must preserve.
2. Initial Parent/admin credentials are:

```text
username: greia
password: greia
```

3. The main Parent password is stored as a bounded digest, changeable through the typed Parent operation, and never returned by an API.
4. Each child may optionally have a separate Greia-profile password. Child passwords are Greia profile credentials, **not Linux users**.
5. During active development/hardware bring-up, developer/test installs remain reachable over SSH as `greia / greia` after install and reboot. Root SSH remains disabled. Key authentication may remain as an additional automation path.
6. Base/release images stay fail-closed unless/until release remote-access policy is explicitly changed.
7. If a Parent-password change is intentionally coupled to maintenance/SSH authentication, that coupling must go through a typed Greia-owned privileged operation, never a generic web-to-shell bridge.

Current local-agent entrypoint:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

That entrypoint composes the full install/Parent/SSH protocol with the later responsive-UI and My-Greia addenda; do not run only the older base protocol and miss the addenda.

---

# 2. Real-hardware installation reconciliation

Canonical records:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
```

The main lesson from Acer bring-up is now a platform rule: **a hardware fix is integrated only when the physical problem is resolved, authoritative build source contains the fix, a hardware-independent regression protects the failure class, and living documentation explains the cause.** A manual repair on one machine is diagnostic evidence, not repository closure.

Current persisted invariants include:

1. Build-host hardware is not target-hardware authority.
2. Live UUID, kernel/initrd/squashfs, install payload, digest and target profile form one coherent build artifact.
3. Graphical services use noninteractive stdin (`StandardInput=null`); installer subprocesses use `DEVNULL` unless input is explicitly required.
4. systemd-owned volatile paths needed during namespace setup use `RuntimeDirectory=` rather than late mkdir workarounds.
5. Current Xorg-owned service hardening matches the actual provisional Xorg/VT/DRM/input requirements instead of desktop-daemon assumptions.
6. `Xwrapper.config` uses the platform-owned appliance-session policy required by the current compatibility backend.
7. legacy `/dev/input/mouse*` aliases are ignored so libinput does not treat one pointer twice.
8. Bubblewrap uses a private `/run`, creates bind targets before binds and does not rely on the previously broken user-namespace assumptions.
9. The no-WM Xorg path explicitly hands keyboard focus to Greia with `XSetInputFocus`.
10. Shared initramfs overlays remain architecture-neutral. Target-kernel-aware hooks add `ahci`, `libata`, `sd_mod` only when the **target kernel** actually supplies them.
11. Developer access is explicit and separate from release/base-image policy.

Both target and live-installer images retain `MODULES=most`. Architecture-specific storage modules are handled by target-kernel-aware initramfs hooks rather than unconditional x86 lines in shared files.

R7 remains open. These fixes make the current Xorg compatibility path reproducible; they do **not** select Xorg as Greia's permanent session architecture.

---

# 3. Launcher interaction and Activity catalogue

Lifecycle/security authority remains in `LauncherApplication`; richer catalogue presentation remains in `GreiaLauncherPresentation`.

The installed X session now starts the profile-aware composition:

```text
python3 -m greia_launcher.child_shell
```

`GreiaChildShell` subclasses the richer presentation layer only to compose child visual preferences and the read-only Activity launch context. It does not replace package/runtime/permission/history/lifecycle authority.

Important launcher behavior currently implemented in source:

- shallow cached card/icon shadows;
- bounded hover/selection lift/scale and stronger selection outline;
- short ~420 ms squiggle/bounce launch flourish before the normal starting overlay;
- bounded visible Activity window rather than an unbounded retained widget set;
- selection-aware scrolling;
- mouse-wheel semantic-row scrolling;
- explicit scroll controls only when needed;
- bounded icon/font/shadow/decorated-icon caches;
- semantic launcher categories separate from educational taxonomy;
- stable category icons;
- explicit Activity-name band on every tile;
- persistent in-category header with local Back + category icon + title.

Current high-level launcher category vocabulary:

```text
All
Create
Play
Learn
Explore
My Greia
```

Current stable semantic icons:

```text
All       -> backpack
Create    -> palette
Play      -> puzzle_pieces
Learn     -> book
Explore   -> magnifier
My Greia  -> unicorn
```

`[presentation].categories` owns launcher navigation. `[education].categories` remains learning/progression metadata.

Launcher-local Back only changes launcher category navigation. It is **not** ADR-0019 running-Activity system chrome.

Canonical design:

```text
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
```

---

# 4. Platform-wide responsive UI contract

The owner explicitly rejected per-resolution/manual designer layouts.

Canonical requirements/decision:

```text
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md
```

Core rule: **a designer/coder authors one semantic layout; Greia derives actual rectangles from the live usable viewport.** Designers must not maintain `800x600`, `1024x600`, `1080p`, Acer/Pi or similar coordinate variants.

`1024x600` remains the low-resource/reference acceptance point, not a universal physical canvas.

Shared renderer-neutral source:

```text
src/greia_platform/responsive_layout.py
```

Required behavior:

- semantic regions rather than screen-model coordinates;
- reflow before shrink;
- collections change rows/columns and scroll/page automatically;
- bounded growth on large displays;
- no essential off-screen controls;
- hit geometry derives from the same layout result as visible geometry;
- aspect ratio is preserved for images/art;
- runtime resize invalidates size-dependent geometry/caches;
- generated/random viewport tests supplement the representative resolution matrix.

The responsive source/tests added after the last executed 663-PASS boundary are currently **UNEXECUTED** until the owner-controlled local agent reruns them.

---

# 5. Activity canvas / viewport architecture

Activities can range from simple math grids to painting/editing tools, simulations, side-scrollers and top-down games. Greia therefore does not force every Activity into one fluid-widget model.

The accepted Activity authoring model uses a common coordinate-transform core with multiple spatial semantics:

- **reference canvas / contain** — fixed puzzle/board/composition authored against a logical reference, normally 1024x600, automatically letterboxed/contained;
- **cover** — artwork/background regions that may crop safely while preserving aspect ratio;
- **expand/world** — games/simulations where wider/taller real viewports reveal more world instead of stretching it;
- **fluid UI** — grids/editors/collections where semantic regions reflow;
- **hybrid** — world/canvas plus Greia-responsive HUD/UI.

Renderer-neutral owner:

```text
src/greia_platform/activity_viewport.py
```

Pygame convenience helpers sit above it so simple Activity authors do not manually apply transform math to every point. Drawing and pointer/touch input use the same reversible transform. Platform Home/Back safe-area authority remains outside the Activity.

The authoring principle is: **design once at the reference logical scale or semantic world scale; Greia adapts to the physical display.** A side-scroller may deliberately reveal more world on a wider screen; a fixed puzzle may remain geometrically identical with safe bars; an editor may use the extra space as additional content area.

---

# 6. Localization and Activity language architecture

Renderer/runtime-neutral localization foundations now exist in source:

```text
src/greia_platform/localization.py
src/greia_platform/language_context.py
src/greia_platform/language_presentation.py
```

The product direction is:

```text
device default language
    -> optional per-child UI-language override
    -> Activity UI-language resolution/fallback
    -> optional platform-owned pre-launch Activity language chooser
```

Important semantic separation:

- **Greia/UI language** controls launcher/system/ordinary Activity UI strings/audio;
- **Activity content/learning language** is independent and may intentionally differ (for example Italian UI around an English writing/language-learning activity).

Single-language Activities remain valid. Example: an English-only Activity can be installed and launched on an Italian child profile; it falls back to English rather than being hidden/rejected.

Activity catalogue/title localization is deliberately separable from in-Activity UI support. An English-only Activity can still ship an Italian launcher name/description.

Child-facing language signalling is visual-first. The owner selected **platform-owned canonical flags**, not initials, as the primary language cue when a language distinction matters:

```text
English -> British flag
Spanish -> Spain flag
Italian -> Italy flag
...
```

A multilingual Activity's language indicator must be dynamic and represent the locale that will actually launch. An Activity that explicitly opts into selection should use a platform-owned flag-based pre-launch chooser rather than inventing a text-heavy language menu.

The localization policy/core has been added, but full profile persistence, launcher-title resolution, flag asset/render integration and end-to-end chooser wiring must be treated as **UNPROVEN/partially integrated** until source integration and owner-controlled tests close them. Do not claim multilingual launcher support merely because the policy classes exist.

---

# 7. My Greia — child-facing settings / personalization

The existing privileged built-in `org.greia.workshop-settings` has been evolved into the child-facing **My Greia** Activity while retaining its stable package identity for permission/migration continuity.

Canonical product requirement:

```text
docs/product/MY_GREIA_SETTINGS.md
```

Mandatory local-agent acceptance addendum:

```text
docs/testing/2026-08-18_MY_GREIA_ACCEPTANCE.md
```

## Child-facing scope

My Greia deliberately exposes only low-risk, profile-scoped settings with obvious visual impact:

- background/wallpaper;
- curated background color;
- curated accent color;
- curated text color;
- semantic interface size: `compact`, `normal`, `large`;
- own avatar.

It does **not** expose Wi-Fi, Parent password, child-password administration, SSH, package installation, disks, Linux users, boot/recovery, security permissions or arbitrary filesystem/system settings.

The target child may not read, so the Activity is visual-first: large icon tabs, actual color swatches, wallpaper previews, three visually different size samples, avatar images and visual check/error feedback. There is no Activity-owned fake Close/Home/Back button; universal system navigation remains platform-owned.

All essential My Greia controls now derive from `ActivityViewport.safe_ui_rect()` around the platform-owned `ActivitySystemChromeLayout` protected region. Background decoration may still fill the complete Activity surface, but tabs/settings/hit targets stay outside Home/Back authority at arbitrary supported resolutions. A regression covers 640x480, 800x600, 1024x600, 1366x768, 1920x1080, 720x1280 and 4K geometry.

## Semantic interface-size preference

New renderer-neutral owner:

```text
src/greia_platform/ui_preferences.py
```

The setting is intentionally **not** a free percentage/pixel slider. It stores only:

```text
compact
normal
large
```

The preference is atomically persisted per profile under customization state. Responsive layout remains authoritative; `large` is never permission to clip content or create a separate fixed layout.

`src/greia_platform/activity_ui.py::ChildUiMetrics` now composes this semantic preference with live viewport scaling, so first-party Pygame Activities already using shared metrics inherit it automatically without `if large:` layout branches. Growth remains bounded on large displays.

## Read-only visual context for ordinary Activities

A key architectural correction was made: previously ordinary Activities received only the canonical default theme unless they had customization write authority, so a child's color choice disappeared inside Writing/Painting.

Current design:

- **My Greia** retains `customization.manage` and direct managed profile customization access;
- ordinary Activities do **not** receive `GREIA_CUSTOMIZATION_DIR`;
- the profile-aware child shell injects a bounded resolved `GREIA_THEME_SNAPSHOT` and `GREIA_INTERFACE_SIZE` into ordinary launches;
- the snapshot contains safe resolved palette values only and deliberately carries no wallpaper path or write authority.

Source owners:

```text
src/greia_platform/theme_snapshot.py
src/greia_platform/activity_api.py
src/greia_launcher/theme.py
src/greia_launcher/child_shell.py
```

A direct regression now locks the ordinary-Activity boundary: visual snapshot present, semantic size present, customization path absent.

## Removable-media race and selection feedback corrections

My Greia wallpaper browsing uses the existing bounded removable-image scanner/importer. A review found a scan-to-render race: a candidate could be removed after scan but before thumbnail `stat()`, crashing the Activity. The thumbnail path now catches that disappearance and returns a placeholder/none instead. A source regression covers the missing-file case.

The current session also keeps an immediately selected removable wallpaper visibly selected while that source is still present. The managed imported wallpaper persists independently of the removable device; the removable-source selection marker itself is intentionally session-local rather than durable profile authority.

Physical eject/removal while the wallpaper page is open is still required acceptance; source regression is not physical evidence.

## Current My Greia evidence

All My Greia/UI-preference/theme-snapshot/child-shell source and tests in this tranche are **committed but not executed by this assistant/connector session**. They require the owner-controlled focused gate and `make verify` before PASS may be recorded.

---

# 8. Activity packages / Parent installation

The bounded `.greiaactivity` **new-install** seam remains implemented but does not close R10.

Platform source:

```text
src/greia_platform/activity_packages.py
```

Important implemented properties:

- bounded ZIP/request/entry/uncompressed-size handling;
- traversal/absolute/backslash/hidden/portable-casefold duplicate rejection;
- encrypted/symlink/special/compression-bomb rejection;
- streamed private staging;
- normal `ActivityRegistry` validation;
- package icon validation before activation;
- distinct `PARENT_TRUSTED_UNSIGNED` provenance;
- digest-addressed immutable read-only version;
- prepared read-only active tree;
- receipt prepared before activation;
- atomic active-directory rename as commit point;
- process-wide local-store serialization with a private `flock` lock.

Existing Activity IDs are rejected. Updates, removal, rollback selection, signatures/revocation, curated-store policy and save migration remain open R10 work.

Greia Parent defines:

```text
POST /api/v1/activities/install
```

but ordinary/release capability remains disabled while Parent transport/security remains provisional. Explicit developer/owner-enabled machines can exercise the new-install path.

The external Parent HTML client is separately pinned/integrity checked and must be changed in its own repository first, then repinned here.

---

# 9. Current verification required before hardware rebuild

Run on an owner-controlled current checkout from the final SHA.

The canonical test-session entrypoint is:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

Its current UI/platform focused gate includes installation regressions, responsive layout, Activity viewport, My Greia, read-only visual context, package/Parent and localization/language policy tests. After repairing any real failures, the agent must run the other full-session gates and finally:

```bash
make verify
```

Do not weaken containment/security/property tests to get a green result. The local agent is explicitly authorized to diagnose and repair real failures, add regressions, commit coherent fixes to `main`, rerun the smallest relevant set, and continue.

If source changes after an image was built, that old image is not physical evidence for the newer SHA.

---

# 10. Physical/rebuilt-image acceptance still required

After current-source tests pass:

1. build a fresh canonical developer/test installer for the actual target profile;
2. verify target-kernel initramfs storage support and live-media/payload coherence;
3. install on the Acer through the graphical installer;
4. confirm no random recovery-password UX;
5. confirm installed developer/test SSH `greia / greia` after reboot and root SSH rejection;
6. exercise the actual Parent HTML connection, main Parent-password change, child password set/replace/clear and owner-enabled Activity install;
7. inspect launcher names/categories/category Back/icon/scroll/hover/launch effects at 1024x600;
8. run the responsive matrix in an owner-controlled windowed/VM environment;
9. exercise My Greia colors, wallpaper, semantic size and avatar across at least two profiles;
10. physically eject removable media while My Greia wallpaper browsing is open;
11. prove My Greia controls never overlap platform Home/Back at the physical/reference target;
12. prove Writing/Painting receive read-only child visual context and no customization path;
13. measure idle/interaction resource behavior on the low-resource Acer floor;
14. where practical, repeat basic install/UI acceptance on another x86 target/VM so one Acer does not become a hidden platform contract.

---

# 11. Remaining blockers / deliberately incomplete work

- **R7 remains the primary blocking platform phase.** Xorg/xinit is provisional compatibility, not final selection.
- Current responsive/Activity-canvas/localization/My-Greia source needs fresh owner-controlled execution.
- Full Activity language integration is not complete: profile-language persistence, localized catalogue title resolution, dynamic flag rendering/assets and platform pre-launch chooser still need end-to-end wiring/testing.
- Parent secure pairing/encrypted transport remains open.
- General release Activity upload remains disabled until Parent transport/security and R10 lifecycle policy justify it.
- R10 update/remove/rollback/signature/revocation/save-migration remains open.
- Activity/category typography and all new customization choices need actual 1024x600 readability/performance acceptance.
- Controller/touch behavior for launcher categories, system navigation and My Greia still needs physical acceptance.
- The selected responsive/canvas architecture does not itself certify every first-party Activity; raw physical-coordinate legacy code (for example simple older game-like Activities) should be migrated through shared canvas/world helpers when found.
- Other later remediation phases remain governed by the active architecture-remediation plan.

---

# 12. Current source landmarks

```text
Installation/hardware:
  docs/INSTALLATION_ISSUES_LOG.md
  docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md

Responsive UI:
  docs/adr/0026-resolution-adaptive-ui-layout.md
  docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
  src/greia_platform/responsive_layout.py
  docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md

Activity canvas/world:
  src/greia_platform/activity_viewport.py
  skills/greia-activity-authoring/SKILL.md

Localization/language:
  src/greia_platform/localization.py
  src/greia_platform/language_context.py
  src/greia_platform/language_presentation.py

My Greia:
  docs/product/MY_GREIA_SETTINGS.md
  activities/workshop_settings/
  src/greia_platform/ui_preferences.py
  src/greia_platform/theme_snapshot.py
  src/greia_launcher/child_shell.py
  docs/testing/2026-08-18_MY_GREIA_ACCEPTANCE.md

Launcher/catalogue:
  src/greia_launcher/main.py
  src/greia_launcher/presentation.py
  src/greia_launcher/catalogue_view.py
  docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md

Parent/package install:
  src/greia_platform/activity_packages.py
  src/greia_parent/package_api.py
  runtime/parent-app-client.toml
  runtime/parent-app-client.manifest.json

Current local-agent entrypoint:
  docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 13. Continuation rule

Before further substantive implementation, read in order:

```text
AGENTS.md
docs/DOCUMENTATION.md
relevant product docs / accepted ADRs
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
```

Then inspect the exact source owners being changed. Do not use the responsive/localization/My-Greia tranche as justification to skip R7 or to label R10 complete. Do not relabel older source/hardware evidence as evidence for the current head.
