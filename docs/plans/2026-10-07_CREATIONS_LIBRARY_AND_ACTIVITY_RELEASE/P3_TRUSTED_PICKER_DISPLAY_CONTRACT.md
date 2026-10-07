# P3 — Trusted Picker Display Handoff Contract

**Status:** SOURCE-WIP implementation contract; **not** a GUI/Simulator/hardware acceptance claim.  
**Parent program:** [PLAN.md](./PLAN.md), exact checkpoint [PROGRESS.md](./PROGRESS.md).  
**Code owners:** existing `ActivitySupervisor`, `SystemChromeCoordinator`, `ShellWindowController`, session broker and shared `CreationsGalleryScreen`. Do not build another long-running service or Activity-local chooser.

## 1. Problem and implemented architecture

A running child Activity owns the foreground display while `LauncherApplication._launch_selected()` synchronously polls that Activity's lifecycle. The normal Shell framebuffer is therefore not automatically visible. The correct solution is one trusted modal presentation seam below the Shell, not an Activity-side file picker or direct shared filesystem.

The current source path is:

```text
Activity get_creations().request_selection(media_types, roles)
 → existing authenticated per-session storage socket
 → CreationSelectionCoordinator (bounded request / timeout / cancel)
 → active-session ActivitySupervisor
 → ActivityCreationPickerHost
 → exact-session ShellActivityModalLease from current ShellWindowController
 → same shared CreationsGalleryScreen in PICKER mode
 → trusted child confirmation callback
 → Supervisor.complete_creation_selection(...)
 → one-use session-specific import handle
 → Activity poll_selection(request_id)
 → Activity import_selected(handle)
 → independent copy saved in Activity-private project storage
```

An Activity can **request / poll / cancel only**. It cannot enumerate creations, choose an ID, delete profile data, mint a grant, set the presenter gate, select another profile, or learn a raw library path.

## 2. Runtime-neutral modal lease

`ShellActivityModalLease` carries only:
- exact Activity `session_id`;
- monotonically increasing backend generation;
- exact supervised Activity PID.

Native window/surface handles are private backend state. X11 window IDs never appear in the generic lease, so future Wayland/KMSDRM implementations do not inherit a legacy window-system API.

The host enables the broker's picker gate **only after** a concrete backend successfully prepares that exact-session lease. Missing/no-op backends remain fail-closed and picker requests return unavailable rather than becoming invisible long waits.

## 3. Legacy-X compatibility implementation

`LegacyXShellWindowController` deliberately reuses Greia's **existing Shell SDL window** instead of creating a parallel full-screen renderer.

Preparation:
1. Validate exact session/PID.
2. Resolve the current Shell native X11 window from SDL.
3. Create one identity-bound modal lease. The Activity native window is **not trusted yet**.

Presentation:
1. Immediately before covering the Activity, query the **currently focused non-Shell X11 window**.
2. Read its `_NET_WM_PID` and require an exact match with the supervised Activity PID.
3. Keep that verified window ID private as the restoration target.
4. Raise/focus the existing Shell window.
5. Restack Greia's already-active mandatory Home/Back chrome above the Shell modal.
6. Render the common picker through the existing Shell Pygame surface.

Dismissal:
1. Stop picker audio and close the shared Screen.
2. Restore the exact PID-verified Activity window.
3. Ensure trusted Home/Back is still above the Activity.
4. Clear Shell events that must not leak back into the Activity.

If PID/window ownership, Shell raise/focus, Activity restoration, or trusted chrome restacking cannot be proven, the modal fails closed. No `xrandr`, process restart, permission weakening, raw X11 API in Activity code, or second full-screen Xlib UI is introduced.

## 4. Simulator implementation

The Simulator uses the **same broker/request/host/gallery** path and no alternate picker.

`SimulatorShellWindowController` uses the existing `SimulatorSystemChromeRemoteBridge` as display authority:
- preparation requires the bridge to own the exact active Activity system-chrome session;
- while modal is active, Activity `/api/events` polling receives no ordinary child input;
- that same queued input is drained by the Shell's real picker Screen;
- protected Home remains routed to Greia system navigation first;
- Activity frame uploads are ignored while the Shell modal owns the synthetic display;
- Shell frame capture becomes the authoritative remote canvas;
- dismissal returns remote input/frame ownership to the Activity.

