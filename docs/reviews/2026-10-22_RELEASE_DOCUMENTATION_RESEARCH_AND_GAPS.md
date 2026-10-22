# Release documentation audit — 2026-10-22

**Scope:** researched, source-aligned practical guides for families, image builders, Activity authors and their coding agents. **Evidence: source/document review and link/command inspection only. No new image, installer, GUI, Windows/Mac or physical-device test was performed for this audit.**

## What was checked before writing

- Root authority: `AGENTS.md`, `SETUP.md`, `docs/DOCUMENTATION.md`, `HANDOVER.md`, `README.md`.
- Install/source: `docs/product/INSTALLER_EXPERIENCE.md`, `docs/product/FIRST_BOOT_PROFILE_SETUP.md`, `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md`, `tools/build-development-installer.sh`, `tools/build-and-flash-development-usb.sh`, `build/build-installer-image.sh`, `tools/greia_release.py`, `build/profiles/README.md` and the lifecycle/release readouts.
- Parent implementation: `src/greia_launcher/main.py` (key tracker configured for S + T, five seconds, on profile picker), `src/greia_launcher/presentation.py` (chord only in profiles mode), `src/greia_launcher/parent_panel.py`, `src/greia_launcher/panel_localization.py` (network URL), `docs/product/PARENT_MANAGEMENT.md` and `docs/architecture/GREIA_PARENT_MANAGEMENT.md`.
- Browser client: separate `frozenpepper/Greia-Parent-App-Html` repository `README.md` and `AGENTS.md` (validated LAN discovery, single-device login, `npm run serve` developer workflow, direct Greia hosting).
- Activity/voice: `skills/greia-activity-authoring/SKILL.md` and Simulator/voice companions, `docs/architecture/GREIA_ACTIVITY_PACKAGE_FORMAT.md`, `tools/validate_activity.py`, `src/greia_platform/activity_packages.py`, `SETUP.md` §7 and `tools/greia_voice_core/README.md`.
- External family USB-writing reference: official [balenaEtcher project](https://etcher.balena.io/), its [documentation](https://github.com/balena-io/etcher/blob/master/docs/USER-DOCUMENTATION.md), [Microsoft boot-media guidance](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/winpe-create-usb-bootable-drive) and [Raspberry Pi official documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html). Those explain standard image-writing/boot-media concerns, not Greia compatibility.

## New practical documentation

- Family guide index: `docs/user/README.md`
- Windows/Mac USB download, flash, installer and first boot: `docs/user/INSTALL_FROM_USB.md`
- On-device and browser Parents App, login, settings and common setups: `docs/user/GREIA_PARENTS.md`
- Image-building overview: `docs/development/BUILD_A_GREIA_IMAGE.md`
- Its relative-linked agent runbook: `docs/agents/GREIA_IMAGE_BUILD_AGENT.md`
- Activity design, install prerequisites, Simulator/voice/package flow: `docs/development/CREATE_AN_ACTIVITY.md`

Root README, SETUP and documentation map route their audiences to these guides; they do not replace the repository's normative docs.

## Important product/acceptance work — documentation alone cannot close it

1. **Parents shortcut discovery/child-selection clarity.** S + T for five seconds is implemented, but the examined source picker renders profile cards and child chrome without an obvious explanatory shortcut hint. Review the **actual 1024×600 and 800×480 UI** in all four languages, including fresh-first-boot → Home → switch profile → hold S + T. Decide where a small, warm, accessible adult hint belongs; keep profile selection obvious to a child, and keep the password boundary. Do not rely on the manual as the only way to find the feature. This finding is a source observation, not a rendered GUI defect claim.
2. **Parent network security.** Current HTTP credential bootstrap and LAN management are marked provisional by parent architecture/product requirements. Authenticated encrypted transport and device identity are a hard ordinary-family release blocker. Do not describe the browser Parent path as release-secure until accepted.
3. **Parent Activity installs.** New `.greiaactivity` installation is implemented behind a semantic capability, but normal/release profiles currently disable it under provisional Parent transport. Do not promise a visible Install button on every release image.
4. **First-boot verification.** First-profile wizard source exists, but the referenced product document still says requested voice recordings and VM/physical fresh-install acceptance are open. Test and update the guide against the actual shipped behavior.
5. **Public image truth.** `website/downloads.html` currently publishes *no* supported image. The quiet `legacy-x86-i686-rc` profile includes developer remote/SSH and is not a general family release. Pi profiles and universal Setup image cannot be advertised before exact build/boot/install acceptance.
6. **Hardware/application parity.** Physically walk through download → flash on Windows and Mac (including platform auto-format prompts) → boot-menu launch → disk-confirmation → install → USB removal → first user → parent management; note which official images/hardware and release SHAs actually passed. Test on-device password and browser client separately, including failure/unreachable states.
7. **Translations and accessibility.** Proofread the actual four-language text for the user-facing manual, especially screenshots or new hint labels; verify beginner links work when the repository becomes public and the website publishes artifacts. Provide friendly, short, visually distinct UI language rather than exposing Linux device names except where safety requires exact disk identity.

## Writing/editing rules for this set

- Families get a small number of direct steps, plain words, clear warnings before both types of disk erasure, and no unsupported Linux or developer instructions.
- Builders/agents get exact source authority, profile distinction, explicit media-write permission boundaries and evidence semantics.
- Do not claim that a command existing means a supported release exists.
- New features should update their user-facing procedure in the same accepted source tranche as the feature; the release candidate must get a final guide-to-device pass before public download buttons go live.
