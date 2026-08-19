# Greia — Standalone Engineering Handover

**Date:** 2026-08-19  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting source tranches after the last full executed gate:** **Activity Simulator hardening + platform Unicode/color-emoji/Writing support**  
**External Parent HTML revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@e30bcbcab393354b8ffb63d5829c08711d8023bd`

This handover owns the **current continuation/evidence boundary**. Historical implementation detail belongs in the append-only active plan and dated reviews. Exact APIs and limits remain source-owned.

---

## 1. Repository and execution rules

The owner requires a **single-branch workflow**. `main` is the only development/integration branch unless the owner explicitly changes that policy. Commit coherent work directly to `main`; GitHub is canonical project persistence.

Do **not** use, query, trigger, rerun, inspect or download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution. Verification is performed in an owner-controlled environment.

Never convert committed tests into a PASS claim merely because test files exist.

The active implementation plan remains:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

R7 remains the first incomplete blocking architecture phase. Cross-cutting source/product work must not be reinterpreted as closing or skipping R7.

---

## 2. Current evidence boundary

The latest genuinely executed complete owner-controlled source gate recorded before the later simulator/emoji tranches is the 2026-08-18 early-boot run:

```text
boot/profile/installer focused set: 108 PASS
boot-experience contract suite:       16 PASS
make verify:                         706 PASS
```

That evidence applies to its exact pre-simulator/pre-emoji source boundary. It does **not** prove later source.

The following later work is committed but lacks a fresh owner-controlled complete source PASS at current head:

- the 2026-08-19 Greia Activity Simulator implementation/adversarial hardening;
- the 2026-08-19 Unicode grapheme/color-emoji typography implementation;
- the current Writing Activity grapheme-editing migration and emoji picker;
- the new emoji/picker focused regression tests;
- documentation/plan/handover synchronization after those source changes.

On the 2026-08-19 owner-controlled checkout, the complete `make verify` still fails on **import-time errors in the owner's in-progress emoji and simulator modules** (`emoji_palette` raises for a `⭐` grapheme on this Python/Unicode build; the simulator test imports classes that do not exist in `src/greia_simulator/runtime.py`). These are unrelated to the boot/installer/SSH work in this handover's §6/§7 and are the owner's active simulator/emoji tranches. The boot/SSH/installer focused suites pass (see §6).

**Real-hardware success (2026-08-19):** a fresh `legacy-x86-i686-dev` installer and its installed OS **booted and ran on the reference Acer Aspire One** using the syslinux/FAT32 live-USB path described in §6. The installer completed and the installed OS reached the launcher. This is the first Acer physical PASS recorded for the current source lineage.

No current-head QEMU acceptance or current-head Pi acceptance is claimed here.

---

# 3. 2026-08-19 — Platform Unicode, color emoji and Writing

## 3.1 Product/architecture decision

Emoji support is now a **Greia platform typography/text capability**, not something each Activity is expected to solve independently.

The selected/current Python/Pygame stack is:

```text
ordinary Greia text
        ↓
Nunito Sans semantic role

emoji grapheme cluster
        ↓
Noto Color Emoji
        ↓
Pillow embedded-color rasterization
        ↓
RGBA Pygame surface
```

Important invariants:

- **Nunito Sans remains Greia's normal interface family**;
- Noto Color Emoji is a fallback, not a replacement system font;
- emoji are expressive text/content, not substitutes for Greia Home/Back/settings/audio/trust/recovery icons;
- authoritative text remains standard Unicode/UTF-8;
- child-visible editing units are Unicode **extended grapheme clusters**, not individual Python codepoints;
- Activities do not crawl `/usr/share/fonts`, implement private fallback stacks, maintain private emoji-range/ZWJ parsers, or persist proprietary emoji tokens;
- platform resource/cache bounds remain mandatory on the Acer/C0 floor.

Design/product/authoring authority:

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
skills/greia-activity-authoring/SKILL.md
```

## 3.2 Source implementation

Current shared source:

```text
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
```

`GreiaTypography` now provides:

