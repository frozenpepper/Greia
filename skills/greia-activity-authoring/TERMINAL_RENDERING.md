# Greia Activity Terminal / Victory Rendering Protocol

**Status:** mandatory for Pygame Activities with completion, victory, results or terminal screens  
**Audience:** Activity authors, coding agents, reviewers  
**Calibrated from:** a cross-Activity performance review of terminal/victory screens

This companion exists because a repeated first-party pattern caused severe slowdown on low-end Greia hardware: Activities kept the live game updating/rendering at roughly 30 Hz and then placed a newly allocated full-screen RGBA victory modal over it every frame.

Greia's measured software-rendering cost model makes that architecture unacceptable. A completion screen is a **terminal application state**, not a translucent effect layered over a still-running game.

---

## 1. Scope

Use this protocol when an Activity has any state equivalent to:

```text
victory
complete
results
finished
round-set complete
session complete
play again / continue
```

Do not invent a terminal state for sandbox/open-ended Activities that do not have one.

---

## 2. Required semantic architecture

Model terminal state explicitly in the Activity/application state machine.

Preferred lifecycle:

```text
ACTIVE
  -> child completes final semantic objective
  -> publish/save completion facts once
  -> enter TERMINAL

TERMINAL
  -> active simulation is frozen
  -> active-world animations/particles stop advancing
  -> terminal presentation is prepared once
  -> terminal frame is presented only when invalidated
  -> input/STOP remains responsive
  -> Play Again / Continue / Exit transitions explicitly
```

The renderer must not need to infer terminal semantics from incidental visual facts.

---

## 3. Performance rules

### 3.1 Never run the full game underneath a static completion screen

Bad:

```python
while running:
    update_world()
    update_particles()
    draw_world()
    draw_hud()
    if is_victory:
        draw_victory_overlay()
    present()
    frames.wait()  # FrameGovernor; never a bare Clock.tick in Activities
```

This keeps paying the complete active-game cost after the game has ended.

Good (the `FrameGovernor` from `greia_platform.frame_governor` decides; see the authoring skill §11):

```python
while running:
    for event in frames.events():
        handle_input(event)

    if state is TERMINAL:
        frame = frames.frame(dirty=terminal_dirty)
        if frame is FrameKind.FULL:
            completion.draw(surface)
            present()
            terminal_dirty = False
        frames.wait()  # static: blocks for input instead of repainting
        continue

    update_active_world()
    if frames.frame(dirty=world_changed, animating=True) is FrameKind.FULL:
        draw_active_world()
        present()
    frames.wait()
```

### 3.2 No per-frame full-screen alpha overlay

Do not do this in a terminal loop:

```python
overlay = pygame.Surface((1024, 600), pygame.SRCALPHA)
overlay.fill((10, 15, 30, 210))
surface.blit(overlay, (0, 0))
```

Measured Greia/Acer work shows that large alpha-blended areas can dominate the entire frame while opaque copies are comparatively cheap.

A terminal screen should normally be fully opaque.

### 3.3 Use the shared Greia completion owner

For standard Pygame terminal screens use:

```text
src/greia_platform/pygame_completion.py
    CompletionContent
    CompletionPalette
    PygameCompletionScreen
```

`PygameCompletionScreen`:

- retains at most one prepared logical terminal frame;
- uses an opaque full-frame surface, never a full-screen alpha overlay;
- prepares finite title/body/button text only when semantic content changes;
- makes repeated `draw()` calls one opaque blit;
- owns a stable primary-action hit target;
- can preserve an Activity's established Play Again/Continue rectangle when compatibility requires it.

The shared component owns **presentation efficiency**, not game semantics. The Activity still owns when it becomes complete, what progress is saved/emitted, and what Play Again means.

### 3.4 Preparation is not permission to repaint continuously

Even an opaque cached terminal surface should not be blitted/flipped 30 times per second when nothing changes.

Use invalidation/dirty rendering:

```text
enter terminal        -> dirty
resize/recreate canvas -> dirty
locale/theme/content change -> dirty
otherwise             -> do not repaint
```

Keep STOP/input polling bounded and responsive while static.

### 3.5 Stop terminal-invisible work

Once terminal state is entered, do not continue updating work that the child cannot see or use:

