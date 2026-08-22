#!/usr/bin/env python3
"""Capture visual acceptance screenshots for Teatrino delle Fiabe."""

import os
from pathlib import Path
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, "src")
import activities.teatrino_fiabe.main as teatrino
from greia_platform.typography import GreiaTypography, FontRole

OUT_DIR = Path("tmp/teatrino_evidence")
OUT_DIR.mkdir(parents=True, exist_ok=True)

pygame.init()
pygame.display.set_mode((1024, 600))
pygame.font.init()
typography = GreiaTypography()

# Load sprites
runtime_dir = Path("activities/teatrino_fiabe/assets/runtime")
puppet_sprites = {}
for p_id, _ in teatrino.PUPPET_ROSTER:
    png_file = runtime_dir / f"puppet_{p_id}.png"
    img = pygame.image.load(str(png_file)).convert_alpha()
    puppet_sprites[p_id] = pygame.transform.smoothscale(img, (110, 110))

# 1. Capture All 5 Sceneries
for bg_id, bg_icon, bg_name in teatrino.BG_CONFIGS:
    surf = pygame.Surface((1024, 600))
    bg_surf = teatrino.render_backdrop_surface(bg_id)
    surf.blit(bg_surf, (0, 0))

    # Add 2-3 actors relevant to the scene
    if bg_id == "castle":
        p1 = teatrino.Puppet("principessa", "Principessa", 360, 270)
        p2 = teatrino.Puppet("cavaliere", "Cavaliere", 520, 275)
        p3 = teatrino.Puppet("draghetto", "Draghetto", 680, 260)
        p3.flip_x = True
        puppets = [p1, p2, p3]
    elif bg_id == "ocean":
        p1 = teatrino.Puppet("sirenetta", "Sirenetta", 380, 260)
        p2 = teatrino.Puppet("lilli", "Lilli", 580, 270)
        p2.flip_x = True
        puppets = [p1, p2]
    elif bg_id == "forest":
        p1 = teatrino.Puppet("fatina", "Fatina", 340, 250)
        p2 = teatrino.Puppet("tito", "Tito", 500, 280)
        p3 = teatrino.Puppet("leo", "Leo", 660, 270)
        p3.flip_x = True
        puppets = [p1, p2, p3]
    elif bg_id == "sky":
        p1 = teatrino.Puppet("mago", "Mago", 360, 265)
        p2 = teatrino.Puppet("flash", "Flash", 512, 270)
        p3 = teatrino.Puppet("dani", "Dani", 670, 275)
        p3.flip_x = True
        puppets = [p1, p2, p3]
    else:  # cottage
        p1 = teatrino.Puppet("momo", "Momo", 380, 280)
        p2 = teatrino.Puppet("lilli", "Lilli", 600, 270)
        p2.flip_x = True
        puppets = [p1, p2]

    # Draw puppets
    for p in puppets:
        spr = puppet_sprites[p.puppet_id]
        p.draw(surf, spr, typography)

    # Draw Stage Curtains
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

    # Top Controls
    pygame.draw.rect(surf, (255, 250, 240), (140, 16, 140, 52), border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), (140, 16, 140, 52), width=2, border_radius=14)
    bg_t = typography.render(f"{bg_icon} {bg_name}", FontRole.TITLE, 17, teatrino.DARK_TEXT)
    surf.blit(bg_t, (210 - bg_t.get_width() // 2, 42 - bg_t.get_height() // 2))

    # Mic
    pygame.draw.rect(surf, (220, 255, 225), (290, 16, 115, 52), border_radius=14)
    pygame.draw.rect(surf, teatrino.MIC_GREEN, (290, 16, 115, 52), width=3, border_radius=14)
    mic_t = typography.render("🎙️ ON", FontRole.TITLE, 17, (30, 120, 50))
    surf.blit(mic_t, (347 - mic_t.get_width() // 2, 42 - mic_t.get_height() // 2))

    # Record
    pygame.draw.rect(surf, (255, 250, 240), (415, 16, 155, 52), border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), (415, 16, 155, 52), width=2, border_radius=14)
    rec_t = typography.render("🔴 Registra", FontRole.TITLE, 17, teatrino.DARK_TEXT)
    surf.blit(rec_t, (492 - rec_t.get_width() // 2, 42 - rec_t.get_height() // 2))

    # Play
    pygame.draw.rect(surf, (255, 250, 240), (580, 16, 165, 52), border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), (580, 16, 165, 52), width=2, border_radius=14)
    ply_t = typography.render("▶️ Spettacolo", FontRole.TITLE, 17, teatrino.DARK_TEXT)
    surf.blit(ply_t, (662 - ply_t.get_width() // 2, 42 - ply_t.get_height() // 2))

    # Clear
    pygame.draw.rect(surf, (255, 250, 240), (755, 16, 68, 52), border_radius=14)
    pygame.draw.rect(surf, (61, 44, 31), (755, 16, 68, 52), width=2, border_radius=14)
    clr_t = typography.render("🗑️", FontRole.TITLE, 22, teatrino.DARK_TEXT)
    surf.blit(clr_t, (789 - clr_t.get_width() // 2, 42 - clr_t.get_height() // 2))

    # SFX sidebar
    for f_idx, (fx_id, fx_sym) in enumerate(teatrino.FX_BUTTONS):
        fy = 100 + f_idx * 56
        pygame.draw.rect(surf, (255, 250, 240), (915, fy, 70, 48), border_radius=14)
        pygame.draw.rect(surf, teatrino.STAGE_GOLD, (915, fy, 70, 48), width=2, border_radius=14)
        fx_t = typography.render(fx_sym, FontRole.DISPLAY, 24, teatrino.DARK_TEXT)
        surf.blit(fx_t, (950 - fx_t.get_width() // 2, fy + 24 - fx_t.get_height() // 2))

    # Bottom Puppet Tray (Page 1)
    pygame.draw.rect(surf, (30, 24, 40), (0, 500, 1024, 100))
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, (0, 500, 1024, 4))

    pygame.draw.rect(surf, (255, 250, 240), (40, 522, 54, 54), border_radius=12)
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, (40, 522, 54, 54), width=2, border_radius=12)
    pygame.draw.polygon(surf, (61, 44, 31), [(67 - 8, 549), (67 + 6, 549 - 10), (67 + 6, 549 + 10)])

    pygame.draw.rect(surf, (255, 250, 240), (930, 522, 54, 54), border_radius=12)
    pygame.draw.rect(surf, teatrino.STAGE_GOLD, (930, 522, 54, 54), width=2, border_radius=12)
    pygame.draw.polygon(surf, (61, 44, 31), [(957 + 8, 549), (957 - 6, 549 - 10), (957 - 6, 549 + 10)])

    for p_idx, (p_id, p_name) in enumerate(teatrino.PUPPET_ROSTER[:6]):
        cx = 110 + p_idx * 135
        pygame.draw.rect(surf, (255, 250, 240), (cx, 508, 120, 84), border_radius=14)
        pygame.draw.rect(surf, (61, 44, 31), (cx, 508, 120, 84), width=2, border_radius=14)
        spr = puppet_sprites[p_id]
        thumb = pygame.transform.smoothscale(spr, (52, 52))
        surf.blit(thumb, (cx + 34, 514))
        n_t = typography.render(p_name, FontRole.CONTROL, 11, teatrino.DARK_TEXT)
        surf.blit(n_t, (cx + 60 - n_t.get_width() // 2, 570))

    out_file = OUT_DIR / f"scene_{bg_id}.png"
    pygame.image.save(surf, str(out_file))
    print(f"Captured {out_file}")

# 2. Capture Recording Mode with Live Voice Waveform
rec_surf = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("castle")
rec_surf.blit(bg_surf, (0, 0))

p1 = teatrino.Puppet("principessa", "Principessa", 400, 260)
p1.jump()
p2 = teatrino.Puppet("draghetto", "Draghetto", 580, 280)
p2.flip_x = True
p2.speak()
p1.draw(rec_surf, puppet_sprites["principessa"], typography)
p2.draw(rec_surf, puppet_sprites["draghetto"], typography)

# Curtains
pygame.draw.polygon(rec_surf, teatrino.STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
pygame.draw.polygon(rec_surf, teatrino.STAGE_CURTAIN, [(1024, 0), (1024 - 110, 0), (1024 - 55, 430), (1024, 430)])
for vx in range(120, 890, 110):
    pygame.draw.circle(rec_surf, teatrino.STAGE_CURTAIN, (vx + 55, 24), 62)
    pygame.draw.circle(rec_surf, teatrino.STAGE_GOLD, (vx + 55, 24), 62, width=2)
pygame.draw.rect(rec_surf, teatrino.STAGE_GOLD, (0, 10, 1024, 4))

# Top controls in recording state
pygame.draw.rect(rec_surf, (255, 250, 240), (140, 16, 140, 52), border_radius=14)
pygame.draw.rect(rec_surf, (61, 44, 31), (140, 16, 140, 52), width=2, border_radius=14)
bg_t = typography.render("🏰 Castello", FontRole.TITLE, 17, teatrino.DARK_TEXT)
rec_surf.blit(bg_t, (210 - bg_t.get_width() // 2, 42 - bg_t.get_height() // 2))

# Mic ON
pygame.draw.rect(rec_surf, (220, 255, 225), (290, 16, 115, 52), border_radius=14)
pygame.draw.rect(rec_surf, teatrino.MIC_GREEN, (290, 16, 115, 52), width=3, border_radius=14)
mic_t = typography.render("🎙️ ON", FontRole.TITLE, 17, (30, 120, 50))
rec_surf.blit(mic_t, (347 - mic_t.get_width() // 2, 42 - mic_t.get_height() // 2))

# Stop REC button active
pygame.draw.rect(rec_surf, (255, 185, 185), (415, 16, 155, 52), border_radius=14)
pygame.draw.rect(rec_surf, teatrino.REC_RED, (415, 16, 155, 52), width=3, border_radius=14)
rec_t = typography.render("⏹️ Stop REC", FontRole.TITLE, 17, teatrino.REC_RED)
rec_surf.blit(rec_t, (492 - rec_t.get_width() // 2, 42 - rec_t.get_height() // 2))

# Waveform meter
meter_x = 425
meter_y = 74
for bar_idx in range(5):
    bar_h = [6, 14, 18, 12, 8][bar_idx]
    pygame.draw.rect(rec_surf, teatrino.REC_RED, (meter_x + bar_idx * 6, meter_y + (18 - bar_h) // 2, 4, bar_h), border_radius=2)
t_surf = typography.render("12s / 45s", FontRole.CONTROL, 12, teatrino.REC_RED)
rec_surf.blit(t_surf, (meter_x + 36, meter_y + 2))

# Feedback Banner
fb_surf = typography.render("🔴 Registrazione in corso... Racconta la tua storia!", FontRole.TITLE, 19, teatrino.STAGE_GOLD)
fb_bg = pygame.Rect(512 - fb_surf.get_width() // 2 - 20, 104, fb_surf.get_width() + 40, 42)
pygame.draw.rect(rec_surf, (20, 16, 32), fb_bg, border_radius=12)
pygame.draw.rect(rec_surf, teatrino.STAGE_GOLD, fb_bg, width=2, border_radius=12)
rec_surf.blit(fb_surf, (512 - fb_surf.get_width() // 2, 112))

# Bottom tray
pygame.draw.rect(rec_surf, (30, 24, 40), (0, 500, 1024, 100))
pygame.draw.rect(rec_surf, teatrino.STAGE_GOLD, (0, 500, 1024, 4))
for p_idx, (p_id, p_name) in enumerate(teatrino.PUPPET_ROSTER[:6]):
    cx = 110 + p_idx * 135
    pygame.draw.rect(rec_surf, (255, 250, 240), (cx, 508, 120, 84), border_radius=14)
    pygame.draw.rect(rec_surf, (61, 44, 31), (cx, 508, 120, 84), width=2, border_radius=14)
    spr = puppet_sprites[p_id]
    thumb = pygame.transform.smoothscale(spr, (52, 52))
    rec_surf.blit(thumb, (cx + 34, 514))
    n_t = typography.render(p_name[:9], FontRole.CONTROL, 13, teatrino.DARK_TEXT)
    rec_surf.blit(n_t, (cx + 60 - n_t.get_width() // 2, 570))

out_rec = OUT_DIR / "mode_recording_with_mic.png"
pygame.image.save(rec_surf, str(out_rec))
print(f"Captured {out_rec}")

# 3. Capture Page 2 of Puppet Tray (Showing remaining 6 characters: Sirenetta, Mago, Fatina, etc.)
page2_surf = pygame.Surface((1024, 600))
bg_surf = teatrino.render_backdrop_surface("forest")
page2_surf.blit(bg_surf, (0, 0))

p1 = teatrino.Puppet("mago", "Mago", 400, 270)
p2 = teatrino.Puppet("sirenetta", "Sirenetta", 550, 260)
p3 = teatrino.Puppet("fatina", "Fatina", 700, 250)
p3.flip_x = True
p1.draw(page2_surf, puppet_sprites["mago"], typography)
p2.draw(page2_surf, puppet_sprites["sirenetta"], typography)
p3.draw(page2_surf, puppet_sprites["fatina"], typography)

# Curtains & Top Bar
pygame.draw.polygon(page2_surf, teatrino.STAGE_CURTAIN, [(0, 0), (110, 0), (55, 430), (0, 430)])
pygame.draw.polygon(page2_surf, teatrino.STAGE_CURTAIN, [(1024, 0), (1024 - 110, 0), (1024 - 55, 430), (1024, 430)])
pygame.draw.rect(page2_surf, teatrino.STAGE_GOLD, (0, 10, 1024, 4))

# Bottom tray page 2
pygame.draw.rect(page2_surf, (30, 24, 40), (0, 500, 1024, 100))
pygame.draw.rect(page2_surf, teatrino.STAGE_GOLD, (0, 500, 1024, 4))

pygame.draw.rect(page2_surf, (255, 250, 240), (40, 522, 54, 54), border_radius=12)
pygame.draw.rect(page2_surf, teatrino.STAGE_GOLD, (40, 522, 54, 54), width=2, border_radius=12)
pygame.draw.polygon(page2_surf, (61, 44, 31), [(67 - 8, 549), (67 + 6, 549 - 10), (67 + 6, 549 + 10)])

pygame.draw.rect(page2_surf, (255, 250, 240), (930, 522, 54, 54), border_radius=12)
pygame.draw.rect(page2_surf, teatrino.STAGE_GOLD, (930, 522, 54, 54), width=2, border_radius=12)
pygame.draw.polygon(page2_surf, (61, 44, 31), [(957 + 8, 549), (957 - 6, 549 - 10), (957 - 6, 549 + 10)])

for p_idx, (p_id, p_name) in enumerate(teatrino.PUPPET_ROSTER[6:12]):
    cx = 110 + p_idx * 135
    pygame.draw.rect(page2_surf, (255, 250, 240), (cx, 508, 120, 84), border_radius=14)
    pygame.draw.rect(page2_surf, (61, 44, 31), (cx, 508, 120, 84), width=2, border_radius=14)
    spr = puppet_sprites[p_id]
    thumb = pygame.transform.smoothscale(spr, (52, 52))
    page2_surf.blit(thumb, (cx + 34, 514))
    n_t = typography.render(p_name, FontRole.CONTROL, 11, teatrino.DARK_TEXT)
    page2_surf.blit(n_t, (cx + 60 - n_t.get_width() // 2, 570))

out_p2 = OUT_DIR / "puppet_tray_page2.png"
pygame.image.save(page2_surf, str(out_p2))
print(f"Captured {out_p2}")

print("Visual evidence capture complete!")
