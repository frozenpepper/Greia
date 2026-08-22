from __future__ import annotations

import math
import time
import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_ui_preferences,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.activity_viewport import CanvasFitMode, ReferenceCanvasSpec
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.pygame_scene import PygameSceneRenderer, SceneRenderError
from greia_platform.scene import SceneDefinition, SceneFit, SceneNode
from greia_platform.scene_actor import (
    CharacterMotion,
    CharacterState,
    SceneActorDefinition,
    sample_scene_actor,
)

CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 600

CHARACTERS = [
    ("lilli", "character.lilli", "Lilli"),
    ("leo", "character.leo", "Leo"),
    ("flash", "character.flash", "Flash"),
    ("dani", "character.dani", "Dani"),
    ("tito", "character.tito", "Tito"),
    ("momo", "character.momo", "Momo"),
]

STATES = [
    (CharacterState.NEUTRAL, "Neutral"),
    (CharacterState.BLINK, "Blink"),
    (CharacterState.HAPPY, "Happy"),
    (CharacterState.SURPRISED, "Surprised"),
    (CharacterState.SLEEPY, "Sleepy"),
]

MOTIONS = [
    (CharacterMotion.IDLE_BOUNCE, "Idle"),
    (CharacterMotion.BLINK, "Blink"),
    (CharacterMotion.HAPPY_HOP, "Hop"),
    (CharacterMotion.CELEBRATE_POP, "Pop"),
    (CharacterMotion.SURPRISED_WOBBLE, "Wobble"),
    (CharacterMotion.SLEEPY_SWAY, "Sway"),
    (CharacterMotion.NONE, "Static"),
]


def create_ensemble_actors() -> list[SceneActorDefinition]:
    actors = []
    for idx, (cid, asset_id, name) in enumerate(CHARACTERS):
        cx = 90 + idx * 144
        cy = 210
        w, h = 136, 136
        sw, sh = 104, 26
        actors.append(
            SceneActorDefinition(
                actor_id=cid,
                asset_id=asset_id,
                rect=(cx, cy, w, h),
                shadow_asset_id="shadow.contact.small.01",
                shadow_rect=(cx + 16, cy + 115, sw, sh),
                idle_phase=idx * 0.16,
                blink_phase=idx * 0.14,
            )
        )
    return actors


