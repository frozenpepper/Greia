# Greia — Standalone Engineering Handover

**Date:** 2026-08-19  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Simulator adversarial review source boundary:** `b4cda82ca18996ad67859976292f0457315052d4`  
**Simulator hardening source/docs boundary before this handover update:** `f1e2ffdb7eaacdb9f6bd938fd917f731f0ef92e3`  
**Adversarial simulator review:** `docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md`  
**Hardening response:** `docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md`  
**External Parent HTML revision currently pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@e30bcbcab393354b8ffb63d5829c08711d8023bd`

This file owns the **current** implementation/evidence boundary. Historical hardware detail remains in the dated reviews and installation issue log; exact APIs/limits remain source-owned.

---

## 0. Branch, execution and evidence policy

`main` is the owner-required development/integration branch. Do not create feature/recovery/work branches unless the owner explicitly changes that policy. GitHub is canonical persistence; commit coherent fixes as work proceeds.

Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution. Verification runs on an owner-controlled environment.

Do not promote committed tests into PASS merely because the files exist.

### 0.1 2026-08-19 — Greia Activity Simulator source tranche

A Mac-first, core-platform-neutral **Greia Activity Simulator** is committed on `main`.

Normative/developer documentation:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

Implementation source:

```text
src/greia_simulator/__init__.py
src/greia_simulator/device.py
src/greia_simulator/workspace.py
src/greia_simulator/runtime.py
src/greia_simulator/python_activity.py
src/greia_simulator/child_shell.py
src/greia_simulator/app.py
tools/greia_simulator.py
tests/test_greia_simulator.py
```

The architectural invariant is deliberately strict: **the simulator is not a second Greia implementation.** It supplies only synthetic/missing-machine facts below existing variation seams and runs the real Greia services above them.

The hardened Python simulator path uses:

- the real `GreiaChildShell` presentation/profile/catalogue implementation;
- the real canonical launcher runtime-service composition and one supervisor publication path;
- the real `ActivityRegistry` and `RuntimeCatalogue`;
- the real package trust vocabulary;
- the real `PermissionBroker` and `RuntimeManager`;
- the real `ActivitySupervisor` lifecycle semantics via the profile-visual specialization;
- the real Activity storage/history/event services;
- the real profile/customization/UI-preference state;
- the real responsive/canvas/system-safe geometry;
- a synthetic typed `GreiaHAL` for exact viewport + semantic capability facts;
- injected runtime adapters through the canonical launcher composition seam;
- an isolated, checkout-bound, single-writer simulator workspace outside the source checkout;
- a workspace lease that records both the controller PID and any owned Greia Shell PID so controller crashes cannot silently free live mutable state;
- a narrow **simulator-only** Python/Pygame child bootstrap that is executed by absolute Greia-owned path and maps current Activity fullscreen display requests to the selected synthetic desktop viewport;
- shared Shell display request hooks rather than simulator `_draw()`/private-cache manipulation.

The desktop control plane currently provides:

```text
geometry-only viewport presets: 1024x600, 1280x720, 1280x800, 1366x768, 1920x1080
bounded custom WIDTHxHEIGHT
explicit real child-profile selector
compact / normal / large child interface size for that profile
semantic capability toggles derived from the canonical runtime catalogue
Load Activity Folder…
Install Activity Package…
Start / Apply
Restart
Stop
unexpected-child-process health reporting
controller/Shell process-lease ownership
prominent trusted-code-only safety warning
```

`Load Activity Folder…` now inspects a finite lstat/content-fingerprinted source snapshot before managed copying, applies the canonical Activity byte limit, rejects symlinks/special/executable/forbidden content and source/state overlap, validates through the ordinary Greia registry together with built-in identity authority under `DEVELOPER_UNSIGNED` trust, and publishes transactionally while preserving the previous valid Activity on failure. The copy checks exact content digests, not only inode/size/mtime, so same-metadata source mutation is rejected.

`Install Activity Package…` calls the canonical `ActivityPackageService`; there is no simulator-only unzip/install authority. The import is intentionally lazy so non-package simulator functions do not inherit a POSIX package-lock import on hosts where the canonical package service is not available.

Colors/wallpaper/avatar remain best exercised through the actual My Greia Activity rather than a duplicate simulator settings implementation.

### Web/HTML boundary

Web/HTML Activity execution is **not implemented by this simulator tranche**. A Web manifest may be registry-valid while the runtime manager correctly reports that no canonical Web adapter is available. ADR 0029 explicitly forbids a simulator-only Safari/Chrome/private-webview workaround. Future simulator Web support must consume the canonical R9 Web runtime adapter/SDK once R9 implements it.

### Simulator evidence boundary

Simulator results may be retained as **simulator/developer evidence** for real registry/trust/runtime/profile/storage/history/lifecycle/responsive semantics against synthetic device facts.

They do **not** prove:

- Bubblewrap/kernel/filesystem containment;
- Xorg/DRM/KMS/compositor/session-backend behavior;
- trusted system-chrome non-coverability/input interception;
- physical controller/touch/audio/network/removable-media behavior;
- boot/installer/initramfs behavior;
- Acer/Pi memory/CPU/GPU/performance;
- R7/R8/R9/R10/R14 closure.

The desktop simulator is **not an untrusted-code security sandbox**. Load/run only trusted development Activities/packages. Semantic capability toggles exercise Greia compatibility/authority semantics; they do not physically revoke host filesystem/input/network access.

R7 therefore remains the primary blocking platform phase exactly as before this simulator tranche.

### 0.2 2026-08-19 — adversarial review and hardening response

The first simulator implementation was reviewed adversarially against ADR 0029, the real launcher composition, runtime adapter, supervisor/lifecycle, ActivityRegistry, package service and acceptance claims. The complete review and source disposition are:

```text
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md
```

**Current classification:**

```text
ADVERSARIAL FINDINGS: ADDRESSED IN SOURCE
FOCUSED HARDENING REGRESSIONS: COMMITTED, NOT YET EXECUTED FOR HARDENED HEAD
FULL make verify: NOT YET EXECUTED FOR HARDENED HEAD
MAC END-TO-END ACCEPTANCE: NOT YET EXECUTED FOR HARDENED HEAD
PRODUCTION/HARDWARE CLAIMS: NONE
```

The adversarial findings were addressed by making the simulator thinner, not more special:

1. **One canonical service graph:** `build_launcher_runtime_services()` accepts typed HAL/runtime-adapter variation while retaining one PermissionBroker/RuntimeManager/storage/history graph; `GreiaChildShell` owns the one runtime-service/supervisor rebuild/publication sequence. The simulator no longer owns `build_simulator_runtime_services` or a simulator supervisor.
2. **Shared Shell display seam:** `GreiaLauncherPresentation` owns initial/resize display request + caption hooks. `GreiaSimulatorChildShell` does not replace `_draw()`, private cache behavior or `_rebuild_runtime_services()`.
3. **Trusted Python bootstrap:** the simulator runtime adapter wraps the canonical Python command and invokes `python_activity.py` by absolute Greia-owned path. Activity content cannot shadow it through `python -m`; trusted Greia `src/` is restored ahead of Activity content and stale `GREIA_SIMULATOR*` variables are removed before Activity execution.
4. **Lifecycle/process-owned Stop/Restart:** control-plane SIGTERM unwinds the simulator Shell, which requests normal supervisor stop, polls boundedly and escalates through `force_stop(... SYSTEM_SHUTDOWN)` before the desktop controller resorts to process kill. The controller retains its `Popen` handle until exit is confirmed, registers the Shell PID in the workspace lease, clears that PID before dropping the dead handle and refuses replacement Start/lease release when ownership cleanup fails.
5. **Transactional source loading:** preflight is lstat-aware, byte-bounded and content-fingerprinted; symlinks/special/executable/forbidden content and source/state overlap are rejected; copy verifies inspected file identity/size/mtime and exact content digest; final registry validation occurs before the previous valid managed Activity is discarded.
6. **Capability/preset claims corrected:** capability choices derive from canonical runtime vocabulary; simulator owns only the HAL mapping and fails on unmapped future canonical capabilities. Presets are geometry-only and no longer imply Acer/tablet/CPU/RAM/GPU emulation.
7. **Workspace authority hardened:** `workspace.json` binds schema and checkout; rebind is legal only under the writer lease. `.workspace.lock` is inode-owned, records controller + Shell PIDs, cannot be released while the child is registered, fails closed on partial/malformed state, retains a workspace when an orphaned Shell still lives, uses POSIX PID probing only on POSIX and fails closed on non-POSIX hosts rather than using unsafe Windows `os.kill(pid, 0)` semantics.
8. **Profile/UI polish corrected:** the control plane edits the selected real profile rather than always the first, and Start preserves a newly selected interface size instead of rereading stale persisted state first.
9. **Regression scope expanded:** test source covers canonical composition injection, shadow resistance, identity absence, display hooks, capability denial, workspace binding/locking/rebind/process ownership portability, controller Start/Stop lease semantics, profile persistence, positive/negative source staging including content TOCTOU, rollback, canonical package delegation, unavailable Web runtime, bounded shutdown and a real local Pygame READY/storage/event/history/STOP integration path.

The current Python fullscreen wrapper remains temporary R7 compatibility debt; it is **not** promoted into a universal simulator display architecture. Windows/Linux packaged simulator maturity also remains future work. These are explicit open boundaries, not unresolved versions of the adversarial blockers.

### Verification actually executed for this hardened tranche

No owner-controlled focused/full/manual execution has yet been recorded for the hardened head. The initial simulator source had earlier been syntax-compiled, but later hardening changed source substantially; that historical syntax check is not current-head evidence.

Required next commands on an owner-controlled current checkout are:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
make verify
python3 tools/greia_simulator.py --state-dir "$HOME/.greia-simulator-acceptance"
```

