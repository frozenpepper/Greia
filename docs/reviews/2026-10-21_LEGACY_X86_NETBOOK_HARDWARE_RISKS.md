# Legacy x86 netbook and 2005-2012 laptop hardware risks (2026-10-21)

Status: DESIGN SPEC / research. No source changed. Labels: **VERIFIED-DOC** = read in the cited page today;
**FROM-KNOWLEDGE** = well known, not re-verified today; **LAB** = must be confirmed on real hardware before
we promise anything. No machine was booted for this review. Companion to
`2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md` and `acer/2026-10-21_ASPIRE_1280X800_VIEWPORT_AND_TARGET_WIFI.md`.

Plan status (2026-10-21, later the same day): source items done and UNPROVEN on real netbooks: section 5.1 force-include list (`FORCED_FIRMWARE_PACKAGES`, ipw2x00 best effort, SOF/intel-sound judged irrelevant to i686), the b43 "no firmware" completion note (5.1 c), a PCI/USB ID rule table, and the extended resume hook list (5.2, one test covering the list rather than one fixture per driver). Open: profile notes and About end-of-support string (5.3), supported-hardware docs page (5.4), all LAB items in section 7.

## 0. Headline: the i386 line is a bookworm line, and it has an end date

1. **Suite and kernel (repo, read today).** Every i386 profile (`legacy-x86-i686*.toml`, `acer-aspire-one-i386*.toml`)
   is `suite = "bookworm"`, `architecture = "i386"`, `support_end_date = "2028-06-30"`.
   `legacy-x86-i686*` and `acer-aspire-one-i386-nonpae*` use `kernel_package = "linux-image-686"` (**non-PAE**);
   only `acer-aspire-one-i386` / `-ab` / `-dev` use `linux-image-686-pae`. The generic profile description says the
   non-PAE flavour was chosen "to avoid requiring PAE".
