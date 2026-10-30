# Greia Parents: the simple guide

Greia Parents is where adults manage a Greia computer. Children use the
pictures and games. You use Parents to set up children, choose what they see
and look after the computer.

You can open it **on the Greia computer itself**, or **in a web browser on
your phone or laptop** when both are on the same home network. You do not
need an account or the internet.

## Open Parents on the Greia computer

1. Switch Greia on and wait for the screen where children **pick their
   picture or name**.
2. On the keyboard, **press and hold S and T together** for **five full
   seconds**.
3. When the Parents panel appears, let go.
4. Type the **Parent password**.

The first Parent password on this preview is `greia`, in lowercase. It is
different from any password you give a child. Change it as soon as you can.
The installer's final screen shows the password for your version.

This shortcut works only on the child-picking screen. It does not work inside
a game, on a child's home page or during the first-child setup. If nothing
happens, go back to the child-picking screen (use the child's profile switcher
on Greia's home screen, or press Escape). Then hold both keys down
for the whole five seconds and try again. You need a keyboard.

**What you can do here:** change the language, connect to Wi-Fi, adjust sound
and microphone, add children, and see connection information. What you see
depends on your computer and Greia version.

## Open Parents from your phone or laptop

The browser version does the same job and is easier to use.

1. Put your phone or laptop and the Greia computer on the **same home Wi-Fi or
   network**.
2. On Greia, open the Parents panel (above) and sign in. Find the
   connection information. It shows an address that looks like
   `https://192.168.1.20:8766`. Yours will differ.
3. Type **that exact address** into your phone's or laptop's browser.
4. The first time, the browser will warn that the site is not verified. This
   is expected: Greia makes its own security certificate (its own ID card),
   because it cannot get a public one. On your own Greia, on your own network,
   choose **Advanced**, then **Continue**. Never continue to an address you
   do not recognise.
5. Sign in with the Parent password. Later visits from the same browser can
   reconnect without it, until you remove that browser.

If Greia has no network address, the browser cannot reach it. Use the panel on
the Greia computer instead. **Never open this to the internet and never set up
port forwarding on your router.**

## What you can manage

The browser app has four areas: **Home**, **Children**, **Activities** and
**This Greia**.

- **Home:** the chosen child, recent play, and time information.
- **Children:** add or rename a child, choose a picture, set an approximate
  age and how challenging games should be, protect a profile with a password,
  and set play-time limits where available.
- **Activities:** see what is installed and choose what each child sees:
  *Automatic* (by age), *Always show* or *Hide from child*.
- **This Greia:** language, network, input, display, sound, security, access
  and system controls. It shows only what your computer supports.

Some planned features are not finished: sharing Activities through a store,
full backup and restore, and some system recovery tools. If a button is
missing or greyed out, your version does not have it yet.

## Change Greia's language

Greia offers **English, Italian, Spanish and French**. You can change it
without reinstalling.

1. In the browser, go to **This Greia**, then **Language**. Or open the panel
   on the Greia computer with **S + T** and choose its **Language** tab.
2. Pick the language and confirm. It becomes the computer's language and
   stays after a restart.
3. A child can have their own language, which wins over the computer's.

## Common setups

**One child:** make the profile at first start, pick a picture and age, and
leave Activities on Automatic.

**Several children:** make one profile per child. Each has their own saved work
and settings. Set visible Activities and time limits for each.

**Greia laptop and your phone:** join the same home Wi-Fi and use the browser
version. If the network is down, use the panel on the Greia computer.

## Passwords and privacy

The **Parent password** gives full control. Do not share it with a child. A
child's own password, if you set one, only opens that child's profile. Each
phone or laptop you connect gets its own sign-in that you can remove
separately, so losing one device does not affect the others.

Children's profiles and progress stay on the Greia computer. Normal Activities
work offline. See the [privacy page](../../PRIVACY.md).

## Activities from other creators

Greia has a file type for Activities made by others (`.greiaactivity`). When
your version supports it, **Activities** in the browser app will offer
**Install Activity**. Greia checks the file before installing.

This preview does not offer that button yet. Do not try to get around it by
copying files or turning on remote access. If you want to make Activities,
read [Make an Activity](../development/CREATE_AN_ACTIVITY.md).

## For developers

The browser app is a separate open-source project,
[Greia-Parent-App-Html](https://github.com/frozenpepper/Greia-Parent-App-Html).
Its source may still be private until the project announces it. Normal
parents never need it: Greia serves the page itself. A developer with
Node.js can run it locally with `npm run serve` and open
`http://127.0.0.1:8080/`. It finds Greia computers on your network. The
Parent password and pairing still apply.

## Stuck?

Write to greia@frozenpepper.it with your Greia version, your computer's
model, and the exact message on screen. Never include passwords.