Then execute `docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md`.

Do not describe the simulator source or current `main` as test-PASS until those commands actually run at the recorded SHA.

### Last genuinely executed source evidence

A 2026-08-18 owner-controlled local-agent session, **before the later responsive/layout/localization/My-Greia source tranche**, recorded:

```text
make verify: 663 PASS
focused installation/UI/package/Parent/credential suites: 114 PASS
Parent-App npm test at pinned e30bcbc: 10 PASS
```

A follow-up 2026-08-18 owner-controlled local-agent run at exact source boundary
`edda4e687d9d73fe69cef40cbbbcea7a7ff0db7d` re-executed the complete source gate **after** the main responsive/layout/localization/My-Greia tranche:

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
679-PASS result is executed evidence for **exactly `edda4e6`**, not for later
commits. After that run, source changed again in several coherent UI/lifecycle
tranches:

- My Greia safe-area implementation/regression (`3c0ee15`, `0e3eea0`);
- first-party post-first-frame READY corrections + structural regression (`3bce9cc`, `522c33e`, `880c379`, `acbf0a4`, `c22c481`);
- Shape Garden logical-canvas/system-navigation migration and lightweight-presentation regression (`aaa24a1`, `a650357`, `e7c77d3`, `1768738`);
- shared Pygame Activity-safe geometry derived from system chrome plus Painting/Writing migration (`8e586a8`, `11c434f`, `f1b614d`, `ff54863`, `bdd67b9`);
- interface-size × resolution safe-geometry regression (`85f60f9`);
- current operator/authoring/authority documentation (`b01613f`, `bf355fe`, `31c206e`);
- `0c06f5a` / `d6bed0e` restore Painting/Writing's pre-migration formatting around the new safe-UI calls; these last two commits are intended as **diff-noise cleanup only**, not additional behavior;
- the 2026-08-19 Activity Simulator implementation, adversarial review, shared launcher seams, transactional source hardening, process/workspace lease hardening and expanded regression/docs tranche described above.

