# Cross-Hardware Robustness Plan

**Status:** active, sequenced, not yet implemented
**Created:** 2026-09-28
**Owner decision:** recorded in this document; approved scope is Tranche A →
Acer end-to-end acceptance → Tranche U → Tranche B → Tranche L.

This plan exists because the reference Acer kept producing defects that were
*classes* of problem, not Acer problems. Every instance found in the
2026-09-27/28 Acer tranche reduces to one of ten classes below, and each class
has known instances on other hardware. This plan owns the sequencing and closure
criteria for removing those classes. It does **not** supersede
`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`,
which remains the active blocking platform plan (T3-P OPEN/BLOCKING).

Root-cause evidence for every instance named here lives in
`docs/engineering/boot/INSTALLATION_ISSUES_LOG.md` §§1–16.

---

## 1. The ten defect classes

| # | Class | Statement | Acer instances |
|---|---|---|---|
| C1 | Undeclared resource ownership | Two authorities are permitted to claim one resource, and nothing states which wins. | §13 `systemd-networkd` vs `iwd` on `wlan0`; §7/§8 X vs application over the controlling VT; stdin ownership |
| C2 | Environment-metric assumption | Geometry or sizing is computed against the development host rather than measured at runtime. | §15 Pointer page: fonts taller on the Acer, layout constants assumed otherwise |
| C3 | Latched or unbounded failure | A transient condition becomes a terminal user-visible state, or a permanent one becomes an infinite loop. | §14 empty scan latched as final; §16 helper respawned 2754 times per boot |
| C4 | Failure masked as a benign state | An error and an absence are rendered identically, so the real cause is invisible. | §14 "No networks found" shown for an actual scan error |
| C5 | Silent under-provisioning | Build and install report success, but the target cannot actually use the hardware that is present. | §2 installed system grey-screened and rebooted; still latent for non-SATA roots (see §4 A1) |
| C6 | Advertised capability ≠ real capability | The UI offers a control the hardware cannot honour. | tap-to-click row offered for a touchpad exposing no tapping property; "disable while typing" ignores keyboard pairing |
| C7 | Runtime mutation lost on re-enumeration | State written at runtime silently reverts when the device re-enumerates. | not yet observed; risk is documented in libinput ("changes performed by xinput do not persist across device hotplugs") |
| C8 | Identity and name instability | Code or configuration assumes a name that is not stable. | iwd device object path moved `/net/connman/iwd/0/4` → `/0/5` across an iwd restart |
| C9 | Probe identity ≠ service identity | A capability is verified under a different identity than the service actually runs as. | §13 `su nobody` reports "Access denied" although the service (with `netdev`) reaches the bus |
| C10 | Single-machine evidence | Source-closed is treated as proven. | §14 shipped as "fixed" while still broken on the machine |

---

## 2. Structural finding: the declared hardware targets have no profiles

An inventory of `build/profiles/*.toml` on 2026-09-28 established that the
schema anticipates hardware the builder cannot yet express:

```text
profiles present:            11
architectures:               i386 (7), amd64 (4), arm64 (0)
boot paths:                  legacy BIOS + Syslinux (11), UEFI (0)
platform.board:              "none" (11)
```

`arm64`, `pi-400-v1`, `pi-500-v1`, `pi-mbr-tryboot-ab-v1`, `pi-tryboot-ab-v1`,
`pi-live-usb-v1` and `modern-gpt-ab-v1` all exist in the schema
(`tools/build_profile.py`, `src/greia_platform/persistent_layout.py`,
`src/greia_installer/layout.py`) but **no profile exercises any of them**.
Consequence: no UEFI-only machine can boot a Greia installer at all, and the
first-class ARM references named in `AGENTS.md` cannot be built.

This is the largest cross-hardware gap, and it is why Tranche U exists.

---

## 3. Sequenced scope

### Tranche A — generalise the actively-wrong Acer shapes

Small, high-value, no architecture change. Ordered as the first implementation
tranche because each item removes a *live* wrong-behaviour risk rather than a
hypothetical one.

