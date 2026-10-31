# Build a Greia OS image

This is for people who want to **build Greia from source**. If you simply want to put Greia on a computer, read the [USB installation guide](../user/INSTALL_FROM_USB.md) instead. Building an image is a technical, privileged operation; it is not part of normal family setup.

**Using a coding agent?** Give it the companion [Greia image-building agent runbook](../agents/GREIA_IMAGE_BUILD_AGENT.md). That guide contains the preflight checks, exact commands, what may and may not be erased, evidence to collect and safe failure handling. Do not ask an agent to invent a shell recipe from this overview.

## What can be built today?

Greia has declarative profiles for different machines. The current repository has a working legacy-x86 development installer build route, including the Acer Aspire One reference device. A quiet `legacy-x86-i686-rc` profile also exists, **but it is a developer release candidate with developer remote services/SSH**, not an image to distribute to families.

The long-term goal is a single convenient Setup image for compatible PCs and Raspberry Pi machines, but that goal must not be confused with certified outputs from today's commands. Raspberry Pi and universal image paths require exact source/build/hardware evidence before anyone should call them supported. Check the current handover (internal record archived), [profile descriptions](../../build/profiles/README.md) and release readiness checklist (internal record archived).

## What you need

- A **supported Debian-based x86 Linux build machine**, with root/sudo access and enough free disk space. The documented release-candidate host is Debian x86; ordinary Windows/macOS developer laptops are **not** drop-in replacements for this privileged image-composition route.
- A clean Greia Git checkout at the revision you intend to build.
- The Linux build prerequisites and preflight checks in [the existing installer build runbook](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md#132-build-host-commands-debian-x86-no-docker).
- Time and disk space for two Linux root compositions, target payload, squashfs and build outputs; do not treat the installed OS footprint limit as the build host's free-space requirement.
- Permission to use any removable medium **before** invoking a media-writing command.

**Never run a raw image writer against a disk containing valuable data.**

## The safe development-image path

First check the [setup index](../../SETUP.md#10-os-image--installer-builder), [OS work skill](../../skills/greia-os-work/SKILL.md), build operations guide (internal record archived), and [installer-image reference](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md). On an appropriate Linux host, from the clean repository root:

```bash
git status --short
git rev-parse HEAD

# Build an installer .img file; does NOT flash any USB device.
sudo bash tools/build-development-installer.sh legacy-x86-i686-dev ./out
```

This high-level wrapper routes legacy-x86 builds through the accepted boot-artwork and installer steps. The real image is named `out/greia-os-installer-<PROFILE>-<VERSION>-build-<COMMIT>.img`; `out/greia-os-installer-legacy-x86-i686-dev.img` is a compatibility symlink. A report is written beside it. Inspect the reports and verification output; **a file existing is not proof it is bootable**.

For the specific quiet developer release candidate, the analogous profile is `legacy-x86-i686-rc`. Follow [the RC runbook](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md#13-release-candidate-build-runbook-legacy-x86-i686-rc) rather than substituting it silently for a normal release.

### Validate before anyone uses it

The applicable check depends on the build profile and evidence target:

1. Verify the source revision, the selected profile and the build report/image hash.
2. Check the high-level builder's exact validation results, especially payload identity, live media boot structure, footprint and boot-policy checks.
3. For VM evidence, use the repository's [image verification scripts](../../build/verify-installer-qemu.sh) with an appropriate target CPU; this is separate from physical hardware evidence.
4. For a release candidate, follow its exact pre-build and physical acceptance runbook. An image that boots on one machine does not establish compatibility with every x86 PC.
5. Record what was actually tested. Do not publish a developer image as an ordinary-family download.

## Writing a built image onto USB

**This is optional and destructive.** The build-only command above is the right default.

On the accepted Linux development host, the repo also provides a combined development build/flash/verify front door:

```bash
# Example syntax ONLY; /dev/sdX is a placeholder, not a real selection.
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX ./out
```

**Do not copy/paste that command until you have positively identified and been authorized to erase the actual USB device.** It targets the whole device, not a file or partition. The [physical USB checklist](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md#133-identify-the-usb-stick-before-writing) requires unplug/replug checks of the exact drive's model/size/serial and a separate read-back verification.

If you are preparing media from an already published, supported image on a personal Windows PC or Mac, use [the graphical Etcher guide](../user/INSTALL_FROM_USB.md), not this Linux builder/writer route.

## What about official release artifacts?

`tools/greia_release.py` is the higher-level release operator and has `doctor`, `build`, `build-profile` and `inspect` commands. The [system-update release guide](GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md) explains which `.greiaupdate` payloads it currently produces. **Building a release/update bundle does not automatically mean a tested, universal, bootable USB installer was published.** Read its release report and exact scope. Do not substitute this operator for the proven legacy development installer merely because the name sounds more general.

For release publication, also check release readiness (internal record archived), the multiplatform lifecycle plan (internal record archived), and the current handover (internal record archived). Those determine whether a profile/target combination may actually be advertised.

## Common mistakes to avoid

- **Using the wrong computer:** image building requires an approved Linux build environment; flashing from Windows/macOS is a separate task.
- **Using the wrong builder:** `build/build-installer-image.sh` is a lower-level composer and can bypass legacy physical-media wrapper obligations.
- **Treating `-dev` or `-rc` as a family release:** these may include developer services and are not hardened/qualified public outputs.
- **Treating an x86 `.img` as a Pi image:** the firmware and target layout are different. Use only a verified Pi-specific or genuinely universal release.
- **Treating a successful build as a successful boot/install:** VM and physical tests are separate, and installed-system boot is separate from live USB boot.
- **Building over another agent's changing checkout:** freeze the commit and use a clean separate build checkout.

For an agentic build, go straight to the [companion runbook](../agents/GREIA_IMAGE_BUILD_AGENT.md).
