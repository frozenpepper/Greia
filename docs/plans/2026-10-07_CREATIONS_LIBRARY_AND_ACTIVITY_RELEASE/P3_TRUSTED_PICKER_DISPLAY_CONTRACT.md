# P3 — Trusted Picker Display Handoff Contract (source-WIP design)

**Status:** IMPLEMENTATION DESIGN, not an accepted display ADR, not a hardware/GUI sign-off.  
**Parent program:** [PLAN.md](./PLAN.md), exact checkpoint [PROGRESS.md](./PROGRESS.md).  
**Code owner:** existing `ActivitySupervisor` / `DisplaySessionCoordinator` / `SystemChromeCoordinator`; do not build another long-running service or another Activity-local chooser.

## Why this remains open

A running child Activity owns the foreground display. The normal Launcher/Shell display is not automatically visible. In `LauncherApplication._launch_selected`, the Shell polls the Activity synchronously for the session's lifetime. Simply calling `CreationsGalleryScreen.draw` from the Shell does **not** put that Screen above a running Activity. The accepted R7 display direction cannot be evaded with an X11-specific permanent dependency, arbitrary `pygame.display.set_mode` calls, or a second file picker inside each Activity.

The existing source now supports the trusted data/transaction half:

```text
Activity get_creations().request_selection(media_types, roles)
 → one authenticated storage socket, creation-aware session broker
 → bounded CreationSelectionCoordinator
 → trusted Supervisor.pending_creation_selection(active_session)
 → [MISSING: real display-owner modal mediation and child input capture]
 → shared CreationsGalleryScreen (PICKER) / typed role and MIME filters
 → trusted Supervisor.complete_creation_selection(session, request_id, creation_id)
 → one-use SelectionSessionAccess handle
 → Activity poll_selection(request_id) → import_selected(handle)
 → Activity stores an independent snapshot in own private namespace
```

An Activity can request/poll/cancel but cannot list files, delete, read by ID, alter the profile or mint a handle. **The broker rejects new picker requests until the trusted presenter explicitly enables that broker's picker gate.** No production Shell path currently enables it.

## Required display owner protocol

Introduce a narrow *existing-backend-owned* modal capability, not a generic window manager dependency. Its operations are conceptual until tested against Greia's real display/session backends:

1. **Can present?** The selected display transport must prove a trusted modal can cover the Activity surface while leaving the session alive. Absence means a typed `unavailable` error; never a 180-second pending request with no UI.
2. **Prepare** with an exact active Activity session/lease and request ID. Freeze/ignore Activity-directed ordinary pointer/keyboard/gamepad actions while allowing Greia system Home/Back to remain authoritative. Activity simulation should pause on its own non-blocking selection-wait state; if needed, add a canonical lifecycle pause signal, not a Python-only side channel.
3. **Present** the platform-owned `CreationsGalleryScreen` and verified `CreationLibrary` for the same launch-bound profile. Use its non-reading visual cards, full PNG detail, actual audible WAV Play/Pause/Replay before choosing, text preview and strong touch targets. Draw in the backend's trusted visible surface, not into a hidden Shell SDL framebuffer.
4. **Choice** creates the one-shot grant only after the child confirms one visible record. Trusted callback checks request id, session id, declared MIME types, optional semantic role scope and non-expired coordinator state. Deliver one status/handle through the already existing authenticated session socket; never deliver raw library paths.
5. **Cancel** from Back/Home, modal close, profile invalidation, Activity STOP/crash, timeout, display failure or user exit marks the transaction cancelled, stops audio playback and never creates a grant.
6. **Restore** Activity focus, input ownership, viewport, display lease, pending audio and prior Activity state. All failure paths converge through one session owner, including unplug/reconnect, unexpected Activity exit, and rapid repeated open/close. A canceled or selected request cannot replay through a stale generation.

The Shell must not invalidate an Activity's *normal* launch/READY/home/system-chrome lease to temporarily show the modal. Prefer extending the actual display owner state machine and existing backend if viable. If legacy X11 and future KMSDRM/Wayland require different presentation mechanics, use **polymorphic backend methods behind one semantic protocol**. No permanent `xrandr`/Xorg/override-redirect assumption, process kill/restart or manual file permission weakening.

## Shape Garden reality check

Inspection of `activities/shape_garden/garden_app.py`, `garden_model.py` and `garden_renderer.py` shows a **transient shape-growing garden**, not a currently persistent editable sticker-canvas app: shape placement is random, shapes are bounded in memory, and no project repository or PNG export exists. Previous shorthand calling Shape Garden a ready-made “stamp editor” is inaccurate.

Before invoking the picker there, P4 must define a legitimate creative project:
- preserve a chosen picture/background as an **Activity-private immutable imported copy**, separate from the shared original;
- preserve placed shapes/stamps in a versioned and bounded editable project state, with independent replay/reopen/undo if supported by its actual UX;
- publish a flattened composed PNG on an explicit child gesture (not on each particle/frame), and optionally allow Painting to open that snapshot as a new editable project;
- avoid pretending continuous particle animation is an editable stamping layer or silently converting the existing garden into an unrelated application.
If another Activity better fits the user's “stampini” concept, do a complete gameplay/source review first and adjust the P4 sequence explicitly.

## Source acceptance boundary and next test collection

The currently committed coordinator enforces: one pending request, an opaque request ID, declared MIME subset, optional bounded role subset, absolute expiry, bounded result retention, terminal cancellation, one-use selection token issuance, session shutdown cleanup, and a presenter availability gate. Filtered library SQL indexes support bounded listing by type/role.

**Still required before activation:** full-checkout source/unit/socket tests, a real backend modal lease and focus/input proof, screenshot and audio UX inspection, profile isolation across actual sessions and both positive/negative cancellation/STOP, and final image importer in at least one real Activity. No hardware evidence has been produced for this work.

## Development rule

Implement the actual display-owner seam next, not a workaround in Pygame Painting or `Shape Garden`. Deliver a focused regression proving only the trusted Shell can complete a pending request, while the Activity's own live session survives. Keep ordinary first-boot/Acer installation work independent.
