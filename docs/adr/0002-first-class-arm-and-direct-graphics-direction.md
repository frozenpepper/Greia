# ADR 0002 — First-Class ARM and Direct Graphics Direction

**Status:** Accepted architecture; implementation evidence pending  
**Date:** 2026-08-08

## Context

Early Pip-era Phase-0 implementation work used an Acer Aspire One as the primary low-end reference machine and selected a minimal Xorg/Pygame path as a pragmatic development implementation. ARM support existed at the architecture seam but was explicitly deferred in implementation.

Subsequent project decisions clarified two points:

1. ARM is not a secondary future port. Raspberry Pi 400 and Raspberry Pi 500-class devices are core Greia targets with the same architectural importance as old i386 systems.
2. Because Greia owns the entire child graphical session, carrying X11 merely to reproduce a conventional Linux application stack is unnecessary architectural overhead.

## Decision

### ARM

ARM64 is a first-class Greia architecture alongside i386 and amd64.

Raspberry Pi 400 and Raspberry Pi 500 are explicit ARM reference devices.

Greia platform APIs, Activity manifests, profile semantics, saves, progression, backups, parent controls, and package semantics must remain architecture-neutral.

Boot/image implementations may differ below the platform layer. A Raspberry Pi image does not need to use the same firmware/bootloader/partitioning implementation as a PC image.

Activities declare capabilities rather than CPU architecture unless native code makes architecture-specific payloads unavoidable.

### Graphics

X11 is not part of the intended Greia architecture.

The preferred direction is a direct appliance-style graphics/input path using Linux DRM/KMS and the thinnest practical runtime backends.

The Greia Shell owns the graphical session. No desktop environment or general-purpose window manager is required.

A compositor, Wayland component, or compatibility display layer may be selected later only if measured evidence shows that it materially improves surface ownership, runtime integration, isolation, transitions, or hardware support at acceptable resource cost.

Historic Xorg implementation work remains useful as evidence and migration code but is **PROVISIONAL/HISTORICAL**, not the target architecture.

## Rationale

ARM devices such as Raspberry Pi 400/500 are unusually aligned with Greia's purpose: affordable keyboard computers, broadly available, replaceable, documented, and suitable for families/schools. Treating them as secondary would distort the architecture around legacy PC boot/display assumptions.

Likewise, Greia is not a desktop distribution. Every unneeded graphical layer consumes memory, disk, startup time, maintenance effort, and creates additional failure/escape surfaces. The platform should therefore begin from the minimal direct path and add layers only when they solve a measured problem.

## Consequences

- Build/image architecture must have board/boot adapters below shared Greia contracts.
- CI and packaging should eventually cover i386, amd64, and arm64 from early development.
- Reference-hardware acceptance must include old i386 hardware plus Pi 400/500.
- Existing Xorg-specific Activity assumptions must not become public APIs.
- The future Web runtime should be investigated as an embedded engine integrated with the direct Greia graphical model rather than as a conventional browser launched inside X11.
- Direct DRM/KMS behavior on the old Acer and Raspberry Pi hardware remains an evidence requirement; this ADR does not claim untested hardware success.
