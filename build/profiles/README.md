# Pip OS image profiles

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

## Useful commands

```bash
python3 tools/build_profile.py validate acer-aspire-one-i386
python3 tools/build_profile.py package-sets acer-aspire-one-i386 --scope target
python3 tools/build_profile.py packages acer-aspire-one-i386 --scope target
python3 tools/build_profile.py manifest acer-aspire-one-i386 --scope target
python3 tools/build_profile.py check-phase0-builder acer-aspire-one-i386 --scope target
```

`PIP_RELEASE_BUILD=1` additionally requires `check-release` to pass. No boot-cover backend is release-safe at present; stock Plymouth remains development-only/provisional under ADR 0011.
