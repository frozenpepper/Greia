#!/usr/bin/env python3
"""Capture visual acceptance screenshots for Teatrino delle Fiabe Iteration 2."""

import os
from pathlib import Path
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, ".")
sys.path.insert(0, "src")
import activities.teatrino_fiabe.main as teatrino
from greia_platform.typography import FontRole, GreiaTypography

OUT_DIR = Path("tmp/teatrino_evidence")
OUT_DIR.mkdir(parents=True, exist_ok=True)

pygame.init()
pygame.display.set_mode((1024, 600))
pygame.font.init()
typography = GreiaTypography()

# Load all 16 character sprites
runtime_dir = Path("activities/teatrino_fiabe/assets/runtime")
puppet_sprites = {}
for p_id, _ in teatrino.PUPPET_ROSTER:
    png_file = runtime_dir / f"puppet_{p_id}.png"
    img = pygame.image.load(str(png_file)).convert_alpha()
    puppet_sprites[p_id] = pygame.transform.smoothscale(img, (110, 110))


def draw_theater_chrome(surf, active_bg_idx=0, num_saved=2):
    # Proscenium Curtains
    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN_DARK, [(0, 0), (130, 0), (70, 440), (0, 440)])
    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN_LIGHT, [(0, 0), (70, 0), (35, 420), (0, 420)])

    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN_DARK, [(1024, 0), (1024 - 130, 0), (1024 - 70, 440), (1024, 440)])
    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN, [(1024, 0), (1024 - 110, 0), (1024 - 55, 430), (1024, 430)])
    pygame.draw.polygon(surf, teatrino.STAGE_CURTAIN_LIGHT, [(1024, 0), (1024 - 70, 0), (1024 - 35, 420), (1024, 420)])

    for vx in range(120, 890, 110):
        pygame.draw.circle(surf, teatrino.STAGE_CURTAIN_DARK, (vx + 55, 24), 68)
        pygame.draw.circle(surf, teatrino.STAGE_CURTAIN, (vx + 55, 24), 62)
        pygame.draw.circle(surf, teatrino.STAGE_GOLD, (vx + 55, 24), 62, width=2)
        pygame.draw.circle(surf, teatrino.STAGE_GOLD, (vx + 55, 86), 4)

    pygame.draw.rect(surf, (60, 40, 15), (0, 0, 1024, 14))
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, (0, 10, 1024, 4))

    # Top Toolbar: Left Deck (Mic & Stories Library)
    mic_rect = pygame.Rect(140, 16, 75, 52)
    pygame.draw.rect(surf, (220, 255, 225), mic_rect, border_radius=14)
    pygame.draw.rect(surf, teatrino.MIC_GREEN, mic_rect, width=3, border_radius=14)
    mic_s = typography.render("🎙️ ON", FontRole.TITLE, 14, teatrino.MIC_GREEN)
    surf.blit(mic_s, (mic_rect.centerx - mic_s.get_width() // 2, mic_rect.centery - mic_s.get_height() // 2))

    lib_rect = pygame.Rect(225, 16, 120, 52)
    pygame.draw.rect(surf, (255, 250, 240), lib_rect, border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), lib_rect, width=2, border_radius=14)
    lib_s = typography.render(f"🎬 Storie ({num_saved})", FontRole.TITLE, 14, teatrino.DARK_TEXT)
    surf.blit(lib_s, (lib_rect.centerx - lib_s.get_width() // 2, lib_rect.centery - lib_s.get_height() // 2))

    # Top Toolbar: Center Deck (Record & Play)
    rec_rect = pygame.Rect(415, 16, 130, 52)
    pygame.draw.rect(surf, (255, 250, 240), rec_rect, border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), rec_rect, width=2, border_radius=14)
    rec_s = typography.render("🔴 REC", FontRole.TITLE, 16, teatrino.DARK_TEXT)
    surf.blit(rec_s, (rec_rect.centerx - rec_s.get_width() // 2, rec_rect.centery - rec_s.get_height() // 2))

    play_rect = pygame.Rect(560, 16, 130, 52)
    pygame.draw.rect(surf, (255, 250, 240), play_rect, border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), play_rect, width=2, border_radius=14)
    play_s = typography.render("▶️ SHOW", FontRole.TITLE, 16, teatrino.DARK_TEXT)
    surf.blit(play_s, (play_rect.centerx - play_s.get_width() // 2, play_rect.centery - play_s.get_height() // 2))

    # Top Toolbar: Right Deck (Clear)
    clear_rect = pygame.Rect(740, 16, 65, 52)
    pygame.draw.rect(surf, (255, 250, 240), clear_rect, border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), clear_rect, width=2, border_radius=14)
    clr_s = typography.render("🗑️", FontRole.TITLE, 22, teatrino.DARK_TEXT)
    surf.blit(clr_s, (clear_rect.centerx - clr_s.get_width() // 2, clear_rect.centery - clr_s.get_height() // 2))

    # Right Sidebar: Magic Deck (Scene Button on Top at y=24, then 6 SFX buttons)
    sc_icon = teatrino.BG_CONFIGS[active_bg_idx][1]
    sc_rect = pygame.Rect(915, 24, 70, 54)
    pygame.draw.rect(surf, (255, 250, 240), sc_rect, border_radius=14)
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, sc_rect, width=3, border_radius=14)
    sc_s = typography.render(sc_icon, FontRole.DISPLAY, 26, teatrino.DARK_TEXT)
    surf.blit(sc_s, (sc_rect.centerx - sc_s.get_width() // 2, sc_rect.centery - sc_s.get_height() // 2 - 4))
    sc_lbl = typography.render("Scena", FontRole.CONTROL, 10, teatrino.DARK_TEXT)
    surf.blit(sc_lbl, (sc_rect.centerx - sc_lbl.get_width() // 2, sc_rect.bottom - 13))

    for f_idx, (fx_id, fx_sym) in enumerate(teatrino.FX_BUTTONS):
        fy = 88 + f_idx * 58
        fx_rect = pygame.Rect(915, fy, 70, 50)
        pygame.draw.rect(surf, (255, 250, 240), fx_rect, border_radius=14)
        pygame.draw.rect(surf, teatrino.STAGE_GOLD, fx_rect, width=2, border_radius=14)
        fx_s = typography.render(fx_sym, FontRole.DISPLAY, 26, teatrino.DARK_TEXT)
        surf.blit(fx_s, (fx_rect.centerx - fx_s.get_width() // 2, fx_rect.centery - fx_s.get_height() // 2))


def draw_tray(surf, page_idx=0):
    pygame.draw.rect(surf, (30, 24, 40), (0, 500, 1024, 100))
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, (0, 500, 1024, 4))

    tray_prev_rect = pygame.Rect(40, 522, 54, 54)
    pygame.draw.rect(surf, (255, 250, 240), tray_prev_rect, border_radius=12)
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, tray_prev_rect, width=2, border_radius=12)
    cx, cy = tray_prev_rect.center
    pygame.draw.polygon(surf, (61, 44, 31), [(cx - 8, cy), (cx + 6, cy - 10), (cx + 6, cy + 10)])

    tray_next_rect = pygame.Rect(930, 522, 54, 54)
    pygame.draw.rect(surf, (255, 250, 240), tray_next_rect, border_radius=12)
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, tray_next_rect, width=2, border_radius=12)
    cx, cy = tray_next_rect.center
    pygame.draw.polygon(surf, (61, 44, 31), [(cx + 8, cy), (cx - 6, cy - 10), (cx - 6, cy + 10)])

    page_puppets = teatrino.PUPPET_ROSTER[page_idx * 6 : (page_idx + 1) * 6]
    for p_idx, (p_id, p_name) in enumerate(page_puppets):
        card_x = 110 + p_idx * 135
        card_rect = pygame.Rect(card_x, 508, 120, 84)
        pygame.draw.rect(surf, (255, 250, 240), card_rect, border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), card_rect, width=2, border_radius=14)

        spr = puppet_sprites[p_id]
        thumb = pygame.transform.smoothscale(spr, (52, 52))
        surf.blit(thumb, (card_rect.centerx - 26, card_rect.y + 6))

        name_s = typography.render(p_name, FontRole.CONTROL, 11, teatrino.DARK_TEXT)
        surf.blit(name_s, (card_rect.centerx - name_s.get_width() // 2, card_rect.y + 63))


# 1. Capture Cheerful Cottage Scene with Baby & Teddy Bear
surf_cottage = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("cottage")
surf_cottage.blit(bg_surf, (0, 0))
p_bebe = teatrino.Puppet("bebe", "Bebè", 350, 275)
p_orsetto = teatrino.Puppet("orsetto", "Orsetto", 520, 270)
p_lilli = teatrino.Puppet("lilli", "Lilli", 690, 260)
p_lilli.flip_x = True
for p in (p_bebe, p_orsetto, p_lilli):
    p.draw(surf_cottage, puppet_sprites[p.puppet_id], typography)
draw_theater_chrome(surf_cottage, active_bg_idx=0)
draw_tray(surf_cottage, page_idx=1)
out_cot = OUT_DIR / "scene_cottage_cheerful.png"
pygame.image.save(surf_cottage, str(out_cot))
print(f"Captured {out_cot}")

# 2. Capture Castle Scene with King, Princess, Knight
surf_castle = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("castle")
surf_castle.blit(bg_surf, (0, 0))
p_re = teatrino.Puppet("re", "Re", 340, 270)
p_prin = teatrino.Puppet("principessa", "Principessa", 500, 275)
p_cav = teatrino.Puppet("cavaliere", "Cavaliere", 670, 265)
p_cav.flip_x = True
for p in (p_re, p_prin, p_cav):
    p.draw(surf_castle, puppet_sprites[p.puppet_id], typography)
draw_theater_chrome(surf_castle, active_bg_idx=1)
draw_tray(surf_castle, page_idx=1)
out_cas = OUT_DIR / "scene_castle_grand.png"
pygame.image.save(surf_castle, str(out_cas))
print(f"Captured {out_cas}")

# 3. Capture Ocean Scene with Mermaid & Baby Dragon
surf_ocean = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("ocean")
surf_ocean.blit(bg_surf, (0, 0))
p_sir = teatrino.Puppet("sirenetta", "Sirenetta", 380, 260)
p_drag = teatrino.Puppet("draghetto", "Draghetto", 600, 270)
p_drag.flip_x = True
for p in (p_sir, p_drag):
    p.draw(surf_ocean, puppet_sprites[p.puppet_id], typography)
draw_theater_chrome(surf_ocean, active_bg_idx=2)
draw_tray(surf_ocean, page_idx=2)
out_oc = OUT_DIR / "scene_ocean_reef.png"
pygame.image.save(surf_ocean, str(out_oc))
print(f"Captured {out_oc}")

# 4. Capture Forest Scene with Wolf, Fairy & Tito
surf_forest = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("forest")
surf_forest.blit(bg_surf, (0, 0))
p_lup = teatrino.Puppet("lupetto", "Lupetto", 350, 270)
p_fat = teatrino.Puppet("fatina", "Fatina", 512, 255)
p_tit = teatrino.Puppet("tito", "Tito", 670, 275)
p_tit.flip_x = True
for p in (p_lup, p_fat, p_tit):
    p.draw(surf_forest, puppet_sprites[p.puppet_id], typography)
draw_theater_chrome(surf_forest, active_bg_idx=3)
draw_tray(surf_forest, page_idx=1)
out_for = OUT_DIR / "scene_forest_magic.png"
pygame.image.save(surf_forest, str(out_for))
print(f"Captured {out_for}")

# 5. Capture Show Library Modal Gallery
surf_lib = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("cottage")
surf_lib.blit(bg_surf, (0, 0))
draw_theater_chrome(surf_lib, active_bg_idx=0)
draw_tray(surf_lib, page_idx=0)

# Dim Modal
modal_overlay = pygame.Surface((1024, 600), pygame.SRCALPHA)
modal_overlay.fill((10, 8, 20, 220))
surf_lib.blit(modal_overlay, (0, 0))

# Modal Box
box_rect = pygame.Rect(100, 50, 824, 500)
pygame.draw.rect(surf_lib, (255, 250, 240), box_rect, border_radius=20)
pygame.draw.rect(surf_lib, teatrino.STAGE_GOLD, box_rect, width=4, border_radius=20)

hdr_surf = typography.render("🎬 Storie Magiche Salvate", FontRole.DISPLAY, 26, teatrino.DARK_TEXT)
surf_lib.blit(hdr_surf, (box_rect.centerx - hdr_surf.get_width() // 2, box_rect.y + 20))

cls_rect = pygame.Rect(box_rect.right - 55, box_rect.y + 15, 40, 40)
pygame.draw.rect(surf_lib, (254, 226, 226), cls_rect, border_radius=10)
pygame.draw.rect(surf_lib, (220, 38, 38), cls_rect, width=2, border_radius=10)
cx, cy = cls_rect.center
pygame.draw.line(surf_lib, (185, 28, 28), (cx - 8, cy - 8), (cx + 8, cy + 8), 3)
pygame.draw.line(surf_lib, (185, 28, 28), (cx + 8, cy - 8), (cx - 8, cy + 8), 3)

# 3 Mock Saved Shows
mock_shows = [
    {"title": "Il Cavaliere e la Principessa", "backdrop": "castle", "actors": ["principessa", "cavaliere", "re"], "dur": "18.4s", "mic": True},
    {"title": "La Festa nella Casetta", "backdrop": "cottage", "actors": ["bebe", "orsetto", "lilli"], "dur": "14.2s", "mic": True},
    {"title": "Il Segreto del Mare Profondo", "backdrop": "ocean", "actors": ["sirenetta", "draghetto"], "dur": "22.0s", "mic": True},
]
for s_idx, s_data in enumerate(mock_shows):
    card_y = 100 + s_idx * 95
    c_rect = pygame.Rect(box_rect.x + 30, card_y, box_rect.width - 60, 82)
    pygame.draw.rect(surf_lib, (248, 240, 225), c_rect, border_radius=14)
    pygame.draw.rect(surf_lib, (180, 140, 90), c_rect, width=2, border_radius=14)

    bg_sym = "🏰" if s_data["backdrop"] == "castle" else "🏡" if s_data["backdrop"] == "cottage" else "🌊"
    bg_icon_s = typography.render(bg_sym, FontRole.DISPLAY, 32, teatrino.DARK_TEXT)
    surf_lib.blit(bg_icon_s, (c_rect.x + 18, c_rect.centery - bg_icon_s.get_height() // 2))

    for a_idx, a_id in enumerate(s_data["actors"][:3]):
        spr = puppet_sprites[a_id]
        micro = pygame.transform.smoothscale(spr, (38, 38))
        surf_lib.blit(micro, (c_rect.x + 70 + a_idx * 34, c_rect.centery - 19))

    title_s = typography.render(s_data["title"], FontRole.TITLE, 18, teatrino.DARK_TEXT)
    surf_lib.blit(title_s, (c_rect.x + 200, c_rect.y + 14))

    dur_text = f"🎙️ {s_data['dur']}"
    dur_s = typography.render(dur_text, FontRole.CONTROL, 13, (120, 60, 20))
    surf_lib.blit(dur_s, (c_rect.x + 200, c_rect.y + 44))

    ply_btn_rect = pygame.Rect(c_rect.right - 200, c_rect.centery - 24, 110, 48)
    pygame.draw.rect(surf_lib, (220, 255, 225), ply_btn_rect, border_radius=12)
    pygame.draw.rect(surf_lib, teatrino.MIC_GREEN, ply_btn_rect, width=2, border_radius=12)
    ply_btn_s = typography.render("▶️ Guarda", FontRole.TITLE, 15, (20, 100, 40))
    surf_lib.blit(ply_btn_s, (ply_btn_rect.centerx - ply_btn_s.get_width() // 2, ply_btn_rect.centery - ply_btn_s.get_height() // 2))

    del_btn_rect = pygame.Rect(c_rect.right - 70, c_rect.centery - 24, 50, 48)
    pygame.draw.rect(surf_lib, (255, 230, 230), del_btn_rect, border_radius=12)
    pygame.draw.rect(surf_lib, (220, 38, 38), del_btn_rect, width=2, border_radius=12)
    del_btn_s = typography.render("🗑️", FontRole.TITLE, 18, (185, 28, 28))
    surf_lib.blit(del_btn_s, (del_btn_rect.centerx - del_btn_s.get_width() // 2, del_btn_rect.centery - del_btn_s.get_height() // 2))

out_lib = OUT_DIR / "library_modal_gallery.png"
pygame.image.save(surf_lib, str(out_lib))
print(f"Captured {out_lib}")

# 6. Capture Viewer Mode
surf_view = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("cottage")
surf_view.blit(bg_surf, (0, 0))
p_bebe = teatrino.Puppet("bebe", "Bebè", 420, 260)
p_bebe.jump()
p_orsetto = teatrino.Puppet("orsetto", "Orsetto", 580, 270)
p_orsetto.speak()
p_bebe.draw(surf_view, puppet_sprites["bebe"], typography)
p_orsetto.draw(surf_view, puppet_sprites["orsetto"], typography)

# Curtains
pygame.draw.polygon(surf_view, teatrino.STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
pygame.draw.polygon(surf_view, teatrino.STAGE_CURTAIN, [(1024, 0), (1024 - 110, 0), (1024 - 55, 430), (1024, 430)])
for vx in range(120, 890, 110):
    pygame.draw.circle(surf_view, teatrino.STAGE_CURTAIN, (vx + 55, 24), 62)
    pygame.draw.circle(surf_view, teatrino.STAGE_GOLD, (vx + 55, 24), 62, width=2)
pygame.draw.rect(surf_view, teatrino.STAGE_GOLD, (0, 10, 1024, 4))

# Viewer controls: [⏹️ Esci] and [🔁 Rivedi]
exit_rect = pygame.Rect(140, 16, 110, 52)
pygame.draw.rect(surf_view, (255, 230, 230), exit_rect, border_radius=14)
pygame.draw.rect(surf_view, (220, 38, 38), exit_rect, width=2, border_radius=14)
exit_s = typography.render("⏹️ Esci", FontRole.TITLE, 15, (185, 28, 28))
surf_view.blit(exit_s, (exit_rect.centerx - exit_s.get_width() // 2, exit_rect.centery - exit_s.get_height() // 2))

rep_rect = pygame.Rect(265, 16, 120, 52)
pygame.draw.rect(surf_view, (255, 250, 240), rep_rect, border_radius=14)
pygame.draw.rect(surf_view, (61, 44, 31), rep_rect, width=2, border_radius=14)
rep_s = typography.render("🔁 Rivedi", FontRole.TITLE, 15, teatrino.DARK_TEXT)
surf_view.blit(rep_s, (rep_rect.centerx - rep_s.get_width() // 2, rep_rect.centery - rep_s.get_height() // 2))

fb_surf = typography.render("🎬 La Festa nella Casetta (14s)", FontRole.TITLE, 20, teatrino.STAGE_GOLD)
fb_bg = pygame.Rect(512 - fb_surf.get_width() // 2 - 20, 16, fb_surf.get_width() + 40, 48)
pygame.draw.rect(surf_view, (20, 16, 32), fb_bg, border_radius=12)
pygame.draw.rect(surf_view, teatrino.STAGE_GOLD, fb_bg, width=2, border_radius=12)
surf_view.blit(fb_surf, (512 - fb_surf.get_width() // 2, 28))

out_view = OUT_DIR / "viewer_mode_theatrical.png"
pygame.image.save(surf_view, str(out_view))
print(f"Captured {out_view}")

print("All Iteration 2 visual evidence captured!")
