# Greia image build — instructions for a coding agent

**Audience:** a coding/operating agent assisting a human who wants to build a Greia OS image.  
**Status:** derived operational runbook, reviewed 2026-10-22.  
**Human companion:** [Build a Greia image](../development/BUILD_A_GREIA_IMAGE.md).

The first duty is to avoid misleading the operator or destroying the wrong drive. A successful file build is **not** a published or hardware-certified release.

## 1. Read authoritative source BEFORE selecting commands

At the **exact checkout** being built, read in this order:

1. [AGENTS.md](../../AGENTS.md), [SETUP.md](../../SETUP.md), HANDOVER.md (internal record archived) and [documentation ownership](../DOCUMENTATION.md).
2. [OS work skill](../../skills/greia-os-work/SKILL.md), [boot companion](../../skills/greia-os-work/BOOT.md) and agent operations (internal record archived).
3. [Installer image creation/boot](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md), especially sections 3, 11–14 and the RC runbook.
4. Release lifecycle authority (internal record archived), release readiness (internal record archived), [image profiles](../../build/profiles/README.md), and [release CLI workflow](../development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md) if making publishable/update artifacts.
5. The actual selected profile TOML, the high-level script's `--help`/usage, its delegated builder, current verifier and any later fixes in source.

Resolve contradictions by authority and current source, not by copying a command from an older review. Do **not** read historical postmortems as instructions without checking their current successor.

## 2. Establish the requested deliverable and permissions

Before doing privileged work, distinguish:

- **A. Image file only** (`.img` plus reports, no real media write): safe default when the request simply says “build an image”.
- **B. Flash a named USB/SD device:** requires explicit authorization for **that exact removable disk**; the filename `/dev/sdX` is never authorization.
- **C. Install onto a computer's internal disk:** a separate graphical, destructive installer action. Never equate build or media flash consent with installation consent.
- **D. Release/update artifacts:** a matrix/bundle operator path; publication and support claims require the separate release gate.

If the user has not specified a profile, inspect current supported profiles and their evidence, then choose only when the target and deliverable are unambiguous. Do not silently use `-dev`/`-rc` to fulfill an ordinary-family image request.

**No automatic media wiping.** No fallback to `dd`, `mkfs`, `parted`, raw block copy or host partition manipulation when a front-door guard refuses. No “fixing” the user's build host with broad cleanup, loop detaches, reboot or package installation without scope approval.

## 3. Preflight for a build-only development installer

The known physical legacy-x86 path uses a **Debian x86 Linux** build host with root access. A Mac/Windows workstation is not an equivalent raw composition host.

Record:

```bash
pwd
git status --porcelain
git rev-parse HEAD
uname -srm
python3 --version
df -h .
```

Stop if the checkout has unreviewed changes, unknown branch/revision, inadequate storage, unexpected host OS or no authorized privilege path. **Do not reset, clean, stash or discard user changes.** Make a separate clean checkout at the pinned commit if needed. Check the exact `SETUP.md` and installer runbook package prerequisites before installation.

For the accepted legacy development front door:

```bash
sudo bash tools/build-development-installer.sh --help
# After approved preflight, profile and output directory:
sudo bash tools/build-development-installer.sh legacy-x86-i686-dev ./out
```

That wrapper delegates to `build/build-legacy-x86-sd-installer.sh` and is the physical legacy route. Do **not** replace it with direct `build/build-installer-image.sh` use unless specifically investigating a lower-level failure.

