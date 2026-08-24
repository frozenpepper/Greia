# Greia — Standalone Engineering Handover

**Date:** 2026-08-24  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**External Parent HTML runtime revision currently pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@7ff7e318eb246618dab26939ba086999864538ce`  
**Newer reviewed-source candidate containing microphone-processing UI:** `frozenpepper/Greia-Parent-App-Html@cdea281a1848d1372a18822a559dc15494e749b0`  
**Parent client integration state:** `source-pinned-not-yet-vendored`; microphone UI repin still requires local test/integrity regeneration

This file is the project-wide **current continuation contract**. Chronology belongs in plans/reviews; exact APIs/limits remain source-owned.

---

# 1. Current state at a glance

## Latest retained physical performance work

The reference Acer Aspire One launcher hover-transition tranche remains accepted at its measured scope.

On-device profiling found pointer hover transitions rebuilding the full 1024×600 scene at roughly **189.6 ms/frame (~5.3 fps)** while steady cached frames were already fast. The accepted `68899e9` tranche added:

- one-time display-format conversion of shared cached surfaces;
- a bounded working-set cache;
- pre-composited opaque scene backdrops;
- static-scene versus dynamic hover/launch cache-key separation;
- tile-level repair for hover/launch dynamics with full-rebuild fallback;
- backdrop-based profile badge repair;
- measurement-backed adaptive idle pacing.

Measured reference-Acer result:

```text
hover transition: 189.6 ms → 26.6 ms  (~5.3 → 37.6 fps)
full scene rebuild: 191.0 ms → 81.8 ms
steady cached frame: 3.46 ms → 3.34 ms
idle launcher CPU: ~10–11% → ~5–8%
card-sweep CPU avg: ~32% → ~16%
launcher RSS: ~153 MB → ~153 MB
```

On-device visual verification covered Collection Home, category grid, hover lift/title disclosure, focus/selection badge, pagination and rapid cross-card traversal without ghosting.

`docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` is now the single accumulating performance manual for measured device cost, cache/alpha/invalidation rules, evidence discipline and case studies. The microphone tranche does not supersede or modify that performance work.

## Contributor engineering skills integration (2026-08-23)

The measured performance lessons and existing OOP/polymorphism foundations are now integrated into the contributor-facing skills rather than remaining specialist documentation only.

Created:

```text
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-os-work/SKILL.md
```

The Activity engineering companion is mandatory for new/substantively changed first-party Activity implementation. It makes `main.py` a thin composition/bootstrap boundary, defines pragmatic module/class decomposition and OOP/polymorphism/reuse protocols, and operationalizes the Acer performance rules: no heavyweight IO/decode/scale/font/device/subprocess/config/storage work in hot loops, bounded caches with invalidation, pre-rendered static presentation, dirty rendering, bounded animations and fast-path equivalence testing.

The OS work skill is the practical contributor router for architecture ownership, extension seams, reusable class placement, OOP/polymorphism, low-resource performance, UI/display/input authority, audio/microphone boundaries, simulator policy, install/update/trust, comments/docstrings, documentation maintenance and evidence discipline.

`AGENTS.md` now requires the OS skill for substantive platform/Shell/Parent/installer/simulator/build/runtime/hardware-service work and requires future changes to keep it synchronized. The performance manual records Activity-skill integration as complete. Durable review: `docs/reviews/2026-08-23_ENGINEERING_SKILLS_INTEGRATION.md`.

## Acer boot contract and boot screen physical acceptance (2026-08-23)

The physical Acer Aspire One boot contract reconciliation and boot screen test protocol (`GREIA_ACER_BOOT_CONTRACT_AND_BOOT_SCREEN_TEST_PROTOCOL.md`) has been fully executed and accepted on hardware.

- **Target host:** Acer Aspire One (`greia-dev.local`, `legacy-x86-i686-dev`, Linux `6.1.0-52-686 i686`).
- **Source contract reconciliation:** `src/greia_platform/boot_contract.py` now enforces the postmortem contract: developer builds require `panic=0` (no reboot loop on failure), `console=tty1`, `loglevel=4`, `systemd.show_status=true`, `rd.systemd.show_status=true`, `udev.log_priority=4`, `vt.global_cursor_default=1`, and forbid release arguments (`quiet`, `splash`, `loglevel=0`, `console=null`, `panic=5`, `systemd.show_status=false`, `rd.systemd.show_status=false`, `udev.log_priority=3`, `vt.global_cursor_default=0`).
- **Pre-change state & backup:** Full backup created at `/var/lib/greia/boot-acceptance-backup-20260823-160333` containing previous `10_greia_appliance`, `grub.cfg`, `greia-theme.txt`, `greia-boot-logo.png`, `boot-logo.ppm`, and `greia-fb-splash`.
- **Initramfs storage module preservation:** Verified `/boot/initrd.img-6.1.0-52-686` retains critical storage drivers before and after regeneration: `ahci.ko`, `libahci.ko`, `libata.ko`, `acard-ahci.ko`, `sd_mod.ko`.
- **Target compilation:** `greia-fb-splash.c` compiled directly on target using `klcc -static -Os -s` producing a native i386 ELF32 executable installed to `/usr/lib/greia-boot/greia-fb-splash` and packaged into the initramfs hooks (`init-top`, `local-premount`, `init-bottom`).
- **GRUB generation & contract validation:** GRUB configuration generated via `update-grub` on the Acer and validated remotely with `PYTHONPATH=src python3 -m greia_platform.boot_contract ... --developer` passing 1 kernel command line. Running kernel command line verified:
  ```text
  BOOT_IMAGE=/vmlinuz root=UUID=cdc4dc87-acde-4bf9-bad1-0ac2b413446f ro loglevel=4 systemd.show_status=true rd.systemd.show_status=true udev.log_priority=4 vt.global_cursor_default=1 console=tty1 panic=0 systemd.crash_shell=no systemd.crash_chvt=0 consoleblank=0
  ```
- **Safety gates & automatic SSH recovery:** Mandatory SSH recovery gate passed prior to reboot; second independent fresh SSH connection confirmed (`GREIA_SSH_PRE_REBOOT_OK`). Machine rebooted cleanly with `systemctl reboot`. Automatic SSH password login (`greia/greia`) succeeded on attempt 1 post-boot (`GREIA_SSH_POST_BOOT_OK`).
- **Launcher & services:** `greia-launcher.service` active with 0 failed units. Service restarted cleanly and verified reachable via SSH (`GREIA_SSH_AFTER_LAUNCHER_RESTART_OK`). Developer remote marker `/etc/greia-os/developer-remote` preserved throughout.
- **Verification evidence:** 73/73 focused boot tests PASSED (`test_boot_contract`, `test_boot_diagnostics_hardening`, `test_boot_animation_contract`, `test_boot_experience_contract`, `test_boot_progress_contract`, `test_launcher_boot_fallback`, `test_grub_security`). Full repository gate `make verify` PASSED (1,089 unit tests OK, 19/19 activities valid). Stored evidence in `tmp/boot-contract-acer-acceptance/`.

## Clinica Cuccioli Activity architecture calibration (2026-08-23)

`activities/clinica_cuccioli` is the first real calibration of the strengthened Activity engineering rules. It was deliberately selected because it required **no new generated character voices** while its previous ~33.5 KB `main.py` mixed gameplay state, random treatment generation, persistence, event publication, procedural SFX synthesis, input, particles and all rendering.

The refactor now separates:

```text
main.py                 thin composition root
clinic_model.py         ClinicSession / TreatmentResult domain invariants
clinic_app.py           lifecycle + semantic input orchestration
clinic_renderer.py      prepared/cached presentation + bounded transient FX
clinic_art.py           stateless procedural drawing helpers
clinic_audio.py         prepared procedural SFX owner behind ClinicAudioPort
clinic_services.py      Greia storage/event adapters behind narrow ports
```

The calibration also found and intentionally repaired real contract/behavior drift hidden inside the monolith:

- `activity.toml` declared `vet.treatment_applied` / `vet.patient_healed`, while the old code emitted undeclared `clinic.patient_cured`; event publication now uses only the manifest-declared IDs;
- palette clicks could complete a later treatment out of order while patient taps enforced the next visible step; all input paths now delegate to one `ClinicSession.use_tool(...)` rule;
- the Activity declared Italian + English and carried localization bundles, but tool/victory UI remained hard-coded Italian; those visible labels now resolve through `LocalizedResources`.

Source-level performance structure now includes a pre-rendered opaque clinic backdrop, finite cached localized tool labels, current-value star text caching, a 96-particle explicit bound, one-time procedural SFX synthesis, and a victory modal that pays the full-screen alpha composition once then freezes to an opaque reusable frame. These are **SOURCE architecture improvements only**; no Acer/Pi speedup is claimed without measurement.

New provider-free tests are authored in `tests/test_clinica_cuccioli_refactor.py` for domain sequencing/session completion and manifest-to-event consistency. They have **not executed in this GitHub editing environment**. The durable review and exact simulator/local verification checklist are in:

```text
docs/reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md
```

The real refactor exposed reusable lessons, so the Activity skill now also contains:

```text
skills/greia-activity-authoring/REFACTORING.md
```

Structural refactors must inventory manifest/runtime/storage/event/localization/input/audio behavior before moving code, classify intentional changes as structural preservation / contract repair / behavior fix / performance structure, and normally extract pure domain truth before platform adapters, presentation ownership, application coordination and finally the thin composition root.

R7 remains the blocking platform phase; this parallel Activity-quality calibration does not change R7 status.

## Nascondino nel Bosco Activity refactoring & physical Acer performance calibration (2026-08-24)

`activities/nascondino_bosco` (Woodland Hide & Seek) had critical performance and visual composition defects on physical hardware:
- **Root cause 1 (performance)**: Re-rendered 15 SVG/PNG scene layers from scratch twice every frame at 30 Hz with software alpha blending (including 1024×512 sunlight rays and 1024×256 fog strips), resulting in physical Acer Atom execution at **505.35 ms/frame (2.0 fps)**.
- **Root cause 2 (visual composition)**: Hardcoded spot coordinates (such as a pine tree at `y=210` in the sky) and drew crude procedural shapes on top of the vector scene instead of grounding hiding spots to natural scene props.
- **Root cause 3 (architecture)**: 714-line monolith executing dynamic font rendering and per-frame fullscreen alpha blending on victory.

The refactor separated the Activity into clean, cohesive modules:
```text
main.py                 thin composition root + test compatibility exports (ANIMALS, SEASONS, WoodlandAudio, SPOTS)
woodland_model.py       AnimalDefinition / HidingSpotDefinition / WoodlandGameState domain invariants
woodland_app.py         lifecycle + semantic input + PygameCompletionScreen terminal victory integration
woodland_renderer.py    one-pass active game compositor + responsive HUD layout (normal/large/compact)
woodland_art.py         pre-rendered background baking + cached animal portraits + grounded clue animations
woodland_audio.py       synthesized PCM sound effects (rustle, pop, win)
```

**Measured physical Acer Aspire One results:**
- Pre-rendered background blit: **1.88 ms** (530 fps capability)
- Active frame render time: **505.35 ms → 9.05 ms** (**55× speedup**, locked at 30 fps with ~27% CPU margin)
- Test suite: `tests/test_activity_nascondino_bosco.py` (9/9 PASS); full suite **1,142 tests PASS**, 19/19 activities valid.
- **Simulator End-to-End Verification**: Tested via `greia_simulator.child_shell` and `greia_simulator_ctl.py` at 1024×600 in Italian:
  1. Selected profile Explorer → navigated Collection Home → opened `Esplora` → launched `Nascondino nel Bosco`.
  2. Verified active gameplay rendering: mascot on tree bough, target animal HUD ("SCOIATTOLO", "VOLPE"), 5 grounded spots with peeking animations, responsive star score increments upon discovering animals.
  3. Verified terminal victory: upon completing 4 animal searches, `PygameCompletionScreen` displays opaque victory frame ("TROVATI TUTTI!", "Tutti gli animaletti sono felici!", 4 gold celebration medals, and green "GIOCA ANCORA" button).
  4. Verified restart & exit: clicking "GIOCA ANCORA" (`primary_contains`) immediately starts a fresh round with new animal positions and accumulated star score; clicking protected Home button (`(36, 36)`) returns cleanly to the Launcher shell.
  5. Fixed `primary_action_rect` attribute error on `PygameCompletionScreen` by replacing it with canonical `primary_contains((mx, my))`.

## Parent Settings overlay tranche (2026-08-23, `3c3e91f`)

The chord-opened (hold S+T) on-device Parent Settings panel had two owner-reported defects, both fixed and verified on the reference Acer:

- **Password field dead**: SDL delivers `TEXTINPUT` only while text input is active, and parent-panel entry never activated it — typed characters vanished while Enter/Backspace still worked. Entry/exit now flows through `_enter_parent_panel`/`_exit_parent_panel`, which manage text input and clear stale input events at every transition site in both production and legacy run loops.
- **UI-thread stalls**: SSH status (two systemctl subprocesses + route probe per call) was invoked per-frame by the Info tab, blocked mid-draw every ~2 s on the SSH tab and was double-polled by `drain()`. Status refreshes now run on a worker thread into a queue drained exactly like Wi-Fi results; tabs render cached snapshots with honest placeholders; toggles cache their returned status; Audio mic-gain reads are throttled; the full-screen dim is composited once per picker-state change (`ParentSettingsOverlay.dim_surface()` + `draw_backdrop=False`) instead of alpha-blended every redraw.

Physical verification sequence: injected 5 s chord → auth dialog → typed dots visible → unlock → Language/SSH/Remote-and-Pairing tabs all render (device IP shown from cached status) → close restores the picker. Info/SSH tabs idle at **6–9 % launcher CPU** (previously subprocess-per-frame). Tests: `tests/test_parent_panel_input_lifecycle.py` (4 PASS).

## Achievement presentation, Activity victory contracts & progression simulator acceptance (2026-08-23)

The complete interactive acceptance protocol from `Greia_Achievement_Activity_Simulator_Acceptance_2026-08-23.md` was executed and **ACCEPTED** at the then-tested source state (`850bf6d` reported by the local-agent completion tranche).

Evidence captured in `./tmp/greia-achievement-simulator-acceptance/` includes:
- **Test A:** Empty Badge Library and collection routes (0/6 unlocked, 6 locked, secret `greia.stars.constellation` hidden).
- **Test B:** Clinica Cuccioli session: out-of-order treatment rejection, 5 patients healed, shared victory card, `First Friend Helped` celebratory popup, NEW/seen badge state, and verified `star=1` once-per-session award.
- **Test C:** Child shell restart persistence: badge and star balances preserved.
- **Test D:** Memory of Wonders completion: shared victory screen, `Memory in Action` badge, `star=2`, count 2/6.
- **Test E:** Costruiamo Ponti (3 levels in 1 session): `Bridge Builder` badge, `star=3` (strictly 1 star gained despite 3 level completions), count 3/6.
- **Test F:** Star milestone at 5 stars: `A Handful of Stars` unlocked, count 4/6, secret badge hidden.
- **Test G:** Profile isolation: second profile `BadgeTest2` starts with 0/6 badges and 0 stars; original profile restores 4/6 badges and 5 stars.
- **Test H:** Responsive smoke across 5 viewports (`1024x600 norm/large`, `1280x800`, `1366x768 compact`, `1920x1080`) plus Activity smoke checks.
- **Test I:** Static repaint sanity check: 0 frame repaints during 5s idle display.

Full Acceptance Ledger recorded in `tmp/greia-achievement-simulator-acceptance/results.md`.

## Achievement localization and Activity-themed art — post-acceptance source tranche (2026-08-24)

After the accepted simulator run, the owner identified that an Italian simulated Greia still opened the Badge Library with English Shell chrome. Root cause: the achievement presentation path could successfully read an empty installed-language store and receive its English default before consulting the simulator's explicit `GREIA_PROFILE_LOCALE` / `GREIA_DEVICE_LOCALE` context.

That presentation bug has been repaired through:

```text
src/greia_launcher/achievement_localization.py
src/greia_launcher/achievement_presentation.py
```

The achievement Shell now resolves explicit launch locale before installed-store fallback and owns localized Badge Library/celebration chrome for the current Greia language registry rather than using `if Italian else English` presentation branches.

The visual award renderer has also moved from one generic medallion shape to a coherent Greia family:

```text
bronze / silver -> medal + ribbons
gold            -> trophy cup
special/secret  -> rosette / constellation treatment
```

The owner then chose a layered Activity-art model: Activities may optionally contribute content-specific artwork while Greia retains global achievement authority.

Implemented contract:

```text
src/greia_platform/achievement_art.py
    bounded package-local Activity emblem declarations and validation

