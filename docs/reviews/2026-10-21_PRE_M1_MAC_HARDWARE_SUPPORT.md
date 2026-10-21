# Pre-M1 Apple hardware support: research and plan (2026-10-21)

Status: DESIGN SPEC / research. No source changed. Evidence labels: **VERIFIED-DOC** = read in the cited
page today; **FROM-KNOWLEDGE** = well-known but not re-verified today; **LAB** = must be confirmed on a
real Mac before we promise anything. No Mac has been booted for this review.

Plan status (2026-10-21, later the same day): source items done and UNPROVEN on real Macs: pool force-list, Broadcom/Radeon/NVIDIA ID rules with a b43 diagnostic (sections 2.2 items 1-3 and 7 partly), `hid_apple fnmode=1` (not the "2" suggested in section 3; 1 keeps media keys primary) and a `b43` blacklist. Still open: EFI boot media/installed EFI (largest blocker), wl prebuilt modules, hardware probe tool, LAB. See HANDOVER and the 2026-09-15 plan entry "Legacy Mac / netbook hardware support".

## 0. Headline findings

1. **Every Greia image today is BIOS-only.** All `build/profiles/*.toml` use `layout = "bios-single-ext4"`
   (or the Pi layout), `installed_adapter = "grub-pc-bios"`, and `build/package-sets/boot-grub-pc.txt`
   is just `grub-pc` + `grub-pc-bin`. There is no `grub-efi-*` package and no ESP anywhere in the repo.
   Intel Macs are EFI machines, so **the first blocker for every Mac is boot, not drivers.**
2. Wi-Fi is the biggest driver risk: most 2007-2015 MacBooks carry a Broadcom chip whose usable driver
   is either firmware-less-but-unredistributable (b43), or out-of-tree (wl). Neither is covered by our
   pool, which is `non-free-firmware` only (`build/lib/compose.sh` lines ~393-395).
