# Greia Parents: the simple guide

Greia Parents is where adults manage a Greia computer. Children use Greia's pictures, games and Activities; parents have separate controls for profiles, the device and each child's experience.

You can access parents' controls **on Greia itself** or, when supported by the installed release, **in a web browser on another device**. The core idea is local management, without a mandatory cloud account.

> **Release note:** Current source uses HTTPS for the network Parents App. Greia automatically creates its own local certificate, so your browser will normally show a certificate warning the first time. Device and browser acceptance testing is still required before calling a public installer release-ready.

## Open Parents on the Greia computer

1. Turn on Greia and reach the screen where children **choose their picture or name**. This is the **child-selection screen** (sometimes called the login screen).
2. On the physical keyboard, **press and hold S and T together** for **five full seconds**.
3. When the Greia Parents panel appears, **release both keys**.
4. Enter the **Parent password** and continue.

**S + T opens the on-device settings panel only from child selection.** It will not open from a game, a child's Home page or the first-child setup wizard. There is no need to press Ctrl, Alt or a function key.

The initial Parent password on current development installs is `greia` (lowercase). It is separate from any password you choose for your child. Change it when you have access to the change-password control; consult the actual release's welcome/completion screen for its initial credential.

If the panel does not open, return to child selection (from Greia Home, choose the current child's profile/switcher, or use Escape on the keyboard). Make sure both keys stay down together for all five seconds and try again. The on-device panel requires a keyboard.

### What you can do on the device

The built-in panel provides practical device setup, including language, Wi-Fi, sound/microphone settings, child accounts and selected maintenance/connection information. Available tabs and controls depend on the exact device and version. You do **not** need Linux or a terminal to use it.

## Open the browser-based Parents App

Greia also has a lightweight browser-based Parents App, developed as part of the open-source Greia project. Its separate source repository is still private during pre-release preparations, so public source access should not be assumed yet. It is a separate interface to the **same Greia management system**, not a different operating system. It works from a phone, tablet or laptop with a browser when it can reach the Greia device.

### Directly from a Greia computer (currently available in development)

1. Make sure Greia and your phone/laptop are connected to the **same local network**.
2. On the Greia computer, open the on-device Parents panel with **S + T for five seconds**, sign in and look at its connection/Info information.
3. The panel shows an address in the form `https://<GREIA-IP>:8766`. Type the **actual address displayed on your Greia** into your phone's or laptop's browser.
4. On your first visit, the browser may warn that Greia's certificate is not publicly verified. For your own Greia, on your home network, you can use your browser's **Advanced / Continue** option. Do not continue to an unfamiliar address.
5. Sign in with the **Greia Parent password** when asked. A paired browser can reconnect on later visits while its device credential remains valid.

If Greia has no working network address, the browser route cannot connect. You can still use the on-device controls. Do not expose port 8766 to the internet or forward it on your router.

### Open-source standalone browser host (advanced/optional)

The source of the Parents App is in the separate [Greia Parent App HTML repository](https://github.com/frozenpepper/Greia-Parent-App-Html). The project intends to publish this source for people who want to inspect, run or contribute to the standalone local host. Access to that separate repository is currently restricted while release preparations continue.

For a developer with **Node.js/npm installed**, the current source workflow is `npm run serve`, then open `http://127.0.0.1:8080/` on the host computer. The host discovers validated Greia devices on the local network and lets you select one. **Normal parents do not need to install Node.js or clone a repository:** they can use the Greia-served page when it is available.

There is no mandatory remote account or monthly subscription for the local Parents App. The standalone host's discovery is not an authentication bypass: the Greia Parent password and device-specific pairing still apply.

## What can parents manage?

The browser interface organizes common tasks into **Home**, **Children**, **Activities** and **This Greia**.

- **Home:** quick view of the selected child, recent activity, visible Activities and available device/time information.
- **Children:** add or rename a child profile, choose a picture, set an approximate age, adjust challenge preferences, optionally protect a child's profile with a password, and configure available play-time limits.
- **Activities:** see what is installed, filter and search it, and decide which Activities each child sees. The options include automatic age-based visibility, **Always show** and **Hide from child**. Difficulty and discovery preferences can be adjusted independently.
- **This Greia:** supported language, network, input, display, audio, security, access and system controls. The app shows only what this device actually supports.

Some features described in plans — especially public Activity-store/update, system recovery and backup flows — are not yet fully delivered. A missing or disabled control may simply mean the installed release does not support that operation.

## Change Greia's language

Greia currently offers **English, Italian, Spanish and French**. You can
change the computer's language without reinstalling it:

1. Open **Greia Parents → This Greia → Language** in the browser, or open
   the on-device Parents panel with **S + T** held for five seconds at the
   child-selection screen, then choose its **Language** tab.
2. Select the language by its name and confirm. It becomes the computer's
   default language and stays selected after restart.
3. If a particular child has a separate language preference, their profile
   can take priority over that computer default. An Activity offered only in
   another language may use its own fallback; that does not change Greia's
   chosen language.

Only languages actually included and approved in that Greia release appear.
Contributors preparing additional languages do not automatically expose
unfinished translations to families.

## Three common family setups

**One child:** create the profile at first startup, choose the child's picture and optional age, and leave Activities on Automatic. You can adjust individual games later.

**Several children:** make one profile for each child in Parents. Each gets their own preferences and saved work. Set separate Activity visibility or time limits as needed.

**A Greia laptop and a parent's phone:** connect both to the same home Wi-Fi. When the browser Parents App is available and the release's connection security is approved, use it for convenient management. If the network is unavailable, use the on-device **S + T** panel.

## Passwords and privacy

Greia distinguishes the **Parent password** from an optional **child profile password**. The Parent password grants management access; do not share it with a child. Parent browsers have separate, revocable credentials so losing one device does not require signing out every other device.

The current design stores child profiles and progress locally and works offline for normal child Activities. Avoid exposing the parent management service outside your home network. The current development source serves the network Parents App over **local HTTPS with a device-generated certificate**; browser and actual-device acceptance still determine public-release readiness.

## Activities from other creators

Greia defines a portable `.greiaactivity` file. Once an installed version **advertises Activity installation as available**, open **Activities** in the browser Parents App, choose **Install Activity**, select the file and follow the Greia validation/confirmation steps.

**Current ordinary/release profiles still do not advertise Activity installation until its separate release acceptance is complete.** If the button is absent or unavailable, do not work around it by copying files or enabling SSH. The [Activity creation guide](../development/CREATE_AN_ACTIVITY.md) explains development-time testing and packaging.

If you are stuck, report your Greia version, device model and the exact screen/message, without sharing passwords.
