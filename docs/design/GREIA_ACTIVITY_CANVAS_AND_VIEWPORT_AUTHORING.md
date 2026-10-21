# Greia Activity Canvas and Viewport Authoring

**Status:** selected design guidance under ADR 0026 and ADR 0027  
**Date:** 2026-08-18  
**Audience:** Activity designers, Activity programmers, SDK/runtime authors, reviewers

---

## 1. The rule in one sentence

**Design the Activity once. Greia adapts it to the actual screen.**

Do not design separate 800×600, 1024×600, 1080p, 4K, Acer, Raspberry Pi, landscape and portrait versions of the same Activity.

For most visual design work, use **1024×600 as the reference design viewport**. It is the real legacy-netbook reference and therefore a useful place to make the child-facing composition look good. It is still a logical design space, not the physical display contract.

---

## 2. Start by choosing the spatial model, not the resolution

Choose according to what the Activity *is*.

| Activity shape | Recommended model | Typical mapping |
|---|---|---|
| arithmetic/question grid | `fluid` | automatic responsive collection |
| menu/gallery/chooser | `fluid` | automatic collection + scroll/page |
| text editor | `fluid` | toolbar + editor region |
| painting app | `hybrid` | fluid tools + document canvas |
| fixed visual puzzle | `reference_canvas` | 1024×600 + `contain` |
| board game with meaningful edges | `reference_canvas` | `contain` |
| immersive scene with decorative bleed | `reference_canvas` | `cover` |
| side-scroller | `world_camera` or `hybrid` | 1024×600 camera + `expand` |
| top-down game | `world_camera` or `hybrid` | camera + `expand` |
| physics/construction sandbox | `hybrid` | world camera + fluid tools |
| endless runner | `world_camera` or `hybrid` | camera + fluid HUD |
| map exploration | `world_camera` | world coordinates + camera |
| card/logic game | usually `fluid` or `hybrid` | automatic layout + optional board canvas |

The model may change later if the Activity grows. It is not identity or save-data authority.

---

## 3. Reference canvas: design once at 1024×600

Use a reference canvas when the *relative composition itself* matters.

Example: a visual balance puzzle has a machine on the left, answer targets on the right, and decorative characters around it. The designer can lay that out at:

```text
1024 × 600 logical units
```

Then choose how Greia adapts it.

### `contain`

Everything stays visible.

```text
reference canvas
+----------------------------------+
|                                  |
|          whole design            |
|                                  |
+----------------------------------+

4:3 physical screen
+---------------------------+
|       letterbox area      |
| +-----------------------+ |
| |      whole design     | |
| +-----------------------+ |
|       letterbox area      |
+---------------------------+
```

Use when cropping would remove meaningful content.

### `cover`

The screen is filled. Outer reference edges may crop.

Use only if outer content is intentionally expendable/decorative.

### Do not use non-uniform stretch

Never solve aspect-ratio differences by making a circle become an ellipse, making a character wider, or squashing text.

---

## 4. World camera: side-scrollers should not be giant fixed canvases

A complex game world is not a 1024×600 bitmap.

Example side-scroller:

```text
world width:        100,000 logical units
world height:         1,200 logical units
reference camera:     1,024 × 600 logical units
camera center:        follows player
fit:                  expand
```

The player's position, platforms, enemies and physics stay in world coordinates.

At the Acer's 1024×600 reference, the reference camera is approximately the authored view.

At 1920×1080, Greia can show more horizontal world while keeping the same gameplay scale.

At a 4:3 display, Greia can show additional vertical world rather than stretching or rewriting the level.

The Activity must not change gravity, player velocity, jump height or collision maps because the monitor changed.

### Camera follow belongs to the game

Greia does **not** decide whether a camera is centered, dead-zoned, predictive, eased, room-locked or cinematic. That is gameplay.

Greia owns only the logical↔physical mapping once the Activity chooses the logical camera view.

---

## 5. Fluid layout: grids, editors and collections should reflow automatically

A grid-based math Activity should not be authored as:

```text
if 800x600: 2 columns at x1/x2
if 1024x600: 3 columns at x1/x2/x3
if 1920x1080: 5 columns ...
```

Instead the designer/programmer specifies intent:

```text
question region
answer collection
minimum useful answer tile size
preferred tile size
maximum useful tile size
allowed rows/columns
scroll/page when not all answers fit
```

Greia computes the actual grid from the current content rectangle.

This means the educational/game logic can simply say:

```text
answers = [2, 4, 6, 8, 10, 12]
```

and the UI layer decides whether the visible arrangement is 2×3, 3×2, 6×1, etc. according to space and usability.

The answer identities and score logic do not change.

---

## 6. Hybrid Activities are expected

The most capable Activities will combine spatial models.

### Painting