3. Debian no longer ships i386 kernels/installers in trixie
   ([release notes](https://www.debian.org/releases/trixie/release-notes/issues.html): "no official kernel
   and no Debian installer for i386 systems"). Our i386 profiles are bookworm (support end 2028-06-30
   in `legacy-x86-i686.toml`), which is the right base for 2006-2007 Macs. Plan on bookworm for any Mac work.
4. PowerPC iBook/PowerBook: **not supportable** (section 5).
5. T2 Macs (2018-2020): **not supported** (section 4).

## 1. Boot

### 1.1 Which Macs have which firmware (FROM-KNOWLEDGE; confirm per model identifier with `ioreg`/`sysctl hw.model`)

| Generation | Typical models | CPU | EFI | Notes |
|---|---|---|---|---|
| A. 2006 Core Duo | MacBook1,1; MacBookPro1,1/1,2; Mac mini1,1; iMac4,1/5,x/6,1 | 32-bit only (Yonah) | **32-bit EFI** | needs i386 userland AND kernel |
| B. 2006-2007 Core 2 | MacBook2,1/3,1; MBP2,x/3,1; Mac mini2,1; iMac7,1 | 64-bit | **32-bit EFI** | "mixed" machines: 64-bit CPU, 32-bit firmware |
| C. 2008-2011 | MacBook4,1+, MBP4,1+/8,x, Air2,1+, mini3,1+, iMac8,1+ | 64-bit | 64-bit EFI | amd64 or i686 both OK |
| D. 2012-2017 | Retina MBP, Air, mini, iMac | 64-bit | 64-bit EFI (UEFI-like) | NVMe/PCIe SSD on 2013+ |
| E. 2016-2020 with T2 (2018+) | MBP 2018+, Air 2018+, mini 2018, iMac 2020 | 64-bit | T2 secure boot | see section 4 |

Sources for the Core Duo vs Core 2 / 32-bit-EFI split: [libreboot MacBook2,1 page](https://libreboot.org/docs/hcl/macbook21.html),
[Arch forum thread](https://bbs.archlinux.org/viewtopic.php?id=238695) (firmware boots `BOOTIA32.EFI` from an EFI partition).

### 1.2 What the firmware needs from our USB
- A **FAT32 ESP** containing `EFI/BOOT/BOOTX64.EFI` (64-bit EFI) or `EFI/BOOT/BOOTIA32.EFI` (32-bit EFI).
  Apple's boot picker (hold **Option** at power-on) shows such media as "EFI Boot". Debian packages
  [`grub-efi-ia32`](https://packages.debian.org/bookworm/grub-efi-ia32) ("EFI-IA32 ... as used by Intel Macs")
  and `grub-efi-amd64`, plus their `-bin` variants, which are what `grub-mkimage`/`grub-install --removable` need.
- Apple EFI is picky about hybrid MBR/GPT: pure GPT with ESP is the safest; a protective MBR with only the
  GPT entry works; hand-made hybrid MBRs are a known trouble source. (FROM-KNOWLEDGE; LAB.)
- Legacy BIOS/CSM: Intel Macs of roughly 2006-2015 expose a "Windows" entry in the Option picker that
  boots MBR/BIOS code from internal or USB disks, so our **current grub-pc USB may boot on many
  generation A-D Macs via CSM** (LAB, unconfirmed; fragile because it needs an MBR active partition
  and varies by model/firmware). It must not be our plan of record: the Apple CSM is absent on T2 Macs.
- rEFInd is a widely suggested fallback ([Debian wiki MacBook](https://wiki.debian.org/MacBook),
  [tinkerdifferent report](https://tinkerdifferent.com/threads/installing-linux-mint-on-my-2006-macbook.4163/post-35808)).
  We should not require it; it is a documented user workaround only.

### 1.3 Does our installer media boot them today?
Unknown/probably only by CSM luck (generation A-D). Gaps:
1. No ESP and no EFI GRUB on the installer image (`docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` describes grub-pc BIOS live boot).
2. **Installed system** also BIOS-only: even if the installer boots, the installed disk would not boot on a
   Mac that lacks CSM, and `grub-install` for `i386-pc` on a GPT disk needs a bios_grub partition.
3. The installer's eligible-target logic and A/B GRUB code (`src/greia_platform/grub_ab.py`) assume `grub-pc`.

### 1.4 What the image must contain
- New boot adapters, siblings of `grub-pc-bios`: `grub-efi-ia32` and `grub-efi-amd64` (dual-install on
  the removable path is the cheapest approach: both BOOTIA32.EFI and BOOTX64.EFI on one ESP, so one USB
  boots both firmware widths).
- New layout adapter (ESP + system + persistent, GPT) beside `bios-single-ext4`. Keep the bios layout untouched.
- Package sets: `boot-grub-efi-ia32.txt` (`grub-efi-ia32-bin`, `grub-efi-ia32`), `boot-grub-efi-amd64.txt`,
  plus `dosfstools` (already in the builder), `efibootmgr` on the installed side (optional; on Apple EFI the removable path works without NVRAM writes, and `efibootmgr` frequently fails on early Apple EFI, so do not make it fatal).
- **i686 vs amd64:**
  - Generation A (32-bit CPU): only the i686 profile can run. 32-bit EFI + i386 kernel: native, no mixed mode.
  - Generation B (64-bit CPU, 32-bit EFI): the **i686 profile is the simplest** (native 32-bit stack). An amd64
    kernel can start via EFI mixed mode (needs `bootia32.efi` plus a kernel built with `CONFIG_EFI_MIXED`;
    Debian's kernel config is believed to enable it, but a [trixie package search](https://packages.debian.org/ia32)
    only proved `grub-efi-ia32` exists) - LAB before relying on it. Recommendation: serve B with the i686 image.
  - Generation C-D: both work. `linux-image-686` (non-PAE) is already our i686 kernel; Core 2 CPUs support PAE,
    so `linux-image-686-pae` is also fine, but staying non-PAE keeps one i686 profile.
- Boot cover: `cover_backend = "greia-early-framebuffer-v1"` assumes legacy VGA/VESA. EFI GOP framebuffer
  hand-off (`efifb`/`simpledrm`) must be validated for the boot-cover contract. (LAB; risk for AGENTS contract 1.)
- Retina displays (2012+ 2560x1600): GRUB gfxmode and the Shell scale need a check; not a boot blocker.

## 2. Wi-Fi

Facts from the [Debian wl wiki](https://wiki.debian.org/wl) and the Debian
[firmware-b43-installer page](https://packages.debian.org/bookworm/firmware-b43-installer) (VERIFIED-DOC):

| Chip | PCI ID(s) | Open driver | Proprietary option | Firmware status in Debian |
|---|---|---|---|---|
| BCM4311 / 4312 | 14e4:4311, 4312 | b43 | wl | b43 fw not redistributable |
| BCM4312 (LP) | 14e4:4315 | b43 (LP-PHY) | wl | idem |
| BCM4321 | 14e4:4328/4329/432a | b43 | wl | idem |
| BCM4322 | 14e4:432b/432c/432d | b43 | wl | idem |
| BCM43224 / 43225 | 14e4:0576, 4353, 4357 | **brcmsmac** | wl | `firmware-brcm80211` (non-free-firmware, **redistributable**) |
| BCM4313 | 14e4:4727 | brcmsmac | wl | firmware-brcm80211 |
| BCM4331 | 14e4:4331 | b43 | wl | b43 fw not redistributable |
| BCM4360 / 4352 | 14e4:43a0, 4360, 43b1 | none | **wl only** | n/a |
| BCM43227/43228/43142 | 14e4:4358/4359/4365 | none | wl only | n/a |

Not in the wiki table but relevant (FROM-KNOWLEDGE): 2015+ MacBooks use BCM4350/4355/4364 (PCI 14e4:43a3 etc.) that
`brcmfmac` can drive, but Apple boards need an Apple-specific NVRAM/`.txt` file that Debian does not ship;
this is the same missing-NVRAM problem the t2linux project solves by extracting from macOS.
Early 2006-2007 models also used Atheros AR5008/AR5418 (`ath9k`, no firmware, mainline) - already handled by
the kernel (PCI vendor 168c). Later Intel-WiFi MacBooks do not exist; Intel Wi-Fi appears only in Macs/hackintosh-like swaps.

Which Mac uses what (FROM-KNOWLEDGE, LAB by `lspci -nn`): 2006-07 mostly Atheros or BCM4321/4311;
2008-09 BCM4321/BCM4322; 2010 BCM4322; 2011-12 BCM4331; 2013-14 BCM4360 (wl-only) or BCM4350.

### 2.1 Licensing / feasibility per option
- **b43 / b43legacy**: firmware must be extracted by `b43-fwcutter` from a Broadcom proprietary driver blob. Debian
  cannot redistribute it; `firmware-b43-installer` is in `contrib` and *downloads* it at install time. That
  breaks "offline-first". Greia cannot bundle it unless the owner obtains a licence; do not assume it is allowed.
  The honest options: (a) skip b43 and use wl for these chips, (b) owner-supplied cutter output (user-provided file).
- **brcmsmac** (BCM43224/25/13): fully offline-capable via `firmware-brcm80211`. This package is already a normal
  isenkram firmware candidate, so it should flow through the existing pool with no new code beyond verifying the mapping.
- **wl** (`broadcom-sta-dkms`, `non-free` component, **not** `non-free-firmware`): redistributable binary blob wrapped
  in source. It builds a module with DKMS, which needs `gcc`, `make`, `linux-headers-*` on the target - conflicts with "no
  compilers on target". Solution: **build `wl.ko` on the build host for the exact target kernel** (our kernel is frozen per image:
  `linux-image-686`/`linux-image-amd64`), package it as `greia-wl-modules-<kver>` (one `.ko`, a `modprobe.d` file)
  and put it in the hardware-support pool as a hardware package, not firmware. Builder needs the
  `non-free` component enabled only on the build side.
  Risks: kernel ABI bump invalidates the module (pin the kernel version in the pool candidate manifest and refuse mismatches);
  wl taints the kernel (cosmetic); wl has had security issues; it is out-of-tree code carried by us.
- **Module conflicts** (VERIFIED-DOC in the wl wiki): recent `broadcom-sta` blacklists `b44, b43, b43legacy, ssb, brcm80211, brcmsmac`.
  `bcma` also binds BCM43xx PCIe parts. Greia must ship one explicit modprobe policy per chip ID, not rely on blacklist races:
  for wl-only chips blacklist b43/bcma/brcmsmac; for brcmsmac chips do NOT install wl.
- **Fit with `iwd`**: wl is a legacy WEXT/cfg80211-partial driver; test it with iwd (our network stack,
  `network-basic.txt`). Known to work with NetworkManager/wpa_supplicant more reliably. LAB-critical.

### 2.2 Recommended Greia strategy for Wi-Fi
1. Detect Broadcom (vendor 14e4) network PCI IDs at install time via the existing sysfs inventory.
2. Map: brcmsmac IDs -> `firmware-brcm80211`; wl-needed IDs -> prebuilt `greia-wl-modules` for the target kernel;
   b43-only legacy (BCM4306/4318, old) -> unsupported unless user supplies firmware.
3. Always show a clear "no Wi-Fi driver available" state; Ethernet/USB dongle (with Realtek/Atheros in-tree) remains the fallback.
4. USB Ethernet and Thunderbolt/ Apple adapters work in-tree; recommend an RTL8153/AX88179 adapter as the documented bypass.

## 3. Other hardware (FROM-KNOWLEDGE unless cited)

| Area | Status | Greia action |
|---|---|---|
| Keyboard fn/media keys | `hid_apple` in-tree; fn-mode via `/sys/module/hid_apple/parameters/fnmode`. [Debian wiki](https://wiki.debian.org/MacBook) mentions `apple:badmap`, `lv3:rwin_switch` and pommed | ship `options hid_apple fnmode=2` (F-keys with fn for media); verify the Greia keyboard layer (kids use arrows+Space, so low risk) |
| Touchpad | pre-2015: `bcm5974` in-tree, Synaptics-like; 2015+ Force Touch: `applespi` driver (in-tree since 5.x for 2015-2017 MBP) | tap-to-click default off already (contract 15); needs typed setting, not xinput |
| Backlight | `apple_bl`/`intel_backlight`/`nvidia_bl`; screen+kbd backlight via `applesmc` | keep to Shell brightness setting; do not require |
| Fans/thermal | `applesmc` + `coretemp`; fanless-ish default OK; Macs run hot under Linux | ship `lm-sensors`? no; `thermald` optional; at least confirm `applesmc` loads |
| Audio | `snd_hda_intel` with Cirrus CS4206/CS4208 codecs; HDMI-only quirks; 2016+ MBP CS8409 poor | already in RC image; verify mic (the RC profile checks it) |
| GPU Intel (GMA 950/X3100/HD) | in-tree i915 or modesetting; `xserver-xorg-video-intel` already in profile | OK |
| GPU NVIDIA 2008-2010 (9400M, 9600M GT) | `nouveau` + external firmware only for newer cores; 9400M works with open kernel path; some need `firmware-misc-nonfree` for accel | add `firmware-nvidia-graphics`? (bookworm: in `firmware-misc-nonfree`) via isenkram; accept software rendering fallback via `fbdev`/`vesa` already listed |
| GPU AMD (2011+ MBP 6750M/etc) | `radeon`/`amdgpu` need `firmware-amd-graphics` (~tens of MiB uncompressed) | pool candidate; budget risk (see 7) |
| Dual-GPU MBPs | gpu-switcheroo; Linux may boot to the dGPU only, black screen risks | boot with `nomodeset`-style fallback ladder (`vesa`) |
| FaceTime / iSight camera | iSight: needs `isight-firmware-tools` (firmware extracted from OS X) per [Debian wiki](https://wiki.debian.org/MacBook); FaceTime HD (2011+): `facetimehd` out-of-tree + extracted firmware | **not supported**; Greia has no camera Activity contract |
| SD card reader, Thunderbolt | in-tree | none |
| SSD / SATA | AHCI OK; 2013+ PCIe SSD uses Apple NVMe quirks, OK in modern kernels | bookworm 6.1 needs no action; installer target selection must list `nvme0n1` |
| Sleep/resume | Often flaky on Linux | do not promise; shutdown works |

Notes: Greia contract 1 (no visible shell) and the `quiet` boot policy mean an unrecognized-hardware failure must degrade to a calm Shell state, not a console error.

## 4. T2 Macs (2018-2020) and the post-2015 line

- T2 chip gates the internal keyboard, trackpad, audio, SSD and Wi-Fi/Bluetooth behind the `apple-bce`/`t2bce`
  driver stack plus kernel patches carried by t2linux, mostly **not in Debian's mainline kernel**
  ([t2linux wiki](https://wiki.t2linux.org/): per-distro patched kernels, own ISO repositories; only `apple-ib-drv` is upstream, in 6.15).
  Debian bookworm's 6.1 kernel has none of it. Without it the Mac has no usable keyboard or trackpad and often cannot see
  the internal SSD. Secure Boot policy also blocks unsigned loaders by default.
- **Verdict: Not supported.** A USB keyboard/mouse and an external disk could in principle work but that is not an appliance for kids.
- 2015-2017 MacBook (no T2) with SPI keyboards: `applespi` is in-tree from Linux 5.3; MacBook 12" 2015-2017 needs extra
  out-of-tree drivers for keyboard/trackpad; classify as **best effort / LAB**.

## 5. PowerPC (iBook/PowerBook G3/G4)

- **Not supported, and we should say so.** Debian's powerpc (32-bit big-endian) was removed as a release
  architecture with stretch (2017) (FROM-KNOWLEDGE); the only 'powerpc' content today is the unofficial Debian Ports
  (sid-only, no stable, no security). The trixie release notes mention PowerPC only as `ppc64el` VMs
  ([release notes](https://www.debian.org/releases/trixie/release-notes/issues.html)). Bookworm has no powerpc.
- Further blockers: Open Firmware/yaboot boot, big-endian (our "portable state" contract 12 requires architecture-neutral
  state across i386/ARM64/amd64, endian-safe but never tested BE), 256-768 MiB RAM Macs with no `python3-pygame`/Xorg support there, no `isenkram`, and no
  Wi-Fi firmware story. Treat as out of scope permanently; add an installer pre-boot message only if we can detect it (we cannot - the machine never reaches our code).

## 6. Support matrix

Legend: S = Supported (works with what is in the image), F = Supported with bundled redistributable firmware,
M = Needs prebuilt out-of-tree module, X = Not supported, ? = LAB to determine. Today's status is for the **current BIOS-only images**.

| Generation | Boot (today) | Boot (after sec. 7 item 1) | Wi-Fi | Verdict after plan |
|---|---|---|---|---|
| A: 2006 Core Duo (32-bit EFI) | ? CSM only | S (i686 + `BOOTIA32.EFI`) | Atheros S / BCM4321 M | S with wired fallback; wl-dependent Wi-Fi |
| B: 2006-07 Core 2 (32-bit EFI) | ? | S (i686 image) | BCM4321/4322 M | same |
| C: 2008-2011 (64-bit EFI) | ? CSM | S | BCM4322/4321 M; BCM43224 F | S / M |
| D: 2012-2014 | ? | S | BCM4331 M; BCM4360 M (wl only) | S / M |
| D: 2015-2017 non-T2 | ? | S | BCM4350 etc. needs NVRAM (X without it) | partial: wired only |
| E: T2 2018-2020 | X | X | X | **X** |
| PowerPC | X | X | X | **X** |

## 7. Recommendation, in order (highest value / lowest risk first)

| # | Work | Effort | Notes / risk |
|---|---|---|---|
| 1 | **Hardware reality check**: owner (or a borrowed machine) runs a read-only Greia probe on 3 real Macs (one per gen A/C/D) and records `lspci -nn`, `dmidecode`, EFI width (`/sys/firmware/efi/fw_platform_size`), Wi-Fi ID. Add a `tools/` script that emits this as a JSON report. | 0.5 d | prevents building for the wrong chips; no image risk |
| 2 | **EFI boot media**: new ESP layout adapter, `boot-grub-efi-ia32/amd64` package sets, dual `BOOTIA32.EFI`/`BOOTX64.EFI` on installer USB; keep BIOS entry as hybrid. Boot-cover and `grub_ab`/installer EFI branch. Test in QEMU (OVMF 32/64) then the Macs. | 5-8 d | largest; touches installer + `grub_ab.py` + boot contract. Must not regress BIOS profiles. Image delta est. 4-8 MiB (grub-efi-*-bin; measure). |
| 3 | **Installed-system EFI**: installer writes ESP + `grub-install --removable --no-nvram`; `efibootmgr` failures non-fatal | 2-3 d | Apple firmware quirks (LAB) |
| 4 | **Broadcom detection + brcmsmac**: add a Broadcom resolver beside `IsenkramHardwareSupportResolver` (vendor 14e4 mapping table above); verify `firmware-brcm80211` lands in the pool for 43224/43225/4313 | 1-2 d | low risk; reuses pool |
| 5 | **wl prebuilt module package**: build-host recipe producing `greia-wl-modules-<kver>` for i686 and amd64, pool candidate keyed on PCI IDs, modprobe policy, kernel-pin check in `TargetImageHardwareIdentity` (add kernel release). Needs `non-free` on build host only. | 4-6 d | licence statement in docs, taint, kernel-update coupling, iwd compatibility LAB |
| 6 | **Apple input defaults**: `hid_apple fnmode`, `bcm5974` check, tap-to-click off | 1 d | trivial |
| 7 | **Graphics fallbacks**: verify nouveau/radeon firmware via isenkram; EFI GOP framebuffer boot cover; `vesa`/`fbdev` fallback | 2-3 d | pool size (firmware-amd-graphics is large) |
| 8 | Document "unsupported" list (T2, PowerPC, FaceTime camera, 2015+ NVRAM Wi-Fi) in the installer pre-check and docs | 0.5 d | honesty over silent failure |

### Budget (1,300 MiB ceiling, AGENTS contract 6)
- EFI GRUB binaries live mostly on the installer/ESP, not the installed core; estimate low single-digit MiB. Measure.
- `firmware-brcm80211`, `wl.ko` (a few MiB per kernel) sit in the hardware-support pool (installer side), not the installed
  core, as long as the installer only copies what it needs offline. The pool is bounded; add a size gate per candidate.
- `firmware-amd-graphics` / `firmware-nvidia-graphics` are the real threat: keep them pool-only, never in `platform-base`.
- Two kernels' worth of wl modules (i686 + amd64) is the only per-arch multiplier.

### Open questions for the owner
1. Is licensing wl via Debian `non-free` acceptable for a free product shipped to Italian families? (Debian already redistributes it.)
2. Is b43 (user-supplied firmware) acceptable as a documented manual step, or should those chips be declared unsupported?
3. Can we borrow at least one gen-A/B (32-bit EFI) and one gen-D MacBook for LAB validation?

## Sources
- https://www.debian.org/releases/trixie/release-notes/issues.html
- https://wiki.debian.org/wl
- https://wiki.debian.org/MacBook
- https://packages.debian.org/bookworm/grub-efi-ia32
- https://packages.debian.org/bookworm/firmware-b43-installer
- https://wiki.t2linux.org/
- https://libreboot.org/docs/hcl/macbook21.html
- https://bbs.archlinux.org/viewtopic.php?id=238695
