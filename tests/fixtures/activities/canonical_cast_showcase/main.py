from __future__ import annotations

import math
import sys
import time
import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
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
    # 6 characters placed evenly across 1024 width
    # usable width: ~80 to 944 -> step ~144
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

    font_title = pygame.font.SysFont("Arial", 20, bold=True)
    font_ui = pygame.font.SysFont("Arial", 14, bold=True)
    font_small = pygame.font.SysFont("Arial", 12)

    clock = pygame.time.Clock()
    renderer = PygameSceneRenderer.for_activity(max_entries=32)

    selected_char_idx = 0  # 0 to 5
    view_mode = "ensemble"  # "ensemble" or "hero"
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
        viewport = activity_viewport_for_surface(screen)
        safe_rect = viewport.safe_ui_rect()

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
                elif event.key == pygame.K_m:
                    motion_enabled = not motion_enabled
                elif event.key == pygame.K_SPACE:
                    # cycle motions
                    m_idx = [m[0] for m in MOTIONS].index(current_motion)
                    current_motion = MOTIONS[(m_idx + 1) % len(MOTIONS)][0]
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mpos = event.pos
                else:
                    mpos = (int(event.x * target_size[0]), int(event.y * target_size[1]))

                if is_home_clicked(screen, mpos):
                    return 0

                # Map click to reference canvas coords (1024x600)
                # Viewport transform is COVER/CONTAIN
                scale_x = target_size[0] / CANVAS_WIDTH
                scale_y = target_size[1] / CANVAS_HEIGHT
                scale = min(scale_x, scale_y)
                ox = (target_size[0] - CANVAS_WIDTH * scale) / 2
                oy = (target_size[1] - CANVAS_HEIGHT * scale) / 2
                canv_x = (mpos[0] - ox) / scale
                canv_y = (mpos[1] - oy) / scale

                # Check Character Selector Buttons (top-left: y 60 to 92)
                for idx, (cid, _, name) in enumerate(CHARACTERS):
                    bx = 80 + idx * 85
                    if bx <= canv_x <= bx + 75 and 60 <= canv_y <= 92:
                        selected_char_idx = idx
                        hero_actor = create_hero_actor(selected_char_idx)

                # Check View Mode toggle button (x 600, y 60 to 92)
                if 600 <= canv_x <= 720 and 60 <= canv_y <= 92:
                    view_mode = "hero" if view_mode == "ensemble" else "ensemble"

                # Check Motion On/Off toggle (x 740, y 60 to 92)
                if 740 <= canv_x <= 860 and 60 <= canv_y <= 92:
                    motion_enabled = not motion_enabled

                # Check State Buttons (bottom bar: y 450 to 482)
                for idx, (st, sname) in enumerate(STATES):
                    bx = 80 + idx * 110
                    if bx <= canv_x <= bx + 100 and 450 <= canv_y <= 482:
                        current_state = st

                # Check Motion Buttons (bottom bar: y 500 to 532)
                for idx, (mot, mname) in enumerate(MOTIONS):
                    bx = 80 + idx * 80
                    if bx <= canv_x <= bx + 72 and 500 <= canv_y <= 532:
                        current_motion = mot

                # Direct Character Click in Ensemble mode
                if view_mode == "ensemble":
                    for idx, actor in enumerate(ensemble_actors):
                        rx, ry, rw, rh = actor.rect
                        if rx <= canv_x <= rx + rw and ry <= canv_y <= ry + rh:
                            selected_char_idx = idx
                            hero_actor = create_hero_actor(selected_char_idx)

        # Build Scene Nodes
        nodes = []

        # Background decorative meadow strip
        nodes.append(
            SceneNode(
                node_id="bg.ground_edge",
                asset_id="ground.grass_edge.01",
                rect=(0, 310, 1024, 150),
                z=10,
                optional=True,
            )
        )

        if view_mode == "ensemble":
            for idx, actor in enumerate(ensemble_actors):
                # Sample actor with active state & motion
                sample = sample_scene_actor(
                    actor,
                    elapsed_seconds=elapsed,
                    motion_enabled=motion_enabled,
                    state=current_state,
                    motion=current_motion,
                )
                nodes.extend(sample.nodes)
        else:
            sample = sample_scene_actor(
                hero_actor,
                elapsed_seconds=elapsed,
                motion_enabled=motion_enabled,
                state=current_state,
                motion=current_motion,
            )
            nodes.extend(sample.nodes)

        scene = SceneDefinition(
            scene_id="canonical_cast_showcase",
            canvas_size=(CANVAS_WIDTH, CANVAS_HEIGHT),
            background=(238, 246, 255),  # Soft pleasant storybook sky
            nodes=tuple(nodes),
            fit=SceneFit.CONTAIN,
        )

        # Render Scene
        try:
            renderer.draw(scene, screen, elapsed_seconds=elapsed, motion_enabled=motion_enabled, clear=True)
        except SceneRenderError as err:
            # Safe Activity-level fallback
            screen.fill((238, 246, 255))
            err_surf = font_title.render(f"Visual Fallback Mode: {err}", True, (180, 40, 40))
            screen.blit(err_surf, (80, 260))

        # Render Fixture UI Controls onto screen (mapped to display surface)
        scale_x = target_size[0] / CANVAS_WIDTH
        scale_y = target_size[1] / CANVAS_HEIGHT
        scale = min(scale_x, scale_y)
        ox = (target_size[0] - CANVAS_WIDTH * scale) / 2
        oy = (target_size[1] - CANVAS_HEIGHT * scale) / 2

        def to_screen(rx, ry, rw, rh):
            return pygame.Rect(int(ox + rx * scale), int(oy + ry * scale), int(rw * scale), int(rh * scale))

        # Title
        t_surf = font_title.render("Greia Canonical Cast Showcase (v0.1)", True, (15, 23, 42))
        screen.blit(t_surf, (int(ox + 80 * scale), int(oy + 24 * scale)))

        # Mode & Status Indicator
        status_str = f"Mode: {view_mode.upper()} | State: {current_state.value.upper()} | Motion: {current_motion.value.upper()} ({'ON' if motion_enabled else 'OFF'})"
        st_surf = font_small.render(status_str, True, (71, 85, 105))
        screen.blit(st_surf, (int(ox + 500 * scale), int(oy + 28 * scale)))

        # Character Buttons
        for idx, (cid, _, name) in enumerate(CHARACTERS):
            r = to_screen(80 + idx * 85, 60, 75, 28)
            is_sel = (idx == selected_char_idx)
            bg_col = (14, 116, 144) if is_sel else (255, 255, 255)
            fg_col = (255, 255, 255) if is_sel else (15, 23, 42)
            pygame.draw.rect(screen, bg_col, r, border_radius=6)
            pygame.draw.rect(screen, (203, 213, 225), r, width=1, border_radius=6)
            btn_txt = font_ui.render(name, True, fg_col)
            screen.blit(btn_txt, btn_txt.get_rect(center=r.center))

        # Mode Button
        r_mode = to_screen(600, 60, 120, 28)
        pygame.draw.rect(screen, (241, 245, 249), r_mode, border_radius=6)
        pygame.draw.rect(screen, (148, 163, 184), r_mode, width=1, border_radius=6)
        txt_m = font_ui.render(f"View: {view_mode.capitalize()}", True, (15, 23, 42))
        screen.blit(txt_m, txt_m.get_rect(center=r_mode.center))

        # Motion Toggle Button
        r_mot = to_screen(740, 60, 120, 28)
        pygame.draw.rect(screen, (220, 252, 231) if motion_enabled else (254, 226, 226), r_mot, border_radius=6)
        pygame.draw.rect(screen, (134, 239, 172) if motion_enabled else (252, 165, 165), r_mot, width=1, border_radius=6)
        txt_mot = font_ui.render(f"Motion: {'ON' if motion_enabled else 'OFF'}", True, (15, 23, 42))
        screen.blit(txt_mot, txt_mot.get_rect(center=r_mot.center))

        # State Buttons
        for idx, (st, sname) in enumerate(STATES):
            r = to_screen(80 + idx * 110, 450, 100, 28)
            is_cur = (st == current_state)
            bg_col = (13, 148, 136) if is_cur else (255, 255, 255)
            fg_col = (255, 255, 255) if is_cur else (15, 23, 42)
            pygame.draw.rect(screen, bg_col, r, border_radius=6)
            pygame.draw.rect(screen, (203, 213, 225), r, width=1, border_radius=6)
            txt_s = font_ui.render(sname, True, fg_col)
            screen.blit(txt_s, txt_s.get_rect(center=r.center))

        # Motion Buttons
        for idx, (mot, mname) in enumerate(MOTIONS):
            r = to_screen(80 + idx * 80, 500, 72, 28)
            is_cur = (mot == current_motion)
            bg_col = (79, 70, 229) if is_cur else (255, 255, 255)
            fg_col = (255, 255, 255) if is_cur else (15, 23, 42)
            pygame.draw.rect(screen, bg_col, r, border_radius=6)
            pygame.draw.rect(screen, (203, 213, 225), r, width=1, border_radius=6)
            txt_mot_b = font_ui.render(mname, True, fg_col)
            screen.blit(txt_mot_b, txt_mot_b.get_rect(center=r.center))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