- world physics;
- NPC animation;
- particle simulation;
- camera interpolation;
- hover pulses behind the terminal screen;
- procedural scenery animation;
- active-game timers unless they have explicit post-completion semantics.

A short intentional completion animation may exist before the terminal state, but it must be bounded and settle.

---

## 4. Text and resource preparation

Do not render stable completion labels every terminal frame.

Prepare/cached semantic resources such as:

- title;
- subtitle/body lines;
- Play Again / Continue label;
- finite achievement markers;
- optional static decoration.

Dynamic score/body text should invalidate terminal content once when the value changes, not on every poll iteration.

Do not use terminal entry as the first opportunity to decode large images, load fonts, walk filesystems, synthesize audio or perform other heavyweight work that could have been prepared earlier.

---

## 5. OOP ownership

Terminal presentation is a strong example of useful OOP:

```text
Activity/domain owner
    owns completion truth and transition

PygameCompletionScreen
    owns one bounded prepared terminal surface + geometry

Activity app/lifecycle
    owns invalidation and input routing
```

Do not create per-Activity `VictoryManager`, `EndScreenController`, etc. when the shared Greia presentation owner already matches the job.

Subclass `PygameCompletionScreen` only if substitutability and a stable extension contract genuinely justify inheritance. Prefer composition/configuration through `CompletionContent` / `CompletionPalette`.

---

## 6. Interaction contract

A terminal screen must remain usable while the active game is frozen.

At minimum verify:

```text
final objective
-> completion facts saved/emitted once
-> terminal screen appears
-> Home/Back/STOP remains responsive
-> primary action works
-> restart/continue restores a valid active state
-> terminal resources are cleared/re-keyed as needed
```

Do not let terminal input fall through into the active game underneath.

---

## 7. Resize/display invalidation

If the display/canvas is recreated while terminal state is active:

1. rebuild/rebind the logical canvas as required;
2. mark terminal presentation dirty;
3. draw the already prepared logical completion frame to the new canvas/target;
4. do not resume active simulation merely to reconstruct pixels.

The completion semantic content normally remains valid across a resize.

---

## 8. Verification

For every Activity with a terminal state, Simulator/manual acceptance must exercise the full path:

```text
launch
-> normal gameplay
-> final objective
-> enter completion screen
-> leave screen displayed long enough to observe responsiveness/performance
-> Play Again / Continue
-> resumed valid gameplay
```

Provider-free tests should cover where practical:

- exact completion transition;
- completion event/persistence emitted once;
- active model no longer advances in terminal state;
- primary action transitions correctly;
- shared completion frame is reused until semantic invalidation;
- resize/restart invalidation.

Hardware performance claims require physical measurement. Simulator smoothness is not an Acer/Pi performance claim.

---

## 9. Known problematic terminal-overlay pattern

A cross-Activity source review found the same terminal-overlay architecture problem in several independent first-party packages. The pattern is some combination of:

- active world still updating after victory;
- active world fully redrawn before terminal UI;
- `pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)` created inside the main loop;
- full-screen alpha blend every terminal frame;
- stable victory labels rendered every frame;
- terminal loop still paced at the active ~30 Hz render cadence.

`activities/clinica_cuccioli` is the reference consumer of the shared opaque completion owner.

Open-ended Activities without a terminal/victory state are not part of this migration merely because they use Pygame.

---

## 10. Review gate

Before accepting a terminal/victory implementation, answer yes:

1. Is completion an explicit semantic state?
2. Does active simulation stop once that state is entered?
3. Is the active game no longer rendered behind the terminal screen?
4. Is there no per-frame full-screen `SRCALPHA` allocation/blend?
5. Are stable completion text/resources prepared rather than recreated per frame?
6. Does the implementation reuse `PygameCompletionScreen` unless there is a documented reason not to?
7. Is terminal repaint driven by invalidation rather than the active-game frame cadence?
8. Are input/STOP/Home still responsive while static?
9. Does Play Again/Continue restore a valid active state?
10. Has the full terminal path actually been exercised, not merely startup?

A terminal screen that is visually correct but causes the Activity to collapse from smooth interaction to visibly slow rendering is a correctness failure on Greia's supported hardware floor.
