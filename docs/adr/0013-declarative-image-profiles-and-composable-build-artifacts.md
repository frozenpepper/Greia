# ADR 0013 — Declarative Image Profiles and Composable Build Artifacts

Status: accepted for Phase 0 source; Linux image evidence pending  
Date: 2026-08-07

## Context

ADR 0012 established that Greia OS is one platform contract delivered through multiple build profiles. A profile determines what an image contains; runtime capability probing determines what the current machine can actually do. Runtime adapters are platform-owned and may differ by image family, while Activities remain architecture/runtime-independent above their adapter.

The pre-ADR-0012 Phase 0 builder did not fully embody those rules:

- build profiles were executable `.env` shell fragments;
- most target packages lived in one universal `core.txt` list;
- Python/Pygame, Xorg, networking, removable-media support, Bubblewrap, GRUB, Plymouth, and parent recovery dependencies were not represented as different architectural concerns;
- runtime inclusion was implicit rather than declared by profile;
- disk limits were hardcoded in the builder rather than profile/resource-class declarations;
- installer media copied the executable profile fragment as `payload/profile.env`;
- produced images recorded resolved Debian packages, but not a machine-readable declaration of the platform family, compatibility class, selected adapters, and runtime families that the image intended to contain;
- x86 BIOS assumptions were embedded in builder code without a typed adapter boundary explaining that ARM64 needs a different image/boot implementation rather than an altered Activity ecosystem.

These were acceptable prototype shortcuts before the architecture constitution, but retaining them would make future Web/ARM/modern profiles drift into ad-hoc forks.

## Decision

### 1. Build profiles are declarative TOML

`build/profiles/*.toml` is the only accepted profile source format. Builders never source a profile file.

`tools/build_profile.py` owns typed parsing and validation for profile identity/certification state, platform family, C0–C3 compatibility class, Debian base and CPU architecture, image layout, installed/installer boot adapters, boot-cover backend, display adapter, enabled Activity runtime families, composable package sets, and profile-specific resource limits.

The helper emits shell-quoted normalized assignments only after validation; profile data itself is never executed.

### 2. Package composition follows architectural concerns

The old universal target/installer lists are replaced by `build/package-sets/`.

Current sets cover platform base, Pygame platform shell, Activity namespace sandbox, networking, removable media, parent recovery, boot adapter, boot-cover backend, display adapter, Python Activity runtime, and graphical installer base.

The resolver adds adapter/runtime package sets from the selected profile and de-duplicates shared packages. Phase 0's platform shell and Python Activity adapter deliberately share Python/Pygame packages, so making the runtime family explicit does not imply a second interpreter or environment.

An Activity runtime family cannot bring per-Activity dependencies. A new family such as Web receives one centrally owned runtime package set after its own measurement/ADR.

### 3. Profiles declare runtimes independently from display/boot implementation

All current Phase 0 profiles declare:

```toml
[runtimes]
enabled = ["python"]
```

This is a build-content declaration, not an Activity taxonomy. A future profile may add `web` without changing profile IDs, saves, progression, package semantics, or parent-management contracts above the runtime adapter.

The project validator confirms that every bundled Activity's explicit `runtime.type` is present in every current Phase 0 image profile.

### 4. Build profile is not a hardware capability report

Every produced target/live image receives `/etc/greia-os/image-profile.json`. The installer also carries the target declaration at `/etc/greia-os/target-image-profile.json` and on removable media as `payload/target-image-profile.json`.

The JSON records declared build composition including platform family, compatibility class, CPU architecture/base, boot/display adapters, enabled runtime families, package-set composition, and resource policy.

It explicitly states that hardware capabilities are runtime-probed. The manifest must not be used to claim that acceleration, audio, Wi-Fi, a resolution, or another device actually works merely because a profile intended to support it.

Resolved package/kernel/display manifests remain the authority for exactly what Debian packages were installed in a particular build.

### 5. Installer media carries declarative metadata only

`payload/profile.env` is removed. The graphical installer USB carries JSON image-profile declarations instead of executable profile configuration.