| Item | Class | Change | Closure criterion |
|---|---|---|---|
| **A1** | C5 | Replace the fixed `("ahci", "libata", "sd_mod")` in `build/*/etc/initramfs-tools/hooks/greia-storage-modules` **and** in `InstallerEngine._verify_installed_initramfs_storage` with a module set derived from the target device's real transport/controller, read from sysfs inside the mounted target chroot. Today the guard passes *vacuously* on NVMe, SAS/RAID, Intel RST/VMD, USB-attached and MMC roots because `modinfo` finds no `ahci` and the check is skipped. | Guard rejects a target whose root transport module is absent, and accepts one whose is present, for at least `nvme` and `sata` cases. |
| **A2** | C2 | Size/resample boot artwork to the actual panel instead of shipping a fixed `P6 1024 600` PPM. | PPM no longer carries a single hardcoded geometry; a non-reference panel produces a valid scaled PPM. |
| **A3** | C6 | Gate "disable while typing" on touchpad↔keyboard pairing, not merely on the property existing. libinput pairs the internal touchpad only with the internal keyboard, so an external keyboard, remote or gamepad will not trigger it. | The installer does not offer a toggle that cannot take effect for the current input inventory. |
| **A4** | C7 | Re-apply pointer property state on device re-enumeration, since runtime `xinput` writes do not survive hotplug. | A re-enumerated pointer retains its configured properties. |

### Acer end-to-end acceptance — gating, not a tranche

**The single highest-uncertainty path in the project.** The installer has been
verified extensively; the *installed* system has never been exercised. The
required run: install to the Acer internal disk, remove the USB, boot from the
internal disk, reach the launcher, exercise input, launch an Activity, return,
and confirm network and developer SSH. C5 is precisely the class that bites at
first boot, so this must produce real evidence before breadth is bought.

Deliberately sequenced **before** Tranche U, against the plan's original
ordering, because a critical-path defect found here would cost more than every
other item here combined. Owner approved this re-sequencing on 2026-09-28.

### Tranche U — UEFI

Approved for implementation, not merely recording.

