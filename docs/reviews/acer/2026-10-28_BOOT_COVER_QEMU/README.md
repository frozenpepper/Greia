# Boot-cover QEMU visual review — 2026-10-28

Evidence class: **SIMULATOR VISUAL REVIEW (QEMU)**. Not physical hardware.

Artifact: installer `b81279afe4c8d72bb458670efda95c6a422deddbceef69051a5e6da309c2bd80`
(runtime source `8bac176bd3d3b562fcf6785cdf663aecf0dcceec`), installed A/B target
from `/var/tmp/greia-boot-cover-acceptance-final/`.

| Image | Observation |
|---|---|
| `01-installer-cover.png` | Installer reaches the Greia-owned white frame with the logo after legacy firmware handoff; no Linux console text. |
| `02-installed-cover.png` | Installed A/B target: early framebuffer cover paints the same artwork after GRUB. |
| `03-installed-launcher.png` | Launcher continues the artwork into the first-child setup; no console text. |

QEMU 8.2.2/KVM, i386, 1024 MiB, one vCPU, snapshot-backed media. The full
acceptance record is `docs/release/2026-10-28_BOOT_COVER_ACCEPTANCE.md`.
Physical Acer review remains outstanding.
