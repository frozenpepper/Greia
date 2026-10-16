# ADR 0037 — Shared Activity control kit

**Status:** Accepted (2026-10-15, primary agent; pilots: pasticceria_magica, casa_del_dieci)
**Scope:** child-facing controls inside Activities (buttons, pills, tool/mode strips, HUD counters, progress, prompts, result feedback, completion)
**Extends:** ADR 0018 (lightweight UI foundation), ADR 0019 (platform-owned Home/Back chrome), ADR 0020 (runtime-neutral input and controllers), ADR 0026 (resolution-adaptive layout), ADR 0034 (CAPITAL child text)
**Evidence/audits:** `docs/reviews/activities/2026-10-15_activity_design_audit/GROUP_A_*.md` and `GROUP_B_*.md` (cross-cutting sections), `docs/reviews/visual/2026-10-15_asset_library_audit/REVIEW.md`
**Implementation (SOURCE):** `src/greia_platform/activity_controls.py`, `src/greia_platform/activity_feedback.py`, `src/greia_platform/pygame_completion.py`; art under `assets/visual/ui/controls/v1/` and cast `pose_think` masters.

## Context

Every Activity drew its own buttons, pills, toolbars and HUD counters (at least eight inconsistent styles), almost none could be operated with the keyboard or a controller, wrong answers were mostly text banners, and 16 Activities ended on the same text-only `PygameCompletionScreen` card. The audits ask for one feedback grammar (correct = cast `pose_cheer`; try-again = a gentle cast pose; completion = a shared cast scene) and for focus navigation provided by the platform rather than hand-rolled per Activity.

## Decision

### 1. Vocabulary (one kit, no parallel framework)

| Control | Meaning | Focusable |
|---|---|---|
| `PillButton` | rounded action: optional icon + short pre-cased label; `NEUTRAL` (cream) or `PRIMARY` (accent) role; drops its label (`compact`) when a row cannot fit it | yes |
| `IconButton` | `ROUND` or `TILE` action with one icon and an optional caption | yes |
| `ToolStrip` / `ToolSlot` | exclusive tool or mode selection; exactly one slot `selected` | slots yes |
| `HudChip` | icon + number counter | no |
| `ProgressDots` | done (accent) / current (ringed) / to-do dots | no |
| `PromptBanner` | icon + short text, optional replay-voice `IconButton` (the Activity owns the cue) | replay yes |
| `CastFeedback` | canonical cast friend: `correct()` → `pose_cheer`, `try_again()` → new gentle `pose_think`, then idle; optional Activity-owned sound hooks | — |
| Completion scene | `PygameCompletionScreen(..., scene=CompletionScene(kit, character=...))`: card art, cheering cast, earned/unearned stars, replay (primary) + optional next (secondary) | buttons yes |

Controls implement `ui_core.Control`. `ControlLayer` is a `ui_core.Screen`, so an Activity hosts it in a `SurfaceNavigator`; the completion scene is pushed as a modal `CompletionOverlay`. Gameplay elements the Activity draws itself (for example ten-frame windows) join focus traversal as `ExternalTarget`s and receive the same focus ring.

Labels are passed already resolved through `LocalizedResources.text`, which applies the ADR 0034 case policy; the kit never re-cases or hard-codes copy. Content pictograms remain Activity content; system/HUD glyphs come from the shared `icon.hud.*` set.

### 2. States

Each control renders `normal`, `hover`, `pressed`, `disabled`, `selected` (and `*-selected`) bodies. `focused` is a separate ring overlay (ink | focus colour | ink, legible on light and dark scenes), shown only after keyboard/controller navigation ("focus-visible") and hidden again by pointer use.

### 3. Input and focus

