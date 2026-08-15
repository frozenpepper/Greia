# Greia Hardware Enablement — Implementation Review

**Date:** 2026-08-15  
**Decision owner:** ADR 0021  
**Evidence state:** SOURCE IMPLEMENTED / CURRENT TESTS AND PHYSICAL ACCEPTANCE NOT RUN

## Judgment

The current implementation is architecturally suitable for source/build verification. It replaces per-model driver thinking with Linux-owned driver binding plus Debian-owned firmware/provider metadata, while keeping Greia's final installed footprint machine-specific.

It is **not yet broad-hardware certified**. No current composed source gate, canonical support-pool build, VM install, or diverse physical machine matrix has been executed after this tranche.

## Implemented topology

```text
hardware
  -> Linux kernel / udev / kmod driver binding
  -> bounded Greia sysfs inventory
  -> bound-driver modinfo firmware declarations
     + isenkram missing-firmware signal
     + isenkram modalias advisory signal
     + x86 CPU microcode policy
  -> verified Debian firmware-provider map
  -> frozen offline installer repository
  -> fail-closed machine-specific target package plan
  -> read-only local APT install
  -> initramfs / GRUB regeneration
```

## Installer-media strategy

The installer media deliberately spends more storage than the installed target:

1. A broad frozen `.deb` repository is derived from Debian firmware Contents metadata plus x86 microcode candidates.
2. Dependency closure is resolved against the exact target squashfs's `dpkg` state.
3. Candidate packages are resolved independently to avoid one alternative/conflicting firmware provider poisoning a global solver transaction.
4. Every `.deb`, `Packages`, and `Packages.gz` is frozen by size and SHA-256.
5. The live root installs a **minimal broad firmware cover**: one deterministic preferred verified provider for each concrete firmware file. All verified alternatives remain in the pool.
6. The final target installs only the packages selected for the actual machine, plus frozen dependencies.

This avoids both bad extremes:

- a tiny installer that cannot bring up hardware because firmware is missing;
- an installed Greia image carrying every firmware package forever.

## Why target selection does not rely only on "missing firmware"

Once the live installer already contains broad firmware, a detector for currently missing firmware can correctly return nothing even though the final target would still need a firmware package.

The implementation therefore also uses the **actual bound kernel driver's `modinfo -F firmware` declarations** and resolves those firmware names/patterns through the frozen Debian provider map. This remains vendor-neutral and avoids Greia-authored PCI/USB mappings.

General `isenkram-lookup` remains advisory because it can recommend user-space hardware utilities. An advisory package can be promoted to automatic firmware only when the independently verified pool classifies that exact package as firmware.

## Trust and mutation boundaries

Automatic hardware enablement is fail-closed:

- incomplete inventory/resolution exposes no target package list;
- a required package absent from the frozen media makes the plan incomplete;
- support media suite/architecture must match the target image profile;
- pool verification occurs before erase and again immediately before use;
- symlinked/unmanifested/mutated payloads or indexes are rejected;
- target pool bind is read-only;
- target APT is given only the temporary local file repository for the transaction;
- package-removal plans are forbidden;
- arbitrary vendor installers/downloaders are forbidden;
- package names and completion state may enter the install record; raw modalias/sysfs/driver/serial inventory may not.

## Resource model

The broad compatibility payload lives on removable installer media and is compressed with the live filesystem. The canonical installer report records the pool package count and byte size. The final installed machine receives only the machine-specific package set.

The current pool has a hard 2 GiB uncompressed `.deb` bound and a bounded package/provider/index model. Actual Bookworm/Trixie pool sizes still need measurement; those measurements may justify tightening the bound substantially.

## Remaining risks / required evidence

1. **No composed source gate has run.** Mechanical/syntax/API errors remain possible.
2. **No canonical pool build has run.** Real Debian package/provider conflicts, package availability and actual byte cost remain unknown.
3. **No VM install has run.** The local APT transaction, read-only bind and cleanup order need real proof.
4. **No diverse physical matrix has run.** Broad compatibility remains a design goal, not an evidence claim.
5. **Kernel coverage remains separate from firmware coverage.** Very new/old hardware may require different kernel tracks or unsupported drivers.
6. **Current x86 Phase-0 boot architecture remains BIOS-oriented.** UEFI breadth is a separate platform compatibility tranche.
7. **Graphics/input/audio semantic capability probing still needs broader modern backends.** Package resolution alone is not proof that a Greia capability works.
8. **Post-install hotplug package enablement is intentionally not exposed yet.** That persistent privileged updater surface should be designed only after the one-shot installer path passes its gates.

## Required next sequence

1. Run `docs/testing/2026-08-15_HARDWARE_ENABLEMENT_SOURCE_ACCEPTANCE.md` exactly on current `main`.
2. Fix the first real source failure; do not weaken gates.
3. Build at least one Bookworm/i386 and one Trixie/amd64 installer in an owner-controlled Debian/Ubuntu environment.
4. Record pool package counts/bytes and inspect the frozen manifests.
5. Execute VM/QEMU installation from the produced media.
6. Only after source/build/VM PASS, start a deliberately diverse physical matrix covering old and new x86 machines and representative USB/Bluetooth peripherals.
7. Then design installed-system first-boot/hotplug enablement and parent diagnostics using the already verified resolver/pool contracts rather than adding a second hardware system.