For the quiet Acer RC, use `legacy-x86-i686-rc` only if explicitly requested, and follow [the RC runbook](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md#13-release-candidate-build-runbook-legacy-x86-i686-rc) including its frozen SHA, host preflight, complete gates, operator public-key handling and boot/USB semantics. The RC includes developer remote access and cannot be relabeled as a family image.

**Pi:** do not infer a working Pi installer from a profile file. Verify the current native Pi build adapter and its exact source/physical acceptance first; otherwise report the gap without generating a mislabeled image.

## 4. Run only the validation justified by the deliverable

For a build-only result:

1. Retain the exact stdout/stderr log and command exit code.
2. Read the resulting `out/greia-os-installer-<PROFILE>-<VERSION>-build-<COMMIT>.img` (the stable `out/greia-os-installer-<PROFILE>.img` is a compatibility symlink), corresponding `-report.txt` and footprint/profile metadata.
3. Compare the report's image hash with a hash of the actual produced image.
4. Verify the high-level builder's success markers, root partition/payload contract, boot console policy and footprint. A log ending early, a missing report or a failing verifier means **FAIL**, even if a partial image exists.
5. Perform supported VM checks when the target and host permit them. Use the appropriate x86 CPU model (for i386, not `-cpu pentium3`; see installer runbook) and save exact outcomes.
6. Label evidence honestly: **SOURCE**, **BUILD/MEDIA**, **VM**, **PHYSICAL** are not interchangeable.

The current release operator `tools/greia_release.py build --version ... --output ...` emits a release bundle/report according to the active implementation scope; do not assume that a universal bootable Setup image exists. Inspect actual `release-report.json` outputs and owner-plan status.

## 5. Media writing — additional explicit authorization gate

Do nothing in this section for a build-only request.

For a named Linux USB target, inspect the **whole device** with:

```bash
lsblk -d -o NAME,SIZE,MODEL,SERIAL,TRAN,RM,TYPE
```

Ask the human to identify it physically. Unplug it, verify the same exact entry disappears, replug and verify it returns. Confirm `TRAN=usb`, `RM=1`, `TYPE=disk` and the expected model/size/serial. Unmount only confirmed partitions belonging to that authorized device using the accepted writer procedure.

Once authorized, the repository's preferred physical legacy developer workflow is:

```bash
# Example, not executable without replacing and confirming the device!
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX ./out
```

Do not substitute an arbitrary target. Read-back verification is separate from writing and mandatory for claimed media success: [writer and verifier contract](../engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md#2-reference-acer-removable-media-keep-the-proven-syslinuxfat32-recipe). If the writer rejects the device, stop and report why; do not bypass it.

**Never auto-install Greia on the destination computer.** It must boot the real GUI installer and require its verified-disk confirmation.

## 6. Common known failure classes

- Insufficient or missing Debian host tools (including `grub-efi-ia32-bin` and `grub-efi-amd64-bin` on the current RC route).
- Building under a shared desktop mount namespace; temporary rootfs/loop mount leakage. Follow the RC runbook's `unshare --mount --propagation private` procedure where specified, not an improvised cleanup.
- Stale regenerated boot artwork when bypassing the high-level legacy wrapper.
- `console=null` and related fatal boot argument errors; never remove `console=tty1` to silence boot messages.
- FAT32/Syslinux removable boot and installed GRUB boot are different contracts.
- Wrong root partition assumptions (the newer ESP + ext4 layout requires selecting the ext4 payload root, not assuming p1).
- Bad virtualization CPU choice (SSE2 requirement on i386).
- The release profile contains SSH/development capability when the requester expects a hardened public image.
- Claiming cross-hardware Pi/UEFI support after only a successful x86 build.

Treat new failure symptoms as evidence. Preserve logs, exact source SHA and relevant receipts before editing code.

## 7. Report back in one self-contained block

Return:

```text
GREIA IMAGE BUILD REPORT
Source repository / exact SHA:
Host OS / architecture:
Selected profile and why:
Output type: file only / USB / release bundle
Operator permissions: 
Command(s) run and exit codes:
Output image/report path(s):
Image size and SHA-256:
Builder/verifier result(s):
VM evidence, if any:
Physical media evidence, if any:
Known unresolved issues:
What the user can safely do next:
```

Never report “release-ready” without all necessary release gates; never report a physical PASS without an actual physical test. Retain bulky build evidence outside the repository and avoid creating many redundant logs.