- existing semantic Nunito roles (`body`, `secondary`, `control`, `title`, `display`);
- mixed ordinary-text + color-emoji rendering;
- measurement using the same fallback decisions as rendering;
- prefix width for caret/hit-test logic;
- a hard-bounded normal font cache;
- a hard-bounded **256-entry emoji surface cache**;
- lazy Noto Color Emoji loading;
- Pillow embedded-color rendering hidden behind the platform abstraction;
- text/emoji variation-selector handling (`VS15` vs `VS16`);
- child-safe degradation if the declared fallback font is present-but-corrupt/incompatible, without treating that degradation as a release-support PASS.

The current Debian/bookworm Noto package exposes a color-bitmap native strike; that renderer-specific detail is deliberately kept inside `GreiaTypography`. Future SDL3/Web implementations may replace the backend without changing Activity-visible Unicode semantics.

### Grapheme contract

`src/greia_platform/typography.py` now exposes:

```text
grapheme_spans
grapheme_boundaries
previous_grapheme_boundary
next_grapheme_boundary
snap_grapheme_boundary
truncate_grapheme_safe
is_emoji_cluster
```

Installed Python/Pygame images now explicitly carry `python3-regex`; shipping segmentation uses Unicode `\X`. A small stdlib fallback exists only to keep development-host imports functional if that dependency is missing and is not the shipping segmentation authority.

## 3.3 Image/runtime composition

Both current Python/Pygame package sets now include the emoji/grapheme dependencies:

```text
build/package-sets/platform-shell-pygame.txt
build/package-sets/runtime-python.txt
```

Required additions:

```text
fonts-noto-color-emoji
python3-regex
```

Pillow and Pygame were already part of the current runtime family.

This adds a meaningful installed-size cost, especially from the emoji font. The package change is source-declared but **C0 installed-footprint acceptance is still pending**.

## 3.4 Shared curated emoji palette

`src/greia_platform/emoji_palette.py` adds a bounded renderer-neutral model:

```text
EmojiCategory
EmojiPalette
DEFAULT_EMOJI_CATEGORIES
```

Current default palette:

```text
7 semantic categories
18 common emoji per category
maximum contract: 12 categories / 24 emoji per category
```

The palette is intentionally much smaller than the complete Unicode emoji catalogue. It is a **child-friendly picker model**, not the rendering limit. Valid emoji arriving from normal input/restored UTF-8 documents can still render through the typography fallback when supported by the installed emoji font.

## 3.5 Writing Activity migration

Current first-party consumer:

```text
activities/writing/main.py
```

Writing now uses Greia typography instead of raw default Pygame fonts for editor/gallery text and adds grapheme-safe behavior for:

- Left/Right cursor movement;
- Backspace;
- Delete;
- undo cursor restoration;
- soft wrapping;
- click hit testing;
- Up/Down visual-column movement;
- caret x-position;
- previews;
- maximum-document truncation.

This prevents sequences such as the following from being torn apart:

```text
👍🏽
👩‍🔬
🏳️‍🌈
🇮🇹
1️⃣
❤️
```

Documents remain ordinary UTF-8 under the existing Greia Storage path. No emoji image filenames/glyph IDs/private tokens are persisted.

### Writing emoji picker

Writing now includes a large visual emoji button and picker:

- uses the shared `EmojiPalette` model;
- seven categories / eighteen common emoji per category;
- inserts the selected Unicode grapheme through normal `TextBuffer.insert()`;
- Escape closes the picker before exiting the Activity;
- switching document/gallery/new state closes the picker;
- category/grid layout derives from the actual Greia-safe editor rectangle;
- grid columns/rows and cell size reflow from available viewport space rather than assuming 1024×600;
- no essential picker geometry is intentionally placed inside platform-owned Home/Back chrome.

This is the **initial reference implementation**, not yet a universal platform picker renderer automatically attached to every Greia text field or future Web runtime.

Touch/controller picker navigation is not claimed complete by this tranche.

## 3.6 Focused regression source

New tests:

```text
tests/test_typography_emoji.py
tests/test_writing_emoji_editing.py
```

They cover, in source:

