# Changelog

Greia has no supported ordinary-family release yet. Versions before
`0.13.1-preview.1` are development snapshots and are not maintained upgrade
targets; reinstall a current development image rather than migrating an old
one.

## 0.13.1-preview.1 — 2026-10-28 (technical preview candidate)

- Made the A/B boot-control menu use the canonical Greia GRUB theme and logo,
  and included common early framebuffer drivers so the branded cover paints on
  the reference Acer and on disposable QEMU test displays.
- Fixed release boot argument ordering so `quiet` cannot re-enable kernel
  console output after `loglevel=0`.
- Pinned the Greia Parents client to the tested `fd57c29` revision, including
  the current Wi-Fi state display and refresh-on-device-view behaviour.
- Repaired the maintained source verification baseline: Foresta waiver
  receipts, MBR adapter diagnostics, ARM64 builder-refusal expectations,
  optional voice-provider skips, and the `morbidi_mostriciattoli` first-frame
  budget on the Linux verification host.
- Added the macOS System Voice audio inventory and corrected the public
  licensing notice. This is an active public-release blocker: 627 committed
  recordings use macOS `say` voices and require replacement/permission before
  public redistribution.
- Added `PRIVACY.md`, this changelog and a concrete technical-preview release
  record.

## 0.13.0-phase0-dev — earlier development snapshots

Installed i386 QEMU A/B update, rollback, interrupted-write recovery and
lightweight Python/Activity/combined application updates passed. See
`2026-10-27_UPDATE_RELEASE_ACCEPTANCE_RESULT.md` (archived; see git history). No public
installer was released.