**The amd64 path is the real deliverable; IA32 is a legacy-niche follow-on.**
AlmaLinux dropped IA32 UEFI outright ("32bit uefi installations are not
supported") and Fedora deprecated legacy BIOS on x86_64. The surviving IA32 use
case is 2013–2016 Bay Trail/Silvermont tablets with a 64-bit CPU but 32-bit-only
firmware, which exist only because community `bootia32-efi` shims serve them.

1. New `build/package-sets/boot-grub-efi-amd64.txt`; wire `grub-efi-amd64-bin`
   into the `modern-amd64*` boot package sets.
2. Live media: GPT + ESP + `\EFI\BOOT\BOOTX64.EFI` alongside the existing proven
   Syslinux MBR path, so one stick serves BIOS and UEFI. **The Acer Syslinux
   path must not be disturbed** — it is postmortem-proven and is the reason the
   reference machine boots at all.
3. Installed target: activate the already-scaffolded `modern-gpt-ab-v1` layout
   adapter (the schema already permits the `esp` and `bios_grub` flags and the
   `gpt` label type) and add the `x86_64-efi` install leg.
4. Follow-on: a `grub-mkimage`-built `BOOTIA32.EFI` for IA32 firmware. Cheap
   once the ESP plumbing exists; not a Phase-0 gate.
5. Verification: QEMU/OVMF, via the GRUB path. Known caveat to state honestly in
   the evidence: UEFI Syslinux is recorded as unreliable under QEMU/OVMF, so
   UEFI evidence must come from GRUB and must be labelled as emulator evidence,
   not physical acceptance.

### Tranche B — synthetic capability matrix

The only mechanism that prevents "works on the Acer, breaks elsewhere" without
buying a second machine: **make hardware variation a test input.**

A table of synthetic device inventories — NVMe root, SAS/RAID root,
USB-attached root, Intel RST/VMD root, MMC root; `ath5k`/`ath9k`/`brcmfmac`/
`rtw88` Wi-Fi; trackpoint + touchpad; no-tap touchpad; external-keyboard-only;
1280×800, 1366×768 and HiDPI panels — driven through the existing probe,
planner and gate code. Each entry asserts the same invariants the Acer proved by
accident, now as a matrix.

### Tranche L — advisory lint for hardware-shaped assumptions

Owner decision: **advisory, report only, does not fail the build.**

Scan for hardcoded device names, fixed pixel dimensions, and fixed module lists
outside declared allowlists. Seeded from what manual review has already found:
the fixed 1024×600 PPM, the storage-module triple, the `POINTER_*` layout
constants, and two stale Pip-era identifiers (`"Missing Pip root filesystem
UUID"` in `10_greia_appliance`, and `pip-runtime-audit-*` bundles in
`greia-collect-runtime-audit`).

---

## 4. Known-good findings that must NOT be "fixed"

Recorded so a later pass does not re-open correct code. Both were checked
directly against the source during this analysis:

- `src/greia_platform/hal_legacy_x.py` resolves XInput properties **by name**
  (`libinput Tapping Enabled`, etc.), not by numeric atom ID. Atom IDs are
  device-specific in practice (275 on one real touchpad, 304 on another); names
  are stable. This is already portable — leave it alone.
- `REFERENCE_WIDTH`/`REFERENCE_HEIGHT` in `activity_ui.py` and
  `activity_viewport.py` are used as scale **denominators** and defaults
  (`min(1.7, width / REFERENCE_WIDTH, ...)`), not as hard layout dependencies.
  This is the intended responsive design — leave it alone.

---

## 5. Researched cross-hardware analogues

Sources consulted 2026-09-28. Recorded because each is a concrete instance of a
class above, not a generic concern.

| Class | Finding |
|---|---|
| C5 | Intel RST/RAID vs AHCI controller mode is the most common cause of "installed system drops to an initramfs shell after a kernel/initramfs update". The storage-module set must follow the actual controller, not a fixed triple. |
| C1 / C8 | iwd creates and destroys the wireless interfaces it manages, which "can interfere with udevd, which may attempt to rename the interface". Greia matches `wl* wlan* wlp* wlx*`, which covers current names, but the iwd **device object path is not stable** (observed incrementing `/0/4` → `/0/5`). `WifiSetupController._station_path` discovers it dynamically and is already correct. |
| C1 | Rootless Xorg requires its VT to be the **foreground** VT with an **active logind session**; it "will fail to claim the VT's TTY" otherwise, and `xorg-xinit` is structurally unable to start X on a different TTY under logind. GDM's own workaround was to jump the VT up front. Seat layout and `NAutoVTs`/`ReserveVT` changes alter whether a session reads as active. |
| C7 | libinput: "Changes performed by `xinput` do not persist across device hotplugs." |
| C6 | libinput pairs touchpad and keyboard for disable-while-typing; "typing on an external keyboard will thus not disable the touchpad". Tapping is also forced on for devices with no physical buttons and cannot be changed by API. |
| Boot | Some BIOSes hang if the boot partition is not FAT16; "certain motherboard manufacturers have less compatibility for booting from USB devices than others"; Syslinux is particular about where `.c32` modules live (Greia uses a `boot/syslinux/` subdirectory the Acer accepts). Some flash devices are not firmware-bootable or are USB 1.0/2.0. |
| C5 / boot | UEFI requires ESP + `BOOTX64.EFI`; the firmware fallback path needs no NVRAM registration for removable media, but the **installed** target needs `grub-install --target=x86_64-efi` plus registration. |
| Scope | Fedora deprecated legacy BIOS for new x86_64 installations; the direction of travel is UEFI-only. |

---

## 6. Closure criteria for this plan

1. A1–A4 each carry a regression test verified to fail against the previous
   behaviour.
2. The Acer end-to-end acceptance has produced real hardware evidence:
   installed to internal disk, booted without the USB, launcher reached, an
   Activity launched and returned from, input and network confirmed.
3. Tranche U ships a UEFI-capable live medium and a UEFI-capable installed
   target for amd64, with evidence labelled as emulator evidence, and the Acer
   BIOS/Syslinux path still proven intact.
4. Tranche B's matrix exercises every root transport and pointer/display shape
   named in §3.
5. Tranche L reports without failing the build, and its current findings are
   either fixed or recorded as accepted.

No tranche in this plan may be marked complete on source-closed evidence alone
where physical hardware is the claim (C10). Evidence labels follow `AGENTS.md`.