```text
full Activity surface
├── platform Home/Back                  Greia-owned
├── tool palette                        fluid safe UI
├── document canvas                     logical document surface
└── gallery/confirm overlays            fluid
```

The painting document has its own size. Changing monitor resolution must not silently resample/rewrite the saved painting merely because the editor viewport changed.

### Side-scroller

```text
full Activity surface
├── platform Home/Back                  Greia-owned
├── parallax/world layers               world_camera / expand
├── player/enemies/collisions           world coordinates
├── score/hearts/task HUD               fluid safe UI
└── pause/help/result overlay            fluid
```

### Physics sandbox

```text
full Activity surface
├── world/simulation                    world_camera
├── parts/tool collection               fluid
├── object selection handles            world coordinates
└── dialog/confirmation                 fluid
```

The Activity author composes a few clear layers. They do not manually calculate a separate physical layout for every display.

---

## 7. System chrome and safe areas

Greia Home/Back controls are platform-owned and physically protected.

There are therefore two useful notions:

### Full Activity surface

Suitable for:

- backgrounds;
- world scenery;
- nonessential decorative art.

Those may visually continue underneath platform chrome where the display backend supports composition. Activity input there is still intercepted by Greia.

### Safe UI region

Suitable for:

- essential buttons;
- answer targets;
- text input;
- HUD elements that must remain readable/clickable;
- destructive/confirm controls.

Greia computes the largest appropriate rectangular region that avoids protected chrome.

The author does **not** write `leave 150px at top-left`.

A fixed reference canvas that uses the full surface can query the corresponding logical safe region, so a designer can keep essential authored content inside it without knowing the physical resolution.

---

## 8. Input follows the same coordinate transform

This is mandatory.

If a ball is drawn at logical `(500, 200)`, pointer/touch interaction must map a physical click back to that same logical coordinate system.

Do not do this:

```text
render scaled
hit test in original physical pixels
```

Greia's transform is bidirectional:

```text
logical -> physical   for rendering
physical -> logical   for pointer/touch
```

For world games, the inverse returns world coordinates.

Keyboard/controller actions are semantic and continue through the runtime-neutral input system.

---

## 9. The Pygame authoring surface

New Pygame Activities should prefer:

```text
from greia_platform.pygame_ui import ...
```

rather than importing launcher internals.

### Fixed/reference Activity

Conceptually:

```python
canvas = PygameReferenceCanvas(screen)
logical = canvas.surface

# Draw once in the 1024×600 reference coordinate space.
pygame.draw.circle(logical, color, (512, 300), 80)

# Greia maps it to the real screen.
canvas.present()

# Pointer comes back in the same reference coordinates.
point = canvas.pointer(event.pos)
```

This is ideal for small fixed puzzles/scenes.

### World game

Conceptually:

```python
mapper = PygameCanvasMapper.world(
    screen,
    center=player.position,
)

physical_player = mapper.point(player.x, player.y)
visible_world = mapper.visible_logical_rect
world_pointer = mapper.pointer(event.pos)
```

A real game should use `visible_world` for culling rather than drawing the entire level.

### Fluid UI

Use shared responsive layout primitives for toolbars/collections/panels. Do not fake fluid UI by drawing everything on a fixed reference bitmap unless the composition is genuinely fixed.

### 9.1 The platform owns the real window size

While R7 is open, Python Activities still call `pygame.display.set_mode`
directly. When an Activity is launched by a Greia session, the platform entry
normalizes that request to the **actual Shell surface size** and preserves the
Activity's flags. The Simulator does the same with its selected synthetic
viewport.

Consequences for authors:

- `screen.get_size()` is not guaranteed to be `1024x600`; it is the real
  session viewport (`1280x800`, `800x480`, ...).
- Always go through `PygameReferenceCanvas`, `PygameCanvasMapper` or
  `ChildUiMetrics` for layout and pointer mapping.
- Do not open a smaller window over the Shell because the reference canvas was
  1024x600. An uncovered Shell window keeps stale pixels and its hidden
  pointer, which looks like a rendering/input fault around the Activity.
- Outside a Greia session (tests, headless captures, direct developer runs)
  the requested size is left untouched; do not depend on the normalization for
  test fixtures.

### 9.2 What `PygameReferenceCanvas` does on a non-reference display

On a display whose aspect ratio differs from 1024x600 the CONTAIN fit leaves
bands (25 px above and below at 1280x800, 137 px at 1280x1024, side bands at
16:9). The canvas owns them:

- every full `present()` repaints the bands with one solid colour: the
  average of the scene's outermost pixels on that side, slightly darkened, or
  the `clear` colour when given. The colour only changes when the edge
  average moves clearly (a backdrop change such as day to night), never
  because a sprite passes the edge;
- non-integer scales are resampled smoothly by default (`smooth=None`); exact
  whole-number scales stay crisp. Pass `smooth=True`/`False` only to force it;