- ZWJ/skin-tone/flag/keycap/combining grapheme segmentation;
- valid cursor boundaries;
- grapheme-safe truncation;
- default emoji-presentation classification;
- `VS15` text presentation versus `VS16` emoji presentation;
- curated palette bounds and semantic selection;
- declared Python/Pygame package dependencies;
- missing-font capability degradation;
- Writing whole-cluster Backspace/Delete;
- whole-cluster horizontal movement;
- undo restoring an entire emoji cluster;
- preview/document bounds not retaining partial clusters.

**These tests have not executed in an owner-controlled current checkout at this head. No PASS is claimed.**

## 3.7 Required emoji verification next

Run, on the owner-controlled Linux checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_typography_emoji \
  tests.test_writing_emoji_editing -v
```

Then run the relevant existing Writing/UI tests and Activity validation, followed by:

```bash
make verify
```

Preserve the first real failure. Do not weaken grapheme/emoji tests merely to obtain a green gate.

Only after source PASS should the image be rebuilt for installed acceptance.

Installed/visual evidence must include at least:

```text
🙂 🚀 🦄
❤️ ☀️
👍🏽 👋🏻
👩‍🔬 👨‍🚀 🏳️‍🌈
🇮🇹 🇫🇷 🇯🇵
1️⃣ 5️⃣ #️⃣
```

and mixed Nunito+emoji text.

Required checks:

- no tofu/missing-glyph boxes for the accepted specimen;
- actual color rendering where expected;
- whole-cluster cursor movement/deletion;
- correct wrapping and click placement around emoji;
- picker fit/readability at **800×600 and 1024×600**;
- save → exit → relaunch preservation;
- installed font/package presence;
- installed-size delta;
- first-emoji render latency;
- cached-emoji render latency;
- RSS/CPU impact;
- bounded cache growth;
- physical Acer/C0 usability.

---

# 4. Greia Activity Simulator — current source state

Normative/developer docs:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_ADVERSARIAL_REVIEW.md
docs/reviews/2026-08-19_ACTIVITY_SIMULATOR_HARDENING_RESPONSE.md
```

Relevant historical source boundaries recorded before the emoji tranche:

```text
initial/adversarial simulator source boundary: b4cda82ca18996ad67859976292f0457315052d4
hardening source/docs boundary:               f1e2ffdb7eaacdb9f6bd938fd917f731f0ef92e3
```

The simulator is deliberately a thin developer surface over the real Greia platform, not a second runtime/platform implementation. It injects synthetic HAL/viewport/capability facts through canonical seams while reusing real registry/trust/runtime/storage/history/lifecycle/profile services.

Current hardening regressions and manual Mac acceptance remain **unexecuted at the hardened/current head**. Do not claim simulator PASS from committed source.

Required focused command remains:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

After current source PASS, manual acceptance is defined by:

```text
docs/testing/2026-08-19_ACTIVITY_SIMULATOR_ACCEPTANCE.md
```

Simulator evidence never substitutes for R7 display/session/input or physical hardware evidence.

---

# 5. Current R7 / display / input state

R7 remains the primary blocking architecture phase.

Current production/display state:

- production Activity/display path remains **provisional Xorg/xinit**;
- no compositor is selected;
- serial direct DRM ownership remains an evidence candidate, not production architecture;
- `DisplaySessionCoordinator` is the backend-neutral lifecycle seam;
- installed legacy-X backend remains the compatibility implementation;
- ADR 0019 trusted Home/Back remains a mandatory production authority requirement;
- ADR 0020 runtime-neutral input/controller semantics remain mandatory;
- ADR 0025 additionally requires a bounded Greia-owned Award/celebration presentation path or safe Greia-controlled deferred equivalent without weakening Home/Back;
- ordinary Activities must not obtain raw display/input authority merely to make the backend convenient.

Open R7 evidence still includes:

- exact current source gate;
- exact current production-image build;
- installed SDL/backend classification;
- compositor package/resource comparisons where still relevant;
- active/serial QEMU evidence where applicable;
- active seat/input evidence;
- compositor/serial/Xorg authority/resource comparison;
- direct-profile sandbox authority migration only after architecture selection;
- physical legacy Intel/Acer scanout/input/suspend/crash acceptance;
- trusted system-chrome non-coverability and protected input;
- controller reconnect/dead-zone/virtual-pointer/system-input evidence.

