# Corrected installer 216/GROUP QEMU acceptance

Evidence class: **SIMULATOR VISUAL REVIEW (QEMU)**, not physical hardware
acceptance. Source `4d2b65f78`; installer SHA-256
`d12568abd9c60a6d23f75b7afe0204f53bf5567ff37ae95bf799fd91b7b0cabd`
(2,270,167,040 bytes).

- `installer-language-screen.png` — the actual new image booted under
  QEMU 8.2.2/KVM, i386, `-cpu n270`, 768 MiB. It reached the interactive
  installer language screen. The image was attached with `snapshot=on`; no
  media was written.
- `service-status-serial.txt` — serial output from a disposable
  observation-only clone of the same image (only a test unit appended; the
  shipped `greia-installer.service` and its group database were unchanged).
  It records `systemctl is-active` = `active`, `is-enabled` = `enabled`,
  `ExecStartPre` success, and the running xinit/installer-client cgroup.

The standalone image boot screenshot and the observation-clone screenshot
were byte-identical (`28b9ce7d…`), confirming the clone showed the same
interactive screen. Physical Acer boot remains the next required step.

## Later rebuild (2026-10-29)

Image `b853330f624d816077c1149aa715e03aa2886e3571bbb834bb3e868d6072a436`
(2,270,167,040 bytes, source `9dd3625fb`) adds the USB failure-logging
changes. `installer-language-screen-r2.png` is the same QEMU default-service
boot evidence for that image; its screenshot hash is identical to the first
image's (`28b9ce7d…`). The actual live squashfs also contains
`opt/greia-os/src/greia_installer/install_diagnostics.py`.

## RAM-scratch rebuild (2026-10-29)

Installer `7869b6b59e973ecd016facc3035ad29b7219a65efac394b26094ed32d447daae`
adds the `initramfs-tools` ENOSPC fix. Its default installer service reached
the same interactive language screen; the captured framebuffer is
byte-identical to `installer-language-screen.png` (`28b9ce7d…`).