This prevents profile selection metadata from becoming a shell execution seam and makes the build artifact inspectable by future parent/recovery tooling without understanding Bash syntax.

### 6. Resource limits are profile data

The builder no longer hardcodes the preferred/hard installed-core values. Each profile declares them and the builder enforces them.

All existing Phase 0 profiles retain the current policy:

- preferred core: 800 MiB;
- required: strictly below 1,000 MiB;
- architecture-review threshold: 1,250 MiB.

This preserves the Acer C0 contract while allowing a future higher-class image to use a different measured budget only through an explicit profile/architecture decision rather than weakening the Acer gate globally.

### 7. ARM64 is accepted by the profile schema but rejected by the Phase 0 x86 builder

The typed model recognizes `arm64`. The current builder explicitly rejects it because only the BIOS x86 image/boot adapter exists.

This is intentional. ARM is first-class at the architecture seam: adding a Raspberry Pi-class image requires a board/image boot adapter beneath the same profile schema, not pretending GRUB-PC/MBR logic is portable or creating an ARM-specific Activity ecosystem.

ADR 0014 subsequently makes Raspberry Pi 400 and Raspberry Pi 500 explicit reference targets; that strengthens the requirement for real ARM adapters without making the old x86 builder falsely portable.

### 8. Release eligibility belongs to the adapter registry

`GREIA_RELEASE_BUILD=1` asks the typed build-profile tool whether the selected boot-cover backend is registered as release-safe.

The registry currently contains no release-safe cover backend. `stock-plymouth-provisional` remains available for development evidence but cannot pass release promotion.

A future cover backend becomes release eligible only after acceptance evidence and adapter registration are deliberately added; changing a profile string alone cannot bypass the gate.

## Consequences

### Positive

- Image composition mirrors the platform layer/runtime/profile architecture.
- Future runtime additions can target selected profiles without universal C0 cost.
- Future ARM/UEFI/display implementations have explicit seams instead of hidden x86 assumptions.
- Build metadata is machine-readable and non-executable.
- Declared build composition and observed runtime capabilities cannot be accidentally conflated.
- Resource policy can vary by certified profile without weakening the Acer floor.
- Package dependency cost can be attributed to architectural subsystems during footprint review.

### Costs

- Build profile changes require typed schema/package-set updates rather than arbitrary shell variables.
- Adding a new runtime/display/boot adapter requires registration and package-set implementation.
- Existing local scripts that directly read old `*.env` profiles must be updated.
- Source tests cannot prove that the resolver produces a bootable image; Linux/QEMU evidence remains mandatory.

## Rejected alternatives

### Keep `.env` profiles and add more variables

Rejected because the profile remains executable configuration, validation stays weak, and external tools must understand shell semantics.

### One universal package list plus comments

Rejected because comments do not create a selectable runtime/adapter boundary and future optional runtimes would still bloat every image.

### Add an ARM profile immediately using the existing builder

Rejected because the current partition/GRUB/live-media implementation is x86 BIOS-specific. A fake profile would create false support claims.

### Treat profile declarations as hardware capability truth

Rejected because driver/package presence does not prove actual graphics/input/audio/network behavior. Certification remains evidence-based.

## Evidence still required

This ADR is source architecture only. Before claiming the image path accepted:

- run `make verify` on the clean tree;
- validate and inspect the exact selected TOML profile/package resolution on the Linux build host;
- build exactly the Acer inventory-selected profile;
- verify target and live package manifests plus both JSON image-profile manifests;
- verify target core remains under its profile hard limit;
- run the existing 768 MiB QEMU installer/installed-target acceptance;
- verify Activity sandbox/display/audio/media behavior;
- retain the known provisional boot-cover blocker demonstration;
- do not write the Acer internal disk until the existing blockers are resolved.

> **Greia note:** references in the historical v0.12 evidence path to Xorg describe the temporary implementation baseline. ADR 0014 supersedes X11 as a target architecture; future image profiles must move toward the direct Greia graphics/session adapter after it is implemented and proven.