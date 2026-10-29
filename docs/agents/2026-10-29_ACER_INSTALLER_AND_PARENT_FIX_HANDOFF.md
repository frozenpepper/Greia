# Acer installer settings and Parent startup: fix handoff

**2026-10-29.** The owner requests that the next installer build fix the
installed system. Do not build, run VMs or emulators on the owner's Mac.
The existing Linux installer USB is running on the Acer with SSH enabled;
the installed disk was inspected read-only. Follow `AGENTS.md` and the lifecycle
plan; no physical reinstall or target-disk writes are authorized by this handoff.

## Findings from the actual Acer

- Installed release: `greia-acceptance-fixture-0.13.1-preview.1`, A/B slot A,
  profile `acer-aspire-one-i386-ab`.
- **Parent app fails before startup:** the actual installed
  `/usr/share/greia-parent-app` is `root:root 0700`. The service runs as
  `greiapanel` and its required `ExecStartPre` integrity check cannot traverse
  it. The Parent credential file was never created. As root, the same pinned
  client integrity check passes; as the real Parent UID/GID it fails reporting
  the runtime files missing. On the Acer, a copy in `/run` with only the root
  directory changed to `0755` passed the same check as the Parent identity.
  Instantiating the installed Parent application against a separate copy of the
  actual profile/settings state also succeeded. The real installed disk was not
  changed, and this does not prove a complete systemd boot/login.
- **Italian, keyboard and other installer settings were dropped:** actual
  PERSIST has neither `device-settings/language.json` nor `settings.json`, and
  slot A has no installer record. Reading the installed stores as the child
  UID returns English and the US keyboard with hardware defaults. The old A/B
  executor accepted but discarded the validated installer locale and settings.
- **Installer Wi-Fi was dropped:** actual PERSIST `network-state` has no saved
  `.psk` or `.open` profile. The old A/B service explicitly skipped carry-over.
- The boot configuration has a hidden GRUB menu with `timeout=0`. The owner
  eventually reached `grub>`; do not claim it is categorically inaccessible.
  The owner also observed a vertically squeezed splash after trying Shift; its
  cause remains unproven. The actual boot theme uses a 1024×600 image with
  `desktop-image-scale-method: padding` and `gfxmode=auto`.
- The installed journal is volatile; the preceding reboot removed the old
  Parent service journal. Do not invent the missing systemd log.

## Repository work and next steps

1. The candidate source fix in this commit addresses the Parent mode defect:
   `tools/update_parent_client_pin.py` and `tools/stage_parent_app.py` create
   traversable static-client directories even under `umask 077`;
   `build/lib/compose.sh` normalizes the installed Parent client to directory
   mode `0755` and file mode `0644`; `build/lib/verify-composed-root.sh` rejects
   unreadable Parent runtime paths. Review and retain these checks. The pinning
   tool's `mkdtemp()` previously made the root `0700`; Git does not track
   directory permissions, and `rsync -a` preserved the build checkout mode.
2. A/B locale, hardware/keyboard and Wi-Fi carry-over source fixes are already
   on `main` (`275b8ddb0`, tested further by `8eb57d5ea`). Preserve the
   `device-settings` and `network-state` PERSIST hand-off and first-boot
   ownership. Wi-Fi copy is best-effort. The live-installer SSH toggle is
   implemented by `7070a6c65`; preserve it and the owner's `greia` / `greia`
   live-installer login.
3. Build a **new A/B release bundle containing the corrected installed Parent
   client**, then build the installer with that new bundle and current
   installer source. Reusing the old `2572bf08…` release bundle would retain
   the broken Parent directory even if the installer itself is newer. No build
   on the owner's Mac. Inspect the actual composed image and live installer,
   not just the repository checkout: verify the Parent client is readable as
   `greiapanel`, and the pinned integrity check passes as that identity.
4. On a disposable Linux installation, exercise the real interactive installer
   using Italian, an Italian keyboard, non-default hardware preferences, and a
   Wi-Fi profile. Boot the installed system and verify effective language,
   keyboard/application settings and network persistence, then verify the
   on-device Parent panel accepts `greia` and the Parent service starts. Also
   test the installer SSH toggle and an actual `greia` / `greia` SSH login.
   Use the current lifecycle acceptance route and accurately report any
   unexecuted Wi-Fi hardware, GUI, physical Acer, or rollback cases.
5. Separately diagnose the owner-observed splash aspect ratio and the recovery
   menu on actual hardware when authorized; do not assert the Shift issue is
   solved by source-only checks. Do not bypass the Parent integrity check or
   silently weaken disk, session, A/B or update safety. Record evidence in the
   lifecycle plan and `HANDOVER.md`, then commit coherent work to `main`.

**Checks in this session:** 160 focused tests passed for Parent pinning,
staging, image contracts, Parent panel, installer A/B settings, Wi-Fi carry-over
and installer SSH. The positive/negative Parent permission test above ran on
the physical Acer's live installer using copies in `/run`; it is not an
installed boot acceptance. The existing A/B bundle and Acer disk remain
unchanged.
