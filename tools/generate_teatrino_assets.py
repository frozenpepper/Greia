#!/usr/bin/env python3
"""Generate crisp, storybook-style SVGs and rasterize PNGs for Teatrino delle Fiabe."""

from pathlib import Path
import subprocess

OUT_SRC = Path("activities/teatrino_fiabe/assets/source")
OUT_RUN = Path("activities/teatrino_fiabe/assets/runtime")
OUT_ICON = Path("activities/teatrino_fiabe/assets/icon.png")

OUT_SRC.mkdir(parents=True, exist_ok=True)
OUT_RUN.mkdir(parents=True, exist_ok=True)

SVGS = {}

# 1. LILLI - Unicorn
SVGS["puppet_lilli.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="lilli_horn" x1="0" y1="1" x2="0.8" y2="0">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="50%" stop-color="#FDE047"/>
      <stop offset="100%" stop-color="#FFFBEB"/>
    </linearGradient>
    <linearGradient id="lilli_mane" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F472B6"/>
      <stop offset="50%" stop-color="#A78BFA"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>
    <linearGradient id="lilli_body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#FEF3C7"/>
    </linearGradient>
  </defs>
  <!-- Mane Back -->
  <path d="M 60 70 C 40 85 45 130 65 145 C 55 125 55 95 75 80 Z" fill="url(#lilli_mane)"/>
  <!-- Body & Legs -->
  <ellipse cx="100" cy="130" rx="46" ry="36" fill="url(#lilli_body)" stroke="#78350F" stroke-width="4"/>
  <rect x="72" y="145" width="16" height="32" rx="8" fill="url(#lilli_body)" stroke="#78350F" stroke-width="4"/>
  <rect x="112" y="145" width="16" height="32" rx="8" fill="url(#lilli_body)" stroke="#78350F" stroke-width="4"/>
  <!-- Pink Hooves -->
  <path d="M 72 165 L 88 165 C 88 173 88 177 80 177 C 72 177 72 173 72 165 Z" fill="#F472B6"/>
  <path d="M 112 165 L 128 165 C 128 173 128 177 120 177 C 112 177 112 173 112 165 Z" fill="#F472B6"/>
  <!-- Tail -->
  <path d="M 58 135 C 35 140 25 165 45 175 C 38 158 48 145 60 142 Z" fill="url(#lilli_mane)" stroke="#78350F" stroke-width="3"/>
  <!-- Star Mark on Flank -->
  <polygon points="76,122 78,127 84,127 79,130 81,136 76,132 71,136 73,130 68,127 74,127" fill="#F59E0B"/>
  <!-- Head -->
  <ellipse cx="125" cy="85" rx="34" ry="30" fill="url(#lilli_body)" stroke="#78350F" stroke-width="4"/>
  <ellipse cx="145" cy="92" rx="18" ry="14" fill="#FFFBEB" stroke="#78350F" stroke-width="3"/>
  <!-- Horn -->
  <polygon points="120,60 148,22 134,60" fill="url(#lilli_horn)" stroke="#D97706" stroke-width="3"/>
  <line x1="126" y1="50" x2="140" y2="40" stroke="#B45309" stroke-width="2"/>
  <line x1="130" y1="40" x2="144" y2="30" stroke="#B45309" stroke-width="2"/>
  <!-- Ears -->
  <path d="M 105 65 C 100 50 115 48 118 62 Z" fill="url(#lilli_body)" stroke="#78350F" stroke-width="3"/>
  <path d="M 108 62 C 105 54 113 52 115 60 Z" fill="#F472B6"/>
  <!-- Mane Front Bangs -->
  <path d="M 115 58 C 128 62 132 75 122 82 C 128 72 138 72 135 60 Z" fill="url(#lilli_mane)"/>
  <!-- Eye -->
  <circle cx="132" cy="80" r="7" fill="#1E1B4B"/>
  <circle cx="134" cy="78" r="2.5" fill="#FFFFFF"/>
  <circle cx="130" cy="82" r="1.2" fill="#FFFFFF"/>
  <!-- Cheek & Muzzle -->
  <ellipse cx="140" cy="92" rx="5" ry="3.5" fill="#F472B6" opacity="0.8"/>
  <circle cx="152" cy="88" r="2" fill="#78350F"/>
  <path d="M 148 96 Q 153 100 157 95" stroke="#78350F" stroke-width="2.5" fill="none" stroke-linecap="round"/>
</svg>"""

# 2. LEO - Owl
SVGS["puppet_leo.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="leo_body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#92400E"/>
      <stop offset="100%" stop-color="#78350F"/>
    </linearGradient>
    <linearGradient id="leo_belly" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FEF3C7"/>
      <stop offset="100%" stop-color="#FDE68A"/>
    </linearGradient>
  </defs>
  <!-- Ear Tufts -->
  <polygon points="62,60 50,30 80,48" fill="#92400E" stroke="#451A03" stroke-width="4"/>
  <polygon points="138,60 150,30 120,48" fill="#92400E" stroke="#451A03" stroke-width="4"/>
  <!-- Main Body -->
  <ellipse cx="100" cy="115" rx="52" ry="62" fill="url(#leo_body)" stroke="#451A03" stroke-width="4"/>
  <!-- Belly -->
  <ellipse cx="100" cy="130" rx="34" ry="40" fill="url(#leo_belly)" stroke="#451A03" stroke-width="3"/>
  <path d="M 88 120 Q 100 126 112 120 M 86 135 Q 100 142 114 135 M 90 150 Q 100 156 110 150" stroke="#D97706" stroke-width="3" fill="none" stroke-linecap="round"/>
  <!-- Wings -->
  <path d="M 50 90 C 35 115 40 145 56 160 C 46 140 48 110 60 92 Z" fill="#78350F" stroke="#451A03" stroke-width="3"/>
  <path d="M 150 90 C 165 115 160 145 144 160 C 154 140 152 110 140 92 Z" fill="#78350F" stroke="#451A03" stroke-width="3"/>
  <!-- Feet -->
  <ellipse cx="85" cy="176" rx="10" ry="6" fill="#F59E0B" stroke="#451A03" stroke-width="3"/>
  <ellipse cx="115" cy="176" rx="10" ry="6" fill="#F59E0B" stroke="#451A03" stroke-width="3"/>
  <!-- Face Mask Disc -->
  <circle cx="76" cy="84" r="22" fill="#FEF3C7" stroke="#451A03" stroke-width="3"/>
  <circle cx="124" cy="84" r="22" fill="#FEF3C7" stroke="#451A03" stroke-width="3"/>
  <!-- Glasses -->
  <rect x="56" y="66" width="38" height="36" rx="12" fill="#38BDF8" fill-opacity="0.25" stroke="#0284C7" stroke-width="4.5"/>
  <rect x="106" y="66" width="38" height="36" rx="12" fill="#38BDF8" fill-opacity="0.25" stroke="#0284C7" stroke-width="4.5"/>
  <line x1="94" y1="84" x2="106" y2="84" stroke="#0284C7" stroke-width="4.5"/>
  <!-- Eyes -->
  <circle cx="75" cy="84" r="10" fill="#1E1B4B"/>
  <circle cx="125" cy="84" r="10" fill="#1E1B4B"/>
  <circle cx="77" cy="81" r="3.5" fill="#FFFFFF"/>
  <circle cx="127" cy="81" r="3.5" fill="#FFFFFF"/>
  <!-- Beak -->
  <polygon points="94,88 106,88 100,104" fill="#F59E0B" stroke="#B45309" stroke-width="2.5"/>
</svg>"""

# 3. FLASH - Rabbit
SVGS["puppet_flash.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="flash_fur" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FB923C"/>
      <stop offset="100%" stop-color="#EA580C"/>
    </linearGradient>
  </defs>
  <!-- Long Ears -->
  <ellipse cx="78" cy="42" rx="14" ry="38" fill="url(#flash_fur)" stroke="#7C2D12" stroke-width="4" transform="rotate(-10 78 42)"/>
  <ellipse cx="78" cy="42" rx="7" ry="26" fill="#FED7AA" transform="rotate(-10 78 42)"/>
  <ellipse cx="122" cy="42" rx="14" ry="38" fill="url(#flash_fur)" stroke="#7C2D12" stroke-width="4" transform="rotate(10 122 42)"/>
  <ellipse cx="122" cy="42" rx="7" ry="26" fill="#FED7AA" transform="rotate(10 122 42)"/>
  <!-- Body -->
  <ellipse cx="100" cy="138" rx="42" ry="40" fill="url(#flash_fur)" stroke="#7C2D12" stroke-width="4"/>
  <!-- Belly -->
  <ellipse cx="100" cy="144" rx="26" ry="26" fill="#FFF7ED"/>
  <!-- Feet -->
  <ellipse cx="72" cy="178" rx="18" ry="10" fill="#FFF7ED" stroke="#7C2D12" stroke-width="3.5"/>
  <ellipse cx="128" cy="178" rx="18" ry="10" fill="#FFF7ED" stroke="#7C2D12" stroke-width="3.5"/>
  <!-- Paws -->
  <ellipse cx="68" cy="132" rx="10" ry="14" fill="#FFF7ED" stroke="#7C2D12" stroke-width="3" transform="rotate(20 68 132)"/>
  <ellipse cx="132" cy="132" rx="10" ry="14" fill="#FFF7ED" stroke="#7C2D12" stroke-width="3" transform="rotate(-20 132 132)"/>
  <!-- Head -->
  <circle cx="100" cy="95" r="36" fill="url(#flash_fur)" stroke="#7C2D12" stroke-width="4"/>
  <!-- Cheeks -->
  <circle cx="76" cy="104" r="9" fill="#FFEDD5"/>
  <circle cx="124" cy="104" r="9" fill="#FFEDD5"/>
  <circle cx="74" cy="102" r="4.5" fill="#F43F5E" opacity="0.5"/>
  <circle cx="126" cy="102" r="4.5" fill="#F43F5E" opacity="0.5"/>
  <!-- Eyes -->
  <ellipse cx="84" cy="88" rx="7" ry="9" fill="#1E1B4B"/>
  <ellipse cx="116" cy="88" rx="7" ry="9" fill="#1E1B4B"/>
  <circle cx="86" cy="85" r="3" fill="#FFFFFF"/>
  <circle cx="118" cy="85" r="3" fill="#FFFFFF"/>
  <!-- Nose & Mouth -->
  <polygon points="96,98 104,98 100,103" fill="#F43F5E"/>
  <path d="M 94 105 Q 100 110 100 105 Q 100 110 106 105" stroke="#7C2D12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
</svg>"""

# 4. DANI - Robot
SVGS["puppet_dani.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="dani_metal" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
    <linearGradient id="dani_screen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E293B"/>
    </linearGradient>
  </defs>
  <!-- Antenna -->
  <line x1="100" y1="52" x2="100" y2="28" stroke="#0369A1" stroke-width="5" stroke-linecap="round"/>
  <circle cx="100" cy="24" r="9" fill="#FBBF24" stroke="#D97706" stroke-width="3"/>
  <!-- Body -->
  <rect x="62" y="115" width="76" height="54" rx="14" fill="url(#dani_metal)" stroke="#0C4A6E" stroke-width="4"/>
  <!-- Chest Gauge -->
  <rect x="74" y="125" width="52" height="22" rx="6" fill="#E0F2FE" stroke="#0284C7" stroke-width="2.5"/>
  <circle cx="86" cy="136" r="4" fill="#10B981"/>
  <circle cx="100" cy="136" r="4" fill="#F59E0B"/>
  <circle cx="114" cy="136" r="4" fill="#EF4444"/>
  <!-- Wheels / Tread Feet -->
  <rect x="70" y="169" width="22" height="15" rx="6" fill="#64748B" stroke="#0F172A" stroke-width="3"/>
  <rect x="108" y="169" width="22" height="15" rx="6" fill="#64748B" stroke="#0F172A" stroke-width="3"/>
  <!-- Arms -->
  <path d="M 62 130 Q 42 140 48 155" stroke="#0284C7" stroke-width="8" stroke-linecap="round" fill="none"/>
  <circle cx="48" cy="155" r="7" fill="#FBBF24" stroke="#D97706" stroke-width="2.5"/>
  <path d="M 138 130 Q 158 140 152 155" stroke="#0284C7" stroke-width="8" stroke-linecap="round" fill="none"/>
  <circle cx="152" cy="155" r="7" fill="#FBBF24" stroke="#D97706" stroke-width="2.5"/>
  <!-- Head -->
  <rect x="56" y="48" width="88" height="62" rx="18" fill="url(#dani_metal)" stroke="#0C4A6E" stroke-width="4"/>
  <!-- Screen Face -->
  <rect x="68" y="58" width="64" height="42" rx="10" fill="url(#dani_screen)" stroke="#38BDF8" stroke-width="2.5"/>
  <!-- Glowing Screen Eyes -->
  <ellipse cx="84" cy="76" rx="7" ry="8" fill="#22D3EE"/>
  <ellipse cx="116" cy="76" rx="7" ry="8" fill="#22D3EE"/>
  <circle cx="86" cy="74" r="2.5" fill="#FFFFFF"/>
  <circle cx="118" cy="74" r="2.5" fill="#FFFFFF"/>
  <!-- Smile -->
  <path d="M 94 88 Q 100 93 106 88" stroke="#22D3EE" stroke-width="3" stroke-linecap="round" fill="none"/>
</svg>"""

# 5. TITO - Fox
SVGS["puppet_tito.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="tito_fur" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#F97316"/>
      <stop offset="100%" stop-color="#C2410C"/>
    </linearGradient>
  </defs>
  <!-- Bushy Tail -->
  <path d="M 130 130 C 170 120 185 160 155 175 C 135 185 125 155 130 130 Z" fill="url(#tito_fur)" stroke="#7C2D12" stroke-width="4"/>
  <path d="M 165 140 C 180 155 175 168 155 175 C 160 162 155 150 165 140 Z" fill="#FFF7ED"/>
  <!-- Ears -->
  <polygon points="62,65 52,25 86,48" fill="url(#tito_fur)" stroke="#7C2D12" stroke-width="4"/>
  <polygon points="60,58 56,36 78,48" fill="#431407"/>
  <polygon points="138,65 148,25 114,48" fill="url(#tito_fur)" stroke="#7C2D12" stroke-width="4"/>
  <polygon points="140,58 144,36 122,48" fill="#431407"/>
  <!-- Body -->
  <ellipse cx="100" cy="138" rx="40" ry="38" fill="url(#tito_fur)" stroke="#7C2D12" stroke-width="4"/>
  <ellipse cx="100" cy="144" rx="24" ry="26" fill="#FFF7ED"/>
  <!-- Feet -->
  <ellipse cx="78" cy="176" rx="12" ry="8" fill="#431407"/>
  <ellipse cx="122" cy="176" rx="12" ry="8" fill="#431407"/>
  <!-- Head -->
  <ellipse cx="100" cy="94" rx="44" ry="34" fill="url(#tito_fur)" stroke="#7C2D12" stroke-width="4"/>
  <!-- White Cheeks -->
  <path d="M 58 98 C 65 115 88 122 100 114 C 112 122 135 115 142 98 C 128 92 115 104 100 100 C 85 104 72 92 58 98 Z" fill="#FFF7ED" stroke="#7C2D12" stroke-width="2.5"/>
  <!-- Eyes -->
  <ellipse cx="80" cy="85" rx="6" ry="8" fill="#1E1B4B"/>
  <ellipse cx="120" cy="85" rx="6" ry="8" fill="#1E1B4B"/>
  <circle cx="82" cy="82" r="2.5" fill="#FFFFFF"/>
  <circle cx="122" cy="82" r="2.5" fill="#FFFFFF"/>
  <!-- Nose -->
  <circle cx="100" cy="105" r="5.5" fill="#1E1B4B"/>
  <path d="M 95 112 Q 100 116 105 112" stroke="#7C2D12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
</svg>"""

# 6. MOMO - Monster
SVGS["puppet_momo.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="momo_fluff" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#C084FC"/>
      <stop offset="100%" stop-color="#9333EA"/>
    </linearGradient>
  </defs>
  <!-- Horns / Antennae -->
  <path d="M 68 58 Q 50 35 62 25 Q 74 35 74 52" fill="#FDE047" stroke="#854D0E" stroke-width="3.5"/>
  <path d="M 132 58 Q 150 35 138 25 Q 126 35 126 52" fill="#FDE047" stroke="#854D0E" stroke-width="3.5"/>
  <!-- Main Fluffy Body -->
  <ellipse cx="100" cy="115" rx="58" ry="62" fill="url(#momo_fluff)" stroke="#581C87" stroke-width="4.5"/>
  <!-- Spots -->
  <circle cx="68" cy="145" r="7" fill="#E9D5FF" opacity="0.6"/>
  <circle cx="135" cy="140" r="9" fill="#E9D5FF" opacity="0.6"/>
  <circle cx="125" cy="160" r="5" fill="#E9D5FF" opacity="0.6"/>
  <!-- Little Feet -->
  <ellipse cx="75" cy="176" rx="14" ry="9" fill="#7E22CE" stroke="#581C87" stroke-width="3"/>
  <ellipse cx="125" cy="176" rx="14" ry="9" fill="#7E22CE" stroke="#581C87" stroke-width="3"/>
  <!-- Big Friendly Eyes -->
  <circle cx="78" cy="85" r="16" fill="#FFFFFF" stroke="#581C87" stroke-width="3.5"/>
  <circle cx="122" cy="85" r="16" fill="#FFFFFF" stroke="#581C87" stroke-width="3.5"/>
  <circle cx="80" cy="85" r="8" fill="#1E1B4B"/>
  <circle cx="120" cy="85" r="8" fill="#1E1B4B"/>
  <circle cx="82" cy="82" r="3" fill="#FFFFFF"/>
  <circle cx="122" cy="82" r="3" fill="#FFFFFF"/>
  <!-- Wide Happy Grin with Cute Tooth -->
  <path d="M 76 114 Q 100 138 124 114 Z" fill="#581C87"/>
  <polygon points="94,114 100,122 106,114" fill="#FFFFFF"/>
  <path d="M 85 125 Q 100 135 115 125" fill="#F43F5E"/>
</svg>"""

# 7. PRINCIPESSA - Fairy Tale Princess
SVGS["puppet_principessa.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="prin_hair" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FDE047"/>
      <stop offset="100%" stop-color="#EAB308"/>
    </linearGradient>
    <linearGradient id="prin_dress" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#F472B6"/>
      <stop offset="100%" stop-color="#DB2777"/>
    </linearGradient>
  </defs>
  <!-- Hair Back -->
  <path d="M 52 75 C 38 110 45 155 60 165 C 50 130 65 95 75 75 Z" fill="url(#prin_hair)" stroke="#854D0E" stroke-width="3"/>
  <path d="M 148 75 C 162 110 155 155 140 165 C 150 130 135 95 125 75 Z" fill="url(#prin_hair)" stroke="#854D0E" stroke-width="3"/>
  <!-- Ballgown -->
  <path d="M 85 110 L 115 110 L 148 175 C 120 185 80 185 52 175 Z" fill="url(#prin_dress)" stroke="#831843" stroke-width="4"/>
  <!-- Gown Peplum / Gold Trim -->
  <path d="M 75 125 Q 100 142 125 125" stroke="#FDE047" stroke-width="4" fill="none"/>
  <!-- Bodice -->
  <path d="M 86 95 L 114 95 L 116 118 L 84 118 Z" fill="#FDF2F8" stroke="#831843" stroke-width="3"/>
  <!-- Puff Sleeves -->
  <circle cx="78" cy="102" r="11" fill="url(#prin_dress)" stroke="#831843" stroke-width="3"/>
  <circle cx="122" cy="102" r="11" fill="url(#prin_dress)" stroke="#831843" stroke-width="3"/>
  <!-- Arms & Magic Wand -->
  <rect x="70" y="112" width="8" height="18" rx="4" fill="#FEE2E2"/>
  <rect x="122" y="112" width="8" height="18" rx="4" fill="#FEE2E2"/>
  <!-- Star Wand -->
  <line x1="130" y1="130" x2="148" y2="92" stroke="#D97706" stroke-width="3"/>
  <polygon points="148,82 152,90 160,91 154,97 156,105 148,100 140,105 142,97 136,91 144,90" fill="#FDE047" stroke="#B45309" stroke-width="2"/>
  <!-- Head -->
  <ellipse cx="100" cy="76" rx="24" ry="22" fill="#FEE2E2" stroke="#854D0E" stroke-width="3"/>
  <!-- Hair Front Bangs -->
  <path d="M 76 70 C 85 55 115 55 124 70 C 115 65 85 65 76 70 Z" fill="url(#prin_hair)" stroke="#854D0E" stroke-width="2.5"/>
  <!-- Crown / Tiara -->
  <polygon points="84,54 88,40 94,48 100,34 106,48 112,40 116,54" fill="#FDE047" stroke="#B45309" stroke-width="2.5"/>
  <circle cx="100" cy="46" r="3" fill="#EF4444"/>
  <!-- Eyes -->
  <ellipse cx="91" cy="74" rx="4.5" ry="6" fill="#1E1B4B"/>
  <ellipse cx="109" cy="74" rx="4.5" ry="6" fill="#1E1B4B"/>
  <circle cx="92.5" cy="72" r="2" fill="#FFFFFF"/>
  <circle cx="110.5" cy="72" r="2" fill="#FFFFFF"/>
  <!-- Cheeks & Smile -->
  <circle cx="86" cy="80" r="3.5" fill="#F43F5E" opacity="0.6"/>
  <circle cx="114" cy="80" r="3.5" fill="#F43F5E" opacity="0.6"/>
  <path d="M 96 83 Q 100 87 104 83" stroke="#9F1239" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>"""

# 8. DRAGHETTO - Baby Dragon
SVGS["puppet_draghetto.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="drag_scale" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#34D399"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <!-- Wings -->
  <path d="M 70 85 C 35 60 25 95 55 115 Z" fill="#C084FC" stroke="#581C87" stroke-width="3"/>
  <path d="M 130 85 C 165 60 175 95 145 115 Z" fill="#C084FC" stroke="#581C87" stroke-width="3"/>
  <!-- Tail -->
  <path d="M 130 145 C 160 150 172 170 160 180 C 150 172 142 165 130 160 Z" fill="url(#drag_scale)" stroke="#064E3B" stroke-width="3.5"/>
  <polygon points="162,175 174,178 168,186" fill="#FDE047"/>
  <!-- Body -->
  <ellipse cx="100" cy="135" rx="42" ry="42" fill="url(#drag_scale)" stroke="#064E3B" stroke-width="4"/>
  <!-- Yellow Belly Plates -->
  <ellipse cx="100" cy="142" rx="26" ry="28" fill="#FEF08A" stroke="#064E3B" stroke-width="2.5"/>
  <line x1="82" y1="130" x2="118" y2="130" stroke="#CA8A04" stroke-width="2"/>
  <line x1="78" y1="144" x2="122" y2="144" stroke="#CA8A04" stroke-width="2"/>
  <line x1="82" y1="158" x2="118" y2="158" stroke="#CA8A04" stroke-width="2"/>
  <!-- Feet -->
  <ellipse cx="76" cy="176" rx="14" ry="9" fill="#059669" stroke="#064E3B" stroke-width="3"/>
  <ellipse cx="124" cy="176" rx="14" ry="9" fill="#059669" stroke="#064E3B" stroke-width="3"/>
  <!-- Little Horns -->
  <polygon points="80,55 72,32 90,48" fill="#FDE047" stroke="#854D0E" stroke-width="2.5"/>
  <polygon points="120,55 128,32 110,48" fill="#FDE047" stroke="#854D0E" stroke-width="2.5"/>
  <!-- Head -->
  <ellipse cx="100" cy="85" rx="36" ry="30" fill="url(#drag_scale)" stroke="#064E3B" stroke-width="4"/>
  <ellipse cx="100" cy="94" rx="22" ry="14" fill="#6EE7B7"/>
  <!-- Snout Nostrils & Smoke Spark -->
  <circle cx="94" cy="94" r="2.5" fill="#064E3B"/>
  <circle cx="106" cy="94" r="2.5" fill="#064E3B"/>
  <circle cx="118" cy="90" r="3" fill="#F97316" opacity="0.8"/>
  <circle cx="125" cy="86" r="2" fill="#FDE047" opacity="0.9"/>
  <!-- Big Eyes -->
  <circle cx="82" cy="76" r="10" fill="#1E1B4B"/>
  <circle cx="118" cy="76" r="10" fill="#1E1B4B"/>
  <circle cx="84" cy="74" r="3.5" fill="#FFFFFF"/>
  <circle cx="120" cy="74" r="3.5" fill="#FFFFFF"/>
</svg>"""

# 9. CAVALIERE - Knight
SVGS["puppet_cavaliere.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="armor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#E2E8F0"/>
      <stop offset="100%" stop-color="#94A3B8"/>
    </linearGradient>
  </defs>
  <!-- Red Feather Plume -->
  <path d="M 100 35 C 100 12 135 15 130 35 C 120 30 110 32 100 35 Z" fill="#EF4444" stroke="#991B1B" stroke-width="2.5"/>
  <!-- Body Armor -->
  <rect x="68" y="108" width="64" height="52" rx="10" fill="url(#armor)" stroke="#334155" stroke-width="4"/>
  <!-- Golden Crest on Chest -->
  <polygon points="100,120 106,128 116,128 108,134 111,144 100,138 89,144 92,134 84,128 94,128" fill="#F59E0B"/>
  <!-- Legs -->
  <rect x="74" y="158" width="18" height="20" rx="6" fill="#64748B" stroke="#334155" stroke-width="3"/>
  <rect x="108" y="158" width="18" height="20" rx="6" fill="#64748B" stroke="#334155" stroke-width="3"/>
  <!-- Shield on Left -->
  <path d="M 44 108 L 68 108 L 68 135 C 68 152 44 162 44 162 C 44 162 20 152 20 135 L 20 108 Z" fill="#3B82F6" stroke="#1E3A8A" stroke-width="3" transform="rotate(-10 44 135)"/>
  <polygon points="42,124 45,130 52,130 46,134 48,140 42,136 36,140 38,134 32,130 39,130" fill="#FDE047" transform="rotate(-10 44 135)"/>
  <!-- Wooden Sword on Right -->
  <line x1="140" y1="150" x2="168" y2="105" stroke="#94A3B8" stroke-width="6" stroke-linecap="round"/>
  <line x1="136" y1="142" x2="148" y2="150" stroke="#B45309" stroke-width="5" stroke-linecap="round"/>
  <circle cx="133" cy="155" r="4" fill="#F59E0B"/>
  <!-- Helmet & Head -->
  <ellipse cx="100" cy="74" rx="34" ry="32" fill="url(#armor)" stroke="#334155" stroke-width="4"/>
  <!-- Helmet Visor Slot & Friendly Face -->
  <rect x="72" y="66" width="56" height="24" rx="8" fill="#FEE2E2" stroke="#334155" stroke-width="3"/>
  <!-- Eyes -->
  <circle cx="86" cy="78" r="4.5" fill="#1E1B4B"/>
  <circle cx="114" cy="78" r="4.5" fill="#1E1B4B"/>
  <circle cx="87.5" cy="76" r="1.5" fill="#FFFFFF"/>
  <circle cx="115.5" cy="76" r="1.5" fill="#FFFFFF"/>
  <path d="M 96 84 Q 100 87 104 84" stroke="#7C2D12" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>"""

# 10. SIRENETTA - Mermaid
SVGS["puppet_sirenetta.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="mermaid_tail" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2DD4BF"/>
      <stop offset="100%" stop-color="#0F766E"/>
    </linearGradient>
    <linearGradient id="mermaid_hair" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FB7185"/>
      <stop offset="100%" stop-color="#E11D48"/>
    </linearGradient>
  </defs>
  <!-- Flowing Hair Back -->
  <path d="M 60 70 C 35 110 40 160 55 175 C 45 135 60 100 70 75 Z" fill="url(#mermaid_hair)" stroke="#881337" stroke-width="3"/>
  <path d="M 140 70 C 165 110 160 160 145 175 C 155 135 140 100 130 75 Z" fill="url(#mermaid_hair)" stroke="#881337" stroke-width="3"/>
  <!-- Mermaid Shimmering Tail -->
  <path d="M 85 118 C 85 145 105 160 100 180 C 85 185 75 190 92 195 C 105 190 115 195 112 185 C 115 165 115 145 115 118 Z" fill="url(#mermaid_tail)" stroke="#115E59" stroke-width="3.5"/>
  <!-- Tail Fin -->
  <path d="M 92 195 C 80 185 68 195 78 200 C 95 198 100 190 100 190 C 100 190 105 198 122 200 C 132 195 120 185 108 195 Z" fill="#2DD4BF" stroke="#115E59" stroke-width="2.5"/>
  <!-- Tail Scales -->
  <path d="M 92 135 Q 100 140 108 135 M 90 148 Q 100 154 110 148 M 94 162 Q 100 166 106 162" stroke="#5EEAD4" stroke-width="2" fill="none"/>
  <!-- Seashell Top -->
  <circle cx="90" cy="112" r="8" fill="#F472B6" stroke="#9D174D" stroke-width="2"/>
  <circle cx="110" cy="112" r="8" fill="#F472B6" stroke="#9D174D" stroke-width="2"/>
  <!-- Torso & Arms -->
  <rect x="86" y="94" width="28" height="24" rx="6" fill="#FED7AA"/>
  <rect x="74" y="100" width="8" height="18" rx="4" fill="#FED7AA"/>
  <rect x="118" y="100" width="8" height="18" rx="4" fill="#FED7AA"/>
  <!-- Head -->
  <ellipse cx="100" cy="74" rx="22" ry="20" fill="#FED7AA" stroke="#881337" stroke-width="2.5"/>
  <!-- Hair Flower -->
  <circle cx="120" cy="60" r="7" fill="#FDE047" stroke="#D97706" stroke-width="2"/>
  <!-- Eyes -->
  <ellipse cx="92" cy="72" rx="4.5" ry="6" fill="#1E1B4B"/>
  <ellipse cx="108" cy="72" rx="4.5" ry="6" fill="#1E1B4B"/>
  <circle cx="93.5" cy="70" r="1.5" fill="#FFFFFF"/>
  <circle cx="109.5" cy="70" r="1.5" fill="#FFFFFF"/>
  <!-- Cheeks & Smile -->
  <circle cx="87" cy="78" r="3" fill="#F43F5E" opacity="0.5"/>
  <circle cx="113" cy="78" r="3" fill="#F43F5E" opacity="0.5"/>
  <path d="M 96 80 Q 100 84 104 80" stroke="#881337" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>"""

# 11. MAGO - Wizard
SVGS["puppet_mago.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="wiz_robe" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#6366F1"/>
      <stop offset="100%" stop-color="#3730A3"/>
    </linearGradient>
  </defs>
  <!-- Wizard Robe -->
  <path d="M 80 100 L 120 100 L 145 175 C 115 182 85 182 55 175 Z" fill="url(#wiz_robe)" stroke="#1E1B4B" stroke-width="4"/>
  <!-- Gold Stars on Robe -->
  <polygon points="76,140 78,144 83,144 79,147 81,152 76,149 71,152 73,147 69,144 74,144" fill="#FDE047"/>
  <polygon points="120,135 122,139 127,139 123,142 125,147 120,144 115,147 117,142 113,139 118,139" fill="#FDE047"/>
  <!-- Magic Crystal Staff -->
  <line x1="142" y1="170" x2="152" y2="70" stroke="#78350F" stroke-width="5" stroke-linecap="round"/>
  <circle cx="154" cy="64" r="12" fill="#38BDF8" stroke="#0284C7" stroke-width="2.5"/>
  <circle cx="152" cy="60" r="3.5" fill="#FFFFFF"/>
  <!-- Beard -->
  <path d="M 78 88 C 78 135 122 135 122 88 Z" fill="#F8FAFC" stroke="#94A3B8" stroke-width="2.5"/>
  <!-- Head -->
  <circle cx="100" cy="80" r="22" fill="#FED7AA"/>
  <!-- Wizard Pointed Hat -->
  <ellipse cx="100" cy="64" rx="42" ry="12" fill="#4338CA" stroke="#1E1B4B" stroke-width="3.5"/>
  <path d="M 68 62 Q 100 15 132 25 Q 120 45 132 62 Z" fill="#4338CA" stroke="#1E1B4B" stroke-width="3.5"/>
  <polygon points="100,38 103,44 110,44 104,48 106,55 100,51 94,55 96,48 90,44 97,44" fill="#FDE047"/>
  <!-- Eyes -->
  <circle cx="91" cy="76" r="4" fill="#1E1B4B"/>
  <circle cx="109" cy="76" r="4" fill="#1E1B4B"/>
  <circle cx="92" cy="74" r="1.5" fill="#FFFFFF"/>
  <circle cx="110" cy="74" r="1.5" fill="#FFFFFF"/>
  <!-- Nose -->
  <ellipse cx="100" cy="82" rx="4" ry="3" fill="#FB923C"/>
</svg>"""

# 12. FATINA - Forest Fairy
SVGS["puppet_fatina.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="fairy_wings" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#E0F2FE" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#FBCFE8" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#DDD6FE" stop-opacity="0.9"/>
    </linearGradient>
    <linearGradient id="fairy_dress" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#86EFAC"/>
      <stop offset="100%" stop-color="#22C55E"/>
    </linearGradient>
  </defs>
  <!-- Iridescent Wings -->
  <ellipse cx="60" cy="90" rx="34" ry="18" fill="url(#fairy_wings)" stroke="#A855F7" stroke-width="2.5" transform="rotate(-30 60 90)"/>
  <ellipse cx="62" cy="115" rx="24" ry="12" fill="url(#fairy_wings)" stroke="#A855F7" stroke-width="2" transform="rotate(-15 62 115)"/>
  <ellipse cx="140" cy="90" rx="34" ry="18" fill="url(#fairy_wings)" stroke="#A855F7" stroke-width="2.5" transform="rotate(30 140 90)"/>
  <ellipse cx="138" cy="115" rx="24" ry="12" fill="url(#fairy_wings)" stroke="#A855F7" stroke-width="2" transform="rotate(15 138 115)"/>
  <!-- Leaf Petal Dress -->
  <path d="M 85 110 L 115 110 L 138 168 C 115 178 85 178 62 168 Z" fill="url(#fairy_dress)" stroke="#15803D" stroke-width="3.5"/>
  <!-- Legs -->
  <rect x="85" y="160" width="8" height="20" rx="4" fill="#FEE2E2"/>
  <rect x="107" y="160" width="8" height="20" rx="4" fill="#FEE2E2"/>
  <!-- Wand with Sparkles -->
  <line x1="120" y1="120" x2="148" y2="85" stroke="#F59E0B" stroke-width="2.5"/>
  <circle cx="148" cy="85" r="6" fill="#FDE047" stroke="#D97706" stroke-width="2"/>
  <!-- Head & Hair -->
  <circle cx="100" cy="74" r="22" fill="#FEE2E2" stroke="#B45309" stroke-width="2"/>
  <!-- Hair -->
  <path d="M 76 74 C 74 50 126 50 124 74 C 115 62 85 62 76 74 Z" fill="#F59E0B" stroke="#B45309" stroke-width="2.5"/>
  <circle cx="100" cy="54" r="6" fill="#F472B6"/>
  <!-- Eyes -->
  <ellipse cx="91" cy="74" rx="4" ry="5.5" fill="#1E1B4B"/>
  <ellipse cx="109" cy="74" rx="4" ry="5.5" fill="#1E1B4B"/>
  <circle cx="92.5" cy="72" r="1.5" fill="#FFFFFF"/>
  <circle cx="110.5" cy="72" r="1.5" fill="#FFFFFF"/>
  <circle cx="86" cy="80" r="3" fill="#F43F5E" opacity="0.6"/>
  <circle cx="114" cy="80" r="3" fill="#F43F5E" opacity="0.6"/>
  <path d="M 96 83 Q 100 86 104 83" stroke="#B45309" stroke-width="2" fill="none" stroke-linecap="round"/>
</svg>"""

# 13. Package ICON
SVGS["icon.svg"] = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="bg_sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1E1B4B"/>
      <stop offset="100%" stop-color="#312E81"/>
    </linearGradient>
    <linearGradient id="curtain" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#991B1B"/>
      <stop offset="50%" stop-color="#DC2626"/>
      <stop offset="100%" stop-color="#7F1D1D"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#FDE047"/>
      <stop offset="100%" stop-color="#D97706"/>
    </linearGradient>
    <linearGradient id="stage_wood" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#B45309"/>
      <stop offset="100%" stop-color="#78350F"/>
    </linearGradient>
  </defs>
  <!-- Background Disc with safe padding -->
  <rect x="16" y="16" width="224" height="224" rx="48" fill="url(#bg_sky)" stroke="#4338CA" stroke-width="4"/>
  <!-- Stars in background -->
  <circle cx="60" cy="65" r="2.5" fill="#FDE047"/>
  <circle cx="196" cy="70" r="2.5" fill="#FDE047"/>
  <circle cx="128" cy="55" r="3" fill="#FDE047"/>
  <!-- Stage Floor -->
  <rect x="24" y="180" width="208" height="48" rx="8" fill="url(#stage_wood)" stroke="#451A03" stroke-width="3"/>
  <line x1="24" y1="184" x2="232" y2="184" stroke="url(#gold)" stroke-width="3"/>
  <!-- Center Spotlight Puppet: Star Princess / Lilli -->
  <!-- Princess Puppet -->
  <ellipse cx="105" cy="135" rx="26" ry="30" fill="#F472B6" stroke="#831843" stroke-width="3"/>
  <circle cx="105" cy="98" r="18" fill="#FEE2E2" stroke="#854D0E" stroke-width="2.5"/>
  <polygon points="94,84 98,72 105,78 112,72 116,84" fill="url(#gold)"/>
  <!-- Dragon Puppet -->
  <ellipse cx="160" cy="138" rx="24" ry="26" fill="#34D399" stroke="#064E3B" stroke-width="3"/>
  <circle cx="155" cy="106" r="16" fill="#34D399" stroke="#064E3B" stroke-width="2.5"/>
  <polygon points="144,92 138,80 150,88" fill="#FDE047"/>
  <!-- Puppet Sticks -->
  <line x1="105" y1="165" x2="105" y2="195" stroke="#78350F" stroke-width="4" stroke-linecap="round"/>
  <line x1="160" y1="164" x2="160" y2="195" stroke="#78350F" stroke-width="4" stroke-linecap="round"/>
  <!-- Curtains Left & Right -->
  <path d="M 20 20 L 70 20 C 50 80 55 150 20 185 Z" fill="url(#curtain)" stroke="#450A0A" stroke-width="3"/>
  <path d="M 236 20 L 186 20 C 206 80 201 150 236 185 Z" fill="url(#curtain)" stroke="#450A0A" stroke-width="3"/>
  <!-- Top Curtain Swag -->
  <path d="M 20 20 Q 75 60 128 35 Q 181 60 236 20 Z" fill="url(#curtain)" stroke="#450A0A" stroke-width="3"/>
  <path d="M 20 20 Q 75 60 128 35 Q 181 60 236 20" fill="none" stroke="url(#gold)" stroke-width="3"/>
  <!-- Golden Theater Comedy/Tragedy Masks or Crown at top arch -->
  <polygon points="128,26 133,36 144,36 135,42 138,52 128,46 118,52 121,42 112,36 123,36" fill="url(#gold)" stroke="#B45309" stroke-width="1.5"/>
</svg>"""

print("Writing SVG source files...")
for name, content in SVGS.items():
    svg_path = OUT_SRC / name
    svg_path.write_text(content.strip(), encoding="utf-8")
    print(f"  Wrote {svg_path}")

print("Rasterizing PNG renditions...")
rsvg = "/opt/local/bin/rsvg-convert"
for name in SVGS.keys():
    svg_path = OUT_SRC / name
    if name == "icon.svg":
        png_path = OUT_ICON
        w, h = 256, 256
    else:
        png_name = name.replace(".svg", ".png")
        png_path = OUT_RUN / png_name
        w, h = 160, 160
    
    cmd = [rsvg, "--width", str(w), "--height", str(h), "--output", str(png_path), str(svg_path)]
    subprocess.run(cmd, check=True)
    print(f"  Baked {png_path} ({w}x{h})")

print("All assets successfully generated!")