Those later source/test changes are **committed but not yet covered by a fresh
owner-controlled full PASS**. Do not describe 679 PASS as current-head evidence.

A rebuilt installer image and fresh physical Acer acceptance remain required;
no rebuilt-image or fresh physical Acer PASS is claimed in this handover.

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

# 4. Platform-wide responsive UI and system-safe Activity geometry

The owner explicitly rejected per-resolution/manual designer layouts.

Canonical requirements/decision:

```text
docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
docs/adr/0026-resolution-adaptive-ui-layout.md
docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md
```

Core rule: **a designer/coder authors one semantic layout; Greia derives actual rectangles from the live usable viewport.** Designers must not maintain `800x600`, `1024x600`, `1080p`, Acer/Pi or similar coordinate variants.

`1024x600` remains the low-resource/reference acceptance point, not a universal physical canvas.

The Activity Simulator is intended to exercise these same shared layout/canvas paths at exact synthetic viewports. The adversarial **source blockers have now been addressed**, but broad simulator acceptance remains **unexecuted** until the hardened focused suite/full gate and manual protocol run on an owner-controlled current checkout. Do not treat committed hardening test source as executed evidence.

Shared renderer-neutral source:

```text
src/greia_platform/responsive_layout.py
src/greia_platform/activity_viewport.py
```