- `present_pointer()` and `present_regions()` repair from the cached physical
  frame and bands at any scale, so a pointer move never re-scales the scene.

This is presentation, not resolution independence: a 1024x600 bitmap scaled
1.25x is softer than art drawn at 1280x800. For opted-in Activities,
native-resolution drawing that removes both the softness and the bands is
delivered by §9.3.

### 9.3 High-resolution rendering (opt-in)

`PygameReferenceCanvas(target, hires=True)` removes the softness described in
§9.2 for an opted-in Activity. When the CONTAIN scale against 1024x600 is at
least 1.2 (owner threshold, 2026-10-21), `canvas.surface` and every surface the
Activity creates afterwards hold physical pixels while the Python API stays in
logical 1024x600 units (`greia_platform.hires_surface`: `ScaledSurface`, plus
patched `pygame.draw`, `pygame.transform`, `pygame.image` loaders and
`pygame.font.Font` inside that process only). `present()` then becomes a 1:1
copy. Below 1.2 the cheap path is kept: close to the reference the gain is
small and the extra fill cost is not worth it. `canvas.render_scale` reports the
scale used; `GREIA_ACTIVITY_HIRES=0` disables the layer for diagnosis.

Known limits: `subsurface` of a scaled surface is a copy, not a pixel-sharing
view; masks and surfarray see physical pixels; code that captured
`pygame.Surface` or `pygame.draw` functions before activation keeps creating
logical surfaces. Raster art is still logical-size PNG (resampled on load), so
only drawn shapes, outlines and text get sharper until higher-resolution
renditions exist.

---

## 10. Performance rules

Greia's automatic adaptation must remain cheap enough for the Acer floor.

### Fixed canvas

A simple off-screen 1024×600 logical surface is acceptable for appropriate Activities, especially because the reference Acer can present it near/native size.

But do not require every complex game to render into that intermediate surface.

### World games

Prefer:

- camera culling;
- direct transformed placement of visible objects;
- bounded sprite/asset caches;
- no giant world bitmap;
- no rendering off-screen entities merely because they exist in the level.

### High-resolution displays

Do not create a persistent 4K logical canvas merely because the physical display is 4K. Logical/world resolution remains independent.

### Repeated resizes

Do not grow one cache entry per arbitrary viewport forever. Size-dependent caches remain bounded or are invalidated.

---

## 11. Artwork guidance for designers

For a 1024×600 reference-canvas Activity:

- compose primary interaction around the center/safe logical region;
- avoid placing unique essential information at the outermost edge if `cover` may be used;
- keep individual assets at useful source resolution rather than baking the entire game into one flattened screenshot;
- separate background/world layers from HUD when possible;
- preserve transparent margins only when they have visual purpose;
- use vector/procedural/shared semantic icons where appropriate;
- preview with Greia system chrome visible.

For world games:

- create tiles/sprites/world art in world units;
- treat the camera as a view into the world, not the world itself;
- design backgrounds with enough horizontal/vertical continuation for `expand` where used;
- decide deliberately whether parallax layers expand, cover or repeat.

---

## 12. Saved state must remain resolution-neutral

Good durable values:

```text
player world position
level identifier
painting document bytes + document dimensions
text contents
selected tool
semantic collection item IDs
camera world position (if product wants it)
```

Bad durable values:

```text
button x=843 because monitor was 1366px wide
physical mouse x/y as game state
current line wrap positions
screen-specific card coordinates
physical pixel camera offset tied to one monitor
```

Portable child state must survive moving to different Greia hardware.

---

## 13. Designer preview direction

A future Greia Activity preview tool should default to the 1024×600 authoring view and offer one-click/arbitrary viewport probes such as:

```text
640×480
800×600
1024×600
1024×768
1280×720
1366×768
1920×1080
portrait stress view
custom width × height
```

The preview must use the **same shared Greia transform/layout code** as runtime.

A designer should be able to switch these views and observe adaptation without editing the Activity.

For world-camera Activities the preview should also show:

- logical camera bounds;
- reference view bounds;
- extra world revealed by `expand`;
- system-chrome protected region;
- safe UI region.

---

## 14. Review questions

When reviewing an Activity, ask:

1. What spatial model is each layer using?
2. Are any physical-resolution values accidentally treated as game/layout state?
3. Does the author maintain any resolution-specific coordinate tables? If yes, why is the shared platform not solving it?
4. Are drawing and pointer hit tests using the same transform?
5. Does system chrome overlap essential controls?
6. Does the game world remain stable when viewport size changes?
7. Does a fluid collection reflow/page automatically?
8. Are images preserving aspect ratio?
9. Is resizing bounded in memory/CPU?
10. Is the Activity still deliberate and readable at 1024×600?

If the answer requires "we special-case that resolution," treat it as an architecture smell unless a genuinely different physical capability—not merely pixel dimensions—requires different product behavior.