`PygameControlInput` translates Pygame events without opening devices: keyboard and SDL-controller buttons use the standard `NAVIGATION` mapping (arrows / D-pad → `NAV_*`, Space / Enter / south face → `ACTIVATE`), the left stick goes through the central dead zone and repeat policy, and pointer/touch samples are mapped into the Activity's logical space and dropped inside the protected chrome region. This gives `pointer` and `hybrid` Activities a learned focus context for their controls without broadening raw `/dev/input` access (ADR 0020). Focus moves spatially to the nearest aligned target in the pressed direction (diagonal fallback, no wrap); disabled, hidden and display-only controls are skipped. Pointer activation happens on release over the pressed control (with a small tap slop); the layer returns `IGNORED` for anything it does not consume so gameplay taps and drags stay with the Activity.

### 4. Layout outside protected chrome

`ControlLayout.for_canvas(canvas, physical_size)` maps the platform Home/Back protected region (`ActivitySystemChromeLayout`) into the reference-canvas logical space; `for_surface` does the same for physical-resolution Activities. `top_bar` starts after the protected edge, `bottom_bar` sits on the bottom margin, `clear_of_chrome` pushes overlapping content down, `control_height` raises heights toward a 40 px physical touch floor (capped by the caller's band), and `fit` keeps labels (shrinking them) before falling back to icon-only compact controls. The same authored layout therefore holds at 1024×600, 800×480, 480×320 and 1280×800 without per-device coordinates (ADR 0026).

### 5. Art versus code

* **Code from theme tokens** — pill/icon/tile bodies, tool slots, chip, dots, banner panel and focus ring. They only vary by size, accent token and state; the `ControlPainter` implements the SVG recipe (≤ 2-stop light→base fill, one ink contour, one highlight, tactile lip, no blur) at 2× and smooth-scales once, so edges match rsvg output. Rendering these as PNG art would need eight accents × six states × arbitrary label widths, or a multiply-tint pipeline that would recolour the ink contour.
* **SVG → PNG art** (shared renditions pipeline, `kind = "ui"`) where illustration adds value: `icon.hud.{listen,replay,check,trophy,bell,clear}` (96), `ui.control.star` (`default`, `off`; 128), `ui.completion.card` (760×440: ribbon, bunting, stage disc), and `character.<id>` `pose_think` for all six canonical characters (on-model per the SVG rules §8).
* Accent: `ControlTheme.for_accent(<theme-defaults accent token>)`, normally the Activity's primary Collection hue; `ControlTheme.from_resolved(get_theme())` follows the child's theme instead.

### 6. Performance rules

Bodies, labels, composites and rings live in hard-bounded LRU caches (`BoundedCache`) owned by one `ControlKit` per Activity surface; `draw` is blits only (no font construction, text rendering, decoding or scaling per frame); content changes (a new number or label) build one new entry. `ControlLayer.invalidation` supports event-driven Activities; cast motion is an offset, never a per-frame scale. Art is resolved semantically (`get_shared_visual_path`), scaled once, and missing art degrades to vector/text fallbacks.

### 6a. Frame governance (amendment 2026-10-16)

The Acer sweep (`docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md` §3.4) measured 19 of 29 Activities above 60% idle CPU on the Atom N270 because their loops re-rendered and flipped the full 1024×600 frame 20–30 times a second while nothing changed. Every Pygame Activity loop is therefore governed by one platform object, `greia_platform.frame_governor.FrameGovernor`, extending the canvas seam rather than adding a framework:

* **Activities declare, the governor decides.** Per iteration the loop calls `frames.frame(dirty=…, animating=…, ambient=…)` and honours the answer: `FULL` (render, `present`, flip), `POINTER` (`PygameReferenceCanvas.present_pointer()` repairs only the old/new pointer rectangles from the last frame and calls `display.update(rects)`), or `SKIP` (no render, no present, no flip). `frames.wait()` replaces `Clock.tick`.
* **Static screens cost ~0.** With nothing dirty the loop only sleeps `idle_poll_seconds` (50 ms) between event/timer polls, so `step()` timers keep running; `pygame.event.wait(timeout)` is deliberately not used because Pygame ≥ 2.1.3 implements it as a 1 ms poll loop.
* **Blocking idle wait (amendment, Acer sweep at 15212f44).** The 50 ms poll alone still left 25 of 36 Activities at ~12.5% CPU on a frozen screen on the Atom. When nothing animates, decoration is frozen and no audio is playing, `wait()` now blocks in SDL's own `SDL_WaitEventTimeout` (via `greia_platform.input_wait.PlatformInputWaiter`, used only after it confirms the SDL instance Pygame initialized; the event stays queued) for up to 250 ms, so any input wakes the loop immediately and idle wakeups drop from ~20/s to ~4/s. Without a blocking-capable driver (dummy, KMSDRM) or with a controller attached it falls back to the 50 ms sliced poll. Idle-hint timers and the Home stop request may be observed up to 250 ms late; `frames.wake_at()` bounds the block for any timer that must fire on time. *Wake latency (Acer, a8be76d7 follow-up):* `SDL_WaitEventTimeout` is used on the device (also inside the Shell's Bubblewrap launch: the main thread sleeps in `poll(…, 250)`) and returns within ~1 ms of the X event; an instrumented Activity handles the first motion after a still screen ~3 ms later (a sliced 250 ms sleep measured +45…+269 ms). The 210–310 ms "first input after idle" in the a8be76d7 re-measure was input queued behind a **full-frame render** (150–220 ms at 1024×600 on the Atom): Painting/Writing re-rendered every second through `keepalive_seconds=1.0`, and My Greia marks the whole frame dirty on every pointer move. The block therefore stays at 250 ms; static screens must simply not render on a timer (see *Migration aids*).
* **Idle audio release (amendment, a8be76d7 follow-up).** An open Pygame mixer costs ~5% CPU on the Atom even in silence (SDL audio thread feeding ALSA `dmix` + SDL's ALSA hot-plug thread; buffer size and pause do not help). `greia_platform.python_activity_entry` installs `greia_platform.activity_mixer_lease` before Activity code runs: `pygame.mixer.Sound`/`Channel` and the mixer module functions go through one lease that closes the mixer after 10 s with no channel or music busy (never while another SDL audio device such as a microphone capture is open) and reopens it in the same format, channel count, reservation and channel volumes immediately before the next sound (~0.1 s once, on the first sound after silence). `FrameGovernor.wait()` drives the check. Activities keep using plain Pygame mixer calls; they must not reach SDL audio by other routes.
* **Capped motion.** `dirty`/`animating`/`animate_for(s)` present at `animation_fps`, never faster (hover storms are capped too). `ambient` (bubbles, clouds, idle cast, page sparkle) runs at full rate for `ambient_after_seconds` after the last child input, then at `ambient_fps`. Fixed-step simulations keep their step via `wait(polling=True)` (Clock.tick-like cadence) and only *present* at the governed rate.
* **Hardware class.** `FramePolicy.from_environment()`: `GREIA_FRAME_PROFILE=standard` (30 / 12 fps, ambient after 8 s) or `reference-floor` (24 / **0** fps, ambient after 6 s); unset → reference-floor on ≤ 2 logical CPUs (Atom N270), else standard.
* **Static decoration on the reference floor (amendment, Acer re-sweep at 0f560c2e).** A full 1024×600 redraw + flip costs tens of ms on the Atom, so 10 fps decorative loops still idled above 100% CPU. `ambient_fps = 0` means: after the decorative window the scene freezes on its last frame (no presents, the loop only idle-polls), the platform pointer still follows the mouse, and any child input resumes decoration at full rate instantly. `dirty`/`animating` frames are never frozen, so an Activity must declare only *essential* motion (a game the child is steering, feedback, physics) as `animating`, and idle cast breathing, bubbles, twinkles and sways as `ambient`. `wait()` never returns without a real sleep (≥ 2 ms) after an iteration that presented nothing, so a loop cannot spin.
* **Partial presentation.** Activities that draw straight to the display (painting, writing) keep Greia's pointer in a save-under `PygamePointerSprite` (`pygame_canvas.py`): `POINTER` frames restore the old pointer patch and draw the new one with `display.update(rects)`; painting strokes push only the stroke's dirty rectangle. Games keep a cached static background and redraw only when their model changes; where only small sprites move (corsa_bacche, foresta_parole) the renderer reports their logical rectangles and the loop uses `PygameReferenceCanvas.plan_regions` / `render_regions` (the normal renderer under a clip, ≤ 2 passes) / `present_regions` (`display.update(rects)`), falling back to a full frame on any other change.
* **Pointer and chrome.** `events()` notes pointer motion, so Greia's platform pointer follows promptly even on static screens; input latency on a static screen is bounded by `idle_poll_seconds` plus one frame (and is immediate when the blocking idle wait is active). Trusted Home/Back is unaffected: it lives in the launcher/simulator layer above the Activity surface (the simulator re-draws it on both `flip` and partial `update`).
* **Migration aids.** Loops that historically redrew every frame without complete dirty tracking use `FrameGovernor(redraw_on_input=True, keepalive_seconds=1.0)`: every non-motion input and every drag invalidates, and keepalive bounds how stale a missed state change can get while the child is active. On the reference floor the keepalive pauses together with decorative motion once the child has been idle for `ambient_after_seconds` and restarts its period from the next input, so a still screen does not re-render every second (Painting idled at ~18% CPU and delayed input by up to one render for exactly that reason). New Activities should track dirty state explicitly instead.
* **Measurement.** `tools/measure_activity_idle_cpu.py` runs Activities headless (SDL dummy) and reports idle CPU via `getrusage` plus presents/s; it is a desktop proxy, not Atom evidence.

### 6b. Idle-hint back-off (amendment 2026-10-16)

Idle hints used to repeat at a fixed rhythm (many Activities never stopped), and each hint is essential full-rate motion, which keeps the reference-floor CPU busy and nags a child who walked away. One platform helper, `greia_platform.activity_feedback.IdleHintScheduler`, now owns the schedule for every Activity that nudges an idle child: hint 1 after 6 s without input, hint 2 a further 12 s later, hint 3 a further 24 s later, then **no more hints until the next child input** (`reset`). The Activity keeps its own graduated content per step (point, then demonstrate, then glow the target) and its own gating (busy, no valid target). `is_due`/`fire` let it check for a target before spending a step; `since` lets a "quiet since" stamp delay a step without restarting the schedule; `patience` stretches the gaps for slower levels; a shorter `gaps` tuple gives fewer steps (e.g. Morbidi Mostriciattoli keeps two). `animation_seconds(nominal)` applies `FramePolicy.hint_animation_cap_seconds` (1.5 s on `reference-floor`, none on `standard`) to every hint animation. Child-requested help (a help button) is not an idle hint and is not capped or counted. Sottomarino's single order highlight is a state flag that expires with its order, not a repeating hint, and is unchanged.

### 7. Relationship to existing decisions

* ADR 0018: the kit is the Control level of Screen → Overlay → Control; no windows, z-order games or desktop widgets.
* ADR 0019: kit controls never enter or imitate the protected Home/Back region; the `HUD` glyph set deliberately has no Home/Back look-alikes.
* ADR 0020: semantic actions only; the kit never opens controllers.
* ADR 0025: completion stars and cheers are presentation, not reward or award authority.
* `PygameCompletionScreen` without `scene` renders exactly as before, so the other users keep working until they migrate.

## Consequences

* New and migrated Activities get consistent controls and keyboard/controller focus by composition; pilots: `pasticceria_magica` (tabs, HUD, pantry, pattern answers, Clear/Serve, feedback, Momo) and `casa_del_dieci` (windows, prompt + replay, answers, OK, progress, Dani, completion scene).
* Remaining Activities migrate incrementally; until then the old drawings stay valid.
* Open: a shared next-arrow glyph, a toast/snackbar variant, a drag helper (audit request), and replacing content emoji with the shared prop sets are separate tranches.