Pygame Activity controls now also have one shared system-safe layer in:

```text
src/greia_platform/activity_ui.py
```

`ChildUiMetrics` keeps its old full-surface `toolbar_button()` for non-Activity Greia surfaces, but Activities should use:

```text
activity_safe_rect()
activity_toolbar_button()
activity_content_rect()
```

Those helpers derive their geometry from `ActivitySystemChromeLayout` + `ActivityViewport.safe_ui_rect()`, so essential controls/content and trusted Home/Back share one authority rather than duplicating guessed insets.

Painting and Writing have been migrated to these helpers and no longer draw Activity-owned close buttons. Their Gallery/Undo/New/Eraser controls and editor/palette regions now live in the platform-safe Activity area.

The geometry regression covers `compact`, `normal` and `large` child interface-size preferences across 640x480, 800x600, 1024x600, 1366x768, 1920x1080, 720x1280 and 4K representative surfaces. This is committed test source, not executed current-head evidence.

Required behavior remains:

- semantic regions rather than screen-model coordinates;
- reflow before shrink;
- collections change rows/columns and scroll/page automatically;
- bounded growth on large displays;
- no essential off-screen controls;
- no Activity control in trusted Home/Back protected geometry;
- hit geometry derives from the same layout result as visible geometry;
- aspect ratio is preserved for images/art;
- runtime resize invalidates size-dependent geometry/caches where the surface supports resize;
- generated/random viewport tests supplement the representative resolution matrix.

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

Pygame convenience owner:

```text
src/greia_platform/pygame_canvas.py
```

### Shape Garden migration

Shape Garden is now a concrete first-party proof of the simple reference-canvas path rather than a known raw-physical-coordinate exception:

- stable 1024x600 **logical** scene coordinates;
- `PygameReferenceCanvas` presentation;
- physical pointer positions mapped back through `canvas.pointer()`;
- pointer input inside platform-protected system chrome rejected before gameplay mapping;
- no Activity-owned close button;
- explicit `pointer` input profile;
- bounded rendering (`shapes[-120:]`);
- normal whole-frame scale rather than `smoothscale` for this flat procedural scene, preserving the transform while avoiding unnecessary CPU on low-resource hardware.

The Activity still exits on the authoritative `activity_stop_requested()` lifecycle; ESC remains a development/keyboard convenience, not system-navigation authority.

### First-frame readiness contract

A source review found all four bundled Python Activities were signaling `mark_activity_ready()` before their first `pygame.display.flip()`. That lets the supervisor believe a child-facing Activity is presentable while the visible surface may still be blank/uninitialized.

The bundled Activities now publish READY once, only after their first rendered frame has been presented. `tests/test_first_party_activity_readiness.py` discovers the first-party Python entrypoints and requires the frame presentation and READY publication to occur in the same launch loop, with presentation first.

This is a lifecycle semantic, not a Pygame timing optimization: **READY means a usable child-facing frame exists.** Initialization alone is not readiness.

### Explicit remaining Painting document-model debt

Painting's **controls/editor viewport** are now responsive and system-safe, but its durable PNG document surface is still sized from the current editor viewport. That pre-existing behavior can resample a painting when opened on a differently sized editor and then saved. It does not satisfy the longer-term resolution-neutral document-content requirement.

Do not hide this by calling Painting fully resolution-neutral. Migrate the painting document to a stable logical/document coordinate space in a separate focused tranche with explicit save-compatibility tests rather than folding an implicit data migration into unrelated UI work.

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

All essential My Greia controls derive from `ActivityViewport.safe_ui_rect()` around the platform-owned `ActivitySystemChromeLayout` protected region. Background decoration may still fill the complete Activity surface, but tabs/settings/hit targets stay outside Home/Back authority at arbitrary supported resolutions.

