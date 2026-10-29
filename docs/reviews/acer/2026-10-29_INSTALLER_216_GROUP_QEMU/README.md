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