Do not deepen X11 merely because current production still uses it, and do not select a compositor simply to satisfy emoji/overlay/picker UI. Emoji rendering is an Activity/UI concern above the R7 transport seam.

---

# 6. Boot / installer / real-hardware state

## 6.1 Current early-boot source architecture

Plymouth is **not** the target Greia boot architecture (migration debt). The current source path uses:

- Greia-owned early framebuffer splash (`build/early-boot/greia-fb-splash.c`);
- canonical white logo/frame lineage under `assets/boot/` (source + static PNG + P6 PPM for target and installer overlays), generated by `tools/generate_boot_artwork.py`;
- target-built initramfs framebuffer renderer (compiled inside the target root with `klcc` + `gcc`, architecture-verified, `libklibc-dev`/`gcc` purged before manifest capture);
- GRUB white-frame continuity (`background_image` in `10_greia_appliance`);
- Shell-owned short intro animation (`src/greia_launcher/boot_intro.py`, one-shot per boot, <=1.0 s) and one-shot PCM boot chime (`src/greia_launcher/boot_chime.py`);
- no Python/SDL/audio dependency inside initramfs;
- consoleless kernel/initramfs policy for normal builds; **developer/test builds keep the boot observable** (`console=tty1 panic=30`).

## 6.2 The real-hardware Acer boot requirement (critical — read this)

The reference Acer Aspire One (2010-era, Intel Atom N270, BIOS-only, no UEFI) **does not reliably execute GRUB's MBR from a USB stick**, and its BIOS will not boot its SD readers at all. The proven USB path is the **antiX-style syslinux/FAT32** live media:

- one active FAT32 partition;
- live files at the partition root (`vmlinuz`, `initrd.img`, `filesystem.squashfs`);
- the installable payload under `payload/` and the live-media identity marker at `.disk/live-uuid`;
- syslinux VBR on the partition (`syslinux --install`) + `mbr.bin` MBR on the device;
- a `syslinux.cfg` that boots straight to the installer (no interactive menu, `TIMEOUT 0`).

This is captured in `tools/build-live-usb.sh` (the reproducible builder) and `build/live-syslinux/syslinux.cfg.in`. The full reasoning and every dead end ruled out are in `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md`.

**WHY it is this way:** the Acer firmware executes simple MBR/VBR loaders (syslinux) but not the more elaborate GRUB stage-1 disk reads on this stick. This is a firmware/media-adapter interaction, not a GRUB defect; the internal disk's GRUB works fine. Do not "fix" this by reverting to GRUB-on-USB for this class of machine.

## 6.3 Installed-OS boot: the regenerated-initramfs trap

A freshly installed OS grey-screens + reboots when the **regenerated** initramfs (built by `update-initramfs` in the target chroot during install) drops the boot-critical storage drivers. The payload-shipped initramfs can look fine while the regenerated one is broken, because `MODULES=dep` in an unrelated chroot has no Acer SATA controller.

**WHY it is fixed in source:** the installed target carries `MODULES=most` (`/etc/initramfs-tools/conf.d/greia-hardware`) plus an executable `greia-storage-modules` hook that runs `modinfo -k "$version"` against the **target kernel** and `manual_add_modules` only when that kernel provides `ahci`/`libata`/`sd_mod`. Never let build-host/chroot hardware decide target boot-critical drivers, and never hardcode x86 module names into a shared cross-architecture overlay. Full narrative in `docs/INSTALLED_OS_BOOT_POSTMORTEM.md`.

## 6.4 Developer/test SSH is now built into the canonical builders

Previously, `greia/greia` SSH depended on running `provision_developer_*` manually after a build — a step that could be missed (a flashed installer shipped with SSH off). **Now** `build-image.sh` and `build-installer-image.sh` detect the `developer-remote` package set in the profile and, for dev profiles:

