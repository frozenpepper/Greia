# Install Greia with a USB stick

This guide is for you if you use a **Windows PC or a Mac** to prepare a USB
stick, then install Greia on a **different computer**. You do not need to
know Linux or type any commands.

> **Technical preview.** The installer on the
> [Greia downloads page](https://www.frozenpepper.it/greia/downloads.html) is a
> first preview, tested on the first-generation Acer Aspire One. Other Intel or
> AMD PCs may work, but they are not tested yet. It is not a finished family
> release. Use a spare computer. If an image is marked *developer*,
> *experimental* or *unverified*, it is not meant for families.

## Before you start

You need:

- **The computer that will get Greia.** Its whole disk will be erased.
- **A second computer** (Windows or Mac) with internet.
- **A spare USB stick, 4 GB or bigger.** Everything on it will be erased.
- A keyboard, a screen and power for the Greia computer. A mouse or touchpad
  helps.
- A **backup** of anything important on the Greia computer, kept somewhere
  else.

Only go on if you are happy to lose everything on that computer. Unplug any
external disks you do not want to use.

Greia installs on PCs, not on Macs. Your Mac is only used to prepare the
stick. There is no Raspberry Pi image yet. Do not use this stick on a
Raspberry Pi.

## 1. Download Greia

1. Open the [Greia downloads page](https://www.frozenpepper.it/greia/downloads.html).
2. Choose the installer that lists your kind of computer.
3. Download it. It is a single `.img` file, about 2.3 GB. It is a ready-made
   disk image. It must be written to the stick. Do not just copy it there.
4. Optional: check the download. The page shows a *checksum* (a fingerprint
   of the file). The downloads page shows how to compare it on your system.
   If it does not match, download again.

## 2. Write it to the USB stick

We suggest **balenaEtcher**, a free program from
[etcher.balena.io](https://etcher.balena.io/). It writes the file and then
checks the result.

1. Install and open balenaEtcher.
2. Plug in the USB stick. Unplug other USB drives so you cannot mix them up.
3. Choose **Flash from file** and pick the Greia `.img` file.
4. Choose **Select target** and pick the USB stick. Check its name and size.
   **Never pick your computer's own disk.** If you are not sure, stop.
5. Choose **Flash**. Say yes if the computer asks for permission. Wait for
   writing **and** checking to finish.
6. Eject the stick safely.

**Windows** may say the stick cannot be read, or offer to format it. Choose
**Cancel**. This is normal.

**Mac** may say the disk is not readable. Choose **Ignore**, not Initialize.

Rufus and Raspberry Pi Imager also work, and the downloads page explains them.

## 3. Start the Greia computer from the stick

1. Plug the stick into the computer that will get Greia. Connect power,
   screen and keyboard. Shut it down fully.
2. Switch it on and tap the **boot-menu key** about twice a second until a
   list of devices appears. It is often **F12**. Others are F9, F11 or Esc.
   The startup screen or the manual says which. On an older Acer, press **F2**
   at power-on, set **F12 Boot Menu** to **Enabled**, then save with **F10**.
3. Choose the USB stick. It may be called **USB HDD** or **Removable device**.
4. The Greia logo appears, then the installer.

If the old system starts instead, shut down and try again. If the stick is
not listed on a newer PC, the firmware settings may need **Secure Boot** off
or **Legacy / CSM** boot on. Only change settings you know how to undo. Never
erase a disk to make the stick appear. This preview is tested on older
computers with the classic BIOS. Starting on newer PCs is experimental.

If you see a plain text screen, or the screen stays blank, stop. Write down the
computer's make and model and what you saw, and tell us.

## 4. Follow the installer

The installer works with a mouse, touchpad or keyboard. It asks for:

1. **Language.** English, Italian, Spanish or French. Press **Start**.
2. **Keyboard.** Greia suggests one.
3. **Disk.** Only safe internal disks are shown. **Check the model and size.**
4. **Pointer.** How the mouse or touchpad behaves. Tap-to-click starts off.
5. **Screen.** Automatic is right for almost everyone.
6. **Wi-Fi** (optional). You can connect now or later. Greia works without
   internet.
7. **Ready to install.** Greia shows the disk that will be erased. To go
   ahead, hold the **Hold to erase and install** button for two seconds. You
   can also hold Enter or Space. Letting go early cancels.

Nothing is erased until that last step. After it starts, **do not switch off
the computer or remove the stick.** It takes several minutes. If an error
appears, write it down. Do not assume the computer is ready.

## 5. First start

1. When the installer says it is done, shut the computer down as it asks.
2. **Take out the USB stick** once the computer is off. Then switch it on.
3. Greia opens straight into its child screen. The first time, you set up the
   first child: a name, a picture and, if you like, an age. Later, children
   pick their own picture at the start.

Children do not need a computer account to use Greia.

## 6. Where are the parent settings?

On the screen where children pick their picture, **hold the S and T keys
together for five seconds**. The Parents panel opens. Enter the **Parent
password**. It is not a child's password.

On this preview the first Parent password is `greia`. The installer's final
screen also shows it. Change it in the Parent settings.

This works only on the child-picking screen, not inside an Activity or during
the first-child setup. To get there from Greia's home screen, use the
child's profile switcher, or press Escape. More in the
[Greia Parents guide](GREIA_PARENTS.md).

## If something goes wrong

| Problem | What to try |
|---|---|
| Etcher cannot find the stick | Unplug it and plug it back in, or try another USB port or stick. |
| Checking failed after writing | Try another stick, or download again. Do not use a failed stick. |
| The old system starts | Open the boot menu again and choose the USB stick. |
| No disk is offered | Stop. Do not change or wipe disks by hand. Tell us what your computer is. |
| No Wi-Fi | Carry on without it. You can set it up later in Parent settings. |
| Installer seems stuck | Wait. Do not interrupt a disk write. If it stops, note the message. |
| Windows or Mac asks to format the stick | Cancel (Windows) or Ignore (Mac). |
| Cannot reach Parent settings | Go back to the child-picking screen. Hold **S + T** for five seconds. |

Still stuck? Write to greia@frozenpepper.it with your computer's make and
model and the exact message you saw. Never send passwords.

## Background reading

The USB steps follow the [balenaEtcher documentation](https://github.com/balena-io/etcher/blob/master/docs/USER-DOCUMENTATION.md).
Boot-menu keys differ by maker, as [Microsoft explains](https://learn.microsoft.com/en-gb/windows-hardware/manufacture/desktop/winpe-create-usb-bootable-drive).
For Raspberry Pi, use that project's own [instructions](https://www.raspberrypi.com/documentation/computers/getting-started.html), not this guide.