This is the canonical desktop test path for an in-Activity picker. It does **not** claim native macOS foreground-window stacking parity with installed Legacy-X; the synthetic device's authoritative display is the Simulator remote canvas/transport.

## 5. Shared host lifecycle

`ActivityCreationPickerHost`:
- exists only for a RUNNING Activity that actually declares `creations.consumes`;
- never opens until the broker exposes a pending request;
- binds the active child's managed `creations_dir`, never an Activity-provided path;
- constructs the same filtered `CreationsGalleryScreen`;
- drops events captured before modal ownership, preventing click-through;
- redraws only on open/input/audio-progress, not continuously while idle;
- creates a one-use handle only through the trusted Supervisor callback;
- restores the Activity immediately after choose/cancel;
- on abnormal unwind, cancels a pending request, disables presenter authority, stops audio, dismisses/restores if still safe, abandons the backend lease, clears Shell input, and never waits for a timeout to clean itself up.

The launch loop wraps this host in unconditional cleanup so Simulator stop, unexpected exceptions and ordinary Activity termination converge on the same teardown.

## 6. Painting reference consumer

Painting is the first end-user consumer path in SOURCE-WIP:
- its private gallery shows a picture-arrow-down import action;
- the action requests only `image/png`;
- the Activity remains responsive and polls no faster than every **120 ms**;
- cancel returns to Painting without changing the current project;
- ready returns one session-scoped handle;
- Painting validates media type + digest, decodes before mutating state, and saves a **new independent editable private painting**;
- the shared source is never overwritten;
- its existing private autosaves remain private;
- its up-arrow publish action still snapshots deliberately rather than publishing every autosave.

## 7. Trusted chrome and cancellation semantics

Mandatory Home/Back remains higher trust than the picker. Home during an active picker ends the Activity through the existing supervisor stop lifecycle; the picker host then tears down. Back/Escape inside the picker cancels only the selection transaction and restores the Activity.

Cancel/cleanup paths that must be proven:
- picker Back/Escape;
- child confirms selection;
- Activity exits while picker is visible;
- Activity crashes;
- system Home is used;
- request timeout;
- selected result is never collected;
- profile/session becomes invalid;
- modal show/restore fails;
- Simulator stop/restart;
- repeated open/cancel/open;
- audio preview active during every exit path.

## 8. Backends still open

Legacy-X compatibility and Simulator remote transport have SOURCE-WIP implementations.

Future target display backends must implement the same `ShellWindowController` semantics:
- **Wayland:** compositor-owned trusted surface/focus/input mediation;
- **direct KMSDRM:** trusted display-plane/session transition appropriate to final R7 architecture.

They must not expose X11 concepts through the generic contract.

## 9. Shape Garden reality check

Current `shape_garden` is a transient randomized shape-growing experience with no persistent editable project repository or PNG export. It is **not** already a sticker editor.

P4 must either:
- add a legitimate bounded/versioned editable picture+shape project there, preserving an imported picture as an independent private snapshot and exporting flattened PNG only on an explicit gesture; or
- identify a genuinely better existing Activity after source/gameplay review.

Do not distort the current garden merely to manufacture a round-trip demo.

## 10. Evidence boundary

**No complete-checkout test, real Pygame modal interaction, screenshot, audible preview, installed X11 focus/stacking test or hardware test has been run for this latest source slice.**

Source regressions now cover or are intended to cover:
- request scope, timeout, cancellation, stale/forged IDs and one-use grant;
- cross-session authority denial;
- exact-object modal lease ownership;
- Legacy-X PID revalidation at show time and Activity restoration;
- trusted Home chrome restacking;
- Simulator input/frame diversion;
- host open/select/cancel/abnormal cleanup;
- Painting request/poll/cancel/import behavior.

All of those tests plus previous Gallery/PNG publication checks are carried into:
[the consolidated P3 desktop/source acceptance](../../testing/2026-10-07_CREATIONS_P3_DESKTOP_SOURCE_AND_VISUAL_ACCEPTANCE.md).

Do not call P3 accepted until that procedure is green and the actual rendered child flow is visually reviewed. Physical Acer evidence remains a later milestone and does not replace the separate first-boot/install lifecycle acceptance.