- create/unlock the `greia` account and set the `greia` password (`chpasswd`, then `passwd -u`);
- rewrite **both** `sshd_config.d` drop-ins (`00-greia-security-floor.conf` and `20-greia-parent.conf`) to `AllowUsers greia` with `PasswordAuthentication yes` / `AuthenticationMethods publickey,password`, `DenyUsers root` — so no later-sorted file re-introduces publickey-only and defeats the password login;
- enable `ssh.service`;
- write `/etc/greia-os/developer-remote` (which also flips the installed boot to observable `console=tty1 panic=30`).

Normal/release profiles stay fail-closed (SSH off, greia locked). Root SSH is always disabled.

**WHY:** the owner policy requires developer/test installs and the live installer to stay reachable as `greia / greia` during active hardware bring-up, and it must be reproducible — not dependent on a manual step that can be forgotten. A real defect where the `20-greia-parent.conf` base config (publickey-only) defeated the dev floor and left password SSH rejected was found and fixed; a regression locks that both drop-ins stay consistent.

## 6.5 Splash logo rendering

Two distinct splash defects were found and fixed:

1. **Color glitch ("one color rendered, broken"):** caused by a **noisy logo extraction** from the legacy animation frame (a crude brightness threshold over-captured the navy gradient). The renderer's `pack_pixel` was verified correct for RGB565/24/32-bit framebuffers. Fixed with a luminance floor + median filter in `tools/generate_boot_artwork.py` and an indigo logo color `(62,70,130)` that survives RGB565.
2. **Geometry glitch ("full-screen-width, clipped vertically"):** the installed-OS splash could render the logo oversized/clipped when the initramfs framebuffer reported odd/degenerate geometry. Fixed in `build/early-boot/greia-fb-splash.c` to always preserve aspect ratio, cap to a margin fraction of the visible area, and guard every division against zero/oversized dimensions.

Regressions in `tests/test_boot_experience_contract.py` lock both the logo-color/white-frame contract and the geometry invariant.

## 6.6 State / evidence

- On 2026-08-19, a fresh `legacy-x86-i686-dev` syslinux/FAT32 installer **and** its installed OS **booted on the Acer** (installer completed; installed OS reached the launcher). This is the first recorded Acer physical PASS for the current lineage.
- The boot/SSH/installer focused suites pass on the owner-controlled checkout; the full `make verify` is blocked only by the owner's in-progress emoji/simulator import errors (§2).
- The splash color+geometry and SSH-consistency fixes are committed after the last physical build; **rebuild from current `main` before further physical acceptance** so these fixes reach the medium and installed system.

## 6.7 How to rebuild the installer image (exact steps)

The current Acer installer/test path is fully reproducible from `main`:

```bash
# 1. Ensure the checked-out tree is current main.
cd <greia-checkout>
git checkout main && git pull --ff-only origin main

# 2. Build the installer image (target + live installer + payload).
#    <profile> = legacy-x86-i686-dev for the developer/test image with SSH.
mkdir -p /path/to/out
sudo bash build/build-installer-image.sh legacy-x86-i686-dev /path/to/out

# 3. Make the Acer-bootable syslinux/FAT32 USB from that image.
#    <device> = the WHOLE removable USB disk (e.g. /dev/sdd). DESTRUCTIVE.
sudo bash tools/build-live-usb.sh \
  /path/to/out/greia-os-installer-legacy-x86-i686-dev.img \
  /dev/sdd

# 4. (Optional) regenerate boot artwork if the source logo frame changed.
python3 tools/generate_boot_artwork.py

# 5. Focused boot/SSH/installer gate before flashing.
PYTHONPATH=src python3 -m unittest \
  tests.test_boot_experience_contract \
  tests.test_boot_contract \
  tests.test_boot_animation_contract \
  tests.test_installation_hardware_regressions \
  tests.test_installer_engine \
  tests.test_launcher_presentation -v
```

**Critical things to remember:**

