# Greia OS image profiles

Image profiles are **declarative TOML data**, not shell fragments. They describe what an OS image contains; they do not claim what hardware capabilities a running machine actually exposes.

ADR 0012 distinguishes these concepts deliberately:

- **build profile** — selected OS contents/adapters/resource policy;
- **runtime capability probe** — what display/audio/input/network/device features actually work on the current machine.

`tools/build_profile.py` is the authoritative Phase 0 parser, validator, package-set resolver, and image-profile manifest generator.

## Profile sections

- `[profile]`: stable profile ID, certification state, description;
- `[platform]`: platform family and C0–C3 compatibility/resource class;
- `[base]`: Debian suite, CPU architecture, mirrors, support deadline, kernel meta-package;
- `[image]`: image layout, allocation size, hostname;
- `[boot]`: installed-system boot adapter, installer boot adapter, graphical cover backend;
- `[display]`: selected display adapter plus profile-specific video packages;
- `[runtimes]`: platform-owned Activity runtime families included in the target image;
- `[packages]`: general target/installer package sets and narrowly justified extra packages;
- `[resources]`: profile-specific preferred/hard/architecture-review installed-core limits.

Adapter and runtime package sets are composed by `tools/build_profile.py`; profiles do not duplicate those implementation mappings.

## Current Phase 0 implementation boundary

The profile schema recognizes `arm64` as an architecture, but the current image builders intentionally implement only the BIOS x86 path (`i386`/`amd64`, GRUB PC, one ext4 root, Xorg). An ARM profile must not be faked by pushing ARM values through x86 builder logic. A board-specific boot/image adapter is required first.

Likewise, the architecture recognizes a future `web` Activity runtime family, but no Web engine/package set is implemented yet. Declaring `web` therefore fails closed during package resolution until a measured platform-owned Web adapter exists.

## Acer Aspire One candidates

The repository deliberately carries three Acer hardware candidates until physical inventory/boot evidence selects the exact reference profile:

```text
acer-aspire-one-i386
acer-aspire-one-i386-nonpae
acer-aspire-one-amd64
```

Each has a matching **development-only remote-control variant**:

```text
acer-aspire-one-i386-dev
acer-aspire-one-i386-nonpae-dev
acer-aspire-one-amd64-dev
```

The developer variants preserve the matching architecture, kernel, display packages, C0 resource policy and image layout. They add the explicit `developer-remote` package set, use hostname `greia-dev`, and remain `experimental`; they are never release profiles.

Build the developer variant that corresponds to the physical Acer profile actually accepted by evidence:

```bash
sudo bash build/build-developer-image.sh out acer-aspire-one-i386-dev
```

The default developer wrapper profile remains `modern-amd64-dev` for compatibility when no second argument is supplied.

Remote-control details and Acer acceptance are documented in:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md
```

## Useful commands

```bash
python3 tools/build_profile.py validate acer-aspire-one-i386
python3 tools/build_profile.py package-sets acer-aspire-one-i386 --scope target
python3 tools/build_profile.py packages acer-aspire-one-i386 --scope target
python3 tools/build_profile.py manifest acer-aspire-one-i386 --scope target
python3 tools/build_profile.py check-phase0-builder acer-aspire-one-i386 --scope target
```

`PIP_RELEASE_BUILD=1` additionally requires `check-release` to pass. No boot-cover backend is release-safe at present; the Greia early-framebuffer cover (`greia-early-framebuffer-v1`) is development-only/provisional until its physical acceptance gate passes.