def create_hero_actor(char_index: int) -> SceneActorDefinition:
    cid, asset_id, name = CHARACTERS[char_index]
    cx = 392
    cy = 130
    w, h = 240, 240
    sw, sh = 180, 42
    return SceneActorDefinition(
        actor_id=cid,
        asset_id=asset_id,
        rect=(cx, cy, w, h),
        shadow_asset_id="shadow.contact.small.01",
        shadow_rect=(cx + 30, cy + 208, sw, sh),
    )


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.font.init()

    canvas = PygameReferenceCanvas(
        screen,
        ReferenceCanvasSpec(width=CANVAS_WIDTH, height=CANVAS_HEIGHT, fit=CanvasFitMode.CONTAIN),
    )

    font_title = pygame.font.SysFont("Arial", 18, bold=True)
    font_ui = pygame.font.SysFont("Arial", 13, bold=True)
    font_small = pygame.font.SysFont("Arial", 11)

    ui_prefs = get_ui_preferences()
    clock = pygame.time.Clock()
    renderer = PygameSceneRenderer.for_activity(max_entries=32)

    selected_char_idx = 0
    view_mode = "ensemble"
    current_state = CharacterState.NEUTRAL
    current_motion = CharacterMotion.IDLE_BOUNCE
    motion_enabled = True

    ensemble_actors = create_ensemble_actors()
    hero_actor = create_hero_actor(selected_char_idx)

    start_time = time.monotonic()
    mark_activity_ready()

    while not activity_stop_requested():
        elapsed = time.monotonic() - start_time
        target_size = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return 0
                elif pygame.K_1 <= event.key <= pygame.K_6:
                    selected_char_idx = event.key - pygame.K_1
                    hero_actor = create_hero_actor(selected_char_idx)
                elif event.key == pygame.K_e:
                    view_mode = "hero" if view_mode == "ensemble" else "ensemble"
                elif event.key == pygame.K_n:
                    current_state = CharacterState.NEUTRAL
                elif event.key == pygame.K_b:
                    current_state = CharacterState.BLINK
                elif event.key == pygame.K_h:
                    current_state = CharacterState.HAPPY
                elif event.key == pygame.K_s:
                    current_state = CharacterState.SURPRISED
                elif event.key == pygame.K_z:
                    current_state = CharacterState.SLEEPY
                elif event.key == pygame.K_i:
                    current_motion = CharacterMotion.IDLE_BOUNCE
                elif event.key == pygame.K_k:
                    current_motion = CharacterMotion.BLINK
                elif event.key == pygame.K_o:
                    current_motion = CharacterMotion.HAPPY_HOP
                elif event.key == pygame.K_p:
                    current_motion = CharacterMotion.CELEBRATE_POP
                elif event.key == pygame.K_w:
                    current_motion = CharacterMotion.SURPRISED_WOBBLE
                elif event.key == pygame.K_y:
                    current_motion = CharacterMotion.SLEEPY_SWAY
                elif event.key == pygame.K_x:
                    current_motion = CharacterMotion.NONE
                elif event.key == pygame.K_m:
                    motion_enabled = not motion_enabled
                elif event.key == pygame.K_SPACE:
                    m_idx = [m[0] for m in MOTIONS].index(current_motion)
                    current_motion = MOTIONS[(m_idx + 1) % len(MOTIONS)][0]
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mpos = event.pos
                else:
                    mpos = (int(event.x * target_size[0]), int(event.y * target_size[1]))

                if is_home_clicked(screen, mpos):
                    return 0

                logical_pos = canvas.pointer(mpos)
                if logical_pos is not None:
                    canv_x, canv_y = logical_pos

                    # Character selector buttons (y: 54 to 84)
                    for idx, (cid, _, name) in enumerate(CHARACTERS):
                        bx = 80 + idx * 84
                        if bx <= canv_x <= bx + 76 and 54 <= canv_y <= 84:
                            selected_char_idx = idx
                            hero_actor = create_hero_actor(selected_char_idx)

                    # View Mode button (x: 600, y: 54 to 84)
                    if 600 <= canv_x <= 720 and 54 <= canv_y <= 84:
                        view_mode = "hero" if view_mode == "ensemble" else "ensemble"

                    # Motion toggle button (x: 740, y: 54 to 84)
                    if 740 <= canv_x <= 860 and 54 <= canv_y <= 84:
                        motion_enabled = not motion_enabled

                    # State buttons (y: 460 to 488)
                    for idx, (st, sname) in enumerate(STATES):
                        bx = 80 + idx * 105
                        if bx <= canv_x <= bx + 95 and 460 <= canv_y <= 488:
                            current_state = st

                    # Motion buttons (y: 504 to 532)
                    for idx, (mot, mname) in enumerate(MOTIONS):
                        bx = 80 + idx * 78
                        if bx <= canv_x <= bx + 70 and 504 <= canv_y <= 532:
                            current_motion = mot

                    # Direct character click in ensemble mode
                    if view_mode == "ensemble":
                        for idx, actor in enumerate(ensemble_actors):
                            rx, ry, rw, rh = actor.rect
                            if rx <= canv_x <= rx + rw and ry <= canv_y <= ry + rh:
                                selected_char_idx = idx
                                hero_actor = create_hero_actor(selected_char_idx)

        # Build Scene Nodes
        nodes = []
        nodes.append(
            SceneNode(
                node_id="bg.ground_edge",
                asset_id="ground.grass_edge.01",
                rect=(0, 310, 1024, 150),
                z=10,
                optional=True,
            )
        )

        effective_motion = current_motion if motion_enabled else CharacterMotion.NONE

        if view_mode == "ensemble":
            for idx, actor in enumerate(ensemble_actors):
                sample = sample_scene_actor(
                    actor,
                    elapsed_seconds=elapsed,
                    motion_enabled=motion_enabled,
                    state=current_state,
                    motion=effective_motion,
                )
                nodes.extend(sample.nodes)
        else:
            sample = sample_scene_actor(
                hero_actor,
                elapsed_seconds=elapsed,
                motion_enabled=motion_enabled,
                state=current_state,
                motion=effective_motion,
            )
            nodes.extend(sample.nodes)

        scene = SceneDefinition(
            scene_id="canonical_cast_showcase",
            canvas_size=(CANVAS_WIDTH, CANVAS_HEIGHT),
            background=(238, 246, 255),
            nodes=tuple(nodes),
            fit=SceneFit.CONTAIN,
        )

        render_failed = False
        # Capture render stats
        render_failed = False
        render_err_msg = ""
        render_stats = None

        try:
            render_stats = renderer.draw(
                scene, canvas.surface, elapsed_seconds=elapsed, motion_enabled=motion_enabled, clear=True
            )
        except SceneRenderError as err:
            render_failed = True
            render_err_msg = str(err)
            canvas.surface.fill((238, 246, 255))
            err_box = pygame.Rect(120, 220, 784, 120)
            pygame.draw.rect(canvas.surface, (254, 242, 242), err_box, border_radius=12)
            pygame.draw.rect(canvas.surface, (239, 68, 68), err_box, width=2, border_radius=12)
            err_title = font_title.render("Activity Visual Safe Fallback Mode", True, (185, 28, 28))
            err_detail = font_ui.render(f"Required rendition failed: {render_err_msg}", True, (127, 29, 29))
            canvas.surface.blit(err_title, (150, 245))
            canvas.surface.blit(err_detail, (150, 285))

        # Render Fixture Developer Controls directly onto canvas.surface
        # Title
        t_surf = font_title.render("Greia Canonical Cast Showcase (v0.1)", True, (15, 23, 42))
        canvas.surface.blit(t_surf, (80, 14))

        # Developer Diagnostic Readout
        screen_w, screen_h = screen.get_size()
        cid, asset_id, name = CHARACTERS[selected_char_idx]
        req_variant = "default" if current_state == CharacterState.NEUTRAL else current_state.value
        fallback_used = (render_stats is not None and render_stats.fallback_nodes > 0)
        rendered_variant = "default" if (fallback_used or req_variant == "default") else req_variant
        fallback_str = "YES (default)" if fallback_used else "NO"
        ui_size_str = ui_prefs.interface_size.value.upper()

        line1 = f"Char: {asset_id} | State: {current_state.value.upper()} | Motion: {effective_motion.value.upper()} | UI: {ui_size_str}"
        line2 = f"Req: {req_variant} | Rendered: {rendered_variant} | Fallback: {fallback_str} | Canvas: {CANVAS_WIDTH}x{CANVAS_HEIGHT} | Screen: {screen_w}x{screen_h}"
        st_surf1 = font_small.render(line1, True, (51, 65, 85))
        st_surf2 = font_small.render(line2, True, (71, 85, 105))
        canvas.surface.blit(st_surf1, (440, 12))
        canvas.surface.blit(st_surf2, (440, 30))

        # Character Selector Buttons
        for idx, (cid, _, name) in enumerate(CHARACTERS):
            r = pygame.Rect(80 + idx * 84, 54, 76, 28)
            is_sel = (idx == selected_char_idx)
            bg_col = (14, 116, 144) if is_sel else (255, 255, 255)
            fg_col = (255, 255, 255) if is_sel else (15, 23, 42)
            pygame.draw.rect(canvas.surface, bg_col, r, border_radius=6)
            pygame.draw.rect(canvas.surface, (203, 213, 225), r, width=1, border_radius=6)
            btn_txt = font_ui.render(name, True, fg_col)
            canvas.surface.blit(btn_txt, btn_txt.get_rect(center=r.center))

        # Mode Button
        r_mode = pygame.Rect(600, 54, 110, 28)
        pygame.draw.rect(canvas.surface, (241, 245, 249), r_mode, border_radius=6)
        pygame.draw.rect(canvas.surface, (148, 163, 184), r_mode, width=1, border_radius=6)
        txt_m = font_ui.render(f"View: {view_mode.capitalize()}", True, (15, 23, 42))
        canvas.surface.blit(txt_m, txt_m.get_rect(center=r_mode.center))

        # Motion Toggle Button
        r_mot = pygame.Rect(720, 54, 110, 28)
        bg_mot = (220, 252, 231) if motion_enabled else (254, 226, 226)
        bd_mot = (134, 239, 172) if motion_enabled else (252, 165, 165)
        pygame.draw.rect(canvas.surface, bg_mot, r_mot, border_radius=6)
        pygame.draw.rect(canvas.surface, bd_mot, r_mot, width=1, border_radius=6)
        txt_mot = font_ui.render(f"Motion: {'ON' if motion_enabled else 'OFF'}", True, (15, 23, 42))
        canvas.surface.blit(txt_mot, txt_mot.get_rect(center=r_mot.center))

        # State Buttons
        for idx, (st, sname) in enumerate(STATES):
            r = pygame.Rect(80 + idx * 105, 460, 95, 28)
            is_cur = (st == current_state)
            bg_col = (13, 148, 136) if is_cur else (255, 255, 255)
            fg_col = (255, 255, 255) if is_cur else (15, 23, 42)
            pygame.draw.rect(canvas.surface, bg_col, r, border_radius=6)
            pygame.draw.rect(canvas.surface, (203, 213, 225), r, width=1, border_radius=6)
            txt_s = font_ui.render(sname, True, fg_col)
            canvas.surface.blit(txt_s, txt_s.get_rect(center=r.center))

        # Motion Buttons
        for idx, (mot, mname) in enumerate(MOTIONS):
            r = pygame.Rect(80 + idx * 78, 504, 70, 28)
            is_cur = (mot == current_motion)
            bg_col = (79, 70, 229) if is_cur else (255, 255, 255)
            fg_col = (255, 255, 255) if is_cur else (15, 23, 42)
            pygame.draw.rect(canvas.surface, bg_col, r, border_radius=6)
            pygame.draw.rect(canvas.surface, (203, 213, 225), r, width=1, border_radius=6)
            txt_mot_b = font_ui.render(mname, True, fg_col)
            canvas.surface.blit(txt_mot_b, txt_mot_b.get_rect(center=r.center))

        # Present canvas onto physical screen
        canvas.present(clear=(238, 246, 255), smooth=True)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    main()
