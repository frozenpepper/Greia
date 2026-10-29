# Recovered Acer installer failure log

Evidence class: **physical Acer installer USB log**, copied read-only from
`GREIA_EFI/greia-logs/last-install-failure.log`.

- `last-install-failure.txt` — raw installer log. The failing package is
  `initramfs-tools`; its postinst ran `update-initramfs`, and `zstd` failed
  with `No space left on device` while writing
  `/boot/initrd.img-6.1.0-54-686-pae`. The earlier `intel-microcode`,
  `firmware-misc-nonfree` and `firmware-realtek` installations succeeded.
- Analysis and the RAM-scratch fix:
  [2026-10-29_ACER_USB_INSTALL_ENOSPC_INITRAMFS.md](../../2026-10-29_ACER_USB_INSTALL_ENOSPC_INITRAMFS.md).

The local reproduction used the exact release bundle payload and a 1,664 MiB
SYSTEM_A slot. Before the fix it produced the same ENOSPC; after the fix the
same package install and initramfs generation completed with a 42 MiB initrd.