## Semantic interface-size preference

Renderer-neutral owner:

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

`src/greia_platform/activity_ui.py::ChildUiMetrics` composes this semantic preference with live viewport scaling. Painting and Writing now consume both the semantic size and the platform-safe Activity geometry from that shared layer. Shape Garden consumes the semantic metrics for its child cursor and uses the reference-canvas path for its scene.

## Read-only visual context for ordinary Activities

A key architectural correction was made: previously ordinary Activities received only the canonical default theme unless they had customization write authority, so a child's color choice disappeared inside Writing/Painting.

Current design:

- **My Greia** retains `customization.manage` and direct managed profile customization access;
- ordinary Activities do **not** receive `GREIA_CUSTOMIZATION_DIR`;
- the profile-aware child shell injects a bounded resolved `GREIA_THEME_SNAPSHOT` and `GREIA_INTERFACE_SIZE` into ordinary launches;
- the snapshot contains safe resolved palette values only and deliberately carries no wallpaper path or write authority;
- the base supervisor constructs a sanitized launch environment first; the child-shell composition then supplies these visual-context values from the active profile rather than inheriting arbitrary host values.

Source owners:

```text
src/greia_platform/theme_snapshot.py
src/greia_platform/activity_api.py
src/greia_launcher/theme.py
src/greia_launcher/child_shell.py
```

A direct regression locks the ordinary-Activity boundary: visual snapshot present, semantic size present, customization path absent.

## Removable-media race and selection feedback corrections

My Greia wallpaper browsing uses the existing bounded removable-image scanner/importer. A review found a scan-to-render race: a candidate could be removed after scan but before thumbnail `stat()`, crashing the Activity. The thumbnail path now catches that disappearance and returns a placeholder/none instead. A source regression covers the missing-file case.

The current session also keeps an immediately selected removable wallpaper visibly selected while that source is still present. The managed imported wallpaper persists independently of the removable device; the removable-source selection marker itself is intentionally session-local rather than durable profile authority.

Physical eject/removal while the wallpaper page is open is still required acceptance; source regression is not physical evidence.

## Current My Greia evidence

The My Greia/UI-preference/theme-snapshot/child-shell source present at `edda4e6` was executed in the 679-PASS full source gate and the 131-PASS focused UI/platform gate. The later safe-area/readiness/shared-safe-geometry work is committed but **not yet re-executed** in an owner-controlled run. Physical 1024x600 acceptance is also still open.

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

The simulator adversarial source fixes S1–S5 are committed. **Do not reimplement them as a prerequisite.** First verify them with the focused regression suite:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

If it fails, diagnose the real current-head failure and repair it without weakening the architecture/non-claim contracts. The focused suite includes controller/Shell process-lease ownership, source content-TOCTOU protection and the real local Pygame READY/storage/event/history/STOP integration when the host has Pygame available.

Then run the canonical full source gate:

```bash
make verify
```

Only after focused + full source gates are green should the operator execute the manual Mac protocol:

```text
docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md
```

Start the control plane for that protocol with an isolated state root, for example:

