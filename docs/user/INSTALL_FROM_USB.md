# Install Greia with a USB stick

This guide is for someone using **Windows or macOS to prepare a USB stick**, then installing Greia on a separate compatible computer. You do not need to know Linux or type terminal commands.

> **Not available for ordinary families yet:** since 30 October 2026 the [Greia downloads page](https://www.frozenpepper.it/greia/downloads.html) offers a **technical-preview** installer for netbooks and PCs (reference: first-generation Acer Aspire One, legacy BIOS; UEFI start is experimental). It is for people comfortable trying new software. An image marked *technical preview*, *developer*, *experimental*, *RC*, or *unverified* is **not** a family release. Questions: greia@frozenpepper.it.

## Before you begin

You will need:

- The computer **on which you want Greia** (it will no longer keep its existing operating system or files).
- Another computer running Windows or macOS, with internet access.
- A spare USB stick, large enough for the published Greia image. Its contents **will be erased**. If the download page gives a minimum size, use that size or larger.
- A keyboard, screen and a working power supply for the Greia computer; a mouse or touchpad is helpful.
- A backup of **everything important** on the destination computer, stored somewhere else.

**Do not continue unless you are willing to erase the destination computer completely.** Disconnect external disks that you do not intend to install onto. For a Raspberry Pi, follow **only** the instructions accompanying a specifically published, supported Pi image: a PC/x86 installer is not a Raspberry Pi image.

## 1. Download the correct Greia image

1. Open the [Greia download page](../../website/downloads.html) or its [GitHub releases](https://github.com/frozenpepper/Greia/releases).
2. Choose an image explicitly listed as compatible with **your** computer. Never pick an image by filename alone.
3. Download the installer image to your Windows PC or Mac. It may be a `.img` file or a compressed image; follow the release's instruction if it must first be extracted.
4. If the release provides a SHA-256 checksum, compare it using the platform-specific help linked by that release. If it does not match, delete the download and download it again. Do not use a file from an unknown mirror.

The download page always shows the newest image with its version, size and SHA-256 checksum. No general-purpose family release is published yet.

## 2. Prepare the USB stick (Windows)

We suggest [balenaEtcher from its official website](https://etcher.balena.io/). It can write disk images and check that the data was written correctly.

1. Download and install balenaEtcher for Windows.
2. Plug in your spare USB stick. If you have several removable disks, unplug the others so they cannot be confused.
3. Open Etcher and select **Flash from file**. Choose the downloaded Greia image.
4. Select **Select target** and check the USB stick's name and capacity. **Not your Windows disk.** If you are unsure, cancel.
5. Select **Flash**, approve the Windows permission prompt if shown, and let writing **and validation** finish.
6. Eject the USB stick safely.

Windows may offer to format a newly flashed USB drive, or say it cannot read some partitions. **Choose Cancel; do not format it.** A bootable Linux installer can contain partitions Windows does not understand.

## 3. Prepare the USB stick (Mac)

The steps are nearly identical. Use the official [balenaEtcher](https://etcher.balena.io/) macOS installer.

1. Download and install Etcher for Mac. Open it from Applications.
2. Connect the spare USB stick. If possible, disconnect other USB drives first.
3. Choose **Flash from file**, then select the Greia image.
4. Choose the USB stick under **Select target**. Check its capacity carefully. **Never select your Mac's own storage or an external backup drive.**
5. Select **Flash**. macOS may ask for your password to allow writing the drive. Let validation complete.
6. Eject the finished USB stick.

macOS may say the disk is not readable and offer **Initialize** or **Ignore**. Choose **Ignore**, not Initialize: the installer image was written deliberately.

**You are using the Mac only to prepare the USB.** These instructions do **not** claim that Greia can be installed on that Mac, especially an Apple Silicon Mac. The *destination* computer must be listed as compatible by the Greia release.

## 4. Start the computer from the USB stick

1. Connect the Greia USB stick to the computer that will receive Greia.
2. Connect power, screen, keyboard and mouse/touchpad if needed.
3. Turn it on and open its **boot menu**. The key varies by manufacturer; common examples are **F12, F9, F11 or Esc**. The computer's manual or startup screen has the reliable answer.
4. Choose the USB stick, sometimes shown as **USB HDD** or by its brand.
5. Greia should start its graphical installer. If you see the original system instead, shut down and try the boot menu again. **Do not try random BIOS changes** or erase a drive to make it boot.

On some computers Secure Boot, firmware age or unsupported hardware can prevent booting. The release's compatibility instructions take priority. If you see an unexpected text console or a persistent blank screen, stop and report the device/model and what appeared.

## 5. Follow the Greia installer

The current graphical installer is designed to guide you through:

1. **Language:** choose from the languages shown by the installer. The current development release includes English, Italian, Spanish and French; future releases may offer more languages when their translations and spoken guidance are ready.
2. **Welcome and keyboard:** read the short introduction, press **Start** and choose your keyboard layout.
3. **Computer's disk:** select the internal disk Greia should use. The installer offers only disks it considers eligible; **check the displayed model and size**.
4. **Pointer and display:** check the mouse/touchpad and the display.
5. **Wi-Fi (optional):** connect if you wish. Greia's core activities are intended to work offline.
6. **Ready to install:** read the final warning. Greia displays the disk that **will be erased**. You must **hold the erase/install control for two seconds** to confirm. Do not confirm unless everything on that disk can be lost.

The last confirmation is the destructive step. **After it begins, do not power off or remove the USB stick during installation.** Greia should show progress and eventually a completion screen. If installation stops or displays an error, note the message; do not assume the computer is ready.

## 6. First startup

1. When the installer says it is done, follow its shutdown instruction.
2. **Remove the USB stick after the computer turns off**, before starting it again. Otherwise it may start the installer from USB once more.
3. Turn the computer on. Greia should open directly into its friendly child interface.
4. On a fresh install, the first-child setup offers a welcome, name, picture/avatar, optional age and a confirmation. Help your child choose those. On later startups, choose the child's picture at the child-selection screen.

You do not need a Linux username to let a child use Greia.

## 7. Where are the parent settings?

**On the child-selection screen, hold the S and T keys together for five full seconds.** Keep both pressed at the same time until the Parents panel opens, then release them. Enter the **Parent password**, not a child's optional password.

For current development images, the initial Parent password is `greia`. Change it under Greia Parents when that control is available. The published release's instructions and completion screen will provide the authoritative initial credential for that version.

The shortcut works **at child selection**, not while playing an Activity or completing the first-child wizard. From Greia Home, use the current child's profile/switcher (or press Escape) to return to child selection and try again. See [Greia Parents](GREIA_PARENTS.md) for on-device and browser options.

## If something goes wrong

| Problem | What to try safely |
|---|---|
| Etcher cannot find the USB stick | Unplug/reconnect it, try another USB port or stick. Do not select a different drive by guesswork. |
| Validation failed | Re-download and try a different USB stick; do not use a failed write. |
| Computer boots its old OS | Open the device's boot menu and select USB. Verify compatibility with the release. |
| No internal disk is offered | Stop. Do not change or wipe partitions manually to force installation. |
| Wi-Fi is unavailable | If Greia allows it, continue offline and check network settings later in Greia Parents. |
| Installer seems stuck | Look for its progress text and wait for its outcome; don't interrupt a disk write. Record the on-screen message if it stops. |
| USB seems unreadable on Windows/Mac | Cancel the operating system's format/initialize prompt. This is expected for some flashed media. |
| Can't reach Parents | Return to the child-selection screen, hold **S + T** together for five seconds, then release. |

### Background reading

This preparation follows the image-selection, target-selection and validation model of the [official balenaEtcher documentation](https://github.com/balena-io/etcher/blob/master/docs/USER-DOCUMENTATION.md) and its [project website](https://etcher.balena.io/). Boot-menu keys vary by PC maker, as [Microsoft's USB boot instructions](https://learn.microsoft.com/en-gb/windows-hardware/manufacture/desktop/winpe-create-usb-bootable-drive) explain. Raspberry Pi images have a separate [official custom-image writing procedure](https://www.raspberrypi.com/documentation/computers/getting-started.html); do not apply it to a PC image.
