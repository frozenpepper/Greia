# R7 Shell Focus Return — Physical Defect and Narrow Correction

**Date:** 2026-09-01  
**Evidence runtime SHA:** `d947eb7ef5ad3703cb7293a8bba73bf9db9277e4`  
**Disposition:** PHYSICAL DEFECT IDENTIFIED; narrow Legacy-X Shell-focus lifecycle correction pending verification

## 1. Evidence

The Writing physical-surface correction at `d947eb7e` is accepted as fixing the earlier black/dot rendering failure:

```text
source gate: PASS, 1512 tests
backend audit: blockers=0
system-chrome audit: blockers=0
Simulator Writing visual: PASS
Acer Writing: visible, typing >15 s, autosave/save, return, relaunch persistence PASS
Acer Painting presentation: PASS
```

During the first Writing return, however, the Shell X window did not own keyboard focus. The operator had to perform one observation-only `windowfocus 4194311` recovery before the relaunch could proceed. The Shell then worked and Writing persistence was proven.

That manual focus intervention is not acceptable evidence for R7.2 durability. The canonical physical contract requires clean Shell recovery and specifically rejects accumulating focus loss across repeated Activity cycles.

## 2. Source diagnosis

The source matches the physical observation:

- `LegacyXShellWindowController.after_window_created()` repairs input focus once when the Shell SDL window is created.
- the controller contract explicitly described this as a one-shot hook;
- `LegacyXDisplaySessionBackend.restore_shell()` is intentionally a semantic no-op because Shell and Activity share the same X server;
- after an Activity ends, `LauncherApplication._launch_selected()` resumes Shell state but does not invoke the trusted Shell-window focus adapter again.

Therefore, in Greia's current no-window-manager X session, the Activity can disappear while X input focus is not restored to the surviving Shell window.

This is a compatibility-lifecycle defect, not a reason to add a window manager, polling loop, generic Xlib code, or Activity authority.

## 3. Correction design

Extend the existing trusted `ShellWindowController` seam with one bounded lifecycle callback:

```python
after_activity_return(pygame) -> bool
```

Rules:

- production Legacy-X implementation reuses the existing `CtypesX11FocusBridge`;
- the Shell window id is resolved from `pygame.display.get_wm_info()` at the moment of repair;
- the operation happens exactly once after an Activity lifecycle returns;
- development/no-op implementations remain no-op;
- failures remain fail-soft and must not crash the child Shell;
- no polling/background worker/per-frame focus work;
- no generic launcher X11 implementation;
- no `xdotool`/subprocess runtime dependency;
- no change to Activity DRM/raw-input/system-chrome authority.

The production `GreiaChildShell` invokes the callback after its inherited Activity launch/lifecycle method returns.

## 4. Required verification

Before physical use:

```text
shell-window composition/lifecycle tests PASS
Legacy-X focus bridge test proves boot + post-Activity focus callbacks target current Shell window
production child-shell test proves focus restoration is invoked after inherited launch lifecycle
R7.2 focused source gate PASS
R7.3 focused source gate PASS
backend audit blockers=0
system-chrome audit blockers=0
make verify PASS
real-Shell Simulator Writing return PASS without regression
```

Then deploy the exact verified source to the Acer and test a short sequence **without any manual focus command**:

```text
Writing -> Shell -> keyboard navigation
Writing -> Shell -> immediate Writing relaunch
Painting -> Shell -> keyboard navigation
```

If any return requires `windowfocus`, mouse click, launcher restart, or another external focus repair, the fix is rejected and the long 10/10 + 20/20 durability lanes must remain blocked.

Only after automatic focus recovery is physically green should the remaining R7.2/R7.3 durability matrix resume.