activities/*/activity.toml [achievement_art]
    optional decorative contribution only

runtime/achievement-policy.toml art = {...}
    explicit Greia admission of one Activity emblem into one platform achievement

src/greia_platform/achievements.py
    trusted policy admission; no Activity unlock authority

src/greia_platform/pygame_achievements.py
    Greia frame + admitted Activity emblem, with icon_id fail-soft fallback
```

V1 Activity emblems are static square PNGs, max 512 KiB, 32–1024 px, recommended 256×256, package-local, non-symlink and text-free. A SHA-256 content fingerprint participates in badge cache identity so updated artwork at the same package path invalidates prepared presentation cleanly.

Clinic, Memory and Bridges now opt in using their existing package icons as initial `activity` emblems, and the platform achievement policy explicitly admits those contributions for their Activity-specific badges. Greia-wide Star achievements remain platform-art-only. The infrastructure supports multiple purpose-made emblem IDs per Activity; future Activity authoring should generate dedicated content-specific emblems where they improve the result rather than treating launcher-icon reuse as the final art ceiling.

Authority remains:

> Activities report facts and may offer art. Greia decides rewards, achievements, tier/frame, localization, persistence, visibility and celebration.

Parent-installed content does not automatically add global badges merely by declaring artwork.

Durable contracts/review:

```text
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
docs/design/GREIA_ACHIEVEMENTS_AND_BADGE_LIBRARY.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/reviews/2026-08-24_ACTIVITY_THEMED_ACHIEVEMENT_ART.md
```

### Current source-test boundary

The earlier local-agent result remains:

```text
Ran 1110 tests in 20.284s
OK (0 failures, 0 errors)
```

That is retained evidence for the earlier accepted source state. **It is not automatically evidence for the newer localization / award-art / Activity-emblem commits.**

New provider-free tests have been authored in:

```text
tests/test_achievement_localization.py
tests/test_achievement_art.py
tests/test_achievement_emblem_cache.py
tests/test_pygame_achievements.py
```

They have not been executed in the GitHub editing environment. Current-head PASS requires local execution. No hosted GitHub Actions were queried or run.

---

# 2. Parent HTML client — runtime pin retained, microphone candidate ready for local repin

Greia still pins the previously tested external Parent client at:

```text
repository: frozenpepper/Greia-Parent-App-Html
revision:   7ff7e318eb246618dab26939ba086999864538ce
runtime:    /usr/share/greia-parent-app
state:      source-pinned-not-yet-vendored
```

Pin authorities:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

That integrity manifest contains the established 12 runtime files:

```text
index.html
styles/app.css
src/api.js
src/app.js
src/credential_store.js
src/demo_api.js
src/state.js
src/ui.js
src/views_helpers.js
src/views_home_children.js
src/views_activities.js
src/views_device.js
```

The Parent source repository now has a newer microphone-processing candidate at:

```text
cdea281a1848d1372a18822a559dc15494e749b0
```

It adds:

- `GET/PUT /settings/audio` and reset client methods;
- capability-gated audio state loading/refresh;
- a **Microphone cleanup** card;
- **Improve microphone sound** as the normal/default control;
- **Enhanced noise reduction** only when `available.advanced` is true;
- explicit UI text that Greia never auto-enables the advanced path;
- demo behavior and focused tests.

This newer revision is intentionally **not yet written into Greia's runtime pin** because its `npm test`, syntax checks and exact 12-file SHA-256 manifest regeneration still need to execute on a real local checkout. Do not bypass that integrity boundary.

Greia now includes:

```text
tools/update_parent_client_pin.py
```

Use it from a clean exact Parent checkout after tests to regenerate both the revision and the exact byte/SHA-256 manifest. The tool refuses dirty or revision-mismatched Parent checkouts.

The previously pinned Parent revision had been verified as:

```text
Parent npm test:                  28 / 28 PASS
changed JS syntax checks:         PASS
changed published Git blobs:      byte-identical to tested local copies
Greia manifest vs Parent runtime: 12 / 12 byte-count + SHA-256 PASS
Greia pin TOML parse/revision:     PASS
```

Those results apply to `7ff7e318...`, not automatically to `cdea281...`.

Manual desktop/mobile browser visual acceptance also remains required for the newer microphone UI.

## Parent product architecture

The rebuilt client has one state model and one product renderer around four parent jobs:

```text
Home
Children
Activities
This Greia
```

Implemented typed surfaces include:

- child profile create/edit/delete;
- child password set/replace/remove;
- optional approximate age;
- Automatic/Easier/Standard/Harder challenge preference;
- installed Activity inventory;
- per-child Activity visibility policy and individual Always show/Always hide overrides;
- Wi-Fi scan/connect;
- language;
- mouse/touchpad/display settings;
- microphone input gain when Greia exposes it;
- typed microphone-processing preferences in the newer source candidate;
- Parent password change;
- SSH maintenance enable/disable;
- paired-device list/revoke;
- system/update status and capability-gated delivery;
- Activity install only when the API advertises it.

The client remains API-first. It does not gain shell/filesystem/package-manager shortcuts.

---

# 3. Platform-owned microphone processing — PHYSICALLY ACCEPTED on the reference Acer (2026-08-24)

Architecture authority:

```text
docs/adr/0031-platform-owned-microphone-processing.md
docs/architecture/GREIA_AUDIO_SERVICE.md
```

Physical finalization protocol and acceptance evidence:

```text
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
docs/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md
```

## Product decision

The microphone-processing policy is now explicit:

```text
lightweight cleanup desired by default
advanced cleanup OFF by default
parent may disable all processing
parent may explicitly enable advanced only when a real endpoint exists
NO automatic benchmark/model/load-based processor selection
```

This is separate from the existing microphone input-gain setting.

## Source implementation

Implemented:

```text
src/greia_platform/audio.py
runtime/audio-settings.toml
src/greia_parent/protocol.py
src/greia_parent/update_api.py
src/greia_launcher/child_shell.py
src/greia_platform/activity_api.py
src/greia_platform/audio_alsa/        (greia_mic_light ExtPlug source)
runtime/alsa/                         (per-launch SDL ALSA composition)
build/overlay/etc/asound.conf
build/overlay/usr/local/lib/greia-os/greia-audio-endpoint-probe
build/overlay/etc/systemd/system/greia-audio-endpoints.service
build/package-sets/platform-shell-pygame.txt   (libspeexdsp1)
```

The typed `AudioService` owns desired state, backend availability, effective route and truthful fallback. The provisional ALSA adapter names stable logical endpoints:

```text
raw/default:   default
lightweight:   greia_mic_light
advanced:      greia_mic_advanced
```

Current route readiness is adapter-fed from current-boot markers under `/run/greia-audio/`; markers must never be created unless the corresponding endpoint really works.

An Activity granted `audio.basic` receives the resolved microphone route through its sanitized launch context. Python Activities obtain it through:

```python
from greia_platform.activity_api import get_audio_capture_device
from greia_platform.activity_api import get_sdl_capture_device
```

`get_sdl_capture_device()` designates the SDL-enumerated capture device that carries the route (SDL 2.26 cannot open arbitrary ALSA PCM names; the launcher injects the composed ALSA view for non-off modes). Activities must not enumerate physical microphones and choose the first host device.

Focused source tests cover the default/no-auto-promotion policy, explicit advanced opt-in, unavailable-backend handling, processing-off route, Activity environment projection, the SDL designation and Parent API settings semantics (31 focused tests PASS at `2972127`).

## Physical acceptance state (2026-08-24, Acer Aspire One)

The lightweight route is implemented and physically accepted on the reference Acer:

- `greia_mic_light` = in-process ALSA ExtPlug: FIR decimation 48k→24k,
  SpeexDSP preprocessor denoise (−15 dB, AGC off), FIR interpolation back,
  primed delay-line FIFO. On-demand only; no daemon; zero idle cost.
- Boot probe service creates `/run/greia-audio/lightweight-ready` only after
  a real one-second capture; verified recreated automatically after reboot.
- Live route proof: during a real launcher-launched Teatrino recording the
  capture hardware ran at 48000 Hz (route contract) owned by the Teatrino pid.
- Measured: −19.9 dB stationary noise-floor reduction, voice band preserved
  (stimulus A/B within ~1.5 dB), zero glitches, ~5–10% of one core, +0.4 MB
  RSS during capture. Owner A/B verdict: routed clearly better.
- Parent controls verified against the device API: default (lightweight),
  off (raw, no ALSA injection), restore, and reboot persistence.
- Negative check: an Activity without `audio.basic` (painting) receives zero
  audio-route environment variables.
- Advanced endpoint intentionally NOT INSTALLED (`available.advanced = false`).
- Device tuning notes: ALSA Capture level was found maxed (+31.5 dB) causing
  hard clipping; set to +3 dB on this device. Parent `mic_gain` raised
  2.0 → 3.0 on this device for post-denoise loudness (Parent-adjustable).

Open follow-up: image-build integration must compile
`src/greia_platform/audio_alsa/` into future i686 images. Images without the
plugin honestly fall back to raw with `lightweight_unavailable`.

## Existing microphone gain retained

Current hardware gain contract remains:

```text
desired.mic_gain
minimum: 0.5× / 50%
default: 2.0× / 200%
maximum: 4.0× / 400%
```

It remains in `HardwareSettingsStore` for compatibility. Do not conflate it with denoising mode or silently move gain/AGC ownership without measured migration of existing consumers.

---

# 4. Child Activity discovery — implementation is active, not future-only

Authorities:

```text
docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md
docs/design/GREIA_LAUNCHER_INTERACTION_AND_ACTIVITY_CATALOGUE.md
src/greia_platform/activity_discovery.py
src/greia_launcher/catalogue_view.py
```

Normal child flow remains:

```text
profile
  → Greia Home
    → primary Collection
      → optional sub-Collection
        → Activity
```

Platform-owned primary vocabulary:

```text
create
play
learn
explore
my_greia
```

Valid Activities with no recognized primary destination fail open through bounded `browse` / More recovery. Arbitrary package category strings do not manufacture Home destinations. One Activity may appear in multiple Collections without duplicating installation/state/progression.

## Implemented audience metadata

`ActivityManifest` now owns:

```text
difficulty                 1..10 baseline
recommended_age_min        optional 1..18
recommended_age_max        optional 1..18
difficulty_min             optional 1..10
difficulty_max             optional 1..10
adaptive_difficulty        boolean
presentation.discovery_tags
```

Adaptive-difficulty ranges must be declared as a valid min/max pair and require `adaptive_difficulty = true`.

`ChildProfile` now owns:

```text
approximate_age            optional 1..18
challenge_preference       automatic/easier/standard/harder
```

No date of birth is required.

## Implemented Parent policy

`ActivityDiscoveryPolicy` owns:

```text
visibility_mode:
  show_all
  hide_too_simple
  recommended_only
  custom

overrides:
  always_show
  always_hide
```

Explicit Parent override wins before automatic recommendation. Missing age/audience metadata fails open for ordinary discovery.

`ActivityDiscoveryService` computes the effective visible/ranked set without changing package authority, saves or permissions.

## Implemented adaptive depth

`AdaptiveCollectionPlanner` currently uses:

```text
enter threshold:    > 10 triggers subdivision evaluation
collapse threshold: <= 8 returns direct Activities
9–10:               retained subdivision only when previously validly subdivided
semantic groups:    2–5, platform-owned vocabulary, >=2 Activities/group
maximum depth:      Home → primary → optional sub-Collection → Activity
```

Bad/incomplete semantic partitions remain direct rather than manufacturing a meaningless Other bucket.

The policy store carries bounded `subdivided_collections` hysteresis state separately from Parent visibility intent.

Collection-first, bounded-primary-vocabulary and adaptive-catalogue simulator acceptance is already recorded in repository testing documentation. Do **not** return to the old All/filter Home model.

---

# 5. Parent/security boundary still open

The current LAN Parent transport remains provisional HTTP/bootstrap pairing.

Implemented foundations include per-device bearer credentials and individual revocation, but production acceptance still requires:

- short-lived Greia-owned pairing challenge;
- local device Allow/Deny confirmation;
- authenticated encrypted transport;
- device binding plus expiry/replay protections.

Ordinary/release capability advertisement must remain honest. In particular, source presence does not authorize package/system mutation over an insecure transport.

The external Parent client remains a source-pinned integrity-checked build input; it is **not yet vendored/composed into the release image as a closed packaging tranche**.

---

# 6. Device language / localization

Authorities:

```text
docs/adr/0028-platform-and-activity-localization-language-context.md
docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md
```

Effective language is selected at install, persisted, and may later be overridden by `SystemLanguageStore`. English remains default; current canonical selectable registry includes:

```text
en, it, es, de, fr, zh-CN, pt, ar, hi, id, bn, sw
```

`zh` canonicalizes to `zh-CN`. Installer, on-device Parent panel and external Parent client consume the Greia-owned registry.

Selectable does not imply complete translations, shaping/font coverage or RTL acceptance.

---

# 7. Transactional Greia system updates

Authorities:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Signed `.greiaupdate` source/trust/inbox/tooling foundations exist.

Current x86 profile remains `bios-single-ext4` with:

```text
system.update.activate = false
```

A/B inactive-slot activation, boot-health confirmation and automatic rollback are not accepted on the current production layout. No in-place active-root fallback is authorized for convenience.

---

# 8. R7 remains the blocking architecture phase

Current production remains provisional Xorg/xinit compatibility behavior while direct appliance display/session/input is resolved.

Mandatory architecture remains:

- Greia-owned display/session authority;
- protected platform Home/Back above Activity content;
- protected-system input intercepted before Activity delivery;
- controller ownership/normalization platform-owned;
- ordinary Activities do not gain raw `/dev/input` or DRM authority.

Recent launcher performance work, achievement presentation/art work and microphone service are useful platform work but are **not** R7 display/session closure.

---

# 9. Boot / installer / physical facts retained

- Reference Acer Aspire One is BIOS-only.
- Proven live USB path is syslinux/FAT32.
- Canonical USB creator: `tools/build-live-usb.sh`.
- Installed initramfs must be target-kernel/target-hardware aware; build-host/chroot hardware is not target authority.
- Developer/test SSH remains owner-approved `greia / greia`, root SSH denied; normal/release remains fail-closed.
- Physical evidence applies only to the exact source/image/tranche measured and must not be generalized to later source.

Canonical hardware history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
```

---

# 10. Visual/art continuation

Stable/current authorities:

```text
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_GENERIC_ART_LIBRARY_TAXONOMY.md
docs/design/GREIA_ACTIVITY_ACHIEVEMENT_ART.md
skills/greia-visual-authoring/SKILL.md
skills/greia-activity-authoring/ACHIEVEMENTS.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
```

Theme/source bundles remain provenance pools; the generic semantic authoring library is the primary authoring interface. Generic authoring tooling stays development-time and does not become a second runtime catalogue.

For global achievements, Activity-generated art is now a supported **decorative contribution**: Greia owns award frames and achievement authority, while explicitly admitted Activity emblems may supply the center artwork. Purpose-made Activity emblem generation should remain inside the Activity's own art/source workflow and obey the bounded PNG contract.

Do not infer arbitrary Activity-authoring-agent drawing capability from the owner's stronger maintainer-side agent.

---

# 11. Next exact steps

## Immediate achievement-art verification

1. Record current `main` SHA before testing.
2. Run:
   ```bash
   PYTHONPATH=src python3 -m unittest \
     tests.test_achievement_art \
     tests.test_achievement_emblem_cache \
     tests.test_achievements \
     tests.test_pygame_achievements \
     tests.test_achievement_localization \
     tests.test_activity_contract \
     -v
   ```
3. Run the checkout's normal complete local unit/validation gate; preserve the first real failure rather than repairing around it during acceptance.
4. In the Activity Simulator, do only the focused visual recheck documented in `docs/reviews/2026-08-24_ACTIVITY_THEMED_ACHIEVEMENT_ART.md`: Italian Badge Library localization, unlocked Clinic/Memory/Bridge Activity-derived centers inside Greia frames, locked-art non-disclosure, Greia-wide Star badge remaining platform art, and idle repaint sanity.
5. Treat this as simulator/developer evidence only; no Acer performance claim follows without hardware measurement.

## Blocking engineering

1. Resolve current `main` before each new implementation tranche.
2. Read `skills/greia-os-work/SKILL.md` for substantive OS/platform work and the Activity skill's `ENGINEERING.md` for substantive Activity implementation; structural Activity refactors additionally require `REFACTORING.md`. Keep the derived skills synchronized when their governed contracts change.
3. Owner disposition: reconcile the four stale boot-contract tests (`panic=30`) with the accepted postmortem/source direction (`panic=5`).
4. Re-run the current aggregate verification only after that disposition; preserve genuine failures.
5. Continue R7 from its first incomplete blocking gate; do not treat launcher performance optimization, microphone processing, achievements or the Activity calibration as display/session closure.
6. Preserve the current Acer performance measurements in the engineering performance manual as future UI/render work is added.

## Clinica Cuccioli calibration verification

1. Run `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_clinica_cuccioli_refactor.py' -v` in a real checkout.
2. Run `make verify`; preserve the known aggregate baseline failures separately from any new regression.
3. Load `activities/clinica_cuccioli` in the real Activity Simulator and execute the Italian/English, sequence-consistency, five-patient, Play Again/persistence, resize and protected-Home checks in `docs/reviews/2026-08-23_CLINICA_CUCCIOLI_ARCHITECTURE_CALIBRATION.md`.
4. Only after simulator/source verification, compare the same Activity on the reference Acer if a performance claim is desired.
5. Do not yet extract the Clinic app-loop/particle/progress/render helpers into `greia_platform`; inspect at least one or two more Activities first and extract only genuinely shared semantics.

## Microphone physical finalization

1. Follow `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md` exactly on the owner-controlled Acer lane.
2. Run the new focused Greia source tests before touching hardware.
3. Implement/prove `greia_mic_light` with the smallest real denoiser that materially helps the Acer signal; prefer on-demand SpeexDSP evaluation before heavyweight architecture.
4. Migrate remaining first-party microphone consumers away from host-device enumeration to `get_audio_capture_device()`.
5. Measure raw vs lightweight CPU/RSS/quality/dropouts; leave readiness absent on failure.
6. Evaluate advanced processing only after lightweight is stable; it is acceptable for Acer to report `advanced = false`.
7. Update this handover with exact PHYSICAL evidence only after it exists.

## Parent

1. In a clean owner-controlled `Greia-Parent-App-Html` checkout at `cdea281a1848d1372a18822a559dc15494e749b0`, run `npm test` and JS syntax checks, then visually exercise desktop + mobile/narrow layouts including the new microphone card.
2. If that revision passes, run `tools/update_parent_client_pin.py --parent-root <clean-parent-checkout> --revision cdea281a1848d1372a18822a559dc15494e749b0` from Greia and validate the regenerated exact 12-file integrity manifest.
3. Commit the Greia repin as a distinct coherent commit; do not runtime-fetch moving Parent `main`.
4. Decide/implement the separate vendoring/release-image composition tranche later.
5. Continue production pairing/encrypted-transport work before enabling ordinary release mutation capabilities.

## Child discovery

1. Treat adaptive Collection depth, profile age/challenge and Parent visibility as **implemented foundations**.
2. Calibrate metadata/group vocabulary/thresholds through evidence rather than adding hierarchy depth.
3. Keep missing metadata fail-open and Parent overrides authoritative.
4. Keep education taxonomy separate from navigation taxonomy.

---

# 12. Non-negotiable continuation rules

- `main` only unless owner changes policy;
- GitHub is canonical persistence;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- substantive OS/platform work consumes `skills/greia-os-work/SKILL.md`;
- substantive Activity implementation consumes `skills/greia-activity-authoring/ENGINEERING.md` through the Activity skill;
- structural Activity refactors additionally consume `skills/greia-activity-authoring/REFACTORING.md` and inventory declaration/behavior contracts before moving code;
- Activity `main.py` is a composition/bootstrap boundary rather than a monolithic application implementation;
- multiple input paths for one semantic child action delegate to one domain rule rather than duplicating correctness/scoring policy;
- Activities may offer bounded language-neutral achievement emblems, but global achievement IDs/criteria/tier/frame/localization/state/rewards remain Greia-owned and require explicit platform-policy admission;
- parent-installed Activity emblem declarations never auto-create global Badge Library entries;
- no visible Linux shell/desktop in normal child path;
- R7 remains open and Xorg/xinit provisional;
- protected Home/Back stays outside Activity authority;
- controller/input/device authority stays platform-owned;
- microphone capture routing is platform-owned for Activities with `audio.basic`;
- lightweight microphone cleanup is desired default; advanced is explicit Parent opt-in only;
- no automatic microphone processor selection/benchmark promotion;
- no readiness marker without a real working endpoint;
- one canonical device-language registry;
- selectable language is not translation/font/RTL completion;
- system-update activation stays false on current single-root profiles;
- Parent HTTP/bootstrap transport remains provisional;
- external Parent JS is pinned/integrity-checked, never fetched from moving `main` at runtime;
- Collection-first Home is accepted; old All/filter root is not normal child IA;
- root and sub-Collection vocabularies are platform-owned;
- effective catalogue is per child after Parent policy;
- age and difficulty remain separate dimensions;
- missing audience metadata fails open;
- explicit Parent Activity overrides win over automatic recommendation;
- adaptive discovery never exceeds one sub-Collection layer;
- Collections are semantic child groupings, never filesystem folders;
- visual/runtime/Activity caches remain bounded with explicit invalidation and avoid per-frame decode/scale/IO;
- performance claims require measurement on the claimed execution scope.

**Resume the blocking platform path from R7 in `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`. In parallel, verify the post-acceptance achievement localization/Activity-art tranche through its focused source + simulator checks before calling current head green; the microphone tranche may be physically finalized only through its dedicated Acer protocol. Do not report source architecture as hardware acceptance.**