- **Do not boot a GRUB-MBR USB on the Acer** — use `tools/build-live-usb.sh` (syslinux/FAT32). See §6.2.
- **Verify the media id is consistent** before booting: `.disk/live-uuid` == `syslinux.cfg` `greia.live_media_id` == initramfs `conf/uuid.conf`. `tools/build-live-usb.sh` derives all three from the image.
- **SSH is `greia / greia`** on the live installer and the installed dev OS; root SSH is denied.
- **The installed boot is observable** (`console=tty1 panic=30`) for dev images, so a kernel panic prints instead of silently rebooting.
- The full `make verify` currently needs the owner's in-progress emoji/simulator import fixes before it passes end-to-end; the boot scope above is independent and green.

Canonical hardware/install history:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

Hardware fixes remain integrated only when:

```text
physical failure resolved
+ authoritative build source corrected
+ hardware-independent regression added
+ living documentation explains root cause
```

A manual repair on one Acer is diagnostic evidence, not repository closure.

---

# 7. Parent credentials / SSH / Parent API

Active owner credential direction:

```text
initial Parent/admin username: greia
initial Parent/admin password: greia
```

There is no required generated random end-install recovery password.

Current policy/source direction:

- main Parent password is Greia-owned, stored as a bounded digest and changeable through typed Parent operations;
- optional child-profile passwords remain Greia-profile credentials, not Linux users;
- development/test installs may remain reachable as `greia / greia` during active hardware bring-up;
- root SSH remains disabled;
- key auth may coexist as an automation path;
- base/release images remain fail-closed unless release remote-access policy is explicitly changed;
- Parent credential changes must not become a generic web-to-shell/root bridge.

The Greia Parent API/client foundation remains API-first and versioned. Current LAN HTTP/shared-bootstrap pieces remain **provisional**, not production credential security. Production pairing still requires the accepted Greia-local approval + authenticated encrypted transport path.

---

# 8. Activity package / catalogue state

A guarded `.greiaactivity` **new-install foundation** exists. It uses the real Activity registry/trust/runtime path and includes bounded archive validation, immutable staged versions, transactional publication and distinct parent-trusted unsigned provenance.

It is not full R10.

Still open before R10 closure:

- update/version replacement policy;
- remove workflow;
- rollback/version selection;
- signature/revocation/public trust chain;
- save migration/compatibility during update;
- complete parent-facing release enablement.

Ordinary/release systems must not silently enable package installation merely because source APIs exist. Parent capability negotiation remains authoritative.

ADR 0023/0024 continue to require an optional official catalogue rather than an install monopoly, separate provenance/license/price concepts, and no child-facing advertising/purchase-pressure model.

---

# 9. Awards / badges state

ADR 0025 and `docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md` define the selected platform-owned Awards architecture.

Important selected constraints:

- Activities report facts/scores; they do not mint durable Awards directly;
- Reward quantity, durable Award/badge and transient Celebration remain distinct;
- award grant and presentation are separate operations;
- earned Awards survive Activity uninstall and logical backup/restore;
- cross-Activity achievements are Greia platform policy;
- celebration UI must not weaken trusted Home/Back or justify a desktop notification/windowing layer;
- manipulative streak/FOMO/advertising/purchase mechanics are rejected.

The Award ledger/evaluator/collection/celebration scheduler are **not yet implemented** merely because the architecture is documented.

---

# 10. Responsive UI / localization / My Greia

The current source contains the accepted responsive/canvas/localization platform work, including:

- ADR 0026 automatic responsive UI/layout;
- ADR 0027 Activity logical canvas/world-camera semantics;
- ADR 0028 localization/language context;
- platform-safe Activity geometry derived from trusted Home/Back regions;
- shared Pygame responsive/canvas helpers;
- current My Greia profile customization source;
- first-party READY corrections requiring a first usable presented frame.

These source families were covered by owner-controlled gates before the later simulator/emoji commits. Any change after those exact evidence boundaries requires a fresh aggregate run before current-head PASS is claimed.

Typography/emoji is now part of this same shared UI story; do not create a separate Activity-local text platform.

---

# 11. Exact verification sequence now

On the owner-controlled current Linux checkout, preserve the first failure and do not weaken tests.

### A. Emoji/Writing focused gate

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_typography_emoji \
  tests.test_writing_emoji_editing -v