```bash
python3 tools/greia_simulator.py \
  --state-dir "$HOME/.greia-simulator-acceptance"
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
8. run the responsive matrix in an owner-controlled windowed/VM environment for compact/normal/large; the hardened simulator may accelerate this developer pass but does not replace physical/reference acceptance;
9. exercise My Greia colors/wallpaper/semantic size/avatar across at least two profiles;
10. physically eject removable media while My Greia wallpaper browsing is open;
11. prove My Greia controls never overlap platform Home/Back at the physical/reference target;
12. prove Writing/Painting receive read-only child visual context and no customization path;
13. prove Painting/Writing essential controls/content stay outside trusted Home/Back chrome;
14. prove Shape Garden drawing/input mapping works at 1024x600 and at least one different aspect ratio, with protected system-chrome clicks not entering gameplay;
15. prove first-party Activities do not signal READY before their first visible frame;
16. measure idle/interaction resource behavior on the low-resource Acer floor;
17. where practical, repeat basic install/UI acceptance on another x86 target/VM so one Acer does not become a hidden platform contract.

---

# 11. Remaining blockers / deliberately incomplete work

- **R7 remains the primary blocking platform phase.** Xorg/xinit is provisional compatibility, not final selection.
- All safe-area/readiness/Shape-Garden/shared-safe-UI source/test changes after `edda4e6` need fresh owner-controlled execution; do not promote the 679-PASS result across those source changes.
- **Activity Simulator adversarial findings are addressed in source, but the hardened head is unverified.** The focused simulator suite, full `make verify` and manual Mac acceptance still need owner-controlled execution before any simulator PASS claim.
- The desktop simulator is **not an untrusted-code security sandbox**. Load/run only trusted development Activities/packages. Synthetic capability toggles prove Greia semantic compatibility/grant behavior, not physical host-input suppression or production filesystem containment.
- The simulator's current Python fullscreen wrapper is development compatibility below the runtime-adapter seam, not a production display contract. It should migrate to the stronger shared R7 Activity display/surface seam when that architecture exists rather than grow into broad simulator monkeypatching.
- Web/HTML Activity simulation is intentionally unavailable until the canonical R9 Web runtime adapter exists.
- Windows/Linux **packaged simulator maturity** remains open. Core startup no longer requires the canonical package service at import time and stale-lock behavior fails closed on non-POSIX hosts, but complete host packaging/manual acceptance has not been performed.
- A partial/malformed workspace lease intentionally fails closed. Manual stale-lock recovery must only happen after proving no controller or recorded Shell from that workspace is alive; this is conservative recovery behavior, not a second-writer shortcut.
- Canonical Activity package install may remain unavailable on hosts that cannot currently import/run the canonical package service. The portability fix belongs in that canonical service; a simulator-only installer remains forbidden.
- Painting's durable document surface is still viewport-sized and requires a separate resolution-neutral document/save migration with compatibility tests.
- Full Activity language integration is not complete: profile-language persistence, localized catalogue title resolution, dynamic flag rendering/assets and platform pre-launch chooser still need end-to-end wiring/testing.
- Parent secure pairing/encrypted transport remains open.
- General release Activity upload remains disabled until Parent transport/security and R10 lifecycle policy justify it.
- R10 update/remove/rollback/signature/revocation/save-migration remains open.
- Activity/category typography and all new customization choices need actual 1024x600 readability/performance acceptance.
- Controller/touch behavior for launcher categories, system navigation and My Greia still needs physical acceptance.
- Other later remediation phases remain governed by the active architecture-remediation plan.

---

# 12. Current source landmarks

```text
Installation/hardware:
  docs/INSTALLATION_ISSUES_LOG.md
  docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md

Responsive / safe Activity UI:
  docs/adr/0026-resolution-adaptive-ui-layout.md
  docs/product/RESPONSIVE_UI_AND_DISPLAY_LAYOUT.md
  src/greia_platform/responsive_layout.py
  src/greia_platform/activity_ui.py
  tests/test_activity_ui.py
  tests/test_core_activity_system_safe_ui.py
  docs/testing/2026-08-18_RESPONSIVE_UI_ACCEPTANCE.md

Activity canvas/world/lifecycle:
  src/greia_platform/activity_viewport.py
  src/greia_platform/pygame_canvas.py
  activities/shape_garden/
  tests/test_shape_garden_contract.py
  tests/test_first_party_activity_readiness.py
  skills/greia-activity-authoring/SKILL.md

Activity Simulator:
  docs/adr/0029-real-runtime-activity-simulator.md
  docs/development/GREIA_ACTIVITY_SIMULATOR.md
  docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md
  docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md
  docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md
  src/greia_launcher/composition.py
  src/greia_launcher/child_shell.py
  src/greia_launcher/presentation.py
  src/greia_simulator/
  tools/greia_simulator.py
  tests/test_greia_simulator.py

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
relevant product docs / accepted ADRs (including ADR 0029 for simulator work)
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md (when Activity/simulator workflow is relevant)
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md (historical finding set)
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md (current source disposition)
```

Then inspect the exact source owners being changed. Do not use the responsive/localization/My-Greia/simulator tranches as justification to skip R7 or to label R9/R10 complete. Do not relabel older source/hardware evidence as evidence for the current head, and do not relabel simulator evidence as backend/hardware/security evidence.