2. **Trixie has no i386 kernel and no i386 installer** (VERIFIED-DOC, Debian 13 release notes, "Reduced support for
   i386": [issues](https://www.debian.org/releases/trixie/release-notes/issues.en.html); reported by
   [LWN](https://lwn.net/Articles/1033741)). i386 remains only as userland for multiarch/chroots on amd64, with
   fewer packages, and the notes say it is meant for 64-bit CPUs and requires **SSE2**. Debian tells i386 users not
   to upgrade and to reinstall as amd64 or retire the hardware. So **there is no Debian 13 route for a 32-bit-only
   machine** (Atom N270/N280, Pentium M, Core Duo "Yonah").
3. **Bookworm end dates (VERIFIED-DOC, [Debian LTS wiki](https://wiki.debian.org/LTS)).** Bookworm LTS runs
   2026-06-11 to **2028-06-30** and the LTS architecture list includes **i386**. Our `support_end_date` matches.
   Security updates for i386 therefore exist only until 2028-06-30 (LTS is a reduced-scope, volunteer/sponsored
   service; package coverage is narrower than regular security. FROM-KNOWLEDGE).
4. **Baseline is i686 + NOPL** (VERIFIED-DOC, [bookworm notes 5.1.13](https://www.debian.org/releases/bookworm/i386/release-notes/ch-information.en.html)):
   no i586 (AMD Geode, VIA C3 early, Pentium MMX). Those cannot run any Greia i386 image.
5. **PAE (VERIFIED-DOC for packages, FROM-KNOWLEDGE for CPUs).** bookworm `linux-image-686` is the meta-package for "PCs
   with one or more processors not supporting PAE" (6.1.190-1 today, [package page](https://packages.debian.org/bookworm/linux-image-686));
   `linux-image-686-pae` is the separate PAE flavour. CPUs lacking the PAE CPUID bit: **Pentium M Banias and early
   Dothan, some Celeron M (notably the Dothan-512 ULV 353 in the ASUS Eee PC 701/900)**. The kernel's `forcepae`
   option lets a PAE kernel boot on PAE-disabled Pentium M but taints the kernel
   ([kernel commit](https://git.linaro.org/plugins/gitiles/kernel/linux-linaro-stable.git/+/69f2366c9456d0ce784cf5aba87ee77eeadc1d5e)).
   Atom N270/N280 (Aspire One, Eee 1000/1005, MSI Wind, Samsung NC10) do support PAE (FROM-KNOWLEDGE; LAB-confirm
   with `grep -w pae /proc/cpuinfo`). **The non-PAE 686 kernel is the right default**: it boots everything the PAE
   one boots (Atom included) and the CPUs the PAE one cannot. Costs: RAM above ~3.x GiB unused, no NX on those CPUs (all
   targets are <=2 GiB netbooks anyway). Keep `-pae` profiles only as an owner-chosen optimisation.

### Consequences and decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| D1 | Is the legacy i386 line "supported until 2028-06-30, then frozen"? | **Yes.** State it in the release notes of every i386 image. No Debian-supported alternative exists after that. |
| D2 | What about 32-bit-only hardware after 2028-06-30? | Options: (a) freeze, ship as-is with a "no security updates" notice; (b) carry our own kernel build on bookworm sources (large, permanent maintenance); (c) trixie i386 userland + self-built 686 kernel (SSE2-only CPUs, fewer packages, no installer: not recommended). Decide at 2027-Q4 review; do nothing now. |
| D3 | Add a 64-bit line for Atom N450+/Core 2 netbooks and laptops? | **Yes, plan for it.** `acer-aspire-one-amd64` / `modern-amd64` already exist on bookworm; move them to trixie when ready. 64-bit-capable machines (N450/N550/D410, Core 2) should be steered to amd64 so they have a post-2028 path. |
| D4 | Non-redistributable firmware (Broadcom b43). Do we ever bundle or fetch it? | Default **no**: stay `non-free-firmware`-only (`build/lib/compose.sh` ~393). Needs an explicit legal/licensing decision; see 3.2. |
| D5 | Is the 512 MB / 800x480 tier (Eee 701) in scope? | Reference floor is 768 MiB / 1024x600. Treat 512 MB / 800x480 as **best-effort, not promised**. |

## 1. How Greia handles firmware today (read today)

- Target images carry `network-basic` (iwd, wireless-regdb, ...) but no firmware beyond what the base installs.
- Hardware enablement is **detect then install from a frozen pool**: `build/populate-hardware-support-pool.sh` builds
  `/opt/greia-hardware-support` from isenkram metadata, resolved against the target dpkg status, from
  `main non-free-firmware` only; `src/greia_installer/hardware_enablement.py` maps bound-driver `modinfo firmware:`
  declarations to pool packages and fails closed (`complete` false -> no target packages). The 2026-10-21 Acer failure
  came from incomplete detection leaving the installed target without `firmware-iwlwifi`.
- Resume workaround: `build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume`, `WIFI_RESUME_DRIVERS="iwl3945 iwl4965 b43 b43legacy brcmsmac ath5k"`.
- Boot is BIOS only (grub-pc). Fine for 2005-2012 PCs, which are BIOS machines.

## 2. Risk matrix

Status keys: **OK** works offline with no extra firmware; **POOL** needs a pool firmware package; **NONFREE**
needs firmware Debian cannot ship (contrib installer / vendor blob); **BROKEN/POOR** expect problems.
All rows are FROM-KNOWLEDGE except where a link is given; every row needs LAB confirmation (section 7).

### 2.1 Netbooks

| Family (CPU, RAM, screen) | Wi-Fi | Ethernet | GPU | Expected status |
|---|---|---|---|---|
| Acer Aspire One ZG5 / A110 / A150 (Atom N270, 512 MB-1.5 GB, 1024x600) | Atheros AR5BXB63 (AR5007EG, **ath5k**, no firmware) in most; some Broadcom BCM4312 (**b43**) or Intel 3945 (**iwl3945**) | Realtek RTL8101E/8102E (r8169, `rtl_nic` fw in `firmware-realtek`) or Atheros AR8132 `atl1c` (none) | GMA950 (i915) | **OK** (Atheros) / **POOL** firmware-iwlwifi (Intel, plus resume hook) / **NONFREE** (Broadcom) / Realtek NIC **POOL**. Our reference unit. |
| Aspire One D250 / D255 / AOD255 / D257 (N270-N550, 1 GB, 1024x600) | Atheros AR9285 (**ath9k**, no firmware; [wiki](https://wiki.debian.org/ath9k)) or Broadcom BCM4312/BCM4313 (b43 / brcmsmac) | Atheros AR8152/8131 `atl1c`/`atl1e` | GMA950 (N270) / GMA3150 (N450+) | **OK** (AR9285) / **NONFREE** BCM4312 / **POOL** `firmware-brcm80211` for BCM4313 (brcmsmac). N450+ are 64-bit: route to amd64 line. |
| ASUS Eee PC 701 / 2G/4G/8G (Celeron M ULV 353 **no PAE**, 512 MB, **800x480**) | Atheros AR5007EG (ath5k) | Atheros L2 `atl2`/AR8132 | GMA 900 (i915) | Wi-Fi/GPU **OK**; **non-PAE kernel mandatory**; 800x480 and 512 MB below floor. Best-effort. |
| Eee PC 900 / 901 / 1000 / 1000H (Celeron M or Atom N270, 1 GB, 1024x600 / 1024x600) | 900: AR5007EG; 901/1000H: Ralink RT2860/RT2790 (**rt2800pci**, `firmware-misc-nonfree`) | Atheros / Realtek | GMA 900 / 950 | **OK** (Atheros) / **POOL** firmware-misc-nonfree (Ralink). |
| Eee PC 1005HA/HAB/HE, 1015PE, 1001PX (Atom N270/N450, 1 GB, 1024x600) | Atheros AR9285 (OK) or Ralink RT3090 (rt2800pci, firmware-misc-nonfree) | Atheros AR8132 | GMA950 / GMA3150 | **OK** / **POOL**. Some 1005s ship Ralink: wide variation by SKU. |
| HP Mini 110 / 1000 / 1100 (Atom N270, 1 GB, 1024x576 or 1024x600) | Broadcom BCM4312 (b43) on many SKUs, Intel 5100/5150 or Atheros on others | Marvell/Realtek (`sky2`/r8169) | GMA950 | Mostly **NONFREE** (Broadcom) unless Intel/Atheros fitted. 1024x576 panels exist. |
| Dell Inspiron Mini 9 (910) (Atom Z520, 512 MB-1 GB, 1024x600) | **BCM4312** (b43), some Dell cards 1397 | Realtek r8169-family | **GMA500 Poulsbo** | **POOR**: b43 NONFREE and gma500 (see 3.3). Z520 has no 64-bit. Best-effort VESA/fbdev. |
| Dell Inspiron Mini 10 / 1010 / 1011 (Atom Z520/Z530, 1 GB, 1024x576 / 1366x768 options) | BCM4312 / Dell 1397/1510 (b43/brcmsmac) | Realtek | **GMA500 Poulsbo** (Z-series) | **POOR** as above. Mini 10v (N270, GMA950) is normal. |
| Lenovo IdeaPad S10 / S10e / S10-2 (N270, 1 GB, 1024x600) | Atheros AR5007EG or Broadcom BCM4312; S10e: Intel 5100 on some | Realtek | GMA950 | **OK** (Atheros) / **NONFREE** (Broadcom) / **POOL** (Intel). |
| Samsung NC10 / N110 / N130 / N145 (N270-N450, 1 GB, 1024x600) | Atheros AR9285 (some Realtek RTL8192) | Marvell `sky2` / Realtek | GMA950 / GMA3150 | **OK** (Atheros) / **POOL** firmware-realtek (RTL8192CE). |
| MSI Wind U90/U100/U120 (N270, 1-2 GB, 1024x600) | Ralink RT2860 (rt2800pci) or Realtek RTL8187SE on early units | Realtek r8169 | GMA950 | **POOL** firmware-misc-nonfree (Ralink); RTL8187SE: driver uncertain (3.1). |
| Toshiba NB100/NB200/NB205 (N270, 1 GB, 1024x600) | Atheros AR5007/AR9285 or Realtek | Realtek / Atheros | GMA950 | **OK** / **POOL**. |

### 2.2 2005-2012 laptops (mostly 15" / 14" / 12" with 1024x768 to 1366x768)

| Family | Wi-Fi | Ethernet | GPU | Expected status |
|---|---|---|---|---|
| ThinkPad T40/T41/T42/X31-X32 (Pentium M **Banias/Dothan: PAE absent**, 512 MB-2 GB, 1024x768) | Intel 2200BG/2915 (ipw2200/ipw2100: `firmware-ipw2x00`, package section for bookworm unverified) or Atheros | Intel e100/e1000, Broadcom tg3 | ATI Radeon 7500-9600 / Intel 855/915 | **non-PAE required**; ipw2x00 firmware: **LAB/verify package section**; Radeon R100-R300 need no GPU firmware; Intel 855-915 OK. |
| ThinkPad T60/T61/X60/X61/R60 (Core Duo T2xxx **32-bit only**, Core 2 T7xxx 64-bit) | Intel 3945ABG / 4965AGN (iwl3945/iwl4965, **POOL** firmware-iwlwifi) | Intel e1000e/Broadcom tg3 | Intel 945/965 or ATI X1300/X1400 / Radeon Mobility | **POOL**. Core Duo: i386 line only; Core 2: amd64 candidate. 4965 resume bug class like 3945. ATI X1xxx (R5xx) need **no** GPU firmware; R600+ (HD2xxx+) need `firmware-amd-graphics`. |
| Dell Latitude D400-D630, Inspiron 6400/1525, XPS M1210/M1330 | Intel 3945/4965 (POOL) or **Broadcom BCM4311/4312/4318 Dell 1390/1395/1490** (NONFREE) | Broadcom tg3/bnx2 (tg3 fw `firmware-misc-nonfree` on some) | Intel GMA / ATI Mobility / **NVIDIA GeForce Go** (nouveau, may need `firmware-misc-nonfree` nvidia blobs only for newer chips) | Broadcom Wi-Fi is the dominant failure; Intel cards **POOL**. Dell Wi-Fi is often swappable; document it. |
| HP Compaq nc6000-nc6400/nx6100-nx7400, Pavilion dv/tx (Pentium M, Core Duo/2) | Intel 2200/3945/4965 or Broadcom BCM4311/4318 | Broadcom tg3 / Realtek | Intel / ATI Xpress / NVIDIA | Mixed **POOL**/**NONFREE**. AMD Turion tx/dv: 64-bit, amd64 line. |
| Acer Aspire 3xxx/5xxx (5100, 5315, 5520, 5532), TravelMate 2xxx/4xxx (Celeron M, Pentium M, Core 2, Athlon/Turion X2) | Atheros AR5006/AR5BMB (ath5k OK), Broadcom BCM4311/4312/4315, Intel 3945/4965/5100, Realtek RTL8187B | Realtek/Atheros/Broadcom | Intel GMA / ATI / NVIDIA | Anything: sample both **OK** and **NONFREE**. Same-model SKUs differ by region. |

Cross-cutting: SD card readers (Ricoh/TI `rtsx_pci`/`sdhci`: RTS5209 and Realtek PCIe readers use `rtsx_pci`, no firmware; Ricoh R5C8xx often needs `sdhci` quirks; FROM-KNOWLEDGE/LAB), touchpads (Synaptics/Elantech/ALPS via kernel `psmouse` + libinput, no firmware; Elantech v1/v2 gesture quirks LAB), HDA audio (see 3.5).

## 3. Component notes

### 3.1 Wi-Fi
- **No firmware (OK offline):** ath5k (AR5xxx), ath9k (AR9285/AR9280/AR928x, [Debian wiki](https://wiki.debian.org/ath9k)), rtl8180/rtl8187 USB (mac80211 `rtl8187`; some firmware-free), b43legacy needs fw (see below).
- **`firmware-iwlwifi` (non-free-firmware):** 3945 (`iwlwifi-3945-2.ucode`), 4965, 5100/5150/5300, 6000 series. Already the Acer fix; must be in the pool and in the fallback set.
- **`firmware-realtek`:** RTL8192CE/8188CE (`rtl_nic`/`rtlwifi/*`), RTL8723; also Realtek NICs (r8169 `rtl_nic/*`). **RTL8187SE (Eee 701 era, MSI Wind early, some Acer)**: historically the staging `rtl8187se` driver, whose status in the Debian 6.1 kernel we have not verified: **LAB**, may be unsupported.
- **`firmware-misc-nonfree`:** Ralink RT2860/RT2800 (`rt2860.bin`/`rt3090`), Intel ipw2x00 on old Debian (verify which package carries `ipw2200-bss.fw`: it moved around across releases. LAB: `apt-file search ipw2200-bss.fw`).
- **`firmware-atheros`:** only Atheros USB/`ath9k_htc`/`ath10k`/`carl9170`; **not needed** for ath5k/ath9k PCI. Cheap to include.
- **`firmware-brcm80211`:** brcmsmac (BCM4313, BCM43224/43225) and brcmfmac (SDIO/USB). **Does not cover BCM4312/4311/4318**.
- **`firmware-libertas`:** Marvell 8686/8388 (OLPC, some SDIO netbooks); small, harmless in the fallback set.
- **`firmware-ti-connectivity`/`firmware-ath9k-htc`:** rare; skip.

### 3.2 Broadcom b43 (BCM4306/4311/4312/4318/4321/4322)
- Driver `b43` (LP-PHY for BCM4312). Debian's route is `firmware-b43-installer`, which **downloads Broadcom's
  proprietary driver at install time and extracts firmware**; Debian cannot ship it
  ([Debian wiki bcm43xx](https://wiki.debian.org/bcm43xx)). It lives in `contrib`, not `non-free-firmware`, and needs
  Internet. The same wiki assigns BCM4313 to brcmsmac and notes that the PCI id alone does not identify the chip.
- Greia is offline-first and our pool is `non-free-firmware` only: **these machines get no Wi-Fi from a clean install.**
- Practical outcomes: (1) document "use wired Ethernet or a USB Wi-Fi dongle with ath9k_htc/rtl8xxx/mt7601 that
  Debian packages"; (2) offer a parent-supervised path: with Ethernet up, the parent app runs the b43 firmware fetch
  (a LAB-proven recipe, not a bundled blob); (3) bundling the blob in our media is a **licensing decision for the
  owner** (D4). Do not do it by default.
- Because the hook already lists `b43` and `b43legacy`, nothing breaks when firmware is missing; the interface simply
  never appears. The UI must say so (Wi-Fi hardware found but no firmware) rather than show an empty list.

### 3.3 Graphics
- **Intel GMA 900/950/3150 (i915)**: fine, no firmware. Matches our `xserver-xorg-video-intel/vesa/fbdev` set.
  `xserver-xorg-video-intel` is the legacy DDX; modesetting DDX also works on i915 in bookworm (FROM-KNOWLEDGE; LAB which is smoother on 945).
- **GMA500 Poulsbo (Atom Z5xx: Dell Mini 9/10/1010, Sony Vaio P, some Fujitsu/Samsung/Lenovo)** and Cedarview
  (GMA3600/3650): driver `gma500_gfx` is mainline but has no 3D, spotty modesetting and suspend/resume faults; Cedarview
  has no usable open 3D. For a pygame/software-rendered Shell this is acceptable **only if** the KMS framebuffer or
  `fbdev`/`vesa` path gives the native mode. Expect wrong modes on 1024x600 and sleep failures. LAB, treat as POOR.
  (Did not find a stable Debian wiki page for gma500: [wiki.debian.org/GMA500 returned 404](https://wiki.debian.org/GMA500).)
- **ATI Radeon R100-R500, X1xxx**: radeon KMS, no firmware for R100-R500. **R600+ (HD2xxx and up)** and 2008+ ATI/AMD mobile
  chips need `firmware-amd-graphics` (radeon microcode); without it `radeon` fails and falls to fbdev/vesa.
  Put `firmware-amd-graphics` in the fallback set (about tens of MB: check size budget, 6.2).
- **NVIDIA GeForce Go (NV4x-G8x laptops)**: nouveau; older chips run without firmware, G8x/G9x PureVideo video decode only;
  newer (Fermi+) need `firmware-nvidia-graphics` (not in 2005-2010 laptops). 2D/fbdev is enough.
- **Intel 8xx/855/915 (Pentium M era)**: i915 fine; 855GM on very old Pentium M needs the `i915` driver with a DRM-quirk-free mode;
  low risk.

### 3.4 Ethernet
- r8169 (RTL8101E/8102E/8168/8111): needs `firmware-realtek` `rtl_nic/rtl8168*`/`rtl8105e-1.fw` etc. for some revisions. It **works without firmware but with reduced reliability** on some chips (dmesg warns). Include `firmware-realtek` in the pool.
- `atl1c`/`atl1e`/`atl2`/`sky2`/`tg3`/`e100`/`e1000e`: no firmware needed (tg3 on a few chips wants `firmware-misc-nonfree`).
- Wired Ethernet matters: it is the recovery route for Broadcom Wi-Fi (3.2).

### 3.5 Audio (FROM-KNOWLEDGE, LAB)
`snd_hda_intel` covers nearly all, with per-model quirks (`model=` parameter) on early Atom netbooks (Realtek ALC269/ALC268/ALC888, Conexant, IDT 92HD). Typical failures: no headphone auto-mute, silent after resume, mic not detected. Greia needs speaker output only; resume silence is the realistic bug.

### 3.6 Suspend/resume
- Documented: iwl3945 `-110` (our hook). Same Intel family 4965 and 5100 sometimes fail identically.
- Broadcom b43/b43legacy often fail after resume; ath5k can lose association; USB Wi-Fi dongles (rtl8187, ath9k_htc) usually recover but can reset.
- `gma500_gfx` panels may stay black after resume.
- Hook list is currently `iwl3945 iwl4965 b43 b43legacy brcmsmac ath5k`. See 5.2.

## 4. Display and boot quirks
- Screens: 800x480 (Eee 701/900-class), 1024x576 (HP Mini 110, Dell Mini 10), 1024x600 (reference), 1280x800/1366x768 (Aspire laptops, handled by the 2026-10-21 viewport fix). Verify Shell and a game at **1024x576 and 800x480** (LAB); 800x480 is below the contract floor.
- BIOS boot from USB: old netbook BIOSes often boot a stick only as **USB-HDD** or **USB-ZIP**, and may need "Hard Disk Drives" priority changed (Acer: F12 boot menu, F2 setup). Some Eee PCs boot USB only if the stick has the BIOS-visible active partition. Our live media must keep a legacy MBR/active partition (LAB on Acer, Eee, Dell Mini).
- 512 MB machines: installed core is fine; the live installer and squashfs/overlay RAM headroom is the limit. Record `MemAvailable` in the LAB log.
- 32-bit-only CPUs (N270/N280/Z5xx, Yonah): cannot run the amd64 line. 64-bit (N450 and later, Core 2): both lines work; steer to amd64 for post-2028 safety.
- Candidate kernel cmdline quirks (apply only on LAB evidence, never globally): `forcepae` (Pentium M on a PAE kernel; unneeded with 686), `nomodeset`/`video=` for gma500 and failing Radeon, `acpi_osi=Linux` or `acpi_backlight=vendor` for dead backlight (Acer/Dell), `i8042.nomux`/`i8042.reset` for stuck PS/2 touchpads, `pcie_aspm=off` for 3945/4965 resume or NIC drops, `snd_hda_intel.model=<quirk>` for individual audio faults, `usbcore.autosuspend=-1` for flaky USB Wi-Fi. Per-model entries belong in a data table consumed by the installer, not in global GRUB defaults.

## 5. Concrete Greia actions

### 5.1 Pool and fallback set
Force-include (even when isenkram/modinfo detection is incomplete), all `non-free-firmware`:

| Package | Why | Size note |
|---|---|---|
| `firmware-iwlwifi` | Intel 3945/4965/5100/6000 (already the Acer failure) | sizeable (tens of MB); keep |
| `firmware-realtek` | RTL81xx Wi-Fi + r8169 NIC | small |
| `firmware-atheros` | USB/AR3011 bluetooth, ath9k_htc dongles; AR5xxx/AR9285 PCI need none | small |
| `firmware-brcm80211` | BCM4313, BCM43224 (brcmsmac) | small-medium |
| `firmware-libertas` | Marvell 8xxx | small |
| `firmware-misc-nonfree` | **Ralink RT2800/3090 (Eee 901/1000H/1005, MSI Wind)**, tg3 on a few chips | medium |
| `firmware-amd-graphics` | Radeon R600+ laptops (2008-2012), also tolerable on amd64 line | large (tens of MB); include only if the 1,300 MiB budget allows after measurement, else include in the **installer pool only** and install on detect |
| `intel-microcode` / `amd64-microcode` | already handled by `X86MicrocodeResolver` | n/a |

Also add: `firmware-ipw2x00` if it is in `non-free-firmware`/`non-free` for bookworm (VERIFY: `apt-cache policy firmware-ipw2x00`; it
may be `non-free` only), `firmware-ti-connectivity` skip, `firmware-linux-free` (main) already base.
Not installable offline: `firmware-b43-installer`, `firmware-b43legacy-installer` (contrib + download), `bcmwl-kernel-source`/`broadcom-sta-dkms`
(contrib, DKMS + compile; reject for a child appliance: Activities and installs may not compile). Document this decision in the installer docs.

Implementation points: (a) add the fallback list as a named constant in `src/greia_installer/hardware_enablement.py`, applied when the resolver plan
is incomplete; (b) add the same names as forced candidates in `tools/build_hardware_support_pool_manifest.py` so the pool always contains them;
(c) record in the installer UI which firmware class is missing (b43) instead of a silent absence; (d) have a unit test per matrix row's expected
package (fixture inventories), using the repo's existing `InstallerHardwareEnablementPlanner` test seams.

### 5.2 Resume hook driver list
Current: `iwl3945 iwl4965 b43 b43legacy brcmsmac ath5k`. Add: `iwldvm` is not a PCI driver, so add the **PCI-bound** names
`iwlwifi` (covers 5100/5300/6000 on the DVM path), `ath9k` (AR9285 reports of lost association after resume, FROM-KNOWLEDGE/LAB),
`rt2800pci`, `rtl8192ce`, `rtl8180`/`rtl8187`, `ipw2200`, `ipw2100`. Because the hook only reloads when interface/station is gone,
longer lists are cheap and safe; keep the hook a no-op where none are loaded. Add one fixture per driver to the hook tests.
Also consider a fallback for non-Wi-Fi resume faults (Ethernet r8169 PHY down): out of scope until LAB shows it.

### 5.3 Profiles
- Keep `legacy-x86-i686*` on `linux-image-686` (non-PAE). Document that `acer-aspire-one-i386` (PAE) is optional.
- Add a `legacy-x86-i686` note: i586/Geode/VIA C3 not supported (baseline i686 + NOPL).
- Add an `i386 end-of-support` string sourced from `support_end_date` in the About and release notes.
- Keep `xserver-xorg-video-intel/vesa/fbdev`; consider adding `xserver-xorg-video-ati` and `xserver-xorg-video-nouveau` only if LAB shows
  the modesetting DDX does not cover Radeon/NVIDIA laptops (footprint cost, LAB first).

### 5.4 Docs
Add a `docs/` supported-hardware page describing the tiers (OK / needs firmware / needs vendor blob / best-effort) and the Broadcom guidance;
mirror it on the website via `site-ftp` only when the owner approves.

## 6. Footprint and legal checks
- Fallback firmware must fit the 1,300 MiB ceiling (AGENTS.md contract 6); measure `du` of the pool and the target before/after.
- Bundling any non-Debian-archive firmware is outside the current policy. `non-free-firmware` is enabled by Debian since the 12 installer; that remains our line.

## 7. Prioritised LAB checklist

P0 (before promising the i386 line):
1. Reference Acer Aspire One ZG5: confirm which Wi-Fi it has (`lspci -nn`), install from clean media, offline, confirm Wi-Fi, suspend/resume x3, audio, 1024x600 viewport, 512 MB/1 GB RAM headroom.
2. A PAE-less CPU (Eee PC 701/900 Celeron M or ThinkPad T4x Pentium M): boot the `legacy-x86-i686` media, confirm `grep -wc pae /proc/cpuinfo` = 0 and that the image still boots.
3. A Broadcom BCM4312 netbook (HP Mini 110 or Dell Mini 9): confirm there is **no Wi-Fi without firmware**, and that the UI says so; test Ethernet and a USB dongle as recovery.
4. An Intel 4965/5100 laptop (ThinkPad T61/X61, Dell D630): firmware from pool, resume behaviour, hook coverage.

P1:
5. Ralink RT2860/RT3090 (MSI Wind, Eee 901/1005): `firmware-misc-nonfree` suffices from the fallback set.
6. Atheros AR9285 (D250, NC10): confirm no firmware needed; resume.
7. GMA500 (Dell Mini 9/10): native mode, black screen after resume, `nomodeset`/`video=` outcomes.
8. Radeon R600+ laptop: with and without `firmware-amd-graphics`.
9. BIOS USB boot sequence on Acer, Eee, HP Mini, Dell Mini, ThinkPad T-series; record key and mode (USB-HDD/ZIP).
10. 800x480 (Eee 701) and 1024x576 (HP Mini 110, Dell Mini 10) rendering of Shell and three Activities.

P2:
11. RTL8187SE Wi-Fi driver availability in the bookworm kernel.
12. Touchpads (Synaptics, Elantech, ALPS) with libinput; tap-to-click default off still honoured.
13. SD/MMC readers on Ricoh/Realtek/TI.
14. HDA audio models on three netbook types; silent-after-resume cases.
15. Memory: 512 MB models, installer overlay headroom.

Record every test as one line in a LAB log: model, `lspci -nn`/`lsusb`, `dmesg | grep -i firmware`, kernel flavour, result.

## 8. Sources
- Debian 13 release notes, issues (i386): <https://www.debian.org/releases/trixie/release-notes/issues.en.html>; LWN: <https://lwn.net/Articles/1033741>
- Debian bookworm release notes, 5.1.13 i686 baseline: <https://www.debian.org/releases/bookworm/i386/release-notes/ch-information.en.html>
- Debian LTS: <https://wiki.debian.org/LTS>
- `linux-image-686`: <https://packages.debian.org/bookworm/linux-image-686>; `forcepae`: <https://git.linaro.org/plugins/gitiles/kernel/linux-linaro-stable.git/+/69f2366c9456d0ce784cf5aba87ee77eeadc1d5e>
- ath9k: <https://wiki.debian.org/ath9k>; Broadcom: <https://wiki.debian.org/bcm43xx>