```

Also execute the existing relevant Writing/UI/Activity validation tests, including the first-party Activity validator.

### B. Simulator focused gate

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

### C. Complete source gate

```bash
make verify
```

Only a real current-head execution can establish a current source PASS. Note: at the 2026-08-19 owner-controlled checkout, `make verify` is blocked only by import-time errors in the in-progress emoji (`emoji_palette` `⭐` grapheme) and simulator (`SimulatorActivitySupervisor` missing) modules — both owner tranches, unrelated to the boot/SSH/installer work in §6/§7.

### C2. Boot / installer / SSH focused gate

These pass independently of the emoji/simulator import issue:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_boot_experience_contract \
  tests.test_boot_contract \
  tests.test_boot_animation_contract \
  tests.test_installation_hardware_regressions \
  tests.test_installer_engine \
  tests.test_launcher_presentation -v
```

### D. Then rebuild image / physical evidence

If and only if source is green (or the boot scope is green and emoji/simulator are explicitly the owner's in-progress tranche):

1. build the canonical current legacy installer/target;
2. build the syslinux/FAT32 live USB with `tools/build-live-usb.sh` (the Acer-compatible path);
3. inspect initramfs/boot-art/package composition (renderer architecture, no Plymouth, no build-only leak);
4. verify the added emoji/font package exists in the installed target;
5. measure installed footprint;
6. run Writing emoji visual/edit/save acceptance;
7. repeat current boot/installer/launcher acceptance on the Acer;
8. continue the already defined R7 physical/display/input evidence.

---

# 12. Current physical acceptance additions for emoji

The next physical Acer/low-resource acceptance should now include a Writing session that proves:

1. `Hello 🙂!` renders as Nunito + color emoji;
2. `❤️`, `👍🏽`, `👩‍🔬`, `🏳️‍🌈`, `🇮🇹`, and `1️⃣` render without tofu/component breakup;
3. Left/Right crosses each composed emoji in one step;
4. Backspace/Delete removes each composed emoji in one operation;
5. click placement does not land inside a grapheme sequence;
6. wrapped lines do not split an emoji sequence;
7. the visual picker is contained and legible at 1024×600 and the supported smaller reference viewport;
8. picker insertion produces standard Unicode text;
9. save/exit/relaunch preserves the exact text;
10. first-render/cached-render latency and RSS are acceptable;
11. emoji cache growth remains bounded;
12. no Home/Back protected-region interaction is compromised.

No physical PASS is currently claimed for this list.

---

# 13. Current source landmarks

### Typography / emoji

```text
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
activities/writing/main.py
tests/test_typography_emoji.py
tests/test_writing_emoji_editing.py
build/package-sets/platform-shell-pygame.txt
build/package-sets/runtime-python.txt
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
skills/greia-activity-authoring/SKILL.md
```

### R7 display/session/input

```text
src/greia_launcher/display_session.py
src/greia_launcher/system_chrome.py
src/greia_platform/system_chrome.py
src/greia_platform/input_core.py
src/greia_platform/pygame_input.py
src/greia_platform/hal.py
src/greia_platform/hal_legacy_x.py
```

### Activity simulator

```text
src/greia_simulator/
tools/greia_simulator.py
tests/test_greia_simulator.py
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

### Parent / package

```text
src/greia_parent/
src/greia_platform/activity_packages.py
src/greia_platform/activity_assets.py
src/greia_platform/trust.py
```

### Boot / installer / SSH / real hardware

```text
build/early-boot/greia-fb-splash.c          initramfs framebuffer renderer
build/early-boot/README.md
tools/generate_boot_artwork.py              canonical white-frame logo lineage
assets/boot/source/                         legacy frame source material
assets/boot/static/greia-boot-logo.png      GRUB + launcher logo
build/overlay/etc/greia-boot/boot-logo.ppm  initramfs PPM (target)
build/installer-overlay/etc/greia-boot/     initramfs PPM (installer)
build/overlay/etc/initramfs-tools/          storage hook + early-fb hook + stages
build/installer-overlay/etc/initramfs-tools/
build/overlay/etc/grub.d/10_greia_appliance GRUB white-frame + observable-boot args
build/live-syslinux/syslinux.cfg.in         straight-to-installer syslinux config
tools/build-live-usb.sh                     Acer-compatible syslinux/FAT32 USB builder
src/greia_launcher/boot_intro.py            one-shot Shell intro (<=1.0 s)
src/greia_launcher/boot_chime.py            one-shot fail-silent chime
src/greia_platform/boot_logo.py             canonical boot-logo resolver
src/greia_platform/boot_contract.py         GRUB/kernel-arg validator (+ --developer)
src/greia_platform/grub_security.py         GRUB recovery credential
build/build-image.sh                        target builder (dev-SSH-at-build)
build/build-installer-image.sh              live-installer builder (dev-SSH-at-build)
tools/provision_developer_image.py          target dev provisioning
tools/provision_developer_installer.py      live-installer dev provisioning
tests/test_boot_experience_contract.py
tests/test_boot_contract.py
tests/test_boot_animation_contract.py
tests/test_installation_hardware_regressions.py
```

### Active plan / evidence

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/testing/LOCAL_AGENT_START_HERE.md
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
```

---

# 14. Exact continuation priorities

1. **Run the new emoji/Writing focused tests** on the current owner-controlled Linux checkout.
2. Run the current **simulator focused tests**.
3. Run **`make verify`** at the exact same current checkout; preserve the first failure. (At the 2026-08-19 checkout this is blocked only by the in-progress emoji/simulator import errors; the boot/SSH/installer focused gate passes.)
4. **Resolve the in-progress emoji (`emoji_palette` `⭐` grapheme) and simulator (`SimulatorActivitySupervisor`) import failures** so `make verify` can pass cleanly at current head — these are the owner's active tranches and the only aggregate-gate blockers.
5. If source passes, rebuild the current legacy installer/target and measure the **Noto Color Emoji + regex installed footprint**.
6. Execute Writing visual/grapheme/picker/save acceptance on the real 1024×600/Acer-class path.
7. Continue physical boot/installer/launcher acceptance; rebuild the syslinux/FAT32 USB from current `main` with `tools/build-live-usb.sh` so the clean-logo and later fixes are on the medium actually tested.
8. Continue R7 direct graphics/session/input evidence; do not select/deepen X11 or add compositor complexity merely for emoji.
9. Continue secure Parent pairing/encrypted transport and full R10/R11/R12 only according to their existing prerequisites.

---

# 15. Non-negotiable continuation rules

- `main` only unless the owner explicitly changes branch policy;
- GitHub is canonical source truth;
- no unauthorized GitHub Actions use or inspection;
- no current-head PASS claim without current-head execution;
- no visible Linux UI during normal child operation;
- R7 remains open; production Xorg/xinit remains provisional until evidence selects/migrates the backend;
- trusted Home/Back remain outside Activity rendering/input authority;
- ordinary Activities do not gain raw `/dev/input` or DRM authority as a convenience shortcut;
- Activity display/input/runtime logic remains behind Greia platform contracts;
- child text stays standard Unicode/UTF-8;
- grapheme clusters are atomic user-visible editing units;
- normal Greia UI uses the shared typography service instead of Activity-specific host-font discovery;
- Noto Color Emoji is a fallback, not Greia system iconography;
- emoji must not replace trusted Greia semantic controls;
- shared emoji/grapheme caches remain bounded and resource cost must be measured on C0;
- the Writing picker is a current reference implementation, not proof of universal cross-runtime picker support;
- Awards remain Greia-owned progression state, not Activity-minted badges;
- the official catalogue remains optional distribution infrastructure rather than the only supported Activity path;
- license/provenance/price/trust remain separate concepts;
- Parent HTTP/shared-bootstrap transport remains provisional until authenticated encrypted pairing is implemented;
- normal/release SSH policy must not be inferred from current development bring-up convenience;
- source/build/VM/physical evidence scopes stay explicit and honest.

Resolve the exact current `main` SHA before any owner-controlled verification/build run and record that SHA with the returned evidence.
