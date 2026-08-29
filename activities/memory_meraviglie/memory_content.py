"""La Memoria delle Meraviglie — content data (themes, grid configs, storage)."""

from __future__ import annotations

from typing import Any


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
STORAGE_KEY = "memory_meraviglie.progress.v1"


THEMES: list[dict[str, Any]] = [
    {
        "id": "animals",
        "name_it": "🐾 Animali",
        "name_en": "🐾 Animals",
        "bg": (240, 249, 255),
        "card_back": (59, 130, 246),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "lion", "color": (251, 191, 36), "label_it": "Leone", "label_en": "Lion"},
            {"id": "panda", "color": (226, 232, 240), "label_it": "Panda", "label_en": "Panda"},
            {"id": "fox", "color": (249, 115, 22), "label_it": "Volpe", "label_en": "Fox"},
            {"id": "cat", "color": (253, 186, 116), "label_it": "Gatto", "label_en": "Cat"},
            {"id": "dog", "color": (217, 119, 6), "label_it": "Cane", "label_en": "Dog"},
            {"id": "bunny", "color": (251, 207, 232), "label_it": "Coniglio", "label_en": "Bunny"},
            {"id": "frog", "color": (74, 222, 128), "label_it": "Rana", "label_en": "Frog"},
            {"id": "bear", "color": (180, 83, 9), "label_it": "Orso", "label_en": "Bear"},
            {"id": "pig", "color": (244, 114, 182), "label_it": "Maialino", "label_en": "Pig"},
            {"id": "monkey", "color": (161, 98, 7), "label_it": "Scimmia", "label_en": "Monkey"},
            {"id": "owl", "color": (147, 51, 234), "label_it": "Gufo", "label_en": "Owl"},
            {"id": "penguin", "color": (51, 65, 85), "label_it": "Pinguino", "label_en": "Penguin"},
            {"id": "elephant", "color": (148, 163, 184), "label_it": "Elefante", "label_en": "Elephant"},
            {"id": "unicorn", "color": (236, 72, 153), "label_it": "Unicorno", "label_en": "Unicorn"},
            {"id": "butterfly", "color": (168, 85, 247), "label_it": "Farfalla", "label_en": "Butterfly"},
            {"id": "fish", "color": (14, 165, 233), "label_it": "Pesciolino", "label_en": "Fish"},
        ],
    },
    {
        "id": "sweets",
        "name_it": "🍭 Dolcetti",
        "name_en": "🍭 Sweets",
        "bg": (253, 242, 248),
        "card_back": (236, 72, 153),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "cupcake", "color": (244, 114, 182), "label_it": "Cupcake", "label_en": "Cupcake"},
            {"id": "icecream", "color": (251, 146, 60), "label_it": "Gelato", "label_en": "Ice Cream"},
            {"id": "donut", "color": (217, 119, 6), "label_it": "Ciambella", "label_en": "Donut"},
            {"id": "strawberry", "color": (239, 68, 68), "label_it": "Fragola", "label_en": "Strawberry"},
            {"id": "cookie", "color": (180, 83, 9), "label_it": "Biscotto", "label_en": "Cookie"},
            {"id": "candy", "color": (168, 85, 247), "label_it": "Caramella", "label_en": "Candy"},
            {"id": "lollipop", "color": (234, 179, 8), "label_it": "Lecca-lecca", "label_en": "Lollipop"},
            {"id": "cake", "color": (244, 63, 94), "label_it": "Torta", "label_en": "Cake"},
            {"id": "watermelon", "color": (34, 197, 94), "label_it": "Anguria", "label_en": "Watermelon"},
            {"id": "apple", "color": (220, 38, 38), "label_it": "Mela", "label_en": "Apple"},
            {"id": "banana", "color": (234, 179, 8), "label_it": "Banana", "label_en": "Banana"},
            {"id": "chocolate", "color": (120, 53, 15), "label_it": "Cioccolato", "label_en": "Chocolate"},
            {"id": "cherry", "color": (225, 29, 72), "label_it": "Ciliegia", "label_en": "Cherry"},
            {"id": "popsicle", "color": (14, 165, 233), "label_it": "Ghiacciolo", "label_en": "Popsicle"},
            {"id": "muffin", "color": (202, 138, 4), "label_it": "Muffin", "label_en": "Muffin"},
            {"id": "honey", "color": (245, 158, 11), "label_it": "Miele", "label_en": "Honey"},
        ],
    },
    {
        "id": "vehicles",
        "name_it": "🚀 Veicoli",
        "name_en": "🚀 Vehicles",
        "bg": (238, 242, 255),
        "card_back": (99, 102, 241),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "rocket", "color": (239, 68, 68), "label_it": "Razzo", "label_en": "Rocket"},
            {"id": "train", "color": (59, 130, 246), "label_it": "Treno", "label_en": "Train"},
            {"id": "boat", "color": (14, 165, 233), "label_it": "Barca", "label_en": "Boat"},
            {"id": "car", "color": (220, 38, 38), "label_it": "Auto", "label_en": "Car"},
            {"id": "helicopter", "color": (245, 158, 11), "label_it": "Elicottero", "label_en": "Helicopter"},
            {"id": "plane", "color": (16, 185, 129), "label_it": "Aereo", "label_en": "Plane"},
            {"id": "tractor", "color": (34, 197, 94), "label_it": "Trattore", "label_en": "Tractor"},
            {"id": "submarine", "color": (234, 179, 8), "label_it": "Sottomarino", "label_en": "Submarine"},
            {"id": "fire_truck", "color": (220, 38, 38), "label_it": "Pompieri", "label_en": "Fire Truck"},
            {"id": "police_car", "color": (37, 99, 235), "label_it": "Polizia", "label_en": "Police"},
            {"id": "bus", "color": (245, 158, 11), "label_it": "Bus", "label_en": "Bus"},
            {"id": "bicycle", "color": (168, 85, 247), "label_it": "Bici", "label_en": "Bicycle"},
            {"id": "balloon", "color": (236, 72, 153), "label_it": "Mongolfiera", "label_en": "Balloon"},
            {"id": "scooter", "color": (13, 148, 136), "label_it": "Scooter", "label_en": "Scooter"},
            {"id": "ufo", "color": (99, 102, 241), "label_it": "UFO", "label_en": "UFO"},
            {"id": "truck", "color": (234, 88, 12), "label_it": "Camion", "label_en": "Truck"},
        ],
    },
    {
        "id": "nature",
        "name_it": "🌸 Natura",
        "name_en": "🌸 Nature",
        "bg": (240, 253, 244),
        "card_back": (34, 197, 94),
        "back_accent": (254, 240, 138),
        "items": [
            {"id": "sunflower", "color": (234, 179, 8), "label_it": "Girasole", "label_en": "Sunflower"},
            {"id": "mushroom", "color": (239, 68, 68), "label_it": "Fungo", "label_en": "Mushroom"},
            {"id": "rainbow", "color": (168, 85, 247), "label_it": "Arcobaleno", "label_en": "Rainbow"},
            {"id": "star", "color": (254, 202, 87), "label_it": "Stella", "label_en": "Star"},
            {"id": "sun", "color": (245, 158, 11), "label_it": "Sole", "label_en": "Sun"},
            {"id": "moon", "color": (253, 224, 71), "label_it": "Luna", "label_en": "Moon"},
            {"id": "flower", "color": (244, 114, 182), "label_it": "Fiore", "label_en": "Flower"},
            {"id": "clover", "color": (16, 185, 129), "label_it": "Quadrifoglio", "label_en": "Clover"},
            {"id": "tree", "color": (22, 163, 74), "label_it": "Albero", "label_en": "Tree"},
            {"id": "cloud", "color": (56, 189, 248), "label_it": "Nuvola", "label_en": "Cloud"},
            {"id": "leaf", "color": (249, 115, 22), "label_it": "Foglia", "label_en": "Leaf"},
            {"id": "mountain", "color": (100, 116, 139), "label_it": "Montagna", "label_en": "Mountain"},
            {"id": "snowflake", "color": (14, 165, 233), "label_it": "Neve", "label_en": "Snowflake"},
            {"id": "planet", "color": (99, 102, 241), "label_it": "Pianeta", "label_en": "Planet"},
            {"id": "shell", "color": (251, 146, 60), "label_it": "Conchiglia", "label_en": "Shell"},
            {"id": "acorn", "color": (180, 83, 9), "label_it": "Ghianda", "label_en": "Acorn"},
        ],
    },
]


GRID_CONFIGS: list[dict[str, Any]] = [
    {"id": "small", "label_key": "grid.small", "label": "2x2", "cols": 2, "rows": 2, "pairs": 2},
    {"id": "medium", "label_key": "grid.medium", "label": "3x2", "cols": 3, "rows": 2, "pairs": 3},
    {"id": "large", "label_key": "grid.large", "label": "4x3", "cols": 4, "rows": 3, "pairs": 6},
    {"id": "xlarge", "label_key": "grid.xlarge", "label": "4x4", "cols": 4, "rows": 4, "pairs": 8},
    {"id": "giant", "label_key": "grid.giant", "label": "6x3", "cols": 6, "rows": 3, "pairs": 9},
]
