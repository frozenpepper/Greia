# Greia R7 — Controlled active KMSDRM acceptance

**Date:** 2026-08-09
**Scope:** QEMU/x86 and later Acer maintenance evidence on an otherwise normal Greia X-compatibility image.
**Safety:** this is a maintainer-only display takeover test. It is never a normal child path and must not be enabled at boot.

## What this test answers

The passive runtime audit answers whether the image appears to contain the prerequisites for SDL KMSDRM. This active test answers the narrower but critical next question:

> Can the image create a real fullscreen Pygame/SDL display using the **actual `kmsdrm` video driver**, render deterministic frames, and release the display cleanly when Xorg is temporarily stopped?

A PASS does **not** yet prove shell↔Activity ownership, input routing, physical scanout continuity, boot-cover continuity, or R7 closure.

## Preconditions

Do not edit services, packages, Xorg files, groups, udev rules, or device permissions before this test.

The candidate image must be built from the current `r7-direct-graphics` source and must contain:

```text
/opt/greia-os/src/greia_platform/direct_graphics_probe.py
/opt/greia-os/src/greia_platform/kmsdrm_acceptance.py
/etc/systemd/system/greia-kmsdrm-acceptance.service
/usr/local/sbin/greia-run-kmsdrm-acceptance
/usr/local/sbin/greia-collect-runtime-audit
```

Normal Greia must already be running successfully through `greia-launcher.service` before the active test begins.

## Step 1 — collect baseline/passive evidence

As root, collect the normal runtime audit **before** taking over the display:

```sh
/usr/local/sbin/greia-collect-runtime-audit /var/lib/greia-audit
```

Record the archive path printed by the command.

Inspect the `direct-graphics-probe.json` member. Do not stop merely because `kmsdrm_prerequisites_visible` is false; preserve that failure as evidence. In particular, installed libdrm/GBM libraries are not a substitute for `sdl.kmsdrm_compiled=true`.

## Step 2 — run exactly one active acceptance transaction

Run exactly:

```sh
/usr/local/sbin/greia-run-kmsdrm-acceptance
```

Do not manually stop Xorg, add environment variables, run Pygame as root, add the user to `video`/`input`, chmod DRM/input devices, or rerun the harness directly.

The controller will:

1. require root;
2. require the normal Greia launcher to be active;
3. install an EXIT trap that restores the normal launcher;
4. stop `greia-launcher.service`;
5. wait boundedly until `xinit`/`Xorg`/`X` are absent from procfs;
6. start the disabled one-shot `greia-kmsdrm-acceptance.service`;
7. run the active Pygame harness as `greiakid` in a `PAMName=login` session on `/dev/tty1` with `SDL_VIDEODRIVER=kmsdrm` and no X11/Wayland transport variables;
8. require Pygame to report the actual driver as exactly `kmsdrm`;
9. render and hash deterministic fullscreen frames;
10. persist bounded JSON evidence;
11. restore the normal Greia launcher even when acceptance fails.

## Mandatory stop conditions

Stop immediately and do not improvise if any of the following occurs:

- the controller reports that the normal launcher was not active before takeover;
- legacy X processes remain after the bounded stop period;
- the acceptance service times out;
- the result JSON is absent or malformed;
- the actual SDL driver is anything other than `kmsdrm`;
- the controller prints `CRITICAL: Greia launcher did not restore`;
- Greia does not visibly return to its normal shell after the command exits;
- the machine reveals a Linux login/text console to the child-facing display during an interaction that the final product would expose.

Do **not** retry after changing permissions or package state. The failed result is the evidence for the next engineering decision.

## Step 3 — collect post-test evidence

After Greia has restored, collect a second runtime audit:

```sh
/usr/local/sbin/greia-collect-runtime-audit /var/lib/greia-audit
```

The post-test archive should contain the prior active result as:

```text
kmsdrm-acceptance.json
```

The audit collector only copies this file; it never starts or repeats the active test.

## Evidence to return

Return both runtime-audit archives and report:

```text
candidate source commit SHA
machine / VM type
baseline audit archive path
active controller exit code
post-test audit archive path
whether Greia visibly restored to the child shell
whether any Linux text/login prompt was visible
```

Do not edit, summarize, or hand-copy the JSON files; preserve the archives as generated.

## PASS criteria for this gate

All must be true:

- controller exits 0;
- `kmsdrm-acceptance.json` has `ok=true`;
- `requested_video_driver="kmsdrm"`;
- `actual_video_driver="kmsdrm"`;
- positive non-zero surface dimensions;
- expected bounded frame count and distinct frame SHA-256 values;
- normal `greia-launcher.service` is active again afterward;
- post-test runtime audit succeeds.

Even then, record the result only as **active SDL KMSDRM display acceptance**. Do not mark R7 complete.

## FAIL interpretation

A clean failure is useful evidence. Likely classes include:

- stock SDL lacks compiled KMSDRM;
- DRM device/connector not visible;
- PAM/logind/VT session does not grant the required device ownership;
- KMS/GBM/EGL initialization fails on the candidate driver;
- fullscreen surface creation works but the wrong SDL backend is selected;
- the display cannot be released/restored cleanly.

The next source change must respond to the observed failure class. Do not preemptively add privileges, a compositor, custom SDL, or a new direct-boot profile before this evidence exists.
